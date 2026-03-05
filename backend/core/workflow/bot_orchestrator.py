import asyncio
import time
from typing import List, Dict, Any, Callable, Coroutine
from backend.core.workflow import executor, core_actions, workflow_registry, execution_log
import uuid
from backend.core.workflow.state_detector import GameStateDetector
from backend.core.workflow.account_detector import AccountDetector
from backend.core.ldplayer_manager import list_all_instances, quit_instance, launch_instance
from backend.config import config
import os

# Dictionary to store active orchestrators per group_id
_active_orchestrators = {}

class BotOrchestrator:
    """
    Manages sequential execution of accounts within a Target Group.
    Accounts run one by one. If they share an emulator, it uses in-game account switching.
    If they use different emulators, it switches the emulator.
    """
    def __init__(self, group_id: int, accounts: List[Dict[str, Any]], activities: List[Dict[str, Any]], ws_callback: Callable, misc_config: Dict[str, Any] = None, start_account_id: int = None):
        self.group_id = group_id
        self.accounts = accounts  # List of dicts: id, game_id, emu_index, lord_name
        self.activities = activities # List of dicts: name, config
        self.ws_callback = ws_callback
        self.misc_config = misc_config or {}
        
        self.main_task: asyncio.Task = None
        
        # Sort accounts by emu_index so all accounts on the same emulator
        # run consecutively, minimizing expensive cross-emu swaps
        self.queue = sorted(accounts, key=lambda a: (a.get("emu_index") or 999))
        self.current_idx = 0
        
        if start_account_id:
            for i, acc in enumerate(self.queue):
                if acc["id"] == start_account_id:
                    self.current_idx = i
                    print(f"[BotOrchestrator] Starting from specific account '{acc.get('lord_name', 'Unknown')}' at index {self.current_idx}")
                    break
        
        self.cycle = 1
        
        self.is_running = False
        self.stop_requested = False
        self.account_statuses = {str(acc["id"]): "pending" for acc in self.accounts}
        self.last_run_times = {} # tracking cooldowns per acc_id

        # Track activity progress
        self.current_activity = None
        # Dict of activity_id -> status string ("pending", "running", "done", "skipped", "error")
        self.activity_statuses = {} 

        self.run_id = str(uuid.uuid4())
        self.run_meta = {
            "source_page": "workflow",
            "target_id": self.group_id,
            "trigger_type": "manual"
        }

        # Resolve templates dir once for detector usage inside orchestrator (if needed)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.templates_dir = os.path.join(current_dir, "templates")

    async def broadcast_state(self):
        """Sends the current orchestrator queue state to the frontend via WebSocket."""
        if not self.ws_callback:
            return
            
        data = {
            "group_id": self.group_id,
            "is_running": self.is_running,
            "stop_requested": self.stop_requested,
            "cycle": self.cycle,
            "current_idx": self.current_idx,
            "total_accounts": len(self.queue),
            "current_activity": self.current_activity,
            "activity_statuses": self.activity_statuses,
            "accounts": [
                {
                    "id": acc["id"],
                    "lord_name": acc.get("lord_name") or acc.get("game_id", "Unknown"),
                    "emu_index": acc.get("emu_index"),
                    "status": self.account_statuses.get(str(acc["id"]), "pending")
                }
                for acc in self.queue
            ]
        }
        
        import inspect
        if inspect.iscoroutinefunction(self.ws_callback):
            await self.ws_callback("bot_queue_update", data)
        else:
            self.ws_callback("bot_queue_update", data)

    def stop(self):
        """Requests the loop to stop and aborts immediately."""
        self.stop_requested = True
        if self.main_task and not self.main_task.done():
            print(f"[BotOrchestrator] Cancelling running task for group {self.group_id}...")
            self.main_task.cancel()

    async def _execute_current_account(self, emulator_index: int, emulator_name: str, steps: List[dict]):
        """Runs the activities for the current account using the existing executor."""
        return await executor.execute_recipe(
            emulator_index=emulator_index,
            emulator_name=emulator_name,
            steps=steps,
            ws_callback=self.ws_callback
        )
        
    async def _handle_cross_emu_swap(self, old_emu_index: int, new_emu_index: int):
        """Closes old emulator / game and boots new one."""
        import logging
        print(f"[BotOrchestrator] Cross-Emu Swap: Switching from Emu {old_emu_index} to Emu {new_emu_index}")
        logging.info(f"Cross-Emu Swap: Switching from Emu {old_emu_index} to Emu {new_emu_index}")
        
        print(f"[BotOrchestrator] Quitting Emu {old_emu_index}...")
        await asyncio.to_thread(quit_instance, old_emu_index)
        
        await asyncio.sleep(3)  # Wait for LDPlayer to close properly
        
        print(f"[BotOrchestrator] Launching Emu {new_emu_index}...")
        await asyncio.to_thread(launch_instance, new_emu_index)
        
        print(f"[BotOrchestrator] Waiting 15s for Emu {new_emu_index} to boot...")
        await asyncio.sleep(15)  # Give LDPlayer system time to boot up

        
    async def start(self):
        """Main orchestrator loop."""
        if self.is_running:
            return
            
        self.is_running = True
        self.stop_requested = False
        self.run_start_time = time.time()
        
        await execution_log.create_run(self.run_id, self.run_meta)
        
        # Reset statuses if starting fresh
        for key in self.account_statuses:
            self.account_statuses[key] = "pending"
            
        await self.broadcast_state()
        
        # Pre-fetch emulator names for logging
        name_map = {e["index"]: e["name"] for e in list_all_instances()}
        
        last_emu_index = None
        consecutive_skips = 0  # Track how many accounts skipped in a row

        try:
            while not self.stop_requested:
                acc = self.queue[self.current_idx]
                acc_id = str(acc["id"])
                
                # Force emu_idx to be an integer (avoid string concatenation issues)
                raw_emu = acc.get("emu_index")
                if raw_emu is None or str(raw_emu).strip() == "":
                    print(f"[BotOrchestrator] Skipping account {acc.get('game_id', 'Unknown')} — no emulator assigned.")
                    self.account_statuses[acc_id] = "error"
                    consecutive_skips += 1
                    self._advance_queue()
                    if consecutive_skips >= len(self.queue):
                        print("[BotOrchestrator] All accounts have no emulator. Stopping.")
                        break
                    continue
                    
                emu_idx = int(raw_emu)
                emu_name = name_map.get(emu_idx, f"Emulator-{emu_idx}")

                # ── ENFORCE COOLDOWN ──
                cooldown_min = self.misc_config.get("cooldown_min", 0)
                last_run = self.last_run_times.get(acc_id, 0)
                cooldown_sec = cooldown_min * 60
                if cooldown_min > 0 and last_run > 0 and (time.time() - last_run) < cooldown_sec:
                    consecutive_skips += 1
                    
                    # If we've skipped ALL accounts → everyone is on cooldown
                    if consecutive_skips >= len(self.queue):
                        # Find the shortest remaining cooldown
                        now = time.time()
                        wait_times = []
                        for a in self.queue:
                            aid = str(a["id"])
                            lr = self.last_run_times.get(aid, 0)
                            if lr > 0:
                                remaining = cooldown_sec - (now - lr)
                                if remaining > 0:
                                    wait_times.append(remaining)
                        
                        sleep_sec = min(wait_times) if wait_times else 30
                        sleep_min = round(sleep_sec / 60, 1)
                        print(f"[BotOrchestrator] All accounts on cooldown. Sleeping {sleep_min}m until next account is ready.")
                        await self.broadcast_state()
                        
                        # Sleep in small chunks so we can respond to stop_requested
                        while sleep_sec > 0 and not self.stop_requested:
                            chunk = min(sleep_sec, 10)  # Check every 10 seconds
                            await asyncio.sleep(chunk)
                            sleep_sec -= chunk
                        
                        consecutive_skips = 0  # Reset after sleeping
                    else:
                        self.account_statuses[acc_id] = "pending"
                        self._advance_queue()
                    continue
                
                # Account is ready — reset skip counter
                consecutive_skips = 0

                self.account_statuses[acc_id] = "running"
                await self.broadcast_state()
                
                print(f"[BotOrchestrator] --- CYCLE {self.cycle} | ACCOUNT {self.current_idx + 1}/{len(self.queue)} | EMU {emu_idx} ---")
                
                # Check if swap is needed
                if last_emu_index is not None:
                    if last_emu_index == emu_idx:
                        # SAME EMULATOR -> Need in-game account swap
                        serial = f"emulator-{5554 + emu_idx * 2}"
                        detector = GameStateDetector(adb_path=config.adb_path, templates_dir=self.templates_dir)
                        account_detector = AccountDetector(adb_path=config.adb_path)
                        
                        #target_lord = self.queue[self.current_idx].get("lord_name")
                        swap_ok = await asyncio.to_thread(
                            core_actions.swap_account, 
                            serial, 
                            account_detector, 
                            detector, 
                            #target_lord
                        )
                        if not swap_ok:
                            print(f"[BotOrchestrator] Account swap failed on Emu {emu_idx}. Skipping account.")
                            self.account_statuses[acc_id] = "error"
                            last_emu_index = emu_idx
                            self._advance_queue()
                            continue
                    else:
                        # DIFFERENT EMULATOR -> Cross-emu swap
                        await self._handle_cross_emu_swap(last_emu_index, emu_idx)
                else:
                    # BEGINNING OF RUN (last_emu_index is None) -> MUST LAUNCH FIRST EMULATOR
                    print(f"[BotOrchestrator] Launching initial Emu {emu_idx}...")
                    
                    # Check if already running to save wait time
                    current_instances = list_all_instances()
                    is_running = any(inst["index"] == emu_idx and inst.get("running") for inst in current_instances)
                    
                    if not is_running:
                        await asyncio.to_thread(launch_instance, emu_idx)
                        print(f"[BotOrchestrator] Waiting 15s for initial Emu {emu_idx} to boot...")
                        await asyncio.sleep(15)
                    else:
                        print(f"[BotOrchestrator] Initial Emu {emu_idx} is already running.")

                # Wait slightly before starting activities
                await asyncio.sleep(2)
                
                # Reset all activity statuses for the current account run
                act_keys = [act.get("id", act.get("name", f"act_{i}")) for i, act in enumerate(self.activities)]
                self.activity_statuses = {k: "pending" for k in act_keys}
                
                limit_min = self.misc_config.get("limit_min", 0)
                account_success = True
                
                # Execute activities one by one
                for i, act in enumerate(self.activities):
                    if self.stop_requested:
                        break
                        
                    act_id_or_name = act_keys[i]
                    act_cfg = act.get("config", {})
                    
                    steps = workflow_registry.build_steps_for_activity(act_id_or_name, act_cfg)
                    
                    if not steps:
                        print(f"[BotOrchestrator] Unknown activity '{act_id_or_name}', skipping.")
                        self.activity_statuses[act_id_or_name] = "skipped"
                        continue
                        
                    self.current_activity = {
                        "id": act_id_or_name,
                        "name": act.get("name", act_id_or_name),
                        "status": "running"
                    }
                    self.activity_statuses[act_id_or_name] = "running"
                    await self.broadcast_state()
                    
                    step_start = time.time()
                    result = None
                    step_status = "FAILED"
                    step_error = ""
                    
                    try:
                        if limit_min > 0:
                            result = await asyncio.wait_for(
                                self._execute_current_account(emu_idx, emu_name, steps),
                                timeout=limit_min * 60
                            )
                        else:
                            result = await self._execute_current_account(emu_idx, emu_name, steps)
                            
                        if not result or not result.get("success", False):
                            account_success = False
                            self.activity_statuses[act_id_or_name] = "error"
                            self.current_activity["status"] = "error"
                            step_error = result.get("error", "Unknown execution failure") if result else "No result returned"
                        else:
                            self.activity_statuses[act_id_or_name] = "done"
                            step_status = "SUCCESS"
                            
                    except asyncio.TimeoutError:
                        print(f"[BotOrchestrator] Account {acc_id} hit Time Limit ({limit_min}m) during {act_id_or_name}. Forcing swap.")
                        account_success = False
                        self.activity_statuses[act_id_or_name] = "error"
                        self.current_activity["status"] = "error"
                        step_error = f"Timeout limit {limit_min}m reached"
                    except Exception as e:
                        account_success = False
                        self.activity_statuses[act_id_or_name] = "error"
                        self.current_activity["status"] = "error"
                        step_error = str(e)
                        
                    step_end = time.time()
                    latency = int((step_end - step_start) * 1000)
                    
                    await execution_log.append_step_log(
                        run_id=self.run_id,
                        step_index=i,
                        function_id=act_id_or_name,
                        input_dict=act_cfg,
                        output_dict=result or {},
                        status=step_status,
                        error_msg=step_error,
                        latency_ms=latency
                    )
                    
                    if not account_success:
                        break # stop processing activities for this account on error
                        
                # End of activities loop for this account
                self.current_activity = None
                
                # Update last run time for cooldown tracking
                self.last_run_times[acc_id] = time.time()
                
                if account_success and not self.stop_requested:
                    self.account_statuses[acc_id] = "done"
                else:
                    self.account_statuses[acc_id] = "error"
                    
                last_emu_index = emu_idx

                self._advance_queue()

        except asyncio.CancelledError:
            print(f"[BotOrchestrator] Execution cancelled via stop() for group {self.group_id}.")
            self.stop_requested = True # Ensure this is flagged
        except Exception as e:
            print(f"[BotOrchestrator] Fatal error in loop: {e}")
        finally:
            self.is_running = False
            await self.broadcast_state()
            
            duration = int((time.time() - getattr(self, 'run_start_time', time.time())) * 1000)
            await execution_log.complete_run(self.run_id, "STOPPED" if self.stop_requested else "COMPLETED", duration)
            
            # Clean up active instances
            if self.group_id in _active_orchestrators:
                del _active_orchestrators[self.group_id]
                
    def _advance_queue(self):
        """Moves to the next account, incrementing cycle if it loops."""
        if self.stop_requested:
            return
            
        self.current_idx += 1
        if self.current_idx >= len(self.queue):
            self.current_idx = 0
            self.cycle += 1
            # Reset all statuses for the new cycle
            for key in self.account_statuses:
                self.account_statuses[key] = "pending"

