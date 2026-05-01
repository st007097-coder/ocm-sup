---
name: ocm-sup
description: "OCM Sup 知識管理系統。結合 Triple-Stream Search（BM25 + Vector + Graph）同 Proactive Memory System，自動管理知識圖譜、主動發現新舊知識連接、防止 AI 失憶。觸發詞：'search'、'搜索'、'記得我'、'找到相關'、'知識圖譜'、'OCM Sup'、'記住呢個'。"
version: "2.5.0"
metadata:
  author: "阿星"
  created: "2026-03-29"
  updated: "2026-05-01"
  trigger_priority: high
  output_type: search_results + knowledge_graph
---

# OCM Sup — 知識管理系統

> Knowledge Management System with Triple-Stream Search + Proactive Memory

## 🎯 目標

將零散嘅知識通過 entity 關係組織起來，唔只係關鍵詞匹配，仲理解概念之間嘅連接。

## ⚡ 觸發條件

| 觸發詞 | 說明 |
|--------|------|
| "search"、"搜索" | 執行三元搜索 |
| "記得我"、"記住呢個" | 將信息加入 memory |
| "找到相關" | 搜索相關 entity |
| "知識圖譜"、"entity" | 查看實體關係 |
| "OCM Sup" | 啟動完整系統 |
| "Proactive Discovery" | 自動發現新舊連接 |

## 📁 專案結構

```
OCM-Sup/
├── scripts/              # 核心腳本（38個）
│   ├── triple_stream_search.py
│   ├── kg_auto_expander.py
│   ├── proactive_discovery.py
│   ├── memory_retriever.py
│   └── ...
├── wiki/                 # Wiki 同步目標
├── entities/             # 實體定義
├── concepts/            # 概念定義
├── tests/               # 測試
├── evals/               # 觸發評測
└── governance/         # 治理
```

## 🔄 核心功能

### 1. Triple-Stream Search（三流搜索）

| Channel | 技術 | 功能 |
|---------|------|------|
| BM25 | exact match | 精確關鍵詞 |
| Vector | semantic | 理解語義 |
| Graph | entity relations | 實體關係 |

### 2. Knowledge Graph（知識圖譜）

- Entity 定义（期哥、古洞站、阿星）
- 關係追蹤（期哥 → QS → 古洞站）
- 自動擴展（發現新 entity）

### 3. Proactive Discovery（主動發現）

- 自動發現新舊知識連接
- Consolidation Loop（~2 sec 完成）
- 防止 AI 失憶

### 4. Memory System（記憶系統）

- Session Start Memory Load
- Pre-compression Checkpoint
- Active Memory Plugin

---

## ⚠️ 邊界條件（Boundary Conditions）

| 情況 | 處理方式 |
|------|----------|
| Vector embedding 缺失 | 降級到 BM25 + Graph |
| Entity 未定義 | 自動創建新 entity |
| Wiki 同步失敗 | 回退到本地 memory |
| 三流都無結果 | 返回「未找到相關信息」 |

---

## 🛑 檢查點（Checkpoints）

| 檢查點 | 觸發條件 | 暫停 |
|--------|----------|------|
| **Entity 創建確認** | 新 entity 加入時 | ✅ |
| **破壞性操作** | 刪除 entity/關係 | ✅ |
| **大量同步** | >10 個文件同步 | ✅ |

---

## 📊 版本歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| v2.5 | 2026-04-28 | P3 Reliability Layer + P4 Integration |
| v2.4 | 2026-04-26 | Memory Stability System |
| v2.3 | 2026-04-25 | AI 失憶問題研究 |
| v2.0 | 2026-04-18 | 7-Dir 全部完成 |
| v0.1 | 2026-03-29 | 阿星誕生 |

---

## 🧪 測試

```bash
# 測試三元搜索
python3 scripts/triple_stream_search.py --query "期哥"

# 測試知識圖譜
python3 scripts/graph_search.py --entity 期哥

# 測試主動發現
python3 scripts/proactive_discovery.py --dry-run

# 運行所有測試
python3 tests/test_ocm_sup.py
```

---

_Last updated: 2026-05-01_