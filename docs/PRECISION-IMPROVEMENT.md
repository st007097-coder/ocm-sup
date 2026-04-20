# OCM-Sup Precision Improvement Analysis

_Last Updated: 2026-04-19 10:35 HKT_

---

## Title Boost Experiment

### Change Made
Added title boost (+50%) to BM25 search when query matches document title.

### Results

| Metric | Before Title Boost | After Title Boost | Change |
|--------|-------------------|------------------|--------|
| Honest Top-1 Hit Rate | 31.2% | 37.5% | **+6.3%** |
| Mismatches | 22/32 | 20/32 | **-2** |

### Improvements (Fixed by Title Boost)
- hermes → What Is Hermes Agent? ✅
- 期哥 → 期哥 ✅
- EvoMap → EvoMap 整合可行性評估 ✅
- ClawEmail → ClawEmail 研究 ✅
- OCM Sup → CraniMem vs OCM Sup 深度對比分析 ✅

### Still Failing (20 mismatches)

**Category 1: Semantic "About" vs "Mention" Problem**
These queries match documents that MENTION the query term but aren't ABOUT it:
- "OpenClaw" → Hermes Agent article (actually about comparing OpenClaw vs Hermes)
- "即夢" → Hermes Agent article (mentions 即夢 as a tool, not about 即夢)
- "BM25" → 阿星 (mentions BM25 in context, not about BM25)
- "Triple-Stream" → 阿星 (mentions in context, not topic)
- "notion" → MCP article (mentions notion in context)
- "RRF" → OCM Sup doc (mentions RRF but not about RRF)

**Category 2: Long Document Dominance**
AI News documents are very long and contain many keywords, dominating results:
- "knowledge graph" → AI News (contains "knowledge graph" mention)
- "latency benchmark" → AI News
- "entity relationship" → AI News

**Category 3: Cross-lingual Still Problematic**
- "Kwu Tung Station" → 元認知規則 (no Chinese entity match)
- "quantity surveyor" → AI工具唔能夠取代QS專業判斷 (partial match)

---

## Root Cause Analysis

### Problem: BM25 Can't Distinguish "Mention" from "About"

BM25 returns high scores for ANY document containing the query term, regardless of whether the document is ABOUT the topic or just MENTIONS it.

Example:
- Query: "BM25"
- BM25 score for "阿星" doc: 5.68 (mentions BM25 in OCM Sup context)
- BM25 score for "BM25 algorithm doc" would be similar
- But if there's no dedicated "BM25" doc, BM25 can't know which is "about"

### Why Title Boost Helps (Sometimes)

Title boost helps when:
1. There's an entity doc with the query in the title
2. The entity doc is actually about the topic

Title boost doesn't help when:
1. There's no dedicated entity doc with the query in title
2. The entity doc mentions the query but isn't about it

---

## Solutions Researched

### Solution 1: Mandatory Vector Re-ranking ✅ (Implemented)
Force Vector re-ranking on top-K BM25 results to catch semantic mismatches.

**Status:** Partially working - Vector search takes 102ms which is slow

**Issue:** Vector alone isn't sufficient - it returns similar-but-wrong docs

### Solution 2: Separate AI News from Entity Docs
Create separate collections:
- Entity collection: Primary search target
- News collection: Secondary, only searched if entity search fails

**Status:** Not implemented

**Effort:** Medium (requires restructuring)

### Solution 3: Create Missing Entity Docs
Create dedicated pages for:
- OpenClaw (currently only Hermes vs OpenClaw comparison exists)
- BM25 (currently mentioned in OCM Sup docs)
- Triple-Stream (same)
- RRF (same)

**Status:** Not implemented

**Effort:** Low-Medium

### Solution 4: Query-Type Detection
Detect query type:
- Entity query → Use entity doc index only
- Concept query → Use concept doc index + vector
- News query → Use news index

**Status:** Not implemented

**Effort:** High

---

## RRF Weight Experiment

### Change Attempted
Increased Vector weight (1.5) and decreased BM25 weight (0.8) in RRF fusion.

### Result: FAILED ❌

**Issue:** When Vector weight is higher, BM25 contributions become 0 (not included in fusion).
This causes ALL results to come from Vector search alone, which returns semantically similar but wrong documents.

