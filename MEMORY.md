---
title: MEMORY
type: note
permalink: openclaw-6b13693c60a5/memory
---

# MEMORY.md - 阿星嘅長期記憶

> ⚠️ **最後更新：2026-04-26**  
> 📁 Backup: `MEMORY.md.backup`（4月25日版本）

---

## ⚡ CURRENT CONTEXT (Last Update: 2026-04-26 00:59)

> 只放「呢 24 小時內」最重要嘅嘢，AI 长对话压缩时会保留呢區塊

### Active Goal
- 🔴 OCM Sup v2.3 AI 失憶問題研究 → ✅ 全部完成（2026-04-25）
- 🟡 準備將 MEMORY.md 升級（進行中）

### Blocking Issues
- ⚠️ 阿袁 Cron job timeout（daily-medical-tech-news）
- ⚠️ Gemini Billing 未搞掂（nano-banana-pro 生圖需要）
- ⚠️ Wiki 雙向同步：422 個空檔案失敗、944 個簡體需轉繁體

### Next Actions（24h內）
- [ ] 完成 MEMORY.md 升級（呢個緊係期哥要求嘅）
- [ ] 考慮更新 Windows Docker Gateway（2026.4.24 pre-release）
- [ ] 23:55 Journal → Obsidian（自動 cron）

### Recent Wins（24h內）
- ✅ OCM Sup v2.3 完成（7 tasks，275x faster Proactive Discovery）
- ✅ Obsidian Journal sync 修復（dynamic script）
- ✅ 補完 11 個日期嘅 Journal（14-22, 24-25）
- ✅ OpenClaw container 更新至 2026.4.23
- ✅ session-memory hook 生效（你重啟後已啟動）

---

## 🤖 AGENT GUIDELINES

> 每次 session start load MEMORY.md 時自動執行

### Path Mapping（必須遵守）
| 實際路徑 | → | 用途 |
|---------|---|------|
| `/root/.openclaw/workspace/wiki` | → | Wiki 根目錄 |
| `wiki/systems/ocm-sup/` | → | OCM Sup 系統文件 |
| `wiki/knowledge/ai-agent/entities/` | → | Entity 定義 |
| `memory/` | → | Daily memory logs |
| `OCM-Sup/` | → | OCM Sup GitHub repo |
| `Journal/` | → | Journal entries（sync to Obsidian） |

### Obsidian Mapping（重要）
當用 Obsidian skill 或 API 時：
- `host.docker.internal:27123` → Windows Obsidian REST API
- Vault 名：`OpenClaw`
- Token：`e61816d4805e30b90638972cd45b8c43b4beebcaf5b168f84cbc0818fe818f1d`
- 自動 mapping：`wiki/` → `Obsidian vault/`

### Safety Rules（🔴 最高優先）
1. **刪除任何檔案或目錄** — 必須向期哥確認先可以執行
2. **外部動作**（email、post、public）— 必須問過期哥先
3. **恢復刪除** — 用 `trash` 而非 `rm`，除非期哥明確確認

### Session Behavior
- Session 開始時自動執行 `session_start_memory_load.py`
- Session 結束時自動執行 `session_end_summary.py`
- Proactive Discovery 每早 08:30 自動運行（Consolidation Loop）

---

## 👤 USER PREFERENCE（期哥）

> 每次 load MEMORY.md 時記得跟呢啲規則

| 項目 | 設定 |
|------|------|
| **語言** | 廣東話（白話文），唔使用簡體中文 |
| **風格** | 簡單易懂、拒絕術語、適量 Emoji |
| **抬頭** | 期哥 / Jacky（@jacky_love_summy） |
| **時區** | Asia/Hong_Kong (UTC+8) |
| **工作時間** | 08:30 - 18:00 HKT |

### 溝通偏好
- 直接，但有禮貌
- 如果唔知，直接話「我唔知」而唔係扮明
- 試完先問，唔好 Lynne 住做
- 一句話搞掂就唔好講三句，但複雜嘢要拆開解釋
- 可以反對、可以話「伏」，但要解釋原因

### 期哥背景
- 住香港
- 正職：QS（工料測量師）
- 工作項目：1601 東鐵線古洞站-BS（MTR 鐵路工程，合約 HKD 3.925 億）
- Telegram：積奇（@jacky_love_summy）

---

## 期哥

- 名：期哥
- Telegram：積奇（@jacky_love_summy）
- 住香港
- 正職：QS（工料測量師）
- 工作項目：1601 東鐵線古洞站-BS（MTR 鐵路工程，合約 HKD 3.925 億）
- 時區：Asia/Hong_Kong (UTC+8)

