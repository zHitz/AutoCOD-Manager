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
import adb_helper
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
        # Check Global first (more specific, .gp won't match .gp.vn substring)
        for pkg in sorted(PACKAGE_PROVIDERS.keys(), key=len):
            if f"package:{pkg}" in out:
                return PACKAGE_PROVIDERS[pkg]
    except Exception:
        pass
    return DEFAULT_PROVIDER


# Global cache to store the last screenshot hash/image for freeze detection
_FREEZE_CACHE = {}

import threading
from datetime import datetime

_KNOWN_LOG_LEVELS = {
    "ERROR",
    "WARNING",
    "FAILED",
    "TIMEOUT",
    "FATAL",
    "CRASH DETECTED",
}


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
    builtins.print(_format_output_message(message), end=end, file=file, flush=flush)


def _exit_with_log(serial: str, level: str, message: str):
    raise SystemExit(_format_output_message(f"[{serial}] [{level}] {message}"))


# ── Debug Context ───────────────────────────────────────────
# Detectors stored in module-level dict (shared across all threads).
# _debug_last_serial is a module-level fallback for asyncio.to_thread()
# worker threads where threading.local won't have the serial.

_debug_detectors = {}          # {serial: detector}
_debug_last_serial = ""        # fallback for worker threads

def _set_debug_context(serial: str, detector):
    """Called by executor at the start of each workflow execution."""
    global _debug_last_serial
    _debug_detectors[serial] = detector
    _debug_last_serial = serial


def _activate_debug_serial(serial: str):
    """Explicitly set serial for current thread (optional, for concurrency)."""
    global _debug_last_serial
    _debug_last_serial = serial


def _capture_debug_screenshot(error_code: str) -> str:
    """Capture screenshot at moment of failure. Returns saved file path or empty string."""
    serial = _debug_last_serial
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
        time.sleep(10)
        return False
    return True

def check_app_crash(serial: str, package_name: str = "", adb_path: str = config.adb_path) -> bool:
    """
    Checks if the game has crashed, frozen, or been pushed to the background.
    Returns True if crashed/not in foreground/frozen, False if running normally.
    """
    try:
        # 1. Check PID
        res = adb_helper._run_adb(["shell", "pidof", package_name], serial=serial)
        if not res or not res.strip().isdigit():
            print(f"[{serial}] [CRASH DETECTED] App {package_name} is not running (No PID).")
            return True
            
        # 2. Check if it's the foreground app
        out = adb_helper._run_adb(["shell", "dumpsys", "window", "windows"], serial=serial)
        is_foreground = False
        for line in out.splitlines():
            if "mCurrentFocus" in line:
                if package_name in line:
                    is_foreground = True
                break
                
        if not is_foreground:
            print(f"[{serial}] [CRASH DETECTED] App {package_name} is not in foreground.")
            return True
            
        # 3. Check for Engine Freeze (screen hasn't changed a single pixel)
        # We take a fast, low-res screencap (e.g. 1/4 size) to compare.
        import subprocess
        proc = subprocess.run([adb_path, "-s", serial, "exec-out", "screencap", "-p"], capture_output=True)
        if proc.returncode == 0 and len(proc.stdout) > 1000:
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
                        # Wait for 6 consecutive checks (60 seconds) before declaring a freeze
                        # to account for long loading screens
                        if _FREEZE_CACHE[serial]["freeze_count"] >= 6:
                            print(f"[{serial}] [CRASH DETECTED] Game engine is completely FROZEN (0 pixel change for 60s).")
                            return True
                    else:
                        # Screen changed, reset freeze counter
                        _FREEZE_CACHE[serial]["freeze_count"] = 0
                    
                    _FREEZE_CACHE[serial]["img"] = small
                    
        return False
    except Exception as e:
        print(f"[{serial}] [WARNING] Error checking crash state: {e}")
        return False


def startup_to_lobby(serial: str, detector: GameStateDetector, package_name: str, adb_path: str = config.adb_path, load_timeout: int = 120) -> dict:
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
        print(f"[{serial}] App was not running. Waiting for game to load into Lobby...")
        lobby = wait_for_state(serial, detector, LOBBY_STATES, timeout_sec=load_timeout)
        if not lobby:
            print(f"[{serial}] [FAILED] Game did not load into Lobby after {load_timeout}s.")
            return _fail(f"TIMEOUT_LOAD: Game did not load into Lobby after {load_timeout}s")
        return _ok()
    else:
        print(f"[{serial}] App is already running. Navigating back to Lobby...")
        result = back_to_lobby(serial, detector)
        return result if isinstance(result, dict) else (_ok() if result else _fail("NAV_LOBBY_UNREACHABLE: back_to_lobby failed"))

def wait_for_state(serial: str, detector: GameStateDetector, target_states: list, timeout_sec: int = 60, package_name: str = "", check_mode: str = "state") -> str:
    """Blocks and loops until the emulator reaches one of the target_states."""
    start_time = time.time()
    print(f"[{serial}] Waiting for one of states: {target_states} (Timeout: {timeout_sec}s)")
    
    last_crash_check = time.time()
    
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
        
        if current_state in target_states:
            print(f"[{serial}] -> Target Reached '{current_state}'")
            return current_state
            
        if current_state == "LOADING SCREEN":
            print(f"[{serial}] -> Game is loading. Waiting 3 seconds...")
            time.sleep(3)
        else:
            # Check for crash every 10 seconds to avoid ADB spam
            if time.time() - last_crash_check > 10:
                if check_app_crash(serial, package_name):
                    return None
                last_crash_check = time.time()
                
            time.sleep(0.5)

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
    time.sleep(3)
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
        time.sleep(2)
        
        current_clip = clipper_helper.get_clipper_data(adb_path, serial)
        
        # Valid ID heuristic: only digits, reasonably long
        if current_clip and current_clip.isdigit() and len(current_clip) >= 5:
            return current_clip
            
        # Fallback if text changed anyway
        if current_clip and current_clip != last_clip:
            return current_clip
            
        print(f"  -> [WARNING] Empty or old data '{current_clip}'. Retrying...")
    
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
    LOBBY_STATES = ["IN-GAME LOBBY (IN_CITY)", "IN-GAME LOBBY (OUT_CITY)"]

    # Debug mode: save UNKNOWN screenshots for template creation
    debug = True
    debug_dir = None
    debug_count = 0
    if debug:
        import cv2 as _cv2
        debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "_unknown_captures")
        os.makedirs(debug_dir, exist_ok=True)
        print(f"[{serial}] [DEBUG] Saving UNKNOWN screenshots to: {debug_dir}")

    print(f"[{serial}] === BACK TO LOBBY ===")

    # 0. Ensure emulator is online and game is running
    was_running = ensure_app_running(serial, get_package_for_provider(), config.adb_path)
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
            time.sleep(10)
            continue

        loading_screen_count = 0

        # === CASE 2: NETWORK ISSUE — Tap confirm ===
        if current_state == "LOADING SCREEN (NETWORK ISSUE)":
            print(f"[{serial}] -> Network issue detected. Tapping Confirm...")
            adb_helper.tap(serial, 500, 325)
            time.sleep(2)
            continue

        # === CASE 3: Construction detected (via check_state_full) — Press BACK immediately ===
        if construction:
            print(f"[{serial}] -> Construction '{construction}' detected. Pressing BACK...")
            unknown_start_time = None
            adb_helper.press_back(serial)
            time.sleep(1.5)
            continue

        # === CASE 4: Special screen detected — Press BACK immediately ===
        if special:
            print(f"[{serial}] -> Special screen '{special}' detected. Pressing BACK...")
            unknown_start_time = None
            adb_helper.press_back(serial)
            time.sleep(1.5)
            continue

        # === CASE 5: BLACK SCREEN — Game booting, NEVER press back! ===
        # Black screen appears before loading screen during game boot.
        # Pressing BACK here kills the app → ensure_app_running restarts it → infinite loop!
        screen = result["screen"]
        if current_state == "UNKNOWN / TRANSITION" and screen is not None:
            mean_brightness = np.mean(screen)
            if mean_brightness < BLACK_SCREEN_THRESHOLD:
                print(f"[{serial}] -> BLACK SCREEN detected (brightness={mean_brightness:.1f}). Game booting. Waiting 5s...")
                unknown_start_time = None  # Reset grace — this is NOT a stuck unknown
                time.sleep(5)
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
                time.sleep(1.5)
                continue

            grace_elapsed = time.time() - unknown_start_time
            if grace_elapsed < 5:
                remaining = 5 - grace_elapsed
                print(f"[{serial}] -> Still unknown. Grace: {remaining:.0f}s left...")
                time.sleep(1.5)
                continue
            else:
                print(f"[{serial}] -> Unknown for >5s. Pressing BACK...")
                adb_helper.press_back(serial)
                time.sleep(1.5)
                continue

        # === CASE 6: Known named state (Profile Menu, Bazaar, Events, etc.) ===
        unknown_start_time = None

        if current_state == last_known_state:
            known_state_back_count += 1
        else:
            last_known_state = current_state
            known_state_back_count = 1

        if known_state_back_count <= 3:
            print(f"[{serial}] -> Known state '{current_state}'. Pressing BACK ({known_state_back_count}/3)...")
            adb_helper.press_back(serial)
            time.sleep(1.5)
        else:
            print(f"[{serial}] -> [WARNING] State '{current_state}' stuck after 3 backs. Extra wait 3s...")
            time.sleep(3)
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
            time.sleep(2)
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
    time.sleep(5)
    
    return _ok()

