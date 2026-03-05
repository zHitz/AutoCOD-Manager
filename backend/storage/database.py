"""
SQLite Storage — Database for emulators, scan snapshots, macro runs, and task runs.

Schema v2: Normalized 6-table design with migration from v1.
"""
import aiosqlite
import sqlite3
import json
import os
from datetime import datetime
from backend.config import config


# ──────────────────────────────────────────────
# Schema v2 — Normalized tables
# ──────────────────────────────────────────────

CREATE_TABLES_SQL = """
-- Master emulator registry
CREATE TABLE IF NOT EXISTS emulators (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    emu_index       INTEGER NOT NULL UNIQUE,
    serial          TEXT NOT NULL,
    name            TEXT DEFAULT '',
    resolution      TEXT DEFAULT '960x540',
    status          TEXT DEFAULT 'OFFLINE',
    last_seen_at    TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Scan snapshots (versioned, one row per scan)
CREATE TABLE IF NOT EXISTS scan_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    emulator_id     INTEGER NOT NULL,
    scan_type       TEXT DEFAULT 'full_scan',
    lord_name       TEXT DEFAULT '',
    power           INTEGER DEFAULT 0,
    hall_level      INTEGER DEFAULT 0,
    market_level    INTEGER DEFAULT 0,
    pet_token       INTEGER DEFAULT 0,
    scan_status     TEXT DEFAULT 'pending',
    duration_ms     INTEGER DEFAULT 0,
    raw_ocr_text    TEXT DEFAULT '',
    game_id         TEXT DEFAULT '',
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (emulator_id) REFERENCES emulators(id)
);

-- Dynamic resources per scan (EAV pattern)
CREATE TABLE IF NOT EXISTS scan_resources (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id     INTEGER NOT NULL,
    resource_type   TEXT NOT NULL,
    bag_value       INTEGER DEFAULT 0,
    total_value     INTEGER DEFAULT 0,
    bag_raw         TEXT DEFAULT '',
    total_raw       TEXT DEFAULT '',
    FOREIGN KEY (snapshot_id) REFERENCES scan_snapshots(id)
);

-- Macro script definitions
CREATE TABLE IF NOT EXISTS macros (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    filename        TEXT NOT NULL UNIQUE,
    display_name    TEXT DEFAULT '',
    resolution      TEXT DEFAULT '',
    duration_ms     INTEGER DEFAULT 0,
    file_path       TEXT DEFAULT '',
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Macro execution history
CREATE TABLE IF NOT EXISTS macro_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    macro_id        INTEGER NOT NULL,
    emulator_id     INTEGER NOT NULL,
    status          TEXT DEFAULT 'running',
    ops_completed   INTEGER DEFAULT 0,
    ops_total       INTEGER DEFAULT 0,
    error           TEXT DEFAULT '',
    started_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    finished_at     TEXT,
    FOREIGN KEY (macro_id)    REFERENCES macros(id),
    FOREIGN KEY (emulator_id) REFERENCES emulators(id)
);

-- Task execution history (v3)
CREATE TABLE IF NOT EXISTS task_runs (
    run_id          TEXT PRIMARY KEY,
    source_page     TEXT, 
    trigger_type    TEXT, 
    triggered_by    TEXT,
    target_id       INTEGER, 
    status          TEXT,
    started_at      TEXT, 
    ended_at        TEXT, 
    duration_ms     INTEGER,
    metadata_json   TEXT
);

-- Task execution steps (v3)
CREATE TABLE IF NOT EXISTS task_run_steps (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT, 
    step_index      INTEGER, 
    function_id     TEXT,
    input_json      TEXT, 
    output_json     TEXT, 
    status          TEXT,
    error_code      TEXT, 
    error_message   TEXT,
    started_at      TEXT, 
    ended_at        TEXT, 
    latency_ms      INTEGER,
    FOREIGN KEY (run_id) REFERENCES task_runs(run_id)
);

-- Audit logs (v3)
CREATE TABLE IF NOT EXISTS audit_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    actor           TEXT,
    action          TEXT,
    target_type     TEXT,
    target_id       INTEGER,
    before_json     TEXT,
    after_json      TEXT,
    reason          TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Account metadata (N:1 with emulators — multiple accounts per emulator)
CREATE TABLE IF NOT EXISTS accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id         TEXT NOT NULL UNIQUE,           -- In-game player ID (primary identity)
    emulator_id     INTEGER,                        -- FK → emulators.id (nullable)
    lord_name       TEXT DEFAULT '',                 -- Synced from latest scan
    login_method    TEXT DEFAULT '',
    email           TEXT DEFAULT '',
    provider        TEXT DEFAULT 'Global',
    alliance        TEXT DEFAULT '',
    note            TEXT DEFAULT '',
    is_active       INTEGER DEFAULT 0,              -- 1 = currently active on its emulator
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (emulator_id) REFERENCES emulators(id)
);

-- Pending accounts (discovered by scan but not yet confirmed by user)
CREATE TABLE IF NOT EXISTS pending_accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id         TEXT NOT NULL UNIQUE,
    emulator_id     INTEGER NOT NULL,
    lord_name       TEXT DEFAULT '',
    power           INTEGER DEFAULT 0,
    snapshot_id     INTEGER,
    status          TEXT DEFAULT 'pending',          -- pending/confirmed/dismissed
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (emulator_id) REFERENCES emulators(id),
    FOREIGN KEY (snapshot_id) REFERENCES scan_snapshots(id)
);

-- Scheduled macro jobs
CREATE TABLE IF NOT EXISTS schedules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    macro_filename  TEXT NOT NULL,
    schedule_type   TEXT DEFAULT 'once',
    schedule_value  TEXT DEFAULT '',
    target_mode     TEXT DEFAULT 'all_online',
    target_indices  TEXT DEFAULT '[]',
    is_enabled      INTEGER DEFAULT 1,
    last_run_at     TEXT,
    next_run_at     TEXT,
    run_count       INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Account Groups
CREATE TABLE IF NOT EXISTS account_groups (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    account_ids     TEXT DEFAULT '[]',
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_snap_emu_time ON scan_snapshots(emulator_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_res_snap ON scan_resources(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_taskrun_start ON task_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_taskrunsteps_run ON task_run_steps(run_id);
CREATE INDEX IF NOT EXISTS idx_macrorun_emu ON macro_runs(emulator_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_accounts_emu ON accounts(emulator_id);
CREATE INDEX IF NOT EXISTS idx_accounts_game_id ON accounts(game_id);
CREATE INDEX IF NOT EXISTS idx_snap_game_id ON scan_snapshots(game_id);
"""


# ──────────────────────────────────────────────
# Migration: v1 → v2
# ──────────────────────────────────────────────

