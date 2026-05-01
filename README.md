# OCM-Sup

> 知識管理系統 (Knowledge Management System)

## 📁 目錄結構

```
OCM-Sup/
├── archive/              # 封存測試品
├── scripts/              # 腳本工具
├── wiki/                 # Wiki 同步
├── entities/             # 實體定義
├── concepts/            # 概念定義
└── [其他子目錄]
```

## 🎯 主要功能

- **Triple-Stream Search**: BM25 + Vector + Graph 三流搜索
- **Knowledge Graph**: 實體關係管理
- **Proactive Discovery**: 自動發現新舊知識連接
- **Entity Auto-Expander**: 自動擴展實體關係

## 📊 系統版本

- **Version**: v2.5.1 (2026-05-01)
- **Status**: Active Development + Optimized

## 🆕 v2.5.1 Update (2026-05-01)

- **Added SKILL.md** with triggers, workflow, checkpoints, boundary conditions
- **Added manifest.json** for governance
- **Added evals/** with trigger cases and semantic config
- **Added governance/** with owner and review cadence
- **Added tests/** with 8 automated tests (all passing)
- **Optimized** using darwin-skill + yao-meta-skill methods

## 🔗 相關項目

- `wiki/` — Wiki 同步目標
- `memory/` — 每日記憶
- `../skills/triple-stream-search/` — 搜索 skill

---

_Last updated: 2026-05-01_