import sys
import os
import time
import builtins

# Root directory (Part3_Control_EMU)
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)

# UI_MANAGER directory for config
ui_manager_dir = os.path.abspath(os.path.join(root_dir, "..", "UI_MANAGER"))
sys.path.append(ui_manager_dir)

from backend.config import config
from backend.core.workflow import adb_helper
from workflow import clipper_helper
from workflow.state_detector import GameStateDetector
from workflow.account_detector import AccountDetector
from workflow.construction_data import CONSTRUCTION_TAPS, CONSTRUCTION_DATA

import numpy as np
import cv2
import random
from workflow.ocr_helper import parse_game_timer, parse_builder_count, ocr_region_text, ocr_region_with_retry
from workflow.trash_detector import detect_with_voting as _trash_detect_with_voting

# ── Package Name Resolver ─────────────────────────────────
# Maps account provider to Android package name.
# Single source of truth — all other files import from here.
PROVIDER_PACKAGES = {
    "Funtap": "com.farlightgames.samo.gp.vn",
    "Global": "com.farlightgames.samo.gp",
}
DEFAULT_PROVIDER = "Funtap"  # backward compatible default


def get_package_for_provider(provider: str = None) -> str:
    """Resolve Android package name from account provider string."""
    if not provider:
        provider = DEFAULT_PROVIDER
    return PROVIDER_PACKAGES.get(provider, PROVIDER_PACKAGES[DEFAULT_PROVIDER])


# Reverse map: package → provider
PACKAGE_PROVIDERS = {pkg: prov for prov, pkg in PROVIDER_PACKAGES.items()}


def detect_provider_from_emulator(serial: str, adb_path: str = None) -> str:
    """Auto-detect provider by checking which game package is on the emulator.
    Checks running foreground app first, then falls back to installed packages.
    Returns provider string ('Global' or 'Funtap'), defaults to DEFAULT_PROVIDER.
    """
    if adb_path is None:
        adb_path = config.adb_path
    import subprocess
    # 1. Check foreground app
    try:
        out = subprocess.check_output(
            [adb_path, "-s", serial, "shell", "dumpsys", "activity", "recents"],
            timeout=5, text=True, stderr=subprocess.DEVNULL,
        )
        for pkg, prov in PACKAGE_PROVIDERS.items():
            if pkg in out:
                return prov
    except Exception:
        pass
    # 2. Fallback: check installed packages
    try:
        out = subprocess.check_output(
            [adb_path, "-s", serial, "shell", "pm", "list", "packages"],
            timeout=5, text=True, stderr=subprocess.DEVNULL,
        )
        # Check longest package first (most specific): .gp.vn before .gp
        # to prevent substring false-match (.gp is a substring of .gp.vn)
        for pkg in sorted(PACKAGE_PROVIDERS.keys(), key=len, reverse=True):
            if f"package:{pkg}" in out:
                return PACKAGE_PROVIDERS[pkg]
    except Exception:
        pass
    return DEFAULT_PROVIDER


# Global cache to store the last screenshot hash/image for freeze detection
_FREEZE_CACHE = {}
_APP_HEALTH_CACHE = {}

import threading
from datetime import datetime
from backend.core.workflow.log_retention import prune_daily_log_tree

_KNOWN_LOG_LEVELS = {
    "ERROR",
    "WARNING",
    "FAILED",
    "TIMEOUT",
    "FATAL",
    "CRASH DETECTED",
}

_LOG_FILE_LOCK = threading.Lock()
_WORKFLOW_LOG_RETENTION_DAYS = 7


def _resolve_workflow_log_path(serial: str) -> str:
    """Build a daily workflow log file path scoped by emulator/account serial."""
    base_dir = os.path.join(os.path.dirname(config.db_path), "workflow_logs")
    prune_daily_log_tree(base_dir, retention_days=_WORKFLOW_LOG_RETENTION_DAYS)
    safe_serial = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in (serial or "GENERAL"))
    dated_name = f"{datetime.now().strftime('%Y-%m-%d')}.log"
    log_dir = os.path.join(base_dir, safe_serial)
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, dated_name)


def _append_workflow_log(line: str) -> None:
    """Best-effort file append for workflow logs. Must never break workflow execution."""
    try:
        serial = "GENERAL"
        parts = line.split("] [", 2)
        if len(parts) >= 2:
            serial = parts[1].rstrip("]").strip() or "GENERAL"

        log_path = _resolve_workflow_log_path(serial)
        with _LOG_FILE_LOCK:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception:
        # Logging to file must never interfere with the actual workflow.
        pass


def _format_output_message(message: str) -> str:
    raw_message = str(message)
    content = raw_message.lstrip("\n").strip()
    if not content:
        return f"[{time.strftime('%H:%M:%S')}] [GENERAL] [INFO]"

    serial = "GENERAL"
    if content.startswith("[") and "]" in content:
        first_end = content.find("]")
        serial = content[1:first_end].strip() or "GENERAL"
        content = content[first_end + 1 :].strip()

    level = "INFO"
    if content.startswith("[") and "]" in content:
        second_end = content.find("]")
        candidate_level = content[1:second_end].strip().upper()
        if candidate_level in _KNOWN_LOG_LEVELS:
            level = candidate_level
            content = content[second_end + 1 :].strip()

    if content.startswith("->"):
        content = content[2:].strip()

    content = " ".join(content.split())
    timestamp = time.strftime("%H:%M:%S")
    return f"[{timestamp}] [{serial}] [{level}] {content}"


def print(*args, sep=" ", end="\n", file=None, flush=False):
    message = sep.join(str(arg) for arg in args)
    formatted = _format_output_message(message)
    builtins.print(formatted, end=end, file=file, flush=flush)
    _append_workflow_log(formatted)


def _exit_with_log(serial: str, level: str, message: str):
    raise SystemExit(_format_output_message(f"[{serial}] [{level}] {message}"))


# ── Debug Context ───────────────────────────────────────────
# Detectors stored in module-level dict (shared across all threads).
# _debug_last_serial is a module-level fallback for asyncio.to_thread()
# worker threads where threading.local won't have the serial.

_debug_detectors = {}          # {serial: detector}
_debug_last_serial = ""        # process-wide fallback
_debug_thread_ctx = threading.local()


def _get_active_debug_serial() -> str:
    """Resolve debug serial from the current thread first, then fallback globally."""
    return getattr(_debug_thread_ctx, "serial", "") or _debug_last_serial

def _set_debug_context(serial: str, detector):
    """Called by executor at the start of each workflow execution."""
    global _debug_last_serial
    _debug_detectors[serial] = detector
    _debug_last_serial = serial
    _debug_thread_ctx.serial = serial


def _activate_debug_serial(serial: str):
    """Explicitly set serial for current thread (optional, for concurrency)."""
    global _debug_last_serial
    _debug_last_serial = serial
    _debug_thread_ctx.serial = serial


def _capture_debug_screenshot(error_code: str) -> str:
    """Capture screenshot at moment of failure. Returns saved file path or empty string."""
    serial = _get_active_debug_serial()
    detector = _debug_detectors.get(serial) if serial else None
    if not serial or not detector or not config.debug_screenshots:
        return ""

    try:
        frame = detector.screencap_memory(serial)
        if frame is None:
            return ""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        code_tag = error_code.split(":")[0].strip().replace(" ", "_")
        filename = f"{ts}_{code_tag}.jpg"

        from pathlib import Path
        save_dir = str(Path(config.db_path).parent / "debug_captures" / serial)
        os.makedirs(save_dir, exist_ok=True)
        path = os.path.join(save_dir, filename)
        cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        return path
    except Exception:
        return ""


# ── Result Helpers ──────────────────────────────────────────
# Use these for standardized return values across all core_actions.
# See DOCS/WORKFLOWS/error_code_architecture.md for error code reference.

def _ok(**extra) -> dict:
    """Return success result. Optionally pass dynamic_cooldown_sec."""
    return {"ok": True, **extra}


def _fail(error: str, **extra) -> dict:
    """Return failure result with error code + message.
    Auto-captures debug screenshot when config.debug_screenshots is True.
    """
    screenshot_path = _capture_debug_screenshot(error)
    result = {"ok": False, "error": error, **extra}
    if screenshot_path:
        result["debug_screenshot"] = screenshot_path
    return result


def _is_ok(result) -> bool:
    """Check if a core_action result (bool or dict) is successful.
    
    Safely handles both old-style bool and new-style dict returns:
        if not _is_ok(back_to_lobby(serial, detector)):
            return _fail("NAV_LOBBY_UNREACHABLE: ...")
    """
    if isinstance(result, dict):
        return bool(result.get("ok", False))
    return bool(result)


def _bubble(result, fallback_error: str = "UNKNOWN: Child function failed") -> dict:
    """Bubble up a child function's error. Preserves error + dynamic_cooldown_sec.
    
    Usage:
        result = back_to_lobby(serial, detector)
        if not _is_ok(result):
            return _bubble(result, "NAV_LOBBY_UNREACHABLE: Could not reach lobby")
    """
    if isinstance(result, dict):
        return result  # already a dict with error info → pass through
    return {"ok": False, "error": fallback_error}

def ensure_app_running(serial: str, package_name: str, adb_path: str = config.adb_path):
    """Checks if the app is active, and boots it if it's not.
    Returns True if already running, False if just launched, None if launch failed."""
    if not clipper_helper.is_app_foreground(adb_path, serial, package_name):
        launched = clipper_helper.open_app(adb_path, serial, package_name)
        if not launched:
            print(f"[{serial}] [ERROR] open_app failed. App did not launch.")
            return None
        _FREEZE_CACHE.pop(serial, None)
        _APP_HEALTH_CACHE.pop(serial, None)
        _human_delay(10)
        return False
    return True

def _parse_pid_output(raw: str) -> list[str]:
    return [part for part in str(raw or "").split() if part.isdigit()]


def _is_package_foreground(serial: str, package_name: str) -> bool:
    activity_out = adb_helper._run_adb(["shell", "dumpsys", "activity", "activities"], serial=serial) or ""
    for line in activity_out.splitlines():
        if any(marker in line for marker in ("topResumedActivity", "mResumedActivity", "ResumedActivity")):
            if package_name in line:
                return True

    window_out = adb_helper._run_adb(["shell", "dumpsys", "window", "windows"], serial=serial) or ""
    for line in window_out.splitlines():
        if any(marker in line for marker in ("mCurrentFocus", "mFocusedApp")):
            if package_name in line:
                return True

    return False


def _log_capture_failure_diagnostics(serial: str, package_name: str = "", source: str = "capture") -> None:
    """Emit compact diagnostics when screencap/ERROR_CAPTURE happens repeatedly."""
    try:
        get_state = adb_helper._run_adb(["get-state"], serial=serial, timeout=5) or ""
        pid_raw = adb_helper._run_adb(["shell", "pidof", package_name], serial=serial, timeout=5) if package_name else ""
        pids = _parse_pid_output(pid_raw)
        is_foreground = _is_package_foreground(serial, package_name) if package_name else False

        current_focus = adb_helper._run_adb(
            ["shell", "dumpsys", "window", "windows"], serial=serial, timeout=5
        ) or ""
        focus_line = ""
        for line in current_focus.splitlines():
            if any(marker in line for marker in ("mCurrentFocus", "mFocusedApp")):
                focus_line = " ".join(line.strip().split())
                break

        print(
            f"[{serial}] [CAPTURE_DIAG] source={source} adb_state='{get_state.strip() or 'EMPTY'}' "
            f"pid_count={len(pids)} foreground={is_foreground}"
        )
        if package_name:
            print(
                f"[{serial}] [CAPTURE_DIAG] package='{package_name}' pid_raw='{(pid_raw or '').strip() or 'EMPTY'}'"
            )
        if focus_line:
            print(f"[{serial}] [CAPTURE_DIAG] focus={focus_line[:240]}")
    except Exception as e:
        print(f"[{serial}] [CAPTURE_DIAG] failed to collect diagnostics: {e}")


def check_app_crash(serial: str, package_name: str = "", adb_path: str = config.adb_path, current_state: str = "") -> bool:
    """
    Checks if the game has crashed, frozen, or been pushed to the background.
    Returns True if crashed/not in foreground/frozen, False if running normally.
    """
    try:
        health = _APP_HEALTH_CACHE.setdefault(serial, {
            "no_pid_count": 0,
            "not_foreground_count": 0,
            "capture_fail_count": 0,
        })
        loading_like_states = {"LOADING SCREEN", "LOADING SCREEN (NETWORK ISSUE)"}

        # 1. Check PID
        res = adb_helper._run_adb(["shell", "pidof", package_name], serial=serial)
        pids = _parse_pid_output(res)
        if not pids:
            health["no_pid_count"] += 1
        else:
            health["no_pid_count"] = 0

        if health["no_pid_count"] >= 2:
            print(f"[{serial}] [CRASH DETECTED] App {package_name} is not running (pidof empty on 2 consecutive checks).")
            return True
            
        # 2. Check if it's the foreground app
        is_foreground = _is_package_foreground(serial, package_name)
        if not is_foreground:
            health["not_foreground_count"] += 1
        else:
            health["not_foreground_count"] = 0
        health["is_foreground"] = is_foreground

        foreground_threshold = 3 if current_state in loading_like_states else 2
        if health["not_foreground_count"] >= foreground_threshold:
            print(f"[{serial}] [CRASH DETECTED] App {package_name} is not foreground on {foreground_threshold} consecutive checks.")
            return True
            
        # 3. Check for Engine Freeze (screen hasn't changed a single pixel)
        # We take a fast, low-res screencap (e.g. 1/4 size) to compare.
        import subprocess
        proc = subprocess.run([adb_path, "-s", serial, "exec-out", "screencap", "-p"], capture_output=True, timeout=5)
        if proc.returncode == 0 and len(proc.stdout) > 1000:
            health["capture_fail_count"] = 0
            img_data = np.frombuffer(proc.stdout, np.uint8)
            img = cv2.imdecode(img_data, cv2.IMREAD_GRAYSCALE)
            
            if img is not None:
                # Resize very small to ignore tiny compression artifacts and speed up
                small = cv2.resize(img, (160, 90))
                
                if serial not in _FREEZE_CACHE:
                    _FREEZE_CACHE[serial] = {"img": small, "freeze_count": 0}
                else:
                    prev_small = _FREEZE_CACHE[serial]["img"]
                    # Compare
                    diff = cv2.absdiff(small, prev_small)
                    if np.max(diff) == 0:
                        # 100% identical pixel for pixel
                        _FREEZE_CACHE[serial]["freeze_count"] += 1
                        freeze_threshold = 6 if current_state in loading_like_states else 4
                        if _FREEZE_CACHE[serial]["freeze_count"] >= freeze_threshold:
                            if health.get("is_foreground") and pids:
                                print(f"[{serial}] [CRASH DETECTED] HARD FREEZE while app is still foreground/alive (0 pixel change for {freeze_threshold} consecutive checks).")
                            else:
                                print(f"[{serial}] [CRASH DETECTED] Game engine is completely FROZEN (0 pixel change for {freeze_threshold} consecutive checks).")
                            return True
                    else:
                        # Screen changed, reset freeze counter
                        _FREEZE_CACHE[serial]["freeze_count"] = 0
                    
                    _FREEZE_CACHE[serial]["img"] = small
        else:
            health["capture_fail_count"] += 1
            if health["capture_fail_count"] >= 3:
                print(f"[{serial}] [CRASH DETECTED] Repeated screencap failure ({health['capture_fail_count']}x).")
                return True
                    
        return False
    except Exception as e:
        print(f"[{serial}] [WARNING] Error checking crash state: {e}")
        return False


def _get_crash_reason(serial: str) -> str:
    freeze = _FREEZE_CACHE.get(serial, {})
    health = _APP_HEALTH_CACHE.get(serial, {})

    if freeze.get("freeze_count", 0) > 0 and health.get("is_foreground"):
        return "CRASH_HARD_FREEZE_FOREGROUND"
    if health.get("capture_fail_count", 0) >= 3:
        return "CRASH_SCREENCAP_FAILURE"
    if health.get("not_foreground_count", 0) >= 2:
        return "CRASH_NOT_FOREGROUND"
    if health.get("no_pid_count", 0) >= 2:
        return "CRASH_NO_PID"
    return "CRASH_APP_UNRESPONSIVE"


def _recover_game_from_crash(
    serial: str,
    detector: GameStateDetector,
    package_name: str,
    target_lobby: str = None,
    load_timeout: int = 180,
) -> dict:
    """Force-stop and relaunch the game after a verified crash/freeze."""
    LOBBY_STATES = ["IN-GAME LOBBY (IN_CITY)", "IN-GAME LOBBY (OUT_CITY)"]

    print(f"[{serial}] [WARNING] Crash confirmed. Force-stopping {package_name} before recovery...")
    adb_helper._run_adb(["shell", "am", "force-stop", package_name], serial=serial)
    _FREEZE_CACHE.pop(serial, None)
    _APP_HEALTH_CACHE.pop(serial, None)
    _human_delay(2)

    print(f"[{serial}] [WARNING] Relaunching {package_name} after crash...")
    launched = clipper_helper.open_app(config.adb_path, serial, package_name)
    if not launched:
        return _fail("CRASH_RECOVERY_LAUNCH_FAILED: Could not relaunch app after crash")

    lobby = wait_for_state(
        serial,
        detector,
        LOBBY_STATES,
        timeout_sec=load_timeout,
        package_name=package_name,
    )
    if not lobby:
        return _fail(f"CRASH_RECOVERY_TIMEOUT: Game did not return to Lobby after {load_timeout}s")

    if target_lobby and lobby != target_lobby:
        print(f"[{serial}] -> Recovery reached {lobby}. Swapping to {target_lobby}...")
        adb_helper.tap(serial, 50, 500)
        swapped = wait_for_state(
            serial,
            detector,
            [target_lobby],
            timeout_sec=10,
            package_name=package_name,
        )
        if not swapped:
            return _fail(f"CRASH_RECOVERY_SWAP_FAILED: Could not swap to {target_lobby} after recovery")

    print(f"[{serial}] [INFO] Crash recovery successful. Lobby restored.")
    return _ok(recovered_from_crash=True)


def startup_to_lobby(serial: str, detector: GameStateDetector, package_name: str, adb_path: str = config.adb_path, load_timeout: int = 180) -> dict:
    """
    All-in-one startup: Boot game nếu chưa chạy -> chờ load vào Lobby.
    Nếu game đang chạy rồi -> dùng back_to_lobby() để mò về Lobby từ bất kỳ state nào.
    Returns dict: _ok() on success, _fail() on failure.
    """
    LOBBY_STATES = ["IN-GAME LOBBY (IN_CITY)", "IN-GAME LOBBY (OUT_CITY)"]
    
    was_running = ensure_app_running(serial, package_name, adb_path)
    
    if was_running is None:
        print(f"[{serial}] [FAILED] Could not launch app at all.")
        return _fail("CRASH_LAUNCH_FAILED: Could not launch app")
    
    if not was_running:
        print(f"[{serial}] App was not in foreground. Checking current state before waiting for Lobby...")
        current_state = detector.check_state(serial)
        print(f"[{serial}] Startup state after foreground check: {current_state}")

        if current_state == "ERROR_CAPTURE":
            if not adb_helper.ping_device(serial):
                print(f"[{serial}] [FAILED] Device is no longer reachable via ADB. Failing fast instead of waiting for Lobby.")
                return _fail("CRASH_DEVICE_OFFLINE: Device not reachable via ADB during startup")

            print(f"[{serial}] [WARNING] Screencap failed during startup, but device is still reachable. Checking for crash recovery...")
            if check_app_crash(serial, package_name, current_state=current_state):
                return _recover_game_from_crash(
                    serial,
                    detector,
                    package_name,
                    target_lobby=None,
                    load_timeout=load_timeout,
                )

            print(f"[{serial}] [FAILED] Screencap failed during startup and app did not qualify for crash recovery.")
            return _fail("ADB_CAPTURE_FAILED: Could not capture screen during startup")

        non_recoverable_states = {
            None,
            "UNKNOWN / TRANSITION",
            "LOADING SCREEN",
            "LOADING SCREEN (NETWORK ISSUE)",
        }

        if current_state in LOBBY_STATES:
            print(f"[{serial}] Already in Lobby after app foreground restore.")
            return _ok()

        if current_state not in non_recoverable_states:
            print(f"[{serial}] Known in-game state '{current_state}' detected. Recovering via back_to_lobby()...")
            result = back_to_lobby(serial, detector)
            return result if isinstance(result, dict) else (_ok() if result else _fail("NAV_LOBBY_UNREACHABLE: back_to_lobby failed after app foreground restore"))

        print(f"[{serial}] State is transitional/loading. Waiting for game to load into Lobby...")
        lobby = wait_for_state(serial, detector, LOBBY_STATES, timeout_sec=load_timeout, package_name=package_name)
        if not lobby:
            if check_app_crash(serial, package_name):
                print(f"[{serial}] [FAILED] Game crashed during startup or loading.")
                return _fail("CRASH_DURING_STARTUP: App crashed while waiting for Lobby")
            print(f"[{serial}] [FAILED] Game did not load into Lobby after {load_timeout}s.")
            return _fail(f"TIMEOUT_LOAD: Game did not load into Lobby after {load_timeout}s")
        return _ok()
    else:
        print(f"[{serial}] App is already running. Navigating back to Lobby...")
        result = back_to_lobby(serial, detector)
        return result if isinstance(result, dict) else (_ok() if result else _fail("NAV_LOBBY_UNREACHABLE: back_to_lobby failed"))

def wait_for_state(serial: str, detector: GameStateDetector, target_states: list, timeout_sec: int = 60, package_name: str = "", check_mode: str = "state") -> str:
    """Blocks and loops until the emulator reaches one of the target_states."""
    NETWORK_ISSUE_STATE = "LOADING SCREEN (NETWORK ISSUE)"
    NETWORK_CONFIRM_XY = (500, 325)

    start_time = time.time()
    print(f"[{serial}] Waiting for one of states: {target_states} (Timeout: {timeout_sec}s)")
    
    last_crash_check = time.time()
    network_dismiss_count = 0
    
    while True:
        if time.time() - start_time > timeout_sec:
            print(f"[{serial}] [TIMEOUT] Failed to reach target state within {timeout_sec}s.")
            return None
            
        if check_mode == "construction":
            current_state = detector.check_construction(serial)
        elif check_mode == "special":
            current_state = None
            for t in target_states:
                if detector.check_special_state(serial, target=t):
                    current_state = t
                    break
        elif check_mode == "activity":
            result = detector.check_activity(serial)
            current_state = result[0] if result else None
        elif check_mode == "account":
            result = detector.check_account_state(serial)
            current_state = result[0] if result else None
        else:
            current_state = detector.check_state(serial)
            
        print(f"[{serial}] Current detected state: {current_state}")

        # ── GLOBAL INTERRUPT: Network Issue popup ──────────────────────
        # "Connection lost due to Network instability" can appear at ANY
        # time during ANY workflow. It blocks the entire screen with only
        # a Confirm button (no back). Must dismiss before continuing.
        _is_network_issue = False
        if check_mode == "state" and current_state == NETWORK_ISSUE_STATE:
            _is_network_issue = True
        elif check_mode != "state" and current_state is None:
            # Non-state modes can't detect the popup directly.
            # Fallback: quick state check to see if popup is blocking.
            detector._cache.invalidate()
            fallback_state = detector.check_state(serial)
            if fallback_state == NETWORK_ISSUE_STATE:
                _is_network_issue = True

        if _is_network_issue:
            network_dismiss_count += 1
            print(f"[{serial}] -> Network Issue detected mid-workflow ({network_dismiss_count}x). Tapping Confirm {NETWORK_CONFIRM_XY}...")
            adb_helper.tap(serial, *NETWORK_CONFIRM_XY)
            _human_delay(3)
            detector._cache.invalidate()
            continue

        network_dismiss_count = 0
        
        if current_state in target_states:
            print(f"[{serial}] -> Target Reached '{current_state}'")
            return current_state
            
        if current_state == "ERROR_CAPTURE":
            print(f"[{serial}] -> ADB screencap failed. Checking whether app is truly crashed...")
            if time.time() - last_crash_check > 10:
                _log_capture_failure_diagnostics(serial, package_name, source="wait_for_state")
                last_crash_check = time.time()
            if package_name and check_app_crash(serial, package_name, current_state=current_state):
                return None
            _human_delay(1.5)
            continue

        if current_state == "LOADING SCREEN":
            print(f"[{serial}] -> Game is loading. Waiting 3 seconds...")
            _human_delay(3)
        elif current_state == "UNKNOWN / TRANSITION":
            # ── GLOBAL INTERRUPT: Popup blocking lobby ─────────────────
            # After loading, popups (events/ads) can appear over the lobby,
            # causing state to read as UNKNOWN. Check for X button to dismiss.
            popup_match = detector.check_special_state(serial, target="POPUP_X_BTN")
            if popup_match:
                print(f"[{serial}] -> Popup X button detected. Pressing BACK to dismiss...")
                adb_helper.press_back(serial)
                _human_delay(1.5)
                detector._cache.invalidate()
                continue
            else:
                # Check for crash every 10 seconds to avoid ADB spam
                if package_name and (time.time() - last_crash_check > 10):
                    if check_app_crash(serial, package_name, current_state=current_state):
                        return None
                    last_crash_check = time.time()
                _human_delay(0.5)
        else:
            # Check for crash every 10 seconds to avoid ADB spam
            if package_name and (time.time() - last_crash_check > 10):
                if check_app_crash(serial, package_name, current_state=current_state):
                    return None
                last_crash_check = time.time()
                
            _human_delay(0.5)

def go_to_profile(serial: str, detector: GameStateDetector) -> dict:
    """Navigates to the Profile menu."""
    if detector.check_state(serial) == "IN-GAME LOBBY (PROFILE MENU)":
        return _ok()
        
    print(f"[{serial}] Navigating to Profile...")
    adb_helper.tap(serial, 25, 25)
    
    state = wait_for_state(serial, detector, ["IN-GAME LOBBY (PROFILE MENU)"], timeout_sec=10)
    return _ok() if state else _fail("NAV_TARGET_NOT_REACHED: Could not reach Profile Menu")

def go_to_profile_details(serial: str, detector: GameStateDetector) -> dict:
    """Navigates to the Profile Details menu."""
    print(f"[{serial}] Navigating to Profile Details...")
    go_to_profile(serial, detector)
    _human_delay(3)
    adb_helper.tap(serial, 550, 200)
    
    state = wait_for_state(serial, detector, ["IN-GAME LOBBY (PROFILE MENU DETAIL)"], timeout_sec=10)
    return _ok() if state else _fail("NAV_TARGET_NOT_REACHED: Could not reach Profile Details")

def extract_player_id(serial: str, detector: GameStateDetector, adb_path: str = config.adb_path) -> str:
    """
    Assumes we are on the Profile Menu.
    Taps the copy button, intercepts the ADB Clipper intent, and returns the ID.
    """
    print(f"[{serial}] Tapping Copy ID Button...")
    last_clip = clipper_helper.get_clipper_data(adb_path, serial)
    
    max_retries = 3
    for attempt in range(max_retries):
        adb_helper.tap(serial, 425, 200)
        print(f"  -> Waiting 2 seconds for clipboard sync (Attempt {attempt+1}/{max_retries})...")
        _human_delay(2)
        
        current_clip = clipper_helper.get_clipper_data(adb_path, serial)
        
        # Valid ID heuristic: only digits, reasonably long
        if current_clip:
            clean_clip = current_clip.strip()
            if clean_clip.isdigit() and len(clean_clip) >= 5:
                # Success
                return clean_clip
            else:
                print(f"  -> [WARNING] Clipboard text is not a valid ID (got '{clean_clip[:20]}...'). Retrying...")
        else:
            print(f"  -> [WARNING] Empty clipboard data. Retrying...")
    
    return None

