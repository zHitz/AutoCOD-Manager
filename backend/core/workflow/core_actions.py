"""
Core Actions — High-level game automation actions.
Copied from TEST/WORKFLOW/core_actions.py with import paths adapted for app context.
"""
import time

from backend.config import config
from backend.core.workflow import adb_helper
from backend.core.workflow import clipper_helper
from backend.core.workflow.state_detector import GameStateDetector


def ensure_app_running(serial: str, package_name: str, adb_path: str = None) -> bool:
    """Checks if the app is active, and boots it if it's not. Returns True if it was already running."""
    if adb_path is None:
        adb_path = config.adb_path
    if not clipper_helper.is_app_foreground(adb_path, serial, package_name):
        clipper_helper.open_app(adb_path, serial, package_name)
        return False
    return True

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

def back_to_lobby(serial: str, detector: GameStateDetector) -> bool:
    """
    Assumes we are on any Menu.
    Taps the back button, intercepts the ADB Clipper intent, and returns the ID.
    """
    print(f"[{serial}] Back to Lobby...")
    adb_helper.press_back(serial)
    
    state = wait_for_state(serial, detector, ["IN-GAME LOBBY (IN_CITY)", "IN-GAME LOBBY (OUT_CITY)"], timeout_sec=10)
    return state is not None
