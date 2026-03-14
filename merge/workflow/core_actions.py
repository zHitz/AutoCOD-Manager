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
from workflow.account_detector import AccountDetector
from workflow.construction_data import CONSTRUCTION_TAPS

import numpy as np
import cv2
import random

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
            frame = detector.get_frame(serial)
            current_state = None
            for ts in target_states:
                result = detector.check_construction(serial, target=ts, frame=frame)
                if result:
                    current_state = result
                    break
        elif check_mode == "special":
            frame = detector.get_frame(serial)
            current_state = None
            for ts in target_states:
                result = detector.check_special_state(serial, target=ts, frame=frame)
                if result:
                    current_state = result
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
                
            time.sleep(2)

def go_to_profile(serial: str, detector: GameStateDetector) -> bool:
    """
    Assumes we are at the main lobby (`IN_CITY` or `OUT_CITY`).
    Navigates to the Profile menu. Returning True on success.
    """
    if detector.check_state(serial) == "IN-GAME LOBBY (PROFILE MENU)":
        return True
        
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
        time.sleep(0.5)
    time.sleep(0.5)  # Extra wait for building info to load
    
    # Verify via construction detector
    result = detector.check_construction(serial, target=name_upper)
    if result:
        print(f"[{serial}] -> {name_upper} detected successfully.")
        return True
    
    print(f"[{serial}] [WARNING] Could not confirm {name_upper} opened.")
    return False

def go_to_capture_pet(serial: str, detector: GameStateDetector) -> bool:
    """
    Go to Capture Pet Full Phase
    """
    capture_pet(serial, detector)
    go_to_pet_sanctuary(serial, detector)
    release_pet(serial, detector)
    capture_pet(serial, detector)
    return True
    
def capture_pet(serial: str, detector: GameStateDetector) -> bool:
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
        return False

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
    outcome = wait_for_state(serial, detector, ["AUTO_CAPTURE_PET", "AUTO_CAPTURE_START", "AUTO_CAPTURE_IN_PROGRESS"], timeout_sec=10, check_mode="special")
    
    if outcome is None:
        print(f"[{serial}] Auto capture started & game pushed to map! Capture successful.")
        return True
        
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
        
    return True


def attack_darkling_legions_v1_basic(serial: str, detector: GameStateDetector) -> bool:
    """
    Basic Darkling Legions attack flow.
    Mirrors capture_pet structure but uses its own taps and target detector state.
    Adjust the tap coordinates below once the real UI is confirmed.
    """
    print(f"[{serial}] Navigating to Attack Darkling Legions V1 (BASIC)...")

    SEARCH_MENU_TAP = (42, 422)
    DARKLING_MENU_TAP = (158, 486)
    DARKLING_LEGIONS_TAB_TAP = (50, 210)
    ACTION_BUTTON_TAP = (285, 400)
    DISPATCH_TAP = (500, 465)
    TARGET_STATES = ["AUTO_PEACEKEEPING"]

    # 1. Back to lobby OUT_CITY
    if not back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)"):
        print(f"[{serial}] [FAILED] Could not reach OUT_CITY lobby.")
        return False

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
        return False

    # 7. Tap Start
    print(f"[{serial}] Starting Peacekeeping dispatch {DISPATCH_TAP}...")
    adb_helper.tap(serial, DISPATCH_TAP[0], DISPATCH_TAP[1])
    time.sleep(2)

    # 8. Check outcome
    print(f"[{serial}] Checking outcome of Darkling Legions dispatch...")
    outcome = wait_for_state(serial, detector, TARGET_STATES, timeout_sec=5, check_mode="special")

    if outcome is None:
        print(f"[{serial}] Dispatch started & game pushed to map! Attack successful.")
        return True

    if outcome == "AUTO_PEACEKEEPING":
        print(f"[{serial}] Still on Peacekeeping screen. Out of CP.")
        adb_helper.press_back(serial)

    return True

