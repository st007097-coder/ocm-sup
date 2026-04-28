"""
Background Reconciliation Job - fixes stale pending transactions.
Runs periodically to detect and repair partial writes.
"""

import time
from datetime import datetime, timedelta
from typing import Optional

from .tx_log import TransactionLog, Transaction, TransactionStatus


# Default reconciliation interval
DEFAULT_INTERVAL_SECONDS = 300  # 5 minutes
DEFAULT_STALE_THRESHOLD_SECONDS = 300  # 5 minutes


class ReconciliationJob:
    """
    Background job that reconciles pending transactions.

    Detects:
    - Stale pending transactions (partial writes that didn't complete)
    - Orphaned writes (layer written but not all layers)

    Fixes:
    - Completes partial writes
    - Rolls back orphaned writes
    """

    def __init__(
        self,
        tx_log: TransactionLog,
        get_layer_state: callable,  # func(layer, entity_id) -> bool
        complete_write: callable,   # func(tx) -> bool
        rollback_tx: callable,      # func(tx) -> bool
        interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
        stale_threshold_seconds: int = DEFAULT_STALE_THRESHOLD_SECONDS
    ):
        self._tx_log = tx_log
        self._get_layer_state = get_layer_state
        self._complete_write = complete_write
        self._rollback_tx = rollback_tx
        self._interval = interval_seconds
        self._stale_threshold = stale_threshold_seconds
        self._running = False

    def run_once(self) -> dict:
        """
        Run one reconciliation cycle.

        Returns:
            dict with reconciliation results
        """
        pending = self._tx_log.get_pending()
        results = {
            "checked": len(pending),
            "completed": 0,
            "rolled_back": 0,
            "still_pending": 0,
            "errors": []
        }

        now = datetime.now()
        stale_threshold = timedelta(seconds=self._stale_threshold)

        for tx in pending:
            try:
                created = datetime.fromisoformat(tx.created_at)
                age = now - created

                if age > stale_threshold:
                    # Stale transaction - check state and repair
                    action = self._reconcile_stale(tx)
                    if action == "completed":
                        results["completed"] += 1
                    elif action == "rolled_back":
                        results["rolled_back"] += 1
                    else:
                        results["still_pending"] += 1
                else:
                    # Not stale yet - leave for next cycle
                    results["still_pending"] += 1

            except Exception as e:
                results["errors"].append(f"Tx {tx.id}: {e}")

        return results

    def _reconcile_stale(self, tx: Transaction) -> str:
        """
        Reconcile a stale transaction.

        Returns:
            "completed" - transaction was completed
            "rolled_back" - transaction was rolled back
            "pending" - could not determine action
        """
        payload = tx.payload
        entity_id = payload.get("entity_id")

        # Check each layer's state
        layer_states = {}
        for layer in ["structured", "vector", "graph"]:
            layer_states[layer] = self._get_layer_state(layer, entity_id)

        # Decision logic:
        # - If all layers written → commit
        # - If some layers written but not all → complete the rest OR rollback
        # - If no layers written → rollback

        all_written = all(layer_states.values())
        none_written = not any(layer_states.values())

        if all_written:
            # All layers written - commit
            self._complete_write(tx)
            return "completed"

        elif none_written:
            # No layers written - rollback
            self._rollback_tx(tx)
            return "rolled_back"

        else:
            # Partial write - need case-by-case decision
            # For now, rollback to be safe
            self._rollback_tx(tx)
            return "rolled_back"

    def start(self):
        """Start background reconciliation loop."""
        self._running = True
        while self._running:
            try:
                self.run_once()
            except Exception as e:
                # Log error but continue
                pass
            time.sleep(self._interval)

    def stop(self):
        """Stop background reconciliation loop."""
        self._running = False