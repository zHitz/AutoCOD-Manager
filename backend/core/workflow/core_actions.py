import sys
import os
import time

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
from workflow.construction_data import CONSTRUCTION_TAPS

import numpy as np
import cv2

# Global cache to store the last screenshot hash/image for freeze detection
_FREEZE_CACHE = {}

def ensure_app_running(serial: str, package_name: str, adb_path: str = config.adb_path) -> bool:
    """Checks if the app is active, and boots it if it's not. Returns True if it was already running."""
    if not clipper_helper.is_app_foreground(adb_path, serial, package_name):
        clipper_helper.open_app(adb_path, serial, package_name)
        return False
    return True

def check_app_crash(serial: str, package_name: str = "com.farlightgames.samo.gp.vn", adb_path: str = config.adb_path) -> bool:
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


def startup_to_lobby(serial: str, detector: GameStateDetector, package_name: str, adb_path: str = config.adb_path, load_timeout: int = 120) -> bool:
    """
    All-in-one startup: Boot game nếu chưa chạy -> chờ load vào Lobby.
    Nếu game đang chạy rồi -> dùng back_to_lobby() để mò về Lobby từ bất kỳ state nào.
    Returns True nếu đã chắc chắn đang ở Lobby, False nếu thất bại.
    """
    LOBBY_STATES = ["IN-GAME LOBBY (IN_CITY)", "IN-GAME LOBBY (OUT_CITY)"]
    
    was_running = ensure_app_running(serial, package_name, adb_path)
    
    if not was_running:
        print(f"[{serial}] App was not running. Waiting for game to load into Lobby...")
        lobby = wait_for_state(serial, detector, LOBBY_STATES, timeout_sec=load_timeout)
        if not lobby:
            print(f"[{serial}] [FAILED] Game did not load into Lobby after {load_timeout}s.")
            return False
        return True
    else:
        print(f"[{serial}] App is already running. Navigating back to Lobby...")
        return back_to_lobby(serial, detector)

def wait_for_state(serial: str, detector: GameStateDetector, target_states: list, timeout_sec: int = 60, package_name: str = "com.farlightgames.samo.gp.vn", check_mode: str = "state") -> str:
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
            current_state = detector.check_special_state(serial)
        elif check_mode == "activity":
            result = detector.check_activity(serial)
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
                
            time.sleep(2)

def go_to_profile(serial: str, detector: GameStateDetector) -> bool:
    """
    Assumes we are at the main lobby (`IN_CITY` or `OUT_CITY`).
    Navigates to the Profile menu. Returning True on success.
    """
    print(f"[{serial}] Navigating to Profile...")
    adb_helper.tap(serial, 25, 25)
    
    state = wait_for_state(serial, detector, ["IN-GAME LOBBY (PROFILE MENU)"], timeout_sec=10)
    return state is not None

def go_to_profile_details(serial: str, detector: GameStateDetector) -> bool:
    """
    Assumes we are at the Profile Menu.
    Navigates to the Profile Details menu. Returning True on success.
    """
    print(f"[{serial}] Navigating to Profile Details...")
    go_to_profile(serial, detector)
    time.sleep(3)
    adb_helper.tap(serial, 550, 200)
    
    state = wait_for_state(serial, detector, ["IN-GAME LOBBY (PROFILE MENU DETAIL)"], timeout_sec=10)
    return state is not None

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

