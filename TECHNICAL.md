# OCM Sup — 技術原理詳解

> 📚 深入理解每個功能背後嘅原理

---

## 📖 目錄

1. [系統總覽](#1-系統總覽)
2. [Triple-Stream Search 原理](#2-triple-stream-search-原理)
3. [Knowledge Graph 原理](#3-knowledge-graph-原理)
4. [RRF Fusion 原理](#4-rrf-fusion-原理)
5. [Smart Recall Hook 原理](#5-smart-recall-hook-原理)
6. [Proactive Discovery 原理](#6-proactive-discovery-原理)
7. [Consolidation Loop 原理](#7-consolidation-loop-原理)
8. [Uncertainty Tracking 原理](#8-uncertainty-tracking-原理)
9. [Entity Type System 原理](#9-entity-type-system-原理)
10. [Implementation Details](#10-implementation-details)

---

## 1. 系統總覽

### 1.1 核心問題

**問題：** AI 助手點樣有效存取同運用長期記憶？

傳統方案：
- Vector Search → 語義相關，但唔理解結構關係
- 純 Keyword → 精確，但唔理解語義
- 純 Graph → 關係清晰，但需要預先建立

**OCM Sup 方案：** 三元融合 + 智能觸發 + 主動發現

```
┌─────────────────────────────────────────────────────┐
│                    User Query                        │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│              Smart Recall Hook                       │
│         (should_trigger 自動判斷)                    │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│           Triple-Stream Search                       │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │  BM25   │  │ Vector  │  │  Graph  │           │
│  │ Channel │  │ Channel │  │ Channel │           │
│  └────┬────┘  └────┬────┘  └────┬────┘           │
│       └─────────────┼─────────────┘                 │
│                     │                               │
│                     ▼                               │
│              ┌───────────┐                         │
│              │  RRF     │                          │
│              │  Fusion  │                          │
│              └─────┬─────┘                         │
└───────────────────┼─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│                  Results                            │
│         (Ranked, Scored, Annotated)                 │
└─────────────────────────────────────────────────────┘
```

### 1.2 數據流

```
Wiki (MD files)
    │
    ├── Entities/Relationships ──→ Graph Channel
    ├── Documents ──────────────→ BM25 Index
    └── Documents ──────────────→ Vector Embeddings
```

---

## 2. Triple-Stream Search 原理

### 2.1 BM25 Channel

**原理：** Best Matching 25，一種基於詞頻嘅 ranking 函數

```python
BM25(doc, query) = Σ IDF(t) × (tf(t,doc) × (k1+1)) / (tf(t,doc) + k1 × (1-b+b×|doc|/avgdl))
```

**參數：**
- `k1 = 1.5` — 詞頻飽和度控制
- `b = 0.75` — 文檔長度正規化

**為乜用 BM25：**
- 精確關鍵詞匹配
-速度快（倒排索引）
-唔受拼寫變化影響

### 2.2 Vector Channel

**原理：** 將文字映射到高維向量，相似內容有相似向量

```python
embedding = model.encode(text)  # e.g., 768-dim vector
similarity = cos(embedding_q, embedding_d)
```

**模型：** Sentence Transformers (e.g., `all-MiniLM-L6-v2`)

**問題：** Embedding 模型有語言 bias

```
中文「古洞站」同「Kwu Tung Station」向量可能唔相似
因為訓練數據入面中文同英文冇足夠對應
```

**解決：** Query Expansion + Multi-stage Filtering

### 2.3 Graph Channel

**原理：** 根據 Entity 之間的預先定義關係發現相關內容

```python
def graph_search(query_entities, depth=2):
    results = set()
    for entity in query_entities:
        # BFS traversal
        frontier = [entity]
        for _ in range(depth):
            next_frontier = []
            for node in frontier:
                for edge in node.edges:
                    next_frontier.append(edge.target)
                    results.add(edge.target)
            frontier = next_frontier
    return results
```

---

## 3. Knowledge Graph 原理

### 3.1 Entity 結構

```yaml
# 期哥.md
---
title: 期哥
type: entity
entity_type: person
confidence: 0.95
relationships:
  - target: 古洞站
    type: works_on
    direction: outgoing
---
```

### 3.2 Entity Types

| Type | 描述 | 例子 |
|------|------|------|
| person | 人物 | 期哥 |
| project | 項目 | 古洞站 |
| system | 系統/工具 | OCM Sup, 阿星 |
| concept | 概念 | 記憶系統 |
| document_title | 文檔 | 某篇 article |

### 3.3 Relationship Types

| Type | From | To | 例子 |
|------|------|----|------|
| works_on | person | project | 期哥 → 古洞站 |
| uses | person | system | 期哥 → 阿星 |
| involves | project | person | 古洞站 → 期哥 |
| part_of | component | whole | 阿星 → OCM Sup |
| related_to | any | any | 通用關係 |

### 3.4 Type Compatibility

唔同 entity types 之間有 compatibility 限制：

```python
INCOMPATIBLE_PAIRS = [
    ('person', 'concept'),    # 人唔係概念
    ('person', 'technology'), # 人唔係工具（但可以用工具）
    ('project', 'concept'),    # 項目唔係概念
]

def is_compatible(entity_a, entity_b):
    """檢查兩個 entity types 之間係否兼容"""
    return (entity_a.type, entity_b.type) not in INCOMPATIBLE_PAIRS
```

**原理：** 
- Vector similarity 高但 type incompatibility = 假陽性
- 應該被過濾

---

## 4. RRF Fusion 原理

### 4.1 問題

三個 channels 返回唔同嘅 ranking，点樣合併？

```
BM25 Ranking:   Doc A (1), Doc B (2), Doc C (3)
Vector Ranking: Doc B (1), Doc A (2), Doc C (3)
Graph Ranking:  Doc C (1), Doc A (2), Doc B (3)
```

### 4.2 RRF Formula

**Reciprocal Rank Fusion:**

```python
RRF_score(doc) = Σ 1 / (k + rank_channel(doc))
```

其中 `k = 60` (industry standard)。

### 4.3 Example

```python
k = 60

doc_scores = defaultdict(float)

# BM25 ranking
for rank, doc in enumerate(['A', 'B', 'C']):
    doc_scores[doc] += 1 / (k + rank)  # A=1/61, B=1/62, C=1/63

# Vector ranking
for rank, doc in enumerate(['B', 'A', 'C']):
    doc_scores[doc] += 1 / (k + rank)  # B=1/61+1/62, A=1/61+1/62, ...

# Graph ranking
for rank, doc in enumerate(['C', 'A', 'B']):
    doc_scores[doc] += 1 / (k + rank)

# Final ranking by RRF score
final_ranking = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
```

### 4.4 點解 RRF 咁好？

- **平衡各 channel 優缺點**
- **避免單一 channel 主導**
- **簡單但有效**
- **Robust** — 一個 channel 錯了，唔會摧毁整體結果

---

## 5. Smart Recall Hook 原理

### 5.1 問題

用戶查詢係咪需要觸發三元搜尋？

### 5.2 Trigger 條件

```python
HIGH_PRIORITY_KEYWORDS = {
n    # Entity names
    '期哥', '古洞站', '阿星', 'OCM Sup',\n    # Action keywords\n    'search', 'find', '搵', '知識', '記得',\n    # Project keywords\n    'project', '項目', '進度', '進展',\n}\n\ndef should_trigger(query):\n    query_lower = query.lower()\n    for keyword in HIGH_PRIORITY_KEYWORDS:\n        if keyword in query_lower:\n            return True\n    return False\n```

### 5.3 為乜要 trigger？

**好處：**
- 節省資源（唔使每次都三元搜尋）
- 確保重要查詢有充足 resources
- 提供更好嘅 context

### 5.4 觸發後流程

```python
def recall_with_hook(query):
    if should_trigger(query):
        # 完整三元搜尋
        results = triple_stream_search(query)
        context = build_context(results)
        return context
    else:
        # 簡單回覆
        return basic_response(query)
```

---

## 6. Proactive Discovery 原理

### 6.1 問題

被動等用戶問，系統幾時主動發現新資訊？

### 6.2 Relationship Inference

根據 entity types 推斷關係：

```python
RELATIONSHIP_RULES = {
    ('person', 'project'): ('works_on', 0.9),
    ('person', 'system'): ('uses', 0.8),
    ('project', 'person'): ('involves', 0.8),
    ('system', 'system'): ('integrates_with', 0.7),
}

def infer_relationship(entity_a, entity_b):
    type_pair = (entity_a.type, entity_b.type)
    if type_pair in RELATIONSHIP_RULES:
        rel_type, base_conf = RELATIONSHIP_RULES[type_pair]
        confidence = calculate_confidence(base_conf, ...)
        return (rel_type, confidence)
    return ('related_to', 0.3)
```

### 6.3 Multi-factor Confidence

```python
def calculate_confidence(base_conf, keyword_density, learned_pattern, type_compat):
    """
    confidence = base_conf + keyword_boost + learned_boost + type_boost
    """
    return min(base_conf 
                + keyword_density * 0.2 
                + learned_pattern * 0.15 
                + type_compat * 0.1, 
                0.95)
```

### 6.4 Bidirectional Check

```python
# 避免重複建議
def relationship_exists(entity_a, entity_b):
    # 檢查 A → B
    if entity_b in entity_a.outgoing_neighbors:
        return True
    # 檢查 B → A
    if entity_a in entity_b.outgoing_neighbors:
        return True
    return False
```

---

## 7. Consolidation Loop 原理

### 7.1 三層記憶

```
┌───────────────────────────────────────┐
│        Episodic Buffer (短期)        │
│  - 每日 raw memory                   │
│  - 7日後 distill                    │
└─────────────────┬─────────────────┘
                  │ distill
                  ▼
┌───────────────────────────────────────┐
│        Semantic Wiki (長期)            │
│  - Entities + Relationships          │
│  - 精煉後嘅知識                       │
└─────────────────┬─────────────────────┘
                  │ distill
                  ▼
┌───────────────────────────────────────┐
│     Procedural Memory (技能)           │
│  - Skills + Workflows                │
│  - 如何做嘢                             │
└───────────────────────────────────────┘
```

### 7.2 Distill 過程

```python
def distill_episodic(episodic_memory, days_threshold=7):
    """
    將 old episodic memories distill 成 semantic knowledge
    """
    old_memories = [m for m in episodic_memory 
                     if m.age > days_threshold]
    
    entities = extract_entities(old_memories)
    relationships = extract_relationships(old_memories)
    insights = extract_insights(old_memories)
    
    # 寫入 Semantic Wiki
    for entity in entities:
        wiki.add_entity(entity)
    for rel in relationships:
        wiki.add_relationship(rel)
    
    # 從 Episodic Buffer 移除
    episodic_memory.remove(old_memories)
    
    return (entities, relationships, insights)
```

### 7.3 點解要用三層？

| 層 | 特點 | 用途 |
|----|------|------|
| Episodic | Raw, 詳細 | 記錄原始對話 |
| Semantic | 結構化, 壓縮 | 知識表示 |
| Procedural | 技能, workflows | 如何做嘢 |

---

## 8. Uncertainty Tracking 原理

### 8.1 EQS Framework

```
O: Observe — 接收新資訊
O: Orient — 理解、更新 confidence
D: Decide — 決定係咪更新
A: Act — 更新記憶
```

### 8.2 Claim 結構

```python
class Claim:
    def __init__(self, content, confidence, source, evidence=None):
        self.content = content
        self.confidence = confidence  # 0.0 - 1.0
        self.source = source
        self.evidence = evidence or []
        self.created_at = now()
        self.last_updated = now()
```

### 8.3 Confidence Decay

```python
HALF_LIVES = {
    'fact': 30,       # 事實 30日 half-life
    'opinion': 7,     # 意見 7日
    'news': 3,        # 新聞 3日
    'project_status': 14,  # 項目狀態 14日
}

def decay_confidence(claim, days_elapsed):
    half_life = HALF_LIVES.get(claim.type, 30)
    decay_factor = 0.5 ** (days_elapsed / half_life)
    return claim.confidence * decay_factor
```

### 8.4 Uncertainty Reasons

```python
UNCERTAINTY_REASONS = [
    'source_unreliable',      # source 唔可靠
    'outdated',               # 資訊過時
    'contradictory',          # 同其他 claims 矛盾
    'insufficient_evidence', # evidence 唔夠
]
```

---

## 9. Entity Type System 原理

### 9.1 Type Hierarchy

```
Entity
├── Person (人)
│   └── 期哥
├── Project (項目)
│   └── 古洞站
├── System (系統/工具)
│   ├── 阿星
│   └── OCM Sup
├── Concept (概念)
│   └── 記憶系統
└── Document (文檔)
    └── 某篇 article
```

### 9.2 Type Compatibility Matrix

```python
COMPATIBILITY_MATRIX = {
    ('person', 'project'): True,      # 人可以參與項目
    ('person', 'system'): True,       # 人可以使用系統
    ('person', 'concept'): False,     # 人唔係概念
    ('project', 'system'): True,     # 項目可以用系統
    ('project', 'concept'): False,   # 項目唔係概念
    ('system', 'concept'): True,     # 系統可以實現概念
}
```

### 9.3 Type-based Filtering

```python
def filter_incompatible(results, query_entity_type):
    filtered = []
    for result in results:
        result_type = result.entity_type
        if COMPATIBILITY_MATRIX.get((query_entity_type, result_type), True):
            filtered.append(result)
    return filtered
```

---

## 10. Implementation Details

### 10.1 Project Structure

```
OCM-Sup/
├── scripts/
│   ├── triple_stream_search.py    # 三流搜索核心
│   ├── query_expansion.py          # 查詢擴展
│   ├── graph_search.py             # 圖譜搜索
│   ├── kg_auto_expander.py        # KG 自動擴展
│   ├── smart_recall_hook.py        # 智能觸發
│   ├── smart_recall_cron.py       # 定時任務
│   ├── search_api.py              # HTTP API
│   ├── proactive_discovery.py      # 主動發現
│   └── graph_visualization.py     # 可視化
├── wiki/
│   ├── ai-agent/
│   │   └── entities/             # Entity files
│   └── ...                        # Other docs
└── tests/
```

### 10.2 Dependencies

```txt
rank-bm25>=1.2.0        # BM25 implementation
sentence-transformers    # Vector embeddings
flask>=2.0               # HTTP API
pyyaml                   # Frontmatter parsing
numpy                    # Numerical operations
```

### 10.3 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/search` | GET | 搜索 `?q=query&top_k=5` |
| `/entities` | GET | 列出所有 entities |
| `/stats` | GET | 搜索統計 |
| `/health` | GET | 健康檢查 |

### 10.4 Performance Considerations

| Operation | Complexity | 優化 |
|----------|------------|------|
| BM25 Search | O(n log n) | 倒排索引 |
| Vector Search | O(n × d) | 預先計算 embeddings |
| Graph Traversal | O(V + E) | BFS, depth limit |
| RRF Fusion | O(n × k) | k channels |

---

## 📚 延伸閱讀

- [BM25 Algorithm](https://en.wikipedia.org/wiki/Okapi_BM25)
- [Sentence Transformers](https://www.sbert.net/)
- [Reciprocal Rank Fusion](https://plg.uwaterloo.ca/~gvcormac/cormacks09-rrf.pdf)
- [Knowledge Graphs](https://en.wikipedia.org/wiki/Knowledge_graph)
- [Confidence Tracking in AI](https://arxiv.org/abs/2401.14015)

---

_技術文檔最後更新：2026-04-18_
_OCM Sup v2.0_