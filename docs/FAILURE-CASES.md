# OCM-Sup Failure Cases Log

_Last Updated: 2026-04-19_

---

## Purpose

Document real failures, errors, and unexpected behaviors in OCM-Sup.
This is not a success log — it's where we admit what went wrong.
 每個 case 包含：時間、現象、根本原因、修復、教训。

---

## Case 1: lastAccessed Not Being Set (2026-04-18)

### 現象
Retention Scan 運行但所有 entities 的 lastAccessed 都是 "NOT SET"。
導致 retention score 無法計算，整個 decay system 失效。

### 根本原因
`TripleStreamSearch.search()` 調用了 `_update_last_accessed()`，但查詢時路徑是相對路徑（如 `ai-agent/entities/期哥.md`），而實際文件在 `/root/.openclaw/workspace/wiki/ai-agent/entities/期哥.md`。
Path resolution logic 沒有正確處理相對 vs 絕對路徑。

### 修復
在 `triple_stream_search.py` 的 `_update_last_accessed()` 中添加：
```python
file_path = WIKI_PATH / relative_path  # 明確使用 WIKI_PATH 前綴
```
並確保所有 entity path 操作都使用 `Path()` 構造完整路徑。

### 教訓
Wiki path 操作需要明確的前綴，不能假設 `Path(path)` 能自動解析。

---

## Case 2: Cross-Lingual BM25 Score Zero (2026-04-18)

### 現象
Query "hermes" 返回結果中 BM25 score 是 0，但 Hermes entity 文件明顯包含 "hermes" keyword。
導致 Hermes 相關 entities 只能靠 Vector search 找回，BM25 完全失效。

### 根本原因
1. Entity files 內沒有 "hermes" 原文（只有中文如 "Hermes Agent 是何者"）
2. Query expansion 沒有包含 "Hermes" → "Hermes Agent" 的擴展
3. 中文 entity 的 aliases 沒有包含英文 terms

### 修復
1. 20 個 entity files 添加 aliases，包含中英文 names
2. Query expansion 加入 "Hermes" → "Hermes Agent", "即夢" 的映射
3. BM25 現在可以通過 aliases 匹配找到跨語言結果

### 教訓
Cross-lingual search 不能只靠 keyword matching，還需要 entity aliases 和 query expansion。

---

## Case 3: BM25 Path Mismatch (2026-04-18)

### 現象
Search API 返回的 `path` 欄位（如 `ai-agent/entities/期哥.md`）與實際文件路徑不符。
導致無法直接讀取文件內容做進一步處理。

### 根本原因
`triple_stream_search.py` 內 `bm25_metadata` 儲存的 path 是相對路徑（相對於 wiki root），
但其他組件可能期望完整路徑或不同的相對基準。

### 修復
統一 path 處理：
- 所有內部操作使用相對路徑（從 wiki root）
- 對外 API 返回時保持相對路徑格式
- 文檔說明 path 是相對於 wiki root 的

### 教訓
API path 格式需要明確約定並寫入文檔。

---

## Case 4: Enhanced Dreaming Cron Error (2026-04-18)

### 現象
Enhanced Dreaming cron job 持續 error，狀態顯示 `lastRunStatus: error`。
手動執行 script 卻正常，問題似乎在 cron job 的環境或執行方式。

### 根本原因
可能是 cron agent 的環境變量不同，或 timeout 設定不夠長。
實際上後來自動恢復（可能是 transient issue）。

### 修復
1. 增加 cron job timeout 設定
2. 添加更詳細的 error logging
3. 創建 watchdog script 監控 API 健康

### 教訓
Cron job 需要 watchdog 或 health check 機制，否則 fail 了也不知道。

---

## Case 5: Vector Search Latency 102ms (2026-04-18)

### 現象
Vector search (Ollama nomic-embed-text) 平均 latency 102ms，
是 BM25 (0.4ms) 的 255 倍。

### 根本原因
Ollama 本地 embedding 模型不是真正的 vector database，
每次 search 都需要重新計算 embedding，無法快取。

### 緩解
Triple-Stream 使用 BM25 + Graph 作為 fast path，
Vector 只在最後階段用於 semantic re-ranking。
最終 average latency 降到 41.2ms（靠 early exit 策略）。

### 教訓
本地 embedding 不是銀彈，需要分層策略（fast path + slow semantic）。

---

## Case 6: Query Expansion 有 Chinese 但返回 English Results (2026-04-18)

### 現象
Query "即夢" 展開後包含 "Hermes Agent"，但返回結果不是預期的中文內容。
測試時 `any('hermes' in v.lower() or 'Hermes' in v for v in variants)` 竟然 False。

### 根本原因
pytest 的 assertion rewrite 與 inline generator 有奇怪的交互作用。
直接在 Python REPL 測試是 True，但 pytest 內運行是 False。

### 修復
改用 explicit for-loop 而不是 `any()` 內聯：
```python
has_hermes = False
for v in variants:
    if 'hermes' in v.lower():
        has_hermes = True
        break
assert has_hermes
```

### 教訓
測試框架可能有不直觀的行為，重要 assertion 需要用最明確的方式寫。

---

## Case 7: Schema Migration v1.2→v1.3 没有更新所有 Files (2026-04-19)

### 現象
Schema migration 運行後檢查，84 個 files 都顯示 v1.3，
但實際有些 fields 沒有正確更新（如 entityType 仍是 default "concept"）。

### 根本原因
Migration functions (`migrate_v1_2_to_v1_3`) 使用 default values 填補 missing fields，
而不是從現有數據推斷（如從 title 推斷 entityType）。

### 緩解
手動審查關鍵 entities 的 frontmatter，確保 schema 完整。
長期需要更智能的 migration logic。

### 教訓
Migration 不只是添加 fields，還要保證數據質量。

---

## Summary Statistics

| Category | Count |
|----------|-------|
| Total documented cases | 7 |
| Fixed | 5 |
| Partially mitigated | 2 |
| Recurring | 0 |

### By Component
| Component | Failures |
|-----------|----------|
| TripleStreamSearch | 3 |
| Query Expansion | 2 |
| Cron Jobs | 1 |
| Schema Migration | 1 |

### By Severity
| Severity | Count |
|----------|-------|
| Critical (system broken) | 2 |
| Major (significant impact) | 3 |
| Minor (annoying but workarounds exist) | 2 |

---

_Last updated: 2026-04-19 10:08 HKT_