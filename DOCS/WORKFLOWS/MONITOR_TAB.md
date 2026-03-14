# 📊 Monitor Tab — Developer Documentation

> **Files:** `workflow.js` (frontend), `bot_orchestrator.py` (backend), `api.py`, `kpi_calculator.py`  
> **Version:** V1 — Last updated: 2026-03-13  
> **Purpose:** Real-time visibility into workflow execution — account queues, activity progress, cooldown timers, KPI metrics, and event timeline.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [UI Structure](#ui-structure)
4. [Frontend — WF3 Monitor Methods](#frontend--wf3-monitor-methods)
5. [Backend — API & WebSocket Events](#backend--api--websocket-events)
6. [Data Flow](#data-flow)
7. [CSS Classes Reference](#css-classes-reference)
8. [File Map](#file-map)

---

## Overview

The Monitor tab is the **4th tab** on the Workflow page (after Activity, Recipe Builder, Account Groups). It provides a centralized, real-time dashboard to answer:

- **What already ran?** — account status badges + activity detail with last run times
- **What is running now?** — live running account highlight + current activity indicator
- **What will run next?** — next-account highlight + queue order visibility
- **How long until next run?** — real-time cooldown countdown timers
- **How well is the bot performing?** — KPI summary metrics

**Key Design Decisions:**

- **Standalone project** — completely separated from the Activity tab; no shared rendering/state
- **WebSocket-first** — real-time updates via `bot_queue_update` (state dump), `timeline_event` (lifecycle events), and `workflow_log` (executor logs)
- **In-memory buffers** — timeline events stored in JS (max 200 FIFO); no backend persistence needed
- **Group-scoped** — all data filtered by the selected Account Group

---

## Architecture

```
WF3 Monitor Methods
├── Tab Init
│   ├── _initMonitorTab()         ← Populate group dropdown, restore timeline state
│   ├── _onMonitorGroupChange()   ← Group switch → clear panels → fetch data
│   └── _refreshMonitor()         ← REST fetch → render queue + KPI
│
├── Queue Panel (Left)
│   ├── _renderMonitorQueue()     ← Groups by emu, sub-info, next highlight, auto-scroll
│   └── _renderMonitorQueueFromGroup()  ← Fallback when bot is not running
│
├── Detail Panel (Right)
│   ├── _onMonitorAccountClick()  ← Fetch per-account activities from REST
│   └── _renderMonitorDetail()    ← Enriched header + activity rows
│
├── Header
│   └── _updateMonitorStatusBadge() ← RUNNING/IDLE/STOPPED + progress + smart wait
│
├── KPI Bar
│   ├── _renderMonitorKpi()       ← Fetch + display 5 KPI cards
│   └── _scheduleKpiRefresh()     ← Throttled refresh (max once per 5s)
│
├── Timeline Panel (Bottom)
│   ├── _toggleTimeline()         ← Expand/collapse + localStorage persist
│   ├── _pushTimelineEvent()      ← Push to buffer (max 200, FIFO)
│   ├── _renderTimeline()         ← Render newest-first event rows
│   └── _clearTimeline()          ← Reset buffer + DOM
│
├── Cooldown Timer
│   ├── _startMonitorTimer()      ← setInterval(1000) countdown
│   └── _stopMonitorTimer()       ← clearInterval on tab leave
│
└── Helpers
    ├── _formatCD(sec)            ← Seconds → "M:SS"
    └── _timeAgo(epochSec)        ← Epoch → "10m ago"
```

---

## UI Structure

### Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ HEADER: [Workflow Monitor] [🟢 RUNNING · Cycle 3] [Account: 5/12]          │
│         [⏳ Smart Wait: 2:30]                [Group ▼]  [🔄 Refresh]       │
├──────────────────────────────────────────────────────────────────────────────┤
│ KPI BAR: [⚖️ Fairness 0.92] [✅ Success 95.2%] [🔄 Ping-pong 0]          │
│          [⏱️ Exec Time 72.1%] [📊 C3 · 85%]                               │
├────────────────────────────────────┬─────────────────────────────────────────┤
│ ACCOUNT QUEUE (~40%)               │ ACTIVITY DETAIL (~60%)                  │
│                                    │                                         │
│ ── Emulator 2 ────────── (3)       │ 👤 Gohan                               │
│  │ 1 │ Goten        ✅  │         │ Emu 4 · ID 11300640 · Status: Running  │
│  │   │ Emu 2 · 16025 · 10m ago   │                                         │
│  │ 2 │ Roshi         ⏳ 12:34    │ ┌──────────────────────────────────────┐ │
│  │   │ Emu 2 · 19231 · 45m ago   │ │ ✅ Gather Resource   Done   2m ago │ │
│  ───────────────────────           │ │ ▶ Catch Pet           Running      │ │
│ ── Emulator 4 ────────── (2)       │ │ ⬜ Full Scan          Pending      │ │
│  │▶3 │ Gohan  ██ Running│         │ │ ⏳ Train Troops       CD 15:23    │ │
│  │   │ Emu 4 · 11300 · Just now   │ └──────────────────────────────────────┘ │
│  │ 4 │ Buu    ┊ Next ┊  │         │                                         │
│  │   │ Emu 4 · 16025 · 1h ago     │                                         │
├────────────────────────────────────┴─────────────────────────────────────────┤
│ [                          Show Timeline ▼                                 ] │
│ (collapsed by default — click to expand)                                     │
│ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│ 18:28:15  🔁  Cycle 3 — Account 5/12: Gohan on Emu 4                       │
│ 18:28:12  ✅  Goten: Gather Resource success (12.3s)                        │
│ 18:27:59  ▶️  Goten: Starting Gather Resource                               │
│ 18:27:55  ✅  Emu 5562: Goten verified — match on attempt 1                 │
│ 18:27:50  🔄  Emu 4: Swapping to Goten (16025767) — attempt 1/3            │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Key DOM IDs

| Element | ID | Description |
|---------|------|-------------|
| Section container | `wf-section-monitor` | Hidden/shown by tab switcher |
| Status badge | `mon-status-badge` | RUNNING / IDLE / STOPPED / STOPPING |
| Progress counter | `mon-progress` | "Account: 3/12" |
| Smart Wait badge | `mon-smart-wait` | "⏳ Smart Wait: 2:30" |
| Group filter | `mon-group-filter` | `<select>` dropdown |
| KPI bar container | `mon-kpi-bar` | 5 KPI cards |
| KPI cells | `mon-kpi-fairness`, `mon-kpi-success`, `mon-kpi-pingpong`, `mon-kpi-exectime`, `mon-kpi-coverage` | Individual KPI values |
| Queue list | `mon-queue-list` | Account queue panel |
| Detail content | `mon-detail-content` | Activity detail panel |
| Timeline container | `mon-timeline` | Collapsible event log |
| Timeline list | `mon-timeline-list` | Event rows |
| Timeline toggle | `mon-tl-toggle-text` | "Show Timeline ▼" / "Hide Timeline ▲" |

### Status Badge States

| State | CSS Class | Display | Trigger |
|-------|-----------|---------|---------|
| Running | `mon-badge-running` | 🟢 RUNNING · Cycle N | `is_running && !stop_requested` |
| Stopping | `mon-badge-stopping` | 🟡 STOPPING | `is_running && stop_requested` |
| Idle | `mon-badge-idle` | ⚪ IDLE / STOPPED | `!is_running` |

### Account Row Status Classes

| Status | CSS Class | Visual |
|--------|-----------|--------|
| running | `mon-st-running` | Green dot |
| done/completed/success | `mon-st-done` | Green check |
| error | `mon-st-error` | Red dot |
| skipped | `mon-st-skipped` | Gray skip |
| pending | `mon-st-pending` | Gray hollow |

### Account Highlighting

| Highlight | CSS Class | Visual |
|-----------|-----------|--------|
| Currently running | `mon-acc-current` | `border-left: 3px solid` green |
| Next in queue | `mon-acc-next` | `border-left: 3px dashed` blue + "NEXT" label |
| Selected (clicked) | `mon-acc-selected` | Background highlight |

---

## Frontend — WF3 Monitor Methods

### State Variables

```javascript
WF3 = {
    // Monitor tab state
    _monitorGroupId: null,              // Selected group ID
    _monitorLastData: null,             // Last bot_queue_update payload (cached)
    _monitorSelectedAccountId: null,    // Currently clicked account in queue
    _monitorTimerInterval: null,        // setInterval reference for CD countdown
    _monitorKpiThrottle: null,          // setTimeout ref for KPI refresh throttle
    _monTimelineEvents: [],             // In-memory timeline buffer (max 200)
}
```

### Method Reference

#### Init & Navigation

| Method | Trigger | Description |
|--------|---------|-------------|
| `_initMonitorTab()` | Tab switch to Monitor | Populates group dropdown, restores timeline state from localStorage |
| `_onMonitorGroupChange(groupId)` | Group dropdown change | Clears panels + last data, calls `_refreshMonitor()` |
| `_refreshMonitor()` | Init or manual refresh | `GET /api/bot/status` → render queue + KPI + status badge |

#### Queue Panel

| Method | Description |
|--------|-------------|
| `_renderMonitorQueue(data)` | Builds queue HTML grouped by `emu_index`. Each row: order number, name, sub-info (`Emu N · game_id · Xm ago`), status dot, CD timer. Determines next account (`current_idx + 1 % length`). Auto-scrolls to running account. |
| `_renderMonitorQueueFromGroup()` | Fallback when bot is not running — renders accounts from group data with "pending" status |

#### Detail Panel

| Method | Description |
|--------|-------------|
| `_onMonitorAccountClick(id)` | Sets `_monitorSelectedAccountId`, highlights row, fetches `GET /api/monitor/account-activities?account_id=X&group_id=Y` |
| `_renderMonitorDetail(data, accountId)` | Enriched header (name, Emu, ID, cooldown/status), activity list with per-activity status/last_run/CD columns |

#### Header

| Method | Description |
|--------|-------------|
| `_updateMonitorStatusBadge(data)` | Updates status badge (RUNNING/IDLE/STOPPED), progress counter (`Account: X/Y`), and smart wait badge (`⏳ Smart Wait: M:SS`) |

#### KPI

| Method | Description |
|--------|-------------|
| `_renderMonitorKpi(groupId)` | `GET /api/monitor/kpi-summary?group_id=X` → updates 5 KPI cards with color classes (kpi-good/warn/bad) |
| `_scheduleKpiRefresh()` | Throttles KPI refresh to max once per 5 seconds |

#### Timeline

| Method | Description |
|--------|-------------|
| `_toggleTimeline()` | Expand/collapse panel. Persists state to `localStorage('mon_timeline_open')`. On open → re-renders. |
| `_pushTimelineEvent(evt)` | Pushes `{ts, icon, message, emu_index?, account_id?}` to buffer. Evicts oldest if >200. Renders if panel visible. |
| `_renderTimeline()` | Renders all events newest-first as `<div class="mon-tl-row">` with timestamp, icon, message columns. |
| `_clearTimeline()` | Resets buffer and DOM. |

#### Cooldown Timer

| Method | Description |
|--------|-------------|
| `_startMonitorTimer()` | `setInterval(1000)` — finds all `[data-cd]` elements, decrements by 1, updates text, removes at 0 |
| `_stopMonitorTimer()` | `clearInterval` on tab leave or bot stop |

#### Helpers

| Method | Input → Output | Description |
|--------|----------------|-------------|
| `_formatCD(sec)` | `134 → "2:14"` | Seconds to `M:SS` format |
| `_timeAgo(epochSec)` | `1710340000 → "10m ago"` | Epoch seconds to human-readable relative time |

---

## Backend — API & WebSocket Events

### REST Endpoints

#### `GET /api/monitor/account-activities`

Returns per-account activity history for the detail panel.

**Query params:** `account_id` (required), `group_id` (optional)

**Response:**
```json
{
  "status": "ok",
  "data": {
    "date": "2026-03-13",
    "activities": [
      {
        "activity_id": "gather_resource_center",
        "activity_name": "Gather Resource Center",
        "last_status": "SUCCESS",
        "last_run": "2026-03-13T03:15:00",
        "runs_today": 4,
        "cooldown_remaining_sec": 1523
      }
    ]
  }
}
```

**Data source:** `account_activity_logs` table + `activity_configs/{group_id}.json`

---

#### `GET /api/monitor/kpi-summary`

Returns aggregated KPI metrics for the selected group.

**Query params:** `group_id` (required)

**Response:**
```json
{
  "status": "ok",
  "data": {
    "fairness_index": 0.92,
    "success_rate": 95.2,
    "ping_pong_count": 0,
    "execute_time_pct": 72.1,
    "cycle": 3,
    "coverage_pct": 85.0,
    "total_runs_today": 47
  }
}
```

**Data source:** `kpi_calculator.py` → `account_activity_logs` table

---

### WebSocket Events

#### `bot_queue_update` (existing, extended)

Primary state dump — emitted by `broadcast_state()` on every significant state change.

```json
{
  "type": "bot_queue_update",
  "data": {
    "group_id": 6,
    "is_running": true,
    "stop_requested": false,
    "cycle": 3,
    "current_idx": 2,
    "total_accounts": 12,
    "current_activity": { "id": "gather_resource", "name": "Gather Resource", "status": "running" },
    "activity_statuses": { "gather_resource": "running", "catch_pet": "pending" },
    "accounts": [
      {
        "id": 5,
        "lord_name": "Gohan",
        "emu_index": 4,
        "game_id": "11300640",
        "status": "running",
        "last_run_time": 1710339800,
        "cooldown_remaining_sec": 0
      }
    ],
    "activity_metrics": { "gather_resource": { "last_run": "...", "runs_today": 3 } },
    "cooldown_config": {
      "cooldown_min": 30,
      "swap_wait_threshold_min": 5,
      "skip_cooldown": false
    },
    "smart_wait_active": {
      "account_id": "5",
      "remaining_sec": 150.2
    }
  }
}
```

**Monitor tab uses:** `accounts[]` (queue panel), `current_idx` (running highlight), `smart_wait_active` (smart wait badge), `activity_metrics` (future use).

---

#### `timeline_event` (new)

High-level lifecycle events emitted by `_emit_timeline()` in `bot_orchestrator.py`.

```json
{
  "type": "timeline_event",
  "data": {
    "ts": 1710340515.3,
    "icon": "🔄",
    "message": "Emu 4: Swapping to Buu (16025767) — attempt 1/3",
    "emu_index": 4,
    "account_id": "5",
    "group_id": 6
  }
}
```

**9 emission points:**

| Location in orchestrator | Icon | Example message |
|--------------------------|------|-----------------|
| Swap attempt start | 🔄 | `Emu 4: Swapping to Buu (16025767) — attempt 1/3` |
| Swap verified | ✅ | `Emu 5562: Buu verified — match on attempt 1` |
| Swap failed (all attempts) | ❌ | `Swap failed for Buu (16025767) after 3 attempts` |
| Activity started | ▶️ | `Gohan: Starting Gather Resource` |
| Activity completed | ✅ | `Gohan: Gather Resource success (12.3s)` |
| Activity failed | ❌ | `Gohan: Full Scan failed (45.2s)` |
| Smart Wait enter | ⏳ | `Emu 4: Smart Wait for Gohan (2.5m remaining)` |
| Cycle start | 🔁 | `Cycle 3 — Account 5/12: Goten on Emu 2` |
| All on cooldown | 💤 | `All accounts on cooldown. Sleeping 4.2m` |

---

#### `workflow_log` (existing, now used by Monitor)

Step-level execution logs from `executor.py`. Previously only used by Recipe Builder tab.

```json
{
  "type": "workflow_log",
  "data": {
    "emulator_index": 4,
    "log_type": "ok",
    "message": "✓ gather_resource complete"
  }
}
```

**Monitor maps `log_type` to icons:** `ok` → ✅, `err` → ❌, anything else → ℹ️

---

### Backend Methods (bot_orchestrator.py)

#### `_emit_timeline(icon, message, emu_index=None, account_id=None)`

Helper to emit `timeline_event` WS events.

```python
async def _emit_timeline(self, icon: str, message: str, emu_index: int = None, account_id: str = None):
    """Emit a timeline_event for the Monitor tab's bottom timeline panel."""
    if not self.ws_callback:
        return
    data = {
        "ts": time.time(),
        "icon": icon,
        "message": message,
        "emu_index": emu_index,
        "account_id": account_id,
        "group_id": self.group_id,
    }
    # ... ws_callback dispatch (async/sync)
```

#### `broadcast_state()` — Extended Fields

| Field | Type | Added for Monitor |
|-------|------|-------------------|
| `accounts[].last_run_time` | `float\|null` | Epoch seconds of last successful run |
| `accounts[].cooldown_remaining_sec` | `float` | Seconds remaining until cooldown expires |
| `accounts[].game_id` | `string` | In-game player ID |
| `cooldown_config` | `object` | `{cooldown_min, swap_wait_threshold_min, skip_cooldown}` |
| `smart_wait_active` | `object` | `{account_id, remaining_sec}` or both `null` |
| `activity_metrics` | `object` | Per-activity `{last_run, runs_today}` from DB |

---

## Data Flow

### On Monitor Tab Open

```
User clicks "Monitor" tab
    │
    ▼
_initMonitorTab()
    ├─ GET /api/groups → populate group dropdown
    ├─ Restore localStorage('mon_timeline_open')
    └─ If _monitorGroupId set → _refreshMonitor()
                                    │
                                    ▼
                        GET /api/bot/status?group_id=X
                                    │
                        ┌───── is_running? ──────┐
                       YES                       NO
                        │                         │
                _renderMonitorQueue()    _renderMonitorQueueFromGroup()
                _updateMonitorStatusBadge()        (fallback from group data)
                _startMonitorTimer()
                        │
                        ▼
                _renderMonitorKpi(groupId) → GET /api/monitor/kpi-summary?group_id=X
```

### Real-time Updates (WebSocket)

```
Orchestrator state changes
    │
    ▼
broadcast_state() → WS "bot_queue_update"
    │                       │
    │               Monitor tab handler:
    │               ├─ _updateGroupStatusBadge()
    │               ├─ _renderMonitorQueue(data)
    │               └─ _scheduleKpiRefresh()
    │
_emit_timeline() → WS "timeline_event"
    │                       │
    │               Monitor tab handler:
    │               └─ _pushTimelineEvent(data)
    │
executor.py log() → WS "workflow_log"
                            │
                    Monitor tab handler:
                    └─ _pushTimelineEvent({icon, message, ...})
```

### On Account Click

```
User clicks account row in queue
    │
    ▼
_onMonitorAccountClick(accountId)
    ├─ Highlight row (.mon-acc-selected)
    ├─ Show loading in detail panel
    └─ GET /api/monitor/account-activities?account_id=Y&group_id=X
                │
                ▼
        _renderMonitorDetail(data, accountId)
           ├─ Enriched header (name, Emu, ID, cooldown)
           └─ Activity list with status badges
```

---

## CSS Classes Reference

### Layout

| Class | Purpose |
|-------|---------|
| `mon-header` | Top header bar (flex, space-between) |
| `mon-layout` | 2-panel grid (`2fr 3fr`) |
| `mon-queue-panel` | Left panel (flex column) |
| `mon-detail-panel` | Right panel (flex column) |
| `mon-timeline-wrapper` | Bottom timeline container |

### Status & Badges

| Class | Purpose |
|-------|---------|
| `mon-badge` | Base badge class |
| `mon-badge-running` | Green pulsing badge |
| `mon-badge-idle` | Gray badge |
| `mon-badge-stopping` | Amber badge |
| `mon-progress` | Progress counter pill ("Account: 3/12") |
| `mon-smart-wait-badge` | Amber pulsing smart wait indicator |

### Account Queue

| Class | Purpose |
|-------|---------|
| `mon-emu-group` | Emulator group container |
| `mon-emu-header` | Group header (sticky, dark background) |
| `mon-account-row` | Single account row (flex, clickable) |
| `mon-acc-current` | Running account (3px solid green left border) |
| `mon-acc-next` | Next account (3px dashed blue left border) |
| `mon-acc-selected` | Clicked account (background highlight) |
| `mon-acc-info` | Column container (name + sub-info) |
| `mon-acc-sub` | Sub-info line ("Emu 2 · 16025767 · 10m ago") |
| `mon-acc-order` | Order number (#1, #2...) |
| `mon-acc-name` | Lord name / game ID |
| `mon-next-label` | "NEXT" micro label (blue, uppercase) |
| `mon-cd` | Cooldown timer badge (`data-cd` attribute for JS countdown) |
| `mon-st-running/done/error/skipped/pending` | Status dot color classes |

### Activity Detail

| Class | Purpose |
|-------|---------|
| `mon-detail-header` | Header block (name + sub-info + date) |
| `mon-activity-list` | Activity rows container |
| `mon-act-row` | Single activity row |
| `mon-ast-success/error/running/pending` | Activity status color classes |

### Timeline

| Class | Purpose |
|-------|---------|
| `mon-timeline-toggle` | Full-width toggle button |
| `mon-timeline` | Scrollable event container (max-height 220px) |
| `mon-tl-row` | Single event row (flex) |
| `mon-tl-time` | Timestamp column (mono font, 64px wide) |
| `mon-tl-icon` | Icon column (18px wide) |
| `mon-tl-msg` | Message column (flex: 1, ellipsis on overflow) |

### KPI

| Class | Purpose |
|-------|---------|
| `kpi-bar` | KPI cards container (flex) |
| `kpi-card` | Individual KPI card |
| `kpi-good` | Green value (good metric) |
| `kpi-warn` | Amber value (warning) |
| `kpi-bad` | Red value (bad metric) |

### Utilities

| Class | Purpose |
|-------|---------|
| `mon-empty` | Empty state placeholder text |
| `mon-loading` | Loading spinner/text |
| `mon-panel-title` | Panel section title |
| `mon-select` | Styled `<select>` dropdown |

---

## File Map

```
UI_MANAGER/
├── frontend/
│   ├── js/pages/
│   │   └── workflow.js                ← WF3 Monitor methods (lines ~2990-3488)
│   └── css/
│       └── workflow.css               ← Monitor CSS (lines ~2530-3090)
│
├── backend/
│   ├── api.py                         ← GET /api/monitor/account-activities
│   │                                     GET /api/monitor/kpi-summary
│   └── core/workflow/
│       ├── bot_orchestrator.py        ← broadcast_state() extensions
│       │                                 _emit_timeline() + 9 emission points
│       │                                 _smart_wait_info tracking
│       └── kpi_calculator.py          ← KPI computation (fairness, success rate, etc.)
│
├── DOCS/
│   ├── WORKFLOWS/
│   │   └── MONITOR_TAB.md             ← This file
│   └── Notes/
│       ├── workflow_monitor_tab_design.md  ← Original design spec
│       └── workflow_kpi_checklist.md       ← KPI definitions & targets
│
└── data/
    └── bot_workflow.db                ← account_activity_logs table (SQLite)
```

---

## localStorage Keys

| Key | Values | Purpose |
|-----|--------|---------|
| `mon_timeline_open` | `"0"` / `"1"` | Timeline panel expand/collapse state |
