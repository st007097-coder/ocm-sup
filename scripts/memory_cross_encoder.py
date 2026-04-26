#!/usr/bin/env python3
"""
Memory Cross-Encoder Reranker
OCM Sup v2.4 - P2-1

Cross-encoder reranking for memory retrieval.
Uses simple sentence similarity as lightweight cross-encoder proxy.

Score = cross_encoder(query, memory) * 0.5 + original_rrf * 0.5

Usage:
    python3 memory_cross_encoder.py --query <query> --memories <json_file> [--top-k N]
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Tuple


class SimpleCrossEncoder:
    """
    Lightweight cross-encoder using sentence-level attention simulation.
    
    Since we can't use full cross-encoder model without GPU,
    we simulate attention with deep similarity matching.
    
    Score = weighted token overlap + position sensitivity + length normalization
    """
    
    def __init__(self):
        self.stopwords = set([
            "的", "係", "係", "咗", "緊", "喇", "呀", "啦", "喺", "個", "係",
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "and", "or", "but", "if", "then", "else", "when", "at", "to", "for",
            "of", "in", "on", "with", "as", "by", "from", "this", "that", "these",
        ])
    
    def score(self, query: str, memory_text: str) -> float:
        """
        Calculate cross-encoder style score.
        
        Combines:
        - Exact token matching (attention simulation)
        - N-gram overlap (context awareness)
        - Length normalization
        """
        query_tokens = self._tokenize(query)
        memory_tokens = self._tokenize(memory_text)
        
        if not query_tokens or not memory_tokens:
            return 0.0
        
        # 1. Exact token overlap (simulate attention)
        exact_overlap = len(set(query_tokens) & set(memory_tokens))
        
        # 2. N-gram overlap (2-grams, simulate context)
        query_bigrams = set(self._ngrams(query_tokens, 2))
        memory_bigrams = set(self._ngrams(memory_tokens, 2))
        bigram_overlap = len(query_bigrams & memory_bigrams) / max(len(query_bigrams), 1)
        
        # 3. Length normalization (penalize very long texts)
        len_penalty = 1.0 / (1 + 0.02 * abs(len(memory_tokens) - len(query_tokens)))
        
        # Combined score
        score = (exact_overlap * 0.4 + bigram_overlap * 0.4 + len_penalty * 0.2)
        
        # Normalize to 0-1 range
        max_possible = min(len(query_tokens), len(memory_tokens))
        if max_possible > 0:
            normalized = score / max_possible
        else:
            normalized = 0.0
        
        return min(1.0, normalized)
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        tokens = []
        for word in text.lower().replace("/", " ").replace("-", " ").split():
            word = word.strip(".,:;()[]{}'\"")
            if word and word not in self.stopwords and len(word) > 1:
                tokens.append(word)
        return tokens
    
    def _ngrams(self, tokens: List[str], n: int) -> List[str]:
        """Generate n-grams from tokens."""
        return [" ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]


class MemoryCrossEncoderReranker:
    """
    Reranks memories using cross-encoder scores combined with original scores.
    """
    
    def __init__(
        self,
        cross_weight: float = 0.5,
        rrf_weight: float = 0.5,
    ):
        self.encoder = SimpleCrossEncoder()
        self.cross_weight = cross_weight
        self.rrf_weight = rrf_weight
    
    def rerank(
        self,
        query: str,
        memories: List[Dict],
        top_k: int = 5,
        use_rrf: bool = True,
    ) -> List[Dict]:
        """
        Rerank memories by combining cross-encoder with original scores.
        
        Args:
            query: Search query
            memories: List of memory dicts
            top_k: Number of results to return
            use_rrf: If True, combine with existing RRF scores
        """
        scored_memories = []
        
        for mem in memories:
            # Get memory text
            mem_text = f"{mem.get('subject', '')} {mem.get('action', '')}"
            
            # Calculate cross-encoder score
            cross_score = self.encoder.score(query, mem_text)
            
            # Get original RRF score if available
            original_rrf = mem.get("rrf_score", mem.get("score", 0.5))
            
            # Combined score
            if use_rrf and original_rrf > 0:
                combined = cross_score * self.cross_weight + original_rrf * self.rrf_weight
            else:
                combined = cross_score
            
            scored_memories.append({
                "memory": mem,
                "cross_score": round(cross_score, 3),
                "original_rrf": round(original_rrf, 3),
                "combined_score": round(combined, 3),
                "reranked": True,
            })
        
        # Sort by combined score
        scored_memories.sort(key=lambda x: x["combined_score"], reverse=True)
        
        return scored_memories[:top_k]
    
    def explain(self, query: str, memory: Dict) -> Dict:
        """Explain reranking decision for a memory."""
        mem_text = f"{memory.get('subject', '')} {memory.get('action', '')}"
        cross_score = self.encoder.score(query, mem_text)
        
        tokens = self.encoder._tokenize(query)
        mem_tokens = self.encoder._tokenize(mem_text)
        
        return {
            "query": query,
            "subject": memory.get("subject", ""),
            "cross_score": round(cross_score, 3),
            "matching_tokens": list(set(tokens) & set(mem_tokens)),
            "query_tokens": tokens[:10],
        }


def main():
    parser = argparse.ArgumentParser(description="Memory Cross-Encoder Reranker")
    parser.add_argument("--query", required=True, help="Query string")
    parser.add_argument("--memories", help="JSON file with memories")
    parser.add_argument("--top-k", type=int, default=5, help="Max results")
    parser.add_argument("--explain", action="store_true", help="Show explanations")
    parser.add_argument("--stdin", action="store_true", help="Read from stdin")
    
    args = parser.parse_args()
    
    # Load memories
    if args.stdin:
        memories = json.load(sys.stdin)
    elif args.memories:
        with open(args.memories) as f:
            memories = json.load(f)
    else:
        # Load from structured dir
        struct_dir = Path("/root/.openclaw/workspace/memory/structured")
        memories = []
        if struct_dir.exists():
            for f in struct_dir.glob("*.json"):
                with open(f) as fh:
                    memories.append(json.load(fh))
    
    if not memories:
        print("No memories to rerank")
        return
    
    # Rerank
    reranker = MemoryCrossEncoderReranker()
    results = reranker.rerank(args.query, memories, top_k=args.top_k)
    
    print(f"🔄 Cross-Encoder Reranking for: {args.query}")
    print(f"📊 Results: {len(results)}")
    print()
    
    for i, r in enumerate(results, 1):
        mem = r["memory"]
        print(f"{i}. [{r['combined_score']:.3f}] {mem.get('subject', '?')}")
        print(f"   cross={r['cross_score']} original={r['original_rrf']}")
        
        if args.explain:
            exp = reranker.explain(args.query, mem)
            print(f"   matched: {exp['matching_tokens']}")
        
        print(f"   type: {mem.get('type', '?')} | conf: {mem.get('confidence', '?')}")
        print(f"   action: {mem.get('action', '')[:60]}...")
        print()


if __name__ == "__main__":
    main()