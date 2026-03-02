"""
Scheduler Engine — Background scheduler for macro jobs.
Checks schedules every 30s and executes due macros on target emulators.
"""
import asyncio
import json
import threading
import time
from datetime import datetime, timedelta

from backend.storage.database import database
from backend.core import macro_replay, ldplayer_manager
from backend.core.emulator import emulator_manager


def _calc_next_run(schedule_type: str, schedule_value: str, from_time: datetime = None) -> str:
    """Calculate next_run_at based on schedule type and value."""
    now = from_time or datetime.now()

    if schedule_type == "once":
        return ""  # One-shot, no next run after execution

    elif schedule_type == "interval":
        # Value like "30m", "2h", "1d"
        val = schedule_value.strip()
        if not val:
            return ""
        unit = val[-1].lower()
        try:
            num = int(val[:-1])
        except ValueError:
            return ""

        if unit == "m":
            delta = timedelta(minutes=num)
        elif unit == "h":
            delta = timedelta(hours=num)
        elif unit == "d":
            delta = timedelta(days=num)
        else:
            return ""
        return (now + delta).isoformat()

    elif schedule_type == "daily":
        # Value like "14:00" or "08:30"
        try:
            h, m = map(int, schedule_value.strip().split(":"))
            next_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if next_dt <= now:
                next_dt += timedelta(days=1)
            return next_dt.isoformat()
        except (ValueError, AttributeError):
            return ""

    elif schedule_type == "cron":
        # Simplified cron: just run every N hours for now
        return (now + timedelta(hours=1)).isoformat()

    return ""


def calc_initial_next_run(schedule_type: str, schedule_value: str) -> str:
    """Calculate the first next_run_at when creating a schedule."""
    now = datetime.now()

    if schedule_type == "once":
        return schedule_value

    elif schedule_type == "interval":
        return _calc_next_run("interval", schedule_value, now)

    elif schedule_type == "daily":
        return _calc_next_run("daily", schedule_value, now)

    elif schedule_type == "cron":
        return _calc_next_run("cron", schedule_value, now)

    return ""


async def execute_schedule(schedule: dict, ws_callback=None):
    """Execute a single schedule — run macro on target emulators."""
    import os

    macro_filename = schedule["macro_filename"]
    target_mode = schedule["target_mode"]
    target_indices_json = schedule.get("target_indices", "[]")

    try:
        target_indices = json.loads(target_indices_json) if target_indices_json else []
    except (json.JSONDecodeError, TypeError):
        target_indices = []

    # Resolve macro filepath
    ops_dir = ldplayer_manager._get_operations_dir()
    filepath = os.path.join(ops_dir, macro_filename)
    if not os.path.exists(filepath):
        print(f"[Scheduler] Macro file not found: {filepath}")
        return

    # Determine which emulators to run on
    all_emus = emulator_manager.get_all()

    if target_mode == "all_online":
        targets = [e for e in all_emus if e.get("status") == "ONLINE"]
    elif target_mode == "specific":
        targets = [e for e in all_emus if e.get("index") in target_indices]
    else:
        targets = [e for e in all_emus if e.get("status") == "ONLINE"]

    if not targets:
        print(f"[Scheduler] No targets available for schedule '{schedule['name']}'")
        return

    print(f"[Scheduler] Executing '{schedule['name']}' → {macro_filename} on {len(targets)} emulator(s)")

    for emu in targets:
        try:
            macro_replay.start_replay(
                emu["index"], filepath, macro_filename,
                ws_callback=ws_callback,
            )
        except Exception as e:
            print(f"[Scheduler] Error running macro on emu {emu['index']}: {e}")

    # Calculate next run
    next_run = _calc_next_run(schedule["schedule_type"], schedule["schedule_value"])

    # If one-shot, disable after execution
    if schedule["schedule_type"] == "once":
        await database.update_schedule(schedule["id"], is_enabled=0)

    await database.record_schedule_run(schedule["id"], next_run_at=next_run)


async def _check_schedules():
    """Check all enabled schedules and execute due ones."""
    schedules = await database.get_all_schedules()
    now = datetime.now()

    for sched in schedules:
        if not sched.get("is_enabled"):
            continue

        next_run_str = sched.get("next_run_at", "")
        if not next_run_str:
            continue

        try:
            next_run = datetime.fromisoformat(next_run_str)
        except (ValueError, TypeError):
            continue

        if now >= next_run:
            try:
                await execute_schedule(sched)
            except Exception as e:
                print(f"[Scheduler] Error executing schedule {sched['id']}: {e}")


def _scheduler_loop(stop_event: threading.Event):
    """Background thread loop that checks schedules every 30s."""
    print("[Scheduler] Background scheduler started (30s interval)")
    while not stop_event.is_set():
        try:
            asyncio.run(_check_schedules())
        except Exception as e:
            print(f"[Scheduler] Loop error: {e}")
        stop_event.wait(30)
    print("[Scheduler] Background scheduler stopped")


# Module-level control
_stop_event = threading.Event()
_thread = None


def start_scheduler():
    """Start the background scheduler thread."""
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop_event.clear()
    _thread = threading.Thread(target=_scheduler_loop, args=(_stop_event,), daemon=True)
    _thread.start()


def stop_scheduler():
    """Stop the background scheduler thread."""
    _stop_event.set()
    if _thread:
        _thread.join(timeout=5)
