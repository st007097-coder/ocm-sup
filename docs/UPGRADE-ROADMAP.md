# OCM-Sup 第三輪升級路線圖：由 7.5 → 8.5

_Last Updated: 2026-04-19 10:25 HKT_
_基於：Second-round GitHub Reviewer Feedback_

---

## 當前位置

| 維度 | 分數 | 狀態 |
|------|------|------|
| Vision | 8.5/10 | ✅ 高 |
| Technical ambition | 9/10 | ✅ 高 |
| Evidence | 7/10 | ⚠️ 有數據但唔夠全面 |
| Engineering clarity | 6.5/10 | ⚠️ MODULES.md 有，但 scripts 有 duplicate |
| Production readiness | 6/10 | ⚠️ 有 pytest，冇 Docker |
| **Overall** | **7.5/10** | 開始係可認真對待的 framework |

---

## 目標：提升到 8.5/10

**關鍵唔係再加功能，而是：**
1. 更硬的評測
2. 更大的測試集
3. 更長期的驗證
4. 更低摩擦的部署

---

## P0：一星期內可做（High Impact, Low Effort）

### P0.1：擴大 Benchmark Dataset（Evidence）

**目標：** 由 3 個 test queries → 20+ queries，包含 hard cases

**具體做法：**
- 新增 10 個「陌生」queries（唔係我熟悉嗰類）
- 新增 5 個 ambiguous queries（多個可能解釋）
- 新增 5 個 cross-lingual edge cases（日文/英文混雜）

**成功標準：**
```
之前：3 queries, 95% hit rate
之後：20 queries, hit rate 唔應該跌太多（目標 >85%）
```

**預計時間：** 2-3 小時

### P0.2：明確「Hit Rate」定義（Evidence）

**目標：** 唔再含糊定義「找到就算 hit」

**具體做法：**
```python
# 三級定義
TOP1_HIT = retrieve exact entity requested
TOP3_HIT = retrieve relevant entity in top-3
TOP5_HIT = retrieve related entity in top-5 (even if not exact)

# 額外指標
STALE_HIT = retrieve entity but information is outdated (>30 days old)
BAD_HIT = retrieve entity that leads to wrong conclusion
```

**成功標準：** README 有明確 metric 定义 + 三級評分結果

**預計時間：** 1-2 小時

### P0.3：Graph False Positive Analysis（Engineering）

**目標：** 確認 Graph 嘅 false positive 幾高，值唔值得保留

**具體做法：**
1. 列出最近 10 次 Graph search 的 results
2. 標記邊個係「真相關」vs「 proximity illusion」
3. 計算 false positive rate

**成功標準：**
```
如果 false positive > 30% → Graph 降級為 optional
如果 false positive < 15% → 保留為 core
```

**預計時間：** 2 小時

### P0.4：寫「已知弱點」章節（Evidence）

**目標：** 承認邊啲部分未站稳，增加可信度

**具體做法：** 在 FAILURE-CASES.md 新增「Current Weaknesses」section：
```
## 已知弱點

### Graph（仍係 Experimental）
- edge 品質未完全驗證
- BFS 可能引入 proximity illusion
- 建議：只用喺 entity relationship 已知嘅場景

### Proactive Discovery
- false positive 未完全控制
- 建議：人類確認 Gate 仍然需要

### Uncertainty Calibration
- 需要更多 eval 驗證
- 目前只係 0-1 confidence scale，唔夠細

### Multilingual Benchmark
- 樣本仍有限（主要係中文+英文）
- 日文/其他語言未充分測試
```

**預計時間：** 1 小時

---

## P1：一個月內可做（Medium Impact, Medium Effort）

### P1.1：7日長跑測試（Evidence）

**目標：** 證明 system 唔會「用耐咗就腫」

**具體做法：**
1. 創建 cron job，每日自動：
   - 生成 5 個 test queries
   - 記錄 retrieval quality
   - 記錄 graph size / entity count
   - 記錄 stale memory count
2. 運行 7 日，收集數據
3. 分析：graph size growth rate、recall quality trend

**成功標準：**
```
7日後：
- Graph size 增長 < 20%（唔係指數爆發）
- Recall quality 維持 >85%（唔會退化）
- Stale memory < 10%（cleanup 正常運作）
```

**預計時間：** 1-2 天設置 + 7 天數據收集

### P1.2：Cost-Benefit Table（Evidence）

**目標：** 證明「複雜度係值得」

**具體做法：**
| 配置 | Latency | Hit Rate | Cost (tokens) | ROI |
|------|---------|----------|---------------|-----|
| BM25 only | 0.4ms | 85% | 50 | baseline |
| BM25+QE | 0.5ms | 90% | 60 | +5% quality, +10 cost |
| BM25+QE+Aliases | 0.6ms | 93% | 70 | +8% quality, +20 cost |
| BM25+Vector | 102ms | 95% | 5000 | +10% quality, +5000 cost |
| BM25+Graph | 1.1ms | 90% | 80 | +5% quality, +30 cost |
| Full Triple | 41.2ms | 95% | 5100 | +10% quality, +5050 cost |

