#!/usr/bin/env python3
"""
Memory Retriever with Usage Tracking
OCM Sup v2.4 - P4 Phase 2

Provides unified memory fact retrieval with automatic usage tracking.
Integrates P3 UsageTracker to monitor retrieval and usage patterns.

Usage:
    python3 memory_retriever.py --query "古洞站" --top-k 5
    python3 memory_retriever.py --stats
    python3 memory_retriever.py --ignored  # show ignored facts
"""

import os
import sys
import json
import argparse
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple

# P3 components
sys.path.insert(0, str(Path(__file__).parent.parent))
from p3_reliability.usage import UsageTracker

# Storage paths (P3 standard)
OCM_SUP_BASE = Path("~/.openclaw/ocm-sup").expanduser()
STRUCTURED_DIR = OCM_SUP_BASE / "structured"
GRAPH_DIR = OCM_SUP_BASE / "graph"

# Ensure directories exist
STRUCTURED_DIR.mkdir(parents=True, exist_ok=True)


class MemoryRetriever:
    """
    Memory fact retriever with automatic usage tracking.
    
    Tracks:
    - on_retrieve: when facts are accessed
    - on_output: when facts appear in agent output
    - on_agent_decision: when agent decisions are influenced by facts
    """
    
    def __init__(self):
        self._usage_tracker = UsageTracker()
        self._all_facts_cache = self._load_all_facts()
    
    def _id(self, memory: Dict) -> str:
        """Generate deterministic ID for a memory."""
        content = f"{memory.get('type')}:{memory.get('subject')}:{memory.get('action')}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _load_all_facts(self) -> Dict[str, dict]:
        """Load all facts from P3 structured storage."""
        facts = {}
        if STRUCTURED_DIR.exists():
            for f in STRUCTURED_DIR.glob("*.json"):
                try:
                    with open(f) as fp:
                        data = json.load(fp)
                        fact_id = data.get("entity_id", f.stem)
                        facts[fact_id] = data
                except:
                    pass
        return facts
    
    def retrieve(
        self,
        query: str = None,
        fact_ids: List[str] = None,
        top_k: int = 10,
        context: str = ""
    ) -> List[Dict]:
        """
        Retrieve facts with automatic usage tracking.
        
        Args:
            query: text query to search for (simple substring match)
            fact_ids: specific fact IDs to retrieve (alternative to query)
            top_k: maximum number of facts to return
            context: current context for usage tracking
            
        Returns:
            list of fact dictionaries with usage stats
        """
        results = []
        
        if fact_ids:
            # Retrieve specific facts by ID
            for fact_id in fact_ids[:top_k]:
                if fact_id in self._all_facts_cache:
                    fact_data = self._all_facts_cache[fact_id]
                    
                    # Track retrieval
                    self._usage_tracker.on_retrieve(fact_id, context)
                    
                    # Add usage stats to result
                    stats = self._usage_tracker.get_stats(fact_id)
                    results.append({
                        **fact_data,
                        "usage_stats": stats or {}
                    })
        elif query:
            # Text search (simple substring match on subject + action)
            query_lower = query.lower()
            scored = []
            
            for fact_id, fact_data in self._all_facts_cache.items():
                subject = fact_data.get("subject", "").lower()
                action = fact_data.get("action", "").lower()
                
                # Simple scoring: count query term matches
                score = 0
                for term in query_lower.split():
                    if term in subject:
                        score += 2  # Subject match weights more
                    if term in action:
                        score += 1
                
                if score > 0:
                    scored.append((score, fact_id, fact_data))
            
            # Sort by score descending
            scored.sort(key=lambda x: x[0], reverse=True)
            
            for score, fact_id, fact_data in scored[:top_k]:
                # Track retrieval
                self._usage_tracker.on_retrieve(fact_id, context)
                
                # Add usage stats
                stats = self._usage_tracker.get_stats(fact_id)
                results.append({
                    **fact_data,
                    "_match_score": score,
                    "usage_stats": stats or {}
                })
        else:
            # Return recent facts (no query)
            recent = sorted(
                self._all_facts_cache.items(),
                key=lambda x: x[1].get("created_at", ""),
                reverse=True
            )[:top_k]
            
            for fact_id, fact_data in recent:
                self._usage_tracker.on_retrieve(fact_id, context)
                stats = self._usage_tracker.get_stats(fact_id)
                results.append({
                    **fact_data,
                    "usage_stats": stats or {}
                })
        
        return results
    
    def mark_used(self, fact_ids: List[str]):
        """
        Mark facts as used in output (call when agent outputs response).
        
        Args:
            fact_ids: list of fact IDs that appeared in output
        """
        for fact_id in fact_ids:
            self._usage_tracker.on_output(fact_id)
    
    def mark_decision(self, context_pattern: str, fact_ids: List[str]):
        """
        Mark facts as influencing agent decision.
        
        Args:
            context_pattern: description of decision context
            fact_ids: list of fact IDs that influenced decision
        """
        self._usage_tracker.on_agent_decision(context_pattern, fact_ids)
    
    def get_stats(self, fact_id: str) -> Optional[dict]:
        """Get usage stats for a specific fact."""
        return self._usage_tracker.get_stats(fact_id)
    
    def get_ignored_facts(self, min_retrieves: int = 5) -> List[Dict]:
        """
        Get facts that are frequently retrieved but never used.
        
        Args:
            min_retrieves: minimum retrieval count to consider
            
        Returns:
            list of ignored fact data with stats
        """
        ignored_ids = self._usage_tracker.get_ignored_facts(
            min_retrieves=min_retrieves,
            usage_threshold=0.1
        )
        
        results = []
        for fact_id in ignored_ids:
            if fact_id in self._all_facts_cache:
                results.append({
                    **self._all_facts_cache[fact_id],
                    "usage_stats": self._usage_tracker.get_stats(fact_id)
                })
        
        return results
    
    def get_utilization_report(self) -> Dict:
        """Generate overall memory utilization report."""
        total_facts = len(self._all_facts_cache)
        tracked_facts = len(self._usage_tracker._tracking)
        
        # Count facts that have been used
        used_count = sum(
            1 for fid in self._usage_tracker._tracking
            if self._usage_tracker.is_fact_used(fid)
        )
        
        # Count ignored facts
        ignored = self._usage_tracker.get_ignored_facts(min_retrieves=3)
        
        return {
            "total_facts": total_facts,
            "tracked_facts": tracked_facts,
            "used_in_output": used_count,
            "utilization_rate": used_count / total_facts if total_facts > 0 else 0,
            "ignored_count": len(ignored),
            "ignored_facts": [
                {
                    "fact_id": f.get("entity_id"),
                    "subject": f.get("subject"),
                    "retrieve_count": f.get("usage_stats", {}).get("retrieve_count", 0)
                }
                for f in ignored[:10]  # Top 10 ignored
            ]
        }
    
    def fact_exists(self, fact_id: str) -> bool:
        """Check if a fact exists in storage."""
        return fact_id in self._all_facts_cache
    
    def get_fact(self, fact_id: str) -> Optional[Dict]:
        """Get a single fact by ID (with usage tracking)."""
        if fact_id in self._all_facts_cache:
            self._usage_tracker.on_retrieve(fact_id, "")
            return self._all_facts_cache[fact_id]
        return None


