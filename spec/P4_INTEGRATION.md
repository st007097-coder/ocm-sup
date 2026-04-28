# OCM Sup v2.4 — P4 Integration
## Integrate P3 Reliability Layer into OCM Sup Core

**Version:** 2.4
**Date:** 2026-04-28
**Author:** 阿星

---

## 🎯 Position

P3 built 4 reliability components as isolated modules.
P4 integrates them into OCM Sup's actual memory pipeline.

```
Before P4:
┌─────────────────┐     ┌──────────────────┐
│ memory_write_    │────▶│  pseudo-atomic    │
│ gate.py         │     │  memory_tx_sync   │
└─────────────────┘     └──────────────────┘
         │                        │
         ▼                        ▼
   (no contradiction      (writes to workspace/
    detection)             memory/ but not atomic)

After P4:
┌─────────────────────────────────────────────────────┐
│                  Memory Pipeline                     │
│                                                      │
│  ┌─────────────────┐    ┌───────────────────────┐  │
│  │ memory_write_    │───▶│ ContradictionDetector │  │
│  │ gate.py         │    │ (P3)                  │  │
│  └─────────────────┘    └───────────────────────┘  │
│          │                        │                 │
│          ▼                        ▼                 │
│  ┌─────────────────────────────────────────────┐   │
│  │ TransactionManager (P3)                      │   │
│  │ begin/commit/rollback atomic semantics       │   │
│  └─────────────────────────────────────────────┘   │
│          │                                          │
│          ▼                                          │
│  ┌─────────────────────────────────────────────┐   │
│  │ Storage Layers (structured/vector/graph)     │   │
│  └─────────────────────────────────────────────┘   │
│          │                                          │
│          ▼                                          │
│  ┌─────────────────────────────────────────────┐   │
│  │ UsageTracker (P3) - track retrieval events   │   │
│  └─────────────────────────────────────────────┘   │
│                                                      │
│  ┌─────────────────────────────────────────────┐   │
│  │ PruningPolicy (P3) - scheduled cleanup       │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## 📁 Integration Points

### 1. memory_write_gate.py — Add Contradiction Detection

**File:** `/root/.openclaw/workspace/OCM-Sup/scripts/memory_write_gate.py`

**Changes:**
```python
# Add to imports
from p3_reliability.contradiction import ContradictionDetector
from p3_reliability.usage import UsageTracker

class MemoryWriteGate:
    def __init__(self, ...):
        # Existing init code...
        self._contradiction_detector = ContradictionDetector()
        self._usage_tracker = UsageTracker()
    
    def validate(self, memory: Dict) -> Tuple[bool, str, Optional[Dict]]:
        # Stage 0: Contradiction check (NEW)
        contradiction = self._check_contradiction(memory)
        if contradiction.found:
            # Log but don't block (P4: configurable blocking)
            self._log_contradiction_warning(contradiction)
        
        # Existing validation stages 1-4...
    
    def _check_contradiction(self, memory: Dict):
        # Build fact_text from subject + action
        fact_text = f"{memory.get('subject')} {memory.get('action')}"
        
        # Load existing facts from memory cache
        all_facts = {m.get('id'): f"{m.get('subject')} {m.get('action')}" 
                     for m in self._memory_cache if m.get('id')}
        
        # Get or generate fact_id
        fact_id = memory.get('id') or self._generate_id(memory)
        
        # Check for contradictions
        results = self._contradiction_detector.check_fact(
            fact_id, fact_text, all_facts
        )
        return results
```

### 2. memory_tx_sync.py — Replace with TransactionManager

**File:** `/root/.openclaw/workspace/OCM-Sup/scripts/memory_tx_sync.py`

**Changes:**
```python
# Replace existing class with:
from p3_reliability.transaction import TransactionManager

