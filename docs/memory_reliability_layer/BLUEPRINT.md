# OCM Sup v2.6 — Memory Reliability Layer
## Blueprint: 融合用户建議 + P3 可靠性

**Version:** 0.1 (Draft)
**Date:** 2026-04-28
**Author:** 阿星 (with 期哥 guidance)
**Status:** 🟡 Draft - Pending Review

---

## 🎯 目標

建立一個 **輕量級、生產級** 嘅 memory reliability layer：
- 簡潔架構（5個核心模組）
- 生產級可靠性（Transaction rollback、crash recovery）
- 輕量級（無 heavy dependencies）
- 易維護、易測試

**核心原則：**
1. Simplicity first（用户建議）
2. Reliability through transactions（P3 概念）
3. Production-ready without complexity

---

## 📁 新目錄結構

```
OCM-Sup/
├── memory_reliability_layer/        # 新！Clean structure
│   ├── __init__.py
│   ├── tx_manager.py               # Transaction manager + rollback
│   ├── contradiction.py            # Sentence transformer based
│   ├── usage_tracker.py           # Simple count-based
│   ├── health_metrics.py          # Health indicators
│   ├── adaptive_pruning.py        # Score-based pruning + archiver
│   └── config.py                   # Configuration
│
├── p3_reliability/                 # 舊結構 → 保留但標記為 deprecated
│   └── (mark as legacy, will be phased out)
│
├── scripts/
│   ├── memory_tx_sync.py          # P4 integration point
│   ├── memory_write_gate.py        # P4 integration point
│   └── memory_retriever.py        # P4 integration point
│
├── tests/
│   ├── test_memory_reliability.py # 新測試
│   └── test_p3_full.py            # 舊測試（保留）
│
└── docs/
    └── memory_reliability_layer/   # 文件
```

---

## 🔧 各模組詳細設計

### 1️⃣ tx_manager.py — Transaction Manager + Rollback

**職責：** 管理 memory write transactions，確保 atomicity + crash recovery

**核心 API：**
```python
class TransactionManager:
    def begin(self, operation: str, payload: dict) -> Transaction
    def write_structured(self, tx: Transaction, data: dict)
    def write_vector(self, tx: Transaction, data: dict)
    def write_graph(self, tx: Transaction, data: dict)
    def commit(self, tx: Transaction) -> bool
    def rollback(self, tx: Transaction)
    def recover_pending()
```

**實現要點：**
- 使用 context manager (`with tx.begin(...) as tx:`)
- 失敗時自動 rollback
- Pending transactions 存於 `memory/transactions/`
- `recover_pending()` 在 startup 時自動調用

**用戶核心建議（已採納）：**
```python
def create_tx(memory):
    tx_id = str(uuid.uuid4())
    tx = {
        "tx_id": tx_id,
        "status": "pending",
        "steps": {"structured": False, "vector": False, "graph": False},
        "memory": memory,
        "timestamp": time.time()
    }
    os.makedirs(TX_DIR, exist_ok=True)
    with open(_tx_path(tx_id), "w") as f:
        json.dump(tx, f)
    return tx
```

**P3 增強（已加入）：**
- Automatic rollback on exception in context manager
- Recovery of pending transactions on restart
- Step-level tracking for partial commit detection

---

### 2️⃣ contradiction.py — Semantic Contradiction Detection

**職責：** 檢測 memory facts 之間的語義衝突

**核心 API：**
```python
class ContradictionEngine:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2")
    def check_fact(self, fact_id: str, fact_text: str, all_facts: dict) -> ContradictionResult
    def detect_candidates(self) -> list[tuple]
    def run_full_scan(self) -> list[ContradictionResult]
```

**實現要點：**
- 使用 Sentence Transformers 做 embedding similarity
- Similarity threshold: 0.75（可配置）
- 檢測「negation patterns」作爲矛盾信號
- 結果存於 `memory/contradictions.jsonl`

**用戶核心建議（已採納）：**
```python
def simple_contradiction(a, b):
    neg_words = ["not", "never", "no"]
    if any(w in a["text"] for w in neg_words) != any(w in b["text"] for w in neg_words):
        return True
    return False
```

