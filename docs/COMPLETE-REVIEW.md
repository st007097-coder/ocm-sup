# OCM-Sup 完整回顧

_Last Updated: 2026-04-19 10:21 HKT_

---

## 一、原意（為何創建）

### 核心問題

單一搜索方法（BM25 或 Vector）對複雜查詢效果不佳。特別係：
- **Cross-lingual**：中英文混雜查詢（"hermes" vs "即夢"）
- **Entity relationships**：需要關係推理（期哥→古洞站→東鐵線）
- **Memory decay**：舊記憶如何影響新查詢
- **Smart recall**：Agent 唔知道自己幾時應該用邊個 search method

### 目標用戶

香港 QS（工料測量師）期哥，需要 AI 助手幫佢記住：
- 項目資料（古洞站工程）
- 合約談判歷史
- 人物關係（分判商、供應商）
- 之前的決定和承諾

### 期望效果

```
"我想知道期哥對某個項目的看法"
→ 需要知道：項目名字、相關人物、之前的決定、目前狀態
→ 而唔係淨係 keyword match
```

---

## 二、過程（Evolution Timeline）

| Phase | 日期 | 內容 |
|-------|------|------|
| Phase 0 | 2026-04-13 | 概念驗證，嘗試簡單記憶系統 |
| Phase 1-2 | 2026-04-13 | Confidence Scoring + Supersession 追蹤 |
| Phase X | 2026-04-15 | Tiered Injection + Content half-lives + Active contradiction |
| Phase Y | 2026-04-15 | Write-Ahead Gating + Episodic Buffer + Consolidation Loop |
| Phase Z | 2026-04-17 | Uncertainty Tracking + EQS Methodology |
| **Phase Z+** | **2026-04-18** | **Self-Audit：6.3 → 7.5/10** |

---

## 三、改善（Key Improvements）

### 1. Triple-Stream Search（最大改進）

```
之前：BM25 only → 中文英文結果分開
之後：BM25 + Vector + Graph → 三流融合，cross-lingual 大幅改善

BM25: 0.4ms（快速精確）
Vector: 102ms（語義相似）
Graph: 0.7ms（實體關係）

融合後：41.2ms average
56.7% top results 被重新排名
```

### 2. Query Expansion（Cross-lingual 關鍵）

```
問題：中文查詢"即夢"搵唔到"Hermes Agent"

解決方案：
- 中文→英文同義詞："即夢" → "即夢", "即夢AI", "Hermes Agent"
- Entity Aliases：每個 entity 有多個名字（Hermes、希格斯、hermes）
- 結果：BM25 現在可以通過 aliases 跨語言匹配
```

### 3. Knowledge Graph Entity Discovery

```
問題：.entities/ 資料散亂，新 entity 唔會自動發現

解決：kg_auto_expander.py
- 自動擴展 entity relationships
- 43 nodes, 47 edges
- BFS traversal 找到相關實體
```

### 4. Smart Recall Hook（7-Dir 5）

```
問題：唔知幾時應該用 Triple-Stream

解決：自動識別觸發時機
- 包含"期哥"、"古洞站"、"記得"等關鍵字 → 觸發
- 自動 inject 相關 entities 到 context
```

---

## 四、試驗（Testing & Validation）

### 1. Ablation Study（組件級別測試）

| 移除組件 | 效果drop | Latency改變 |
|---------|---------|-------------|
| -BM25 | -35% quality | +60ms（如果只用Vector） |
| -Vector | -15% quality | -40x faster（1.1ms） |
| -Graph | -10% quality | 不變 |
| -QueryExpansion | -20% quality | 不變 |
| -EntityAliases | -25% quality | 不變 |

**結論：** BM25 + QueryExpansion + EntityAliases 係最高 ROI 組合（<2ms cost，貢獻 45% quality）

### 2. Before/After Benchmark

| 配置 | Hit Rate (hermes) | Latency |
|------|------------------|---------|
| BM25 only | 85% | 0.4ms |
| Vector only | 80% | 102ms |
| Full Triple | 95% | 41.2ms |
| BM25 + Graph | 90% | 1.1ms |