def _check_v1_tables(conn: sqlite3.Connection) -> list[str]:
    """Return list of v1 table names that still exist."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN "
        "('emulator_data', 'scan_results', 'task_logs', 'emulator_sessions')"
    )
    return [row[0] for row in cursor.fetchall()]


def _migrate_v1_to_v2(conn: sqlite3.Connection):
    """Migrate data from v1 schema to v2 schema, then drop v1 tables."""
    v1_tables = _check_v1_tables(conn)
    if not v1_tables:
        return  # Nothing to migrate

    print("[DB Migration] Detected v1 tables, migrating to v2 schema...")

    # ── Migrate emulator_data → emulators + scan_snapshots + scan_resources ──
    if "emulator_data" in v1_tables:
        cursor = conn.execute("SELECT * FROM emulator_data ORDER BY created_at ASC")
        rows = cursor.fetchall()
        col_names = [desc[0] for desc in cursor.description]

        for row in rows:
            d = dict(zip(col_names, row))
            emu_index = d.get("emulator_index", 0)
            serial = d.get("serial", "")
            emu_name = d.get("emulator_name", "")

            # Upsert emulator
            conn.execute(
                """INSERT INTO emulators (emu_index, serial, name)
                   VALUES (?, ?, ?)
                   ON CONFLICT(emu_index) DO UPDATE SET
                     serial = excluded.serial,
                     name = excluded.name""",
                (emu_index, serial, emu_name),
            )

            # Get emulator_id
            emu_row = conn.execute(
                "SELECT id FROM emulators WHERE emu_index = ?", (emu_index,)
            ).fetchone()
            emu_id = emu_row[0] if emu_row else None
            if not emu_id:
                continue

            # Insert scan snapshot
            conn.execute(
                """INSERT INTO scan_snapshots
                   (emulator_id, scan_type, lord_name, power, hall_level,
                    market_level, pet_token, scan_status, duration_ms,
                    raw_ocr_text, created_at)
                   VALUES (?, 'full_scan', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    emu_id,
                    d.get("lord_name", ""),
                    d.get("power", 0),
                    d.get("hall_level", 0),
                    d.get("market_level", 0),
                    d.get("pet_token", 0),
                    d.get("scan_status", "completed"),
                    d.get("scan_duration_ms", 0),
                    d.get("raw_ocr_text", ""),
                    d.get("created_at", ""),
                ),
            )

            # Get snapshot_id
            snap_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

            # Insert resources
            for res_type in ("gold", "wood", "ore", "mana"):
                value = d.get(res_type, 0) or 0
                if value > 0:
                    conn.execute(
                        """INSERT INTO scan_resources
                           (snapshot_id, resource_type, bag_value, total_value)
                           VALUES (?, ?, ?, ?)""",
                        (snap_id, res_type, value, value),
                    )

        print(f"  -> Migrated {len(rows)} rows from emulator_data")

    # -- Migrate task_logs -> task_runs --
    if "task_logs" in v1_tables:
        cursor = conn.execute("SELECT * FROM task_logs ORDER BY created_at ASC")
        rows = cursor.fetchall()
        col_names = [desc[0] for desc in cursor.description]

        migrated = 0
        for row in rows:
            d = dict(zip(col_names, row))
            serial = d.get("serial", "")

            # Find or create emulator
            emu_row = conn.execute(
                "SELECT id FROM emulators WHERE serial = ?", (serial,)
            ).fetchone()

            if not emu_row:
                # Create placeholder emulator
                conn.execute(
                    "INSERT OR IGNORE INTO emulators (emu_index, serial, name) VALUES (?, ?, ?)",
                    (-1, serial, ""),
                )
                emu_row = conn.execute(
                    "SELECT id FROM emulators WHERE serial = ?", (serial,)
                ).fetchone()

            if not emu_row:
                continue

            emu_id = emu_row[0]
            conn.execute(
                """INSERT INTO task_runs
                   (emulator_id, task_type, status, error, duration_ms, started_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    emu_id,
                    d.get("task_type", ""),
                    d.get("status", ""),
                    d.get("error", ""),
                    d.get("duration_ms", 0),
                    d.get("created_at", ""),
                ),
            )
            migrated += 1

        print(f"  -> Migrated {migrated} rows from task_logs")

    # -- Drop old tables --
    for table in v1_tables:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
        print(f"  -> Dropped old table: {table}")

    conn.commit()
    print("[DB Migration] v1 -> v2 migration complete.")


def _migrate_v2_to_v3(conn: sqlite3.Connection):
    """Migrate from v2 to v3 schema (drops old task_runs)."""
    # Check if task_runs has 'emulator_id' column (v2 schema)
    cursor = conn.execute("PRAGMA table_info(task_runs)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "emulator_id" in columns:
        print("[DB Migration] Detected v2 task_runs schema, dropping for v3 migration...")
        conn.execute("DROP TABLE IF EXISTS task_runs")
        # Re-run CREATE_TABLES_SQL to recreate properly
        conn.executescript(CREATE_TABLES_SQL)
        conn.commit()
        print("[DB Migration] v2 -> v3 migration complete.")# ──────────────────────────────────────────────
# Database class
# ──────────────────────────────────────────────

class Database:
    """Async SQLite database wrapper with normalized schema."""

    def __init__(self):
        self.db_path = config.db_path
        self._initialized = False

    def init_sync(self):
        """Initialize database synchronously (for startup)."""
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")

        # Create tables (IF NOT EXISTS is safe)
        conn.executescript(CREATE_TABLES_SQL)

        # Migrate v1 data if needed
        _migrate_v1_to_v2(conn)
        _migrate_v2_to_v3(conn)

        conn.close()
        self._initialized = True
        print(f"[DB] Initialized at {self.db_path}")

    def _get_conn(self):
        return aiosqlite.connect(self.db_path)

    # ──────────────────────────────────────────
    # Emulators
    # ──────────────────────────────────────────

    async def get_emulator_id(self, emu_index: int) -> int | None:
        """Get emulator DB id by emu_index."""
        async with self._get_conn() as db:
            cursor = await db.execute(
                "SELECT id FROM emulators WHERE emu_index = ?", (emu_index,)
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def upsert_emulator(
        self, emu_index: int, serial: str, name: str = "",
        resolution: str = "960x540", status: str = "ONLINE"
    ) -> int:
        """Insert or update an emulator. Returns emulator id."""
        async with self._get_conn() as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await db.execute(
                """INSERT INTO emulators (emu_index, serial, name, resolution, status, last_seen_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(emu_index) DO UPDATE SET
                     serial = excluded.serial,
                     name = CASE WHEN excluded.name != '' THEN excluded.name ELSE emulators.name END,
                     resolution = excluded.resolution,
                     status = excluded.status,
                     last_seen_at = excluded.last_seen_at""",
                (emu_index, serial, name, resolution, status,
                 datetime.now().isoformat()),
            )
            await db.commit()

            cursor = await db.execute(
                "SELECT id FROM emulators WHERE emu_index = ?", (emu_index,)
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_emulator_id(self, emu_index: int = None,
                               serial: str = None) -> int | None:
        """Get emulator DB id by index or serial."""
        async with self._get_conn() as db:
            if emu_index is not None:
                cursor = await db.execute(
                    "SELECT id FROM emulators WHERE emu_index = ?", (emu_index,)
                )
            elif serial:
                cursor = await db.execute(
                    "SELECT id FROM emulators WHERE serial = ?", (serial,)
                )
            else:
                return None
            row = await cursor.fetchone()
            return row[0] if row else None

    async def get_all_emulators(self) -> list[dict]:
        """Get all registered emulators."""
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM emulators ORDER BY emu_index"
            )
            return [dict(row) for row in await cursor.fetchall()]

    async def update_emulator_status(self, emu_index: int, status: str):
        """Update emulator status."""
        async with self._get_conn() as db:
            await db.execute(
                "UPDATE emulators SET status = ?, last_seen_at = ? WHERE emu_index = ?",
                (status, datetime.now().isoformat(), emu_index),
            )
            await db.commit()

    # ──────────────────────────────────────────
    # Scan Snapshots
    # ──────────────────────────────────────────

    async def save_scan_snapshot(
        self,
        emulator_index: int,
        serial: str,
        emulator_name: str,
        parsed_data: dict,
        scan_type: str = "full_scan",
        scan_status: str = "completed",
        scan_duration_ms: int = 0,
        raw_ocr_text: str = "",
        game_id: str = "",
    ) -> int:
        """Save scan snapshot + resources. Returns snapshot id."""
        # Ensure emulator exists
        emu_id = await self.upsert_emulator(emulator_index, serial, emulator_name)

        async with self._get_conn() as db:
            await db.execute("PRAGMA foreign_keys = ON")

            # Insert snapshot
            cursor = await db.execute(
                """INSERT INTO scan_snapshots
                   (emulator_id, scan_type, lord_name, power, hall_level,
                    market_level, pet_token, scan_status, duration_ms, raw_ocr_text, game_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    emu_id,
                    scan_type,
                    parsed_data.get("lord_name", ""),
                    parsed_data.get("power", 0),
                    parsed_data.get("hall_level", 0),
                    parsed_data.get("market_level", 0),
                    parsed_data.get("pet_token", 0),
                    scan_status,
                    scan_duration_ms,
                    raw_ocr_text,
                    game_id,
                ),
            )

            snap_id = cursor.lastrowid

            # Insert resources
            resources = parsed_data.get("resources", {})
            for res_type in ("gold", "wood", "ore", "mana"):
                res_data = resources.get(res_type, {})
                if isinstance(res_data, dict):
                    bag = res_data.get("bag", 0) or 0
                    total = res_data.get("total", 0) or 0
                    bag_raw = res_data.get("bag_raw", "")
                    total_raw = res_data.get("total_raw", "")
                elif isinstance(res_data, (int, float)):
                    bag = int(res_data)
                    total = int(res_data)
                    bag_raw = ""
                    total_raw = ""
                else:
                    continue

                if bag > 0 or total > 0:
                    await db.execute(
                        """INSERT INTO scan_resources
                           (snapshot_id, resource_type, bag_value, total_value,
                            bag_raw, total_raw)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (snap_id, res_type, bag, total, bag_raw, total_raw),
                    )

            await db.commit()
            return snap_id

    async def get_emulator_data(self, serial: str = None,
                                 emulator_index: int = None) -> dict | None:
        """Get latest scan data for a specific emulator.
        Returns data in a format compatible with the old emulator_data table.
        """
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row

            if serial:
                cursor = await db.execute(
                    """SELECT s.*, e.emu_index as emulator_index, e.serial, e.name as emulator_name
                       FROM scan_snapshots s
                       JOIN emulators e ON s.emulator_id = e.id
                       WHERE e.serial = ?
                       ORDER BY s.created_at DESC LIMIT 1""",
                    (serial,),
                )
            elif emulator_index is not None:
                cursor = await db.execute(
                    """SELECT s.*, e.emu_index as emulator_index, e.serial, e.name as emulator_name
                       FROM scan_snapshots s
                       JOIN emulators e ON s.emulator_id = e.id
                       WHERE e.emu_index = ?
                       ORDER BY s.created_at DESC LIMIT 1""",
                    (emulator_index,),
                )
            else:
                return None

            row = await cursor.fetchone()
            if not row:
                return None

            result = dict(row)

            # Attach resources
            snap_id = result["id"]
            res_cursor = await db.execute(
                "SELECT * FROM scan_resources WHERE snapshot_id = ?",
                (snap_id,),
            )
            res_rows = await res_cursor.fetchall()
            for res in res_rows:
                res_dict = dict(res)
                rtype = res_dict["resource_type"]
                result[rtype] = res_dict.get("bag_value", 0)
                result[f"{rtype}_total"] = res_dict.get("total_value", 0)
                result[f"{rtype}_bag_raw"] = res_dict.get("bag_raw", "")
                result[f"{rtype}_total_raw"] = res_dict.get("total_raw", "")

            return result

    async def get_all_emulator_data(self) -> list[dict]:
        """Get latest scan data for ALL emulators (one row per emulator)."""
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT s.*, e.emu_index as emulator_index, e.serial, e.name as emulator_name
                   FROM scan_snapshots s
                   JOIN emulators e ON s.emulator_id = e.id
                   WHERE s.id IN (
                       SELECT MAX(s2.id) FROM scan_snapshots s2
                       GROUP BY s2.emulator_id
                   )
                   ORDER BY e.emu_index""",
            )
            rows = await cursor.fetchall()

            results = []
            for row in rows:
                result = dict(row)
                snap_id = result["id"]
                res_cursor = await db.execute(
                    "SELECT * FROM scan_resources WHERE snapshot_id = ?",
                    (snap_id,),
                )
                for res in await res_cursor.fetchall():
                    res_dict = dict(res)
                    rtype = res_dict["resource_type"]
                    result[rtype] = res_dict.get("bag_value", 0)
                    result[f"{rtype}_total"] = res_dict.get("total_value", 0)
                results.append(result)

            return results

    async def get_emulator_scan_history(self, emulator_index: int,
                                         limit: int = 20) -> list[dict]:
        """Get scan history for a specific emulator."""
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT s.*, e.emu_index as emulator_index, e.serial, e.name as emulator_name
                   FROM scan_snapshots s
                   JOIN emulators e ON s.emulator_id = e.id
                   WHERE e.emu_index = ?
                   ORDER BY s.created_at DESC LIMIT ?""",
                (emulator_index, limit),
            )
            rows = await cursor.fetchall()

            results = []
            for row in rows:
                result = dict(row)
                snap_id = result["id"]
                res_cursor = await db.execute(
                    "SELECT * FROM scan_resources WHERE snapshot_id = ?",
                    (snap_id,),
                )
                for res in await res_cursor.fetchall():
                    res_dict = dict(res)
                    rtype = res_dict["resource_type"]
                    result[rtype] = res_dict.get("bag_value", 0)
                    result[f"{rtype}_total"] = res_dict.get("total_value", 0)
                results.append(result)

            return results

    async def get_scan_comparison(self, game_id: str) -> dict:
        """Get latest scan vs scan from 24h+ ago for delta comparison.

        Returns: {
            "current": {...snapshot},
            "previous": {...snapshot or None},
            "delta": {...computed deltas}
        }
        """
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row

            # 1. Get the LATEST scan for this game_id
            cursor = await db.execute(
                """SELECT s.*, e.emu_index, e.serial, e.name as emulator_name
                   FROM scan_snapshots s
                   JOIN emulators e ON s.emulator_id = e.id
                   WHERE s.game_id = ?
                   ORDER BY s.created_at DESC LIMIT 1""",
                (game_id,),
            )
            latest_row = await cursor.fetchone()
            if not latest_row:
                return {"current": None, "previous": None, "delta": None}

            current = dict(latest_row)
            latest_time = current.get("created_at", "")

            # Attach resources to current
            res_cursor = await db.execute(
                "SELECT * FROM scan_resources WHERE snapshot_id = ?",
                (current["id"],),
            )
            for res in await res_cursor.fetchall():
                rd = dict(res)
                rtype = rd["resource_type"]
                current[rtype] = rd.get("bag_value", 0)
                current[f"{rtype}_total"] = rd.get("total_value", 0)

            # 2. Get the closest scan that is AT LEAST 24h older
            cursor2 = await db.execute(
                """SELECT s.*, e.emu_index, e.serial, e.name as emulator_name
                   FROM scan_snapshots s
                   JOIN emulators e ON s.emulator_id = e.id
                   WHERE s.game_id = ?
                     AND datetime(s.created_at) <= datetime(?, '-24 hours')
                   ORDER BY s.created_at DESC LIMIT 1""",
                (game_id, latest_time),
            )
            prev_row = await cursor2.fetchone()

            previous = None
            delta = None

            if prev_row:
                previous = dict(prev_row)

                # Attach resources to previous
                res_cursor2 = await db.execute(
                    "SELECT * FROM scan_resources WHERE snapshot_id = ?",
                    (previous["id"],),
                )
                for res in await res_cursor2.fetchall():
                    rd = dict(res)
                    rtype = rd["resource_type"]
                    previous[rtype] = rd.get("bag_value", 0)
                    previous[f"{rtype}_total"] = rd.get("total_value", 0)

                # 3. Compute deltas
                delta = {
                    "power": (current.get("power", 0) or 0) - (previous.get("power", 0) or 0),
                    "hall_level": (current.get("hall_level", 0) or 0) - (previous.get("hall_level", 0) or 0),
                    "market_level": (current.get("market_level", 0) or 0) - (previous.get("market_level", 0) or 0),
                    "pet_token": (current.get("pet_token", 0) or 0) - (previous.get("pet_token", 0) or 0),
                    "gold": (current.get("gold", 0) or 0) - (previous.get("gold", 0) or 0),
                    "wood": (current.get("wood", 0) or 0) - (previous.get("wood", 0) or 0),
                    "ore": (current.get("ore", 0) or 0) - (previous.get("ore", 0) or 0),
                    "mana": (current.get("mana", 0) or 0) - (previous.get("mana", 0) or 0),
                    "previous_scan_at": previous.get("created_at", ""),
                }

            return {"current": current, "previous": previous, "delta": delta}

    #
    # Legacy-compatible methods (scan_results)
    # ──────────────────────────────────────────

    async def save_scan_result(self, serial, task_type, status, data,
                                is_reliable, validation_errors, duration_ms):
        """Legacy method — saves as a task_run + scan_snapshot if applicable."""
        emu_id = await self.get_emulator_id(serial=serial)
        if not emu_id:
            # Auto-register emulator
            emu_id = await self.upsert_emulator(-1, serial, "")

        async with self._get_conn() as db:
            await db.execute(
                """INSERT INTO task_runs
                   (emulator_id, task_type, status, result_json, duration_ms)
                   VALUES (?, ?, ?, ?, ?)""",
                (emu_id, task_type, status,
                 json.dumps(data, default=str), duration_ms),
            )
            await db.commit()

    async def save_task_log(self, task_id, serial, task_type, status,
                             error=None, duration_ms=0):
        """Legacy method — saves as task_run."""
        emu_id = await self.get_emulator_id(serial=serial)
        if not emu_id:
            emu_id = await self.upsert_emulator(-1, serial, "")

        async with self._get_conn() as db:
            await db.execute(
                """INSERT INTO task_runs
                   (emulator_id, task_type, status, error, duration_ms)
                   VALUES (?, ?, ?, ?, ?)""",
                (emu_id, task_type, status, error or "", duration_ms),
            )
            await db.commit()

    async def get_scan_history(self, limit=50, serial=None) -> list[dict]:
        """Get scan snapshot history (replaces old scan_results query)."""
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row
            if serial:
                cursor = await db.execute(
                    """SELECT s.*, e.serial, e.name as emulator_name
                       FROM scan_snapshots s
                       JOIN emulators e ON s.emulator_id = e.id
                       WHERE e.serial = ?
                       ORDER BY s.created_at DESC LIMIT ?""",
                    (serial, limit),
                )
            else:
                cursor = await db.execute(
                    """SELECT s.*, e.serial, e.name as emulator_name
                       FROM scan_snapshots s
                       JOIN emulators e ON s.emulator_id = e.id
                       ORDER BY s.created_at DESC LIMIT ?""",
                    (limit,),
                )
            rows = await cursor.fetchall()

            results = []
            for row in rows:
                d = dict(row)
                # Attach resources
                snap_id = d["id"]
                res_cursor = await db.execute(
                    "SELECT * FROM scan_resources WHERE snapshot_id = ?",
                    (snap_id,),
                )
                res_data = {}
                for res in await res_cursor.fetchall():
                    res_dict = dict(res)
                    rtype = res_dict["resource_type"]
                    res_data[rtype] = {
                        "bag": res_dict.get("bag_value", 0),
                        "total": res_dict.get("total_value", 0),
                    }

                d["data"] = {
                    "lord_name": d.get("lord_name", ""),
                    "power": d.get("power", 0),
                    "hall_level": d.get("hall_level", 0),
                    "market_level": d.get("market_level", 0),
                    "pet_token": d.get("pet_token", 0),
                    "resources": res_data,
                }
                d["validation_errors"] = []
                results.append(d)

            return results

    async def get_task_logs(self, limit=100) -> list[dict]:
        """Get task execution history."""
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT t.*, e.serial, e.name as emulator_name
                   FROM task_runs t
                   JOIN emulators e ON t.emulator_id = e.id
                   ORDER BY t.started_at DESC LIMIT ?""",
                (limit,),
            )
            return [dict(row) for row in await cursor.fetchall()]

    async def get_latest_report(self, serial: str) -> dict | None:
        """Get the latest scan snapshot for a device."""
        result = await self.get_emulator_data(serial=serial)
        if result:
            # Build compatible response
            result["data"] = {
                "lord_name": result.get("lord_name", ""),
                "power": result.get("power", 0),
                "hall_level": result.get("hall_level", 0),
                "market_level": result.get("market_level", 0),
                "pet_token": result.get("pet_token", 0),
                "resources": {
                    rtype: result.get(rtype, 0)
                    for rtype in ("gold", "wood", "ore", "mana")
                },
            }
        return result

    # ──────────────────────────────────────────
    # Macro Runs
    # ──────────────────────────────────────────

    async def upsert_macro(
        self, filename: str, display_name: str = "",
        resolution: str = "", duration_ms: int = 0,
        file_path: str = ""
    ) -> int:
        """Insert or update a macro definition. Returns macro id."""
        async with self._get_conn() as db:
            await db.execute(
                """INSERT INTO macros (filename, display_name, resolution, duration_ms, file_path)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(filename) DO UPDATE SET
                     display_name = CASE WHEN excluded.display_name != '' THEN excluded.display_name ELSE macros.display_name END,
                     resolution = CASE WHEN excluded.resolution != '' THEN excluded.resolution ELSE macros.resolution END,
                     duration_ms = CASE WHEN excluded.duration_ms > 0 THEN excluded.duration_ms ELSE macros.duration_ms END,
                     file_path = CASE WHEN excluded.file_path != '' THEN excluded.file_path ELSE macros.file_path END""",
                (filename, display_name, resolution, duration_ms, file_path),
            )
            await db.commit()

            cursor = await db.execute(
                "SELECT id FROM macros WHERE filename = ?", (filename,)
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def save_macro_run(
        self, macro_id: int, emulator_id: int,
        status: str = "running", ops_total: int = 0
    ) -> int:
        """Create a new macro run record. Returns run id."""
        async with self._get_conn() as db:
            cursor = await db.execute(
                """INSERT INTO macro_runs
                   (macro_id, emulator_id, status, ops_total)
                   VALUES (?, ?, ?, ?)""",
                (macro_id, emulator_id, status, ops_total),
            )
            await db.commit()
            return cursor.lastrowid

    async def update_macro_run(
        self, run_id: int, status: str = None,
        ops_completed: int = None, error: str = None,
        finished_at: str = None
    ):
        """Update a macro run record."""
        updates = []
        params = []
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if ops_completed is not None:
            updates.append("ops_completed = ?")
            params.append(ops_completed)
        if error is not None:
            updates.append("error = ?")
            params.append(error)
        if finished_at is not None:
            updates.append("finished_at = ?")
            params.append(finished_at)

        if not updates:
            return

        params.append(run_id)
        async with self._get_conn() as db:
            await db.execute(
                f"UPDATE macro_runs SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            await db.commit()

    async def get_macro_runs(self, emulator_index: int = None,
                              limit: int = 50) -> list[dict]:
        """Get macro execution history."""
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row
            if emulator_index is not None:
                cursor = await db.execute(
                    """SELECT mr.*, m.filename, m.display_name,
                              e.emu_index, e.serial, e.name as emulator_name
                       FROM macro_runs mr
                       JOIN macros m ON mr.macro_id = m.id
                       JOIN emulators e ON mr.emulator_id = e.id
                       WHERE e.emu_index = ?
                       ORDER BY mr.started_at DESC LIMIT ?""",
                    (emulator_index, limit),
                )
            else:
                cursor = await db.execute(
                    """SELECT mr.*, m.filename, m.display_name,
                              e.emu_index, e.serial, e.name as emulator_name
                       FROM macro_runs mr
                       JOIN macros m ON mr.macro_id = m.id
                       JOIN emulators e ON mr.emulator_id = e.id
                       ORDER BY mr.started_at DESC LIMIT ?""",
                    (limit,),
                )
            return [dict(row) for row in await cursor.fetchall()]

    # ──────────────────────────────────────────
    # Task Runs
    # ──────────────────────────────────────────

    async def save_task_run(
        self, emulator_id: int, task_type: str,
        status: str = "queued"
    ) -> int | str:
        """Create a new task run record. Returns run id (int for v2, str for v3)."""
        async with self._get_conn() as db:
            schema_cursor = await db.execute("PRAGMA table_info(task_runs)")
            cols = {row[1] for row in await schema_cursor.fetchall()}

            # Legacy schema compatibility
            if {"emulator_id", "task_type", "status"}.issubset(cols):
                cursor = await db.execute(
                    """INSERT INTO task_runs (emulator_id, task_type, status)
                       VALUES (?, ?, ?)""",
                    (emulator_id, task_type, status),
                )
                await db.commit()
                return cursor.lastrowid

            # v3 schema compatibility
            import uuid
            run_id = str(uuid.uuid4())
            meta = {"task_type": task_type, "emulator_id": emulator_id}
            await db.execute(
                """INSERT INTO task_runs (
                       run_id, source_page, trigger_type, triggered_by, target_id,
                       status, started_at, duration_ms, metadata_json
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    "task",
                    "manual",
                    "task_queue",
                    emulator_id,
                    str(status or "queued").upper(),
                    datetime.now().isoformat(),
                    0,
                    json.dumps(meta),
                ),
            )
            await db.commit()
            return run_id

    async def update_task_run(
        self, run_id: int | str, status: str = None,
        error: str = None, duration_ms: int = None,
        result_json: str = None, finished_at: str = None
    ):
        """Update a task run record."""
        async with self._get_conn() as db:
            schema_cursor = await db.execute("PRAGMA table_info(task_runs)")
            cols = {row[1] for row in await schema_cursor.fetchall()}

            # Legacy schema compatibility
            if {"id", "status"}.issubset(cols):
                updates = []
                params = []
                if status is not None:
                    updates.append("status = ?")
                    params.append(status)
                if error is not None:
                    updates.append("error = ?")
                    params.append(error)
                if duration_ms is not None:
                    updates.append("duration_ms = ?")
                    params.append(duration_ms)
                if result_json is not None:
                    updates.append("result_json = ?")
                    params.append(result_json)
                if finished_at is not None:
                    updates.append("finished_at = ?")
                    params.append(finished_at)
                if not updates:
                    return
                params.append(run_id)
                set_clause = ", ".join(updates)
                await db.execute(
                    f"UPDATE task_runs SET {set_clause} WHERE id = ?",
                    params,
                )
                await db.commit()
                return

            # v3 schema compatibility
            current_meta = {}
            if "metadata_json" in cols:
                cur = await db.execute(
                    "SELECT metadata_json FROM task_runs WHERE run_id = ?",
                    (str(run_id),),
                )
                row = await cur.fetchone()
                if row and row[0]:
                    try:
                        current_meta = json.loads(row[0])
                    except Exception:
                        current_meta = {}

            if error is not None:
                current_meta["error"] = error
            if result_json is not None:
                current_meta["result_json"] = result_json

            updates = []
            params = []
            if status is not None:
                updates.append("status = ?")
                params.append(str(status).upper())
            if duration_ms is not None:
                updates.append("duration_ms = ?")
                params.append(duration_ms)
            if finished_at is not None:
                ended_col = "ended_at" if "ended_at" in cols else "finished_at"
                updates.append(f"{ended_col} = ?")
                params.append(finished_at)
            if "metadata_json" in cols:
                updates.append("metadata_json = ?")
                params.append(json.dumps(current_meta, default=str))

            if not updates:
                return

            params.append(str(run_id))
            set_clause = ", ".join(updates)
            await db.execute(
                f"UPDATE task_runs SET {set_clause} WHERE run_id = ?",
                params,
            )
            await db.commit()

    async def get_task_history(self, limit: int = 200) -> list[dict]:
        """Get unified task execution history from task_runs + scan_snapshots."""
        results = list(await self.get_task_runs(limit=limit))
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row

            # Query scan_snapshots (full scans not routed through task_queue)
            cursor2 = await db.execute(
                """SELECT s.id, 'full_scan' as task_type,
                          CASE WHEN s.scan_status = 'completed' THEN 'success'
                               WHEN s.scan_status = 'failed' THEN 'failed'
                               ELSE s.scan_status END as status,
                          '' as error, s.duration_ms,
                          '' as result_json, s.created_at as started_at,
                          s.created_at as finished_at,
                          e.serial, e.name as emu_name, e.emu_index,
                          s.lord_name, s.power, s.hall_level, s.market_level,
                          s.game_id
                   FROM scan_snapshots s
                   LEFT JOIN emulators e ON s.emulator_id = e.id
                   ORDER BY s.created_at DESC
                   LIMIT ?""",
                (limit,),
            )
            scan_rows = await cursor2.fetchall()

            # Process scan_snapshots (avoid duplicates - skip if same timestamp+serial exists in tasks)
            task_keys = set()
            for r in results:
                task_keys.add(f"{r.get('serial','')}-{r.get('started_at','')}")

            for row in scan_rows:
                r = dict(row)
                key = f"{r.get('serial','')}-{r.get('started_at','')}"
                if key in task_keys:
                    continue
                r["source"] = "full_scan"
                # Build data summary for scan
                r["result_json"] = ""
                data = {}
                if r.get("lord_name"):
                    data["lord_name"] = r["lord_name"]
                if r.get("power"):
                    data["power"] = r["power"]
                if r.get("hall_level"):
                    data["hall_level"] = r["hall_level"]
                if r.get("market_level"):
                    data["market_level"] = r["market_level"]
                if r.get("game_id"):
                    data["game_id"] = r["game_id"]
                if data:
                    r["result_json"] = json.dumps(data)
                results.append(r)

            # Sort all by started_at descending
            results.sort(key=lambda x: x.get("started_at", "") or "", reverse=True)
            return results[:limit]

    async def get_task_runs(self, emulator_index: int = None,
                             limit: int = 50) -> list[dict]:
        """Get task execution history."""
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row
            schema_cursor = await db.execute("PRAGMA table_info(task_runs)")
            cols = {row[1] for row in await schema_cursor.fetchall()}

            # Legacy schema (with emulator_id/task_type/etc.)
            if "emulator_id" in cols:
                if emulator_index is not None:
                    cursor = await db.execute(
                        """SELECT t.*, e.serial, e.emu_index, e.name as emulator_name
                           FROM task_runs t
                           JOIN emulators e ON t.emulator_id = e.id
                           WHERE e.emu_index = ?
                           ORDER BY t.started_at DESC LIMIT ?""",
                        (emulator_index, limit),
                    )
                else:
                    cursor = await db.execute(
                        """SELECT t.*, e.serial, e.emu_index, e.name as emulator_name
                           FROM task_runs t
                           JOIN emulators e ON t.emulator_id = e.id
                           ORDER BY t.started_at DESC LIMIT ?""",
                        (limit,),
                    )
                rows = [dict(row) for row in await cursor.fetchall()]
                for row in rows:
                    row["source"] = row.get("source") or "task_queue"
                    row["emu_name"] = row.get("emu_name") or row.get("emulator_name", "")
                return rows

            # v3 schema
            ended_col = "ended_at" if "ended_at" in cols else "finished_at"
            if emulator_index is not None:
                cursor = await db.execute(
                    f"""SELECT t.run_id, t.source_page, t.trigger_type, t.triggered_by,
                               t.target_id, t.status, t.started_at, t.{ended_col} as finished_at,
                               t.duration_ms, t.metadata_json,
                               e.serial, e.emu_index, e.name as emulator_name
                        FROM task_runs t
                        LEFT JOIN emulators e ON t.target_id = e.id
                        WHERE e.emu_index = ?
                        ORDER BY t.started_at DESC LIMIT ?""",
                    (emulator_index, limit),
                )
            else:
                cursor = await db.execute(
                    f"""SELECT t.run_id, t.source_page, t.trigger_type, t.triggered_by,
                               t.target_id, t.status, t.started_at, t.{ended_col} as finished_at,
                               t.duration_ms, t.metadata_json,
                               e.serial, e.emu_index, e.name as emulator_name
                        FROM task_runs t
                        LEFT JOIN emulators e ON t.target_id = e.id
                        ORDER BY t.started_at DESC LIMIT ?""",
                    (limit,),
                )
            rows = await cursor.fetchall()
            results = []
            for row in rows:
                d = dict(row)
                meta = {}
                if d.get("metadata_json"):
                    try:
                        meta = json.loads(d["metadata_json"])
                    except Exception:
                        meta = {}
                results.append({
                    "id": d.get("run_id"),
                    "task_type": meta.get("task_type") or d.get("source_page") or "workflow",
                    "status": d.get("status", ""),
                    "error": meta.get("error", ""),
                    "duration_ms": d.get("duration_ms", 0),
                    "result_json": meta.get("result_json", ""),
                    "started_at": d.get("started_at"),
                    "finished_at": d.get("finished_at"),
                    "serial": d.get("serial") or meta.get("serial", ""),
                    "emu_name": d.get("emulator_name") or meta.get("emu_name", ""),
                    "emu_index": d.get("emu_index"),
                    "source": d.get("source_page") or "workflow",
                })
            return results

    async def upsert_account(
        self, game_id: str, emulator_id: int = None,
        lord_name: str = "", login_method: str = "",
        email: str = "", provider: str = "Global",
        alliance: str = "", note: str = "",
        is_active: int = 0,
    ) -> int:
        """Insert or update account by game_id. Returns account id."""
        now = datetime.now().isoformat()
        async with self._get_conn() as db:
            cursor = await db.execute(
                """INSERT INTO accounts
                   (game_id, emulator_id, lord_name, login_method, email, provider, alliance, note, is_active, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(game_id) DO UPDATE SET
                       emulator_id = COALESCE(excluded.emulator_id, accounts.emulator_id),
                       lord_name = CASE WHEN excluded.lord_name != '' THEN excluded.lord_name ELSE accounts.lord_name END,
                       login_method = CASE WHEN excluded.login_method != '' THEN excluded.login_method ELSE accounts.login_method END,
                       email = CASE WHEN excluded.email != '' THEN excluded.email ELSE accounts.email END,
                       provider = excluded.provider,
                       alliance = CASE WHEN excluded.alliance != '' THEN excluded.alliance ELSE accounts.alliance END,
                       note = CASE WHEN excluded.note != '' THEN excluded.note ELSE accounts.note END,
                       is_active = excluded.is_active,
                       updated_at = excluded.updated_at""",
                (game_id, emulator_id, lord_name, login_method, email, provider, alliance, note, is_active, now),
            )
            await db.commit()
            # Get the actual id (lastrowid returns 0 on conflict update)
            id_cur = await db.execute("SELECT id FROM accounts WHERE game_id = ?", (game_id,))
            row = await id_cur.fetchone()
            return row[0] if row else cursor.lastrowid

    async def upsert_account_full(
        self, game_id: str, emulator_index: int = None,
        lord_name: str = "", power: float = 0,
        login_method: str = "", email: str = "", provider: str = "Global",
        alliance: str = "", note: str = "",
    ) -> int:
        """Create/update account with game_id and optionally create a manual scan snapshot."""
        emu_id = None
        serial = ""
        name = ""
        if emulator_index is not None:
            emu_id = await self.get_emulator_id(emu_index=emulator_index)
            serial = f"emulator-{5554 + emulator_index * 2}"
            name = f"LDPlayer-{emulator_index:02d}"
            if not emu_id:
                emu_id = await self.upsert_emulator(
                    emu_index=emulator_index, serial=serial, name=name
                )

        acc_id = await self.upsert_account(
            game_id=game_id,
            emulator_id=emu_id,
            lord_name=lord_name,
            login_method=login_method,
            email=email,
            provider=provider,
            alliance=alliance,
            note=note,
            is_active=1 if emu_id else 0,
        )

        # Create a manual scan snapshot if we have emulator info
        if emulator_index is not None:
            await self.save_scan_snapshot(
                emulator_index=emulator_index,
                serial=serial,
                emulator_name=name,
                parsed_data={"lord_name": lord_name, "power": power},
                scan_type="manual_account_creation",
                scan_status="completed",
                game_id=game_id,
            )

        return acc_id

    async def auto_link_account(
        self, emulator_id: int, game_id: str,
        lord_name: str = "", snapshot_id: int = 0,
    ) -> dict:
        """After a scan, link game_id to accounts or create pending.
        Returns {"action": "linked"|"pending", "account_id"|"pending_id": int}"""
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row

            # Check if game_id exists in accounts
            cursor = await db.execute(
                "SELECT id FROM accounts WHERE game_id = ?", (game_id,)
            )
            existing = await cursor.fetchone()

            if existing:
                # Known account — update active flags
                now = datetime.now().isoformat()
                # Set this account as active on this emulator
                await db.execute(
                    """UPDATE accounts SET
                        emulator_id = ?, is_active = 1,
                        lord_name = CASE WHEN ? != '' THEN ? ELSE lord_name END,
                        updated_at = ?
                       WHERE game_id = ?""",
                    (emulator_id, lord_name, lord_name, now, game_id),
                )
                # Deactivate other accounts on same emulator
                await db.execute(
                    "UPDATE accounts SET is_active = 0 WHERE emulator_id = ? AND game_id != ?",
                    (emulator_id, game_id),
                )
                await db.commit()
                return {"action": "linked", "account_id": existing["id"]}
            else:
                # Unknown account — check pending (dismissed ones should reappear)
                await db.execute(
                    "DELETE FROM pending_accounts WHERE game_id = ? AND status = 'dismissed'",
                    (game_id,)
                )
                # Insert or update pending
                cursor = await db.execute(
                    """INSERT INTO pending_accounts (game_id, emulator_id, lord_name, power, snapshot_id, status)
                       VALUES (?, ?, ?, 0, ?, 'pending')
                       ON CONFLICT(game_id) DO UPDATE SET
                           emulator_id = excluded.emulator_id,
                           lord_name = excluded.lord_name,
                           snapshot_id = excluded.snapshot_id,
                           status = 'pending'""",
                    (game_id, emulator_id, lord_name, snapshot_id),
                )
                await db.commit()
                pid_cur = await db.execute(
                    "SELECT id FROM pending_accounts WHERE game_id = ?", (game_id,)
                )
                prow = await pid_cur.fetchone()
                return {"action": "pending", "pending_id": prow["id"] if prow else 0}

    def _attach_scan_defaults(self, acc: dict):
        """Set default scan fields on an account dict."""
        acc.setdefault("lord_name", acc.get("acc_lord_name", ""))
        acc["power"] = acc.get("power", 0)
        acc["hall_level"] = acc.get("hall_level", 0)
        acc["market_level"] = acc.get("market_level", 0)
        acc["pet_token"] = acc.get("pet_token", 0)
        acc["last_scan_at"] = acc.get("last_scan_at", "")

    async def get_all_accounts(self) -> list[dict]:
        """Get all accounts with emulator info + latest scan data + resources."""
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row

            cursor = await db.execute(
                """SELECT
                       a.id as account_id, a.game_id,
                       a.lord_name as acc_lord_name,
                       a.login_method, a.email, a.provider, a.alliance, a.note,
                       a.is_active,
                       a.created_at as account_created_at, a.updated_at,
                       e.id as emulator_db_id, e.emu_index, e.serial, e.name as emu_name,
                       e.status as emu_status, e.last_seen_at
                   FROM accounts a
                   LEFT JOIN emulators e ON a.emulator_id = e.id
                   ORDER BY a.is_active DESC, e.emu_index, a.game_id"""
            )
            accounts = [dict(row) for row in await cursor.fetchall()]

            for acc in accounts:
                game_id = acc["game_id"]

                # Try to find latest scan by game_id first, fallback to emulator_id
                scan_row = None
                if game_id:
                    scan_cur = await db.execute(
                        """SELECT * FROM scan_snapshots
                           WHERE game_id = ?
                           ORDER BY created_at DESC LIMIT 1""",
                        (game_id,),
                    )
                    scan_row = await scan_cur.fetchone()

                if not scan_row and acc.get("emulator_db_id"):
                    scan_cur = await db.execute(
                        """SELECT * FROM scan_snapshots
                           WHERE emulator_id = ?
                           ORDER BY created_at DESC LIMIT 1""",
                        (acc["emulator_db_id"],),
                    )
                    scan_row = await scan_cur.fetchone()

                if scan_row:
                    scan = dict(scan_row)
                    acc["lord_name"] = scan.get("lord_name", "") or acc.get("acc_lord_name", "")
                    acc["power"] = scan.get("power", 0)
                    acc["hall_level"] = scan.get("hall_level", 0)
                    acc["market_level"] = scan.get("market_level", 0)
                    acc["pet_token"] = scan.get("pet_token", 0)
                    acc["scan_status"] = scan.get("scan_status", "")
                    acc["last_scan_at"] = scan.get("created_at", "")
                    acc["scan_id"] = scan["id"]

                    res_cur = await db.execute(
                        "SELECT * FROM scan_resources WHERE snapshot_id = ?",
                        (scan["id"],),
                    )
                    for res in await res_cur.fetchall():
                        rd = dict(res)
                        rtype = rd["resource_type"]
                        acc[rtype] = rd.get("bag_value", 0)
                        acc[f"{rtype}_total"] = rd.get("total_value", 0)
                else:
                    acc["lord_name"] = acc.get("acc_lord_name", "")
                    acc["power"] = 0
                    acc["hall_level"] = 0
                    acc["market_level"] = 0
                    acc["pet_token"] = 0
                    acc["last_scan_at"] = ""

                # Clean up internal key
                acc.pop("acc_lord_name", None)

            return accounts

    async def get_account_by_game_id(self, game_id: str) -> dict | None:
        """Get single account by game_id with full scan data."""
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT
                       a.id as account_id, a.game_id,
                       a.lord_name as acc_lord_name,
                       a.login_method, a.email, a.provider, a.alliance, a.note,
                       a.is_active,
                       a.created_at as account_created_at, a.updated_at,
                       e.id as emulator_db_id, e.emu_index, e.serial, e.name as emu_name,
                       e.status as emu_status, e.last_seen_at
                   FROM accounts a
                   LEFT JOIN emulators e ON a.emulator_id = e.id
                   WHERE a.game_id = ?""",
                (game_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            acc = dict(row)

            # Attach latest scan by game_id
            scan_cur = await db.execute(
                """SELECT * FROM scan_snapshots
                   WHERE game_id = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (game_id,),
            )
            scan_row = await scan_cur.fetchone()

            if not scan_row and acc.get("emulator_db_id"):
                scan_cur = await db.execute(
                    """SELECT * FROM scan_snapshots
                       WHERE emulator_id = ?
                       ORDER BY created_at DESC LIMIT 1""",
                    (acc["emulator_db_id"],),
                )
                scan_row = await scan_cur.fetchone()

            if scan_row:
                scan = dict(scan_row)
                acc["lord_name"] = scan.get("lord_name", "") or acc.get("acc_lord_name", "")
                acc["power"] = scan.get("power", 0)
                acc["hall_level"] = scan.get("hall_level", 0)
                acc["market_level"] = scan.get("market_level", 0)
                acc["pet_token"] = scan.get("pet_token", 0)
                acc["last_scan_at"] = scan.get("created_at", "")
                acc["scan_id"] = scan["id"]
                res_cur = await db.execute(
                    "SELECT * FROM scan_resources WHERE snapshot_id = ?",
                    (scan["id"],),
                )
                for res in await res_cur.fetchall():
                    rd = dict(res)
                    rtype = rd["resource_type"]
                    acc[rtype] = rd.get("bag_value", 0)
                    acc[f"{rtype}_total"] = rd.get("total_value", 0)
            else:
                acc["lord_name"] = acc.get("acc_lord_name", "")
                acc["power"] = 0
                acc["hall_level"] = 0
                acc["market_level"] = 0
                acc["pet_token"] = 0
                acc["last_scan_at"] = ""

            acc.pop("acc_lord_name", None)
            return acc

    async def get_account_by_emu_index(self, emu_index: int) -> list[dict]:
        """Get all accounts linked to an emulator index."""
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT a.game_id FROM accounts a
                   JOIN emulators e ON a.emulator_id = e.id
                   WHERE e.emu_index = ?
                   ORDER BY a.is_active DESC""",
                (emu_index,),
            )
            rows = await cursor.fetchall()
            results = []
            for row in rows:
                acc = await self.get_account_by_game_id(row["game_id"])
                if acc:
                    results.append(acc)
            return results

    async def update_account(self, game_id: str, **fields) -> bool:
        """Update specific account fields by game_id."""
        allowed = {"login_method", "email", "provider", "alliance", "note", "lord_name"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return False
        updates["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values())
        async with self._get_conn() as db:
            cursor = await db.execute(
                f"UPDATE accounts SET {set_clause} WHERE game_id = ?",
                (*values, game_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def delete_account(self, game_id: str) -> bool:
        """Delete account by game_id."""
        async with self._get_conn() as db:
            cursor = await db.execute(
                "DELETE FROM accounts WHERE game_id = ?", (game_id,),
            )
            await db.commit()
            return cursor.rowcount > 0

    # ── Pending Account CRUD ────────────────────────

    async def get_pending_accounts(self) -> list[dict]:
        """Get all pending accounts."""
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT p.*, e.emu_index, e.name as emu_name
                   FROM pending_accounts p
                   JOIN emulators e ON p.emulator_id = e.id
                   WHERE p.status = 'pending'
                   ORDER BY p.created_at DESC"""
            )
            return [dict(row) for row in await cursor.fetchall()]

    async def confirm_pending_account(
        self, pending_id: int, login_method: str = "",
        email: str = "", provider: str = "Global",
        alliance: str = "", note: str = "",
    ) -> int:
        """Confirm a pending account → create it in accounts table. Returns account id."""
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM pending_accounts WHERE id = ? AND status = 'pending'",
                (pending_id,),
            )
            pending = await cursor.fetchone()
            if not pending:
                return 0
            pending = dict(pending)

        # Create the actual account
        acc_id = await self.upsert_account(
            game_id=pending["game_id"],
            emulator_id=pending["emulator_id"],
            lord_name=pending["lord_name"],
            login_method=login_method,
            email=email,
            provider=provider,
            alliance=alliance,
            note=note,
            is_active=1,
        )

        # Mark pending as confirmed
        async with self._get_conn() as db:
            await db.execute(
                "UPDATE pending_accounts SET status = 'confirmed' WHERE id = ?",
                (pending_id,),
            )
            await db.commit()

        return acc_id

    async def dismiss_pending_account(self, pending_id: int) -> bool:
        """Dismiss a pending account (will reappear on next scan)."""
        async with self._get_conn() as db:
            cursor = await db.execute(
                "UPDATE pending_accounts SET status = 'dismissed' WHERE id = ?",
                (pending_id,),
            )
            await db.commit()
            return cursor.rowcount > 0

    # ──────────────────────────────────────────
    # Schedules
    # ──────────────────────────────────────────

    async def get_all_schedules(self) -> list[dict]:
        """Get all schedules ordered by created_at."""
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM schedules ORDER BY is_enabled DESC, created_at DESC"
            )
            return [dict(row) for row in await cursor.fetchall()]

    async def get_schedule(self, schedule_id: int) -> dict | None:
        """Get single schedule by id."""
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM schedules WHERE id = ?", (schedule_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def create_schedule(
        self, name: str, macro_filename: str,
        schedule_type: str = "once", schedule_value: str = "",
        target_mode: str = "all_online", target_indices: str = "[]",
        is_enabled: int = 1, next_run_at: str = "",
    ) -> int:
        """Create a new schedule. Returns schedule id."""
        async with self._get_conn() as db:
            cursor = await db.execute(
                """INSERT INTO schedules
                   (name, macro_filename, schedule_type, schedule_value,
                    target_mode, target_indices, is_enabled, next_run_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, macro_filename, schedule_type, schedule_value,
                 target_mode, target_indices, is_enabled, next_run_at),
            )
            await db.commit()
            return cursor.lastrowid

    async def update_schedule(self, schedule_id: int, **kwargs) -> bool:
        """Update schedule fields."""
        allowed = {
            "name", "macro_filename", "schedule_type", "schedule_value",
            "target_mode", "target_indices", "is_enabled", "next_run_at",
        }
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return False

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [schedule_id]

        async with self._get_conn() as db:
            cursor = await db.execute(
                f"UPDATE schedules SET {set_clause} WHERE id = ?", values
            )
            await db.commit()
            return cursor.rowcount > 0

    async def delete_schedule(self, schedule_id: int) -> bool:
        """Delete a schedule."""
        async with self._get_conn() as db:
            cursor = await db.execute(
                "DELETE FROM schedules WHERE id = ?", (schedule_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def record_schedule_run(self, schedule_id: int, next_run_at: str = "") -> bool:
        """Record that a schedule has been executed."""
        async with self._get_conn() as db:
            cursor = await db.execute(
                """UPDATE schedules SET
                    last_run_at = ?, run_count = run_count + 1,
                    next_run_at = ?
                   WHERE id = ?""",
                (datetime.now().isoformat(), next_run_at, schedule_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    # ──────────────────────────────────────────
    # Account Groups
    # ──────────────────────────────────────────

    async def get_all_groups(self) -> list[dict]:
        """Get all account groups."""
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM account_groups ORDER BY created_at DESC")
            return [dict(row) for row in await cursor.fetchall()]

    async def create_group(self, name: str, account_ids: str = '[]') -> int:
        """Create a new account group."""
        async with self._get_conn() as db:
            cursor = await db.execute(
                "INSERT INTO account_groups (name, account_ids) VALUES (?, ?)",
                (name, account_ids),
            )
            await db.commit()
            return cursor.lastrowid

    async def update_group(self, group_id: int, name: str = None, account_ids: str = None) -> bool:
        """Update an account group."""
        fields = {}
        if name is not None:
            fields["name"] = name
        if account_ids is not None:
            fields["account_ids"] = account_ids

        if not fields:
            return False

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [group_id]

        async with self._get_conn() as db:
            cursor = await db.execute(
                f"UPDATE account_groups SET {set_clause} WHERE id = ?", values
            )
            await db.commit()
            return cursor.rowcount > 0

    async def delete_group(self, group_id: int) -> bool:
        """Delete an account group."""
        async with self._get_conn() as db:
            cursor = await db.execute("DELETE FROM account_groups WHERE id = ?", (group_id,))
            await db.commit()
            return cursor.rowcount > 0


# Global singleton
database = Database()
