"""
Transaction Manager - orchestrates atomic writes across structured + vector + graph layers.
Provides begin/commit/rollback semantics for fact operations.

Actual implementation connects to:
- Structured storage: JSON files in ~/.openclaw/ocm-sup/structured/
- Vector storage: numpy embeddings in ~/.openclaw/ocm-sup/embeddings/
- Graph storage: JSON graph in ~/.openclaw/ocm-sup/graph/
"""

import uuid
import json
import os
from typing import Optional, Literal, Any
from datetime import datetime
from pathlib import Path

from .tx_log import Transaction, TransactionLog, TransactionStatus, OperationType

# Storage directories
STRUCTURED_DIR = Path("~/.openclaw/ocm-sup/structured").expanduser()
VECTOR_DIR = Path("~/.openclaw/ocm-sup/embeddings").expanduser()
GRAPH_DIR = Path("~/.openclaw/ocm-sup/graph").expanduser()

# Ensure directories exist
STRUCTURED_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_DIR.mkdir(parents=True, exist_ok=True)
GRAPH_DIR.mkdir(parents=True, exist_ok=True)


class StorageLayer:
    """
    Actual storage layer implementation for structured, vector, and graph.
    Each layer handles read/write/delete operations for its data type.
    """

    def __init__(self, layer_type: Literal["structured", "vector", "graph"], base_dir: Path):
        self.layer_type = layer_type
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _entity_path(self, entity_id: str) -> Path:
        """Get file path for an entity."""
        return self.base_dir / f"{entity_id}.json"

    def write(self, entity_id: str, data: dict) -> bool:
        """
        Write entity data.

        Args:
            entity_id: Unique identifier for the entity
            data: Entity data to write

        Returns:
            True if write succeeded
        """
        try:
            file_path = self._entity_path(entity_id)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            # Log error but don't fail
            return False

    def delete(self, entity_id: str) -> bool:
        """Delete an entity."""
        try:
            file_path = self._entity_path(entity_id)
            if file_path.exists():
                file_path.unlink()
            return True
        except Exception:
            return False

    def exists(self, entity_id: str) -> bool:
        """Check if entity exists."""
        return self._entity_path(entity_id).exists()

    def read(self, entity_id: str) -> Optional[dict]:
        """Read entity data."""
        try:
            file_path = self._entity_path(entity_id)
            if not file_path.exists():
                return None
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def list_all(self) -> list[str]:
        """List all entity IDs in this layer."""
        try:
            return [f.stem for f in self.base_dir.glob("*.json")]
        except Exception:
            return []