class MemoryTransactionSync:
    def __init__(self, ...):
        self._tx_manager = TransactionManager()
    
    def write(self, memory: Dict) -> Tuple[bool, str]:
        # Generate entity_id
        entity_id = memory.get("id") or self._id(memory)
        payload = {"entity_id": entity_id, "memory": memory}
        
        try:
            with self._tx_manager.begin("write_fact", payload) as tx:
                # Write to structured
                struct_data = {
                    "entity_id": entity_id,
                    "type": memory.get("type"),
                    "subject": memory.get("subject"),
                    "action": memory.get("action"),
                    "metadata": {k: v for k, v in memory.items() 
                                 if k not in ["type", "subject", "action", "id"]}
                }
                self._tx_manager.write_structured(struct_data)
                
                # Write to vector (embedding text)
                self._tx_manager.write_vector({
                    "entity_id": entity_id,
                    "embedding_text": f"{memory.get('subject')} {memory.get('action')}"
                })
                
                # Write to graph (entities + relations)
                self._tx_manager.write_graph({
                    "entity_id": entity_id,
                    "subject": memory.get("subject"),
                    "entities": self._extract_entities(memory.get("subject", "")),
                    "relations": self._extract_relations(memory)
                })
            
            # Transaction committed automatically
            return True, f"COMMITTED: {entity_id}"
            
        except Exception as e:
            # Transaction rolled back automatically
            return False, f"FAILED: {str(e)}"
```

### 3. Usage Tracking — Integration Points

**When to track:**
- `on_retrieve(fact_id, context)` — called when memory is retrieved in search
- `on_output(fact_id)` — called when fact appears in agent output
- `on_agent_decision(pattern, facts_used)` — called when agent makes decision

**Where to integrate:**
- `triple_stream_search.py` — add `usage_tracker.on_retrieve()` for each returned fact
- Agent output generation — add `usage_tracker.on_output()` for referenced facts

### 4. Pruning Integration

**Current state:** P3 `PruningPolicy` expects entities in `~/.openclaw/ocm-sup/{structured,embeddings,graph}/`

**Challenge:** OCM Sup uses `/root/.openclaw/workspace/memory/` as primary store

**Solution (P4):**
- Option A: Migrate to P3 storage paths (clean but disruptive)
- Option B: Add adapter layer to prune from current paths (safer)
- **P4 Decision:** Option B — write adapters

**Files to create:**
- `p3_reliability/pruning/adapters.py` — adapters for different storage formats

---

## 📊 Integration Status

| Component | Integration Point | Status | Notes |
|-----------|-------------------|--------|-------|
| ContradictionDetector | memory_write_gate.py | ✅ DONE | Stage 0 contradiction check before validation |
| TransactionManager | memory_tx_sync.py | ✅ DONE | Real atomic begin/commit/rollback |
| UsageTracker | memory retrieval points | 🔴 PHASE 2 | Agent-level tracking (future work) |
| PruningPolicy | storage adapters | 🔴 PHASE 2 | Scheduled cleanup (future work) |

### ✅ P4 Phase 1 Completed (2026-04-28)
- `memory_write_gate.py` — Added P3 imports, Stage 0 contradiction check
- `memory_tx_sync.py` — Replaced pseudo-atomic with TransactionManager, new P3 storage paths
- Verified: Transaction write commits to all 3 layers (structured/vector/graph)
- Verified: ContradictionDetector initialized and connected
- Verified: UsageTracker initialized and connected

### 🔴 P4 Phase 2 (Future)
- UsageTracker: Integrate with agent memory retrieval (not wiki search)
- PruningPolicy: Create storage adapters for existing memory format

---

## 🧪 Test Plan

1. **Contradiction integration:**
   - Write a fact, verify it checks against existing
   - Write contradicting fact, verify detection

2. **Transaction integration:**
   - Simulate layer failure, verify rollback
   - Verify committed data persists

3. **Usage tracking:**
   - Run search, verify on_retrieve called
   - Check usage_tracking.json updated

4. **Pruning integration:**
   - Dry-run pruning, verify eligible facts identified
   - Execute pruning, verify archive created

---

_Last updated: 2026-04-28 17:45 HKT_
