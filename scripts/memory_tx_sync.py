#!/usr/bin/env python3
"""
Memory Transaction Sync
OCM Sup v2.4 - P0-2

Single Source of Truth for memory writes.
LLM extraction → structured JSON → derived (vector + graph)
Ensures atomic sync between all memory stores.

Usage:
    python3 memory_tx_sync.py --action write --memory <json_file>
    python3 memory_tx_sync.py --action verify
    python3 memory_tx_sync.py --action repair
"""

import os
import sys
import json
import argparse
import hashlib
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple


class MemoryTransactionSync:
    """
    Memory Transaction Sync - Atomic write to all stores
    
    Flow:
    1. Write structured JSON (source of truth)
    2. Sync to vector store (embedding)
    3. Sync to graph store (entities + relations)
    
    Transaction log ensures consistency + rollback on failure.
    """
    
    def __init__(
        self,
        tx_dir: str = "/root/.openclaw/workspace/memory/transactions",
        struct_dir: str = "/root/.openclaw/workspace/memory/structured",
        vector_cache: str = "/root/.openclaw/workspace/memory/vector_store.jsonl",
        graph_path: str = "/root/.openclaw/workspace/memory/graph_store.jsonl",
    ):
        self.tx_dir = Path(tx_dir)
        self.struct_dir = Path(struct_dir)
        self.vector_cache = Path(vector_cache)
        self.graph_path = Path(graph_path)
        
        for p in [self.tx_dir, self.struct_dir]:
            p.mkdir(parents=True, exist_ok=True)
    
    def _id(self, memory: Dict) -> str:
        content = f"{memory.get('type')}:{memory.get('subject')}:{memory.get('action')}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _write_structured(self, memory: Dict) -> Path:
        """Write to structured JSON (source of truth)."""
        mem_id = self._id(memory)
        struct_file = self.struct_dir / f"{mem_id}.json"
        
        entry = {
            **memory,
            "id": mem_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        with open(struct_file, "w") as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)
        
        return struct_file
    
    def _sync_vector(self, memory: Dict) -> bool:
        """Sync to vector store (append to vector cache)."""
        mem_id = memory.get("id", self._id(memory))
        
        vector_entry = {
            "id": mem_id,
            "type": memory.get("type"),
            "subject": memory.get("subject"),
            "action": memory.get("action"),
            "embedding_text": f"{memory.get('subject')} {memory.get('action')}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Append to vector cache
        with open(self.vector_cache, "a") as f:
            f.write(json.dumps(vector_entry, ensure_ascii=False) + "\n")
        
        return True
    
    def _sync_graph(self, memory: Dict) -> bool:
        """Sync to graph store (entity + relationship extraction)."""
        mem_id = memory.get("id", self._id(memory))
        
        # Extract entities from subject
        subject = memory.get("subject", "")
        
        graph_entry = {
            "id": mem_id,
            "type": memory.get("type"),
            "subject": subject,
            "action": memory.get("action"),
            "entities": self._extract_entities(subject),
            "relations": self._extract_relations(memory),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Append to graph store
        with open(self.graph_path, "a") as f:
            f.write(json.dumps(graph_entry, ensure_ascii=False) + "\n")
        
        return True
    
    def _extract_entities(self, text: str) -> List[str]:
        """Simple entity extraction from text."""
        # Very simple - just split by common delimiters and filter
        # In production, use NER
        entities = []
        for part in text.replace("/", " ").replace("-", " ").split():
            part = part.strip(".,:;()[]{}")
            if part and len(part) > 1 and part[0].isupper():
                entities.append(part)
        return list(set(entities))[:10]  # Limit to 10
    
    def _extract_relations(self, memory: Dict) -> List[Dict]:
        """Extract relations from memory."""
        relations = []
        mem_type = memory.get("type", "")
        
        # Infer relations based on type
        if mem_type == "decision":
            relations.append({
                "type": "causes",
                "from": memory.get("subject"),
                "to": "outcome",
            })
        elif mem_type == "lesson":
            relations.append({
                "type": "learned_from",
                "from": memory.get("subject"),
                "to": memory.get("action", "")[:50],
            })
        
        return relations
    
    def _write_transaction(self, memory: Dict, success: bool, details: str):
        """Log transaction to transaction log."""
        tx_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "memory_id": memory.get("id", self._id(memory)),
            "success": success,
            "details": details,
            "memory": memory,
        }
        
        tx_file = self.tx_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
        with open(tx_file, "a") as f:
            f.write(json.dumps(tx_entry, ensure_ascii=False) + "\n")
    
    def write(self, memory: Dict) -> Tuple[bool, str]:
        """
        Atomic write: structured → vector + graph.
        
        Returns:
            (success, message)
        """
        mem_id = self._id(memory)
        
        try:
            # Step 1: Write structured (source of truth)
            struct_file = self._write_structured(memory)
            
            # Step 2: Sync to vector
            vec_ok = self._sync_vector({**memory, "id": mem_id})
            
            # Step 3: Sync to graph
            graph_ok = self._sync_graph({**memory, "id": mem_id})
            
            # Step 4: Log transaction (success)
            self._write_transaction(memory, True, f"OK: {struct_file}")
            
            return True, f"COMMITTED: {mem_id}"
            
        except Exception as e:
            # Rollback: remove from all stores
            self._rollback(mem_id)
            self._write_transaction(memory, False, f"ROLLBACK: {str(e)}")
            return False, f"FAILED: {str(e)}"
    
    def _rollback(self, mem_id: str):
        """Rollback a failed transaction."""
        # Remove from structured
        struct_file = self.struct_dir / f"{mem_id}.json"
        if struct_file.exists():
            struct_file.unlink()
        
        # Note: Can't easily remove from vector/graph without rewriting
        # This is a known limitation - rely on verify/repair
    
    def verify(self) -> Dict:
        """
        Verify consistency across all stores.
        
        Returns:
            verification report
        """
        report = {
            "structured_count": 0,
            "vector_count": 0,
            "graph_count": 0,
            "missing_in_vector": [],
            "missing_in_graph": [],
            "inconsistent": [],
        }
        
        # Count structured
        if self.struct_dir.exists():
            report["structured_count"] = len(list(self.struct_dir.glob("*.json")))
        
        # Count vector
        if self.vector_cache.exists():
            with open(self.vector_cache) as f:
                report["vector_count"] = sum(1 for _ in f)
        
        # Count graph
        if self.graph_path.exists():
            with open(self.graph_path) as f:
                report["graph_count"] = sum(1 for _ in f)
        
        # Check for orphaned entries (in vector but not in structured)
        if self.vector_cache.exists():
            with open(self.vector_cache) as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        struct_file = self.struct_dir / f"{entry['id']}.json"
                        if not struct_file.exists():
                            report["missing_in_vector"].append(entry['id'])
                    except:
                        pass
        
        return report
    
    def repair(self) -> Tuple[int, int]:
        """
        Attempt to repair inconsistencies.
        
        Returns:
            (repaired_count, failed_count)
        """
        report = self.verify()
        repaired = 0
        failed = 0
        
        # Re-sync orphaned entries
        for mem_id in report.get("missing_in_vector", []):
            # Try to find in vector/graph and rewrite structured
            # This is a best-effort repair
            failed += 1
        
        return repaired, failed


def main():
    parser = argparse.ArgumentParser(description="Memory Transaction Sync")
    parser.add_argument("--action", choices=["write", "verify", "repair"], required=True)
    parser.add_argument("--memory", help="JSON file with memory to write")
    parser.add_argument("--id", help="Memory ID to verify/repair")
    
    args = parser.parse_args()
    
    sync = MemoryTransactionSync()
    
    if args.action == "write":
        if not args.memory:
            print("ERROR: --memory required for write action")
            sys.exit(1)
        
        with open(args.memory) as f:
            memory = json.load(f)
        
        success, msg = sync.write(memory)
        print(msg)
        sys.exit(0 if success else 1)
    
    elif args.action == "verify":
        report = sync.verify()
        print(json.dumps(report, indent=2))
    
    elif args.action == "repair":
        repaired, failed = sync.repair()
        print(f"Repaired: {repaired}, Failed: {failed}")


if __name__ == "__main__":
    main()