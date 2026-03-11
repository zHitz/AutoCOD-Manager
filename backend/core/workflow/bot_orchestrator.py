import asyncio
import time
from typing import List, Dict, Any, Callable, Optional, Tuple
from backend.core.workflow import (
    adb_helper,
    executor,
    core_actions,
    workflow_registry,
    execution_log,
)
import uuid
from backend.core.workflow.state_detector import GameStateDetector
from backend.core.workflow.account_detector import AccountDetector
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
        self.package_name = "com.farlightgames.samo.gp.vn"

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
                    "status": self.account_statuses.get(str(acc["id"]), "pending"),
                }
                for acc in self.queue
            ],
            "activity_metrics": await self._get_activity_metrics(),
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

    async def _handle_cross_emu_swap(self, old_emu_index: int, new_emu_index: int) -> bool:
        """Closes old emulator / game and boots new one. Returns True on success."""
        import logging

        print(
            f"[BotOrchestrator] Cross-Emu Swap: Switching from Emu {old_emu_index} to Emu {new_emu_index}"
        )
        logging.info(
            f"Cross-Emu Swap: Switching from Emu {old_emu_index} to Emu {new_emu_index}"
        )

        print(f"[BotOrchestrator] Quitting Emu {old_emu_index}...")
        await asyncio.to_thread(quit_instance, old_emu_index)

        await asyncio.sleep(3)  # Wait for LDPlayer to close properly

        print(f"[BotOrchestrator] Launching Emu {new_emu_index}...")
        await asyncio.to_thread(launch_instance, new_emu_index)

        print(f"[BotOrchestrator] Waiting for Emu {new_emu_index} to fully boot...")
        boot_ok = await asyncio.to_thread(wait_for_device, new_emu_index, 120)
        if not boot_ok:
            # Retry once with shorter timeout
            print(f"[BotOrchestrator] Boot timeout. Retrying with 60s...")
            boot_ok = await asyncio.to_thread(wait_for_device, new_emu_index, 60)
        if not boot_ok:
            print(f"[BotOrchestrator] Emu {new_emu_index} boot FAILED after retry.")
            return False
        # Short grace period for OS services to settle after boot_completed
        await asyncio.sleep(5)
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

    async def _read_live_account_id(
        self, serial: str, detector: GameStateDetector, context: str
    ) -> Dict[str, Any]:
        """Read the active in-game account ID, retrying the ID extraction once if needed."""
        lobby_ok = await self._ensure_lobby(serial, detector)
        if not lobby_ok:
            print(
                f"[BotOrchestrator] Cannot verify account during {context}: lobby not reachable."
            )
            return {"lobby_ok": False, "account_id": None}

        profile_ok = await asyncio.to_thread(core_actions.go_to_profile, serial, detector)
        if not profile_ok:
            print(
                f"[BotOrchestrator] Cannot verify account during {context}: profile not reachable."
            )
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
        else:
            print(
                f"[BotOrchestrator] Live account verification during {context} could not read account_id."
            )

        return {"lobby_ok": True, "account_id": account_id}

    async def _restart_game_app(
        self, serial: str, detector: GameStateDetector
    ) -> bool:
        """Restart the game app as a last-resort recovery before the final swap attempt."""
        print(f"[BotOrchestrator] Restarting game app on {serial} before final swap attempt...")
        await asyncio.to_thread(
            adb_helper._run_adb,
            ["shell", "am", "force-stop", self.package_name],
            serial,
            15,
        )
        await asyncio.sleep(2)
        return await self._ensure_lobby(serial, detector)

    async def _ensure_correct_account(
        self,
        serial: str,
        detector: GameStateDetector,
        account_detector: AccountDetector,
        expected_game_id: str,
        target_lord: Optional[str],
    ) -> Tuple[bool, Optional[str]]:
        """Guarantee the live account matches the target account before activities run."""
        verify_result = await self._read_live_account_id(
            serial, detector, "pre-swap verification"
        )
        current_account_id = verify_result["account_id"]

        if current_account_id == expected_game_id:
            print(
                f"[BotOrchestrator] Verified correct account already active: {expected_game_id}"
            )
            return True, current_account_id

        self._log_account_verification_failure(
            expected_game_id, current_account_id, "pre-swap verification"
        )

        for attempt in range(1, 4):
            if attempt == 3:
                restart_ok = await self._restart_game_app(serial, detector)
                if not restart_ok:
                    print(
                        "[BotOrchestrator] App restart failed before final swap attempt."
                    )

            print(
                f"[BotOrchestrator] Swap verification attempt {attempt}/3 for expected_game_id={expected_game_id}"
            )
            swap_ok = await asyncio.to_thread(
                core_actions.swap_account,
                serial,
                account_detector,
                detector,
                target_lord,
            )
            if not swap_ok:
                print(
                    f"[BotOrchestrator] swap_account() reported failure on attempt {attempt}/3."
                )

            verify_result = await self._read_live_account_id(
                serial, detector, f"post-swap verification attempt {attempt}"
            )
            current_account_id = verify_result["account_id"]
            if current_account_id == expected_game_id:
                print(
                    f"[BotOrchestrator] Verified target account after swap attempt {attempt}: {expected_game_id}"
                )
                return True, current_account_id

            self._log_account_verification_failure(
                expected_game_id,
                current_account_id,
                f"post-swap verification attempt {attempt}",
            )

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

        await self.broadcast_state()

        # Pre-fetch emulator names for logging
        name_map = {e["index"]: e["name"] for e in list_all_instances()}

        last_emu_index = None
        last_account_id = None
        consecutive_skips = 0  # Track how many accounts skipped in a row
        
        # Pre-populate last_run_times from database
        if not self.skip_cooldown:
            for acc in self.accounts:
                db_last_run = await execution_log.get_last_account_run(int(acc["id"]))
                if db_last_run > 0:
                    self.last_run_times[str(acc["id"])] = db_last_run

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
                    if (
                        swap_wait_threshold > 0
                        and remaining_cd <= swap_wait_threshold
                        and last_account_id
                        and expected_gid_for_wait == last_account_id
                    ):
                        print(
                            f"[BotOrchestrator] Smart Wait: account {acc_id} is active and cooldown ends in "
                            f"{remaining_cd/60:.1f}m (threshold: {swap_wait_threshold/60:.0f}m). Waiting..."
                        )
                        await self.broadcast_state()
                        while remaining_cd > 0 and not self.stop_requested:
                            chunk = min(remaining_cd, 10)
                            await asyncio.sleep(chunk)
                            remaining_cd -= chunk
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

                # Account is ready — reset skip counter
                consecutive_skips = 0

                self.account_statuses[acc_id] = "running"
                await self.broadcast_state()

                print(
                    f"[BotOrchestrator] --- CYCLE {self.cycle} | ACCOUNT {self.current_idx + 1}/{len(self.queue)} | EMU {emu_idx} ---"
                )
                if last_emu_index is not None:
                    if last_emu_index != emu_idx:
                        # DIFFERENT EMULATOR -> Cross-emu swap
                        swap_ok = await self._handle_cross_emu_swap(last_emu_index, emu_idx)
                        if not swap_ok:
                            print(f"[BotOrchestrator] Cross-emu swap FAILED. Skipping account.")
                            self.account_statuses[acc_id] = "error"
                            # Do NOT set last_emu_index - next account should retry boot
                            self._advance_queue()
                            continue
                    elif last_account_id:
                        print(
                            f"[BotOrchestrator] Last verified live account on Emu {emu_idx}: {last_account_id}. Re-verifying target {acc.get('game_id', '')}."
                        )
                else:
                    # BEGINNING OF RUN (last_emu_index is None) -> MUST LAUNCH FIRST EMULATOR
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
                        self._reorder_queue_for_active_account(last_account_id)
                        acc = self.queue[self.current_idx]
                        acc_id = str(acc["id"])
                        emu_idx = int(acc.get("emu_index") or 0)
                        emu_name = name_map.get(emu_idx, f"Emulator-{emu_idx}")

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

                account_ready, verified_account_id = await self._ensure_correct_account(
                    serial,
                    detector,
                    account_detector,
                    expected_game_id,
                    target_lord,
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

                limit_min = self.misc_config.get("limit_min", 0)
                account_success = True

                # Execute activities one by one
                for i, act in enumerate(self.activities):
                    if self.stop_requested:
                        break

                    act_id_or_name = act_keys[i]
                    act_cfg = act.get("config", {})

                    # ── ACTIVITY-LEVEL COOLDOWN ──
                    if not self.skip_cooldown and act_cfg.get("cooldown_enabled"):
                        cd_minutes = act_cfg.get("cooldown_minutes", 0)
                        if cd_minutes > 0:
                            last_act_run = await execution_log.get_last_activity_run(int(acc_id), act_id_or_name)
                            if last_act_run > 0 and (time.time() - last_act_run) < (cd_minutes * 60):
                                print(f"[BotOrchestrator] Activity '{act_id_or_name}' is on cooldown for Account {acc_id}. Skipping.")
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

                    self.current_activity = {
                        "id": act_id_or_name,
                        "name": act.get("name", act_id_or_name),
                        "status": "running",
                    }
                    self.activity_statuses[act_id_or_name] = "running"
                    await self.broadcast_state()

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
                        break  # stop processing activities for this account on error

                # End of activities loop for this account
                # Log finalized account status and broadcast fresh metrics
                await self.broadcast_state()

                self.current_activity = None

                # Update last run time for cooldown tracking
                self.last_run_times[acc_id] = time.time()

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
            old_order = [str(a.get('game_id', '')) for a in self.queue]
            self.queue = reordered
            new_order = [str(a.get('game_id', '')) for a in self.queue]
            print(
                f"[BotOrchestrator] Smart Queue: reordered for active account {active_account_id}. "
                f"Order: {old_order} → {new_order}"
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





