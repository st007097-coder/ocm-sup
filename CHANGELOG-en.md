# Changelog - OCM Sup Evolution History

> 📅 Recording every change, decision, and lesson learned

---

## ⚠️ Important Note

**This CHANGELOG is not a timeline, it's a "Why" record.**

I explain:
- Why I made each decision at each stage
- What problems I encountered
- Why I chose this solution
- What lessons I learned

If you want to copy my system, please first understand the "why" behind each decision.

---

## 📅 Complete Evolution Timeline

| Date | Version | Major Changes |
|------|---------|---------------|
| 2026-03-29 | v0.1 | 阿星 (Ah Sing) born |
| 2026-04-11 | v0.3 | Triple-Stream Search research started |
| 2026-04-13 | v0.5 | Phase 1-5 completed (Triple-Stream + Wiki v2) |
| 2026-04-15 | v0.7 | Phase X + Phase Y completed (ClawMem + CraniMem) |
| 2026-04-17 | v0.9 | Phase Z completed (Uncertainty Tracking + EQS) |
| **2026-04-18** | **v2.0** | **7-Dir all completed** |

---

## 🧬 v0.1: 阿星 Born (2026-03-29)

### Situation

- 阿星 just set up
- 期哥 asked: "What can you help me with?"
- Memory system: just daily `memory/YYYY-MM-DD.md` journal

### Decision

**Don't build any systematic memory.**

Reason:
- 期哥 said "directly save, I won't read" — means he doesn't want to read journals
- I didn't know yet what services he needs
- Build trust relationship slowly

### Result

- 阿星 exists, but no complex memory system
- Learning about 期哥 through daily conversations

---

## 🧬 v0.3: Triple-Stream Search Research Started (2026-04-11)

### Situation

- Wiki has 110 MD files
- Problem: `memory_search` only does semantic search, doesn't understand entity relationships
- Query "What does 期哥 do?" - vector search only knows "related", doesn't know "期哥 → QS → 古洞站"

### Decision

**Research Triple-Stream Search solution combining BM25 + Vector + Graph.**

Why three streams?

| Channel | Strength | Weakness |
|---------|----------|----------|
| BM25 | Precise keyword matching | Doesn't understand semantics |
| Vector | Understands semantics | High false positives (especially Chinese-English) |
| Graph | Entity relationships precise | Need pre-established relationships |

Triple fusion: `RRF(d) = Σ 1/(k + rank_i)` balances strengths and weaknesses.

---

## 🧬 v0.5: Phase 1-5 Completed (2026-04-13)

### Phase 1: BM25 Channel

**Content:** Using rank_bm25 for keyword search

### Phase 2: Graph Channel

**Content:** BFS traversal depth 2, discovering relationships between entities

### Phase 3: RRF Fusion

**Content:** Reciprocal Rank Fusion merging three channel results
```python
RRF_score = Σ 1 / (k + rank_i)  # k=60
```

### Phase 4: Token Budget

**Content:** Limit each result to 2000 tokens

### Phase 5: Integration Testing

**Content:** AGENTS.md + SKILL.md trigger guidance

### Problem Discovered: Embedding Similarity False Positives

```
Query: MCP
Vector Search returns: 期哥 (similarity: 0.82)
```

Why? Possibly because in training data, M*** and J*** often appear together.

### Decision: Add Entity-Type Compatibility Check

```python
# Stage 4: Entity-type compatibility check
incompatible_pairs = [
    ('person', 'concept'),
    ('person', 'technology'),
    ('project', 'concept'),
]
```

If entity types don't match, no matter how high the embedding similarity, skip it.

### Same Day: Wiki v2 Changes

Based on LLM Wiki v2 inspiration:

1. **Confidence Scoring** — add confidence score to each entity
2. **Supersession** — track new/old info with `supersedes`/`supersededBy`
3. **Forgetting** — retention scan auto-demotes long-unupdated entities
4. **Typed Relationships** — relationships have types (works_on, uses, part_of)
5. **Self-healing Lint** — auto-fix common problems

### Result

- Triple-Stream basic functionality complete
- Wiki has structured metadata
- Still passive — waiting for user questions to respond

---

## 🧬 v0.7: Phase X + Phase Y Completed (2026-04-15)

### Phase X: ClawMem Inspiration

**Content:**
1. **Tiered Injection** — different priority content layered injection
2. **Content Half-lives** — content has "decay" mechanism, fresh content is more important
3. **Active Contradiction Detection** — detect and tag contradictory information

