from __future__ import annotations

from datetime import datetime

from backend.storage.database import database


def build_rss_center_request_key(source_game_id: str = "", source_serial: str = "") -> str:
    """Build a per-source daily dedupe key for RSS Center rebuild requests."""
    source_token = (source_game_id or source_serial or "unknown").strip() or "unknown"
    return f"rss_center:{source_token}:{datetime.now().strftime('%Y%m%d')}"


async def persist_rss_center_rebuild_signal(
    *,
    account_id: int | None,
    game_id: str = "",
    group_id: int | None = None,
    emu_index: int | None = None,
    serial: str = "",
    activity_id: str,
    result: dict,
) -> dict | None:
    """Persist a rebuild-required signal emitted by the RSS Center farmer workflow."""
    if activity_id != "gather_rss_center":
        return None
    if not isinstance(result, dict):
        return None
    if result.get("rss_center_signal") != "rebuild_required":
        return None

    emulator_db_id = None
    if emu_index is not None:
        try:
            emulator_db_id = await database.get_emulator_id(emu_index=int(emu_index))
        except Exception:
            emulator_db_id = None

    request_key = build_rss_center_request_key(game_id, serial)
    request = await database.create_or_get_rss_center_rebuild_request(
        source_account_id=int(account_id) if account_id is not None else None,
        source_game_id=str(game_id or ""),
        source_group_id=int(group_id) if group_id is not None else None,
        source_emulator_id=int(emulator_db_id) if emulator_db_id is not None else None,
        source_serial=str(serial or ""),
        request_key=request_key,
        reason_code=str(result.get("rss_center_reason_code") or "RSS_CENTER_REBUILD_REQUIRED"),
        reason_message=str(result.get("error") or result.get("rss_center_reason_message") or ""),
        requested_resource_type=str(result.get("rss_center_requested_resource_type") or "random"),
        request_source="farmer_workflow",
        run_mode="signal",
    )
    return request