def back_to_lobby(serial: str, detector: GameStateDetector, max_attempts: int = 15, target_lobby: str = None) -> bool:
    """
    Intelligently navigates back to the main Lobby from ANY state.
    Handles edge cases:
      - LOADING SCREEN: Waits 20s before attempting back (avoid breaking the load).
      - UNKNOWN / TRANSITION: Waits 10s grace period before pressing back.
      - Known menu states: Presses back immediately, but max 3 times per state
        before escalating (prevents infinite back-press on sticky menus).
    
    target_lobby: Optional. If set to 'IN-GAME LOBBY (IN_CITY)' or 'IN-GAME LOBBY (OUT_CITY)',
                  will swap lobby by tapping (50, 500) after reaching any lobby.
    Returns True if Lobby was reached, False on failure.
    """
    LOBBY_STATES = ["IN-GAME LOBBY (IN_CITY)", "IN-GAME LOBBY (OUT_CITY)"]
    
    print(f"[{serial}] === BACK TO LOBBY ===")
    
    known_state_back_count = 0   # How many times we pressed back on the same known state
    last_known_state = None      # Track the last known state to count consecutive backs
    unknown_start_time = None    # Timer for UNKNOWN grace period
    loading_screen_count = 0     # Timer for LOADING SCREEN loop
    
    for attempt in range(1, max_attempts + 1):
        current_state = detector.check_state(serial)
        print(f"[{serial}] [Attempt {attempt}/{max_attempts}] State: {current_state}")
        
        # === SUCCESS: Already at Lobby ===
        if current_state in LOBBY_STATES:
            print(f"[{serial}] -> Lobby reached! ({current_state})")
            
            # Swap lobby if target specified and doesn't match
            if target_lobby and current_state != target_lobby:
                print(f"[{serial}] -> Swapping to {target_lobby}...")
                adb_helper.tap(serial, 50, 500)
                swapped = wait_for_state(serial, detector, [target_lobby], timeout_sec=10)
                if not swapped:
                    print(f"[{serial}] [WARNING] Could not swap to {target_lobby}.")
                    return False
                print(f"[{serial}] -> Swapped to {target_lobby}.")
            return True
        
        # === CASE 1: LOADING SCREEN — Wait patiently, do NOT press back ===
        if current_state == "LOADING SCREEN":
            loading_screen_count += 1
            if loading_screen_count >= 3:
                print(f"[{serial}] -> Loading detected {loading_screen_count} times. Checking for Server Maintenance...")
                special_state = detector.check_special_state(serial, target="SERVER_MAINTENANCE")
                if special_state == "SERVER_MAINTENANCE":
                    print(f"[{serial}] [FATAL] Server Maintenance detected! Aborting script.")
                    sys.exit(f"[{serial}] Server Maintenance - Script Terminated")

            print(f"[{serial}] -> Loading detected. Waiting 20s before next check...")
            unknown_start_time = None  # Reset unknown timer
            known_state_back_count = 0
            last_known_state = None
            time.sleep(20)
            continue
            
        # Reset loading count if we entered a different state
        loading_screen_count = 0
        
        # === CASE 2: LOADING SCREEN (NETWORK ISSUE) — Wait patiently, do NOT press back ===
        if current_state == "LOADING SCREEN (NETWORK ISSUE)":
            print(f"[{serial}] -> Network issue detected. Click Confirm for restart")
            adb_helper.tap(serial, 500, 325)
            time.sleep(2)
            continue

        # === CASE 3: UNKNOWN — Check if it's a construction screen ===
        if current_state == "UNKNOWN / TRANSITION":
            construction = detector.check_construction(serial)
            if construction:
                print(f"[{serial}] -> Construction '{construction}' detected. Pressing BACK...")
                unknown_start_time = None
                adb_helper.press_back(serial)
                time.sleep(2)
                continue
            
            # Not a construction either — grace period
            if unknown_start_time is None:
                unknown_start_time = time.time()
                print(f"[{serial}] -> Unknown state. Starting 10s grace period...")
                time.sleep(3)
                continue
            
            elapsed = time.time() - unknown_start_time
            if elapsed < 10:
                remaining = 10 - elapsed
                print(f"[{serial}] -> Still unknown. Grace period: {remaining:.0f}s left...")
                time.sleep(3)
                continue
            else:
                # Grace period expired, press back
                print(f"[{serial}] -> Unknown for >10s. Pressing BACK immediately...")
                adb_helper.press_back(serial)
                # Không reset unknown_start_time để các lần sau nếu vẫn kẹt thì tự động back tiếp luôn
                time.sleep(2)
                continue
        
        # === CASE 4: Known named state (Profile Menu, Events, etc.) ===
        unknown_start_time = None  # Reset unknown timer since we have a known state
        
        if current_state == last_known_state:
            known_state_back_count += 1
        else:
            # New state detected, reset counter
            last_known_state = current_state
            known_state_back_count = 1
        
        if known_state_back_count <= 3:
            print(f"[{serial}] -> Known state '{current_state}'. Pressing BACK ({known_state_back_count}/3)...")
            adb_helper.press_back(serial)
            time.sleep(2)
        else:
            # Pressed back 3 times on the same state and it's not changing
            print(f"[{serial}] -> [WARNING] State '{current_state}' stuck after 3 backs. Forcing extra wait...")
            time.sleep(5)
            known_state_back_count = 0  # Reset and try again
    
    print(f"[{serial}] [FAILED] Could not reach Lobby after {max_attempts} attempts.")
    return False