**Principle:** Memory is not a static database, it's dynamic, decaying, and contradictory.

### Phase Y: CraniMem Inspiration

**Content:**
1. **Write-Ahead Gating** — new memory must pass gate before writing
2. **Episodic Buffer** — short-term memory accumulates in buffer
3. **Consolidation Loop** — periodically convert episodic to semantic

**Principle:** Not everything is directly written to long-term memory, it goes through digestion (consolidation).

### Consolidation Loop Architecture

```
Episodic (7+ days) → Semantic Wiki → Procedural (Skills)
        ↑                                    ↓
        ←─────── Reflection ◯───────────────
```

Every night:
1. Distill memories older than 7 days from Episodic buffer
2. Extract entities, relationships, insights
3. Write to wiki (semantic)
4. Update skills (procedural)

### Problem Discovered

- All phases completed, but lacked clear evolution direction
- Decision: Build Roadmap to clarify future direction

---

## 🧬 v0.9: Phase Z Completed (2026-04-17)

### Situation

- Problem discovered: our memory system doesn't know "what it doesn't know"
- 期哥 asked: "When did you know about OCM?" I answered: "I don't remember."
- But I should know that I "don't remember", instead of answering as if I remember

### Phase Z-1: Uncertainty Tracking

**Decision: Add Uncertainty Tracking (EQS Methodology).**

```
Each claim should have:
1. Content - what
2. Confidence - how certain (0-1)
3. Evidence - which source
4. Last Updated - when updated
```

When confidence < threshold, we explicitly say "I don't remember" instead of guessing.

### Phase Z-3: EQS Methodology

**Principle:** OODA Loop (Observe-Orient-Decide-Act) application

```
O: Observe new information
O: Understand - contextualize
D: Assess - confidence update
A: Act - inject / ignore
```

### Result

- Responses more disciplined
- "I don't remember" "need to confirm" become normal responses
- 期哥 said: "At least you know you don't know."

---

## 🧬 v2.0: 7-Dir All Completed (2026-04-18)

### Situation

7-Dir Roadmap previous status:
- ✅ Phase 1-5: Triple-Stream Search
- ✅ 7-Dir 1: Memory System Integration
- ✅ 7-Dir 2: Wiki Search
- ❌ 7-Dir 3: Search API (50%)
- ❌ 7-Dir 4: KG Auto-Expansion (30%)
- ❌ 7-Dir 5: Smart Recall (60%)
- ❌ 7-Dir 6: Proactive Discovery
- ❌ 7-Dir 7: Graph Visualization

### Decision

**Complete all remaining directions in one day.**

This is a milestone, but doesn't mean "complete".

### What We Did Today

#### 7-Dir 3: Search API
- Created Flask HTTP API
- Endpoints: `/search`, `/entities`, `/stats`, `/health`

#### 7-Dir 4: KG Auto-Expansion
- Improved Multi-stage filtering
- Added Levenshtein distance
- Added Entity-type compatibility
- Added 39 new entities
- **Problem:** 39 entities all pointing to "ocm-sup", but ocm-sup entity doesn't exist
- **Solution:** Created OCM Sup entity, fixed frontmatter format
- **Result:** 43 nodes, 47 edges ✅

#### 7-Dir 5: Smart Recall Hook
- Added High priority keywords
- Fixed entities → nodes AttributeError
- Established smart_recall_cron.py

#### 7-Dir 6: Proactive Discovery
- Created `proactive_discovery.py`
- Added Rule-based relationship inference
- Added Multi-factor confidence scoring
- Added Bidirectional relationship check
- Added Learning system

#### 7-Dir 7: Graph Visualization
- Created `graph_visualization.py`
- Supported Mermaid / DOT / HTML formats
- Visualized Entity relationships

---

## 📚 Lessons Learned

### 1. Frontmatter Format is Critical

**Problem:**
```yaml
---
title: 期哥
type: entity
---
# Below is not in frontmatter
relationships:
  - target: 古洞站
---
```

**Learning:** Relationships must be inside `---`, otherwise graph_search.py can't read it.

### 2. Embedding Model Has Language Bias

**Problem:** Chinese-English cross-lingual similarity is unreliable.

**Solution:** Multi-stage filtering, not fully relying on embedding.

### 3. Simple > Complex

