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
from workflow.state_detector import GameStateDetector
from workflow import core_actions

# Configuration
SERIAL = "emulator-5558"
APP_PACKAGE = "com.farlightgames.samo.gp.vn"

def parse_training_args(args):
    """Parses list of arguments like ['cavalry,3', 'infantry,default', 'archer'] into tuples"""
    training_list = []
    for arg in args:
        if ',' in arg:
            parts = arg.split(',')
            house = parts[0].strip()
            tier_str = parts[1].strip()
            if tier_str.lower() == "default":
                tier = "default"
            else:
                tier = int(tier_str)
            training_list.append((house, tier))
        else:
            # Fallback for old format or invalid -> default training
            training_list.append((arg, "default"))
    return training_list

def main():

    print(f"\n[WORKFLOW] Starting Quick Test on {SERIAL}...\n")
    training_list = [
    ("cavalry", 3), 
    ("infantry", 5),
    ("archer", 1),
    ("siege",3),
    ("mage",2)
    ]
    
    print(f"=== TEST SCRIPT: TRAIN TROOPS ===")
    print(f"Serial: {SERIAL}")
    print(f"Training List: {training_list}")
    
    # Initialize detector
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)
    
    # Enable quick checks to see loaded templates
    print("\n[INIT] Loaded Templates Summary:")
    print(f"  - Construction Templates: {list(detector.construction_templates.keys())}")
    print(f"  - Activity Templates: {list(detector.activity_templates.keys())}")
    
    # Execute the workflow
    print("\n[START] Executing core_actions.train_troops()...")
    success = core_actions.train_troops(SERIAL, detector, training_list=training_list)
    
    if success:
        print("\n✅ WORKFLOW COMPLETED SUCCESSFULLY!")
    else:
        print("\n❌ WORKFLOW FAILED! (Some operations may have been skipped due to errors)")

if __name__ == "__main__":
    main()