def back_to_lobby(serial: str, detector: GameStateDetector, timeout_sec: int = 30, target_lobby: str = None, debug: bool = False) -> dict:
    """
    Intelligently navigates back to the main Lobby from ANY state.
    Uses a time-based loop (timeout_sec) instead of attempt count.
    Single screencap per iteration via check_state_full() for speed.

    Handles:
      - BLACK SCREEN: Waits patiently (game booting, NEVER press back!).
      - LOADING SCREEN: Waits 10s (avoid breaking the load).
      - UNKNOWN / TRANSITION: 5s grace period, then press back.
      - Construction / Special screens: Press back immediately (no grace).
      - Known menu states: Press back, max 3 per same state before escalating.

    target_lobby: Optional. 'IN-GAME LOBBY (IN_CITY)' or 'IN-GAME LOBBY (OUT_CITY)'.
    Returns dict: _ok() on success, _fail() on failure.
    """
    import numpy as np
    BLACK_SCREEN_THRESHOLD = 15  # Mean brightness below this = black screen (game booting)
    NETWORK_ISSUE_STATE = "LOADING SCREEN (NETWORK ISSUE)"
    NETWORK_CONFIRM_XY = (500, 325)
    NETWORK_FALLBACK_THRESHOLD = 0.72
    LOBBY_STATES = ["IN-GAME LOBBY (IN_CITY)", "IN-GAME LOBBY (OUT_CITY)"]

    # Debug mode: save UNKNOWN screenshots for template creation
    debug_dir = None
    debug_count = 0
    if debug:
        import cv2 as _cv2
        debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "_unknown_captures")
        os.makedirs(debug_dir, exist_ok=True)
        print(f"[{serial}] [DEBUG] Saving UNKNOWN screenshots to: {debug_dir}")

    print(f"[{serial}] === BACK TO LOBBY ===")

    def _tap_back_ui_or_fallback(reason: str, frame=None) -> str:
        """Prefer the in-game back arrow; only use ADB BACK if still not in lobby."""
        back_arrow = detector._find_template(
            serial,
            detector.activity_templates,
            target="BACK_ARROW",
            threshold=0.75,
            use_color=True,
            frame=frame,
            _caller="back_to_lobby_back_arrow",
        )
        if back_arrow:
            _, bx, by = back_arrow
            print(f"[{serial}] -> {reason}: BACK_ARROW detected at ({bx}, {by}). Tapping UI back...")
            adb_helper.tap(serial, bx, by)
            _human_delay(1.5)
            return "ui_back"

        lobby_state = detector.check_state(serial)
        if lobby_state in LOBBY_STATES:
            print(f"[{serial}] -> {reason}: No BACK_ARROW, but already at lobby ({lobby_state}).")
            return "already_lobby"

        print(f"[{serial}] -> {reason}: No BACK_ARROW and not in lobby ({lobby_state}). Falling back to ADB BACK...")
        adb_helper.press_back(serial)
        _human_delay(1.5)
        return "adb_back"

    # 0. Ensure emulator is online and game is running
    detected_provider = detect_provider_from_emulator(serial)
    package_name = get_package_for_provider(detected_provider)
    was_running = ensure_app_running(serial, package_name, config.adb_path)
    if was_running is None:
        print(f"[{serial}] [FAILED] Could not launch app during back_to_lobby.")
        return _fail("CRASH_LAUNCH_FAILED: Could not launch app during back_to_lobby")
    if not was_running:
        print(f"[{serial}] [WARNING] Game was not running during back_to_lobby! Attempting to wait for lobby...")
        lobby_ok = wait_for_state(serial, detector, LOBBY_STATES, timeout_sec=120)
        if not lobby_ok:
            print(f"[{serial}] [FAILED] Game did not load into Lobby after booting.")
            return _fail("TIMEOUT_LOAD: Game did not load into Lobby after booting")
        current_state = detector.check_state(serial)
        if target_lobby and current_state != target_lobby:
            print(f"[{serial}] -> Swapping to {target_lobby}...")
            adb_helper.tap(serial, 50, 500)
            swapped = wait_for_state(serial, detector, [target_lobby], timeout_sec=10)
            if not swapped:
                print(f"[{serial}] [WARNING] Could not swap to {target_lobby}.")
                return _fail(f"NAV_SWAP_FAILED: Could not swap to {target_lobby}")
            print(f"[{serial}] -> Swapped to {target_lobby}.")
        return _ok()

    # --- Time-based main loop ---
    known_state_back_count = 0
    last_known_state = None
    unknown_start_time = None
    loading_screen_count = 0
    start_time = time.time()
    iteration = 0
    last_crash_check = time.time()

    while time.time() - start_time < timeout_sec:
        iteration += 1
        elapsed = time.time() - start_time

        # Single screencap: check state + construction + special in one pass
        result = detector.check_state_full(serial)
        current_state = result["state"]
        construction = result["construction"]
        special = result["special"]

        print(f"[{serial}] [{elapsed:.1f}s] State: {current_state}"
              + (f" | Construction: {construction}" if construction else "")
              + (f" | Special: {special}" if special else ""))

        # === SUCCESS: Already at Lobby ===
        if current_state in LOBBY_STATES:
            print(f"[{serial}] -> Lobby reached! ({current_state})")
            if target_lobby and current_state != target_lobby:
                print(f"[{serial}] -> Swapping to {target_lobby}...")
                adb_helper.tap(serial, 50, 500)
                swapped = wait_for_state(serial, detector, [target_lobby], timeout_sec=10)
                if not swapped:
                    print(f"[{serial}] [WARNING] Could not swap to {target_lobby}.")
                    return _fail(f"NAV_SWAP_FAILED: Could not swap to {target_lobby}")
                print(f"[{serial}] -> Swapped to {target_lobby}.")
            return _ok()

        if current_state == "ERROR_CAPTURE":
            print(f"[{serial}] -> Screencap failed inside back_to_lobby. Verifying crash state...")
            if time.time() - last_crash_check > 10:
                _log_capture_failure_diagnostics(serial, package_name, source="back_to_lobby")
                last_crash_check = time.time()
            if check_app_crash(serial, package_name, current_state=current_state):
                return _recover_game_from_crash(
                    serial,
                    detector,
                    package_name,
                    target_lobby=target_lobby,
                    load_timeout=180,
                )
            _human_delay(1.5)
            continue

        # === CASE 1: LOADING SCREEN — Wait patiently ===
        if current_state == "LOADING SCREEN":
            loading_screen_count += 1
            if loading_screen_count >= 3:
                print(f"[{serial}] -> Loading detected {loading_screen_count} times. Checking for Server Maintenance...")
                special_state = detector.check_special_state(serial, target="SERVER_MAINTENANCE")
                if special_state == "SERVER_MAINTENANCE":
                    print(f"[{serial}] [FATAL] Server Maintenance detected! Aborting script.")
                    _exit_with_log(serial, "FATAL", "Server Maintenance - Script Terminated")

            print(f"[{serial}] -> Loading detected. Waiting 10s...")
            unknown_start_time = None
            known_state_back_count = 0
            last_known_state = None
            _human_delay(10)
            continue

        loading_screen_count = 0

        # === CASE 2: NETWORK ISSUE — Tap confirm ===
        if current_state == NETWORK_ISSUE_STATE:
            print(f"[{serial}] -> Network issue detected. Tapping Confirm...")
            adb_helper.tap(serial, *NETWORK_CONFIRM_XY)
            _human_delay(2)
            continue

        # === CASE 3: Construction detected (via check_state_full) — Press BACK immediately ===
        if construction:
            print(f"[{serial}] -> Construction '{construction}' detected. Navigating back...")
            unknown_start_time = None
            _tap_back_ui_or_fallback(f"Construction '{construction}'", frame=result["screen"])
            continue

        # === CASE 4: Special screen detected — mostly BACK immediately ===
        if special:
            unknown_start_time = None

            if special == "NOTE":
                screen_before_back = result["screen"]
                network_note_icon = detector.locate_icon(serial, target="NETWORK_ISSUE_NOTE_ICON", threshold=0.8)
                if network_note_icon:
                    _, nix, niy = network_note_icon
                    print(
                        f"[{serial}] -> Special screen 'NOTE' matched NETWORK_ISSUE_NOTE_ICON "
                        f"at ({nix}, {niy}). Treating as network note. Tapping Confirm..."
                    )
                    adb_helper.tap(serial, *NETWORK_CONFIRM_XY)
                    _human_delay(2)
                else:
                    print(f"[{serial}] -> Special screen 'NOTE' detected without network icon. Navigating back...")
                    _tap_back_ui_or_fallback("Special 'NOTE'", frame=screen_before_back)
                continue

            print(f"[{serial}] -> Special screen '{special}' detected. Navigating back...")
            _tap_back_ui_or_fallback(f"Special '{special}'", frame=result["screen"])
            continue

        # === CASE 5: BLACK SCREEN — Game booting, NEVER press back! ===
        # Black screen appears before loading screen during game boot.
        # Pressing BACK here kills the app → ensure_app_running restarts it → infinite loop!
        screen = result["screen"]
        if current_state == "UNKNOWN / TRANSITION" and screen is not None:
            # Fallback: the network popup can sometimes miss the normal state pass
            # if the template confidence is slightly below the default threshold.
            network_fallback = detector._find_name_only(
                screen,
                detector.templates,
                target=NETWORK_ISSUE_STATE,
                threshold=NETWORK_FALLBACK_THRESHOLD,
                _caller="back_to_lobby_network_fallback",
            )
            if network_fallback == NETWORK_ISSUE_STATE:
                print(
                    f"[{serial}] -> Network issue recovered via UNKNOWN fallback "
                    f"(threshold={NETWORK_FALLBACK_THRESHOLD:.2f}). Tapping Confirm..."
                )
                unknown_start_time = None
                adb_helper.tap(serial, *NETWORK_CONFIRM_XY)
                _human_delay(2)
                continue

            mean_brightness = np.mean(screen)
            if mean_brightness < BLACK_SCREEN_THRESHOLD:
                print(f"[{serial}] -> BLACK SCREEN detected (brightness={mean_brightness:.1f}). Game booting. Waiting 5s...")
                unknown_start_time = None  # Reset grace — this is NOT a stuck unknown
                _human_delay(5)
                continue

        # === CASE 6: UNKNOWN / TRANSITION — Short grace period, then back ===
        if current_state == "UNKNOWN / TRANSITION":
            # Debug: save screenshot for template creation
            if debug and debug_dir and screen is not None:
                debug_count += 1
                ts = time.strftime("%H%M%S")
                fname = f"unknown_{ts}_{debug_count:03d}.png"
                _cv2.imwrite(os.path.join(debug_dir, fname), screen)
                print(f"[{serial}] [DEBUG] Saved: {fname}")

            if unknown_start_time is None:
                unknown_start_time = time.time()
                print(f"[{serial}] -> Unknown state. Starting 5s grace period...")
                _human_delay(1.5)
                continue

            # Crash/freeze detection must run aggressively in UNKNOWN state.
            # Rare engine-dead cases can stay foreground/alive but never leave
            # UNKNOWN, so waiting 10s before checking causes endless back loops.
            if check_app_crash(serial, package_name, current_state=current_state):
                print(f"[{serial}] [WARNING] {_get_crash_reason(serial)} detected while stuck in UNKNOWN state. Attempting crash recovery...")
                return _recover_game_from_crash(
                    serial,
                    detector,
                    package_name,
                    target_lobby=target_lobby,
                    load_timeout=180,
                )

            grace_elapsed = time.time() - unknown_start_time
            if grace_elapsed < 5:
                remaining = 5 - grace_elapsed
                print(f"[{serial}] -> Still unknown. Grace: {remaining:.0f}s left...")
                _human_delay(1.5)
                continue
            else:
                last_crash_check = time.time()
                print(f"[{serial}] -> Unknown for >5s. Trying UI back / fallback...")
                _tap_back_ui_or_fallback("UNKNOWN >5s", frame=screen)
                continue

        # === CASE 6: Known named state (Profile Menu, Bazaar, Events, etc.) ===
        unknown_start_time = None

        if current_state == last_known_state:
            known_state_back_count += 1
        else:
            last_known_state = current_state
            known_state_back_count = 1

        if known_state_back_count <= 3:
            if time.time() - last_crash_check > 10:
                if check_app_crash(serial, package_name, current_state=current_state):
                    print(f"[{serial}] [WARNING] {_get_crash_reason(serial)} detected while stuck in state '{current_state}'. Attempting crash recovery...")
                    return _recover_game_from_crash(
                        serial,
                        detector,
                        package_name,
                        target_lobby=target_lobby,
                        load_timeout=180,
                    )
                last_crash_check = time.time()
            print(f"[{serial}] -> Known state '{current_state}'. Trying UI back / fallback ({known_state_back_count}/3)...")
            _tap_back_ui_or_fallback(f"Known state '{current_state}'", frame=result["screen"])
        else:
            if time.time() - last_crash_check > 10:
                if check_app_crash(serial, package_name, current_state=current_state):
                    print(f"[{serial}] [WARNING] {_get_crash_reason(serial)} detected while stuck in state '{current_state}'. Attempting crash recovery...")
                    return _recover_game_from_crash(
                        serial,
                        detector,
                        package_name,
                        target_lobby=target_lobby,
                        load_timeout=180,
                    )
                last_crash_check = time.time()
            print(f"[{serial}] -> [WARNING] State '{current_state}' stuck after 3 backs. Extra wait 3s...")
            _human_delay(3)
            known_state_back_count = 0

    print(f"[{serial}] [FAILED] Could not reach Lobby within {timeout_sec}s.")
    return _fail(f"TIMEOUT_STATE_WAIT: Could not reach Lobby within {timeout_sec}s")

def ensure_lobby_menu_open(serial: str, detector: GameStateDetector, max_attempts: int = 5) -> dict:
    """
    Ensures the expandable lobby menu is open.
    Uses detector.is_menu_expanded() which is separate from check_state().
    If menu is closed and we're at Lobby, taps the expand button (925, 500).
    Returns dict: _ok() on success, _fail() on failure.
    """
    LOBBY_STATES = ["IN-GAME LOBBY (IN_CITY)", "IN-GAME LOBBY (OUT_CITY)"]
    
    for attempt in range(1, max_attempts + 1):
        if detector.is_menu_expanded(serial):
            print(f"[{serial}] -> Lobby menu is already open.")
            return _ok()
        
        current_state = detector.check_state(serial)
        print(f"[{serial}] [ensure_menu] Attempt {attempt}/{max_attempts} | State: {current_state} | Menu: closed")
        
        if current_state in LOBBY_STATES:
            print(f"[{serial}] -> Tapping expand button (925, 500)...")
            adb_helper.tap(serial, 925, 500)
            _human_delay(2)
            continue
        
        # Not in a lobby state at all
        print(f"[{serial}] -> [WARNING] Not in Lobby state ({current_state}). Cannot expand menu.")
        return _fail(f"STATE_WRONG_SCREEN: Not in Lobby ({current_state}), cannot expand menu")
    
    print(f"[{serial}] [FAILED] Could not confirm lobby menu open after {max_attempts} attempts.")
    return _fail(f"NAV_MENU_OPEN_FAILED: Could not open lobby menu after {max_attempts} attempts")

def go_to_resources(serial: str, detector: GameStateDetector) -> dict:
    """Navigates to the Resources menu from Lobby. Returns dict."""
    print(f"[{serial}] Navigating to Resources...")
    
    result = ensure_lobby_menu_open(serial, detector)
    if not _is_ok(result):
        print(f"[{serial}] [FAILED] Could not open lobby menu.")
        return _bubble(result, "NAV_MENU_OPEN_FAILED: Could not open lobby menu")
    # Tap (780, 500) with retry — could land on any IN-GAME ITEMS tab
    LOBBY_STATES = ["IN-GAME LOBBY (IN_CITY)", "IN-GAME LOBBY (OUT_CITY)"]
    ITEMS_STATES = ["IN-GAME ITEMS (ARTIFACTS)", "IN-GAME ITEMS (RESOURCES)"]
    
    items_reached = False
    for retry in range(1, 4):
        adb_helper.tap(serial, 780, 500)
        state = wait_for_state(serial, detector, ITEMS_STATES, timeout_sec=5)
        if state:
            items_reached = True
            break
        
        # Check what state we're in
        current = detector.check_state(serial)
        if current in LOBBY_STATES:
            # Tap didn't register, re-expand and retry
            print(f"[{serial}] -> Tap (780,500) missed. Retry {retry}/3 — re-expanding menu...")
            menu_result = ensure_lobby_menu_open(serial, detector)
            if not _is_ok(menu_result):
                return _bubble(menu_result, "NAV_MENU_OPEN_FAILED: Could not re-expand lobby menu")
            continue
        
        # Unknown state — likely some other IN-GAME ITEMS tab without a template
        # Tap (75, 180) directly to switch to Resources tab
        print(f"[{serial}] -> Unknown Items tab ({current}). Tapping (75, 180) to switch to Resources...")
        items_reached = True
        break
    
    if not items_reached:
        print(f"[{serial}] [FAILED] Could not enter Items menu after 3 retries.")
        return _fail("NAV_TARGET_NOT_REACHED: Could not enter Items menu after 3 retries")
    
    # If we landed on Resources directly, skip tapping (75, 180)
    if state != "IN-GAME ITEMS (RESOURCES)":
        adb_helper.tap(serial, 75, 180)
        state = wait_for_state(serial, detector, ["IN-GAME ITEMS (RESOURCES)"], timeout_sec=15)

        if not state:
            print(f"[{serial}] [FAILED] Could not reach Items - Resources state.")
            return _fail("NAV_TARGET_NOT_REACHED: Could not reach Items - Resources state")

    adb_helper.tap(serial, 620, 100)
    _human_delay(5)
    
    return _ok()

def go_to_construction(
    serial: str,
    detector: GameStateDetector,
    name: str,
    feature: str | None = None,
    post_base_tap_swipe: tuple[int, int, int, int, int] | None = None,
) -> dict:
    """
    Generic navigation to any construction building.

    Two modes:
      V1 (legacy): feature=None → tap sequence from CONSTRUCTION_TAPS (backward compat)
      V2 (new):    feature="upgrade" → tap base, then tap feature (fixed or template-based)

    Must navigate to IN-GAME LOBBY (IN_CITY) first.
    """
    name_upper = name.upper()

    # ── V2 path: feature-based navigation ──
    if feature is not None:
        return _go_to_construction_v2(
            serial,
            detector,
            name_upper,
            feature,
            post_base_tap_swipe=post_base_tap_swipe,
        )

    # ── V1 path: legacy tap sequence (backward compat) ──
    if name_upper not in CONSTRUCTION_TAPS:
        print(f"[{serial}] [FAILED] Unknown construction '{name}'. Not found in construction_data.")
        return _fail(f"CONFIG_INVALID_PARAM: Unknown construction '{name}'")

    print(f"[{serial}] === GO TO CONSTRUCTION: {name_upper} ===")

    result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not _is_ok(result):
        return _bubble(result, "NAV_LOBBY_UNREACHABLE: Could not reach IN_CITY")
    current_state = detector.check_state(serial)
    if current_state != "IN-GAME LOBBY (IN_CITY)":
        print(f"[{serial}] [FAILED] Must be IN_CITY. Current: {current_state}")
        return _fail(f"STATE_WRONG_SCREEN: Must be IN_CITY, current: {current_state}")

    # Execute tap sequence from data
    taps = CONSTRUCTION_TAPS[name_upper]
    for i, (x, y) in enumerate(taps):
        adb_helper.tap(serial, x, y)
        _human_delay(2)
    _human_delay(2)

    # Verify construction opened (retry up to 3 times)
    for attempt in range(3):
        detector._screen_cache = None
        result = detector.check_construction(serial, target=name_upper)
        if result:
            print(f"[{serial}] -> {name_upper} detected successfully.")
            return _ok()
        if attempt < 2:
            print(f"[{serial}] {name_upper} not detected, retrying ({attempt + 1}/3)...")
            _human_delay(1.5)

    # Retry: re-tap last coordinate
    last_x, last_y = taps[-1]
    print(f"[{serial}] [RETRY] {name_upper} not detected. Re-tapping ({last_x}, {last_y})...")
    adb_helper.tap(serial, last_x, last_y)
    _human_delay(2)

    for attempt in range(3):
        detector._screen_cache = None
        result = detector.check_construction(serial, target=name_upper)
        if result:
            print(f"[{serial}] -> {name_upper} detected on retry.")
            return _ok()
        if attempt < 2:
            print(f"[{serial}] {name_upper} still not detected, retrying ({attempt + 1}/3)...")
            _human_delay(1.5)

    print(f"[{serial}] [WARNING] Could not confirm {name_upper} opened after retry.")
    return _fail(f"NAV_TARGET_NOT_REACHED: Could not confirm {name_upper} opened")


def _go_to_construction_v2(
    serial: str,
    detector: GameStateDetector,
    name_upper: str,
    feature: str,
    post_base_tap_swipe: tuple[int, int, int, int, int] | None = None,
) -> dict:
    """
    V2 feature-based construction navigation. ALL features use template detection.

    Flow:
      1. Navigate to IN_CITY
      2. Tap base (building on city map) → wait popup
      3. Detect feature icon via template → tap detected position
         - If detect fails on attempt 0: re-tap base (overlay dismiss)
         - If detect fails on attempt 1: use fallback coords if configured
      4. Verify construction screen opened (up to 3 retries)
    """
    if name_upper not in CONSTRUCTION_DATA:
        print(f"[{serial}] [FAILED] Unknown construction '{name_upper}'. Not found in CONSTRUCTION_DATA.")
        return _fail(f"CONFIG_INVALID_PARAM: Unknown construction '{name_upper}' in V2 data")

    data = CONSTRUCTION_DATA[name_upper]
    feature_lower = feature.lower()

    if feature_lower not in data["features"]:
        available = list(data["features"].keys())
        print(f"[{serial}] [FAILED] Unknown feature '{feature}' for {name_upper}. Available: {available}")
        return _fail(f"CONFIG_INVALID_PARAM: Unknown feature '{feature}' for {name_upper}")

    print(f"[{serial}] === GO TO CONSTRUCTION V2: {name_upper} -> {feature_lower} ===")

    # ── Step 1: Navigate to IN_CITY ──
    result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not _is_ok(result):
        return _bubble(result, "NAV_LOBBY_UNREACHABLE: Could not reach IN_CITY")
    current_state = detector.check_state(serial)
    if current_state != "IN-GAME LOBBY (IN_CITY)":
        print(f"[{serial}] [FAILED] Must be IN_CITY. Current: {current_state}")
        return _fail(f"STATE_WRONG_SCREEN: Must be IN_CITY, current: {current_state}")

    # ── Steps 2-4: Tap base → Detect feature → Tap → Verify ──
    base_x, base_y = data["base"]
    feat_config = data["features"][feature_lower]
    feat_type = feat_config.get("type", "template")

    for base_attempt in range(2):
        if base_attempt > 0:
            print(f"[{serial}] [RETRY] Re-tapping base ({base_x}, {base_y}) — first tap may have dismissed overlay...")
        else:
            print(f"[{serial}] Tapping base building at ({base_x}, {base_y})...")
        adb_helper.tap(serial, base_x, base_y)
        _human_delay(1.2)
        if base_attempt == 0 and post_base_tap_swipe:
            sx1, sy1, sx2, sy2, duration_ms = post_base_tap_swipe
            print(
                f"[{serial}] Applying one-time post-base swipe "
                f"({sx1}, {sy1}) -> ({sx2}, {sy2}) for {name_upper}."
            )
            adb_helper.swipe(serial, sx1, sy1, sx2, sy2, duration_ms)
            _human_delay(1.0)

        # ── Step 3: Detect & tap feature button ──
        if feat_type == "template":
            template_name = feat_config["template"]
            print(f"[{serial}] Detecting feature '{feature_lower}' via template '{template_name}'...")

            # Fast path: single check (popup should be rendered after 1.2s)
            detector._screen_cache = None
            match = detector.check_activity(serial, target=template_name, threshold=0.75)

            # Slow path: retry if fast check missed (animation lag, overlay)
            if not match:
                _human_delay(0.8)
                match = _detect_with_retry(serial, detector, template_name, threshold=0.75, attempts=2, delay=0.8)

            if not match:
                if base_attempt == 0:
                    print(f"[{serial}] Feature '{template_name}' not found. Will re-tap base...")
                    continue
                # Attempt 1 failed: use fallback coords if configured
                fallback = feat_config.get("fallback")
                if fallback:
                    fx, fy = fallback["x"], fallback["y"]
                    print(f"[{serial}] [FALLBACK] Template failed. Using fallback coords ({fx}, {fy})...")
                    adb_helper.tap(serial, fx, fy)
                    _human_delay(1.0)
                else:
                    print(f"[{serial}] [FAILED] Feature button '{template_name}' not found after retry.")
                    adb_helper.press_back(serial)
                    return _fail(f"TEMPLATE_NO_MATCH: Feature button '{template_name}' not found for {name_upper}")
            else:
                _, mx, my = match
                print(f"[{serial}] Tapping feature '{feature_lower}' at detected ({mx}, {my})...")
                adb_helper.tap(serial, mx, my)
                _human_delay(0.8)

        elif feat_type == "fixed":
            # Legacy backward-compat — should not happen after migration
            fx, fy = feat_config["x"], feat_config["y"]
            print(f"[{serial}] [DEPRECATED] Tapping feature '{feature_lower}' at fixed ({fx}, {fy})...")
            adb_helper.tap(serial, fx, fy)
            _human_delay(1.2)

        else:
            print(f"[{serial}] [FAILED] Unknown feature type '{feat_type}' for {name_upper}.{feature_lower}")
            return _fail(f"CONFIG_INVALID_PARAM: Unknown feature type '{feat_type}'")

        # ── Step 4: Verify construction screen ──
        verify_name = feat_config.get("verify", data["verify"])
        print(f"[{serial}] Verifying screen with template '{verify_name}'...")
        for attempt in range(3):
            detector._screen_cache = None
            result = detector.check_construction(serial, target=verify_name)
            if result:
                print(f"[{serial}] -> {name_upper} (feature={feature_lower}) detected successfully.")
                return _ok()
            if attempt < 2:
                print(f"[{serial}] {verify_name} not detected, retrying ({attempt + 1}/3)...")
                _human_delay(1.0)

        # Verify failed — if first attempt, re-tap base
        if base_attempt == 0:
            print(f"[{serial}] Verify failed. Will re-tap base...")

    print(f"[{serial}] [WARNING] Could not confirm {name_upper} opened via feature '{feature_lower}'.")
    return _fail(f"NAV_TARGET_NOT_REACHED: Could not confirm {name_upper} via feature '{feature_lower}'")

def go_to_capture_pet(serial: str, detector: GameStateDetector) -> dict:
    """
    Go to Capture Pet Full Phase
    """
    dispatch_result = capture_pet(serial, detector, mode="dispatch")
    if not _is_ok(dispatch_result):
        return _bubble(dispatch_result, "CAPTURE_PET_DISPATCH_FAILED")
    dispatch_status = str((dispatch_result or {}).get("capture_status") or "")

    sanctuary_result = go_to_pet_sanctuary(serial, detector)
    if not _is_ok(sanctuary_result):
        return _bubble(sanctuary_result, "NAV_TARGET_NOT_REACHED: Could not reach Pet Sanctuary")

    clean_result = clean_trash_pet_sanctuary(serial, detector, duration=20, navigate=False)
    if not _is_ok(clean_result):
        return _bubble(clean_result, "CLEAN_TRASH_FAILED")

    release_result = release_pet(serial, detector)
    if not _is_ok(release_result):
        return _bubble(release_result, "RELEASE_PET_FAILED")

    if dispatch_status == "idle_no_warrants":
        print(f"[{serial}] Capture dispatch had no warrants. Skipping final check_only phase.")
        return _ok(capture_status="idle_no_warrants")

    check_result = capture_pet(serial, detector, mode="check_only")
    if not _is_ok(check_result):
        return _bubble(check_result, "CAPTURE_PET_CHECK_FAILED")
    return _ok()


def capture_pet(serial: str, detector: GameStateDetector, mode: str = "dispatch") -> dict:
    """
    Pet capture flow.

    Modes:
      - dispatch: start a real pet capture and return without waiting for completion
      - check_only: open the capture screen only to inspect current status
    """
    mode = str(mode or "dispatch").strip().lower()
    if mode not in {"dispatch", "check_only"}:
        return _fail(f"CONFIG_INVALID_PARAM: Unknown capture_pet mode '{mode}'")

    print(f"[{serial}] Navigating to Capture Pet...")
    
    lobby_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)")
    if not _is_ok(lobby_result):
        print(f"[{serial}] [FAILED] Could not reach OUT_CITY lobby.")
        return _bubble(lobby_result, "NAV_LOBBY_UNREACHABLE: Could not reach OUT_CITY")

    # 2. Open search menu and switch to Darkling category if needed
    category = _ensure_search_menu_category(serial, detector, "darkling")
    if category is None:
        return _fail("NAV_TARGET_NOT_REACHED: Could not open search menu")

    # 3. Select Catch Pet sub-tab under Darkling category
    print(f"[{serial}] Selecting BEASTS MENU (301, 215)...")
    adb_helper.tap(serial, 301, 215)
    _human_delay(2)

    # 4. Tap Auto Capture submenu
    print(f"[{serial}] Selecting Auto Capture (285, 400)...")
    adb_helper.tap(serial, 285, 400)
    _human_delay(2)

    # 5. Verify state AUTO_CAPTURE_PET / AUTO_CAPTURE_START
    print(f"[{serial}] Waiting for Capture window to open...")
    state = wait_for_state(serial, detector, ["AUTO_CAPTURE_PET", "AUTO_CAPTURE_START", "AUTO_CAPTURE_IN_PROGRESS"], timeout_sec=10, check_mode="special")
    
    if state not in ["AUTO_CAPTURE_PET", "AUTO_CAPTURE_START", "AUTO_CAPTURE_IN_PROGRESS"]:
        print(f"[{serial}] [FAILED] Did not reach Capture window.")
        return _fail("NAV_TARGET_NOT_REACHED: Did not reach Capture window")

    if mode == "check_only":
        resolved_state = state
        if state == "AUTO_CAPTURE_PET":
            print(f"[{serial}] Capture window opened at AUTO_CAPTURE_PET. Resolving actual capture state...")
            resolved_state = wait_for_state(
                serial,
                detector,
                ["AUTO_CAPTURE_START", "AUTO_CAPTURE_IN_PROGRESS"],
                timeout_sec=10,
                check_mode="special",
            ) or "AUTO_CAPTURE_PET"

        if resolved_state == "AUTO_CAPTURE_IN_PROGRESS":
            print(f"[{serial}] Auto capture is still in progress. Waiting for completion...")
            while True:
                finished = detector.check_special_state(serial, target="AUTO_CAPTURE_START")
                if finished:
                    print(f"[{serial}] Auto capture completed successfully!")
                    adb_helper.press_back(serial)
                    _human_delay(1.2)
                    return _ok(capture_status="completed")

                print(f"[{serial}] Still in progress... waiting 5s for auto refresh.")
                _human_delay(5)

        print(f"[{serial}] Auto capture is idle/ready (capture likely completed or no warrants).")
        adb_helper.press_back(serial)
        _human_delay(1.2)
        return _ok(capture_status="ready")

    # 6. Tap (284, 398) x5 to configure
    print(f"[{serial}] Configuring Pet Capture (284, 398) x5...")
    for _ in range(5):
        adb_helper.tap(serial, 284, 398)
        _human_delay(0.05)
    _human_delay(2)
    
    # 7. Tap Start
    print(f"[{serial}] Starting Capture (501, 466)...")
    adb_helper.tap(serial, 501, 466)
    _human_delay(2)

    # 8. Check if not enough warrants or capture in progress
    print(f"[{serial}] Checking outcome of Auto Capture...")
    outcome = wait_for_state(serial, detector, ["AUTO_CAPTURE_START", "AUTO_CAPTURE_IN_PROGRESS"], timeout_sec=10, check_mode="special")
    
    if outcome is None:
        print(f"[{serial}] Auto capture started & game pushed to map! Capture successful.")
        return _ok(capture_status="started_background")
        
    if outcome == "AUTO_CAPTURE_IN_PROGRESS":
        print(f"[{serial}] Auto capture is running in background. Leaving screen to use waiting time.")
        adb_helper.press_back(serial)
        _human_delay(1.2)
        return _ok(capture_status="in_progress")
            
    elif outcome == "AUTO_CAPTURE_START":
        print(f"[{serial}] Not enough warrants to capture pet (or idle state returned).")
        adb_helper.press_back(serial)
        _human_delay(1.2)
        return _ok(capture_status="idle_no_warrants")
        
    return _ok(capture_status="unknown")

def go_to_pet_sanctuary(serial: str, detector: GameStateDetector) -> dict:
    """
    Navigates from lobby (OUT_CITY) through Pet Sanctuary into Pet Enclosure.
    """
    print(f"[{serial}] Navigating to Pet Sanctuary...")

    lobby_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)")
    if not _is_ok(lobby_result):
        print(f"[{serial}] [FAILED] Could not reach OUT_CITY.")
        return _bubble(lobby_result, "NAV_LOBBY_UNREACHABLE: Could not reach OUT_CITY")
    menu_result = ensure_lobby_menu_open(serial, detector)
    if not _is_ok(menu_result):
        print(f"[{serial}] [FAILED] Could not expand lobby menu.")
        return _bubble(menu_result, "NAV_MENU_OPEN_FAILED: Could not expand lobby menu")
        
    print(f"[{serial}] Opening Pet Sanctuary (510, 507)...")
    adb_helper.tap(serial, 510, 507)
    _human_delay(3)
    
    state = wait_for_state(serial, detector, ["PET_SANCTUARY"], timeout_sec=10, check_mode="construction")
    if state != "PET_SANCTUARY":
        print(f"[{serial}] [FAILED] Did not reach PET_SANCTUARY state.")
        return _fail("NAV_TARGET_NOT_REACHED: Did not reach PET_SANCTUARY")
    
    print(f"[{serial}] -> PET_SANCTUARY reached successfully.")
    return _ok()

_BLANK_PET_TEMPLATE = os.path.join("pets", "blank_pet_slot_8.png")
_PET_LOCK_TEMPLATE = os.path.join("pets", "pet_lock_icon.png")
_PET_KEEP_COUNT = 7
_PET_LOCK_THRESHOLD = 0.75
_PET_BLANK_THRESHOLD = 0.80

_PET_LOCK_ROIS = [
    {"slot": "r1c1", "lock_roi": (150, 165, 180, 190), "slot_roi": (110, 110, 180, 190)},
    {"slot": "r2c1", "lock_roi": (150, 250, 180, 275), "slot_roi": (110, 190, 180, 275)},
    {"slot": "r3c1", "lock_roi": (150, 330, 180, 360), "slot_roi": (110, 278, 180, 360)},
    {"slot": "r4c1", "lock_roi": (150, 405, 180, 435), "slot_roi": (110, 360, 180, 435)},
    {"slot": "r1c2", "lock_roi": (225, 165, 250, 190), "slot_roi": (180, 110, 250, 190)},
    {"slot": "r2c2", "lock_roi": (225, 250, 250, 275), "slot_roi": (180, 190, 250, 275)},
    {"slot": "r3c2", "lock_roi": (225, 330, 250, 360), "slot_roi": (180, 278, 250, 360)},
    {"slot": "r4c2", "lock_roi": (225, 405, 250, 435), "slot_roi": (180, 360, 250, 435)},
    {"slot": "r1c3", "lock_roi": (295, 165, 320, 190), "slot_roi": (250, 110, 320, 190)},
    {"slot": "r2c3", "lock_roi": (295, 250, 320, 275), "slot_roi": (250, 190, 320, 275)},
    {"slot": "r3c3", "lock_roi": (295, 330, 320, 360), "slot_roi": (250, 278, 320, 360)},
    {"slot": "r4c3", "lock_roi": (295, 405, 320, 435), "slot_roi": (250, 360, 320, 435)},
]


def _is_pet_slot_blank(
    serial: str, detector: GameStateDetector, roi: tuple, threshold: float = 0.80
) -> bool:
    """Check if a pet grid slot is empty using blank-slot template matching.

    Args:
        roi: (x1, y1, x2, y2) crop region for the slot.
        threshold: Match confidence threshold.

    Returns True if the slot is blank (empty).
    """
    frame = detector.get_frame(serial)
    if frame is None:
        return False

    x1, y1, x2, y2 = roi
    roi_crop = frame[y1:y2, x1:x2]
    if roi_crop.size == 0:
        return False

    template_path = os.path.join(detector.templates_dir, _BLANK_PET_TEMPLATE)
    if not os.path.exists(template_path):
        print(f"[{serial}] [PET] [WARNING] Blank slot template not found: {template_path}")
        return False

    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if template is None:
        return False

    roi_gray = cv2.cvtColor(roi_crop, cv2.COLOR_BGR2GRAY) if len(roi_crop.shape) == 3 else roi_crop

    # Resize template to match ROI if larger
    th, tw = template.shape[:2]
    rh, rw = roi_gray.shape[:2]
    if th > rh or tw > rw:
        template = cv2.resize(template, (rw, rh))

    result = cv2.matchTemplate(roi_gray, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)

    is_blank = max_val >= threshold
    print(f"[{serial}] [PET] Slot blank check ROI={roi}: conf={max_val:.3f} → {'BLANK' if is_blank else 'HAS PET'}")
    return is_blank


def _match_pet_template(roi_crop: np.ndarray, template_path: str) -> float:
    if roi_crop.size == 0 or not os.path.exists(template_path):
        return 0.0

    template = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
    if template is None:
        return 0.0

    if len(template.shape) == 3 and template.shape[2] == 4:
        template = template[:, :, :3]

    if roi_crop.shape[0] < template.shape[0] or roi_crop.shape[1] < template.shape[1]:
        template = cv2.resize(template, (roi_crop.shape[1], roi_crop.shape[0]))

    roi_gray = cv2.cvtColor(roi_crop, cv2.COLOR_BGR2GRAY)
    tpl_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

    gray_res = cv2.matchTemplate(roi_gray, tpl_gray, cv2.TM_CCOEFF_NORMED)
    _, gray_val, _, _ = cv2.minMaxLoc(gray_res)

    color_res = cv2.matchTemplate(roi_crop, template, cv2.TM_CCOEFF_NORMED)
    _, color_val, _, _ = cv2.minMaxLoc(color_res)

    return max(float(gray_val), float(color_val))


