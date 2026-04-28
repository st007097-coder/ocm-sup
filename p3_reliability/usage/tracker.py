"""
Usage Tracker - tracks memory retrieval and usage events.
"""

import json
from typing import Optional
from datetime import datetime
from pathlib import Path

STATE_DIR = Path("~/.openclaw/ocm-sup").expanduser()
STATE_DIR.mkdir(parents=True, exist_ok=True)


class UsageTracker:
    """
    Tracks when facts are retrieved, used in output, and influence decisions.

    Events:
    - on_retrieve: fact was retrieved from memory
    - on_output: fact appeared in agent response
    - on_agent_decision: agent made decision influenced by fact
    """

    def __init__(self):
        self._state_file = STATE_DIR / "usage_tracking.json"
        self._tracking: dict[str, dict] = self._load()
        self._context_history: list[dict] = []  # rolling window
        self._max_context_history = 50

    def _load(self) -> dict:
        """Load tracking state from disk."""
        if self._state_file.exists():
            with open(self._state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save(self):
        """Save tracking state to disk."""
        with open(self._state_file, "w", encoding="utf-8") as f:
            json.dump(self._tracking, f, ensure_ascii=False, indent=2)

    def _ensure_fact(self, fact_id: str):
        """Ensure fact exists in tracking state."""
        if fact_id not in self._tracking:
            self._tracking[fact_id] = {
                "retrieve_count": 0,
                "used_in_output": False,
                "last_retrieved": None,
                "last_used": None,
                "decision_influenced_count": 0,
                "decision_influenced_last": None
            }

    def on_retrieve(self, fact_id: str, context: str = ""):
        """
        Record fact retrieval event.

        Args:
            fact_id: ID of retrieved fact
            context: current query/command context (for pattern detection)
        """
        self._ensure_fact(fact_id)
        self._tracking[fact_id]["retrieve_count"] += 1
        self._tracking[fact_id]["last_retrieved"] = datetime.now().isoformat()

        # Add to context history for pattern detection
        if context:
            self._context_history.append({
                "context": context,
                "fact_id": fact_id,
                "timestamp": datetime.now().isoformat()
            })
            # Trim to rolling window
            if len(self._context_history) > self._max_context_history:
                self._context_history = self._context_history[-self._max_context_history:]

        self._save()

    def on_output(self, fact_id: str):
        """
        Record fact appeared in agent output.

        Args:
            fact_id: ID of fact used in output
        """
        self._ensure_fact(fact_id)
        self._tracking[fact_id]["used_in_output"] = True
        self._tracking[fact_id]["last_used"] = datetime.now().isoformat()
        self._save()

    def on_agent_decision(self, pattern: str, facts_used: list[str]):
        """
        Record agent decision influenced by memory.

        Args:
            pattern: context pattern (e.g., "user debugging system")
            facts_used: list of fact IDs that influenced decision
        """
        for fact_id in facts_used:
            self._ensure_fact(fact_id)
            self._tracking[fact_id]["decision_influenced_count"] += 1
            self._tracking[fact_id]["decision_influenced_last"] = datetime.now().isoformat()

        self._save()

    def get_stats(self, fact_id: str) -> Optional[dict]:
        """Get usage statistics for a fact."""
        if fact_id not in self._tracking:
            return None

        t = self._tracking[fact_id]
        retrieve_count = t["retrieve_count"]
        used_in_output = t["used_in_output"]
        influenced_count = t["decision_influenced_count"]

        return {
            "retrieve_count": retrieve_count,
            "used_in_output": used_in_output,
            "decision_influenced_count": influenced_count,
            "usage_ratio": (
                1.0 if used_in_output else 0.0
            ) / retrieve_count if retrieve_count > 0 else 0,
            "last_retrieved": t["last_retrieved"],
            "last_used": t["last_used"],
            "decision_influenced_last": t["decision_influenced_last"]
        }

    def get_ignored_facts(self, min_retrieves: int = 10, usage_threshold: float = 0.1) -> list[str]:
        """
        Get facts that are frequently retrieved but never used.

        Args:
            min_retrieves: minimum retrieval count to consider
            usage_threshold: max usage_ratio to be considered "ignored"

        Returns:
            list of ignored fact IDs
        """
        ignored = []
        for fact_id, stats in self._tracking.items():
            if stats["retrieve_count"] >= min_retrieves:
                ratio = stats["used_in_output"] / stats["retrieve_count"] if stats["retrieve_count"] > 0 else 0
                if ratio < usage_threshold:
                    ignored.append(fact_id)
        return ignored

    def is_fact_used(self, fact_id: str) -> bool:
        """Check if a fact has ever been used in output."""
        return self._tracking.get(fact_id, {}).get("used_in_output", False)

    def get_utilization_rate(self) -> float:
        """
        Get overall memory utilization rate.

        Returns:
            fraction of facts that have been used in output
        """
        if not self._tracking:
            return 0.0

        used = sum(1 for s in self._tracking.values() if s["used_in_output"])
        return used / len(self._tracking)


# Module-level convenience functions
_tracker = None

def _get_tracker() -> UsageTracker:
    global _tracker
    if _tracker is None:
        _tracker = UsageTracker()
    return _tracker


def on_retrieve(fact_id: str, context: str = ""):
    """Record fact retrieval event."""
    _get_tracker().on_retrieve(fact_id, context)


def on_output(fact_id: str):
    """Record fact appeared in output."""
    _get_tracker().on_output(fact_id)


def on_agent_decision(pattern: str, facts_used: list[str]):
    """Record agent decision influenced by memory."""
    _get_tracker().on_agent_decision(pattern, facts_used)