# OCM Sup - OpenClaw Memory System

> 🧠 Jacky's Intelligent Memory System — Combining Triple-Stream Search + Knowledge Graph + Proactive Discovery

[![Status](https://img.shields.io/badge/status-production_ready-green.svg)](#)
[![OCM Sup](https://img.shields.io/badge/OCM%20Sup-v2.0-blue.svg)](#)

[![View on GitHub](https://img.shields.io/badge/GitHub-Repo-green.svg)](https://github.com/st007097-coder/ocm-sup)

## 🔗 Quick Links

| Document | Description | English Version |
|----------|-------------|-----------------|
| [README.md](README.md) | 📖 Main documentation (this one) | [English](README-en.md) |
| [TECHNICAL.md](TECHNICAL.md) | 🔬 Technical Principles + Algorithms | [English](TECHNICAL-en.md) |
| [CHANGELOG.md](CHANGELOG.md) | 📅 Evolution History + Decision Process | [English](CHANGELOG-en.md) |
| [TEST-REPORT.md](TEST-REPORT.md) | 🧪 Test Results + Bug Fixes | [English](TEST-REPORT-en.md) |
| [cover.webp](cover.webp) | 🖼️ Cover Image |

---

## ⚠️ Important Note: About This Project

**This is not meant to be copied as-is.**

Everyone, every Agent, and every use case is different. Jacky is a Hong Kong QS (Quantity Surveyor), and the system I use is based on his:

- **Nature of work** — Engineering project management, cost estimation
- **Technical background** — Interested in AI but not an engineer
- **Usage habits** — Cantonese, Telegram, Obsidian
- **Time resources** — Spare time, building gradually

**How you should use this project:**

1. **Understand the principles** — Why does OCM Sup need Triple-Stream? Because single search methods aren't good enough
2. **Take what you need** — You might only need one or two scripts
3. **Modify for your situation** — Your memory system should serve your needs, not copy all features
4. **What you think up is truly yours** — My evolution direction doesn't mean it's right for you, what you figure out yourself is best

**You don't need:**
- To completely copy my architecture
- To use all 9 scripts
- To follow my timeline exactly

**You need:**
- To understand your actual needs
- To choose the right technical solutions for you
- To think and adjust for yourself

> _"Copying is the last form of learning, but creating is the first form of thinking."_

---

## 🎯 Pain Points and Solutions

> **Every feature exists to solve a real problem.**

---

### 1. Triple-Stream Search

#### 📍 Scenario

Jacky asks: "How's the Kwu Tung Station project going?"

#### 😣 Pain Points

| Problem | Description |
|---------|-------------|
| Single search method has poor results | Vector Search only knows "relevance", not "Jacky → works_on → Kwu Tung Station" |
| Chinese-English mixed queries perform poorly | Chinese "古洞站" and English "Kwu Tung Station" don't return the same results |
| High false positives | Vector search incorrectly returns "Jacky" just because they often appear together in training data |

#### ✅ Solution

Triple fusion: `BM25 + Vector + Graph`

```
Query: Kwu Tung Station

BM25: Exact keyword match for "Kwu Tung Station"
Vector: Understands concepts related to "station construction", "MTR project"
Graph: Discovers "Jacky → works_on → Kwu Tung Station" relationship

→ Combine results from three channels (RRF Fusion)
```

#### 📝 Practical Example

```
Ask: "What projects has Jacky been working on lately?"

Traditional approach:
Vector Search → Returns a bunch of relevant but scattered documents

Triple fusion:
1. BM25 finds documents containing "Jacky" and "project"
2. Vector finds semantically related "QS work", "cost estimation"
3. Graph discovers: Jacky → works_on → Kwu Tung Station

→ Returns: Coherent results related to Kwu Tung Station project
```

---

### 2. Knowledge Graph

#### 📍 Scenario

Jacky asks: "Does Star know I'm a QS?"

#### 😣 Pain Points

| Problem | Description |
|---------|-------------|
| Information fragmentation | The fact "Jacky is a QS" is scattered across various documents |
| Relationships unclear | Even if you find Jacky, you don't know their relationship with Kwu Tung Station or OCM Sup |
| Requires manual maintenance | You have to remember who's connected to whom, easy to miss things |

#### ✅ Solution

Build an Entity relationship graph:

```
       ┌──────┐
       │ Jacky  │ (person)
       └──┬───┘
    works_on│
      ┌─────┴─────┐
      ▼           ▼
┌──────────┐  ┌──────┐
│ Kwu Tung  │  │ Star  │
│  Station  │  │(system)│
└────┬─────┘  └───┬──┘
     │             │
     │ uses       │ integrates_with
     ▼             ▼
┌─────────────────────┐
│      OCM Sup        │
│      (system)       │
└─────────────────────┘
```

#### 📝 Practical Example

```
Ask: "Why does Star know about Kwu Tung Station?"

Without Graph:
→ Star says "I searched for documents about Kwu Tung Station"

With Graph:
→ Star says "Because Jacky works_on Kwu Tung Station, and Star serves Jacky,
   so I remember that Kwu Tung Station is in Jacky's projects"
```

---

### 3. Smart Recall Hook

#### 📍 Scenario

Jacky asks: "What's the latest progress on Kwu Tung Station?"

#### 😣 Pain Points

| Problem | Description |
|---------|-------------|
| Passive waiting | If Jacky doesn't ask, Star doesn't proactively bring it up |
| Manual every time | Jacky has to remember to say "search Kwu Tung Station for me" |
| Unclear when to trigger | Which keywords should trigger search? |

#### ✅ Solution

Automatically identify queries that need triggering:

```python
HIGH_PRIORITY_KEYWORDS = [
    'Jacky', 'Kwu Tung Station', 'Star',  # Core entities
    'project', 'progress', 'update',  # Work-related
    'search', 'find', 'knowledge',     # Action keywords
]

def should_trigger(query):
    # If query contains these words, automatically trigger triple search
```

#### 📝 Practical Example

```
Without Hook:
Jacky: "How's Kwu Tung Station progress?"
Star: "Oh." (passively waiting for instructions)

With Hook:
Jacky: "How's Kwu Tung Station progress?"
Star: "Kwu Tung Station is an MTR East Rail Line project, currently in the BS (Building Survey) phase..."
    (automatically triggers triple search, provides context)
```

---

### 4. Proactive Discovery

#### 📍 Scenario

Star runs daily but finds that new AI news has nothing to do with Jacky's work, doesn't know how to use it

#### 😣 Pain Points

| Problem | Description |
|---------|-------------|
| Passive waiting for problems | If Jacky doesn't ask, Star doesn't discover anything new |
| New and old info not connected | News mentions "ChatGPT" but doesn't know how it relates to OCM Sup |
| Manually establishing relationships | Too much hassle |

#### ✅ Solution

Automatically infer relationships between Entities:

```python
# Rule engine
RELATIONSHIP_RULES = {
    ('person', 'project'): 'works_on',      # Jacky + Kwu Tung Station → works_on
    ('person', 'system'): 'uses',           # Jacky + OCM Sup → uses
    ('project', 'system'): 'uses',         # Kwu Tung Station + OCM Sup → uses
}

# Confidence calculation
confidence = base_confidence + keyword_density + type_compatibility
```

#### 📝 Practical Example

```
Proactive Discovery finds:
- News mentions "Jacky"
- News mentions "Kwu Tung Station"

Automatically infers: Jacky → works_on → Kwu Tung Station

Next time Jacky asks "What have I been doing lately":
Star: "You've been working on the Kwu Tung Station project (BS phase)"
```

---

### 5. HTTP API (Search Interface)

#### 📍 Scenario

Other systems want to use OCM Sup's search functionality but don't know how to call it

#### 😣 Pain Points

| Problem | Description |
|---------|-------------|
| Can only be used inside OpenClaw | Other tools (Telegram bot, external scripts) can't use it |
| Not a standard interface | Each script has its own way of being called |

#### ✅ Solution

Provide HTTP API:

```bash
# Any tool that can send HTTP requests can use it
curl "http://localhost:5005/search?q=Kwu+Tung+Station&top_k=5"
curl "http://localhost:5005/entities"
curl "http://localhost:5005/health"
```

#### 📝 Practical Example

```bash
# Telegram Bot usage:
Jacky: /search Kwu Tung Station
Bot: → HTTP GET /search?q=Kwu+Tung+Station
    ← JSON results
Bot: → "Kwu Tung Station is an MTR East Rail Line project..."
```

---

### 6. Graph Visualization

#### 📍 Scenario

Star says: "My Graph has 43 entities, 47 relationships"

#### 😣 Pain Points

| Problem | Description |
|---------|-------------|
| Can't see structure | Everything is text, can't tell who's at the center |
| Hard to debug | If a relationship is wrong, it's nearly impossible to discover |
| Hard to explain | It's troublesome to explain to Jacky "what the Graph looks like" |

#### ✅ Solution

Generate visual charts:

```bash
# Generate HTML interactive view
python3 graph_visualization.py --format html

# Generate Mermaid diagram
python3 graph_visualization.py --format mermaid
```

#### 📝 Practical Example

```
Graph visualization shows:

        Jacky ──works_on──→ Kwu Tung Station
           │                   │
         uses              uses │
           ▼                   ▼
        Star ←──integrates_with──→ OCM Sup

One glance shows:
- Jacky is the center (most connections)
- OCM Sup is another hub
- Kwu Tung Station and Star both connect to Jacky
```

---

### 7. Uncertainty Tracking

#### 📍 Scenario

Jacky asks: "When did you learn about OCM Sup?"

#### 😣 Pain Points

| Problem | Description |
|---------|-------------|
| Random answers | Star answers as if they remember, but actually doesn't |
| No concept of confidence | Doesn't know how much they know, doesn't know how much they don't know |
| Misleading Jacky | False confidence is worse than not remembering |

#### ✅ Solution

Each claim has metadata:

```python
claim = {
    "content": "Jacky is a QS",
    "confidence": 0.9,           # 90% sure
    "evidence": ["Wiki: Jacky.md"],
    "last_updated": "2026-04-18",
    "uncertainty_reasons": []
}

# If confidence < 0.5
if claim.confidence < 0.5:
    return "I don't remember, need to verify"
```

#### 📝 Practical Example

```
Without Uncertainty Tracking:
Jacky: "Do you know who I am?"
Star: "You're Jacky."
Jacky: "How do you know?"
Star: "I know."
(Actually doesn't remember how they know)

With Uncertainty Tracking:
Jacky: "Do you know who I am?"
Star: "You're Jacky (confidence: 95%, from: Jacky.md)"
Jacky: "How do you know?"
Star: "Because you have an entry in the Wiki, I remember you're a QS."
```

---

### 8. Consolidation Loop

#### 📍 Scenario

Star writes memory daily, but finds:
- Old memories keep accumulating, search gets slower
- Important info and junk info mixed together
- Doesn't know when to "digest" old memories

#### 😣 Pain Points

| Problem | Description |
|---------|-------------|
| Memory overload | All info is "short-term memory", no stratification |
| Info aging | 7-day-old memories might be outdated |
| Not proactively organized | Waits for user to ask before passively searching |

#### ✅ Solution

Build a three-tier memory structure:

```
Episodic Buffer (Short-term) → Semantic Wiki (Long-term) → Procedural Memory (Skills)
```

Run Consolidation Loop automatically every night:
1. Distill memories older than 7 days from Episodic Buffer
2. Extract entities, relationships, insights
3. Write to Semantic Wiki
4. Update Procedural Memory (Skills)

#### 📝 Practical Example

```
Without Consolidation Loop:
memory/2026-03-01.md ~ 2026-04-18.md
All scattered, slow to search, relationships unclear

With Consolidation Loop:
1. Daily memories written to Episodic Buffer
2. Automatically distilled after 7 days:
   "Jacky" from memory → Jacky.md (entity)
   "Jacky works_on Kwu Tung Station" → relationship
3. Wiki has structured knowledge
```

---

### 9. Content Half-lives

#### 📍 Scenario

Star finds: Old memories still appear in searches sometimes, but might be outdated

#### 😣 Pain Points

| Problem | Description |
|---------|-------------|
| No distinction between new and old info | 2019 memories have the same weight as today's memories |
| Info outdated | But still treated as "known facts" |
| False confidence | Old info still has high confidence |

#### ✅ Solution

Each claim has a "half-life":

```python
HALF_LIVES = {
    'fact': 30,        # Facts decay over 30 days
    'opinion': 7,      # Opinions over 7 days
    'news': 3,        # News over 3 days
    'project': 14,     # Project status over 14 days
}

def calculate_confidence(original_conf, days_elapsed):
    decay = 0.5 ** (days_elapsed / half_life)
    return original_conf * decay
```

#### 📝 Practical Example

```
Without half-life:
Jacky: "How's my project progress?"
Star: "Kwu Tung Station is in QS phase" (confidence: 95%)
(This might be from 3 months ago)

With half-life:
Jacky: "How's my project progress?"
Star: "Kwu Tung Station is currently in BS phase" (confidence: 70%)
Jacky: "What about before?"
Star: "Previously it was in QS phase (confidence: 35%, decayed)
```

---

### 10. Active Contradiction Detection

#### 📍 Scenario

Star finds:
- Memory says "Jacky is a QS"
- But another document says "Jacky is an engineer"
- Can't figure out which is correct

#### 😣 Pain Points

| Problem | Description |
|---------|-------------|
| Contradictions not discovered | Two sources say conflicting things |
| Misleading | Randomly picks one, what if it's wrong? |
| No mechanism to handle | Doesn't know which one to trust |

#### ✅ Solution

When contradiction is found, automatically flag:

```python
def detect_contradiction(claim_a, claim_b):
    if are_mutually_exclusive(claim_a, claim_b):
        return {
            "status": "CONTRADICTION",
            "claims": [claim_a, claim_b],
            "resolution_needed": True
        }
```

#### 📝 Practical Example

```
Without contradiction detection:
Jacky: "What do I do for a living?"
Star: "You're a QS." (randomly picked QS)
Jacky: "But you said I was an engineer before?"
Star: "Huh?"

With contradiction detection:
Jacky: "What do I do for a living?"
Star: "I found a contradiction:
   - Source A says you're a QS
   - Source B says you're an engineer
   Which is correct?"
Jacky: "QS is correct, updated"
```

---

### Summary: Why Do We Need These Features?

| Feature | Solves What Pain Point |
|---------|------------------------|
| Triple-Stream Search | Single search method has poor results |
| Knowledge Graph | Relationships unclear, info fragmented |
| Smart Recall Hook | Passive waiting, forced manual triggering |
| Proactive Discovery | Can't discover relationships between new and old info |
| HTTP API | Other systems can't use the search function |
| Graph Visualization | Can't see Graph structure |
| Uncertainty Tracking | Random answers, misleading |
| Consolidation Loop | Memory overload, not proactively organized |
| Content Half-lives | No distinction between new and old info, info outdated |
| Active Contradiction | Contradictions not discovered, misleading |

**Core Goal:** Let Star know "what", "why", "when", and "how much".

---

## 📖 Table of Contents

---

## 📖 Table of Contents

- [Introduction](#introduction)
- [⚠️ Important Note](#⚠️-important-note-about-this-project)
- [🎯 Pain Points and Solutions](#🎯-pain-points-and-solutions) ← 🆕
- [Core Features](#core-features)
- [System Architecture](#system-architecture)
- [Quick Start](#quick-start)
- [Scripts Description](#scripts-description)
- [Usage](#usage)
- [Technical Details](#technical-details)
- [Step-by-Step Tutorial](#📚-step-by-step-tutorial-build-your-own-memory-system)
- [Technical Principles](TECHNICAL.md) — **Deep understanding of principles behind each feature**
- [Evolution History](CHANGELOG.md) — **Detailed evolution + decision process + lessons**
- [Test Report](TEST-REPORT.md) — **All test results + bug fix records**
- [Credits](#credits)

---

## 🚀 Introduction

**OCM Sup** (OpenClaw Memory System Supreme) is an intelligent memory system combining multiple search technologies, designed for Jacky (Hong Kong QS professional) and his AI assistant Star.

### What Problems Does It Solve?

| Problem | Traditional Solution | OCM Sup Solution |
|---------|---------------------|------------------|
| Keyword search | BM25 only | BM25 + Vector + Graph triple fusion |
| Semantic understanding | Pure Vector Search | Chinese-English bilingual Query Expansion |
| Entity relationships | None | Knowledge Graph tracking |
| Proactive discovery | Passive query waiting | Proactive Discovery auto-discovery |
| Smart triggering | Fixed keywords | Smart Recall Hook |

---

## ✨ Core Features

### 1. Triple-Stream Search

```
Query → BM25 Channel ─┐
     → Vector Channel ─┼→ RRF Fusion → Results
     → Graph Channel ──┘
```

- **BM25 Channel**: Exact keyword matching
- **Vector Channel**: Semantic similarity search (supports Chinese-English bilingual)
- **Graph Channel**: Discover related content through Entity relationships

### 2. Knowledge Graph

- 43 Entities
- 47 Relationships
- Supports Entity Types: Person, Project, System, Concept, Document

### 3. Smart Recall Hook

Automatically identifies scenarios needing Triple-Stream Search triggering:
- Entity names: Jacky, Kwu Tung Station, Star, OCM Sup
- Keywords: search, find, knowledge, project
- Hot topics: Auto-boosted based on access frequency

### 4. Proactive Discovery

- Auto-monitor new entities
- Smart inference of relationships between Entities
- Rule engine based on Entity Types
- Multi-factor confidence calculation

### 5. HTTP API

```bash
GET /search?q=Kwu+Tung+Station&top_k=5
GET /entities
GET /stats
GET /health
```

---

## 🏗 System Architecture

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
        │ Jacky  │ (person)
        └──┬───┘
     works_on│
      ┌─────┴─────┐
      ▼           ▼
┌──────────┐  ┌──────┐
│ Kwu Tung  │  │ Star  │
│  Station  │  │(system)│
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

## ⚡ Quick Start

### Prerequisites

- Python 3.8+
- OpenClaw v2026.4.10+
- Ollama (for embeddings)

### Installation Steps

```bash
# 1. Clone repository
git clone https://github.com/st007097-coder/ocm-sup.git
cd ocm-sup

# 2. Install Python dependencies
pip install rank-bm25 sentence-transformers flask

# 3. Set up environment
export PYTHONPATH=/path/to/ocm-sup/scripts:$PYTHONPATH

# 4. Verify installation
python3 scripts/triple_stream_search.py --test
```

### Quick Test

```bash
# Search test
python3 scripts/triple_stream_search.py --query "Kwu Tung Station"

# Start API
python3 scripts/search_api.py --port 5005

# Generate graph visualization
python3 scripts/graph_visualization.py --format html
```

---

## 📜 Scripts Description

| Script | Function | Use Case |
|--------|----------|----------|
| `triple_stream_search.py` | Triple-Stream Search core | Main search functionality |
| `query_expansion.py` | Chinese-English synonym expansion | Improve search recall |
| `graph_search.py` | Entity graph search | Relationship discovery |
| `kg_auto_expander.py` | Auto-expand Knowledge Graph | Discover new entities |
| `smart_recall_hook.py` | Smart triggering hook | Auto-identify search needs |
| `smart_recall_cron.py` | Scheduled prewarming script | Periodic context preloading |
| `search_api.py` | Flask HTTP API | Other system calls |
| `proactive_discovery.py` | Proactive discovery engine | Auto relationship inference |
| `graph_visualization.py` | Graph visualization | Generate Mermaid/HTML |

---

## 📖 Usage

### 1. Triple-Stream Search

```python
import sys
sys.path.insert(0, 'scripts')
from triple_stream_search import TripleStreamSearch

search = TripleStreamSearch('/path/to/wiki')
results = search.search('Kwu Tung Station', top_k=5)

for r in results:
    print(f"[{r['sources']}] {r['title']}")
    print(f"   Path: {r['path']}")
    print(f"   RRF Score: {r['rrf_score']:.4f}")
```

**Sample Output:**
```
[bm25+vector+graph] Kwu Tung Station
   Path: ai-agent/entities/Kwu Tung Station.md
   RRF Score: 0.1827
[bm25+vector+graph] Star
   Path: ai-agent/entities/Star.md
   RRF Score: 0.1563
```

### 2. Smart Recall Hook

```python
from smart_recall_hook import SmartRecallHook

hook = SmartRecallHook()

# Auto-identify whether triggering is needed
if hook.should_trigger('Kwu Tung Station project progress'):
    results = hook.recall('Kwu Tung Station')
    context = hook.inject_into_context(results)
    print(context)
```

**Trigger Conditions:**
- Entity names: Jacky, Kwu Tung Station, Star, OCM Sup
- Keywords: search, find, knowledge, project
- Hot topics: High-frequency queries

### 3. HTTP API

```bash
# Start API
python3 scripts/search_api.py --port 5005

# Search
curl "http://localhost:5005/search?q=Kwu+Tung+Station&top_k=5"

# Health check
curl http://localhost:5005/health
```

**API Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/search` | GET | Search |
| `/entities` | GET | List all entities |
| `/stats` | GET | Search statistics |
| `/health` | GET | Health check |

### 4. Proactive Discovery

```bash
# Full scan
python3 scripts/proactive_discovery.py --report

# Continuous monitoring
python3 scripts/proactive_discovery.py --watch --interval 300

# Apply suggestions
python3 scripts/proactive_discovery.py --apply
```

**Relationship Inference Rules:**

| From | To | Relationship | Confidence |
|------|----|--------------|------------|
| person | project | works_on | 90% |
| person | system | uses | 80% |
| project | person | involves | 80% |
| system | system | integrates_with | 80% |

### 5. Graph Visualization

```bash
# Generate HTML visualization
python3 scripts/graph_visualization.py --format html

# Focus on specific entity
python3 scripts/graph_visualization.py --focus Jacky --depth 2

# Mermaid format
python3 scripts/graph_visualization.py --format mermaid
```

---

## 🔬 Technical Details

### RRF (Reciprocal Rank Fusion)

```python
RRF_score(d) = Σ 1 / (k + rank_i(d))

# k=60 is the industry standard
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

## 📈 Evolution History

### Timeline

| Date | Version | Content |
|------|---------|---------|
| 2026-03-29 | v1.0 | Star born, basic search |
| 2026-04-11 | v1.1 | Triple-Stream Search Phase 1-5 |
| 2026-04-13 | v1.2 | 7-Dir 1, 2 integration |
| 2026-04-15 | v1.3 | 7-Dir 4 KG Auto-Expansion |
| 2026-04-17 | v1.4 | Phase Z (Uncertainty Tracking + EQS) |
| **2026-04-18** | **v2.0** | **Complete Roadmap Done** |

### Roadmap Completion Status

| # | Direction | Status | Completion |
|---|-----------|--------|------------|
| Phase 1-5 | Triple-Stream Search | ✅ | 100% |
| 7-Dir 1 | Memory System Integration | ✅ | 100% |
| 7-Dir 2 | Wiki Search | ✅ | 100% |
| 7-Dir 3 | Search API | ✅ | 100% |
| 7-Dir 4 | KG Auto-Expansion | ✅ | 100% |
| 7-Dir 5 | Smart Recall | ✅ | 100% |
| 7-Dir 6 | Proactive Discovery | ✅ | 100% |
| 7-Dir 7 | Graph Visualization | ✅ | 100% |

**Total Completion: 7/7 = 100%** 🎉

---

## 📊 System Status

### Test Results (2026-04-18)

| Test Item | Result |
|-----------|--------|
| Triple-Stream Search | ✅ PASS |
| Knowledge Graph | ✅ PASS (43 nodes, 47 edges) |
| Smart Recall Hook | ✅ PASS (5/5) |
| Search API | ✅ PASS |
| Proactive Discovery | ✅ PASS (0 new suggestions) |
| Graph Visualization | ✅ PASS |
| Entity Files | ✅ PASS (0 frontmatter issues) |

### System Metrics

| Metric | Value |
|--------|-------|
| Entities | 43 |
| Relationships | 47 |
| Document Types | 5 (person, project, system, concept, document_title) |
| Relationship Types | 5 (works_on, uses, involves, integrates_with, related_to) |

---

## 📚 Step-by-Step Tutorial: Build Your Own Memory System

> ⚠️ **Important reminder**: This is a general direction, not a checklist you must follow exactly.
> Everyone's situation is different, you should adjust according to your needs.

---

### Step 1: Know Yourself

Before building any system, understand who you're serving:

```
Ask yourself:
1. Who am I? (role, background)
2. What domain do I serve? (professional field)
3. What language do I use? (Cantonese/Mandarin/English)
4. What tools do I have? (Telegram/Obsidian/Notion)
5. How much time do I have? (part-time/full-time)
```

**Why do you need to know these?**
- Your system should serve you, not you serve your system
- Example: Jacky is a Hong Kong QS, uses Cantonese, primarily uses Telegram + Obsidian

---

### Step 2: Choose Search Solution

**Question**: How does your AI assistant remember things?

| Solution | Pros | Cons | Who it's for |
|----------|------|------|--------------|
| Pure Vector Search | Simple | Slow, many false positives | Small scale, simple needs |
| Pure BM25 | Fast, accurate | Doesn't understand semantics | Only need keywords |
| **Triple fusion** | Balances all methods | Needs more setup | **Most cases** |

**Why triple fusion?**
```
BM25: "Kwu Tung Station" → Exact match for "Kwu Tung Station"
Vector: "Kwu Tung Station" → Understands "station construction" related concepts
Graph: "Kwu Tung Station" → Jacky(person) → QS(profession)
```

If you only need simple search, you can just use BM25.

---

### Step 3: Design Entity Relationships

**Question**: What entities does your system need to track?

**Steps**:
```
1. List core entities
   - People (yourself, your users)
   - Projects (projects you participate in)
   - Systems (tools/services you use)


2. Define relationship types
   - works_on: who works on which project
   - uses: who uses which tool
   - part_of: what is part of what

3. Create entity files
   One .md file per entity, containing:
   - title, type, entity_type
   - relationships
   - description
```

**Jacky's example**:
```yaml
# Jacky.md
---
title: Jacky
entity_type: person
relationships:
  - target: Kwu Tung Station
    type: works_on
---

# Kwu Tung Station.md
---
title: Kwu Tung Station
entity_type: project
relationships:
  - target: Jacky
    type: involves
---
```

---

### Step 4: Implement Triple-Stream Search

**If you choose triple fusion**:
```python
# 1. BM25 Channel - Keyword matching
from rank_bm25 import BM25Okapi

# 2. Vector Channel - Semantic matching
from sentence_transformers import SentenceTransformer

# 3. Graph Channel - Relationship matching
# Read entity files, build graph

# 4. RRF Fusion
def rrf_fusion(results_dict, k=60):
    scores = defaultdict(float)
    for channel, results in results_dict.items():
        for rank, item in enumerate(results):
            scores[item] += 1 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**What about mixed languages?**
If you use Chinese-English mix:
```python
# Query Expansion
def expand_query(query):
    synonyms = {
        'Kwu Tung Station': ['Kwu Tung Station', '古洞站', 'gutong'],
        'AI assistant': ['AI assistant', 'AI助手', '助手'],
    }
    expanded = [query]
    for term, alts in synonyms.items():
        if term in query:
            expanded.extend(alts)
    return expanded
```

---

### Step 5: Add Smart Triggering (Smart Recall)

**Question**: You don't want to manually search every time, you want AI to proactively remember things.

**Solution**:
```python
# Smart Recall Hook
HIGH_PRIORITY_KEYWORDS = [
    'search', 'find', 'locate',
    'Jacky', 'Kwu Tung Station', 'Star',
    'project', 'knowledge', 'entity',
]

def should_trigger(query):
    query_lower = query.lower()
    for keyword in HIGH_PRIORITY_KEYWORDS:
        if keyword in query_lower:
            return True
    return False
```

**Adjust KEYWORDS based on YOUR entities**:
```python
MY_ENTITIES = ['Jacky', 'Kwu Tung Station', 'Star']
HIGH_PRIORITY_KEYWORDS.extend(MY_ENTITIES)
```

---

### Step 6: Build Proactive Discovery

**Question**: Passive query waiting is too slow, you want the system to proactively discover new info.

**Solution**:
```python
# Proactive Discovery Engine

# 1. Rule-based Relationship Inference
RELATIONSHIP_RULES = {
    ('person', 'project'): 'works_on',
    ('person', 'system'): 'uses',
    ('project', 'person'): 'involves',
}

# 2. Multi-factor Confidence
def calculate_confidence(base, keyword_density, type_compat):
    return min(base + keyword_density*0.2 + type_compat*0.1, 0.95)

# 3. Bidirectional Check
# Ensure both A→B and B→A are considered
```

---

### Step 7: Visualization

**Question**: How do you know how big your Graph is?

**Solution**:
```bash
# Generate Mermaid diagram
python3 graph_visualization.py --format mermaid

# Or generate HTML interactive view
python3 graph_visualization.py --format html
```

**What you should see**:
- How many nodes
- How many edges
- Who's the central node (most connections)

---

### Step 8: Continuous Optimization

**Remember**: The system is evolution, not built all at once.

```
Weekly review:
1. Are search results correct?
2. Any new entities to add?
3. Any relationships missed?
4. Which feature is most used?

Adjust as needed:
- If you don't need a channel, remove it
- If you have new entity types, add them
```

---

### Step 9: FAQ

**Q: Should I use all scripts?**
A: No. Pick what you need. If you want to upgrade search, add triple fusion. If you just want quick search, BM25 is enough.

**Q: What about mixed Chinese and English?**
A: Query expansion + entity-type filtering. See Step 4 for details.

**Q: How often to update entities?**
A: Daily or weekly recommended, depending on your data volume.

---

### Summary: Why Step-by-Step?

> Because you can't build a perfect system all at once.
> Everyone's starting point is different, the features you need are different.

**Recommended path**:
```
1. Know yourself (Step 1)
2. Choose search solution (Step 2)
3. Design entities (Step 3)
4. Implement search (Step 4)
5. Add smart triggering (Step 5)
6. Proactive discovery (Step 6) - can skip
7. Visualization (Step 7) - can skip
8. Continuous optimization (Step 8)
```

**Most importantly**:
- Don't copy, think
- Don't do it all at once, iterate
- Don't aim for perfect, aim for working

---

## 🙏 Credits

### Inspiration Sources

- **Andrej Karpathy** - Programming Principles (Simplicity First, Surgical Changes)
- **Aporia Labs** - LLM Wiki v2 (Confidence Scoring, Supersession, Forgetting)
- **Anthropic** - OODA Loop / CraniMem Architecture
- **Jacky** - QS professional, requirements originator for the entire system

### Tech Stack

- **OpenClaw** - AI Assistant Framework
- **BM25 (rank_bm25)** - Keyword Search
- **Sentence Transformers** - Vector Embeddings
- **Flask** - HTTP API
- **Mermaid.js** - Diagram rendering

### Main Contributors

- **Jacky** - Product design, requirements
- **Star** - System development, algorithm implementation

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🔗 Links

- [GitHub Repository](https://github.com/st007097-coder/ocm-sup)
- [OpenClaw Docs](https://docs.openclaw.ai)
- [Jacky's GitHub](https://github.com/st007097-coder)

---

_Last updated: 2026-04-18_
_OCM Sup v2.0 - Production Ready_ 🚀
