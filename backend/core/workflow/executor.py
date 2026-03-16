import asyncio
import time
from typing import Callable, Coroutine
from backend.core.workflow import core_actions
from backend.core.workflow import adb_helper
from backend.core.workflow.state_detector import GameStateDetector
from backend.core import full_scan as full_scan_module

# To be resilient, we'll keep a mapped dictionary of function_ids to actual python logic.
# These function_ids match what is defined in workflow_registry.py


async def execute_recipe(
    emulator_index: int,
    emulator_name: str,
    steps: list,
    ws_callback: Callable[[dict], Coroutine] = None,
):
    """
    Executes a list of workflow steps sequentially on the given emulator via ADB.
    Reports progress and logs via the provided WebSocket callback if available.
    """
    serial = f"emulator-{5554 + emulator_index * 2}"
    total_steps = len(steps)
    from backend.config import config
    import os

    # Resolve the standard templates directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "templates")

    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    async def log(msg: str, log_type: str = "info"):
        print(f"[{emulator_name}] {msg}")
        if ws_callback:
            # handle both async and sync callbacks just in case, or just call it directly since broadcast_sync is sync
            import inspect

            data = {
                "emulator_index": emulator_index,
                "log_type": log_type,
                "message": msg,
            }
            if inspect.iscoroutinefunction(ws_callback):
                await ws_callback("workflow_log", data)
            else:
                ws_callback("workflow_log", data)

    async def progress(current: int, total: int):
        if ws_callback:
            import inspect

            data = {
                "emulator_index": emulator_index,
                "current": current,
                "total": total,
            }
            if inspect.iscoroutinefunction(ws_callback):
                await ws_callback("workflow_progress", data)
            else:
                ws_callback("workflow_progress", data)

    async def status(state: str):
        if ws_callback:
            import inspect

            data = {
                "emulator_index": emulator_index,
                "status": state,  # e.g., "RUNNING", "SUCCESS", "ERROR"
            }
            if inspect.iscoroutinefunction(ws_callback):
                await ws_callback("workflow_status", data)
            else:
                ws_callback("workflow_status", data)

    await status("RUNNING")
    await log(f"▶ Workflow execution started on {emulator_name}", "info")

    all_ok = True
    _activity_meta = {}  # Collects metadata from dict-returning core_actions

    try:
        # Step Execution Loop
        for i, step in enumerate(steps):
            fn_id = step.get("function_id")
            config = step.get("config") or {}

            await log(f"[{i + 1}/{total_steps}] Executing {fn_id}...", "run")
            await progress(i, total_steps)

            # --- MAP FUNCTION IDS TO REAL ACTIONS ---
            ok = True

            # Common Actions
            if fn_id == "flow_delay":
                secs = int(config.get("seconds", 2))
                await asyncio.sleep(secs)

            elif fn_id == "act_click_xy":
                x = int(config.get("x", 0))
                y = int(config.get("y", 0))
                await asyncio.to_thread(adb_helper.tap, serial, x, y)
                await asyncio.sleep(0.5)

            elif fn_id == "act_swipe":
                x1 = int(config.get("startX", 0))
                y1 = int(config.get("startY", 0))
                x2 = int(config.get("endX", 0))
                y2 = int(config.get("endY", 0))
                duration = int(config.get("durationMs", 500))
                await asyncio.to_thread(
                    adb_helper.swipe, serial, x1, y1, x2, y2, duration
                )
                await asyncio.sleep(0.5)

            elif fn_id == "act_input_text":
                text = str(config.get("text", ""))
                await asyncio.to_thread(adb_helper.input_text, serial, text)
                await asyncio.sleep(1)

            # App/System Controls
            elif fn_id == "sys_start_app":
                pkg = config.get("package", "com.farlightgames.samo.gp.vn")
                was_running = await asyncio.to_thread(
                    core_actions.ensure_app_running, serial, pkg
                )
                if was_running is None:
                    ok = False  # App launch failed entirely
                elif not was_running:
                    await asyncio.sleep(10)  # Give it time to boot up

            elif fn_id == "sys_close_app":
                pkg = config.get("package", "com.farlightgames.samo.gp.vn")
                await asyncio.to_thread(adb_helper.kill_app, serial, pkg)
                await asyncio.sleep(2)

            elif fn_id in ("sys_back_btn", "adb_press_back"):
                await asyncio.to_thread(adb_helper.press_back, serial)
                await asyncio.sleep(1.5)

            # ── Startup / Boot ──
            elif fn_id == "startup_to_lobby":
                timeout = int(config.get("timeout", 120))
                ok = await asyncio.to_thread(
                    core_actions.startup_to_lobby,
                    serial,
                    detector,
                    package_name="com.farlightgames.samo.gp.vn",
                    load_timeout=timeout,
                )

            # ── Full Scan ──
            elif fn_id == "scan_full":
                import asyncio as _aio

                result = await asyncio.to_thread(
                    full_scan_module.start_full_scan,
                    emulator_index,
                    emulator_name,
                    ws_callback=ws_callback,
                )
                if result and not result.get("success", True):
                    await log(
                        f"  Full scan reported error: {result.get('error', 'unknown')}",
                        "err",
                    )
                    ok = False
                else:
                    await log("  Full Scan started, waiting for completion...", "info")
                    scan_started_wall = time.time()
                    started_at = _aio.get_event_loop().time()
                    max_wait_sec = int(config.get("max_wait_sec", 900))
                    poll_count = 0
                    seen_scan_entry = False
                    missing_after_seen = 0
                    while True:
                        poll_count += 1
                        statuses = full_scan_module.get_scan_status()
                        scan_info = None
                        for s in statuses:
                            if str(s.get("emulator_index")) == str(emulator_index):
                                scan_info = s
                                break

                        if scan_info:
                            seen_scan_entry = True
                            missing_after_seen = 0
                        elif seen_scan_entry:
                            missing_after_seen += 1

                        scan_status = (scan_info or {}).get("status", "")
                        scan_step = (scan_info or {}).get("step", "")

                        # Print debug info to terminal so we can see what's happening
                        print(
                            f"[{emulator_name}] Polling scan_full... status: {scan_status or 'None'} | step: {scan_step or 'None'}"
                        )

                        # Status can be inconsistent across producers; use both status and step.
                        if scan_info and (
                            scan_status in ["completed", "failed", "error"]
                            or scan_step in ["done", "failed", "error"]
                        ):
                            if scan_status in ["failed", "error"] or scan_step in ["failed", "error"]:
                                await log(
                                    f"  Full scan failed: {scan_info.get('error')}",
                                    "err",
                                )
                                ok = False
                            else:
                                await log("  Full Scan completed", "ok")
                            break

                        # If scan entry disappeared after being observed, treat it as abnormal termination.
                        if seen_scan_entry and missing_after_seen >= 3:
                            await log(
                                "  Full scan status disappeared unexpectedly.",
                                "err",
                            )
                            ok = False
                            break

                        # Fallback: trust DB if a fresh completed snapshot exists for this emulator.
                        # This avoids indefinite "running/validating" loops when in-memory scan state drifts.
                        if poll_count % 3 == 0:
                            try:
                                from datetime import datetime
                                from backend.storage.database import database as _db

                                latest_scan = await _db.get_emulator_data(
                                    emulator_index=emulator_index
                                )
                                if latest_scan and str(latest_scan.get("scan_status", "")).lower() == "completed":
                                    created_at_raw = latest_scan.get("created_at", "")
                                    created_ts = None
                                    if created_at_raw:
                                        try:
                                            from datetime import timezone
                                            dt_str = str(created_at_raw).replace("Z", "")
                                            time_obj = datetime.fromisoformat(dt_str)
                                            if time_obj.tzinfo is None:
                                                time_obj = time_obj.replace(tzinfo=timezone.utc)
                                            created_ts = time_obj.timestamp()
                                        except Exception:
                                            created_ts = None

                                    if created_ts and created_ts >= (scan_started_wall - 30):
                                        await log(
                                            "  Full Scan completed (verified from DB snapshot)",
                                            "ok",
                                        )
                                        break
                            except Exception as db_check_err:
                                print(
                                    f"[{emulator_name}] scan_full DB completion check error: {db_check_err}"
                                )

                        # Guardrail: don't block workflow forever if scan state gets stuck.
                        elapsed = _aio.get_event_loop().time() - started_at
                        if elapsed > max_wait_sec:
                            await log(
                                f"  Full Scan timed out after {max_wait_sec}s (last status={scan_status or 'unknown'}, step={scan_step or 'unknown'})",
                                "err",
                            )
                            ok = False
                            break

                        # Optional heartbeat in workflow log every 5 polls.
                        if poll_count % 5 == 0 and scan_info:
                            await log(
                                f"  waiting... status={scan_status or 'unknown'}, step={scan_step or 'unknown'}",
                                "info",
                            )

                        await _aio.sleep(2)

                    # Force-clear stale scan state after polling exits.
                    # This prevents the next account on the same emulator
                    # from hitting "Scan already running" due to leftover
                    # in-memory state (e.g. when poll exited via DB fallback
                    # while the background thread hadn't updated its status).
                    scan_key = f"scan-{emulator_index}"
                    with full_scan_module._lock:
                        leftover = full_scan_module._running_scans.get(scan_key)
                        if leftover and leftover.get("status") == "running":
                            print(
                                f"[{emulator_name}] Clearing stale scan state for "
                                f"#{emulator_index} (was still 'running' after poll exit)"
                            )
                            del full_scan_module._running_scans[scan_key]

            # ── ADB Tap (registry id: adb_tap) ──
            elif fn_id == "adb_tap":
                x = int((config or {}).get("x", 0))
                y = int((config or {}).get("y", 0))
                await asyncio.to_thread(adb_helper.tap, serial, x, y)
                await asyncio.sleep(0.5)

            # ── Check Game State (registry id: check_state) ──
            elif fn_id == "check_state":
                current_state = await asyncio.to_thread(detector.check_state, serial)
                await log(f"  Detected State: {current_state}", "info")

            # ── Run Macro (registry id: run_macro) ──
            elif fn_id == "run_macro":
                from backend.core import macro_replay
                from backend.core import ldplayer_manager
                import asyncio as _aio

                macro_file = (config or {}).get("file", "")
                loop_count = int((config or {}).get("loop", 1))
                if macro_file:
                    import os

                    filepath = os.path.join(
                        ldplayer_manager._get_operations_dir(), macro_file
                    )
                    if os.path.exists(filepath):
                        for loop_i in range(loop_count):
                            await log(
                                f"  Macro '{macro_file}' loop {loop_i + 1}/{loop_count}",
                                "info",
                            )
                            res = await asyncio.to_thread(
                                macro_replay.start_replay,
                                emulator_index,
                                filepath,
                                macro_file,
                                ws_callback=ws_callback,
                            )
                            if res and not res.get("success", True):
                                await log(
                                    f"  Macro start error: {res.get('error', 'unknown')}",
                                    "err",
                                )
                                ok = False
                                break

                            while True:
                                statuses = macro_replay.get_status()
                                # Key format in macro_replay: f"{serial}:{filename}"
                                macro_info = None
                                for s in statuses:
                                    if (
                                        s.get("serial") == serial
                                        and s.get("filename") == macro_file
                                    ):
                                        macro_info = s
                                        break

                                if not macro_info or macro_info.get("status") in [
                                    "completed",
                                    "error",
                                    "failed",
                                ]:
                                    if macro_info and macro_info.get("status") in [
                                        "error",
                                        "failed",
                                    ]:
                                        await log(
                                            f"  Macro failed: {macro_info.get('error', 'unknown')}",
                                            "err",
                                        )
                                        ok = False
                                    break
                                await _aio.sleep(2)

                            if not ok:
                                break
                    else:
                        await log(f"  Macro file not found: {macro_file}", "err")
                        ok = False
                else:
                    await log("  No macro file specified", "err")
                    ok = False

            # Game Navigation Macros
            elif fn_id == "nav_to_lobby":
                ok = await asyncio.to_thread(
                    core_actions.back_to_lobby, serial, detector
                )

            elif fn_id == "nav_to_profile":
                ok = await asyncio.to_thread(
                    core_actions.go_to_profile, serial, detector
                )

            elif fn_id == "nav_to_items":
                ok = await asyncio.to_thread(
                    core_actions.go_to_resources, serial, detector
                )

            # Advanced / State Dependent
            elif fn_id == "adv_detect_state":
                current_state = await asyncio.to_thread(detector.check_state, serial)
                await log(f"  Detected State: {current_state}", "info")

            elif fn_id == "adv_copy_id":
                player_id = await asyncio.to_thread(
                    core_actions.extract_player_id, serial, detector
                )
                if player_id:
                    await log(f"  Successfully copied Player ID: {player_id}", "ok")
                else:
                    await log("  Failed to extract Player ID.", "err")
                    ok = False

            elif fn_id == "nav_to_pet_token":
                ok = await asyncio.to_thread(
                    core_actions.go_to_pet_token, serial, detector
                )

            elif fn_id == "nav_to_capture_pet":
                ok = await asyncio.to_thread(
                    core_actions.go_to_capture_pet, serial, detector
                )

            elif fn_id == "nav_to_market":
                ok = await asyncio.to_thread(
                    core_actions.go_to_market, serial, detector
                )

            elif fn_id == "nav_to_resources":
                ok = await asyncio.to_thread(
                    core_actions.go_to_resources, serial, detector
                )

            elif fn_id == "nav_to_hall":
                ok = await asyncio.to_thread(core_actions.go_to_hall, serial, detector)

            elif fn_id == "nav_to_rss_center_farm":
                ok = await asyncio.to_thread(
                    core_actions.go_to_rss_center_farm, serial, detector
                )

            elif fn_id == "nav_to_farming":
                resource_type = (config or {}).get("resource_type", "wood")
                ok = await asyncio.to_thread(
                    core_actions.go_to_farming,
                    serial,
                    detector,
                    resource_type=resource_type,
                )

            elif fn_id == "check_mail":
                mail_type = (config or {}).get("mail_type", "all")
                ok = await asyncio.to_thread(
                    core_actions.check_mail, serial, detector, mail_type=mail_type
                )

            elif fn_id == "claim_city_resources":
                claimed = await asyncio.to_thread(
                    core_actions.claim_city_resources, serial, detector
                )
                # claim_city_resources returns int (count), not bool.
                # 0 claimed is still a success (nothing to collect).
                ok = claimed is not None
                await log(f"  Claimed {claimed} city resources", "info")

            elif fn_id == "train_troops":
                training_list = []
                for house in ["infantry", "cavalry", "archer", "mage", "siege"]:
                    val = str((config or {}).get(f"tier_{house}", "default"))
                    if val != "skip":
                        tier = val if val == "default" else int(val)
                        training_list.append((house, tier))

                ok = await asyncio.to_thread(
                    core_actions.train_troops, serial, detector, training_list=training_list
                )

            elif fn_id == "claim_alliance_resource":
                ok = await asyncio.to_thread(
                    core_actions.claim_alliance_resource, serial, detector
                )

            # ── Merged Workflow Mappings ──
            elif fn_id == "nav_to_alliance_help":
                ok = await asyncio.to_thread(
                    core_actions.alliance_help, serial, detector
                )

            elif fn_id == "nav_to_tavern_chest":
                draw_x10_silver = str((config or {}).get("draw_x10_silver", "false")).lower() == "true"
                draw_x10_gold = str((config or {}).get("draw_x10_gold", "false")).lower() == "true"
                draw_x10_artifact = str((config or {}).get("draw_x10_artifact", "false")).lower() == "true"
                ok = await asyncio.to_thread(
                    core_actions.claim_daily_chests, serial, detector,
                    draw_x10_silver=draw_x10_silver,
                    draw_x10_gold=draw_x10_gold,
                    draw_x10_artifact=draw_x10_artifact
                )

            elif fn_id == "nav_to_heal_troops":
                ok = await asyncio.to_thread(
                    core_actions.heal_troops, serial, detector
                )

            elif fn_id == "nav_to_darkling_legions":
                ok = await asyncio.to_thread(
                    core_actions.attack_darkling_legions_v1_basic, serial, detector
                )

            elif fn_id == "nav_to_chat_hero":
                # chat_with_hero is standalone — runs its own cv2 template matching
                import os as _os
                chat_module_path = _os.path.join(
                    _os.path.dirname(_os.path.abspath(__file__)), "chat_with_hero.py"
                )
                if _os.path.exists(chat_module_path):
                    from backend.core.workflow import chat_with_hero
                    ok = await asyncio.to_thread(
                        chat_with_hero.run_chat_with_hero, serial, detector
                    )
                else:
                    await log(f"  chat_with_hero.py not found at {chat_module_path}", "warn")
                    ok = True  # Skip gracefully

            else:
                await log(
                    f"  [Warning] Function '{fn_id}' is not implemented yet. Skipping.",
                    "warn",
                )
                # Don't abort — just skip unrecognized steps
                ok = True

            # Normalize dict returns from core_actions
            # e.g. {"ok": True, "dynamic_cooldown_sec": 11700}
            if isinstance(ok, dict):
                _activity_meta.update(ok)
                ok = ok.get("ok", False)

            if ok:
                await log(f"  ✓ {fn_id} complete", "ok")
            else:
                await log(f"  ✕ {fn_id} failed", "err")
                all_ok = False
                break

        # Finished Loop
        await progress(total_steps, total_steps)
        if all_ok:
            await log("✅ Workflow completed successfully", "ok")
            await status("SUCCESS")
        else:
            await log("❌ Workflow aborted due to failure", "err")
            await status("ERROR")

        result = {"success": all_ok}
        # Propagate dynamic cooldown if any core_action provided it
        if _activity_meta.get("dynamic_cooldown_sec"):
            result["dynamic_cooldown_sec"] = _activity_meta["dynamic_cooldown_sec"]
        return result

    except Exception as e:
        await log(f"Exception during execution: {str(e)}", "err")
        await status("ERROR")
        return {"success": False, "error": str(e)}
