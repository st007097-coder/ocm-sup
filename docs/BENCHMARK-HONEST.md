# OCM-Sup Benchmark Analysis — Honest Assessment

_Last Updated: 2026-04-19 10:28 HKT_

---

## 測試結果（32 queries）

| Metric | 數值 | 備註 |
|--------|------|------|
| **Naive Top-1 Hit Rate** | 100% | (any result with score > 0) |
| **Honest Top-1 Hit Rate** | 31.2% | (result actually relevant to query) |
| **Naive Top-3 Hit Rate** | 100% | |
| **Top-5 Hit Rate** | 100% | |

**關鍵發現：系統返回結果，但結果未必相關！**

---

## 22 個 Mismatches 分析

### 類型 1：系統/Tool 名稱 → 返回錯誤 entity

| Query | Expected | Got | 原因 |
|-------|----------|-----|------|
| `OpenClaw` | OpenClaw system docs | Hermes Agent 文章 | OpenClaw 字樣出現喺 Hermes 文章 |
| `即夢` | Jimeng/即夢 AI tool | F2 Cross-lingual 修復 | 即夢字樣喺修復文檔 |
| `OCM Sup` | OCM Sup memory system | 阿星 entity | OCM Sup 提及喺阿星頁面 |
| `notion` | Notion integration | MCP Protocol 文章 | Notion 提及喺 MCP 文章 |
| `BM25` | BM25 algorithm docs | 阿星 entity | BM25 提及喺多處 |
| `Triple-Stream` | Triple-Stream docs | 阿星 entity | 提及但唔係主 topic |

### 類型 2：中文關鍵詞 → 返回英文 AI 新聞

| Query | Expected | Got | 原因 |
|-------|----------|-----|------|
| `工程` | Engineering docs | AI News articles | "工程" 字樣喺 AI 新聞 |
| `分判商` | Subcontractor docs | 兩極分化 article | 分判商提及但唔係主題 |
| `供應商` | Supplier docs | Latest AI Digest | 行業關鍵詞匹配 |
| `合約` | Contract docs | 期哥 entity | 合約提及但分散 |
| `投標` | Tendering docs | Latest AI Digest | 投標關鍵詞匹配 |

### 類型 3：Cross-lingual → 返回不相關結果

| Query | Expected | Got | 原因 |
|-------|----------|-----|------|
| `Kwu Tung Station` | 古洞站 docs | 元認知規則 | 英文關鍵詞匹配到唔相關內容 |
| `knowledge graph` | 知識圖譜/圖譜 | OCM Sup Test Report | Graph 提及但唔係關於 graph |

---

## 根本原因分析

### 1. Wiki 內容分佈不均

問題：大量 AI news 文章淹沒咗真正嘅 entity docs
- AI news 佔用咗大量 storage
- 期哥相關 entities 相對少
- 導致 keyword search 偏向 AI news

### 2. BM25 匹配太寬鬆

"OpenClaw" 匹配到任何包含呢個字嘅文章
但呢啲文章唔係「關於 OpenClaw」
而係「提及 OpenClaw」

### 3. 缺乏 semantic re-ranking

Vector search 102ms latency 太慢
系統用咗 early exit，只靠 BM25
結果：高 recall（找到所有提到 keyword 嘅 doc）
但低 precision（找到嘅唔係真正相關嘅 doc）

### 4. Entity relationship 未被利用

Graph search 可以幫手
但 BFS 可能返回 "proximity" 相關而非 "semantic" 相關

---

## 改進方向

### 短期（1-2 星期）

1. **增加 entity documents 数量**
   - 創建更多明確的 entity docs（不用成日靠 AI news）
   - 每個 system/tool 有獨立 page

2. **調整 BM25 boost**
   - 提高 exact entity match 的 boost
   - 降低 keyword mention 的 boost

3. **強制 Vector re-ranking（就算慢）**
   - 對 top-20 BM25 results 強制 vector re-rank
   -犧牲 speed 換 quality

### 中期（1 個月）

4. **實現真正的 Top-K Precision**
   ```python
   def is_relevant(result, query):
       # 檢查 result 是否「關於」query，而唔係「提及」query
       return semantic_similarity(query, result.title) > threshold
   ```

5. **分離 AI News vs Entity Storage**
   - AI news → separate collection
   - Entities → primary search

6. **增加 entity page 數量**
   - OpenClaw, Hermes, Jimeng, Notion, Obsidian 等
   - 每個有獨立、詳細的 page

### 長期

7. **Implement RAG-style retrieval**
   - 唔只返回 doc，改為返回 answer
   - 结合 retrieval + synthesis

---

## 總結

**問題核心：** OCM-Sup 目前係 high-recall, low-precision system

| 方面 | 目前 | 目標 |
|------|------|------|
| Recall | 高（100%）| 高（維持）|
| Precision | 低（31%）| 高（>80%）|
| Latency | 快（BM25 0.4ms）| 可接受（<100ms）|

**下一步最關鍵：** 提高 precision，而唔係继续提高 recall

---

_Last updated: 2026-04-19 10:28 HKT_