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
## 🧬 v2.3: AI 失憶問題研究 — Proactive Memory System (2026-04-25)

### 當時情况

- 所有現有系統都係被動觸發（keyword trigger）
- Active Memory → keyword trigger
- Smart Recall Hook → keyword trigger
- 根本問題：冇 proactive 機制
- AI 依然會忘記做過嘅嘢，即使有完整 memory systems

### 發現嘅 Root Cause

所有現有系統都被動：等 user 問問題 → 先做 search
冇主動發現新舊知識連接嘅機制

### 解決方案：Proactive Memory System

#### Phase 1: Session Start Memory Load
- Script: session_start_memory_load.py
- 功能：Session 開始時自動 load 三層 context
  - Must Keep Facts（压縮前 checkpoints）
  - 上次 Session Summary
  - 近 5 日 Memory
- 位置: /root/.openclaw/workspace/scripts/

#### Phase 2: Pre-compression Checkpoint
- Script: pre_compression_checkpoint.py
- 功能：压縮前自動識別重要 facts 保存去 must_keep_facts.md
- 結果: 60 facts 被保存

#### Phase 3: Proactive Discovery Super Quick
- Script: proactive_discovery_super_quick.py
- 原理: 直接掃描 wiki 目錄，繞過慢速 LLM query
- 性能提升: ~275 秒 → ~1 秒（275x faster）
- 整合入: Consolidation Loop

#### Phase 4: Session End Summary
- Script: session_end_summary.py
- 功能: Session 結束時自動生成 structured summary
- 觸發: 用戶話「聽晚再傾」「下次再傾」或長 pause

#### Phase 5: Session-Memory Hook
- 發現: OpenClaw 内置 session-memory hook
- 觸發: command:new, command:reset
- 功能: 保存最近 15 條 messages 去 memory/YYYY-MM-DD-slug.md
- 設定: 已添加到 openclaw.json

#### Phase 6: Consolidation Loop
- Script: consolidation-loop.sh
- 流程:
  1. Episodic distillation（placeholder）
  2. Proactive Discovery（~1 sec）
  3. Pre-compression checkpoint
- 總時間: ~280 秒 → ~2 秒（140x faster）

### 完成嘅 Tasks

| Task | 狀態 | 備註 |
|------|------|------|
| Task 1: Active Memory 分析 | ✅ | keyword trigger 確認 |
| Task 2: Smart Recall Hook 分析 | ✅ | keyword trigger 確認 |
| Task 3: Session Start Memory Load | ✅ | 3-layer context |
| Task 4: Pre-compression Checkpoint | ✅ | 60 facts saved |
| Task 5: Proactive Discovery 整合 | ✅ | ~1 sec (275x faster) |
| Task 6: 獨立 Cron Job | ✅ | 整合入 Consolidation Loop |
| Task 7: OpenClaw Hooks 研究 | ✅ | session-memory hook 發現 |

### Benchmark 結果

| Component | Before | After | Improvement |
|-----------|--------|-------|-------------|
| Proactive Discovery | ~275 sec | ~1 sec | 275x faster |
| Total Loop Time | ~280 sec | ~2 sec | 140x faster |
| Must Keep Facts | 0 | 60 | ✅ |
| Session Start Load | 0 | 3 layers | ✅ |

### 關鍵教訓

1. 被動 vs 主動: 所有現有系統都被動，要加 proactive trigger
2. 速度係關鍵: 慢速 scripts 冇人用，快先係道理
3. Hook 系統: OpenClaw 内置 hook 可以利用，唔好自己重造
4. 兩層備份: session-memory (raw) + session_end_summary (structured)

---
_Changelog 最後更新：2026-04-25_
_Version: 2.3_

## 🧬 v2.4: Memory Stability System (2026-04-26)

### 當時情况

GPT 分析指出架構問題：
- Memory Write 不穩（LLM extraction non-deterministic）
- Vector + Graph 不同步（memory 分裂）
- Agent 無 memory selection 策略（context 污染）
- Memory 無 lifecycle（只加不減）

### 解決方案：Memory Stability System

#### P0-1: Memory Write Gate
- Script: memory_write_gate.py
- 功能：pre-write validation（schema + content + dedup + canonicalization）
- Rejection log: memory/logs/memory_rejects.log

#### P0-2: Memory Transaction Sync
- Script: memory_tx_sync.py
- 功能：Single Source of Truth atomic sync
- Flow: LLM extraction → structured JSON → derived (vector + graph)

#### P1-1: Memory Consistency Checker
- Script: memory_consistency_check.py
- 功能：duplicate / contradiction / structural issue 檢測
- Health score = 100 - (issues / total) * 20

#### P1-2: Memory Relevance Filter
- Script: memory_relevance_filter.py
- Score = semantic_similarity * 0.6 + recency * 0.2 + importance * 0.2

#### P2-1: Cross-Encoder Reranker
- Script: memory_cross_encoder.py
- 功能：Lightweight cross-encoder reranking
- Combined score = cross_encoder * 0.5 + original_rrf * 0.5

#### P2-2: Memory Pruning & Decay
- Script: memory_pruning.py
- 功能：lifecycle management
- Decay: half-life 30 days, Prune: archive + delete

### 整合：Consolidation Loop v2.4

| Step | Module | Status |
|------|--------|--------|
| 0 | Memory Write Gate | ✅ |
| 1 | Transaction Sync | ✅ |
| 2 | Consistency Check | ✅ (Health: 100%) |
| 3 | Relevance Filter ready | ✅ |
| 4 | Cross-Encoder ready | ✅ |
| 5 | Pruning status | ✅ |
| 6 | Proactive Discovery | ✅ |
| 7 | Pre-compression Checkpoint | ✅ |

Total time: ~3 sec

### 關鍵教訓

1. Pre-write gate > post-write checkpoint：事前攔，唔係事後修
2. Single source of truth：所有 derived data 來自同一 source
3. Transaction log：失敗時可以 rollback
4. Health score：量化系統健康狀態

---
_Changelog 最後更新：2026-04-26_
_Version: 2.4_
