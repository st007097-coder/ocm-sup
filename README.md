# OCM Sup - OpenClaw Memory System

> 🧠 期哥嘅智能記憶系統 — 結合 Triple-Stream Search + Knowledge Graph + Proactive Discovery

[![Status](https://img.shields.io/badge/status-production_ready-green.svg)](#)
[![OCM Sup](https://img.shields.io/badge/OCM%20Sup-v2.3-blue.svg)](#)

[![View on GitHub](https://img.shields.io/badge/GitHub-Repo-green.svg)](https://github.com/st007097-coder/ocm-sup)

## 🔗 Quick Links

| 文檔 | 描述 | 英文版 |
|------|------|--------|
| [README.md](README.md) | 📖 主要文檔（呢個）| [English](README-en.md) |
| [TECHNICAL.md](TECHNICAL.md) | 🔬 技術原理 + 演算法 | [English](TECHNICAL-en.md) |
| [CHANGELOG.md](CHANGELOG.md) | 📅 進化歷史 + 決策過程 | [English](CHANGELOG-en.md) |
| [TEST-REPORT.md](TEST-REPORT.md) | 🧪 測試結果 + 問題修復 | [English](TEST-REPORT-en.md) |
| [cover.webp](cover.webp) | 🖼️ 封面圖片 |

---

## ⚠️ 重要說明：關於呢個項目

**呢個唔係比你照抄嘅。**

每個人、每個 Agent、每個使用場景都唔同。期哥係香港 QS（工料測量師），我用嘅系統係基於我嘅：

- **工作性質** — 工程項目管理、造價估算
- **技術背景** — 對 AI 有興趣但唔係工程師
- **使用習慣** — 廣東話、Telegram、Obsidian
- **時間資源** — 業餘時間慢慢整

**你應該點用呢個項目：**

1. **理解原理** — OCM Sup 點解要用 Triple-Stream？因為單一搜索方法唔夠好
2. **按需取用** — 你可能只需要其中一兩個腳本
3. **按自身情況修改** — 你嘅記憶系統應該服務你嘅需求，唔係抄晒所有功能
4. **自己諗嘅先係你嘅** — 我嘅 evolution 方向唔代表啱你，你自己諗出嚟嘅先最啱

**你唔需要：**
- 完全複製我嘅架構
- 用晒所有 9 個腳本
- 跟足我嘅 timeline

**你需要：**
- 了解自己嘅實際需求
- 選擇啱你嘅技術方案
- 自己思考、自己調整

> _「Copying is the last form of learning, but creating is the first form of thinking.」_

---

## 🎯 痛點與解決方案

> **每個功能背後都係為了解決一個真實問題。**

---

### 1. Triple-Stream Search（三流搜索）

#### 📍 情景

期哥問：「古洞站項目進展點樣？」

#### 😣 痛點

| 問題 | 描述 |
|------|------|
| 單一搜尋方法效果差 | Vector Search 只知「相關」，唔知「期哥 → works_on → 古洞站」
| 中英混合效果差 | 中文「古洞站」同英文「Kwu Tung Station」search 唔到同一結果
| 假陽性多 | 向量搜索會錯誤返回「期哥」，只因為佢哋training data 常一起出現

#### ✅ 解決方案

三元融合：`BM25 + Vector + Graph`

```
Query: 古洞站

BM25: 精確匹配關鍵詞「古洞站」
Vector: 理解「車站建設」、「MTR項目」相關概念
Graph: 發現「期哥 → works_on → 古洞站」關係

→ 結合三個channel結果（RRF Fusion）
```

#### 📝 實際例子

```
問：「期哥最近做咩project？」

傳統方式：
Vector Search → 返回一堆相關但分散的document

三元融合：
1. BM25 找到包含「期哥」「project」的document
2. Vector 找到語義相關的「QS工作」、「造價估算」
3. Graph 發現：期哥 → works_on → 古洞站

→ 返回：古洞站項目相關的 coherent 結果
```

---

### 2. Knowledge Graph（知識圖譜）

#### 📍 情景

期哥問：「阿星知唔知我係做QS？」

#### 😣 痛點

| 問題 | 描述 |
|------|------|
| 資訊碎片化 | 「期哥係QS」呢個事實散落在各個document入面
| 關係唔明確 | 就算找到期哥，都唔知佢同古洞站、OCM Sup嘅關係
| 需要手動維護 | 要記得邊個連接邊個，容易漏

#### ✅ 解決方案

建立 Entity 關係圖：

```
       ┌──────┐
       │ 期哥  │ (person)
       └──┬───┘
    works_on│
      ┌─────┴─────┐
      ▼           ▼
┌──────────┐  ┌──────┐
│  古洞站   │  │  阿星  │
│ (project)│  │(system)│
└────┬─────┘  └───┬──┘
     │             │
     │ uses       │ integrates_with
     ▼             ▼
┌─────────────────────┐
│      OCM Sup        │
│      (system)       │
└─────────────────────┘
```

#### 📝 實際例子

```
問：「阿星點解知道古洞站嘅嘢？」

沒有Graph：
→ 阿星話「我search到關於古洞站嘅document」

有Graph：
→ 阿星話「因為期哥 works_on 古洞站，而阿星 serves 期哥，
   所以我記得期哥嘅project入面有古洞站」
```

---

### 3. Smart Recall Hook（智能觸發）

#### 📍 情景

期哥問：「古洞站嘅最新進度？」

#### 😣 痛點

| 問題 | 描述 |
|------|------|
| 被動等待 | 期哥唔記得問，阿星就唔主動提
| 每次都要手動 | 期哥要記得話「幫我search古洞站」
| 唔知幾時觸發 | 乜嘢關鍵詞應該觸發搜尋？

#### ✅ 解決方案

自動識別需要觸發嘅 query：

```python
HIGH_PRIORITY_KEYWORDS = [
    '期哥', '古洞站', '阿星',  # 核心 entities
    'project', '進度', '進展',  # 工作相關
    'search', '搵', '知識',     # 動作關鍵詞
]

def should_trigger(query):
    # 如果query包含呢啲詞，自動觸發三元搜尋
```

#### 📝 實際例子

```
沒有Hook：
期哥：「古洞站進度係？」
阿星：「哦。」（被動等指示）

有Hook：
期哥：「古洞站進度係？」
阿星：「古洞站係MTR東鐵線項目，目前處於BS（Building Survey）階段...」
    （自動觸發三元搜尋，提供context）
```

---

### 4. Proactive Discovery（主動發現）

#### 📍 情景

阿星每日運行，但發現新嘅 AI news 同 期哥嘅工作冇關係，唔知點用

#### 😣 痛點

| 問題 | 描述 |
|------|------|
| 被動等問題 | 如果期哥唔問，阿星就唔發現新嘢
| 新舊資訊唔連接 | 新聞入面提到「ChatGPT」，但唔知佢同 OCM Sup 有咩關係
| 需要手動建立關係 | 好麻煩

#### ✅ 解決方案

自動推斷 Entity 之間嘅關係：

```python
# 規則引擎
RELATIONSHIP_RULES = {
    ('person', 'project'): 'works_on',      # 期哥 + 古洞站 → works_on
    ('person', 'system'): 'uses',           # 期哥 + OCM Sup → uses
    ('project', 'system'): 'uses',         # 古洞站 + OCM Sup → uses
}

# 信心度計算
confidence = base_confidence + keyword_density + type_compatibility
```

#### 📝 實際例子

```
Proactive Discovery 发现：
- News 入面提到「期哥」
- News 入面提到「古洞站」

自動推斷：期哥 → works_on → 古洞站

下次期哥問「我最近做咩」：
阿星：「你最近喺做古洞站項目（BS階段）」
```

---

### 5. HTTP API（搜索接口）

#### 📍 情景

其他系統想用 OCM Sup 嘅搜尋功能，但唔知點调用

#### 😣 痛點

| 問題 | 描述 |
|------|------|
| 只能喺 OpenClaw 入面用 | 其他工具（Telegram bot、external script）用唔到
| 唔係 standard interface | 每個script有自己的調用方式

#### ✅ 解決方案

提供 HTTP API：

```bash
# 任何可以發 HTTP request 嘅工具都可以用
curl "http://localhost:5005/search?q=古洞站&top_k=5"
curl "http://localhost:5005/entities"
curl "http://localhost:5005/health"
```

#### 📝 實際例子

```bash
# Telegram Bot 可以咁用：
期哥：/search 古洞站
Bot：→ HTTP GET /search?q=古洞站
    ← JSON results
Bot：→ 「古洞站係MTR東鐵線項目...」
```

---

### 6. Graph Visualization（圖譜可視化）

#### 📍 情景

阿星話：「我嘅Graph有43個entities，47個relationships」

#### 😣 痛點

| 問題 | 描述 |
|------|------|
| 睇唔到結構 | 全部係文字，唔知邊個係中心
| 難debug | 如果關係錯咗，幾乎發現唔到
| 難解釋 | 向期哥解釋「Graph係點嘅」好麻煩

#### ✅ 解決方案

生成視覺化圖表：

```bash
# 生成 HTML interactive view
python3 graph_visualization.py --format html

# 生成 Mermaid diagram
python3 graph_visualization.py --format mermaid
```

#### 📝 實際例子

```
Graph 可視化顯示：

        期哥 ──works_on──→ 古洞站
           │                   │
         uses              uses │
           ▼                   ▼
        阿星 ←──integrates_with──→ OCM Sup

一眼就睇到：
- 期哥係中心（最多連接）
- OCM Sup 係另一個 hub
- 古洞站 同 阿星 都連接到期哥
```

---

### 7. Uncertainty Tracking（不確定性追蹤）

#### 📍 情景

期哥問：「你幾時知 OCM Sup 嘅？」

#### 😣 痛點

| 問題 | 描述 |
|------|------|
| 乱答 | 阿星當記得咁答，但其實唔記得
| 冇confidence概念 | 唔知自己知幾多、唔知幾多
| 誤導期哥 | 錯誤的自信比唔記得更糟糕

#### ✅ 解決方案

每個 claim 有 metadata：

```python
claim = {
    "content": "期哥係QS",
    "confidence": 0.9,           # 90% 肯定
    "evidence": ["Wiki: 期哥.md"],
    "last_updated": "2026-04-25",
    "uncertainty_reasons": []
}

# 如果 confidence < 0.5
if claim.confidence < 0.5:
    return "我唔記得喇，需要再確認"
```

#### 📝 實際例子

```
沒有 Uncertainty Tracking：
期哥：「你知唔知我係邊個？」
阿星：「你係期哥。」
期哥：「你點知嘅？」
阿星：「我知。」
（其實唔記得點知）

有 Uncertainty Tracking：
期哥：「你知唔知我係邊個？」
阿星：「你係期哥（confidence: 95%，from: 期哥.md）"
期哥：「你點知嘅？」
阿星：「因为你喺 Wiki 度有 entry，我記得你係QS。」
```

---

### 8. Consolidation Loop（記憶整合循環）

#### 📍 情景

阿星每日寫 memory，但發現：
- 舊 memory 越積越多，search 變慢
- 重要資訊同垃圾資訊混在一起
- 唔知幾時應該「消化」舊 memory

#### 😣 痛點

| 問題 | 描述 |
|------|------|
| Memory 過載 | 所有資訊都係「短期記憶」，冇分層 |
| 資訊衰老 | 7日前嘅memory可能已經過時 |
| 唔主動整理 | 等 user 問先被動 search |

#### ✅ 解決方案

建立三層記憶結構：

```
Episodic Buffer (短期) → Semantic Wiki (長期) → Procedural Memory (技能)
```

每晚自動運行 Consolidation Loop：
1. Episodic Buffer 入面 7 天以上嘅 memory distill
2. 提取 entities、relationships、insights
3. 寫入 Semantic Wiki
4. 更新 Procedural Memory (Skills)

#### 📝 實際例子

```
冇 Consolidation Loop：
memory/2026-03-01.md ~ 2026-04-18.md
全部散落，search 慢，關係唔清楚

有 Consolidation Loop：
1. 每日 memory 寫入 Episodic Buffer
2. 7日後自動 distill:
   「期哥」從 memory → 期哥.md (entity)
   「期哥 works_on 古洞站」→ relationship
3. Wiki 有結構化嘅知識
```

---

### 9. Content Half-lives（內容衰減）

#### 📍 情景

阿星發現：舊嘅 memory 有時仲係search到，但可能已經唔啱了

#### 😣 痛點

| 問題 | 描述 |
|------|------|
| 新舊資訊冇區分 | 2019年嘅memory同今日嘅memory權重一樣 |
| 資訊過時 | 但仍然被當成「已知事實」 |
| Confidence 假象 | 舊資訊 confidence 仍然好高 |

#### ✅ 解決方案

每個 claim 有「半衰期」：

```python
HALF_LIVES = {
    'fact': 30,        # 事實 30日衰減
    'opinion': 7,      # 意見 7日
    'news': 3,        # 新聞 3日
    'project': 14,     # 項目狀態 14日
}

def calculate_confidence(original_conf, days_elapsed):
    decay = 0.5 ** (days_elapsed / half_life)
    return original_conf * decay
```

#### 📝 實際例子

```
冇半衰期：
期哥：「我項目進展點？」
阿星：「古洞站係QS階段」（confidence: 95%）
（可能係3個月前嘅狀態）

有半衰期：
期哥：「我項目進展點？」
阿星：「古洞站目前處於BS階段」（confidence: 70%）
期哥：「之前呢？」
阿星：「之前係QS階段（confidence: 35%，已衰減）
```

---

### 10. Active Contradiction Detection（主動矛盾檢測）

#### 📍 情景

阿星發現：
- memory話「期哥係QS」
- 但另一個document話「期哥係工程師」
- 搞唔清楚邊個啱

#### 😣 痛點

| 問題 | 描述 |
|------|------|
| 矛盾冇被發現 | 兩個 sources 讲嘅嘢衝突 |
| 誤導 | 隨機選擇一個，錯了點算？ |
| 冇機制處理 | 唔知信邊個 |

#### ✅ 解決方案

當發現矛盾，自動標記：

```python
def detect_contradiction(claim_a, claim_b):
    if are_mutually_exclusive(claim_a, claim_b):
        return {
            "status": "CONTRADICTION",
            "claims": [claim_a, claim_b],
            "resolution_needed": True
        }
```

#### 📝 實際例子

```
冇矛盾檢測：
期哥：「我係做咩嘅？」
阿星：「你係QS。」（隨機揀咗QS）
期哥：「但係你之前話我係工程師？」
阿星：「吓？」

有矛盾檢測：
期哥：「我係做咩嘅？」
阿星：「我發現有矛盾：
   - Source A 話你係QS
   - Source B 話你係工程師
   邊個啱？」
期哥：「QS啱，已更新」
```

---

### 總結：點解要有呢啲功能？

| 功能 | 解決咩痛點 |
|------|-----------|
| Triple-Stream Search | 單一搜尋方法效果差 |
| Knowledge Graph | 關係唔明確、資訊碎片化 |
| Smart Recall Hook | 被動等問題、被迫手動觸發 |
| Proactive Discovery | 發現唔到新資訊同舊資訊嘅關係 |
| HTTP API | 其他系統用唔到搜尋功能 |
| Graph Visualization | 睇唔到Graph結構 |
| Uncertainty Tracking | 乱答、誤導 |
| Consolidation Loop | Memory 過載、唔主動整理 |
| Content Half-lives | 新舊資訊冇區分、資訊過時 |
| Active Contradiction | 矛盾冇被發現、誤導 |

**核心目標：** 讓阿星知道「乜嘢」、「點解」、「幾時知」、「知幾多」。

---

## 📖 目錄

---

## 📖 目錄

- [簡介](#簡介)
- [⚠️ 重要說明](#⚠️-重要說明-關於呢個項目)
- [🎯 痛點與解決方案](#🎯-痛點與解決方案) ← 🆕
- [核心功能](#核心功能)
- [系統架構](#系統架構)
- [快速開始](#快速開始)
- [腳本説明](#腳本説明)
- [使用方法](#使用方法)
- [技術細節](#技術細節)
- [一步步教程](📚-一步步教程建立自己嘅記憶系統)
- [技術原理](TECHNICAL.md) — **深入理解每個功能背後嘅原理**
- [進化歷程](CHANGELOG.md) — **詳細進化史 + 決策過程 + 教訓**
- [測試報告](TEST-REPORT.md) — **所有測試結果 + 問題修復記錄**
- [Credits](#credits)

---

## 🚀 簡介

**OCM Sup** (OpenClaw Memory System Supreme) 係一個結合多種搜索技術嘅智能記憶系統，專為期哥（香港QS專業人士）同佢嘅 AI 助手阿星設計。

### 解決什麼問題？

| 問題 | 傳統方案 | OCM Sup 方案 |
|------|----------|--------------|
| 關鍵詞搜索 | BM25 のみ | BM25 + Vector + Graph 三流融合 |
| 語義理解 | 單純 Vector Search | 中英雙語 Query Expansion |
| Entity 關係 | 無 | Knowledge Graph 追蹤 |
| 主動發現 | 被動等待查詢 | Proactive Discovery 自動發現 |
| 智能觸發 | 固定關鍵詞 | Smart Recall Hook |

---

## ✨ 核心功能

### 1. Triple-Stream Search（三流搜索）

```
查詢 → BM25 Channel ─┐
     → Vector Channel ─┼→ RRF Fusion → 結果
     → Graph Channel ──┘
```

- **BM25 Channel**: 精確關鍵詞匹配
- **Vector Channel**: 語義相似度搜索（支持中英雙語）
- **Graph Channel**: 通過 Entity 關係發現相關內容

### 2. Knowledge Graph（知識圖譜）

- 43 個 Entities
- 47 個 Relationships
- 支援 Entity Types: Person, Project, System, Concept, Document

### 3. Smart Recall Hook（智能回憶觸發）

自動識別需要觸發 Triple-Stream Search 嘅場景：
- Entity 名稱：期哥、古洞站、阿星、OCM Sup
- 關鍵詞：search、find、知識、project
- 熱門話題：根據訪問頻率自動提升

### 4. Proactive Discovery（主動發現）

- 自動監控新 entities
- 智能推斷 Entity 之間的關係
- 基於 Entity Types 嘅規則引擎
- 多因素信心度計算

### 5. HTTP API（搜索接口）

```bash
GET /search?q=古洞站&top_k=5
GET /entities
GET /stats
GET /health
```

---

## 🏗 系統架構

```
┌─────────────────────────────────────────────────────────┐
│                    OCM Sup Architecture                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐     ┌──────────────┐                │
│  │   Wiki       │     │   Memory     │                │
│  │   (MD files) │     │   (Daily)   │                │
│  └──────┬───────┘     └──────┬───────┘                │
│         │                    │                          │
│         ▼                    ▼                          │
│  ┌─────────────────────────────────────┐              │
│  │       Triple-Stream Search           │              │
│  │  ┌─────────┐ ┌─────────┐ ┌───────┐ │              │
│  │  │  BM25   │ │ Vector  │ │ Graph  │ │              │
│  │  └────┬────┘ └────┬────┘ └───┬───┘ │              │
│  │       └────────────┼──────────┘      │              │
│  │                    ▼                   │              │
│  │            ┌───────────┐              │              │
│  │            │  RRF      │              │              │
│  │            │  Fusion   │              │              │
│  │            └─────┬─────┘              │              │
│  └──────────────────┼────────────────────┘              │
│                     ▼                                    │
│  ┌─────────────────────────────────────┐              │
│  │     Smart Recall Hook + Proactive    │              │
│  │           Discovery                   │              │
│  └─────────────────────────────────────┘              │
│                     │                                  │
│                     ▼                                  │
│  ┌─────────────────────────────────────┐              │
│  │          HTTP API + CLI             │              │
│  └─────────────────────────────────────┘              │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Entity Relationships

```
        ┌──────┐
        │ 期哥  │ (person)
        └──┬───┘
     works_on│
      ┌─────┴─────┐
      ▼           ▼
┌──────────┐  ┌──────┐
│  古洞站   │  │  阿星  │
│ (project)│  │(system)│
└────┬─────┘  └───┬──┘
     │             │
     │ uses       │ integrates_with
     ▼             ▼
┌─────────────────────┐
│      OCM Sup        │
│      (system)       │
└─────────────────────┘
```

---

## ⚡ 快速開始

### 前置要求

- Python 3.8+
- OpenClaw v2026.4.10+
- Ollama (用於 embeddings)

### 安裝步驟

```bash
# 1. 克隆 repository
git clone https://github.com/st007097-coder/ocm-sup.git
cd ocm-sup

# 2. 安裝 Python dependencies
pip install rank-bm25 sentence-transformers flask

# 3. 設置 environment
export PYTHONPATH=/path/to/ocm-sup/scripts:$PYTHONPATH

# 4. 驗證安裝
python3 scripts/triple_stream_search.py --test
```

### 快速測試

```bash
# 搜索測試
python3 scripts/triple_stream_search.py --query "古洞站"

# 啟動 API
python3 scripts/search_api.py --port 5005

# 生成圖譜視覺化
python3 scripts/graph_visualization.py --format html
```

---

## 📜 腳本説明

| 腳本 | 功能 | 使用場景 |
|------|------|----------|
| `triple_stream_search.py` | 三流搜索核心 | 主要搜索功能 |
| `query_expansion.py` | 中英同義詞擴展 | 提升搜索召回率 |
| `graph_search.py` | Entity 圖譜搜索 | 關係發現 |
| `kg_auto_expander.py` | 自動擴展 Knowledge Graph | 發現新 entities |
| `smart_recall_hook.py` | 智能觸發鉤子 | 自動識別搜索需求 |
| `smart_recall_cron.py` | 定時預熱腳本 | 定期預加載 context |
| `search_api.py` | Flask HTTP API | 其他系統調用 |
| `proactive_discovery.py` | 主動發現引擎 | 自動關係推斷 |
| `graph_visualization.py` | 圖譜視覺化 | 生成 Mermaid/HTML |

---

## 📖 使用方法

### 1. Triple-Stream Search

```python
import sys
sys.path.insert(0, 'scripts')
from triple_stream_search import TripleStreamSearch

search = TripleStreamSearch('/path/to/wiki')
results = search.search('古洞站', top_k=5)

for r in results:
    print(f"[{r['sources']}] {r['title']}")
    print(f"   Path: {r['path']}")
    print(f"   RRF Score: {r['rrf_score']:.4f}")
```

**輸出示例：**
```
[bm25+vector+graph] 古洞站
   Path: ai-agent/entities/古洞站.md
   RRF Score: 0.1827
[bm25+vector+graph] 阿星
   Path: ai-agent/entities/阿星.md
   RRF Score: 0.1563
```

### 2. Smart Recall Hook

```python
from smart_recall_hook import SmartRecallHook

hook = SmartRecallHook()

# 自動識別是否需要觸發
if hook.should_trigger('古洞站項目進度'):
    results = hook.recall('古洞站')
    context = hook.inject_into_context(results)
    print(context)
```

**觸發條件：**
- Entity 名稱：期哥、古洞站、阿星、OCM Sup
- 關鍵詞：search、find、知識、project
- 熱門話題：高頻訪問的查詢

### 3. HTTP API

```bash
# 啟動 API
python3 scripts/search_api.py --port 5005

# 搜索
curl "http://localhost:5005/search?q=古洞站&top_k=5"

# 健康檢查
curl http://localhost:5005/health
```

**API Endpoints：**

| Endpoint | Method | 描述 |
|----------|--------|------|
| `/search` | GET | 搜索 |
| `/entities` | GET | 列出所有 entities |
| `/stats` | GET | 搜索統計 |
| `/health` | GET | 健康檢查 |

### 4. Proactive Discovery

```bash
# 完整 scan
python3 scripts/proactive_discovery.py --report

# 連續監控
python3 scripts/proactive_discovery.py --watch --interval 300

# 應用建議
python3 scripts/proactive_discovery.py --apply
```

**Relationship Inference 規則：**

| From | To | Relationship | Confidence |
|------|----|--------------|------------|
| person | project | works_on | 90% |
| person | system | uses | 80% |
| project | person | involves | 80% |
| system | system | integrates_with | 80% |

### 5. Graph Visualization

```bash
# 生成 HTML 視覺化
python3 scripts/graph_visualization.py --format html

# 聚焦特定 entity
python3 scripts/graph_visualization.py --focus 期哥 --depth 2

# Mermaid 格式
python3 scripts/graph_visualization.py --format mermaid
```

---

## 🔬 技術細節

### RRF (Reciprocal Rank Fusion)

```python
RRF_score(d) = Σ 1 / (k + rank_i(d))

# k=60 係 industry standard
```

### Multi-Stage Similarity Filtering

```
Stage 1: Exact match check
Stage 2: Prefix/suffix check
Stage 3: String similarity (Levenshtein distance)
Stage 4: Entity-type compatibility check
Stage 5: Embedding similarity (combined)
```

### Entity Type Compatibility

| Type Pair | Compatible? |
|-----------|-------------|
| person ↔ concept | ❌ |
| person ↔ technology | ❌ |
| project ↔ concept | ❌ |
| project ↔ technology | ❌ |
| concept ↔ technology | ✅ |

### Confidence Scoring Formula

```
confidence = base_confidence
           + keyword_density_boost (+0.2)
           + learned_pattern_boost (+0.15)
           + type_compatibility_boost (+0.1)
```

---

## 📈 進化歷程

### Timeline

| 日期 | 版本 | 內容 |
|------|------|------|
| 2026-03-29 | v1.0 | 阿星誕生，基本搜尋 |
| 2026-04-11 | v1.1 | Triple-Stream Search Phase 1-5 |
| 2026-04-13 | v1.2 | 7-Dir 1, 2 整合 |
| 2026-04-15 | v1.3 | 7-Dir 4 KG Auto-Expansion |
| 2026-04-17 | v1.4 | Phase Z (Uncertainty Tracking + EQS) |
| **2026-04-18** | **v2.0** | **完整 Roadmap 完成** |
| **2026-04-25** | **v2.3** | **AI 失憶問題研究（Proactive Memory）** |

### Roadmap 完成狀態

| # | Direction | 狀態 | 完成度 |
|---|-----------|------|--------|
| Phase 1-5 | Triple-Stream Search | ✅ | 100% |
| 7-Dir 1 | Memory System 整合 | ✅ | 100% |
| 7-Dir 2 | Wiki Search | ✅ | 100% |
| 7-Dir 3 | Search API | ✅ | 100% |
| 7-Dir 4 | KG Auto-Expansion | ✅ | 100% |
| 7-Dir 5 | Smart Recall | ✅ | 100% |
| 7-Dir 6 | Proactive Discovery | ✅ | 100% |
| 7-Dir 7 | Graph Visualization | ✅ | 100% |

**總完成度：7/7 = 100%** 🎉

---

## 📊 系統狀況

### 測試結果 (2026-04-18)

| 測試項目 | 結果 |
|----------|------|
| Triple-Stream Search | ✅ PASS |
| Knowledge Graph | ✅ PASS (43 nodes, 47 edges) |
| Smart Recall Hook | ✅ PASS (5/5) |
| Search API | ✅ PASS |
| Proactive Discovery | ✅ PASS (0 new suggestions) |
| Graph Visualization | ✅ PASS |
| Entity Files | ✅ PASS (0 frontmatter issues) |

### 系統 Metrics

| Metric | 數值 |
|--------|------|
| Entities | 43 |
| Relationships | 47 |
| Document Types | 5 (person, project, system, concept, document_title) |
| Relationship Types | 5 (works_on, uses, involves, integrates_with, related_to) |

---

## 📚 一步步教程：建立自己嘅記憶系統

> ⚠️ **重要提醒**：呢個係 general 方向，唔係你要跟足嘅 checklist。
> 每個人嘅情況唔同，你應該按自己需要調整。

---

### Step 1: 了解你自己

在建立任何系統之前，先了解你服務嘅對象：

```
問自己：
1. 我係邊個？（角色、背景）
2. 我服務邊個範疇？（專業領域）
3. 我慣用咩語言？（廣東話/普通話/英文）
4. 我有咩工具？（Telegram/Obsidian/Notion）
5. 我有多少時間？（業餘/全職）
```

**為乜要知呢啲？**
- 你嘅系統應該服務你，唔係你服務你嘅系統
- 例子：期哥係香港 QS，用廣東話，主要用 Telegram + Obsidian

---

### Step 2: 選擇搜尋方案

**問題**：你嘅 AI 助手點記得嘢？


| 方案 | 優點 | 缺點 | 適合邊個？ |
|------|------|------|-----------|
| 純 Vector Search | 簡單 | 慢、假陽性多 | 小規模、簡單需求 |
| 純 BM25 | 快、準確 | 唔理解語義 | 只需要關鍵詞 |
| **三元融合** | 平衡各方法 | 需要更多設置 | **大多數情況** |

**點解要三元融合？**
```
BM25: 「古洞站」→ 精確匹配「古洞站」
Vector: 「古洞站」→ 理解「車站建設」相關概念
Graph: 「古洞站」→ 期哥(人) → QS(專業)
```

如果你只需要簡單搜尋，可以只用 BM25。

---

### Step 3: 設計 Entity 關係

**問題**：你嘅系統要追蹤邊啲 entities？


**步驟**：
```
1. 列出核心 entities
   - 人（你自己、你的用戶）
   - 項目（你參與的項目）
   - 系統（你用嘅工具/服務）


2. 定義關係類型
   - works_on: 邊個做邊個項目
   - uses: 邊個用邊個工具
   - part_of: 邊個係邊個的一部分

3. 建立實體文件
   每個 entity 一個 .md 檔案，包含：
   - title, type, entity_type
   - relationships（關係）
   - 描述
```

**期哥嘅例子**：
```yaml
# 期哥.md
---
title: 期哥
entity_type: person
relationships:
  - target: 古洞站
    type: works_on
---

# 古洞站.md
---
title: 古洞站
entity_type: project
relationships:
  - target: 期哥
    type: involves
---
```

---

### Step 4: 實現三元融合搜尋

**如果你選擇三元融合**：
```python
# 1. BM25 Channel - 關鍵詞匹配
from rank_bm25 import BM25Okapi

# 2. Vector Channel - 語義匹配
from sentence_transformers import SentenceTransformer

# 3. Graph Channel - 關係匹配
# 讀取 entities 檔案，建立 graph

# 4. RRF Fusion
def rrf_fusion(results_dict, k=60):
    scores = defaultdict(float)
    for channel, results in results_dict.items():
        for rank, item in enumerate(results):
            scores[item] += 1 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**唔同語言要點做？**
如果你用中英混合：
```python
# Query Expansion
def expand_query(query):
    synonyms = {
        '古洞站': ['古洞站', 'Kwu Tung Station', 'gutong'],
        'AI助手': ['AI助手', 'AI assistant', '助手'],
    }
    expanded = [query]
    for term, alts in synonyms.items():
        if term in query:
            expanded.extend(alts)
    return expanded
```

---

### Step 5: 加入智能觸發 (Smart Recall)

**問題**：你唔想每次都手動搜尋，想 AI 主動記得嘢。


**方案**：
```python
# Smart Recall Hook
HIGH_PRIORITY_KEYWORDS = [
    'search', 'find', 'locate',
    '期哥', '古洞站', '阿星',
    'project', '知識', 'entity',
]

def should_trigger(query):
    query_lower = query.lower()
    for keyword in HIGH_PRIORITY_KEYWORDS:
        if keyword in query_lower:
            return True
    return False
```

**根據你嘅 Entities 調整 KEYWORDS**：
```python
MY_ENTITIES = ['期哥', '古洞站', '阿星']
HIGH_PRIORITY_KEYWORDS.extend(MY_ENTITIES)
```

---

### Step 6: 建立 Proactive Discovery

**問題**：被動等查詢太慢，你想系統主動發現新資訊。

**方案**：
```python
# Proactive Discovery Engine

# 1. 規則-based Relationship Inference
RELATIONSHIP_RULES = {
    ('person', 'project'): 'works_on',
    ('person', 'system'): 'uses',
    ('project', 'person'): 'involves',
}

# 2. Multi-factor Confidence
def calculate_confidence(base, keyword_density, type_compat):
    return min(base + keyword_density*0.2 + type_compat*0.1, 0.95)

# 3. Bidirectional Check
# 確保 A→B 同 B→A 都考慮
```

---

### Step 7: 可視化

**問題**：你點知你嘅 Graph 有幾大？

**方案**：
```bash
# 生成 Mermaid diagram
python3 graph_visualization.py --format mermaid

# 或者生成 HTML interactive view
python3 graph_visualization.py --format html
```

**你應該睇到**：
- 有幾多 nodes
- 有幾多 edges
- 邊個係中心 node（最多連接）

---

### Step 8: 持續優化

**記住**：系統係 evolution，唔係一次過建立。

```
每週檢討：
1. 搜尋結果啱唔啱？
2. 有冇新 entities 要加？
3. 有冇關係漏咗？
4. 邊個 feature 最常用？

按需調整：
- 如果你唔需要某個 channel，拎走佢
- 如果你有新嘅 entities type，加上去
```

---

### Step 9: 常見問題

**Q: 我應該用晒所有 scripts 嗎？**
A: 唔需要。揀你需要嘅。如果你想升級搜尋，加三元融合。如果你只想快速搜尋，BM25 就夠。

**Q: 中英文混雜要點做？**
A: Query expansion + entity-type filtering。詳細見 Step 4。

**Q: 幾耐更新一次 entities？**
A: 建議每日或每週，視乎你嘅資訊量。

---

### 總結：點解係一步步？

> 因為你唔可能一次過建立完美嘅系統。
> 每個人嘅起點都唔同，你需要嘅功能都唔同。

**建議路徑**：
```
1. 了解自己（Step 1）
2. 選擇搜尋方案（Step 2）
3. 設計 entities（Step 3）
4. 實現搜尋（Step 4）
5. 加入智能觸發（Step 5）
6. 主動發現（Step 6）可跳過
7. 可視化（Step 7）可跳過
8. 持續優化（Step 8）
```

**最緊要嘅係**：
- 唔好抄，要諗
- 唔好一次過，要迭代
- 唔好完美，要 work

---

## 🙏 Credits

### 靈感來源

- **Andrej Karpathy** - Programming Principles (Simplicity First, Surgical Changes)
- **Aporia Labs** - LLM Wiki v2 (Confidence Scoring, Supersession, Forgetting)
- **Anthropic** - OODA Loop / CraniMem Architecture
- **期哥** - QS專業人士，整個系統的需求提出者

### 技術棧

- **OpenClaw** - AI Assistant Framework
- **BM25 (rank_bm25)** - Keyword Search
- **Sentence Transformers** - Vector Embeddings
- **Flask** - HTTP API
- **Mermaid.js** - 圖表渲染

### 主要貢獻者

- **期哥** - 產品設計、需求提出
- **阿星** - 系統開發、算法實現

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🔗 Links

- [GitHub Repository](https://github.com/st007097-coder/ocm-sup)
- [OpenClaw Docs](https://docs.openclaw.ai)
- [期哥嘅 GitHub](https://github.com/st007097-coder)

---

_最後更新：2026-04-25_
_OCM Sup v2.3 - Proactive Memory System_ 🚀