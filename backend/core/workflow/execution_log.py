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
                json.dumps(meta)
            )
        )
        await db.commit()

async def append_step_log(run_id: str, step_index: int, function_id: str, input_dict: dict, output_dict: dict, status: str, error_msg: str = "", latency_ms: int = 0):
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
                latency_ms
            )
        )
        await db.commit()

async def complete_run(run_id: str, status: str, duration_ms: int):
    """Mark a run as complete or failed with final duration."""
    async with aiosqlite.connect(config.db_path) as db:
        await db.execute(
            """UPDATE task_runs SET 
                status = ?, ended_at = ?, duration_ms = ?
            WHERE run_id = ?""",
            (status, datetime.now().isoformat(), duration_ms, run_id)
        )
        await db.commit()