def start_sequential_orchestrator(group_id: int, accounts: List[Dict], activities: List[Dict], ws_callback: Callable, misc_config: Dict = None, start_account_id: int = None) -> BotOrchestrator:
    """Creates and starts a new BotOrchestrator for a group."""
    # Prevent duplicate starts — preserve cooldown state
    if group_id in _active_orchestrators:
        existing = _active_orchestrators[group_id]
        if existing.is_running:
            return existing  # Already running, don't reset
        # Not running anymore — clean up old reference
        del _active_orchestrators[group_id]
        
    orch = BotOrchestrator(group_id, accounts, activities, ws_callback, misc_config, start_account_id)
    _active_orchestrators[group_id] = orch
    
    # Run in background and keep a reference to cancel execution
    orch.main_task = asyncio.create_task(orch.start())
    return orch

def stop_sequential_orchestrator(group_id: int) -> bool:
    """Stops an active orchestrator for the given group."""
    if group_id in _active_orchestrators:
        _active_orchestrators[group_id].stop()
        return True
    return False

def get_orchestrator_status(group_id: int) -> dict:
    """Gets current status of a group's orchestrator."""
    if group_id in _active_orchestrators:
        orch = _active_orchestrators[group_id]
        return {
            "group_id": orch.group_id,
            "is_running": orch.is_running,
            "stop_requested": orch.stop_requested,
            "cycle": orch.cycle,
            "current_idx": orch.current_idx,
            "total_accounts": len(orch.queue),
            "account_statuses": orch.account_statuses,
            "accounts": [
                {
                    "id": acc["id"],
                    "lord_name": acc.get("lord_name") or acc.get("game_id", "Unknown"),
                    "emu_index": acc.get("emu_index"),
                    "status": orch.account_statuses.get(str(acc["id"]), "pending")
                }
                for acc in orch.queue
            ]
        }
    return None

def get_all_orchestrator_statuses() -> dict:
    """Gets status summaries for ALL active orchestrators."""
    result = {}
    for gid, orch in _active_orchestrators.items():
        all_pending = all(s == "pending" for s in orch.account_statuses.values())
        result[gid] = {
            "group_id": gid,
            "is_running": orch.is_running,
            "stop_requested": orch.stop_requested,
            "cycle": orch.cycle,
            "all_on_cooldown": orch.is_running and all_pending,
        }
    return result
