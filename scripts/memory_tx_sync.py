#!/usr/bin/env python3
"""
Memory Transaction Sync
OCM Sup v2.4 - P4

Single Source of Truth for memory writes.
LLM extraction → structured JSON → derived (vector + graph)
Ensures atomic sync between all memory stores.

Now uses P3 TransactionManager for real atomicity (begin/commit/rollback).

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

# Memory Reliability Layer (v2.6)
sys.path.insert(0, str(Path(__file__).parent.parent))
from memory_reliability_layer import TransactionManager
from memory_reliability_layer import ContradictionEngine as ContradictionDetector
from memory_reliability_layer import UsageTracker

# Storage paths - now using P3 standard locations
OCM_SUP_BASE = Path("~/.openclaw/ocm-sup").expanduser()
STRUCTURED_DIR = OCM_SUP_BASE / "structured"
VECTOR_DIR = OCM_SUP_BASE / "embeddings"
GRAPH_DIR = OCM_SUP_BASE / "graph"
TX_DIR = OCM_SUP_BASE / "transactions"

# Ensure directories exist
for d in [STRUCTURED_DIR, VECTOR_DIR, GRAPH_DIR, TX_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class MemoryTransactionSync:
    """
    Memory Transaction Sync - Atomic write to all stores
    
    Flow (P4):
    1. Contradiction check (P3 ContradictionDetector)
    2. BEGIN TRANSACTION (P3 TransactionManager)
    3. Write structured JSON (source of truth)
    4. Sync to vector store (embedding)
    5. Sync to graph store (entities + relations)
    6. COMMIT or ROLLBACK
    
    Uses P3 TransactionManager for real atomicity.
    """
    
    def __init__(
        self,
        tx_dir: str = None,
        struct_dir: str = None,
        vector_cache: str = None,
        graph_path: str = None,
    ):
        # Use P3 standard paths by default
        self.tx_dir = Path(tx_dir) if tx_dir else TX_DIR
        self.struct_dir = Path(struct_dir) if struct_dir else STRUCTURED_DIR
        self.vector_cache = Path(vector_cache) if vector_cache else (VECTOR_DIR / "vectors.jsonl")
        self.graph_path = Path(graph_path) if graph_path else (GRAPH_DIR / "graph.jsonl")
        
        # Ensure directories exist
        for p in [self.tx_dir, self.struct_dir, self.vector_cache.parent, self.graph_path.parent]:
            p.mkdir(parents=True, exist_ok=True)
        
        # P3 Components
        self._tx_manager = TransactionManager()
        self._contradiction_detector = ContradictionDetector()
        self._usage_tracker = UsageTracker()
        
        # Load existing facts for contradiction detection
        self._all_facts_cache = self._load_all_facts()
    
    def _id(self, memory: Dict) -> str:
        content = f"{memory.get('type')}:{memory.get('subject')}:{memory.get('action')}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _load_all_facts(self) -> Dict[str, str]:
        """Load all existing facts for contradiction detection."""
        facts = {}
        if self.struct_dir.exists():
            for f in self.struct_dir.glob("*.json"):
                try:
                    with open(f) as fp:
                        data = json.load(fp)
                        fact_id = data.get("id", f.stem)
                        fact_text = f"{data.get('subject', '')} {data.get('action', '')}"
                        facts[fact_id] = fact_text
                except:
                    pass
        return facts
    
    def _check_contradiction(self, memory: Dict, mem_id: str) -> List:
        """Check for semantic contradictions before writing."""
        fact_text = f"{memory.get('subject')} {memory.get('action')}"
        if not fact_text.strip():
            return []
        
        results = self._contradiction_detector.check_fact(
            mem_id, fact_text, self._all_facts_cache
        )
        return results if results.found else []
    
    def write(self, memory: Dict) -> Tuple[bool, str]:
        """
        P4: Atomic write using TransactionManager.
        
        Flow:
        1. Generate entity_id
        2. Contradiction check (non-blocking)
        3. BEGIN TRANSACTION
        4. Write structured + vector + graph
        5. COMMIT or ROLLBACK
        
        Returns:
            (success, message)
        """
        entity_id = memory.get("id") or self._id(memory)
        
        # Step 1: Contradiction check (non-blocking, log only)
        contradictions = self._check_contradiction(memory, entity_id)
        if contradictions:
            for c in contradictions:
                print(f"⚠️  Contradiction detected: {mem_id} ↔ {c.get('fact_id')} "
                      f"(similarity: {c.get('similarity', 0):.2f})")
            self._contradiction_detector.run_full_scan()  # Log to file
        
        # Step 2: Atomic transaction
        payload = {"entity_id": entity_id, "memory": memory}
        
        try:
            with self._tx_manager.begin("write_fact", payload) as tx:
                # Write structured (source of truth)
                struct_data = {
                    "entity_id": entity_id,
                    "type": memory.get("type"),
                    "subject": memory.get("subject"),
                    "action": memory.get("action"),
                    "confidence": memory.get("confidence", 0.5),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "metadata": {k: v for k, v in memory.items()
                                 if k not in ["type", "subject", "action", "id", "confidence"]}
                }
                self._tx_manager.write_structured(tx, struct_data)
                
                # Write vector (embedding text)
                self._tx_manager.write_vector(tx, {
                    "entity_id": entity_id,
                    "embedding_text": f"{memory.get('subject')} {memory.get('action')}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                # Write graph (entities + relations)
                subject = memory.get("subject", "")
                self._tx_manager.write_graph(tx, {
                    "entity_id": entity_id,
                    "subject": subject,
                    "type": memory.get("type"),
                    "entities": self._extract_entities(subject),
                    "relations": self._extract_relations(memory),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            
            # Transaction committed successfully
            # Update local cache
            self._all_facts_cache[entity_id] = f"{memory.get('subject')} {memory.get('action')}"
            
            return True, f"COMMITTED: {entity_id}"
            
        except Exception as e:
            # Transaction rolled back automatically
            return False, f"FAILED: {str(e)}"
    
    def verify(self) -> Dict:
        """
        P4: Use TransactionManager's reconciliation capabilities.
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
        
        # Count vector (new format: one JSON per entity)
        if VECTOR_DIR.exists():
            report["vector_count"] = len(list(VECTOR_DIR.glob("*.json")))
        
        # Count graph
        if GRAPH_DIR.exists():
            report["graph_count"] = len(list(GRAPH_DIR.glob("*.json")))
        
        # Check consistency: find entities missing in some layers
        all_ids = set()
        for d in [self.struct_dir, VECTOR_DIR, GRAPH_DIR]:
            if d.exists():
                all_ids.update(f.stem for f in d.glob("*.json"))
        
        for eid in all_ids:
            struct_exists = (self.struct_dir / f"{eid}.json").exists()
            vector_exists = (VECTOR_DIR / f"{eid}.json").exists()
            graph_exists = (GRAPH_DIR / f"{eid}.json").exists()
            
            if not vector_exists:
                report["missing_in_vector"].append(eid)
            if not graph_exists:
                report["missing_in_graph"].append(eid)
            if not (struct_exists and vector_exists and graph_exists):
                report["inconsistent"].append(eid)
        
        return report
    
    def repair(self) -> Tuple[int, int]:
        """
        P4: Attempt to repair inconsistencies using transaction semantics.
        """
        report = self.verify()
        repaired = 0
        failed = 0
        
        for eid in report.get("inconsistent", []):
            # Try to reconstruct missing layers from structured (source of truth)
            struct_file = self.struct_dir / f"{eid}.json"
            if not struct_file.exists():
                failed += 1
                continue
            
            try:
                with open(struct_file) as f:
                    data = json.load(f)
                
                # Re-write to missing layers using transaction
                payload = {"entity_id": eid, "memory": data}
                
                with self._tx_manager.begin("repair", payload) as tx:
                    if not (VECTOR_DIR / f"{eid}.json").exists():
                        self._tx_manager.write_vector({
                            "entity_id": eid,
                            "embedding_text": f"{data.get('subject', '')} {data.get('action', '')}"
                        })
                    if not (GRAPH_DIR / f"{eid}.json").exists():
                        self._tx_manager.write_graph({
                            "entity_id": eid,
                            "subject": data.get("subject", ""),
                            "entities": self._extract_entities(data.get("subject", ""))
                        })
                
                repaired += 1
            except Exception as e:
                print(f"Failed to repair {eid}: {e}")
                failed += 1
        
        return repaired, failed
    
    def _extract_entities(self, text: str) -> List[str]:
        """Simple entity extraction from text."""
        entities = []
        for part in text.replace("/", " ").replace("-", " ").split():
            part = part.strip(".,:;()[]{}")
            if part and len(part) > 1 and part[0].isupper():
                entities.append(part)
        return list(set(entities))[:10]
    
    def _extract_relations(self, memory: Dict) -> List[Dict]:
        """Extract relations from memory."""
        relations = []
        mem_type = memory.get("type", "")
        
        if mem_type == "decision":
            relations.append({"type": "causes", "from": memory.get("subject"), "to": "outcome"})
        elif mem_type == "lesson":
            relations.append({"type": "learned_from", "from": memory.get("subject"),
                            "to": memory.get("action", "")[:50]})
        
        return relations


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