# OCM Sup v2.4 — P3 Reliability Layer
## Full Specification

**Version:** 2.4
**Date:** 2026-04-28
**Author:** 阿星 (OCM Sup System)

---

## 🎯 Position

| Layer | Component | Purpose |
|-------|-----------|---------|
| Foundation | **Transaction System** | Atomicity guarantee — all writes succeed or all fail |
| Core Intelligence | **Semantic Contradiction Engine** | Detect implicit semantic conflicts |
| Core Intelligence | **Memory Usage Tracker** | Know if agent actually uses memory |
| Execution | **Pruning Policy** | Multi-factor scoring, real deletion |

**Execution order:** Transaction → Contradiction → Usage → Pruning

---

## 📁 File Structure

```
OCM-Sup/
├── p3_reliability/
│   ├── contradiction/
│   │   ├── __init__.py
│   │   ├── detector.py         # Core detection engine
│   │   ├── embedding_store.py  # Embedding cache
│   │   ├── sentiment.py        # Heuristic sentiment
│   │   └── llm_judge.py        # LLM integration
│   ├── transaction/
│   │   ├── __init__.py
│   │   ├── tx_manager.py       # Transaction lifecycle
│   │   ├── tx_log.py           # Transaction records
│   │   └── reconciler.py       # Background reconciliation
│   ├── pruning/
│   │   ├── __init__.py
│   │   ├── scorer.py           # Multi-factor scoring
│   │   ├── policy.py           # Threshold + scheduling
│   │   └── archiver.py         # Pruned fact recovery
│   ├── usage/
│   │   ├── __init__.py
│   │   ├── tracker.py          # Usage event tracking
│   │   ├── metrics.py          # Stats + reporting
│   │   └── binding.py          # Pattern → fact binding
│   └── api/
│       ├── __init__.py
│       └── p3_routes.py        # HTTP API endpoints
├── spec/
│   └── P3_RELIABILITY_LAYER.md # This spec
└── tests/
    ├── test_contradiction.py
    ├── test_transaction.py
    ├── test_pruning.py
    └── test_usage_tracker.py
```

---

## 1️⃣ Semantic Contradiction Engine

### Problem
字面duplicate/contradiction可以detect，但「喜歡快節奏」vs「偏好穩定環境」呢類semantic conflict detect唔到。

### Architecture

```
Input Fact
    ↓
Embedding (nomic-embed-text)
    ↓
Similarity Scan ←→ existing fact embeddings
    ↓
Heuristic Filter (similarity > 0.85 AND intent_opposite?)
    ↓
LLM Judge (mini or balanced)
    ↓
┌─ No contradiction → proceed
└─ Contradiction found → flag + record
```

### Data Model

```python
class Fact:
    id: str
    content: str
    embedding: list[float]      # 1536-dim nomic
    sentiment_sign: int          # +1 (positive/active) / -1 (negative/stable)
    contradiction_flags: list[str]  # [fact_id, ...]
    contradiction_score: float   # 0.0 - 1.0
```

### Sentiment Heuristic

```python
POSITIVE_MARKERS = ["快", "active", "dynamic", "新", "變", "high-speed", ...]
NEGATIVE_MARKERS = ["慢", "stable", "steady", "穩", "守", "固定", ...]

def get_sentiment_sign(text: str) -> int:
    pos = sum(1 for m in POSITIVE_MARKERS if m in text.lower())
    neg = sum(1 for m in NEGATIVE_MARKERS if m in text.lower())
    return 1 if pos > neg else -1
```

### Detection Pipeline

1. **Embed new fact** → get 1536-dim nomic embedding
2. **Compare with all existing** → cosine similarity
3. **Pre-filter:** if similarity < 0.85 → skip
4. **Sentiment check:** if same sign → skip (no contradiction possible)
5. **LLM judgment:** if opposite sign AND similarity > threshold → call LLM
6. **Store result:** if LLM says CONFLICT → record contradiction

### LLM Judgment Prompt

```
You are a concise conflict detector. Judge if two facts represent conflicting preferences or beliefs.

Fact A: {fact_a}
Fact B: {fact_b}

Respond with exactly one line:
- If CONFLICT: "CONFLICT|{confidence}|{explanation}"
  where confidence is 0.0-1.0, explanation is 1 sentence max
- If NO_CONFLICT: "NO_CONFLICT"
```

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `detect_contradiction(fact_id)` | Check single fact |
| `detect_all_contradictions()` | Full scan |
| `resolve_contradiction(fact_a, fact_b, decision)` | Manual resolution |
| `get_contradiction_report()` | Summary stats |
| `calibrate_threshold(sample_size)` | Self-tune threshold |

### Calibration
- Threshold: start at 0.85 similarity
- Adjust based on precision over first 500 checks
- If FP > 20%, raise threshold to 0.88

---

## 2️⃣ Transaction System

### Problem
依家三層寫入（structured/vector/graph）係pseudo-atomic——如果vector fail但structured已寫入，個state就corrupted。

### Architecture

```
BEGIN TRANSACTION
  → Create TX record (status=pending, rollback_data=previous_state)
  → Write structured (pending)
  → Write vector (pending)
  → Write graph (pending)
  → If ALL success → COMMIT (status=committed, delete rollback_data)
  → If ANY fail → ROLLBACK (restore previous_state, status=failed)
COMMIT
```

### Data Model

