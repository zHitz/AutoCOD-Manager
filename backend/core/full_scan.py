"""
Full Scan Pipeline - Orchestrator for capture -> PDF -> OCR -> parse -> save.

Runs the complete scan pipeline for one or more emulators in background threads.
Broadcasts WebSocket progress events at each step.
"""

import time
import threading
import os
from backend.core.macro_replay import _get_adb_serial

# Track scan state
_running_scans = {}
_scan_controls = {}
_lock = threading.Lock()

WORK_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "scan_captures"
)


class _ScanCancelled(Exception):
    """Raised when a background scan is asked to stop cooperatively."""


def _log_scan(
    serial: str,
    level: str,
    message: str,
    *,
    step: str | None = None,
    emulator_index: int | None = None,
    emulator_name: str | None = None,
):
    timestamp = time.strftime("%H:%M:%S")
    parts = [f"[{timestamp}]", "[FullScan]"]
    if serial:
        parts.append(f"[{serial}]")
    if emulator_index is not None:
        parts.append(f"[emu={emulator_index}]")
    if emulator_name:
        parts.append(f"[{emulator_name}]")
    if step:
        parts.append(f"[step={step}]")
    parts.append(f"[{level}]")
    print(" ".join(parts + [message]))


def _resource_value(res_entry, key: str = "total") -> int:
    if isinstance(res_entry, dict):
        return int(res_entry.get(key, 0) or 0)
    if isinstance(res_entry, (int, float)):
        return int(res_entry)
    return 0


def _resolve_ocr_mode(scan_config: dict | None) -> str:
    mode = str((scan_config or {}).get("ocr_mode") or "local_then_api").strip().lower()
    if mode in {"local_then_api", "local_only", "api_only"}:
        return mode
    return "local_then_api"


