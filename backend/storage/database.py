"""
SQLite Storage — Database for scan results, task logs, and emulator sessions.
"""
import aiosqlite
import sqlite3
import json
import os
from datetime import datetime
from backend.config import config


CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS scan_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    serial TEXT NOT NULL,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL,
    data TEXT,
    is_reliable INTEGER DEFAULT 1,
    validation_errors TEXT,
    duration_ms INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS task_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    serial TEXT NOT NULL,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL,
    error TEXT,
    duration_ms INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS emulator_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    serial TEXT NOT NULL,
    event TEXT NOT NULL,
    details TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_scan_serial ON scan_results(serial);
CREATE INDEX IF NOT EXISTS idx_scan_created ON scan_results(created_at);
CREATE INDEX IF NOT EXISTS idx_logs_serial ON task_logs(serial);
"""


class Database:
    """Async SQLite database wrapper."""

    def __init__(self):
        self.db_path = config.db_path
        self._initialized = False

    def init_sync(self):
        """Initialize database synchronously (for startup)."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.executescript(CREATE_TABLES_SQL)
        conn.close()
        self._initialized = True

    async def _get_conn(self):
        return await aiosqlite.connect(self.db_path)

    async def save_scan_result(
        self,
        serial: str,
        task_type: str,
        status: str,
        data: dict,
        is_reliable: bool,
        validation_errors: list,
        duration_ms: int,
    ):
        """Save a scan result to the database."""
        async with await self._get_conn() as db:
            await db.execute(
                """INSERT INTO scan_results
                   (serial, task_type, status, data, is_reliable, validation_errors, duration_ms)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    serial,
                    task_type,
                    status,
                    json.dumps(data, default=str),
                    1 if is_reliable else 0,
                    json.dumps(validation_errors),
                    duration_ms,
                ),
            )
            await db.commit()

    async def save_task_log(
        self,
        task_id: str,
        serial: str,
        task_type: str,
        status: str,
        error: str = None,
        duration_ms: int = 0,
    ):
        """Log a task execution."""
        async with await self._get_conn() as db:
            await db.execute(
                """INSERT INTO task_logs
                   (task_id, serial, task_type, status, error, duration_ms)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (task_id, serial, task_type, status, error, duration_ms),
            )
            await db.commit()

    async def get_scan_history(self, limit: int = 50, serial: str = None) -> list[dict]:
        """Get recent scan results."""
        async with await self._get_conn() as db:
            db.row_factory = aiosqlite.Row
            if serial:
                cursor = await db.execute(
                    """SELECT * FROM scan_results WHERE serial = ?
                       ORDER BY created_at DESC LIMIT ?""",
                    (serial, limit),
                )
            else:
                cursor = await db.execute(
                    """SELECT * FROM scan_results
                       ORDER BY created_at DESC LIMIT ?""",
                    (limit,),
                )
            rows = await cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "serial": row["serial"],
                    "task_type": row["task_type"],
                    "status": row["status"],
                    "data": json.loads(row["data"]) if row["data"] else {},
                    "is_reliable": bool(row["is_reliable"]),
                    "validation_errors": json.loads(row["validation_errors"])
                    if row["validation_errors"]
                    else [],
                    "duration_ms": row["duration_ms"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    async def get_task_logs(self, limit: int = 100) -> list[dict]:
        """Get recent task logs."""
        async with await self._get_conn() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM task_logs ORDER BY created_at DESC LIMIT ?""",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_latest_report(self, serial: str) -> dict | None:
        """Get the latest scan result for a specific device."""
        async with await self._get_conn() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM scan_results WHERE serial = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (serial,),
            )
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "serial": row["serial"],
                    "task_type": row["task_type"],
                    "status": row["status"],
                    "data": json.loads(row["data"]) if row["data"] else {},
                    "is_reliable": bool(row["is_reliable"]),
                    "duration_ms": row["duration_ms"],
                    "created_at": row["created_at"],
                }
            return None


# Global singleton
database = Database()