def _scan_pet_release_candidates(serial: str, detector: GameStateDetector) -> list[dict]:
    frame = detector.get_frame(serial)
    if frame is None:
        print(f"[{serial}] [PET] [WARNING] Could not capture frame for pet grid scan.")
        return []

    blank_template_path = os.path.join(detector.templates_dir, _BLANK_PET_TEMPLATE)
    lock_template_path = os.path.join(detector.templates_dir, _PET_LOCK_TEMPLATE)
    results = []

    for slot_def in _PET_LOCK_ROIS:
        slot_name = slot_def["slot"]
        sx1, sy1, sx2, sy2 = slot_def["slot_roi"]
        lx1, ly1, lx2, ly2 = slot_def["lock_roi"]

        slot_roi = frame[sy1:sy2, sx1:sx2]
        lock_roi = frame[ly1:ly2, lx1:lx2]
        blank_conf = _match_pet_template(slot_roi, blank_template_path)
        is_blank = blank_conf >= _PET_BLANK_THRESHOLD
        lock_conf = _match_pet_template(lock_roi, lock_template_path)
        is_locked = (not is_blank) and lock_conf >= _PET_LOCK_THRESHOLD

        if is_blank:
            status = "BLANK"
        elif is_locked:
            status = "LOCKED"
        else:
            status = "RELEASE"

        tap_point = ((sx1 + sx2) // 2, (sy1 + sy2) // 2)
        print(
            f"[{serial}] [PET] {slot_name.upper()} -> {status} "
            f"(blank={blank_conf:.3f}, lock={lock_conf:.3f}, tap={tap_point})"
        )
        results.append(
            {
                "slot": slot_name,
                "status": status,
                "tap": tap_point,
                "slot_roi": slot_def["slot_roi"],
                "lock_roi": slot_def["lock_roi"],
                "blank_confidence": blank_conf,
                "lock_confidence": lock_conf,
            }
        )

    return results


def _release_single_pet(serial: str, detector: GameStateDetector, tap_point: tuple):
    """Execute the release UI sequence for one pet at the given grid position.

    Captures skill pool (Phase 1) and skill obtained (Phase 2) for data analysis.
    Both screenshots share the same release_id for pairing.
    """
    release_id = time.strftime("%Y%m%d_%H%M%S")
    save_dir = os.path.join("data", "pet_releases")
    os.makedirs(save_dir, exist_ok=True)

    adb_helper.tap(serial, tap_point[0], tap_point[1])  # Select pet in grid
    _human_delay(1.5)
    adb_helper.tap(serial, 352, 214)   # "Release" button → GHI CHÚ popup
    _human_delay(1.5)

    # Phase 1: Capture skill pool available
    detector._screen_cache = None
    frame1 = detector.get_frame(serial)
    if frame1 is not None:
        crop1 = frame1[150:300, 250:700]
        fname1 = f"available_{serial}_{release_id}.png"
        cv2.imwrite(os.path.join(save_dir, fname1), crop1)
        print(f"[{serial}] [PET] Phase 1 saved: {fname1}")

    adb_helper.tap(serial, 577, 365)   # Confirm dialog (XÁC NHẬN)
    _human_delay(1.5)

    # Phase 2: Capture skill obtained
    detector._screen_cache = None
    frame2 = detector.get_frame(serial)
    if frame2 is not None:
        crop2 = frame2[100:200, 400:560]
        fname2 = f"get_{serial}_{release_id}.png"
        cv2.imwrite(os.path.join(save_dir, fname2), crop2)
        print(f"[{serial}] [PET] Phase 2 saved: {fname2}")

    adb_helper.tap(serial, 547, 414)   # OK / second confirm
    _human_delay(2)


def release_pet(serial: str, detector: GameStateDetector) -> dict:
    """Release all unlocked pets from PET_ENCLOSURE."""
    print(f"[{serial}] === RELEASE PET ===")

    adb_helper.tap(serial, 918, 504)
    _human_delay(3)

    state = wait_for_state(serial, detector, ["PET_ENCLOSURE"], timeout_sec=10, check_mode="construction")
    if state != "PET_ENCLOSURE":
        print(f"[{serial}] [FAILED] Did not reach PET_ENCLOSURE state.")
        return _fail("NAV_TARGET_NOT_REACHED: Did not reach PET_ENCLOSURE")

    # 3. Navigate sort/release tabs
    print(f"[{serial}] Selecting Release Tabs (254,93) -> (670,131) -> (50,135)...")
    adb_helper.tap(serial, 254, 93)
    _human_delay(2)
    adb_helper.tap(serial, 670, 131)
    _human_delay(2.8)
    adb_helper.tap(serial, 50, 135)
    _human_delay(2)

    released = 0

    while True:
        detector._cache.invalidate()
        scan_results = _scan_pet_release_candidates(serial, detector)
        if not scan_results:
            print(f"[{serial}] [PET] [WARNING] Pet grid scan returned no slots. Stopping release flow.")
            break

        locked_slots = [item for item in scan_results if item["status"] == "LOCKED"]
        release_slots = [item for item in scan_results if item["status"] == "RELEASE"]
        occupied_count = len(locked_slots) + len(release_slots)

        print(
            f"[{serial}] [PET] Grid summary: "
            f"locked={len(locked_slots)} release={len(release_slots)} occupied={occupied_count}"
        )

        if occupied_count <= _PET_KEEP_COUNT:
            print(
                f"[{serial}] [PET] Stop condition reached: locked + release = {occupied_count} <= {_PET_KEEP_COUNT}. "
                f"Keeping remaining pets."
            )
            break

        if not release_slots:
            print(
                f"[{serial}] [PET] [WARNING] No release candidates left, but occupied={occupied_count} > {_PET_KEEP_COUNT}. "
                f"Likely too many locked pets. Stopping safely."
            )
            break

        target_slot = release_slots[0]
        print(
            f"[{serial}] [PET] Releasing {target_slot['slot'].upper()} at {target_slot['tap']} "
            f"(blank={target_slot['blank_confidence']:.3f}, lock={target_slot['lock_confidence']:.3f})"
        )
        _release_single_pet(serial, detector, target_slot["tap"])
        released += 1
        _human_delay(1.5)

    # 5. Exit
    print(f"[{serial}] Back x2 to exit Pet screen...")
    adb_helper.press_back(serial)
    _human_delay(2)
    adb_helper.press_back(serial)
    _human_delay(2)

    print(f"[{serial}] === RELEASE PET COMPLETE — released {released} pet(s) ===")
    return _ok()

def _human_delay(base_sec: float, variance: float = 0.2):
    """Sleep with Gaussian randomization to simulate human reaction time."""
    sigma = base_sec * variance
    delay = random.gauss(base_sec, sigma)
    time.sleep(max(0.1, delay))


def _detect_with_retry(serial, detector, target, threshold=0.8, attempts=3, delay=1.5):
    """Try to detect a template with retries. Returns match tuple or None."""
    for attempt in range(attempts):
        detector._screen_cache = None
        result = detector.check_activity(serial, target=target, threshold=threshold)
        if result:
            return result
        if attempt < attempts - 1:
            print(f"[{serial}] {target} not found, retrying ({attempt + 1}/{attempts})...")
            _human_delay(delay)
    return None


_SEARCH_MENU_TAP = (42, 422)
_SEARCH_CATEGORY_TAPS = {
    "darkling": (158, 486),
    "gold": (320, 485),
    "wood": (475, 485),
    "stone": (640, 485),
    "mana": (795, 485),
}
_SEARCH_TAB_ROIS = {
    "darkling": (80, 370, 260, 425),
    "gold": (320, 370, 410, 425),
    "wood": (385, 370, 560, 425),
    "stone": (545, 370, 720, 425),
    "mana": (700, 370, 875, 425),
}
_SEARCH_BTN_TEMPLATE = os.path.join("activities", "search_btn.png")


def _detect_search_menu_current_category(serial: str, detector: GameStateDetector) -> str | None:
    frame = detector.get_frame(serial)
    if frame is None:
        print(f"[{serial}] [SEARCH] [WARNING] Could not capture frame to detect current category.")
        return None

    template_path = os.path.join(detector.templates_dir, _SEARCH_BTN_TEMPLATE)
    best_category = None
    best_score = -1.0

    for category, (x1, y1, x2, y2) in _SEARCH_TAB_ROIS.items():
        roi = frame[y1:y2, x1:x2]
        score = _match_pet_template(roi, template_path)
        print(f"[{serial}] [SEARCH] Category ROI {category.upper()} score={score:.3f}")
        if score > best_score:
            best_score = score
            best_category = category

    print(f"[{serial}] [SEARCH] Current category detected as {best_category} (score={best_score:.3f})")
    return best_category


def _ensure_search_menu_category(serial: str, detector: GameStateDetector, target_category: str) -> str | None:
    print(f"[{serial}] Opening Search Menu {_SEARCH_MENU_TAP}...")
    adb_helper.tap(serial, _SEARCH_MENU_TAP[0], _SEARCH_MENU_TAP[1])
    _human_delay(1.0)

    search_panel = _detect_with_retry(serial, detector, "FARM_SEARCH_BTN", threshold=0.8, attempts=3, delay=1)
    if not search_panel:
        print(f"[{serial}] [FAILED] Search panel did not open.")
        return None

    print(f"[{serial}] Search panel confirmed open.")
    current_category = _detect_search_menu_current_category(serial, detector)
    if current_category and current_category == target_category:
        print(f"[{serial}] [SEARCH] Current category already matches target {target_category.upper()}.")
        return current_category

    target_tap = _SEARCH_CATEGORY_TAPS[target_category]
    print(f"[{serial}] [SEARCH] Switching category to {target_category.upper()} at {target_tap}...")
    adb_helper.tap(serial, target_tap[0], target_tap[1])
    _human_delay(1.0)
    return current_category


def go_to_farming(
    serial: str,
    detector: GameStateDetector,
    farming_mode: str = "legacy",
    resource_type: str = "wood",
    rotation_shuffle: bool = False,
    legion_resource_plan: list[str] | None = None,
    max_legions: int = 5,
) -> dict:
    """
    Farming Workflow (Anti-Detection Enhanced):
    1. Back to OUT_CITY
    2. Pre-compute random search method per dispatch (menu vs manual)
    3. For each dispatch:
       - Method 1 (menu): open search -> multi-click search K times -> gather
       - Method 2 (manual): zoom out -> scan map templates -> tap mine -> gather
    4. Create Legion -> Select Preset -> Dispatch -> Verify OUT_CITY

    Anti-bot: randomized delays, randomized search method, randomized mine selection.
    """
    RESOURCE_TAPS = {
        "gold": (320, 485), "wood": (475, 485),
        "stone": (640, 485), "mana": (795, 485),
    }
    SEARCH_TAPS = {
        "gold": (320, 400), "wood": (475, 400),
        "stone": (640, 400), "mana": (795, 400),
    }
    ALL_LEGION_TAPS = [
        (695, 90), (735, 90), (780, 90), (825, 90), (865, 90),
    ]
    ROTATION_ORDER = ["gold", "wood", "stone", "mana"]
    VALID_RESOURCES = set(RESOURCE_TAPS.keys())

    mode = str(farming_mode or "legacy").strip().lower()
    if mode not in {"legacy", "manual"}:
        return _fail(f"CONFIG_INVALID_PARAM: Unknown farming_mode '{farming_mode}'")

    r_type = resource_type.lower()
    if r_type != "rotation" and r_type not in RESOURCE_TAPS:
        print(f"[{serial}] [ERROR] Unknown resource type: {resource_type}")
        return _fail(f"CONFIG_INVALID_PARAM: Unknown resource type '{resource_type}'")

    try:
        resolved_max_legions = int(max_legions or 0)
    except Exception:
        resolved_max_legions = 0
    resolved_max_legions = max(0, min(5, resolved_max_legions))
    if resolved_max_legions <= 0:
        print(f"[{serial}] No free legion capacity available for farming. Skipping dispatch.")
        return _ok()
    LEGION_TAPS = ALL_LEGION_TAPS[:resolved_max_legions]

    normalized_legion_plan = None
    if legion_resource_plan:
        normalized_legion_plan = []
        for idx, raw_value in enumerate(legion_resource_plan, start=1):
            value = str(raw_value or "wood").strip().lower()
            if value == "skip":
                normalized_legion_plan.append("skip")
                continue
            if value not in VALID_RESOURCES:
                return _fail(
                    f"CONFIG_INVALID_PARAM: Unknown legion_{idx}_resource '{raw_value}'"
                )
            normalized_legion_plan.append(value)

    print(f"[{serial}] Starting Farming Workflow mode={mode} resource_type={resource_type.upper()}")
    print(f"[{serial}] Farming legion capacity resolved to {resolved_max_legions} preset(s).")

    # 1. Back to lobby OUT_CITY
    result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)")
    if not _is_ok(result):
        print(f"[{serial}] [FAILED] Could not reach OUT_CITY lobby.")
        return _bubble(result, "NAV_LOBBY_UNREACHABLE: Could not reach OUT_CITY lobby")

    resource_plan = (
        normalized_legion_plan[:len(LEGION_TAPS)]
        if mode == "manual" and normalized_legion_plan
        else (
            _build_resource_plan(len(LEGION_TAPS), ROTATION_ORDER, shuffle=rotation_shuffle)
            if r_type == "rotation"
            else [r_type] * len(LEGION_TAPS)
        )
    )
    # 2. Pre-compute dispatch resources + search methods
    resource_plan, methods = _plan_farming_dispatches(
        resource_plan,
        mode=mode,
        selected_resource_type=r_type,
    )
    search_k_values = _plan_search_clicks(len(LEGION_TAPS))
    shuffled_legion_taps = _shuffle_preset_legions(LEGION_TAPS)
    print(f"[{serial}] Search plan: {methods}, K values: {search_k_values}")
    print(
        f"[{serial}] Resource plan: {resource_plan} "
        f"(mode={mode}, shuffle={rotation_shuffle})"
    )
    print(f"[{serial}] Legion preset order: {[LEGION_TAPS.index(tap) + 1 for tap in shuffled_legion_taps]}")
    planned_dispatches = sum(1 for item in resource_plan if item != "skip")
    required_dispatches = min(3, planned_dispatches)

    # 3. Dispatch loop
    consumed_manual_positions = set()
    total_deployed = 0

    def _dispatch_menu_backup(
        dispatch_idx: int,
        legion_tap: tuple[int, int],
        dispatch_resource: str,
        search_clicks: int,
        reason: str,
    ) -> tuple[str, int]:
        print(
            f"[{serial}] [MENU BACKUP] Manual fallback for dispatch #{dispatch_idx + 1} "
            f"resource={dispatch_resource.upper()} reason={reason}."
        )
        mine_result = _search_mine_via_menu(
            serial,
            detector,
            dispatch_resource,
            RESOURCE_TAPS,
            SEARCH_TAPS,
            search_clicks=search_clicks,
        )
        if mine_result is None:
            print(f"[{serial}] [MENU BACKUP] No mine found via menu. Stopping backup.")
            return "stop", 0
        if mine_result == "occupied":
            print(f"[{serial}] [MENU BACKUP] Menu result occupied. Continuing without deploy.")
            return "continue", 0

        print(f"[{serial}] [MENU BACKUP] Locked mine type: {mine_result.upper()}")
        if not _gather_and_dispatch_current_mine(
            serial,
            detector,
            legion_tap,
            LEGION_TAPS,
        ):
            return "stop", 0
        return "continue", 1

    for idx, legion_tap in enumerate(shuffled_legion_taps):
        if idx in consumed_manual_positions:
            continue
        method = methods[idx]
        k_val = search_k_values[idx]
        dispatch_resource = resource_plan[idx]
        if dispatch_resource == "skip":
            print(f"\n[{serial}] --- Dispatch #{idx+1} skipped by config ---")
            continue

        if method == "manual":
            block_indices = []
            scan_idx = idx
            while (
                scan_idx < len(shuffled_legion_taps)
                and resource_plan[scan_idx] == dispatch_resource
                and methods[scan_idx] == "manual"
            ):
                block_indices.append(scan_idx)
                consumed_manual_positions.add(scan_idx)
                scan_idx += 1

            block_taps = [shuffled_legion_taps[pos] for pos in block_indices]
            print(
                f"\n[{serial}] --- Manual Session {dispatch_resource.upper()} "
                f"(dispatches {block_indices[0]+1}-{block_indices[-1]+1}) ---"
            )
            session_result, session_deployed = _run_manual_dispatch_session(
                serial,
                detector,
                dispatch_resource,
                block_taps,
                RESOURCE_TAPS,
                SEARCH_TAPS,
                LEGION_TAPS,
            )
            total_deployed += session_deployed
            if session_result == "stop":
                break
            if session_result == "manual_no_mine" and session_deployed < len(block_taps):
                remaining_positions = block_indices[session_deployed:]
                print(
                    f"[{serial}] [MENU BACKUP] Manual session deployed "
                    f"{session_deployed}/{len(block_taps)} for {dispatch_resource.upper()}. "
                    f"Backing up {len(remaining_positions)} remaining dispatch(es) with menu."
                )
                for backup_pos in remaining_positions:
                    backup_status, backup_deployed = _dispatch_menu_backup(
                        backup_pos,
                        shuffled_legion_taps[backup_pos],
                        dispatch_resource,
                        search_k_values[backup_pos],
                        session_result,
                    )
                    total_deployed += backup_deployed
                    if backup_status == "stop":
                        session_result = "stop"
                        break
                if session_result == "stop":
                    break
            continue
        print(f"\n[{serial}] --- Dispatch #{idx+1} ({method} search, K={k_val}, resource={dispatch_resource.upper()}) ---")

        if method == "menu":
            mine_result = _search_mine_via_menu(
                serial, detector, dispatch_resource, RESOURCE_TAPS, SEARCH_TAPS,
                search_clicks=k_val,
            )
        else:
            mine_result = _search_mine_manual(serial, detector, dispatch_resource)

        if mine_result is None:
            # No mine found — stop dispatching
            break

        if mine_result == "occupied":
            # Mine was occupied (View), continue to next dispatch
            continue

        # mine_result is the actual resource type used (may differ from dispatch plan if fallback)
        print(f"[{serial}] Dispatch #{idx+1} locked mine type: {mine_result.upper()}")

        # ── Gather -> Create Legion -> Preset -> Dispatch ──
        gather_btn = _detect_with_retry(serial, detector, "RSS_GATHER", threshold=0.8, attempts=3, delay=1)
        if not gather_btn:
            print(f"[{serial}] [WARNING] Gather button not visible. Mine popup may not have loaded.")
            current_state = detector.check_state(serial)
            if current_state == "IN-GAME LOBBY (OUT_CITY)":
                print(f"[{serial}] Already at OUT_CITY after missing Gather. Not pressing BACK.")
            else:
                print(f"[{serial}] Cleaning up missing Gather state via back_to_lobby()...")
                back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)", timeout_sec=10)
            break

        if not _gather_and_dispatch_current_mine(
            serial,
            detector,
            legion_tap,
            LEGION_TAPS,
            gather_btn=gather_btn,
        ):
            break

        total_deployed += 1

    print(f"[{serial}] Farming Deployment Finished.")

    print(f"[{serial}] Farming Deployment Finished. Total deployed count: {total_deployed}")
    if total_deployed < required_dispatches:
        return _fail(
            f"RESOURCE_SLOT_FULL: Only deployed {total_deployed} legions "
            f"(required {required_dispatches}). Missing CREATE_LEGION or node occupied."
        )
    return _ok()


def _plan_farming_dispatches(
    resource_plan: list[str],
    mode: str = "legacy",
    selected_resource_type: str = "wood",
) -> tuple[list[str], list[str]]:
    """Build dispatch resource order and per-dispatch search method.

    Rules:
    - legacy mode:
      - fixed resource => keep order, all manual
      - rotation => count-based methods without reordering
    - manual mode:
      - resources with count >= 2 are grouped together and use manual
      - resources with count == 1 are randomized between menu/manual
      - skip entries are preserved at the end
    """
    counts = {}
    first_seen_order = []
    skip_count = 0

    def _pick_weighted_search_method() -> str:
        return "menu" if random.random() < 0.70 else "manual"

    for item in resource_plan:
        if item == "skip":
            skip_count += 1
            continue
        if item not in counts:
            counts[item] = 0
            first_seen_order.append(item)
        counts[item] += 1

    if mode == "legacy":
        legacy_plan = list(resource_plan)
        if selected_resource_type != "rotation":
            methods = ["skip" if item == "skip" else "manual" for item in legacy_plan]
            return legacy_plan, methods

        methods = []
        for name in legacy_plan:
            if name == "skip":
                methods.append("skip")
            elif counts.get(name, 0) >= 2:
                methods.append("manual")
            else:
                methods.append(_pick_weighted_search_method())
        return legacy_plan, methods

    repeated_resources = [name for name in first_seen_order if counts.get(name, 0) >= 2]
    single_resources = [name for name in resource_plan if name != "skip" and counts.get(name, 0) == 1]
    reordered_plan = []

    for name in repeated_resources:
        reordered_plan.extend([name] * counts[name])
    reordered_plan.extend(single_resources)
    reordered_plan.extend(["skip"] * skip_count)

    methods = []
    for name in reordered_plan:
        if name == "skip":
            methods.append("skip")
        elif counts.get(name, 0) >= 2:
            methods.append("manual")
        else:
            methods.append(_pick_weighted_search_method())

    return reordered_plan, methods


