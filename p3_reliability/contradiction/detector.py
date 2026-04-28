"""
Contradiction Detector - Core detection engine for semantic contradictions.
Combines embedding similarity, sentiment heuristic, and LLM judgment.
"""

import os
import json
import numpy as np
from typing import Optional, Literal
from datetime import datetime
from pathlib import Path

from .embedding_store import EmbeddingStore
from .sentiment import get_sentiment_sign, is_opposite_sign
from .llm_judge import LLMJudge

# Config
DEFAULT_SIMILARITY_THRESHOLD = 0.85
DEFAULT_CONFIDENCE_THRESHOLD = 0.7
STATE_DIR = Path("~/.openclaw/ocm-sup").expanduser()
STATE_DIR.mkdir(parents=True, exist_ok=True)


class ContradictionResult:
    """Result of a contradiction check."""

    def __init__(
        self,
        fact_a_id: str,
        fact_b_id: str,
        fact_a_text: str,
        fact_b_text: str,
        similarity: float,
        sentiment_opposite: bool,
        llm_contradiction: bool,
        llm_confidence: float,
        llm_explanation: str,
        resolved: bool = False,
        resolution: str = "",
        created_at: str = None
    ):
        self.fact_a_id = fact_a_id
        self.fact_b_id = fact_b_id
        self.fact_a_text = fact_a_text
        self.fact_b_text = fact_b_text
        self.similarity = similarity
        self.sentiment_opposite = sentiment_opposite
        self.llm_contradiction = llm_contradiction
        self.llm_confidence = llm_confidence
        self.llm_explanation = llm_explanation
        self.resolved = resolved
        self.resolution = resolution
        self.created_at = created_at or datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "fact_a_id": self.fact_a_id,
            "fact_b_id": self.fact_b_id,
            "fact_a_text": self.fact_a_text,
            "fact_b_text": self.fact_b_text,
            "similarity": self.similarity,
            "sentiment_opposite": self.sentiment_opposite,
            "llm_contradiction": self.llm_contradiction,
            "llm_confidence": self.llm_confidence,
            "llm_explanation": self.llm_explanation,
            "resolved": self.resolved,
            "resolution": self.resolution,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ContradictionResult":
        return cls(**d)


