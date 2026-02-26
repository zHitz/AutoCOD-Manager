"""
Macro Replay Engine — ADB-based playback of LDPlayer .record files.

Parses the .record JSON format and replays touch operations via
`adb shell input tap / swipe` commands with accurate timing.

Coordinate System:
    LDPlayer .record files store touch coordinates at 12x scale
    of the recording resolution. For example, on a 960x540 emulator:
        record_x=11040 → pixel_x = 11040/12 = 920
        record_y=4380  → pixel_y = 4380/12 = 365

    When replaying on a different resolution, coordinates are
    proportionally scaled.
"""
import json
import time
import threading
import subprocess
import os
from backend.config import config

ADB_PATH = config.adb_path

# LDPlayer .record coordinates use a 20x scale of the recording resolution.
# E.g., for 960x540: max_x = 960*20 = 19200, max_y = 540*20 = 10800.
# Verified via user empirical data: raw 17940 → pixel 900 (17940/900 ≈ 20).
COORD_SCALE = 20

# Track running macros: key = f"{serial}:{filename}", value = status dict
_running_macros = {}
_lock = threading.Lock()


def _get_adb_serial(index: int) -> str:
    """Convert LDPlayer instance index to ADB serial.
    LDPlayer assigns ADB ports as: 5554 + (index * 2).
    """
    port = 5554 + (index * 2)
    return f"emulator-{port}"


def _get_target_resolution(serial: str) -> tuple:
    """Get the target emulator's screen resolution via ADB."""
    try:
        result = subprocess.run(
            [ADB_PATH, "-s", serial, "shell", "wm", "size"],
            capture_output=True, text=True, timeout=5, encoding="utf-8",
        )
        # Output: "Physical size: 960x540"
        for line in result.stdout.strip().splitlines():
            if "size:" in line.lower():
                parts = line.split(":")[-1].strip().split("x")
                return int(parts[0]), int(parts[1])
    except Exception:
        pass
    return 960, 540  # fallback


def _adb_tap(serial: str, x: int, y: int):
    """Send a tap event via ADB."""
    subprocess.run(
        [ADB_PATH, "-s", serial, "shell",
         "input", "tap", str(x), str(y)],
        capture_output=True, timeout=5,
    )


def _adb_swipe(serial: str, x1: int, y1: int, x2: int, y2: int,
               duration_ms: int = 200):
    """Send a swipe event via ADB."""
    subprocess.run(
        [ADB_PATH, "-s", serial, "shell",
         "input", "swipe",
         str(x1), str(y1), str(x2), str(y2), str(duration_ms)],
        capture_output=True, timeout=10,
    )