def _scan_worker(emulator_index: int, emulator_name: str, ws_callback=None, scan_config=None):
    """Background thread: runs full scan pipeline for one emulator."""
    serial = _get_adb_serial(emulator_index)
    key = f"scan-{emulator_index}"
    ocr_mode = _resolve_ocr_mode(scan_config)
    with _lock:
        control = _scan_controls.get(key, {})
    stop_event = control.get("stop_event")

    def _raise_if_stopped(stage: str = ""):
        if stop_event and stop_event.is_set():
            raise _ScanCancelled(f"Scan stop requested{f' during {stage}' if stage else ''}.")

    try:
        start_time = time.time()

        with _lock:
            _running_scans[key] = {
                "status": "running",
                "emulator_index": emulator_index,
                "emulator_name": emulator_name,
                "serial": serial,
                "step": "starting",
                "start_time": start_time,
                "ocr_mode": ocr_mode,
            }

        def _broadcast(step, detail=""):
            _raise_if_stopped(step)
            with _lock:
                if key in _running_scans:
                    _running_scans[key]["step"] = step
            _log_scan(
                serial,
                "INFO",
                detail or "Progress updated.",
                step=step,
                emulator_index=emulator_index,
                emulator_name=emulator_name,
            )
            if ws_callback:
                ws_callback(
                    "scan_progress",
                    {
                        "emulator_index": emulator_index,
                        "serial": serial,
                        "step": step,
                        "detail": detail,
                    },
                )

        _log_scan(
            serial,
            "START",
            "Background full scan worker started.",
            step="starting",
            emulator_index=emulator_index,
            emulator_name=emulator_name,
        )

        _raise_if_stopped("startup")
        _broadcast("extracting_id", "Extracting Game ID from profile.")

        import os
        from backend.config import config as app_config
        from backend.core.workflow.state_detector import GameStateDetector
        from backend.core.workflow import core_actions

        templates_dir = os.path.join(os.path.dirname(__file__), "workflow", "templates")
        detector = GameStateDetector(app_config.adb_path, templates_dir)

        # Auto-detect which game provider is on this emulator
        detected_provider = core_actions.detect_provider_from_emulator(serial, app_config.adb_path)
        APP_PACKAGE = core_actions.get_package_for_provider(detected_provider)
        _log_scan(
            serial, "INFO",
            f"Detected provider: {detected_provider} → package: {APP_PACKAGE}",
            step="extracting_id", emulator_index=emulator_index, emulator_name=emulator_name,
        )
        game_id = ""
        try:
            _log_scan(
                serial,
                "INFO",
                f"Detector initialized with templates at: {templates_dir}",
                step="extracting_id",
                emulator_index=emulator_index,
                emulator_name=emulator_name,
            )

            if core_actions.startup_to_lobby(serial, detector, APP_PACKAGE):
                _raise_if_stopped("extracting_id")
                _log_scan(
                    serial,
                    "INFO",
                    "Lobby confirmed. Opening profile to copy Game ID.",
                    step="extracting_id",
                    emulator_index=emulator_index,
                    emulator_name=emulator_name,
                )
                if core_actions.go_to_profile(serial, detector):
                    player_id = core_actions.extract_player_id(serial, detector)
                    if player_id:
                        game_id = player_id
                        _broadcast("id_extracted", f"Game ID extracted: {game_id}")
                    else:
                        _log_scan(
                            serial,
                            "WARNING",
                            "Profile opened but clipboard extraction returned empty or stale data.",
                            step="extracting_id",
                            emulator_index=emulator_index,
                            emulator_name=emulator_name,
                        )

                    core_actions.back_to_lobby(serial, detector)
                else:
                    _log_scan(
                        serial,
                        "ERROR",
                        "Failed to open profile while extracting Game ID.",
                        step="extracting_id",
                        emulator_index=emulator_index,
                        emulator_name=emulator_name,
                    )
            else:
                _log_scan(
                    serial,
                    "ERROR",
                    "startup_to_lobby() returned False during Game ID extraction.",
                    step="extracting_id",
                    emulator_index=emulator_index,
                    emulator_name=emulator_name,
                )

        except Exception as e:
            _log_scan(
                serial,
                "ERROR",
                f"Game ID extraction raised exception: {e}",
                step="extracting_id",
                emulator_index=emulator_index,
                emulator_name=emulator_name,
            )

        if not game_id:
            _broadcast(
                "failed",
                "Cannot identify account. Game ID extraction failed. Scan aborted.",
            )
            raise RuntimeError("Game ID extraction failed. Aborting full scan.")

        _raise_if_stopped("capturing")
        _broadcast("capturing", "Navigating and capturing screenshots.")
        from backend.core.screen_capture import run_full_capture_modern

        def progress_cb(phase, step, total):
            _raise_if_stopped(f"capture:{phase}")
            _broadcast(
                f"capturing ({step}/{total})",
                f"Capture phase {step}/{total} started: {phase}",
            )

        pdf_path = run_full_capture_modern(
            serial, detector, WORK_DIR, progress_callback=progress_cb
        )

        if not pdf_path:
            raise RuntimeError(
                "Screenshot capture failed. Capture pipeline returned no PDF path."
            )

        _log_scan(
            serial,
            "INFO",
            f"Capture pipeline completed. PDF ready at: {pdf_path}",
            step="capturing",
            emulator_index=emulator_index,
            emulator_name=emulator_name,
        )

        from backend.core.local_scan_ocr import run_local_scan_ocr
        from backend.core.ocr_client import run_ocr

        device_dir = os.path.dirname(pdf_path)
        ocr_result = None

        if ocr_mode != "api_only":
            _raise_if_stopped("local_ocr")
            _broadcast(
                "ocr_processing",
                f"Running local OCR on captured screenshots (mode={ocr_mode}).",
            )
            ocr_result = run_local_scan_ocr(device_dir)
            if ocr_result["success"]:
                _log_scan(
                    serial,
                    "INFO",
                    "Local OCR succeeded from captured screenshots.",
                    step="ocr_processing",
                    emulator_index=emulator_index,
                    emulator_name=emulator_name,
                )
            elif ocr_mode == "local_only":
                raise RuntimeError(
                    f"Local OCR failed in local_only mode: {ocr_result['error']}"
                )
            else:
                _log_scan(
                    serial,
                    "WARNING",
                    f"Local OCR failed or incomplete: {ocr_result['error']}. Falling back to OCR API.",
                    step="ocr_processing",
                    emulator_index=emulator_index,
                    emulator_name=emulator_name,
                )

        if ocr_mode == "api_only" or (ocr_mode == "local_then_api" and not ocr_result["success"]):
            api_result = None
            max_ocr_retries = 3
            for ocr_attempt in range(1, max_ocr_retries + 1):
                _raise_if_stopped(f"ocr_api_attempt_{ocr_attempt}")
                _broadcast(
                    "ocr_processing",
                    f"Uploading PDF to OCR API (attempt {ocr_attempt}/{max_ocr_retries}).",
                )
                api_result = run_ocr(pdf_path)
                if api_result["success"]:
                    _log_scan(
                        serial,
                        "INFO",
                        f"OCR API succeeded on attempt {ocr_attempt}/{max_ocr_retries}.",
                        step="ocr_processing",
                        emulator_index=emulator_index,
                        emulator_name=emulator_name,
                    )
                    break
                _log_scan(
                    serial,
                    "WARNING",
                    f"OCR API attempt {ocr_attempt}/{max_ocr_retries} failed: {api_result['error']}",
                    step="ocr_processing",
                    emulator_index=emulator_index,
                    emulator_name=emulator_name,
                )
                if ocr_attempt < max_ocr_retries:
                    _broadcast(
                        "ocr_retry",
                        f"OCR API failed, retrying ({ocr_attempt}/{max_ocr_retries}).",
                    )
                    time.sleep(2)

            if api_result and api_result["success"]:
                ocr_result = api_result
            else:
                fallback_error = api_result["error"] if api_result else (ocr_result or {}).get("error", "unknown OCR error")
                if ocr_mode == "api_only":
                    raise RuntimeError(f"OCR API failed in api_only mode: {fallback_error}")
                raise RuntimeError(
                    f"Local OCR failed and OCR API fallback failed: {fallback_error}"
                )

        _raise_if_stopped("parsing")
        _broadcast("parsing", "Parsing OCR results.")

        parsed_data = ocr_result["parsed"]
        raw_text = ocr_result["text"]

        _raise_if_stopped("validating")
        _broadcast("validating", "Verifying OCR data integrity.")

        res = parsed_data.get("resources", {})
        total_resources = sum(
            [
                _resource_value(res.get("gold", 0)),
                _resource_value(res.get("wood", 0)),
                _resource_value(res.get("ore", 0)),
                _resource_value(res.get("mana", 0)),
            ]
        )
        power = parsed_data.get("power", 0)
        hall = parsed_data.get("hall_level", 0)
        market = parsed_data.get("market_level", 0)

        if power == 0 and hall == 0 and market == 0 and total_resources == 0:
            raise RuntimeError(
                "OCR data validation failed. All critical fields are 0. "
                "Screenshot capture likely failed. Scan aborted to protect existing data."
            )

        try:
            import sqlite3
            from backend.config import config as _config

            prev = None
            with sqlite3.connect(_config.db_path) as conn:
                conn.row_factory = sqlite3.Row
                if game_id:
                    cursor = conn.execute(
                        """SELECT s.*, e.emu_index as emulator_index, e.serial, e.name as emulator_name
                           FROM scan_snapshots s
                           JOIN emulators e ON s.emulator_id = e.id
                           WHERE s.game_id = ?
                           ORDER BY s.created_at DESC LIMIT 1""",
                        (game_id,),
                    )
                else:
                    cursor = conn.execute(
                        """SELECT s.*, e.emu_index as emulator_index, e.serial, e.name as emulator_name
                           FROM scan_snapshots s
                           JOIN emulators e ON s.emulator_id = e.id
                           WHERE e.emu_index = ?
                           ORDER BY s.created_at DESC LIMIT 1""",
                        (emulator_index,),
                    )
                row = cursor.fetchone()
                if row:
                    prev = dict(row)
                    snap_id = prev["id"]
                    res_cursor = conn.execute(
                        "SELECT * FROM scan_resources WHERE snapshot_id = ?",
                        (snap_id,),
                    )
                    for res_row in res_cursor.fetchall():
                        rd = dict(res_row)
                        rtype = rd["resource_type"]
                        prev[rtype] = rd.get("total_value", 0)

            if prev:
                prev_hall = prev.get("hall_level", 0)
                prev_power = prev.get("power", 0)
                prev_pet_token = prev.get("pet_token", 0)

                if prev_hall > 0 and hall == 0:
                    _log_scan(
                        serial,
                        "WARNING",
                        f"Hall was {prev_hall}, new OCR says 0. Keeping previous value.",
                        step="validating",
                        emulator_index=emulator_index,
                        emulator_name=emulator_name,
                    )
                    parsed_data["hall_level"] = prev_hall

                if prev_power > 0 and power == 0:
                    _log_scan(
                        serial,
                        "WARNING",
                        f"Power was {prev_power}, new OCR says 0. Keeping previous value.",
                        step="validating",
                        emulator_index=emulator_index,
                        emulator_name=emulator_name,
                    )
                    parsed_data["power"] = prev_power

                prev_market = prev.get("market_level", 0)
                if prev_market > 0 and market == 0:
                    _log_scan(
                        serial,
                        "WARNING",
                        f"Market was {prev_market}, new OCR says 0. Keeping previous value.",
                        step="validating",
                        emulator_index=emulator_index,
                        emulator_name=emulator_name,
                    )
                    parsed_data["market_level"] = prev_market

                if prev_pet_token > 0 and parsed_data.get("pet_token", 0) == 0:
                    _log_scan(
                        serial,
                        "WARNING",
                        f"Pet token was {prev_pet_token}, new OCR says 0. Keeping previous value.",
                        step="validating",
                        emulator_index=emulator_index,
                        emulator_name=emulator_name,
                    )
                    parsed_data["pet_token"] = prev_pet_token

                for key in ["gold", "wood", "ore", "mana"]:
                    prev_val = prev.get(key, 0) or 0
                    if prev_val > 0 and _resource_value(res.get(key, 0)) == 0:
                        _log_scan(
                            serial,
                            "WARNING",
                            f"{key} was {prev_val}, new OCR says 0. Keeping previous value.",
                            step="validating",
                            emulator_index=emulator_index,
                            emulator_name=emulator_name,
                        )
                        if isinstance(parsed_data["resources"].get(key), dict):
                            parsed_data["resources"][key]["total"] = prev_val
                            if not parsed_data["resources"][key].get("bag"):
                                parsed_data["resources"][key]["bag"] = prev_val
                        else:
                            parsed_data["resources"][key] = prev_val

        except Exception as val_err:
            _log_scan(
                serial,
                "WARNING",
                f"Validation comparison skipped: {val_err}",
                step="validating",
                emulator_index=emulator_index,
                emulator_name=emulator_name,
            )

        _raise_if_stopped("saving")
        _broadcast("saving", "Saving to database.")
        import asyncio
        from backend.storage.database import database

        elapsed_ms = int((time.time() - start_time) * 1000)

        async def _save():
            snap_id = await database.save_scan_snapshot(
                emulator_index=emulator_index,
                serial=serial,
                emulator_name=emulator_name,
                parsed_data=parsed_data,
                scan_status="completed",
                scan_duration_ms=elapsed_ms,
                raw_ocr_text=raw_text,
                game_id=game_id,
            )

            link_result = None
            if game_id:
                emu_id = await database.get_emulator_id(emu_index=emulator_index)
                if emu_id:
                    lord_name = parsed_data.get("lord_name", "")
                    link_result = await database.auto_link_account(
                        emulator_id=emu_id,
                        game_id=game_id,
                        lord_name=lord_name,
                        snapshot_id=snap_id,
                        provider=detected_provider,
                    )
            return snap_id, link_result

        snap_id, link_result = asyncio.run(_save())

        with _lock:
            _running_scans[key] = {
                "status": "completed",
                "emulator_index": emulator_index,
                "emulator_name": emulator_name,
                "serial": serial,
                "step": "done",
                "elapsed_ms": elapsed_ms,
                "data": parsed_data,
                "game_id": game_id,
                "link_result": link_result,
            }

        if ws_callback:
            ws_callback(
                "scan_completed",
                {
                    "emulator_index": emulator_index,
                    "serial": serial,
                    "elapsed_ms": elapsed_ms,
                    "data": parsed_data,
                    "game_id": game_id,
                    "link_result": link_result,
                },
            )

        _log_scan(
            serial,
            "SUCCESS",
            f"Completed in {elapsed_ms}ms | Game ID: {game_id or 'N/A'}",
            step="done",
            emulator_index=emulator_index,
            emulator_name=emulator_name,
        )

    except _ScanCancelled as e:
        _log_scan(
            serial,
            "WARNING",
            str(e),
            step="stopped",
            emulator_index=emulator_index,
            emulator_name=emulator_name,
        )

        with _lock:
            _running_scans[key] = {
                "status": "stopped",
                "emulator_index": emulator_index,
                "serial": serial,
                "step": "stopped",
                "error": str(e),
            }

    except Exception as e:
        import traceback

        traceback.print_exc()
        _log_scan(
            serial,
            "ERROR",
            f"Worker failed with exception: {e}",
            step="error",
            emulator_index=emulator_index,
            emulator_name=emulator_name,
        )

        with _lock:
            _running_scans[key] = {
                "status": "failed",
                "emulator_index": emulator_index,
                "serial": serial,
                "step": "error",
                "error": str(e),
            }

        if ws_callback:
            ws_callback(
                "scan_failed",
                {
                    "emulator_index": emulator_index,
                    "serial": serial,
                    "error": str(e),
                },
            )
    finally:
        with _lock:
            _scan_controls.pop(key, None)