def research_technology(serial: str, detector: GameStateDetector, research_type: str = "default") -> bool:
    """
    Automates Technology Research at Research Center.
    
    research_type:
      - "economy": tap Economy tab (30, 190) before researching
      - "military": tap Military tab (30, 320) before researching
      - "balance": alternate economy/military per slot
      - "default": don't tap any tab, just research whatever is shown
    
    Flow:
      1. Navigate to Research Center
      2. Handle any existing Alliance Help buttons
      3. Detect empty slots → select tech type → research → confirm
      4. Handle edge cases (no resources, no tech available)
    """
    print(f"[{serial}] === TECHNOLOGY RESEARCH (type={research_type}) ===")

    ECONOMY_TAB_TAP = (30, 190)
    MILITARY_TAB_TAP = (30, 320)

    # 1. Navigate to Research Center
    if not go_to_construction(serial, detector, "RESEARCH_CENTER"):
        print(f"[{serial}] [FAILED] Could not navigate to Research Center.")
        return False

    # Verify we're at Research Center
    state = wait_for_state(serial, detector, ["RESEARCH_CENTER"], timeout_sec=10, check_mode="construction")
    if state != "RESEARCH_CENTER":
        print(f"[{serial}] [FAILED] Did not reach RESEARCH_CENTER screen.")
        return False

    print(f"[{serial}] Research Center opened successfully.")

    # 2. Scan for Alliance Help buttons first (already researching, need help)
    alliance_help_count = 0
    for scan in range(2):
        help_match = detector.check_activity(serial, target="RESEARCH_ALLIANCE_HELP", threshold=0.8)
        if help_match:
            _, hx, hy = help_match
            print(f"[{serial}] Found Alliance Help button at ({hx}, {hy}). Tapping...")
            adb_helper.tap(serial, hx, hy)
            time.sleep(2)
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

        # Detect empty slot
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

        # 3c. Edge case #2: no tech to research (no confirm button visible)
        no_confirm = detector.check_special_state(serial, target="RESEARCH_NO_CONFIRM")
        if no_confirm:
            print(f"[{serial}] No available tech to research (requirements not met). Backing out.")
            adb_helper.press_back(serial)
            time.sleep(2)
            continue

        # 3d. Tap Confirm Research
        confirm_match = detector.check_activity(serial, target="RESEARCH_CONFIRM", threshold=0.8)
        if not confirm_match:
            print(f"[{serial}] [WARNING] Confirm button not found. Backing out.")
            adb_helper.press_back(serial)
            time.sleep(2)
            continue

        _, cx, cy = confirm_match
        print(f"[{serial}] Tapping Confirm Research at ({cx}, {cy})...")
        adb_helper.tap(serial, cx, cy)
        time.sleep(3)

        # 3e. Edge case #1: not enough resources
        no_resource = detector.check_special_state(serial, target="RESEARCH_NO_RESOURCE")
        if no_resource:
            print(f"[{serial}] Not enough resources! Trying to use bag resources...")
            bag_match = detector.check_activity(serial, target="RESEARCH_USE_BAG", threshold=0.8)
            if bag_match:
                _, bx, by = bag_match
                print(f"[{serial}] Tapping Use Resource in Bag at ({bx}, {by})...")
                adb_helper.tap(serial, bx, by)
                time.sleep(3)
                
                # Re-check if still no resource after using bag
                still_no = detector.check_special_state(serial, target="RESEARCH_NO_RESOURCE")
                if still_no:
                    print(f"[{serial}] Still not enough resources even after bag. Cancelling.")
                    adb_helper.press_back(serial)
                    time.sleep(2)
                    continue
            else:
                print(f"[{serial}] No 'Use Bag' button found. Cancelling research.")
                adb_helper.press_back(serial)
                time.sleep(2)
                continue

        # 3f. Check for Alliance Help popup after confirming
        time.sleep(2)
        post_help = detector.check_activity(serial, target="RESEARCH_ALLIANCE_HELP", threshold=0.8)
        if post_help:
            _, phx, phy = post_help
            print(f"[{serial}] Alliance Help appeared at ({phx}, {phy}). Tapping...")
            adb_helper.tap(serial, phx, phy)
            time.sleep(2)

        slots_researched += 1
        print(f"[{serial}] Slot #{slot_idx + 1} research started successfully!")

    print(f"[{serial}] === TECHNOLOGY RESEARCH COMPLETE ({slots_researched} slot(s) started) ===")
    adb_helper.press_back(serial)
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
    return True

