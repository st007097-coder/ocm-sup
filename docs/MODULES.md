# OCM Sup Module Architecture

_Last Updated: 2026-04-18_

---

## Directory Structure

```
OCM-Sup/                          # Primary repo (git-tracked)
├── README.md                     # Main documentation
├── scripts/                      # CORE modules (single source of truth)
│   ├── triple_stream_search.py   # Core: BM25 + Vector + Graph + RRF
│   ├── search_api.py             # HTTP API (Flask)
│   ├── graph_search.py           # Graph channel
│   ├── graph_visualization.py    # Graph visualization
│   ├── query_expansion.py        # Bilingual query expansion
│   ├── proactive_discovery.py    # Proactive entity discovery
│   ├── smart_recall_hook.py      # Recall triggering hook
│   ├── smart_recall_cron.py      # Cron job for recall
│   ├── kg_auto_expander.py       # Knowledge graph auto-expansion
│   └── triple_stream_cli.py      # CLI interface
├── consolidation/
│   └── consolidation_loop.sh      # Memory consolidation (episodic → semantic)
├── scripts_workspace/             # Operational scripts (NOT OCM Sup core)
│   ├── aws-credential-scan.sh
│   ├── journal-to-obsidian.sh
│   ├── lint-auto-fix.py
│   ├── retention-scan.sh
│   ├── wiki-add-confidence.py
│   ├── run_search_api.sh         # API launcher
│   └── manage_search_api.sh
└── wiki/                         # Wiki documentation
    ├── entities/
    ├── concepts/
    └── syntheses/

skills/triple-stream-search/       # Skill wrapper (references OCM-Sup/scripts)
└── scripts/ → SYMLINK to OCM-Sup/scripts/
```

---

## Module Boundaries

### Layer 1: Core Retrieval (No external dependencies)
| Module | Responsibility | API |
|--------|---------------|-----|
| `triple_stream_search.py` | Triple-Stream BM25+Vector+Graph+RRF | `search(query, top_k)`, `search_bm25_expanded()`, `search_vector()`, `search_graph()` |
| `query_expansion.py` | Chinese-English bilingual query expansion | `expand_query(text)` |
| `graph_search.py` | Knowledge Graph entity traversal | `search_graph(query, top_k)` |

### Layer 2: Knowledge Graph
| Module | Responsibility | API |
|--------|---------------|-----|
| `graph_visualization.py` | Graph rendering for display | `render_graph()` |
| `kg_auto_expander.py` | Auto-expand entity relationships | `expand_entity(name)` |

### Layer 3: Memory Management
| Module | Responsibility | API |
|--------|---------------|-----|
| `consolidation_loop.sh` | Episodic → Semantic memory | `bash consolidation-loop.sh` |
| `retention_scan.sh` | Confidence-based page retention | `bash retention-scan.sh` |

### Layer 4: Proactive Layer
| Module | Responsibility | API |
|--------|---------------|-----|
| `smart_recall_hook.py` | Trigger recall based on conversation | `should_recall(context)` |
| `smart_recall_cron.py` | Scheduled recall check | Cron job |
| `proactive_discovery.py` | Discover new entity relationships | `discover(query)` |

### Layer 5: HTTP Interface
| Module | Responsibility | API |
|--------|---------------|-----|
| `search_api.py` | Flask HTTP API | `GET /search`, `GET /stats`, `GET /health` |

### Layer 6: CLI
| Module | Responsibility | API |
|--------|---------------|-----|
| `triple_stream_cli.py` | Command-line interface | `python3 triple_stream_cli.py <query>` |

---

## Data Flow

```
User Query
    ↓
query_expansion.py        (expand Chinese ↔ English)
    ↓
┌───────────────┬───────────────┬───────────────┐
│ BM25 Channel  │ Vector Channel│ Graph Channel │
│ (fast, exact) │ (semantic)    │ (entity rel.) │
└───────┬───────┴───────┬───────┴───────┬───────┘
        │               │               │
        └───────────────┼───────────────┘
                        ↓
               RRF Fusion (Reciprocal Rank Fusion)
                        ↓
               ranked_results (top_k)
                        ↓
         ┌──────────────┴──────────────┐
         │                             │
         ↓                             ↓
smart_recall_hook.py          lastAccessed update
         ↓
proactive_discovery.py (optional)
```

---

## API Reference

### Primary Search (Triple-Stream)
```python
from triple_stream_search import TripleStreamSearch
search = TripleStreamSearch(wiki_path='/path/to/wiki')
results = search.search('古洞站', top_k=5)
# Returns: [{'title', 'path', 'rrf_score', 'sources', 'bm25_score', 'vector_score', 'graph_score'}]
```

### Channel-Level Search
```python
bm25_results = search.search_bm25_expanded(query, top_k=10)
vector_results = search.search_vector(query, top_k=10)
graph_results = search.search_graph(query, top_k=10)
```

### HTTP API
```bash
curl "http://localhost:5000/search?q=古洞站&top_k=5&explain=true"
curl "http://localhost:5000/stats"
curl "http://localhost:5000/entities"
```

---

## Known Issues

1. **Duplicate scripts**: `OCM-Sup/scripts/` and `skills/triple-stream-search/scripts/` have similar files but different content. Active development is in `skills/triple-stream-search/scripts/`. Need to consolidate.

2. **Flask API restart**: After code changes, must manually restart: `fuser -k 5000/tcp && bash run_search_api.sh`

3. **Ollama dependency**: Vector channel requires Ollama running locally (`ollama serve`). If Ollama is down, vector channel returns empty results.

---

## TODO

- [ ] Consolidate duplicate scripts between OCM-Sup and skills directories
- [ ] Create proper symlink: `skills/triple-stream-search/scripts/` → `OCM-Sup/scripts/`
- [ ] Add unit tests for each module
- [ ] Document failure modes per module
