import os
from datetime import date, datetime, timedelta
from pathlib import Path


def _retention_cutoff(retention_days: int) -> date:
    keep_days = max(int(retention_days or 1), 1)
    return date.today() - timedelta(days=keep_days - 1)


def prune_daily_log_tree(base_dir: str | os.PathLike, retention_days: int = 7) -> None:
    """Delete dated .log files older than the retention window from serial subfolders."""
    root = Path(base_dir)
    if not root.exists():
        return

    cutoff = _retention_cutoff(retention_days)
    for serial_dir in root.iterdir():
        if not serial_dir.is_dir():
            continue

        for log_file in serial_dir.glob("*.log"):
            try:
                file_date = datetime.strptime(log_file.stem, "%Y-%m-%d").date()
            except ValueError:
                continue

            if file_date < cutoff:
                try:
                    log_file.unlink()
                except OSError:
                    continue

        try:
            if not any(serial_dir.iterdir()):
                serial_dir.rmdir()
        except OSError:
            pass


def prune_prefixed_daily_logs(
    log_dir: str | os.PathLike,
    prefix: str,
    retention_days: int = 7,
    suffix: str = ".jsonl",
) -> None:
    """Delete files like `<prefix>YYYY-MM-DD<suffix>` older than the retention window."""
    root = Path(log_dir)
    if not root.exists():
        return

    cutoff = _retention_cutoff(retention_days)
    for log_file in root.glob(f"{prefix}*{suffix}"):
        if not log_file.is_file():
            continue

        filename = log_file.name
        if not filename.startswith(prefix) or not filename.endswith(suffix):
            continue

        date_part = filename[len(prefix):-len(suffix)]
        try:
            file_date = datetime.strptime(date_part, "%Y-%m-%d").date()
        except ValueError:
            continue

        if file_date < cutoff:
            try:
                log_file.unlink()
            except OSError:
                continue
