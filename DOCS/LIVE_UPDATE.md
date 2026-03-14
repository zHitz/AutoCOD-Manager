# Live Update System

> How real-time UI updates work across pages. For dev & debugging. Last updated: 2026-03-14.

---

## Architecture Overview

```
BotOrchestrator                  WebSocket                    Frontend Pages
  broadcast_state() ──────►  bot_queue_update  ──────►  Account Queue (live)
                                                         Activity Detail (live patch)
                                                         KPI Panel (throttled)
                                                         Activity Tab badges
  _emit_timeline()  ──────►  timeline_event    ──────►  Monitor Timeline
                             activity_started           Timeline buffer
                             activity_completed
                             activity_failed
```

---

## Monitor Tab — Live Update Flow

### Account Queue (Left Panel)

**Update method:** Full re-render from WS data.

```
bot_queue_update received
  └── WF3._renderMonitorQueue(data)     ← re-renders entire queue HTML
      └── Uses data.accounts[] for:
          - lord_name, status, emu_index
          - cooldown_remaining_sec
          - Running/Next/Done indicators
```

**File:** `workflow.js` → `setupWebSocket()` line ~2908

### Activity Detail (Right Panel)

**Two-layer update strategy:**

| Layer | Speed | What it updates | Method |
|-------|-------|-----------------|--------|
| **Instant patch** | ~0ms | Tags (Running/Next/Done), row highlight | `_liveUpdateActivityDetail(wsData)` |
| **Full refresh** | 10s throttle | Duration, runs count, cooldown timer | `_onMonitorAccountClick()` → API fetch |

#### Instant Patch — `_liveUpdateActivityDetail(wsData)`

**Trigger:** Every `bot_queue_update` event.

**How it works:**
1. Reads `wsData.activity_statuses` (e.g., `{Train Troops: "running", Catch Pet: "done"}`)
2. Reads `wsData.current_activity` (e.g., `"Train Troops"`)
3. Matches current account: `wsData.accounts[wsData.current_idx].id === selectedAccountId`
4. Finds activity rows in DOM by `.mon-act-name` text content
5. Determines `runningIdx` and `nextIdx`
6. Patches:
   - Row class: `mon-act-current` (green border) or `mon-act-next` (blue border)
   - Tag HTML: `Running`, `Next`, `Done`, `Error` inside `.mon-act-w-tag`

**Does NOT update:** Duration (Time column), Runs count, Cooldown timer — these require API data.

#### Full Refresh — Throttled API Call

**Trigger:** First `bot_queue_update` after previous refresh completes (10s cooldown).

```
bot_queue_update
  └── if (!_monDetailRefreshPending)
        _monDetailRefreshPending = true
        setTimeout(10000) → _onMonitorAccountClick(selectedAccountId)
            └── GET /api/monitor/account-activities?account_id=X&group_id=Y
                └── _renderMonitorDetail(data, accountId)  ← full re-render
```

### KPI Panel

**Update method:** Throttled fetch.

```
bot_queue_update → _scheduleKpiRefresh() → GET /api/monitor/kpi (debounced)
```

### Cooldown Timer

**Update method:** 1-second interval timer.

```
bot_queue_update → _startMonitorTimer() → setInterval(1000)
  └── ticks all [data-cd] elements, decrementing seconds
```

---

## Activity Tab — Live Update Flow

### Activity Status Badges

**File:** `workflow.js` → `_updateActivityStatuses(data)`

```
bot_queue_update (if groupId matches activitySelectedGroupId)
  └── _updateActivityStatuses(data)
      └── Updates badge dots, status text on activity cards
```

### Account Queue Panel

```
bot_queue_update → renderAccountQueue(data)  ← re-renders queue panel on Activity tab
```

---

## Task Page — Live Update Flow

**File:** `task.js` → `_wsWorkflowHandler`

```
bot_queue_update → _wsWorkflowHandler(data)
  └── Updates task progress indicators
```

---

## When Bot is NOT Running

When the bot stops, no more `bot_queue_update` events are emitted. The last state persists in the UI until:
- User navigates away and back
- User refreshes the page

**Account Queue fallback:** `_renderMonitorQueueFromGroup()` fetches account names from `/api/accounts` API instead of WS data.

---

## Common Live Update Bugs & Fixes

### 1. Activity tags don't update live
**Symptom:** Tags (Running/Next/Done) stay stale, only update on page reload.
**Root cause:** `_liveUpdateActivityDetail()` not called or `activity_statuses` missing from WS data.
**Debug:**
```js
wsClient.on('bot_queue_update', d => console.log('activity_statuses:', d.activity_statuses));
```
**Check:** Ensure `bot_orchestrator.activity_statuses` is populated for each activity.

### 2. Account Queue doesn't show real names
**Symptom:** Shows "Account #12" instead of "dragonball Goten".
**Root cause:** When bot is NOT running, `_renderMonitorQueueFromGroup()` only has account IDs.
**Fix:** Function now fetches `/api/accounts` for `lord_name`. If `lord_name` is empty in DB, it falls back to `game_id` then `Account #ID`.

### 3. Detail panel shows stale data after activity completes
**Symptom:** Duration/runs don't update immediately after activity finishes.
**Root cause:** These values come from DB via API, not WS. The 10s throttle delays the refresh.
**Workaround:** Reduce throttle timeout or trigger immediate refresh on `activity_completed`.

### 4. Updates work on Monitor but not Activity tab
**Symptom:** Monitor tab updates fine, Activity tab badges are stale.
**Root cause:** `bot_queue_update` handler has a gate: `if (groupId != WF3.activitySelectedGroupId) return;`
**Fix:** Ensure `activitySelectedGroupId` matches the running bot's group.

### 5. WS connected but no events received
**Symptom:** WS status shows "Connected" but UI never updates.
**Debug:**
```js
wsClient.on('*', (e, d) => console.log('[WS ALL]', e));
```
**Check:** Backend `broadcast_state()` is actually being called (add print statement).

---

## Key Files Reference

| File | Role | Key Functions |
|------|------|---------------|
| `backend/websocket.py` | WS manager singleton | `broadcast()`, `broadcast_sync()` |
| `backend/core/workflow/bot_orchestrator.py` | Main event emitter | `broadcast_state()`, `_emit_timeline()` |
| `frontend/js/api.js` | WS client class | `WSClient.connect()`, `.on()`, `.off()` |
| `frontend/js/app.js` | Global WS wiring | `wireUpWebSocket()` — task/scan events |
| `frontend/js/pages/workflow.js` | Monitor/Activity WS | `setupWebSocket()` — bot/workflow events |
| `frontend/js/pages/task.js` | Task page WS | `_wsWorkflowHandler` |

---

## Adding a New WS Event (Checklist)

1. **Backend:** Emit via `ws_callback("my_event", {...data})`
2. **Frontend:** Register listener: `wsClient.on('my_event', (data) => { ... })`
3. **Add to this doc:** Event name, data schema, consumer
4. **Test:** Use `wsClient.on('*', ...)` to verify receipt
5. **Consider:** Does it need page-specific gating? (e.g., only when Monitor tab is active)