### 3. Failure Cases Log（7個 cases）

| Case | 根本原因 | 修復 |
|------|---------|------|
| lastAccessed NOT SET | Path resolution bug | 明確使用 WIKI_PATH 前綴 |
| BM25 score = 0 for "hermes" | 冇 entity aliases | 添加 20 個 entity aliases |
| BM25 path mismatch | 相對 vs 絕對路徑 | 統一 path 格式 |
| Enhanced Dreaming cron error | Timeout/環境問題 | Watchdog + 增加 timeout |
| Vector latency 102ms | Ollama 非 vector DB | BM25+Graph fast path |
| Query expansion test fail | pytest assertion rewrite bug | 改用 explicit for-loop |
| Schema migration data quality | Default values 代替推斷 | 手動審查關鍵 entities |

---

## 五、Self Audit / Self Assessment

### Self-Audit（2026-04-18）

評分：6.3 → 7.5/10

**P0 完成：**
- lastAccessed 追蹤 ✅
- Before/After Benchmark ✅
- Failure Cases Log ✅
- README 更新 ✅

**P1 完成：**
- Observability（explain=true）✅
- Ablation Study ✅

**F2 修復：**
- Query Expansion ✅
- Entity Aliases（20 entities）✅

### 深夜完成（00:30-00:58 HKT）

| 維度 | 狀態 |
|------|------|
| Unit Tests | ✅ 37 tests (test_query_expansion.py + test_triple_stream_search.py) |
| Schema Versioning | ✅ Migration system (schema_migration.py) |
| Time-based Decay | ✅ Age-based decay (time_decay.py) |

### GitHub Reviewer Rubric 評分（10項）

| 維度 | 分數 | 狀態 |
|------|------|------|
| 1. 問題定義 | 8/10 | ✅ 清楚（cross-lingual + entity recall）|
| 2. Baseline | 8/10 | ✅ 有對比（BM25 vs Vector vs Triple）|
| 3. Ablation | 9/10 | ✅ 詳細（per-component ablation）|
| 4. Failure Cases | 8/10 | ✅ 7 cases documented |
| 5. 模組邊界 | 7/10 | ⚠️ MODULES.md 有，但scripts有重疊 |
| 6. 可觀測性 | 8/10 | ✅ explain=true, retention scan logs |
| 7. 成本/延遲 | 7/10 | ⚠️ 有數據但唔夠全面 |
| 8. 記憶生命週期 | 8/10 | ✅ time_decay.py + consolidation loop |
| 9. 可部署 | 7/10 | ⚠️ one-command demo 有，但無 Docker |
| 10. README 說服力 | 8/10 | ✅ 有 benchmark 有 limitation 有 roadmap |

**4 Verdict Summary：**
```
Vision: ✅ 高（Triple-Stream + KG + Uncertainty 方向正確）
Ambition: ✅ 高（唔係普通 wrapper，有系統設計野心）
Proof: ✅ 7.5/10（有 benchmark/ablation/failure cases）
Engineering: ⚠️ 6.5/10（scripts 組織有啲乱，duplicate 未清理）
```

---

## 六、Response to GitHub Reviewer Rubric

### 1. 問題定義清唔清楚？✅ 清楚

OCM-Sup 係為了解決：
- AI assistant 記唔住之前討論過嘅項目資料（entity recall）
- 單一 BM25/Vector 應對唔到中文英文混合查詢（cross-lingual）
- 記憶冇 decay，慢慢變成垃圾（memory hygiene）
- Agent 唔知道自己幾時應該用邊個 search method（smart recall）

### 2. 有冇 baseline？✅ 有（7.5/10）

BM25 only vs Vector only vs Triple-Stream：
- hermes query: 85% vs 80% vs 95% hit rate
- latency: 0.4ms vs 102ms vs 41.2ms
- 結論：Full triple quality 最好，但 BM25+Graph 可以係 90% quality at 1.1ms

### 3. 有冇 ablation？✅ 有（9/10）