class ContradictionDetector:
    """
    Detects semantic contradictions between facts.

    Detection pipeline:
    1. Embed new fact → get embedding
    2. Compare with all existing embeddings (cosine similarity)
    3. If similarity > threshold AND sentiment opposite → flag for LLM
    4. LLM judges if actual contradiction exists
    5. Store result if contradiction found
    """

    def __init__(
        self,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        embedding_store: EmbeddingStore = None,
        llm_judge: LLMJudge = None
    ):
        self.similarity_threshold = similarity_threshold
        self.confidence_threshold = confidence_threshold
        self.embedding_store = embedding_store or EmbeddingStore()
        self.llm_judge = llm_judge or LLMJudge()

        # Load existing contradictions
        self._state_file = STATE_DIR / "contradictions.json"
        self._contradictions: list[ContradictionResult] = self._load_state()

    def _load_state(self) -> list[ContradictionResult]:
        """Load saved contradictions from disk."""
        if self._state_file.exists():
            with open(self._state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [ContradictionResult.from_dict(d) for d in data]
        return []

    def _save_state(self):
        """Save contradictions to disk."""
        with open(self._state_file, "w", encoding="utf-8") as f:
            json.dump([c.to_dict() for c in self._contradictions], f, ensure_ascii=False, indent=2)

    def _cosine_similarity(self, emb_a: np.ndarray, emb_b: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings."""
        dot = np.dot(emb_a, emb_b)
        norm_a = np.linalg.norm(emb_a)
        norm_b = np.linalg.norm(emb_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    def store_embedding(self, fact_id: str, embedding: list[float], metadata: dict = None):
        """Store embedding for a fact (call after fact creation)."""
        self.embedding_store.store(fact_id, embedding, metadata)

    def check_fact(self, new_fact_id: str, new_fact_text: str, all_facts: dict[str, str]) -> list[ContradictionResult]:
        """
        Check a new or existing fact against all other facts for contradictions.

        Args:
            new_fact_id: ID of the fact to check
            new_fact_text: Text content of the fact
            all_facts: dict of {fact_id: fact_text} for all existing facts

        Returns:
            list of ContradictionResult for found contradictions
        """
        new_emb = self.embedding_store.get(new_fact_id)
        if new_emb is None:
            # Cannot check without embedding - need to embed first
            return []

        new_sign = get_sentiment_sign(new_fact_text)
        results = []

        for other_id, other_text in all_facts.items():
            if other_id == new_fact_id:
                continue

            other_emb = self.embedding_store.get(other_id)
            if other_emb is None:
                continue

            # Compute similarity
            sim = self._cosine_similarity(new_emb, other_emb)

            # Fast pre-filter: skip if below threshold
            if sim < self.similarity_threshold:
                continue

            # Check sentiment
            other_sign = get_sentiment_sign(other_text)
            opposite = is_opposite_sign(new_sign, other_sign)

            # If similar AND opposite sentiment → LLM judgment
            if opposite or sim > 0.95:  # Very high similarity triggers LLM regardless
                llm_result = self.llm_judge.judge(new_fact_text, other_text)

                if llm_result["contradiction"]:
                    result = ContradictionResult(
                        fact_a_id=new_fact_id,
                        fact_b_id=other_id,
                        fact_a_text=new_fact_text,
                        fact_b_text=other_text,
                        similarity=sim,
                        sentiment_opposite=opposite,
                        llm_contradiction=True,
                        llm_confidence=llm_result["confidence"],
                        llm_explanation=llm_result["explanation"]
                    )
                    results.append(result)

        return results

    def add_contradiction(self, result: ContradictionResult):
        """Manually add a contradiction result."""
        # Check if already exists
        for existing in self._contradictions:
            if (existing.fact_a_id == result.fact_a_id and existing.fact_b_id == result.fact_b_id) or \
               (existing.fact_a_id == result.fact_b_id and existing.fact_b_id == result.fact_a_id):
                # Update existing
                existing.llm_contradiction = result.llm_contradiction
                existing.llm_confidence = result.llm_confidence
                existing.llm_explanation = result.llm_explanation
                return
        self._contradictions.append(result)
        self._save_state()

    def resolve(self, fact_a_id: str, fact_b_id: str, decision: str):
        """
        Resolve a contradiction.

        Args:
            fact_a_id, fact_b_id: IDs of conflicting facts
            decision: resolution (e.g., "keep_a", "keep_b", "merge", "ignore")
        """
        for c in self._contradictions:
            if (c.fact_a_id == fact_a_id and c.fact_b_id == fact_b_id) or \
               (c.fact_a_id == fact_b_id and c.fact_b_id == fact_a_id):
                c.resolved = True
                c.resolution = decision
                self._save_state()
                return

    def get_unresolved(self) -> list[ContradictionResult]:
        """Return all unresolved contradictions."""
        return [c for c in self._contradictions if not c.resolved]

    def get_report(self) -> dict:
        """Generate contradiction report."""
        total = len(self._contradictions)
        resolved = sum(1 for c in self._contradictions if c.resolved)
        return {
            "total_contradictions": total,
            "resolved": resolved,
            "unresolved": total - resolved,
            "resolution_rate": resolved / total if total > 0 else 0,
            "high_confidence_count": sum(1 for c in self._contradictions if c.llm_confidence > 0.8)
        }

    def calibrate_threshold(self, sample_pairs: list[tuple[str, str]], known_contradictions: list[bool]) -> float:
        """
        Calibrate similarity threshold based on labeled samples.

        Args:
            sample_pairs: list of (fact_a_text, fact_b_text) pairs
            known_contradictions: list of bool (True = is contradiction)

        Returns:
            calibrated threshold
        """
        # Placeholder - in production, compute precision/recall curve
        return self.similarity_threshold