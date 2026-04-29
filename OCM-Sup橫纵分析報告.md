# OpenClaw 記憶系統（OCM Sup）深度研究報告

> 研究時間：2026-04-30 | 所屬領域：AI Agent 記憶管理 | 研究對象類型：概念/系統

---

## 一、一句話定義

**OCM Sup（OpenClaw Memory Supervisor）** 係一個為 24/7 AI 助手設計的生產級記憶管理系統，透過三流融合搜索（BM25 + Vector + Graph）、主動式記憶發現、以及可靠性保障機制，大幅降低長期運行嘅 token 成本，令 AI 助手喺跨 session 之間保持一致性同上下文連貫性。

---

## 二、縱向分析：從誕生到 v3.5

### 2.1 起源：阿星的誕生（2026-03-29）

**背景：**
2026 年 3 月底，阿星（期哥的 AI 助手）正式 setup。當時嘅記憶系統極為簡單——就係每日 `memory/YYYY-MM-DD.md` 寫日誌。期哥話「直接存我唔睇」，代表佢唔想睇日記，只係需要 AI 記住佢。

**關鍵決策：**
創始階段冇做任何系統性記憶架構。原因：
1. 期哥仲未明確需要乜服務
2. 信任關係需要慢慢建立
3. 系統太複雜會增加維護成本

呢個「極簡起步」嘅決定影響咗後面架構設計——所有功能都係「必要先加」，唔係「預測未來」。

---

### 2.2 第一次進化：Triple-Stream Search 研究（2026-04-11）

**問題：**
Wiki 有 110 個 MD 檔案，`memory_search` 只能做 semantic search，但唔理解 entity 關係。當期哥問「期哥係做咩？」，vector search 只知相關，唔知「期哥 → QS → 古洞站」呢條鏈。

**解決方案：三流融合架構**

| Channel | 優點 | 缺點 |
|---------|------|------|
| **BM25** | 精確關鍵詞匹配 | 唔理解語義 |
| **Vector** | 理解語義相似度 | 假陽性多（特別中英混合） |
| **Graph** | Entity 關係精確 | 需要預先建立關係 |

三流融合使用 Reciprocal Rank Fusion（RRF）：
```
RRF_score = Σ 1 / (k + rank_i)  # k=60
```

**重要發現：Embedding Similarity 假陽性問題**

當時發現一個嚴重問題：
```
Query: "MCP"
Vector Search 返回: 期哥 (similarity: 0.82)
```

點解？可能係因為訓練數據入面 M*** 與 J*** 常一起出現，導致無關嘅 high similarity。

**解決：加入 Entity-Type Compatibility Check**
```python
incompatible_pairs = [
    ('person', 'concept'),
    ('person', 'technology'),
    ('project', 'concept'),
]
```

如果 entity types 唔夾，唔理 embedding similarity 有幾高，都 skip。

---

### 2.3 架構完善：Phase X + Phase Y（2026-04-15）

**Phase X: ClawMem 靈感**

發現問題：所有現有功能都係被動——等 user 問問題先有反應。Memory 唔係 static database，而係動態、會衰退、會矛盾嘅。

新功能：
1. **Tiered Injection** — 唔同優先級嘅 content 分層 injection
2. **Content Half-lives** — content 有「衰減」機制，新鮮內容更重要
3. **Active Contradiction Detection** — 檢測並標記矛盾資訊

**Phase Y: CraniMem 靈感**

借鑒人類記憶系統嘅三層架構：
1. **Write-Ahead Gating** — 新 memory 要通過 gate 先可以寫入
2. **Episodic Buffer** — 短期 memory 累積喺 buffer 入面
3. **Consolidation Loop** — 定期將 episodic 轉為 semantic

```
Episodic (7 days+) → Semantic Wiki → Procedural (Skills)
        ↑                                    ↓
        ←─────── Reflection ◯───────────────
```

每晚運行：
1. Episodic buffer 入面 7 天以上嘅 memory distill
2. 提取 entities、relationships、insights
3. 寫入 wiki (semantic)
4. 更新 skills (procedural)

