# COD Game Automation Manager

Desktop automation manager for Call of Dragons workflows running on LDPlayer emulators.

The current codebase is a Python desktop app that launches a local FastAPI server, serves a vanilla JavaScript SPA, and opens it inside a `pywebview` window when available.

## What The App Does

- Discovers and manages LDPlayer emulator instances
- Runs recorded macro scripts (`.record` files) through ADB replay
- Executes workflow and bot activities for grouped game accounts
- Tracks task/checklist progress per account and per day
- Stores emulator, account, workflow, macro, and execution history in SQLite
- Runs OCR-based scans and stores scan snapshots
- Supports scheduled macro execution in a background scheduler
- Streams live status to the UI through WebSocket events

## Tech Stack

- Backend: FastAPI, Uvicorn, Pydantic, aiosqlite
- Desktop shell: pywebview
- Frontend: static HTML/CSS plus vanilla JavaScript SPA
- OCR and imaging: OpenCV, NumPy, pytesseract
- Storage: SQLite

## Current Entry Point

The app starts from [main.py](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/main.py).

Startup flow:

1. Load configuration from `config.yaml`
2. Start the FastAPI app from [backend/api.py](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/api.py)
3. Serve the frontend from [frontend/index.html](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/frontend/index.html)
4. Open the UI in a native `pywebview` window, or fall back to the browser if `pywebview` is missing

## Quick Start

### Requirements

- Python 3.10+
- Windows environment with LDPlayer installed
- LDPlayer ADB available at the path configured in `config.yaml`
- Tesseract OCR installed if you use OCR features

### Install

```bash
pip install -r requirements.txt
```

### Run

```bash
python main.py
```

By default the server runs on `http://127.0.0.1:8000` and the desktop window loads that local URL.

## Configuration

Runtime configuration is loaded from [config.yaml](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/config.yaml) by [backend/config.py](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/config.py).

Current config fields:

- `app_version`: app version shown by the backend
- `adb_path`: path to LDPlayer `adb.exe`
- `tesseract_path`: path to `tesseract.exe`
- `resolution`: target emulator resolution
- `coordinate_map`: coordinate map name from `data/coordinate_maps`
- `work_dir`: working folder for debug output and related runtime files
- `debug_screenshots`: enable screenshot/debug artifact generation
- `db_path`: SQLite database path
- `server_port`: FastAPI port

The default project database path is `data/cod_manager.db`.

OCR API keys are managed through the config endpoints and are resolved from `api_keys_file` settings in code. Relative paths are resolved from the project root.

## Frontend Pages

The SPA router in [frontend/js/app.js](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/frontend/js/app.js) currently exposes these main screens:

- `dashboard`: overview and device status
- `task`: task checklist and daily account activity tracking
- `runner`: macro and scan actions page
- `history`: execution and data history views
- `emulators`: LDPlayer instance management
- `accounts`: account management
- `workflow`: workflow builder, bot controls, groups, and monitor views
- `scheduled`: scheduled macro jobs
- `settings`: app configuration and operational settings

The frontend is no longer a small flat JS app. It now includes layered code under:

- [frontend/js/application](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/frontend/js/application)
- [frontend/js/domain](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/frontend/js/domain)
- [frontend/js/infrastructure](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/frontend/js/infrastructure)
- [frontend/js/shared](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/frontend/js/shared)
- [frontend/js/pages](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/frontend/js/pages)

## Backend Overview

The main FastAPI app lives in [backend/api.py](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/api.py).

Major backend areas:

- [backend/core](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/core): emulator, OCR, scheduler, macro replay, scan orchestration
- [backend/core/workflow](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/core/workflow): workflow execution, activity registry, templates, bot orchestration, policy logic
- [backend/storage](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/storage): SQLite schema and persistence helpers
- [backend/tasks](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/tasks): task queue integration
- [backend/websocket.py](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/websocket.py): live event broadcast manager

## Main Functional Areas

### Emulator Management

The app can list, launch, quit, and inspect LDPlayer instances.

Relevant files:

- [backend/core/emulator.py](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/core/emulator.py)
- [backend/core/ldplayer_manager.py](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/core/ldplayer_manager.py)
- [frontend/js/pages/emulators.js](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/frontend/js/pages/emulators.js)

### Macro Replay

Macro execution is built around LDPlayer `.record` files and ADB replay.

Relevant files:

- [backend/core/macro_replay.py](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/core/macro_replay.py)
- [frontend/js/pages/task-runner.js](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/frontend/js/pages/task-runner.js)

### OCR Scan Pipeline

OCR-based capture and parsing flows live in the core scan modules.

Relevant files:

