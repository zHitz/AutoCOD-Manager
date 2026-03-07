# Implementation Plan: Account Activity Logging (Phase 1)

> Addresses the TASKS team's [response.md](file:///f:/COD_CHECK/UI_MANAGER/improve/TASKS/response.md) — Phase 1 (data foundation) + Phase 2 (dedicated API).

---

## Scope

Phase 1+2 from the TASKS roadmap. Phase 3 (frontend cleanup) and Phase 4 (analytics/SLA) are out of scope for now.

---

## Proposed Changes

### 1. Database Schema — `account_activity_logs` v2

#### [MODIFY] [database.py](file:///f:/COD_CHECK/UI_MANAGER/backend/storage/database.py)

Add the new table + indexes to `CREATE_TABLES_SQL` (after line 194):

```sql
-- Activity execution history per account (v2)
CREATE TABLE IF NOT EXISTS account_activity_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL,
    account_id      INTEGER NOT NULL,
    game_id         TEXT NOT NULL,
    emulator_id     INTEGER,
    group_id        INTEGER,
    activity_id     TEXT NOT NULL,
    activity_name   TEXT NOT NULL,
    status          TEXT NOT NULL CHECK(status IN ('PENDING','RUNNING','SUCCESS','FAILED','SKIPPED','CANCELED')),
    error_code      TEXT DEFAULT '',
    error_message   TEXT DEFAULT '',
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    duration_ms     INTEGER DEFAULT 0,
    attempts        INTEGER DEFAULT 1,
    source          TEXT DEFAULT 'workflow',
    metadata_json   TEXT DEFAULT '{}',
    result_json     TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_aal_account_started ON account_activity_logs(account_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_aal_game_started    ON account_activity_logs(game_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_aal_activity_started ON account_activity_logs(activity_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_aal_status_started   ON account_activity_logs(status, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_aal_run              ON account_activity_logs(run_id);
```

---

### 2. Execution Logger — New Methods

#### [MODIFY] [execution_log.py](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/execution_log.py)

Add two new async functions:

```python
async def start_account_activity(run_id, account_id, game_id, emulator_id, group_id, activity_id, activity_name, source="workflow", metadata=None) -> int:
    """Insert a new RUNNING row. Returns the log row id."""
    # INSERT INTO account_activity_logs (...)
    # VALUES (run_id, account_id, game_id, emulator_id, group_id,
    #         activity_id, activity_name, 'RUNNING', ..., now(), ...)
    # return cursor.lastrowid

async def finish_account_activity(log_id, status, error_code="", error_message="", duration_ms=0, result=None):
    """Update the row to final status."""
    # UPDATE account_activity_logs
    # SET status=?, error_code=?, error_message=?, finished_at=now(),
    #     duration_ms=?, result_json=?
    # WHERE id=?
```

---

### 3. Orchestrator Hook Points

#### [MODIFY] [bot_orchestrator.py](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/bot_orchestrator.py#L269-L341)

Inside the activity loop (line 269–341), hook the new logger:

```diff
 for i, act in enumerate(self.activities):
     ...
     step_start = time.time()
+    # ── LOG: Activity Started ──
+    log_id = await execution_log.start_account_activity(
+        run_id=self.run_id,
+        account_id=int(acc_id),
+        game_id=acc.get("game_id", ""),
+        emulator_id=emu_idx,
+        group_id=self.group_id,
+        activity_id=act_id_or_name,
+        activity_name=act.get("name", act_id_or_name),
+        source="workflow",
+        metadata=act_cfg
+    )
     ...
     step_end = time.time()
     latency = int((step_end - step_start) * 1000)
+    # ── LOG: Activity Finished ──
+    await execution_log.finish_account_activity(
+        log_id=log_id,
+        status=step_status,
+        error_code="TIMEOUT" if isinstance(...) else "",
+        error_message=step_error,
+        duration_ms=latency,
+        result=result
+    )
```

Also emit WebSocket events:
- `activity_started` — when activity begins
- `activity_completed` / `activity_failed` — when activity ends

---

### 4. Dedicated API Endpoint

#### [MODIFY] [api.py](file:///f:/COD_CHECK/UI_MANAGER/backend/api.py)

Add new endpoint:

```python
@app.get("/api/task/checklist")
async def get_task_checklist(date: str = None, group_id: int = None):
    """
    Returns activity execution history grouped by account.
    Query params: ?date=YYYY-MM-DD&group_id=X
    
    Response shape:
    {
      "accounts": [
        {
          "account_id": 1,
          "game_id": "ABC123",
          "lord_name": "Goten",
          "emulator_name": "BotInstance1",
          "activities": {
            "full_scan":      {"status": "SUCCESS", "last_run": "...", "runs_today": 2, "total_duration_ms": 45000},
            "gather_resource": {"status": "FAILED",  "last_run": "...", "runs_today": 1, "total_duration_ms": 12000, "error": "Timeout"},
            ...
          },
          "stats": { "total": 6, "done": 5, "failed": 1, "coverage": 83 }
        },
        ...
      ],
      "summary": { "total_accounts": 7, "avg_coverage": 85 }
    }
    ```
    Internally: SELECT from account_activity_logs
    JOIN accounts, emulators
    WHERE date(started_at) = ?date AND group_id = ?group_id
    GROUP BY account_id, activity_id
    """
```

---

## Verification Plan

1. Start a workflow via the UI for a group with 2+ accounts.
2. After completion, query SQLite: `SELECT * FROM account_activity_logs ORDER BY id DESC LIMIT 20;`
3. Verify each activity has: correct `account_id`, [game_id](file:///f:/COD_CHECK/UI_MANAGER/backend/storage/database.py#1457-1526), `activity_id`, [status](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/executor.py#54-65), `duration_ms`.
4. Hit `GET /api/task/checklist?date=2026-03-05` and verify the JSON response matches the expected shape for the TASKS team's UI grid.