**結論：** BM25+QE+Aliases 係最高 ROI（+8% quality at +20 cost）

**預計時間：** 3-4 小時

### P1.3：Production Deployment Path（Production Readiness）

**目標：** 降低 deployment friction

**具體做法：**
1. 創建 `Dockerfile`：
   - Python 3.11 + venv
   - Ollama as separate container
   - Wiki volume mount
2. 創建 `docker-compose.yml`：
   - openclaw + ollama + wiki
3. 創建 `DEPLOY.md`：
   - 一鍵 setup 指令
   - 常見問題解答

**成功標準：**
```bash
git clone https://github.com/st007097-coder/ocm-sup.git
cd ocm-sup
docker-compose up
# → System running, /search endpoint accessible
```

**預計時間：** 4-6 小時

### P1.4：Real Workflow Case Study（Evidence）

**目標：** 唔好淨係 benchmark，最好有真 agent 任務案例

**具體做法：**
選擇 3 個真實期哥工作場景：
1. 「上星期期哥問過呢個分判商價錢，我記得佢點答」
2. 「古洞站混凝土用量，三個月前討論過」
3. 「期哥話想換供應商，但未決定邊個」

每個場景：
- 記錄 query
- 記錄 expected recall
- 記錄 actual recall
- 評估「幫助 decision」程度（1-5分）

**成功標準：**
```
3 個 real cases：
- 至少 2 個達到 4/5 decision quality
- 1 個可以「完全回答」
- 0 個「完全答錯」
```

**預計時間：** 3-4 小時（需要回顧歷史對話）

---

## P2：論文/產品級（High Effort, High Impact）

### P2.1：OpenAPI Spec + Monitoring Dashboard（Production Readiness）

**目標：** 變成真正嘅「platform」而唔係 scripts

**具體做法：**
1. OpenAPI 3.0 spec for `/search`, `/entity`, `/stats`
2. Prometheus metrics endpoint
3. Grafana dashboard showing：
   - Query latency P50/P95/P99
   - Hit rate over time
   - Graph size growth
   - Error rate

**預計時間：** 1-2 周

### P2.2：Multilingual Benchmark（Evidence）

**目標：** 證明 system 唔只係中英文

**具體做法：**
- 日文 queries（學習日文建築術語）
- 韓文 queries（可能涉及韓國分判商）
- 測試東南亞建築術語（泰文/馬來文）

**預計時間：** 1 周

### P2.3：Memory Pollution Control（Engineering）

**目標：** 解決「用耐咗就腫」問題

**具體做法：**
1. 實現「記憶衝突檢測」：
   - 同一 entity 有多個矛盾嘅 lastAccessed → 標記 warning
2. 實現「自動降級」：
   - 30天未 access 的 entity → confidence -0.1
   - 60天未 access → 自動 archive
3. 實現「合并策略」：
   - duplicate entity detection
   - 自動 merge 而唔係保留兩份

**預計時間：** 1-2 周

---

## 資源估算

| Phase | 時間 | 難度 | Impact |
|--------|------|------|--------|
| P0 | 6-8 小時 | 低 | 高（立即可見）|
| P1 | 2-3 周 | 中 | 高（顯著提升可信度）|
| P2 | 1-2 月 | 高 | 極高（變成真正 platform）|

---

## 推薦優先順序

**如果期哥想快啲提升分數：**

1. **P0.1（擴大 benchmark）** — 最快見效，證明唔係 cherry-pick
2. **P0.4（寫已知弱點）** — 免費，立刻提升可信度
3. **P1.1（7日長跑測試）** — 解決長期运行担忧
4. **P1.2（cost-benefit table）** — 回答「複雜度值得嗎」核心問題
5. **P1.3（Docker）** — 降低 deployment friction

**如果想一步到位：**
P1.3（Docker）+ P1.1（7日長跑）係最佳 combo，直接解決最大懷疑

---

## 當前最大懷疑（Reviewer 提出）

### 懷疑 1：長期運行會唔會腫？

**回答方案：** P1.1（7日長跑測試）+ P2.3（Memory Pollution Control）

### 懷疑 2：主動發現會唔會過度聰明？

**回答方案：** P0.3（Graph false positive analysis）+ 人類確認 Gate 保持開啟

---

## 最終目標

由：

```
「有想法的 memory project」
```

升級去：

```
「開始有研究可信度 / 工程可信度的 system」
```

再升級去：

```
「可被驗證、可被部署、可被維護的 memory framework」
```

---

_Last updated: 2026-04-19 10:25 HKT_
_Author: 阿星 (Ah Sing)_
_Document: OCM-Sup 第三輪升級路線圖（7.5 → 8.5）_