# WebSocket Architecture

> Internal doc for dev & debugging. Last updated: 2026-03-14.

---

## Overview

The app uses a single shared WebSocket connection for real-time communication between backend and all frontend pages. All events are broadcast to ALL connected clients.

```
Backend (Python)                    Frontend (JS)
──────────────                    ─────────────
WebSocketManager                    WSClient
  ├─ broadcast(event, data)         ├─ connect()     → ws://host/ws
  ├─ broadcast_sync(event, data)    ├─ on(event, fn) → register listener
  └─ connections: Set[WebSocket]    └─ listeners: {event: [fn...]}
```

---

## Backend: WebSocket Manager

**File:** `backend/websocket.py`

```python
ws_manager = WebSocketManager()  # Global singleton
```

| Method | Thread-safe | Usage |
|--------|-------------|-------|
| `broadcast(event, data)` | No (async) | From async code |
| `broadcast_sync(event, data)` | Yes | From sync threads (scan, macro, etc.) |

**How it's wired:** All backend modules receive `ws_callback=ws_manager.broadcast_sync` when invoked from API endpoints.

---

## Frontend: WSClient

**File:** `frontend/js/api.js` (class `WSClient`, global `wsClient`)

- Auto-reconnects on disconnect (2s delay)
- Ping interval: 15s to keep connection alive
- Message format: `{"event": "event_name", "data": {...}}`
- Supports wildcard listener: `wsClient.on('*', (event, data) => ...)`

---

## All WebSocket Events

### Bot/Workflow Events

| Event | Emitter | Data Schema | Consumers |
|-------|---------|-------------|-----------|
| `bot_queue_update` | `bot_orchestrator.broadcast_state()` | See below | `workflow.js`, `task.js` |
| `workflow_log` | `bot_orchestrator._emit_timeline()` | `{message, log_type, emu_idx, acc_id}` | `workflow.js`, `app.js` |
| `workflow_progress` | `bot_orchestrator` | `{current, total}` | `workflow.js` |
| `workflow_status` | `bot_orchestrator` | `{status: RUNNING\|SUCCESS\|ERROR}` | `workflow.js`, `app.js` |
| `timeline_event` | `bot_orchestrator._emit_timeline()` | `{ts, icon, text, emu_idx, acc_id, group_id}` | `workflow.js` |
| `activity_started` | `bot_orchestrator` | `{activity, account_id, group_id, ts}` | `workflow.js` |
| `activity_completed` | `bot_orchestrator` | `{activity, account_id, group_id, ts, duration_ms}` | `workflow.js` |
| `activity_failed` | `bot_orchestrator` | `{activity, account_id, group_id, ts, error}` | `workflow.js` |

### Task Events

| Event | Emitter | Data Schema | Consumers |
|-------|---------|-------------|-----------|
| `task_started` | `task_queue` | `{task_id, task_type, serial}` | `app.js` |
| `task_progress` | `task_queue` | `{task_id, progress, message}` | `app.js` |
| `task_completed` | `task_queue` | `{task_id, result}` | `app.js` |
| `task_failed` | `task_queue` | `{task_id, error}` | `app.js` |

### Scan Events

| Event | Emitter | Data Schema | Consumers |
|-------|---------|-------------|-----------|
| `scan_progress` | `full_scan._scan_worker()` | `{emulator_index, step, total_steps, message}` | `app.js` |
| `scan_completed` | `full_scan._scan_worker()` | `{emulator_index, result}` | `app.js` |
| `scan_failed` | `full_scan._scan_worker()` | `{emulator_index, error}` | `app.js` |

### Macro Events

| Event | Emitter | Data Schema | Consumers |
|-------|---------|-------------|-----------|
| `macro_progress` | `macro_replay._replay_worker()` | `{emu_index, progress, message}` | `app.js` |
| `macro_completed` | `macro_replay._replay_worker()` | `{emu_index, result}` | `app.js` |
| `macro_failed` | `macro_replay._replay_worker()` | `{emu_index, error}` | `app.js` |

---

## `bot_queue_update` Data Schema (Critical Event)

This is the **most important event** — drives the Monitor tab, Activity tab, and KPI panel.

```json
{
  "group_id": 1,
  "is_running": true,
  "stop_requested": false,
  "cycle": 2,
  "current_idx": 0,
  "total_accounts": 9,
  "current_activity": "Train Troops",
  "activity_statuses": {
    "Gather Resource Center": "done",
    "Catch Pet": "done",
    "Train Troops": "running",
    "Claim Resources": "pending"
  },
  "accounts": [
    {
      "id": 12,
      "lord_name": "dragonball \"Goten",
      "emu_index": 1,
      "game_id": "12",
      "status": "running",
      "last_run_time": 1710400000.0,
      "cooldown_remaining_sec": 0
    }
  ],
  "activity_metrics": { ... },
  "cooldown_config": {
    "cooldown_min": 30,
    "swap_wait_threshold_min": 5,
    "skip_cooldown": false
  },
  "smart_wait_active": null
}
```

### Account Status Values
`pending` | `running` | `done` | `error` | `skipped` | `cooldown`

### Activity Status Values
`pending` | `running` | `done` | `error` | `skipped`

---

## Listener Registration Points

| File | Method | Events Handled |
|------|--------|----------------|
| `app.js` | `wireUpWebSocket()` | `task_*`, `scan_*`, `workflow_log`, `workflow_status` |
| `workflow.js` | `setupWebSocket()` | `workflow_*`, `bot_queue_update`, `timeline_event`, `activity_*` |
| `task.js` | `_initWsHandler()` | `bot_queue_update` |

---

## Debugging Tips

### Check if WS is connected
```js
// Browser console
wsClient.ws.readyState  // 0=CONNECTING, 1=OPEN, 2=CLOSING, 3=CLOSED
```

### Monitor all events
```js
wsClient.on('*', (event, data) => console.log('[WS]', event, data));
```

### Force re-broadcast from backend
```python
# In Python REPL or debugger
await orch.broadcast_state()
```

### Common issues
| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| No updates at all | WS disconnected | Check `ws-status` dot in UI |
| Updates delayed | Throttle too high | Check `_monDetailRefreshPending` timer |
| Wrong group updates | `group_id` mismatch | Verify `_monitorGroupId` matches |
| Stale data after activity done | API returns old DB data | Use live WS patch instead of API |