**vs P3 舊實現：**
| 方面 | P3 舊版 | 新版 |
|------|---------|------|
| Detection method | LLM judge (slow, expensive) | Sentence similarity (fast) |
| Threshold | Configurable but complex | Simple 0.75 |
| Negation heuristic | Via sentiment analysis | Direct pattern match |
| Dependencies | OpenAI/LLM | sentence-transformers only |

---

### 3️⃣ usage_tracker.py — Usage Tracking

**職責：** 追蹤每個 memory fact 的使用情況

**核心 API：**
```python
class UsageTracker:
    def on_retrieve(self, fact_id: str, context: str = "")
    def on_output(self, fact_id: str)
    def on_agent_decision(self, pattern: str, facts_used: list[str])
    def get_stats(self, fact_id: str) -> UsageStats
    def get_ignored_facts(self, min_retrieves: int = 5, usage_threshold: float = 0.1) -> list[str]
    def get_utilization_rate(self) -> float
```

**實現要點：**
- Simple count-based tracking（用户建議）
- Storage: `memory/usage_stats.json`
- 追蹤：retrieve_count, used_in_output, last_retrieved
- 提供 utilization rate 計算

**用戶核心建議（已採納）：**
```python
def track(memory_ids):
    data = load()
    now = time.time()
    for mid in memory_ids:
        if mid not in data:
            data[mid] = {"count": 0, "last": now}
        data[mid]["count"] += 1
        data[mid]["last"] = now
    save(data)
```

**vs P3 舊實現：**
- 简化为单文件，无多级子模块
- 保留核心 API（on_retrieve, on_output, get_stats）
- 简化数据结构（去掉 decision_influenced_count 等冗余字段）

---

### 4️⃣ health_metrics.py — Health Indicators

**職責：** 計算和報告 memory system health

**核心 API：**
```python
class HealthMetrics:
    def compute(self) -> HealthReport
    def get_weekly_report(self) -> HealthReport
    def save_report(self, report: HealthReport)
```

**實現要點：**
- 計算 multiple metrics
- 輸出 `memory/reports/weekly_report.json`
- Metrics include:
  - contradiction_rate
  - duplicate_rate
  - unused_rate
  - freshness_score
  - overall health score

**用戶核心建議（已採納）：**
```python
def compute():
    report = {
        "duplicate_rate": 0.0,
        "contradiction_rate": 0.0,
        "unused_rate": 0.0,
        "freshness": 1.0
    }
    health = (
        (1-report["duplicate_rate"])*0.2 +
        (1-report["contradiction_rate"])*0.3 +
        (1-report["unused_rate"])*0.2 +
        report["freshness"]*0.3
    )
```

**增強（相比用戶建議）：**
- 加入 contradiction_rate 計算（調用 contradiction.py）
- 加入 unused_rate 計算（調用 usage_tracker.py）
- Weekly report 持久化

---

### 5️⃣ adaptive_pruning.py — Adaptive Pruning + Archiver

**職責：** 自動清理低價值 memory facts

**核心 API：**
```python
class AdaptivePruning:
    def __init__(self, threshold: float = 0.7)
    def score(self, fact: dict, usage: dict) -> float
    def should_prune(self, fact: dict, usage: dict) -> bool
    def execute(self, dry_run: bool = True) -> PruningResult
    def archive(self, fact_id: str, fact_text: str, metadata: dict)
```

**實現要點：**
- Score formula（已修復用戶建議的問題）：
```python
def score(fact, usage):
    age = (time.time() - fact["timestamp"]) / 86400
    access = usage.get(fact["id"], {}).get("count", 0)
    importance = fact.get("importance", 0.5)  # Default 0.5

    # 修復：importance weight 提升到 0.4（原來 0.3）
    # 同時加入 minimum access bonus
    access_factor = 1 / (1 + access)  # 低 access = high score
    age_factor = min(age / 30, 1.0)   # 30日內線性增長
    importance_factor = (1 - importance) * 0.4  # 低 importance = high score

    return (
        importance_factor +
        age_factor * 0.3 +
        access_factor * 0.3
    )
```

**用戶核心建議（已採納 + 修復）：**
- 採用 `prune()` 函數結構
- 修復 score formula：
  - Importance weight 提升（0.3 → 0.4）
  - 加入 access bonus 避免高重要性fact被刪
  - 30日 half-life 合理

