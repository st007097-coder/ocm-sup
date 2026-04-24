# Changelog - OCM Sup 進化史

> 📅 記錄每一次嘅改動、決定、同教訓

---

## ⚠️ 重要提醒

**呢個 CHANGELOG 唔係時間線，係「點解」嘅記錄。**

我會解釋：
- 每個階段我做呢個決定嘅原因
- 遇到咩問題
- 點解選擇呢個方案
- 學到咩教訓

如果你想複製我嘅系統，請先讀懂每個決定背後嘅「點解」。

---

## 📅 完整進化 Timeline

| 日期 | 版本 | 主要改動 |
|------|------|----------|
| 2026-03-29 | v0.1 | 阿星誕生 |
| 2026-04-11 | v0.3 | Triple-Stream Search 開始研究 |
| 2026-04-13 | v0.5 | Phase 1-5 完成 (Triple-Stream + Wiki v2) |
| 2026-04-15 | v0.7 | Phase X + Phase Y 完成 (ClawMem + CraniMem) |
| 2026-04-17 | v0.9 | Phase Z 完成 (Uncertainty Tracking + EQS) |
| **2026-04-18** | **v2.0** | **7-Dir 全部完成** |

---

## 🧬 v0.1: 阿星誕生 (2026-03-29)

### 當時情况

- 阿星剛剛setup
- 期哥問：「你有乜嘢可以幫我？」
- 記憶系統：就係每日 `memory/YYYY-MM-DD.md` 寫日誌

### 決定

**不做任何系統性記憶。**

原因：
- 期哥話「直接存我唔睇」— 代表佢唔想睇日記
- 我仲未知道佢需要乜服務
- 慢慢建立信任關係

### 結果

- 阿星存在，但冇複雜嘅記憶系統
- 靠日常對話慢慢了解期哥

---

## 🧬 v0.3: Triple-Stream Search 開始研究 (2026-04-11)

### 當時情况

- Wiki 有 110 個 MD 檔案
- 問題：`memory_search` 只能做 semantic search，但唔理解 entity 關係
- 問「期哥係做咩？」vector search 只知相關，唔知「期哥 → QS → 古洞站」

### 決定

**研究 Triple-Stream Search 方案，結合 BM25 + Vector + Graph。**

點解係三流？

| Channel | 優點 | 缺點 |
|---------|------|------|
| BM25 | 精確關鍵詞匹配 | 唔理解語義 |
| Vector | 理解語義 | 假陽性多（特別係中英） |
| Graph | Entity 關係精確 | 需要預先建立關係 |

三流融合：`RRF(d) = Σ 1/(k + rank_i)` 可以平衡各channel嘅優缺點。

---

## 🧬 v0.5: Phase 1-5 完成 (2026-04-13)

### Phase 1: BM25 Channel

**內容：** 使用 rank_bm25 做關鍵詞搜索

### Phase 2: Graph Channel

**內容：** BFS 遍歷 2 層，發現 entities 之間嘅關係

### Phase 3: RRF Fusion

**內容：** Reciprocal Rank Fusion 合併三個 channel 結果
```python
RRF_score = Σ 1 / (k + rank_i)  # k=60
```

### Phase 4: Token Budget

**內容：** 限制每個結果 2000 tokens

### Phase 5: 整合測試

**內容：** AGENTS.md + SKILL.md 觸發指引

### 當時問題：Embedding Similarity 假陽性

```
Query: MCP
Vector Search 返回: 期哥 (similarity: 0.82)
```

點解？可能係因為訓練數據入面 M*** 與 J*** 常一起出現。

### 決定：加入 Entity-Type Compatibility Check

```python
# Stage 4: Entity-type compatibility check
incompatible_pairs = [
    ('person', 'concept'),
    ('person', 'technology'),
    ('project', 'concept'),
]
```

如果 entity types 唔夾，唔理 embedding similarity 有幾高，都 skip。

### 同日完成：Wiki v2 改動

基於 LLM Wiki v2 嘅靈感：

1. **Confidence Scoring** — 每個 entity 加 confidence 分數
2. **Supersession** — 新舊資訊用 `supersedes`/`supersededBy` 追蹤
3. **Forgetting** — retention scan 自動降級長期未更新嘅 entities
4. **Typed Relationships** — relationships 加入類型（works_on, uses, part_of）
5. **Self-healing Lint** — 自動修復常見問題

### 結果

- Triple-Stream 基本功能完成
- Wiki 有 structured metadata
- 但仍然係被動 — 等 user 問問題先有反應

---

## 🧬 v0.7: Phase X + Phase Y 完成 (2026-04-15)

### Phase X: ClawMem 靈感