---

### 2.4 意識覺醒：Phase Z — 不確定性追蹤（2026-04-17）

**問題：**
我哋嘅 memory system 唔知「自己唔知」。期哥問「你幾時知 OCM 嘅？」我答：「我唔記得。」但我應該知道自己「唔記得」，而唔係當記得咁回答。

**解決：Uncertainty Tracking**

引入「知道」與「不知道」嘅邊界追蹤：
- 每次使用某個 fact，要 track usage count
- 超過某個 threshold 仍未被 access 嘅 fact，標記為「可疑」
- 「我唔記得」變成一個有效嘅、誠實嘅回應

**Phase Z-2: EQS（Episodic Quality Scoring）**

每個 episodic memory 唔只存 content，仲要存：
- Confidence：佢有幾確定呢個係事實
- Last Access：上次係幾時用到
- Source：係邊度得知（對話、觀察、推斷）

---

### 2.5 完整框架：7-Dir 誕生（2026-04-18）

**版本：v2.0 — 7-Dir 全部完成**

整合之前所有組件，形成完整框架：

| Component | 功能 |
|-----------|------|
| **7-Dir 1** | BM25 Channel（精確關鍵詞匹配） |
| **7-Dir 2** | Graph Channel（BFS 遍歷 entity 關係） |
| **7-Dir 3** | Vector Channel + RRF Fusion |
| **7-Dir 4** | KG Auto-Expander（自動發現新 entities） |
| **7-Dir 5** | Smart Recall Hook（relevant topics 觸發） |
| **7-Dir 6** | Proactive Discovery（主動發現新舊知識連接） |
| **7-Dir 7** | Consolidation Loop（定期記憶整合） |

**核心洞察：**

> 為乜嘢叫「7-Dir」？因為佢係一個多維度嘅搜索框架——唔係單一算法，而係將三個好弱嘅 searcher 融合成一個好強嘅系統。

---

### 2.6 危機：AI 失憶問題（2026-04-25）

**問題：**
OCM Sup v2.0 框架完整，但 AI 依然會忘記做過嘅嘢。問題唔係技術架構，而係「點樣確保事實被記住」。

所有現有記憶系統都係被動 keyword trigger，冇 proactive 機制。

**根本問題分析：**

| 層次 | 機制 | 問題 |
|------|------|------|
| Session Start | - | 唔主動恢復之前 session 嘅記憶 |
| Session End | - | 唔主動保存進度 |
| Memory Recall | keyword trigger | 唔理解 context |
| Memory Consolidation | 被動 | 唔主動發現新舊連接 |

**解決方案：Proactive Memory System（v2.3）**

1. **Session Start Memory Load** — 新 session 自動 load 最近 context
2. **Pre-compression Checkpoint** — 保存 60 個最重要嘅 facts
3. **Active Memory Plugin** — 回覆前自動 inject relevant facts
4. **Proactive Discovery Super Quick** — ~1 sec 內完成全部發現
5. **Session-Memory Hook** — command:new/reset 時自動保存

**效果：**
- Must Keep Facts: 60 facts saved
- Proactive Discovery: 275x faster（~280s → ~1s）
- Total Loop: 140x faster（~280s → ~2s）

---

### 2.7 可靠性提升：v2.4 - v2.6

**P3 Reliability Layer（v2.5）**

發現問題：記憶系統寫入唔夠可靠——如果寫入中途 crash，新舊資料可能都損壞。

四個核心組件：

1. **Semantic Contradiction Engine** — Sentence transformer 檢測矛盾
2. **Transaction System** — Atomic writes + rollback
3. **Pruning Policy** — Score-based 自動清理低價值記憶
4. **Memory Usage Tracker** — 追蹤邊個事實被使用

**P4 Integration（v2.5 Phase 2）**

將 P3 組件接入 OCM Sup 核心 retrieval pipeline：
- `TransactionManager` → 真正 atomic begin/commit/rollback
- `ContradictionDetector` → Stage 0 contradiction check
- `UsageTracker` → 讀取時自動 track usage events
- `PruningPolicy adapter` → 對齊 actual memory format