def go_to_construction(serial: str, detector: GameStateDetector, name: str, feature: str | None = None) -> dict:
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
        return _go_to_construction_v2(serial, detector, name_upper, feature)

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


def _go_to_construction_v2(serial: str, detector: GameStateDetector, name_upper: str, feature: str) -> dict:
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
    capture_pet(serial, detector)
    go_to_pet_sanctuary(serial, detector)
    release_pet(serial, detector)
    capture_pet(serial, detector)
    return _ok()
    
def capture_pet(serial: str, detector: GameStateDetector) -> dict:
    """
    Navigates from OUT_CITY to Auto Capture Pet screen and starts capture.
    """
    print(f"[{serial}] Navigating to Capture Pet...")
    
    lobby_result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)")
    if not _is_ok(lobby_result):
        print(f"[{serial}] [FAILED] Could not reach OUT_CITY lobby.")
        return _bubble(lobby_result, "NAV_LOBBY_UNREACHABLE: Could not reach OUT_CITY")

    # 2. Tap Menu search
    print(f"[{serial}] Opening Search Menu (42, 422)...")
    adb_helper.tap(serial, 42, 422)
    time.sleep(3)
    
    # 3. Tap Menu search Pet
    print(f"[{serial}] Selecting Darklink Legions (158, 486)...")
    adb_helper.tap(serial, 158, 486)
    time.sleep(2)

    print(f"[{serial}] Selecting BEASTS MENU (301, 215)...")
    adb_helper.tap(serial, 301, 215)
    time.sleep(2)

    # 4. Tap Auto Capture submenu
    print(f"[{serial}] Selecting Auto Capture (285, 400)...")
    adb_helper.tap(serial, 285, 400)
    time.sleep(2)

    # 5. Verify state AUTO_CAPTURE_PET / AUTO_CAPTURE_START
    print(f"[{serial}] Waiting for Capture window to open...")
    state = wait_for_state(serial, detector, ["AUTO_CAPTURE_PET", "AUTO_CAPTURE_START", "AUTO_CAPTURE_IN_PROGRESS"], timeout_sec=10, check_mode="special")
    
    if state not in ["AUTO_CAPTURE_PET", "AUTO_CAPTURE_START", "AUTO_CAPTURE_IN_PROGRESS"]:
        print(f"[{serial}] [FAILED] Did not reach Capture window.")
        return _fail("NAV_TARGET_NOT_REACHED: Did not reach Capture window")

    # 6. Tap (284, 398) x5 to configure
    print(f"[{serial}] Configuring Pet Capture (284, 398) x5...")
    for _ in range(5):
        adb_helper.tap(serial, 284, 398)
        time.sleep(0.05)
    time.sleep(2)
    
    # 7. Tap Start
    print(f"[{serial}] Starting Capture (501, 466)...")
    adb_helper.tap(serial, 501, 466)
    time.sleep(2)

    # 8. Check if not enough warrants or capture in progress
    print(f"[{serial}] Checking outcome of Auto Capture...")
    outcome = wait_for_state(serial, detector, ["AUTO_CAPTURE_START", "AUTO_CAPTURE_IN_PROGRESS"], timeout_sec=10, check_mode="special")
    
    if outcome is None:
        print(f"[{serial}] Auto capture started & game pushed to map! Capture successful.")
        return _ok()
        
    if outcome == "AUTO_CAPTURE_IN_PROGRESS":
        print(f"[{serial}] Auto Capture remains on screen and is in progress! Waiting for completion...")
        while True:
            # Check if start icon appeared (meaning capture finished)
            finished = detector.check_special_state(serial, target="AUTO_CAPTURE_START")
            if finished:
                print(f"[{serial}] Auto capture completed successfully!")
                adb_helper.press_back(serial)
                break
                
            print(f"[{serial}] Still in progress... tapping refresh (285, 400) and waiting 5s.")
            # Bấm đổi tab Auto Capture để nó loading lại giao diện
            adb_helper.tap(serial, 147, 140)
            time.sleep(0.5)
            adb_helper.tap(serial, 150, 233)
            time.sleep(5)
            
    elif outcome == "AUTO_CAPTURE_START":
        print(f"[{serial}] Not enough warrants to capture pet (or idle state returned).")
        adb_helper.press_back(serial)
        
    return _ok()

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
    time.sleep(3)
    
    state = wait_for_state(serial, detector, ["PET_SANCTUARY"], timeout_sec=10, check_mode="construction")
    if state != "PET_SANCTUARY":
        print(f"[{serial}] [FAILED] Did not reach PET_SANCTUARY state.")
        return _fail("NAV_TARGET_NOT_REACHED: Did not reach PET_SANCTUARY")
    
    print(f"[{serial}] -> PET_SANCTUARY reached successfully.")
    return _ok()

# Pet grid slot definitions (3 columns × N rows, 1-indexed)
# Slot 7 = row 3 col 1, Slot 8 = row 3 col 2
_PET_SLOT_7 = {"tap": (151, 315), "roi": (116, 275, 186, 355)}
_PET_SLOT_8 = {"tap": (217, 320), "roi": (180, 275, 250, 355)}
_BLANK_PET_TEMPLATE = os.path.join("pets", "blank_pet_slot_8.png")


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


def _release_single_pet(serial: str, detector: GameStateDetector, tap_point: tuple):
    """Execute the release UI sequence for one pet at the given grid position.

    Captures skill pool (Phase 1) and skill obtained (Phase 2) for data analysis.
    Both screenshots share the same release_id for pairing.
    """
    release_id = time.strftime("%Y%m%d_%H%M%S")
    save_dir = os.path.join("data", "pet_releases")
    os.makedirs(save_dir, exist_ok=True)

    adb_helper.tap(serial, tap_point[0], tap_point[1])  # Select pet in grid
    time.sleep(1.5)
    adb_helper.tap(serial, 352, 214)   # "Release" button → GHI CHÚ popup
    time.sleep(1.5)

    # Phase 1: Capture skill pool available
    detector._screen_cache = None
    frame1 = detector.get_frame(serial)
    if frame1 is not None:
        crop1 = frame1[150:300, 250:700]
        fname1 = f"available_{serial}_{release_id}.png"
        cv2.imwrite(os.path.join(save_dir, fname1), crop1)
        print(f"[{serial}] [PET] Phase 1 saved: {fname1}")

    adb_helper.tap(serial, 577, 365)   # Confirm dialog (XÁC NHẬN)
    time.sleep(1.5)

    # Phase 2: Capture skill obtained
    detector._screen_cache = None
    frame2 = detector.get_frame(serial)
    if frame2 is not None:
        crop2 = frame2[100:200, 400:560]
        fname2 = f"get_{serial}_{release_id}.png"
        cv2.imwrite(os.path.join(save_dir, fname2), crop2)
        print(f"[{serial}] [PET] Phase 2 saved: {fname2}")

    adb_helper.tap(serial, 547, 414)   # OK / second confirm
    time.sleep(2)