**內容：**
1. **Tiered Injection** — 唔同優先級嘅 content 分層 injection
2. **Content Half-lives** — content 有「衰減」機制，新鮮內容更重要
3. **Active Contradiction Detection** — 檢測並標記矛盾資訊

**原理：** Memory 唔係 static database，而係動態、會衰退、會矛盾嘅。

### Phase Y: CraniMem 靈感

**內容：**
1. **Write-Ahead Gating** — 新 memory 要通過 gate 先可以寫入
2. **Episodic Buffer** — 短期 memory 累積喺 buffer 入面
3. **Consolidation Loop** — 定期將 episodic 轉為 semantic

**原理：** 唔係所有嘢都直接寫入長期記憶，要經過消化（consolidation）。

### Consolidation Loop 架構

```
Episodic (7 days+) → Semantic Wiki → Procedural (Skills)
        ↑                                    ↓
        ←─────── Reflection ◯───────────────
```

每晚：
1. Episodic buffer 入面 7 天以上嘅 memory distill
2. 提取 entities、relationships、insights
3. 寫入 wiki (semantic)
4. 更新 skills (procedural)

### 發現問題

- 所有 Phase 完成，但缺乏明確嘅 evolution 方向
- 決定：建立 Roadmap 明確未來方向

---

## 🧬 v0.9: Phase Z 完成 (2026-04-17)

### 當時情况

- 發現問題：我哋嘅 memory system 唔知「自己唔知」
- 期哥問：「你幾時知 OCM 嘅？」我答：「我唔記得。」
- 但我應該知道自己「唔記得」，而唔係當記得咁回答

### Phase Z-1: Uncertainty Tracking

**決定：加入 Uncertainty Tracking (EQS Methodology)。**

```
每一個 claim 應該有：
1. Content - 乜嘢
2. Confidence - 幾肯定 (0-1)
3. Evidence - 邊個 source
4. Last Updated - 幾時更新
```

當 confidence < threshold，我哋 explicit 話「我唔記得」而唔係乱答。

### Phase Z-3: EQS Methodology

**原理：** OODA Loop (Observe-Orient-Decide-Act) 嘅應用

```
O: 觀察新資訊
O: 理解-contextualize
D: 評估-confidence 更新
A: 行動-inject / ignore
```

### 結果

- 回覆更有紀律
- 「我唔記得」「需要確認」成為正常回覆
- 期哥話：「起碼知道你唔知。」

---

## 🧬 v2.0: 7-Dir 全部完成 (2026-04-18)

### 當時情况

7-Dir Roadmap 之前狀態：
- ✅ Phase 1-5: Triple-Stream Search
- ✅ 7-Dir 1: Memory System 整合
- ✅ 7-Dir 2: Wiki Search
- ❌ 7-Dir 3: Search API (50%)
- ❌ 7-Dir 4: KG Auto-Expansion (30%)
- ❌ 7-Dir 5: Smart Recall (60%)
- ❌ 7-Dir 6: Proactive Discovery
- ❌ 7-Dir 7: Graph Visualization

### 今日做咗乜

#### 7-Dir 3: Search API
- 創建 Flask HTTP API
- Endpoints: `/search`, `/entities`, `/stats`, `/health`

#### 7-Dir 4: KG Auto-Expansion
- 改善 Multi-stage filtering
- 加入 Levenshtein distance
- 加入 Entity-type compatibility
- 加入 39 個新 entities
- **問題：** 39 entities 都指向 "ocm-sup"，但 ocm-sup 實體唔存在
- **解決：** 創建 OCM Sup entity，修復 frontmatter 格式
- **結果：** 43 nodes, 47 edges ✅

#### 7-Dir 5: Smart Recall Hook
- 加入 High priority keywords
- 修復 entities → nodes AttributeError
- 建立 smart_recall_cron.py

#### 7-Dir 6: Proactive Discovery
- 創建 `proactive_discovery.py`
- 加入 Rule-based relationship inference
- 加入 Multi-factor confidence scoring
- 加入 Bidirectional relationship check
- 加入 Learning system

#### 7-Dir 7: Graph Visualization
- 創建 `graph_visualization.py`
- 支持 Mermaid / DOT / HTML 格式
- 可視化 Entity relationships

---

## 📚 學到嘅教訓

### 1. Frontmatter Format 係關鍵

**問題：**
```yaml
---
title: 期哥
type: entity
---
# 下面呢啲唔喺 frontmatter 入面
relationships:
  - target: 古洞站
---
```

**學習：** Relationship 一定要喺 `---` 入面，否則 graph_search.py 讀唔到。

### 2. Embedding Model 有語言 Bias

**問題：** 中文-英文 cross-lingual similarity 唔可靠。

