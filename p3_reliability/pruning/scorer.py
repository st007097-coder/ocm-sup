"""
Multi-factor Prune Scorer - computes deletion priority for facts.
Factors: access frequency, importance level, age.
"""

import math
from typing import Literal
from datetime import datetime, timedelta

# Importance weight mapping
IMPORTANCE_WEIGHTS = {
    "HIGH": 0.0,
    "MEDIUM": 0.3,
    "LOW": 0.6,
    "UNKNOWN": 0.5
}

# Scoring weights
ACCESS_WEIGHT = 0.4
IMPORTANCE_WEIGHT = 0.3
AGE_WEIGHT = 0.3

# Default threshold
DEFAULT_PRUNE_THRESHOLD = 0.7


class PruneScorer:
    """
    Computes prune score for a fact.

    Score range: 0.0 - 1.0
    Higher score = more urgent to prune

    Formula:
        prune_score = access_factor * 0.4 + importance_factor * 0.3 + age_factor * 0.3
    """

    def __init__(self, threshold: float = DEFAULT_PRUNE_THRESHOLD):
        self.threshold = threshold

    def compute(self, fact: dict) -> float:
        """
        Compute prune score for a fact.

        Args:
            fact: dict with keys:
                - access_count: int (number of times retrieved)
                - importance: str (HIGH/MEDIUM/LOW/UNKNOWN)
                - created_at: str (ISO datetime)
                - last_accessed: str (ISO datetime, optional)
                - used_in_output: bool (optional)
                - decision_influenced_count: int (optional)

        Returns:
            float prune score (0.0 - 1.0)
        """
        access_count = fact.get("access_count", 0)
        importance = fact.get("importance", "UNKNOWN")
        created_at = fact.get("created_at", datetime.now().isoformat())

        # Access factor: low access = high prune score
        # Use sqrt to dampen the effect of very high access counts
        access_factor = 1 / math.sqrt(access_count + 1)

        # Importance factor: low importance = high prune score
        importance_factor = IMPORTANCE_WEIGHTS.get(importance, 0.5)

        # Age factor: older = higher score (logarithmic)
        try:
            created = datetime.fromisoformat(created_at)
            age_days = (datetime.now() - created).days
        except (ValueError, TypeError):
            age_days = 0

        age_factor = min(math.log(age_days + 1) / 10, 1.0)

        # Weighted sum
        score = (
            access_factor * ACCESS_WEIGHT +
            importance_factor * IMPORTANCE_WEIGHT +
            age_factor * AGE_WEIGHT
        )

        return round(score, 4)

    def should_prune(self, fact: dict) -> bool:
        """Returns True if fact should be pruned."""
        return self.compute(fact) > self.threshold

    def rank(self, facts: list[dict]) -> list[tuple[dict, float]]:
        """
        Rank facts by prune score (highest first).

        Returns:
            list of (fact, score) tuples
        """
        scored = [(f, self.compute(f)) for f in facts]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored


# Module-level convenience functions
def compute_prune_score(fact: dict) -> float:
    """Compute prune score for a fact."""
    scorer = PruneScorer()
    return scorer.compute(fact)


def should_prune(fact: dict) -> bool:
    """Returns True if fact should be pruned."""
    scorer = PruneScorer()
    return scorer.should_prune(fact)