**Problem:** Initially wanted to add too many features.

**Solution:** Karpathy principle: "Simplicity First, Surgical Changes".

### 4. Testing is Confirmation, Not Discovery

**Problem:** Our tests confirm results we want, not truly discovering problems.

**Solution:** Need independent verification (but subagent environment issues...).

### 5. Evolution is Gradual, Not One-shot

**Problem:** Initially wanted to build perfect system at once.

**Solution:** As understanding of user deepens, system evolves gradually.

---

## 🔮 Future Directions

### Short-term (1-2 months)

- [ ] Package scripts as pip package
- [ ] Automate cron jobs
- [ ] Telegram command integration

### Medium-term (3-6 months)

- [ ] Multi-language support (Chinese/English/Japanese)
- [ ] Automated Relationship Discovery
- [ ] Obsidian plugin integration

### Long-term (6+ months)

- [ ] Vector database replacement (Faiss/Milvus)
- [ ] Knowledge graph visualization interface
- [ ] Autonomous learning system

---

## 🙏 Credits

- **期哥** — Requirement proposer, tester, direction guide
- **Andrej Karpathy** — Simplicity First principle
- **Aporia Labs** — LLM Wiki v2 architecture reference
- **Anthropic** — OODA Loop / CraniMem inspiration
- **OpenClaw Community** — Framework support

---

## 📌 How to Contribute

This is 期哥's personal project, not an open source project.

But if you find some parts useful, you can:

1. **Fork** — take the parts you need
2. **Modify** — change based on your situation
3. **Think** — your own evolution direction

Remember: **Copying is the last form of learning, but creating is the first form of thinking.**

---

_Last updated: 2026-04-18_
_Version: 2.0_
---

## 🧬 v2.1: Phase Z+ Self-Audit (2026-04-19)

### Situation

After completing 7-Dir, system needed honest assessment.
Self-audit scored only 5.4/10 — significant gaps identified.

### Decision

**Self-Audit + Precision Improvement in one session.**

### What We Did Today

#### Self-Audit Framework
- 8-dimension scoring system
- Unit Tests (37 tests: query_expansion + triple_stream)
- Schema Versioning (schema_migration.py)
- Time-based Decay (time_decay.py)

#### Precision Improvement
- Exact Match + Position-Aware scoring
- Title Boost (+5 for exact title match)
- BM25 tuning for Chinese/English
- Query Expansion with synonyms
- **Result:** 32 queries, 100% top-1 accuracy

#### Result
- Self-Audit Score: **5.4 → 7.5/10**
- Unit Tests: 37 passing
- Schema v1.3: 84 entities migrated
- Time Decay: 73 entities calculated

---

## 🧬 v2.2: Wiki Cleanup + OCM-Sup Repo Structuring (2026-04-20)

### Situation

- Wiki had 5721 broken wikilinks (905 warnings in lint report)
- OCM-Sup repo had unorganized docs scattered at root
- Double frontmatter issue in 226 files

### Decision

**Clean up Wiki and reorganize OCM-Sup repo in parallel.**

### What We Did Today

#### Wiki Tags
- Auto-added tags to 1986 files
- Result: 2888/2961 files now have tags (was 955)

#### Wiki Weblink Formatting  
- Converted bare URLs to markdown [text](url) format
- 1107 files converted, 13000+ links formatted
- Result: 1574 files with weblinks (was 990)

#### Double Frontmatter Fix
- Fixed 226 files with multiple YAML frontmatter blocks
- Merged frontmatter blocks correctly
- Restored 2 corrupted files from Obsidian

#### Wiki pageType Fix
- Added pageType: note to 95 files missing it

#### Wikilinks Repair
- Fixed 5482 broken wikilinks (95.8% reduction)
- System references → folder links (e.g., [[AI]] → [AI](AI-News/))
- Malformed links fixed (e.g., [[OpenClaw)]] → [[OpenClaw]])
- Remaining 239 broken links are genuine missing pages

#### OCM-Sup Repo Reorganization
- Created docs/ folder for documentation
- Moved 9 self-audit docs to docs/
- Added .gitignore for __pycache__
- Pushed to GitHub with proper commit messages
- Added x-thread-2026-04-18.md to docs/

### Result

- **Wiki Quality:** Significantly improved structure and links
- **OCM-Sup Repo:** Clean, organized, properly documented
- **GitHub:** https://github.com/st007097-coder/ocm-sup

---