def start_full_scan(
    emulator_index: int, emulator_name: str = "", ws_callback=None, scan_config: dict | None = None
) -> dict:
    """Start a full scan for one emulator in a background thread."""
    key = f"scan-{emulator_index}"
    ocr_mode = _resolve_ocr_mode(scan_config)

    with _lock:
        existing = _running_scans.get(key)
        if existing and existing.get("status") in ("running", "stopping"):
            start_t = existing.get("start_time", 0)
            if time.time() - start_t > 1200:  # 20 minutes timeout
                print(f"[FullScan] ⚠️ Zombie scan detected on #{emulator_index} (>20m). Forcing new scan.")
            else:
                return {
                    "success": False,
                    "error": f"Scan already running on #{emulator_index}",
                }
        # Clear previous terminal scan state for this emulator
        if existing and existing.get("status") in ("completed", "failed", "stopped"):
            del _running_scans[key]
        stop_event = threading.Event()
        _scan_controls[key] = {"stop_event": stop_event, "thread": None}

    thread = threading.Thread(
        target=_scan_worker,
        args=(emulator_index, emulator_name, ws_callback, scan_config),
        daemon=True,
    )
    with _lock:
        if key in _scan_controls:
            _scan_controls[key]["thread"] = thread
    thread.start()

    return {
        "success": True,
        "emulator_index": emulator_index,
        "serial": _get_adb_serial(emulator_index),
        "ocr_mode": ocr_mode,
    }


def stop_scan(emulator_index: int, wait_timeout: float = 0) -> dict:
    """Request a running scan to stop cooperatively and optionally wait for exit."""
    key = f"scan-{emulator_index}"
    thread = None
    with _lock:
        control = _scan_controls.get(key)
        status = _running_scans.get(key)
        if control:
            control["stop_event"].set()
            thread = control.get("thread")
        if status and status.get("status") == "running":
            _running_scans[key]["status"] = "stopping"
            _running_scans[key]["step"] = "stopping"

    if not control and not status:
        return {"success": False, "error": "Scan not running"}

    joined = False
    if thread and wait_timeout > 0:
        thread.join(wait_timeout)
        joined = not thread.is_alive()

    return {
        "success": True,
        "stopping": True,
        "joined": joined,
    }


def is_scan_active(emulator_index: int) -> bool:
    """Return True while the worker thread for this emulator is still alive."""
    key = f"scan-{emulator_index}"
    with _lock:
        thread = (_scan_controls.get(key) or {}).get("thread")
    return bool(thread and thread.is_alive())


def get_scan_status() -> list[dict]:
    """Get status of all scans."""
    with _lock:
        return list(_running_scans.values())
