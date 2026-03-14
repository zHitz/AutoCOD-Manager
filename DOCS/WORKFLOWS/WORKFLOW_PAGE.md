# 📋 Workflow Page — Developer Documentation

> **File:** `frontend/js/pages/workflow.js`  
> **Version:** V3 — Last updated: 2026-03-04  
> **Purpose:** Bot automation control center + Recipe Builder

---

## Table of Contents

1. [Overview](#overview)
2. [Page Architecture](#page-architecture)
3. [UI Sections](#ui-sections)
4. [Frontend — WF3 Object](#frontend--wf3-object)
5. [Backend — API Endpoints](#backend--api-endpoints)
6. [Registry System](#registry-system)
7. [Config Schema (v2)](#config-schema-v2)
8. [WebSocket Protocol](#websocket-protocol)
9. [Bot Orchestrator](#bot-orchestrator)
10. [Data Flow Diagrams](#data-flow-diagrams)
11. [How to Add a New Activity](#how-to-add-a-new-activity)
12. [How to Add a New Recipe Function](#how-to-add-a-new-recipe-function)
13. [File Map](#file-map)
14. [Known Limitations](#known-limitations)

---

## Overview

The Workflow page has **three main sections** reachable via the top tab bar:

| Tab | Purpose |
|-----|---------|
| **Activity (Bot)** | Configure and run automated bot activities per Account Group |
| **Recipe Builder** | Compose custom step-by-step automation recipes |
| **Account Groups** | Create and manage groups of accounts to assign to bots |
| **Monitor** | Real-time workflow overview — queue, activities, KPIs, timeline ([docs](./MONITOR_TAB.md)) |

**Key Design Decisions:**
- Activity definitions live **exclusively** in `workflow_registry.py` → the frontend fetches them at init time
- Activity configs are **stored per-group** as JSON on disk (`data/activity_configs/{group_id}.json`)
- Bot execution state is **pushed in real-time** via WebSocket (`bot_queue_update` event)
- Per-activity status tracking is embedded in WS payloads — no polling needed

---

## Page Architecture

```
workflow.js
├── WorkflowPage       ← Static HTML renderer (renders page shell once)
│
└── WF3                ← Main engine object (all logic lives here)
    ├── init()         ← Entry point called by page router
    ├── Registry       ← _systemActivities[], loadRegistry()
    ├── Config Cache   ← _groupConfigs{}, _loadConfigFromBackend()
    ├── Tab Switching  ← switchMainTab(), switchActivityTab(), switchRightTab()
    ├── Activity Tab   ← renderActivitiesForGroup(), saveActivityConfig()
    ├── Group Tab      ← renderGroupList(), saveCurrentGroup()
    ├── Builder Tab    ← renderListView(), renderEditorView(), step logic
    ├── Bot Control    ← runBotActivities(), stopBotActivities()
    ├── Monitor Tab    ← _initMonitorTab(), queue/detail/timeline/KPI (see MONITOR_TAB.md)
    ├── WebSocket      ← setupWebSocket(), _processQueueUpdate()
    └── Status         ← _updateActivityStatuses(), _updateGroupStatusBadge()
```

---

## UI Sections

### 1. Activity (Bot) Tab

**Layout:** Three-panel design

```
┌────────────────────────────────────────────────────────────────────────┐
│  LEFT SIDEBAR (Target Groups)   │  CENTER (Activity List)  │  RIGHT PANEL  │
│                                  │                          │               │
│  ● Group A  🟢                  │  ☑ Gather Resource ⚙️   │  Config or Log │
│  ○ Group B  ⚪                  │  ☐ Full Scan        ⚙️   │               │
│  ○ Group C  ⚪                  │  ☑ Catch Pet        ⚙️   │               │
│                                  │                          │               │
│  [▶ Start Bot]  [■ Stop Bot]    │                          │               │
└────────────────────────────────────────────────────────────────────────┘
```

**Key DOM IDs:**

| Element | ID |
|---------|-----|
| Target Groups list | `wf-target-groups-list` |
| Activity list container | `wf-act-dynamic-list` |
| Activity log console | `wf-activity-console` |
| Config panel | `acv-config-panel` |
| Group badge (selected) | `wf-act-group-badge` |
| Session timer | `wf-session-timer` |
| Start button | `wf-act-start-btn` |
| Stop button | `wf-act-stop-btn` |

**Per-Activity Row Elements:**

| Element | ID Pattern |
|---------|-----------|
| Status badge | `acv-status-{activity_id}` |
| Group status dot | `grp-status-{group_id}` |

**Activity Status Values:**

| Value | Display | Meaning |
|-------|---------|---------|
| `na` | N/A | Not started / bot not running |
| `pending` | Queued | Bot running, activity not yet reached |
| `running` | Running | Currently executing |
| `done` | Done | Completed successfully |
| `error` | Error | Failed with an error |
| `skipped` | Skipped | Skipped (e.g., on cooldown) |

---

### 2. Recipe Builder Tab

Step-based drag-and-drop editor. Each step maps to a `function_id` from the `FUNCTION_REGISTRY`.

**Key DOM IDs:**

| Element | ID |
|---------|-----|
| Step list container | `wf-step-list` |
| Function search | `wf-fn-search` |
| Recipe name input | `wf-recipe-name` |

---

### 3. Account Groups Tab

CRUD interface for managing account groups.

**Key DOM IDs:**

| Element | ID |
|---------|-----|
| Group sidebar list | `wf-group-list` |
| Group editor | `wf-group-editor` |
| Group name input | `wf-group-name` |
| Account table | `wf-group-accounts-list` |

---

## Frontend — WF3 Object

### State Variables

```javascript
WF3 = {
    // Recipe Builder State
    steps: [],              // Current recipe steps
    functions: [],          // Available functions from registry
    templates: [],          // Pre-built templates
    recipes: [],            // User's saved recipes
    currentRecipeId: null,  // Currently editing recipe
    isRunning: false,       // Whether bot is currently running
    activeView: 'list',     // 'list' | 'editor'
    activeMainTab: 'activity',

    // Activity Tab State
    activitySelectedGroupId: null, // Currently selected group in Activities tab
    groupsData: [],         // All account groups from API
    accountsData: [],       // All accounts from API

    // NEW Registry & Config Cache
    _systemActivities: [],  // Loaded from /api/workflow/activity-registry
    _groupConfigs: {},      // keyed by groupId → v2 config object

    // Status Tracking
    _latestActivityStatuses: null, // Cached WS payload for tab-switch restore
    _botLogs: [],           // In-memory log ring buffer (max 500)
}
```

### Key Methods

#### Init & Data Loading

| Method | Description |
|--------|-------------|
| `init()` | Entry point — loads registry, data; starts WS |
| `loadRegistry()` | Fetches `ACTIVITY_REGISTRY` from backend |
| `loadGroupsData()` | Fetches account groups |
| `loadAccountsData()` | Fetches accounts list |

#### Config Management

| Method | Description |
|--------|-------------|
| `getActivityConfig(groupId)` | Returns mapped array of `{id, name, enabled}` from cache |
| `saveActivityConfig(groupId)` | Reads checkboxes → updates `_groupConfigs` → saves to backend |
| `getPerActivityConfig(activityId, groupId)` | Returns full config for one activity (merged defaults + saved) |
| `savePerActivityConfig(activityId, groupId)` | Reads panel fields → saves cooldown + config keys to cache → backend |
| `getMiscConfig(groupId)` | Returns `{cooldown_min, limit_min}` |
| `saveMiscConfig(groupId)` | Saves misc timing settings to cache + backend |
| `_loadConfigFromBackend(groupId)` | Fetches v2 config JSON from API → hydrates `_groupConfigs` |
| `_saveConfigToBackend(groupId)` | POST current `_groupConfigs[groupId]` to backend |

#### Rendering

| Method | Description |
|--------|-------------|
| `renderActivitiesForGroup(groupId)` | Renders activity checkboxes using `_systemActivities` |
| `renderMiscForGroup(groupId)` | Renders cooldown/time limit fields |
| `showActivityConfig(activityId, groupId)` | Renders config panel for a specific activity |
| `renderGroupList()` | Renders the sidebar group list |

#### Bot Control

| Method | Description |
|--------|-------------|
| `runBotActivities()` | Validates, filters cooldowns, builds payload, calls `/api/bot/run-sequential` |
| `stopBotActivities()` | Calls `/api/bot/stop/{group_id}` |
| `addBotLog(type, message)` | Appends to in-memory log + DOM console |
| `_replayLogs()` | Restores log DOM after tab switch |

#### Status Updates

| Method | Description |
|--------|-------------|
| `_updateActivityStatuses(queueData)` | Reads `queueData.activity_statuses` → updates per-activity badges |
| `_updateGroupStatusBadge(groupId, statusInfo)` | Updates 🟢/🟡/⚪ dot in sidebar |

---

## Backend — API Endpoints

### Workflow Registry

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/workflow/activity-registry` | Returns all botactivities from `ACTIVITY_REGISTRY` |
| `GET` | `/api/workflow/functions` | Returns all recipe functions from `FUNCTION_REGISTRY` |
| `GET` | `/api/workflow/templates` | Returns pre-built recipe templates |

### Activity Config

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/workflow/activity-config/{group_id}` | Returns v2 config for a group (migrates v1 on the fly) |
| `POST` | `/api/workflow/activity-config/{group_id}` | Saves v2 config for a group |

**GET Response format:**
```json
{
  "status": "ok",
  "config": { ...v2 schema... }
}
```

### Bot Control

| Method | URL | Description |
|--------|-----|-------------|
| `POST` | `/api/bot/run-sequential` | Starts sequential bot for a group |
| `POST` | `/api/bot/run` | Starts parallel bot (all accounts at once) |
| `POST` | `/api/bot/stop/{group_id}` | Requests stop for a running group |
| `GET` | `/api/bot/status` | Returns all active orchestrators' state |

**`/api/bot/run-sequential` Payload:**
```json
{
  "group_id": 6,
  "accounts": [
    { "id": 1, "game_id": "12345", "emu_index": 0, "lord_name": "Hero" }
  ],
  "activities": [
    { "id": "gather_resource", "name": "Gather Resource", "config": { "resource_type": "stone" } }
  ],
  "misc": { "cooldown_min": 30, "limit_min": 45 }
}
```

### Recipes

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/workflow/recipes` | List all saved recipes |
| `POST` | `/api/workflow/recipes` | Create a new recipe |
| `PUT` | `/api/workflow/recipes/{id}` | Update a recipe |
| `DELETE` | `/api/workflow/recipes/{id}` | Delete a recipe |

### Groups

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/groups` | List all account groups |
| `POST` | `/api/groups` | Create a group |
| `PUT` | `/api/groups/{id}` | Update a group |
| `DELETE` | `/api/groups/{id}` | Delete a group |

---

## Registry System

### `workflow_registry.py`

The **single source of truth** for all activity and function definitions.

#### `ACTIVITY_REGISTRY` — Bot Activities

```python
{
    "id": "gather_resource",       # Machine ID (used everywhere)
    "name": "Gather Resource",     # Display name
    "icon": "⛏️",
    "description": "...",
    "steps": [
        { "function_id": "startup_to_lobby", "config": {} },
        { "function_id": "nav_to_farming", "config": { "resource_type": "wood" } },
    ],
    "config_fields": [
        {
            "key": "resource_type",
            "label": "Farm Resource Type",
            "type": "select",              # select | checkbox | number | text
            "options": ["gold", "wood", "stone", "mana"],
            "default": "wood"
        }
    ],
    "defaults": {
        "cooldown_enabled": False,
        "cooldown_minutes": 60
    }
}
```

#### `FUNCTION_REGISTRY` — Recipe Builder Functions

```python
{
    "id": "adb_tap",
    "label": "Tap Screen",
    "category": "ADB Actions",
    "icon": "👆",
    "color": "#fb923c",
    "description": "...",
    "params": [
        { "key": "x", "label": "X", "type": "number", "default": 540, "min": 0, "max": 1920 },
        { "key": "y", "label": "Y", "type": "number", "default": 960, "min": 0, "max": 1080 }
    ]
}
```

**Available Function Categories:**

| Category | Color | Examples |
|----------|-------|---------|
| Core Actions | `#6366f1` (indigo) | `startup_to_lobby`, `back_to_lobby`, `wait_for_state` |
| ADB Actions | `#fb923c` (orange) | `adb_tap`, `adb_swipe`, `adb_press_back`, `adb_screencap` |
| App Control | `#22c55e` (green) | `open_app`, `check_app_foreground` |
| Scan Operations | `#38bdf8` (sky) | `scan_full`, `scan_profile` |
| Scripts | `#a855f7` (purple) | `run_macro` |
| Flow Control | `#f59e0b` (amber) | `flow_delay`, `check_state` |

---

## Config Schema (v2)

Stored as `data/activity_configs/{group_id}.json`

```json
{
  "version": 2,
  "group_id": 6,
  "updated_at": "2026-03-04T08:11:15Z",
  "activities": {
    "gather_resource": {
      "enabled": true,
      "config": { "resource_type": "stone" },
      "cooldown_enabled": false,
      "cooldown_minutes": 60,
      "last_run": "2026-03-04T08:00:00Z"
    },
    "gather_rss_center": {
      "enabled": false,
      "config": {},
      "cooldown_enabled": false,
      "cooldown_minutes": 60,
      "last_run": null
    }
  },
  "misc": {
    "cooldown_min": 30,
    "limit_min": 45
  }
}
```

> **Key rule:** The activity `id` (e.g., `gather_resource`) is the canonical key used everywhere — frontend, backend, and JSON. **Never use display names as keys.**

### Migration from v1

The `GET /api/workflow/activity-config/{group_id}` endpoint automatically migrates old v1 configs (which used arrays + separate `perActivityConfigs` dict) to v2 on first access.

---

## WebSocket Protocol

**Connection URL:** `ws://localhost:8000/ws`

### Message Types

#### Received by frontend

```javascript
// Bot queue update (primary status event)
{
  "type": "bot_queue_update",
  "data": {
    "group_id": 6,
    "is_running": true,
    "stop_requested": false,
    "cycle": 1,
    "current_idx": 0,
    "total_accounts": 3,
    "current_activity": {
      "id": "gather_resource",
      "name": "Gather Resource",
      "status": "running"
    },
    "activity_statuses": {
      "gather_resource": "running",
      "full_scan": "pending",
      "catch_pet": "pending"
    },
    "accounts": [
      { "id": 1, "lord_name": "Hero", "emu_index": 0, "status": "running" }
    ]
  }
}

// Executor log line (printed to console)
{
  "type": "executor_log",
  "data": { "level": "info", "message": "Step 1: Boot to Lobby..." }
}
```

#### Frontend handling

The `_processQueueUpdate(data)` method in `WF3` handles all `bot_queue_update` events:
1. Updates `isRunning` state
2. Calls `_updateGroupStatusBadge()` for sidebar dot
3. Calls `_updateActivityStatuses()` for per-activity badges
4. Updates Start/Stop button states

---

## Bot Orchestrator

`backend/core/workflow/bot_orchestrator.py`

### Class: `BotOrchestrator`

Manages sequential account execution for a single group.

**Constructor params:**
```python
BotOrchestrator(
    group_id: int,
    accounts: List[Dict],   # [{id, game_id, emu_index, lord_name}]
    activities: List[Dict], # [{id, name, config}]
    ws_callback: Callable,  # async fn(event_type, data)
    misc_config: Dict       # {cooldown_min, limit_min}
)
```

**Execution flow:**
1. Iterates accounts sequentially in `queue`
2. For each account, checks cooldown against `last_run_times`
3. For each enabled activity, calls `build_steps_for_activity()` to get executor steps
4. Updates `activity_statuses[activity_id]` before/after each activity execution
5. Broadcasts state via `ws_callback` after every significant state change

**Active orchestrators** are stored in `_active_orchestrators[group_id]` (module-level dict in `bot_orchestrator.py`).

---

## Data Flow Diagrams

### Config Load Flow (on group select)

```
User selects group in UI
    │
    ▼
toggleActivityGroup(groupId, ...)
    │
    ▼
_loadConfigFromBackend(groupId)     GET /api/workflow/activity-config/{groupId}
    │                                       │
    │                               Backend reads JSON
    │                               Migrates v1 → v2 if needed
    │                               Returns {status: "ok", config: {...v2...}}
    │
    ▼
_groupConfigs[groupId] = config     (hydrates in-memory cache)
    │
    ▼
renderActivitiesForGroup(groupId)   (reads from _groupConfigs + _systemActivities)
    │
    ▼
DOM renders activities with correct enabled state
```

### Bot Start Flow

```
User clicks [▶ Start Bot]
    │
    ▼
runBotActivities()
    ├─ getActivityConfig(groupId)     → filters enabled activities
    ├─ _isOnCooldown(actId, groupId)  → filters out cooldown activities
    └─ getPerActivityConfig(actId)    → builds executor config payload
    │
    ▼
POST /api/bot/run-sequential
    │
    ├─ Backend reads accounts from DB
    ├─ Creates BotOrchestrator(group_id, accounts, activities, ws_callback)
    └─ asyncio.create_task(orchestrator.start())
    │
    ▼
WS: bot_queue_update events pushed every ~2s
    │
    ▼
_processQueueUpdate(data)
    ├─ _updateGroupStatusBadge()      → 🟢/🟡/⚪
    └─ _updateActivityStatuses()      → per-activity badges
```

---

## How to Add a New Activity

### Step 1: Register in backend

In `backend/core/workflow/workflow_registry.py`, add to `ACTIVITY_REGISTRY`:

```python
{
    "id": "daily_quest",               # Unique snake_case ID
    "name": "Daily Quest",             # Display name
    "icon": "📅",
    "description": "Complete all daily quests",
    "steps": [
        { "function_id": "startup_to_lobby", "config": {} },
        { "function_id": "nav_to_daily_quest", "config": {} },  # Must exist in executor
    ],
    "config_fields": [
        # Optional: fields shown in the config panel
        { "key": "quest_count", "label": "Quests to Complete", "type": "number", "default": 5, "min": 1, "max": 10 }
    ],
    "defaults": {
        "cooldown_enabled": True,
        "cooldown_minutes": 1440  # 24h
    }
}
```

### Step 2: Implement the executor function

In `backend/core/workflow/core_actions.py` (or a dedicated activity script), implement the function referenced by `function_id`:

```python
def nav_to_daily_quest(serial: str, detector: GameStateDetector) -> bool:
    # ... ADB actions here ...
    return True
```

Register the routing in `backend/core/workflow/executor.py` inside the dispatch table or `if/elif` block:
```python
        elif fn_id == "nav_to_daily_quest":
            ok = await asyncio.to_thread(
                core_actions.nav_to_daily_quest, serial, detector
            )
```

### Step 3: Done ✅

The frontend automatically fetches and displays the new activity because it loads from `/api/workflow/activity-registry`. No frontend code changes needed.

---

## How to Add a New Recipe Function

### Step 1: Add to `FUNCTION_REGISTRY`

```python
{
    "id": "nav_to_market",
    "label": "Open Market",
    "category": "Core Actions",
    "icon": "🏪",
    "color": "#6366f1",
    "description": "Navigate to the in-game market",
    "params": [
        { "key": "tab", "label": "Market Tab", "type": "select",
          "default": "buy", "options": ["buy", "sell", "exchange"] }
    ]
}
```

### Step 2: Implement the executor function

Same as activity step 2. Implement in `executor.py` and register in the function map.

### Step 3: Done ✅

The Recipe Builder automatically picks up the new function via `GET /api/workflow/functions`.

---

## File Map

```
UI_MANAGER/
├── frontend/
│   └── js/
│       └── pages/
│           └── workflow.js              ← Main page JS (WF3 + WorkflowPage)
├── backend/
│   ├── api.py                          ← All REST endpoints
│   └── core/
│       └── workflow/
│           ├── workflow_registry.py    ← ACTIVITY_REGISTRY + FUNCTION_REGISTRY
│           ├── bot_orchestrator.py     ← Sequential bot execution engine
│           ├── executor.py             ← Step-by-step recipe runner
│           ├── core_actions.py         ← High-level game navigation functions
│           ├── state_detector.py       ← OpenCV game state detection
│           └── templates/              ← OpenCV template images (.png)
├── data/
│   ├── activity_configs/
│   │   └── {group_id}.json            ← Per-group activity config (v2 schema)
│   └── recipes/
│       └── {recipe_id}.json           ← Saved user recipes
└── WORKFLOW_PAGE.md                    ← This file
```

---

## Known Limitations

| Issue | Workaround / Notes |
|-------|-------------------|
| **Cross-emulator swap** is a stub | `_handle_cross_emu_swap()` only logs; real LDPlayer kill/launch not yet implemented |
| **No retry logic** | If an activity fails mid-execution, the orchestrator marks it as `error` and moves on |
| **No parallel execution** per group | `run-sequential` is the primary path; `/api/bot/run` (parallel) still exists but uses a different flow |
| **`ruff` / `mypy` not installed** | Lint checker will fail on Windows without these; safe to ignore for now |
