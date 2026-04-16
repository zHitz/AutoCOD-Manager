"""
Optional LDPlayer window arrangement service for Windows.

This module is intentionally isolated from emulator launch logic so the
existing production flow remains unchanged unless the feature is enabled.
"""

from __future__ import annotations

import ctypes
import json
import os
import threading
import time
from ctypes import wintypes
from pathlib import Path

from backend.config import PROJECT_ROOT
from backend.core import ldplayer_manager


LAYOUT_SETTINGS_PATH = PROJECT_ROOT / "data" / "emulator_window_layout.json"

DEFAULT_SETTINGS = {
    "enabled": False,
    "mode": "fixed_per_instance",
    "window_width": 540,
    "window_height": 960,
    "start_x": 0,
    "start_y": 0,
    "horizontal_gap": 16,
    "vertical_gap": 16,
    "windows_per_row": 2,
    "remember_positions": False,
    "positions": {},
}

_LOCK = threading.Lock()


def _is_windows() -> bool:
    return os.name == "nt"


def _clone_default_settings() -> dict:
    return json.loads(json.dumps(DEFAULT_SETTINGS))


def _normalize_int(value, default: int, minimum: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if minimum is not None and parsed < minimum:
        parsed = minimum
    return parsed


def normalize_settings(payload: dict | None) -> dict:
    payload = payload or {}
    normalized = _clone_default_settings()
    normalized["enabled"] = bool(payload.get("enabled", normalized["enabled"]))
    normalized["mode"] = "fixed_per_instance"
    normalized["window_width"] = _normalize_int(
        payload.get("window_width"), normalized["window_width"], minimum=100
    )
    normalized["window_height"] = _normalize_int(
        payload.get("window_height"), normalized["window_height"], minimum=100
    )
    normalized["start_x"] = _normalize_int(payload.get("start_x"), normalized["start_x"])
    normalized["start_y"] = _normalize_int(payload.get("start_y"), normalized["start_y"])
    normalized["horizontal_gap"] = _normalize_int(
        payload.get("horizontal_gap"), normalized["horizontal_gap"]
    )
    normalized["vertical_gap"] = _normalize_int(
        payload.get("vertical_gap"), normalized["vertical_gap"]
    )
    normalized["windows_per_row"] = _normalize_int(
        payload.get("windows_per_row"), normalized["windows_per_row"], minimum=1
    )
    normalized["remember_positions"] = bool(
        payload.get("remember_positions", normalized["remember_positions"])
    )

    positions = payload.get("positions") or {}
    if not isinstance(positions, dict):
        positions = {}

    clean_positions: dict[str, dict] = {}
    for key, raw in positions.items():
        if not isinstance(raw, dict):
            continue
        idx = str(_normalize_int(key, -1))
        if idx == "-1":
            continue
        clean_positions[idx] = {
            "x": _normalize_int(raw.get("x"), 0),
            "y": _normalize_int(raw.get("y"), 0),
            "width": _normalize_int(raw.get("width"), normalized["window_width"], minimum=100),
            "height": _normalize_int(
                raw.get("height"), normalized["window_height"], minimum=100
            ),
        }
    normalized["positions"] = clean_positions
    return normalized


def load_settings() -> dict:
    with _LOCK:
        if not LAYOUT_SETTINGS_PATH.exists():
            return _clone_default_settings()
        try:
            data = json.loads(LAYOUT_SETTINGS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return _clone_default_settings()
        return normalize_settings(data)


def save_settings(payload: dict | None) -> dict:
    settings = normalize_settings(payload)
    with _LOCK:
        LAYOUT_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        LAYOUT_SETTINGS_PATH.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    return settings


def is_supported() -> bool:
    return _is_windows()


if _is_windows():
    user32 = ctypes.WinDLL("user32", use_last_error=True)

    SW_RESTORE = 9
    SWP_NOZORDER = 0x0004
    SWP_NOACTIVATE = 0x0010
    SWP_ASYNCWINDOWPOS = 0x4000

    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.IsWindow.argtypes = [wintypes.HWND]
    user32.IsWindow.restype = wintypes.BOOL
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsIconic.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL
    user32.SetWindowPos.argtypes = [
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL


def _get_window_text(hwnd: int) -> str:
    if not _is_windows():
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, len(buffer))
    return buffer.value.strip()


def _get_window_pid(hwnd: int) -> int | None:
    if not _is_windows():
        return None
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(pid.value) if pid.value else None


def _get_window_rect(hwnd: int) -> dict | None:
    if not _is_windows():
        return None
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    return {
        "x": int(rect.left),
        "y": int(rect.top),
        "width": int(rect.right - rect.left),
        "height": int(rect.bottom - rect.top),
    }


def _enumerate_windows() -> list[dict]:
    if not _is_windows():
        return []
    windows: list[dict] = []

    @EnumWindowsProc
    def callback(hwnd, _lparam):
        try:
            if not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd):
                return True
            title = _get_window_text(hwnd)
            if not title:
                return True
            rect = _get_window_rect(hwnd)
            if not rect or rect["width"] <= 0 or rect["height"] <= 0:
                return True
            windows.append(
                {
                    "hwnd": int(hwnd),
                    "title": title,
                    "pid": _get_window_pid(hwnd),
                    **rect,
                }
            )
        except Exception:
            return True
        return True

    user32.EnumWindows(callback, 0)
    return windows


def _parse_hwnd(value) -> int | None:
    try:
        hwnd = int(value)
    except (TypeError, ValueError):
        return None
    return hwnd if hwnd > 0 else None


def _get_instance_details(index: int) -> dict | None:
    for instance in ldplayer_manager.list_all_instances():
        if instance.get("index") == index:
            return instance
    return None


def _matches_window(candidate: dict, instance: dict) -> bool:
    title = (candidate.get("title") or "").lower()
    name = (instance.get("name") or "").lower()
    if name and name in title:
        return True

    idx = instance.get("index")
    pid_player = instance.get("pid_player")
    pid_vbox = instance.get("pid")
    candidate_pid = candidate.get("pid")
    if candidate_pid and pid_player and candidate_pid == pid_player:
        return True
    if candidate_pid and pid_vbox and candidate_pid == pid_vbox:
        return True
    if f"ldplayer" in title and idx is not None and str(idx) in title:
        return True
    return False


def _resolve_window_for_instance(index: int) -> dict | None:
    instance = _get_instance_details(index)
    if not instance:
        return None

    for handle_key in ("top_win", "bind_handle"):
        hwnd = _parse_hwnd(instance.get(handle_key))
        if hwnd and _is_windows() and user32.IsWindow(hwnd):
            rect = _get_window_rect(hwnd)
            if rect:
                return {"hwnd": hwnd, "title": _get_window_text(hwnd), **rect}

    matches = [w for w in _enumerate_windows() if _matches_window(w, instance)]
    if not matches:
        return None

    def score(item: dict) -> tuple[int, int, int]:
        title = (item.get("title") or "").lower()
        name = (instance.get("name") or "").lower()
        title_match = 1 if name and name in title else 0
        area = int(item.get("width", 0)) * int(item.get("height", 0))
        return (title_match, area, int(item.get("hwnd", 0)))

    matches.sort(key=score, reverse=True)
    return matches[0]


def _compute_target_bounds(index: int, settings: dict) -> dict:
    saved = (settings.get("positions") or {}).get(str(index))
    if settings.get("remember_positions") and isinstance(saved, dict):
        return {
            "x": _normalize_int(saved.get("x"), settings["start_x"]),
            "y": _normalize_int(saved.get("y"), settings["start_y"]),
            "width": _normalize_int(saved.get("width"), settings["window_width"], minimum=100),
            "height": _normalize_int(
                saved.get("height"), settings["window_height"], minimum=100
            ),
        }

    per_row = max(1, _normalize_int(settings.get("windows_per_row"), 2, minimum=1))
    row = index // per_row
    col = index % per_row
    return {
        "x": settings["start_x"] + col * (settings["window_width"] + settings["horizontal_gap"]),
        "y": settings["start_y"] + row * (settings["window_height"] + settings["vertical_gap"]),
        "width": settings["window_width"],
        "height": settings["window_height"],
    }


def _move_window(hwnd: int, bounds: dict) -> bool:
    if not _is_windows():
        return False
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    flags = SWP_NOZORDER | SWP_NOACTIVATE | SWP_ASYNCWINDOWPOS
    return bool(
        user32.SetWindowPos(
            hwnd,
            0,
            int(bounds["x"]),
            int(bounds["y"]),
            int(bounds["width"]),
            int(bounds["height"]),
            flags,
        )
    )


def get_settings_payload() -> dict:
    settings = load_settings()
    return {
        "supported": is_supported(),
        "settings": settings,
    }


def apply_layout(indices: list[int] | None = None, settings: dict | None = None) -> dict:
    effective_settings = normalize_settings(settings or load_settings())
    if not is_supported():
        return {
            "success": True,
            "supported": False,
            "message": "Window arrangement is only supported on Windows.",
            "results": [],
        }

    instances = ldplayer_manager.list_all_instances()
    targets = [item["index"] for item in instances if item.get("running")]
    if indices:
        requested = {int(i) for i in indices}
        targets = [idx for idx in targets if idx in requested]

    results = []
    for index in sorted(targets):
        window_info = _resolve_window_for_instance(index)
        if not window_info:
            results.append(
                {
                    "index": index,
                    "success": False,
                    "reason": "window_not_found",
                }
            )
            continue
        bounds = _compute_target_bounds(index, effective_settings)
        moved = _move_window(window_info["hwnd"], bounds)
        results.append(
            {
                "index": index,
                "success": moved,
                "reason": "ok" if moved else "move_failed",
                "title": window_info.get("title", ""),
                "bounds": bounds,
            }
        )

    applied = sum(1 for item in results if item["success"])
    return {
        "success": True,
        "supported": True,
        "message": f"Applied layout to {applied}/{len(results)} running emulator window(s).",
        "results": results,
        "settings": effective_settings,
    }


def capture_positions(indices: list[int] | None = None) -> dict:
    settings = load_settings()
    if not is_supported():
        return {
            "success": True,
            "supported": False,
            "message": "Window arrangement is only supported on Windows.",
            "captured": [],
            "settings": settings,
        }

    instances = ldplayer_manager.list_all_instances()
    requested = {int(i) for i in indices} if indices else None
    captured = []
    positions = dict(settings.get("positions") or {})

    for instance in instances:
        index = instance.get("index")
        if not instance.get("running"):
            continue
        if requested is not None and index not in requested:
            continue
        window_info = _resolve_window_for_instance(index)
        if not window_info:
            continue
        rect = {
            "x": window_info["x"],
            "y": window_info["y"],
            "width": window_info["width"],
            "height": window_info["height"],
        }
        positions[str(index)] = rect
        captured.append({"index": index, **rect, "title": window_info.get("title", "")})

    settings["positions"] = positions
    saved = save_settings(settings)
    return {
        "success": True,
        "supported": True,
        "message": f"Captured {len(captured)} running emulator window position(s).",
        "captured": captured,
        "settings": saved,
    }


def arrange_after_launch(index: int, attempts: int = 20, delay_seconds: float = 1.0) -> None:
    settings = load_settings()
    if not settings.get("enabled") or not is_supported():
        return

    def worker():
        effective_settings = load_settings()
        for _ in range(max(1, attempts)):
            try:
                result = apply_layout(indices=[index], settings=effective_settings)
                matched = result.get("results") or []
                if matched and matched[0].get("success"):
                    return
            except Exception:
                pass
            time.sleep(delay_seconds)

    thread = threading.Thread(
        target=worker,
        name=f"window-arranger-{index}",
        daemon=True,
    )
    thread.start()
