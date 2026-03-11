"""
Smart Wait Logger — File-based diagnostics for queue evaluation.

Writes structured logs to `logs/smart_queue/` to track:
  - Account being evaluated
  - Current active account
  - Cooldown remaining vs threshold
  - The final decision: Wait or Skip
"""

import os
import json
from datetime import datetime

_LOG_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "logs", "smart_queue"
)

def _ensure_log_dir():
    os.makedirs(_LOG_DIR, exist_ok=True)

def log_smart_wait_eval(
    serial: str,
    target_account_id: str,
    active_account_id: str,
    remaining_cd_sec: float,
    threshold_sec: float,
    decision: str,
):
    """Log a Smart Wait evaluation event.
    
    Args:
        serial: Emulator serial (e.g. 'emulator-5556')
        target_account_id: The ID of the account currently being evaluated by the loop
        active_account_id: The ID of the account currently open on the emulator
        remaining_cd_sec: Remaining cooldown in seconds
        threshold_sec: The configured swap_wait_threshold in seconds
        decision: The final outcome (e.g. 'Waiting', 'Skipped (Not Active)', 'Skipped (Over Threshold)', 'Skipped (No Config)')
    """
    _ensure_log_dir()

    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(_LOG_DIR, f"smart_wait_{today}.jsonl")

    entry = {
        "ts": datetime.now().isoformat(),
        "serial": serial,
        "eval_target": target_account_id,
        "active_account": active_account_id,
        "cd_remaining_min": round(remaining_cd_sec / 60, 2),
        "threshold_min": round(threshold_sec / 60, 2),
        "decision": decision,
    }

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # Never crash 
