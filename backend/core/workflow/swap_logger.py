"""
Swap Account Logger — File-based diagnostics for account swap operations.

Writes structured JSONL logs to `logs/swap_account/` to track:
  - Cross-emulator swaps (quit old emu → boot new emu)
  - In-game account swaps (swap_account via AccountDetector)
  - Account verification (pre-swap, post-swap, early probe)
  - Queue reordering decisions
  - Restart recovery attempts
  - Final swap outcomes (success/failure with reason)
"""

import os
import json
from datetime import datetime
from typing import Optional, Any

_LOG_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "logs", "swap_account"
)


def _ensure_log_dir():
    os.makedirs(_LOG_DIR, exist_ok=True)


def _write_entry(entry: dict):
    """Append a single JSON line to today's log file."""
    _ensure_log_dir()
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(_LOG_DIR, f"swap_{today}.jsonl")
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass  # Never crash the orchestrator


def log_cross_emu_swap(
    old_emu: int,
    new_emu: int,
    phase: str,
    success: bool,
    detail: str = "",
):
    """Log a cross-emulator swap event.

    Args:
        old_emu: Source emulator index
        new_emu: Target emulator index
        phase: 'start', 'quit_old', 'launch_new', 'boot_wait', 'boot_retry', 'complete'
        success: Whether this phase succeeded
        detail: Additional context
    """
    _write_entry({
        "ts": datetime.now().isoformat(),
        "event": "cross_emu_swap",
        "old_emu": old_emu,
        "new_emu": new_emu,
        "phase": phase,
        "success": success,
        "detail": detail,
    })


def log_account_verification(
    serial: str,
    context: str,
    expected_game_id: str,
    actual_account_id: Optional[str],
    match: bool,
    detail: str = "",
):
    """Log an account verification check.

    Args:
        serial: Emulator serial (e.g. 'emulator-5556')
        context: Where verification happened (e.g. 'pre-swap', 'post-swap attempt 1', 'early probe')
        expected_game_id: The game_id we wanted
        actual_account_id: The game_id we actually read (None if unreadable)
        match: Whether expected == actual
        detail: Additional context
    """
    _write_entry({
        "ts": datetime.now().isoformat(),
        "event": "account_verification",
        "serial": serial,
        "context": context,
        "expected_game_id": expected_game_id,
        "actual_account_id": actual_account_id or "<unreadable>",
        "match": match,
        "detail": detail,
    })


def log_swap_attempt(
    serial: str,
    attempt: int,
    max_attempts: int,
    expected_game_id: str,
    target_lord: Optional[str],
    swap_result: bool,
    post_verify_id: Optional[str] = None,
    final_match: bool = False,
    detail: str = "",
):
    """Log an in-game swap_account() call and its result.

    Args:
        serial: Emulator serial
        attempt: Current attempt number (1-based)
        max_attempts: Total allowed attempts
        expected_game_id: Target game_id
        target_lord: Target lord_name (used for swap UI matching)
        swap_result: Return value of core_actions.swap_account()
        post_verify_id: Account ID read after swap (None if not yet verified)
        final_match: Whether post-verify matches expected
        detail: Additional context
    """
    _write_entry({
        "ts": datetime.now().isoformat(),
        "event": "swap_attempt",
        "serial": serial,
        "attempt": f"{attempt}/{max_attempts}",
        "expected_game_id": expected_game_id,
        "target_lord": target_lord or "<none>",
        "swap_fn_result": swap_result,
        "post_verify_id": post_verify_id or "<pending>",
        "final_match": final_match,
        "detail": detail,
    })


def log_ensure_correct_account(
    serial: str,
    expected_game_id: str,
    phase: str,
    success: bool,
    known_current_id: Optional[str] = None,
    final_id: Optional[str] = None,
    detail: str = "",
):
    """Log the _ensure_correct_account overall flow.

    Args:
        serial: Emulator serial
        expected_game_id: Target game_id
        phase: 'start', 'already_correct', 'mismatch_detected', 'swap_loop_done', 'failed'
        success: Whether the operation succeeded
        known_current_id: The account ID known before any swap
        final_id: The final verified account ID
        detail: Additional context
    """
    _write_entry({
        "ts": datetime.now().isoformat(),
        "event": "ensure_correct_account",
        "serial": serial,
        "expected_game_id": expected_game_id,
        "phase": phase,
        "success": success,
        "known_current_id": known_current_id or "<none>",
        "final_id": final_id or "<none>",
        "detail": detail,
    })


def log_restart_recovery(
    serial: str,
    expected_game_id: str,
    lobby_ok: bool,
    detail: str = "",
):
    """Log a game restart recovery attempt before the final swap try."""
    _write_entry({
        "ts": datetime.now().isoformat(),
        "event": "restart_recovery",
        "serial": serial,
        "expected_game_id": expected_game_id,
        "lobby_ok": lobby_ok,
        "detail": detail,
    })


def log_queue_reorder(
    active_account_id: str,
    old_order: list,
    new_order: list,
    trigger: str = "cycle_end",
):
    """Log a Smart Queue reorder event.

    Args:
        active_account_id: The account ID that triggered the reorder
        old_order: Previous queue order (list of game_ids)
        new_order: New queue order (list of game_ids)
        trigger: What triggered the reorder ('early_probe', 'cycle_end')
    """
    _write_entry({
        "ts": datetime.now().isoformat(),
        "event": "queue_reorder",
        "active_account_id": active_account_id,
        "old_order": old_order,
        "new_order": new_order,
        "trigger": trigger,
    })


def log_early_probe(
    serial: str,
    emu_idx: int,
    detected_account_id: Optional[str],
    detail: str = "",
):
    """Log the early probe detection of which account is active on an emulator."""
    _write_entry({
        "ts": datetime.now().isoformat(),
        "event": "early_probe",
        "serial": serial,
        "emu_idx": emu_idx,
        "detected_account_id": detected_account_id or "<unreadable>",
        "detail": detail,
    })


def log_main_loop_swap_decision(
    acc_id: str,
    expected_game_id: str,
    emu_idx: int,
    last_emu_idx: Optional[int],
    last_account_id: Optional[str],
    decision: str,
    detail: str = "",
):
    """Log the main loop decision about what kind of swap is needed.

    Args:
        acc_id: Database account ID
        expected_game_id: Target game_id for this account
        emu_idx: Target emulator index
        last_emu_idx: Previous emulator index (None = first run)
        last_account_id: Last verified account ID on the emulator
        decision: 'cross_emu_swap', 'in_game_swap', 'skip_verified', 'first_launch', 'no_swap_needed'
        detail: Additional context
    """
    _write_entry({
        "ts": datetime.now().isoformat(),
        "event": "main_loop_swap_decision",
        "acc_id": acc_id,
        "expected_game_id": expected_game_id,
        "emu_idx": emu_idx,
        "last_emu_idx": last_emu_idx,
        "last_account_id": last_account_id or "<none>",
        "decision": decision,
        "detail": detail,
    })
