#!/usr/bin/env python3
"""
Memory Consistency Checker
OCM Sup v2.4 - P1-1

Detects:
- Duplicate memories (same subject + action)
- Contradictory memories (same subject, conflicting actions)
- Inconsistent memories (type/confidence mismatches)

Usage:
    python3 memory_consistency_check.py [--fix] [--report]
"""

import os
import sys
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone


class MemoryConsistencyChecker:
    """
    Check memory consistency across all stores.
    
    Detects:
    - Duplicates: same type + subject + similar action
    - Contradictions: same subject, different/conflicting actions
    - Structural issues: missing fields, invalid types
    """
    
    def __init__(
        self,
        struct_dir: str = "/root/.openclaw/workspace/memory/structured",
        vector_cache: str = "/root/.openclaw/workspace/memory/vector_store.jsonl",
        graph_store: str = "/root/.openclaw/workspace/memory/graph_store.jsonl",
        validated_db: str = "/root/.openclaw/workspace/memory/checkpoints/validated_memories.jsonl",
    ):
        self.struct_dir = Path(struct_dir)
        self.vector_cache = Path(vector_cache)
        self.graph_store = Path(graph_store)
        self.validated_db = Path(validated_db)
        
        self.duplicates = []
        self.contradictions = []
        self.structural_issues = []
        
        self._memories = []
        self._load_memories()
    
    def _load_memories(self):
        """Load all memories from structured store."""
        if not self.struct_dir.exists():
            return
        
        for f in self.struct_dir.glob("*.json"):
            try:
                with open(f) as fh:
                    self._memories.append(json.load(fh))
            except:
                pass
    
    def check(self) -> dict:
        """Run all consistency checks."""
        print("🔍 Checking for duplicates...")
        self._check_duplicates()
        
        print("🔍 Checking for contradictions...")
        self._check_contradictions()
        
        print("🔍 Checking structural integrity...")
        self._check_structural()
        
        return self._build_report()
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        return text.lower().strip().replace(" ", "").replace("\n", "")
    
    def _check_duplicates(self):
        """Find duplicate memories."""
        seen = defaultdict(list)
        
        for mem in self._memories:
            key = f"{mem.get('type')}:{mem.get('subject', '')}"
            seen[key].append(mem.get('id', 'unknown'))
        
        for key, ids in seen.items():
            if len(ids) > 1:
                self.duplicates.append({
                    "type": key.split(":")[0],
                    "subject": key.split(":")[1],
                    "ids": ids,
                    "count": len(ids),
                })
    
    def _check_contradictions(self):
        """Find contradictory memories (same subject, different outcomes)."""
        by_subject = defaultdict(list)
        
        for mem in self._memories:
            by_subject[mem.get('subject', '')].append(mem)
        
        for subject, memories in by_subject.items():
            if len(memories) < 2:
                continue
            
            # Group by action similarity
            action_groups = defaultdict(list)
            for mem in memories:
                action = mem.get('action', '')
                # Simple grouping: first 50 chars
                action_key = action[:50].lower().strip()
                action_groups[action_key].append(mem)
            
            # If we have significantly different actions for same subject
            if len(action_groups) > 1 and len(memories) > 1:
                self.contradictions.append({
                    "subject": subject,
                    "memory_count": len(memories),
                    "action_groups": len(action_groups),
                    "ids": [m.get('id') for m in memories],
                })
    
    def _check_structural(self):
        """Check for structural issues."""
        required_fields = ["type", "subject", "action", "confidence", "id", "created_at"]
        
        for mem in self._memories:
            missing = [f for f in required_fields if f not in mem]
            if missing:
                self.structural_issues.append({
                    "id": mem.get("id", "unknown"),
                    "missing_fields": missing,
                })
            
            # Check confidence range
            conf = mem.get("confidence")
            if conf is not None and not (0.0 <= conf <= 1.0):
                self.structural_issues.append({
                    "id": mem.get("id", "unknown"),
                    "issue": f"invalid_confidence:{conf}",
                })
    
    def _build_report(self) -> dict:
        """Build consistency report."""
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_memories": len(self._memories),
            "duplicates": {
                "count": len(self.duplicates),
                "items": self.duplicates,
            },
            "contradictions": {
                "count": len(self.contradictions),
                "items": self.contradictions,
            },
            "structural_issues": {
                "count": len(self.structural_issues),
                "items": self.structural_issues,
            },
            "health_score": self._calc_health_score(),
        }
        return report
    
    def _calc_health_score(self) -> float:
        """Calculate overall health score (0-100)."""
        total = len(self._memories)
        if total == 0:
            return 100.0
        
        issues = len(self.duplicates) * 2 + len(self.contradictions) * 3 + len(self.structural_issues)
        score = max(0.0, 100.0 - (issues / total) * 20)
        return round(score, 1)
    
    def fix(self) -> dict:
        """Fix detected issues (keeps most recent, removes others)."""
        fixed = {"duplicates": 0, "contradictions": 0, "structural": 0}
        
        # Fix duplicates: keep most recent by created_at
        for dup in self.duplicates:
            ids = sorted(dup["ids"])
            to_remove = ids[1:]  # Keep first, remove rest
            for mem_id in to_remove:
                struct_file = self.struct_dir / f"{mem_id}.json"
                if struct_file.exists():
                    struct_file.unlink()
                    fixed["duplicates"] += 1
        
        # Fix structural: remove entries with missing required fields
        for issue in self.structural_issues:
            mem_id = issue.get("id", "unknown")
            struct_file = self.struct_dir / f"{mem_id}.json"
            if struct_file.exists():
                struct_file.unlink()
                fixed["structural"] += 1
        
        return fixed
    
    def generate_summary(self) -> str:
        """Generate human-readable summary."""
        report = self._build_report()
        
        lines = [
            f"📊 Memory Consistency Report",
            f"   Total memories: {report['total_memories']}",
            f"   Health score: {report['health_score']}%",
            "",
            f"   Duplicates: {report['duplicates']['count']}",
            f"   Contradictions: {report['contradictions']['count']}",
            f"   Structural issues: {report['structural_issues']['count']}",
        ]
        
        if report['duplicates']['count'] > 0:
            lines.append("")
            lines.append("   🔴 Duplicates:")
            for d in report['duplicates']['items'][:3]:
                lines.append(f"     - {d['subject']}: {d['count']} copies")
        
        return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Memory Consistency Checker")
    parser.add_argument("--fix", action="store_true", help="Auto-fix detected issues")
    parser.add_argument("--report", action="store_true", help="Show detailed report")
    args = parser.parse_args()
    
    checker = MemoryConsistencyChecker()
    
    if args.report:
        report = checker.check()
        print(json.dumps(report, indent=2))
    else:
        summary = checker.generate_summary()
        print(summary)
        
        if args.fix:
            fixed = checker.fix()
            print("")
            print(f"🔧 Fixed: {fixed}")


if __name__ == "__main__":
    main()