- [backend/core/full_scan.py](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/core/full_scan.py)
- [backend/core/screen_capture.py](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/core/screen_capture.py)
- [backend/core/ocr_client.py](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/core/ocr_client.py)
- [backend/core/ocr_engine.py](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/core/ocr_engine.py)

### Workflow And Bot System

The workflow area is now one of the largest parts of the project. It includes:

- recipe and template management
- activity registry and group-specific activity configuration
- sequential bot execution for account groups
- execution logs, monitoring, and KPI summaries

Relevant files:

- [backend/core/workflow/workflow_registry.py](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/core/workflow/workflow_registry.py)
- [backend/core/workflow/executor.py](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/core/workflow/executor.py)
- [backend/core/workflow/bot_orchestrator.py](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/core/workflow/bot_orchestrator.py)
- [frontend/js/pages/workflow.js](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/frontend/js/pages/workflow.js)

### Task Checklist

The task page is backed by daily per-account activity state in SQLite and supports:

- filtering by date and account group
- activity coverage tracking
- manual mark done/undo actions
- account activity history side panel
- checklist template persistence

Relevant files:

- [frontend/js/pages/task.js](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/frontend/js/pages/task.js)
- [backend/storage/database.py](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/storage/database.py)
- [backend/api.py](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/api.py)

### Scheduling

The scheduler runs in a background thread and currently handles scheduled macro execution.

Relevant files:

- [backend/core/scheduler.py](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/core/scheduler.py)
- [frontend/js/pages/scheduled.js](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/frontend/js/pages/scheduled.js)

## API Surface

The API has grown substantially. Major route groups currently include:

- `/api/devices`
- `/api/tasks`
- `/api/reports`
- `/api/config`
- `/api/emulators`
- `/api/macros`
- `/api/scan`
- `/api/accounts`
- `/api/pending-accounts`
- `/api/schedules`
- `/api/apks`
- `/api/workflow`
- `/api/bot`
- `/api/monitor`
- `/api/groups`
- `/api/execution`
- `/api/task/checklist`
- `/api/task/account-history`
- `/ws`

For the full list, see [backend/api.py](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/api.py).

## Database

The database layer is implemented in [backend/storage/database.py](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/storage/database.py).

Important tables include:

- `emulators`
- `scan_snapshots`
- `scan_resources`
- `macros`
- `macro_runs`
- `task_runs`
- `task_run_steps`
- `audit_logs`
- `accounts`
- `pending_accounts`
- `schedules`
- `account_groups`
- `account_activity_logs`
- `task_daily_state`
- `task_templates`
- `task_template_items`

## Project Structure

```text
UI_MANAGER/
|-- main.py
|-- config.yaml
|-- pyproject.toml
|-- requirements.txt
|-- backend/
|   |-- api.py
|   |-- config.py
|   |-- websocket.py
|   |-- core/
|   |   |-- emulator.py
|   |   |-- full_scan.py
|   |   |-- ldplayer_manager.py
|   |   |-- macro_replay.py
|   |   |-- scheduler.py
|   |   `-- workflow/
|   |-- storage/
|   `-- tasks/
|-- frontend/
|   |-- index.html
|   |-- loading.html
|   |-- css/
|   `-- js/
|       |-- app.js
|       |-- api.js
|       |-- store.js
|       |-- application/
|       |-- components/
|       |-- domain/
|       |-- infrastructure/
|       |-- pages/
|       `-- shared/
`-- data/
    |-- cod_manager.db
    `-- coordinate_maps/
```

## Development Commands

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
python main.py
```

Configured tooling in [pyproject.toml](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/pyproject.toml):

- `pytest`
- `pyright`
- `ruff`
- `mypy`

Typical commands:

```bash
pytest
pyright
ruff check .
mypy .
```

Note: this repo currently does not include a dedicated Node-based frontend build pipeline.

## Important Runtime Notes

- The project is Windows-oriented because it depends on LDPlayer tooling paths and ADB usage patterns.
- Many workflow modules rely on image templates and coordinate maps under [backend/core/workflow/templates](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/core/workflow/templates) and [data/coordinate_maps](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/data/coordinate_maps).
- Some workflow actions still contain placeholders, tuning hooks, and debug assets, so not every activity should be assumed production-complete.
- The startup hook initializes the database, discovers emulators, and starts the scheduler automatically.

## Additional Docs

- [GUIDE.md](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/GUIDE.md)
- [walkthrough.md](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/walkthrough.md)
- [update.md](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/update.md)
- [release.md](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/release.md)
- [backend/core/WORKFLOW_GUIDE.md](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/core/WORKFLOW_GUIDE.md)
- [backend/core/PRODUCTION_GUIDE.md](C:/Users/16lem/.codex/worktrees/8401/UI_MANAGER/backend/core/PRODUCTION_GUIDE.md)