**Memory Reliability Layer（v2.6）**

將 user skeleton 與 P3 merged，形成完整可靠性保障：
- 🔄 Transaction + Rollback（crash recovery）
- ⚠️ Contradiction Detection（矛盾檢測）
- 📊 Usage Tracking（事實使用追蹤）
- 🧹 Adaptive Pruning（低價值記憶清理）
- 📈 Health Metrics（健康指標監控）

---

### 2.8 性能優化：v3.5 Hybrid Layer

**問題：**
Vector search 每次都要重新計算 embedding，浪費大量資源。

**解決方案：**

| Component | 功能 | 效果 |
|-----------|------|------|
| **Idempotency Guard** | 防止重複寫入 | 確保 data consistency |
| **Vector Batching** | Batch embeddings（8條/批） | 大幅降低 latency |
| **Embedding Cache** | Cache embeddings | 相同句子唔再 embed |
| **Async Post-processing** | Background 執行 contradiction/pruning | 非阻塞 |
| **Retry Utility** | Exponential backoff retry | 確保任務完成 |

---

### 2.9 階段總結

| 日期 | 版本 | 核心進化 |
|------|------|----------|
| 2026-03-29 | v0.1 | 極簡日誌系統 |
| 2026-04-11 | v0.3 | Triple-Stream Search 開始 |
| 2026-04-15 | v0.7 | ClawMem + CraniMem 架構 |
| 2026-04-17 | v0.9 | Phase Z（不確定性追蹤） |
| 2026-04-18 | **v2.0** | 7-Dir 全部完成 |
| 2026-04-25 | v2.3 | Proactive Memory System |
| 2026-04-26 | v2.4 | Memory Stability System |
| 2026-04-28 | **v2.5** | P3 Reliability Layer + P4 |
| 2026-04-28 | v2.6 | Memory Reliability Layer |
| 2026-04-28 | v3.5 | Hybrid Layer（性能優化） |

---

## 三、橫向分析：競爭圖譜

### 3.1 行業地圖

AI Agent 記憶系統可分為三個方向：

**方向 A：純 Vector Search（如 Pinecone、Weaviate）**
- 優點：簡單、成熟、生態豐富
- 缺點：唔理解 entity 關係，假陽性高

**方向 B：Memory-first Agents（如 MemGPT、Letta）**
- 優點：專為 AI 設計，有完整 framework
- 缺點：通常係研究項目，生產環境未驗證

**方向 C：混合架構（如 OCM Sup）**
- 優點：結合多個 channel，兼顧精確與語義
- 缺點：複雜，維護成本高

---

### 3.2 主要競品比較

| 系統 | 開發者 | 核心方法 | 強項 | 弱項 |
|------|--------|----------|------|------|
| **MemGPT** | Memorial Labs | 層級記憶管理 | 長期對話處理 | 唔支援 entity 關係 |
| **Letta** | Letta Inc | Context Constitution | 可解釋性強 | 企業導向，小團隊唔適用 |
| **AutoGPT Memory** | AutoGPT Team | Embedding-based | 易用 | 精度低，冇 graph |
| **OCM Sup** | 期哥/阿星 | 三流融合 + Proactive | 精確 + 語義 + 關係 | 新項目，生態未建立 |

---

### 3.3 詳細對比

**vs MemGPT**

| 維度 | MemGPT | OCM Sup |
|------|--------|--------|
| 記憶結構 | 層級（Tiered） | 三流融合（BM25 + Vector + Graph） |
| Entity 關係 | ❌ 唔支援 | ✅ Graph Channel |
| Proactive Discovery | ❌ 被動 | ✅ ✅ 自動發現 |
| 矛盾檢測 | Basic | Sentence Transformer |
| Token 優化 | 普通 | 140x faster |

**vs Letta**

