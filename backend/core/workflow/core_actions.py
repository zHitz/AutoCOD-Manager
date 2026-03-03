"""
Core Actions — High-level game automation actions.
Migrated from TEST/workflow/core_actions.py with import paths adapted for app context.
"""
import time

from backend.config import config
from backend.core.workflow import adb_helper
from backend.core.workflow import clipper_helper
from backend.core.workflow.state_detector import GameStateDetector
from backend.core.workflow.construction_data import CONSTRUCTION_TAPS


def ensure_app_running(serial: str, package_name: str, adb_path: str = None) -> bool:
    """Checks if the app is active, and boots it if it's not. Returns True if it was already running."""
    if adb_path is None:
        adb_path = config.adb_path
    if not clipper_helper.is_app_foreground(adb_path, serial, package_name):
        clipper_helper.open_app(adb_path, serial, package_name)
        return False
    return True

def startup_to_lobby(serial: str, detector: GameStateDetector, package_name: str, adb_path: str = None, load_timeout: int = 120) -> bool:
    """
    All-in-one startup: Boot game nếu chưa chạy -> chờ load vào Lobby.
    Nếu game đang chạy rồi -> dùng back_to_lobby() để mò về Lobby từ bất kỳ state nào.
    Returns True nếu đã chắc chắn đang ở Lobby, False nếu thất bại.
    """
    if adb_path is None:
        adb_path = config.adb_path

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

def wait_for_state(serial: str, detector: GameStateDetector, target_states: list, timeout_sec: int = 60) -> str:
    """Blocks and loops until the emulator reaches one of the target_states."""
    start_time = time.time()
    print(f"[{serial}] Waiting for one of states: {target_states} (Timeout: {timeout_sec}s)")
    
    while True:
        if time.time() - start_time > timeout_sec:
            print(f"[{serial}] [TIMEOUT] Failed to reach target state within {timeout_sec}s.")
            return None
            
        current_state = detector.check_state(serial)
        print(f"[{serial}] Current detected state: {current_state}")
        
        if current_state in target_states:
            print(f"[{serial}] -> Target Reached '{current_state}'")
            return current_state
            
        if current_state == "LOADING SCREEN":
            print(f"[{serial}] -> Game is loading. Waiting 3 seconds...")
            time.sleep(3)
        else:
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
    Navigates to the Profile Details menu via Profile Menu.
    """
    print(f"[{serial}] Navigating to Profile Details...")
    go_to_profile(serial, detector)
    time.sleep(3)
    adb_helper.tap(serial, 550, 200)

    state = wait_for_state(serial, detector, ["IN-GAME LOBBY (PROFILE MENU DETAIL)"], timeout_sec=10)
    return state is not None

def extract_player_id(serial: str, detector: GameStateDetector, adb_path: str = None) -> str:
    """
    Assumes we are on the Profile Menu.
    Taps the copy button, intercepts the ADB Clipper intent, and returns the ID.
    """
    if adb_path is None:
        adb_path = config.adb_path
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
      - LOADING SCREEN (NETWORK ISSUE): Clicks Confirm for restart.
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
            print(f"[{serial}] -> Loading detected. Waiting 20s before next check...")
            unknown_start_time = None  # Reset unknown timer
            known_state_back_count = 0
            last_known_state = None
            time.sleep(20)
            continue

        # === CASE 2: LOADING SCREEN (NETWORK ISSUE) — Click Confirm for restart ===
        if current_state == "LOADING SCREEN (NETWORK ISSUE)":
            print(f"[{serial}] -> Network issue detected. Click Confirm for restart")
            adb_helper.tap(serial, 500, 325)
            time.sleep(2)
            continue

        # === CASE 3: UNKNOWN / TRANSITION — Grace period 10s ===
        if current_state == "UNKNOWN / TRANSITION":
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

    LOBBY_STATES = ["IN-GAME LOBBY (IN_CITY)", "IN-GAME LOBBY (OUT_CITY)"]
    ITEMS_STATES = ["IN-GAME ITEMS (ARTIFACTS)", "IN-GAME ITEMS (RESOURCES)"]
    
    items_reached = False
    state = None
    for retry in range(1, 4):
        adb_helper.tap(serial, 780, 500)
        state = wait_for_state(serial, detector, ITEMS_STATES, timeout_sec=5)
        if state:
            items_reached = True
            break
        
        # Check what state we're in
        current = detector.check_state(serial)
        if current in LOBBY_STATES:
            print(f"[{serial}] -> Tap (780,500) missed. Retry {retry}/3 — re-expanding menu...")
            if not ensure_lobby_menu_open(serial, detector):
                return False
            continue
        
        # Unknown state — likely some other IN-GAME ITEMS tab without a template
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

def go_to_hall(serial: str, detector: GameStateDetector) -> bool:
    """Shortcut: navigates to City Hall."""
    return go_to_construction(serial, detector, "HALL")

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

def go_to_capture_pet(serial: str, detector: GameStateDetector) -> bool:
    """
    Navigates to the Capture Pet screen.
    From lobby: taps the pet/bestiary icon, then enters the capture flow.
    Returns True on success.
    """
    print(f"[{serial}] Navigating to Capture Pet...")
    back_to_lobby(serial, detector)
    # Tap the beast/pet icon in the lobby (bottom-right area)
    adb_helper.tap(serial, 50, 680)
    time.sleep(2)
    adb_helper.tap(serial, 50, 680)
    time.sleep(2)
    print(f"[{serial}] -> Pet capture screen initiated.")
    return True

