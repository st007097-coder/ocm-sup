# News Intelligence System
## OCM Sup 之外第2個 Project — 智能資訊收集、分析、去重、總結

**Version:** 1.0
**Date:** 2026-04-29
**Author:** 阿星
**Status:** ✅ **Complete**

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
│   ├── unified_combined.json # Unified pipeline 結果
│   └── scored_items.json    # 評分後的新聞
├── output/               # 輸出
│   ├── daily/            # 每日摘要 MD
│   └── brief_*.txt       # Telegram 簡報
├── scripts/
│   ├── rss_fetcher.py       # Phase 1: RSS 收集（5 feeds）
│   ├── deduplicator.py       # Phase 2: Rolling 7-day 去重
│   ├── scorer.py             # Phase 3: 興趣評分
│   ├── daily_digest.py       # Phase 4: 每日總結生成
│   └── unified_collector.py # Unified Pipeline (Tavily + RSS)
└── README.md
```

---

## 📋 Phase 計劃

| Phase | 內容 | 狀態 |
|-------|------|------|
| **Phase 1** | RSS Fetcher（5 feeds） | ✅ **Complete** |
| **Phase 2** | Deduplicator（Rolling 7-day DB） | ✅ **Complete** |
| **Phase 3** | Interest Scorer（Keyword matching） | ✅ **Complete** |
| **Phase 4** | Daily Digest Generator | ✅ **Complete** |
| **Unified** | Tavily Search + RSS Feeds | ✅ **Complete** |

---

## 🔧 Phase 1: RSS Fetcher

從多個 RSS 來源收集 AI/科技新聞

### 來源（5 feeds）
- HackerNews AI（20 items）
- MIT Tech Review（10 items）
- TechCrunch AI（19 items）
- The Verge AI（10 items）
- Ars Technica（20 items）

### 輸出
- 原始新聞列表（JSON）
- 緩存以便去重用

---

## 🔧 Phase 2: Deduplicator

避免同一件事重複出現

### 機制
- Rolling 7-day Events DB
- 新聞進入時 check 數據庫
- 有就標記為"舊聞"降權
- 冇就加入數據庫
- 自動清理第8日

---

## 🔧 Phase 3: Interest Scorer

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

## 🔄 Unified Pipeline

結合所有 Sources：

1. **RSS Feeds** → 79 items
2. **Tavily Search API** → 24 items（3 queries）
3. **Combined + Deduplicated** → 103 items
4. **7-day Freshness Filter** → 73 fresh items
5. **Scoring** → 🔥13 頭條 + ⭐15 重要 + 📌17 值得關注

### Sources
| Source | Type | Items |
|--------|------|-------|
| HackerNews AI | RSS | 20 |
| MIT Tech Review | RSS | 10 |
| TechCrunch AI | RSS | 19 |
| The Verge AI | RSS | 10 |
| Ars Technica | RSS | 20 |
| OpenAI/GPT News | Tavily | 8 |
| Claude/Anthropic News | Tavily | 8 |
| AI Agent News | Tavily | 8 |

### 7日 Freshness Filter
- 只顯示 7日內新鮮新聞
- 移除舊聞避免混淆

---

## ⚙️ 使用方法

```bash
# 1. 收集 RSS feeds
python3 scripts/rss_fetcher.py

# 2. 運行 Unified Pipeline（Tavily + RSS）
python3 scripts/unified_collector.py

# 3. 評分新聞
python3 scripts/scorer.py

# 4. 生成每日摘要
python3 scripts/daily_digest.py
```

---

## 📊 測試結果（2026-04-29）

| 指標 | 數值 |
|------|------|
| **總 items** | 103 |
| **Fresh items（7日）** | 73 |
| **🔥 Headlines** | 13 |
| **⭐ Important** | 15 |
| **📌 Notable** | 17 |
| **📝 General** | 28 |

**Headlines:**
1. AI Agent Breakthroughs - LinkedIn
2. Anthropic's new Claude - Tom's Guide
3. Claude Opus 4.5 vs Gemini 3

---

_Last updated: 2026-04-29_