---

## 規則（🔴 最重要）

1. **刪除任何檔案或目錄 — 必須向期哥確認先可以執行** 🚨
2. **每次安裝新 skill 前，必須先用 skill-vetter 審查安全性** 🔒
3. **記憶分級：**
   - 🔴 最重要：決定+規則 → MEMORY.md + Wiki entities
   - 🟡 次重要：人+項目+金錢+文件 → Wiki entities
   - 🟢 一般：日常瑣事 → Daily Memory

---

## 連接狀態

| 服務 | 狀態 | 備註 |
|------|------|------|
| Obsidian | ✅ | `host.docker.internal:27123`，Vault 名 OpenClaw |
| Notion | ✅ | 12 個 databases 全部可讀 |
| GitHub | ✅ | `st007097-coder` |
| Tavily Web Search | ✅ | 已啟用 |
| Camofox Browser | ✅ | Anti-detection browser |
| 花叔技能 (huashu-design) | ✅ | 已安裝，已用於 OCM-Sup 視頻 |

---

## Cron Jobs（2026-04-26 更新）

> ⚠️ 所有 cron jobs 喺 `~/.openclaw/cron/jobs.json`

### 🤖 阿星 (main) — 8 個 jobs

| Job | Schedule | Status | Next Action |
|-----|----------|--------|-------------|
| 每日總結 | 07:00 HKT | ✅ | - |
| Security Audit | 07:15 HKT | ✅ | - |
| daily-gdrive-backup | 07:30 HKT | ✅ | - |
| Wiki Retention Scan | 08:00 HKT | ✅ | - |
| AI News Digest | 08:00 HKT | ✅ | - |
| Wiki Lint | 10:00 HKT | ✅ | - |
| Journal → Obsidian v3 | 23:55 HKT | ✅ | dynamic sync script |
| OCM-Sup Consolidation Loop | 08:30 HKT | ✅ | ~2 sec 完成 |

### 🤖 Mr. Black — 3 個 jobs

| Job | Schedule | Status | Next Action |
|-----|----------|--------|-------------|
| Enhanced Dreaming | 07:45 HKT | ✅ | - |
| OCM-Sup Consolidation Loop | 08:30 HKT | ✅ | 已整合入 main |
| Memory Dreaming Promotion | 04:00 HKT | ⏭️ SKIPPED | 需要 re-enable |

### 🤖 阿袁 (yuan) — 1 個 jobs

| Job | Schedule | Status | Next Action |
|-----|----------|--------|-------------|
| daily-medical-tech-news | 09:00 HKT | ⚠️ timeout | **需要拆分 task** |

---

## Wiki 結構（重要）

**日後所有系統路徑統一指向：** `/root/.openclaw/workspace/wiki`

| Wiki 路徑 | → | Obsidian 路徑 |
|-----------|---|---------------|
| `originals/期哥/` | → | `期哥/` |
| `knowledge/ai-agent/entities/` | → | `Hermes-Wiki/entities/` |
| `knowledge/ai-agent/concepts/` | → | `Hermes-Wiki/concepts/` |
| `AI/Hermes/` | → | `Hermes-Wiki/` |
| `AI/OpenClaw/` | → | `OpenClaw-Wiki/` |
| `systems/ocm-sup/` | → | `OCM-Sup/` |

---

## OCM Sup 系統（v2.3）📈

**位置：** `/root/.openclaw/workspace/OCM-Sup/`
**GitHub:** https://github.com/st007097-coder/ocm-sup
**Badge:** v2.3 (Proactive Memory System)

### 7-Dir 框架 ✅ 全部完成

| Phase | 名稱 | 功能 | 狀態 |
|-------|------|------|------|
| 7-Dir 3 | Triple-Stream Search | BM25 + Vector + Graph 搜索 | ✅ |
| 7-Dir 4 | KG Auto-Expander | 自動發現 + 加入新 entities | ✅ |
| 7-Dir 5 | Smart Recall Hook | Relevant topics 觸發 | ✅ |
| 7-Dir 6 | Proactive Discovery | 主動發現新舊知識連接 | ✅ |

### v2.3 新功能（2026-04-25）

| 功能 | 描述 | 效果 |
|------|------|------|
| Session Start Memory Load | 3-layer context (must_keep + session_summary + 5day memory) | 減少失憶 |
| Pre-compression Checkpoint | 自動保存 60 facts 去 must_keep_facts.md | 壓縮保护 |
| Proactive Discovery Super Quick | 直接 scan wiki，繞過 LLM query | **275x faster** (~1 sec) |
| Session End Summary | 自動生成 structured summary | 減少失憶 |
| Session-Memory Hook | command:new/reset 時自動保存 | ✅ 已啟動 |
| Consolidation Loop | ~2 sec 完成全部 Proactive 工作 | **140x faster** |

