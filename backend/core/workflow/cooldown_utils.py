from __future__ import annotations

from datetime import datetime, timedelta, timezone


def next_utc_daily_reset_after(last_run_epoch: float) -> float:
    """Return the next 00:00 UTC reset timestamp after a run."""
    if last_run_epoch <= 0:
        return 0

    last_run_dt = datetime.fromtimestamp(last_run_epoch, tz=timezone.utc)
    next_reset_dt = datetime.combine(
        last_run_dt.date() + timedelta(days=1),
        datetime.min.time(),
        tzinfo=timezone.utc,
    )
    return next_reset_dt.timestamp()


def apply_daily_reset_cap(
    *,
    last_run_epoch: float,
    effective_cooldown_sec: float,
    now_epoch: float,
    reset_at_utc_midnight: bool,
) -> int:
    """Return remaining cooldown seconds after applying the optional UTC reset cap.

    Normal cooldown remains the primary mechanism. When reset_at_utc_midnight is
    enabled, the next 00:00 UTC after the last run acts as an upper bound, so the
    cooldown is forced to 0 once that daily reset is reached.
    """
    if last_run_epoch <= 0 or effective_cooldown_sec <= 0:
        return 0

    remaining = max(0, int(effective_cooldown_sec - (now_epoch - last_run_epoch)))
    if remaining <= 0:
        return 0

    if not reset_at_utc_midnight:
        return remaining

    next_reset_epoch = next_utc_daily_reset_after(last_run_epoch)
    if next_reset_epoch <= 0:
        return remaining

    reset_remaining = max(0, int(next_reset_epoch - now_epoch))
    return min(remaining, reset_remaining)
