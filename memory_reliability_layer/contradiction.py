"""
Contradiction Detection Engine
OCM Sup v2.6

Semantic contradiction detection using sentence transformers.
Based on user's sentence transformer approach.

Usage:
    engine = ContradictionEngine()
    result = engine.check_fact(fact_id, fact_text, all_facts)
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from sentence_transformers import SentenceTransformer, util
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

from . import config


class ContradictionResult:
    """Result of contradiction check."""
    
    def __init__(self, found: bool = False, contradicting_facts: list = None, 
                 similarity: float = 0.0, method: str = "none"):
        self.found = found
        self.contradicting_facts = contradicting_facts or []
        self.similarity = similarity
        self.method = method
    
    def to_dict(self) -> dict:
        return {
            "found": self.found,
            "contradicting_facts": self.contradicting_facts,
            "similarity": self.similarity,
            "method": self.method
        }


class ContradictionEngine:
    """
    Detects semantic contradictions between memory facts.
    
    Uses two methods:
    1. Sentence transformer similarity (primary)
    2. Negation pattern matching (supplementary)
    """
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or config.CONTRADICTION_MODEL
        self.threshold = config.SIMILARITY_THRESHOLD
        self._model = None
        self._negation_words = {"not", "never", "no", "dont", "don't", "without", "none", "nothing"}
    
    @property
    def model(self):
        """Lazy load the model."""
        if self._model is None and HAS_SENTENCE_TRANSFORMERS:
            self._model = SentenceTransformer(self.model_name)
        return self._model
    
    def check_fact(self, fact_id: str, fact_text: str, all_facts: Dict[str, dict]) -> ContradictionResult:
        """
        Check if a fact contradicts any existing facts.
        
        Args:
            fact_id: ID of the new fact
            fact_text: Text content of the new fact
            all_facts: Dict of {fact_id: fact_data} for existing facts
            
        Returns:
            ContradictionResult with found status and details
        """
        if not self.model:
            return ContradictionResult(method="no_model")
        
        # Encode the new fact
        new_embedding = self.model.encode(fact_text)
        
        contradicting = []
        max_similarity = 0.0
        
        for other_id, other_data in all_facts.items():
            if other_id == fact_id:
                continue
            
            other_text = f"{other_data.get('subject', '')} {other_data.get('action', '')}"
            
            # Check similarity
            other_embedding = self.model.encode(other_text)
            sim = util.cos_sim(new_embedding, other_embedding).item()
            
            if sim > self.threshold:
                # Check if they actually contradict using negation patterns
                if self._simple_contradiction(fact_text, other_text):
                    contradicting.append({
                        "fact_id": other_id,
                        "similarity": sim,
                        "reason": "semantic_similarity_with_negation"
                    })
                    max_similarity = max(max_similarity, sim)
        
        return ContradictionResult(
            found=len(contradicting) > 0,
            contradicting_facts=contradicting,
            similarity=max_similarity,
            method="sentence_transformer"
        )
    
    def _simple_contradiction(self, text_a: str, text_b: str) -> bool:
        """
        Simple heuristic for contradiction detection.
        Based on negation word presence difference.
        
        Returns True if one text has negation and the other doesn't.
        """
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())
        
        has_neg_a = bool(words_a & self._negation_words)
        has_neg_b = bool(words_b & self._negation_words)
        
        # One has negation, the other doesn't = potential contradiction
        return has_neg_a != has_neg_b
    
    def detect_candidates(self, facts: List[dict]) -> List[Tuple[dict, dict, float]]:
        """
        Find all pairs of facts that might contradict each other.
        
        Returns list of (fact_a, fact_b, similarity) tuples.
        """
        if not self.model or len(facts) < 2:
            return []
        
        # Encode all fact texts
        texts = [f"{f.get('subject', '')} {f.get('action', '')}" for f in facts]
        embeddings = self.model.encode(texts)
        
        candidates = []
        
        for i in range(len(facts)):
            for j in range(i + 1, len(facts)):
                sim = util.cos_sim(embeddings[i], embeddings[j]).item()
                
                if sim > self.threshold:
                    candidates.append((facts[i], facts[j], sim))
        
        return candidates
    
    def run_full_scan(self, output_path: Path = None) -> List[dict]:
        """
        Run full contradiction scan on all stored facts.
        
        Args:
            output_path: Optional path to save results
            
        Returns:
            List of contradiction results
        """
        if output_path is None:
            output_path = config.BASE_DIR / "contradictions.jsonl"
        
        # Load all facts from structured storage
        facts = []
        for fpath in config.STORAGE_DIR.glob("*.json"):
            with open(fpath) as f:
                facts.append(json.load(f))
        
        results = []
        
        for fact in facts:
            fact_id = fact.get("entity_id", fpath.stem)
            fact_text = f"{fact.get('subject', '')} {fact.get('action', '')}"
            
            # Build all_facts dict
            all_facts = {}
            for other in facts:
                other_id = other.get("entity_id", "")
                if other_id != fact_id:
                    all_facts[other_id] = other
            
            result = self.check_fact(fact_id, fact_text, all_facts)
            
            if result.found:
                results.append({
                    "fact_id": fact_id,
                    "text": fact_text,
                    "contradictions": result.contradicting_facts,
                    "max_similarity": result.similarity
                })
        
        # Save results
        config.BASE_DIR.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        
        return results