def main():
    parser = argparse.ArgumentParser(description="Memory Retriever with Usage Tracking")
    parser.add_argument("--query", "-q", help="Search query")
    parser.add_argument("--fact-id", "-i", action="append", help="Specific fact ID(s)")
    parser.add_argument("--top-k", "-k", type=int, default=10, help="Max results")
    parser.add_argument("--stats", "-s", action="store_true", help="Show utilization stats")
    parser.add_argument("--ignored", action="store_true", help="Show ignored facts")
    parser.add_argument("--context", "-c", default="", help="Context for usage tracking")
    
    args = parser.parse_args()
    
    retriever = MemoryRetriever()
    
    if args.stats:
        report = retriever.get_utilization_report()
        print("=== Memory Utilization Report ===")
        print(f"Total facts: {report['total_facts']}")
        print(f"Tracked: {report['tracked_facts']}")
        print(f"Used in output: {report['used_in_output']}")
        print(f"Utilization rate: {report['utilization_rate']:.1%}")
        print(f"Ignored facts: {report['ignored_count']}")
        return
    
    if args.ignored:
        print("=== Ignored Facts (retrieved but never used) ===")
        ignored = retriever.get_ignored_facts(min_retrieves=3)
        if not ignored:
            print("No ignored facts found!")
            return
        for f in ignored:
            stats = f.get("usage_stats", {})
            print(f"\n[{f.get('entity_id')}]")
            print(f"  Subject: {f.get('subject')}")
            print(f"  Retrieves: {stats.get('retrieve_count', 0)}")
            print(f"  Used: {stats.get('used_in_output', False)}")
        return
    
    # Default: retrieve facts
    results = retriever.retrieve(
        query=args.query,
        fact_ids=args.fact_id,
        top_k=args.top_k,
        context=args.context
    )
    
    if not results:
        print("No matching facts found.")
        return
    
    print(f"=== Retrieved {len(results)} fact(s) ===\n")
    for i, fact in enumerate(results, 1):
        stats = fact.get("usage_stats", {})
        print(f"{i}. [{fact.get('entity_id')}]")
        print(f"   Type: {fact.get('type')}")
        print(f"   Subject: {fact.get('subject')}")
        print(f"   Action: {fact.get('action', '')[:80]}...")
        print(f"   Usage: retrieve={stats.get('retrieve_count', 0)}, "
              f"used={stats.get('used_in_output', False)}")
        print()


if __name__ == "__main__":
    main()
