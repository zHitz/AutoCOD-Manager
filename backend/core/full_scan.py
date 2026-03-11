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
_lock = threading.Lock()

WORK_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "scan_captures"
)


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


def _scan_worker(emulator_index: int, emulator_name: str, ws_callback=None):
    """Background thread: runs full scan pipeline for one emulator."""
    serial = _get_adb_serial(emulator_index)
    key = f"scan-{emulator_index}"

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
            }

        def _broadcast(step, detail=""):
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

        _broadcast("extracting_id", "Extracting Game ID from profile.")

        import os
        from backend.config import config as app_config
        from backend.core.workflow.state_detector import GameStateDetector
        from backend.core.workflow import core_actions

        templates_dir = os.path.join(os.path.dirname(__file__), "workflow", "templates")
        detector = GameStateDetector(app_config.adb_path, templates_dir)

        APP_PACKAGE = "com.farlightgames.samo.gp.vn"
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

        _broadcast("capturing", "Navigating and capturing screenshots.")
        from backend.core.screen_capture import run_full_capture_modern

        def progress_cb(phase, step, total):
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

        from backend.core.ocr_client import run_ocr

        ocr_result = None
        max_ocr_retries = 3
        for ocr_attempt in range(1, max_ocr_retries + 1):
            _broadcast(
                "ocr_processing",
                f"Uploading PDF to OCR API (attempt {ocr_attempt}/{max_ocr_retries}).",
            )
            ocr_result = run_ocr(pdf_path)
            if ocr_result["success"]:
                _log_scan(
                    serial,
                    "INFO",
                    f"OCR succeeded on attempt {ocr_attempt}/{max_ocr_retries}.",
                    step="ocr_processing",
                    emulator_index=emulator_index,
                    emulator_name=emulator_name,
                )
                break
            _log_scan(
                serial,
                "WARNING",
                f"OCR attempt {ocr_attempt}/{max_ocr_retries} failed: {ocr_result['error']}",
                step="ocr_processing",
                emulator_index=emulator_index,
                emulator_name=emulator_name,
            )
            if ocr_attempt < max_ocr_retries:
                _broadcast(
                    "ocr_retry",
                    f"OCR failed, retrying ({ocr_attempt}/{max_ocr_retries}).",
                )
                time.sleep(2)

        if not ocr_result or not ocr_result["success"]:
            raise RuntimeError(
                f"OCR failed after {max_ocr_retries} attempts: {ocr_result['error']}"
            )

        _broadcast("parsing", "Parsing OCR results.")

        parsed_data = ocr_result["parsed"]
        raw_text = ocr_result["text"]

        _broadcast("validating", "Verifying OCR data integrity.")

        res = parsed_data.get("resources", {})
        total_resources = sum(
            [
                res.get("gold", 0),
                res.get("wood", 0),
                res.get("ore", 0),
                res.get("mana", 0),
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
                        prev[rtype] = rd.get("bag_value", 0)

            if prev:
                prev_hall = prev.get("hall_level", 0)
                prev_power = prev.get("power", 0)

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

                for key in ["gold", "wood", "ore", "mana"]:
                    prev_val = prev.get(key, 0) or 0
                    if prev_val > 0 and res.get(key, 0) == 0:
                        _log_scan(
                            serial,
                            "WARNING",
                            f"{key} was {prev_val}, new OCR says 0. Keeping previous value.",
                            step="validating",
                            emulator_index=emulator_index,
                            emulator_name=emulator_name,
                        )
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


def start_full_scan(
    emulator_index: int, emulator_name: str = "", ws_callback=None
) -> dict:
    """Start a full scan for one emulator in a background thread."""
    key = f"scan-{emulator_index}"

    with _lock:
        existing = _running_scans.get(key)
        if existing and existing.get("status") == "running":
            start_t = existing.get("start_time", 0)
            if time.time() - start_t > 1200:  # 20 minutes timeout
                print(f"[FullScan] ⚠️ Zombie scan detected on #{emulator_index} (>20m). Forcing new scan.")
            else:
                return {
                    "success": False,
                    "error": f"Scan already running on #{emulator_index}",
                }

    thread = threading.Thread(
        target=_scan_worker,
        args=(emulator_index, emulator_name, ws_callback),
        daemon=True,
    )
    thread.start()

    return {
        "success": True,
        "emulator_index": emulator_index,
        "serial": _get_adb_serial(emulator_index),
    }


def stop_scan(emulator_index: int) -> dict:
    """Stop a running scan."""
    key = f"scan-{emulator_index}"
    with _lock:
        if key in _running_scans:
            del _running_scans[key]
            return {"success": True}
    return {"success": False, "error": "Scan not running"}


def get_scan_status() -> list[dict]:
    """Get status of all scans."""
    with _lock:
        return list(_running_scans.values())
