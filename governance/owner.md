# OCM Sup Governance

## Owner

- **Primary Owner**: 阿星 (main agent)
- **Responsible for**: System maintenance, entity updates, quality assurance

## Review Cadence

- **Monthly review** (every 30 days)
- **Next review**: 2026-06-01

## Maturity

- **Tier**: Library（跨項目共享資產）
- **Stage**: Production
- **Status**: Active

## Lifecycle Rules

1. **Version bumps** require: new features, breaking changes, or major fixes
2. **Breaking changes** require: user confirmation (期哥)
3. **Entity updates** should be done when relationships change
4. **Script changes** should maintain backward compatibility

## Evolution Triggers

- Add new entity types as knowledge grows
- Improve search algorithm based on hit rate
- Expand Graph relationships quarterly
- Add new memory consolidation strategies

## Quality Metrics

- **Search Accuracy**: TOP1 rate ≥ 80%
- **Entity Coverage**: All major concepts have entity definition
- **Memory Reliability**: Session continuity maintained
- **Discovery Speed**: Consolidation Loop ≤ 5 sec

## Architecture

```
Triple-Stream Search
├── BM25 Channel (keyword)
├── Vector Channel (semantic)
└── Graph Channel (entity relations)
       ↓
   RRF Fusion
       ↓
   Results + Knowledge Graph Display
```

## Related Projects

| Project | Relationship |
|---------|--------------|
| wiki/ | Sync target |
| memory/ | Daily memory source |
| triple-stream-search skill | Search implementation |
| news-intelligence | News integration |

## Contact & Feedback

- For entity additions: 通知阿星
- For search issues: 通知阿星
- For system errors: 通知阿星