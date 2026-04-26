#!/usr/bin/env python3
"""
Memory Write Gate
OCM Sup v2.4 - P0-1

Pre-write validator for memory extraction.
Ensures all memory writes go through schema validation, deduplication, and canonicalization.

Schema:
{
    "type": "lesson | fact | preference | decision | insight",
    "subject": "...",
    "action": "...",
    "confidence": 0.0-1.0,
    "timestamp": "ISO8601"
}

Usage:
    python3 memory_write_gate.py --input <json> [--output <file>] [--dry-run]
    echo '{"type":"fact","subject":"...","action":"...","confidence":0.9}' | python3 memory_write_gate.py
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple


VALID_TYPES = {"fact", "lesson", "preference", "decision", "insight", "constraint", "habit", "goal", "project", "episode", "reflection"}

REJECT_LOG = Path("/root/.openclaw/workspace/logs/memory_rejects.log")
REJECT_LOG.parent.mkdir(parents=True, exist_ok=True)


class MemoryWriteGate:
    """
    Memory Write Gate - Pre-write validator
    
    Validation stages:
    1. Schema validation (structure + types)
    2. Content validation (non-empty, reasonable length)
    3. Deduplication (check against existing memory)
    4. Canonicalization (normalize entities)
    """
    
    def __init__(
        self,
        memory_db_path: str = "/root/.openclaw/workspace/memory/checkpoints/validated_memories.jsonl",
        entity_map_path: str = "/root/.openclaw/workspace/memory/entity_canonical_map.json",
    ):
        self.memory_db_path = Path(memory_db_path)
        self.memory_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.entity_map = self._load_entity_map()
        self._memory_cache = self._load_memory_cache()
    
    def _load_entity_map(self) -> Dict[str, str]:
        """Load entity canonicalization map."""
        p = Path(entity_map_path if 'entity_map_path' in dir() else "/root/.openclaw/workspace/memory/entity_canonical_map.json")
        if p.exists():
            with open(p) as f:
                return json.load(f)
        return {}
    
    def _load_memory_cache(self) -> List[Dict]:
        """Load existing memories for deduplication."""
        if self.memory_db_path.exists():
            memories = []
            with open(self.memory_db_path) as f:
                for line in f:
                    try:
                        memories.append(json.loads(line.strip()))
                    except:
                        pass
            return memories
        return []
    
    def validate(self, memory: Dict) -> Tuple[bool, str, Optional[Dict]]:
        """
        Validate a memory entry.
        
        Returns:
            (is_valid, rejection_reason, canonicalized_memory)
        """
        
        # === Stage 1: Schema Validation ===
        if not isinstance(memory, dict):
            return False, "NOT_DICT", None
        
        for field in ["type", "subject", "action"]:
            if field not in memory:
                return False, f"MISSING_FIELD:{field}", None
        
        # Type validation
        mem_type = memory.get("type", "").lower()
        if mem_type not in VALID_TYPES:
            return False, f"INVALID_TYPE:{mem_type}", None
        
        # Confidence validation
        conf = memory.get("confidence", 0.0)
        if not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
            return False, f"INVALID_CONFIDENCE:{conf}", None
        
        # === Stage 2: Content Validation ===
        subject = memory.get("subject", "").strip()
        action = memory.get("action", "").strip()
        
        if len(subject) < 2:
            return False, "SUBJECT_TOO_SHORT", None
        
        if len(subject) > 500:
            return False, "SUBJECT_TOO_LONG", None
        
        if len(action) < 2:
            return False, "ACTION_TOO_SHORT", None
        
        if len(action) > 2000:
            return False, "ACTION_TOO_LONG", None
        
        # === Stage 3: Deduplication ===
        for existing in self._memory_cache:
            if self._is_duplicate(memory, existing):
                return False, f"DUPLICATE:{existing.get('id', 'unknown')}", None
        
        # === Stage 4: Canonicalization ===
        canonical = self._canonicalize(memory)
        
        # Double-check canonicalized version isn't a dupe
        for existing in self._memory_cache:
            if self._is_duplicate(canonical, existing):
                return False, f"DUPLICATE_AFTER_CANON:{existing.get('id', 'unknown')}", None
        
        return True, "", canonical
    
    def _is_duplicate(self, a: Dict, b: Dict) -> bool:
        """Check if two memories are semantically duplicate."""
        # Same type + same subject + high overlap in action
        if a.get("type") != b.get("type"):
            return False
        
        subj_a = a.get("subject", "").lower().strip()
        subj_b = b.get("subject", "").lower().strip()
        
        # Subject must match (with alias support)
        subj_a_canon = self._canonicalize_entity(subj_a)
        subj_b_canon = self._canonicalize_entity(subj_b)
        
        if subj_a_canon != subj_b_canon:
            return False
        
        # Action similarity (simple word overlap)
        action_a = set(a.get("action", "").lower().split())
        action_b = set(b.get("action", "").lower().split())
        
        if not action_a or not action_b:
            return False
        
        overlap = len(action_a & action_b) / max(len(action_a | action_b), 1)
        return overlap > 0.85
    
    def _canonicalize_entity(self, entity: str) -> str:
        """Canonicalize entity name using alias map."""
        entity_lower = entity.lower().strip()
        return self.entity_map.get(entity_lower, entity_lower)
    
    def _canonicalize(self, memory: Dict) -> Dict:
        """Canonicalize a memory entry."""
        canonical = dict(memory)
        
        # Canonicalize subject
        subject = memory.get("subject", "").strip()
        canonical["subject"] = self.entity_map.get(subject.lower(), subject)
        
        # Add metadata
        canonical["id"] = self._generate_id(canonical)
        canonical["canonicalized_at"] = datetime.now(timezone.utc).isoformat()
        
        return canonical
    
    def _generate_id(self, memory: Dict) -> str:
        """Generate deterministic ID for a memory."""
        import hashlib
        content = f"{memory.get('type')}:{memory.get('subject')}:{memory.get('action')}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def write(self, memory: Dict) -> Tuple[bool, str]:
        """
        Validate and write a memory entry.
        
        Returns:
            (success, message)
        """
        is_valid, reason, canonical = self.validate(memory)
        
        if not is_valid:
            # Log rejected memory
            self._log_rejection(memory, reason)
            return False, f"REJECTED: {reason}"
        
        # Write to database
        with open(self.memory_db_path, "a") as f:
            f.write(json.dumps(canonical, ensure_ascii=False) + "\n")
        
        # Update cache
        self._memory_cache.append(canonical)
        
        return True, f"WRITTEN: {canonical['id']}"
    
    def _log_rejection(self, memory: Dict, reason: str):
        """Log rejected memory for audit."""
        with open(REJECT_LOG, "a") as f:
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": reason,
                "memory": memory,
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    def get_stats(self) -> Dict:
        """Get memory gate statistics."""
        return {
            "total_memories": len(self._memory_cache),
            "reject_log_lines": self._count_log_lines(REJECT_LOG),
            "entity_map_size": len(self.entity_map),
            "db_path": str(self.memory_db_path),
        }
    
    def _count_log_lines(self, path: Path) -> int:
        if not path.exists():
            return 0
        with open(path) as f:
            return sum(1 for _ in f)


def main():
    parser = argparse.ArgumentParser(description="Memory Write Gate - Pre-write validator")
    parser.add_argument("--input", help="JSON file with memory to validate")
    parser.add_argument("--output", help="Output file for validated memories")
    parser.add_argument("--dry-run", action="store_true", help="Validate but don't write")
    parser.add_argument("--stats", action="store_true", help="Show gate statistics")
    parser.add_argument("--entity-map", help="Path to entity canonicalization map")
    
    args = parser.parse_args()
    
    gate = MemoryWriteGate()
    
    if args.stats:
        stats = gate.get_stats()
        print(json.dumps(stats, indent=2))
        return
    
    # Read memory to validate
    if args.input:
        with open(args.input) as f:
            memory = json.load(f)
    else:
        memory = json.load(sys.stdin)
    
    is_valid, reason, canonical = gate.validate(memory)
    
    if is_valid:
        print(f"✅ VALID: {canonical['id']}")
        if not args.dry_run:
            success, msg = gate.write(memory)
            print(msg)
        if args.output and not args.dry_run:
            with open(args.output, "w") as f:
                json.dump(canonical, f, ensure_ascii=False)
    else:
        print(f"❌ REJECTED: {reason}")
        sys.exit(1)


if __name__ == "__main__":
    main()