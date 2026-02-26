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
    """List all registered emulators with status."""
    devices = emulator_manager.get_all()
    return [d.to_dict() for d in devices]


@app.post("/api/devices/refresh")
async def refresh_devices():
    """Re-discover ADB devices."""
    devices = emulator_manager.discover()
    return {"count": len(devices), "devices": [d.to_dict() for d in devices]}


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

    task_id = task_queue.submit_task(serial, tt)

    # Also save to DB
    try:
        await database.save_task_log(
            task_id=task_id,
            serial=serial,
            task_type=task_type,
            status="QUEUED",
        )
    except Exception:
        pass

    return {"status": "accepted", "task_id": task_id}


@app.post("/api/tasks/run-all")
async def run_all_tasks(task_type: str):
    """Submit a task for all online devices."""
    try:
        tt = TaskType(task_type)
    except ValueError:
        return {"status": "error", "msg": f"Invalid task type: {task_type}"}

    online = emulator_manager.get_online()
    if not online:
        # Try discover first
        online = emulator_manager.discover()
        online = [e for e in online if e.status == "ONLINE"]

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
    """Get task execution history."""
    return task_queue.get_history(limit)


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

    filepath = os.path.join(ldplayer_manager.OPERATIONS_DIR, filename)
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
    print(f"[API] Started on port {config.server_port}")
    print(f"[API] Devices found: {len(emulator_manager.get_all())}")

