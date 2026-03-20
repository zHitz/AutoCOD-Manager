import aiosqlite
import json
from datetime import datetime
from backend.config import config


async def create_run(run_id: str, meta: dict):
    """Create a new execution run record."""
    async with aiosqlite.connect(config.db_path) as db:
        await db.execute(
            """INSERT INTO task_runs (
                run_id, source_page, trigger_type, triggered_by, target_id, 
                status, started_at, duration_ms, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                meta.get("source_page", "workflow"),
                meta.get("trigger_type", "manual"),
                meta.get("triggered_by", "system"),
                meta.get("target_id", 0),
                "RUNNING",
                datetime.now().isoformat(),
                0,
                json.dumps(meta),
            ),
        )
        await db.commit()


async def append_step_log(
    run_id: str,
    step_index: int,
    function_id: str,
    input_dict: dict,
    output_dict: dict,
    status: str,
    error_msg: str = "",
    latency_ms: int = 0,
):
    """Append a step log to an existing run."""
    async with aiosqlite.connect(config.db_path) as db:
        await db.execute(
            """INSERT INTO task_run_steps (
                run_id, step_index, function_id, input_json, output_json, 
                status, error_code, error_message, started_at, ended_at, latency_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                step_index,
                function_id,
                json.dumps(input_dict) if input_dict else "{}",
                json.dumps(output_dict) if output_dict else "{}",
                status,
                "",  # error_code
                error_msg,
                datetime.now().isoformat(),  # started_at
                datetime.now().isoformat(),  # ended_at (approx)
                latency_ms,
            ),
        )
        await db.commit()


async def complete_run(run_id: str, status: str, duration_ms: int):
    """Mark a run as complete or failed with final duration."""
    async with aiosqlite.connect(config.db_path) as db:
        await db.execute(
            """UPDATE task_runs SET 
                status = ?, ended_at = ?, duration_ms = ?
            WHERE run_id = ?""",
            (status, datetime.now().isoformat(), duration_ms, run_id),
        )
        await db.commit()


# ── Account Activity Logs (v2 fact table for Task page) ──


async def start_account_activity(
    run_id: str,
    account_id: int,
    game_id: str,
    emulator_id: int,
    group_id: int,
    activity_id: str,
    activity_name: str,
    source: str = "workflow",
    metadata: dict = None,
) -> int:
    """Insert a RUNNING row into account_activity_logs. Returns the row id."""
    async with aiosqlite.connect(config.db_path) as db:
        cursor = await db.execute(
            """INSERT INTO account_activity_logs (
                run_id, account_id, game_id, emulator_id, group_id,
                activity_id, activity_name, status, started_at,
                source, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'RUNNING', ?, ?, ?)""",
            (
                run_id,
                account_id,
                game_id,
                emulator_id,
                group_id,
                activity_id,
                activity_name,
                datetime.now().isoformat(),
                source,
                json.dumps(metadata) if metadata else "{}",
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def finish_account_activity(
    log_id: int,
    status: str,
    error_code: str = "",
    error_message: str = "",
    duration_ms: int = 0,
    result: dict = None,
):
    """Update an account_activity_logs row to its final status."""
    async with aiosqlite.connect(config.db_path) as db:
        await db.execute(
            """UPDATE account_activity_logs SET
                status = ?, error_code = ?, error_message = ?,
                finished_at = ?, duration_ms = ?, result_json = ?
            WHERE id = ?""",
            (
                status,
                error_code,
                error_message,
                datetime.now().isoformat(),
                duration_ms,
                json.dumps(result) if result else "{}",
                log_id,
            ),
        )
        await db.commit()


async def get_last_account_run(account_id: int) -> float:
    """Return the timestamp of the most recent started_at for any activity on an account."""
    async with aiosqlite.connect(config.db_path) as db:
        async with db.execute(
            """SELECT started_at FROM account_activity_logs 
               WHERE account_id = ? 
               ORDER BY started_at DESC LIMIT 1""",
            (account_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                try:
                    return datetime.fromisoformat(row[0]).timestamp()
                except ValueError:
                    return 0
            return 0


async def get_last_activity_run(account_id: int, activity_id: str) -> float:
    """Return the timestamp of the most recent SUCCESS run for a specific activity on an account."""
    async with aiosqlite.connect(config.db_path) as db:
        async with db.execute(
            """SELECT started_at FROM account_activity_logs 
               WHERE account_id = ? AND activity_id = ? AND status = 'SUCCESS'
               ORDER BY started_at DESC LIMIT 1""",
            (account_id, activity_id),
        ) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                try:
                    return datetime.fromisoformat(row[0]).timestamp()
                except ValueError:
                    return 0
            return 0


async def get_effective_cooldown_sec(
    account_id: int, activity_id: str, include_failures: bool = False
) -> tuple:
    """Return (last_run_epoch, dynamic_cooldown_sec) from the latest log.

    If the activity's result_json contains 'dynamic_cooldown_sec', that value
    is returned. Otherwise dynamic_cooldown_sec = 0, meaning the caller should
    fall back to the static cooldown_minutes config.

    When include_failures=True, also considers FAILED runs for cooldown timing.
    FAILED runs always return dynamic_cooldown_sec=0 (uses static cooldown).
    """
    status_filter = "status IN ('SUCCESS', 'FAILED')" if include_failures else "status = 'SUCCESS'"
    async with aiosqlite.connect(config.db_path) as db:
        async with db.execute(
            f"""SELECT started_at, result_json, status FROM account_activity_logs
               WHERE account_id = ? AND activity_id = ? AND {status_filter}
               ORDER BY started_at DESC LIMIT 1""",
            (account_id, activity_id),
        ) as cursor:
            row = await cursor.fetchone()
            if not row or not row[0]:
                return (0, 0)

            try:
                last_run = datetime.fromisoformat(row[0]).timestamp()
            except ValueError:
                return (0, 0)

            # FAILED runs: no dynamic cooldown, caller uses static config
            row_status = row[2] if row[2] else "SUCCESS"
            if row_status == "FAILED":
                return (last_run, 0)

            dynamic_cd = 0
            if row[1]:
                try:
                    result = json.loads(row[1])
                    dynamic_cd = int(result.get("dynamic_cooldown_sec", 0))
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass

            return (last_run, dynamic_cd)
