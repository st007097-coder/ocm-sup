# Karpathy LLM KB Analysis
## Andrej Karpathy's LLM Knowledge Base Pattern - OCM Sup 對比

**Source:** [gist.github.com/karpathy/442a6bf555914893e9891c11519de94f](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
**Date:** 2026-04-29

---

## 🎯 Karpathy 的核心概念

> "Instead of just retrieving from raw documents at query time, the LLM **incrementally builds and maintains a persistent wiki** — a structured, interlinked collection of markdown files."

### Three Layers

```
Raw Sources → Wiki → Schema (AGENTS.md)
     ↓            ↓           ↓
  Immutable    LLM-owned    Instructions
```

| Layer | 描述 | OCM Sup |
|-------|------|---------|
| **Raw Sources** | Immutable source documents | Wiki entities/sources |
| **Wiki** | LLM-generated markdown files | ✅ Wiki (markdown) |
| **Schema** | Instructions for LLM | AGENTS.md, SOUL.md |

---

## 🔄 Core Workflows

### 1️⃣ Ingest（攝入新 sources）

```
Drop new source → LLM reads → Discuss → Update wiki
→ Update index → Update entities → Append to log
```

**Karpathy 建議：** 一次攝入一個 source，stay involved

### 2️⃣ Query（查詢）

```
User question → Search wiki → Read pages → Synthesize answer
→ File answer back as new page（可選）
```

**重點：** Answers can be filed back into wiki as new pages！

### 3️⃣ Lint（健康檢查）

```
Contradictions between pages?
Stale claims superseded by new sources?
Orphan pages with no inbound links?
Missing cross-references?
Data gaps?
```

---

## 📁 Special Files（OCM Sup 缺少的）

### index.md（內容導向）

Karpathy 建議：
```
## Entities
- [[古洞站]] - MTR railway station, Kwu Tung
- [[期哥]] - QS engineer, works on 1601

## Concepts
- [[OCM Sup]] - Memory management system
- [[Triple-Stream Search]] - BM25 + Vector + Graph

## Sources
- [[Project Notes]] - Daily work summaries
- [[Meeting Notes]] - Team meeting records
```

**好處：** 唔需要 vector search，簡單 index 就够用（~100 sources, hundreds of pages）

### log.md（時間導向）

Karpathy 建議：
```
## [2026-04-29] ingest | Article about Claude Memory
## [2026-04-28] query | How does triple-stream search work?
## [2026-04-28] lint | Found 3 stale claims
```

**好處：** Timeline of wiki evolution, `grep "^## \[" log.md | tail -5` gives last 5 entries

---

## 🛠️ Tools Karpathy 推薦

| Tool | 用途 | OCM Sup 對應 |
|------|------|-------------|
| **Obsidian** | IDE for wiki | ✅ Wiki folder |
| **qmd** | BM25/vector search CLI | ✅ Triple-Stream |
| **Marp** | Markdown slides | ❌ Not implemented |
| **Dataview** | Query frontmatter | ❌ Not implemented |
| **Graph View** | Visualize connections | ❌ Not implemented |
| **Web Clipper** | Save web articles | ❌ Not implemented |

---

## 🤔 OCM Sup vs Karpathy KB

### ✅ OCM Sup 已經有

| Feature | Karpathy | OCM Sup |
|---------|----------|---------|
| Wiki (markdown files) | ✅ | ✅ |
| Triple-Stream Search | ~index.md | ✅ |
| Schema (AGENTS.md) | ✅ | ✅ |
| Source tracking | ✅ | ✅ |
| Lint/health check | ✅ | ✅ |
| Archive backup | Weekly copy | ✅ (scripts/wiki_archive.py) |
| Import from LLMs | ✅ | ✅ (scripts/memory_import.py) |

### ❌ OCM Sup 缺少

| Feature | 建議 |
|---------|------|
| **index.md** | Add content index for manual navigation |
| **log.md** | Add append-only log of operations |
| **Better lint workflow** | More structured contradiction/staleness check |
| **Ingest workflow** | Structured process for new sources |
| **Answers → wiki** | File good answers back as pages |
| **Graph view** | Visualize entity relationships |
| **Dataview-like** | Query wiki by frontmatter |

---

## 💡 Key Takeaways for OCM Sup

### 1. Wiki as Compounding Artifact
> "The knowledge is compiled once and then kept current, not re-derived on every query."

**OCM Sup 已經做到：** Triple-Stream searchcompiled knowledge

### 2. LLM Does the Bookkeeping
> "LLMs don't get bored, don't forget to update a cross-reference, and can touch 15 files in one pass."

**OCM Sup 已經做到：** Proactive Discovery, contradiction detection

### 3. Human Directs, LLM Executes
> "The human's job is to curate sources, direct the analysis, ask good questions, and think about what it all means. The LLM's job is everything else."

**OCM Sup 已經做到：** 期哥 directs, 阿星 executes

### 4. File Answers Back
> "A comparison you asked for, an analysis, a connection you discovered — these are valuable and shouldn't disappear into chat history."

**可以加強：** When 阿星 generates useful analysis, file it back to wiki

---

## 📋 Recommended Next Steps

### High Priority
1. **Add log.md** - Append-only log of wiki operations
2. **Add index.md** - Content index for manual navigation
3. **Improve lint workflow** - More structured contradiction check

### Medium Priority
4. **Ingest workflow** - Document how to process new sources
5. **Better AGENTS.md** - More explicit schema for wiki structure

### Low Priority
6. **Graph view** - Visualize entity relationships (future)
7. **Dataview-like** - Frontmatter queries (future)

---

## 📝 Quote of the Day

> "The tedious part of maintaining a knowledge base is not the reading or the thinking — it's the bookkeeping. Updating cross-references, keeping summaries current, noting when new data contradicts old claims, maintaining consistency across dozens of pages. Humans abandon wikis because the maintenance burden grows faster than the value. LLMs don't get bored, don't forget to update a cross-reference, and can touch 15 files in one pass. The wiki stays maintained because the cost of maintenance is near zero."

— Andrej Karpathy

---

_Last updated: 2026-04-29_