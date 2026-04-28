"""
Transaction Log - persistent record of all transactions for atomicity guarantee.
Supports rollback of partial writes if any layer fails.
"""

import os
import json
from typing import Optional
from datetime import datetime
from enum import Enum
from pathlib import Path

TX_DIR = Path("~/.openclaw/ocm-sup/transactions").expanduser()
TX_DIR.mkdir(parents=True, exist_ok=True)


class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMMITTED = "committed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class OperationType(str, Enum):
    WRITE_FACT = "write_fact"
    DELETE_FACT = "delete_fact"
    UPDATE_FACT = "update_fact"
    WRITE_ENTITY = "write_entity"
    DELETE_ENTITY = "delete_entity"


class Transaction:
    """Represents a single atomic transaction."""

    def __init__(
        self,
        id: str,
        operation: str,
        payload: dict,
        rollback_data: Optional[dict] = None,
        status: str = TransactionStatus.PENDING,
        created_at: str = None,
        committed_at: Optional[str] = None,
        failed_at: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        self.id = id
        self.operation = operation
        self.payload = payload
        self.rollback_data = rollback_data
        self.status = status
        self.created_at = created_at or datetime.now().isoformat()
        self.committed_at = committed_at
        self.failed_at = failed_at
        self.error_message = error_message

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "operation": self.operation,
            "payload": self.payload,
            "rollback_data": self.rollback_data,
            "status": self.status,
            "created_at": self.created_at,
            "committed_at": self.committed_at,
            "failed_at": self.failed_at,
            "error_message": self.error_message
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Transaction":
        return cls(**d)

    def mark_committed(self):
        self.status = TransactionStatus.COMMITTED
        self.committed_at = datetime.now().isoformat()
        self.rollback_data = None  # Release rollback data on commit

    def mark_failed(self, error: str = ""):
        self.status = TransactionStatus.FAILED
        self.failed_at = datetime.now().isoformat()
        self.error_message = error

    def mark_rolled_back(self):
        self.status = TransactionStatus.ROLLED_BACK
        self.failed_at = datetime.now().isoformat()


class TransactionLog:
    """
    Persistent transaction log with atomic writes.

    All transactions are written to disk before being considered valid.
    On restart, pending transactions are reconciled.
    """

    def __init__(self):
        self._log_file = TX_DIR / "transaction_log.jsonl"
        self._pending: list[Transaction] = []
        self._load_pending()

    def _load_pending(self):
        """Load all pending transactions from disk on startup."""
        if not self._log_file.exists():
            return

        with open(self._log_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                tx = Transaction.from_dict(json.loads(line))
                if tx.status == TransactionStatus.PENDING:
                    self._pending.append(tx)

    def _append_log(self, tx: Transaction):
        """Append transaction to log file (durable write)."""
        with open(self._log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(tx.to_dict(), ensure_ascii=False) + "\n")

    def _overwrite_log(self, tx: Transaction):
        """Overwrite transaction status in log (for committed/failed)."""
        # Read all, update target, rewrite
        if not self._log_file.exists():
            return

        lines = []
        with open(self._log_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                t = Transaction.from_dict(json.loads(line))
                if t.id == tx.id:
                    lines.append(json.dumps(tx.to_dict(), ensure_ascii=False) + "\n")
                else:
                    lines.append(line)

        with open(self._log_file, "w", encoding="utf-8") as f:
            f.writelines(lines)

    def begin(self, tx: Transaction) -> Transaction:
        """
        Begin a new transaction.

        Returns the transaction with updated status.
        """
        self._append_log(tx)
        self._pending.append(tx)
        return tx

    def commit(self, tx: Transaction):
        """Mark transaction as committed."""
        tx.mark_committed()
        self._overwrite_log(tx)
        if tx in self._pending:
            self._pending.remove(tx)

    def rollback(self, tx: Transaction):
        """Mark transaction as rolled back."""
        tx.mark_rolled_back()
        self._overwrite_log(tx)
        if tx in self._pending:
            self._pending.remove(tx)

    def fail(self, tx: Transaction, error: str):
        """Mark transaction as failed."""
        tx.mark_failed(error)
        self._overwrite_log(tx)
        if tx in self._pending:
            self._pending.remove(tx)

    def get_pending(self) -> list[Transaction]:
        """Get all pending transactions."""
        return list(self._pending)

    def get_by_id(self, tx_id: str) -> Optional[Transaction]:
        """Get transaction by ID."""
        for tx in self._pending:
            if tx.id == tx_id:
                return tx
        return None

    def count(self) -> dict:
        """Get transaction counts by status."""
        counts = {s: 0 for s in TransactionStatus}
        if self._log_file.exists():
            with open(self._log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    tx = Transaction.from_dict(json.loads(line))
                    counts[tx.status] = counts.get(tx.status, 0) + 1
        return counts