def release_pet(serial: str, detector: GameStateDetector) -> dict:
    """Release all unlocked pets from PET_ENCLOSURE."""
    print(f"[{serial}] === RELEASE PET ===")

    adb_helper.tap(serial, 918, 504)
    time.sleep(3)

    state = wait_for_state(serial, detector, ["PET_ENCLOSURE"], timeout_sec=10, check_mode="construction")
    if state != "PET_ENCLOSURE":
        print(f"[{serial}] [FAILED] Did not reach PET_ENCLOSURE state.")
        return _fail("NAV_TARGET_NOT_REACHED: Did not reach PET_ENCLOSURE")

    # 3. Navigate sort/release tabs
    print(f"[{serial}] Selecting Release Tabs (254,93) -> (670,131) -> (50,135)...")
    adb_helper.tap(serial, 254, 93)
    time.sleep(2)
    adb_helper.tap(serial, 670, 131)
    time.sleep(2)
    adb_helper.tap(serial, 50, 135)
    time.sleep(2)

    # 4. Linear release flow (max 5 pets/day)
    _RELEASE_COUNT = 5
    released = 0

    # Step A: Check slot 8 — if already blank, nothing to release
    if _is_pet_slot_blank(serial, detector, _PET_SLOT_8["roi"]):
        print(f"[{serial}] [PET] Slot 8 already empty → nothing to release.")
    else:
        # Step B: Release from slot 8 x5
        print(f"[{serial}] [PET] Releasing from slot 8 (up to {_RELEASE_COUNT})...")
        for i in range(_RELEASE_COUNT):
            _release_single_pet(serial, detector, _PET_SLOT_8["tap"])
            if _is_pet_slot_blank(serial, detector, _PET_SLOT_8["roi"]):
                released += (i + 1)
                print(f"[{serial}] [PET] Slot 8 empty after {i + 1} release(s).")
                break
        else:
            # After 5 releases slot 8 still has pet → it's LOCKED
            # Edge case: sort put locked pet at slot 8, free pet at slot 7
            print(f"[{serial}] [PET] Slot 8 still occupied after {_RELEASE_COUNT}x → pet is LOCKED.")
            print(f"[{serial}] [PET] Trying slot 7 fallback (x1)...")
            _release_single_pet(serial, detector, _PET_SLOT_7["tap"])

            # After releasing slot 7, grid shifts: locked pet → slot 7, new pet → slot 8
            if not _is_pet_slot_blank(serial, detector, _PET_SLOT_8["roi"]):
                print(f"[{serial}] [PET] Slot 8 has new pet after grid shift. Releasing slot 8 (up to {_RELEASE_COUNT})...")
                for j in range(_RELEASE_COUNT):
                    _release_single_pet(serial, detector, _PET_SLOT_8["tap"])
                    if _is_pet_slot_blank(serial, detector, _PET_SLOT_8["roi"]):
                        released += (j + 1) + 1  # +1 for slot 7 release
                        print(f"[{serial}] [PET] Slot 8 empty after {j + 1} release(s).")
                        break
            else:
                released += 1  # Only the slot 7 release counted
                print(f"[{serial}] [PET] Slot 8 empty after slot 7 release.")

    # 5. Exit
    print(f"[{serial}] Back x2 to exit Pet screen...")
    adb_helper.press_back(serial)
    time.sleep(2)
    adb_helper.press_back(serial)
    time.sleep(2)

    print(f"[{serial}] === RELEASE PET COMPLETE — released {released} pet(s) ===")
    return _ok()

def _human_delay(base_sec: float, variance: float = 0.4):
    """Sleep with ±variance randomization to avoid bot-like fixed timing."""
    jitter = base_sec * variance
    delay = base_sec + random.uniform(-jitter, jitter)
    time.sleep(max(0.5, delay))


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


def go_to_farming(serial: str, detector: GameStateDetector, resource_type: str = "wood") -> dict:
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
    LEGION_TAPS = [
        (695, 90), (735, 90), (780, 90), (825, 90), (865, 90),
    ]

    r_type = resource_type.lower()
    if r_type not in RESOURCE_TAPS:
        print(f"[{serial}] [ERROR] Unknown resource type: {resource_type}")
        return _fail(f"CONFIG_INVALID_PARAM: Unknown resource type '{resource_type}'")

    print(f"[{serial}] Starting Farming Workflow for: {resource_type.upper()}")

    # 1. Back to lobby OUT_CITY
    result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)")
    if not _is_ok(result):
        print(f"[{serial}] [FAILED] Could not reach OUT_CITY lobby.")
        return _bubble(result, "NAV_LOBBY_UNREACHABLE: Could not reach OUT_CITY lobby")

    # 2. Pre-compute random search methods for each dispatch
    methods = _plan_search_methods(len(LEGION_TAPS))
    search_k_values = _plan_search_clicks(len(LEGION_TAPS))
    print(f"[{serial}] Search plan: {methods}, K values: {search_k_values}")

    # 3. Dispatch loop
    for idx, legion_tap in enumerate(LEGION_TAPS):
        method = methods[idx]
        k_val = search_k_values[idx]
        print(f"\n[{serial}] --- Dispatch #{idx+1} ({method} search, K={k_val}) ---")

        if method == "menu":
            mine_result = _search_mine_via_menu(
                serial, detector, r_type, RESOURCE_TAPS, SEARCH_TAPS,
                search_clicks=k_val,
            )
        else:
            mine_result = _search_mine_manual(serial, detector, r_type)

        if mine_result is None:
            # No mine found — stop dispatching
            break

        if mine_result == "occupied":
            # Mine was occupied (View), continue to next dispatch
            continue

        # mine_result is the actual resource type used (may differ from input if fallback)
        r_type = mine_result

        # ── Gather -> Create Legion -> Preset -> Dispatch ──
        gather_btn = _detect_with_retry(serial, detector, "RSS_GATHER", threshold=0.8, attempts=3, delay=1)
        if not gather_btn:
            print(f"[{serial}] [WARNING] Gather button not visible. Mine popup may not have loaded.")
            adb_helper.press_back(serial)
            _human_delay(1)
            break

        _, gx, gy = gather_btn
        print(f"[{serial}] Tapping Gather Button at detected ({gx}, {gy})...")
        adb_helper.tap(serial, gx, gy)
        _human_delay(2)

        # Check if we can create a legion
        print(f"[{serial}] Checking if we can deploy legions (looking for CREATE_LEGION)...")
        create_result = _detect_with_retry(serial, detector, "CREATE_LEGION", threshold=0.8, attempts=3, delay=1)

        if not create_result:
            print(f"[{serial}] Legions are FULL, node is occupied, or no AP! Returning to Lobby.")
            adb_helper.press_back(serial)
            _human_delay(2)
            break

        print(f"[{serial}] Found CREATE_LEGION -> Deploying forces...")

        # Create Legion
        print(f"[{serial}] Tapping Create Legion Button (755, 115)...")
        adb_helper.tap(serial, 755, 115)
        _human_delay(2)

        # Select Legion Preset
        print(f"[{serial}] Selecting Legion Preset #{idx+1} at {legion_tap}...")
        adb_helper.tap(serial, legion_tap[0], legion_tap[1])
        _human_delay(1)

        # Dispatch + verify return to world map
        dispatch_loc = (850, 480)
        print(f"[{serial}] Tapping March/Dispatch {dispatch_loc}...")
        adb_helper.tap(serial, dispatch_loc[0], dispatch_loc[1])
        _human_delay(2)

        state = wait_for_state(serial, detector,
            ["IN-GAME LOBBY (OUT_CITY)"], timeout_sec=10)
        if not state:
            print(f"[{serial}] [WARNING] Did not return to OUT_CITY after dispatch. Recovering...")
            back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)")

    print(f"[{serial}] Farming Deployment Finished.")
    return _ok()


def _plan_search_methods(total: int) -> list:
    """Pre-compute random search method assignment for each dispatch.

    Returns list of 'menu' or 'manual' strings.
    Method 'manual' is capped at max 2 per session (slower, more expensive).
    If mine map templates are not available, returns all 'menu'.
    """
    # Phase 3: set True when mine world-map templates are registered
    manual_available = False

    if not manual_available:
        return ["menu"] * total

    manual_count = random.randint(0, min(2, total))
    methods = ["menu"] * total

    if manual_count > 0:
        manual_positions = random.sample(range(total), manual_count)
        for pos in manual_positions:
            methods[pos] = "manual"

    return methods


