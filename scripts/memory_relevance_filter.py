#!/usr/bin/env python3
"""
Memory Relevance Filter
OCM Sup v2.4 - P1-2

Filters retrieved memories by relevance threshold.
Prevents irrelevant memories from polluting context.

Score = semantic_similarity * 0.6 + recency * 0.2 + importance * 0.2

Usage:
    python3 memory_relevance_filter.py --query <query> --memories <json_file> [--top-k N] [--threshold 0.3]
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta


class MemoryRelevanceFilter:
    """
    Filter memories by relevance score.
    
    Scoring:
    - semantic_similarity: 60% (query vs memory content)
    - recency: 20% (time decay)
    - importance: 20% (confidence as proxy)
    
    Threshold: memories below threshold are excluded.
    """
    
    def __init__(
        self,
        threshold: float = 0.3,
        recency_weight: float = 0.2,
        importance_weight: float = 0.2,
        similarity_weight: float = 0.6,
        half_life_days: int = 30,
    ):
        self.threshold = threshold
        self.recency_weight = recency_weight
        self.importance_weight = importance_weight
        self.similarity_weight = similarity_weight
        self.half_life_days = half_life_days
    
    def score(self, memory: dict, query: str) -> float:
        """
        Calculate relevance score for a memory.
        
        Returns score 0.0-1.0
        """
        # 1. Semantic similarity (simple word overlap for now)
        similarity = self._calc_similarity(
            memory.get("subject", "") + " " + memory.get("action", ""),
            query
        )
        
        # 2. Recency score (time decay)
        recency = self._calc_recency(memory)
        
        # 3. Importance score (confidence as proxy)
        importance = memory.get("confidence", 0.5)
        
        # Weighted sum
        score = (
            similarity * self.similarity_weight +
            recency * self.recency_weight +
            importance * self.importance_weight
        )
        
        return round(score, 3)
    
    def _calc_similarity(self, text: str, query: str) -> float:
        """Simple word overlap similarity."""
        text_words = set(text.lower().split())
        query_words = set(query.lower().split())
        
        if not text_words or not query_words:
            return 0.0
        
        overlap = len(text_words & query_words)
        union = len(text_words | query_words)
        
        return overlap / union if union > 0 else 0.0
    
    def _calc_recency(self, memory: dict) -> float:
        """Calculate recency score with time decay."""
        created = memory.get("created_at") or memory.get("timestamp")
        
        if not created:
            return 0.5  # Default if no timestamp
        
        try:
            if isinstance(created, str):
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            else:
                created_dt = created
            
            now = datetime.now(timezone.utc)
            age_days = (now - created_dt).total_seconds() / 86400
            
            # Half-life decay
            decay = 0.5 ** (age_days / self.half_life_days)
            return decay
        except:
            return 0.5
    
    def filter(self, memories: list, query: str, top_k: int = 5, threshold: float = None) -> list:
        """
        Filter and rank memories by relevance.
        
        Returns top_k memories above threshold.
        """
        if threshold is None:
            threshold = self.threshold
        
        # Score all memories
        scored = []
        for mem in memories:
            score = self.score(mem, query)
            if score >= threshold:
                scored.append((score, mem))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Return top_k
        return [
            {"memory": mem, "score": score, "filtered": True}
            for score, mem in scored[:top_k]
        ]
    
    def explain_score(self, memory: dict, query: str) -> dict:
        """Explain why a memory got its score."""
        similarity = self._calc_similarity(
            memory.get("subject", "") + " " + memory.get("action", ""),
            query
        )
        recency = self._calc_recency(memory)
        importance = memory.get("confidence", 0.5)
        total = self.score(memory, query)
        
        return {
            "id": memory.get("id", "unknown"),
            "subject": memory.get("subject", ""),
            "total_score": total,
            "breakdown": {
                "semantic_similarity": round(similarity, 3),
                "recency": round(recency, 3),
                "importance": round(importance, 3),
            },
            "weights": {
                "similarity": self.similarity_weight,
                "recency": self.recency_weight,
                "importance": self.importance_weight,
            },
            "passed_threshold": total >= self.threshold,
        }


def load_memories_from_file(filepath: str) -> list:
    """Load memories from JSON file."""
    with open(filepath) as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return data.get("memories", [])


def main():
    parser = argparse.ArgumentParser(description="Memory Relevance Filter")
    parser.add_argument("--query", required=True, help="Query to score against")
    parser.add_argument("--memories", help="JSON file with memories (or use --stdin)")
    parser.add_argument("--top-k", type=int, default=5, help="Max memories to return")
    parser.add_argument("--threshold", type=float, default=0.3, help="Minimum score threshold")
    parser.add_argument("--explain", action="store_true", help="Show score breakdown")
    parser.add_argument("--stdin", action="store_true", help="Read memories from stdin")
    
    args = parser.parse_args()
    
    # Load memories
    if args.stdin:
        memories = json.load(sys.stdin)
    elif args.memories:
        memories = load_memories_from_file(args.memories)
    else:
        # Try loading from structured dir
        struct_dir = Path("/home/jacky/.openclaw/workspace/memory/structured")
        memories = []
        if struct_dir.exists():
            for f in struct_dir.glob("*.json"):
                with open(f) as fh:
                    memories.append(json.load(fh))
    
    if not memories:
        print("No memories to filter")
        sys.exit(0)
    
    # Create filter
    filter_obj = MemoryRelevanceFilter(threshold=args.threshold)
    
    # Filter
    results = filter_obj.filter(memories, args.query, top_k=args.top_k, threshold=args.threshold)
    
    # Output
    print(f"🔍 Query: {args.query}")
    print(f"📊 Found {len(results)} relevant memories (threshold: {args.threshold})")
    print()
    
    for i, r in enumerate(results, 1):
        mem = r["memory"]
        print(f"{i}. [{r['score']:.3f}] {mem.get('subject', 'unknown')}")
        print(f"   type: {mem.get('type', '?')} | conf: {mem.get('confidence', '?')}")
        
        if args.explain:
            exp = filter_obj.explain_score(mem, args.query)
            b = exp["breakdown"]
            print(f"   breakdown: sim={b['semantic_similarity']} rec={b['recency']} imp={b['importance']}")
        
        action = mem.get("action", "")[:80]
        print(f"   action: {action}...")
        print()


if __name__ == "__main__":
    main()