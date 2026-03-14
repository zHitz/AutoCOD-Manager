"""
KPI Calculator — Computes real-time KPI metrics for workflow bot monitoring.

Metrics:
  1. Fairness Index: 1 - (σ/μ) of runs_today per account
  2. Activity Success Rate: SUCCESS / (SUCCESS + FAILED) × 100
  3. Ping-pong Swap Count: A→B→A patterns within 10 min on same emu
  4. Execute Time %: total_execution_ms / total_runtime_ms × 100
  5. Cycle / Coverage: done_accounts / total_accounts from live state
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import aiosqlite

from backend.config import config


_SWAP_LOG_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "logs", "swap_account"
)


async def compute_kpi_summary(group_id: int, orchestrator_status: Optional[dict] = None) -> Dict[str, Any]:
    """Compute all KPI metrics for a group on today's data.

    Args:
        group_id: Target group ID
        orchestrator_status: Live orchestrator state dict (from get_orchestrator_status)

    Returns:
        Dict with all KPI fields
    """
    today = datetime.now().strftime("%Y-%m-%d")

    fairness = await _calc_fairness_index(group_id, today)
    success_rate, total_runs, total_errors = await _calc_success_rate(group_id, today)
    ping_pong = _calc_ping_pong_count(today)
    exec_pct, total_exec_ms = await _calc_execute_time_pct(group_id, today, orchestrator_status)
    cycle, coverage_pct, done_count, total_count = _calc_coverage(orchestrator_status)

    return {
        "fairness_index": fairness,
        "success_rate": success_rate,
        "ping_pong_count": ping_pong,
        "execute_time_pct": exec_pct,
        "cycle": cycle,
        "coverage_pct": coverage_pct,
        "total_accounts": total_count,
        "done_accounts": done_count,
        "total_runs_today": total_runs,
        "total_errors_today": total_errors,
        "total_exec_ms": total_exec_ms,
    }


async def _calc_fairness_index(group_id: int, today: str) -> Optional[float]:
    """Fairness = 1 - (σ / μ) of runs per account today. 1.0 = perfect."""
    try:
        async with aiosqlite.connect(config.db_path) as db:
            cursor = await db.execute(
                """SELECT account_id, COUNT(*) as cnt
                   FROM account_activity_logs
                   WHERE group_id = ? AND status = 'SUCCESS'
                     AND started_at LIKE ?
                   GROUP BY account_id""",
                (group_id, f"{today}%"),
            )
            rows = await cursor.fetchall()

        if len(rows) < 2:
            return None  # Not enough data

        counts = [r[1] for r in rows]
        mean = sum(counts) / len(counts)
        if mean == 0:
            return None

        variance = sum((c - mean) ** 2 for c in counts) / len(counts)
        std_dev = variance ** 0.5
        fairness = round(1 - (std_dev / mean), 3)
        return max(0.0, min(1.0, fairness))

    except Exception as e:
        print(f"[KPI] Fairness calc error: {e}")
        return None


async def _calc_success_rate(group_id: int, today: str) -> tuple:
    """Returns (success_rate_pct, total_runs, total_errors)."""
    try:
        async with aiosqlite.connect(config.db_path) as db:
            cursor = await db.execute(
                """SELECT status, COUNT(*) as cnt
                   FROM account_activity_logs
                   WHERE group_id = ? AND started_at LIKE ?
                     AND status IN ('SUCCESS', 'FAILED')
                   GROUP BY status""",
                (group_id, f"{today}%"),
            )
            rows = await cursor.fetchall()

        status_counts = {r[0]: r[1] for r in rows}
        successes = status_counts.get("SUCCESS", 0)
        failures = status_counts.get("FAILED", 0)
        total = successes + failures

        if total == 0:
            return (None, 0, 0)

        rate = round((successes / total) * 100, 1)
        return (rate, total, failures)

    except Exception as e:
        print(f"[KPI] Success rate calc error: {e}")
        return (None, 0, 0)


def _calc_ping_pong_count(today: str) -> int:
    """Count A→B→A swap patterns within 10 min on same emulator from swap JSONL."""
    swap_file = os.path.join(_SWAP_LOG_DIR, f"swap_{today}.jsonl")
    if not os.path.exists(swap_file):
        return 0

    try:
        # Collect verified swap events per emulator
        # Look for ensure_correct_account phase="swap_loop_done" or phase="already_correct"
        emu_swaps: Dict[str, list] = {}  # emu_idx -> [(timestamp, final_account_id)]

        with open(swap_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                event = entry.get("event")

                # Track main_loop_swap_decision for account transitions
                if event == "main_loop_swap_decision":
                    emu_idx = str(entry.get("emu_idx", ""))
                    game_id = entry.get("expected_game_id", "")
                    ts_str = entry.get("ts", "")
                    decision = entry.get("decision", "")

                    # Only count actual swap decisions (not skips)
                    if decision in ("in_game_swap", "cross_emu_swap", "no_swap_needed", "skip_verified", "first_launch"):
                        if emu_idx not in emu_swaps:
                            emu_swaps[emu_idx] = []
                        emu_swaps[emu_idx].append((ts_str, game_id))

        # Detect A→B→A patterns within 10 minutes
        ping_pong = 0
        for emu_idx, swaps in emu_swaps.items():
            for i in range(len(swaps) - 2):
                ts_a, acc_a = swaps[i]
                ts_b, acc_b = swaps[i + 1]
                ts_c, acc_c = swaps[i + 2]

                if acc_a == acc_c and acc_a != acc_b:
                    # Check time window (10 min)
                    try:
                        t_a = datetime.fromisoformat(ts_a)
                        t_c = datetime.fromisoformat(ts_c)
                        if (t_c - t_a) <= timedelta(minutes=10):
                            ping_pong += 1
                    except (ValueError, TypeError):
                        pass

        return ping_pong

    except Exception as e:
        print(f"[KPI] Ping-pong calc error: {e}")
        return 0


async def _calc_execute_time_pct(
    group_id: int, today: str, orchestrator_status: Optional[dict]
) -> tuple:
    """Returns (execute_time_pct, total_execution_ms)."""
    try:
        async with aiosqlite.connect(config.db_path) as db:
            cursor = await db.execute(
                """SELECT SUM(duration_ms)
                   FROM account_activity_logs
                   WHERE group_id = ? AND started_at LIKE ?
                     AND status IN ('SUCCESS', 'FAILED')
                     AND duration_ms > 0""",
                (group_id, f"{today}%"),
            )
            row = await cursor.fetchone()

        total_exec_ms = row[0] if row and row[0] else 0

        # Get total runtime from orchestrator
        total_runtime_ms = 0
        if orchestrator_status and orchestrator_status.get("is_running"):
            # Estimate from run_start_time if available
            from backend.core.workflow.bot_orchestrator import _active_orchestrators
            import time

            orch = _active_orchestrators.get(group_id)
            if orch and hasattr(orch, "run_start_time"):
                elapsed_sec = time.time() - orch.run_start_time
                total_runtime_ms = int(elapsed_sec * 1000)

        if total_runtime_ms <= 0:
            # Fallback: estimate from first and last log entries today
            async with aiosqlite.connect(config.db_path) as db:
                cursor = await db.execute(
                    """SELECT MIN(started_at), MAX(finished_at)
                       FROM account_activity_logs
                       WHERE group_id = ? AND started_at LIKE ?
                         AND status IN ('SUCCESS', 'FAILED')""",
                    (group_id, f"{today}%"),
                )
                row = await cursor.fetchone()

            if row and row[0] and row[1]:
                try:
                    t_start = datetime.fromisoformat(row[0])
                    t_end = datetime.fromisoformat(row[1])
                    total_runtime_ms = int((t_end - t_start).total_seconds() * 1000)
                except (ValueError, TypeError):
                    pass

        if total_runtime_ms <= 0:
            return (None, total_exec_ms)

        pct = round((total_exec_ms / total_runtime_ms) * 100, 1)
        return (min(pct, 100.0), total_exec_ms)

    except Exception as e:
        print(f"[KPI] Execute time calc error: {e}")
        return (None, 0)


def _calc_coverage(orchestrator_status: Optional[dict]) -> tuple:
    """Returns (cycle, coverage_pct, done_count, total_count) from live state."""
    if not orchestrator_status:
        return (None, None, 0, 0)

    cycle = orchestrator_status.get("cycle", 0)
    accounts = orchestrator_status.get("accounts", [])
    total = len(accounts)

    if total == 0:
        return (cycle, None, 0, 0)

    done = sum(
        1 for a in accounts
        if a.get("status") in ("done", "completed", "success")
    )
    running = sum(1 for a in accounts if a.get("status") == "running")

    # Include running as partial progress
    coverage = round(((done + running * 0.5) / total) * 100, 1)

    return (cycle, coverage, done, total)
