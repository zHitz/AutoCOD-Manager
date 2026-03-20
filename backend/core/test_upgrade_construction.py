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


def test_upgrade_construction(emulator_index=4, max_depth=5, max_power=0, max_hall_level=0):
    serial = f"emulator-{5554 + emulator_index * 2}"
    print(f"\n[TEST] === Upgrade Construction Test on {serial} ===")
    print(f"[TEST] max_depth={max_depth}, max_power={max_power}, max_hall_level={max_hall_level}")

    # Init Detector
    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")

    print(f"[TEST] Loading Detector from {templates_dir}...")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    # Run upgrade_construction
    print(f"\n[TEST] Running upgrade_construction()...")
    print("=" * 60)

    result = core_actions.upgrade_construction(
        serial, detector,
        max_depth=max_depth,
        max_power=max_power,
        max_hall_level=max_hall_level,
    )

    print("=" * 60)
    print(f"\n[TEST] === RESULT ===")
    print(f"  Upgraded:      {result.get('upgraded', 0)}")
    print(f"  Paths found:   {result.get('paths_found', 0)}")
    print(f"  Depth reached: {result.get('depth_reached', 0)}")

    if result.get("upgraded", 0) > 0:
        print(f"[TEST] ✅ Upgrade construction completed successfully")
    else:
        print(f"[TEST] ⚠️ No constructions were upgraded")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test Upgrade Construction workflow")
    parser.add_argument("emulator_index", type=int, nargs="?", default=4,
                        help="Index of emulator (default: 4)")
    parser.add_argument("--max-depth", type=int, default=5,
                        help="Max GO chain depth (default: 5)")
    parser.add_argument("--max-power", type=int, default=0,
                        help="Skip if power exceeds this (0=disabled)")
    parser.add_argument("--max-hall-level", type=int, default=0,
                        help="Skip if hall level exceeds this (0=disabled)")
    args = parser.parse_args()

    # Handle Windows encoding
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    test_upgrade_construction(args.emulator_index, args.max_depth, args.max_power, args.max_hall_level)