def ensure_lobby_menu_open(serial: str, detector: GameStateDetector, max_attempts: int = 5) -> bool:
    """
    Ensures the expandable lobby menu is open.
    Uses detector.is_menu_expanded() which is separate from check_state().
    If menu is closed and we're at Lobby, taps the expand button (925, 500).
    Returns True if menu is confirmed open, False on failure.
    """
    LOBBY_STATES = ["IN-GAME LOBBY (IN_CITY)", "IN-GAME LOBBY (OUT_CITY)"]
    
    for attempt in range(1, max_attempts + 1):
        if detector.is_menu_expanded(serial):
            print(f"[{serial}] -> Lobby menu is already open.")
            return True
        
        current_state = detector.check_state(serial)
        print(f"[{serial}] [ensure_menu] Attempt {attempt}/{max_attempts} | State: {current_state} | Menu: closed")
        
        if current_state in LOBBY_STATES:
            print(f"[{serial}] -> Tapping expand button (925, 500)...")
            adb_helper.tap(serial, 925, 500)
            time.sleep(2)
            continue
        
        # Not in a lobby state at all
        print(f"[{serial}] -> [WARNING] Not in Lobby state ({current_state}). Cannot expand menu.")
        return False
    
    print(f"[{serial}] [FAILED] Could not confirm lobby menu open after {max_attempts} attempts.")
    return False

def go_to_resources(serial: str, detector: GameStateDetector) -> bool:
    """Navigates to the Resources menu from Lobby."""
    print(f"[{serial}] Navigating to Resources...")
    
    if not ensure_lobby_menu_open(serial, detector):
        print(f"[{serial}] [FAILED] Could not open lobby menu.")
        return False
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
            if not ensure_lobby_menu_open(serial, detector):
                return False
            continue
        
        # Unknown state — likely some other IN-GAME ITEMS tab without a template
        # Tap (75, 180) directly to switch to Resources tab
        print(f"[{serial}] -> Unknown Items tab ({current}). Tapping (75, 180) to switch to Resources...")
        items_reached = True
        break
    
    if not items_reached:
        print(f"[{serial}] [FAILED] Could not enter Items menu after 3 retries.")
        return False
    
    # If we landed on Resources directly, skip tapping (75, 180)
    if state != "IN-GAME ITEMS (RESOURCES)":
        adb_helper.tap(serial, 75, 180)
        state = wait_for_state(serial, detector, ["IN-GAME ITEMS (RESOURCES)"], timeout_sec=15)

        if not state:
            print(f"[{serial}] [FAILED] Could not reach Items - Resources state.")
            return False

    adb_helper.tap(serial, 620, 100)
    time.sleep(5)
    
    return True

def go_to_construction(serial: str, detector: GameStateDetector, name: str) -> bool:
    """
    Generic navigation to any construction building.
    Looks up tap coordinates from construction_data.py.
    Must navigate to IN-GAME LOBBY (IN_CITY) first.
    """
    name_upper = name.upper()
    
    if name_upper not in CONSTRUCTION_TAPS:
        print(f"[{serial}] [FAILED] Unknown construction '{name}'. Not found in construction_data.")
        return False
    
    print(f"[{serial}] Navigating to construction: {name_upper}...")
    
    back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    current_state = detector.check_state(serial)
    if current_state != "IN-GAME LOBBY (IN_CITY)":
        print(f"[{serial}] [FAILED] Must be IN_CITY. Current: {current_state}")
        return False
    
    # Execute tap sequence from data
    taps = CONSTRUCTION_TAPS[name_upper]
    for i, (x, y) in enumerate(taps):
        adb_helper.tap(serial, x, y)
        time.sleep(2)
    time.sleep(3)  # Extra wait for building info to load
    
    # Verify via construction detector
    result = detector.check_construction(serial, target=name_upper)
    if result:
        print(f"[{serial}] -> {name_upper} detected successfully.")
        return True
    
    print(f"[{serial}] [WARNING] Could not confirm {name_upper} opened.")
    return False

