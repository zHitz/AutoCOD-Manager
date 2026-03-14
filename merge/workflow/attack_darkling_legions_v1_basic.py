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

from workflow.state_detector import GameStateDetector
from workflow import core_actions


SERIAL = "emulator-5556"
APP_PACKAGE = "com.farlightgames.samo.gp.vn"
LEGION_SLOT = 1


def main():
    print(f"\n[WORKFLOW] Starting Attack Darkling Legions V1 (BASIC) on {SERIAL}...\n")

    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    print("[WORKFLOW] Booting game and navigating to Lobby...")
    if not core_actions.startup_to_lobby(SERIAL, detector, APP_PACKAGE):
        print("\n[WORKFLOW FAILED] Could not reach Lobby.")
        return

    print("\n[WORKFLOW] Running Darkling Legions basic attack...")
    success = core_actions.attack_darkling_legions_v1_basic(SERIAL, detector, legion_slot=LEGION_SLOT)

    if success:
        print("\n[WORKFLOW SUCCESS] Attack Darkling Legions V1 (BASIC) completed.")
    else:
        print("\n[WORKFLOW FAILED] Attack Darkling Legions V1 (BASIC) failed.")


if __name__ == "__main__":
    main()
