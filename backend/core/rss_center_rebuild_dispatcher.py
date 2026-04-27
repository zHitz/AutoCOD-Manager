from __future__ import annotations

import asyncio
import threading

from backend.storage.database import database


_POLL_INTERVAL_SEC = 300
_stop_event = threading.Event()
_thread = None


async def run_rss_center_rebuild_dispatch_cycle(
    trigger_mode: str = "scheduled",
    limit: int = 20,
) -> dict:
    """Claim pending RSS center rebuild requests and assign a safe builder stub."""
    requests = await database.get_pending_rss_center_rebuild_requests(limit=limit)
    summary = {
        "trigger_mode": trigger_mode,
        "processed": 0,
        "claimed": 0,
        "failed_not_implemented": 0,
        "pending_no_builder": 0,
    }

    for request in requests:
        summary["processed"] += 1
        request_id = int(request["id"])
        builders = await database.get_rss_center_builder_candidates()
        if not builders:
            await database.note_rss_center_rebuild_request(
                request_id,
                result_message="No safe builder available",
                last_error="No safe builder available",
                run_mode=trigger_mode,
            )
            print(f"[RSSCenterDispatcher] Request {request_id}: no safe builder available.")
            summary["pending_no_builder"] += 1
            continue

        builder = builders[0]
        claimed = await database.claim_rss_center_rebuild_request(
            request_id=request_id,
            builder_account_id=int(builder["account_id"]),
            builder_game_id=str(builder["game_id"]),
        )
        if not claimed:
            print(f"[RSSCenterDispatcher] Request {request_id}: already claimed by another worker.")
            continue

        summary["claimed"] += 1
        await database.mark_builder_run(str(builder["game_id"]))
        await database.fail_rss_center_rebuild_request(
            request_id=request_id,
            error="Builder workflow not implemented yet",
            retryable=True,
            result_status="not_implemented",
            result_message="Builder workflow not implemented yet",
        )
        print(
            f"[RSSCenterDispatcher] Request {request_id}: claimed by builder {builder['game_id']} "
            f"and closed as not_implemented."
        )
        summary["failed_not_implemented"] += 1

    return summary


def _dispatcher_loop(stop_event: threading.Event):
    print("[RSSCenterDispatcher] Background dispatcher started (300s interval)")
    while not stop_event.is_set():
        try:
            asyncio.run(run_rss_center_rebuild_dispatch_cycle(trigger_mode="scheduled"))
        except Exception as exc:
            print(f"[RSSCenterDispatcher] Loop error: {exc}")
        stop_event.wait(_POLL_INTERVAL_SEC)
    print("[RSSCenterDispatcher] Background dispatcher stopped")


def start_rss_center_rebuild_dispatcher():
    """Start the background RSS center rebuild dispatcher thread."""
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop_event.clear()
    _thread = threading.Thread(target=_dispatcher_loop, args=(_stop_event,), daemon=True)
    _thread.start()


def stop_rss_center_rebuild_dispatcher():
    """Stop the background RSS center rebuild dispatcher thread."""
    _stop_event.set()
    if _thread:
        _thread.join(timeout=5)
