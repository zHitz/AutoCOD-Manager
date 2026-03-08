# PAGES/TASKS — Architecture & Operational Tracking README

## 1) Overview

The **Tasks page** is the operational tracking layer ("Second Brain") for automation execution.

- **Workflows = Automation Logic** (what to execute and in what sequence).
- **Tasks = Execution Tracking** (what executed, current state, outcomes, and productivity).

Tasks provides operational visibility per account/day/group without owning orchestration logic.

---

## 2) Role of Tasks Page in the System

Tasks operates as:

- **Operational layer**: provides daily account/activity execution matrix.
- **Execution tracker**: exposes runtime state changes.
- **Productivity monitor**: surfaces completion/failure/coverage metrics.

### Automation Brain vs Operational Brain

| Layer | Responsibility | Output |
|---|---|---|
| Workflows (Automation Brain) | define activities, trigger runs, execute orchestrations | activity/run events + raw execution logs |
| Tasks (Operational Brain) | aggregate and project execution data for operators | checklist grid, status indicators, KPIs |

---

## 3) System Architecture

```text
[Accounts + Groups]
      -> [Workflows API/UI]
          -> [Execution Engine / BotOrchestrator]
              -> [account_activity_logs + Event Bus]
                  -> [Read Model Builder]
                      -> [task_daily_state + task_metrics_daily]
                          -> [Tasks API /api/task/checklist]
                              -> [Tasks Page grid + filters + KPI cards]
```

Execution writes immutable/append-style activity logs first; operational APIs consume derived read models.

---

## 4) Activity Dimension Table (`activities`)

A persistent `activities` table should act as the canonical activity catalog rather than relying only on runtime registry responses.

### Proposed schema

| Column | Purpose |
|---|---|
| `id` | stable activity identifier (referenced everywhere) |
| `name` | display name |
| `icon` | UI icon |
| `description` | activity description |
| `category` | grouping/domain (e.g., gather, scan, combat) |
| `is_critical` | critical-path marker for checklist strategy |
| `created_at` | creation timestamp |

### Usage contract

- Workflows reference `activity_id` from `activities.id`.
- Tasks grid columns are built from this catalog (optionally filtered by template/scope).
- Activity registry API should be backed by this table for consistency.

---

## 5) Relationship Between Workflows and Tasks

### Lifecycle

```text
Workflow configured
  -> Execution triggered
    -> Activity logged (RUNNING)
      -> Activity finalized (SUCCESS/FAILED/SKIPPED/CANCELED)
        -> Read model updated
          -> Tasks UI refresh + WS patch
```

### Contract boundary

- **Workflows** own execution planning, runtime orchestration, and event emission.
- **Tasks** own read model consumption, operational rendering, and triage interactions.

---

## 6) Workflow API Integration

| Endpoint | Method | Tasks usage |
|---|---|---|
| `/api/workflow/activity-registry` | GET | catalog sync / fallback registry view |
| `/api/task/checklist` | GET | single payload for checklist view |
| `/api/task/checklist/mark` | POST | manual override command |
| `/api/task/checklist/templates` | GET/POST | column strategy persistence |

---

## 7) Execution Data Source (`account_activity_logs`)

`account_activity_logs` is the canonical execution journal.

### Important execution fields

| Field | Purpose |
|---|---|
| `run_id` | workflow session lineage key |
| `account_id` | account owner of execution |
| `game_id` | denormalized game identity |
| `emulator_id` | runtime emulator context |
| `group_id` | group context at run time |
| `activity_id` | stable activity identity |
| `status` | lifecycle state (`RUNNING`, `SUCCESS`, `FAILED`, etc.) |
| `error_code` | structured failure category |
| `error_message` | human-readable failure reason |
| `duration_ms` | activity runtime latency |
| `attempts` | retry count for the activity execution |
| `metadata_json` | runtime input/config snapshot |
| `result_json` | runtime output/result snapshot |

### Retry and attempts

- `attempts = 1`: first attempt.
- `attempts > 1`: retried execution path.

This identifies flaky behavior and repeated timeout/retry loops.

### Observability fields

- `metadata_json` explains **how** activity executed.
- `result_json` explains **what** activity produced.

Together with `error_code`/`error_message`, they enable root-cause analysis.

---

## 8) Read Model Builder Component

A dedicated **Read Model Builder** component maintains operational projections.

### Event-driven architecture

```text
Execution Engine
  -> Event Bus
    -> Read Model Builder
      -> Upsert task_daily_state
      -> Upsert task_metrics_daily
```

### Responsibilities

