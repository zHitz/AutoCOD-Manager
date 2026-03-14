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

def run_troop_healing(serial: str, healing_method: str = "elixir", troop_priorities: str = ""):
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)
    
    # Parse priorities
    priorities = [p.strip() for p in troop_priorities.split(",") if p.strip()] if troop_priorities else None

    # Boot and go to lobby
    if not core_actions.startup_to_lobby(serial, detector, "com.farlightgames.samo.gp.vn"):
        print(f"[{serial}] Failed to start or reach lobby.")
        return False
        
    print(f"\n[{serial}] Starting Troop Healing workflow with Method: {healing_method.upper()}, Priorities: {priorities}")
    
    success = core_actions.heal_troops(serial, detector, healing_method=healing_method, troop_priorities=priorities)
    if success:
        print(f"\n[{serial}] Successfully completed Troop Healing workflow.")
    else:
        print(f"\n[{serial}] Failed to complete Troop Healing workflow.")
        
    return success

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python troop_healing_workflow.py <emulator_serial> [healing_method] [priorities_comma_separated]")
        print("Example: python troop_healing_workflow.py emulator-5554 elixir infantry,cavalry")
        sys.exit(1)
        
    serial = sys.argv[1]
    method = sys.argv[2] if len(sys.argv) > 2 else "elixir"
    priorities = sys.argv[3] if len(sys.argv) > 3 else ""
    
    run_troop_healing(serial, method, priorities)
