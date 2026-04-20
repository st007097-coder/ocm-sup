# OCM-Sup Architecture Diagram

_Last Updated: 2026-04-19_

---

## System Architecture (Mermaid)

```mermaid
flowchart TB
    subgraph Input["📥 Input Layer"]
        UserQuery["User Query<br/>(中文/英文/混合)"]
    end

    subgraph Expansion["🔄 Query Expansion"]
        QE["QueryExpander"]
        CN["中文同義詞"]
        EN["英文同義詞"]
        EntityAlias["Entity Aliases<br/>(Hermes, 期哥, 阿星)"]
    end

    subgraph Search["🔍 Triple-Stream Search"]
        BM25["BM25 Search<br/>⚡ 0.4ms"]
        VEC["Vector Search<br/>🦥 102ms (with Ollama)"]
        GRAPH["Graph Search<br/>⚡ 0.7ms"]
    end

    subgraph Fusion["🔀 RRF Fusion"]
        RRF["Reciprocal Rank Fusion<br/>k=60"]
    end

    subgraph Output["📤 Output Layer"]
        Results["Top-K Results<br/>with scores + sources"]
        Explain["explain=true<br/>channel_stats + ranks"]
    end

    subgraph Memory["🧠 Memory Management"]
        LD["LastAccessed Tracker"]
        DECAY["Time-based Decay<br/>(score = 1/(1 + (age/30)^1.5))"]
        CONSOL["Consolidation Loop<br/>(episodic → semantic)"]
    end

    subgraph Schema["📋 Schema Management"]
        MIGRATE["Schema Migration<br/>(v1.0 → v1.3)"]
        VERSION["Version Tracking"]
    end

    UserQuery --> QE
    QE --> CN & EN & EntityAlias
    CN & EN --> BM25
    EntityAlias --> BM25
    UserQuery --> BM25 & VEC & GRAPH
    BM25 --> RRF
    VEC --> RRF
    GRAPH --> RRF
    RRF --> Results
    Results --> Explain
    BM25 --> LD
    LD --> DECAY
    CONSOL --> Schema
    MIGRATE --> VERSION
```

---

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant QE as Query Expansion
    participant BM25
    participant VEC as Vector
    participant GRAPH
    participant RRF
    participant Output

    User->>QE: "hermes" (English query)
    QE->>BM25: "hermes hermes Hermes Agent 即夢"
    QE->>VEC: "hermes hermes Hermes Agent 即夢"
    QE->>GRAPH: "hermes"

    Note over BM25: 0.4ms, keyword match<br/>aliases enable cross-lingual
    Note over VEC: 102ms, semantic similarity<br/>Ollama embedding
    Note over GRAPH: 0.7ms, entity relationships<br/>BFS traversal

    BM25->>RRF: [(doc_hermes, 3.76), (doc_jimeng, 3.66)...]
    VEC->>RRF: [(doc_jimeng, 0.954), (doc_hermes, 0.586)...]
    GRAPH->>RRF: [(doc_hermes, 0.5), (doc_openclaw, 0.3)...]

    RRF->>Output: Fused ranking with scores
    Output->>User: Top-K results with sources
```

---

## Component Responsibilities

| Component | Type | Latency | Responsibility |
|-----------|------|---------|----------------|
| QueryExpander | Module | <1ms | Chinese/English term expansion + entity aliases |
| BM25 Search | Channel 1 | 0.4ms | Keyword exact match, cross-lingual via aliases |
| Vector Search | Channel 2 | 102ms | Semantic similarity via Ollama embeddings |
| Graph Search | Channel 3 | 0.7ms | Entity relationship traversal |
| RRF Fusion | Merger | <1ms | Combine rankings: score = Σ(1/(k+rank)) |
| Time Decay | Module | <10ms | Age-based decay with boosting |
| Schema Migration | Module | ~2s | Version upgrades for 84 entities |

---

## Ablation Study

| Component Removed | BM25 Score | Vector Score | Graph Score | Final Quality | Latency Change |
|-------------------|-----------|--------------|-------------|---------------|----------------|
| Full Triple (baseline) | 3.76 | 0.586 | 0.5 | Best | 41.2ms |
| - Graph | 3.76 | 0.586 | 0 | Good | ~41ms |
| - Vector | 3.76 | 0 | 0.5 | Medium | ~1.1ms |
| - BM25 | 0 | 0.586 | 0.5 | Medium | ~103ms |

**Key Finding:** BM25 + Graph can achieve near-full quality with 1.1ms latency. Vector adds semantic depth but costs 40x latency.

---

## Memory Lifecycle

```mermaid
flowchart LR
    subgraph Episodic["Episodic (raw)"]
        DAILY["Daily Notes<br/>(memory/YYYY-MM-DD.md)"]
    end

    subgraph Buffer["Buffer"]
        RECENT["<7 days<br/>*.consolidated"]
    end

    subgraph Semantic["Semantic (refined)"]
        WIKI["Wiki Entities<br/>(confidence + decay)"]
    end

    subgraph Distill["Distilled"]
        SYNTH["Syntheses<br/>(high-value insights)"]
    end

    DAILY -->|"Consolidation Loop<br/>daily 08:30"| Buffer
    Buffer -->|"30+ days<br/>auto-delete"| RECENT
    RECENT -->|"memory promotion"| WIKI
    WIKI -->|"retention scan<br/>daily 08:00"| SYNTH
```

---

_Last updated: 2026-04-19 10:08 HKT_