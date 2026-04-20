# OCM-Sup Benchmark Analysis — Honest Assessment

_Last Updated: 2026-04-19 10:28 HKT_

---

## Test Results (32 queries)

| Metric | Value | Notes |
|--------|------|------|
| **Naive Top-1 Hit Rate** | 100% | (any result with score > 0) |
| **Honest Top-1 Hit Rate** | 31.2% | (result actually relevant to query) |
| **Naive Top-3 Hit Rate** | 100% | |
| **Top-5 Hit Rate** | 100% | |

**Key Finding: System returns results, but results may not be relevant!**

---

## 22 Mismatches Analysis

### Type 1: System/Tool Name → Returns Wrong Entity

| Query | Expected | Got | Reason |
|-------|----------|-----|------|
| `OpenClaw` | OpenClaw system docs | Hermes Agent 文章 | OpenClaw mentioned in Hermes article |
| `即夢` | Jimeng/即夢 AI tool | F2 Cross-lingual 修復 | Jimeng mentioned in fix document |
| `OCM Sup` | OCM Sup memory system | Ah Sing entity | OCM Sup mentioned in Ah Sing page |
| `notion` | Notion integration | MCP Protocol 文章 | Notion mentioned in MCP article |
| `BM25` | BM25 algorithm docs | Ah Sing entity | BM25 mentioned in multiple places |
| `Triple-Stream` | Triple-Stream docs | Ah Sing entity | mentioned but not main topic |

### Type 2: Chinese Keywords → Returns English AI News

| Query | Expected | Got | Reason |
|-------|----------|-----|------|
| `Engineering` | Engineering docs | AI News articles | "Engineering" mentioned in AI News |
| `Subcontractor` | Subcontractor docs | polarization article | Subcontractor mentioned but not the topic |
| `Supplier` | Supplier docs | Latest AI Digest | industry keyword match |
| `Contract` | Contract docs | Jacky entity | Contract mentioned but scattered |
| `Tendering` | Tendering docs | Latest AI Digest | Tendering關鍵詞匹配 |

### Type 3: Cross-lingual → Returns Irrelevant Results

| Query | Expected | Got | Reason |
|-------|----------|-----|------|
| `Kwu Tung Station` | Kwu Tung Station docs | Metacognition Rules | English keyword matched to unrelated content |
| `Knowledge Graph` | Knowledge Graph | OCM Sup Test Report | Graph mentioned but not about graph |

---

## Root Cause Analysis

### 1. Wiki Content Distribution Imbalance

Problem: Large amount of AI news articles overwhelm actual entity docs
- AI news occupies large storage
- Jacky-related entities are relatively few
- causes keyword search to favor AI news

### 2. BM25 Matching Too Loose

"OpenClaw" matches any article containing this word
but these articles are not "about OpenClaw"
but "mentions OpenClaw"

### 3. Lack of Semantic Re-ranking

Vector search 102ms latency too slow
System used early exit, relying only on BM25
Result: High recall (found all docs mentioning keyword)
but low precision (found docs are not actually relevant)

### 4. Entity Relationships Not Utilized

Graph search could help
but BFS may return "proximity" related instead of "semantic" related

---

## Improvement Directions

### Short-term (1-2 weeks)

1. **Increase Entity Document Count**
   - Create more explicit entity docs (not relying on AI news)
   - Each system/tool has its own page

2. **Adjust BM25 Boost**
   - Increase boost for exact entity match
   - Decrease boost for keyword mention

3. **Force Vector Re-ranking (even if slow)**
   - Force vector re-rank on top-20 BM25 results
   -sacrifice speed for quality

### Medium-term (1 month)

4. **Implement True Top-K Precision**
   ```python
   def is_relevant(result, query):
       # Check if result is "about" query, not "mentions" query
       return semantic_similarity(query, result.title) > threshold
   ```

5. **Separate AI News vs Entity Storage**
   - AI news → separate collection
   - Entities → primary search

6. **Increase Entity Page Count**
   - OpenClaw, Hermes, Jimeng, Notion, Obsidian, etc.
   - 每個有獨立、詳細的 page

### Long-term

7. **Implement RAG-style Retrieval**
   - 唔只返回 doc，改為return answer
   - combine retrieval + synthesis

---

## Summary

**Core Problem:** OCM-Sup is currently a high-recall, low-precision system

| Aspect | Current | Target |
|------|------|------|
| Recall | 高（100%）| High (maintain)|
| Precision | Low (31%)| High (>80%)|
| Latency | Fast (BM25 0.4ms)| Acceptable (<100ms)|

**Next Step Priority:** Increase precision, not continue increasing recall

---

_Last updated: 2026-04-19 10:28 HKT_