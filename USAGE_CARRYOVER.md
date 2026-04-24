# OCM Sup Continuity Layer — 實際使用指南

## 簡介

OCM Sup Continuity Layer 為 OpenClaw 添加了 `/new carryover` 和結構化 follow-up 功能。

主要功能：
- **/new Carryover** — 新對話接回真正 pending 嘅 topic
- **消息分類** — 自動識別 casual/staged/tracked 消息
- **Follow-up Hooks** — 自動提醒你之前提到嘅事項
- **前台保護** — 防止內部邏輯泄露到前台

---

## 快速開始

### 1. 運行 Continuity API

```bash
cd /root/.openclaw/workspace/OCM-Sup
/root/.openclaw/venv/bin/python3 scripts/continuity_api.py --port 5001
```

API 將在 `http://localhost:5001` 運行。

### 2. 測試 CLI

```bash
# 查看狀態
/root/.openclaw/venv/bin/python3 scripts/continuity/smart_recall_carryover.py --status

# 檢查到期 hooks
/root/.openclaw/venv/bin/python3 scripts/continuity/smart_recall_carryover.py --check-due
```

---

## 日常使用場景

### 場景 1: Parking a Topic

**你說：** 「幫我記住我哋研究緊OCM Sup融合方案」

**系統自動：**
1. 分類為 `tracked_followup` + `delegated_task`
2. 創建 incident
3. 設置為 pending topic
4. 寫入 daily memory trace

### 場景 2: /new Session

**你說：** 「早晨」（新對話）

**系統自動：**
1. 識別為 `/new` session
2. 檢索 pending topic
3. 生成 continuity prompt：「你之前交代咗個任務關於『OCM Sup融合方案』，你想繼續傾嗎？」

### 場景 3: Follow-up Reminder

**當 cron job 運行時：**
1. 檢查所有 active hooks
2. 應用 sleep/rest suppress
3. 渲染 follow-up message
4. 自動 dispatch（在允許的時間）

---

## API 使用示例

### 測試消息分類

```bash
curl -X POST http://localhost:5001/continuity/classify \
  -H "Content-Type: application/json" \
  -d '{"text": "幫我記住我哋研究緊融合方案"}'
```

返回：
```json
{
  "success": true,
  "data": {
    "classification": {
      "routing": "tracked_followup",
      "event_type": "delegated_task",
      "confidence": 0.9
    }
  }
}
```

### 獲取 Carryover Context

```bash
curl "http://localhost:5001/continuity/carryover?text=早晨&is_new_session=true"
```

返回：
```json
{
  "success": true,
  "data": {
    "type": "new_session_carryover",
    "continuity_prompt": "你之前交代咗個任務關於「融合方案」，你想繼續傾嗎？",
    "is_low_info_greeting": true
  }
}
```

### 檢查到期 Hooks

```bash
curl http://localhost:5001/continuity/hooks/due
```

返回：
```json
{
  "success": true,
  "data": {
    "count": 1,
    "hooks": [{
      "id": "hook_abc123",
      "entity_name": "OCM Sup 研究",
      "rendered_message": "想提醒你之前交代嘅任務..."
    }]
  }
}
```

---

## CLI 命令

### 查看狀態

```bash
/root/.openclaw/venv/bin/python3 scripts/continuity/smart_recall_carryover.py --status
```

### 檢查到期 Hooks

```bash
/root/.openclaw/venv/bin/python3 scripts/continuity/smart_recall_carryover.py --check-due
```

### 關閉所有 Pending Hooks（測試用）

```bash
/root/.openclaw/venv/bin/python3 scripts/continuity/smart_recall_carryover.py --close-all
```

### 清理舊 Traces

```bash
/root/.openclaw/venv/bin/python3 scripts/continuity/smart_recall_carryover.py --cleanup 30
```

---

## 觸發關鍵詞

### Staged Memory (Park for Later)
- 「幫我記住...」
- 「遲啲再傾...」
- 「記住呢個...」

### Tracked Followup (Delegate Task)
- 「麻煩你幫我跟進...」
- 「麻煩你...」
- 「跟進...」

### Watchful State (Monitor)
- 「感覺...」
- 「身體有啲...」

### Sensitive Event (Confidential)
- 「保密...」
- 「私人...」

### Casual Chat (No Tracking)
- 「你好嗎？」
- 「早晨」
- 普通問答

---

## 設置

編輯 `/root/.openclaw/workspace/OCM-Sup/scripts/continuity/settings.json`：

```json
{
  "routine_schedule": {
    "timezone": "Asia/Hong_Kong",
    "sleep_time": "00:00",
    "wake_time": "08:30"
  },
  "carryover": {
    "enabled": true,
    "max_turns": 5
  },
  "proactive_chat": {
    "enabled": false
  }
}
```

---

## 文件結構

```
OCM-Sup/scripts/continuity/
├── __init__.py                     # Module init
├── state_router.py                 # 消息分類
├── carryover.py                    # Carryover 管理
├── continuity_state.py             # 整合 facade
├── hook_lifecycle.py               # Hook 生命周期
├── frontstage_guard.py             # 前台保護
├── ocm_graph_integration.py       # Wiki 實體整合
├── daily_memory_trace.py           # 記憶 traces
├── smart_recall_carryover.py       # CLI tool
├── continuity_api.py               # HTTP API
├── settings.json                  # 設置
├── staging.json                   # 暫存狀態
├── incidents.json                 # 追蹤事件
├── hooks.json                    # Hook 狀態
└── carryover.json               # Carryover 緩衝
```

---

## 故障排除

### API 無法啟動

確保 port 未被佔用：
```bash
lsof -i :5001
```

### Hooks 未到期

檢查時間狀態：
```bash
/root/.openclaw/venv/bin/python3 scripts/continuity/smart_recall_carryover.py --status
```

確保 `is_proactive_allowed: true` 和 `phase: active_day`。

### Carryover 未生效

檢查 pending topic 是否設置：
```bash
curl http://localhost:5001/continuity/pending
```

---

## 下一步

1. **整合 Cron Job** — 將 `--check-due` 加入定期 cron
2. **Telegram Bot** — 通過 bot 發送 follow-ups
3. **Graph Visualization** — 可視化 continuity 狀態
4. **實際測試** — 在真實對話中測試

---

_最後更新：2026-04-24_