def _shuffle_preset_legions(legion_taps: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Shuffle preset legion order with slots 1-4 randomized and slot 5 fixed last."""
    if len(legion_taps) <= 1:
        return list(legion_taps)
    if len(legion_taps) < 5:
        shuffled = list(legion_taps)
        random.shuffle(shuffled)
        return shuffled

    first_four = list(legion_taps[:4])
    random.shuffle(first_four)
    return first_four + [legion_taps[4]]


_MANUAL_SCAN_STEP_SEGMENTS = {
    "R": ((180, 270), (760, 270)),
    "L": ((760, 270), (180, 270)),
    "U": ((480, 430), (480, 90)),
    "D": ((480, 90), (480, 430)),
}
_MANUAL_SCAN_SETTLE_S = 1.5
_MANUAL_SCAN_RADIUS = 3
_MANUAL_SCAN_SKIP_INNER_RING = 2
_MANUAL_ICON_DEDUPE_PX = 70
_MANUAL_MAX_CONSECUTIVE_EMPTY_SWIPES = 15


def _build_ring_perimeter(ring: int, clockwise: bool = True) -> list[tuple[int, int]]:
    if ring <= 0:
        return []

    coords: list[tuple[int, int]] = []
    for x in range(-ring, ring + 1):
        coords.append((x, -ring))
    for y in range(-ring + 1, ring + 1):
        coords.append((ring, y))
    for x in range(ring - 1, -ring - 1, -1):
        coords.append((x, ring))
    for y in range(ring - 1, -ring, -1):
        coords.append((-ring, y))

    if not clockwise:
        coords = list(reversed(coords))

    start_idx = random.randint(0, len(coords) - 1)
    return coords[start_idx:] + coords[:start_idx]


def _grid_path_to_step_plan(targets: list[tuple[int, int]]) -> list[tuple[str, tuple[tuple[int, int], tuple[int, int]], tuple[int, int]]]:
    current_x, current_y = 0, 0
    plan: list[tuple[str, tuple[tuple[int, int], tuple[int, int]], tuple[int, int]]] = []

    for target_x, target_y in targets:
        while current_x != target_x or current_y != target_y:
            if current_x != target_x and current_y != target_y:
                move_axis = random.choice(["x", "y"])
            elif current_x != target_x:
                move_axis = "x"
            else:
                move_axis = "y"

            if move_axis == "x":
                step_name = "R" if target_x > current_x else "L"
                current_x += 1 if step_name == "R" else -1
            else:
                step_name = "D" if target_y > current_y else "U"
                current_y += 1 if step_name == "D" else -1

            plan.append((step_name, _MANUAL_SCAN_STEP_SEGMENTS[step_name], (current_x, current_y)))

    return plan


def _build_outward_ring_scan_plan(
    radius: int = _MANUAL_SCAN_RADIUS,
    min_ring_first: int = _MANUAL_SCAN_SKIP_INNER_RING,
) -> list[tuple[str, tuple[tuple[int, int], tuple[int, int]], tuple[int, int]]]:
    if radius <= 0:
        return []

    clockwise = random.choice([True, False])
    ring_order = [ring for ring in range(max(1, min_ring_first), radius + 1)]
    if min_ring_first > 1:
        ring_order.extend(range(1, min_ring_first))

    targets: list[tuple[int, int]] = []
    for ring in ring_order:
        targets.extend(_build_ring_perimeter(ring, clockwise=clockwise))

    plan = _grid_path_to_step_plan(targets)
    print(
        f"[MANUAL SCAN] Outward ring plan radius={radius} "
        f"ring_order={ring_order} rotation={'clockwise' if clockwise else 'counterclockwise'} "
        f"steps={len(plan)}"
    )
    return plan


def _is_near_any_point(point: tuple[int, int], points: list[tuple[int, int]], threshold_px: float = _MANUAL_ICON_DEDUPE_PX) -> bool:
    for px, py in points:
        if ((point[0] - px) ** 2 + (point[1] - py) ** 2) ** 0.5 < threshold_px:
            return True
    return False


def _compute_gather_tap_point(gather_btn: tuple[str, int, int]) -> tuple[int, int]:
    """Bias gather taps slightly into the body of the button.

    The RSS_GATHER template is text-centric. In practice, tapping a little
    down/right from the template center is more forgiving when the popup is
    still settling or the matched text sits near the button edge.
    """
    _, gx, gy = gather_btn
    return min(900, gx + 18), min(500, gy + 10)


def _gather_and_dispatch_current_mine(
    serial: str,
    detector: GameStateDetector,
    legion_tap: tuple[int, int],
    legion_taps_master: list[tuple[int, int]],
    gather_btn=None,
    return_status: bool = False,
) -> bool | tuple[bool, str]:
    def _finish(ok: bool, status: str) -> bool | tuple[bool, str]:
        return (ok, status) if return_status else ok

    if not gather_btn:
        gather_btn = _detect_with_retry(serial, detector, "RSS_GATHER", threshold=0.8, attempts=3, delay=0.35)
    if not gather_btn:
        print(f"[{serial}] [WARNING] Gather button not visible. Mine popup may not have loaded.")
        return _finish(False, "gather_not_visible")

    _, gx, gy = gather_btn
    tap_x, tap_y = _compute_gather_tap_point(gather_btn)
    print(
        f"[{serial}] Tapping Gather Button at detected ({gx}, {gy}) "
        f"using click point ({tap_x}, {tap_y})..."
    )
    adb_helper.tap(serial, tap_x, tap_y)
    _human_delay(0.55)

    print(f"[{serial}] Checking if we can deploy legions (looking for CREATE_LEGION)...")
    create_result = _detect_with_retry(serial, detector, "CREATE_LEGION", threshold=0.8, attempts=4, delay=0.25)
    if not create_result:
        gather_still_visible = _detect_with_retry(serial, detector, "RSS_GATHER", threshold=0.8, attempts=2, delay=0.2)
        if gather_still_visible:
            retry_x = min(910, tap_x + 18)
            retry_y = min(505, tap_y + 8)
            print(
                f"[{serial}] Gather button still visible after first tap. "
                f"Retrying safer click at ({retry_x}, {retry_y})..."
            )
            adb_helper.tap(serial, retry_x, retry_y)
            _human_delay(0.65)
            print(f"[{serial}] Re-checking CREATE_LEGION after gather retry...")
            create_result = _detect_with_retry(serial, detector, "CREATE_LEGION", threshold=0.8, attempts=5, delay=0.25)
    if not create_result:
        current_state = detector.check_state(serial)
        if current_state == "IN-GAME LOBBY (OUT_CITY)":
            print(
                f"[{serial}] CREATE_LEGION not found and already OUT_CITY. "
                "Likely gather tap missed or popup was dismissed; not pressing BACK."
            )
            return _finish(False, "already_out_city")

        print(f"[{serial}] Legions are FULL, node is occupied, or no AP! Returning safely to OUT_CITY.")
        back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)", timeout_sec=10)
        return _finish(False, "create_legion_missing")

    print(f"[{serial}] Found CREATE_LEGION -> Deploying forces...")
    print(f"[{serial}] Tapping Create Legion Button (755, 115)...")
    adb_helper.tap(serial, 755, 115)
    _human_delay(1.3)

    preset_number = legion_taps_master.index(legion_tap) + 1
    print(f"[{serial}] Selecting Legion Preset #{preset_number} at {legion_tap}...")
    adb_helper.tap(serial, legion_tap[0], legion_tap[1])
    _human_delay(0.45)

    dispatch_loc = (850, 480)
    print(f"[{serial}] Tapping March/Dispatch {dispatch_loc}...")
    adb_helper.tap(serial, dispatch_loc[0], dispatch_loc[1])
    _human_delay(0.8)

    state = wait_for_state(serial, detector, ["IN-GAME LOBBY (OUT_CITY)"], timeout_sec=10)
    if not state:
        print(f"[{serial}] [WARNING] Did not return to OUT_CITY after dispatch. Recovering...")
        back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)")
    return _finish(True, "deployed")


def _run_manual_dispatch_session(
    serial: str,
    detector: GameStateDetector,
    r_type: str,
    legion_taps: list[tuple[int, int]],
    resource_taps: dict,
    search_taps: dict,
    legion_taps_master: list[tuple[int, int]],
) -> tuple[str, int]:
    anchor_result = _search_mine_via_menu(
        serial,
        detector,
        r_type,
        resource_taps,
        search_taps,
        search_clicks=1,
    )
    if anchor_result is None:
        print(f"[{serial}] [MANUAL SESSION] No anchor mine found for {r_type.upper()}.")
        return "manual_no_mine", 0
    if anchor_result == "occupied":
        print(f"[{serial}] [MANUAL SESSION] Anchor mine occupied for {r_type.upper()}. Skipping block.")
        return "manual_no_mine", 0

    print(f"[{serial}] [MANUAL SESSION] Anchor mine found ({anchor_result.upper()}). Scanning for nearby alternatives...")
    print(f"[{serial}] [MANUAL SESSION] Dismissing anchor mine popup before manual scan...")
    adb_helper.tap(serial, 480, 270)
    _human_delay(0.8)

    icon_targets = {
        "gold": "MANUAL_RSS_GOLD",
        "wood": "MANUAL_RSS_WOOD",
        "stone": "MANUAL_RSS_ORE",
        "mana": "MANUAL_RSS_MANA",
    }
    plan = _build_outward_ring_scan_plan()
    planned_steps = len(plan)
    legion_idx = 0
    blocked_centers: list[tuple[int, int]] = []
    consecutive_empty_swipes = 0

    for step_idx, (direction_name, segment, grid_xy) in enumerate(plan, start=1):
        if legion_idx >= len(legion_taps):
            break

        print(
            f"[{serial}] [MANUAL SESSION] Swipe {step_idx}/{planned_steps} "
            f"dir={direction_name} grid={grid_xy}"
        )
        adb_helper.swipe(
            serial,
            segment[0][0], segment[0][1],
            segment[1][0], segment[1][1],
            1200,
        )
        _human_delay(_MANUAL_SCAN_SETTLE_S)

        initial_icon_matches = detector.find_all_icon_matches(serial, target=icon_targets[r_type], threshold=0.75)
        if not initial_icon_matches:
            consecutive_empty_swipes += 1
            if consecutive_empty_swipes >= _MANUAL_MAX_CONSECUTIVE_EMPTY_SWIPES:
                print(
                    f"[{serial}] [MANUAL SESSION] Reached consecutive empty swipe limit "
                    f"{consecutive_empty_swipes}/{_MANUAL_MAX_CONSECUTIVE_EMPTY_SWIPES}. "
                    f"Stopping manual scan early."
                )
                break
            continue
        consecutive_empty_swipes = 0
        same_screen_limit = max(1, len(initial_icon_matches))
        same_screen_taps = 0
        current_icon_matches = initial_icon_matches

        while same_screen_taps < same_screen_limit and legion_idx < len(legion_taps):
            print(
                f"[{serial}] [MANUAL SESSION] Found {len(current_icon_matches)} nearby {r_type.upper()} "
                f"icon match(es) on this screen."
            )
            dispatched_this_pass = False
            for icon_x, icon_y in current_icon_matches:
                candidate_center = (icon_x, icon_y)
                if _is_near_any_point(candidate_center, blocked_centers):
                    continue

                print(f"[{serial}] [MANUAL SESSION] Probing icon at ({icon_x}, {icon_y}).")
                adb_helper.tap(serial, icon_x, icon_y)
                _human_delay(0.45)

                gather_btn = _detect_with_retry(serial, detector, "RSS_GATHER", threshold=0.8, attempts=2, delay=0.3)
                if gather_btn:
                    print(f"[{serial}] [MANUAL SESSION] Gather available on scanned mine.")
                    dispatched, dispatch_status = _gather_and_dispatch_current_mine(
                        serial,
                        detector,
                        legion_taps[legion_idx],
                        legion_taps_master,
                        gather_btn=gather_btn,
                        return_status=True,
                    )
                    if not dispatched:
                        blocked_centers.append(candidate_center)
                        if dispatch_status == "already_out_city":
                            print(
                                f"[{serial}] [MANUAL SESSION] Gather attempt returned to OUT_CITY. "
                                "Treating as miss-tap and continuing scan."
                            )
                            _human_delay(0.8)
                            continue
                        return "stop", legion_idx
                    legion_idx += 1
                    same_screen_taps += 1
                    dispatched_this_pass = True
                    break

                recall_btn = _detect_with_retry(serial, detector, "RSS_RECALL", threshold=0.8, attempts=1, delay=0.0)
                attack_btn = _detect_with_retry(serial, detector, "RSS_ATTACK", threshold=0.8, attempts=1, delay=0.0)
                view_btn = _detect_with_retry(serial, detector, "RSS_VIEW", threshold=0.8, attempts=1, delay=0.0)
                if recall_btn or attack_btn or view_btn:
                    print(f"[{serial}] [MANUAL SESSION] Candidate icon is occupied/invalid. Trying next match.")
                    blocked_centers.append(candidate_center)
                    _human_delay(0.8)
                    continue

                current_state = detector.check_state(serial)
                if current_state != "IN-GAME LOBBY (OUT_CITY)":
                    print(f"[{serial}] [MANUAL SESSION] Unexpected state {current_state}. Recovering with BACK.")
                    adb_helper.press_back(serial)
                    _human_delay(1.0)
                blocked_centers.append(candidate_center)

            if not dispatched_this_pass:
                break
            if len(initial_icon_matches) < 2:
                break
            if same_screen_taps >= same_screen_limit:
                print(
                    f"[{serial}] [MANUAL SESSION] Reached same-screen tap limit "
                    f"{same_screen_taps}/{same_screen_limit}. Moving to next swipe."
                )
                break

            current_icon_matches = detector.find_all_icon_matches(serial, target=icon_targets[r_type], threshold=0.75)
            if not current_icon_matches:
                break

    if legion_idx == 0:
        print(f"[{serial}] [MANUAL SESSION] No valid nearby mine found after local scan.")
        return "manual_no_mine", 0

    print(f"[{serial}] [MANUAL SESSION] Completed {legion_idx}/{len(legion_taps)} dispatches for {r_type.upper()}.")
    if legion_idx < len(legion_taps):
        return "manual_no_mine", legion_idx
    return "continue", legion_idx


def _build_resource_plan(total: int, rotation_order: list[str], shuffle: bool = False) -> list[str]:
    """Build per-dispatch resource plan.

    Rotation guarantees coverage of all resource types before repeating.
    When shuffle=True, each 4-resource cycle is randomized to avoid a fixed pattern.
    """
    plan = []
    while len(plan) < total:
        cycle = list(rotation_order)
        if shuffle:
            random.shuffle(cycle)
        plan.extend(cycle)
    return plan[:total]


def _plan_search_clicks(total: int) -> list:
    """Pre-compute K (search click count) for each dispatch.

    Weighted distribution favoring K=1:
        K=1: 65%,  K=2: 25%,  K=3: 7%,  K=4: 3%
    After any K>=3 is assigned, all subsequent K values cap at 2.
    """
    weights = [65, 25, 7, 3]  # K=1, K=2, K=3, K=4
    choices = [1, 2, 3, 4]
    capped_weights = [65, 35]   # K=1, K=2 (after deep search)
    capped_choices = [1, 2]

    k_values = []
    deep_used = False

    for _ in range(total):
        if deep_used:
            k = random.choices(capped_choices, weights=capped_weights, k=1)[0]
        else:
            k = random.choices(choices, weights=weights, k=1)[0]
            if k >= 3:
                deep_used = True
        k_values.append(k)

    return k_values


def _search_mine_via_menu(
    serial: str,
    detector: GameStateDetector,
    r_type: str,
    resource_taps: dict,
    search_taps: dict,
    search_clicks: int = 1,
) -> str | None:
    """Search for a mine using the in-game search menu.

    Anti-detection: taps Search K times (K=random 1-5) to skip past the first
    mine and select a mine further away. Each tap pans the map to a different mine.

    Returns:
        r_type (str): resource type found (may differ from input if fallback used)
        "occupied": mine found but already has our legion (View detected)
        None: no mine found at all
    """
    ALL_TYPES = ["gold", "wood", "stone", "mana"]

    category = _ensure_search_menu_category(serial, detector, r_type)
    if category is None:
        return None

    search_x, search_y = search_taps[r_type]
    print(f"[{serial}] [Anti-Detect] Will tap Search {search_clicks} time(s) to randomize mine selection")

    mine_found = False
    for click_num in range(1, search_clicks + 1):
        if click_num > 1:
            reopened = _ensure_search_menu_category(serial, detector, r_type)
            if reopened is None:
                print(f"[{serial}] Search panel didn't reopen. Using last mine.")
                mine_found = True
                break

        print(f"[{serial}] Search click {click_num}/{search_clicks}...")
        adb_helper.tap(serial, search_x, search_y)
        _human_delay(3)

        detector._screen_cache = None
        panel_still_open = detector.check_activity(serial, target="FARM_SEARCH_BTN", threshold=0.8)

        if panel_still_open:
            print(f"[{serial}] [NO MINE] No {r_type} mine nearby on click {click_num}.")
            break

        mine_found = True

    if not mine_found:
        print(f"[{serial}] [NO MINE] Trying other resource types...")
        for alt_type in ALL_TYPES:
            if alt_type == r_type:
                continue

            alt_search_x, alt_search_y = search_taps[alt_type]
            print(f"[{serial}]   Trying {alt_type.upper()}...")

            current_alt = _detect_search_menu_current_category(serial, detector)
            if current_alt != alt_type:
                alt_res_x, alt_res_y = resource_taps[alt_type]
                adb_helper.tap(serial, alt_res_x, alt_res_y)
                _human_delay(1)

            adb_helper.tap(serial, alt_search_x, alt_search_y)
            _human_delay(3)

            detector._screen_cache = None
            still_open = detector.check_activity(serial, target="FARM_SEARCH_BTN", threshold=0.8)
            if not still_open:
                print(f"[{serial}]   {alt_type.upper()} mine found! Switching resource type.")
                r_type = alt_type
                mine_found = True
                break
            else:
                print(f"[{serial}]   No {alt_type.upper()} mine either.")

    if not mine_found:
        print(f"[{serial}] [NO MINE] All resource types exhausted. No mines available!")
        adb_helper.press_back(serial)
        _human_delay(1)
        return None

    print(f"[{serial}] Mine found ({r_type.upper()})! Map panned to resource node.")

    view_btn = _detect_with_retry(serial, detector, "RSS_VIEW", threshold=0.8, attempts=2, delay=0.5)
    if view_btn:
        print(f"[{serial}] [OCCUPIED] Mine already has our legion (View detected). Dismissing...")
        adb_helper.tap(serial, 50, 500)
        _human_delay(1.5)
        return "occupied"

    return r_type

    # ── Open Search Menu ──
    print(f"[{serial}] Opening Search Menu (42, 422)...")
    adb_helper.tap(serial, 42, 422)
    _human_delay(1.0)

    search_panel = _detect_with_retry(serial, detector, "FARM_SEARCH_BTN", threshold=0.8, attempts=3, delay=1)
    if not search_panel:
        print(f"[{serial}] [FAILED] Search panel did not open.")
        adb_helper.press_back(serial)
        _human_delay(1)
        return None

    print(f"[{serial}] Search panel confirmed open.")

    # ── Select Resource Category ──
    res_x, res_y = resource_taps[r_type]
    print(f"[{serial}] Selecting Resource Category {r_type.upper()} ({res_x}, {res_y})...")
    adb_helper.tap(serial, res_x, res_y)
    _human_delay(1)

    # ── Multi-click Search (anti-detection) ──
    # Each search click exits menu → pans to mine. Game remembers resource type.
    search_x, search_y = search_taps[r_type]
    print(f"[{serial}] [Anti-Detect] Will tap Search {search_clicks} time(s) to randomize mine selection")

    mine_found = False
    for click_num in range(1, search_clicks + 1):
        if click_num > 1:

            # Re-open search menu (game remembers resource type)
            print(f"[{serial}] Re-opening Search Menu...")
            adb_helper.tap(serial, 42, 422)
            _human_delay(1.0)

            # Verify panel reopened
            detector._screen_cache = None
            reopened = detector.check_activity(serial, target="FARM_SEARCH_BTN", threshold=0.8)
            if not reopened:
                print(f"[{serial}] Search panel didn't reopen. Using last mine.")
                mine_found = True
                break

        # Tap search (resource type already selected — game remembers)
        print(f"[{serial}] Search click {click_num}/{search_clicks}...")
        adb_helper.tap(serial, search_x, search_y)
        _human_delay(3)

        # Check if mine was found (search panel closed = mine found)
        detector._screen_cache = None
        panel_still_open = detector.check_activity(serial, target="FARM_SEARCH_BTN", threshold=0.8)

        if panel_still_open:
            print(f"[{serial}] [NO MINE] No {r_type} mine nearby on click {click_num}.")
            break

        mine_found = True

    # ── Fallback: try other resource types if primary not found ──
    if not mine_found:
        print(f"[{serial}] [NO MINE] Trying other resource types...")
        for alt_type in ALL_TYPES:
            if alt_type == r_type:
                continue

            alt_res_x, alt_res_y = resource_taps[alt_type]
            alt_search_x, alt_search_y = search_taps[alt_type]

            print(f"[{serial}]   Trying {alt_type.upper()}...")
            adb_helper.tap(serial, alt_res_x, alt_res_y)
            _human_delay(1)
            adb_helper.tap(serial, alt_search_x, alt_search_y)
            _human_delay(3)

            detector._screen_cache = None
            still_open = detector.check_activity(serial, target="FARM_SEARCH_BTN", threshold=0.8)
            if not still_open:
                print(f"[{serial}]   {alt_type.upper()} mine found! Switching resource type.")
                r_type = alt_type
                mine_found = True
                break
            else:
                print(f"[{serial}]   No {alt_type.upper()} mine either.")

    if not mine_found:
        print(f"[{serial}] [NO MINE] All resource types exhausted. No mines available!")
        adb_helper.press_back(serial)
        _human_delay(1)
        return None

    print(f"[{serial}] Mine found ({r_type.upper()})! Map panned to resource node.")

    # ── Check if mine is occupied ──
    view_btn = _detect_with_retry(serial, detector, "RSS_VIEW", threshold=0.8, attempts=2, delay=0.5)
    if view_btn:
        print(f"[{serial}] [OCCUPIED] Mine already has our legion (View detected). Dismissing...")
        adb_helper.tap(serial, 50, 500)
        _human_delay(1.5)
        return "occupied"

    return r_type


def _search_mine_manual(
    serial: str,
    detector: GameStateDetector,
    r_type: str,
) -> str | None:
    """Search for a mine by using the first search result as an anchor, then scanning nearby tiles.

    Anti-detect rule:
    - The first mine found by Search is NOT gathered.
    - That mine is only used as an anchor for local spiral scanning.
    """
    RESOURCE_TAPS = {
        "gold": (320, 485), "wood": (475, 485),
        "stone": (640, 485), "mana": (795, 485),
    }
    SEARCH_TAPS = {
        "gold": (320, 400), "wood": (475, 400),
        "stone": (640, 400), "mana": (795, 400),
    }
    icon_targets = {
        "gold": "MANUAL_RSS_GOLD",
        "wood": "MANUAL_RSS_WOOD",
        "stone": "MANUAL_RSS_ORE",
        "mana": "MANUAL_RSS_MANA",
    }

    anchor_result = _search_mine_via_menu(
        serial,
        detector,
        r_type,
        RESOURCE_TAPS,
        SEARCH_TAPS,
        search_clicks=1,
    )
    if anchor_result in {None, "occupied"}:
        return anchor_result

    print(f"[{serial}] [MANUAL SEARCH] Anchor mine found ({anchor_result.upper()}). Skipping first mine by design.")
    print(f"[{serial}] [MANUAL SEARCH] Dismissing anchor mine popup before manual scan...")
    adb_helper.tap(serial, 480, 270)
    _human_delay(0.8)

    plan = _build_outward_ring_scan_plan()
    blocked_centers: list[tuple[int, int]] = []

    for step_idx, (direction_name, segment, grid_xy) in enumerate(plan, start=1):
        print(
            f"[{serial}] [MANUAL SEARCH] Swipe {step_idx}/{len(plan)} "
            f"dir={direction_name} grid={grid_xy}"
        )
        adb_helper.swipe(
            serial,
            segment[0][0], segment[0][1],
            segment[1][0], segment[1][1],
            1200,
        )
        _human_delay(_MANUAL_SCAN_SETTLE_S)

        icon_matches = detector.find_all_icon_matches(serial, target=icon_targets[r_type], threshold=0.75)
        if not icon_matches:
            continue

        for icon_x, icon_y in icon_matches:
            candidate_center = (icon_x, icon_y)
            if _is_near_any_point(candidate_center, blocked_centers):
                continue

            print(f"[{serial}] [MANUAL SEARCH] Found nearby {r_type.upper()} icon at ({icon_x}, {icon_y}).")
            adb_helper.tap(serial, icon_x, icon_y)
            _human_delay(1.0)

            gather_btn = _detect_with_retry(serial, detector, "RSS_GATHER", threshold=0.8, attempts=2, delay=0.8)
            if gather_btn:
                print(f"[{serial}] [MANUAL SEARCH] Gather available on scanned mine.")
                return r_type

            recall_btn = _detect_with_retry(serial, detector, "RSS_RECALL", threshold=0.8, attempts=1, delay=0.0)
            attack_btn = _detect_with_retry(serial, detector, "RSS_ATTACK", threshold=0.8, attempts=1, delay=0.0)
            view_btn = _detect_with_retry(serial, detector, "RSS_VIEW", threshold=0.8, attempts=1, delay=0.0)
            if recall_btn or attack_btn or view_btn:
                print(f"[{serial}] [MANUAL SEARCH] Scanned mine is occupied/invalid. Continuing scan on next swipe.")
                blocked_centers.append(candidate_center)
                _human_delay(1.0)
                continue

            current_state = detector.check_state(serial)
            if current_state != "IN-GAME LOBBY (OUT_CITY)":
                print(f"[{serial}] [MANUAL SEARCH] Unexpected state {current_state}. Recovering with BACK.")
                adb_helper.press_back(serial)
                _human_delay(1.0)
            blocked_centers.append(candidate_center)

    print(f"[{serial}] [MANUAL SEARCH] No valid nearby mine found after local scan.")
    return None

def go_to_rss_center_farm(serial: str, detector: GameStateDetector) -> dict:
    """
    Farms Alliance Resource Center with Dynamic Cooldown.

    TH1 (Build state): RSS Center needs building.
      - Check builder count (max 36 clan-wide)
      - If full (36): fail + CD = building_time (retry after build to gather)
      - If not full: send troops to build + CD = building_time + 12h + buffer
    TH2 (Gather state): RSS Center already built.
      - Dispatch legion + CD = remaining_time + buffer
    """
    RSS_12H_SEC = 43200
    EDGE_RECHECK_SEC = 7200  # 2 hours for "no actionable button" edge case
    BUFFER_SEC = 300  # 5 minutes
    ROI_BUILDER_COUNT = (750, 265, 800, 290)
    ROI_BUILDING_TIME = (725, 350, 800, 370)
    ROI_REMAINING_TIME = (655, 222, 725, 240)

    print(f"[{serial}] Starting Alliance Resource Center Farming...")
    result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)")
    if not _is_ok(result):
        print(f"[{serial}] [FAILED] Could not reach OUT_CITY lobby.")
        return _bubble(result, "NAV_LOBBY_UNREACHABLE: Could not reach OUT_CITY")

    print(f"[{serial}] Tapping Markers Icon (180, 16)...")
    adb_helper.tap(serial, 180, 16)
    #_human_delay(2)

    # Wait for Markers Menu
    state = wait_for_state(serial, detector, ["MARKERS_MENU"], timeout_sec=10, check_mode="construction")
    if state != "MARKERS_MENU":
        print(f"[{serial}] [FAILED] Could not open Markers Menu.")
        return _fail("NAV_TARGET_NOT_REACHED: Could not open Markers Menu")

    # Check for Resource Center marker (may need scroll if list is long)
    print(f"[{serial}] Searching for Resource Center marker...")
    rss_marker = None
    for attempt in range(5):
        detector._screen_cache = None  # Fresh capture each attempt
        rss_marker = detector.check_activity(serial, target="RSS_CENTER_MARKER", threshold=0.8)
        if rss_marker:
            break
        # Scroll down to reveal hidden markers
        print(f"[{serial}] Marker not visible, scrolling down... (attempt {attempt + 1}/5)")
        adb_helper.swipe(serial, 480, 400, 480, 250, 300)
        #_human_delay(2)

    if not rss_marker:
        print(f"[{serial}] Resource Center not found in markers! Aborting.")
        adb_helper.press_back(serial)
        #_human_delay(2)
        return _fail("TEMPLATE_NO_MATCH: Resource Center marker not found")

    # Navigate to RSS Center on map
    center_x, center_y = rss_marker[1], rss_marker[2]
    go_x, go_y = center_x + 570, center_y
    print(f"[{serial}] Found RSS Center. Tapping GO ({go_x}, {go_y})...")
    adb_helper.tap(serial, go_x, go_y)
    _human_delay(5)

    print(f"[{serial}] Tapping RSS Center on map (479, 254)...")
    adb_helper.tap(serial, 479, 254)
    _human_delay(2)

    # --- Detect state: View / Gather(Build) ---
    print(f"[{serial}] Checking RSS Center state...")
    view_state = _detect_with_retry(serial, detector, "RSS_VIEW", threshold=0.8, attempts=3, delay=1)
    if view_state:
        print(f"[{serial}] 'View' detected. Legion already farming. Aborting.")
        adb_helper.tap(serial, 50, 500)
        _human_delay(2)
        return {"ok": False}

    gather_state = _detect_with_retry(serial, detector, "RSS_GATHER", threshold=0.8, attempts=3, delay=1)
    build_state = None
    if not gather_state:
        # RSS Center may be in Build state — button shows as "Build" instead of "Gather"
        build_state = _detect_with_retry(serial, detector, "RSS_BUILD", threshold=0.8, attempts=3, delay=1)

    if not gather_state and not build_state:
        print(f"[{serial}] Neither Gather nor Build button found. Aborting.")
        save_unknown_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "_unknown_captures")
        os.makedirs(save_unknown_dir, exist_ok=True)
        detector._screen_cache = None
        frame = detector.get_frame(serial)
        if frame is not None:
            debug_path = os.path.join(save_unknown_dir, f"rss_center_no_action_{serial}_{int(time.time())}.png")
            cv2.imwrite(debug_path, frame)
            print(f"[{serial}] [DEBUG] Saved no-action RSS Center screen: {debug_path}")
        adb_helper.tap(serial, 50, 500)
        _human_delay(2)
        print(f"[{serial}] [EDGE] No actionable RSS Center button detected. Rechecking later.")
        return _fail("TEMPLATE_NO_MATCH: RSS Center button not found", dynamic_cooldown_sec=EDGE_RECHECK_SEC)

    actionable_state = gather_state or build_state
    g_x, g_y = actionable_state[1], actionable_state[2]

    # --- OCR all info BEFORE tapping (screen changes after tap) ---
    print(f"[{serial}] Reading OCR data from info panel...")

    building_time_text = ocr_region_text(serial, detector, ROI_BUILDING_TIME)
    building_sec = parse_game_timer(building_time_text) if building_time_text else 0

    if building_sec > 0:
        # TH1: Build state — also read builder count
        builder_text = ocr_region_text(serial, detector, ROI_BUILDER_COUNT)
        builder_count = parse_builder_count(builder_text)
        print(f"[{serial}] [TH1] Building time: {building_time_text} ({building_sec}s), Builders: {builder_count}/36")
    else:
        # TH2: Gather state — read remaining time
        remaining_text = ocr_region_with_retry(
            serial, detector, ROI_REMAINING_TIME,
            attempts=5, style="outline",
            validator=lambda t: parse_game_timer(t) > 0
        )
        remaining_sec = parse_game_timer(remaining_text) if remaining_text else 0
        print(f"[{serial}] [TH2] Remaining time: {remaining_text} ({remaining_sec}s)")

    # --- Now tap the button ---
    print(f"[{serial}] Tapping Gather/Build ({g_x}, {g_y})...")
    adb_helper.tap(serial, g_x, g_y)
    _human_delay(3)

    # --- Branch on TH1 vs TH2 ---
    if building_sec > 0:
        # ========== TH1: Build State ==========
        if builder_count >= 36:
            print(f"[{serial}] [TH1] Builders FULL (36/36). Setting CD = building_time to retry gather.")
            adb_helper.press_back(serial)
            _human_delay(1.0)
            return {"ok": False, "dynamic_cooldown_sec": building_sec + BUFFER_SEC}

        # Not full — send troops to build (Create Legion -> Dispatch)
        print(f"[{serial}] [TH1] Sending troops to build RSS Center...")

        # RSS Center panel may show a list-style "Create Legion" button first
        rss_create = _detect_with_retry(serial, detector, "CREATE_LEGION_RSS", threshold=0.8, attempts=2, delay=1)
        if rss_create:
            _, rx, ry = rss_create
            print(f"[{serial}] [TH1] RSS Create Legion found at ({rx}, {ry}). Tapping...")
            adb_helper.tap(serial, rx, ry)
            _human_delay(2.0)

        create_result = _detect_with_retry(serial, detector, "CREATE_LEGION", threshold=0.8, attempts=3, delay=1)
        if not create_result:
            print(f"[{serial}] [TH1] CREATE_LEGION not found. Aborting.")
            adb_helper.press_back(serial)
            return _fail("TEMPLATE_NO_MATCH: CREATE_LEGION not found after Build tap")

        _, cl_x, cl_y = create_result
        print(f"[{serial}] [TH1] Tapping Create Legion at ({cl_x}, {cl_y})...")
        adb_helper.tap(serial, cl_x, cl_y)
        _human_delay(2.0)

        print(f"[{serial}] Setting up legion (755, 115)...")
        adb_helper.tap(serial, 755, 115)
        _human_delay(2.0)

        LEGION_5_TAP = (865, 90)
        print(f"[{serial}] Selecting Legion Preset #5 at {LEGION_5_TAP}...")
        adb_helper.tap(serial, LEGION_5_TAP[0], LEGION_5_TAP[1])
        _human_delay(1.0)

        dispatch_loc = (850, 480)
        print(f"[{serial}] Tapping Dispatch {dispatch_loc}...")
        adb_helper.tap(serial, dispatch_loc[0], dispatch_loc[1])
        _human_delay(3.0)

        dynamic_cd = building_sec + RSS_12H_SEC + BUFFER_SEC
        print(f"[{serial}] [TH1] Build dispatched. Dynamic CD = {building_sec}s + 12h + 5min = {dynamic_cd}s")
        return {"ok": True, "dynamic_cooldown_sec": dynamic_cd}

    else:
        # ========== TH2: Gather State (already built) ==========
        print(f"[{serial}] [TH2] Dispatching gather legion...")

        # RSS Center panel may show a list-style "Create Legion" button first
        rss_create = _detect_with_retry(serial, detector, "CREATE_LEGION_RSS", threshold=0.8, attempts=2, delay=1)
        if rss_create:
            _, rx, ry = rss_create
            print(f"[{serial}] [TH2] RSS Create Legion found at ({rx}, {ry}). Tapping...")
            adb_helper.tap(serial, rx, ry)
            _human_delay(2.0)

        create_result = _detect_with_retry(serial, detector, "CREATE_LEGION", threshold=0.8, attempts=3, delay=1)
        if not create_result:
            print(f"[{serial}] [TH2] CREATE_LEGION not found. Aborting.")
            adb_helper.press_back(serial)
            return _fail("TEMPLATE_NO_MATCH: CREATE_LEGION not found after Gather tap")

        _, cl_x, cl_y = create_result
        print(f"[{serial}] [TH2] Tapping Create Legion at ({cl_x}, {cl_y})...")
        adb_helper.tap(serial, cl_x, cl_y)
        _human_delay(2.0)

        print(f"[{serial}] Setting up legion (755, 115)...")
        adb_helper.tap(serial, 755, 115)
        _human_delay(2.0)

        LEGION_5_TAP = (865, 90)
        print(f"[{serial}] Selecting Legion Preset #5 at {LEGION_5_TAP}...")
        adb_helper.tap(serial, LEGION_5_TAP[0], LEGION_5_TAP[1])
        _human_delay(1.0)

        dispatch_loc = (850, 480)
        print(f"[{serial}] Tapping Dispatch {dispatch_loc}...")
        adb_helper.tap(serial, dispatch_loc[0], dispatch_loc[1])
        _human_delay(3.0)

        if remaining_sec > 0:
            dynamic_cd = remaining_sec + BUFFER_SEC
            print(f"[{serial}] [TH2] Dispatched. Dynamic CD = {remaining_sec}s + 5min = {dynamic_cd}s")
            return {"ok": True, "dynamic_cooldown_sec": dynamic_cd}

        # OCR fail — fallback to static
        print(f"[{serial}] [TH2] OCR remaining time failed. Using static fallback.")
        return _ok()

def go_to_market(serial: str, detector: GameStateDetector) -> dict:
    """Navigates to Market."""
    print(f"[{serial}] Navigating to Market...")
    adb_helper.tap(serial, 639, 232)
    _human_delay(2)
    adb_helper.tap(serial, 545, 267)
    _human_delay(3)
    return _ok()

def go_to_alliance(serial: str, detector: GameStateDetector) -> dict:
    """
    Navigates to the Alliance menu from Lobby IN_CITY.
    """
    print(f"[{serial}] Navigating to Alliance Menu...")
    
    lobby_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not _is_ok(lobby_result):
        print(f"[{serial}] [FAILED] Could not reach IN_CITY lobby.")
        return _bubble(lobby_result, "NAV_LOBBY_UNREACHABLE: Could not reach IN_CITY lobby")
        
    menu_result = ensure_lobby_menu_open(serial, detector)
    if not _is_ok(menu_result):
        print(f"[{serial}] [FAILED] Could not expand lobby menu.")
        return _bubble(menu_result, "NAV_MENU_OPEN_FAILED: Could not expand lobby menu")
        
    print(f"[{serial}] Tapping Alliance Icon...")
    adb_helper.tap(serial, 719, 503)
    _human_delay(3)
    
    state = wait_for_state(serial, detector, ["ALLIANCE_MENU"], timeout_sec=10, check_mode="construction")
    if state != "ALLIANCE_MENU":
        print(f"[{serial}] [FAILED] Did not reach ALLIANCE_MENU.")
        return _fail("NAV_TARGET_NOT_REACHED: Did not reach ALLIANCE_MENU")
        
    print(f"[{serial}] -> ALLIANCE_MENU reached successfully.")
    return _ok()


def donate_alliance_technology(serial: str, detector: GameStateDetector) -> dict:
    """
    Alliance Technology Donate Workflow:
    1. Navigate to Alliance Menu
    2. Tap Technology tab (530, 465)
    3. Detect blue DONATE button (free, not gems)
    4. Burst-click donate 10-12 times with human-like timing
    5. Return _ok() regardless of donate availability

    Returns _fail() only if Alliance navigation fails.
    """
    print(f"[{serial}] === DONATE ALLIANCE TECHNOLOGY ===")

    # ── Phase 1: Navigate to Alliance ──
    result = go_to_alliance(serial, detector)
    if not _is_ok(result):
        return _bubble(result, "NAV_TARGET_NOT_REACHED: Could not open Alliance Menu")

    # ── Phase 2: Tap Technology tab ──
    print(f"[{serial}] Tapping Technology tab (530, 465)...")
    adb_helper.tap(serial, 530, 465)
    _human_delay(2.0)

    # ── Phase 3: Detect blue DONATE button ──
    # Retry detection — uses check_alliance() since template is in alliance_configs
    donate_match = None
    for attempt in range(3):
        detector._screen_cache = None
        donate_match = detector.check_alliance(serial, target="ALLIANCE_DONATE_BTN", threshold=0.8)
        if donate_match:
            break
        if attempt < 2:
            print(f"[{serial}] ALLIANCE_DONATE_BTN not found, retrying ({attempt + 1}/3)...")
            _human_delay(1.5)

    if not donate_match:
        print(f"[{serial}] No Donate button found — already donated or tech completed.")
        cleanup_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
        if not _is_ok(cleanup_result):
            return _bubble(cleanup_result, "NAV_LOBBY_UNREACHABLE: Could not close Alliance Donate screen")
        return _ok()

    _, dx, dy = donate_match
    print(f"[{serial}] Donate button found at ({dx}, {dy}). Starting burst clicks...")

    # ── Phase 4: Human-like burst clicking ──
    # Total 10-12 clicks, split into bursts of 2-3 with random pauses between
    total_clicks = random.randint(10, 12)
    remaining = total_clicks

    while remaining > 0:
        burst = min(random.randint(2, 3), remaining)
        for _ in range(burst):
            # Jitter coordinates ±3px to avoid bot detection
            jx = dx + random.randint(-3, 3)
            jy = dy + random.randint(-3, 3)
            adb_helper.tap(serial, jx, jy)
            _human_delay(0.1, variance=0.5)
        remaining -= burst
        print(f"[{serial}] Burst done ({total_clicks - remaining}/{total_clicks} clicks)")
        if remaining > 0:
            _human_delay(0.8)

    print(f"[{serial}] Donate complete — {total_clicks} clicks sent.")

    # ── Phase 5: Cleanup ──
    cleanup_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not _is_ok(cleanup_result):
        return _bubble(cleanup_result, "NAV_LOBBY_UNREACHABLE: Could not close Alliance Donate screen")
    return _ok()


def claim_scout_sentry_post(serial: str, detector: GameStateDetector) -> dict:
    """
    Claim rewards from Scout Sentry Post:
    1. Navigate via _go_to_construction_v2 (SCOUT_SENTRY_POST, feature=scout)
    2. Outer loop x3:
       a. Inner loop: detect QUICK HELP → tap → 5s wait → tap dismiss → repeat
       b. Detect CLAIM ALL → tap → 5s wait → tap (50,500) dismiss
       c. If neither button found → break (all done)
    3. Return _ok()
    """
    print(f"[{serial}] === CLAIM SCOUT SENTRY POST ===")

    # ── Phase 1: Navigate to Scout Sentry Post ──
    result = _go_to_construction_v2(serial, detector, "SCOUT_SENTRY_POST", feature="scout")
    if not _is_ok(result):
        return _bubble(result, "NAV_TARGET_NOT_REACHED: Could not open Scout Sentry Post")

    _human_delay(1.5)

    # ── Phase 2: Main loop x3 (Quick Help → Claim All per round) ──
    OUTER_ROUNDS = 3
    MAX_QUICK_HELP_PER_ROUND = 10  # Safety cap: stamina may run out silently
    total_helps = 0
    total_claims = 0

    for round_num in range(1, OUTER_ROUNDS + 1):
        print(f"\n[{serial}] --- Round {round_num}/{OUTER_ROUNDS} ---")
        round_had_action = False

        # ── 2a: Loop Quick Help clicks ──
        round_helps = 0
        while round_helps < MAX_QUICK_HELP_PER_ROUND:
            detector._screen_cache = None
            qh_match = detector.check_activity(serial, target="SCOUT_QUICK_HELP_BTN", threshold=0.8)

            if not qh_match:
                print(f"[{serial}] No more QUICK HELP buttons (round {round_num}: {round_helps} helps).")
                break

            _, qx, qy = qh_match
            print(f"[{serial}] Quick Help candidate #{round_helps + 1} at ({qx}, {qy}). Tapping...")
            adb_helper.tap(serial, qx, qy)

            print(f"[{serial}] Dismissing Quick Help popup immediately at ({qx}, {qy})...")
            adb_helper.tap(serial, qx, qy)
            _human_delay(5.0)

            print(f"[{serial}] Dismissing Quick Help popup again at ({qx}, {qy})...")
            adb_helper.tap(serial, qx, qy)
            _human_delay(2.0)

            detector._screen_cache = None
            qh_after = detector.check_activity(serial, target="SCOUT_QUICK_HELP_BTN", threshold=0.8)
            if qh_after:
                print(
                    f"[{serial}] QUICK HELP still visible after tap. "
                    "Treating as no-op (likely out of stamina) and stopping help loop."
                )
                break

            round_helps += 1
            round_had_action = True
            print(f"[{serial}] Quick Help #{round_helps} confirmed by button disappearance.")

        total_helps += round_helps

        # ── 2b: Detect and tap CLAIM ALL ──
        detector._screen_cache = None
        claim_match = _detect_with_retry(serial, detector, "SCOUT_CLAIM_ALL_BTN", threshold=0.8, attempts=3, delay=1.5)

        if claim_match:
            _, cx, cy = claim_match
            round_had_action = True
            total_claims += 1
            print(f"[{serial}] CLAIM ALL found at ({cx}, {cy}). Tapping...")
            adb_helper.tap(serial, cx, cy)

            _human_delay(10.0)

            # Dismiss claim result screen
            print(f"[{serial}] Dismissing claim result (50, 500)...")
            adb_helper.tap(serial, 50, 500)
            _human_delay(2.0)
        else:
            print(f"[{serial}] No CLAIM ALL button found this round.")

        # ── 2c: Early exit if nothing happened this round ──
        if not round_had_action:
            print(f"[{serial}] No buttons found in round {round_num} — all rewards claimed.")
            break

    print(f"\n[{serial}] Scout Sentry Post done — {total_helps} help(s), {total_claims} claim(s) across {round_num} round(s).")

    # ── Phase 3: Cleanup ──
    cleanup_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not _is_ok(cleanup_result):
        return _bubble(cleanup_result, "NAV_LOBBY_UNREACHABLE: Could not close Scout Sentry Post screen")
    return _ok()

def go_to_alliance_war_loop(serial: str, detector: GameStateDetector, loop_count: int = 1) -> dict:
    """
    Alliance War Rally Loop.
    """
    print(f"[{serial}] Starting Alliance War Rally Loop (Count: {loop_count})...")
    
    for loop in range(loop_count):
        print(f"\n[{serial}] --- Rally Loop #{loop+1}/{loop_count} ---")
            
        result = go_to_alliance(serial, detector)
        if not _is_ok(result):
            print(f"[{serial}] [FAILED] Could not open Alliance Menu.")
            return _bubble(result, "NAV_TARGET_NOT_REACHED: Could not open Alliance Menu")
            
        # 3. Go to War
        print(f"[{serial}] Searching for War tab...")
        war_tab_found = False
        for attempt in range(3):
            war_info = detector.check_alliance(serial, target="ALLIANCE_WAR", threshold=0.8)
            if war_info:
                name, w_x, w_y = war_info
                print(f"[{serial}] Found War Tab at ({w_x}, {w_y}). Tapping...")
                adb_helper.tap(serial, w_x, w_y)
                war_tab_found = True
                break
            _human_delay(2)
            
        if not war_tab_found:
            print(f"[{serial}] [WARNING] War tab not found. Aborting this loop.")
            continue
            
        _human_delay(4) # Wait for War screen to load
        
        # 4. Check state in war if have rally
        print(f"[{serial}] Scanning and waiting for active rallies...")
        
        rally_available = False
        for attempt in range(100):
            # Check for barriers to joining
            no_rally = detector.check_alliance(serial, target="NO_RALLY", threshold=0.8)
            already_join = detector.check_alliance(serial, target="ALREADY_JOIN_RALLY", threshold=0.8)
            
            # If neither the 'No Rally' text nor the 'Joined' tag are found, we have a fresh rally!
            if not no_rally and not already_join:
                print(f"[{serial}] Active joinable rally detected!")
                rally_available = True
                break
                
            if attempt % 6 == 0:
                print(f"[{serial}] Waiting for new rallies to appear... ({attempt}/100)")
            _human_delay(5)
            
        if not rally_available:
            print(f"[{serial}] Timeout: No active rallies found after waiting. Returning to lobby.")
            continue
            
        # 5. Join Rally
        print(f"[{serial}] Tapping Join Rally at (659, 211)...")
        adb_helper.tap(serial, 659, 211)
        _human_delay(4)
        
        # 6. Deploy legions (use legion_1)
        # Check if we can create a legion with retries
        print(f"[{serial}] Checking if we can deploy legions (looking for CREATE_LEGION)...")
        result = None
        for attempt in range(3):
            result = detector.check_activity(serial, target="CREATE_LEGION", threshold=0.8)
            if result:
                break
            print(f"[{serial}] CREATE_LEGION not found, retrying ({attempt + 1}/3)...")
            _human_delay(2)
            
        if not result:
            print(f"[{serial}] Legions are FULL, node is occupied, or no AP! Returning to Lobby.")
            continue
            
        print(f"[{serial}] Found CREATE_LEGION -> Deploying forces...")
        
        # Create legion & Dispatch
        print(f"[{serial}] Tapping Create Legion Button (755, 115)...")
        adb_helper.tap(serial, 755, 115)
        _human_delay(4)
        
        adb_helper.tap(serial, 848, 154)
        _human_delay(2)
        adb_helper.tap(serial, 852, 223)
        _human_delay(2)
        adb_helper.tap(serial, 715, 300)
        _human_delay(2)
        adb_helper.tap(serial, 723, 448)
        _human_delay(2)
        adb_helper.tap(serial, 852, 453)
        _human_delay(2)
        
        dispatch_loc = (850, 480) 
        print(f"[{serial}] Tapping March/Dispatch {dispatch_loc}...")
        adb_helper.tap(serial, dispatch_loc[0], dispatch_loc[1])
        
        # Game usually puts us back to map or lobby after dispatching. Wait for transition.
        _human_delay(7)
        
        # 7. Return to IN_CITY (handled by start of next loop)
        print(f"[{serial}] Rally join complete for this loop.")

    print(f"[{serial}] Finished all {loop_count} Rally loops.")
    return _ok()

def train_troops(serial: str, detector: GameStateDetector, training_list: list = None) -> dict:
    """
    Trains troops at the specified training houses and tiers.
    """
    def shuffer(items: list) -> list:
        shuffled = list(items)
        random.shuffle(shuffled)
        return shuffled

    HOUSE_TRAIN_BTN_THRESHOLD = 0.78
    HOUSE_TRAIN_BTN_SETTLE_SEC = 1.2

    def _wait_for_house_train_button(
        target_name: str,
        attempts: int = 2,
        delay_sec: float = HOUSE_TRAIN_BTN_SETTLE_SEC,
        threshold: float = HOUSE_TRAIN_BTN_THRESHOLD,
    ):
        match = None
        for attempt in range(attempts):
            detector._cache.invalidate()
            match = detector.check_activity(serial, target=target_name, threshold=threshold)
            if match:
                name, mx, my = match
                print(
                    f"[{serial}] {target_name} detected "
                    f"at ({mx}, {my}) on attempt {attempt + 1}/{attempts}."
                )
                return match
            if attempt < attempts - 1:
                print(
                    f"[{serial}] {target_name} not visible yet at threshold {threshold:.2f}. "
                    f"Waiting for UI settle ({attempt + 1}/{attempts})..."
                )
                _human_delay(delay_sec)
        return None

    if training_list is None:
        training_list = [("infantry", 1)]
    else:
        training_list = list(training_list)

    training_list = shuffer(training_list)
        
    print(f"[{serial}] Starting Train Troops workflow for {len(training_list)} houses: {training_list}")
    
    HOUSE_TAPS = {
        "archer": (465, 256),
        "cavalry": (302, 369),
        "infantry": (379, 318),
        "siege": (195, 290),
        "mage": (278, 247)
    }

    HOUSE_TRAIN_BUTTONS = {
        "archer": "ARCHER_TRAIN_BTN",
        "cavalry": "CAVALRY_TRAIN_BTN",
        "infantry": "INFANTRY_TRAIN_BTN",
        "siege": "SIEGE_TRAIN_BTN",
        "mage": "MAGE_TRAIN_BTN",
    }
    
    TIER_TAPS = {
        1: (121, 460),
        2: (198, 460),
        3: (275, 460),
        4: (352, 460),
        5: (429, 460)
    }
    
    TRAIN_BTN_COORD = (792, 466) 
    
    # 1. Back to IN_CITY once at the start
    lobby_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not _is_ok(lobby_result):
        print(f"[{serial}] [FAILED] Could not reach IN_CITY lobby.")
        return _bubble(lobby_result, "NAV_LOBBY_UNREACHABLE: Could not reach IN_CITY lobby")

    # Recenter the city camera before touching any troop buildings.
    reset_position(serial)
        
    all_success = True
        
    for house_type, tier in training_list:
        h_type = house_type.lower()
        if str(tier).lower() == "default":
            tier = "default"
            
        if h_type == "siege" and tier in [1, 2]:
            print(f"[{serial}] [WARNING] Validation: Siege only trains tier 3-5. Changing Tier {tier} to Tier 3.")
            tier = 3
            
        print(f"\n[{serial}] --- Processing House: {h_type.upper()} | Tier: {tier} ---")
        
        if h_type not in HOUSE_TAPS:
            print(f"[{serial}] [ERROR] Unknown house_type: {house_type}. Skipping.")
            all_success = False
            continue
            
        if tier != "default" and tier not in TIER_TAPS:
            print(f"[{serial}] [ERROR] Unknown tier: {tier}. Skipping.")
            all_success = False
            continue
            
        # Ensure we are in the lobby before tapping the next house
        current_state = detector.check_state(serial)
        if current_state != "IN-GAME LOBBY (IN_CITY)":
            retry_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
            if not _is_ok(retry_result):
                 print(f"[{serial}] [FAILED] Not in IN_CITY lobby. Aborting current training.")
                 all_success = False
                 continue

        # 2. Tap training house
        hx, hy = HOUSE_TAPS[h_type]
        house_train_target = HOUSE_TRAIN_BUTTONS[h_type]
        print(f"[{serial}] Tapping {h_type.upper()} House at ({hx}, {hy})...")
        adb_helper.tap(serial, hx, hy)
        _human_delay(HOUSE_TRAIN_BTN_SETTLE_SEC)

        # Verify the correct troop panel/button is visible after tapping the house.
        troop_panel_match = _wait_for_house_train_button(house_train_target, attempts=2)
        if troop_panel_match:
            print(f"[{serial}] {house_train_target} detected after first tap.")
        else:
            print(f"[{serial}] {house_train_target} not detected. Re-tapping house to claim/reopen training panel...")
            adb_helper.tap(serial, hx, hy)
            _human_delay(1.5)
            troop_panel_match = _wait_for_house_train_button(house_train_target, attempts=2)
            if troop_panel_match:
                print(f"[{serial}] {house_train_target} detected after re-tap.")
            else:
                print(f"[{serial}] [FAILED] {house_train_target} not detected after claim/reopen sequence.")
                all_success = False
                cleanup_state = detector.check_construction(serial)
                if cleanup_state == "TRAIN_UNITS":
                    print(f"[{serial}] TRAIN_UNITS still open after failed troop panel detect. Pressing BACK to recover.")
                    adb_helper.press_back(serial)
                    _human_delay(1)
                elif cleanup_state:
                    print(f"[{serial}] Construction state '{cleanup_state}' still open after failed troop panel detect. Pressing BACK to recover.")
                    adb_helper.press_back(serial)
                    _human_delay(1)
                else:
                    print(f"[{serial}] No construction screen detected after failed troop panel detect. Skipping BACK to avoid exiting game.")
                continue

        # 3. Open the training panel once the correct troop type button is confirmed.
        _, icon_x, icon_y = troop_panel_match
        print(f"[{serial}] Tapping detected {house_train_target} at ({icon_x}, {icon_y}) to open training panel...")
        adb_helper.tap(serial, icon_x, icon_y)
        _human_delay(2)
        
        # 4. Wait for TRAIN_UNITS construction state
        state = wait_for_state(serial, detector, ["TRAIN_UNITS"], timeout_sec=10, check_mode="construction")
        if state != "TRAIN_UNITS":
            print(f"[{serial}] [FAILED] Did not reach TRAIN_UNITS screen. Current state: {state}")
            adb_helper.press_back(serial)
            all_success = False
            continue
            
        print(f"[{serial}] -> Reached TRAIN_UNITS screen.")
        
        # 5. Check if we can train (look for BTN_TRAIN)
        print(f"[{serial}] Checking if already training (waiting for BTN_TRAIN)...")
        btn_train_state = detector.check_activity(serial, target="BTN_TRAIN", threshold=0.8)
        
        if btn_train_state:
            print(f"[{serial}] BTN_TRAIN found -> Troops are already training. Moving to next house.")
            adb_helper.press_back(serial)
            _human_delay(2)
            continue # Try next house
            
        # Not training! Begin training
        print(f"[{serial}] House is idle! Preparing to train Tier {tier}...")
        
        if tier == "default":
            print(f"[{serial}] Default training mode selected. Skipping tier selection.")
            train_icon = detector.check_activity(serial, target="TRAINING_ICON", threshold=0.8)
            if train_icon:
                _, tx, ty = train_icon
                print(f"[{serial}] Tapping Train Button at coordinate ({tx}, {ty})...")
                adb_helper.tap(serial, tx, ty)
                _human_delay(3)
                print(f"[{serial}] Training started successfully for Default Tier {h_type.upper()}.")
            else:
                print(f"[{serial}] [FAILED] Could not find Train Button for Default Tier.")
                all_success = False
        else:
            current_tier = int(tier)
            trained = False
            
            while current_tier >= 1:
                # Tap Tier
                tx, ty = TIER_TAPS[current_tier]
                print(f"[{serial}] Tapping Tier {current_tier} selector at ({tx}, {ty})...")
                adb_helper.tap(serial, tx, ty)
                _human_delay(2)
                
                # Check for train button
                train_icon = detector.check_activity(serial, target="TRAINING_ICON", threshold=0.8)
                if train_icon:
                    _, btn_x, btn_y = train_icon
                    print(f"[{serial}] Tapping Train Button at coordinate ({btn_x}, {btn_y})...")
                    adb_helper.tap(serial, btn_x, btn_y)
                    _human_delay(3)
                    print(f"[{serial}] Training started successfully for Tier {current_tier} {h_type.upper()}.")
                    trained = True
                    break
                else:
                    print(f"[{serial}] Train button not found for Tier {current_tier} (might be locked). Falling back...")
                    current_tier -= 1
                    
            if not trained:
                print(f"[{serial}] [FAILED] Could not train any tier for {h_type.upper()}.")
                all_success = False
        
        # Back out of the building info if needed, or wait for animation
        # adb_helper.press_back(serial)
        _human_delay(2)

    print(f"[{serial}] Finished all training requests. Returning to lobby.")
    back_to_lobby(serial, detector)
    
    return _ok() if all_success else _fail("ACTION_VERIFY_FAILED: Some training houses failed")


def claim_alliance_resource(serial: str, detector: GameStateDetector) -> dict:
    """
    Claims Alliance Territory Resource.
    """
    print(f"[{serial}] Starting Claim Alliance Resource...")
    
    result = go_to_alliance(serial, detector)
    if not _is_ok(result):
        print(f"[{serial}] [FAILED] Could not reach Alliance Menu to claim resource.")
        return _bubble(result, "NAV_TARGET_NOT_REACHED: Could not reach Alliance Menu")
        
    print(f"[{serial}] Tapping Territory Icon...")
    adb_helper.tap(serial, 635, 350)
    _human_delay(3)
    
    print(f"[{serial}] Tapping Claim Button (826, 175)...")
    adb_helper.tap(serial, 826, 175)
    _human_delay(2)
    
    print(f"[{serial}] -> Claim Alliance Resource completed.")

    cleanup_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not _is_ok(cleanup_result):
        return _bubble(cleanup_result, "NAV_LOBBY_UNREACHABLE: Could not close Alliance Resource screen")
    return _ok()

def check_mail(serial: str, detector: GameStateDetector, mail_type: str = "all") -> dict:
    """
    Checks and claims mail in the game.
    mail_type can be 'events', 'system', 'alliance', or 'all' (default).
    """
    valid_types = ["events", "system", "alliance", "all"]
    mail_type = mail_type.lower()
    if mail_type not in valid_types:
        print(f"[{serial}] [ERROR] Invalid mail_type '{mail_type}'. Use {valid_types}.")
        return _fail(f"CONFIG_INVALID_PARAM: Invalid mail_type '{mail_type}'")
        
    print(f"[{serial}] Starting Check Mail ({mail_type})...")

    # 1. Back to lobby
    lobby_result = back_to_lobby(serial, detector)
    if not _is_ok(lobby_result):
        print(f"[{serial}] [FAILED] Could not reach lobby.")
        return _bubble(lobby_result, "NAV_LOBBY_UNREACHABLE: Could not reach lobby")
        
    # 2. Tap mail icon
    print(f"[{serial}] Tapping Mail Icon (926, 447)...")
    adb_helper.tap(serial, 926, 447)
    _human_delay(3)
    
    # 3. Verify MAIL_MENU
    state = wait_for_state(serial, detector, ["MAIL_MENU"], timeout_sec=10, check_mode="special")
    if state != "MAIL_MENU":
        print(f"[{serial}] [FAILED] Did not reach MAIL_MENU.")
        return _fail("NAV_TARGET_NOT_REACHED: Did not reach MAIL_MENU")
        
    print(f"[{serial}] -> MAIL_MENU reached successfully.")
    
    tabs = {
        "alliance": (370, 25),
        "events": (500, 25),
        "system": (615, 25)
    }
    mail_badge_rois = {
        "alliance": (410, 0, 440, 25),
        "events": (520, 0, 550, 25),
        "system": (645, 0, 675, 25),
    }
    claim_button = (100, 512)
    
    tabs_to_check = ["alliance", "events", "system"] if mail_type == "all" else [mail_type]

    def _normalize_roi(roi: tuple[int, int, int, int], width: int, height: int) -> tuple[int, int, int, int]:
        x1, y1, x2, y2 = roi
        left, right = sorted((int(x1), int(x2)))
        top, bottom = sorted((int(y1), int(y2)))
        return (
            max(0, min(width, left)),
            max(0, min(height, top)),
            max(0, min(width, right)),
            max(0, min(height, bottom)),
        )

    def _detect_mail_red_badge(frame: np.ndarray, roi: tuple[int, int, int, int]) -> dict:
        height, width = frame.shape[:2]
        x1, y1, x2, y2 = _normalize_roi(roi, width, height)
        crop = frame[y1:y2, x1:x2]
        result = {
            "roi": (x1, y1, x2, y2),
            "red_pixels": 0,
            "red_ratio": 0.0,
            "max_contour_area": 0.0,
            "has_badge": False,
        }
        if crop.size == 0:
            return result

        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        lower_red_1 = np.array([0, 140, 170], dtype=np.uint8)
        upper_red_1 = np.array([8, 255, 255], dtype=np.uint8)
        lower_red_2 = np.array([172, 140, 170], dtype=np.uint8)
        upper_red_2 = np.array([180, 255, 255], dtype=np.uint8)
        hsv_mask = cv2.inRange(hsv, lower_red_1, upper_red_1) | cv2.inRange(hsv, lower_red_2, upper_red_2)

        b, g, r = cv2.split(crop)
        b_i = b.astype(np.int16)
        g_i = g.astype(np.int16)
        r_i = r.astype(np.int16)
        dominant_red = (
            (r_i >= 190)
            & (g_i <= 95)
            & (b_i <= 95)
            & ((r_i - g_i) >= 100)
            & ((r_i - b_i) >= 100)
        ).astype(np.uint8) * 255
        mask = cv2.bitwise_and(hsv_mask, dominant_red)
        kernel = np.ones((2, 2), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        red_pixels = int(cv2.countNonZero(mask))
        area = max(1, mask.shape[0] * mask.shape[1])
        red_ratio = red_pixels / area
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        max_contour_area = max((float(cv2.contourArea(c)) for c in contours), default=0.0)
        has_badge = red_pixels >= 18 and red_ratio >= 0.05 and max_contour_area >= 6.0
        result.update(
            {
                "red_pixels": red_pixels,
                "red_ratio": red_ratio,
                "max_contour_area": max_contour_area,
                "has_badge": has_badge,
            }
        )
        return result

    def _filter_mail_tabs_by_badge(requested_tabs: list[str]) -> list[str]:
        detector._screen_cache = None
        frame = detector.screencap_memory(serial)
        if frame is None:
            print(f"[{serial}] [MAIL_BADGE] Could not capture badge frame. Falling back to requested tabs: {requested_tabs}")
            return requested_tabs

        filtered = []
        for tab in requested_tabs:
            badge = _detect_mail_red_badge(frame, mail_badge_rois[tab])
            status = "CHECK" if badge["has_badge"] else "SKIP"
            print(
                f"[{serial}] [MAIL_BADGE] {tab} roi={badge['roi']} "
                f"red_pixels={badge['red_pixels']} ratio={badge['red_ratio']:.2%} "
                f"contour={badge['max_contour_area']:.1f} -> {status}"
            )
            if badge["has_badge"]:
                filtered.append(tab)
        return filtered

    tabs_to_check = _filter_mail_tabs_by_badge(tabs_to_check)
    if not tabs_to_check:
        print(f"[{serial}] [MAIL_BADGE] No unread/reward mail badge detected. Skipping mail tab taps.")

    def _save_mail_confirm_debug(label: str) -> None:
        debug_dir = os.environ.get("MAIL_CONFIRM_DEBUG_DIR", "").strip()
        if not debug_dir:
            return
        try:
            os.makedirs(debug_dir, exist_ok=True)
            detector._screen_cache = None
            frame = detector.screencap_memory(serial)
            if frame is None:
                print(f"[{serial}] [MAIL_DEBUG] Could not capture {label}.")
                return
            safe_serial = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in serial)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            path = os.path.join(debug_dir, f"{ts}_{safe_serial}_{label}.png")
            cv2.imwrite(path, frame)
            print(f"[{serial}] [MAIL_DEBUG] Saved {label}: {path}")
        except Exception as exc:
            print(f"[{serial}] [MAIL_DEBUG] Failed to save {label}: {exc}")

    def _tap_mail_reward_confirm() -> bool:
        _human_delay(1.25)
        _save_mail_confirm_debug("after_claim_before_confirm_detect")
        confirm = _detect_with_retry(
            serial,
            detector,
            "MAIL_REWARD_CONFIRM_BTN",
            threshold=0.78,
            attempts=2,
            delay=0.30,
        )
        if not confirm:
            _save_mail_confirm_debug("confirm_not_found")
            print(f"[{serial}] No mail reward confirm popup detected.")
            return False

        _, cx, cy = confirm
        print(f"[{serial}] Mail reward confirm found at ({cx}, {cy}). Tapping...")
        adb_helper.tap(serial, cx, cy)
        _human_delay(0.8)
        return True
        
    for tab in tabs_to_check:
        print(f"[{serial}] Checking '{tab.capitalize()}' mail...")
        tab_x, tab_y = tabs[tab]
        adb_helper.tap(serial, tab_x, tab_y)
        _human_delay(2)
        print(f"[{serial}] Tapping Claim ({claim_button[0]}, {claim_button[1]})...")
        adb_helper.tap(serial, claim_button[0], claim_button[1])
        _tap_mail_reward_confirm()
        
    print(f"[{serial}] Closing Mail Menu...")
    cleanup_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not _is_ok(cleanup_result):
        return _bubble(cleanup_result, "NAV_LOBBY_UNREACHABLE: Could not close Mail Menu")
    
    print(f"[{serial}] -> Check Mail completed.")
    return _ok()


def go_to_pet_token(serial: str, detector: GameStateDetector) -> dict:
    """Navigates to Pet Token area."""
    print(f"[{serial}] Navigating to Pet Token...")
    adb_helper.tap(serial, 934, 14)
    _human_delay(2)
    adb_helper.swipe(serial, 100, 450, 100, 100, 500)
    _human_delay(1)
    adb_helper.swipe(serial, 100, 450, 100, 100, 500)
    _human_delay(1)
    adb_helper.swipe(serial, 100, 450, 100, 100, 500)
    _human_delay(1)
    adb_helper.tap(serial, 100, 375)
    _human_delay(3)
    return _ok()

def swap_account(serial: str, account_detector: AccountDetector, detector: GameStateDetector, target_account: str = None, max_scrolls: int = 5) -> dict:
    """
    In-game account switch flow.
    Navigates: LOBBY -> Profile -> Settings -> Switch Account -> Find & Select Account -> Confirm -> LOBBY.

    Args:
        serial: Emulator serial ID.
        account_detector: AccountDetector instance for OCR text detection.
        detector: GameStateDetector instance with templates loaded.
        target_account: Account string name to search for (e.g. "Goten"). 
                        If None, uses a fallback mechanism that blindly taps 
                        the top 2 visible characters sequentially.
        max_scrolls: Maximum scroll attempts to find the account in the list.

    Returns True if successfully swapped and reached LOBBY, False on failure.
    """
    LOBBY_STATES = ["IN-GAME LOBBY (IN_CITY)", "IN-GAME LOBBY (OUT_CITY)"]
    print(f"[{serial}] === SWAP ACCOUNT: {target_account} ===")

    result = startup_to_lobby(serial, detector, package_name=get_package_for_provider(detect_provider_from_emulator(serial)), load_timeout=180)
    if not _is_ok(result):
        print(f"[{serial}] swap_account failed: Could not reach lobby.")
        return _bubble(result, "NAV_LOBBY_UNREACHABLE: Could not reach lobby")

    print(f"[{serial}] Step 1/6: Opening Profile...")
    profile_result = go_to_profile(serial, detector)
    if not _is_ok(profile_result):
        print(f"[{serial}] swap_account failed: Could not open Profile.")
        return _bubble(profile_result, "NAV_TARGET_NOT_REACHED: Could not open Profile")
    _human_delay(1) 

    # 4. Tap Settings button (683, 340) -> wait via account detector
    print(f"[{serial}] Step 2/6: Opening Settings (683, 340)...")
    adb_helper.tap(serial, 683, 340)
    state = wait_for_state(serial, detector, ["SETTINGS"], timeout_sec=10, check_mode="special")
    if not state:
        print(f"[{serial}] swap_account failed: Could not reach Settings screen.")
        return _fail("NAV_TARGET_NOT_REACHED: Could not reach Settings screen")
    _human_delay(1)

    # 5. Tap "Switch Account" (478, 354) -> wait via account detector
    print(f"[{serial}] Step 3/6: Tapping Switch Account (478, 354)...")
    adb_helper.tap(serial, 478, 354)
    state = wait_for_state(serial, detector, ["CHARACTER_MANAGEMENT"], timeout_sec=10, check_mode="special")
    if not state:
        print(f"[{serial}] swap_account failed: Could not reach Character Management screen.")
        return _fail("NAV_TARGET_NOT_REACHED: Could not reach Character Management")
        
    # Give the Character Management UI time to fully slide in and render its text
    print(f"[{serial}] Waiting 3s for Character Management UI to settle...")
    _human_delay(1)

    if target_account:
        # 6. Find target account in the list using check_account_state (OCR text) + scroll
        from workflow.ocr_name_utils import sanitize_lord_name
        clean_name = sanitize_lord_name(target_account)
        if clean_name != target_account:
            print(f"[{serial}] Sanitized account name: '{target_account}' → '{clean_name}'")
        print(f"[{serial}] Step 4/6: Searching for account TEXT '{target_account}' in list...")
        account_found = None

        for scroll_attempt in range(max_scrolls + 1):
            # Try to find the account text on current viewport via OCR
            result = account_detector.check_account_name(serial, target=target_account, check_type="text")
            _human_delay(2)

            if result:
                name, center_x, center_y = result
                print(f"[{serial}] -> Account '{target_account}' found at ({center_x}, {center_y})!")
                account_found = (center_x, center_y)
                break

            if scroll_attempt < max_scrolls:
                print(f"[{serial}] -> Account not visible. Scrolling down... ({scroll_attempt + 1}/{max_scrolls})")
                # swipe(x1, y1, x2, y2, duration_ms)
                adb_helper.swipe(serial, 500, 400, 500, 200, 800)
                # Wait for the kinetic scroll animation to completely stop
                _human_delay(3)
            else:
                print(f"[{serial}] -> Account not found after {max_scrolls} scrolls.")

        from workflow.account_detector import AccountNotFoundError

        if not account_found:
            print(f"[{serial}] swap_account failed: Account '{target_account}' not found in Character Management list.")
            adb_helper.press_back(serial)
            _human_delay(2)
            raise AccountNotFoundError(f"Account '{target_account}' not found.")

        # 7. Tap the found account
        print(f"[{serial}] Step 5/6: Selecting account at ({account_found[0]}, {account_found[1]})...")
        adb_helper.tap(serial, account_found[0], account_found[1])
        _human_delay(2)

        # Check if the confirmation prompt appeared. 
        # If the state is STILL "CHARACTER_MANAGEMENT", it means the account was already selected,
        # so no confirmation prompt appeared. We just back out 3 times to Lobby.
        if detector.check_special_state(serial) == "CHARACTER_MANAGEMENT":
            print(f"[{serial}] Target account '{target_account}' is already the active account. Backing out to Lobby...")
            for _ in range(3):
                adb_helper.press_back(serial)
                _human_delay(1.5)
            return _ok()
        else: 
            print("Account not selected, proceeding to confirm")
    else:
        # Fallback Logic: Just toggle between the first 2 character slots
        print(f"[{serial}] Step 4/6 & 5/6: No target account specified. Using 2-character toggle logic.")
        char1_pos = (493, 181)  # Tọa độ slot nhân vật 1
        char2_pos = (487, 249)  # Tọa độ slot nhân vật 2
        
        print(f"[{serial}] Tapping Character 1 at {char1_pos}...")
        adb_helper.tap(serial, char1_pos[0], char1_pos[1])
        _human_delay(2)
        
        if detector.check_special_state(serial) == "CHARACTER_MANAGEMENT":
            print(f"[{serial}] Character 1 is active. Tapping Character 2 at {char2_pos}...")
            adb_helper.tap(serial, char2_pos[0], char2_pos[1])
            _human_delay(2)
        else:
            print(f"[{serial}] Character 1 selected, proceeding to confirm.")

    # 8. Tap Confirm (400, 300)
    print(f"[{serial}] Step 6/6: Confirming switch (556, 356)...")
    adb_helper.tap(serial, 556, 356)
    _human_delay(3)

    # 9. Wait for game to reload and reach Lobby
    print(f"[{serial}] Waiting for game to reload into Lobby (timeout: 120s)...")
    lobby_state = wait_for_state(serial, detector, LOBBY_STATES, timeout_sec=120)
    if not lobby_state:
        print(f"[{serial}] swap_account failed: Game did not reload into Lobby after switch.")
        return _fail("TIMEOUT_LOAD: Game did not reload into Lobby after account switch")

    print(f"[{serial}] === SWAP ACCOUNT SUCCESS -> {lobby_state} ===")
    return _ok()

def claim_city_resources(serial: str, detector: GameStateDetector) -> int:
    """
    Claims all available resources (Gold, Wood, Ore, Mana) in the city.
    Requirements:
    - User must have icons_markers/city_rss_..._full.png configured in state_detector mapped to specific resource names.
    Returns:
    - Number of resources successfully claimed.
    """
    print(f"[{serial}] Starting Claim City Resources workflow...")
    
    # 1. Back to IN_CITY
    lobby_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not _is_ok(lobby_result):
        print(f"[{serial}] [FAILED] Could not reach IN_CITY lobby.")
        return 0
        
    claimed_count = 0
    centered_once = False
    
    # 2. Specific Resource Icons to check
    rss_types = ["CITY_RSS_GOLD", "CITY_RSS_WOOD", "CITY_RSS_ORE", "CITY_RSS_MANA"]
    
    # 3. Loop each resource type individually
    for rss_type in rss_types:
        print(f"[{serial}] --- Checking for {rss_type} ---")
        for attempt in range(2):
            print(f"[{serial}] Looking for {rss_type} (Attempt {attempt + 1}/2)...")
            rss_icon = detector.locate_icon(serial, target=rss_type, threshold=0.8)
            
            if rss_icon:
                icon_name, icon_x, icon_y = rss_icon
                if not centered_once:
                    print(f"[{serial}] First city RSS icon found. Centering view once before tapping...")
                    centered_icon = _center_icon_once_then_redetect(
                        serial,
                        detector,
                        rss_type,
                        (icon_x, icon_y),
                        threshold=0.78,
                    )
                    centered_once = True
                    if centered_icon:
                        icon_x, icon_y = centered_icon
                    else:
                        print(f"[{serial}] [WARNING] Lost {rss_type} after center swipe. Falling back to original tap point.")
                print(f"[{serial}] Found {rss_type}! Tapping at ({icon_x}, {icon_y})...")
                adb_helper.tap(serial, icon_x, icon_y)
                claimed_count += 1
                _human_delay(1.5)
            else:
                print(f"[{serial}] No more {rss_type} found.")
                break
            
    print(f"[{serial}] Finished claiming city resources. Total claimed: {claimed_count}")
    return claimed_count


def _clamp_int(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _locate_icon_fullscreen(
    serial: str,
    detector: GameStateDetector,
    target: str,
    threshold: float = 0.78,
):
    if target not in detector.icon_templates:
        print(f"[{serial}] [CENTER] Icon target '{target}' is not loaded.")
        return None

    detector._cache.invalidate()
    frame = detector.screencap_memory(serial)
    if frame is None:
        print(f"[{serial}] [CENTER] Screencap failed while locating {target}.")
        return None

    screen_gray = detector._get_gray(frame)
    best = None
    best_score = 0.0

    for entry in detector.icon_templates[target]:
        entry_no_roi = dict(entry)
        entry_no_roi["roi"] = None
        score, top_left = detector._match_single(
            screen_gray,
            entry_no_roi,
            threshold,
            use_color=True,
            screen_color=frame,
        )
        if score > best_score:
            h, w = entry["color"].shape[:2]
            best_score = float(score)
            best = (target, int(top_left[0] + w // 2), int(top_left[1] + h // 2), float(score))

    if best and best_score >= threshold:
        _, x, y, score = best
        print(f"[{serial}] [CENTER] {target} fullscreen match at ({x}, {y}) conf={score:.3f}")
        return best

    print(f"[{serial}] [CENTER] {target} fullscreen not found. best_conf={best_score:.3f} threshold={threshold:.2f}")
    return None


def _center_icon_once_then_redetect(
    serial: str,
    detector: GameStateDetector,
    target: str,
    initial_xy: tuple[int, int],
    threshold: float = 0.78,
    desired_center: tuple[int, int] = (480, 270),
    tolerance_px: int = 65,
    gain: float = 0.70,
    duration_ms: int = 850,
    settle_sec: float = 1.0,
) -> tuple[int, int] | None:
    current_x, current_y = initial_xy
    dx = desired_center[0] - current_x
    dy = desired_center[1] - current_y
    dist = (dx * dx + dy * dy) ** 0.5

    print(
        f"[{serial}] [CENTER] {target} before swipe at ({current_x}, {current_y}); "
        f"center={desired_center}; dist={dist:.1f}"
    )
    if dist > tolerance_px:
        end_x = _clamp_int(int(desired_center[0] + dx * gain), 180, 780)
        end_y = _clamp_int(int(desired_center[1] + dy * gain), 90, 430)
        print(
            f"[{serial}] [CENTER] Swipe once ({desired_center[0]}, {desired_center[1]}) "
            f"-> ({end_x}, {end_y}) gain={gain:.2f} duration={duration_ms}ms"
        )
        adb_helper.swipe(
            serial,
            desired_center[0],
            desired_center[1],
            end_x,
            end_y,
            duration=duration_ms,
        )
        _human_delay(settle_sec)
    else:
        print(f"[{serial}] [CENTER] Icon already close enough to center. Skipping center swipe.")

    for attempt in range(1, 3):
        redetected = _locate_icon_fullscreen(serial, detector, target, threshold=threshold)
        if redetected:
            _, rx, ry, _ = redetected
            return rx, ry
        if attempt < 2:
            _human_delay(0.35)
    return None


def heal_troops(serial: str, detector: GameStateDetector, healing_method: str = "elixir", troop_priorities: list = None) -> dict:
    """
    Heals troops using Elixir Healing building.
    """
    print(f"[{serial}] Starting Troop Healing workflow...")

    # 1. Back to lobby IN_CITY
    lobby_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not _is_ok(lobby_result):
        print(f"[{serial}] [FAILED] Could not reach IN_CITY lobby.")
        return _bubble(lobby_result, "NAV_LOBBY_UNREACHABLE: Could not reach IN_CITY lobby")

    # 2. Check for Healing Icon
    print(f"[{serial}] Scanning for Healing Icon fullscreen...")
    icon_match = None
    for attempt in range(3):
        icon_match = _locate_icon_fullscreen(serial, detector, target="HEALING_ICON", threshold=0.78)
        if icon_match:
            break
        _human_delay(0.8)

    if not icon_match:
        print(f"[{serial}] No Healing Icon found. Troops are fully healed or icon is missing.")
        return _ok()  # Not an error — nothing to heal

    # 3. Move the icon closer to center once, then tap the re-detected position.
    _, icon_x, icon_y, _ = icon_match
    centered_icon = _center_icon_once_then_redetect(
        serial,
        detector,
        "HEALING_ICON",
        (icon_x, icon_y),
        threshold=0.78,
    )
    if not centered_icon:
        print(f"[{serial}] [FAILED] HEALING_ICON was lost after centering swipe.")
        return _fail("TEMPLATE_NO_MATCH: HEALING_ICON lost after centering swipe")

    tap_x, tap_y = centered_icon
    print(f"[{serial}] Found Healing Icon after centering. Tapping at ({tap_x}, {tap_y})...")
    adb_helper.tap(serial, tap_x, tap_y)

    # 4. Wait for Elixir Healing screen
    state = wait_for_state(serial, detector, ["ELIXIR_HEALING"], timeout_sec=10, check_mode="construction")
    if state != "ELIXIR_HEALING":
        print(f"[{serial}] [FAILED] Did not reach ELIXIR_HEALING screen.")
        return _fail("NAV_TARGET_NOT_REACHED: Did not reach ELIXIR_HEALING screen")

    # 5. Heal Troops directly. Do not select the Elixir/Resources tab here.
    HEAL_BTN = (684, 504)
    TROOP_LOCS = {
        "infantry": (494, 203),
        "cavalry": (568, 203),
        "archer": (638, 203),
        "mage": (709, 203),
        "workhorses": (782, 203),
        "siege": (856, 203)
    }

    if troop_priorities:
        for t in troop_priorities:
            t_lower = t.lower()
            if t_lower in TROOP_LOCS:
                loc = TROOP_LOCS[t_lower]
                print(f"[{serial}] Tick priority troop: {t_lower} at {loc}")
                adb_helper.tap(serial, loc[0], loc[1])
                _human_delay(1)

                print(f"[{serial}] Healing {t_lower}...")
                adb_helper.tap(serial, HEAL_BTN[0], HEAL_BTN[1])
                _human_delay(2)

                print(f"[{serial}] Untick priority troop: {t_lower} at {loc}")
                adb_helper.tap(serial, loc[0], loc[1])
                _human_delay(1)

    # Final 'Heal All' or heal remaining
    print(f"[{serial}] Tapping Heal All/Remaining (684, 504)...")
    adb_helper.tap(serial, HEAL_BTN[0], HEAL_BTN[1])
    _human_delay(3)

    # 6. Return to lobby
    print(f"[{serial}] Healing completed. Returning to lobby...")
    cleanup_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not _is_ok(cleanup_result):
        return _bubble(cleanup_result, "NAV_LOBBY_UNREACHABLE: Could not close Healing screen")

    return _ok()


def alliance_help(serial: str, detector: GameStateDetector) -> dict:
    """
    Alliance Help quick path.
    From IN_CITY/OUT_CITY lobby, detect the floating need-help button and tap it.
    """
    print(f"[{serial}] === ALLIANCE HELP QUICK ===")

    current_state = detector.check_state(serial)
    if current_state not in ("IN-GAME LOBBY (IN_CITY)", "IN-GAME LOBBY (OUT_CITY)"):
        print(f"[{serial}] Current state is {current_state}. Returning to lobby before quick help...")
        lobby_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
        if not _is_ok(lobby_result):
            return _bubble(lobby_result, "NAV_LOBBY_UNREACHABLE: Could not reach lobby before Alliance Help")

    templates = [
        ("alliance_need_help_btn", _workflow_template_path("alliance", "alliance_need_help_btn.png")),
        ("alliance_need_help_btn_2", _workflow_template_path("alliance", "alliance_need_help_btn_2.png")),
    ]
    for _, template_path in templates:
        if not os.path.exists(template_path):
            return _fail(f"TEMPLATE_MISSING: {template_path}")

    detector._cache.invalidate()
    frame = detector.screencap_memory(serial)
    if frame is None:
        return _fail("ADB_CAPTURE_FAILED: Could not capture screen for Alliance Help quick detect")

    roi = (650, 400, 960, 540)
    best = None
    for name, template_path in templates:
        match = _match_template_path_in_frame(frame, template_path, roi, threshold=0.78)
        if match:
            confidence, center, box = match
            print(f"[{serial}] {name} detected at {center} (confidence={confidence:.3f}, box={box}).")
            if best is None or confidence > best[0]:
                best = (confidence, center, name)
        else:
            print(f"[{serial}] {name} not detected in quick-help ROI.")

    if not best:
        print(f"[{serial}] No quick Alliance Help button detected. Nothing to help.")
        return _ok()

    confidence, (hx, hy), name = best
    print(f"[{serial}] Tapping quick Alliance Help '{name}' at ({hx}, {hy}) (confidence={confidence:.3f})...")
    adb_helper.tap(serial, hx, hy)
    _human_delay(1.2)
    print(f"[{serial}] === ALLIANCE HELP QUICK DONE ===")
    return _ok()


def claim_daily_chests(serial: str, detector: GameStateDetector,
                       draw_x10_silver: bool = False,
                       draw_x10_gold: bool = False,
                       draw_x10_artifact: bool = False) -> dict:
    """
    Claim daily free Hero & Artifact chest draws at the Tavern.

    Flow:
      1. go_to_construction -> TAVERN (lands on Hero Recruitment screen)
      2. Tap Silver Chest free draw -> dismiss result
      3. Tap Gold Chest free draw -> dismiss result
      4. (Optional) x10 Silver draw if draw_x10_silver & button visible
      5. (Optional) x10 Gold draw if draw_x10_gold & button visible
      6. Swap to Artifact screen
      7. Tap Artifact free draw -> dismiss result
      8. (Optional) x10 Artifact draw if draw_x10_artifact & button visible
      9. BACK -> lobby

    NOTE: x10 buttons only appear when player has >= 10 keys.
    """
    print(f"[{serial}] === TAVERN CHEST DRAW ===")

    # ============================================================
    # TODO: USER — Replace all (0, 0) with real tap coordinates
    # ============================================================
    SILVER_FREE_DRAW_TAP = (0, 0)    # TODO: Silver Chest free draw button
    GOLD_FREE_DRAW_TAP = (0, 0)      # TODO: Gold Chest free draw button
    SILVER_X10_TAP = (0, 0)          # TODO: Silver Chest x10 draw button
    GOLD_X10_TAP = (0, 0)            # TODO: Gold Chest x10 draw button
    SWAP_TO_ARTIFACT_TAP = (0, 0)    # TODO: Tab to swap Hero Recruitment -> Artifact
    ARTIFACT_FREE_DRAW_TAP = (0, 0)  # TODO: Artifact free draw button
    ARTIFACT_X10_TAP = (0, 0)        # TODO: Artifact x10 draw button
    DISMISS_POPUP_TAP = (480, 300)   # TODO: Tap to dismiss draw result popup

    # ROI for x10 button detection (to avoid mismatch between Silver & Gold)
    SILVER_X10_ROI = (0.0, 0.0, 0.5, 1.0)   # TODO: left half of screen (sample)
    GOLD_X10_ROI = (0.5, 0.0, 0.5, 1.0)     # TODO: right half of screen (sample)

    result = go_to_construction(serial, detector, "TAVERN")
    if not _is_ok(result):
        print(f"[{serial}] [FAILED] Could not navigate to Tavern.")
        return _bubble(result, "NAV_TARGET_NOT_REACHED: Could not navigate to Tavern")

    state = wait_for_state(serial, detector, ["TAVERN"], timeout_sec=10, check_mode="construction")
    if state != "TAVERN":
        print(f"[{serial}] [FAILED] Did not reach TAVERN screen.")
        return _fail("NAV_TARGET_NOT_REACHED: Did not reach TAVERN screen")

    print(f"[{serial}] Tavern opened -> Hero Recruitment screen.")
    _human_delay(2)

    # ---- HERO RECRUITMENT SCREEN ----

    # 2. Silver Chest free draw
    print(f"[{serial}] Tapping Silver Chest Free Draw {SILVER_FREE_DRAW_TAP}...")
    adb_helper.tap(serial, SILVER_FREE_DRAW_TAP[0], SILVER_FREE_DRAW_TAP[1])
    _human_delay(3)
    adb_helper.tap(serial, DISMISS_POPUP_TAP[0], DISMISS_POPUP_TAP[1])
    _human_delay(2)

    # 3. Gold Chest free draw
    print(f"[{serial}] Tapping Gold Chest Free Draw {GOLD_FREE_DRAW_TAP}...")
    adb_helper.tap(serial, GOLD_FREE_DRAW_TAP[0], GOLD_FREE_DRAW_TAP[1])
    _human_delay(3)
    adb_helper.tap(serial, DISMISS_POPUP_TAP[0], DISMISS_POPUP_TAP[1])
    _human_delay(2)

    # 4. (Optional) x10 Silver draw
    if draw_x10_silver:
        print(f"[{serial}] Checking for Silver x10 draw button...")
        x10_match = detector.check_activity(serial, target="TAVERN_DRAW_X10", threshold=0.8)
        if x10_match:
            print(f"[{serial}] Silver x10 button found! Tapping {SILVER_X10_TAP}...")
            adb_helper.tap(serial, SILVER_X10_TAP[0], SILVER_X10_TAP[1])
            _human_delay(3)
            adb_helper.tap(serial, DISMISS_POPUP_TAP[0], DISMISS_POPUP_TAP[1])
            _human_delay(2)
        else:
            print(f"[{serial}] Silver x10 button NOT found (not enough keys). Skipping.")

    # 5. (Optional) x10 Gold draw
    if draw_x10_gold:
        print(f"[{serial}] Checking for Gold x10 draw button...")
        x10_match = detector.check_activity(serial, target="TAVERN_DRAW_X10", threshold=0.8)
        if x10_match:
            print(f"[{serial}] Gold x10 button found! Tapping {GOLD_X10_TAP}...")
            adb_helper.tap(serial, GOLD_X10_TAP[0], GOLD_X10_TAP[1])
            _human_delay(3)
            adb_helper.tap(serial, DISMISS_POPUP_TAP[0], DISMISS_POPUP_TAP[1])
            _human_delay(2)
        else:
            print(f"[{serial}] Gold x10 button NOT found (not enough keys). Skipping.")

    # ---- SWAP TO ARTIFACT SCREEN ----

    # 6. Swap to Artifact
    print(f"[{serial}] Swapping to Artifact screen {SWAP_TO_ARTIFACT_TAP}...")
    adb_helper.tap(serial, SWAP_TO_ARTIFACT_TAP[0], SWAP_TO_ARTIFACT_TAP[1])
    _human_delay(3)

    # 7. Artifact free draw
    print(f"[{serial}] Tapping Artifact Free Draw {ARTIFACT_FREE_DRAW_TAP}...")
    adb_helper.tap(serial, ARTIFACT_FREE_DRAW_TAP[0], ARTIFACT_FREE_DRAW_TAP[1])
    _human_delay(3)
    adb_helper.tap(serial, DISMISS_POPUP_TAP[0], DISMISS_POPUP_TAP[1])
    _human_delay(2)

    # 8. (Optional) x10 Artifact draw
    if draw_x10_artifact:
        print(f"[{serial}] Checking for Artifact x10 draw button...")
        x10_match = detector.check_activity(serial, target="TAVERN_DRAW_X10", threshold=0.8)
        if x10_match:
            print(f"[{serial}] Artifact x10 button found! Tapping {ARTIFACT_X10_TAP}...")
            adb_helper.tap(serial, ARTIFACT_X10_TAP[0], ARTIFACT_X10_TAP[1])
            _human_delay(3)
            adb_helper.tap(serial, DISMISS_POPUP_TAP[0], DISMISS_POPUP_TAP[1])
            _human_delay(2)
        else:
            print(f"[{serial}] Artifact x10 button NOT found (not enough keys). Skipping.")

    # 9. Back to lobby
    print(f"[{serial}] Done! Pressing BACK to return to lobby...")
    adb_helper.press_back(serial)
    _human_delay(2)

    print(f"[{serial}] === TAVERN CHEST DRAW COMPLETE ===")
    return _ok()


def attack_darkling_legions_v1_basic(serial: str, detector: GameStateDetector) -> dict:
    """
    Basic Darkling Legions attack flow.
    """
    print(f"[{serial}] Navigating to Attack Darkling Legions V1 (BASIC)...")

    SEARCH_MENU_TAP = (42, 422)
    DARKLING_MENU_TAP = (158, 486)
    DARKLING_LEGIONS_TAB_TAP = (50, 210)
    ACTION_BUTTON_TAP = (285, 400)
    DISPATCH_TAP = (500, 465)
    CHOOSE_LEGIONS_TAP = (500, 265)
    CONFIRM_TAP = (800, 480)
    TARGET_STATES = ["AUTO_PEACEKEEPING"]

    lobby_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)")
    if not _is_ok(lobby_result):
        print(f"[{serial}] [FAILED] Could not reach OUT_CITY lobby.")
        return _bubble(lobby_result, "NAV_LOBBY_UNREACHABLE: Could not reach OUT_CITY")

    # 2. Open search menu and switch to Darkling category if needed
    category = _ensure_search_menu_category(serial, detector, "darkling")
    if category is None:
        return _fail("NAV_TARGET_NOT_REACHED: Could not open search menu")

    # 3. Select Darkling Legions tab
    print(f"[{serial}] Selecting Darkling Legions tab {DARKLING_LEGIONS_TAB_TAP}...")
    adb_helper.tap(serial, DARKLING_LEGIONS_TAB_TAP[0], DARKLING_LEGIONS_TAB_TAP[1])
    _human_delay(2)

    # 4. Tap action/search button
    print(f"[{serial}] Triggering basic attack action {ACTION_BUTTON_TAP}...")
    adb_helper.tap(serial, ACTION_BUTTON_TAP[0], ACTION_BUTTON_TAP[1])
    _human_delay(2)

    # 6. Wait for create-legion state
    print(f"[{serial}] Waiting for Darkling Legions attack window...")
    state = wait_for_state(serial, detector, TARGET_STATES, timeout_sec=10, check_mode="special")
    if state not in TARGET_STATES:
        print(f"[{serial}] [FAILED] Did not reach Darkling Legions attack window.")
        return _fail("NAV_TARGET_NOT_REACHED: Did not reach Darkling Legions window")

    #7. Use all free Legions
    print(f"[{serial}] Using all free Legions...")
    adb_helper.tap(serial, CHOOSE_LEGIONS_TAP[0], CHOOSE_LEGIONS_TAP[1])
    _human_delay(2)
    adb_helper.tap(serial, CONFIRM_TAP[0], CONFIRM_TAP[1])
    _human_delay(2)

    # 7. Tap Start
    print(f"[{serial}] Starting Peacekeeping dispatch {DISPATCH_TAP}...")
    adb_helper.tap(serial, DISPATCH_TAP[0], DISPATCH_TAP[1])
    _human_delay(2)

    # 8. Check outcome
    print(f"[{serial}] Checking outcome of Darkling Legions dispatch...")
    outcome = wait_for_state(serial, detector, TARGET_STATES, timeout_sec=5, check_mode="special")

    if outcome is None:
        print(f"[{serial}] Dispatch started & game pushed to map! Attack successful.")
        _human_delay(120)
        return _ok()

    if outcome == "AUTO_PEACEKEEPING":
        print(f"[{serial}] Still on Peacekeeping screen. Out of CP.")
        adb_helper.press_back(serial)

    return _ok()

def check_legion_state(serial: str, detector: GameStateDetector, max_legions: int = 5) -> dict:
    """Thin wrapper — delegates to detector.check_legion_state()."""
    return detector.check_legion_state(serial, max_legions=max_legions)

def recall_idle_legions(serial: str, detector: GameStateDetector, idle_slots: list[int]) -> int:
    """Recall only the idle legion rows that need recovery."""
    slot_zones = [
        (50, 130),
        (140, 220),
        (230, 310),
        (320, 400),
        (410, 490),
    ]

    try:
        recall_matches = detector.find_all_activity_matches(
            serial, target="LEGION_RECALL_BTN", threshold=0.85
        )
    except Exception:
        recall_matches = []

    print(f"[{serial}] Detected {len(recall_matches)} Recall button(s) on panel.")

    recalled = 0
    used_matches: set[int] = set()
    for slot in idle_slots:
        if slot < 1 or slot > 5:
            continue

        y_min, y_max = slot_zones[slot - 1]
        print(f"[{serial}] Looking for Recall button in slot {slot} (Y: {y_min}-{y_max})...")

        zone_matches = [
            (idx, rx, ry)
            for idx, (rx, ry) in enumerate(recall_matches)
            if idx not in used_matches and y_min <= ry <= y_max
        ]
        if not zone_matches:
            print(f"[{serial}] No Recall button found inside slot {slot} zone.")
            continue

        zone_center_y = (y_min + y_max) / 2.0
        idx, rx, ry = min(zone_matches, key=lambda item: abs(item[2] - zone_center_y))
        print(f"[{serial}] Found Recall button at ({rx}, {ry}) for slot {slot}. Tapping...")
        adb_helper.tap(serial, rx, ry)
        used_matches.add(idx)
        recalled += 1
        _human_delay(2)

    print(f"[{serial}] Recalled {recalled} idle legion(s).")
    return recalled


def run_legion_preflight(
    serial: str,
    detector: GameStateDetector,
    max_legions: int = 5,
    recall_idle: bool = True,
) -> dict:
    """Pre-check legion availability once before account workflows start."""
    base_result = {
        "legions_outcity": 0,
        "legions_idle": 0,
        "idle_slots": [],
        "legions_returning": 0,
        "returning_slots": [],
        "legions_free": max_legions,
        "max_legions": max_legions,
        "detected_label": None,
        "idle_recalled": 0,
        "preflight_ran": True,
    }

    print(
        f"[{serial}] === LEGION PREFLIGHT (max_legions={max_legions}, recall_idle={recall_idle}) ==="
    )

    current = detector.check_state(serial)
    if current != "IN-GAME LOBBY (OUT_CITY)":
        print(f"[{serial}] Legion preflight aligning to OUT_CITY lobby (current={current})...")
        lobby_result = back_to_lobby(
            serial,
            detector,
            target_lobby="IN-GAME LOBBY (OUT_CITY)",
        )
        if not _is_ok(lobby_result):
            print(f"[{serial}] [WARNING] Legion preflight could not reach OUT_CITY lobby.")
            base_result["error"] = "out_city_unreachable"
            return base_result

    management_match = detector.check_activity(
        serial, target="LEGIONS_MANAGEMENT", threshold=0.90
    )
    if not management_match:
        final_state = detector.check_state(serial)
        print(
            f"[{serial}] No legion management icon found in state '{final_state}'. "
            f"Treating all {max_legions} legions as free."
        )
        return base_result

    _, cx, cy = management_match
    print(f"[{serial}] Opening Legion Management at ({cx}, {cy})...")
    adb_helper.tap(serial, cx, cy)
    _human_delay(3)

    try:
        result = detector.check_legion_state(serial, max_legions=max_legions) or dict(base_result)
        result.setdefault("idle_recalled", 0)
        result["preflight_ran"] = True

        idle_slots = list(result.get("idle_slots") or [])
        if recall_idle and idle_slots:
            print(f"[{serial}] Recalling idle legion slots: {idle_slots}")
            recalled = recall_idle_legions(serial, detector, idle_slots)
            result["idle_recalled"] = recalled
            if recalled > 0:
                _human_delay(2)
                refreshed = detector.check_legion_state(serial, max_legions=max_legions) or {}
                refreshed["idle_recalled"] = recalled
                refreshed["preflight_ran"] = True
                result = {**result, **refreshed}
        return result
    finally:
        adb_helper.press_back(serial)
        _human_delay(1)


def go_to_check_legions_state(serial: str, detector: GameStateDetector, max_legions: int = 5) -> dict:
    """
    Full navigation flow: Lobby → detect management icon → open → check → close.
    
    1. Ensures we are at Lobby (IN_CITY or OUT_CITY).
    2. Scans for any LEGION count indicator (LEGION_{max}_{outcity}) on screen.
       - If found → taps it to open Legion Management panel.
       - If not found → all legions are free (0 out-city), returns immediately.
    3. Inside Legion Management, runs detector.check_legion_state() for full
       idle/returning slot detection.
    4. Presses back to close the panel.
    
    Returns same dict as check_legion_state():
        {
            "legions_outcity", "legions_idle", "idle_slots",
            "legions_returning", "returning_slots",
            "legions_free", "max_legions", "detected_label"
        }
    Returns None if navigation to lobby fails.
    """
    LOBBY_STATES = ["IN-GAME LOBBY (IN_CITY)", "IN-GAME LOBBY (OUT_CITY)"]
    
    # 1. Ensure at lobby
    current = detector.check_state(serial)
    if current not in LOBBY_STATES:
        lobby_result = back_to_lobby(serial, detector)
        if not _is_ok(lobby_result):
            print(f"[{serial}] [FAILED] Could not reach Lobby for legion check.")
            return None
    
    # 2. Scan for legion management icon
    print(f"[{serial}] Scanning for legion management icon...")
    management_match = detector.check_activity(serial, target="LEGIONS_MANAGEMENT", threshold=0.90)
    
    if not management_match:
        # No indicator = no legions dispatched = all free
        print(f"[{serial}] No legion management icon found. All {max_legions} legions are free.")
        return {
            "legions_outcity": 0,
            "legions_idle": 0,
            "idle_slots": [],
            "legions_returning": 0,
            "returning_slots": [],
            "legions_free": max_legions,
            "max_legions": max_legions,
            "detected_label": None,
        }
    
    # 3. Tap on the indicator to open Legion Management
    name, cx, cy = management_match
    print(f"[{serial}] Found {name} at ({cx}, {cy}). Tapping to open Legion Management...")
    adb_helper.tap(serial, cx, cy)
    _human_delay(3)
    
    # 4. Run full check inside the management panel
    result = detector.check_legion_state(serial, max_legions=max_legions)
    
    # 5. Close management panel
    adb_helper.press_back(serial)
    _human_delay(1)
    
    return result

def research_technology(serial: str, detector: GameStateDetector, research_type: str = "default", max_power: int = 0) -> dict:
    """
    Automates Technology Research at Research Center.
    
    research_type:
      - "economy": tap Economy tab (30, 190) before researching
      - "military": tap Military tab (30, 320) before researching
      - "balance": alternate economy/military per slot
      - "default": don't tap any tab, just research whatever is shown
    
    max_power: if > 0, skip research when account power exceeds this value (in raw number, e.g. 14000000 for 14M).
    
    Returns:
      bool: True if at least 1 slot researched, False otherwise.
    """
    print(f"[{serial}] === TECHNOLOGY RESEARCH (type={research_type}) ===")
    research_type = research_type.lower()

    if max_power > 0:
        from workflow.ocr_helper import ocr_region_with_retry
        try:
            power_text = ocr_region_with_retry(serial, detector, (0, 0, 120, 30), attempts=2, style="outline")
            if power_text:
                power_val = int(power_text.replace(",", "").replace(".", "").strip())
                if power_val > max_power:
                    print(f"[{serial}] Power {power_val:,} > max_power {max_power:,}. Skipping research.")
                    return _fail(f"CONFIG_EXCEEDED_LIMIT: Power {power_val:,} > max_power {max_power:,}")
        except Exception as e:
            print(f"[{serial}] [WARNING] Could not read power: {e}. Proceeding anyway.")

    ECONOMY_TAB_TAP = (30, 190)
    MILITARY_TAB_TAP = (30, 320)
    BUFFER_SEC = 120  # 2 minutes buffer for research cooldown

    # 1. Navigate to Research Center (V2 — detects research icon on city popup)
    print(f"[{serial}] Resetting city camera before Research Center navigation...")
    reset_position(serial)
    result = go_to_construction(serial, detector, "RESEARCH_CENTER", feature="research")
    if not _is_ok(result):
        print(f"[{serial}] [FAILED] Could not navigate to Research Center.")
        return _bubble(result, "NAV_TARGET_NOT_REACHED: Could not navigate to Research Center")

    print(f"[{serial}] Research Center opened successfully.")

    # 1b. Dismiss any auto-popup (when research is active, the current node popup appears)
    print(f"[{serial}] Dismissing any auto-popup (415, 520)...")
    adb_helper.tap(serial, 415, 520)
    _human_delay(1.5)

    # 2. Scan for Alliance Help buttons (already researching, need help)
    alliance_help_count = 0
    for scan in range(2):
        detector._screen_cache = None
        print(f"[{serial}] [DEBUG] Alliance Help scan #{scan+1} (threshold=0.8)...")
        help_match = detector.check_activity(serial, target="RESEARCH_ALLIANCE_HELP", threshold=0.8)
        print(f"[{serial}] [DEBUG] Alliance Help result: {help_match}")
        if help_match:
            _, hx, hy = help_match
            print(f"[{serial}] Found Alliance Help button at ({hx}, {hy}). Tapping...")
            adb_helper.tap(serial, hx, hy)
            _human_delay(2)
            alliance_help_count += 1
        else:
            break
    if alliance_help_count > 0:
        print(f"[{serial}] Tapped {alliance_help_count} Alliance Help button(s).")

    # 3. Scan for empty research slots
    slots_researched = 0
    max_slots = 2

    for slot_idx in range(max_slots):
        print(f"\n[{serial}] --- Checking Research Slot #{slot_idx + 1} ---")

        # Detect empty slot (green "RESEARCH" button at top)
        empty_match = detector.check_activity(serial, target="RESEARCH_EMPTY_SLOT", threshold=0.8)
        if not empty_match:
            print(f"[{serial}] No empty research slot found. Done.")
            break

        _, slot_x, slot_y = empty_match
        print(f"[{serial}] Found empty slot at ({slot_x}, {slot_y}).")

        # 3a. Select research type tab (before tapping research)
        if research_type == "economy":
            print(f"[{serial}] Selecting Economy Tech tab {ECONOMY_TAB_TAP}...")
            adb_helper.tap(serial, ECONOMY_TAB_TAP[0], ECONOMY_TAB_TAP[1])
            _human_delay(2)
        elif research_type == "military":
            print(f"[{serial}] Selecting Military Tech tab {MILITARY_TAB_TAP}...")
            adb_helper.tap(serial, MILITARY_TAB_TAP[0], MILITARY_TAB_TAP[1])
            _human_delay(2)
        elif research_type == "balance":
            if slot_idx % 2 == 0:
                print(f"[{serial}] Balance mode: selecting Economy Tech tab...")
                adb_helper.tap(serial, ECONOMY_TAB_TAP[0], ECONOMY_TAB_TAP[1])
            else:
                print(f"[{serial}] Balance mode: selecting Military Tech tab...")
                adb_helper.tap(serial, MILITARY_TAB_TAP[0], MILITARY_TAB_TAP[1])
            _human_delay(2)
        # "default" → don't tap any tab

        # 3b. Tap the Research button (at detected empty slot position)
        print(f"[{serial}] Tapping Research button at ({slot_x}, {slot_y})...")
        adb_helper.tap(serial, slot_x, slot_y)
        _human_delay(3)

        # 3b2. Tab verification: game may auto-switch tab when current tab
        #      has no available tech (e.g. economy maxed -> jumps to military).
        #      If user selected a specific type, verify we're still on that tab.
        if research_type in ("economy", "military"):
            expected_tab = "RESEARCH_ECONOMY_TECH" if research_type == "economy" else "RESEARCH_MILITARY_TECH"
            tab_match = detector.check_activity(serial, target=expected_tab, threshold=0.8)
            if not tab_match:
                print(f"[{serial}] [INFO] Tab {research_type} maxed (auto-switched). Nothing to research.")
                adb_helper.tap(serial, 415, 520)
                _human_delay(2)
                adb_helper.press_back(serial)
                _human_delay(2)
                return _ok(dynamic_cooldown_sec=21600)  # 6h cooldown — tab maxed

        # 3c. Edge case: no tech to research (no confirm button visible)
        no_confirm = detector.check_special_state(serial, target="RESEARCH_NO_CONFIRM")
        if no_confirm:
            print(f"[{serial}] No available tech to research (requirements not met). Dismissing popup...")
            adb_helper.tap(serial, 415, 520)
            _human_delay(2)
            continue

        # 3d. Tap Confirm Research
        confirm_match = detector.check_activity(serial, target="RESEARCH_CONFIRM", threshold=0.8)
        if not confirm_match:
            print(f"[{serial}] [WARNING] Confirm button not found. Dismissing popup...")
            adb_helper.tap(serial, 415, 520)
            _human_delay(2)
            continue

        # TODO: OCR timer reading for dynamic cooldown (future feature)
        _, cx, cy = confirm_match
        print(f"[{serial}] Tapping Confirm Research at ({cx}, {cy})...")
        adb_helper.tap(serial, cx, cy)
        _human_delay(3)

        # 3f. Edge case: not enough resources
        no_resource = detector.check_special_state(serial, target="RESEARCH_NO_RESOURCE")
        if no_resource:
            print(f"[{serial}] Not enough resources! Trying to use bag resources...")
            bag_match = detector.check_activity(serial, target="RESEARCH_USE_BAG", threshold=0.8)
            if bag_match:
                _, bx, by = bag_match
                print(f"[{serial}] Tapping Use Resource in Bag at ({bx}, {by})...")
                adb_helper.tap(serial, bx, by)
                _human_delay(3)
                
                still_no = detector.check_special_state(serial, target="RESEARCH_NO_RESOURCE")
                if still_no:
                    print(f"[{serial}] Still not enough resources even after bag. Cancelling.")
                    adb_helper.tap(serial, 415, 520)
                    _human_delay(2)
                    continue
            else:
                print(f"[{serial}] No 'Use Bag' button found. Cancelling research.")
                adb_helper.tap(serial, 415, 520)
                _human_delay(2)
                continue

        # 3g. Handle Alliance Help popup after confirming
        _human_delay(2)
        detector._screen_cache = None
        print(f"[{serial}] [DEBUG] Post-confirm Alliance Help scan (threshold=0.8)...")
        post_help = detector.check_activity(serial, target="RESEARCH_ALLIANCE_HELP", threshold=0.8)
        print(f"[{serial}] [DEBUG] Post-confirm Alliance Help result: {post_help}")
        if post_help:
            _, phx, phy = post_help
            print(f"[{serial}] Alliance Help appeared at ({phx}, {phy}). Tapping...")
            adb_helper.tap(serial, phx, phy)
            _human_delay(2)

        slots_researched += 1
        print(f"[{serial}] Slot #{slot_idx + 1} research started successfully!")

    print(f"[{serial}] === TECHNOLOGY RESEARCH COMPLETE ({slots_researched} slot(s) started) ===")
    adb_helper.press_back(serial)
    _human_delay(2)

    if slots_researched > 0:
        return _ok(dynamic_cooldown_sec=21600)  # 6h cooldown
    return _ok(message="RESEARCH_NO_SLOT: No empty research slot available")


def _parse_research_timer(timer_str: str) -> int:
    """
    Parse research timer from text like '2d 21:43:41', '21:43:41', '03:15:22'.
    Returns total seconds. Supports days, hours, minutes, seconds.
    """
    import re
    if not timer_str:
        return 0

    total_sec = 0
    remaining = timer_str.strip()

    # Extract days if present (e.g., "2d", "2d ")
    day_match = re.search(r'(\d+)\s*d', remaining, re.IGNORECASE)
    if day_match:
        total_sec += int(day_match.group(1)) * 86400
        remaining = remaining[day_match.end():].strip()

    # Extract HH:MM:SS or MM:SS from remaining
    time_match = re.search(r'(\d+):(\d+):(\d+)', remaining)
    if time_match:
        h, m, s = int(time_match.group(1)), int(time_match.group(2)), int(time_match.group(3))
        total_sec += h * 3600 + m * 60 + s
    else:
        time_match_short = re.search(r'(\d+):(\d+)', remaining)
        if time_match_short:
            m, s = int(time_match_short.group(1)), int(time_match_short.group(2))
            total_sec += m * 60 + s
        else:
            # Fallback: Xh Ym format
            h_match = re.search(r'(\d+)\s*h', remaining, re.IGNORECASE)
            m_match = re.search(r'(\d+)\s*m', remaining, re.IGNORECASE)
            if h_match:
                total_sec += int(h_match.group(1)) * 3600
            if m_match:
                total_sec += int(m_match.group(1)) * 60

    return total_sec


def claim_daily_vip_gift(serial: str, detector: GameStateDetector) -> dict:
    """
    Claim daily VIP Gift.
    """
    print(f"[{serial}] Starting Claim Daily VIP Gift workflow...")
    workflow_start = time.time()
    
    t0 = time.time()
    result = go_to_construction(serial, detector, "SHOP")
    if not _is_ok(result):
        print(f"[{serial}] [FAILED] Could not access SHOP construction.")
        return _bubble(result, "NAV_TARGET_NOT_REACHED: Could not access SHOP")
        
    _human_delay(3)
    print(f"[{serial}] [TIMING] Accessing SHOP construction took {time.time() - t0:.2f}s")
    
    t0 = time.time()
    # 3. Tap Claim
    print(f"[{serial}] Tapping Claim (718, 425)...")
    adb_helper.tap(serial, 718, 425)
    _human_delay(2)
    print(f"[{serial}] [TIMING] Tapping Claim took {time.time() - t0:.2f}s")
    
    t0 = time.time()
    # 4. Tap Hornor Point (PLUS icon)
    print(f"[{serial}] Tapping Hornor Point (PLUS icon) (278, 357)...")
    adb_helper.tap(serial, 278, 357)
    _human_delay(2)
    print(f"[{serial}] [TIMING] Tapping Hornor Point took {time.time() - t0:.2f}s")
    
    t0 = time.time()
    # 5. Tap claim point
    print(f"[{serial}] Tapping Claim point (714, 165)...")
    adb_helper.tap(serial, 714, 165)
    _human_delay(2)
    print(f"[{serial}] [TIMING] Tapping Claim point took {time.time() - t0:.2f}s")
    
    t0 = time.time()
    # 6. Return safely to lobby
    print(f"[{serial}] Returning safely to lobby...")
    cleanup_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    print(f"[{serial}] [TIMING] Lobby cleanup took {time.time() - t0:.2f}s")
    if not _is_ok(cleanup_result):
        return _bubble(cleanup_result, "NAV_LOBBY_UNREACHABLE: Could not close VIP Gift menus")
    
    print(f"[{serial}] VIP Gift claim workflow finished successfully in {time.time() - workflow_start:.2f}s.")
    return _ok()


# ═══════════════════════════════════════════════════════════════════════
#  FESTIVAL OF FORTITUDE
# ═══════════════════════════════════════════════════════════════════════

# Day tab coordinates (960×540 resolution)
_FESTIVAL_DAY_TAPS = {
    1: (545, 100),
    2: (605, 100),
    3: (670, 100),
    4: (740, 100),
    5: (810, 100),
}

# Category tab coordinates (up to 3 tabs per day)
_FESTIVAL_CATEGORY_TAPS = [
    (565, 160),   # 1st tab (left)
    (670, 160),   # 2nd tab (mid)
    (775, 160),   # 3rd tab (right)
]

# ROI region around each day tab for lock-icon detection (relative offsets from day tap)
_DAY_LOCK_CHECK_OFFSET = (0, -5, 50, 50)  # x_off, y_off, width, height


def _detect_active_festival_day(serial: str, detector: GameStateDetector) -> int:
    """
    Detect the highest unlocked day in the Festival of Fortitude.
    Scans Day 5 → Day 1. The first day WITHOUT a lock icon is the active day.
    Returns day number (1-5) or 0 if detection fails.
    """
    print(f"[{serial}] [FESTIVAL] Detecting active day...")

    frame = detector.get_frame(serial)
    if frame is None:
        print(f"[{serial}] [FESTIVAL] [ERROR] Could not capture screen for day detection.")
        return 0

    for day_num in range(5, 0, -1):
        day_x, day_y = _FESTIVAL_DAY_TAPS[day_num]

        # Crop a small region around the day tab to check for lock icon
        ox, oy, rw, rh = _DAY_LOCK_CHECK_OFFSET
        x1 = max(0, day_x + ox - rw // 2)
        y1 = max(0, day_y + oy - rh // 2)
        x2 = min(frame.shape[1], x1 + rw)
        y2 = min(frame.shape[0], y1 + rh)

        day_region = frame[y1:y2, x1:x2]
        if day_region.size == 0:
            continue

        # Check if lock icon is present in this region
        lock_found = detector.check_special_state(serial, target="FESTIVAL_DAY_LOCKED", frame=frame)

        if lock_found:
            print(f"[{serial}] [FESTIVAL]   Day {day_num}: LOCKED")
            continue
        else:
            print(f"[{serial}] [FESTIVAL]   Day {day_num}: UNLOCKED → Active Day!")
            return day_num

    # Fallback: if no lock detected on any day, default to Day 1
    print(f"[{serial}] [FESTIVAL] [WARNING] Could not determine active day. Defaulting to Day 1.")
    return 1


def _scan_festival_tasks(serial: str, detector: GameStateDetector) -> dict:
    """
    Scan all visible task rows in current tab.
    Returns stats dict: {"claimed": N, "claim_tapped": N, "incomplete": N, "skipped": N}
    """
    stats = {"claimed": 0, "claim_tapped": 0, "incomplete": 0, "skipped": 0}
    max_scan_rounds = 6  # Maximum task rows visible per tab (safety limit)

    for scan_idx in range(max_scan_rounds):
        try:
            frame = detector.get_frame(serial)
            if frame is None:
                print(f"[{serial}] [FESTIVAL] [ERROR] Screen capture failed during task scan.")
                break

            # Priority 1: Check for Claim button (green, tappable)
            claim_match = detector.check_activity(
                serial, target="FESTIVAL_CLAIM_BTN", threshold=0.8, frame=frame
            )
            if claim_match:
                _, cx, cy = claim_match
                print(f"[{serial}] [FESTIVAL]   Task #{scan_idx+1}: CLAIMABLE at ({cx}, {cy}). Tapping...")
                adb_helper.tap(serial, cx, cy)
                _human_delay(2)  # Wait for claim animation
                stats["claim_tapped"] += 1
                continue

            # Priority 2: Check for "Claimed" badge (already collected)
            claimed_match = detector.check_special_state(
                serial, target="FESTIVAL_TASK_CLAIMED", threshold=0.8, frame=frame
            )
            if claimed_match:
                stats["claimed"] += 1
                # No more claimable buttons found and we see "Claimed" — this tab is done
                print(f"[{serial}] [FESTIVAL]   Found 'Claimed' indicator. Tab likely complete.")
                break

            # Priority 3: Check for GO button (incomplete task)
            go_match = detector.check_activity(
                serial, target="FESTIVAL_GO_BTN", threshold=0.8, frame=frame
            )
            if go_match:
                _, gx, gy = go_match
                print(f"[{serial}] [FESTIVAL]   Task #{scan_idx+1}: INCOMPLETE (GO) at ({gx}, {gy}).")
                # Delegate to external handler (stub — logs only for now)
                _execute_event_task_stub(serial, detector, f"task_{scan_idx+1}")
                stats["incomplete"] += 1
                # After handler returns, re-scan this tab for any remaining claims
                continue

            # Nothing found — no more tasks visible
            print(f"[{serial}] [FESTIVAL]   No more task buttons detected. Tab scan complete.")
            break

        except Exception as e:
            print(f"[{serial}] [FESTIVAL] [ERROR] Task scan #{scan_idx+1} failed: {e}")
            stats["skipped"] += 1
            continue

    return stats


def _execute_event_task_stub(serial: str, detector: GameStateDetector, task_id: str):
    """
    Stub for execute_event_task(). Logs the task and returns.
    Will be replaced with real task execution logic later.
    """
    print(f"[{serial}] [FESTIVAL] [STUB] execute_event_task('{task_id}') — not implemented yet, skipping.")


def process_festival_of_fortitude_event(serial: str, detector: GameStateDetector) -> dict:
    """
    Automate the Festival of Fortitude event workflow.

    Preconditions:
        - Game is running, bot is already on the Festival of Fortitude event screen.
        - GameStateDetector is initialized.

    Flow:
        1. Detect the highest unlocked day.
        2. Tap that day tab.
        3. Iterate all category tabs (left → right).
        4. For each tab: scan task rows — claim rewards, delegate incomplete tasks, skip claimed.

    Returns True if completed successfully, False on critical failure.
    """
    print(f"\n[{serial}] ═══════════════════════════════════════════")
    print(f"[{serial}]   FESTIVAL OF FORTITUDE — START")
    print(f"[{serial}] ═══════════════════════════════════════════\n")

    # 0. Verify we are on the Festival screen
    header_check = detector.check_special_state(serial, target="FESTIVAL_HEADER", threshold=0.75)
    if not header_check:
        print(f"[{serial}] [FESTIVAL] [WARNING] Festival header not detected. Proceeding anyway (template may be missing).")

    # 1. Detect active day
    active_day = _detect_active_festival_day(serial, detector)
    if active_day == 0:
        print(f"[{serial}] [FESTIVAL] [FAILED] Could not detect any unlocked day.")
        return _fail("TEMPLATE_NO_MATCH: Could not detect any unlocked festival day")

    print(f"[{serial}] [FESTIVAL] Active Day: {active_day}")

    # 2. Tap the active day tab
    day_tap = _FESTIVAL_DAY_TAPS[active_day]
    print(f"[{serial}] [FESTIVAL] Tapping Day {active_day} tab at {day_tap}...")
    adb_helper.tap(serial, day_tap[0], day_tap[1])
    _human_delay(2)

    # 3. Iterate category tabs
    total_stats = {"claimed": 0, "claim_tapped": 0, "incomplete": 0, "skipped": 0}

    for tab_idx, tab_tap in enumerate(_FESTIVAL_CATEGORY_TAPS):
        print(f"\n[{serial}] [FESTIVAL] --- Category Tab #{tab_idx+1} at {tab_tap} ---")

        try:
            adb_helper.tap(serial, tab_tap[0], tab_tap[1])
            _human_delay(1.5)  # Wait for UI to update

            # Scan tasks in this tab
            tab_stats = _scan_festival_tasks(serial, detector)

            # Accumulate stats
            for key in total_stats:
                total_stats[key] += tab_stats.get(key, 0)

            print(f"[{serial}] [FESTIVAL]   Tab #{tab_idx+1} result: {tab_stats}")

        except Exception as e:
            print(f"[{serial}] [FESTIVAL] [ERROR] Tab #{tab_idx+1} failed: {e}. Skipping.")
            continue

    # 4. Summary
    print(f"\n[{serial}] ═══════════════════════════════════════════")
    print(f"[{serial}]   FESTIVAL OF FORTITUDE — COMPLETE")
    print(f"[{serial}]   Day {active_day} | Claims: {total_stats['claim_tapped']} | "
          f"Already Claimed: {total_stats['claimed']} | Incomplete: {total_stats['incomplete']} | "
          f"Errors: {total_stats['skipped']}")
    print(f"[{serial}] ═══════════════════════════════════════════\n")

    return _ok()


def clean_trash_pet_sanctuary(
    serial: str,
    detector: GameStateDetector,
    duration: float = 60,
    score_threshold: float = 0.30,
    navigate: bool = True,
) -> dict:
    """
    Clean trash at Pet Sanctuary.

    Flow:
      1. Navigate to Pet Sanctuary
      2. Load clean baseline image from templates
      3. Loop for `duration` seconds:
         - Multi-frame voting detection (3 frames × 2s)
         - Tap each confirmed trash
         - Dismiss pet menu after each tap
         - Early exit after 3 consecutive empty cycles
      4. Return True
    """
    _TAP_DELAY = 0.35
    _CYCLE_COOLDOWN = 1.0
    _DISMISS_POS = (50, 500)
    _DISMISS_DELAY = 0.25
    _MAX_EMPTY_STREAK = 3

    print(f"[{serial}] === CLEAN TRASH PET SANCTUARY ===")

    # 1. Navigate to Pet Sanctuary
    if navigate:
        result = go_to_pet_sanctuary(serial, detector)
        if not _is_ok(result):
            print(f"[{serial}] [FAILED] Could not reach Pet Sanctuary.")
            return _bubble(result, "NAV_TARGET_NOT_REACHED: Could not reach Pet Sanctuary")
    else:
        print(f"[{serial}] [TRASH] Reusing current Pet Sanctuary session without re-navigation.")

    # 2. Load baseline image
    templates_dir = detector.templates_dir
    clean_path = os.path.join(templates_dir, "clean_state_960x540.png")
    if not os.path.exists(clean_path):
        print(f"[{serial}] [FAILED] Clean baseline image not found: {clean_path}")
        return _fail("TEMPLATE_NO_MATCH: Clean baseline image not found")

    clean_img = cv2.imread(clean_path, cv2.IMREAD_COLOR)
    if clean_img is None:
        print(f"[{serial}] [FAILED] Could not load clean baseline image.")
        return _fail("TEMPLATE_NO_MATCH: Could not load clean baseline image")

    print(f"[{serial}] [TRASH] Duration: {duration}s | Threshold: {score_threshold}")

    # 3. Detection + tap loop
    total_taps = 0
    cycle = 0
    empty_streak = 0
    start = time.time()

    while time.time() - start < duration:
        cycle += 1
        elapsed = round(time.time() - start, 1)
        print(f"[{serial}] [TRASH] -- Cycle {cycle} ({elapsed}s / {duration}s) --")

        confirmed = _trash_detect_with_voting(
            serial, detector, clean_img, score_threshold=score_threshold
        )

        if not confirmed:
            empty_streak += 1
            print(f"[{serial}] [TRASH] No confirmed trash. ({empty_streak}/{_MAX_EMPTY_STREAK} empty)")
            if empty_streak >= _MAX_EMPTY_STREAK:
                print(f"[{serial}] [TRASH] {_MAX_EMPTY_STREAK} consecutive empty cycles -> stopping early.")
                break
        else:
            empty_streak = 0
            print(f"[{serial}] [TRASH] Tapping {len(confirmed)} trash item(s)...")
            for det in confirmed:
                cx, cy = det.center
                print(f"[{serial}] [TRASH]   -> Tap ({cx}, {cy}) score={det.score}")
                adb_helper.tap(serial, cx, cy)
                total_taps += 1
                _human_delay(_TAP_DELAY)
                # Dismiss pet menu if accidentally tapped a pet
                adb_helper.tap(serial, _DISMISS_POS[0], _DISMISS_POS[1])
                _human_delay(_DISMISS_DELAY)

        _human_delay(_CYCLE_COOLDOWN)

    elapsed_total = round(time.time() - start, 1)
    print(f"[{serial}] === CLEAN TRASH COMPLETE -- {cycle} cycles, {total_taps} taps in {elapsed_total}s ===")
    return _ok()


# ═══════════════════════════════════════════════════════════════════════
#  SEASON POLICIES
# ═══════════════════════════════════════════════════════════════════════

# Popup detection ROI — crop to popup area to avoid false positives from tree icons
_POLICY_POPUP_ROI = (250, 150, 750, 510)


def detect_policy_popup(serial: str, detector: GameStateDetector) -> str:
    """Detect which popup is displayed on the policy screen.

    Checks the popup ROI region for buttons/headers.
    Returns:
        'ENACT'            — ENACT button visible (can research this policy)
        'REQUIREMENTS_GO'  — GO button visible (needs prerequisite)
        'SELECT'           — Governance SELECT header visible
        'LOCKED'           — No actionable popup detected
    """
    frame = detector.get_frame(serial)
    if frame is None:
        return "LOCKED"

    roi = _POLICY_POPUP_ROI
    popup_crop = frame[roi[1]:roi[3], roi[0]:roi[2]]

    # Check ENACT button
    enact = detector.check_activity(serial, target="POLICY_ENACT_BTN", threshold=0.85, frame=popup_crop)
    if enact:
        return "ENACT"

    # Check GO button
    go = detector.check_activity(serial, target="POLICY_GO_BTN", threshold=0.92, frame=popup_crop)
    if go:
        return "REQUIREMENTS_GO"

    # Check SELECT (governance header)
    gov = detector.check_special_state(serial, target="GOVERNANCE_HEADER", threshold=0.85, frame=popup_crop)
    if gov:
        return "SELECT"

    return "LOCKED"


def _tap_policy_enact(serial: str, detector: GameStateDetector) -> dict:
    """Find and tap the ENACT button on the policy popup.

    Returns True if tapped, False if button not found.
    """
    enact = detector.check_activity(serial, target="POLICY_ENACT_BTN", threshold=0.85)
    if enact:
        _, ex, ey = enact
        print(f"[{serial}] [POLICY] Tapping ENACT at ({ex}, {ey})")
        adb_helper.tap(serial, ex, ey)
        _human_delay(2)
        return _ok()
    print(f"[{serial}] [POLICY] ENACT button not found")
    return _fail("TEMPLATE_NO_MATCH: ENACT button not found")


def _tap_policy_go(serial: str, detector: GameStateDetector) -> dict:
    """Find and tap the GO button on the policy popup.

    Returns True if tapped, False if button not found.
    """
    go = detector.check_activity(serial, target="POLICY_GO_BTN", threshold=0.92)
    if go:
        _, gx, gy = go
        print(f"[{serial}] [POLICY] Tapping GO at ({gx}, {gy})")
        adb_helper.tap(serial, gx, gy)
        _human_delay(2)
        return _ok()
    print(f"[{serial}] [POLICY] GO button not found")
    return _fail("TEMPLATE_NO_MATCH: GO button not found")


def process_season_policies(serial: str, detector: GameStateDetector, account_id: str = "default") -> dict:
    """Main entry point for Season Policies automation.

    Runs the PolicyV3Engine in a loop until target is reached or all locked.
    Returns True on meaningful progress, False on failure.
    """
    from backend.config import config as app_config

    print(f"\n[{serial}] ═══════════════════════════════════════════")
    print(f"[{serial}]   SEASON POLICIES — START (account={account_id})")
    print(f"[{serial}] ═══════════════════════════════════════════\n")

    from backend.core.workflow.policy.engine import PolicyV3Engine

    engine = PolicyV3Engine(serial, detector, app_config.adb_path, account_id=account_id)

    max_cycles = 20
    enacted_count = 0

    for cycle in range(max_cycles):
        print(f"\n[{serial}] [POLICY] --- Cycle {cycle + 1}/{max_cycles} ---")
        result = engine.run()
        print(f"[{serial}] [POLICY] Result: {result}")

        if result == "TARGET_REACHED":
            print(f"[{serial}] [POLICY] All target columns completed!")
            break
        elif result == "GOVERNANCE_DONE":
            enacted_count += 1
            # Governance selected — continue loop to enact the policy
        elif result in ("TARGET_ENACTED", "ENACT_SUCCESS"):
            enacted_count += 1
            print(f"[{serial}] [POLICY] Policy enacted — done for this run.")
            break
        elif result == "ALL_LOCKED":
            print(f"[{serial}] [POLICY] All locked — stopping.")
            break
        elif result == "REPLENISH_LOCKED":
            print(f"[{serial}] [POLICY] Not enough points — 24h cooldown.")
            break
        else:
            print(f"[{serial}] [POLICY] Unexpected result: {result}")
            break

    print(f"\n[{serial}] ═══════════════════════════════════════════")
    print(f"[{serial}]   SEASON POLICIES — COMPLETE ({enacted_count} enacted)")
    print(f"[{serial}] ═══════════════════════════════════════════\n")

    print(f"[{serial}] [POLICY] Cleanup: returning safely to IN_CITY lobby...")
    cleanup_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not _is_ok(cleanup_result):
        return _bubble(cleanup_result, "NAV_LOBBY_UNREACHABLE: Could not close Policy screens")

    if result == "REPLENISH_LOCKED":
        return _ok(dynamic_cooldown_sec=86400)  # 24h — not enough points

    return _ok()


# ═══════════════════════════════════════════════════════════════════
#  CONSTRUCTION UPGRADE
# ═══════════════════════════════════════════════════════════════════

def check_builder_slots(serial: str, detector: GameStateDetector) -> dict:
    """
    Checks how many builder slots are free by navigating to Halfling House
    and counting BUILD buttons visible on screen.

    Flow:
      1. go_to_construction("HALFLING_HOUSE")
      2. If "Unlock Permanently" button found → tap → Hire → Confirm (unlock 2nd slot)
      3. Count CONSTRUCTION_BUILD_BTN matches = free slots
         (slots in use show "speedup" instead of "BUILD")

    Returns:
        {
            "free_slots": int,   # 0, 1 or 2
            "total_slots": int,  # 2
            "unlocked_2nd": bool, # True if 2nd slot was unlocked during this call
        }
    """
    result = {"free_slots": 0, "total_slots": 2, "unlocked_2nd": False}

    print(f"[{serial}] === CHECK BUILDER SLOTS ===")

    # 1. Navigate to Halfling House
    construction_result = go_to_construction(serial, detector, "HALFLING_HOUSE")
    if not _is_ok(construction_result):
        print(f"[{serial}] [FAILED] Could not navigate to Halfling House.")
        result["free_slots"] = 1
        return result

    _human_delay(1.0)

    # 2. Check for "Unlock Permanently" button → unlock 2nd builder slot
    unlock_match = detector.check_activity(serial, target="CONSTRUCTION_UNLOCK_PERMANENTLY_BTN", threshold=0.80)
    if unlock_match:
        _, ulx, uly = unlock_match
        print(f"[{serial}] 'Unlock Permanently' found at ({ulx}, {uly}). Tapping to unlock 2nd builder...")
        adb_helper.tap(serial, ulx, uly)
        _human_delay(1.2)

        # Wait for "Hire" button
        hire_match = _detect_with_retry(serial, detector, "CONSTRUCTION_HIRE_BTN", threshold=0.80, attempts=3, delay=0.8)
        if hire_match:
            _, hx, hy = hire_match
            print(f"[{serial}] 'Hire' button found at ({hx}, {hy}). Tapping...")
            adb_helper.tap(serial, hx, hy)
            _human_delay(1.2)

            # Wait for "Confirm" button
            confirm_match = _detect_with_retry(serial, detector, "CONSTRUCTION_CONFIRM_BTN", threshold=0.80, attempts=3, delay=0.8)
            if confirm_match:
                _, cx, cy = confirm_match
                print(f"[{serial}] 'Confirm' button found at ({cx}, {cy}). Tapping...")
                adb_helper.tap(serial, cx, cy)
                _human_delay(1.2)
                result["unlocked_2nd"] = True
                print(f"[{serial}] 2nd builder slot unlocked!")

        if not result["unlocked_2nd"]:
            print(f"[{serial}] [WARNING] Could not complete unlock flow. Continuing with slot count.")
    else:
        print(f"[{serial}] No 'Unlock Permanently' button. 2nd slot already unlocked or not available.")

    # 3. Count BUILD buttons = free slots
    _human_delay(0.5)
    detector._screen_cache = None
    build_positions = detector.find_all_activity_matches(serial, target="CONSTRUCTION_BUILD_BTN", threshold=0.80)
    free_count = len(build_positions)

    result["free_slots"] = min(free_count, result["total_slots"])
    print(f"[{serial}] Builder slots: {result['free_slots']}/{result['total_slots']} free (BUILD buttons found: {free_count})")

    # 4. Press back to exit Halfling House
    adb_helper.press_back(serial)
    _human_delay(0.8)

    return result


def dismiss_promo_popup(serial: str, detector: GameStateDetector) -> dict:
    """
    Dismiss promotional popup by detecting X button in top-right corner.
    ROI: (775, 75) → (850, 150) to avoid false matches.
    Reusable across all workflows that may trigger promo popups.

    Returns True if popup was found and dismissed.
    """
    ROI_X1, ROI_Y1, ROI_X2, ROI_Y2 = 775, 75, 850, 150

    frame = detector.get_frame(serial)
    if frame is None:
        return _fail("ADB_NO_FRAME: Could not capture frame")

    # Crop ROI from frame
    roi_frame = frame[ROI_Y1:ROI_Y2, ROI_X1:ROI_X2]
    if roi_frame.size == 0:
        return _fail("ADB_NO_FRAME: ROI crop is empty")

    # Load template (COLOR to match frame's BGR format)
    template_path = os.path.join(detector.templates_dir, "special", "popup_X_btn.png")
    if not os.path.exists(template_path):
        return _fail("TEMPLATE_NO_MATCH: popup_X_btn.png not found")

    template = cv2.imread(template_path, cv2.IMREAD_COLOR)
    if template is None:
        return _fail("TEMPLATE_NO_MATCH: Could not load popup_X_btn template")

    # Template match within ROI (both BGR)
    result = cv2.matchTemplate(roi_frame, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val >= 0.80:
        # Calculate absolute position from ROI-relative coords
        th, tw = template.shape[:2]
        abs_x = ROI_X1 + max_loc[0] + tw // 2
        abs_y = ROI_Y1 + max_loc[1] + th // 2
        print(f"[{serial}] Promo popup detected (conf={max_val:.3f}). Dismissing at ({abs_x}, {abs_y})...")
        adb_helper.tap(serial, abs_x, abs_y)
        _human_delay(1)
        return _ok()

    return _fail("TEMPLATE_NO_MATCH: No promo popup detected")


def reset_position(serial: str):
    """
    Resets camera position by double-tapping lobby toggle (50, 500).
    Switches IN_CITY ↔ OUT_CITY and back, which recenters the camera.
    """
    print(f"[{serial}] Resetting position...")
    adb_helper.tap(serial, 50, 500)
    _human_delay(1.0)
    adb_helper.tap(serial, 50, 500)
    _human_delay(1.0)
    print(f"[{serial}] -> Position reset.")


_ASSIST_PANEL_ROI = (0, 65, 235, 460)
_ASSIST_PANEL_OPEN_TAP = (38, 370)
_ASSIST_PANEL_EXPAND_ROI = (220, 200, 275, 325)
_ASSIST_HALL_TOGGLE_TAP = (50, 500)


def _workflow_template_path(*parts: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", *parts)


def _normalize_screen_roi(
    roi: tuple[int, int, int, int],
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = roi
    left, right = sorted((int(x1), int(x2)))
    top, bottom = sorted((int(y1), int(y2)))
    return (
        max(0, min(width, left)),
        max(0, min(height, top)),
        max(0, min(width, right)),
        max(0, min(height, bottom)),
    )


def _match_template_path_in_frame(
    frame: np.ndarray,
    template_path: str,
    roi: tuple[int, int, int, int],
    threshold: float = 0.78,
) -> tuple[float, tuple[int, int], tuple[int, int, int, int]] | None:
    if frame is None or not os.path.exists(template_path):
        return None

    height, width = frame.shape[:2]
    x1, y1, x2, y2 = _normalize_screen_roi(roi, width, height)
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    template = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
    if template is None:
        return None
    if len(template.shape) == 3 and template.shape[2] == 4:
        template = template[:, :, :3]

    th, tw = template.shape[:2]
    if crop.shape[0] < th or crop.shape[1] < tw:
        return None

    crop_gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    result = cv2.matchTemplate(crop_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    if max_val < threshold:
        return None

    top_left = (x1 + max_loc[0], y1 + max_loc[1])
    center = (top_left[0] + tw // 2, top_left[1] + th // 2)
    box = (top_left[0], top_left[1], top_left[0] + tw, top_left[1] + th)
    return float(max_val), center, box


def scout_unknown_area(serial: str, detector: GameStateDetector) -> dict:
    """Use the assist panel to explore any visible unknown scout area."""
    panel_expand_tpl = _workflow_template_path("icon_markers", "panel_expand_icon.png")
    scout_icon_tpl = _workflow_template_path("icon_markers", "scout_map_icon.png")
    scout_explore_tpl = _workflow_template_path("icon_markers", "scout_explore_btn.png")

    print(f"[{serial}] === SCOUT UNKNOWN AREA ===")
    lobby_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not _is_ok(lobby_result):
        return _bubble(lobby_result, "NAV_LOBBY_UNREACHABLE: Could not reach IN_CITY before Scout Unknown Area")

    for path in (panel_expand_tpl, scout_icon_tpl, scout_explore_tpl):
        if not os.path.exists(path):
            return _fail(f"TEMPLATE_MISSING: {path}")

    def _capture_frame():
        detector._cache.invalidate()
        return detector.screencap_memory(serial)

    panel_open = False
    for attempt in range(3):
        frame = _capture_frame()
        if frame is None:
            return _fail("ADB_CAPTURE_FAILED: Could not capture screen while opening assist panel")

        match = _match_template_path_in_frame(frame, panel_expand_tpl, _ASSIST_PANEL_EXPAND_ROI, threshold=0.78)
        if match:
            conf, center, _ = match
            print(f"[{serial}] Assist panel confirmed open at {center} (confidence={conf:.3f}).")
            panel_open = True
            break

        print(f"[{serial}] Assist panel not open. Tapping opener {_ASSIST_PANEL_OPEN_TAP} (attempt {attempt + 1}/3)...")
        adb_helper.tap(serial, *_ASSIST_PANEL_OPEN_TAP)
        _human_delay(1.0)

    if not panel_open:
        return _fail("NAV_TARGET_NOT_REACHED: Assist panel did not open")

    x1, y1, x2, y2 = _ASSIST_PANEL_ROI
    max_swipes = 6
    for attempt in range(max_swipes + 1):
        frame = _capture_frame()
        if frame is None:
            return _fail("ADB_CAPTURE_FAILED: Could not capture screen while scanning assist panel")

        scout_match = _match_template_path_in_frame(frame, scout_icon_tpl, _ASSIST_PANEL_ROI, threshold=0.76)
        if scout_match:
            conf, center, box = scout_match
            print(f"[{serial}] Scout map icon found at {center} (confidence={conf:.3f}, box={box}). Tapping...")
            adb_helper.tap(serial, center[0], center[1])
            _human_delay(3.0)

            after_tap_frame = _capture_frame()
            explore_match = (
                _match_template_path_in_frame(
                    after_tap_frame,
                    scout_explore_tpl,
                    (0, 0, after_tap_frame.shape[1], after_tap_frame.shape[0]),
                    threshold=0.76,
                )
                if after_tap_frame is not None
                else None
            )
            if explore_match:
                explore_conf, explore_center, explore_box = explore_match
                print(
                    f"[{serial}] Scout Explore button found at {explore_center} "
                    f"(confidence={explore_conf:.3f}, box={explore_box}). Tapping..."
                )
                adb_helper.tap(serial, explore_center[0], explore_center[1])
                _human_delay(1.5)
            else:
                print(f"[{serial}] Scout Explore button not visible. Continuing cleanup.")

            print(f"[{serial}] Returning to city via Hall toggle {_ASSIST_HALL_TOGGLE_TAP}...")
            adb_helper.tap(serial, *_ASSIST_HALL_TOGGLE_TAP)
            _human_delay(1.0)
            return _ok()

        if attempt >= max_swipes:
            print(f"[{serial}] Scout map icon not found after {max_swipes} light swipes. Treating as already fully scouted.")
            return _ok()

        swipe_x = (x1 + x2) // 2
        swipe_from_y = 360
        swipe_to_y = 220
        print(
            f"[{serial}] Scout icon not visible. Light panel swipe "
            f"({swipe_x}, {swipe_from_y}) -> ({swipe_x}, {swipe_to_y}) ({attempt + 1}/{max_swipes})..."
        )
        adb_helper.swipe(serial, swipe_x, swipe_from_y, swipe_x, swipe_to_y, 1200)
        _human_delay(1.0)

    return _ok()


def _navigate_to_hall_upgrade(
    serial: str,
    detector: GameStateDetector,
    first_hall_tap_swipe: bool = False,
) -> dict:
    """
    Navigates to the Hall upgrade screen using V2 go_to_construction.
    """
    print(f"[{serial}] Navigating to Hall upgrade screen...")
    swipe = (115, 250, 115, 360, 500) if first_hall_tap_swipe else None
    return go_to_construction(
        serial,
        detector,
        "HALL",
        feature="upgrade",
        post_base_tap_swipe=swipe,
    )


def upgrade_construction(serial: str, detector: GameStateDetector, max_depth: int = 5,
                          max_power: int = 0, max_hall_level: int = 0) -> dict:
    """
    Automates construction upgrade starting from Hall.

    Algorithm:
      1. Validate max_power (<= 14M) and max_hall_level (<= 21)
      2. check_builder_slots() → get free_slots
      3. Tap Hall → detect upgrade icon → enter upgrade screen
      4. _try_upgrade_or_go() → recursive

    Supports:
      - Recursive GO chain (Hall → GO → Sub → GO → Sub2 → upgrade)
      - Multi-path (2 GO buttons + 2 free slots → upgrade both paths)
      - max_depth safety limit

    Args:
        max_power: if > 0, skip upgrade when power exceeds this value. Max allowed: 14000000.
        max_hall_level: if > 0, skip upgrade when hall level exceeds this value. Max allowed: 21.

    Returns:
        {
            "upgraded": int,       # constructions upgraded
            "paths_found": int,    # GO paths discovered
            "depth_reached": int,  # deepest GO chain level
        }
    """
    print(f"[{serial}] === UPGRADE CONSTRUCTION (max_depth={max_depth}) ===")

    result = {"ok": True, "upgraded": 0, "paths_found": 0, "depth_reached": 0}

    # NOTE: max_power and max_hall_level are pre-validated by executor via DB check.
    # They are kept as params here for direct-call compatibility.

    # 1. Check builder slots
    builder_info = check_builder_slots(serial, detector)
    remaining_slots = builder_info["free_slots"]

    if remaining_slots <= 0:
        print(f"[{serial}] No free builder slots. Cannot upgrade.")
        return result  # ok=True — no slots is not an error, just nothing to do

    print(f"[{serial}] {remaining_slots} builder slot(s) available for upgrade.")

    # 2. Navigate to Hall upgrade screen
    hall_result = _navigate_to_hall_upgrade(
        serial,
        detector,
        first_hall_tap_swipe=True,
    )
    if not _is_ok(hall_result):
        hall_reason = ""
        if isinstance(hall_result, dict):
            hall_reason = str(hall_result.get("error") or "").strip()
        if hall_reason:
            print(
                f"[{serial}] Hall upgrade path unavailable ({hall_reason}). "
                f"Treating Hall as busy/already upgrading and moving to fallback constructions..."
            )
        else:
            print(
                f"[{serial}] Hall upgrade path unavailable. "
                f"Treating Hall as busy/already upgrading and moving to fallback constructions..."
            )
    else:
        _human_delay(1.0)

        # 3. Recursive upgrade from Hall
        remaining_slots = _try_upgrade_or_go(
            serial,
            detector,
            remaining_slots,
            depth=0,
            max_depth=max_depth,
            result=result,
            allow_go_paths=True,
            root_construction="HALL",
        )

    # 4. Fallback: if slots remain but Hall paths exhausted, try other constructions
    FALLBACK_CONSTRUCTIONS = ["MARKET", "RESEARCH_CENTER"]

    if remaining_slots > 0:
        print(f"[{serial}] Hall paths exhausted but {remaining_slots} slot(s) remaining. Trying fallback constructions...")

        for construction_name in FALLBACK_CONSTRUCTIONS:
            if remaining_slots <= 0:
                break

            print(f"[{serial}] --- Fallback: {construction_name} ---")

            # Navigate to IN_CITY first
            lobby_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
            if not _is_ok(lobby_result):
                print(f"[{serial}] Could not reach IN_CITY for {construction_name}. Skipping.")
                continue

            print(
                f"[{serial}] Resetting camera after Hall swipe before fallback "
                f"navigation to {construction_name}..."
            )
            reset_position(serial)

            # Use V2 go_to_construction to navigate directly to upgrade screen
            fallback_result = go_to_construction(serial, detector, construction_name, feature="upgrade")
            if not _is_ok(fallback_result):
                print(f"[{serial}] No upgrade icon on {construction_name}. Skipping.")
                continue

            _human_delay(0.8)

            # Try upgrade (reuse same recursive logic)
            remaining_slots = _try_upgrade_or_go(
                serial,
                detector,
                remaining_slots,
                depth=0,
                max_depth=max_depth,
                result=result,
                allow_go_paths=False,
                root_construction=construction_name,
            )

            if remaining_slots <= 0:
                print(f"[{serial}] No more slots after {construction_name}.")
                break

    print(f"[{serial}] === UPGRADE CONSTRUCTION COMPLETE ===")
    print(f"[{serial}]   Upgraded: {result['upgraded']}")
    print(f"[{serial}]   Paths found: {result['paths_found']}")
    print(f"[{serial}]   Depth reached: {result['depth_reached']}")

    return result


def _try_upgrade_or_go(
    serial: str,
    detector: GameStateDetector,
    remaining_slots: int,
    depth: int,
    max_depth: int,
    result: dict,
    allow_go_paths: bool = True,
    root_construction: str = "HALL",
) -> int:
    """
    Inner recursive function for upgrade_construction.
    At the current construction screen, checks for upgrade button or GO buttons.

    Returns updated remaining_slots count.
    """
    if remaining_slots <= 0:
        print(f"[{serial}] [depth={depth}] No remaining builder slots. Stopping.")
        return remaining_slots

    if depth > max_depth:
        print(f"[{serial}] [WARNING] Max depth {max_depth} reached. Aborting GO chain.")
        return remaining_slots

    result["depth_reached"] = max(result["depth_reached"], depth)

    print(f"[{serial}] [depth={depth}] Checking construction screen... (remaining_slots={remaining_slots})")

    # --- Case 1: Check for UPGRADE button ---
    upgrade_match = detector.check_activity(serial, target="CONSTRUCTION_UPGRADE_BTN", threshold=0.85)
    if upgrade_match:
        _, ux, uy = upgrade_match
        print(f"[{serial}] [depth={depth}] UPGRADE button found at ({ux}, {uy})! Tapping...")
        adb_helper.tap(serial, ux, uy)
        _human_delay(2.0)  # Upgrade animation takes time

        # Edge case: insufficient RSS → popup with MULTI-USE button appears
        rss_popup = detector.check_activity(serial, target="RSS_MULTI_USE_BTN", threshold=0.80)
        if rss_popup:
            _, mx, my = rss_popup
            print(f"[{serial}] [depth={depth}] RSS shortage detected! MULTI-USE button at ({mx}, {my}). Tapping...")
            adb_helper.tap(serial, mx, my)
            _human_delay(1.5)

            # Confirm popup
            confirm_match = detector.check_activity(serial, target="RSS_CONFIRM_BTN", threshold=0.80)
            if confirm_match:
                _, cx, cy = confirm_match
                print(f"[{serial}] [depth={depth}] Tapping CONFIRM at ({cx}, {cy})...")
                adb_helper.tap(serial, cx, cy)
                _human_delay(2.0)

                # Check if popup is still there (not enough items → popup stays)
                still_popup = detector.check_activity(serial, target="RSS_MULTI_USE_BTN", threshold=0.80)
                if still_popup:
                    print(f"[{serial}] [depth={depth}] RSS still insufficient after using items. Closing popup...")
                    adb_helper.press_back(serial)
                    _human_delay(1.0)
                    adb_helper.press_back(serial)
                    _human_delay(1.0)
                    return remaining_slots  # Don't count as upgraded
                else:
                    print(f"[{serial}] [depth={depth}] RSS items used! Re-tapping UPGRADE button...")
                    _human_delay(1.0)
                    # Re-tap UPGRADE button (back on upgrade screen now)
                    retry_upgrade = detector.check_activity(serial, target="CONSTRUCTION_UPGRADE_BTN", threshold=0.85)
                    if retry_upgrade:
                        _, rux, ruy = retry_upgrade
                        adb_helper.tap(serial, rux, ruy)
                        _human_delay(2.0)
                    else:
                        print(f"[{serial}] [depth={depth}] UPGRADE button not found after RSS use. Aborting.")
                        return remaining_slots
            else:
                print(f"[{serial}] [depth={depth}] CONFIRM button not found. Closing popup...")
                adb_helper.press_back(serial)
                _human_delay(1.0)
                return remaining_slots  # Don't count as upgraded

        result["upgraded"] += 1
        remaining_slots -= 1
        print(f"[{serial}] [depth={depth}] Construction upgraded! (total upgraded: {result['upgraded']}, remaining_slots: {remaining_slots})")

        # Dismiss any promo popup that appears after upgrade
        _human_delay(0.8)
        dismiss_promo_popup(serial, detector)

        # Get alliance help after upgrade.
        # Only true Hall-root upgrades should tap the Hall coordinates.
        current_root = str(root_construction or "HALL").upper()
        if depth == 0 and current_root == "HALL":
            from backend.core.workflow.construction_data import CONSTRUCTION_TAPS
            hall_coords = CONSTRUCTION_TAPS["HALL"][0]
            print(f"[{serial}] Requesting alliance help (Hall @ {hall_coords})...")
            adb_helper.tap(serial, hall_coords[0], hall_coords[1])
        else:
            print(
                f"[{serial}] Requesting alliance help "
                f"(root={current_root}, depth={depth})..."
            )
            adb_helper.tap(serial, 475, 275)
        _human_delay(0.8)

        # Reset camera position after upgrade
        reset_position(serial)

        return remaining_slots

    if not allow_go_paths:
        print(
            f"[{serial}] [depth={depth}] No UPGRADE button on fallback construction. "
            "Skipping GO paths to avoid looping back into Hall requirements."
        )
        return remaining_slots

    # --- Case 2: Check for GO button(s) ---
    print(f"[{serial}] [depth={depth}] No UPGRADE button. Checking for GO button(s)...")

    # Use dedicated construction GO button template
    go_positions = detector.find_all_activity_matches(serial, target="CONSTRUCTION_GO_BTN", threshold=0.85)

    if not go_positions:
        print(f"[{serial}] [depth={depth}] No GO button found either. Cannot upgrade this construction.")
        return remaining_slots

    result["paths_found"] += len(go_positions)
    print(f"[{serial}] [depth={depth}] Found {len(go_positions)} GO button(s).")

    # Process each GO path (limited by remaining slots)
    for go_idx, (gx, gy) in enumerate(go_positions):
        if remaining_slots <= 0:
            print(f"[{serial}] [depth={depth}] No more builder slots. Skipping remaining paths.")
            break

        print(f"[{serial}] [depth={depth}] --- GO Path {go_idx + 1}/{len(go_positions)} at ({gx}, {gy}) ---")

        # Tap GO button → game camera pans to the sub-construction on map
        adb_helper.tap(serial, gx, gy)
        _human_delay(1.5)  # Camera pan animation

        # After GO, screen shows map with the target construction highlighted.
        # Detect CONSTRUCTION_UPGRADE_ICON to tap into it.
        detector._screen_cache = None
        icon_match = detector.check_activity(serial, target="CONSTRUCTION_UPGRADE_ICON", threshold=0.80)
        if not icon_match:
            _human_delay(0.6)
            icon_match = _detect_with_retry(serial, detector, "CONSTRUCTION_UPGRADE_ICON", threshold=0.80, attempts=2, delay=0.8)

        if not icon_match:
            print(f"[{serial}] [depth={depth}] [WARNING] Could not find upgrade icon after GO. Skipping this path.")
            reset_position(serial)
            if go_idx + 1 < len(go_positions) and remaining_slots > 0:
                if _is_ok(_navigate_to_hall_upgrade(serial, detector)):
                    _human_delay(0.8)
            continue

        _, ix, iy = icon_match
        print(f"[{serial}] [depth={depth}] Upgrade icon found at ({ix}, {iy}). Tapping to enter construction...")
        adb_helper.tap(serial, ix, iy)
        _human_delay(1.0)

        # Recurse into sub-construction
        remaining_slots = _try_upgrade_or_go(
            serial,
            detector,
            remaining_slots,
            depth + 1,
            max_depth,
            result,
            allow_go_paths=allow_go_paths,
            root_construction=root_construction,
        )

        # If more paths to process AND slots available, go back to Hall
        if go_idx + 1 < len(go_positions) and remaining_slots > 0:
            print(f"[{serial}] [depth={depth}] Going back to Hall for next GO path...")
            hall_retry = _navigate_to_hall_upgrade(serial, detector)
            if not _is_ok(hall_retry):
                print(f"[{serial}] [depth={depth}] [FAILED] Could not return to Hall upgrade screen.")
                break
            _human_delay(0.8)

    return remaining_slots


# ── Quest Reward Claim ─────────────────────────────────────────

# Tab coordinates (fixed, vertical left side)
QUEST_TAB_COORDS = {
    "quest":       (80, 175),
    "challenges":  (80, 265),
    "dark_chests": (80, 360),
}

MAX_CLAIMS_PER_TAB = 20  # Safety cap to prevent infinite loop


def _claim_all_in_tab(serial: str, detector: GameStateDetector, tab_name: str) -> int:
    """
    Claim all available rewards in the current tab.
    Game pushes unclaimed quests up after each claim, so we loop:
      detect first Claim btn → tap → re-check → repeat.
    Returns number of claims made.
    """
    claimed = 0

    for attempt in range(MAX_CLAIMS_PER_TAB):
        detector._screen_cache = None
        matches = detector.find_all_activity_matches(
            serial, target="QUEST_CLAIM_BTN", threshold=0.8
        )

        if not matches:
            print(f"[{serial}] [{tab_name}] No more Claim buttons found. Total claimed: {claimed}")
            break

        # Tap the first (topmost) Claim button
        cx, cy = matches[0]
        print(f"[{serial}] [{tab_name}] Claim #{claimed + 1} at ({cx}, {cy}) — {len(matches)} visible")
        adb_helper.tap(serial, cx, cy)
        _human_delay(1.5)
        claimed += 1

    return claimed


def claim_quest_reward(serial: str, detector: GameStateDetector) -> dict:
    """
    Claim Quest Reward Workflow:
    1. Navigate to IN_CITY lobby
    2. Tap Events icon (35, 100) → verify QUEST_MENU
    3. Process Quest tab — claim all available rewards
    4. Process Challenges tab — claim all available rewards
    5. Dark Chests tab — #TODO (placeholder)
    6. Press back → return
    """
    print(f"[{serial}] === CLAIM QUEST REWARD ===")

    # ── Phase 1: Navigate to Lobby ──
    result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not _is_ok(result):
        return _bubble(result, "NAV_LOBBY_UNREACHABLE: Could not reach IN_CITY")

    # ── Phase 2: Open Quest Menu ──
    print(f"[{serial}] Opening Events menu (35, 100)...")
    adb_helper.tap(serial, 35, 100)

    # Poll a few frames before retrying. A second tap on the same spot can
    # close the Quest menu if it already opened but the first frame missed it.
    quest_screen = wait_for_state(
        serial,
        detector,
        ["QUEST_MENU"],
        timeout_sec=10,
        check_mode="special",
    )
    if not quest_screen:
        detector._cache.invalidate()
        current_state = detector.check_state(serial)
        if current_state == "IN-GAME LOBBY (IN_CITY)":
            print(f"[{serial}] QUEST_MENU not detected. Still in IN_CITY, retrying tap (35, 100)...")
            adb_helper.tap(serial, 35, 100)
            quest_screen = wait_for_state(
                serial,
                detector,
                ["QUEST_MENU"],
                timeout_sec=10,
                check_mode="special",
            )
        else:
            print(f"[{serial}] QUEST_MENU not detected, but current state is {current_state}. Skipping retry tap to avoid closing an opened menu.")

        if not quest_screen:
            print(f"[{serial}] [FAILED] Could not open Quest Menu.")
            return _fail("NAV_TARGET_NOT_REACHED: Could not open Quest Menu")

    print(f"[{serial}] Quest Menu confirmed.")
    total_claimed = 0

    # ── Phase 3: Quest Tab ──
    qx, qy = QUEST_TAB_COORDS["quest"]
    print(f"[{serial}] Switching to Quest tab ({qx}, {qy})...")
    adb_helper.tap(serial, qx, qy)
    _human_delay(1.0)

    quest_claimed = _claim_all_in_tab(serial, detector, "Quest")
    total_claimed += quest_claimed
    print(f"[{serial}] Quest tab done — claimed {quest_claimed} reward(s).")

    # ── Phase 4: Challenges Tab (has 3 sub-tabs) ──
    cx, cy = QUEST_TAB_COORDS["challenges"]
    print(f"[{serial}] Switching to Challenges tab ({cx}, {cy})...")
    adb_helper.tap(serial, cx, cy)
    _human_delay(1.0)

    # Sub-tab coordinates: tab 1 is already open, only need to click tab 2 & 3
    CHALLENGES_SUB_TABS = [
        ("Challenges-1", None),           # Already open by default
        ("Challenges-2", (510, 210)),
        ("Challenges-3", (685, 210)),
    ]

    challenges_claimed = 0
    for sub_name, sub_coord in CHALLENGES_SUB_TABS:
        if sub_coord:
            sx, sy = sub_coord
            print(f"[{serial}] Switching to {sub_name} ({sx}, {sy})...")
            adb_helper.tap(serial, sx, sy)
            _human_delay(1.0)

        sub_claimed = _claim_all_in_tab(serial, detector, sub_name)
        challenges_claimed += sub_claimed

    total_claimed += challenges_claimed
    print(f"[{serial}] Challenges tab done — claimed {challenges_claimed} reward(s) across 3 sub-tabs.")

    # ── Phase 5: Dark Chests Tab (#TODO) ──
    # dcx, dcy = QUEST_TAB_COORDS["dark_chests"]
    # adb_helper.tap(serial, dcx, dcy)
    # _human_delay(1.0)
    # TODO: Implement Dark Chests logic

    # ── Phase 6: Cleanup ──
    print(f"[{serial}] === CLAIM QUEST REWARD COMPLETE — total {total_claimed} reward(s) claimed ===")
    cleanup_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not _is_ok(cleanup_result):
        return _bubble(cleanup_result, "NAV_LOBBY_UNREACHABLE: Could not close Quest screen")
    return _ok()


def claim_daily_gift_and_buy_vip_store(serial: str, detector: GameStateDetector) -> dict:
    """
    Claim Daily Gift + Buy VIP Store Items (weekly):
    1. Navigate to Alliance Menu (go_to_alliance)
    2. Tap Store tab (fixed x,y)
    3. Detect VIP Store icon (template) → tap to claim daily reward
    4. Switch to Store tab → buy 4 VIP Store items (fixed x,y per item)

    Coordinates marked with TODO are placeholders — fill in after capturing actual values.
    """
    print(f"[{serial}] === CLAIM DAILY GIFT + BUY VIP STORE ===")

    # ── Coordinate config (TODO: fill real values) ──
    STORE_TAB_TAP = (0, 0)              # TODO: fill x,y — Store tab inside Alliance Menu
    VIP_CLAIM_REWARD_TAP = (0, 0)       # TODO: fill x,y — Claim reward button position
    VIP_STORE_TAB_TAP = (0, 0)          # TODO: fill x,y — VIP Store sub-tab inside Store

    # 4 VIP Store items to buy (item tap → then confirm buy)
    VIP_ITEMS = [
        {"name": "Item 1", "tap": (0, 0)},  # TODO: fill x,y
        {"name": "Item 2", "tap": (0, 0)},  # TODO: fill x,y
        {"name": "Item 3", "tap": (0, 0)},  # TODO: fill x,y
        {"name": "Item 4", "tap": (0, 0)},  # TODO: fill x,y
    ]
    CONFIRM_BUY_TAP = (0, 0)            # TODO: fill x,y — Confirm buy button after selecting item

    # ── Phase 1: Navigate to Alliance Menu ──
    result = go_to_alliance(serial, detector)
    if not _is_ok(result):
        return _bubble(result, "NAV_TARGET_NOT_REACHED: Could not open Alliance Menu")

    # ── Phase 2: Tap Store tab ──
    print(f"[{serial}] Tapping Store tab {STORE_TAB_TAP}...")
    adb_helper.tap(serial, STORE_TAB_TAP[0], STORE_TAB_TAP[1])
    _human_delay(2.0)

    # ── Phase 3: Detect VIP Store icon & Claim daily reward ──
    print(f"[{serial}] Detecting VIP Store icon...")
    vip_icon = _detect_with_retry(serial, detector, "VIP_STORE_ICON", threshold=0.8, attempts=3, delay=1)

    if not vip_icon:
        print(f"[{serial}] [WARNING] VIP_STORE_ICON not detected. Skipping claim, proceeding to buy.")
    else:
        _, vx, vy = vip_icon
        print(f"[{serial}] VIP Store icon found at ({vx}, {vy}). Tapping to enter...")
        adb_helper.tap(serial, vx, vy)
        _human_delay(2.0)

        # Claim daily reward
        print(f"[{serial}] Claiming daily reward at {VIP_CLAIM_REWARD_TAP}...")
        adb_helper.tap(serial, VIP_CLAIM_REWARD_TAP[0], VIP_CLAIM_REWARD_TAP[1])
        _human_delay(2.0)

        # Dismiss any reward popup
        print(f"[{serial}] Dismissing reward popup (50, 500)...")
        adb_helper.tap(serial, 50, 500)
        _human_delay(1.5)

        print(f"[{serial}] Daily gift claimed.")

    # ── Phase 4: Buy VIP Store items (4 items) ──
    print(f"[{serial}] Switching to VIP Store tab {VIP_STORE_TAB_TAP}...")
    adb_helper.tap(serial, VIP_STORE_TAB_TAP[0], VIP_STORE_TAB_TAP[1])
    _human_delay(2.0)

    items_bought = 0
    for idx, item in enumerate(VIP_ITEMS):
        item_name = item["name"]
        ix, iy = item["tap"]
        print(f"[{serial}] --- Buying {item_name} ({idx+1}/{len(VIP_ITEMS)}) at ({ix}, {iy}) ---")

        # Tap item
        adb_helper.tap(serial, ix, iy)
        _human_delay(1.5)

        # Confirm purchase
        print(f"[{serial}] Confirming purchase at {CONFIRM_BUY_TAP}...")
        adb_helper.tap(serial, CONFIRM_BUY_TAP[0], CONFIRM_BUY_TAP[1])
        _human_delay(2.0)

        # Dismiss result popup
        adb_helper.tap(serial, 50, 500)
        _human_delay(1.0)

        items_bought += 1
        print(f"[{serial}] {item_name} purchased ({items_bought}/{len(VIP_ITEMS)}).")

    # ── Phase 5: Cleanup ──
    print(f"[{serial}] VIP Store done — claimed gift + bought {items_bought} item(s).")
    cleanup_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not _is_ok(cleanup_result):
        return _bubble(cleanup_result, "NAV_LOBBY_UNREACHABLE: Could not close VIP Store screen")
    return _ok()



def buy_merchant_items(serial: str, detector: GameStateDetector, max_refreshes: int = 2) -> dict:
    """
    Buy Merchant Items Workflow:
    1. Navigate to Alliance Menu (go_to_alliance)
    2. Tap Store button (fixed coordinates)
    3. Verify Goblin Merchant icon
    4. Scan visible 2x4 grid → detect RSS-priced items → tap to buy
    5. Scroll down → scan remaining 2x4 grid → buy
    6. Reroll → repeat steps 4-5 once more
    7. Cleanup & return

    Grid layout: 4 columns x 4 rows. Screen shows 2 rows at a time.
    Only buys items priced with RSS (3 template variants).

    Args:
        max_refreshes: Number of reroll rounds (default 2 = 1 initial + 1 reroll).
    """
    # ── Fixed Coordinates ──
    STORE_TAP = (735, 458)              # Store button inside Alliance Menu
    REROLL_TAP = (725, 130)             # Reroll button at top of merchant store
    RSS_TARGETS = [
        "MERCHANT_RSS_ITEM_1",
        "MERCHANT_RSS_ITEM_2",
        "MERCHANT_RSS_ITEM_3",
    ]
    # Shift tap slightly right from detected RSS icon to trigger buy action.
    CARD_TAP_X_OFFSET = 20
    MAX_ROUNDS = max(1, max_refreshes)  # At least 1 initial scan

    print(f"[{serial}] === BUY MERCHANT ITEMS ===")

    # ── Enable diagnostics for all detector calls ──
    detector.diagnostic_mode = True
    detector.clear_diagnostics()

    # ── Phase 1: Navigate to Alliance ──
    result = go_to_alliance(serial, detector)
    if not _is_ok(result):
        return _bubble(result, "NAV_TARGET_NOT_REACHED: Could not open Alliance Menu")

    # ── Phase 2: Tap Store ──
    sx, sy = STORE_TAP
    print(f"[{serial}] Tapping Store ({sx}, {sy})...")
    adb_helper.tap(serial, sx, sy)
    _human_delay(2.0)

    # ── Phase 3: Verify Goblin Merchant ──
    merchant = _detect_with_retry(
        serial, detector, "GOBLIN_MERCHANT_ICON",
        threshold=0.8, attempts=3, delay=1.5,
    )
    if not merchant:
        print(f"[{serial}] Goblin Merchant not available (on cooldown). Skipping.")
        swipe_duration = random.randint(650, 1150)
        print(
            f"[{serial}] Swiping store panel lightly before cleanup "
            f"(duration={swipe_duration}ms)..."
        )
        adb_helper.swipe(serial, 480, 360, 480, 180, swipe_duration)
        _human_delay(random.uniform(0.8, 1.3))
        cleanup_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
        if not _is_ok(cleanup_result):
            return _bubble(cleanup_result, "NAV_LOBBY_UNREACHABLE: Could not close Merchant cooldown screen")
        return _ok(dynamic_cooldown_sec=3600)

    _, mx, my = merchant
    print(f"[{serial}] Goblin Merchant found at ({mx}, {my}). Tapping to enter shop...")
    adb_helper.tap(serial, mx, my)
    _human_delay(2.0)

    # ── Phase 4: Buy loop (initial + reroll) ──
    total_bought = 0

    for round_idx in range(MAX_ROUNDS):
        round_label = "Initial" if round_idx == 0 else f"Reroll #{round_idx}"
        print(f"[{serial}] --- {round_label} Round ---")

        # ── Scan top 2x4 (visible grid) ──
        half_bought = _scan_and_buy_rss_items(serial, detector, RSS_TARGETS, "top", CARD_TAP_X_OFFSET)
        total_bought += half_bought

        # ── Scroll down to reveal bottom 2x4 ──
        print(f"[{serial}] Scrolling down to reveal bottom rows...")
        adb_helper.swipe(serial, 480, 400, 480, 100, 600)
        _human_delay(2.0)

        # ── Scan bottom 2x4 ──
        half_bought = _scan_and_buy_rss_items(serial, detector, RSS_TARGETS, "bottom", CARD_TAP_X_OFFSET)
        total_bought += half_bought

        # ── Scroll back up + Reroll (skip on last round) ──
        if round_idx < MAX_ROUNDS - 1:
            # Scroll back up — bottom scan left the store scrolled down
            print(f"[{serial}] Scrolling up to restore store position...")
            adb_helper.swipe(serial, 480, 200, 480, 400, 600)
            _human_delay(1.5)

            rx, ry = REROLL_TAP
            print(f"[{serial}] Tapping Reroll ({rx}, {ry})...")
            adb_helper.tap(serial, rx, ry)
            _human_delay(1.5)

            # Confirm reroll popup
            print(f"[{serial}] Confirming reroll...")
            adb_helper.tap(serial, 380, 370)
            _human_delay(2.0)

    # ── Phase 5: Diagnostic Report ──
    print(f"\n[{serial}] === BUY MERCHANT ITEMS COMPLETE — bought {total_bought} item(s) ===")

    diag_entries = detector.get_diagnostics()
    if diag_entries:
        print(f"\n[{serial}] ┌{'─' * 58}┐")
        print(f"[{serial}] │  📊 MERCHANT DIAGNOSTIC REPORT{' ' * 27}│")
        print(f"[{serial}] ├{'─' * 58}┤")

        # Group by target
        from collections import defaultdict
        by_target = defaultdict(list)
        for e in diag_entries:
            by_target[e.target].append(e)

        for target in sorted(by_target.keys()):
            entries = by_target[target]
            confs = [e.confidence for e in entries]
            hits = [e for e in entries if e.matched]
            best = max(confs)
            avg = sum(confs) / len(confs)
            status = "✅" if hits else "❌"

            print(f"[{serial}] │ {status} {target:35s}              │")
            print(f"[{serial}] │    calls={len(entries):2d}  hits={len(hits):2d}  best={best:.3f}  avg={avg:.3f}   │")

            # Recommend optimal threshold
            if hits:
                min_hit = min(e.confidence for e in hits)
                recommended = round(min_hit - 0.03, 2)
                print(f"[{serial}] │    💡 min_hit={min_hit:.3f} → recommend thr={recommended:.2f}{' ' * 10}│")
            elif best > 0.5:
                recommended = round(best - 0.02, 2)
                print(f"[{serial}] │    ⚠️  never matched! best={best:.3f} → try thr={recommended:.2f}{' ' * 3}│")

        # Timing
        total_ms = sum(e.time_ms for e in diag_entries)
        slowest = max(diag_entries, key=lambda e: e.time_ms)
        print(f"[{serial}] ├{'─' * 58}┤")
        print(f"[{serial}] │  ⏱  Total detection time: {total_ms:.0f}ms{' ' * (30 - len(f'{total_ms:.0f}'))}│")
        print(f"[{serial}] │  🐢 Slowest: {slowest.target} ({slowest.time_ms:.0f}ms){' ' * max(0, 43 - len(f'{slowest.target} ({slowest.time_ms:.0f}ms)'))}│")
        print(f"[{serial}] └{'─' * 58}┘")

    detector.diagnostic_mode = False

    # ── Cleanup ──
    cleanup_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not _is_ok(cleanup_result):
        return _bubble(cleanup_result, "NAV_LOBBY_UNREACHABLE: Could not close Merchant shop")
    return _ok()


def _scan_and_buy_rss_items(
    serial: str,
    detector: GameStateDetector,
    rss_targets: list,
    grid_half: str,
    x_offset: int = 0,
) -> int:
    """
    Fast multi-buy: find ALL RSS-priced items at once, tap them rapidly,
    then re-scan once to catch any that appeared after grid shifted.
    Total: 2 scan passes max.
    """
    THRESHOLD = 0.75
    MAX_PASSES = 2
    TAP_DELAY = 0.4  # Fast tap between items

    bought = 0

    for pass_idx in range(MAX_PASSES):
        pass_label = f"pass{pass_idx + 1}"
        detector._screen_cache = None
        frame = detector.screencap_memory(serial)
        if frame is None:
            print(f"[{serial}] [{grid_half}] Screencap failed.")
            break

        # Collect ALL matches across all RSS targets
        all_hits = []
        for target in rss_targets:
            matches = detector.find_all_activity_matches(
                serial, target=target, threshold=THRESHOLD
            )
            for cx, cy in matches:
                all_hits.append((target, cx, cy))

        if not all_hits:
            print(f"[{serial}] [{grid_half}] [{pass_label}] No RSS items found.")
            break

        print(f"[{serial}] [{grid_half}] [{pass_label}] Found {len(all_hits)} RSS item(s) — buying all:")

        # Tap all matches rapidly
        for target, cx, cy in all_hits:
            tap_x = cx + x_offset
            print(f"[{serial}] [{grid_half}]   → {target} at ({tap_x}, {cy})")
            adb_helper.tap(serial, tap_x, cy)
            _human_delay(TAP_DELAY)

        bought += len(all_hits)
        print(f"[{serial}] [{grid_half}] [{pass_label}] Bought {len(all_hits)}, total={bought}")

        # Wait for grid to settle before re-scan
        if pass_idx < MAX_PASSES - 1:
            _human_delay(1.0)

    return bought


def claim_daily_vip_reward(serial: str, detector: GameStateDetector) -> dict:
    """
    Claim Daily VIP Reward from Alliance Store → Honorary Membership.

    Flow:
      1. Navigate to Alliance Menu (go_to_alliance)
      2. Tap Store button (735, 458)
      3. Tap Honorary Membership (320, 500)
      4. Tap Claim reward (715, 425)
      5. Cleanup & return
    """
    STORE_TAP = (735, 458)
    HONORARY_MEMBERSHIP_TAP = (320, 500)
    CLAIM_TAP = (715, 425)

    print(f"[{serial}] === CLAIM DAILY VIP REWARD ===")

    # Phase 1: Navigate to Alliance
    result = go_to_alliance(serial, detector)
    if not _is_ok(result):
        return _bubble(result, "NAV_TARGET_NOT_REACHED: Could not open Alliance Menu")

    # Phase 2: Tap Store
    sx, sy = STORE_TAP
    print(f"[{serial}] Tapping Store ({sx}, {sy})...")
    adb_helper.tap(serial, sx, sy)
    _human_delay(2.0)

    # Phase 3: Detect & Tap Honorary Membership
    honorary = _detect_with_retry(
        serial, detector, "HONORARY_MEMBERSHIP_ICON",
        threshold=0.75, attempts=3, delay=1.5,
    )
    if honorary:
        _, hx, hy = honorary
        print(f"[{serial}] Honorary Membership found at ({hx}, {hy}). Tapping...")
        adb_helper.tap(serial, hx, hy)
    else:
        # Fallback to fixed coordinates
        hx, hy = HONORARY_MEMBERSHIP_TAP
        print(f"[{serial}] Honorary Membership not detected — fallback tap ({hx}, {hy})")
        adb_helper.tap(serial, hx, hy)
    _human_delay(2.0)

    # Phase 4: Tap Claim
    cx, cy = CLAIM_TAP
    print(f"[{serial}] Tapping Claim reward ({cx}, {cy})...")
    adb_helper.tap(serial, cx, cy)
    _human_delay(2.0)

    # Phase 5: Cleanup
    print(f"[{serial}] === CLAIM DAILY VIP REWARD COMPLETE ===")
    cleanup_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not _is_ok(cleanup_result):
        return _bubble(cleanup_result, "NAV_LOBBY_UNREACHABLE: Could not close Daily VIP Reward screen")
    return _ok()


def back_to_lobby_end_workflow(serial: str, detector: GameStateDetector) -> dict:
    """
    Fast back-to-lobby by detecting the back arrow (top-left, ROI 50×50)
    and tapping it at max speed until reaching the lobby.

    Speed-optimized: only checks BACK_ARROW each loop (~3ms with ROI).
    Only calls the expensive check_state() when no arrow is found,
    to confirm we've actually reached the lobby.

    Template: templates/special/back_btn.png
    """
    MAX_TAPS = 15
    TAP_DELAY = 0.15  # Max speed — arrow detection is fast with tiny ROI
    THRESHOLD = 0.75
    LOBBY_STATES = ("IN-GAME LOBBY (IN_CITY)", "IN-GAME LOBBY (OUT_CITY)")

    print(f"[{serial}] === BACK TO LOBBY (end workflow) ===")

    for i in range(MAX_TAPS):
        detector._screen_cache = None
        frame = detector.screencap_memory(serial)
        if frame is None:
            adb_helper.press_back(serial)
            _human_delay(TAP_DELAY)
            continue

        # Fast path: check only BACK_ARROW (tiny ROI = ~3ms)
        match = detector.check_activity(
            serial, target="BACK_ARROW", threshold=THRESHOLD, frame=frame
        )

        if match:
            _, bx, by = match
            print(f"[{serial}] [{i+1}] ← Back arrow ({bx},{by})")
            adb_helper.tap(serial, bx, by)
            _human_delay(TAP_DELAY)
            continue

        # Slow path: no arrow found → check if we reached lobby
        detector._screen_cache = frame
        state = detector.check_state(serial)
        if state in LOBBY_STATES:
            print(f"[{serial}] ✅ Lobby reached after {i} taps ({state})")
            return _ok()

        # Not lobby and no arrow — press_back as fallback
        print(f"[{serial}] [{i+1}] No arrow, not lobby ({state}) — press_back")
        adb_helper.press_back(serial)
        _human_delay(TAP_DELAY)

    print(f"[{serial}] Max {MAX_TAPS} taps reached.")
    adb_helper.press_back(serial)
    _human_delay(0.5)
    return _ok()