### P0/P1 Benchmark ✅ 全部完成

| Phase | 內容 | Result |
|-------|------|--------|
| P0.1 | Expand Benchmark | 27 queries |
| P0.4 | Substring Matching | **81.5% TOP1** |
| P0.5 | Add Missing Entities | **100% TOP1** |
| P1.1 | Lazy Vector Loading | Init: 277s → **~5s** |
| P1.2 | RRF 權重調整 | BM25=1.5, Vector=1.0, Graph=0.8 |
| P1.3 | Cross-lingual 增強 | 中英對照 synonyms |
| P2 | Intent Classification | 意圖分類適應性 RRF |

### Scripts ✅

| Script | 用途 |
|--------|------|
| `triple_stream_search.py` | 核心搜索 |
| `proactive_discovery_super_quick.py` | ~1 sec 主動發現 |
| `session_start_memory_load.py` | Session 開始時 load context |
| `session_end_summary.py` | Session 結束時生成 summary |
| `pre_compression_checkpoint.py` | 壓縮前保存 facts |
| `obsidian-journal-sync-dynamic.py` | 動態 sync Journal → Obsidian |

---

## 待解決 ⚠️（需要繼續跟進）

### 🔴 高優先

| 項目 | 問題 | 負責 | Next Action |
|------|------|------|-------------|
| **Wiki 雙向同步** | 422 個空檔案失敗、944 個簡體需轉繁體 | 阿星 | 寫 script 檢查空檔案 |
| **Memory Dreaming Promotion** | SKIPPED (disabled) | 阿星 | re-enable cron |

### 🟡 中優先

| 項目 | 問題 | 負責 | Next Action | 依賴 |
|------|------|------|-------------|------|
| 阿袁 timeout | daily-medical-tech-news cron timeout | 阿袁 | **拆分 task** 避免 timeout | - |
| Gemini billing | nano-banana-pro 生圖需要 | 期哥 | 聯絡 Google 開通 | - |
| AI 失憶問題 | v2.3 已完成主動機制，但需持續觀察 | 阿星 | 觀察效果 | - |

### 🟢 低優先

| 項目 | 問題 | 負責 | Next Action |
|------|------|------|-------------|
| GPU 加速 whisper | Docker Desktop 環境限制 | - | 長期暫緩 |
| Windows Gateway 更新 | 2026.4.24 pre-release 未穩定 | 期哥 | 等 stable release |

---

## AI 失憶問題研究 📋

> 📁 詳見：`/root/.openclaw/workspace/wiki/systems/ocm-sup/AI-Forgetfulness-Research.md`

**問題：** 雖然 OCM Sup 系統完整，但 AI 依然會忘記做過嘅嘢

**解決方案（v2.3 完成）：**
1. ✅ Session 開始時自動 Memory Load（P0）
2. ✅ Pre-compression Checkpoint 保存重要 facts
3. ✅ Active Memory Plugin 強化
4. ✅ Proactive Discovery 自動化
5. ✅ session-memory hook

**效果：** 
- Must Keep Facts: 60 facts saved
- Proactive Discovery: ~275 sec → ~1 sec (275x faster)
- Total Loop: ~280 sec → ~2 sec (140x faster)

---

## 古洞站項目摘要

- 合約：HKD 3.925 億
- 上家 VO：87 項，HKD 1.1 億
- 下家 VO：100+ 項，HKD 3,056 萬
- 分判商：13 間（最大：承達 Sundart HKD 5,300 萬）
- 供應商：41 間
- 工期：2023-10-13 → 2027-03-31

---

## Skills（已安裝）

| Skill | 用途 | 狀態 |
|-------|------|------|
| huashu-design | HTML 原生設計（信息圖/原型/動畫）| ✅ 已用 |
| nano-banana-pro | AI 生圖 | ⏳ 等 Gemini billing |
| obsidian | Wiki 管理 | ✅ |
| notion | Notion 操作 | ✅ |
| triple-stream-search | 搜索增強 | ✅ |
| weather | 天氣查詢 | ✅ |
| healthcheck | 主機安全 | ✅ |
| node-connect | Node 連接診斷 | ✅ |
| skill-creator | Skill 創作 | ✅ |

---

## Plugins

