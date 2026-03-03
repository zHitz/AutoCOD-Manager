import asyncio
from typing import Callable, Coroutine
from backend.core.workflow import core_actions
from backend.core.workflow import adb_helper
from backend.core.workflow.state_detector import GameStateDetector

# To be resilient, we'll keep a mapped dictionary of function_ids to actual python logic.
# These function_ids match what is defined in workflow_registry.py

async def execute_recipe(emulator_index: int, emulator_name: str, steps: list, ws_callback: Callable[[dict], Coroutine] = None):
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
            await ws_callback({
                "type": "workflow_log",
                "emulator_index": emulator_index,
                "log_type": log_type,
                "message": msg
            })
            
    async def progress(current: int, total: int):
        if ws_callback:
            await ws_callback({
                "type": "workflow_progress",
                "emulator_index": emulator_index,
                "current": current,
                "total": total
            })

    async def status(state: str):
        if ws_callback:
            await ws_callback({
                "type": "workflow_status",
                "emulator_index": emulator_index,
                "status": state  # e.g., "RUNNING", "SUCCESS", "ERROR"
            })

    await status("RUNNING")
    await log(f"▶ Workflow execution started on {emulator_name}", "info")
    
    all_ok = True

    try:
        # Step Execution Loop
        for i, step in enumerate(steps):
            fn_id = step.get("function_id")
            config = step.get("config", {})
            
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
                adb_helper.tap(serial, x, y)
                await asyncio.sleep(0.5)
                
            elif fn_id == "act_swipe":
                x1 = int(config.get("startX", 0))
                y1 = int(config.get("startY", 0))
                x2 = int(config.get("endX", 0))
                y2 = int(config.get("endY", 0))
                duration = int(config.get("durationMs", 500))
                adb_helper.swipe(serial, x1, y1, x2, y2, duration)
                await asyncio.sleep(0.5)
                
            elif fn_id == "act_input_text":
                text = str(config.get("text", ""))
                adb_helper.input_text(serial, text)
                await asyncio.sleep(1)
                
            # App/System Controls
            elif fn_id == "sys_start_app":
                pkg = config.get("package", "com.farlightgames.samo.gp")
                was_running = core_actions.ensure_app_running(serial, pkg)
                if not was_running:
                    await asyncio.sleep(10) # Give it time to boot up
            
            elif fn_id == "sys_close_app":
                pkg = config.get("package", "com.farlightgames.samo.gp")
                adb_helper.kill_app(serial, pkg)
                await asyncio.sleep(2)
                
            elif fn_id == "sys_back_btn":
                adb_helper.press_back(serial)
                await asyncio.sleep(1.5)
                
            # Game Navigation Macros
            elif fn_id == "nav_to_lobby":
                ok = core_actions.back_to_lobby(serial, detector)
                
            elif fn_id == "nav_to_profile":
                ok = core_actions.go_to_profile(serial, detector)
                
            elif fn_id == "nav_to_items":
                ok = core_actions.go_to_resources(serial, detector)
                
            # Advanced / State Dependent
            elif fn_id == "adv_detect_state":
                current_state = detector.check_state(serial)
                await log(f"  Detected State: {current_state}", "info")
                
            elif fn_id == "adv_copy_id":
                player_id = core_actions.extract_player_id(serial, detector)
                if player_id:
                    await log(f"  Successfully copied Player ID: {player_id}", "ok")
                else:
                    await log("  Failed to extract Player ID.", "err")
                    ok = False
                    
            elif fn_id == "nav_to_pet_token":
                ok = core_actions.go_to_pet_token(serial, detector)

            elif fn_id == "nav_to_capture_pet":
                ok = core_actions.go_to_capture_pet(serial, detector)

            elif fn_id == "nav_to_market":
                ok = core_actions.go_to_market(serial, detector)

            elif fn_id == "nav_to_resources":
                ok = core_actions.go_to_resources(serial, detector)

            elif fn_id == "nav_to_hall":
                ok = core_actions.go_to_hall(serial, detector)

            else:
                await log(f"  [Warning] Function '{fn_id}' is not implemented yet in python backend.", "err")
                ok = False

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

        return {"success": all_ok}

    except Exception as e:
        await log(f"Exception during execution: {str(e)}", "err")
        await status("ERROR")
        return {"success": False, "error": str(e)}
