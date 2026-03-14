import os
import sys
import threading

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

# Configuration
APP_PACKAGE = "com.farlightgames.samo.gp.vn"


def run_worker(serial: str, detector: GameStateDetector, max_helps: int, interval_min: float, interval_max: float):
    """Worker function to execute alliance help on a specific emulator serial."""
    print(f"\n[WORKFLOW] [{serial}] Booting game and navigating to Lobby...")
    if not core_actions.startup_to_lobby(serial, detector, APP_PACKAGE):
        print(f"\n[WORKFLOW FAILED] [{serial}] Could not reach Lobby.")
        return

    print(f"\n[WORKFLOW] [{serial}] Executing alliance_help()...")
    total = core_actions.alliance_help(serial, detector, max_helps=max_helps, interval_min=interval_min, interval_max=interval_max)
    print(f"\n[WORKFLOW] [{serial}] Finished. Total helps: {total}")


def main():
    print(f"\n[WORKFLOW] Starting Alliance Help Workflow...\n")

    # User Input: serials
    serials_input = input("Enter emulator serials separated by comma (e.g. emulator-5554,emulator-5556):\n> ")
    if not serials_input.strip():
        serials_input = "emulator-5554"
        print(f"[WARNING] No input provided, defaulting to {serials_input}")

    serials = [s.strip() for s in serials_input.split(",") if s.strip()]

    # User Input: max helps
    max_input = input("Enter maximum daily number of helps (default 1000):\n> ")
    try:
        max_helps = int(max_input) if max_input.strip() else 1000
    except ValueError:
        print("[WARNING] Invalid number. Defaulting to 1000.")
        max_helps = 1000

    # User Input: interval range
    interval_input = input("Enter help interval in minutes as min-max (default 10-20):\n> ")
    try:
        if interval_input.strip():
            parts = interval_input.strip().split("-")
            interval_min = float(parts[0]) * 60
            interval_max = float(parts[1]) * 60
        else:
            interval_min = 600
            interval_max = 1200
    except (ValueError, IndexError):
        print("[WARNING] Invalid interval format. Defaulting to 10-20 minutes.")
        interval_min = 600
        interval_max = 1200

    print(f"\n[CONFIG] Max Helps: {max_helps} | Interval: {interval_min/60:.0f}-{interval_max/60:.0f} min")

    # Initialize Detector
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    # Launch threads
    threads = []
    print(f"\n[WORKFLOW] Launching {len(serials)} worker threads...\n")

    for serial in serials:
        t = threading.Thread(
            target=run_worker,
            args=(serial, detector, max_helps, interval_min, interval_max),
            name=f"Thread-{serial}",
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    print("\n[WORKFLOW] All emulators have finished the Alliance Help Workflow!")


if __name__ == "__main__":
    main()