def heal_troops(serial: str, detector: GameStateDetector, healing_method: str = "elixir", troop_priorities: list = None) -> bool:
    """
    Heals troops using Exlixir Healing building.
    healing_method: 'elixir' or 'resources' (default: 'elixir')
    troop_priorities: list of strings (e.g., ['infantry', 'cavalry', 'archer', 'mage', 'workhorses', 'siege'])
    """
    print(f"[{serial}] Starting Troop Healing workflow...")
    
    # 1. Back to lobby IN_CITY
    if not back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)"):
        print(f"[{serial}] [FAILED] Could not reach IN_CITY lobby.")
        return False
        
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
        return False
        
    # 3. Tap Healing Icon
    _, icon_x, icon_y = icon_match
    print(f"[{serial}] Found Healing Icon. Tapping at ({icon_x}, {icon_y})...")
    adb_helper.tap(serial, icon_x, icon_y)
    
    # 4. Wait for Exlixir Healing screen
    state = wait_for_state(serial, detector, ["ELIXIR_HEALING"], timeout_sec=10, check_mode="construction")
    if state != "ELIXIR_HEALING":
        print(f"[{serial}] [FAILED] Did not reach ELIXIR_HEALING screen.")
        return False
        
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
    
    return True

def buy_merchant_items(serial: str, detector: GameStateDetector, max_refreshes: int = 5) -> bool:
    """
    Buys all resource-priced items from the Goblin Merchant.
    Skips gem-priced items. Scrolls down for more items. Refreshes up to max_refreshes times.
    Assumes we are already at the GOBLIN_MERCHANT screen (call go_to_goblin_merchant first).
    """
    print(f"[{serial}] Starting Goblin Merchant buy workflow (Refreshes: {max_refreshes})...")
    
    # Load resource icon template for price checking
    templates_dir = detector.templates_dir
    resource_icon_path = os.path.join(templates_dir, "icon_markers", "merchant_resource_icon.png")
    resource_icon = cv2.imread(resource_icon_path, cv2.IMREAD_COLOR)
    if resource_icon is None:
        print(f"[{serial}] [FAILED] Could not load merchant_resource_icon.png from {resource_icon_path}")
        return False
    
    # Grid layout: 4 columns x 2 rows of buy buttons (center coordinates)
    # Adjust these after testing with tool_region_selector.py
    SLOT_BUY_BUTTONS = [
        # Row 1 (Speedups)
        (258, 295), (412, 295), (567, 295), (720, 295),
        # Row 2 (Boosts)
        (258, 462), (412, 462), (567, 462), (720, 462),
    ]
    
    # Offset from buy button center to the resource/gem icon region
    ICON_OFFSET_X = -55   # icon is to the left of price text
    ICON_OFFSET_Y = -12   # slightly above center
    ICON_CROP_W = 28
    ICON_CROP_H = 28
    
    REFRESH_BTN = (728, 130)
    
    def _scan_and_buy_visible(screenshot):
        """Scan all visible slots and buy resource-priced items. Returns count of items bought."""
        bought = 0
        for idx, (bx, by) in enumerate(SLOT_BUY_BUTTONS):
            # Crop the small region where the price icon lives
            ix = bx + ICON_OFFSET_X
            iy = by + ICON_OFFSET_Y
            
            # Bounds check
            if iy < 0 or ix < 0:
                continue
            if iy + ICON_CROP_H > screenshot.shape[0] or ix + ICON_CROP_W > screenshot.shape[1]:
                continue
                
            crop = screenshot[iy:iy + ICON_CROP_H, ix:ix + ICON_CROP_W]
            
            # Template match against resource icon
            if crop.shape[0] < resource_icon.shape[0] or crop.shape[1] < resource_icon.shape[1]:
                # Crop is smaller than template — do full-region match instead
                res = cv2.matchTemplate(screenshot, resource_icon, cv2.TM_CCOEFF_NORMED)
                # This fallback won't help per-slot, skip
                continue
            
            res = cv2.matchTemplate(crop, resource_icon, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            
            if max_val >= 0.8:
                print(f"[{serial}] Slot {idx+1} ({bx},{by}): RESOURCE price (conf: {max_val:.3f}) -> BUYING")
                adb_helper.tap(serial, bx, by)
                time.sleep(2)
                bought += 1
            else:
                print(f"[{serial}] Slot {idx+1} ({bx},{by}): GEM price (conf: {max_val:.3f}) -> SKIP")
        
        return bought
    
    total_bought = 0
    
    for refresh_round in range(max_refreshes + 1):
        print(f"\n[{serial}] --- Merchant Round {refresh_round + 1}/{max_refreshes + 1} ---")
        
        # Verify still on merchant screen
        state = detector.check_construction(serial, target="GOBLIN_MERCHANT")
        if state != "GOBLIN_MERCHANT":
            print(f"[{serial}] [WARNING] Not on GOBLIN_MERCHANT screen. Attempting recovery...")
            time.sleep(2)
            state = detector.check_construction(serial, target="GOBLIN_MERCHANT")
            if state != "GOBLIN_MERCHANT":
                print(f"[{serial}] [FAILED] Lost merchant screen. Aborting.")
                break
        
        # Take screenshot and scan visible slots
        screenshot = detector.screencap_memory(serial)
        if screenshot is None:
            print(f"[{serial}] [FAILED] Could not capture screen.")
            break
            
        bought = _scan_and_buy_visible(screenshot)
        total_bought += bought
        
        # Scroll down to reveal "Other" section
        print(f"[{serial}] Scrolling down for more items...")
        adb_helper.swipe(serial, 480, 450, 480, 200, duration=500)
        time.sleep(3)
        
        # Take new screenshot and scan again
        screenshot = detector.screencap_memory(serial)
        if screenshot is not None:
            bought = _scan_and_buy_visible(screenshot)
            total_bought += bought
        
        # Scroll back up to reset view
        adb_helper.swipe(serial, 480, 200, 480, 450, duration=500)
        time.sleep(2)
        
        # Refresh if not the last round
        if refresh_round < max_refreshes:
            print(f"[{serial}] Tapping Refresh button ({REFRESH_BTN})...")
            adb_helper.tap(serial, REFRESH_BTN[0], REFRESH_BTN[1])
            time.sleep(3)
    
    print(f"\n[{serial}] Goblin Merchant complete! Total items bought: {total_bought}")
    
    # Return to lobby
    adb_helper.press_back(serial)
    time.sleep(2)
    
    return True

def go_to_alliance(serial: str, detector: GameStateDetector) -> bool:
    """
    Navigates to the Alliance menu from Lobby IN_CITY.
    Returns True if ALLIANCE_MENU state is reached successfully.
    """
    print(f"[{serial}] Navigating to Alliance Menu...")
    
    # 1. Back to lobby IN_CITY & open menu
    if not back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)"):
        print(f"[{serial}] [FAILED] Could not reach IN_CITY lobby.")
        return False
        
    if not ensure_lobby_menu_open(serial, detector):
        print(f"[{serial}] [FAILED] Could not expand lobby menu.")
        return False
        
    # 2. Tap Alliance Icon
    print(f"[{serial}] Tapping Alliance Icon...")
    adb_helper.tap(serial, 719, 503)
    time.sleep(3)
    
    # 3. Verify ALLIANCE_MENU
    state = wait_for_state(serial, detector, ["ALLIANCE_MENU"], timeout_sec=10, check_mode="construction")
    if state != "ALLIANCE_MENU":
        print(f"[{serial}] [FAILED] Did not reach ALLIANCE_MENU. Account might not be in an Alliance.")
        return False
        
    print(f"[{serial}] -> ALLIANCE_MENU reached successfully.")
    return True