def _plan_search_clicks(total: int) -> list:
    """Pre-compute K (search click count) for each dispatch.

    Weighted distribution favoring K=1:
        K=1: 40%,  K=2: 30%,  K=3: 20%,  K=4: 10%
    After any K>=3 is assigned, all subsequent K values cap at 2.
    """
    weights = [40, 30, 20, 10]  # K=1, K=2, K=3, K=4
    choices = [1, 2, 3, 4]
    capped_weights = [40, 60]   # K=1, K=2 (after deep search)
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
    """Search for a mine by manually scanning the world map (Phase 3 — stub).

    Full implementation requires mine world-map templates to be captured and registered.
    Currently falls back to menu search.
    """
    print(f"[{serial}] [MANUAL SEARCH] Phase 3 not yet implemented. Falling back to menu search.")
    RESOURCE_TAPS = {
        "gold": (320, 485), "wood": (475, 485),
        "stone": (640, 485), "mana": (795, 485),
    }
    SEARCH_TAPS = {
        "gold": (320, 400), "wood": (475, 400),
        "stone": (640, 400), "mana": (795, 400),
    }
    return _search_mine_via_menu(serial, detector, r_type, RESOURCE_TAPS, SEARCH_TAPS)

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
    time.sleep(3)

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
        time.sleep(2)

    if not rss_marker:
        print(f"[{serial}] Resource Center not found in markers! Aborting.")
        adb_helper.press_back(serial)
        time.sleep(2)
        return _fail("TEMPLATE_NO_MATCH: Resource Center marker not found")

    # Navigate to RSS Center on map
    center_x, center_y = rss_marker[1], rss_marker[2]
    go_x, go_y = center_x + 570, center_y
    print(f"[{serial}] Found RSS Center. Tapping GO ({go_x}, {go_y})...")
    adb_helper.tap(serial, go_x, go_y)
    time.sleep(6)

    print(f"[{serial}] Tapping RSS Center on map (479, 254)...")
    adb_helper.tap(serial, 479, 254)
    time.sleep(3)

    # --- Detect state: View / Gather(Build) ---
    print(f"[{serial}] Checking RSS Center state...")
    view_state = detector.check_activity(serial, target="RSS_VIEW", threshold=0.8)
    if view_state:
        print(f"[{serial}] 'View' detected. Legion already farming. Aborting.")
        adb_helper.tap(serial, 50, 500)
        time.sleep(2)
        return {"ok": False}

    gather_state = detector.check_activity(serial, target="RSS_GATHER", threshold=0.8)
    if not gather_state:
        # RSS Center may be in Build state — button shows as "Build" instead of "Gather"
        gather_state = detector.check_activity(serial, target="RSS_BUILD", threshold=0.8)

    if not gather_state:
        print(f"[{serial}] Neither Gather nor Build button found. Aborting.")
        adb_helper.tap(serial, 50, 500)
        time.sleep(2)
        return _ok()

    g_x, g_y = gather_state[1], gather_state[2]

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
    time.sleep(3)

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
    time.sleep(2)
    adb_helper.tap(serial, 545, 267)
    time.sleep(3)
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
    time.sleep(3)
    
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
        adb_helper.press_back(serial)
        _human_delay(1.0)
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
            time.sleep(random.uniform(0.05, 0.15))
        remaining -= burst
        print(f"[{serial}] Burst done ({total_clicks - remaining}/{total_clicks} clicks)")
        if remaining > 0:
            _human_delay(0.8)

    print(f"[{serial}] Donate complete — {total_clicks} clicks sent.")

    # ── Phase 5: Cleanup ──
    _human_delay(1.0)
    adb_helper.press_back(serial)
    _human_delay(1.0)
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
            round_helps += 1
            round_had_action = True
            print(f"[{serial}] Quick Help #{round_helps} at ({qx}, {qy}). Tapping...")
            adb_helper.tap(serial, qx, qy)

            _human_delay(5.0)

            # Tap same position to dismiss popup
            print(f"[{serial}] Dismissing popup at ({qx}, {qy})...")
            adb_helper.tap(serial, qx, qy)
            _human_delay(2.0)

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
    adb_helper.press_back(serial)
    _human_delay(1.0)
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
            time.sleep(2)
            
        if not war_tab_found:
            print(f"[{serial}] [WARNING] War tab not found. Aborting this loop.")
            continue
            
        time.sleep(4) # Wait for War screen to load
        
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
            time.sleep(5)
            
        if not rally_available:
            print(f"[{serial}] Timeout: No active rallies found after waiting. Returning to lobby.")
            continue
            
        # 5. Join Rally
        print(f"[{serial}] Tapping Join Rally at (659, 211)...")
        adb_helper.tap(serial, 659, 211)
        time.sleep(4)
        
        # 6. Deploy legions (use legion_1)
        # Check if we can create a legion with retries
        print(f"[{serial}] Checking if we can deploy legions (looking for CREATE_LEGION)...")
        result = None
        for attempt in range(3):
            result = detector.check_activity(serial, target="CREATE_LEGION", threshold=0.8)
            if result:
                break
            print(f"[{serial}] CREATE_LEGION not found, retrying ({attempt + 1}/3)...")
            time.sleep(2)
            
        if not result:
            print(f"[{serial}] Legions are FULL, node is occupied, or no AP! Returning to Lobby.")
            continue
            
        print(f"[{serial}] Found CREATE_LEGION -> Deploying forces...")
        
        # Create legion & Dispatch
        print(f"[{serial}] Tapping Create Legion Button (755, 115)...")
        adb_helper.tap(serial, 755, 115)
        time.sleep(4)
        
        adb_helper.tap(serial, 848, 154)
        time.sleep(2)
        adb_helper.tap(serial, 852, 223)
        time.sleep(2)
        adb_helper.tap(serial, 715, 300)
        time.sleep(2)
        adb_helper.tap(serial, 723, 448)
        time.sleep(2)
        adb_helper.tap(serial, 852, 453)
        time.sleep(2)
        
        dispatch_loc = (850, 480) 
        print(f"[{serial}] Tapping March/Dispatch {dispatch_loc}...")
        adb_helper.tap(serial, dispatch_loc[0], dispatch_loc[1])
        
        # Game usually puts us back to map or lobby after dispatching. Wait for transition.
        time.sleep(7)
        
        # 7. Return to IN_CITY (handled by start of next loop)
        print(f"[{serial}] Rally join complete for this loop.")

    print(f"[{serial}] Finished all {loop_count} Rally loops.")
    return _ok()

