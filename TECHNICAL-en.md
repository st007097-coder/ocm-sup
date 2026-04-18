# OCM Sup — Technical Documentation

> 📚 Deep dive into the原理 behind each feature

---

## 📖 Table of Contents

1. [System Overview](#1-system-overview)
2. [Triple-Stream Search Principle](#2-triple-stream-search-principle)
3. [Knowledge Graph Principle](#3-knowledge-graph-principle)
4. [RRF Fusion Principle](#4-rrf-fusion-principle)
5. [Smart Recall Hook Principle](#5-smart-recall-hook-principle)
6. [Proactive Discovery Principle](#6-proactive-discovery-principle)
7. [Consolidation Loop Principle](#7-consolidation-loop-principle)
8. [Uncertainty Tracking Principle](#8-uncertainty-tracking-principle)
9. [Entity Type System Principle](#9-entity-type-system-principle)
10. [Implementation Details](#10-implementation-details)

---

## 1. System Overview

### 1.1 Core Problem

**Problem:** How does an AI assistant effectively access and utilize long-term memory?

Traditional approaches:
- Vector Search → semantic relevance, but doesn't understand structural relationships
- Pure Keyword → precise, but doesn't understand semantics
- Pure Graph → clear relationships, but requires pre-establishment

**OCM Sup Solution:** Triple Fusion + Smart Trigger + Proactive Discovery

```
┌─────────────────────────────────────────────────────┐
│                    User Query                        │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│              Smart Recall Hook                       │
│         (should_trigger automatic detection)          │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│           Triple-Stream Search                        │
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

### 1.2 Data Flow

```
Wiki (MD files)
    │
    ├── Entities/Relationships ──→ Graph Channel
    ├── Documents ──────────────→ BM25 Index
    └── Documents ──────────────→ Vector Embeddings
```

---

## 2. Triple-Stream Search Principle

### 2.1 BM25 Channel

**Principle:** Best Matching 25, a ranking function based on term frequency

```python
BM25(doc, query) = Σ IDF(t) × (tf(t,doc) × (k1+1)) / (tf(t,doc) + k1 × (1-b+b×|doc|/avgdl))
```

**Parameters:**
- `k1 = 1.5` — term frequency saturation control
- `b = 0.75` — document length normalization

**Why BM25:**
- Precise keyword matching
- Fast (inverted index)
- Not affected by spelling variations

### 2.2 Vector Channel

**Principle:** Map text to high-dimensional vectors, similar content has similar vectors

```python
embedding = model.encode(text)  # e.g., 768-dim vector
similarity = cos(embedding_q, embedding_d)
```

**Model:** Sentence Transformers (e.g., `all-MiniLM-L6-v2`)

**Problem:** Embedding models have language bias

```
Chinese "古洞站" and "Kwu Tung Station" vectors may not be similar
because training data lacks sufficient Chinese-English correspondence
```

**Solution:** Query Expansion + Multi-stage Filtering

### 2.3 Graph Channel

**Principle:** Discover related content based on pre-defined relationships between Entities

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

## 3. Knowledge Graph Principle

### 3.1 Entity Structure

```yaml
# jacky-evolution.md (期哥)
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

| Type | Description | Example |
|------|-------------|---------|
| person | Person | 期哥 |
| project | Project | 古洞站 |
| system | System/Tool | OCM Sup, 阿星 |
| concept | Concept | 記憶系統 |
| document_title | Document | Some article |

### 3.3 Relationship Types

| Type | From | To | Example |
|------|------|----|---------|
| works_on | person | project | 期哥 → 古洞站 |
| uses | person | system | 期哥 → 阿星 |
| involves | project | person | 古洞站 → 期哥 |
| part_of | component | whole | 阿星 → OCM Sup |
| related_to | any | any | General relationship |

### 3.4 Type Compatibility

Different entity types have compatibility restrictions:

```python
INCOMPATIBLE_PAIRS = [
    ('person', 'concept'),    # person is not a concept
    ('person', 'technology'), # person is not a tool (but can use tools)
    ('project', 'concept'),  # project is not a concept
]

def is_compatible(entity_a, entity_b):
    """Check if two entity types are compatible"""
    return (entity_a.type, entity_b.type) not in INCOMPATIBLE_PAIRS
```

**Principle:**
- High vector similarity but type incompatibility = false positive
- Should be filtered out

---

## 4. RRF Fusion Principle

### 4.1 Problem

Three channels return different rankings, how to merge them?

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

Where `k = 60` (industry standard).

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

### 4.4 Why RRF Works So Well

- **Balances channel strengths and weaknesses**
- **Prevents single channel from dominating**
- **Simple but effective**
- **Robust** — if one channel is wrong, it won't destroy the overall result

---

## 5. Smart Recall Hook Principle

### 5.1 Problem

Does a user query need to trigger triple search?

### 5.2 Trigger Conditions

```python
HIGH_PRIORITY_KEYWORDS = {
    # Entity names
    '期哥', '古洞站', '阿星', 'OCM Sup',
    # Action keywords
    'search', 'find', '搵', '知識', '記得',
    # Project keywords
    'project', '項目', '進度', '進展',
}

def should_trigger(query):
    query_lower = query.lower()
    for keyword in HIGH_PRIORITY_KEYWORDS:
        if keyword in query_lower:
            return True
    return False
```

### 5.3 Why Trigger?

**Benefits:**
- Saves resources (don't need triple search every time)
- Ensures important queries get sufficient resources
- Provides better context

### 5.4 Post-Trigger Flow

```python
def recall_with_hook(query):
    if should_trigger(query):
        # Full triple search
        results = triple_stream_search(query)
        context = build_context(results)
        return context
    else:
        # Simple response
        return basic_response(query)
```

---

## 6. Proactive Discovery Principle

### 6.1 Problem

Passive waiting for user questions, when does the system proactively discover new information?

### 6.2 Relationship Inference

Infer relationships based on entity types:

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
# Avoid duplicate suggestions
def relationship_exists(entity_a, entity_b):
    # Check A → B
    if entity_b in entity_a.outgoing_neighbors:
        return True
    # Check B → A
    if entity_a in entity_b.outgoing_neighbors:
        return True
    return False
```

---

## 7. Consolidation Loop Principle

### 7.1 Three-Layer Memory

```
┌───────────────────────────────────────┐
│        Episodic Buffer (Short-term)   │
│  - Daily raw memory                   │
│  - Distill after 7 days               │
└─────────────────┬─────────────────────┘
                  │ distill
                  ▼
┌───────────────────────────────────────┐
│        Semantic Wiki (Long-term)      │
│  - Entities + Relationships          │
│  - Refined knowledge                  │
└─────────────────┬─────────────────────┘
                  │ distill
                  ▼
┌───────────────────────────────────────┐
│     Procedural Memory (Skills)         │
│  - Skills + Workflows                 │
│  - How to do things                    │
└───────────────────────────────────────┘
```

### 7.2 Distill Process

```python
def distill_episodic(episodic_memory, days_threshold=7):
    """
    Distill old episodic memories into semantic knowledge
    """
    old_memories = [m for m in episodic_memory 
                     if m.age > days_threshold]
    
    entities = extract_entities(old_memories)
    relationships = extract_relationships(old_memories)
    insights = extract_insights(old_memories)
    
    # Write to Semantic Wiki
    for entity in entities:
        wiki.add_entity(entity)
    for rel in relationships:
        wiki.add_relationship(rel)
    
    # Remove from Episodic Buffer
    episodic_memory.remove(old_memories)
    
    return (entities, relationships, insights)
```

### 7.3 Why Three Layers?

| Layer | Characteristics | Use |
|-------|----------------|-----|
| Episodic | Raw, detailed | Record original conversations |
| Semantic | Structured, compressed | Knowledge representation |
| Procedural | Skills, workflows | How to do things |

---

## 8. Uncertainty Tracking Principle

### 8.1 EQS Framework

```
O: Observe — Receive new information
O: Orient — Understand, update confidence
D: Decide — Decide whether to update
A: Act — Update memory
```

### 8.2 Claim Structure

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
    'fact': 30,       # Fact 30-day half-life
    'opinion': 7,     # Opinion 7-day
    'news': 3,       # News 3-day
    'project_status': 14,  # Project status 14-day
}

def decay_confidence(claim, days_elapsed):
    half_life = HALF_LIVES.get(claim.type, 30)
    decay_factor = 0.5 ** (days_elapsed / half_life)
    return claim.confidence * decay_factor
```

### 8.4 Uncertainty Reasons

```python
UNCERTAINTY_REASONS = [
    'source_unreliable',      # source is unreliable
    'outdated',               # information is outdated
    'contradictory',          # contradicts other claims
    'insufficient_evidence', # insufficient evidence
]
```

---

## 9. Entity Type System Principle

### 9.1 Type Hierarchy

```
Entity
├── Person
│   └── 期哥
├── Project
│   └── 古洞站
├── System (System/Tool)
│   ├── 阿星
│   └── OCM Sup
├── Concept
│   └── 記憶系統
└── Document
    └── Some article
```

### 9.2 Type Compatibility Matrix

```python
COMPATIBILITY_MATRIX = {
    ('person', 'project'): True,      # person can participate in project
    ('person', 'system'): True,       # person can use system
    ('person', 'concept'): False,     # person is not a concept
    ('project', 'system'): True,     # project can use system
    ('project', 'concept'): False,   # project is not a concept
    ('system', 'concept'): True,     # system can implement concept
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
│   ├── triple_stream_search.py    # Core search engine
│   ├── query_expansion.py          # Query expansion
│   ├── graph_search.py             # Graph search
│   ├── kg_auto_expander.py        # KG auto expansion
│   ├── smart_recall_hook.py        # Smart trigger
│   ├── smart_recall_cron.py       # Cron jobs
│   ├── search_api.py              # HTTP API
│   ├── proactive_discovery.py      # Proactive discovery
│   └── graph_visualization.py     # Visualization
├── wiki/
│   └── ai-agent/
│       └── entities/             # Entity files
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
| `/search` | GET | Search `?q=query&top_k=5` |
| `/entities` | GET | List all entities |
| `/stats` | GET | Search statistics |
| `/health` | GET | Health check |

### 10.4 Performance Considerations

| Operation | Complexity | Optimization |
|-----------|-------------|---------------|
| BM25 Search | O(n log n) | Inverted index |
| Vector Search | O(n × d) | Pre-computed embeddings |
| Graph Traversal | O(V + E) | BFS, depth limit |
| RRF Fusion | O(n × k) | k channels |

---

## 📚 Further Reading

- [BM25 Algorithm](https://en.wikipedia.org/wiki/Okapi_BM25)
- [Sentence Transformers](https://www.sbert.net/)
- [Reciprocal Rank Fusion](https://plg.uwaterloo.ca/~gvcormac/cormacks09-rrf.pdf)
- [Knowledge Graphs](https://en.wikipedia.org/wiki/Knowledge_graph)
- [Confidence Tracking in AI](https://arxiv.org/abs/2401.14015)

---

_Last updated: 2026-04-18_
_OCM Sup v2.0_