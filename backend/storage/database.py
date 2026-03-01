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
    serial          TEXT NOT NULL UNIQUE,
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

-- Task execution history (replaces task_logs)
CREATE TABLE IF NOT EXISTS task_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    emulator_id     INTEGER NOT NULL,
    task_type       TEXT NOT NULL,
    status          TEXT DEFAULT 'queued',
    error           TEXT DEFAULT '',
    duration_ms     INTEGER DEFAULT 0,
    result_json     TEXT DEFAULT '',
    started_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    finished_at     TEXT,
    FOREIGN KEY (emulator_id) REFERENCES emulators(id)
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_snap_emu_time ON scan_snapshots(emulator_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_res_snap ON scan_resources(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_taskrun_emu ON task_runs(emulator_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_macrorun_emu ON macro_runs(emulator_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_accounts_emu ON accounts(emulator_id);
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


def _migrate_accounts_schema(conn: sqlite3.Connection):
    """Migrate accounts table to v2 schema (add game_id, is_active, lord_name).
    Also add game_id column to scan_snapshots. Safe to re-run (idempotent)."""
    # Check if accounts table needs migration (no game_id column)
    cursor = conn.execute("PRAGMA table_info(accounts)")
    cols = {row[1] for row in cursor.fetchall()}

    if "game_id" not in cols:
        print("[DB Migration] Migrating accounts table → adding game_id, is_active, lord_name...")

        # SQLite can't ALTER constraints, so we recreate the table
        conn.execute("ALTER TABLE accounts RENAME TO accounts_old")
        conn.executescript("""
            CREATE TABLE accounts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id         TEXT NOT NULL UNIQUE,
                emulator_id     INTEGER,
                lord_name       TEXT DEFAULT '',
                login_method    TEXT DEFAULT '',
                email           TEXT DEFAULT '',
                provider        TEXT DEFAULT 'Global',
                alliance        TEXT DEFAULT '',
                note            TEXT DEFAULT '',
                is_active       INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (emulator_id) REFERENCES emulators(id)
            );
        """)

        # Migrate existing data with placeholder game_ids
        old_cursor = conn.execute("SELECT * FROM accounts_old")
        old_cols = [desc[0] for desc in old_cursor.description]
        rows = old_cursor.fetchall()

        for row in rows:
            d = dict(zip(old_cols, row))
            placeholder_id = f"LEGACY-{d['id']}"
            conn.execute(
                """INSERT INTO accounts
                   (game_id, emulator_id, login_method, email, provider, alliance, note, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    placeholder_id,
                    d.get("emulator_id"),
                    d.get("login_method", ""),
                    d.get("email", ""),
                    d.get("provider", "Global"),
                    d.get("alliance", ""),
                    d.get("note", ""),
                    d.get("created_at", ""),
                    d.get("updated_at", ""),
                ),
            )

        conn.execute("DROP TABLE accounts_old")
        print(f"  -> Migrated {len(rows)} accounts with LEGACY- game_ids")
        conn.commit()

    # Add game_id column to scan_snapshots if missing
    cursor = conn.execute("PRAGMA table_info(scan_snapshots)")
    snap_cols = {row[1] for row in cursor.fetchall()}
    if "game_id" not in snap_cols:
        try:
            conn.execute("ALTER TABLE scan_snapshots ADD COLUMN game_id TEXT DEFAULT ''")
            conn.commit()
            print("[DB Migration] Added game_id column to scan_snapshots")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Create indexes that depend on game_id (safe now that columns exist)
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_accounts_game_id ON accounts(game_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_snap_game_id ON scan_snapshots(game_id)")
            conn.commit()
        except sqlite3.OperationalError:
            pass


# ──────────────────────────────────────────────
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

        # Create v2 tables first (IF NOT EXISTS is safe)
        conn.executescript(CREATE_TABLES_SQL)

        # Migrate v1 data if needed
        _migrate_v1_to_v2(conn)

        # Migrate accounts schema (add game_id etc.)
        _migrate_accounts_schema(conn)

        conn.close()
        self._initialized = True
        print(f"[DB] Initialized at {self.db_path}")

    def _get_conn(self):
        return aiosqlite.connect(self.db_path)

    # ──────────────────────────────────────────
    # Emulators
    # ──────────────────────────────────────────

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

    # ──────────────────────────────────────────
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
    ) -> int:
        """Create a new task run record. Returns run id."""
        async with self._get_conn() as db:
            cursor = await db.execute(
                """INSERT INTO task_runs (emulator_id, task_type, status)
                   VALUES (?, ?, ?)""",
                (emulator_id, task_type, status),
            )
            await db.commit()
            return cursor.lastrowid

    async def update_task_run(
        self, run_id: int, status: str = None,
        error: str = None, duration_ms: int = None,
        result_json: str = None, finished_at: str = None
    ):
        """Update a task run record."""
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
        async with self._get_conn() as db:
            await db.execute(
                f"UPDATE task_runs SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            await db.commit()

    async def get_task_runs(self, emulator_index: int = None,
                             limit: int = 50) -> list[dict]:
        """Get task execution history."""
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row
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
            return [dict(row) for row in await cursor.fetchall()]

    # ── Account CRUD ──────────────────────────────

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


# Global singleton
database = Database()