- Consume activity lifecycle events.
- Perform idempotent upserts into read model tables.
- Apply manual override merge rules.
- Emit optional compacted events for UI optimization.

### Drift repair

Periodic reconciliation jobs recompute read models from `account_activity_logs` to repair missed events or drift.

---

## 9) Read Model Architecture (`task_daily_state`)

To avoid expensive per-request aggregation from `account_activity_logs`, `/api/task/checklist` reads from `task_daily_state`.

### Suggested schema

| Field | Description |
|---|---|
| `date` | partition key for checklist date |
| `account_id` | row identity for account |
| `activity_id` | activity column identity |
| `group_id` | group filter dimension |
| `status` | latest status for day/account/activity |
| `runs_today` | number of runs for that day |
| `last_run` | latest execution timestamp |
| `duration_total` | sum of durations for the day |
| `error` | latest error snapshot |
| `attempts` | latest/aggregated attempt count for day |

### Indexing strategy

- **Primary key**: `(date, account_id, activity_id)`
- **Secondary index**: `(date, group_id)`
- **Secondary index**: `(account_id, date)`

### Query support

- **Daily checklist by group**: served by `(date, group_id)`.
- **Account history views**: served by `(account_id, date)`.
- **Fast daily aggregations**: bounded scans by `date` with PK locality.

---

## 10) Task Metrics Read Model (`task_metrics_daily`)

A second read model should power analytics dashboards and operational reports.

### Example fields

| Field | Description |
|---|---|
| `date` | metric date partition |
| `activity_id` | activity dimension |
| `total_runs` | total executions |
| `success_count` | successful runs |
| `fail_count` | failed runs |
| `avg_duration` | average duration |
| `p95_duration` | p95 latency |
| `retry_rate` | retry ratio/percentage |

### Purpose

- Powers activity performance analytics without scanning raw logs.
- Supports trend dashboards by day/activity/group (extended dimensions optional).

---

## 11) Grid Data Contract (`GET /api/task/checklist`)

Checklist API returns a **single grid-ready payload** so frontend does not depend on multiple blocking calls.

### Required top-level shape

- `activities`
- `accounts`
- `stats`
- `filters`

### Response contract (recommended)

```json
{
  "status": "success",
  "date": "2026-03-05",
  "activities": [
    {"id": "full_scan", "name": "Full Scan", "icon": "🔬", "is_critical": true}
  ],
  "accounts": [
    {
      "account_id": 1,
      "game_id": "ABC123",
      "lord_name": "dragonball Goten",
      "emulator_name": "BotInstance1",
      "group_id": 1,
      "activities": {
        "full_scan": {
          "status": "SUCCESS",
          "runs_today": 2,
          "last_run": "2026-03-05T14:30:00",
          "duration_total": 45000,
          "error": "",
          "attempts": 1
        }
      },
      "stats": {"total": 1, "done": 1, "failed": 0, "coverage": 100}
    }
  ],
  "stats": {
    "total_accounts": 1,
    "avg_coverage": 100,
    "failed_accounts": 0
  },
  "filters": {
    "applied": {"group_id": 1},
    "cursor": {"next_cursor_account_id": "2"}
  }
}
```

### UI field mapping

- `accounts[].game_id`: identity/search fallback.
- `accounts[].lord_name`: primary row label.
- `accounts[].emulator_name`: execution context label.
- `accounts[].activities`: per-cell status + timings + error + attempts.
- `accounts[].stats`: row progress and coverage.

`stats.coverage` is backend-owned and must not be treated as frontend-computed truth.

---

## 12) Pagination Strategy (Cursor-based)

For 1000+ accounts, checklist API should use cursor pagination instead of offset.

### Query parameters

- `cursor_account_id` (exclusive cursor anchor)
- `limit` (page size)

### Why cursor pagination

- Stable under concurrent writes/updates.
- Avoids large-offset scan cost degradation.
- Supports deterministic continuation for lazy-loading grids.

### Example

```text
GET /api/task/checklist?date=2026-03-05&group_id=1&cursor_account_id=500&limit=100
```

---

## 13) Backend vs Frontend Responsibilities

| Domain | Backend | Frontend |
|---|---|---|
| Execution | run orchestrator/activities | none |
| Logging | persist `account_activity_logs` | none |
| Dimensions | maintain `activities` catalog | consume for column rendering |
| Read models | build/update `task_daily_state`, `task_metrics_daily` | none |
| Aggregation | compute checklist stats/coverage | none |
| Rendering | provide API and WS payloads | render grid/cards/cell status |
| Interaction | expose mark/retry/trigger APIs | filters, sorting, triage UX |
| Reconciliation | publish canonical snapshots | reconcile local UI state with checklist API |

