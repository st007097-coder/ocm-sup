# OCM Sup

> 🧠 智能記憶管理系統 — 為 24/7 AI 助手而生

[![Status](https://img.shields.io/badge/status-production_ready-green.svg)](#)
[![Version](https://img.shields.io/badge/OCM%20Sup-v3-blue.svg)](#)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](#)

**OCM Sup = OpenClaw Memory Supervisor**

為 AI 助手構建嘅生產級記憶管理系統，大幅降低長期運行嘅 token 成本，令 24/7 主動式 AI 助手成為可能。

---

## ✨ 核心功能

### v2.6 - Memory Reliability Layer（核心可靠性）

| 功能 | 描述 |
|------|------|
| 🔄 **Transaction + Rollback** | Atomic writes + crash recovery，生產級可靠性 |
| ⚠️ **Contradiction Detection** | Sentence transformer 矛盾檢測 |
| 📊 **Usage Tracking** | 追蹤邊個事實被使用 |
| 🧹 **Adaptive Pruning** | Score-based 自動清理低價值記憶 |
| 📈 **Health Metrics** | 健康指標可視化監控 |

### v3 - Hybrid Layer（性能優化）

| 功能 | 描述 |
|------|------|
| 🔒 **Idempotency Guard** | 防止重複寫入，確保 data consistency |
| ⚡ **Vector Batching** | Batch embeddings（8條/批），大幅降低 latency |
| 🗃️ **Embedding Cache** | Cache embeddings，相同句子唔再 embed |
| 🔁 **Async Post-processing** | Background 執行 contradiction/pruning/metrics |
| ↩️ **Retry Utility** | Exponential backoff retry，確保任務完成 |

---

## 🏗️ 系統架構

```
┌─────────────────────────────────────────────────────────┐
│                    User Query                             │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Memory Reliability Layer (v2.6)              │
│  Transaction Manager + Contradiction + Usage + Pruning  │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                Hybrid Layer (v3)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ Idempotency │  │   Vector    │  │  Post-process   │  │
│  │   Guard     │→ │  Batching   │→ │  (async)        │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 目錄結構

```
OCM-Sup/
├── memory_reliability_layer/     # v2.6 核心記憶可靠性
│   ├── tx_manager.py             # Atomic transactions
│   ├── contradiction.py          # 矛盾檢測
│   ├── usage_tracker.py         # 使用追蹤
│   ├── adaptive_pruning.py      # 智能清理
│   └── health_metrics.py        # 健康監控
├── hybrid_layer/                  # v3 性能優化
│   ├── idempotency_guard.py     # 防止重複寫入
│   ├── async_runner.py          # Background thread
│   ├── retry_utils.py          # Retry with backoff
│   ├── vector_batcher.py        # Batch embeddings
│   ├── embedding_cache.py       # Cache embeddings
│   └── postprocess_worker.py   # Async post-processing
├── scripts/                      # 記憶管理腳本
├── tests/                        # 測試
│   └── comprehensive_test.py   # 全面測試 + Benchmark
└── docs/                        # 文檔
```

---

## 🚀 快速開始

```bash
# 全面測試 + Benchmark
python tests/comprehensive_test.py

# 搜索記憶
python scripts/triple_stream_search.py --query "古洞站"

# 寫入新記憶（自動 idempotency + batching）
python scripts/memory_tx_sync.py --action write --memory data.json

# 健康檢查
python scripts/memory_pruning_adapter.py --status
```

---

## 📊 性能指標

| 指標 | 數值 |
|------|------|
| **Write Latency** | ~229ms avg (with batching) |
| **Cache Hit** | 相同句子唔再 embed |
| **Health Score** | >79% |
| **Idempotency** | ✅ 防止重複寫入 |
| **Batch Size** | 8 items per batch |
| **Triple-Stream 準確率** | **90.6%** (vs 31.2% baseline) |
| **Proactive Discovery** | **~1 秒** (275x提速) |

---

## 📚 文檔

| 文檔 | 描述 |
|------|------|
| [README.md](README.md) | 📖 主要文檔 |
| [COMPREHENSIVE_SUMMARY.md](docs/COMPREHENSIVE_SUMMARY.md) | 📋 全面性總結 |
| [TECHNICAL.md](TECHNICAL.md) | 🔬 技術原理 |
| [CHANGELOG.md](CHANGELOG.md) | 📅 進化歷史 |
| [TEST-REPORT.md](TEST-REPORT.md) | 🧪 測試報告 |

---

## 🎯 與 OpenClaw 內建記憶對比

| 方面 | OpenClaw 內建 | OCM Sup v3 |
|------|---------------|------------|
| 搜索 | 單一 semantic | Triple-Stream ✅ |
| 可靠性 | Session hooks | Transaction + Rollback ✅ |
| 衝突檢測 | ❌ | ✅ |
| 記憶清理 | Dreaming/Promotion | Adaptive Score + Pruning ✅ |
| 主動發現 | 被動 trigger | Proactive ✅ |
| Idempotency | ❌ | ✅ |
| Vector Batching | ❌ | ✅ |
| Async Post-processing | ❌ | ✅ |

---

## 🧪 測試結果（最後更新：2026-04-29）

```
============================================================
OCM Sup v3 - Comprehensive System Test
============================================================

TEST 1: Memory Reliability Layer (v2.6)
  ✓ TransactionManager: PASS
  ✓ UsageTracker: PASS
  ✓ HealthMetrics: PASS (99.97%)

TEST 2: Hybrid Layer (v3) - Reliability
  ✓ Idempotency Guard: PASS
  ✓ Retry Utility: PASS

TEST 3: Integration - memory_tx_sync.py
  ✓ Idempotency in write: PASS
  ✓ Vector Batching: PASS (15 writes / 3.4s)

TEST 4: Post-processing
  ✓ Health score: 79.98%
  ✓ Total facts: 33
  ✓ Post-processing: PASS

ALL TESTS PASSED ✓
```

---

## 📜 License

MIT

---

_Last updated: 2026-04-29 | v3_