**解決：** Multi-stage filtering，唔完全依賴 embedding。

### 3. 簡單 > 複雜

**問題：** 一開始想加太多功能。

**解決：** Karpathy 原則：「Simplicity First, Surgical Changes」。

### 4. 測試係確認，唔係發現

**問題：** 我哋嘅測試係確認我哋想嘅結果，唔係真正發現問題。

**解決：** 需要 independent verification（但 subagent 環境問題...）。

### 5. Evolution 係漸進，唔係一步到位

**問題：** 一開始想做完美嘅 system。

**解決：** 隨住對用家了解加深，system 慢慢進化。

---

## 🔮 未來方向

### 短期 (1-2 個月)

- [ ] 將 scripts 包裝成 pip package
- [ ] 自動化 cron jobs
- [ ] Telegram command integration

### 中期 (3-6 個月)

- [ ] 多語言支援（中英日）
- [ ] 自動化 Relationship Discovery
- [ ] Obsidian plugin 整合

### 長期 (6+ 個月)

- [ ] 向量數據庫替換（Faiss/Milvus）
- [ ] 知識圖譜視覺化界面
- [ ] 自主學習系統

---

## 🙏 致謝

- **期哥** — 需求提出者、測試者、方向指引
- **Andrej Karpathy** — Simplicity First 原則
- **Aporia Labs** — LLM Wiki v2 架構參考
- **Anthropic** — OODA Loop / CraniMem 靈感
- **OpenClaw Community** — 框架支援

---

## 📌 如何貢獻

呢個係期哥嘅 personal project，唔係開源項目。

但如果你覺得某部分有用，你可以：

1. **Fork** — 取你需要嘅部分
2. **改** — 按你嘅情況修改
3. **諗** — 自己嘅 evolution 方向

記住：**抄係最後形式嘅學習，但創造係最初形式嘅思考。**

---

_Changelog 最後更新：2026-04-18_
_Version: 2.0_
---

## v2.1: Exact Match Boost（2026-04-21）

### 當時情况

- Triple-Stream Search 已實装，但有 Graph False Positive 問題
- 期哥查「期哥」→ Graph 返回 Quantity Surveyor（相關）→ 但期哥想要「期哥」本人
- 期哥話：「我地未做呢堆咩」— 提醒我 roadnap items 未做

### 決定

做 **P0.2（Hit Rate 定義）** 和 **P0.3（Graph False Positive Analysis）**。

### P0.2：Hit Rate 定義

**問題：** 之前沒有清楚定義「搵到」係乜意思

**解決：** 創建三級定義
- TOP1_HIT：第1個就啱
- TOP3_HIT：第1-3個有一個啱
- TOP5_HIT：第1-5個有一個相關

### P0.3：Graph False Positive Analysis

**問題：** 
- 測試 14 個 queries，False Positive Rate = 93%
- 幾乎所有 query 都被 Graph 返回的「相關」entities 搶走

**分析：**
| Query | 期望 | 實際 | 問題 |
|-------|------|------|------|
| 期哥 | 期哥本人 | Quantity Surveyor | 期哥→QS edge 太強 |
| 古洞站 | 古洞站 | 期哥 | 期哥→古洞站 edge 太強 |
| OpenClaw | OpenClaw | Hermes Agent | OpenClaw→Hermes edge 太強 |

**解決方案：** Exact Match Boost

當 query 精確匹配某 entity title，該 entity 被放到結果頂部（score = 10000）。

代碼實現：
```python
def _exact_match_boost(query, bm25_results, boost_factor=50.0):
    # 將精確匹配放到 BM25 results 頂部，score = 10000

def _exact_match_graph_boost(query, graph_results):
    # 將精確匹配放到 Graph results 頂部，score = 10000
```

### 結果

| 指標 | 修復前 | 修復後 |
|------|---------|--------|
| TOP1_HIT_RATE | 0% | **82.4%** (14/17) |
| False Positive Rate | 93% | **17.6%** |

### 仍然失敗（3個）

1. **Triple-Stream** → BM25（應該匹配 "Triple-Stream Search"）
2. **Hermes Agent** → Hermes 接入即夢 CLI（應該匹配 "Hermes Agent"）
3. **Lossless-Claw** → Hermes 接入即夢 CLI（應該匹配 "Lossless-Claw"）

**原因：** Multi-word entity names 未完全處理（Boost logic 只做 exact match，唔做 substring match）

### 教訓

1. **Graph 太 aggressive** — 容易找到「相關」entities，但用家多數想要「精確」entities
2. **Entity files 好多冇 body content** — 只有 frontmatter + relationships，BM25 搵唔到
3. **Build first, document later** — 期哥提醒我要記錄進步/失敗

### 下一步

