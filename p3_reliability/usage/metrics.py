"""
Usage Metrics - statistics and reporting for memory usage.
"""

from typing import Optional
from datetime import datetime, timedelta

from .tracker import UsageTracker

# Default ignored threshold
DEFAULT_MIN_RETRIEVES = 10
DEFAULT_USAGE_THRESHOLD = 0.1
DEFAULT_IGNORED_DAYS = 30


class UsageMetrics:
    """
    Generates usage reports and alerts.
    """

    def __init__(self, tracker: UsageTracker = None):
        self._tracker = tracker or UsageTracker()

    def get_utilization_rate(self) -> float:
        """Get overall memory utilization rate."""
        return self._tracker.get_utilization_rate()

    def get_fact_stats(self, fact_id: str) -> Optional[dict]:
        """Get detailed stats for a fact."""
        return self._tracker.get_stats(fact_id)

    def get_summary(self) -> dict:
        """
        Get overall usage summary.

        Returns:
            dict with:
            - total_tracked_facts
            - used_in_output_count
            - never_used_count
            - utilization_rate
            - ignored_count (retrieved >10x but never used)
            """
        tracking = self._tracker._tracking

        total = len(tracking)
        used = sum(1 for s in tracking.values() if s["used_in_output"])
        never_used = total - used
        ignored = len(self._tracker.get_ignored_facts())

        return {
            "total_tracked_facts": total,
            "used_in_output_count": used,
            "never_used_count": never_used,
            "utilization_rate": used / total if total > 0 else 0,
            "ignored_count": ignored,
            "generated_at": datetime.now().isoformat()
        }

    def get_high_value_facts(self, min_influence_count: int = 3) -> list[dict]:
        """
        Get facts that have influenced multiple decisions.

        Args:
            min_influence_count: minimum decision influence count

        Returns:
            list of fact stats dicts, sorted by influence count
        """
        results = []
        for fact_id, stats in self._tracker._tracking.items():
            if stats["decision_influenced_count"] >= min_influence_count:
                results.append({
                    "fact_id": fact_id,
                    "decision_influenced_count": stats["decision_influenced_count"],
                    "retrieve_count": stats["retrieve_count"],
                    "used_in_output": stats["used_in_output"]
                })

        results.sort(key=lambda x: x["decision_influenced_count"], reverse=True)
        return results

    def get_neglected_facts(self, days: int = DEFAULT_IGNORED_DAYS) -> list[dict]:
        """
        Get facts that haven't been used in a while.

        Args:
            days: number of days without usage to be "neglected"

        Returns:
            list of neglected fact stats
        """
        threshold = datetime.now() - timedelta(days=days)
        results = []

        for fact_id, stats in self._tracker._tracking.items():
            last_used = stats.get("last_used")
            if not last_used:
                continue

            try:
                last_used_dt = datetime.fromisoformat(last_used)
                if last_used_dt < threshold:
                    results.append({
                        "fact_id": fact_id,
                        "last_used": last_used,
                        "days_since_use": (datetime.now() - last_used_dt).days,
                        "retrieve_count": stats["retrieve_count"],
                        "used_in_output": stats["used_in_output"]
                    })
            except (ValueError, TypeError):
                continue

        results.sort(key=lambda x: x["days_since_use"], reverse=True)
        return results

    def get_alerts(self) -> list[dict]:
        """
        Generate usage alerts.

        Returns:
            list of alert dicts
        """
        alerts = []

        # Check for ignored facts
        ignored = self._tracker.get_ignored_facts(
            min_retrieves=DEFAULT_MIN_RETRIEVES,
            usage_threshold=DEFAULT_USAGE_THRESHOLD
        )
        for fact_id in ignored:
            stats = self._tracker.get_stats(fact_id)
            days_since = 0
            if stats and stats.get("last_retrieved"):
                try:
                    last = datetime.fromisoformat(stats["last_retrieved"])
                    days_since = (datetime.now() - last).days
                except (ValueError, TypeError):
                    days_since = 0

            if days_since > DEFAULT_IGNORED_DAYS:
                alerts.append({
                    "type": "ignored_long_term",
                    "severity": "warning",
                    "fact_id": fact_id,
                    "message": f"Fact {fact_id} retrieved {stats['retrieve_count']}x but never used (>30 days)",
                    "retrieve_count": stats["retrieve_count"] if stats else 0
                })

        # Check for zero-utilization
        summary = self.get_summary()
        if summary["total_tracked_facts"] > 0 and summary["utilization_rate"] < 0.1:
            alerts.append({
                "type": "low_utilization",
                "severity": "info",
                "message": f"Memory utilization rate is {summary['utilization_rate']:.1%} - agent may not be using memories",
                "utilization_rate": summary["utilization_rate"]
            })

        return alerts


def get_memory_utilization_rate() -> float:
    """Module-level convenience for utilization rate."""
    tracker = UsageTracker()
    return tracker.get_utilization_rate()