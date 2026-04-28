#!/usr/bin/env python3
"""
Memory Pruning Adapter
OCM Sup v2.4 - P4 Phase 2

Bridges P3 PruningPolicy with actual P3 storage layers.
Reads facts from structured storage + usage tracking, executes pruning.

Usage:
    python3 memory_pruning_adapter.py --dry-run
    python3 memory_pruning_adapter.py --execute
    python3 memory_pruning_adapter.py --status
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple

# P3 components
sys.path.insert(0, str(Path(__file__).parent.parent))
from p3_reliability.pruning import PruningPolicy, PruneScorer
from p3_reliability.usage import UsageTracker

# Storage paths (P3 standard)
OCM_SUP_BASE = Path("~/.openclaw/ocm-sup").expanduser()
STRUCTURED_DIR = OCM_SUP_BASE / "structured"
VECTOR_DIR = OCM_SUP_BASE / "embeddings"
GRAPH_DIR = OCM_SUP_BASE / "graph"
ARCHIVE_DIR = OCM_SUP_BASE / "archive"

# Ensure directories exist
for d in [STRUCTURED_DIR, VECTOR_DIR, GRAPH_DIR, ARCHIVE_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class MemoryPruningAdapter:
    """
    Adapter that connects P3 PruningPolicy to P3 storage layers.
    
    Flow:
    1. Load facts from structured storage
    2. Enrich with usage tracking data
    3. Run PruningPolicy to score and rank facts
    4. Execute pruning (archive + delete) based on scores
    """
    
    def __init__(self, threshold: float = 0.7):
        self._pruning_policy = PruningPolicy(threshold=threshold)
        self._usage_tracker = UsageTracker()
        self._scorer = PruneScorer(threshold=threshold)
    
    def _load_facts(self) -> List[Dict]:
        """Load facts from structured storage and enrich with usage data."""
        facts = []
        
        if not STRUCTURED_DIR.exists():
            return facts
        
        for f in STRUCTURED_DIR.glob("*.json"):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                    fact_id = data.get("entity_id", f.stem)
                    
                    # Get usage data from tracker
                    usage_stats = self._usage_tracker.get_stats(fact_id) or {}
                    
                    # Enrich fact with usage data for scoring
                    enriched = {
                        "entity_id": fact_id,
                        "type": data.get("type"),
                        "subject": data.get("subject"),
                        "action": data.get("action"),
                        "created_at": data.get("created_at"),
                        "importance": data.get("metadata", {}).get("importance", "UNKNOWN"),
                        # From usage tracking
                        "access_count": usage_stats.get("retrieve_count", 0),
                        "used_in_output": usage_stats.get("used_in_output", False),
                        "decision_influenced_count": usage_stats.get("decision_influenced_count", 0),
                        "last_accessed": usage_stats.get("last_retrieved"),
                    }
                    facts.append(enriched)
            except Exception as e:
                print(f"Error loading {f}: {e}")
        
        return facts
    
    def _get_fact_text(self, fact: Dict) -> str:
        """Get fact text for archiving."""
        return f"{fact.get('subject', '')} {fact.get('action', '')}"
    
    def _delete_from_layers(self, fact_id: str) -> bool:
        """
        Delete fact from all storage layers.
        
        Returns True if all deletions succeeded.
        """
        success = True
        
        # Delete from structured
        struct_file = STRUCTURED_DIR / f"{fact_id}.json"
        if struct_file.exists():
            try:
                struct_file.unlink()
            except Exception as e:
                print(f"Failed to delete structured {fact_id}: {e}")
                success = False
        
        # Delete from vector
        vector_file = VECTOR_DIR / f"{fact_id}.json"
        if vector_file.exists():
            try:
                vector_file.unlink()
            except Exception as e:
                print(f"Failed to delete vector {fact_id}: {e}")
                success = False
        
        # Delete from graph
        graph_file = GRAPH_DIR / f"{fact_id}.json"
        if graph_file.exists():
            try:
                graph_file.unlink()
            except Exception as e:
                print(f"Failed to delete graph {fact_id}: {e}")
                success = False
        
        return success
    
    def status(self) -> Dict:
        """Get pruning status without executing."""
        facts = self._load_facts()
        ranked = self._scorer.rank(facts)
        
        prune_eligible = [f for f, score in ranked if score > self._scorer.threshold]
        
        return {
            "total_facts": len(facts),
            "prune_eligible": len(prune_eligible),
            "threshold": self._scorer.threshold,
            "top_prune_candidates": [
                {
                    "entity_id": f.get("entity_id"),
                    "subject": (f.get("subject") or "")[:50],
                    "score": self._scorer.compute(f),
                    "access_count": f.get("access_count", 0),
                    "used_in_output": f.get("used_in_output", False)
                }
                for f, _ in ranked[:10]
            ]
        }
    
    def dry_run(self) -> Dict:
        """
        Run pruning in dry-run mode (no actual deletion).
        
        Returns detailed report.
        """
        facts = self._load_facts()
        result = self._pruning_policy.execute(
            facts,
            dry_run=True,
            get_fact_text=self._get_fact_text
        )
        
        # Add additional info
        result["threshold"] = self._scorer.threshold
        result["status"] = "dry_run"
        
        return result
    
    def execute(self, max_prune: int = 50) -> Dict:
        """
        Execute pruning (archive + delete eligible facts).
        
        Args:
            max_prune: maximum number of facts to prune in one run
            
        Returns:
            execution report
        """
        facts = self._load_facts()
        ranked = self._scorer.rank(facts)
        
        # Filter to only prune-eligible
        eligible = [(f, score) for f, score in ranked if score > self._scorer.threshold]
        
        pruned_count = 0
        archived_count = 0
        failed_count = 0
        pruned_facts = []
        
        for fact, score in eligible[:max_prune]:
            fact_id = fact.get("entity_id")
            fact_text = self._get_fact_text(fact)
            
            # Archive first
            try:
                self._pruning_policy.archiver.archive(fact_id, fact_text, fact)
                archived_count += 1
            except Exception as e:
                print(f"Failed to archive {fact_id}: {e}")
                failed_count += 1
                continue
            
            # Then delete from layers
            if self._delete_from_layers(fact_id):
                pruned_count += 1
                pruned_facts.append({
                    "entity_id": fact_id,
                    "subject": (fact.get("subject") or "")[:50],
                    "score": score,
                    "archived": True
                })
            else:
                failed_count += 1
        
        return {
            "status": "executed",
            "total_facts": len(facts),
            "pruned_count": pruned_count,
            "archived_count": archived_count,
            "failed_count": failed_count,
            "threshold": self._scorer.threshold,
            "pruned_facts": pruned_facts
        }


def main():
    parser = argparse.ArgumentParser(description="Memory Pruning Adapter")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no actual deletion)")
    parser.add_argument("--execute", action="store_true", help="Execute pruning")
    parser.add_argument("--status", action="store_true", help="Show pruning status")
    parser.add_argument("--threshold", type=float, default=0.7, help="Prune threshold (0.0-1.0)")
    parser.add_argument("--max-prune", type=int, default=50, help="Max facts to prune per run")
    
    args = parser.parse_args()
    
    adapter = MemoryPruningAdapter(threshold=args.threshold)
    
    if args.status:
        status = adapter.status()
        print("=== Memory Pruning Status ===")
        print(f"Total facts: {status['total_facts']}")
        print(f"Prune-eligible: {status['prune_eligible']}")
        print(f"Threshold: {status['threshold']}")
        print("\nTop prune candidates:")
        for c in status['top_prune_candidates']:
            print(f"  [{c['score']:.3f}] {c['entity_id']}: {c['subject']}... "
                  f"(access={c['access_count']}, used={c['used_in_output']})")
        return
    
    if args.dry_run:
        result = adapter.dry_run()
        print("=== Pruning Dry Run ===")
        print(f"Total facts: {result['total_facts']}")
        print(f"Would prune: {result['pruned_count']}")
        print(f"Threshold: {result['threshold']}")
        if result['pruned_facts']:
            print("\nWould delete:")
            for pf in result['pruned_facts'][:10]:
                print(f"  [{pf.get('score', 0):.3f}] {pf.get('entity_id')}")
        return
    
    if args.execute:
        result = adapter.execute(max_prune=args.max_prune)
        print("=== Pruning Executed ===")
        print(f"Pruned: {result['pruned_count']}")
        print(f"Archived: {result['archived_count']}")
        print(f"Failed: {result['failed_count']}")
        return
    
    # Default: show dry run
    result = adapter.dry_run()
    print("=== Pruning Dry Run (default) ===")
    print(f"Total facts: {result['total_facts']}")
    print(f"Would prune: {result['pruned_count']} (threshold={result['threshold']})")


if __name__ == "__main__":
    main()
