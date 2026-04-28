"""
Transaction Manager with Rollback
OCM Sup v2.6

Simple transaction management with crash recovery.
Based on user's tx_manager.py design + P3 rollback concept.

Usage:
    with tx_manager.begin("write_fact", payload) as tx:
        tx_manager.write_structured(tx, data)
        tx_manager.write_vector(tx, data)
        tx_manager.write_graph(tx, data)
    # Auto-commits if no exception
    # Auto-rollbacks if exception occurs
"""

import json
import os
import time
import uuid
from pathlib import Path
from typing import Dict, Optional, Any
from contextlib import contextmanager

from . import config


class Transaction:
    """A transaction context."""
    
    def __init__(self, tx_id: str, operation: str, payload: dict):
        self.tx_id = tx_id
        self.operation = operation
        self.payload = payload
        self.status = "pending"
        self.steps = {"structured": False, "vector": False, "graph": False}
        self.timestamp = time.time()
    
    def to_dict(self) -> dict:
        return {
            "tx_id": self.tx_id,
            "operation": self.operation,
            "payload": self.payload,
            "status": self.status,
            "steps": self.steps,
            "timestamp": self.timestamp
        }
    
    @property
    def path(self) -> Path:
        return config.TX_DIR / f"{self.tx_id}.json"
    
    def save(self):
        """Save transaction state to disk."""
        config.TX_DIR.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def load(self, tx_id: str) -> bool:
        """Load transaction from disk. Returns True if found."""
        path = config.TX_DIR / f"{tx_id}.json"
        if path.exists():
            with open(path) as f:
                data = json.load(f)
                self.tx_id = data["tx_id"]
                self.operation = data["operation"]
                self.payload = data["payload"]
                self.status = data["status"]
                self.steps = data["steps"]
                self.timestamp = data["timestamp"]
            return True
        return False


class TransactionManager:
    """
    Transaction manager with atomic writes and rollback.
    
    Features:
    - Context manager for automatic commit/rollback
    - Pending transaction recovery on startup
    - Step-level tracking
    """
    
    def __init__(self):
        config.TX_DIR.mkdir(parents=True, exist_ok=True)
        self._active_tx: Optional[Transaction] = None
    
    @contextmanager
    def begin(self, operation: str, payload: dict):
        """
        Context manager for transaction.
        
        Usage:
            with tx_manager.begin("write_fact", payload) as tx:
                tx_manager.write_structured(tx, data)
                tx_manager.write_vector(tx, data)
                tx_manager.write_graph(tx, data)
            # Auto-commits here if no exception
        """
        tx = Transaction(str(uuid.uuid4()), operation, payload)
        tx.save()
        self._active_tx = tx
        
        try:
            yield tx
            # If we get here without exception, commit
            self.commit(tx)
        except Exception as e:
            # Rollback on any exception
            self.rollback(tx)
            raise e
        finally:
            self._active_tx = None
    
    def write_structured(self, tx: Transaction, data: dict) -> bool:
        """
        Write data to structured storage layer.
        Marks 'structured' step as complete.
        """
        entity_id = data.get("entity_id") or self._generate_id(data)
        filepath = config.STORAGE_DIR / f"{entity_id}.json"
        
        record = {
            "entity_id": entity_id,
            "type": data.get("type"),
            "subject": data.get("subject"),
            "action": data.get("action"),
            "metadata": data.get("metadata", {}),
            "created_at": data.get("created_at", time.time()),
            "tx_id": tx.tx_id
        }
        
        with open(filepath, "w") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        
        tx.steps["structured"] = True
        tx.save()
        return True
    
    def write_vector(self, tx: Transaction, data: dict) -> bool:
        """
        Write data to vector storage layer (embeddings).
        Marks 'vector' step as complete.
        """
        entity_id = data.get("entity_id")
        filepath = config.VECTOR_DIR / f"{entity_id}.json"
        
        record = {
            "entity_id": entity_id,
            "embedding_text": data.get("embedding_text", ""),
            "tx_id": tx.tx_id
        }
        
        with open(filepath, "w") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        
        tx.steps["vector"] = True
        tx.save()
        return True
    
    def write_graph(self, tx: Transaction, data: dict) -> bool:
        """
        Write data to graph storage layer.
        Marks 'graph' step as complete.
        """
        entity_id = data.get("entity_id")
        filepath = config.GRAPH_DIR / f"{entity_id}.json"
        
        record = {
            "entity_id": entity_id,
            "subject": data.get("subject"),
            "entities": data.get("entities", []),
            "relations": data.get("relations", []),
            "tx_id": tx.tx_id
        }
        
        with open(filepath, "w") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        
        tx.steps["graph"] = True
        tx.save()
        return True
    
    def commit(self, tx: Transaction) -> bool:
        """Mark transaction as committed."""
        tx.status = "committed"
        tx.save()
        
        # Clean up old pending transactions (keep last 100)
        self._cleanup_old_transactions()
        return True
    
    def rollback(self, tx: Transaction):
        """
        Rollback transaction by removing partial writes.
        """
        tx.status = "rolled_back"
        tx.save()
        
        # Remove any files written by this transaction
        for step in ["structured", "vector", "graph"]:
            if tx.steps.get(step):
                entity_id = tx.payload.get("entity_id")
                if entity_id:
                    if step == "structured":
                        filepath = config.STORAGE_DIR / f"{entity_id}.json"
                    elif step == "vector":
                        filepath = config.VECTOR_DIR / f"{entity_id}.json"
                    else:
                        filepath = config.GRAPH_DIR / f"{entity_id}.json"
                    
                    if filepath.exists():
                        filepath.unlink()
        
        return True
    
    def recover_pending(self) -> list[dict]:
        """
        Recover pending transactions on startup.
        Returns list of recovered transactions.
        """
        recovered = []
        
        if not config.TX_DIR.exists():
            return recovered
        
        for fname in os.listdir(config.TX_DIR):
            if not fname.endswith(".json"):
                continue
            
            path = config.TX_DIR / fname
            with open(path) as f:
                tx_data = json.load(f)
            
            if tx_data["status"] == "pending":
                recovered.append(tx_data)
                print(f"[RECOVER] Pending transaction: {tx_data['tx_id']} ({tx_data['operation']})")
        
        return recovered
    
    def _generate_id(self, data: dict) -> str:
        """Generate deterministic ID from data."""
        content = f"{data.get('type')}:{data.get('subject')}:{data.get('action')}"
        import hashlib
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _cleanup_old_transactions(self, keep_last: int = 100):
        """Remove old committed transactions, keeping only the most recent."""
        txs = []
        for fname in os.listdir(config.TX_DIR):
            if not fname.endswith(".json"):
                continue
            path = config.TX_DIR / fname
            with open(path) as f:
                txs.append((path, json.load(f)))
        
        # Sort by timestamp descending
        txs.sort(key=lambda x: x[1].get("timestamp", 0), reverse=True)
        
        # Remove old committed (keep last N)
        for path, data in txs[keep_last:]:
            if data["status"] == "committed":
                path.unlink()