```python
class Transaction:
    id: str                    # uuid
    created_at: datetime
    status: str                # "pending" | "committed" | "failed" | "rolled_back"
    operation: str             # "write_fact" | "delete_fact" | "update_fact"
    payload: dict              # the fact data being written
    rollback_data: dict | None # previous state for rollback
    committed_at: datetime | None
    failed_at: datetime | None
```

### Transaction Log

Location: `~/.openclaw/ocm-sup/transactions/transaction_log.jsonl`

Format: JSONL (one transaction per line)
- All writes are durable (append-only)
- On restart, pending transactions are reconciled

### Rollback Logic

```python
def rollback(tx: Transaction):
    if tx.rollback_data:
        # Restore previous state
        restore_structured(tx.rollback_data["structured"])
        restore_vector(tx.rollback_data["vector"])
        restore_graph(tx.rollback_data["graph"])
    tx.status = "rolled_back"
    log(f"Rolled back transaction {tx.id}")
```

### Reconciliation Job

Runs every 5 minutes:
1. Find stale pending transactions (>5 min old)
2. Check layer states
3. Complete if all written, rollback if partial

### Consistency Guarantees
- **All-or-nothing:** partial writes never persist
- **Durability:** committed transactions survive restart
- **Serial ordering:** transactions processed sequentially

---

## 3️⃣ Pruning Policy

### Problem
依家係scan但唔prune，memory無限膨脹。

### Multi-Factor Scoring

```python
def compute_prune_score(fact: dict) -> float:
    # Low access penalty
    access_factor = 1 / math.sqrt(fact.access_count + 1)

    # Low importance penalty
    importance_map = {"HIGH": 0.0, "MEDIUM": 0.3, "LOW": 0.6}
    importance_factor = importance_map.get(fact.importance, 0.5)

    # Age factor (logarithmic)
    age_days = (now - fact.created_at).days
    age_factor = min(math.log(age_days + 1) / 10, 1.0)

    return access_factor * 0.4 + importance_factor * 0.3 + age_factor * 0.3
```

**Threshold: 0.7** (above = prune)

### Archive Before Delete

All pruned facts go to `~/.openclaw/ocm-sup/archive/` with 30-day TTL.

```python
def restore(fact_id: str) -> Optional[dict]:
    # Search archive, check TTL, restore if valid
```

### Schedule
- Daily at 03:00 HKT (off-peak)
- Manual trigger: `prune_now(dry_run=False)`

### Recovery
- Pruned facts stored in `archive/` (30-day TTL)
- `restore_fact(fact_id)` recovers if needed

---

## 4️⃣ Memory Usage Tracker

### Problem
Agent retrieve到memory但唔使用——我哋完全冇visibility。

### Tracking Events

```python
class UsageTracker:
    def on_retrieve(self, fact_id: str, context: str = ""):
        # Record: fact retrieved

    def on_output(self, fact_id: str):
        # Record: fact appeared in agent output

    def on_agent_decision(self, pattern: str, facts_used: list[str]):
        # Record: agent decision influenced by memory
```

### Usage Metrics

```python
def get_utilization_rate() -> float:
    # Fraction of facts that have been used in output

def get_ignored_facts() -> list[str]:
    # Facts retrieved >10x but never used

def get_alerts() -> list[dict]:
    # Generate usage-related alerts
```

### Pattern Binding

```python
CONTEXT_HISTORY = []  # rolling window

def suggest_boost(fact_id: str, current_context: str) -> bool:
    # If similar context recurred before and fact was used → boost
```

### Schedule
- Daily at 04:00 HKT (after pruning)
- Manual trigger available

---

## 📊 Expected Outcomes

| Metric | Current | After P3 |
|--------|---------|----------|
| Semantic contradiction detection | ❌ 0% | ✅ 85%+ |
| Transaction atomicity | Pseudo-atomic | ✅ Full atomic |
| Memory pruning | ❌ None | ✅ Daily execution |
| Agent memory usage visibility | ❌ None | ✅ Full tracking |
| Production readiness | ~65% | ✅ 90%+ |

---

## 🔧 Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| `contradiction/detector.py` | ✅ Skeleton | Core detection engine |
| `contradiction/embedding_store.py` | ✅ Skeleton | Embedding cache |
| `contradiction/sentiment.py` | ✅ Skeleton | Heuristic sentiment |
| `contradiction/llm_judge.py` | ✅ Skeleton | LLM integration |
| `transaction/tx_manager.py` | ✅ Skeleton | Transaction lifecycle |
| `transaction/tx_log.py` | ✅ Skeleton | Transaction records |
| `transaction/reconciler.py` | ✅ Skeleton | Background reconciliation |
| `pruning/scorer.py` | ✅ Skeleton | Multi-factor scoring |
| `pruning/policy.py` | ✅ Skeleton | Threshold + scheduling |
| `pruning/archiver.py` | ✅ Skeleton | Pruned fact recovery |
| `usage/tracker.py` | ✅ Skeleton | Usage event tracking |
| `usage/metrics.py` | ✅ Skeleton | Stats + reporting |
| `usage/binding.py` | ✅ Skeleton | Pattern → fact binding |
| `api/p3_routes.py` | ✅ Skeleton | HTTP API endpoints |

---

## 📝 Next Steps (P4+)

1. **Integrate with OCM Sup core** — connect P3 to existing retrieval pipeline
2. **Real LLM call integration** — replace placeholder in `llm_judge.py`
3. **Cross-encoder normalization** — calibrate score distribution
4. **Reflection memory** — self-correct based on contradictions
5. **Agent memory binding** — ensure Hermes uses memory in decisions

---

_Last updated: 2026-04-28 15:42 HKT_