ABLATION.md 有詳細 per-component ablation：
- 8 個 components 全部測試
- 3 個 test queries（hermes, 古洞站, OpenClaw）
- 結論：QueryExpansion + EntityAliases 係最高 ROI

### 4. 有冇 failure cases？✅ 有（8/10）

FAILURE-CASES.md 有 7 個 documented cases：
- Critical: 2（lastAccessed bug, BM25 score zero）
- Major: 3（path mismatch, cron error, vector latency）
- Minor: 2（test framework issue, schema migration）

### 5. 模組邊界清唔清？⚠️ 一般（7/10）

MODULES.md 有清楚嘅 Layer 架構定義：
- Layer 1: Core Retrieval（triple_stream_search.py, query_expansion.py）
- Layer 2: Knowledge Graph（graph_search.py, kg_auto_expander.py）
- Layer 3: Memory Management（time_decay.py, consolidation loop）

問題：實際 scripts 有 duplicate（OCM-Sup/scripts/ vs skills/triple-stream-search/scripts/）
但期哥確認分開係正常，所以呢個唔算真正問題

### 6. 可觀測性夠唔夠？✅ 夠（8/10）

有：
- /search?explain=true → channel_stats + ranks + expansion_used
- retention-scan.sh 日誌
- lastAccessed tracking
- decayScore + decayStatus markers

可以 debug：
- 邊個 channel 搵到？
- BM25 rank vs Vector rank？
- 邊個 query expansion 觸發咗？

### 7. 成本/延遲有冇數據？⚠️ 有但唔夠（7/10）

有：
- BM25: 0.4ms
- Vector: 102ms  
- Graph: 0.7ms
- Full Triple: 41.2ms

冇：
- Token cost（每次 query 用幾多 token）
- Ollama embedding 嘅真實 latency distribution（P50/P95）
- 係 production load 下嘅表現

### 8. 記憶生命週期有冇定義？✅ 有（8/10）

有完整 lifecycle：
- 寫入：daily memory → episodic
- 整合：consolidation_loop.sh（episodic → semantic）
- Decay：time_decay.py（score = 1/(1+(age/30)^1.5)）
- 清理：retention-scan.sh（deprecated → archive）
- 蒸餾：wiki/syntheses/（高價值 insights）

生命周期有定義，但整合入 cron loop 係部分完成

### 9. 可唔可以真部署？⚠️ 一般（7/10）

✅ 有：
- README 有安裝說明
- 有 one-command demo script
- 有 pytest tests（37 passed）
- 有 schema migration

❌ 冇：
- Docker image
- 複雜嘅 install flow（依賴 Ollama + Python venv）
- Production deployment guide

### 10. README 係咪令人信服？✅ 係（8/10）

✅ 有：
- 問題定義 ✅
- Baseline ✅
- 方法唔同處 ✅
- 架構圖（Mermaid in ARCHITECTURE.md）✅
- Demo ✅
- Benchmark（56.7% re-ranking）✅
- Failure cases（在 FAILURE-CASES.md）✅
- Limitations ✅
- Cost/Latency ✅

❌ 缺：
- Roadmap 太簡短
- 互動式 demo（live demo page）

---

## 總結

### OCM-Sup 目前狀態

評分：7.5/10（對照 rubric）
達到：Proof ✅ Engineering ⚠️ Vision ✅ Ambition ✅

### 最大 Strength

- Triple-Stream + Query Expansion + Entity Aliases 係 smart combo
- Failure cases 願意承認（唔係只 show 成功）
- Ablation 有數據支撐

### 最大 Gap

- 冇 Docker / production deployment guide
- Cost/Latency bench唔夠全面
- Engineering maturity（scripts 組織有啲乱）

### 如果想再提升到 8.5+/10，需要：

1. **Docker image / 一鍵部署**
2. **Production benchmark（under load）**
3. **API document（OpenAPI spec）**

---

_Last updated: 2026-04-19 10:21 HKT_
_Author: 阿星 (Ah Sing)_
_Document: OCM-Sup Complete Review (vs GitHub Reviewer Rubric)_