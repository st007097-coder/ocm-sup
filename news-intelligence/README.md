# News Intelligence System
## OCM Sup 之外第2個 Project — 智能資訊收集、分析、去重、總結

**Version:** 0.1 (Draft)
**Date:** 2026-04-29
**Author:** 阿星
**Status:** 🟡 In Progress

---

## 🎯 目標

大量收集各方資訊 → 我分析去重總結 → 重要資訊比期哥

---

## 📁 專案結構

```
news-intelligence/
├── sources/              # 來源配置
│   ├── rss_feeds.yaml    # RSS feeds 配置
│   └── keywords.yaml     # 關鍵詞配置（用於評分）
├── cache/                # 緩存
│   ├── rolling_events.json   # Rolling 7-day 去重數據庫
│   └── rss_cache/            # RSS 緩存
├── output/               # 輸出
│   └── daily/            # 每日摘要
├── scripts/
│   ├── rss_fetcher.py       # Phase 1: RSS 收集
│   ├── deduplicator.py      # Phase 2: 去重機制
│   ├── scorer.py            # Phase 3: 興趣評分
│   └── daily_digest.py      # Phase 4: 每日總結生成
└── README.md
```

---

## 📋 Phase 計劃

| Phase | 內容 | 狀態 |
|-------|------|------|
| **Phase 1** | RSS Fetcher（量子位、三花AI） | 🟡 In Progress |
| **Phase 2** | Deduplicator（Rolling 7-day DB） | ⬜ Pending |
| **Phase 3** | Interest Scorer（Keyword matching） | ⬜ Pending |
| **Phase 4** | Daily Digest Generator | ⬜ Pending |

---

## 🔧 Phase 1: RSS Fetcher

### 目標
從多個 RSS 來源收集 AI/科技新聞

### 來源（預設）
- 量子位（AI/科技）
- 三花 AI 快訊
- 其他（可配置）

### 輸出
- 原始新聞列表（JSON）
- 緩存以便去重用

---

## 🔧 Phase 2: Deduplicator

### 目標
避免同一件事重複出現

### 機制
- Rolling 7-day Events DB
- 新聞進入時 check 數據庫
- 有就標記為"舊聞"降權
- 冇就加入數據庫
- 自動清理第8日

---

## 🔧 Phase 3: Interest Scorer

### 目標
根據興趣評分新聞

### 評分標準
- AI/模型重大發布：+3分
- AI Agent/框架：+2分
- 實用工具/產品：+2分
- 行業趨勢：+1分
- 其他：+0分

### 輸出分級
- 🔥 8-10分：頭條
- ⭐ 5-7分：重要
- 📌 3-4分：值得關注
- 📝 0-2分：一般

---

## 🔧 Phase 4: Daily Digest Generator

### 目標
生成每日摘要

### 輸出格式
1. **詳細 MD**（寫入 wiki/AI-News/daily/YYYY-MM-DD.md）
2. **簡報**（直接 message 期哥）

### 內容結構
- 今日行業大事
- 今日對期哥有用
- 值得關注
- 今日關鍵信號

---

_Last updated: 2026-04-29_
