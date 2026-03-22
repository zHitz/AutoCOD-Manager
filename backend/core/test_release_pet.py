import os
import sys
import argparse

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


def test_release_pet_only(emulator_index=1):
    """Test only the release_pet function (assumes you're already at PET_SANCTUARY)."""
    serial = f"emulator-{5554 + emulator_index * 2}"
    print(f"\n[TEST] === Release Pet Test on {serial} ===")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")
    print(f"[TEST] Loading Detector from {templates_dir}...")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    print(f"\n[TEST] Running release_pet()...")
    print("=" * 60)
    result = core_actions.release_pet(serial, detector)
    print("=" * 60)

    print(f"\n[TEST] === RESULT: {result} ===")
    _check_saved_screenshots()


def test_full_capture_flow(emulator_index=1):
    """Test the full go_to_capture_pet flow (capture → sanctuary → release → capture)."""
    serial = f"emulator-{5554 + emulator_index * 2}"
    print(f"\n[TEST] === Full Capture Pet Flow on {serial} ===")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")
    print(f"[TEST] Loading Detector from {templates_dir}...")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    print(f"\n[TEST] Running go_to_capture_pet()...")
    print("=" * 60)
    result = core_actions.go_to_capture_pet(serial, detector)
    print("=" * 60)

    print(f"\n[TEST] === RESULT: {result} ===")
    _check_saved_screenshots()


def test_sanctuary_then_release(emulator_index=1):
    """Test navigate to Pet Sanctuary then release (most common debug flow)."""
    serial = f"emulator-{5554 + emulator_index * 2}"
    print(f"\n[TEST] === Sanctuary → Release Test on {serial} ===")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")
    print(f"[TEST] Loading Detector from {templates_dir}...")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    # Step 1: Navigate to Pet Sanctuary
    print(f"\n[TEST] Step 1: Navigating to Pet Sanctuary...")
    print("-" * 50)
    sanctuary_result = core_actions.go_to_pet_sanctuary(serial, detector)
    if not sanctuary_result.get("ok"):
        print(f"[TEST] ❌ Could not reach Pet Sanctuary. Aborting.")
        return

    # Step 2: Release pets
    print(f"\n[TEST] Step 2: Running release_pet()...")
    print("-" * 50)
    result = core_actions.release_pet(serial, detector)
    print("=" * 60)

    print(f"\n[TEST] === RESULT: {result} ===")
    _check_saved_screenshots()


def _check_saved_screenshots():
    """Show summary of saved pet release screenshots."""
    save_dir = os.path.join("data", "pet_releases")
    if not os.path.exists(save_dir):
        print(f"\n[TEST] ⚠️ No screenshots saved (directory not found: {save_dir})")
        return

    files = sorted(os.listdir(save_dir))
    available = [f for f in files if f.startswith("available_")]
    get = [f for f in files if f.startswith("get_")]

    print(f"\n[TEST] === Screenshot Summary ===")
    print(f"  Directory: {os.path.abspath(save_dir)}")
    print(f"  Available (Phase 1): {len(available)} files")
    print(f"  Get (Phase 2):       {len(get)} files")

    if available:
        print(f"\n  Latest pairs:")
        for f in available[-3:]:
            release_id = f.replace("available_", "").replace(".png", "")
            paired = f"get_{release_id}.png"
            has_pair = "✅" if paired in get else "❌ MISSING"
            print(f"    {f}  ↔  {paired}  {has_pair}")


if __name__ == "__main__":
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(description="Test Release Pet workflow")
    parser.add_argument("emulator_index", type=int, nargs="?", default=1,
                        help="Index of emulator (default: 1)")
    parser.add_argument("--mode", choices=["release", "full", "sanctuary"],
                        default="sanctuary",
                        help="Test mode: release (only release), full (capture+release+capture), sanctuary (nav+release, default)")
    args = parser.parse_args()

    if args.mode == "release":
        test_release_pet_only(args.emulator_index)
    elif args.mode == "full":
        test_full_capture_flow(args.emulator_index)
    else:
        test_sanctuary_then_release(args.emulator_index)
