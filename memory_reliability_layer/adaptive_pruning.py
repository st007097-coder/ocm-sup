"""
Adaptive Pruning with Archiver
OCM Sup v2.6

Score-based pruning with automatic archiving.
Based on user's adaptive pruning approach with fixed formula.

Usage:
    pruner = AdaptivePruning(threshold=0.7)
    
    # Dry run
    result = pruner.execute(dry_run=True)
    
    # Actual execution
    result = pruner.execute(dry_run=False, max_prune=50)
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import config


class PruningResult:
    """Result of a pruning run."""
    
    def __init__(self, pruned_count: int = 0, archived_count: int = 0, 
                 failed_count: int = 0, dry_run: bool = True):
        self.dry_run = dry_run
        self.pruned_count = pruned_count
        self.archived_count = archived_count
        self.failed_count = failed_count
        self.facts = []
    
    def to_dict(self) -> dict:
        return {
            "dry_run": self.dry_run,
            "pruned_count": self.pruned_count,
            "archived_count": self.archived_count,
            "failed_count": self.failed_count,
            "facts": self.facts
        }


class AdaptivePruning:
    """
    Adaptive pruning with score-based decision.
    
    Formula (fixed from user's suggestion):
        score = importance_factor + age_factor * 0.3 + access_factor * 0.3
        
    Where:
        importance_factor = (1 - importance) * 0.4
        age_factor = min(age_days / 30, 1.0)
        access_factor = 1 / (1 + access_count)
    
    Higher score = more urgent to prune
    """
    
    def __init__(self, threshold: float = None):
        self.threshold = threshold or config.PRUNE_THRESHOLD
        self.max_per_run = config.PRUNE_MAX_PER_RUN
        self.half_life_days = config.HALF_LIFE_DAYS
        self.importance_weights = config.IMPORTANCE_WEIGHTS
    
    def score(self, fact: dict, usage: dict) -> float:
        """
        Compute prune score for a fact.
        
        Score range: 0.0 - 1.0
        Higher score = more urgent to prune
        
        Args:
            fact: Fact dict with keys:
                - timestamp or created_at: creation time
                - importance: HIGH/MEDIUM/LOW/UNKNOWN (default 0.5)
            usage: Usage dict with keys:
                - count: number of retrievals
        """
        # Get timestamp
        timestamp = fact.get("timestamp") or fact.get("created_at") or time.time()
        # Handle string timestamps
        if isinstance(timestamp, str):
            try:
                from datetime import datetime
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp()
            except:
                timestamp = time.time()
        age_days = (time.time() - float(timestamp)) / 86400  # Convert to days
        
        # Get importance (0.0 to 1.0, higher = more important = lower prune score)
        importance_str = fact.get("importance", "UNKNOWN")
        if isinstance(importance_str, (int, float)):
            importance = float(importance_str)
        else:
            importance = self.importance_weights.get(importance_str, config.DEFAULT_IMPORTANCE)
        
        # Get access count
        access_count = usage.get("count", 0) if usage else 0
        
        # Compute factors
        # Importance factor: low importance = high prune score
        # Weight: 0.4 (upgraded from 0.3 in user's suggestion)
        importance_factor = (1 - importance) * 0.4
        
        # Age factor: older = higher score (logarithmic growth, capped at 30 days)
        age_factor = min(age_days / self.half_life_days, 1.0) * 0.3
        
        # Access factor: low access = high prune score
        # Weight: 0.3
        access_factor = (1 / (1 + access_count)) * 0.3
        
        score = importance_factor + age_factor + access_factor
        
        return round(score, 4)
    
    def should_prune(self, fact: dict, usage: dict) -> bool:
        """Returns True if fact should be pruned."""
        return self.score(fact, usage) > self.threshold
    
    def rank_facts(self, facts: List[dict], usage_data: dict) -> List[Tuple[dict, float]]:
        """
        Rank facts by prune score (highest first).
        
        Returns list of (fact, score) tuples.
        """
        scored = []
        for fact in facts:
            fact_id = fact.get("entity_id", "")
            usage = usage_data.get(fact_id, {})
            score = self.score(fact, usage)
            scored.append((fact, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
    
    def execute(self, facts: List[dict], usage_data: dict, 
               dry_run: bool = True, max_prune: int = None) -> PruningResult:
        """
        Execute pruning on facts.
        
        Args:
            facts: List of fact dicts
            usage_data: Dict of {fact_id: usage_info}
            dry_run: If True, don't actually delete (default True)
            max_prune: Maximum number of facts to prune
            
        Returns:
            PruningResult with counts and fact list
        """
        if max_prune is None:
            max_prune = self.max_per_run
        
        result = PruningResult(dry_run=dry_run)
        ranked = self.rank_facts(facts, usage_data)
        
        # Filter to prune-eligible
        eligible = [(f, s) for f, s in ranked if s > self.threshold]
        
        for fact, score in eligible[:max_prune]:
            fact_id = fact.get("entity_id", "unknown")
            
            if not dry_run:
                # Archive first, then delete
                fact_text = f"{fact.get('subject', '')} {fact.get('action', '')}"
                archived = self.archive(fact_id, fact_text, fact)
                
                if archived:
                    # Delete from storage
                    success = self._delete_from_storage(fact_id)
                    if success:
                        result.pruned_count += 1
                        result.archived_count += 1
                    else:
                        result.failed_count += 1
                else:
                    result.failed_count += 1
            else:
                result.pruned_count += 1
            
            result.facts.append({
                "fact_id": fact_id,
                "subject": fact.get("subject", ""),
                "score": score
            })
        
        return result
    
    def archive(self, fact_id: str, fact_text: str, metadata: dict = None) -> bool:
        """
        Archive a fact before deletion.
        
        Args:
            fact_id: ID of the fact
            fact_text: Text content for archive log
            metadata: Optional metadata
            
        Returns:
            True if archived successfully
        """
        config.ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        
        archive_entry = {
            "fact_id": fact_id,
            "fact_text": fact_text,
            "metadata": metadata or {},
            "archived_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            "reason": "pruning"
        }
        
        archive_file = config.ARCHIVE_DIR / f"{fact_id}.json"
        
        try:
            with open(archive_file, "w") as f:
                json.dump(archive_entry, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[PRUNE] Failed to archive {fact_id}: {e}")
            return False
    
    def _delete_from_storage(self, fact_id: str) -> bool:
        """
        Delete fact from all storage layers.
        
        Returns True if all deletions succeeded.
        """
        success = True
        
        # Delete from structured
        struct_file = config.STORAGE_DIR / f"{fact_id}.json"
        if struct_file.exists():
            try:
                struct_file.unlink()
            except Exception as e:
                print(f"[PRUNE] Failed to delete structured {fact_id}: {e}")
                success = False
        
        # Delete from vector
        vector_file = config.VECTOR_DIR / f"{fact_id}.json"
        if vector_file.exists():
            try:
                vector_file.unlink()
            except Exception as e:
                print(f"[PRUNE] Failed to delete vector {fact_id}: {e}")
                success = False
        
        # Delete from graph
        graph_file = config.GRAPH_DIR / f"{fact_id}.json"
        if graph_file.exists():
            try:
                graph_file.unlink()
            except Exception as e:
                print(f"[PRUNE] Failed to delete graph {fact_id}: {e}")
                success = False
        
        return success
    
    def get_status(self, facts: List[dict], usage_data: dict) -> dict:
        """
        Get pruning status without executing.
        
        Returns summary of prune-eligible facts.
        """
        ranked = self.rank_facts(facts, usage_data)
        
        prune_eligible = [(f, s) for f, s in ranked if s > self.threshold]
        
        return {
            "total_facts": len(facts),
            "prune_eligible": len(prune_eligible),
            "threshold": self.threshold,
            "top_candidates": [
                {
                    "fact_id": f.get("entity_id"),
                    "subject": f.get("subject", ""),
                    "score": s
                }
                for f, s in prune_eligible[:10]
            ]
        }
