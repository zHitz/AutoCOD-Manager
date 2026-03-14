import os
import sys

# Root directory (Part3_Control_EMU)
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)
sys.path.append(os.path.abspath(os.path.join(root_dir, "..", "UI_MANAGER")))

from backend.config import config
config.load()
import adb_helper
from workflow.state_detector import GameStateDetector
from workflow import core_actions

# Configuration
APP_PACKAGE = "com.farlightgames.samo.gp.vn"


def run_tavern_chest(serial: str, draw_x10_silver: bool = False,
                     draw_x10_gold: bool = False,
                     draw_x10_artifact: bool = False):
    """Run the Tavern Chest Draw workflow on a single emulator."""
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    # Boot and go to lobby
    if not core_actions.startup_to_lobby(serial, detector, APP_PACKAGE):
        print(f"[{serial}] Failed to start or reach lobby.")
        return False

    print(f"\n[{serial}] Starting Tavern Chest Draw workflow...")
    print(f"  x10 Silver: {draw_x10_silver} | x10 Gold: {draw_x10_gold} | x10 Artifact: {draw_x10_artifact}")

    success = core_actions.claim_daily_chests(
        serial, detector,
        draw_x10_silver=draw_x10_silver,
        draw_x10_gold=draw_x10_gold,
        draw_x10_artifact=draw_x10_artifact,
    )

    if success:
        print(f"\n[{serial}] Tavern Chest Draw workflow completed successfully!")
    else:
        print(f"\n[{serial}] Tavern Chest Draw workflow failed.")

    return success


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tavern_chest_workflow.py <emulator_serial> [x10_silver] [x10_gold] [x10_artifact]")
        print("Example: python tavern_chest_workflow.py emulator-5554 true false true")
        sys.exit(1)

    serial = sys.argv[1]
    x10_silver = sys.argv[2].lower() == "true" if len(sys.argv) > 2 else False
    x10_gold = sys.argv[3].lower() == "true" if len(sys.argv) > 3 else False
    x10_artifact = sys.argv[4].lower() == "true" if len(sys.argv) > 4 else False

    run_tavern_chest(serial, x10_silver, x10_gold, x10_artifact)
