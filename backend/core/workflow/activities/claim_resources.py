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
from workflow.state_detector import GameStateDetector
from workflow import core_actions

# Configuration
SERIAL = "emulator-5556"  # Can be overridden by args
APP_PACKAGE = "com.farlightgames.samo.gp.vn"

def main():
    print(f"=== TEST SCRIPT: CLAIM CITY RESOURCES ===")
    
    serial = sys.argv[1] if len(sys.argv) > 1 else SERIAL
    print(f"Serial: {serial}")
    
    # Initialize detector
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)
    
    # Enable quick checks to see loaded templates
    print("\n[INIT] Loaded Templates Summary:")
    print(f"  - Construction Templates: {list(detector.construction_templates.keys())}")
    print(f"  - Activity Templates: {list(detector.activity_templates.keys())}")
    
    # Execute the workflow
    print("\n[START] Executing core_actions.claim_city_resources()...")
    
    # Ensure app is running
    print(f"[{serial}] Ensuring game is running...")
    core_actions.ensure_app_running(serial, APP_PACKAGE)
    time.sleep(5) # Give it a moment if it just started
    
    claimed = core_actions.claim_city_resources(serial, detector)
    
    print(f"\n✅ WORKFLOW COMPLETED! Total resources claimed: {claimed}")

if __name__ == "__main__":
    main()