def train_troops(serial: str, detector: GameStateDetector, training_list: list = None) -> dict:
    """
    Trains troops at the specified training houses and tiers.
    """
    if training_list is None:
        training_list = [("infantry", 1)]
        
    print(f"[{serial}] Starting Train Troops workflow for {len(training_list)} houses: {training_list}")
    
    HOUSE_TAPS = {
        "archer": (465, 256),
        "cavalry": (302, 369),
        "infantry": (379, 318),
        "siege": (195, 290),
        "mage": (278, 247)
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
        print(f"[{serial}] Tapping {h_type.upper()} House at ({hx}, {hy})...")
        adb_helper.tap(serial, hx, hy)
        time.sleep(1)
        adb_helper.tap(serial, hx, hy)
        time.sleep(2)
        
        # 3. Tap training icon relative to house (+90, +20)
        icon_x = hx + 90
        icon_y = hy + 20
        print(f"[{serial}] Tapping TRAINING_ICON at ({icon_x}, {icon_y})...")
        adb_helper.tap(serial, icon_x, icon_y)
        time.sleep(2)
        
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
            time.sleep(2)
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
                time.sleep(3)
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
                time.sleep(2)
                
                # Check for train button
                train_icon = detector.check_activity(serial, target="TRAINING_ICON", threshold=0.8)
                if train_icon:
                    _, btn_x, btn_y = train_icon
                    print(f"[{serial}] Tapping Train Button at coordinate ({btn_x}, {btn_y})...")
                    adb_helper.tap(serial, btn_x, btn_y)
                    time.sleep(3)
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
        time.sleep(2)

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
    time.sleep(3)
    
    print(f"[{serial}] Tapping Claim Button (826, 175)...")
    adb_helper.tap(serial, 826, 175)
    time.sleep(2)
    
    print(f"[{serial}] -> Claim Alliance Resource completed.")

    adb_helper.press_back(serial)
    time.sleep(2)
    adb_helper.press_back(serial)
    time.sleep(2)
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
    time.sleep(3)
    
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
    claim_button = (100, 512)
    
    tabs_to_check = ["alliance", "events", "system"] if mail_type == "all" else [mail_type]
        
    for tab in tabs_to_check:
        print(f"[{serial}] Checking '{tab.capitalize()}' mail...")
        tab_x, tab_y = tabs[tab]
        # Tap tab twice: first tap dismisses any reward popup, second selects tab
        adb_helper.tap(serial, tab_x, tab_y)
        time.sleep(1)
        adb_helper.tap(serial, tab_x, tab_y)
        time.sleep(2)
        print(f"[{serial}] Tapping Claim ({claim_button[0]}, {claim_button[1]})...")
        adb_helper.tap(serial, claim_button[0], claim_button[1])
        time.sleep(2)
        
    print(f"[{serial}] Closing Mail Menu...")
    adb_helper.press_back(serial)
    time.sleep(2)
    
    print(f"[{serial}] -> Check Mail completed.")
    return _ok()


def go_to_pet_token(serial: str, detector: GameStateDetector) -> dict:
    """Navigates to Pet Token area."""
    print(f"[{serial}] Navigating to Pet Token...")
    adb_helper.tap(serial, 750, 80)
    time.sleep(2)
    adb_helper.swipe(serial, 100, 450, 100, 100, 500)
    time.sleep(1)
    adb_helper.swipe(serial, 100, 450, 100, 100, 500)
    time.sleep(1)
    adb_helper.swipe(serial, 100, 450, 100, 100, 500)
    time.sleep(1)
    adb_helper.tap(serial, 100, 375)
    time.sleep(3)
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

    result = startup_to_lobby(serial, detector, package_name=get_package_for_provider(), load_timeout=120)
    if not _is_ok(result):
        print(f"[{serial}] swap_account failed: Could not reach lobby.")
        return _bubble(result, "NAV_LOBBY_UNREACHABLE: Could not reach lobby")

    print(f"[{serial}] Step 1/6: Opening Profile...")
    profile_result = go_to_profile(serial, detector)
    if not _is_ok(profile_result):
        print(f"[{serial}] swap_account failed: Could not open Profile.")
        return _bubble(profile_result, "NAV_TARGET_NOT_REACHED: Could not open Profile")
    time.sleep(1) 

    # 4. Tap Settings button (683, 340) -> wait via account detector
    print(f"[{serial}] Step 2/6: Opening Settings (683, 340)...")
    adb_helper.tap(serial, 683, 340)
    state = wait_for_state(serial, detector, ["SETTINGS"], timeout_sec=10, check_mode="special")
    if not state:
        print(f"[{serial}] swap_account failed: Could not reach Settings screen.")
        return _fail("NAV_TARGET_NOT_REACHED: Could not reach Settings screen")
    time.sleep(1)

    # 5. Tap "Switch Account" (478, 354) -> wait via account detector
    print(f"[{serial}] Step 3/6: Tapping Switch Account (478, 354)...")
    adb_helper.tap(serial, 478, 354)
    state = wait_for_state(serial, detector, ["CHARACTER_MANAGEMENT"], timeout_sec=10, check_mode="special")
    if not state:
        print(f"[{serial}] swap_account failed: Could not reach Character Management screen.")
        return _fail("NAV_TARGET_NOT_REACHED: Could not reach Character Management")
        
    # Give the Character Management UI time to fully slide in and render its text
    print(f"[{serial}] Waiting 3s for Character Management UI to settle...")
    time.sleep(1)

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
            time.sleep(2)

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
                time.sleep(3)
            else:
                print(f"[{serial}] -> Account not found after {max_scrolls} scrolls.")

        from workflow.account_detector import AccountNotFoundError

        if not account_found:
            print(f"[{serial}] swap_account failed: Account '{target_account}' not found in Character Management list.")
            adb_helper.press_back(serial)
            time.sleep(2)
            raise AccountNotFoundError(f"Account '{target_account}' not found.")

        # 7. Tap the found account
        print(f"[{serial}] Step 5/6: Selecting account at ({account_found[0]}, {account_found[1]})...")
        adb_helper.tap(serial, account_found[0], account_found[1])
        time.sleep(2)

        # Check if the confirmation prompt appeared. 
        # If the state is STILL "CHARACTER_MANAGEMENT", it means the account was already selected,
        # so no confirmation prompt appeared. We just back out 3 times to Lobby.
        if detector.check_special_state(serial) == "CHARACTER_MANAGEMENT":
            print(f"[{serial}] Target account '{target_account}' is already the active account. Backing out to Lobby...")
            for _ in range(3):
                adb_helper.press_back(serial)
                time.sleep(1.5)
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
        time.sleep(2)
        
        if detector.check_special_state(serial) == "CHARACTER_MANAGEMENT":
            print(f"[{serial}] Character 1 is active. Tapping Character 2 at {char2_pos}...")
            adb_helper.tap(serial, char2_pos[0], char2_pos[1])
            time.sleep(2)
        else:
            print(f"[{serial}] Character 1 selected, proceeding to confirm.")

    # 8. Tap Confirm (400, 300)
    print(f"[{serial}] Step 6/6: Confirming switch (556, 356)...")
    adb_helper.tap(serial, 556, 356)
    time.sleep(3)

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
                print(f"[{serial}] Found {rss_type}! Tapping at ({icon_x}, {icon_y})...")
                adb_helper.tap(serial, icon_x, icon_y)
                claimed_count += 1
                time.sleep(1.5)
            else:
                print(f"[{serial}] No more {rss_type} found.")
                break
            
    print(f"[{serial}] Finished claiming city resources. Total claimed: {claimed_count}")
    return claimed_count


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
    print(f"[{serial}] Scanning for Healing Icon...")
    icon_match = None
    for attempt in range(3):
        icon_match = detector.locate_icon(serial, target="HEALING_ICON", threshold=0.8)
        if icon_match:
            break
        time.sleep(2)

    if not icon_match:
        print(f"[{serial}] No Healing Icon found. Troops are fully healed or icon is missing.")
        return _ok()  # Not an error — nothing to heal

    # 3. Tap Healing Icon
    _, icon_x, icon_y = icon_match
    print(f"[{serial}] Found Healing Icon. Tapping at ({icon_x}, {icon_y})...")
    adb_helper.tap(serial, icon_x, icon_y)

    # 4. Wait for Elixir Healing screen
    state = wait_for_state(serial, detector, ["ELIXIR_HEALING"], timeout_sec=10, check_mode="construction")
    if state != "ELIXIR_HEALING":
        print(f"[{serial}] [FAILED] Did not reach ELIXIR_HEALING screen.")
        return _fail("NAV_TARGET_NOT_REACHED: Did not reach ELIXIR_HEALING screen")

    # 5. Select Healing Method
    if healing_method.lower() == "resources":
        print(f"[{serial}] Selecting Resources Healing (777, 155)...")
        adb_helper.tap(serial, 777, 155)
    else:
        print(f"[{serial}] Selecting Elixir Healing (581, 153)...")
        adb_helper.tap(serial, 581, 153)
    time.sleep(2)

    # 6. Heal Troops
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
                time.sleep(1)

                print(f"[{serial}] Healing {t_lower}...")
                adb_helper.tap(serial, HEAL_BTN[0], HEAL_BTN[1])
                time.sleep(2)

                print(f"[{serial}] Untick priority troop: {t_lower} at {loc}")
                adb_helper.tap(serial, loc[0], loc[1])
                time.sleep(1)

    # Final 'Heal All' or heal remaining
    print(f"[{serial}] Tapping Heal All/Remaining (684, 504)...")
    adb_helper.tap(serial, HEAL_BTN[0], HEAL_BTN[1])
    time.sleep(3)

    # 7. Press back to return to lobby
    print(f"[{serial}] Healing completed. Returning to lobby...")
    adb_helper.press_back(serial)
    time.sleep(2)

    return _ok()


def alliance_help(serial: str, detector: GameStateDetector) -> dict:
    """
    Alliance Help — single-shot.
    Navigate to Alliance Menu, detect & tap Help button, return.
    """
    print(f"[{serial}] === ALLIANCE HELP (single-shot) ===")

    result = go_to_alliance(serial, detector)
    if not _is_ok(result):
        print(f"[{serial}] [FAILED] Could not reach Alliance Menu.")
        return _bubble(result, "NAV_TARGET_NOT_REACHED: Could not reach Alliance Menu")

    print(f"[{serial}] Tapping Alliance Help Menu (730, 330)...")
    adb_helper.tap(serial, 730, 330)
    time.sleep(3)

    help_match = detector.check_alliance(serial, target="ALLIANCE_HELP", threshold=0.8)

    if not help_match:
        print(f"[{serial}] No Alliance Help button detected. Nothing to help with.")
        adb_helper.press_back(serial)
        time.sleep(2)
        return _ok()

    _, hx, hy = help_match
    print(f"[{serial}] Found Alliance Help button at ({hx}, {hy}). Tapping...")
    adb_helper.tap(serial, hx, hy)
    time.sleep(3)
    print(f"[{serial}] Help completed!")

    adb_helper.press_back(serial)
    time.sleep(1)
    adb_helper.press_back(serial)
    time.sleep(1)

    print(f"[{serial}] === ALLIANCE HELP DONE ===")
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
    time.sleep(2)

    # ---- HERO RECRUITMENT SCREEN ----

    # 2. Silver Chest free draw
    print(f"[{serial}] Tapping Silver Chest Free Draw {SILVER_FREE_DRAW_TAP}...")
    adb_helper.tap(serial, SILVER_FREE_DRAW_TAP[0], SILVER_FREE_DRAW_TAP[1])
    time.sleep(3)
    adb_helper.tap(serial, DISMISS_POPUP_TAP[0], DISMISS_POPUP_TAP[1])
    time.sleep(2)

    # 3. Gold Chest free draw
    print(f"[{serial}] Tapping Gold Chest Free Draw {GOLD_FREE_DRAW_TAP}...")
    adb_helper.tap(serial, GOLD_FREE_DRAW_TAP[0], GOLD_FREE_DRAW_TAP[1])
    time.sleep(3)
    adb_helper.tap(serial, DISMISS_POPUP_TAP[0], DISMISS_POPUP_TAP[1])
    time.sleep(2)

    # 4. (Optional) x10 Silver draw
    if draw_x10_silver:
        print(f"[{serial}] Checking for Silver x10 draw button...")
        x10_match = detector.check_activity(serial, target="TAVERN_DRAW_X10", threshold=0.8)
        if x10_match:
            print(f"[{serial}] Silver x10 button found! Tapping {SILVER_X10_TAP}...")
            adb_helper.tap(serial, SILVER_X10_TAP[0], SILVER_X10_TAP[1])
            time.sleep(3)
            adb_helper.tap(serial, DISMISS_POPUP_TAP[0], DISMISS_POPUP_TAP[1])
            time.sleep(2)
        else:
            print(f"[{serial}] Silver x10 button NOT found (not enough keys). Skipping.")

    # 5. (Optional) x10 Gold draw
    if draw_x10_gold:
        print(f"[{serial}] Checking for Gold x10 draw button...")
        x10_match = detector.check_activity(serial, target="TAVERN_DRAW_X10", threshold=0.8)
        if x10_match:
            print(f"[{serial}] Gold x10 button found! Tapping {GOLD_X10_TAP}...")
            adb_helper.tap(serial, GOLD_X10_TAP[0], GOLD_X10_TAP[1])
            time.sleep(3)
            adb_helper.tap(serial, DISMISS_POPUP_TAP[0], DISMISS_POPUP_TAP[1])
            time.sleep(2)
        else:
            print(f"[{serial}] Gold x10 button NOT found (not enough keys). Skipping.")

    # ---- SWAP TO ARTIFACT SCREEN ----

    # 6. Swap to Artifact
    print(f"[{serial}] Swapping to Artifact screen {SWAP_TO_ARTIFACT_TAP}...")
    adb_helper.tap(serial, SWAP_TO_ARTIFACT_TAP[0], SWAP_TO_ARTIFACT_TAP[1])
    time.sleep(3)

    # 7. Artifact free draw
    print(f"[{serial}] Tapping Artifact Free Draw {ARTIFACT_FREE_DRAW_TAP}...")
    adb_helper.tap(serial, ARTIFACT_FREE_DRAW_TAP[0], ARTIFACT_FREE_DRAW_TAP[1])
    time.sleep(3)
    adb_helper.tap(serial, DISMISS_POPUP_TAP[0], DISMISS_POPUP_TAP[1])
    time.sleep(2)

    # 8. (Optional) x10 Artifact draw
    if draw_x10_artifact:
        print(f"[{serial}] Checking for Artifact x10 draw button...")
        x10_match = detector.check_activity(serial, target="TAVERN_DRAW_X10", threshold=0.8)
        if x10_match:
            print(f"[{serial}] Artifact x10 button found! Tapping {ARTIFACT_X10_TAP}...")
            adb_helper.tap(serial, ARTIFACT_X10_TAP[0], ARTIFACT_X10_TAP[1])
            time.sleep(3)
            adb_helper.tap(serial, DISMISS_POPUP_TAP[0], DISMISS_POPUP_TAP[1])
            time.sleep(2)
        else:
            print(f"[{serial}] Artifact x10 button NOT found (not enough keys). Skipping.")

    # 9. Back to lobby
    print(f"[{serial}] Done! Pressing BACK to return to lobby...")
    adb_helper.press_back(serial)
    time.sleep(2)

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

    # 2. Open search menu
    print(f"[{serial}] Opening Search Menu {SEARCH_MENU_TAP}...")
    adb_helper.tap(serial, SEARCH_MENU_TAP[0], SEARCH_MENU_TAP[1])
    time.sleep(3)

    # 3. Select Darkling category
    print(f"[{serial}] Selecting Darkling menu {DARKLING_MENU_TAP}...")
    adb_helper.tap(serial, DARKLING_MENU_TAP[0], DARKLING_MENU_TAP[1])
    time.sleep(2)

    # 4. Select Darkling Legions tab
    print(f"[{serial}] Selecting Darkling Legions tab {DARKLING_LEGIONS_TAB_TAP}...")
    adb_helper.tap(serial, DARKLING_LEGIONS_TAB_TAP[0], DARKLING_LEGIONS_TAB_TAP[1])
    time.sleep(2)

    # 5. Tap action/search button
    print(f"[{serial}] Triggering basic attack action {ACTION_BUTTON_TAP}...")
    adb_helper.tap(serial, ACTION_BUTTON_TAP[0], ACTION_BUTTON_TAP[1])
    time.sleep(2)

    # 6. Wait for create-legion state
    print(f"[{serial}] Waiting for Darkling Legions attack window...")
    state = wait_for_state(serial, detector, TARGET_STATES, timeout_sec=10, check_mode="special")
    if state not in TARGET_STATES:
        print(f"[{serial}] [FAILED] Did not reach Darkling Legions attack window.")
        return _fail("NAV_TARGET_NOT_REACHED: Did not reach Darkling Legions window")

    #7. Use all free Legions
    print(f"[{serial}] Using all free Legions...")
    adb_helper.tap(serial, CHOOSE_LEGIONS_TAP[0], CHOOSE_LEGIONS_TAP[1])
    time.sleep(2)
    adb_helper.tap(serial, CONFIRM_TAP[0], CONFIRM_TAP[1])
    time.sleep(2)

    # 7. Tap Start
    print(f"[{serial}] Starting Peacekeeping dispatch {DISPATCH_TAP}...")
    adb_helper.tap(serial, DISPATCH_TAP[0], DISPATCH_TAP[1])
    time.sleep(2)

    # 8. Check outcome
    print(f"[{serial}] Checking outcome of Darkling Legions dispatch...")
    outcome = wait_for_state(serial, detector, TARGET_STATES, timeout_sec=5, check_mode="special")

    if outcome is None:
        print(f"[{serial}] Dispatch started & game pushed to map! Attack successful.")
        time.sleep(60)
        return _ok()

    if outcome == "AUTO_PEACEKEEPING":
        print(f"[{serial}] Still on Peacekeeping screen. Out of CP.")
        adb_helper.press_back(serial)

    return _ok()

def check_legion_state(serial: str, detector: GameStateDetector, max_legions: int = 5) -> dict:
    """Thin wrapper — delegates to detector.check_legion_state()."""
    return detector.check_legion_state(serial, max_legions=max_legions)

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
    time.sleep(3)
    
    # 4. Run full check inside the management panel
    result = detector.check_legion_state(serial, max_legions=max_legions)
    
    # 5. Close management panel
    adb_helper.press_back(serial)
    time.sleep(1)
    
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
    # ── DEBUG: save frame before scanning ──
    _dbg_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "_debug_research")
    os.makedirs(_dbg_dir, exist_ok=True)
    detector._screen_cache = None
    _dbg_frame = detector.get_frame(serial)
    if _dbg_frame is not None:
        import cv2 as _cv2
        _dbg_path = os.path.join(_dbg_dir, f"alliance_help_scan_{serial}.png")
        _cv2.imwrite(_dbg_path, _dbg_frame)
        print(f"[{serial}] [DEBUG] Saved pre-scan frame: {_dbg_path}")
    # ── END DEBUG ──

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
            time.sleep(2)
        elif research_type == "military":
            print(f"[{serial}] Selecting Military Tech tab {MILITARY_TAB_TAP}...")
            adb_helper.tap(serial, MILITARY_TAB_TAP[0], MILITARY_TAB_TAP[1])
            time.sleep(2)
        elif research_type == "balance":
            if slot_idx % 2 == 0:
                print(f"[{serial}] Balance mode: selecting Economy Tech tab...")
                adb_helper.tap(serial, ECONOMY_TAB_TAP[0], ECONOMY_TAB_TAP[1])
            else:
                print(f"[{serial}] Balance mode: selecting Military Tech tab...")
                adb_helper.tap(serial, MILITARY_TAB_TAP[0], MILITARY_TAB_TAP[1])
            time.sleep(2)
        # "default" → don't tap any tab

        # 3b. Tap the Research button (at detected empty slot position)
        print(f"[{serial}] Tapping Research button at ({slot_x}, {slot_y})...")
        adb_helper.tap(serial, slot_x, slot_y)
        time.sleep(3)

        # 3b2. Tab verification: game may auto-switch tab when current tab
        #      has no available tech (e.g. economy maxed -> jumps to military).
        #      If user selected a specific type, verify we're still on that tab.
        if research_type in ("economy", "military"):
            expected_tab = "RESEARCH_ECONOMY_TECH" if research_type == "economy" else "RESEARCH_MILITARY_TECH"
            tab_match = detector.check_activity(serial, target=expected_tab, threshold=0.8)
            if not tab_match:
                print(f"[{serial}] [INFO] Tab {research_type} maxed (auto-switched). Nothing to research.")
                adb_helper.tap(serial, 415, 520)
                time.sleep(2)
                adb_helper.press_back(serial)
                time.sleep(2)
                return _ok(dynamic_cooldown_sec=21600)  # 6h cooldown — tab maxed

        # 3c. Edge case: no tech to research (no confirm button visible)
        no_confirm = detector.check_special_state(serial, target="RESEARCH_NO_CONFIRM")
        if no_confirm:
            print(f"[{serial}] No available tech to research (requirements not met). Dismissing popup...")
            adb_helper.tap(serial, 415, 520)
            time.sleep(2)
            continue

        # 3d. Tap Confirm Research
        confirm_match = detector.check_activity(serial, target="RESEARCH_CONFIRM", threshold=0.8)
        if not confirm_match:
            print(f"[{serial}] [WARNING] Confirm button not found. Dismissing popup...")
            adb_helper.tap(serial, 415, 520)
            time.sleep(2)
            continue

        # TODO: OCR timer reading for dynamic cooldown (future feature)
        _, cx, cy = confirm_match
        print(f"[{serial}] Tapping Confirm Research at ({cx}, {cy})...")
        adb_helper.tap(serial, cx, cy)
        time.sleep(3)

        # 3f. Edge case: not enough resources
        no_resource = detector.check_special_state(serial, target="RESEARCH_NO_RESOURCE")
        if no_resource:
            print(f"[{serial}] Not enough resources! Trying to use bag resources...")
            bag_match = detector.check_activity(serial, target="RESEARCH_USE_BAG", threshold=0.8)
            if bag_match:
                _, bx, by = bag_match
                print(f"[{serial}] Tapping Use Resource in Bag at ({bx}, {by})...")
                adb_helper.tap(serial, bx, by)
                time.sleep(3)
                
                still_no = detector.check_special_state(serial, target="RESEARCH_NO_RESOURCE")
                if still_no:
                    print(f"[{serial}] Still not enough resources even after bag. Cancelling.")
                    adb_helper.tap(serial, 415, 520)
                    time.sleep(2)
                    continue
            else:
                print(f"[{serial}] No 'Use Bag' button found. Cancelling research.")
                adb_helper.tap(serial, 415, 520)
                time.sleep(2)
                continue

        # 3g. Handle Alliance Help popup after confirming
        _human_delay(2)
        # ── DEBUG: save post-confirm frame ──
        detector._screen_cache = None
        _dbg_post = detector.get_frame(serial)
        if _dbg_post is not None:
            import cv2 as _cv2
            _dbg_post_path = os.path.join(_dbg_dir, f"post_confirm_slot{slot_idx+1}_{serial}.png")
            _cv2.imwrite(_dbg_post_path, _dbg_post)
            print(f"[{serial}] [DEBUG] Saved post-confirm frame: {_dbg_post_path}")
        # ── END DEBUG ──
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
    time.sleep(2)

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
        
    time.sleep(3)
    print(f"[{serial}] [TIMING] Accessing SHOP construction took {time.time() - t0:.2f}s")
    
    t0 = time.time()
    # 3. Tap Claim
    print(f"[{serial}] Tapping Claim (718, 425)...")
    adb_helper.tap(serial, 718, 425)
    time.sleep(2)
    print(f"[{serial}] [TIMING] Tapping Claim took {time.time() - t0:.2f}s")
    
    t0 = time.time()
    # 4. Tap Hornor Point (PLUS icon)
    print(f"[{serial}] Tapping Hornor Point (PLUS icon) (278, 357)...")
    adb_helper.tap(serial, 278, 357)
    time.sleep(2)
    print(f"[{serial}] [TIMING] Tapping Hornor Point took {time.time() - t0:.2f}s")
    
    t0 = time.time()
    # 5. Tap claim point
    print(f"[{serial}] Tapping Claim point (714, 165)...")
    adb_helper.tap(serial, 714, 165)
    time.sleep(2)
    print(f"[{serial}] [TIMING] Tapping Claim point took {time.time() - t0:.2f}s")
    
    t0 = time.time()
    # 6. Back x2
    print(f"[{serial}] Pressing BACK x2 to exit menus...")
    adb_helper.press_back(serial)
    time.sleep(1)
    adb_helper.press_back(serial)
    time.sleep(1)
    print(f"[{serial}] [TIMING] Pressing BACK x2 took {time.time() - t0:.2f}s")
    
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
                time.sleep(2)  # Wait for claim animation
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
    time.sleep(2)

    # 3. Iterate category tabs
    total_stats = {"claimed": 0, "claim_tapped": 0, "incomplete": 0, "skipped": 0}

    for tab_idx, tab_tap in enumerate(_FESTIVAL_CATEGORY_TAPS):
        print(f"\n[{serial}] [FESTIVAL] --- Category Tab #{tab_idx+1} at {tab_tap} ---")

        try:
            adb_helper.tap(serial, tab_tap[0], tab_tap[1])
            time.sleep(1.5)  # Wait for UI to update

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
    result = go_to_pet_sanctuary(serial, detector)
    if not _is_ok(result):
        print(f"[{serial}] [FAILED] Could not reach Pet Sanctuary.")
        return _bubble(result, "NAV_TARGET_NOT_REACHED: Could not reach Pet Sanctuary")

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
                time.sleep(_TAP_DELAY)
                # Dismiss pet menu if accidentally tapped a pet
                adb_helper.tap(serial, _DISMISS_POS[0], _DISMISS_POS[1])
                time.sleep(_DISMISS_DELAY)

        time.sleep(_CYCLE_COOLDOWN)

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
        time.sleep(2)
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
        time.sleep(2)
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
        time.sleep(1)
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


