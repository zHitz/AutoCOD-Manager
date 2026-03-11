"""
OCR Swap Logger — File-based diagnostics for production monitoring.

Writes structured logs to `logs/ocr_swap/` to track:
  - Which candidates were tried (raw, sanitized)
  - What OCR actually read on screen
  - Whether match succeeded or failed
  - Which strategy won (exact / sanitized)

Purpose: Collect production data to evaluate if auto-sanitization
is sufficient, or if manual alias infrastructure is needed.
"""

import os
import time
import json
from datetime import datetime

# Log directory: relative to this file → backend/core/workflow/logs/ocr_swap/
_LOG_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "logs", "ocr_swap"
)


def _ensure_log_dir():
    os.makedirs(_LOG_DIR, exist_ok=True)


def log_ocr_swap_attempt(
    serial: str,
    raw_target: str,
    candidates: list,
    ocr_words: list,
    matched_strategy: str = None,
    matched_term: str = None,
):
    """Log a single OCR swap search attempt to daily log file.

    Args:
        serial: Emulator serial (e.g. 'emulator-5556')
        raw_target: Original lord_name from DB (may contain noise)
        candidates: List of search terms tried [raw, sanitized, ...]
        ocr_words: All words detected by OCR on screen
        matched_strategy: 'exact' | 'sanitized' | None (if failed)
        matched_term: The term that matched (if any)
    """
    _ensure_log_dir()

    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(_LOG_DIR, f"ocr_swap_{today}.jsonl")

    entry = {
        "ts": datetime.now().isoformat(),
        "serial": serial,
        "raw_target": raw_target,
        "candidates": candidates,
        "ocr_words": ocr_words[:40],
        "matched": matched_strategy is not None,
        "matched_strategy": matched_strategy,
        "matched_term": matched_term,
    }

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # Never crash the bot for logging
