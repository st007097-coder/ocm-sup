# OCM Sup

> 🧠 Intelligent Memory Management System — Built for 24/7 AI Assistants

[![Status](https://img.shields.io/badge/status-production_ready-green.svg)](#)
[![Version](https://img.shields.io/badge/OCM%20Sup-v2.6-blue.svg)](#)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](#)

**OCM Sup = OpenClaw Memory Supervisor**

A production-grade memory management system for AI assistants, drastically reducing token costs for always-on operation and making 24/7 proactive AI practical.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🔍 **Triple-Stream Search** | BM25 + Vector + Graph, 90.6% accuracy |
| 🔄 **Transaction + Rollback** | Atomic writes + crash recovery |
| ⚠️ **Contradiction Detection** | Sentence transformer based |
| 📊 **Usage Tracking** | Track which facts are used |
| 🧹 **Adaptive Pruning** | Score-based memory cleanup |
| 📈 **Health Metrics** | Visual health monitoring |
| 🚀 **Proactive Discovery** | ~1 second knowledge discovery |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Query                             │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Smart Recall Hook                            │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Triple-Stream Search                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                 │
│  │  BM25   │→ │ Vector  │→ │  Graph  │→ RRF Fusion     │
│  └─────────┘  └─────────┘  └─────────┘                 │
└─────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Memory Reliability Layer                     │
│  Transaction Manager + Contradiction + Usage + Pruning  │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
OCM-Sup/
├── memory_reliability_layer/     # v2.6 Core Memory Reliability
│   ├── tx_manager.py             # Atomic transactions
│   ├── contradiction.py          # Contradiction detection
│   ├── usage_tracker.py         # Usage tracking
│   ├── adaptive_pruning.py      # Smart cleanup
│   └── health_metrics.py        # Health monitoring
├── scripts/                      # Memory management scripts
├── tests/                        # Tests
└── docs/                        # Documentation
```

---

## 🚀 Quick Start

```bash
# Search memory
python scripts/triple_stream_search.py --query "古洞站"

# Write new memory
python scripts/memory_tx_sync.py --action write --memory data.json

# Health check
python scripts/memory_pruning_adapter.py --status

# Run tests
python tests/test_memory_reliability.py
```

---

## 📊 Performance

| Metric | Value |
|--------|-------|
| Triple-Stream Accuracy | **90.6%** (vs 31.2% baseline) |
| Proactive Discovery | **~1 second** (275x speedup) |
| Health Score | **93.28%** |
| Test Pass Rate | **4/4** |

---

## 📚 Documentation

| Doc | Description |
|-----|-------------|
| [README.md](README.md) | 📖 Main documentation (Chinese) |
| [COMPREHENSIVE_SUMMARY.md](docs/COMPREHENSIVE_SUMMARY.md) | 📋 Comprehensive summary |
| [TECHNICAL.md](TECHNICAL.md) | 🔬 Technical details |
| [CHANGELOG.md](CHANGELOG.md) | 📅 Evolution history |
| [TEST-REPORT.md](TEST-REPORT.md) | 🧪 Test report |

---

## 🎯 vs OpenClaw Built-in Memory

| Aspect | OpenClaw Built-in | OCM Sup |
|-------|-------------------|---------|
| Search | Single semantic | Triple-Stream |
| Reliability | Session hooks | Transaction + Rollback |
| Contradiction | ❌ | ✅ |
| Memory Cleanup | Dreaming/Promotion | Adaptive Score |
| Proactive | Passive trigger | Proactive |

---

## 📜 License

MIT

---

_Last updated: 2026-04-28 | v2.6_
