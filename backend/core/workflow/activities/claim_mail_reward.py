import os
import sys
import time

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
from workflow.screen_capture import run_full_capture_modern
from workflow import clipper_helper
from workflow.state_detector import GameStateDetector
from workflow.construction_data import CONSTRUCTION_TAPS
from workflow import test_back_to_lobby
# Configuration
SERIAL = "emulator-5556"
APP_PACKAGE = "com.farlightgames.samo.gp.vn"

def main():
    print(f"\n[WORKFLOW] Starting Quick Test on {SERIAL}...\n")
    
    # 1. Initialize the Detector 
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)
    

    # 2. Quick test
    core_actions.check_mail(SERIAL, detector, mail_type="all")


if __name__ == "__main__":
    main()