def go_to_capture_pet(serial: str, detector: GameStateDetector) -> bool:
    """
    Navigates from OUT_CITY to Auto Capture Pet screen and starts capture.
    Returns True if capture was started successfully.
    """
    print(f"[{serial}] Navigating to Capture Pet...")
    
    # 1. Back to lobby OUT_CITY
    if not back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)"):
        print(f"[{serial}] [FAILED] Could not reach OUT_CITY lobby.")
        return False
        
    # 2. Tap Menu search
    print(f"[{serial}] Opening Search Menu (42, 422)...")
    adb_helper.tap(serial, 42, 422)
    time.sleep(3)
    
    # 3. Tap Menu search Pet
    print(f"[{serial}] Selecting Pet Search (304, 209)...")
    adb_helper.tap(serial, 304, 209)
    time.sleep(3)

    # 4. Tap Auto Capture submenu
    print(f"[{serial}] Selecting Auto Capture (285, 400)...")
    adb_helper.tap(serial, 285, 400)
    time.sleep(3)

    # 5. Verify state AUTO_CAPTURE_PET
    print(f"[{serial}] Waiting for AUTO_CAPTURE_PET state...")
    state = wait_for_state(serial, detector, ["AUTO_CAPTURE_PET"], timeout_sec=10, check_mode="special")
    
    if state != "AUTO_CAPTURE_PET":
        print(f"[{serial}] [FAILED] Did not reach AUTO_CAPTURE_PET state.")
        return False

    # 6. Tap (284, 398) x5 to configure
    print(f"[{serial}] Configuring Pet Capture (284, 398) x5...")
    for _ in range(5):
        adb_helper.tap(serial, 284, 398)
        time.sleep(1)
    time.sleep(3)
    
    # 7. Tap Start
    print(f"[{serial}] Starting Capture (501, 466)...")
    adb_helper.tap(serial, 501, 466)
    time.sleep(2)
    return True

def go_to_pet_sanctuary(serial: str, detector: GameStateDetector) -> bool:
    """
    Navigates from lobby (OUT_CITY) through Pet Sanctuary into Pet Enclosure.
    Returns True if PET_ENCLOSURE state is reached successfully.
    """
    print(f"[{serial}] Navigating to Pet Sanctuary...")

    # 1. Back to lobby OUT_CITY & open menu
    if not back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)"):
        print(f"[{serial}] [FAILED] Could not reach OUT_CITY.")
        return False
    if not ensure_lobby_menu_open(serial, detector):
        print(f"[{serial}] [FAILED] Could not expand lobby menu.")
        return False
        
    # 2. Tap (510, 507) to open Sanctuary
    print(f"[{serial}] Opening Pet Sanctuary (510, 507)...")
    adb_helper.tap(serial, 510, 507)
    time.sleep(3)
    
    # 3. Verify PET_SANCTUARY
    state = wait_for_state(serial, detector, ["PET_SANCTUARY"], timeout_sec=10, check_mode="construction")
    if state != "PET_SANCTUARY":
        print(f"[{serial}] [FAILED] Did not reach PET_SANCTUARY state.")
        return False
    
    print(f"[{serial}] -> PET_SANCTUARY reached successfully.")
    return True

def release_pet(serial: str, detector: GameStateDetector) -> bool:
    """
    Navigates from PET_SANCTUARY into PET_ENCLOSURE, then executes full pet release loop.
    Call go_to_pet_sanctuary() first.
    """
    print(f"[{serial}] Starting Pet Release...")

    # 1. Tap (918, 504) to open Enclosure
    print(f"[{serial}] Opening Pet Enclosure (918, 504)...")
    adb_helper.tap(serial, 918, 504)
    time.sleep(3)
    
    # 2. Verify PET_ENCLOSURE
    state = wait_for_state(serial, detector, ["PET_ENCLOSURE"], timeout_sec=10, check_mode="construction")
    if state != "PET_ENCLOSURE":
        print(f"[{serial}] [FAILED] Did not reach PET_ENCLOSURE state.")
        return False

    # Navigate release tabs
    print(f"[{serial}] Selecting Release Tabs (254,93) -> (670,131) -> (50,135)...")
    adb_helper.tap(serial, 254, 93)
    time.sleep(2)
    adb_helper.tap(serial, 670, 131)
    time.sleep(2)
    adb_helper.tap(serial, 50, 135)
    time.sleep(2)
    
    def release_loop(tap_point, count):
        print(f"[{serial}] Release loop {tap_point} x{count}...")
        for _ in range(count):
            adb_helper.tap(serial, tap_point[0], tap_point[1])
            time.sleep(1.5)
            adb_helper.tap(serial, 352, 214)
            time.sleep(1.5)
            adb_helper.tap(serial, 577, 365)
            time.sleep(1.5)
            adb_helper.tap(serial, 547, 414)
            time.sleep(2)
            
    release_loop((217, 320), 5)  # x5
    release_loop((151, 315), 3)  # x3
    release_loop((217, 320), 2)  # x2
    
    # Back x2
    print(f"[{serial}] Back x2 to exit Pet screen...")
    adb_helper.press_back(serial)
    time.sleep(2)
    adb_helper.press_back(serial)
    time.sleep(2)
    
    print(f"[{serial}] Pet Release completed!")
    return True

