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


def test_season_policies(emulator_index=4, account_id="default", last_col=None):
    serial = f"emulator-{5554 + emulator_index * 2}"
    print(f"\n[TEST] Starting Season Policies test on {serial} (account={account_id})...")

    # Init Detector
    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")

    print(f"[TEST] Loading Detector from {templates_dir}...")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    # Set initial progress if specified
    if last_col is not None:
        from backend.core.workflow.policy.data import save_progress
        save_progress(last_col, account_id)
        print(f"[TEST] Set initial progress: last_col={last_col} (will start from col {last_col + 1})")

    # Run Season Policies
    print(f"\n[TEST] Running process_season_policies()...")
    print("=" * 60)

    result = core_actions.process_season_policies(serial, detector, account_id=account_id)

    print("=" * 60)
    if result:
        print(f"[TEST] ✅ Season Policies completed successfully")
    else:
        print(f"[TEST] ❌ Season Policies failed")

    # Show progress after run
    from backend.core.workflow.policy.data import load_progress
    progress = load_progress(account_id)
    print(f"[TEST] Progress (account={account_id}): {progress}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test Season Policies workflow")
    parser.add_argument("emulator_index", type=int, nargs="?", default=4,
                        help="Index of emulator (default: 4)")
    parser.add_argument("--account-id", type=str, default="default",
                        help="Account ID for per-account progress (default: 'default')")
    parser.add_argument("--last-col", type=int, default=None,
                        help="Set last completed column before running (e.g. 3 = start from col 4)")
    args = parser.parse_args()

    # Handle Windows encoding
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    test_season_policies(args.emulator_index, args.account_id, args.last_col)
