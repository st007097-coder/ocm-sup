![OCM Sup Social Preview](https://raw.githubusercontent.com/st007097-coder/ocm-sup/main/cover.webp)

# OCM Sup — OpenClaw Memory System

> 🧠 Jacky's Intelligent Memory System — Triple-Stream Search + Knowledge Graph + Proactive Discovery

[![Status](https://img.shields.io/badge/status-production_ready-green.svg)](#)
[![OCM Sup](https://img.shields.io/badge/OCM%20Sup-v2.0-blue.svg)](#)
[![View on GitHub](https://img.shields.io/badge/GitHub-Repo-green.svg)](https://github.com/st007097-coder/ocm-sup)

## 🔗 Quick Links

| Document | Description | Language |
|----------|-------------|----------|
| [README.md](README.md) | 📖 English version (this page) | English |
| [README_粵語.md](README_粵語.md) | 📖 Cantonese version | 粵語 |
| [README_中文.md](README_中文.md) | 📖 Simplified Chinese (Formal) | 書面語 |
| [TECHNICAL.md](TECHNICAL-en.md) | 🔬 Technical documentation | English |
| [CHANGELOG.md](CHANGELOG-en.md) | 📅 Evolution history | English |
| [TEST-REPORT.md](TEST-REPORT-en.md) | 🧪 Test results | English |
| [cover.webp](cover.webp) | 🖼️ Cover image | |

---

## ⚠️ Important Notice: About This Project

**This is not meant for you to copy.**

Everyone, every Agent, every use case is different. Jacky is a Hong Kong QS (Quantity Surveyor). His system is based on:

- **Work Nature** — Engineering project management, cost estimation
- **Technical Background** — Interested in AI but not an engineer
- **Usage Habits** — Cantonese, Telegram, Obsidian
- **Time Resources** — Spare time, built slowly

**How you should use this project:**

1. **Understand the principles** — Why does OCM Sup need Triple-Stream? Because single search methods are insufficient
2. **Take what you need** — You might only need one or two scripts
3. **Modify for your situation** — Your memory system should serve your needs, not copy all features
4. **Your own ideas are yours** — My evolution direction doesn't mean it's right for you

**You don't need:**
- To completely copy my architecture
- To use all 9 scripts
- To follow my exact timeline

**You need:**
- To understand your actual needs
- To choose the right technical solution for you
- To think and adjust yourself

> _「Copying is the last form of learning, but creating is the first form of thinking.」_

---

## 🎯 Pain Points & Solutions

> **Every feature exists to solve a real problem.**

---

### 1. Triple-Stream Search

#### 📍 Scenario

Jacky asks: "How's the Kwu Tung Station project progressing?"

#### 😣 Pain Points

| Problem | Description |
|---------|-------------|
| Single search methodpoor results | Vector Search only knows "related", doesn't know "Jacky → works_on → Kwu Tung Station" |
| 中英混合not effective | Chinese "Kwu Tung Station" and English "Kwu Tung Station" don't search to the same result |
| High false positives | Vector search incorrectly returns "Jacky" just because they're often together in training data |

#### ✅ Solution

Triple fusion: `BM25 + Vector + Graph`

```
Query: Kwu Tung Station

BM25: Precise keyword match for "Kwu Tung Station"
Vector: Understand related concepts like "車站建設", "MTR項目"
Graph: Discover "Jacky → works_on → Kwu Tung Station" relationship

→ Combine results from three channels (RRF Fusion)
```

---

### 2. Knowledge Graph

#### 📍 Scenario

Jacky asks: "Does Star know I'm a QS?"

#### 😣 Pain Points

| Problem | Description |
|---------|-------------|
| Information scattered | "Jacky is a QS" fact scattered across documents |
| Relationships unclear | Even if you find Jacky, you don't know his relationship with Kwu Tung Station or OCM Sup |
| Requires manual maintenance | Have to remember which connections go where, easy to miss |

#### ✅ Solution

Build Entity relationship graph:

```
       ┌──────┐
       │ Jacky  │ (person)
       └──┬───┘
    works_on│
      ┌─────┴─────┐
      ▼           ▼
┌──────────┐  ┌──────┐
│  Kwu Tung Station   │  │  Star  │
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

### 3. Smart Recall Hook

#### 📍 Scenario

Jacky asks: "What's the latest progress on Kwu Tung Station?"

#### 😣 Pain Points

| Problem | Description |
|---------|-------------|
| Passive waiting | If Jacky doesn't ask, Star doesn't proactively bring it up |
| Requires manual trigger each time | Jacky has to remember to say "search Kwu Tung Station" |
| Unknown trigger timing | Which keywords should trigger search? |

#### ✅ Solution

Automatically identify queries that need triggering:

```python
HIGH_PRIORITY_KEYWORDS = [
    'Jacky', 'Kwu Tung Station', 'Star',  # Core entities
    'project', '進度', '進展',  # Work-related
    'search', '搵', '知識',     # Action keywords
]

def should_trigger(query):
    # If query contains these words, automatically trigger triple search
```

---

### 4. Proactive Discovery

#### 📍 Scenario

System automatically discovers new entity relationships without waiting for queries.

#### 😣 Pain Points

| Problem | Description |
|---------|-------------|
| Passively waiting for questions | System only finds relationships when user asks |
| Relationships become outdated | New documents don't automatically connect to existing entities |

#### ✅ Solution

Rule-based relationship inference:

```python
RELATIONSHIP_RULES = {
    ('person', 'project'): ('works_on', 0.9),
    ('person', 'system'): ('uses', 0.8),
    ('project', 'person'): ('involves', 0.8),
    ('system', 'system'): ('integrates_with', 0.7),
}
```

---

## 📁 Project Structure

```
OCM-Sup/
├── README.md           📖 English main page
├── README_粵語.md      📖 Cantonese version
├── README_中文.md      📖 Simplified Chinese (Formal)
├── TECHNICAL.md       🔬 Technical documentation (English)
├── CHANGELOG.md       📅 Evolution history (English)
├── TEST-REPORT.md     🧪 Test results (English)
├── cover.webp         🖼️ Cover image
└── scripts/
    ├── triple_stream_search.py    Core search engine
    ├── graph_search.py             Knowledge Graph search
    ├── query_expansion.py         Chinese/English query expansion
    ├── graph_visualization.py     Graph visualization
    ├── kg_auto_expander.py        Auto entity expansion
    ├── proactive_discovery.py      Proactive relationship discovery
    ├── smart_recall_hook.py        Smart recall trigger
    ├── smart_recall_cron.py       Cron job for recall pre-warming
    ├── search_api.py               Flask HTTP API
    └── triple_stream_cli.py        CLI interface
```

---

## 🔬 System Architecture

### Triple-Stream Search

```
┌─────────────────────────────────────────────────────┐
│                    User Query                        │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│              Smart Recall Hook                       │
│         (should_trigger auto-detection)            │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│           Triple-Stream Search                       │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│  │  BM25   │  │ Vector  │  │  Graph  │            │
│  │ Channel │  │ Channel │  │ Channel │            │
│  └────┬────┘  └────┬────┘  └────┬────┘            │
│       └─────────────┼─────────────┘                  │
│                     │                              │
│                     ▼                              │
│              ┌───────────┐                         │
│              │  RRF     │                         │
│              │  Fusion  │                         │
│              └─────┬─────┘                         │
└───────────────────┼─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│                  Results                            │
│         (Ranked, Scored, Annotated)                │
└─────────────────────────────────────────────────────┘
```

### RRF Fusion Formula

```python
RRF_score(doc) = Σ 1 / (k + rank_channel(doc))
# k = 60 (industry standard)
```

---

## 🙏 Credits

- **Jacky** — Requirement proposer, tester, direction guide
- **Andrej Karpathy** — Simplicity First principle
- **Aporia Labs** — LLM Wiki v2 architecture reference
- **Anthropic** — OODA Loop / CraniMem inspiration
- **OpenClaw Community** — Framework support

---

_Last updated: 2026-04-18_
_OCM Sup v2.0_