def parse_record(filepath: str) -> dict:
    """Parse a .record file and return operations + metadata."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    operations = data.get("operations", [])
    record_info = data.get("recordInfo", {})

    return {
        "operations": operations,
        "info": record_info,
        "duration_ms": record_info.get("circleDuration", 0),
        "loop_times": record_info.get("loopTimes", 1),
        "record_width": record_info.get("resolutionWidth", 960),
        "record_height": record_info.get("resolutionHeight", 540),
    }


def _convert_coord(record_x, record_y,
                    record_w, record_h,
                    target_w, target_h):
    """Convert .record coordinates to ADB pixel coordinates.

    .record coords = pixel * 12 (in the recording resolution).
    If target resolution differs, scale proportionally.
    """
    # Step 1: Convert from 12x scale to record's pixel space
    px_x = record_x / COORD_SCALE
    px_y = record_y / COORD_SCALE

    # Step 2: Scale to target resolution if different
    if record_w != target_w or record_h != target_h:
        px_x = px_x * target_w / record_w
        px_y = px_y * target_h / record_h

    return int(round(px_x)), int(round(px_y))


def _replay_worker(serial: str, filepath: str, filename: str,
                    ws_callback=None):
    """Background thread that replays a macro on one emulator.

    Processes operations sequentially with proper timing:
    1. PutMultiTouch with state=1 → touch DOWN (save position)
    2. PutMultiTouch with empty points → release indicator
    3. PutMultiTouch with state=0 → touch UP
       - Compare with DOWN position: if movement > threshold → swipe, else → tap
    """
    key = f"{serial}:{filename}"

    try:
        record = parse_record(filepath)
        ops = record["operations"]
        loop_times = record["loop_times"]
        duration_ms = record["duration_ms"]
        rec_w = record["record_width"]
        rec_h = record["record_height"]

        # Get target emulator's actual resolution
        tgt_w, tgt_h = _get_target_resolution(serial)
        print(f"[MacroReplay] Record: {rec_w}x{rec_h} -> Target: {tgt_w}x{tgt_h}")

        # Count actionable touch events
        touch_count = 0
        for op in ops:
            if op.get("operationId") == "PutMultiTouch":
                pts = op.get("points", [])
                if len(pts) == 1 and pts[0].get("state") == 1:
                    touch_count += 1

        with _lock:
            _running_macros[key] = {
                "status": "running",
                "filename": filename,
                "serial": serial,
                "start_time": time.time(),
                "total_ops": touch_count,
                "completed_ops": 0,
                "current_loop": 1,
                "total_loops": loop_times,
                "duration_ms": duration_ms,
            }

        if ws_callback:
            ws_callback("macro_started", {
                "serial": serial,
                "filename": filename,
                "total_ops": touch_count,
                "duration_ms": duration_ms,
            })

        for loop in range(loop_times):
            with _lock:
                if key not in _running_macros:
                    break
                _running_macros[key]["current_loop"] = loop + 1

            prev_timing = 0
            completed = 0
            down_pos = None  # Track touch-down position
            down_timing = 0

            for op in ops:
                with _lock:
                    if key not in _running_macros:
                        break

                if op.get("operationId") != "PutMultiTouch":
                    continue

                timing = op.get("timing", 0)
                points = op.get("points", [])

                # Wait for proper timing
                delay = (timing - prev_timing) / 1000.0
                if delay > 0.001:
                    time.sleep(delay)
                prev_timing = timing

                if len(points) == 0:
                    # Empty points = release event, skip
                    continue

                if len(points) >= 1:
                    p = points[0]
                    state = p.get("state", 0)
                    ax, ay = _convert_coord(
                        p["x"], p["y"],
                        rec_w, rec_h, tgt_w, tgt_h,
                    )

                    if state == 1:
                        # Touch DOWN — save position
                        down_pos = (ax, ay)
                        down_timing = timing

                    elif state == 0 and down_pos is not None:
                        # Touch UP — determine tap vs swipe
                        dx = abs(ax - down_pos[0])
                        dy = abs(ay - down_pos[1])
                        dt = timing - down_timing

                        if dx > 10 or dy > 10:
                            # Significant movement → swipe
                            swipe_dur = max(50, dt)
                            _adb_swipe(serial,
                                       down_pos[0], down_pos[1],
                                       ax, ay, swipe_dur)
                            print(f"[MacroReplay] swipe ({down_pos[0]},{down_pos[1]}) → ({ax},{ay}) {swipe_dur}ms")
                        else:
                            # Tap at down position
                            _adb_tap(serial, down_pos[0], down_pos[1])
                            print(f"[MacroReplay] tap ({down_pos[0]},{down_pos[1]})")

                        completed += 1
                        down_pos = None

                        with _lock:
                            if key in _running_macros:
                                _running_macros[key]["completed_ops"] = completed

                        if ws_callback:
                            ws_callback("macro_progress", {
                                "serial": serial,
                                "filename": filename,
                                "completed": completed,
                                "total": touch_count,
                            })

        # Done
        elapsed = time.time() - _running_macros.get(key, {}).get(
            "start_time", time.time()
        )
        with _lock:
            if key in _running_macros:
                _running_macros[key]["status"] = "completed"
                _running_macros[key]["elapsed_ms"] = int(elapsed * 1000)

        if ws_callback:
            ws_callback("macro_completed", {
                "serial": serial,
                "filename": filename,
                "elapsed_ms": int(elapsed * 1000),
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        with _lock:
            if key in _running_macros:
                _running_macros[key]["status"] = "error"
                _running_macros[key]["error"] = str(e)

        if ws_callback:
            ws_callback("macro_failed", {
                "serial": serial,
                "filename": filename,
                "error": str(e),
            })


def start_replay(index: int, filepath: str, filename: str,
                  ws_callback=None) -> dict:
    """Start replaying a macro in a background thread."""
    serial = _get_adb_serial(index)
    key = f"{serial}:{filename}"

    with _lock:
        existing = _running_macros.get(key) 
        if existing and existing.get("status") == "running":
            return {"success": False, "error": "Macro already running"}

    record = parse_record(filepath)

    # Count touch events
    touch_count = 0
    for op in record["operations"]:
        if op.get("operationId") == "PutMultiTouch":
            pts = op.get("points", [])
            if len(pts) == 1 and pts[0].get("state") == 1:
                touch_count += 1

    thread = threading.Thread(
        target=_replay_worker,
        args=(serial, filepath, filename, ws_callback),
        daemon=True,
    )
    thread.start()

    return {
        "success": True,
        "serial": serial,
        "total_ops": touch_count,
        "duration_ms": record["duration_ms"],
        "loop_times": record["loop_times"],
    }


def stop_replay(index: int, filename: str) -> dict:
    """Stop a running macro replay."""
    serial = _get_adb_serial(index)
    key = f"{serial}:{filename}"

    with _lock:
        if key in _running_macros:
            del _running_macros[key]
            return {"success": True, "message": "Macro stopped"}
    return {"success": False, "error": "Macro not running"}


def get_status(index: int = None, filename: str = None) -> list:
    """Get status of running macros."""
    with _lock:
        if index is not None and filename:
            serial = _get_adb_serial(index)
            key = f"{serial}:{filename}"
            info = _running_macros.get(key)
            return [info] if info else []
        return list(_running_macros.values())
