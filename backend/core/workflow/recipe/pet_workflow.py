import os
import sys

# Root directory (Part3_Control_EMU)
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
SERIAL = "emulator-5556"
APP_PACKAGE = core_actions.get_package_for_provider()


def main():
    print(f"\n[WORKFLOW] Starting Pet Test on {SERIAL}...\n")

    # 1. Initialize the Detector
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    # 2. Boot game & Go to Lobby
    print("[WORKFLOW] Booting game and navigating to Lobby...")
    if not core_actions.startup_to_lobby(SERIAL, detector, APP_PACKAGE):
        print("\n[WORKFLOW FAILED] Could not reach Lobby.")
        return

    # 3. Run test action
    print("\n[WORKFLOW] Test action.")
    core_actions.go_to_capture_pet(SERIAL, detector)


if __name__ == "__main__":
    main()
