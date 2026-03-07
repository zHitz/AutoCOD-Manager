# 📋 TASK PAGE — Backend API Documentation

> **Audience:** Team TASKS (Frontend)
> **Last updated:** 2026-03-05
> **Backend contact:** Workflow Team

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Database Schema](#2-database-schema)
3. [API Endpoints](#3-api-endpoints)
4. [WebSocket Events](#4-websocket-events)
5. [Activity Registry](#5-activity-registry)
6. [Data Flow](#6-data-flow)
7. [Example Scenarios](#7-example-scenarios)
8. [Error Codes](#8-error-codes)

---

## 1. Architecture Overview

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────────────┐
│  Task Page   │────▶│  GET /api/task/   │────▶│  account_activity_logs  │
│  (Frontend)  │     │  checklist        │     │  (SQLite)               │
└──────┬───────┘     └──────────────────┘     └─────────────────────────┘
       │                                                ▲
       │  WebSocket                                     │ INSERT/UPDATE
       │  (real-time)                                   │
       ▼                                       ┌────────┴────────┐
┌─────────────┐                                │ BotOrchestrator │
│  WS Events  │◀───────────────────────────────│ (execution loop)│
│  activity_*  │                                └─────────────────┘
└─────────────┘
```

**Key principle:** Backend writes all data. Frontend only reads via API + listens to WS for real-time updates. No frontend derivation needed.

---

## 2. Database Schema

### Table: `account_activity_logs`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment row ID |
| `run_id` | TEXT NOT NULL | Links to `task_runs.run_id` — identifies the workflow session |
| `account_id` | INTEGER NOT NULL | Links to `accounts.id` |
| `game_id` | TEXT NOT NULL | Denormalized game ID for fast query (e.g., `"ABC123"`) |
| `emulator_id` | INTEGER | Emulator index used during execution |
| `group_id` | INTEGER | Account group at execution time |
| `activity_id` | TEXT NOT NULL | Stable key from Activity Registry (e.g., `"full_scan"`) |
| `activity_name` | TEXT NOT NULL | Display name snapshot (e.g., `"Full Scan"`) |
| `status` | TEXT NOT NULL | One of: `PENDING`, `RUNNING`, `SUCCESS`, `FAILED`, `SKIPPED`, `CANCELED` |
| `error_code` | TEXT | Structured error category: `TIMEOUT`, `EXEC_FAIL`, `EXCEPTION`, or empty |
| `error_message` | TEXT | Human-readable error detail |
| `started_at` | TEXT NOT NULL | ISO 8601 timestamp (e.g., `"2026-03-05T14:30:00"`) |
| `finished_at` | TEXT | ISO 8601 timestamp, NULL if still running |
| `duration_ms` | INTEGER | Execution time in milliseconds |
| `attempts` | INTEGER | Number of execution attempts (default: 1) |
| `source` | TEXT | Origin: `"workflow"`, `"manual"`, `"scheduler"`, `"retry"` |
| `metadata_json` | TEXT | JSON string of activity config/inputs |
| `result_json` | TEXT | JSON string of execution output |

### Indexes (for fast queries)

| Index | Columns | Use Case |
|-------|---------|----------|
| `idx_aal_account_started` | `(account_id, started_at DESC)` | Filter by account |
| `idx_aal_game_started` | `(game_id, started_at DESC)` | Filter by game ID |
| `idx_aal_activity_started` | `(activity_id, started_at DESC)` | Filter by activity type |
| `idx_aal_status_started` | `(status, started_at DESC)` | Filter by status |
| `idx_aal_run` | `(run_id)` | Lookup by run session |

---

## 3. API Endpoints

### `GET /api/task/checklist`

The **primary endpoint** for the Task page. Returns all activity execution data grouped by account.

#### Query Parameters

| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `date` | string | No | Today (`YYYY-MM-DD`) | Filter logs by date |
| `group_id` | integer | No | All groups | Filter by account group |

#### Example Request

```
GET /api/task/checklist?date=2026-03-05&group_id=1
```

#### Success Response

```json
{
  "status": "success",
  "date": "2026-03-05",
  "accounts": [
    {
      "account_id": 1,
      "game_id": "ABC123",
      "lord_name": "dragonball Goten",
      "emulator_name": "BotInstance1",
      "emulator_id": 0,
      "group_id": 1,
      "activities": {
        "full_scan": {
          "activity_name": "Full Scan",
          "status": "SUCCESS",
          "last_run": "2026-03-05T14:30:00",
          "runs_today": 2,
          "total_duration_ms": 45000,
          "error": ""
        },
        "gather_resource": {
          "activity_name": "Gather Resource",
          "status": "FAILED",
          "last_run": "2026-03-05T15:10:00",
          "runs_today": 1,
          "total_duration_ms": 12000,
          "error": "Timeout limit 30m reached"
        },
        "gather_rss_center": {
          "activity_name": "Gather Resource Center",
          "status": "SUCCESS",
          "last_run": "2026-03-05T13:00:00",
          "runs_today": 1,
          "total_duration_ms": 60000,
          "error": ""
        }
      },
      "stats": {
        "total": 3,
        "done": 2,
        "failed": 1,
        "coverage": 67
      }
    },
    {
      "account_id": 2,
      "game_id": "DEF456",
      "lord_name": "dragonball King Kai",
      "emulator_name": "BotInstance2",
      "emulator_id": 1,
      "group_id": 1,
      "activities": {
        "full_scan": {
          "activity_name": "Full Scan",
          "status": "SUCCESS",
          "last_run": "2026-03-05T14:35:00",
          "runs_today": 1,
          "total_duration_ms": 22000,
          "error": ""
        }
      },
      "stats": {
        "total": 1,
        "done": 1,
        "failed": 0,
        "coverage": 100
      }
    }
  ],
  "summary": {
    "total_accounts": 2,
    "avg_coverage": 84
  }
}
```

#### Error Response

```json
{
  "status": "error",
  "error": "database is locked"
}
```

---

### `GET /api/workflow/activity-registry`

Returns **all available activities** defined in the backend. Use this to build the column headers for the Task grid.

#### Example Response

```json
{
  "status": "success",
  "data": [
    {
      "id": "gather_rss_center",
      "name": "Gather Resource Center",
      "icon": "🏛️",
      "description": "Farm resources at the Resource Center"
    },
    {
      "id": "gather_resource",
      "name": "Gather Resource",
      "icon": "⛏️",
      "description": "Gather resources on the world map"
    },
    {
      "id": "full_scan",
      "name": "Full Scan",
      "icon": "🔬",
      "description": "Boot to lobby and run full data scan"
    },
    {
      "id": "catch_pet",
      "name": "Catch Pet",
      "icon": "🐾",
      "description": "Capture pet on the world map"
    }
  ]
}
```

---

### `GET /api/accounts`

Returns all accounts in the system. Useful for cross-referencing account details.

#### Key Fields

| Field | Description |
|-------|-------------|
| `account_id` | Primary key |
| `game_id` | In-game player ID |
| `lord_name` | Display name |
| `emulator_id` | Assigned emulator |
| `power` | Account power level |
| `status` | `pending` / `confirmed` / `dismissed` |

---

## 4. WebSocket Events

Connect to the WebSocket at `ws://localhost:{port}/ws` to receive real-time activity updates.

### Event: `activity_started`

Fired when an activity begins execution for an account.

```json
{
  "type": "activity_started",
  "data": {
    "group_id": 1,
    "account_id": "1",
    "activity_id": "full_scan",
    "activity_name": "Full Scan",
    "status": "",
    "error": "",
    "duration_ms": 0
  }
}
```

### Event: `activity_completed`

Fired when an activity finishes successfully.

```json
{
  "type": "activity_completed",
  "data": {
    "group_id": 1,
    "account_id": "1",
    "activity_id": "full_scan",
    "activity_name": "Full Scan",
    "status": "SUCCESS",
    "error": "",
    "duration_ms": 45000
  }
}
```

### Event: `activity_failed`

Fired when an activity fails.

```json
{
  "type": "activity_failed",
  "data": {
    "group_id": 1,
    "account_id": "1",
    "activity_id": "gather_resource",
    "activity_name": "Gather Resource",
    "status": "FAILED",
    "error": "Timeout limit 30m reached",
    "duration_ms": 1800000
  }
}
```

---

## 5. Activity Registry (Current Activities)

These are the `activity_id` values that will appear in the logs. Use them as column keys in your grid.

| `activity_id` | Display Name | Icon | Description |
|----------------|-------------|------|-------------|
| `gather_rss_center` | Gather Resource Center | 🏛️ | Farm resources at the Resource Center |
| `gather_resource` | Gather Resource | ⛏️ | Gather resources on the world map |
| `full_scan` | Full Scan | 🔬 | Boot to lobby and run full data scan |
| `catch_pet` | Catch Pet | 🐾 | Capture pet on the world map |

> **Note:** This list grows as the Workflow team adds new activities. Always use `GET /api/workflow/activity-registry` at runtime to get the latest list.

---

## 6. Data Flow

### When a workflow runs:

```
1. User clicks "Start" on Workflow page
   └─▶ POST /api/bot/run-sequential

2. BotOrchestrator starts processing accounts one by one
   └─▶ For each account:
       └─▶ For each activity:
           ├─▶ INSERT into account_activity_logs (status: RUNNING)
           ├─▶ WS emit: activity_started
           ├─▶ Execute activity...
           ├─▶ UPDATE account_activity_logs (status: SUCCESS/FAILED)
           └─▶ WS emit: activity_completed / activity_failed

3. Task page calls GET /api/task/checklist
   └─▶ Returns grouped, aggregated data ready to render
```

### Recommended Frontend Flow:

```
1. On page load:
   - GET /api/workflow/activity-registry → build column headers
   - GET /api/task/checklist?date=today  → populate the grid

2. Connect WebSocket:
   - Listen for activity_started/completed/failed
   - Update specific cells in real-time (optimistic UI)

3. On date/group change:
   - Re-fetch GET /api/task/checklist?date=X&group_id=Y
```

---

## 7. Example Scenarios

### Scenario: Building the Grid (like the reference image)

The reference UI shows:

| Account | ƯU TIÊN | ĐIỂM DANH | THU TÀI NGUYÊN | DONATE LM | TUẦN TRA | SHOP | SỰ KIỆN | TIẾN ĐỘ |
|---------|---------|-----------|----------------|-----------|---------|------|---------|---------|
| Goten | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | | 6/6 · 100% |

**To build this:**

1. **Columns** = activity registry items (mapped to Vietnamese labels by your UI).
2. **Rows** = `accounts[]` from checklist response.
3. **Checkmarks** = `activities[activity_id].status === "SUCCESS"` → ✅, else ☐.
4. **Progress** = `stats.done` / `stats.total` · `stats.coverage`%.

### Scenario: Account has no data yet today

If an account has not run any activities today, it will **not appear** in the `accounts[]` array. You should cross-reference with `GET /api/accounts` to show all accounts with empty checkmarks.

### Scenario: Activity running right now

If an activity is currently running, its status will be `"RUNNING"` and `finished_at` will be `null`. You can show a spinner ⏳ instead of a checkmark.

---

## 8. Error Codes

| `error_code` | Meaning | Suggested UI |
|-------------|---------|--------------|
| `""` (empty) | No error (SUCCESS) | ✅ |
| `TIMEOUT` | Activity exceeded time limit | ⏱️ Timeout |
| `EXEC_FAIL` | Activity returned failure | ❌ Failed |
| `EXCEPTION` | Unexpected runtime error | ⚠️ Error |

---

## Quick Start Checklist

- [ ] Fetch activity registry → build grid columns
- [ ] Fetch checklist data → populate rows
- [ ] Connect WebSocket → real-time cell updates
- [ ] Handle missing accounts (show empty row with all ☐)
- [ ] Handle `RUNNING` status (show spinner)
- [ ] Map `activity_id` to your Vietnamese label/column
- [ ] Calculate progress bar from `stats.coverage`
