import asyncio
import random
import time
from typing import List, Dict, Any, Callable, Optional, Tuple
from backend.core.workflow import (
    adb_helper,
    executor,
    core_actions,
    workflow_registry,
    execution_log,
)
from backend.core.workflow.workflow_registry import ACTIVITY_REGISTRY
import uuid
from backend.core.workflow.state_detector import GameStateDetector
from backend.core.workflow.account_detector import AccountDetector
from backend.core.workflow.swap_logger import (
    log_cross_emu_swap,
    log_account_verification,
    log_swap_attempt,
    log_ensure_correct_account,
    log_restart_recovery,
    log_queue_reorder,
    log_early_probe,
    log_main_loop_swap_decision,
)
from backend.core.workflow.smart_wait_logger import log_smart_wait_eval
from backend.core.ldplayer_manager import (
    list_all_instances,
    quit_instance,
    launch_instance,
    wait_for_device,
)
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

    def __init__(
        self,
        group_id: int,
        accounts: List[Dict[str, Any]],
        activities: List[Dict[str, Any]],
        ws_callback: Callable,
        misc_config: Dict[str, Any] = None,
        start_account_id: int = None,
    ):
        self.group_id = group_id
        self.accounts = accounts  # List of dicts: id, game_id, emu_index, lord_name
        self.activities = activities  # List of dicts: name, config
        self.ws_callback = ws_callback
        self.misc_config = misc_config or {}
        self.skip_cooldown = self.misc_config.get("skip_cooldown", False)
        self.continue_on_error = self.misc_config.get("continue_on_error", False)
        self.package_name = core_actions.get_package_for_provider()  # default, updated per-account

        self.main_task: asyncio.Task = None

        # Sort accounts by emu_index so all accounts on the same emulator
        # run consecutively, minimizing expensive cross-emu swaps
        self.queue = sorted(accounts, key=lambda a: a.get("emu_index") or 999)
        self.current_idx = 0

        if start_account_id:
            for i, acc in enumerate(self.queue):
                if acc["id"] == start_account_id:
                    self.current_idx = i
                    print(
                        f"[BotOrchestrator] Starting from specific account '{acc.get('lord_name', 'Unknown')}' at index {self.current_idx}"
                    )
                    break

        self.cycle = 1

        self.is_running = False
        self.stop_requested = False
        self.account_statuses = {str(acc["id"]): "pending" for acc in self.accounts}
        self.last_run_times = {}  # tracking cooldowns per acc_id
        self._smart_wait_info = {"account_id": None, "remaining_sec": None}

        # Track activity progress
        self.current_activity = None
        # Dict of activity_id -> status string ("pending", "running", "done", "skipped", "error")
        # Initialize all activities to "pending" immediately so the UI shows them as QUEUED
        self.activity_statuses = {
            act.get("id", act.get("name", f"act_{i}")): "pending"
            for i, act in enumerate(self.activities)
        }

        self.run_id = str(uuid.uuid4())
        self.run_meta = {
            "source_page": "workflow",
            "target_id": self.group_id,
            "trigger_type": "manual",
        }

        # Resolve templates dir once for detector usage inside orchestrator (if needed)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.templates_dir = os.path.join(current_dir, "templates")

        # Build weight lookup: registry definitions are the source of truth.
        # Frontend payload only has {id, name, config} — weight is NOT included.
        self._weight_map = {}
        for act in ACTIVITY_REGISTRY:
            self._weight_map[act["id"]] = act.get("weight", "heavy")

    async def broadcast_state(self):
        """Sends the current orchestrator queue state to the frontend via WebSocket."""
        if not self.ws_callback:
            return

        import time as _time

        cooldown_min = self.misc_config.get("cooldown_min", 0)
        cooldown_sec = cooldown_min * 60
        now_ts = _time.time()

        accounts_payload = []
        for acc in self.queue:
            aid = str(acc["id"])
            last_run = self.last_run_times.get(aid, 0)
            cd_remaining = 0
            if not self.skip_cooldown and cooldown_sec > 0 and last_run > 0:
                cd_remaining = max(0, cooldown_sec - (now_ts - last_run))
            accounts_payload.append({
                "id": acc["id"],
                "lord_name": acc.get("lord_name") or acc.get("game_id", "Unknown"),
                "emu_index": acc.get("emu_index"),
                "game_id": acc.get("game_id", ""),
                "status": self.account_statuses.get(aid, "pending"),
                "last_run_time": last_run if last_run > 0 else None,
                "cooldown_remaining_sec": round(cd_remaining, 1),
            })

        data = {
            "group_id": self.group_id,
            "is_running": self.is_running,
            "stop_requested": self.stop_requested,
            "cycle": self.cycle,
            "current_idx": self.current_idx,
            "total_accounts": len(self.queue),
            "current_activity": self.current_activity,
            "activity_statuses": self.activity_statuses,
            "accounts": accounts_payload,
            "activity_metrics": await self._get_activity_metrics(),
            "cooldown_config": {
                "cooldown_min": cooldown_min,
                "swap_wait_threshold_min": self.misc_config.get("swap_wait_threshold_min", 0),
                "skip_cooldown": self.skip_cooldown,
            },
            "smart_wait_active": self._smart_wait_info,
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
            print(
                f"[BotOrchestrator] Cancelling running task for group {self.group_id}..."
            )
            self.main_task.cancel()

    async def _execute_current_account(
        self, emulator_index: int, emulator_name: str, steps: List[dict]
    ):
        """Runs the activities for the current account using the existing executor."""
        return await executor.execute_recipe(
            emulator_index=emulator_index,
            emulator_name=emulator_name,
            steps=steps,
            ws_callback=self.ws_callback,
        )

    async def _emit_activity_event(
        self,
        event_type: str,
        account_id: str,
        activity_id: str,
        activity_name: str,
        status: str = "",
        error: str = "",
        duration_ms: int = 0,
    ):
        """Emit a WebSocket event for activity lifecycle changes."""
        if not self.ws_callback:
            return
        data = {
            "group_id": self.group_id,
            "account_id": account_id,
            "activity_id": activity_id,
            "activity_name": activity_name,
            "status": status,
            "error": error,
            "duration_ms": duration_ms,
        }
        import inspect

        if inspect.iscoroutinefunction(self.ws_callback):
            await self.ws_callback(event_type, data)
        else:
            self.ws_callback(event_type, data)

    async def _emit_timeline(self, icon: str, message: str, emu_index: int = None, account_id: str = None):
        """Emit a timeline_event for the Monitor tab's bottom timeline panel."""
        if not self.ws_callback:
            return
        import time as _t, inspect
        data = {
            "ts": _t.time(),
            "icon": icon,
            "message": message,
            "emu_index": emu_index,
            "account_id": account_id,
            "group_id": self.group_id,
        }
        if inspect.iscoroutinefunction(self.ws_callback):
            await self.ws_callback("timeline_event", data)
        else:
            self.ws_callback("timeline_event", data)

    async def _get_activity_metrics(self) -> Dict[str, Any]:
        """Queries the database for live metrics (last_run, runs_today) for all activities in this group."""
        metrics = {}
        import aiosqlite
        from datetime import datetime
        
        try:
            today_prefix = datetime.now().strftime('%Y-%m-%d')
            async with aiosqlite.connect(config.db_path) as db:
                for act in self.activities:
                    act_id = act.get("id", act.get("name"))
                    if not act_id:
                        continue
                        
                    metrics[act_id] = {"last_run": None, "runs_today": 0}
                    
                    # Get Last Run
                    async with db.execute(
                        """SELECT started_at FROM account_activity_logs 
                           WHERE group_id = ? AND activity_id = ? AND status = 'SUCCESS'
                           ORDER BY started_at DESC LIMIT 1""", 
                        (self.group_id, act_id)
                    ) as cursor:
                        row = await cursor.fetchone()
                        if row and row[0]:
                            metrics[act_id]["last_run"] = row[0]
                            
                            # Get Runs Today
                            async with db.execute(
                                """SELECT COUNT(*) FROM account_activity_logs 
                                   WHERE group_id = ? AND activity_id = ? AND status = 'SUCCESS'
                                   AND started_at LIKE ?""", 
                                (self.group_id, act_id, f"{today_prefix}%")
                            ) as cursor2:
                                count_row = await cursor2.fetchone()
                                metrics[act_id]["runs_today"] = count_row[0] if count_row else 0
        except Exception as e:
            print(f"[BotOrchestrator] Error fetching activity metrics: {e}")
            
        return metrics

    async def _all_activities_on_cooldown(self, acc_id: str) -> bool:
        """Check if ALL activities are on cooldown for this account.
        Returns True if every activity with cooldown_enabled is still cooling down,
        meaning a swap to this account would be pointless.
        """
        if self.skip_cooldown:
            return False

        now = time.time()
        has_any_runnable = False

        for i, act in enumerate(self.activities):
            act_id_or_name = act.get("id", act.get("name", f"act_{i}"))
            act_cfg = act.get("config", {})

            if not act_cfg.get("cooldown_enabled"):
                # Activity has no cooldown → always runnable
                has_any_runnable = True
                break

            cd_minutes = act_cfg.get("cooldown_minutes", 0)
            if cd_minutes <= 0:
                has_any_runnable = True
                break

            last_act_run, dynamic_cd = await execution_log.get_effective_cooldown_sec(
                int(acc_id), act_id_or_name
            )
            effective_cd = dynamic_cd if dynamic_cd > 0 else (cd_minutes * 60)
            if last_act_run <= 0 or (now - last_act_run) >= effective_cd:
                # Never run before OR cooldown expired → runnable
                has_any_runnable = True
                break

        return not has_any_runnable

    async def _only_light_tasks_ready(self, acc_id: str) -> bool:
        """Check if only light-weight tasks are ready while heavy tasks exist but are all on cooldown.
        Returns True if the account should be skipped to preserve global cooldown for heavy tasks.
        If there are NO heavy tasks at all → return False (run everything normally).
        """
        if self.skip_cooldown:
            return False

        now = time.time()
        has_heavy = False
        has_heavy_ready = False
        has_any_ready = False

        for i, act in enumerate(self.activities):
            act_id = act.get("id", act.get("name", f"act_{i}"))
            act_cfg = act.get("config", {})
            weight = act_cfg.get("weight") or self._weight_map.get(act_id, "heavy")

            # Determine if this activity is currently on cooldown
            is_on_cd = False
            if act_cfg.get("cooldown_enabled"):
                cd_minutes = act_cfg.get("cooldown_minutes", 0)
                if cd_minutes > 0:
                    last_act_run, dynamic_cd = await execution_log.get_effective_cooldown_sec(
                        int(acc_id), act_id
                    )
                    effective_cd = dynamic_cd if dynamic_cd > 0 else (cd_minutes * 60)
                    if last_act_run > 0 and (now - last_act_run) < effective_cd:
                        is_on_cd = True

            if weight == "heavy":
                has_heavy = True
                if not is_on_cd:
                    has_heavy_ready = True

            if not is_on_cd:
                has_any_ready = True

        # If no heavy tasks exist at all → normal behavior (all light = run normally)
        if not has_heavy:
            return False

        # Heavy tasks exist but none are ready, and some light tasks are ready → skip
        return has_any_ready and not has_heavy_ready

    async def _earliest_activity_ready_sec(self, heavy_only: bool = False) -> float:
        """Scan all accounts × activities to find the shortest remaining cooldown.
        Returns seconds until the earliest activity becomes runnable.
        If heavy_only=True, only considers heavy-weight activities.
        Falls back to 60s if nothing can be computed.
        """
        now = time.time()
        min_remaining = float("inf")

        for acc in self.queue:
            aid = str(acc["id"])
            for i, act in enumerate(self.activities):
                act_cfg = act.get("config", {})
                act_id = act.get("id", act.get("name", f"act_{i}"))
                weight = act_cfg.get("weight") or self._weight_map.get(act_id, "heavy")
                if heavy_only and weight != "heavy":
                    continue  # Skip light activities when waiting for heavy
                if not act_cfg.get("cooldown_enabled"):
                    return 0  # At least one activity has no cooldown → ready now
                cd_minutes = act_cfg.get("cooldown_minutes", 0)
                if cd_minutes <= 0:
                    return 0
                last_run, dynamic_cd = await execution_log.get_effective_cooldown_sec(int(aid), act_id)
                if last_run <= 0:
                    return 0  # Never run → ready now
                effective_cd = dynamic_cd if dynamic_cd > 0 else (cd_minutes * 60)
                remaining = effective_cd - (now - last_run)
                if remaining <= 0:
                    return 0  # Already expired
                min_remaining = min(min_remaining, remaining)

        return min_remaining if min_remaining < float("inf") else 60

    async def _handle_cross_emu_swap(self, old_emu_index: int, new_emu_index: int) -> bool:
        """Closes old emulator / game and boots new one. Returns True on success."""
        import logging

        print(
            f"[BotOrchestrator] Cross-Emu Swap: Switching from Emu {old_emu_index} to Emu {new_emu_index}"
        )
        logging.info(
            f"Cross-Emu Swap: Switching from Emu {old_emu_index} to Emu {new_emu_index}"
        )
        log_cross_emu_swap(old_emu_index, new_emu_index, "start", True)

        print(f"[BotOrchestrator] Quitting Emu {old_emu_index}...")
        await asyncio.to_thread(quit_instance, old_emu_index)
        log_cross_emu_swap(old_emu_index, new_emu_index, "quit_old", True)

        await asyncio.sleep(3)  # Wait for LDPlayer to close properly

        print(f"[BotOrchestrator] Launching Emu {new_emu_index}...")
        await asyncio.to_thread(launch_instance, new_emu_index)
        log_cross_emu_swap(old_emu_index, new_emu_index, "launch_new", True)

        print(f"[BotOrchestrator] Waiting for Emu {new_emu_index} to fully boot...")
        boot_ok = await asyncio.to_thread(wait_for_device, new_emu_index, 120)
        if not boot_ok:
            # Retry once with shorter timeout
            print(f"[BotOrchestrator] Boot timeout. Retrying with 60s...")
            log_cross_emu_swap(old_emu_index, new_emu_index, "boot_retry", False, "First boot timeout, retrying 60s")
            boot_ok = await asyncio.to_thread(wait_for_device, new_emu_index, 60)
        if not boot_ok:
            print(f"[BotOrchestrator] Emu {new_emu_index} boot FAILED after retry.")
            log_cross_emu_swap(old_emu_index, new_emu_index, "complete", False, "Boot FAILED after retry")
            return False
        # Short grace period for OS services to settle after boot_completed
        await asyncio.sleep(5)
        log_cross_emu_swap(old_emu_index, new_emu_index, "complete", True)
        return True

    async def _ensure_lobby(
        self, serial: str, detector: GameStateDetector, load_timeout: int = 120
    ) -> bool:
        """Ensure the game is running and at lobby before account-sensitive actions."""
        return await asyncio.to_thread(
            core_actions.startup_to_lobby,
            serial,
            detector,
            self.package_name,
            config.adb_path,
            load_timeout,
        )

    def _log_account_verification_failure(
        self,
        expected_game_id: str,
        actual_account_id: Optional[str],
        context: str,
    ):
        """Log account verification failures with both expected and actual IDs when readable."""
        if actual_account_id:
            print(
                f"[BotOrchestrator] Account verification failed during {context}: "
                f"expected_game_id={expected_game_id}, actual_account_id={actual_account_id}"
            )
        else:
            print(
                f"[BotOrchestrator] Account verification failed during {context}: "
                f"expected_game_id={expected_game_id}, actual_account_id=<unreadable>"
            )
        log_account_verification(
            serial="<orchestrator>",
            context=context,
            expected_game_id=expected_game_id,
            actual_account_id=actual_account_id,
            match=False,
            detail="Verification failure logged",
        )

    async def _read_live_account_id(
        self, serial: str, detector: GameStateDetector, context: str
    ) -> Dict[str, Any]:
        """Read the active in-game account ID, retrying the ID extraction once if needed."""
        lobby_ok = await self._ensure_lobby(serial, detector)
        if not lobby_ok:
            print(
                f"[BotOrchestrator] Cannot verify account during {context}: lobby not reachable."
            )
            log_account_verification(serial, context, "<unknown>", None, False, "Lobby not reachable")
            return {"lobby_ok": False, "account_id": None}

        profile_ok = await asyncio.to_thread(core_actions.go_to_profile, serial, detector)
        if not profile_ok:
            print(
                f"[BotOrchestrator] Cannot verify account during {context}: profile not reachable."
            )
            log_account_verification(serial, context, "<unknown>", None, False, "Profile not reachable")
            await asyncio.to_thread(core_actions.back_to_lobby, serial, detector)
            return {"lobby_ok": True, "account_id": None}

        account_id = None
        try:
            account_id = await asyncio.to_thread(
                core_actions.extract_player_id,
                serial,
                detector,
            )
            if not account_id:
                print(
                    f"[BotOrchestrator] Account ID read failed during {context}. Retrying once..."
                )
                log_account_verification(serial, context, "<unknown>", None, False, "First extract failed, retrying")
                account_id = await asyncio.to_thread(
                    core_actions.extract_player_id,
                    serial,
                    detector,
                )
        finally:
            await asyncio.to_thread(core_actions.back_to_lobby, serial, detector)

        if account_id:
            print(
                f"[BotOrchestrator] Live account verification during {context}: account_id={account_id}"
            )
            log_account_verification(serial, context, "<live_read>", account_id, True, f"Read OK: {account_id}")
        else:
            print(
                f"[BotOrchestrator] Live account verification during {context} could not read account_id."
            )
            log_account_verification(serial, context, "<unknown>", None, False, "Could not read account_id after retry")

        return {"lobby_ok": True, "account_id": account_id}

    async def _restart_game_app(
        self, serial: str, detector: GameStateDetector, expected_game_id: str = ""
    ) -> bool:
        """Restart the game app as a last-resort recovery before the final swap attempt."""
        print(f"[BotOrchestrator] Restarting game app on {serial} before final swap attempt...")
        log_restart_recovery(serial, expected_game_id, False, "Initiating force-stop")
        await asyncio.to_thread(
            adb_helper._run_adb,
            ["shell", "am", "force-stop", self.package_name],
            serial,
            15,
        )
        await asyncio.sleep(2)
        lobby_ok = await self._ensure_lobby(serial, detector)
        log_restart_recovery(serial, expected_game_id, lobby_ok, f"After restart lobby_ok={lobby_ok}")
        return lobby_ok

    async def _ensure_correct_account(
        self,
        serial: str,
        detector: GameStateDetector,
        account_detector: AccountDetector,
        expected_game_id: str,
        target_lord: Optional[str],
        known_current_account_id: Optional[str] = None,
        emu_idx: int = 0,
        acc_id: str = "",
    ) -> Tuple[bool, Optional[str]]:
        """Guarantee the live account matches the target account before activities run."""
        log_ensure_correct_account(
            serial, expected_game_id, "start", True,
            known_current_id=known_current_account_id,
            detail=f"target_lord={target_lord}",
        )
        
        if known_current_account_id:
            current_account_id = known_current_account_id
        else:
            verify_result = await self._read_live_account_id(
                serial, detector, "pre-swap verification"
            )
            current_account_id = verify_result["account_id"]

        if current_account_id == expected_game_id:
            print(
                f"[BotOrchestrator] Verified correct account already active: {expected_game_id}"
            )
            log_ensure_correct_account(
                serial, expected_game_id, "already_correct", True,
                known_current_id=current_account_id,
                final_id=current_account_id,
            )
            return True, current_account_id

        self._log_account_verification_failure(
            expected_game_id, current_account_id, "pre-swap verification"
        )
        log_ensure_correct_account(
            serial, expected_game_id, "mismatch_detected", False,
            known_current_id=current_account_id,
            detail=f"Current={current_account_id}, starting swap loop",
        )

        for attempt in range(1, 4):
            if attempt == 3:
                restart_ok = await self._restart_game_app(serial, detector, expected_game_id)
                if not restart_ok:
                    print(
                        "[BotOrchestrator] App restart failed before final swap attempt."
                    )

            print(
                f"[BotOrchestrator] Swap verification attempt {attempt}/3 for expected_game_id={expected_game_id}"
            )
            swap_ok = False
            try:
                await self._emit_timeline("\ud83d\udd04", f"Emu {emu_idx}: Swapping to {target_lord or expected_game_id} ({expected_game_id}) \u2014 attempt {attempt}/3", emu_idx, acc_id)
                swap_ok = await asyncio.to_thread(
                    core_actions.swap_account,
                    serial,
                    account_detector,
                    detector,
                    target_lord,
                )
            except Exception as e:
                # AccountNotFoundError raised by swap_account when OCR can't find target
                from workflow.account_detector import AccountNotFoundError
                if isinstance(e, AccountNotFoundError):
                    print(f"[BotOrchestrator] FAST-FAIL: {e}")
                    log_swap_attempt(
                        serial, attempt, 3, expected_game_id, target_lord,
                        swap_result=False,
                        detail=f"Fast-Fail: {e}",
                    )
                    break  # Break retry loop immediately
                raise  # Re-raise any other unexpected exceptions
            log_swap_attempt(
                serial, attempt, 3, expected_game_id, target_lord,
                swap_result=swap_ok,
                detail="swap_account() returned" if swap_ok else "swap_account() reported failure",
            )
            if not swap_ok:
                print(
                    f"[BotOrchestrator] swap_account() reported failure on attempt {attempt}/3."
                )

            verify_result = await self._read_live_account_id(
                serial, detector, f"post-swap verification attempt {attempt}"
            )
            current_account_id = verify_result["account_id"]
            match = current_account_id == expected_game_id
            log_swap_attempt(
                serial, attempt, 3, expected_game_id, target_lord,
                swap_result=swap_ok,
                post_verify_id=current_account_id,
                final_match=match,
                detail=f"Post-verify: {'MATCH' if match else 'MISMATCH'}",
            )
            if match:
                print(
                    f"[BotOrchestrator] Verified target account after swap attempt {attempt}: {expected_game_id}"
                )
                log_ensure_correct_account(
                    serial, expected_game_id, "swap_loop_done", True,
                    final_id=current_account_id,
                    detail=f"Matched on attempt {attempt}/3",
                )
                await self._emit_timeline("\u2705", f"Emu {serial.split('-')[-1]}: {target_lord or expected_game_id} verified \u2014 match on attempt {attempt}", account_id=acc_id)
                return True, current_account_id

            self._log_account_verification_failure(
                expected_game_id,
                current_account_id,
                f"post-swap verification attempt {attempt}",
            )

        log_ensure_correct_account(
            serial, expected_game_id, "failed", False,
            final_id=current_account_id,
            detail="All 3 swap attempts exhausted",
        )
        await self._emit_timeline("\u274c", f"Swap failed for {target_lord or expected_game_id} ({expected_game_id}) after 3 attempts", account_id=acc_id)
        return False, current_account_id

    async def start(self):
        """Main orchestrator loop."""
        if self.is_running:
            return

        self.is_running = True
        self.stop_requested = False
        self.run_start_time = time.time()
        self._last_verified_account_id = None

        await execution_log.create_run(self.run_id, self.run_meta)

        # Reset statuses if starting fresh
        for key in self.account_statuses:
            self.account_statuses[key] = "pending"

        # Pre-populate last_run_times from database (always, so UI shows "last run")
        for acc in self.accounts:
            db_last_run = await execution_log.get_last_account_run(int(acc["id"]))
            if db_last_run > 0:
                self.last_run_times[str(acc["id"])] = db_last_run

        await self.broadcast_state()

        # Pre-fetch emulator names for logging
        name_map = {e["index"]: e["name"] for e in list_all_instances()}

        last_emu_index = None
        last_account_id = None
        consecutive_skips = 0  # Track how many accounts skipped in a row

        try:
            while not self.stop_requested:
                acc = self.queue[self.current_idx]
                acc_id = str(acc["id"])

                # Force emu_idx to be an integer (avoid string concatenation issues)
                raw_emu = acc.get("emu_index")
                if raw_emu is None or str(raw_emu).strip() == "":
                    print(
                        f"[BotOrchestrator] Skipping account {acc.get('game_id', 'Unknown')} — no emulator assigned."
                    )
                    self.account_statuses[acc_id] = "error"
                    consecutive_skips += 1
                    self._advance_queue()
                    if consecutive_skips >= len(self.queue):
                        print(
                            "[BotOrchestrator] All accounts have no emulator. Stopping."
                        )
                        break
                    continue

                emu_idx = int(raw_emu)
                emu_name = name_map.get(emu_idx, f"Emulator-{emu_idx}")

                # ── ENFORCE COOLDOWN ──
                cooldown_min = self.misc_config.get("cooldown_min", 0)
                last_run = self.last_run_times.get(acc_id, 0)
                cooldown_sec = cooldown_min * 60
                # DEBUG: Account Cooldown values
                _elapsed = round((time.time() - last_run) / 60, 1) if last_run > 0 else -1
                print(f"[DEBUG-CD] Account {acc_id}: cooldown_min={cooldown_min}, last_run={last_run:.0f}, elapsed={_elapsed}m, skip_cooldown={self.skip_cooldown}")
                
                if (
                    not self.skip_cooldown
                    and cooldown_min > 0
                    and last_run > 0
                    and (time.time() - last_run) < cooldown_sec
                ):
                    remaining_cd = cooldown_sec - (time.time() - last_run)

                    # ── SMART WAIT: if active account's cooldown ends soon, wait instead of swapping ──
                    expected_gid_for_wait = str(acc.get("game_id") or "").strip()
                    swap_wait_threshold = self.misc_config.get("swap_wait_threshold_min", 0) * 60
                    
                    # Detailed debug logging for Smart Wait evaluation
                    is_active_account = bool(last_account_id and expected_gid_for_wait == last_account_id)
                    is_within_threshold = (swap_wait_threshold > 0 and remaining_cd <= swap_wait_threshold)
                    
                    if swap_wait_threshold > 0:
                        decision = 'Waiting' if (is_active_account and is_within_threshold) else 'Skipped'
                        if decision == 'Skipped':
                            if not is_active_account:
                                decision = 'Skipped (Not Active)'
                            elif not is_within_threshold:
                                decision = 'Skipped (Over Threshold)'
                                
                        eval_msg = (
                            f"[BotOrchestrator] Smart Wait Eval for {acc_id}: "
                            f"CD=({remaining_cd/60:.1f}m / {swap_wait_threshold/60:.0f}m) "
                            f"| ActiveID='{last_account_id}' vs TargetID='{expected_gid_for_wait}' "
                            f"-> {decision}"
                        )
                        print(eval_msg)
                        
                        # Log to file for historical debugging
                        log_smart_wait_eval(
                            serial=f"emulator-{5554 + emu_idx * 2}",
                            target_account_id=acc_id,
                            active_account_id=last_account_id or "UNKNOWN",
                            remaining_cd_sec=remaining_cd,
                            threshold_sec=swap_wait_threshold,
                            decision=decision,
                        )

                    if is_active_account and is_within_threshold:
                        print(
                            f"[BotOrchestrator] Smart Wait: account {acc_id} is active and cooldown ends in "
                            f"{remaining_cd/60:.1f}m (threshold: {swap_wait_threshold/60:.0f}m). Waiting..."
                        )
                        self._smart_wait_info = {"account_id": acc_id, "remaining_sec": round(remaining_cd, 1)}
                        await self._emit_timeline("\u23f3", f"Emu {emu_idx}: Smart Wait for {acc.get('lord_name') or acc_id} ({remaining_cd/60:.1f}m remaining)", emu_idx, acc_id)
                        await self.broadcast_state()
                        while remaining_cd > 0 and not self.stop_requested:
                            chunk = min(remaining_cd, 10)
                            await asyncio.sleep(chunk)
                            remaining_cd -= chunk
                            self._smart_wait_info["remaining_sec"] = round(max(0, remaining_cd), 1)
                        self._smart_wait_info = {"account_id": None, "remaining_sec": None}
                        # Fall through to normal processing — no skip, no swap needed
                    else:
                        # Normal cooldown skip
                        consecutive_skips += 1

                        # If we've skipped ALL accounts → everyone is on cooldown
                        if consecutive_skips >= len(self.queue):
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
                            print(
                                f"[BotOrchestrator] All accounts on cooldown. Sleeping {sleep_min}m until next account is ready."
                            )
                            await self._emit_timeline("\ud83d\udca4", f"All accounts on cooldown. Sleeping {sleep_min}m")
                            await self.broadcast_state()

                            while sleep_sec > 0 and not self.stop_requested:
                                chunk = min(sleep_sec, 10)
                                await asyncio.sleep(chunk)
                                sleep_sec -= chunk

                            consecutive_skips = 0
                        else:
                            self.account_statuses[acc_id] = "pending"
                            self._advance_queue()
                        continue

                # ── PRE-CHECK: Skip swap if ALL activities are on cooldown ──
                if await self._all_activities_on_cooldown(acc_id):
                    print(
                        f"[BotOrchestrator] All activities on cooldown for Account {acc_id}. "
                        f"Skipping swap."
                    )
                    await self._emit_timeline(
                        "⏭️",
                        f"Skipped {acc.get('lord_name') or acc_id}: all activities on cooldown",
                        emu_idx, acc_id,
                    )
                    self.account_statuses[acc_id] = "pending"
                    consecutive_skips += 1
                    if consecutive_skips >= len(self.queue):
                        # All accounts fully on cooldown → compute sleep from activity cooldowns
                        sleep_sec = await self._earliest_activity_ready_sec()
                        sleep_min = round(sleep_sec / 60, 1)
                        print(
                            f"[BotOrchestrator] All accounts on cooldown (activity-level). "
                            f"Sleeping {sleep_min}m until next activity is ready."
                        )
                        await self._emit_timeline("💤", f"All accounts on cooldown. Sleeping {sleep_min}m")
                        await self.broadcast_state()
                        while sleep_sec > 0 and not self.stop_requested:
                            chunk = min(sleep_sec, 10)
                            await asyncio.sleep(chunk)
                            sleep_sec -= chunk
                        consecutive_skips = 0
                    else:
                        self._advance_queue()
                    continue

                # ── PRE-CHECK: Skip swap if only light tasks are ready (heavy tasks on cooldown) ──
                if await self._only_light_tasks_ready(acc_id):
                    print(
                        f"[BotOrchestrator] Only light activities ready for Account {acc_id}. "
                        f"Skipping swap to preserve cooldown for heavy tasks."
                    )
                    await self._emit_timeline(
                        "🪶",
                        f"Skipped {acc.get('lord_name') or acc_id}: only light tasks ready, waiting for heavy",
                        emu_idx, acc_id,
                    )
                    self.account_statuses[acc_id] = "pending"
                    consecutive_skips += 1
                    if consecutive_skips >= len(self.queue):
                        sleep_sec = await self._earliest_activity_ready_sec(heavy_only=True)
                        sleep_min = round(sleep_sec / 60, 1)
                        print(
                            f"[BotOrchestrator] All accounts waiting for heavy tasks. "
                            f"Sleeping {sleep_min}m until next heavy activity is ready."
                        )
                        await self._emit_timeline("💤", f"Waiting for heavy tasks. Sleeping {sleep_min}m")
                        await self.broadcast_state()
                        while sleep_sec > 0 and not self.stop_requested:
                            chunk = min(sleep_sec, 10)
                            await asyncio.sleep(chunk)
                            sleep_sec -= chunk
                        consecutive_skips = 0
                    else:
                        self._advance_queue()
                    continue

                # Account is ready — reset skip counter
                consecutive_skips = 0

                self.account_statuses[acc_id] = "running"
                # Resolve package per-account provider (Global → .gp, Asia → .gp.vn)
                self.package_name = core_actions.get_package_for_provider(acc.get("provider"))
                await self.broadcast_state()

                print(
                    f"[BotOrchestrator] --- CYCLE {self.cycle} | ACCOUNT {self.current_idx + 1}/{len(self.queue)} | EMU {emu_idx} ---"
                )
                await self._emit_timeline("\ud83d\udd01", f"Cycle {self.cycle} \u2014 Account {self.current_idx + 1}/{len(self.queue)}: {acc.get('lord_name') or acc_id} on Emu {emu_idx}", emu_idx, acc_id)
                if last_emu_index is not None:
                    if last_emu_index != emu_idx:
                        # DIFFERENT EMULATOR -> Cross-emu swap
                        log_main_loop_swap_decision(
                            acc_id, str(acc.get('game_id', '')), emu_idx,
                            last_emu_idx=last_emu_index, last_account_id=last_account_id,
                            decision="cross_emu_swap",
                            detail=f"Emu {last_emu_index} -> {emu_idx}",
                        )
                        swap_ok = await self._handle_cross_emu_swap(last_emu_index, emu_idx)
                        if not swap_ok:
                            print(f"[BotOrchestrator] Cross-emu swap FAILED. Skipping account.")
                            self.account_statuses[acc_id] = "error"
                            # Do NOT set last_emu_index - next account should retry boot
                            self._advance_queue()
                            continue
                        
                        # Reset known live account since we just booted a new emulator
                        last_account_id = None
                        self._last_verified_account_id = None
                    elif last_account_id:
                        log_main_loop_swap_decision(
                            acc_id, str(acc.get('game_id', '')), emu_idx,
                            last_emu_idx=last_emu_index, last_account_id=last_account_id,
                            decision="in_game_swap" if last_account_id != str(acc.get('game_id', '')) else "no_swap_needed",
                            detail=f"Same emu, last_account={last_account_id}",
                        )
                        print(
                            f"[BotOrchestrator] Last verified live account on Emu {emu_idx}: {last_account_id}. Re-verifying target {acc.get('game_id', '')}."
                        )
                else:
                    # BEGINNING OF RUN (last_emu_index is None) -> MUST LAUNCH FIRST EMULATOR
                    log_main_loop_swap_decision(
                        acc_id, str(acc.get('game_id', '')), emu_idx,
                        last_emu_idx=None, last_account_id=None,
                        decision="first_launch",
                        detail=f"Initial boot of Emu {emu_idx}",
                    )
                    print(f"[BotOrchestrator] Launching initial Emu {emu_idx}...")

                    # Check if already running to save wait time
                    current_instances = list_all_instances()
                    is_running = any(
                        inst["index"] == emu_idx and inst.get("running")
                        for inst in current_instances
                    )

                    if not is_running:
                        await asyncio.to_thread(launch_instance, emu_idx)
                        print(
                            f"[BotOrchestrator] Waiting for initial Emu {emu_idx} to fully boot..."
                        )
                        boot_ok = await asyncio.to_thread(wait_for_device, emu_idx, 120)
                        if not boot_ok:
                            # Retry once
                            print(f"[BotOrchestrator] Boot timeout. Retrying with 60s...")
                            boot_ok = await asyncio.to_thread(wait_for_device, emu_idx, 60)
                        if not boot_ok:
                            print(f"[BotOrchestrator] Emu {emu_idx} boot FAILED after retry. Skipping account.")
                            self.account_statuses[acc_id] = "error"
                            # Do NOT set last_emu_index - next account should retry boot
                            self._advance_queue()
                            continue
                        await asyncio.sleep(5)
                    else:
                        print(
                            f"[BotOrchestrator] Initial Emu {emu_idx} is already running."
                        )

                serial = f"emulator-{5554 + emu_idx * 2}"
                detector = GameStateDetector(
                    adb_path=config.adb_path,
                    templates_dir=self.templates_dir,
                )

                print(f"[BotOrchestrator] Ensuring game is running and at lobby on Emu {emu_idx}...")
                lobby_ok = await self._ensure_lobby(serial, detector, 120)
                
                if not lobby_ok:
                    print(f"[BotOrchestrator] Failed to reach lobby on Emu {emu_idx}. Skipping account.")
                    self.account_statuses[acc_id] = "error"
                    last_emu_index = emu_idx
                    self._advance_queue()
                    continue

                # ── SMART QUEUE: Early probe on first iteration to reorder queue ──
                if last_account_id is None and lobby_ok:
                    probe = await self._read_live_account_id(serial, detector, "smart queue probe")
                    if probe["account_id"]:
                        last_account_id = probe["account_id"]
                        self._last_verified_account_id = last_account_id
                        print(
                            f"[BotOrchestrator] Smart Queue: detected active account "
                            f"{last_account_id} on Emu {emu_idx}. Reordering queue..."
                        )
                        log_early_probe(
                            serial, emu_idx, last_account_id,
                            detail="Detected active account, triggering queue reorder",
                        )
                        self._reorder_queue_for_active_account(last_account_id)
                        
                        # Fix misaligned current_idx: Reset to the start of this emulator's group
                        # and let the main loop re-evaluate from the newly ordered head!
                        first_idx_for_emu = next(
                            (i for i, a in enumerate(self.queue) if int(a.get("emu_index") or 0) == emu_idx), 
                            self.current_idx
                        )
                        print(
                            f"[BotOrchestrator] Restarting evaluation for Emu {emu_idx} at index {first_idx_for_emu} after reorder."
                        )
                        self.current_idx = first_idx_for_emu
                        
                        # Preserve last_emu_index so the next iteration doesn't reset last_account_id 
                        # and cause an infinite probe loop.
                        last_emu_index = emu_idx
                        continue
                    else:
                        log_early_probe(
                            serial, emu_idx, None,
                            detail="Early probe could not detect account ID",
                        )

                expected_game_id = str(acc.get("game_id") or "").strip()
                if not expected_game_id:
                    print(
                        f"[BotOrchestrator] Account {acc_id} has no expected game_id. Skipping account."
                    )
                    self.account_statuses[acc_id] = "error"
                    last_emu_index = emu_idx
                    self._advance_queue()
                    continue

                target_lord = (acc.get("lord_name") or "").strip() or None
                if target_lord and ('"' in target_lord or "'" in target_lord or ' ' in target_lord):
                    print(f"[BotOrchestrator] ⚠ lord_name may contain OCR noise: '{target_lord}'")
                account_detector = AccountDetector(adb_path=config.adb_path)

                # Skip _ensure_correct_account if early probe already verified this account
                if last_account_id and last_account_id == expected_game_id:
                    print(
                        f"[BotOrchestrator] Skipping re-verification: early probe already confirmed account {expected_game_id}"
                    )
                    log_main_loop_swap_decision(
                        acc_id, expected_game_id, emu_idx,
                        last_emu_idx=last_emu_index, last_account_id=last_account_id,
                        decision="skip_verified",
                        detail="Early probe already confirmed correct account",
                    )
                    account_ready = True
                    verified_account_id = last_account_id
                else:
                    account_ready, verified_account_id = await self._ensure_correct_account(
                        serial,
                        detector,
                        account_detector,
                        expected_game_id,
                        target_lord,
                        known_current_account_id=last_account_id,
                        emu_idx=emu_idx,
                        acc_id=acc_id,
                    )
                if not account_ready:
                    print(
                        f"[BotOrchestrator] Could not verify target account {expected_game_id} on Emu {emu_idx}. Skipping account."
                    )
                    self.account_statuses[acc_id] = "error"
                    last_emu_index = emu_idx
                    self._advance_queue()
                    continue

                if verified_account_id != expected_game_id:
                    self._log_account_verification_failure(
                        expected_game_id,
                        verified_account_id,
                        "final activity guard",
                    )
                    account_ready, verified_account_id = await self._ensure_correct_account(
                        serial,
                        detector,
                        account_detector,
                        expected_game_id,
                        target_lord,
                        emu_idx=emu_idx,
                        acc_id=acc_id,
                    )
                    if not account_ready:
                        print(
                            f"[BotOrchestrator] Final activity guard could not recover target account {expected_game_id}. Skipping account."
                        )
                        self.account_statuses[acc_id] = "error"
                        last_emu_index = emu_idx
                        self._advance_queue()
                        continue

                # Wait slightly before starting activities
                await asyncio.sleep(2)

                # Reset all activity statuses for the current account run
                act_keys = [
                    act.get("id", act.get("name", f"act_{i}"))
                    for i, act in enumerate(self.activities)
                ]
                self.activity_statuses = {k: "pending" for k in act_keys}

                # Shuffle activity order per-account for anti-detection
                # Then fix relative order of troop-dependent activities:
                #   claim_scout_sentry → attack_darkling → catch_pet/gather_rss_center (random) → gather_resource (last)
                # because gather_resource uses ALL troops and would block the others.
                TROOP_ORDER = {
                    "claim_scout_sentry_task": 0,   # scouts needed before combat
                    "attack_darkling_legions": 1,    # uses combat troops
                    "catch_pet": 2,                  # uses troops (random with rss_center)
                    "gather_rss_center": 2,          # uses troops (random with catch_pet)
                    "gather_resource": 99,           # LAST — uses ALL remaining troops
                }

                run_order = list(range(len(self.activities)))
                random.shuffle(run_order)

                # Find positions where troop activities landed after shuffle
                troop_positions = []  # (position_in_run_order, original_index)
                for pos, orig_idx in enumerate(run_order):
                    aid = act_keys[orig_idx]
                    if aid in TROOP_ORDER:
                        troop_positions.append((pos, orig_idx))

                if len(troop_positions) >= 2:
                    # Sort troop items by their priority, with same-priority items shuffled
                    troop_items = [(TROOP_ORDER[act_keys[oi]], random.random(), oi) for _, oi in troop_positions]
                    troop_items.sort()
                    desired_troop_order = [oi for _, _, oi in troop_items]

                    # Assign desired order into the sorted positions
                    sorted_positions = sorted(p for p, _ in troop_positions)
                    for slot_pos, orig_idx in zip(sorted_positions, desired_troop_order):
                        run_order[slot_pos] = orig_idx

                shuffled_activities = [self.activities[j] for j in run_order]
                shuffled_keys = [act_keys[j] for j in run_order]
                print(
                    f"[BotOrchestrator] Shuffled activity order for Account {acc_id}: "
                    f"{[a.get('name', k) for a, k in zip(shuffled_activities, shuffled_keys)]}"
                )

                limit_min = self.misc_config.get("limit_min", 0)
                account_success = True
                ran_heavy = False  # Track if any heavy activity succeeded (for conditional account CD)
                ran_heavy_attempted = False  # Track if any heavy activity was attempted (for failure CD)

                # Execute activities one by one (shuffled order)
                for i, act in enumerate(shuffled_activities):
                    if self.stop_requested:
                        break

                    act_id_or_name = shuffled_keys[i]
                    act_cfg = act.get("config", {})

                    # ── ACTIVITY-LEVEL COOLDOWN (dynamic override > static config) ──
                    if not self.skip_cooldown and act_cfg.get("cooldown_enabled"):
                        cd_minutes = act_cfg.get("cooldown_minutes", 0)
                        if cd_minutes > 0:
                            last_act_run, dynamic_cd = await execution_log.get_effective_cooldown_sec(int(acc_id), act_id_or_name)
                            effective_cd = dynamic_cd if dynamic_cd > 0 else (cd_minutes * 60)
                            if last_act_run > 0 and (time.time() - last_act_run) < effective_cd:
                                cd_src = "dynamic" if dynamic_cd > 0 else "static"
                                remain_m = round((effective_cd - (time.time() - last_act_run)) / 60, 1)
                                print(f"[BotOrchestrator] Activity '{act_id_or_name}' on cooldown ({cd_src}: {effective_cd/60:.0f}m, {remain_m}m left) for Account {acc_id}. Skipping.")
                                self.activity_statuses[act_id_or_name] = "skipped"
                                await self.broadcast_state()
                                continue

                    steps = workflow_registry.build_steps_for_activity(
                        act_id_or_name, act_cfg
                    )

                    if not steps:
                        print(
                            f"[BotOrchestrator] Unknown activity '{act_id_or_name}', skipping."
                        )
                        self.activity_statuses[act_id_or_name] = "skipped"
                        continue

                    # Inject account_id + global limits into each step config
                    for step in steps:
                        step_cfg = step.setdefault("config", {})
                        step_cfg["account_id"] = acc_id
                        step_cfg["max_power"] = self.misc_config.get("max_power", 14_000_000)
                        step_cfg["max_hall_level"] = self.misc_config.get("max_hall_level", 21)

                    self.current_activity = {
                        "id": act_id_or_name,
                        "name": act.get("name", act_id_or_name),
                        "status": "running",
                    }
                    self.activity_statuses[act_id_or_name] = "running"
                    await self.broadcast_state()

                    # Track heavy attempt BEFORE execution (for failure cooldown)
                    act_weight_pre = act_cfg.get("weight") or self._weight_map.get(act_id_or_name, "heavy")
                    if act_weight_pre == "heavy":
                        ran_heavy_attempted = True

                    step_start = time.time()
                    result = None
                    step_status = "FAILED"
                    step_error = ""
                    error_code = ""

                    # ── LOG: Activity Started ──
                    log_id = await execution_log.start_account_activity(
                        run_id=self.run_id,
                        account_id=int(acc_id),
                        game_id=acc.get("game_id", ""),
                        emulator_id=emu_idx,
                        group_id=self.group_id,
                        activity_id=act_id_or_name,
                        activity_name=act.get("name", act_id_or_name),
                        source="workflow",
                        metadata=act_cfg,
                    )

                    # Emit WS event: activity started
                    await self._emit_activity_event(
                        "activity_started",
                        acc_id,
                        act_id_or_name,
                        act.get("name", act_id_or_name),
                    )
                    await self._emit_timeline("\u25b6\ufe0f", f"{acc.get('lord_name') or acc_id}: Starting {act.get('name', act_id_or_name)}", emu_idx, acc_id)

                    try:
                        if limit_min > 0:
                            result = await asyncio.wait_for(
                                self._execute_current_account(emu_idx, emu_name, steps),
                                timeout=limit_min * 60,
                            )
                        else:
                            result = await self._execute_current_account(
                                emu_idx, emu_name, steps
                            )

                        if not result or not result.get("success", False):
                            account_success = False
                            self.activity_statuses[act_id_or_name] = "error"
                            self.current_activity["status"] = "error"
                            step_error = (
                                result.get("error", "Unknown execution failure")
                                if result
                                else "No result returned"
                            )
                            error_code = "EXEC_FAIL"
                        else:
                            self.activity_statuses[act_id_or_name] = "done"
                            step_status = "SUCCESS"
                            # Track if a heavy activity succeeded (for conditional account CD)
                            act_weight = act_cfg.get("weight") or self._weight_map.get(act_id_or_name, "heavy")
                            if act_weight == "heavy":
                                ran_heavy = True

                            # ── RANDOM COOLDOWN RANGE ──
                            # If user configured a range (cooldown_minutes_max > cooldown_minutes)
                            # and core_actions didn't already set a dynamic_cooldown, pick a random
                            # value and inject it into result so it gets persisted to DB.
                            try:
                                cd_min = int(act_cfg.get("cooldown_minutes", 0) or 0)
                                cd_max = int(act_cfg.get("cooldown_minutes_max", 0) or 0)
                            except (TypeError, ValueError):
                                cd_min, cd_max = 0, 0
                            has_dynamic = (result or {}).get("dynamic_cooldown_sec", 0) > 0
                            if cd_max > cd_min > 0 and not has_dynamic:
                                rand_cd_sec = int(random.uniform(cd_min, cd_max) * 60)
                                if result is None:
                                    result = {}
                                result["dynamic_cooldown_sec"] = rand_cd_sec
                                print(
                                    f"[BotOrchestrator] 🎲 Random cooldown for '{act_id_or_name}': "
                                    f"{rand_cd_sec // 60}m (range: {cd_min}-{cd_max}m)"
                                )

                        await self.broadcast_state()

                    except asyncio.TimeoutError:
                        print(
                            f"[BotOrchestrator] Account {acc_id} hit Time Limit ({limit_min}m) during {act_id_or_name}. Forcing swap."
                        )
                        account_success = False
                        self.activity_statuses[act_id_or_name] = "error"
                        self.current_activity["status"] = "error"
                        step_error = f"Timeout limit {limit_min}m reached"
                        error_code = "TIMEOUT"
                        await self.broadcast_state()
                    except Exception as e:
                        account_success = False
                        self.activity_statuses[act_id_or_name] = "error"
                        self.current_activity["status"] = "error"
                        step_error = str(e)
                        error_code = "EXCEPTION"
                        await self.broadcast_state()

                    step_end = time.time()
                    latency = int((step_end - step_start) * 1000)

                    # ── LOG: Activity Finished ──
                    await execution_log.finish_account_activity(
                        log_id=log_id,
                        status=step_status,
                        error_code=error_code,
                        error_message=step_error,
                        duration_ms=latency,
                        result=result if isinstance(result, dict) else {},
                    )

                    # Emit WS event: activity completed/failed
                    ws_event = (
                        "activity_completed"
                        if step_status == "SUCCESS"
                        else "activity_failed"
                    )
                    await self._emit_activity_event(
                        ws_event,
                        acc_id,
                        act_id_or_name,
                        act.get("name", act_id_or_name),
                        step_status,
                        step_error,
                        latency,
                    )
                    tl_icon = "\u2705" if step_status == "SUCCESS" else "\u274c"
                    tl_dur = f" ({latency/1000:.1f}s)" if latency > 0 else ""
                    await self._emit_timeline(tl_icon, f"{acc.get('lord_name') or acc_id}: {act.get('name', act_id_or_name)} {step_status.lower()}{tl_dur}", emu_idx, acc_id)

                    await execution_log.append_step_log(
                        run_id=self.run_id,
                        step_index=i,
                        function_id=act_id_or_name,
                        input_dict=act_cfg,
                        output_dict=result or {},
                        status=step_status,
                        error_msg=step_error,
                        latency_ms=latency,
                    )

                    if not account_success:
                        if self.continue_on_error:
                            print(f"[BotOrchestrator] Activity '{act_id_or_name}' failed, but continue_on_error is globally enabled. Continuing.")
                            account_success = True
                        else:
                            break  # stop processing activities for this account on error

                # End of activities loop for this account
                # Log finalized account status and broadcast fresh metrics
                await self.broadcast_state()

                self.current_activity = None

                # Update last run time for cooldown tracking
                # - SUCCESS path: only update if heavy activity ran (light-only = no account CD)
                # - ERROR path: ALWAYS update (prevent rapid re-run after failure)
                print(f"[DEBUG-CD] Account {acc_id} POST-LOOP: ran_heavy={ran_heavy}, ran_heavy_attempted={ran_heavy_attempted}, account_success={account_success}")
                if ran_heavy or ran_heavy_attempted or (not account_success):
                    self.last_run_times[acc_id] = time.time()
                    print(f"[DEBUG-CD] Account {acc_id}: last_run_times UPDATED to {time.time():.0f}")

                if account_success and not self.stop_requested:
                    self.account_statuses[acc_id] = "done"
                else:
                    self.account_statuses[acc_id] = "error"

                last_emu_index = emu_idx
                last_account_id = verified_account_id
                self._last_verified_account_id = verified_account_id

                self._advance_queue()

        except asyncio.CancelledError:
            print(
                f"[BotOrchestrator] Execution cancelled via stop() for group {self.group_id}."
            )
            self.stop_requested = True  # Ensure this is flagged
        except Exception as e:
            print(f"[BotOrchestrator] Fatal error in loop: {e}")
        finally:
            self.is_running = False
            await self.broadcast_state()

            duration = int(
                (time.time() - getattr(self, "run_start_time", time.time())) * 1000
            )
            await execution_log.complete_run(
                self.run_id, "STOPPED" if self.stop_requested else "COMPLETED", duration
            )

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
            # Smart reorder: prioritize currently-active account to avoid swap-back
            if self._last_verified_account_id:
                self._reorder_queue_for_active_account(self._last_verified_account_id)
            # Reset all statuses for the new cycle
            for key in self.account_statuses:
                self.account_statuses[key] = "pending"

    def _reorder_queue_for_active_account(self, active_account_id: str):
        """Reorder queue so the currently-active account on each emulator
        runs first, minimizing unnecessary swaps.

        Groups accounts by emu_index, then within each group:
        - If the active account is in this group → move it to front of group
        - Otherwise → keep original order

        Preserves cross-emulator ordering (emu0 group before emu1 group).
        """
        from collections import OrderedDict

        old_order = [str(a.get('game_id', '')) for a in self.queue]

        groups = OrderedDict()
        for acc in self.queue:
            emu = acc.get("emu_index") or 999
            groups.setdefault(emu, []).append(acc)

        reordered = []
        changed = False

        for emu, accs in groups.items():
            active_idx = None
            for i, a in enumerate(accs):
                if str(a.get("game_id", "")).strip() == active_account_id:
                    active_idx = i
                    break

            if active_idx is not None and active_idx != 0:
                active_acc = accs.pop(active_idx)
                accs.insert(0, active_acc)
                changed = True

            reordered.extend(accs)

        if changed:
            self.queue = reordered
            new_order = [str(a.get('game_id', '')) for a in self.queue]
            print(
                f"[BotOrchestrator] Smart Queue: reordered for active account {active_account_id}. "
                f"Order: {old_order} → {new_order}"
            )
            log_queue_reorder(
                active_account_id, old_order, new_order,
                trigger="early_probe" if self.cycle == 1 else "cycle_end",
            )
        else:
            log_queue_reorder(
                active_account_id, old_order, old_order,
                trigger="no_change",
            )


def start_sequential_orchestrator(
    group_id: int,
    accounts: List[Dict],
    activities: List[Dict],
    ws_callback: Callable,
    misc_config: Dict = None,
    start_account_id: int = None,
) -> BotOrchestrator:
    """Creates and starts a new BotOrchestrator for a group."""
    # Prevent duplicate starts — preserve cooldown state
    if group_id in _active_orchestrators:
        existing = _active_orchestrators[group_id]
        if existing.is_running:
            return existing  # Already running, don't reset
        # Not running anymore — clean up old reference
        del _active_orchestrators[group_id]

    orch = BotOrchestrator(
        group_id, accounts, activities, ws_callback, misc_config, start_account_id
    )
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
            "current_activity": orch.current_activity,
            "activity_statuses": orch.activity_statuses,
            "account_statuses": orch.account_statuses,
            "accounts": [
                {
                    "id": acc["id"],
                    "lord_name": acc.get("lord_name") or acc.get("game_id", "Unknown"),
                    "emu_index": acc.get("emu_index"),
                    "status": orch.account_statuses.get(str(acc["id"]), "pending"),
                }
                for acc in orch.queue
            ],
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