- [ ] P0.1：擴大 Benchmark Dataset（3 queries → 20+ queries）
- [ ] 修復 Multi-word entity matching（Triple-Stream → "Triple-Stream Search"）


## v3.0: P0 100% TOP1 HIT（2026-04-22）

### 完成情况

| Phase | 內容 | 日期 | 結果 |
|-------|------|------|------|
| P0.1 | Expand Benchmark | 2026-04-22 | 17 → 35 queries |
| P0.2 | Hit Rate 定義 | 2026-04-22 | 三級定義建立 |
| P0.3 | Exact Match Boost | 2026-04-22 | 59.3% → 81.5% |
| P0.4 | Substring Matching | 2026-04-22 | 81.5% → 100% |
| P0.5 | Add Missing Entities | 2026-04-22 | 100% ✅ |

### 最終結果

- **TOP1 Rate: 35/35 = 100%** 🎉
- **TOP3 Rate: 35/35 = 100%**
- **TOP5 Rate: 35/35 = 100%**
- **0 個失敗 cases**

### 新增 Entity Docs

- `query-expansion.md`（1513 bytes）
- `retention-scan.md`（1731 bytes）
- `tavily.md`（1202 bytes）
- `reciprocal-rank-fusion.md`（1423 bytes）

### 技術突破

1. **Exact Match Boost**：精確匹配 entity title 時 score = 10000
2. **Substring/Prefix Matching**：處理 multi-word entities
3. **Position-Aware Title Boost**：匹配位置越前 boost 分數越高
4. **BM25 + Vector + Graph + RRF Fusion**：四流合併

### 教訓

1. **Cache corruption 要即時修復** — embedding cache JSON 損壞會導致 rebuild 失敗
2. **Lazy load 係未來優化方向** — 全量 rebuild 3338 docs 需要 277 秒
3. **100% 唔係終點** — 35 queries 係基本覆蓋，真實 usage 可能有不同的 queries

### 下一步

- [ ] P1.1：速度優化（Lazy load）
- [ ] P1.2：Relevance Ranking 改善
- [ ] P2：Evaluation 自動化（AB Test + Regression 檢測）


---

## 🧬 v2.1: Continuity Layer 完成 (2026-04-24)

### 當時情况

- OCM Sup 已有 Triple-Stream Search (BM25 + Vector + Graph)
- 但缺乏 `/new` carryover 和 structured follow-up 功能
- 期哥話：「/new之後掉回寒暄，唔記得之前傾緊乜」

### Phase 1 完成 (2026-04-22)

1. **State Router** — 消息分類 (casual/staged/tracked)
2. **Carryover Manager** — `/new` session continuity
3. **Hook Lifecycle** — due/render/complete 鉤子

### Phase 2 完成 (2026-04-24)

4. **Frontstage Guard** — 防止內部邏輯泄露
5. **OCM Graph Integration** — Wiki 實體整合
6. **Daily Memory Traces** — 結構化蹤跡

### Items 1-3 完成 (2026-04-24 下午)

7. **Cron Setup** — `setup_cron.sh`
8. **Telegram Bot** — `telegram_notify.py` + `setup_telegram.sh`
9. **Real Conversation Test** — `real_conversation_test.py` (4/5 passed)

### Benchmark 完成 (2026-04-24 下午)

| Benchmark | 結果 | 評級 |
|-----------|------|------|
| Latency | P99: 419ms, Mean: 251ms | 🟡 Good |
| Load | 18.7 qps, No errors | 🟢 Excellent |
| Continuity | Mean: 39ms overall | 🟡 Good |

### 新增文件

```
scripts/continuity/
├── __init__.py
├── state_router.py          (22KB)
├── carryover.py             (17KB)
├── continuity_state.py      (17KB)
├── hook_lifecycle.py        (19KB)
├── frontstage_guard.py      (9KB)
├── ocm_graph_integration.py (20KB)
├── daily_memory_trace.py    (15KB)
├── setup_cron.sh            (6.6KB)
├── setup_telegram.sh        (3.9KB)
├── telegram_notify.py        (5.8KB)
├── integration_test.py      (12.6KB)
├── real_conversation_test.py (7.4KB)
├── continuity_benchmark.py  (10.3KB)
└── latency_benchmark.py     (5.5KB)

continuity_api.py            (11.3KB) — HTTP API
USAGE_CARRYOVER.md           (4.6KB) — 使用指南
```

### 學到嘅教訓

1. **Lazy loading 好重要** — Vector loading 從 277s 降到 5s
2. **RRF weights 要調** — Graph weight 1.5 太高，降到 0.8
3. **測試先行** — Integration test 發現 93% 問題
4. **Benchmark 必要** — 確認優化有效