def go_to_farming(serial: str, detector: GameStateDetector, resource_type: str = "wood") -> bool:
    """
    Farming Workflow:
    1. Back to OUT_CITY
    2. Open Search Menu
    3. Select Resource Type (Wood, Stone, Gold, Mana)
    4. Start Search
    5. Tap Gather
    6. Check if Create Legion exists -> If so, dispatch available legions.
    """
    print(f"[{serial}] Starting Farming Workflow for: {resource_type.upper()}")
    
    # Coordinates mapping
    RESOURCE_TAPS = {
        "gold": (320, 485),
        "wood": (475, 485),
        "stone": (640, 485),
        "mana": (795, 485)
    }
    
    SEARCH_TAPS = {
        "gold": (320, 400),
        "wood": (475, 400),
        "stone": (640, 400),
        "mana": (795, 400)
    }
    
    LEGION_TAPS = [
        (695, 90), # legion_1
        (735, 90), # legion_2
        (780, 90), # legion_3
        (825, 90), # legion_4
        (865, 90)  # legion_5
    ]
    
    r_type = resource_type.lower()
    if r_type not in RESOURCE_TAPS:
        print(f"[{serial}] [ERROR] Unknown resource type: {resource_type}")
        return False
        
    # 1. Back to lobby OUT_CITY
    if not back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)"):
        print(f"[{serial}] [FAILED] Could not reach OUT_CITY lobby.")
        return False
        
    # Loop over legions. Will break when we hit max/can't deploy
    for idx, legion_tap in enumerate(LEGION_TAPS):
        print(f"\n[{serial}] --- Attempting Dispatch #{idx+1} ---")
        
        # 2. Tap Menu search
        print(f"[{serial}] Opening Search Menu (42, 422)...")
        adb_helper.tap(serial, 42, 422)
        time.sleep(4)

        # 3. Tap Resource Category
        res_x, res_y = RESOURCE_TAPS[r_type]
        print(f"[{serial}] Selecting Resource Category {r_type.upper()} ({res_x}, {res_y})...")
        adb_helper.tap(serial, res_x, res_y)
        time.sleep(3)

        # 4. Tap Search
        search_x, search_y = SEARCH_TAPS[r_type]
        print(f"[{serial}] Tapping Search ({search_x}, {search_y})...")
        adb_helper.tap(serial, search_x, search_y)
        time.sleep(6)  # Wait for map to pan

        # 5. Tap Gather Button
        print(f"[{serial}] Tapping Gather Button (665, 395)...")
        adb_helper.tap(serial, 665, 395)
        time.sleep(5)
        
        # 6. Check if we can create a legion with retries
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
            adb_helper.press_back(serial)
            time.sleep(3)
            # We are done farming.
            break
            
        print(f"[{serial}] Found CREATE_LEGION -> Deploying forces...")
        
        # 7. Create legion & Dispatch
        print(f"[{serial}] Tapping Create Legion Button (755, 115)...")
        adb_helper.tap(serial, 755, 115)
        time.sleep(4)
        
        print(f"[{serial}] Selecting Legion Preset #{idx+1} at {legion_tap}...")
        adb_helper.tap(serial, legion_tap[0], legion_tap[1])
        time.sleep(3)
        
        dispatch_loc = (850, 480) 
        print(f"[{serial}] Tapping March/Dispatch {dispatch_loc}...")
        adb_helper.tap(serial, dispatch_loc[0], dispatch_loc[1])
        
        # Game puts us back to OUT_CITY after dispatching
        # Sleep enough time to let the march animation start and UI settle
        time.sleep(7)
        
    print(f"[{serial}] Farming Deployment Finished.")
    return True