class TransactionManager:
    """
    Orchestrates atomic transactions across multiple storage layers.

    Usage:
        tm = TransactionManager()
        with tm.begin("write_fact", {"entity_id": "fact_123", "content": "..."}) as tx:
            tm.write_structured({"entity_id": "fact_123", "data": {...}})
            tm.write_vector({"entity_id": "fact_123", "embedding": [...]})
            tm.write_graph({"entity_id": "fact_123", "relations": [...]})
        # If any write fails, all are rolled back
    """

    def __init__(self, tx_log: TransactionLog = None):
        self._tx_log = tx_log or TransactionLog()

        # Initialize actual storage layers
        self._structured = StorageLayer("structured", STRUCTURED_DIR)
        self._vector = StorageLayer("vector", VECTOR_DIR)
        self._graph = StorageLayer("graph", GRAPH_DIR)

        self._active_tx: Optional[Transaction] = None
        self._write_order = ["structured", "vector", "graph"]
        self._tx_data: dict = {}  # Temporary data for active transaction

    def begin(self, operation: str, payload: dict) -> "TransactionContext":
        """
        Begin a new transaction.

        Returns a context manager (use with `with`).
        """
        return TransactionContext(self, operation, payload)

    def _begin_internal(self, operation: str, payload: dict) -> Transaction:
        """Internal method to start a transaction."""
        # Capture rollback data (current state of affected entities)
        rollback_data = self._capture_rollback_data(payload)

        tx = Transaction(
            id=str(uuid.uuid4()),
            operation=operation,
            payload=payload,
            rollback_data=rollback_data,
            status=TransactionStatus.PENDING
        )

        self._tx_log.begin(tx)
        self._active_tx = tx
        self._tx_data = {}  # Reset temp data storage
        return tx

    def _capture_rollback_data(self, payload: dict) -> dict:
        """Capture current state of all affected entities for rollback."""
        rollback = {}
        entity_id = payload.get("entity_id")

        if entity_id:
            for layer_name, layer in [("structured", self._structured),
                                       ("vector", self._vector),
                                       ("graph", self._graph)]:
                state = layer.read(entity_id)
                if state:
                    rollback[layer_name] = {entity_id: state}

        return rollback

    def write_structured(self, data: dict) -> bool:
        """Write to structured layer (must be within transaction)."""
        return self._write_layer("structured", data)

    def write_vector(self, data: dict) -> bool:
        """Write to vector layer (must be within transaction)."""
        return self._write_layer("vector", data)

    def write_graph(self, data: dict) -> bool:
        """Write to graph layer (must be within transaction)."""
        return self._write_layer("graph", data)

    def _write_layer(self, layer_name: str, data: dict) -> bool:
        """
        Internal write to a specific layer.

        Args:
            layer_name: "structured", "vector", or "graph"
            data: Entity data (must contain "entity_id")

        Returns:
            True if write succeeded
        """
        if self._active_tx is None:
            raise RuntimeError("Write called outside transaction context")

        entity_id = data.get("entity_id")
        if not entity_id:
            raise ValueError(f"{layer_name} write requires entity_id in data")

        # Store in temp data (will be committed on success)
        if layer_name not in self._tx_data:
            self._tx_data[layer_name] = {}
        self._tx_data[layer_name][entity_id] = data

        return True  # Optimistic success - will be committed

    def _commit(self):
        """Commit the active transaction - write all pending data to storage."""
        if self._active_tx is None:
            return

        entity_id = self._active_tx.payload.get("entity_id")
        errors = []

        # Write to each layer
        for layer_name, layer in [("structured", self._structured),
                                   ("vector", self._vector),
                                   ("graph", self._graph)]:
            if layer_name in self._tx_data and entity_id in self._tx_data[layer_name]:
                data = self._tx_data[layer_name][entity_id]
                success = layer.write(entity_id, data)
                if not success:
                    errors.append(f"{layer_name}: write failed")

        if errors:
            # Some writes failed - rollback
            self._rollback_internal()
            raise RuntimeError(f"Transaction failed: {', '.join(errors)}")

        # All succeeded - commit
        self._tx_log.commit(self._active_tx)
        self._active_tx = None
        self._tx_data = {}

    def _rollback_internal(self):
        """Internal rollback - restore previous state."""
        if self._active_tx is None:
            return

        tx = self._active_tx

        # Restore previous state from rollback_data
        if tx.rollback_data:
            for layer_name, entities in tx.rollback_data.items():
                layer = {"structured": self._structured,
                         "vector": self._vector,
                         "graph": self._graph}.get(layer_name)
                if layer:
                    for eid, state in entities.items():
                        layer.write(eid, state)

        self._tx_log.rollback(tx)
        self._active_tx = None
        self._tx_data = {}

    def _rollback(self):
        """Rollback the active transaction."""
        self._rollback_internal()

    def get_status(self) -> dict:
        """Get transaction manager status."""
        counts = self._tx_log.count()
        return {
            "active_tx": self._active_tx.id if self._active_tx else None,
            "registered_layers": self._write_order,
            "transaction_counts": counts,
            "storage_paths": {
                "structured": str(STRUCTURED_DIR),
                "vector": str(VECTOR_DIR),
                "graph": str(GRAPH_DIR)
            }
        }

    def get_layer_state(self, layer_name: str, entity_id: str) -> bool:
        """Check if entity exists in a specific layer (for reconciliation)."""
        layer = {"structured": self._structured,
                 "vector": self._vector,
                 "graph": self._graph}.get(layer_name)
        if layer:
            return layer.exists(entity_id)
        return False

    def get_entity(self, entity_id: str) -> dict:
        """Get entity from all layers."""
        return {
            "structured": self._structured.read(entity_id),
            "vector": self._vector.read(entity_id),
            "graph": self._graph.read(entity_id)
        }


class TransactionContext:
    """
    Context manager for transaction scope.

    Usage:
        with tm.begin("write_fact", payload) as tx:
            tm.write_structured({...})
            tm.write_vector({...})
            tm.write_graph({...})
    """

    def __init__(self, manager: TransactionManager, operation: str, payload: dict):
        self._manager = manager
        self._operation = operation
        self._payload = payload
        self._tx: Optional[Transaction] = None
        self._failed = False
        self._error = None

    def __enter__(self) -> Transaction:
        self._tx = self._manager._begin_internal(self._operation, self._payload)
        return self._tx

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Exception occurred - rollback
            self._manager._rollback()
            return False

        if self._failed:
            # Marked as failed - rollback
            self._manager._rollback()
            return False

        # Success - commit
        self._manager._commit()
        return True

    def fail(self, error: str = ""):
        """Mark transaction as failed (call this instead of raising)."""
        self._failed = True
        self._error = error

    @property
    def transaction(self) -> Optional[Transaction]:
        return self._tx