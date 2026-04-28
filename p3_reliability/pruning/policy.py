"""
Pruning Policy - scheduling and execution of memory pruning.
"""

import os
import json
from typing import Optional, Literal
from datetime import datetime, timedelta
from pathlib import Path

from .scorer import PruneScorer, DEFAULT_PRUNE_THRESHOLD
from .archiver import FactArchiver

ARCHIVE_DIR = Path("~/.openclaw/ocm-sup/archive").expanduser()
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

# Default schedule: 03:00 HKT daily
DEFAULT_SCHEDULE_HOUR = 3
DEFAULT_SCHEDULE_MINUTE = 0


class PruningPolicy:
    """
    Manages pruning schedule and execution.

    Supports:
    - Scheduled pruning (daily at configured time)
    - Manual trigger
    - Dry-run mode
    - Archive before delete (30-day recovery)
    """

    def __init__(
        self,
        threshold: float = DEFAULT_PRUNE_THRESHOLD,
        archive_ttl_days: int = 30,
        schedule_hour: int = DEFAULT_SCHEDULE_HOUR,
        schedule_minute: int = DEFAULT_SCHEDULE_MINUTE
    ):
        self.threshold = threshold
        self.archive_ttl_days = archive_ttl_days
        self.schedule_hour = schedule_hour
        self.schedule_minute = schedule_minute
        self.scorer = PruneScorer(threshold=threshold)
        self.archiver = FactArchiver(ttl_days=archive_ttl_days)
        self._last_run: Optional[datetime] = None
        self._load_state()

    def _state_file(self) -> Path:
        return ARCHIVE_DIR / "pruning_state.json"

    def _load_state(self):
        """Load last run timestamp."""
        sf = self._state_file()
        if sf.exists():
            with open(sf, "r") as f:
                data = json.load(f)
                ts = data.get("last_run")
                if ts:
                    self._last_run = datetime.fromisoformat(ts)

    def _save_state(self):
        """Save last run timestamp."""
        sf = self._state_file()
        with open(sf, "w") as f:
            json.dump({
                "last_run": self._last_run.isoformat() if self._last_run else None,
                "threshold": self.threshold,
                "archive_ttl_days": self.archive_ttl_days
            }, f)

    def should_run_now(self) -> bool:
        """
        Check if pruning should run now based on schedule.

        Returns True if current time matches scheduled time (±5 min window).
        """
        now = datetime.now()
        scheduled = now.replace(
            hour=self.schedule_hour,
            minute=self.schedule_minute,
            second=0,
            microsecond=0
        )

        # Within 5-minute window
        diff = abs((now - scheduled).total_seconds())
        return diff <= 300

    def execute(
        self,
        facts: list[dict],
        dry_run: bool = True,
        get_fact_text: callable = None
    ) -> dict:
        """
        Execute pruning on facts.

        Args:
            facts: list of fact dicts
            dry_run: if True, don't actually delete (default True)
            get_fact_text: optional func to get fact text for logging

        Returns:
            dict with results: {pruned_count, archived_count, scores}
        """
        results = {
            "dry_run": dry_run,
            "total_facts": len(facts),
            "pruned_count": 0,
            "archived_count": 0,
            "total_score": 0.0,
            "pruned_facts": []
        }

        for fact in facts:
            score = self.scorer.compute(fact)
            results["total_score"] += score

            if self.scorer.should_prune(fact):
                fact_id = fact.get("id", "unknown")

                if not dry_run:
                    # Archive before delete
                    fact_text = get_fact_text(fact) if get_fact_text else fact.get("content", "")
                    self.archiver.archive(fact_id, fact_text, fact)

                    # Delete from all layers (call layer interfaces)
                    # Implementation depends on actual storage

                results["pruned_count"] += 1
                results["pruned_facts"].append({
                    "id": fact_id,
                    "score": score
                })

        if not dry_run:
            self._last_run = datetime.now()
            self._save_state()

        return results

    def get_stats(self, facts: list[dict]) -> dict:
        """Get pruning statistics without executing."""
        total = len(facts)
        prune_eligible = sum(1 for f in facts if self.scorer.should_prune(f))
        scores = [self.scorer.compute(f) for f in facts]

        return {
            "total_facts": total,
            "prune_eligible": prune_eligible,
            "prune_rate": prune_eligible / total if total > 0 else 0,
            "mean_score": sum(scores) / len(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "threshold": self.threshold,
            "last_run": self._last_run.isoformat() if self._last_run else None
        }


def prune_batch(
    facts: list[dict],
    threshold: float = DEFAULT_PRUNE_THRESHOLD,
    dry_run: bool = True
) -> dict:
    """
    Convenience function for batch pruning.

    Args:
        facts: list of fact dicts
        threshold: prune threshold (default 0.7)
        dry_run: if True, don't delete (default True)

    Returns:
        pruning results dict
    """
    policy = PruningPolicy(threshold=threshold)
    return policy.execute(facts, dry_run=dry_run)