def go_to_alliance_war_loop(serial: str, detector: GameStateDetector, loop_count: int = 1) -> bool:
    """
    Function Claim Ressource in CITY LOBBY
    Workflow:
    1. in lobby IN_CITY
    2. Go to Alliance
    3. Go to War (alliance/war.png)
    4. Check state in war if have rally (alliance/rally.png)
    5. Join Rally (tap rally button) 
    6. Using #6 in go_to_farm funciton (core_actions.py) to deploy legions. -> use legion_1
    7. tap (x.y) to go to lobby IN_CITY
    -> loop loop_count times
    """
    print(f"[{serial}] Starting Alliance War Rally Loop (Count: {loop_count})...")
    
    for loop in range(loop_count):
        print(f"\n[{serial}] --- Rally Loop #{loop+1}/{loop_count} ---")
            
        # 2. Go to Alliance
        if not go_to_alliance(serial, detector):
            print(f"[{serial}] [FAILED] Could not open Alliance Menu.")
            return False
            
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
    return True

def train_troops(serial: str, detector: GameStateDetector, training_list: list = None) -> bool:
    """
    Trains troops at the specified training houses and tiers.
    Requirements:
    - User must configure the 5 house center coordinates in HOUSE_TAPS.
    - User must configure the 5 tier coordinates in TIER_TAPS.
    - Requires TRAIN_UNITS, TRAINING_ICON, BTN_TRAIN templates in state_detector.
    
    Args:
        training_list: A list of tuples, e.g., [("cavalry", 3), ("infantry", 5)]
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
    
    # Default train button coordinate (adjust if needed)
    TRAIN_BTN_COORD = (792, 466) 
    
    # 1. Back to IN_CITY once at the start
    if not back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)"):
        print(f"[{serial}] [FAILED] Could not reach IN_CITY lobby.")
        return False
        
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
            if not back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)"):
                 print(f"[{serial}] [FAILED] Not in IN_CITY lobby. Aborting current training.")
                 all_success = False
                 continue

        # 2. Tap training house
        hx, hy = HOUSE_TAPS[h_type]
        print(f"[{serial}] Tapping {h_type.upper()} House at ({hx}, {hy})...")
        adb_helper.tap(serial, hx, hy)
        time.sleep(3)
        
        # 3. Tap training icon relative to house (+90, +20)
        icon_x = hx + 90
        icon_y = hy + 20
        print(f"[{serial}] Tapping TRAINING_ICON at ({icon_x}, {icon_y})...")
        adb_helper.tap(serial, icon_x, icon_y)
        time.sleep(3)
        
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
    
    return all_success


def claim_alliance_resource(serial: str, detector: GameStateDetector) -> bool:
    """
    Claims Alliance Territory Resource.
    1. Go to Alliance Menu
    2. Tap Territory Icon
    3. Tap Claim Button
    """
    print(f"[{serial}] Starting Claim Alliance Resource...")
    
    # 1. Request in alliance menu
    if not go_to_alliance(serial, detector):
        print(f"[{serial}] [FAILED] Could not reach Alliance Menu to claim resource.")
        return False
        
    # 2. Tap territory icon
    print(f"[{serial}] Tapping Territory Icon...")
    adb_helper.tap(serial, 635, 350)
    time.sleep(3)
    
    # 3. Tap claim button (826, 175)
    print(f"[{serial}] Tapping Claim Button (826, 175)...")
    adb_helper.tap(serial, 826, 175)
    time.sleep(2)
    
    print(f"[{serial}] -> Claim Alliance Resource completed.")

    # back to lobby
    adb_helper.press_back(serial)
    time.sleep(2)
    adb_helper.press_back(serial)
    time.sleep(2)
    return True

def check_mail(serial: str, detector: GameStateDetector, mail_type: str = "all") -> bool:
    """
    Checks and claims mail in the game.
    mail_type can be 'events', 'system', 'alliance', or 'all' (default).
    """
    valid_types = ["events", "system", "alliance", "all"]
    mail_type = mail_type.lower()
    if mail_type not in valid_types:
        print(f"[{serial}] [ERROR] Invalid mail_type '{mail_type}'. Use {valid_types}.")
        return False
        
    print(f"[{serial}] Starting Check Mail ({mail_type})...")


    
    # 1. Back to lobby
    if not back_to_lobby(serial, detector):
        print(f"[{serial}] [FAILED] Could not reach lobby.")
        return False
        
    # 2. Tap mail icon
    print(f"[{serial}] Tapping Mail Icon (926, 447)...")
    adb_helper.tap(serial, 926, 447)
    time.sleep(3)
    
    # 3. Verify MAIL_MENU
    state = wait_for_state(serial, detector, ["MAIL_MENU"], timeout_sec=10, check_mode="special")
    if state != "MAIL_MENU":
        print(f"[{serial}] [FAILED] Did not reach MAIL_MENU.")
        return False
        
    print(f"[{serial}] -> MAIL_MENU reached successfully.")
    
    # 4. Locations for tabs
    tabs = {
        "alliance": (370, 25),
        "events": (500, 25),
        "system": (615, 25)
    }
    claim_button = (100, 512)
    
    tabs_to_check = []
    if mail_type == "all":
        tabs_to_check = ["alliance", "events", "system"]
    else:
        tabs_to_check = [mail_type]
        
    for tab in tabs_to_check:
        print(f"[{serial}] Checking '{tab.capitalize()}' mail...")
        tab_x, tab_y = tabs[tab]
        
        # Tap tab
        adb_helper.tap(serial, tab_x, tab_y)
        time.sleep(2)
        
        # Tap claim
        print(f"[{serial}] Tapping Claim ({claim_button[0]}, {claim_button[1]})...")
        adb_helper.tap(serial, claim_button[0], claim_button[1])
        time.sleep(2)
        
    # 5. Back out
    print(f"[{serial}] Closing Mail Menu...")
    adb_helper.press_back(serial)
    time.sleep(2)
    
    print(f"[{serial}] -> Check Mail completed.")
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

def swap_account(serial: str, account_detector: AccountDetector, detector: GameStateDetector, target_account: str = None, max_scrolls: int = 5) -> bool:
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

    # 1. Ensure we're in LOBBY first
    current = detector.check_state(serial)
    if current not in LOBBY_STATES:
        print(f"[{serial}] Not in Lobby ({current}). Navigating back...")
        if not back_to_lobby(serial, detector):
            print(f"[{serial}] swap_account failed: Could not reach lobby.")
            return False

    # 2. Navigate to Profile
    print(f"[{serial}] Step 1/6: Opening Profile...")
    if not go_to_profile(serial, detector):
        print(f"[{serial}] swap_account failed: Could not open Profile.")
        return False
    time.sleep(1) 

    # 4. Tap Settings button (683, 340) -> wait via account detector
    print(f"[{serial}] Step 2/6: Opening Settings (683, 340)...")
    adb_helper.tap(serial, 683, 340)
    state = wait_for_state(serial, detector, ["SETTINGS"], timeout_sec=10, check_mode="special")
    if not state:
        print(f"[{serial}] swap_account failed: Could not reach Settings screen.")
        return False
    time.sleep(1)

    # 5. Tap "Switch Account" (478, 354) -> wait via account detector
    print(f"[{serial}] Step 3/6: Tapping Switch Account (478, 354)...")
    adb_helper.tap(serial, 478, 354)
    state = wait_for_state(serial, detector, ["CHARACTER_MANAGEMENT"], timeout_sec=10, check_mode="special")
    if not state:
        print(f"[{serial}] swap_account failed: Could not reach Character Management screen.")
        return False
    time.sleep(1)

    if target_account:
        # 6. Find target account in the list using check_account_state (OCR text) + scroll
        print(f"[{serial}] Step 4/6: Searching for account TEXT '{target_account}' in list...")
        account_found = None

        for scroll_attempt in range(max_scrolls + 1):
            # Try to find the account text on current viewport via OCR
            result = account_detector.check_account_name(serial, target=target_account, check_type="text")

            if result:
                name, center_x, center_y = result
                print(f"[{serial}] -> Account '{target_account}' found at ({center_x}, {center_y})!")
                account_found = (center_x, center_y)
                break

            if scroll_attempt < max_scrolls:
                print(f"[{serial}] -> Account not visible. Scrolling down... ({scroll_attempt + 1}/{max_scrolls})")
                adb_helper.swipe(serial, 500, 400, 500, 200, 500)
                time.sleep(2)
            else:
                print(f"[{serial}] -> Account not found after {max_scrolls} scrolls.")

        if not account_found:
            print(f"[{serial}] swap_account failed: Account '{target_account}' not found in Character Management list.")
            adb_helper.press_back(serial)
            time.sleep(2)
            return False

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
            return True
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
        return False

    print(f"[{serial}] === SWAP ACCOUNT SUCCESS -> {lobby_state} ===")
    return True

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
    if not back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)"):
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

def claim_daily_vip_gift(serial: str, detector: GameStateDetector) -> bool:
    """
    Claim daily VIP Gift:
    - Navigates to IN_CITY and taps SHOP construction
    - Taps VIP ICON, Claim, Hornor Point (+), Claim point
    - Back x2 to return
    """
    print(f"[{serial}] Starting Claim Daily VIP Gift workflow...")
    workflow_start = time.time()
    
    t0 = time.time()
    # 1. Access SHOP
    if not go_to_construction(serial, detector, "SHOP"):
        print(f"[{serial}] [FAILED] Could not access SHOP construction.")
        return False
        
    time.sleep(3)
    print(f"[{serial}] [TIMING] Accessing SHOP construction took {time.time() - t0:.2f}s")
    
    # [NOTE] Coordinates below are placeholders and need to be measured via ADB / tool_inspector!
    # 2. Tap VIP ICON
    # print(f"[{serial}] [TODO] Tapping VIP ICON (Placeholder coords: 100, 100)...")
    # adb_helper.tap(serial, 718, 425)
    # time.sleep(2)
    
    t0 = time.time()
    # 3. Tap Claim
    print(f"[{serial}] [TODO] Tapping Claim (Placeholder coords: 200, 200)...")
    adb_helper.tap(serial, 718, 425)
    time.sleep(2)
    print(f"[{serial}] [TIMING] Tapping Claim took {time.time() - t0:.2f}s")
    
    t0 = time.time()
    # 4. Tap Hornor Point (PLUS icon)
    print(f"[{serial}] [TODO] Tapping Hornor Point (PLUS icon) (Placeholder coords: 300, 300)...")
    adb_helper.tap(serial, 278, 357)
    time.sleep(2)
    print(f"[{serial}] [TIMING] Tapping Hornor Point took {time.time() - t0:.2f}s")
    
    t0 = time.time()
    # 5. Tap claim point
    print(f"[{serial}] [TODO] Tapping Claim point (Placeholder coords: 400, 400)...")
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
    return True


def alliance_help(serial: str, detector: GameStateDetector, max_helps: int = 1000, interval_min: float = 600, interval_max: float = 1200) -> int:
    """
    Alliance Help workflow.
    
    1. go_to_alliance() → ALLIANCE_MENU
    2. Detect & tap Alliance Help button
    3. Tap Help All (if visible)
    4. If Help button not found → BACK (to alliance) → BACK (to lobby) → done
    5. Loop with random interval between interval_min and interval_max seconds
    
    Args:
        max_helps: Maximum number of help attempts (default 1000)
        interval_min: Minimum seconds between help attempts (default 600 = 10 min)
        interval_max: Maximum seconds between help attempts (default 1200 = 20 min)
    
    Returns: Total number of successful help taps.
    """
    print(f"[{serial}] === ALLIANCE HELP (max={max_helps}, interval={interval_min}-{interval_max}s) ===")
    
    help_count = 0
    
    for attempt in range(1, max_helps + 1):
        print(f"\n[{serial}] --- Alliance Help Attempt #{attempt}/{max_helps} ---")
        
        # 1. Navigate to Alliance Menu
        if not go_to_alliance(serial, detector):
            print(f"[{serial}] [FAILED] Could not reach Alliance Menu. Stopping.")
            break
        
        # 2. Detect Alliance Help button
        help_match = detector.check_alliance(serial, target="ALLIANCE_HELP", threshold=0.8)
        
        if not help_match:
            print(f"[{serial}] No Alliance Help button detected. Nothing to help with.")
            # As per spec: Back 1 time (to alliance screen) then Back again (to lobby)
            adb_helper.press_back(serial)
            time.sleep(2)
            break
        
        # 3. Tap Alliance Help button
        _, hx, hy = help_match
        print(f"[{serial}] Found Alliance Help button at ({hx}, {hy}). Tapping...")
        adb_helper.tap(serial, hx, hy)
        time.sleep(3)
        
        help_count += 1
        print(f"[{serial}] Help #{help_count} completed!")
        
        # 4. Back to lobby after each help
        adb_helper.press_back(serial)
        time.sleep(1)
        adb_helper.press_back(serial)
        time.sleep(1)
        
        # 5. Wait random interval before next attempt
        if attempt < max_helps:
            wait_time = random.uniform(interval_min, interval_max)
            print(f"[{serial}] Sleeping {wait_time:.0f}s before next help attempt...")
            time.sleep(wait_time)
    
    print(f"[{serial}] === ALLIANCE HELP FINISHED ({help_count} helps completed) ===")
    return help_count


def claim_daily_chests(serial: str, detector: GameStateDetector,
                       draw_x10_silver: bool = False,
                       draw_x10_gold: bool = False,
                       draw_x10_artifact: bool = False) -> bool:
    """
    Claim daily free Hero & Artifact chest draws at the Tavern.
    
    Flow:
      1. go_to_construction → TAVERN (lands on Hero Recruitment screen)
      2. Tap Silver Chest free draw → dismiss result
      3. Tap Gold Chest free draw → dismiss result
      4. (Optional) x10 Silver draw if draw_x10_silver & button visible
      5. (Optional) x10 Gold draw if draw_x10_gold & button visible
      6. Swap to Artifact screen
      7. Tap Artifact free draw → dismiss result
      8. (Optional) x10 Artifact draw if draw_x10_artifact & button visible
      9. BACK → lobby
    
    NOTE: x10 buttons only appear when player has >= 10 keys.
    Uses ROI to distinguish Silver vs Gold x10 on the same screen.
    """
    print(f"[{serial}] === TAVERN CHEST DRAW ===")

    # ============================================================
    # TODO: USER — Replace all (0, 0) with real tap coordinates
    # ============================================================
    SILVER_FREE_DRAW_TAP = (0, 0)    # TODO: Silver Chest free draw button
    GOLD_FREE_DRAW_TAP = (0, 0)      # TODO: Gold Chest free draw button
    SILVER_X10_TAP = (0, 0)          # TODO: Silver Chest x10 draw button
    GOLD_X10_TAP = (0, 0)            # TODO: Gold Chest x10 draw button
    SWAP_TO_ARTIFACT_TAP = (0, 0)    # TODO: Tab to swap Hero Recruitment → Artifact
    ARTIFACT_FREE_DRAW_TAP = (0, 0)  # TODO: Artifact free draw button
    ARTIFACT_X10_TAP = (0, 0)        # TODO: Artifact x10 draw button
    DISMISS_POPUP_TAP = (480, 300)   # TODO: Tap to dismiss draw result popup

    # ROI for x10 button detection (to avoid mismatch between Silver & Gold)
    # Format: (x_ratio, y_ratio, w_ratio, h_ratio) — proportional to screen size
    SILVER_X10_ROI = (0.0, 0.0, 0.5, 1.0)   # TODO: left half of screen (sample)
    GOLD_X10_ROI = (0.5, 0.0, 0.5, 1.0)     # TODO: right half of screen (sample)

    # 1. Navigate to Tavern
    if not go_to_construction(serial, detector, "TAVERN"):
        print(f"[{serial}] [FAILED] Could not navigate to Tavern.")
        return False

    state = wait_for_state(serial, detector, ["TAVERN"], timeout_sec=10, check_mode="construction")
    if state != "TAVERN":
        print(f"[{serial}] [FAILED] Did not reach TAVERN screen.")
        return False

    print(f"[{serial}] Tavern opened → Hero Recruitment screen.")
    time.sleep(2)

    # ---- HERO RECRUITMENT SCREEN ----

    # 2. Silver Chest free draw
    print(f"[{serial}] Tapping Silver Chest Free Draw {SILVER_FREE_DRAW_TAP}...")
    adb_helper.tap(serial, SILVER_FREE_DRAW_TAP[0], SILVER_FREE_DRAW_TAP[1])
    time.sleep(3)
    # Dismiss result popup
    adb_helper.tap(serial, DISMISS_POPUP_TAP[0], DISMISS_POPUP_TAP[1])
    time.sleep(2)

    # 3. Gold Chest free draw
    print(f"[{serial}] Tapping Gold Chest Free Draw {GOLD_FREE_DRAW_TAP}...")
    adb_helper.tap(serial, GOLD_FREE_DRAW_TAP[0], GOLD_FREE_DRAW_TAP[1])
    time.sleep(3)
    # Dismiss result popup
    adb_helper.tap(serial, DISMISS_POPUP_TAP[0], DISMISS_POPUP_TAP[1])
    time.sleep(2)

    # 4. (Optional) x10 Silver draw
    if draw_x10_silver:
        print(f"[{serial}] Checking for Silver x10 draw button...")
        # Use ROI-limited frame to detect x10 in Silver area only
        frame = detector.get_frame(serial)
        if frame is not None:
            h, w = frame.shape[:2]
            roi = SILVER_X10_ROI
            cropped = frame[int(roi[1]*h):int((roi[1]+roi[3])*h), int(roi[0]*w):int((roi[0]+roi[2])*w)]
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
    # Dismiss result popup
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
    return True


