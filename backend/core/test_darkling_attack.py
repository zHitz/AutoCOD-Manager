import os
import sys

# Path setup
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(root_dir)

ui_manager_dir = os.path.abspath(os.path.join(root_dir, "..", "UI_MANAGER"))
if ui_manager_dir not in sys.path:
    sys.path.append(ui_manager_dir)

from backend.config import config
config.load()

from backend.core.workflow.state_detector import GameStateDetector
from backend.core.workflow import core_actions


def test_release_pet(serial="emulator-5556"):
    print(f"\n[TEST] Starting release_pet test on {serial}...")

    # Init Detector
    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")

    print(f"[TEST] Loading Detector from {templates_dir}...")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    # Step 1: Navigate to Pet Sanctuary
    print(f"\n[TEST] Step 1: Navigating to Pet Sanctuary...")
    print("-" * 50)
    attack_darkling_legions_v1_basic_OK = core_actions.attack_darkling_legions_v1_basic(serial, detector)
    if not attack_darkling_legions_v1_basic_OK:
        print(f"[TEST] ❌ Could not attack darkling legions v1 basic. Aborting.")
        return



if __name__ == "__main__":
    # Handle Windows encoding
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    test_release_pet("emulator-5556")
