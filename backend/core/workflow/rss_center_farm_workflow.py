import os
import sys
import time

# Part3_Control_EMU directory
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)

# UI_MANAGER directory for config
ui_manager_dir = os.path.abspath(os.path.join(root_dir, "..", "UI_MANAGER"))
sys.path.append(ui_manager_dir)

from backend.config import config
config.load()

# Import our new Production modules
from workflow.state_detector import GameStateDetector
from workflow import core_actions

# Configuration
SERIAL = "emulator-5568"
APP_PACKAGE = "com.farlightgames.samo.gp.vn"

def main():
    print(f"\n[WORKFLOW] Starting RSS Center Farming on {SERIAL}...\n")
    
    # 1. Initialize the Detector 
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)
    
    # 2. Boot game & Go to Lobby
    print("[WORKFLOW] Booting game and navigating to Lobby...")
    if not core_actions.startup_to_lobby(SERIAL, detector, APP_PACKAGE):
        print("\n[WORKFLOW FAILED] Could not reach Lobby.")
        return
    
    # 3. Run farming action
    print(f"\n[WORKFLOW] Executing go_to_rss_center_farm()...")
    result = core_actions.go_to_rss_center_farm(SERIAL, detector)
    
    print(f"\n{'='*50}")
    print(f"[WORKFLOW] Result: {result}")
    if isinstance(result, dict) and "dynamic_cooldown_sec" in result:
        cd = result["dynamic_cooldown_sec"]
        hours = cd // 3600
        mins = (cd % 3600) // 60
        print(f"[WORKFLOW] Dynamic Cooldown: {cd}s ({hours}h {mins}m)")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
