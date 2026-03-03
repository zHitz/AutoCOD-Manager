"""
FastAPI Routes — REST API + WebSocket endpoints.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

# MUST load config BEFORE any other backend imports
from backend.config import config
if not config.is_loaded:
    config.load()

from backend.core.emulator import emulator_manager
from backend.tasks.task_queue import task_queue
from backend.storage.database import database
from backend.websocket import ws_manager
from backend.models.scan_result import TaskType

import os

# Resolve frontend path
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="COD Game Automation Manager", version="1.0.0")

# Allow loading screen (html= origin is null) to reach the API
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")


# ──────────────────────────────────────────────
# Pages
# ──────────────────────────────────────────────

@app.get("/")
async def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


# ──────────────────────────────────────────────
# Device Endpoints
# ──────────────────────────────────────────────

@app.get("/api/devices")
async def get_devices():
    """List all registered emulators with status and latest DB data."""
    from backend.storage.database import database
    devices = emulator_manager.get_all()
    
    # Fetch latest data from database
    db_data = await database.get_all_emulator_data()
    serial_to_data = {row["serial"]: row for row in db_data}
    
    result = []
    for d in devices:
        d_dict = d.to_dict()
        if d.serial in serial_to_data:
            # Inject full_scan db data shape for the UI mapped in device-card.js
            row_data = dict(serial_to_data[d.serial])
            # Map flat resource columns to a nested 'resources' dict as expected by UI
            row_data["resources"] = {
                "gold": row_data.get("gold", 0),
                "wood": row_data.get("wood", 0),
                "ore": row_data.get("ore", 0),
                "mana": row_data.get("mana", 0)
            }
            d_dict["data"] = row_data
            d_dict["task_type"] = "full_scan"
        result.append(d_dict)
        
    return result


@app.post("/api/devices/refresh")
async def refresh_devices():
    """Re-discover ADB devices and load latest DB data."""
    from backend.storage.database import database
    devices = emulator_manager.discover()
    
    db_data = await database.get_all_emulator_data()
    serial_to_data = {row["serial"]: row for row in db_data}
    
    result = []
    for d in devices:
        d_dict = d.to_dict()
        if d.serial in serial_to_data:
            row_data = dict(serial_to_data[d.serial])
            row_data["resources"] = {
                "gold": row_data.get("gold", 0),
                "wood": row_data.get("wood", 0),
                "ore": row_data.get("ore", 0),
                "mana": row_data.get("mana", 0)
            }
            d_dict["data"] = row_data
            d_dict["task_type"] = "full_scan"  
        result.append(d_dict)
        
    return {"count": len(devices), "devices": result}


@app.get("/api/devices/health")
async def device_health():
    """Health check all emulators."""
    summary = emulator_manager.health_check()
    return summary


# ──────────────────────────────────────────────
# Task Endpoints
# ──────────────────────────────────────────────

@app.post("/api/tasks/run")
async def run_task(serial: str, task_type: str):
    """Submit a task for a single device."""
    try:
        tt = TaskType(task_type)
    except ValueError:
        return {"status": "error", "msg": f"Invalid task type: {task_type}"}

    if tt == TaskType.FULL_SCAN:
        # Route to the dedicated full scan orchestrator
        from backend.core import full_scan
        from backend.core import ldplayer_manager
        from backend.websocket import ws_manager
        
        # Derive LDPlayer index from adb serial (emulator-5556 -> index 1)
        try:
            port = int(serial.split("-")[1])
            idx = (port - 5554) // 2
        except Exception:
            return {"status": "error", "msg": "Cannot determine emulator index from serial"}
            
        all_emus = ldplayer_manager.list_all_instances()
        name_map = {e["index"]: e["name"] for e in all_emus}
        name = name_map.get(idx, f"Emulator-{idx}")
        
        result = full_scan.start_full_scan(idx, name, ws_callback=ws_manager.broadcast_sync)
        if result.get("success"):
            return {"status": "accepted", "task_id": f"fullscan-{idx}"}
        else:
            return {"status": "error", "msg": result.get("error")}

    task_id = task_queue.submit_task(serial, tt)
    # task_queue now handles DB persistence internally
    return {"status": "accepted", "task_id": task_id}


@app.post("/api/tasks/run-all")
async def run_all_tasks(task_type: str, indices: str = None):
    """Submit a task for selected devices (by LDPlayer index) or all online."""
    try:
        tt = TaskType(task_type)
    except ValueError:
        return {"status": "error", "msg": f"Invalid task type: {task_type}"}

    online = emulator_manager.get_online()
    if not online:
        online = emulator_manager.discover()
        online = [e for e in online if e.status == "ONLINE"]

    if not online:
        return {"status": "error", "msg": "No online emulators found"}

    # Filter by selected indices if provided (comma-separated, e.g. "0,2,3")
    if indices:
        selected = set(int(i) for i in indices.split(",") if i.strip().isdigit())
        selected_serials = {f"emulator-{5554 + idx * 2}" for idx in selected}
        online = [e for e in online if e.serial in selected_serials]
        if not online:
            return {"status": "error", "msg": "None of the selected emulators are online"}

    if tt == TaskType.FULL_SCAN:
        # Route each device through the dedicated full scan orchestrator
        from backend.core import full_scan
        from backend.core import ldplayer_manager
        from backend.websocket import ws_manager

        all_emus = ldplayer_manager.list_all_instances()
        name_map = {e["index"]: e["name"] for e in all_emus}

        results = []
        for emu in online:
            try:
                port = int(emu.serial.split("-")[1])
                idx = (port - 5554) // 2
            except Exception:
                results.append({"serial": emu.serial, "status": "error", "msg": "Cannot parse index"})
                continue

            name = name_map.get(idx, f"Emulator-{idx}")
            result = full_scan.start_full_scan(idx, name, ws_callback=ws_manager.broadcast_sync)
            if result.get("success"):
                results.append({"serial": emu.serial, "task_id": f"fullscan-{idx}", "status": "accepted"})
            else:
                results.append({"serial": emu.serial, "status": "error", "msg": result.get("error")})

        return {"status": "accepted", "count": len(results), "tasks": results}

    task_ids = []
    for emu in online:
        tid = task_queue.submit_task(emu.serial, tt)
        task_ids.append({"serial": emu.serial, "task_id": tid})

    return {"status": "accepted", "count": len(task_ids), "tasks": task_ids}


@app.get("/api/tasks/queue")
async def get_queue():
    """Get current task queue state."""
    return task_queue.get_queue()


@app.get("/api/tasks/history")
async def get_history(limit: int = 50):
    """Get task execution history (in-memory + DB fallback)."""
    mem_history = task_queue.get_history(limit)
    if mem_history:
        return mem_history
    # Fallback to DB history
    return await database.get_task_runs(limit=limit)


# ──────────────────────────────────────────────
# Report Endpoints
# ──────────────────────────────────────────────

@app.get("/api/reports/history")
async def get_reports(limit: int = 50, serial: str = None):
    """Get scan result history from database."""
    return await database.get_scan_history(limit=limit, serial=serial)


@app.get("/api/reports/latest/{serial}")
async def get_latest_report(serial: str):
    """Get the latest scan result for a device."""
    return await database.get_latest_report(serial)


# ──────────────────────────────────────────────
# Config Endpoints
# ──────────────────────────────────────────────

@app.get("/api/config")
async def get_config():
    """Get current app configuration."""
    return config.to_dict()


@app.get("/api/config/ocr-keys")
async def get_ocr_keys():
    """Get OCR API keys as newline separated text."""
    keys_path = config.get_api_keys_path()
    if not keys_path.exists():
        return {"keys": ""}

    with open(keys_path, "r", encoding="utf-8") as f:
        return {"keys": f.read()}


@app.post("/api/config/ocr-keys")
async def save_ocr_keys(payload: dict):
    """Save OCR API keys file content."""
    keys_text = (payload or {}).get("keys", "")
    keys_path = config.get_api_keys_path()
    keys_path.parent.mkdir(parents=True, exist_ok=True)
    with open(keys_path, "w", encoding="utf-8") as f:
        f.write(keys_text.rstrip() + ("\n" if keys_text.strip() else ""))
    return {"status": "ok"}


# ──────────────────────────────────────────────
# WebSocket
# ──────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            # Keep connection alive, handle client messages if needed
            data = await ws.receive_text()
            # Echo back for ping/pong
            if data == "ping":
                await ws.send_text('{"event":"pong"}')
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


# ──────────────────────────────────────────────
# LDPlayer Instance Management
# ──────────────────────────────────────────────

@app.get("/api/emulators/all")
async def list_all_emulators():
    """List ALL LDPlayer instances (online + offline)."""
    from backend.core import ldplayer_manager
    return ldplayer_manager.list_all_instances()


@app.post("/api/emulators/launch")
async def launch_emulator(index: int):
    """Start an emulator by index."""
    from backend.core import ldplayer_manager
    ldplayer_manager.launch_instance(index)
    return {"status": "ok", "msg": f"Launch command sent for index {index}"}


@app.post("/api/emulators/quit")
async def quit_emulator(index: int):
    """Stop an emulator by index."""
    from backend.core import ldplayer_manager
    ldplayer_manager.quit_instance(index)
    return {"status": "ok", "msg": f"Quit command sent for index {index}"}


# ──────────────────────────────────────────────
# Macro / Operation Records
# ──────────────────────────────────────────────

@app.get("/api/macros/list")
async def list_macros():
    """List all available .record macro files."""
    from backend.core import ldplayer_manager
    return ldplayer_manager.list_record_files()


@app.get("/api/macros/info")
async def macro_info(index: int, filename: str):
    """Get detailed info about a macro script."""
    from backend.core import ldplayer_manager
    return ldplayer_manager.get_operation_info(index, filename)


@app.post("/api/macros/run")
async def run_macro(index: int, filename: str):
    """Execute a macro on a target emulator via ADB replay."""
    from backend.core import ldplayer_manager
    from backend.core import macro_replay
    import os

    filepath = os.path.join(ldplayer_manager._get_operations_dir(), filename)
    if not os.path.exists(filepath):
        return {"success": False, "error": f"Record file not found: {filename}"}

    result = macro_replay.start_replay(
        index, filepath, filename,
        ws_callback=ws_manager.broadcast_sync,
    )
    return result


@app.post("/api/macros/stop")
async def stop_macro(index: int, filename: str):
    """Stop a running macro replay."""
    from backend.core import macro_replay
    return macro_replay.stop_replay(index, filename)


@app.get("/api/macros/status")
async def macro_status():
    """Get status of all running macros."""
    from backend.core import macro_replay
    return macro_replay.get_status()


# ──────────────────────────────────────────────
# Full Scan (OCR Pipeline)
# ──────────────────────────────────────────────

@app.post("/api/scan/full")
async def start_full_scan(indices: str):
    """Start Full Scan on selected emulators.

    Args:
        indices: comma-separated emulator indices, e.g. "1,2,3"
    """
    from backend.core import full_scan
    from backend.core import ldplayer_manager

    index_list = [int(i.strip()) for i in indices.split(",") if i.strip().isdigit()]
    if not index_list:
        return {"success": False, "error": "No valid indices provided"}

    # Get emulator names
    all_emus = ldplayer_manager.list_all_instances()
    name_map = {e["index"]: e["name"] for e in all_emus}

    results = []
    for idx in index_list:
        name = name_map.get(idx, f"Emulator-{idx}")
        result = full_scan.start_full_scan(
            idx, name, ws_callback=ws_manager.broadcast_sync,
        )
        results.append(result)

    return {"success": True, "scans": results}


@app.get("/api/scan/status")
async def scan_status():
    """Get status of all running scans."""
    from backend.core import full_scan
    return full_scan.get_scan_status()


@app.post("/api/scan/stop")
async def stop_scan(index: int):
    """Stop a running scan."""
    from backend.core import full_scan
    return full_scan.stop_scan(index)


# ──────────────────────────────────────────────
# DB-backed History Endpoints
# ──────────────────────────────────────────────

@app.get("/api/macro-runs/history")
async def get_macro_runs_history(emulator_index: int = None, limit: int = 50):
    """Get macro execution history from database."""
    return await database.get_macro_runs(emulator_index=emulator_index, limit=limit)


@app.get("/api/task-runs/history")
async def get_task_runs_history(emulator_index: int = None, limit: int = 50):
    """Get task execution history from database."""
    return await database.get_task_runs(emulator_index=emulator_index, limit=limit)


# ──────────────────────────────────────────────
# Emulator Data (Scan Results)
# ──────────────────────────────────────────────

@app.get("/api/emulators/data")
async def get_all_emulator_data():
    """Get latest scan data for all emulators."""
    return await database.get_all_emulator_data()


@app.get("/api/emulators/{index}/data")
async def get_emulator_data(index: int):
    """Get latest scan data for a specific emulator."""
    data = await database.get_emulator_data(emulator_index=index)
    if data:
        return data
    return {"error": "No scan data found", "emulator_index": index}


@app.get("/api/emulators/{index}/history")
async def get_emulator_history(index: int, limit: int = 20):
    """Get scan history for a specific emulator."""
    return await database.get_emulator_scan_history(index, limit)

# ──────────────────────────────────────────────
# Account Endpoints
# ──────────────────────────────────────────────

@app.get("/api/accounts")
async def get_accounts():
    """Get all accounts with emulator + latest scan data."""
    return await database.get_all_accounts()


@app.post("/api/accounts")
async def create_account(body: dict):
    """Create a new account manually. Requires game_id."""
    if not body:
        return {"error": "Empty body"}
    
    game_id = body.get("game_id", "").strip()
    if not game_id:
        return {"error": "game_id is required"}

    emu_index = body.get("emu_index")
    if emu_index is not None:
        try:
            emu_index = int(emu_index)
        except ValueError:
            return {"error": "emu_index must be an integer"}

    try:
        acc_id = await database.upsert_account_full(
            game_id=game_id,
            emulator_index=emu_index,
            lord_name=body.get("lord_name", ""),
            power=float(body.get("power", 0)),
            login_method=body.get("login_method", ""),
            email=body.get("email", ""),
            provider=body.get("provider", "Global"),
            alliance=body.get("alliance", ""),
            note=body.get("note", "")
        )
        return {"status": "ok", "account_id": acc_id, "game_id": game_id}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/accounts/{game_id}")
async def get_account(game_id: str):
    """Get single account by game_id."""
    acc = await database.get_account_by_game_id(game_id)
    if acc:
        return acc
    return {"error": "Account not found", "game_id": game_id}


@app.put("/api/accounts/{game_id}")
async def update_account(game_id: str, body: dict):
    """Update account fields (note, login_method, email, provider, alliance, lord_name)."""
    if not body:
        return {"error": "Empty body", "game_id": game_id}
    body.pop("game_id", None)
    body.pop("emu_index", None)
    ok = await database.update_account(game_id, **body)
    if ok:
        return {"status": "ok", "game_id": game_id}
    return {"error": "Account not found or no valid fields", "game_id": game_id}


@app.delete("/api/accounts/{game_id}")
async def delete_account(game_id: str):
    """Delete an account record."""
    ok = await database.delete_account(game_id)
    if ok:
        return {"status": "deleted", "game_id": game_id}
    return {"error": "Account not found", "game_id": game_id}


@app.get("/api/accounts/{game_id}/comparison")
async def get_scan_comparison(game_id: str):
    """Get latest scan vs 24h-ago scan for delta comparison."""
    result = await database.get_scan_comparison(game_id)
    return result


# ──────────────────────────────────────────────
# Task History Endpoints
# ──────────────────────────────────────────────

@app.get("/api/tasks/history")
async def get_task_history(limit: int = 200):
    """Get unified task execution history."""
    return await database.get_task_history(limit)


# ──────────────────────────────────────────────
# Pending Account Endpoints
# ──────────────────────────────────────────────

@app.get("/api/pending-accounts")
async def get_pending_accounts():
    """Get all pending accounts awaiting user confirmation."""
    return await database.get_pending_accounts()


@app.post("/api/pending-accounts/{pending_id}/confirm")
async def confirm_pending(pending_id: int, body: dict = None):
    """Confirm a pending account and create it."""
    body = body or {}
    acc_id = await database.confirm_pending_account(
        pending_id=pending_id,
        login_method=body.get("login_method", ""),
        email=body.get("email", ""),
        provider=body.get("provider", "Global"),
        alliance=body.get("alliance", ""),
        note=body.get("note", ""),
    )
    if acc_id:
        return {"status": "confirmed", "account_id": acc_id}
    return {"error": "Pending account not found or already processed"}


@app.post("/api/pending-accounts/{pending_id}/dismiss")
async def dismiss_pending(pending_id: int):
    """Dismiss a pending account (will reappear on next scan)."""
    ok = await database.dismiss_pending_account(pending_id)
    if ok:
        return {"status": "dismissed"}
    return {"error": "Pending account not found"}


# ──────────────────────────────────────────────
# Schedule Endpoints
# ──────────────────────────────────────────────

@app.get("/api/schedules")
async def get_schedules():
    """Get all scheduled jobs."""
    return await database.get_all_schedules()


@app.post("/api/schedules")
async def create_schedule(body: dict):
    """Create a new schedule."""
    from backend.core.scheduler import calc_initial_next_run

    name = body.get("name", "").strip()
    macro_filename = body.get("macro_filename", "").strip()
    if not name or not macro_filename:
        return {"error": "name and macro_filename are required"}

    schedule_type = body.get("schedule_type", "once")
    schedule_value = body.get("schedule_value", "")
    target_mode = body.get("target_mode", "all_online")
    target_indices = body.get("target_indices", "[]")
    is_enabled = 1 if body.get("is_enabled", True) else 0

    # If target_indices is a list, JSON-encode it
    import json as json_mod
    if isinstance(target_indices, list):
        target_indices = json_mod.dumps(target_indices)

    next_run = calc_initial_next_run(schedule_type, schedule_value)

    sched_id = await database.create_schedule(
        name=name,
        macro_filename=macro_filename,
        schedule_type=schedule_type,
        schedule_value=schedule_value,
        target_mode=target_mode,
        target_indices=target_indices,
        is_enabled=is_enabled,
        next_run_at=next_run,
    )
    return {"status": "created", "id": sched_id}


@app.get("/api/schedules/{schedule_id}")
async def get_schedule(schedule_id: int):
    """Get single schedule."""
    sched = await database.get_schedule(schedule_id)
    if sched:
        return sched
    return {"error": "Schedule not found"}


@app.put("/api/schedules/{schedule_id}")
async def update_schedule(schedule_id: int, body: dict):
    """Update a schedule."""
    from backend.core.scheduler import calc_initial_next_run
    import json as json_mod

    # If schedule_type or schedule_value changed, recalculate next_run
    if "schedule_type" in body or "schedule_value" in body:
        stype = body.get("schedule_type")
        sval = body.get("schedule_value")
        if stype and sval:
            body["next_run_at"] = calc_initial_next_run(stype, sval)

    # Convert target_indices list to JSON string
    if "target_indices" in body and isinstance(body["target_indices"], list):
        body["target_indices"] = json_mod.dumps(body["target_indices"])

    # Convert is_enabled boolean to int
    if "is_enabled" in body:
        body["is_enabled"] = 1 if body["is_enabled"] else 0

    ok = await database.update_schedule(schedule_id, **body)
    if ok:
        return {"status": "ok", "id": schedule_id}
    return {"error": "Schedule not found or no valid fields"}


@app.delete("/api/schedules/{schedule_id}")
async def delete_schedule(schedule_id: int):
    """Delete a schedule."""
    ok = await database.delete_schedule(schedule_id)
    if ok:
        return {"status": "deleted"}
    return {"error": "Schedule not found"}


@app.post("/api/schedules/{schedule_id}/execute")
async def execute_schedule_now(schedule_id: int):
    """Execute a schedule immediately (Execute Now)."""
    from backend.core.scheduler import execute_schedule
    import asyncio

    sched = await database.get_schedule(schedule_id)
    if not sched:
        return {"error": "Schedule not found"}

    # Run in background (don't block API response)
    asyncio.create_task(execute_schedule(sched, ws_callback=ws_manager.broadcast_sync))
    return {"status": "executing", "name": sched["name"]}


# ──────────────────────────────────────────────
# APK Install Management
# ──────────────────────────────────────────────

@app.get("/api/apks")
async def list_apks():
    """List all APKs in registry with download status."""
    from backend.core import apk_manager
    return apk_manager.get_apk_list()


@app.post("/api/apks/{app_id}/download")
async def download_apk(app_id: str):
    """Download an APK from its registry URL."""
    from backend.core import apk_manager
    result = apk_manager.download_apk(app_id)
    return result


@app.post("/api/apks/{app_id}/install")
async def install_apk_single(app_id: str, serial: str):
    """Install APK on a single emulator."""
    from backend.core import apk_manager
    return apk_manager.install_apk(app_id, serial)


@app.post("/api/apks/{app_id}/install-all")
async def install_apk_all(app_id: str, payload: dict = None):
    """Install APK on selected emulators (by LDPlayer index)."""
    from backend.core import apk_manager

    indices = (payload or {}).get("indices", [])
    if not indices:
        return {"success": False, "error": "No emulators selected"}

    # Convert LDPlayer indices to ADB serials (index N -> emulator-{5554 + N*2})
    serials = [f"emulator-{5554 + idx * 2}" for idx in indices]
    result = apk_manager.install_apk_on_multiple(app_id, serials, ws_callback=ws_manager.broadcast_sync)
    return result


# ──────────────────────────────────────────────
# Workflow API — Function Registry & Recipes
# ──────────────────────────────────────────────

# In-memory recipe storage (persists across requests, resets on restart)
_saved_recipes: list[dict] = []
_recipe_id_counter = 0


@app.get("/api/workflow/functions")
async def get_workflow_functions():
    """Return the full function registry for the Recipe Builder."""
    from backend.core.workflow.workflow_registry import get_functions
    return get_functions()


@app.get("/api/workflow/templates")
async def get_workflow_templates():
    """Return pre-built recipe templates."""
    from backend.core.workflow.workflow_registry import get_templates
    return get_templates()


@app.get("/api/workflow/recipes")
async def get_workflow_recipes():
    """List all saved user recipes."""
    return _saved_recipes


@app.post("/api/workflow/recipes")
async def save_workflow_recipe(body: dict):
    """Save a new recipe or update an existing one."""
    global _recipe_id_counter
    recipe_id = body.get("id")

    if recipe_id:
        # Update existing
        for i, r in enumerate(_saved_recipes):
            if r["id"] == recipe_id:
                _saved_recipes[i] = {**r, **body}
                return {"status": "ok", "id": recipe_id, "action": "updated"}
        return {"status": "error", "error": "Recipe not found"}

    # Create new
    _recipe_id_counter += 1
    recipe_id = f"recipe_{_recipe_id_counter}"
    recipe = {
        "id": recipe_id,
        "name": body.get("name", "Untitled Recipe"),
        "description": body.get("description", ""),
        "icon": body.get("icon", "📝"),
        "steps": body.get("steps", []),
    }
    _saved_recipes.append(recipe)
    return {"status": "ok", "id": recipe_id, "action": "created"}


@app.post("/api/workflow/run")
async def run_workflow_recipe(body: dict):
    """Run a recipe on a specific emulator."""
    from backend.core.workflow.executor import execute_recipe
    from backend.core.ldplayer_manager import list_all_instances
    import asyncio

    emulator_index = body.get("emulator_index")
    steps = body.get("steps", [])
    
    if emulator_index is None:
        return {"status": "error", "error": "target emulator index is required"}
    if not steps:
        return {"status": "error", "error": "recipe steps are required"}
        
    try:
        emulator_index = int(emulator_index)
    except ValueError:
        return {"status": "error", "error": "invalid emulator index"}

    # Find name
    name = f"Emulator-{emulator_index}"
    for e in list_all_instances():
        if e["index"] == emulator_index:
            name = e["name"]
            break

    # Spawn execution in background
    asyncio.create_task(execute_recipe(
        emulator_index=emulator_index,
        emulator_name=name,
        steps=steps,
        ws_callback=ws_manager.broadcast_sync
    ))
    
    return {"status": "accepted", "msg": f"Workflow started on {name}"}


# Activity<->executor step mapping
_ACTIVITY_TO_STEPS = {
    "Capture Pet":              [{"function_id": "nav_to_lobby"}, {"function_id": "nav_to_capture_pet", "config": {}}],
    "Pet Token":                [{"function_id": "nav_to_lobby"}, {"function_id": "nav_to_pet_token", "config": {}}],
    "Market":                   [{"function_id": "nav_to_lobby"}, {"function_id": "nav_to_market", "config": {}}],
    "Resources":                [{"function_id": "nav_to_lobby"}, {"function_id": "nav_to_resources", "config": {}}],
    "City Hall":                [{"function_id": "nav_to_lobby"}, {"function_id": "nav_to_hall", "config": {}}],
    "Boot to Lobby":            [{"function_id": "startup_to_lobby", "config": {"timeout": 120}}],
    "Back to Lobby":            [{"function_id": "nav_to_lobby", "config": {}}],
    "Detect State":             [{"function_id": "adv_detect_state", "config": {}}],
    "Full Scan":                [{"function_id": "startup_to_lobby", "config": {}}, {"function_id": "scan_full", "config": {}}],
    "Extract Player ID":        [{"function_id": "startup_to_lobby", "config": {}}, {"function_id": "nav_to_profile"}, {"function_id": "adv_copy_id", "config": {}}],
}


@app.post("/api/bot/run")
async def run_bot_activities(body: dict):
    """
    Run bot activities for a group.
    Body: { group_id: int, activities: [str], emulator_indices: [int] }
    Streams logs to WS as workflow_log events → Activity Log in frontend.
    """
    from backend.core.workflow.executor import execute_recipe
    from backend.core.ldplayer_manager import list_all_instances
    import asyncio
    import json as json_mod
    import aiosqlite

    group_id = body.get("group_id")
    activities = body.get("activities", [])
    emulator_indices = body.get("emulator_indices")  # optional override

    if not activities:
        return {"status": "error", "error": "No activities provided"}

    # Build step list
    steps = []
    for act in activities:
        act_steps = _ACTIVITY_TO_STEPS.get(act)
        if act_steps:
            steps.extend(act_steps)
        else:
            steps.append({"function_id": "flow_delay", "config": {"seconds": 1}})

    if not steps:
        return {"status": "error", "error": "No valid activities mapped to steps"}

    # Resolve emulator indices from group's account_ids
    if not emulator_indices and group_id:
        try:
            async with aiosqlite.connect(config.db_path) as db:
                db.row_factory = aiosqlite.Row

                # Get group's account_ids JSON array
                cursor = await db.execute(
                    "SELECT account_ids FROM account_groups WHERE id = ?",
                    (int(group_id),)
                )
                row = await cursor.fetchone()
                if row:
                    account_ids = json_mod.loads(row["account_ids"] or "[]")

                    if account_ids:
                        placeholders = ",".join("?" for _ in account_ids)
                        # Join accounts → emulators to get emu_index
                        cursor2 = await db.execute(
                            f"""SELECT e.emu_index
                                FROM accounts a
                                LEFT JOIN emulators e ON a.emulator_id = e.id
                                WHERE a.id IN ({placeholders})
                                  AND e.emu_index IS NOT NULL""",
                            account_ids
                        )
                        rows = await cursor2.fetchall()
                        emulator_indices = [r["emu_index"] for r in rows]
        except Exception as exc:
            print(f"[bot/run] Error resolving emulators: {exc}")

    if not emulator_indices:
        return {"status": "error", "error": "No emulators found for this group. Make sure the group's accounts have emulators assigned."}

    name_map = {e["index"]: e["name"] for e in list_all_instances()}

    launched = []
    for idx in emulator_indices:
        name = name_map.get(idx, f"Emulator-{idx}")
        asyncio.create_task(execute_recipe(
            emulator_index=idx,
            emulator_name=name,
            steps=steps,
            ws_callback=ws_manager.broadcast_sync
        ))
        launched.append({"index": idx, "name": name})

    return {"status": "accepted", "emulators": launched, "steps": len(steps)}



@app.delete("/api/workflow/recipes/{recipe_id}")
async def delete_workflow_recipe(recipe_id: str):
    """Delete a saved recipe."""
    global _saved_recipes
    before = len(_saved_recipes)
    _saved_recipes = [r for r in _saved_recipes if r["id"] != recipe_id]
    if len(_saved_recipes) < before:
        return {"status": "deleted"}
    return {"status": "error", "error": "Recipe not found"}


# ──────────────────────────────────────────────
# System Endpoints
# ──────────────────────────────────────────────

@app.post("/api/restart")
async def restart_server():
    """Restart the entire backend server process."""
    import subprocess
    import sys
    import threading

    project_root = str(Path(__file__).resolve().parent.parent)
    main_script = os.path.join(project_root, "main.py")

    def _do_restart():
        import time
        time.sleep(0.3)  # Let HTTP response flush
        # Spawn shell that waits 2s (for port release) then starts new process
        subprocess.Popen(
            f'timeout /t 2 /nobreak > nul & "{sys.executable}" "{main_script}"',
            cwd=project_root,
            shell=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        os._exit(0)  # Kill current process — port released immediately

    threading.Thread(target=_do_restart, daemon=True).start()
    return {"status": "restarting"}


@app.post("/api/shutdown")
async def shutdown_server():
    """Shutdown the entire backend server process."""
    import threading

    def _do_shutdown():
        import time
        time.sleep(0.5)
        os._exit(0)

    threading.Thread(target=_do_shutdown, daemon=True).start()
    return {"status": "shutting_down"}



# ──────────────────────────────────────────────
# Account Group Endpoints
# ──────────────────────────────────────────────

@app.get("/api/groups")
async def get_groups():
    """Get all account groups."""
    return await database.get_all_groups()


@app.post("/api/groups")
async def create_group(body: dict):
    """Create a new account group."""
    import json
    name = body.get("name", "").strip()
    if not name:
        return {"error": "Name is required"}
    
    account_ids = body.get("account_ids", [])
    account_ids_json = json.dumps(account_ids)

    try:
        group_id = await database.create_group(name=name, account_ids=account_ids_json)
        return {"status": "created", "id": group_id}
    except Exception as e:
        if "UNIQUE" in str(e):
            return {"error": f"Group name '{name}' already exists"}
        return {"error": str(e)}


@app.put("/api/groups/{group_id}")
async def update_group(group_id: int, body: dict):
    """Update an account group."""
    import json
    name = body.get("name")
    if name is not None:
        name = name.strip()
        if not name:
            return {"error": "Name cannot be empty"}

    account_ids = body.get("account_ids")
    account_ids_json = json.dumps(account_ids) if account_ids is not None else None

    try:
        ok = await database.update_group(group_id, name=name, account_ids=account_ids_json)
        if ok:
            return {"status": "ok", "id": group_id}
        return {"error": "Group not found"}
    except Exception as e:
        if "UNIQUE" in str(e):
            return {"error": f"Group name '{name}' already exists"}
        return {"error": str(e)}


@app.delete("/api/groups/{group_id}")
async def delete_group(group_id: int):
    """Delete an account group."""
    ok = await database.delete_group(group_id)
    if ok:
        return {"status": "deleted"}
    return {"error": "Group not found"}


# ──────────────────────────────────────────────
# Startup
# ──────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    # Wire up WebSocket callback to task queue
    task_queue.set_ws_callback(ws_manager.broadcast_sync)

    # Init database
    database.init_sync()

    # Discover devices
    emulator_manager.discover()

    # Start background scheduler
    from backend.core.scheduler import start_scheduler
    start_scheduler()

    print(f"[API] Started on port {config.server_port}")
    print(f"[API] Devices found: {len(emulator_manager.get_all())}")

