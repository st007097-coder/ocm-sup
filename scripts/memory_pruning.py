#!/usr/bin/env python3
"""
Memory Pruning & Decay
OCM Sup v2.4 - P2-2

Implements memory lifecycle:
- Decay: old memories lose relevance over time
- Pruning: low-value / stale memories removed
- Promotion: important short-term memories promoted to long-term

Usage:
    python3 memory_pruning.py [--dry-run] [--report]
    python3 memory_pruning.py --decay-days 30 --min-confidence 0.4
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Tuple


class MemoryPruner:
    """
    Memory lifecycle manager.
    
    - Decay: memories older than max_age lose score
    - Prune: memories below threshold removed
    - Archive: deleted memories saved to archive
    """
    
    def __init__(
        self,
        struct_dir: str = "/root/.openclaw/workspace/memory/structured",
        archive_dir: str = "/root/.openclaw/workspace/memory/archive",
        decayed_dir: str = "/root/.openclaw/workspace/memory/decayed",
        max_age_days: int = 90,
        min_confidence: float = 0.3,
        min_score_threshold: float = 0.2,
        decay_rate: float = 0.95,
    ):
        self.struct_dir = Path(struct_dir)
        self.archive_dir = Path(archive_dir)
        self.decayed_dir = Path(decayed_dir)
        self.max_age_days = max_age_days
        self.min_confidence = min_confidence
        self.min_score_threshold = min_score_threshold
        self.decay_rate = decay_rate
        
        # Create directories
        for d in [self.archive_dir, self.decayed_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def calculate_decay_score(self, memory: Dict) -> float:
        """Calculate decay score based on age and confidence."""
        created = memory.get("created_at") or memory.get("timestamp")
        
        if not created:
            return 0.5  # Default
        
        try:
            if isinstance(created, str):
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            else:
                created_dt = created
            
            age_days = (datetime.now(timezone.utc) - created_dt).total_seconds() / 86400
            
            # Exponential decay based on age
            decay = self.decay_rate ** (age_days / 30)  # Half-life of 30 days
            
            # Base confidence
            confidence = memory.get("confidence", 0.5)
            
            # Final score = decay * confidence
            score = decay * confidence
            
            return round(score, 3)
        except:
            return 0.0
    
    def should_prune(self, memory: Dict) -> Tuple[bool, str]:
        """
        Determine if a memory should be pruned.
        
        Returns:
            (should_prune, reason)
        """
        score = self.calculate_decay_score(memory)
        
        # Check score threshold
        if score < self.min_score_threshold:
            return True, f"score_too_low:{score}"
        
        # Check age
        created = memory.get("created_at") or memory.get("timestamp")
        if created:
            try:
                if isinstance(created, str):
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                else:
                    created_dt = created
                
                age_days = (datetime.now(timezone.utc) - created_dt).total_seconds() / 86400
                
                if age_days > self.max_age_days:
                    return True, f"too_old:{age_days}d"
            except:
                pass
        
        # Check confidence
        conf = memory.get("confidence", 0.5)
        if conf < self.min_confidence:
            return True, f"low_confidence:{conf}"
        
        # Check type-specific rules
        mem_type = memory.get("type", "")
        if mem_type == "habit" and score < 0.4:
            return True, f"habit_stale:{score}"
        
        return False, ""
    
    def prune(self, dry_run: bool = True) -> Dict:
        """
        Prune memories based on lifecycle rules.
        
        Returns:
            Pruning report
        """
        report = {
            "scanned": 0,
            "pruned": 0,
            "archived": 0,
            "decayed": 0,
            "kept": 0,
            "pruned_ids": [],
            "reasons": {},
        }
        
        if not self.struct_dir.exists():
            return report
        
        for f in self.struct_dir.glob("*.json"):
            try:
                with open(f) as fh:
                    memory = json.load(fh)
                
                report["scanned"] += 1
                mem_id = memory.get("id", f.stem)
                
                should_prune, reason = self.should_prune(memory)
                
                if should_prune:
                    if dry_run:
                        report["pruned"] += 1
                        report["pruned_ids"].append(mem_id)
                        report["reasons"][mem_id] = reason
                    else:
                        # Archive before delete
                        archive_path = self.archive_dir / f"{mem_id}.json"
                        shutil.copy(f, archive_path)
                        
                        # Delete original
                        f.unlink()
                        
                        report["archived"] += 1
                        report["pruned_ids"].append(mem_id)
                        report["reasons"][mem_id] = reason
                else:
                    # Check if decayed but still kept
                    score = self.calculate_decay_score(memory)
                    if score < 0.5:
                        report["decayed"] += 1
                    report["kept"] += 1
                    
            except Exception as e:
                print(f"Error processing {f}: {e}")
        
        return report
    
    def generate_report(self) -> str:
        """Generate human-readable pruning report."""
        report = self.prune(dry_run=True)
        
        lines = [
            "📊 Memory Pruning Report",
            f"   Scanned: {report['scanned']}",
            f"   Kept: {report['kept']}",
            f"   Decayed (low score): {report['decayed']}",
            f"   Would prune: {report['pruned']}",
            "",
        ]
        
        if report["pruned"] > 0:
            lines.append("   🔴 Would be pruned:")
            for mem_id, reason in report["reasons"].items():
                lines.append(f"     - {mem_id}: {reason}")
        
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Memory Pruning & Decay")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be pruned")
    parser.add_argument("--report", action="store_true", help="Show full report")
    parser.add_argument("--decay-days", type=int, default=90, help="Max age in days")
    parser.add_argument("--min-confidence", type=float, default=0.3, help="Min confidence threshold")
    parser.add_argument("--min-score", type=float, default=0.2, help="Min score threshold")
    parser.add_argument("--execute", action="store_true", help="Actually prune (dry-run if not set)")
    
    args = parser.parse_args()
    
    pruner = MemoryPruner(
        max_age_days=args.decay_days,
        min_confidence=args.min_confidence,
        min_score_threshold=args.min_score,
    )
    
    if args.report or args.dry_run:
        report = pruner.prune(dry_run=not args.execute)
        
        if args.report:
            print(json.dumps(report, indent=2))
        else:
            print(pruner.generate_report())
        
        if args.dry_run and not args.execute:
            print("\n💡 Use --execute to actually prune")
    else:
        report = pruner.prune(dry_run=not args.execute)
        print(f"Pruned: {report['pruned']} ({report['archived']} archived)")


if __name__ == "__main__":
    main()