def _navigate_to_hall_upgrade(serial: str, detector: GameStateDetector) -> dict:
    """
    Navigates to the Hall upgrade screen using V2 go_to_construction.
    """
    print(f"[{serial}] Navigating to Hall upgrade screen...")
    return go_to_construction(serial, detector, "HALL", feature="upgrade")


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
    hall_result = _navigate_to_hall_upgrade(serial, detector)
    if not _is_ok(hall_result):
        print(f"[{serial}] [FAILED] Could not enter Hall upgrade screen.")
        return result

    _human_delay(1.0)

    # 3. Recursive upgrade from Hall
    remaining_slots = _try_upgrade_or_go(serial, detector, remaining_slots, depth=0, max_depth=max_depth, result=result)

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

            # Use V2 go_to_construction to navigate directly to upgrade screen
            fallback_result = go_to_construction(serial, detector, construction_name, feature="upgrade")
            if not _is_ok(fallback_result):
                print(f"[{serial}] No upgrade icon on {construction_name}. Skipping.")
                continue

            _human_delay(0.8)

            # Try upgrade (reuse same recursive logic)
            remaining_slots = _try_upgrade_or_go(
                serial, detector, remaining_slots,
                depth=0, max_depth=max_depth, result=result
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

        result["upgraded"] += 1
        remaining_slots -= 1
        print(f"[{serial}] [depth={depth}] Construction upgraded! (total upgraded: {result['upgraded']}, remaining_slots: {remaining_slots})")

        # Dismiss any promo popup that appears after upgrade
        _human_delay(0.8)
        dismiss_promo_popup(serial, detector)

        # Get alliance help after upgrade
        if depth == 0:
            from backend.core.workflow.construction_data import CONSTRUCTION_TAPS
            hall_coords = CONSTRUCTION_TAPS["HALL"][0]
            print(f"[{serial}] Requesting alliance help (Hall @ {hall_coords})...")
            adb_helper.tap(serial, hall_coords[0], hall_coords[1])
        else:
            print(f"[{serial}] Requesting alliance help...")
            adb_helper.tap(serial, 475, 275)
        _human_delay(0.8)

        # Reset camera position after upgrade
        reset_position(serial)

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
        remaining_slots = _try_upgrade_or_go(serial, detector, remaining_slots, depth + 1, max_depth, result)

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
    _human_delay(2.0)

    # Verify Quest Menu opened
    detector._screen_cache = None
    quest_screen = detector.check_special_state(serial, target="QUEST_MENU")
    if not quest_screen:
        # Retry once — tap may have missed or overlay dismissed
        print(f"[{serial}] QUEST_MENU not detected. Retrying tap (35, 100)...")
        adb_helper.tap(serial, 35, 100)
        _human_delay(2.0)
        detector._screen_cache = None
        quest_screen = detector.check_special_state(serial, target="QUEST_MENU")
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
    adb_helper.press_back(serial)
    _human_delay(1.0)
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
    adb_helper.press_back(serial)
    _human_delay(1.0)
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
        print(f"[{serial}] [FAILED] Goblin Merchant icon not detected.")
        adb_helper.press_back(serial)
        _human_delay(1.0)
        return _fail("TEMPLATE_NO_MATCH: Goblin Merchant not found in Alliance Store")

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

    # ── Phase 5: Cleanup ──
    print(f"[{serial}] === BUY MERCHANT ITEMS COMPLETE — bought {total_bought} item(s) ===")
    adb_helper.press_back(serial)
    _human_delay(1.0)
    return _ok()


def _scan_and_buy_rss_items(
    serial: str,
    detector: GameStateDetector,
    rss_targets: list,
    grid_half: str,
    x_offset: int = 0,
) -> int:
    """
    Helper: scan current visible grid for RSS-priced items and buy them one by one.
    Re-detects after each purchase. Saves debug screenshots with annotations.
    """
    # Debug output dir
    debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "_merchant_debug")
    os.makedirs(debug_dir, exist_ok=True)

    bought = 0
    MAX_BUYS_PER_HALF = 8  # Safety cap
    scan_idx = 0

    for _ in range(MAX_BUYS_PER_HALF):
        scan_idx += 1
        # Re-detect every iteration (grid shifts after each buy)
        detector._screen_cache = None
        frame = detector.screencap_memory(serial)
        if frame is None:
            print(f"[{serial}] [{grid_half}] [DEBUG] Screencap failed. Stopping.")
            break

        # ── Debug: annotate frame with ALL matches for ALL targets ──
        annotated = frame.copy()
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        all_debug_matches = []

        for target in rss_targets:
            if target not in detector.activity_templates:
                continue
            for entry in detector.activity_templates[target]:
                tmpl_gray = entry["gray"]
                if (frame_gray.shape[0] < tmpl_gray.shape[0] or
                        frame_gray.shape[1] < tmpl_gray.shape[1]):
                    continue
                res = cv2.matchTemplate(frame_gray, tmpl_gray, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                h, w = tmpl_gray.shape[:2]
                if max_val >= 0.5:  # Low threshold for debug visibility
                    cx, cy = max_loc[0] + w // 2, max_loc[1] + h // 2
                    all_debug_matches.append((target, max_loc[0], max_loc[1], w, h, max_val, cx, cy))

        # Draw all detections on annotated frame
        for tname, tx, ty, tw, th, conf, cx, cy in all_debug_matches:
            color = (0, 255, 0) if conf >= 0.8 else (0, 165, 255) if conf >= 0.6 else (0, 0, 255)
            cv2.rectangle(annotated, (tx, ty), (tx + tw, ty + th), color, 2)
            cv2.drawMarker(annotated, (cx, cy), color, cv2.MARKER_CROSS, 10, 2)
            label = f"{tname} {conf:.3f}"
            cv2.putText(annotated, label, (tx, max(ty - 4, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1, cv2.LINE_AA)

        ts = time.strftime("%H%M%S")
        dbg_path = os.path.join(debug_dir, f"{serial}_{grid_half}_{scan_idx:02d}_{ts}.png")
        cv2.imwrite(dbg_path, annotated)
        print(f"[{serial}] [{grid_half}] [DEBUG] Scan #{scan_idx} saved: {dbg_path}")
        for tname, tx, ty, tw, th, conf, cx, cy in all_debug_matches:
            status = "PASS" if conf >= 0.8 else "BELOW"
            print(f"[{serial}] [{grid_half}] [DEBUG]   {tname}: conf={conf:.4f} center=({cx},{cy}) [{status}]")

        # ── Actual detection with threshold ──
        match = None
        for target in rss_targets:
            result = detector.check_activity(serial, target=target, threshold=0.8, frame=frame)
            if result:
                match = result
                break

        if not match:
            print(f"[{serial}] [{grid_half}] No more RSS items above threshold.")
            break

        _, mx, my = match
        tap_x = mx + x_offset
        print(f"[{serial}] [{grid_half}] Tapping RSS item '{match[0]}' at ({tap_x}, {my})...")
        adb_helper.tap(serial, tap_x, my)
        _human_delay(1.0)

        bought += 1
        print(f"[{serial}] [{grid_half}] Bought {bought} item(s) so far.")

    if bought == 0:
        print(f"[{serial}] [{grid_half}] No RSS items found in this half.")

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

    # Phase 3: Tap Honorary Membership
    hx, hy = HONORARY_MEMBERSHIP_TAP
    print(f"[{serial}] Tapping Honorary Membership ({hx}, {hy})...")
    adb_helper.tap(serial, hx, hy)
    _human_delay(2.0)

    # Phase 4: Tap Claim
    cx, cy = CLAIM_TAP
    print(f"[{serial}] Tapping Claim reward ({cx}, {cy})...")
    adb_helper.tap(serial, cx, cy)
    _human_delay(2.0)

    # Phase 5: Cleanup
    print(f"[{serial}] === CLAIM DAILY VIP REWARD COMPLETE ===")
    adb_helper.press_back(serial)
    _human_delay(1.0)
    return _ok()