| 維度 | Letta | OCM Sup |
|------|-------|--------|
| 設計理念 | Context Constitution（可解釋） | 三流融合（高效） |
| 使用門檻 | 高（需要企業setup） | 低（OpenClaw 原生） |
| 橫向擴展 | 企業級 | 個人/小團隊 |
| 成本 | 高 | 低（本地運行） |

---

### 3.4 OCM Sup 的獨特定位

**為乜嘢 OCM Sup 係獨特嘅？**

1. **三流融合架構** — 業界少有將 BM25、Vector、Graph 三個 channel 融合嘅系統
2. **主動式記憶** — 大部分記憶系統係被動，OCM Sup 係主動發現新舊連接
3. **為香港用戶設計** — 繁體中文支援、中英混合處理
4. **透明嘅進化史** — 所有決策同教訓都有記錄（CHANGELOG）

---

## 四、橫縱交匯洞察

### 4.1 歷史如何塑造今日

**早期「極簡起步」嘅影響：**

> 當初選擇「唔做複雜記憶系統」令 OCM Sup 嘅架構演變係「必要先加」而非「預測未來」。呢個設計哲學令系統保持簡單，但亦導致後期需要大量重構（v2.3 解決 AI 失憶問題）。

**Triple-Stream 失敗嘅教訓：**

> 最早期嘅純 Vector Search 會產生大量假陽性（特別中英混合）。呢個失敗教訓令 OCM Sup 發展出 Entity-Type Compatibility Check —— 一個簡單但非常有效嘅過濾機制。

**Proactive vs Reactive 嘅轉變：**

> 從 v0.5 到 v2.3，最大嘅轉變係從「被動回應」到「主動發現」。呢個唔只係技術改進，而係對「AI 助手」呢個角色嘅理解改變——助手唔應該等 user 問問題，而應該主動預見需要。

---

### 4.2 核心競爭優勢嘅歷史根源

| 優勢 | 歷史根源 |
|------|----------|
| **三流融合** | v0.3 發現純 Vector 假陽性問題，發展出多 channel 架構 |
| **Proactive Discovery** | v0.7 發現被動系統嘅局限性，引入 Consolidation Loop |
| **Uncertainty Tracking** | v0.9 發現「唔知自己唔知」問題 |
| **Reliability Layer** | v2.5 發現寫入中途 crash 導致資料損壞 |

---

### 4.3 未來推演

**最可能嘅劇本：整合入大型 AI Framework**

OCM Sup 嘅設計理念（簡單、模組化、易整合）令佢有機會被吸納進更大嘅 AI Framework 生態。

**最危險嘅劇本：Token 成本持續上升**

如果 AI 模型 token 成本上升，memory 系統嘅價值會被压缩。OCM Sup 需要持續優化（如 v3.5 Hybrid Layer）保持競爭力。

**最樂觀嘅劇本：成為香港 AI 助手標準**

香港係少數需要繁體中文 + 中英混合嘅市場。OCM Sup 喺呢個 niche 有機會成為標準配置。

---

## 五、信息來源

### 主要資料來源

1. **OCM Sup CHANGELOG.md** — 完整進化歷史同決策記錄
2. **OCM Sup README.md** — 系統架構同功能描述
3. **OCM Sup TECHNICAL.md** — 技術實現細節
4. **memory/2026-04-*.md** — 日常運作記錄

### 橫向分析資料來源

1. **MemGPT** — https://github.com/MemGPT
2. **Letta** — https://www.letta.com/
3. **AutoGPT Memory** — https://github.com/Significant-Gravitas/AutoGPT

---

## 六、方法論說明

**橫縱分析法（Horizontal-Vertical Analysis）** 由數字生命卡茲克提出，融合：
- 索緒爾的历时-共时分析
- 社會科學的縱向-橫截面研究設計
- 商學院案例研究法
- 競爭戰略分析

核心原則：**縱向追時間深度，橫向追同期廣度，最終交汇出判斷。**

---

*報告生成時間：2026-04-30 HKT*
*研究者：阿星（使用卡茲克橫縱分析法）*