def go_to_rss_center_farm(serial: str, detector: GameStateDetector) -> bool:
    """
    Farms Alliance Resource Center:
    1. Go to OUT_CITY
    2. Open Markers menu
    3. Find RSS Center coordinate
    4. Tap Go -> Tap Gather -> Create Legion -> Dispatch
    """
    print(f"[{serial}] Starting Alliance Resource Center Farming...")
    if not back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)"):
        print(f"[{serial}] [FAILED] Could not reach OUT_CITY lobby.")
        return False
        
    print(f"[{serial}] Tapping Markers Icon (180, 16)...")
    adb_helper.tap(serial, 180, 16)
    time.sleep(3)
    
    # Wait for Markers Menu
    state = wait_for_state(serial, detector, ["MARKERS_MENU"], timeout_sec=10, check_mode="construction")
    if state != "MARKERS_MENU":
        print(f"[{serial}] [FAILED] Could not open Markers Menu.")
        return False
        
    # Check for Resource Center (Activity detector to get coords)
    print(f"[{serial}] Searching for Resource Center marker...")
    rss_marker = None
    for attempt in range(3):
        rss_marker = detector.check_activity(serial, target="RSS_CENTER_MARKER", threshold=0.8)
        if rss_marker:
            break
        time.sleep(2)
        
    if not rss_marker:
        print(f"[{serial}] Resource Center not found in markers! Aborting and returning to lobby.")
        adb_helper.press_back(serial)
        time.sleep(2)
        return False
        
    # rss_marker is (name, x, y)
    center_x, center_y = rss_marker[1], rss_marker[2]
    # Tap go to rss_center: (x+570, y)
    go_x, go_y = center_x + 570, center_y
    print(f"[{serial}] Found RSS Center. Tapping GO ({go_x}, {go_y})...")
    adb_helper.tap(serial, go_x, go_y)
    
    # Wait for map to pan
    time.sleep(6)
    
    # Tap the center of the screen
    print(f"[{serial}] Tapping RSS Center on map (479, 254)...")
    adb_helper.tap(serial, 479, 254)
    time.sleep(3)
    
    # Check for View vs Gather
    print(f"[{serial}] Checking whether to Gather or if already occupied...")
    view_state = detector.check_activity(serial, target="RSS_VIEW", threshold=0.8)
    if view_state:
        print(f"[{serial}] 'View' button detected. Legion already farming this Resource Center. Aborting.")
        adb_helper.tap(serial, 50, 500)
        time.sleep(2)
        return False
        
    gather_state = detector.check_activity(serial, target="RSS_GATHER", threshold=0.8)
    if not gather_state:
        print(f"[{serial}] 'Gather' button not found. Aborting.")
        adb_helper.tap(serial, 50, 500)
        time.sleep(2)
        return False
        
    g_x, g_y = gather_state[1], gather_state[2]
    print(f"[{serial}] Tapping Gather ({g_x}, {g_y})...")
    adb_helper.tap(serial, g_x, g_y)
    time.sleep(3)
    
    # Create new legion
    print(f"[{serial}] Tapping Create Legion (490, 277)...")
    adb_helper.tap(serial, 490, 277)
    time.sleep(3)
    
    # Create new legion (next screen)
    print(f"[{serial}] Setting up legion (755, 115)...")
    adb_helper.tap(serial, 755, 115)
    time.sleep(3)
    
    LEGION_5_TAP = (865, 90)
    print(f"[{serial}] Selecting Legion Preset #5 at {LEGION_5_TAP}...")
    adb_helper.tap(serial, LEGION_5_TAP[0], LEGION_5_TAP[1])
    time.sleep(2)
    
    dispatch_loc = (850, 480) 
    print(f"[{serial}] Tapping Dispatch {dispatch_loc}...")
    adb_helper.tap(serial, dispatch_loc[0], dispatch_loc[1])
    time.sleep(6)
    
    print(f"[{serial}] Successfully dispatched legion to Resource Center.")
    return True

def go_to_market(serial: str, detector: GameStateDetector) -> bool:
    """Navigates to Market."""
    print(f"[{serial}] Navigating to Market...")
    adb_helper.tap(serial, 639, 232)
    time.sleep(2)
    adb_helper.tap(serial, 545, 267)
    time.sleep(3)
    return True

def go_to_pet_token(serial: str, detector: GameStateDetector) -> bool:
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
    return True