**vs P3 舊實現：**
| 方面 | P3 舊版 | 新版 |
|------|---------|------|
| Files | policy.py + scorer.py + archiver.py | 合併為 1 個檔案 |
| Score formula | 複雜多重加權 | 簡化但修復 |
| Config | 多參數 | 單一 threshold |

---

### 6️⃣ config.py — Configuration

**職責：** 集中管理所有配置

**內容：**
```python
TX_DIR = "memory/transactions"
STORAGE_DIR = "memory/structured"
ARCHIVE_DIR = "memory/archive"
USAGE_FILE = "memory/usage_stats.json"

# Contradiction
CONTRADICTION_MODEL = "all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = 0.75

# Pruning
PRUNE_THRESHOLD = 0.7
PRUNE_MAX_PER_RUN = 50
ARCHIVE_RETENTION_DAYS = 90

# Health
HEALTH_REPORT_PATH = "memory/reports/weekly_report.json"
```

---

## 🔌 P4 Integration Points

### Patch 1: memory_tx_sync.py
```python
# 舊
from p3_reliability.transaction import TransactionManager

# 新
from memory_reliability_layer.tx_manager import TransactionManager

# 用法不變
tx_manager = TransactionManager()
```

### Patch 2: memory_retriever.py
```python
# 舊
from p3_reliability.usage import UsageTracker

# 新
from memory_reliability_layer.usage_tracker import UsageTracker
```

### Patch 3: consolidation-loop.sh
```bash
# 舊
python p3_reliability/contradiction/run_detector.py

# 新
python memory_reliability_layer/contradiction.py
```

---

## 📋 Migration Plan

### Phase 1: Create new modules
- [ ] Create `memory_reliability_layer/` directory
- [ ] Implement `config.py`
- [ ] Implement `tx_manager.py` (with rollback)
- [ ] Implement `contradiction.py`
- [ ] Implement `usage_tracker.py`
- [ ] Implement `health_metrics.py`
- [ ] Implement `adaptive_pruning.py`

### Phase 2: Update integration points
- [ ] Update `memory_tx_sync.py` to use new tx_manager
- [ ] Update `memory_retriever.py` to use new usage_tracker
- [ ] Update `memory_write_gate.py` to use new contradiction

### Phase 3: Test & Verify
- [ ] Run existing tests (should pass)
- [ ] Add new tests for memory_reliability_layer
- [ ] Verify transaction rollback works
- [ ] Verify contradiction detection works
- [ ] Verify pruning executes correctly

### Phase 4: Deprecate old P3
- [ ] Mark `p3_reliability/` as deprecated in README
- [ ] Keep for backward reference
- [ ] Eventually remove in future version

---

## 🧪 Test Plan

```bash
# Test each module independently
python -m pytest tests/test_memory_reliability.py -v

# Key tests:
# 1. Transaction commit & rollback
# 2. Contradiction detection accuracy
# 3. Usage tracking counts
# 4. Pruning score calculation
# 5. Health metrics computation
```

---

## 📊 預期效果

| 指標 | v2.5 (Before) | v2.6 (After) |
|------|--------------|--------------|
| Modules | 12 files (P3) | 5 files |
| Dependencies | Heavy (LLM, etc.) | Light (sentence-transformers only) |
| Transaction safety | ✅ | ✅ |
| Crash recovery | ⚠️ Partial | ✅ Full |
| Contradiction detection | LLM-based | Similarity-based |
| Setup complexity | High | Low |

---

## ⏱️ 預計時間

| Phase | 時間 |
|-------|------|
| Phase 1: Create modules | ~1-2 hours |
| Phase 2: Update integration | ~30 min |
| Phase 3: Test & verify | ~30 min |
| **Total** | **~2-3 hours** |

---

## 🤔 Open Questions

1. **Backward compatibility:** Should we keep P3 as deprecated module?
2. **LLM judge:** Should we keep LLM-based contradiction as optional upgrade?
3. **Async support:** Do we need async queue for high throughput? (User mentioned this as future option)

---

_Last updated: 2026-04-28 18:59 HKT_
