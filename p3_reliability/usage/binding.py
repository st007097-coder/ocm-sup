"""
Pattern Binding - binds context patterns to memory facts.
Enables "when X context recurs, boost relevant facts" behavior.
"""

import json
from typing import Optional
from datetime import datetime
from pathlib import Path

STATE_DIR = Path("~/.openclaw/ocm-sup").expanduser()
STATE_DIR.mkdir(parents=True, exist_ok=True)


class PatternBinding:
    """
    Binds context patterns to facts for predictive boosting.

    When the agent encounters a similar context again,
    facts that were used in that context before are boosted.

    Example:
        Context: "user debugging system"
        Facts used: ["fact_123", "fact_456"]

        Next time "debugging" or "system" appears,
        fact_123 and fact_456 get boost signal.
    """

    def __init__(self, similarity_threshold: float = 0.8):
        self.similarity_threshold = similarity_threshold
        self._state_file = STATE_DIR / "pattern_bindings.json"
        self._patterns: list[dict] = self._load()

    def _load(self) -> list[dict]:
        """Load pattern bindings from disk."""
        if self._state_file.exists():
            with open(self._state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save(self):
        """Save pattern bindings to disk."""
        with open(self._state_file, "w", encoding="utf-8") as f:
            json.dump(self._patterns, f, ensure_ascii=False, indent=2)

    def add_binding(self, pattern: str, facts_used: list[str], context_hash: str = ""):
        """
        Add a pattern → facts binding.

        Args:
            pattern: context pattern text (e.g., "debugging system")
            facts_used: list of fact IDs used in this context
            context_hash: optional hash for exact match
        """
        # Check if pattern already exists
        for existing in self._patterns:
            if existing["pattern"] == pattern:
                # Update facts used
                for fid in facts_used:
                    if fid not in existing["fact_ids"]:
                        existing["fact_ids"].append(fid)
                existing["hit_count"] += 1
                existing["last_hit"] = datetime.now().isoformat()
                self._save()
                return

        # New pattern
        self._patterns.append({
            "pattern": pattern,
            "fact_ids": list(facts_used),
            "hit_count": 1,
            "created_at": datetime.now().isoformat(),
            "last_hit": datetime.now().isoformat(),
            "context_hash": context_hash
        })
        self._save()

    def _word_similarity(self, word1: str, word2: str) -> bool:
        """
        Check if two words are similar enough to count as match.
        Handles: exact match, substring, stem similarity.
        """
        w1 = word1.lower()
        w2 = word2.lower()
        # Exact match
        if w1 == w2:
            return True
        # Substring match (e.g., "debugging" contains "debug")
        if len(w1) >= 3 and len(w2) >= 3:
            if w1 in w2 or w2 in w1:
                return True
        return False

    def get_facts_for_context(self, context: str) -> list[str]:
        """
        Get facts that should be boosted for a context.

        Args:
            context: current context text

        Returns:
            list of fact IDs to boost (from patterns that match current context)
        """
        matching_facts = set()

        context_lower = context.lower()
        context_words = set(context_lower.split())

        for p in self._patterns:
            pattern_words = set(p["pattern"].lower().split())

            # Count how many pattern words have a similar word in context
            matched_pattern_words = 0
            for pw in pattern_words:
                for cw in context_words:
                    if self._word_similarity(cw, pw):
                        matched_pattern_words += 1
                        break  # One context word per pattern word is enough

            # If significant portion of pattern words matched, it's a match
            if matched_pattern_words >= min(len(pattern_words), 2):
                for fid in p["fact_ids"]:
                    matching_facts.add(fid)

        return list(matching_facts)

    def suggest_boost(self, fact_id: str, current_context: str) -> bool:
        """
        Check if a specific fact should be boosted for current context.

        Args:
            fact_id: ID of fact to check
            current_context: current context text

        Returns:
            True if fact should be boosted
        """
        facts = self.get_facts_for_context(current_context)
        return fact_id in facts

    def get_top_patterns(self, limit: int = 10) -> list[dict]:
        """
        Get most frequently matched patterns.

        Returns:
            list of pattern dicts sorted by hit_count
        """
        sorted_patterns = sorted(self._patterns, key=lambda x: x["hit_count"], reverse=True)
        return sorted_patterns[:limit]

    def get_pattern_for_fact(self, fact_id: str) -> list[dict]:
        """
        Get all patterns that include a specific fact.

        Args:
            fact_id: ID of fact

        Returns:
            list of pattern dicts
        """
        return [p for p in self._patterns if fact_id in p["fact_ids"]]

    def remove_pattern(self, pattern: str) -> bool:
        """Remove a pattern binding."""
        original_len = len(self._patterns)
        self._patterns = [p for p in self._patterns if p["pattern"] != pattern]
        if len(self._patterns) < original_len:
            self._save()
            return True
        return False

    def clear_all(self):
        """Clear all pattern bindings."""
        self._patterns = []
        self._save()

    def get_stats(self) -> dict:
        """Get pattern binding statistics."""
        return {
            "total_patterns": len(self._patterns),
            "total_bindings": sum(len(p["fact_ids"]) for p in self._patterns),
            "most_hit": max((p["hit_count"] for p in self._patterns), default=0),
            "avg_hits": (
                sum(p["hit_count"] for p in self._patterns) / len(self._patterns)
                if self._patterns else 0
            )
        }


# Module-level convenience
_binding = None

def _get_binding() -> PatternBinding:
    global _binding
    if _binding is None:
        _binding = PatternBinding()
    return _binding


def suggest_boost(fact_id: str, current_context: str) -> bool:
    """Check if fact should be boosted for current context."""
    return _get_binding().suggest_boost(fact_id, current_context)