---

## 14) Task Status System

### States

- Pending
- Queued
- Running
- Completed (`SUCCESS` in payload)
- Failed
- Cancelled (`CANCELED`)
- Skipped

### Transitions

```text
PENDING/QUEUED -> RUNNING
RUNNING -> SUCCESS | FAILED | CANCELED
PENDING/QUEUED -> SKIPPED
FAILED -> RUNNING (retry; attempts increments)
```

---

## 15) WebSocket Event Strategy

### Event payloads (contract examples)

#### `activity_started`

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

#### `activity_completed`

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

#### `activity_failed`

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

### Render-storm prevention strategy

- **Event batching**: buffer events in short windows (e.g., 100–300ms).
- **Debounced/throttled patching**: patch visible rows only.
- **Reconciliation loop**: periodic or trigger-based `GET /api/task/checklist` refresh.

### UI patch rule

- Match row by `account_id` and column by `activity_id`.
- Patch lightweight in-memory state first.
- Checklist snapshots remain canonical reconciliation source.

---

## 16) Scalability Design (1000+ accounts, 20+ activities)

### Backend/API

- Cursor pagination (`cursor_account_id`, `limit`) with deterministic ordering.
- Date/group partitioned queries and supporting indexes.
- Read-model queries against `task_daily_state` and `task_metrics_daily`, not raw-log scans.

### Frontend

- Row virtualization (render visible window only).
- Lazy loading/incremental fetch using returned cursor.
- Selective patching for mounted/visible rows during WS bursts.

### Real-time channel

- WS throttling/batching server-side and/or client-side.
- Coalescing duplicate account/activity events under short backpressure windows.

---

## 17) Manual Override Architecture

Manual completion overrides should be isolated in `task_manual_overrides`.

### Suggested fields

| Field | Description |
|---|---|
| `id` | override record id |
| `date` | override scope date |
| `account_id` | target account |
| `activity_id` | target activity |
| `override_status` | `SUCCESS` / `UNDO` / future states |
| `reason` | optional operator note |
| `actor` | user/system source |
| `created_at` | audit timestamp |

### Merge semantics

1. Build base state from `account_activity_logs`.
2. Apply latest manual override for `(date, account_id, activity_id)`.
3. Persist merged result in `task_daily_state` (optionally with `is_overridden` flag).

This preserves auditability while enabling operational correction.

---

## 18) Task Execution Lifecycle

1. Activity starts; execution row written to `account_activity_logs`.
2. Event emitted on bus and WS `activity_started` sent.
3. Activity finalizes with status, errors, duration, attempts, metadata/result.
4. Read Model Builder upserts `task_daily_state` and `task_metrics_daily`.
5. WS completion/failure emitted.
6. Checklist API serves grid-ready derived state.

---

## 19) UI/UX Behavior

Tasks page should expose:

- Checklist matrix (accounts × activities).
- Cell status indicators and error context.
- Row/global progress cards.
- Operational filters (date/group/search/status/priority).
- Fast triage flows for failed/overdue states.

---

## 20) Productivity Tracking

| Metric | Source | Value |
|---|---|---|
| Completed runs | derived status counts | throughput confidence |
| Failed runs | derived status counts | reliability risk signal |
| Execution time | `duration_total`, metrics aggregates | bottleneck detection |
| Success rate / coverage | backend-computed `stats.coverage` | daily execution health |
| Retry pressure | `attempts`, `retry_rate` | flakiness diagnosis |

---

## 21) Debugging and Observability

Use combined fields for diagnosis:

- `run_id` for lineage navigation.
- `error_code` + `error_message` for failure classification.
- `attempts` and `retry_rate` for retry-pattern analysis.
- `metadata_json` + `result_json` for deep context.
- `last_run`, `duration_total`, p95 latency for performance regression.

```text
Failed cell -> inspect error + attempts -> open run_id history
-> inspect metadata/result snapshots -> assess retry/manual trigger/workflow fix
```

---

## 22) Operational Features (Architecture Notes)

Future architecture extensions:

- **Retry activity from failed cell**
  - command endpoint creates new execution with incremented attempt context.
- **Manual activity trigger**
  - direct trigger endpoint scoped to `(account_id, activity_id)`.
- **Execution history by run_id**
  - drilldown API returning full activity timeline and step details.
- **Activity performance analytics**
  - `task_metrics_daily` backed dashboards for latency/failure/retry trends.