**Conclusion:** The three channels must remain balanced. BM25 provides exact match, Vector provides semantic similarity, Graph provides relationship awareness. Unbalancing them hurts precision.

---

## Current Best Configuration

```python
# Triple-Stream with Title Boost
RRF_weights = {
    'BM25': 1.0,      # Exact keyword match
    'Vector': 1.0,     # Semantic similarity  
    'Graph': 1.5,     # Entity relationships
}

BM25_title_boost = 1.5  # 50% boost when query matches title
```

---

## Next Steps for Precision Improvement

### P1: Create Missing Entity Docs (Low Effort, High Impact)
Create dedicated pages for:
1. OpenClaw.md - System overview
2. BM25.md - Algorithm explanation
3. Triple-Stream.md - Architecture explanation
4. RRF.md - Algorithm explanation

**Expected improvement:** +10-15% hit rate for system/concept queries

### P2: Separate AI News Collection (Medium Effort)
1. Tag documents with `collection: entity` or `collection: news`
2. Search entity collection first
3. Only search news if entity search returns < K results

**Expected improvement:** +15-20% precision for entity queries

### P3: Mandatory Vector Re-rank for Top-10 (Medium Effort, Slow)
1. Get top-20 BM25 results
2. Force Vector re-ranking
3. Use Vector similarity to filter out wrong docs

**Expected improvement:** +20-25% precision but 10x slower

---

## Summary

| Approach | Effort | Precision Gain | Latency Impact |
|----------|--------|---------------|----------------|
| Title Boost | ✅ Done | +6.3% | None |
| Create Entity Docs | Low | +10-15% | None |
| Separate Collections | Medium | +15-20% | None |
| Vector Re-rank | Medium | +20-25% | 10x slower |
| RRF Weight Tuning | ✅ Failed | 0% | N/A |

**Conclusion:** Title boost helped (+6.3%). Next best wins: Create entity docs for missing systems/concepts.

---

_Last updated: 2026-04-19 10:35 HKT_
---

## Final Results (2026-04-19 10:55 HKT)

### Honest Benchmark After All Improvements

| Metric | Value |
|--------|-------|
| Honest Top-1 Hit Rate | **40.6%** |
| Original Baseline | 31.2% |
| Improvement | **+9.4 points** |

### What Was Fixed
- OpenClaw ✅ → OpenClaw entity (was 期哥)
- BM25 ✅ → BM25 entity (was Triple-Stream Search)
- knowledge graph ✅ → Knowledge Graph entity
- vector search ✅ → Vector Search entity
- Triple-Stream ✅ → Triple-Stream Search (acceptable)
- OCM Sup ✅ → OCM Sup entity
- ClawEmail ✅ → ClawEmail entity
- EvoMap ✅ → EvoMap 整合可行性評估

### Still Failing (19 mismatches)
- RRF → Triple-Stream Search (suffix matching issue)
- 即夢 → Hermès Lobster article (completely unrelated)
- notion → MCP (wrong system match)
- QS/memory/search/project/agent → AI News (ambiguous queries)
- Cross-lingual: Kwu Tung Station → 元認知規則

### Key Technical Changes Made
1. **Title Boost (+50%)** - BM25 boosts when query matches title
2. **Exact Entity Match Override** - Forces entity doc to #1 when query matches entity name
3. **New Entity Docs** - Created 6 new dedicated entity pages
4. **RRF Weights** - BM25: 2.0, Vector: 1.0, Graph: 1.5

### Remaining Root Causes
1. **Suffix Matching Too Loose** - "RRF" matches "Triple-Stream Search" because "search" is in acceptable suffixes
2. **Ambiguous Queries** - QS, memory, search, project, agent all have multiple meanings
3. **Cross-lingual Still Broken** - Kwu Tung Station, quantity surveyor still fail
4. **Short Names Collide** - RRF is too short, matches too many docs

### Next Steps for Further Improvement
- P1: Fix suffix matching (stricter rules for short entity names)
- P1: Create dedicated RRF.md with shorter name in title
- P2: Implement cross-lingual query expansion for English→Chinese
- P2: Implement query type detection (entity vs concept vs ambiguous)
