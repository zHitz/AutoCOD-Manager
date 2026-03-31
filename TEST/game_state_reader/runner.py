"""Entry point for PET SANCTUARY hierarchy-based research runs."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from backend.core.workflow.state_detector import GameStateDetector
from backend.core.workflow import core_actions

try:
    from .config import ResearchConfig, load_app_config
    from .collector import HierarchyCollector
    from .parser import (
        ERROR_HIERARCHY_DUMP_FAILED,
        ERROR_NAV_TARGET_NOT_REACHED,
        ERROR_PET_SANCTUARY_NOT_CONFIRMED,
        ERROR_PET_TOKEN_NOT_FOUND,
        ERROR_UNSUPPORTED_RENDER_SURFACE,
        parse_hierarchy_file,
    )
    from .runtime_probe import RuntimeLogProbe
except ImportError:  # pragma: no cover - direct script execution fallback
    from config import ResearchConfig, load_app_config
    from collector import HierarchyCollector
    from parser import (
        ERROR_HIERARCHY_DUMP_FAILED,
        ERROR_NAV_TARGET_NOT_REACHED,
        ERROR_PET_SANCTUARY_NOT_CONFIRMED,
        ERROR_PET_TOKEN_NOT_FOUND,
        ERROR_UNSUPPORTED_RENDER_SURFACE,
        parse_hierarchy_file,
    )
    from runtime_probe import RuntimeLogProbe


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(_json_safe(payload), indent=2, ensure_ascii=True),
        encoding="utf-8",
    )


def _json_safe(value):
    """Recursively convert numpy/OpenCV scalars into plain Python JSON types."""
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item") and callable(value.item):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _append_log(log_path: Path, message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def _final_payload(
    *,
    ok: bool,
    error: str | None,
    screenshot_path: Path | None,
    xml_path: Path | None,
    parsed_path: Path | None,
    runtime_probe_path: Path | None = None,
    park_log_tail_path: Path | None = None,
    doc_listing_path: Path | None = None,
    pet_token: int | None = None,
    screen: str | None = None,
) -> dict:
    return {
        "ok": ok,
        "method": "uiautomator_dump",
        "screen": screen,
        "pet_token": pet_token,
        "evidence": {
            "xml_path": str(xml_path.resolve()) if xml_path and xml_path.exists() else None,
            "screenshot_path": (
                str(screenshot_path.resolve()) if screenshot_path and screenshot_path.exists() else None
            ),
            "parsed_path": str(parsed_path.resolve()) if parsed_path and parsed_path.exists() else None,
            "runtime_probe_path": (
                str(runtime_probe_path.resolve())
                if runtime_probe_path and runtime_probe_path.exists()
                else None
            ),
            "park_log_tail_path": (
                str(park_log_tail_path.resolve())
                if park_log_tail_path and park_log_tail_path.exists()
                else None
            ),
            "doc_listing_path": (
                str(doc_listing_path.resolve()) if doc_listing_path and doc_listing_path.exists() else None
            ),
        },
        "error": error,
    }


def _should_try_runtime_probe(parsed: dict) -> bool:
    if not parsed or parsed.get("ok"):
        return False
    if parsed.get("error") not in {
        ERROR_UNSUPPORTED_RENDER_SURFACE,
        ERROR_PET_SANCTUARY_NOT_CONFIRMED,
        ERROR_PET_TOKEN_NOT_FOUND,
    }:
        return False
    return True


def run_pet_sanctuary_reader(
    serial: str,
    *,
    output_dir: str | None = None,
    skip_navigation: bool = False,
    capture_screenshot: bool = False,
) -> dict:
    """Navigate to PET SANCTUARY, collect evidence, and parse hierarchy."""
    load_app_config()
    settings = ResearchConfig.from_app_config(serial=serial, output_dir=output_dir)
    run_dir = settings.create_run_dir()
    log_path = run_dir / "session.log"
    screenshot_path = run_dir / "screen.png"
    xml_path = run_dir / "window_dump.xml"
    parsed_path = run_dir / "parsed.json"
    result_path = run_dir / "result.json"
    runtime_probe_artifact_path = run_dir / "runtime_probe.json"
    park_log_tail_path = run_dir / "park_log_tail.txt"
    doc_listing_path = run_dir / "doc_listing.txt"

    _append_log(log_path, f"Starting PET SANCTUARY reader for {serial}")

    detector = GameStateDetector(
        adb_path=settings.adb_path,
        templates_dir=str(settings.templates_dir),
    )
    collector = HierarchyCollector(settings)
    runtime_probe = RuntimeLogProbe(settings)

    if not skip_navigation:
        _append_log(log_path, "Navigating to PET_SANCTUARY using existing workflow.")
        nav_result = core_actions.go_to_pet_sanctuary(serial, detector)
        if not nav_result.get("ok"):
            _append_log(log_path, f"Navigation failed: {nav_result.get('error')}")
            collector.capture_screenshot(screenshot_path)
            payload = _final_payload(
                ok=False,
                error=ERROR_NAV_TARGET_NOT_REACHED,
                screenshot_path=screenshot_path,
                xml_path=None,
                parsed_path=None,
                runtime_probe_path=None,
                park_log_tail_path=None,
                doc_listing_path=None,
            )
            _write_json(result_path, payload)
            return payload
    else:
        _append_log(log_path, "Skipping navigation as requested.")

    if capture_screenshot:
        _append_log(log_path, "Capturing screenshot evidence.")
        if not collector.capture_screenshot(screenshot_path):
            _append_log(log_path, "Screenshot capture failed; continuing with hierarchy dump.")
    else:
        _append_log(log_path, "Skipping screenshot capture because true-parameter mode does not read screenshots.")

    _append_log(log_path, "Running uiautomator dump.")
    dump_ok, dump_message = collector.dump_hierarchy(xml_path)
    if not dump_ok:
        _append_log(log_path, f"Hierarchy dump failed: {dump_message}")
        payload = _final_payload(
            ok=False,
            error=ERROR_HIERARCHY_DUMP_FAILED,
            screenshot_path=screenshot_path,
            xml_path=xml_path,
            parsed_path=None,
            runtime_probe_path=None,
            park_log_tail_path=None,
            doc_listing_path=None,
        )
        _write_json(result_path, payload)
        return payload

    _append_log(log_path, f"Hierarchy dump succeeded: {dump_message}")
    hierarchy_result = parse_hierarchy_file(xml_path)
    runtime_result = None

    _append_log(
        log_path,
        f"Hierarchy parser result: ok={hierarchy_result.get('ok')} error={hierarchy_result.get('error')}",
    )

    final_method = "uiautomator_dump"
    final_ok = bool(hierarchy_result.get("ok"))
    final_error = hierarchy_result.get("error")
    final_pet_token = hierarchy_result.get("pet_token")
    final_screen = hierarchy_result.get("screen")

    if _should_try_runtime_probe(hierarchy_result):
        _append_log(log_path, "Attempting runtime_log_probe for true-parameter sources.")
        runtime_result = runtime_probe.collect(run_dir)
        _write_json(runtime_probe_artifact_path, runtime_result)
        _append_log(
            log_path,
            f"Runtime probe result: ok={runtime_result.get('ok')} error={runtime_result.get('error')}",
        )
        final_method = runtime_result.get("method", "runtime_log_probe")
        final_screen = runtime_result.get("screen") or "PET_SANCTUARY"
        final_error = runtime_result.get("error")
        if runtime_result.get("ok"):
            final_ok = True
            final_error = None
            final_pet_token = runtime_result.get("pet_token")
        else:
            final_ok = False

    parsed_payload = {
        "hierarchy": hierarchy_result,
        "runtime_probe": runtime_result,
        "final": {
            "ok": final_ok,
            "method": final_method,
            "screen": final_screen,
            "pet_token": final_pet_token,
            "error": final_error,
        },
    }
    _write_json(parsed_path, parsed_payload)

    payload = _final_payload(
        ok=final_ok,
        error=final_error,
        screenshot_path=screenshot_path,
        xml_path=xml_path,
        parsed_path=parsed_path,
        runtime_probe_path=runtime_probe_artifact_path,
        park_log_tail_path=park_log_tail_path,
        doc_listing_path=doc_listing_path,
        pet_token=final_pet_token,
        screen=final_screen,
    )
    payload["method"] = final_method
    _write_json(result_path, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Research runner for PET SANCTUARY hierarchy-based state reading."
    )
    parser.add_argument("--serial", required=True, help="ADB serial, for example emulator-5556")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional artifact root directory. Defaults to TEST/game_state_reader/artifacts",
    )
    parser.add_argument(
        "--skip-navigation",
        action="store_true",
        help="Skip go_to_pet_sanctuary() and collect evidence from the current screen.",
    )
    parser.add_argument(
        "--capture-screenshot",
        action="store_true",
        help="Optionally capture a screenshot as evidence only. It is never used for reading pet_token.",
    )
    args = parser.parse_args()

    payload = run_pet_sanctuary_reader(
        args.serial,
        output_dir=args.output_dir,
        skip_navigation=args.skip_navigation,
        capture_screenshot=args.capture_screenshot,
    )
    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