- **memory-core** — 內建 active memory（dreaming、promotion、semantic search）
- **Active Memory** — 回覆前 context 注入（`queryMode: full`）
- **lossless-claw** — 對話壓縮存儲
- **camofox-browser** — Anti-detection browser
- **session-memory** — command:new/reset 時自動保存 raw messages

---

## 已刪除 Skills

- ❌ felo-superagent（2026-03-31）
- ❌ felo-youtube-subtitling（2026-03-31）
- ❌ MoltGuard（安全問題）

---

## ✅ 已完成（歷史記錄）

> 格式：**日期 | 項目 | 狀態 + Root Cause（如有）**

| 日期 | 項目 | 狀態 | Root Cause / 解決方法 |
|------|------|------|----------------------|
| 2026-04-25 | Cron Jobs 重整 | ✅ | 7 main + 3 black + 1 yuan |
| 2026-04-25 | OCM Sup v2.3 AI 失憶研究 | ✅ | 所有 7 tasks 完成，275x faster |
| 2026-04-25 | Obsidian Journal Sync 修復 | ✅ | hardcoded date → dynamic script |
| 2026-04-25 | OpenClaw 更新 | ✅ | 2026.4.22 → 2026.4.23 |
| 2026-04-25 | session-memory hook | ✅ | 你重啟後生效 |
| 2026-04-25 | MEMORY.md 升級 | ✅ | 加入 Current Context、AGENT GUIDELINES |
| 2026-04-22 | OCM Sup P0.1-P2 全部完成 | ✅ | 100% TOP1 |
| 2026-04-22 | Bug: 期哥 TOP1 變醫療文檔 | ✅ 已修 | Root Cause: RRF 權重偏差，已調低 Vector 權重 |
| 2026-04-22 | Bug: 搜 "OpenClaw" 變相關文章 | ✅ 已修 | Root Cause: BM25 匹配邏輯問題 |
| 2026-04-22 | elephant-alpha vs MiniMax-M2.7 | elephant-alpha 勝 | - |
| 2026-04-21 | Wiki Taxonomy v2 | ✅ | 41 dirs → 6 dirs |
| 2026-04-20 | Wiki Tag + Weblink 改進 | ✅ | 1986 個檔案加 tags |
| 2026-04-20 | Wiki Wikilinks Script | ❌ 放棄 | 92% corruption，修復成本太高 |
| 2026-04-19 | Wiki ↔ Obsidian 雙向同步 | ⚠️ 進行中 | 422 空檔案失敗（已知） |
| 2026-04-19 | Wiki 雙 Wiki 合併 | ✅ | 1845 個檔案 |
| 2026-04-19 | Wiki 簡體→繁體轉換 | ✅ | 944 個檔案 |
| 2026-04-19 | OCM Sup Triple-Stream Search | ✅ | 31.2% → 90.6% |
| 2026-04-19 | Schema Migration + Time Decay | ✅ | - |
| 2026-04-18 | OCM Sup v2.0 發布 | ✅ | 7-Dir 全部完成 |
| 2026-04-18 | Triple-Stream Enhanced Search | ✅ | BM25 + Vector + Graph |
| 2026-04-18 | huashu-design skill | ✅ | 已安裝 |
| 2026-04-18 | Entity Aliases 注入 | ✅ | 20 個 entity files |
| 2026-04-17 | OCM Sup Phase Z Evolution | ✅ | 詳見 OCM-Sup/CHANGELOG |
| 2026-04-15 | Lossless-Claw | ✅ | 修復成功 |
| 2026-04-15 | Obsidian Journal Sync | ✅ | 恢復正常 |
| 2026-04-14 | Active Memory Plugin | ✅ | 安裝完成 |
| 2026-04-11 | Memory System Audit | ✅ | 清理完成 |

---

## 📌 下一步行動（2026-04-26）

### 即時（今天）
- [ ] 測試 MEMORY.md v2 效果（你呢個評價就係測試）
- [ ] 觀察 OCM Sup v2.3 AI 失憶問題係咪改善

### 本週
- [ ] 修復 Wiki 同步（寫 script 檢查 422 個空檔案）
- [ ] 解決阿袁 timeout（拆分 task）
- [ ] re-enable Memory Dreaming Promotion cron

### 長期
- [ ] Gemini billing 開通（nano-banana-pro 生圖）
- [ ] Windows Gateway 更新（等 2026.4.24 stable）
- [ ] 考慮加入 PDF/Meeting notes input pipeline

---

_最後更新：2026-04-26 00:59 HKT_
_版本：v2.0 → v2.1 (MEMORY.md 升級)_