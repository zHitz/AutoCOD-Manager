import os
import sys
import time
import cv2

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
import adb_helper

# Output directory for debug screenshots
DEBUG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_alliance_tech")


def save_frame(serial, detector, label):
    """Save full annotated frame for visual debugging."""
    os.makedirs(DEBUG_DIR, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    frame = detector.get_frame(serial)
    if frame is None:
        print(f"[{serial}] [DEBUG] Could not capture frame for {label}")
        return

    path = os.path.join(DEBUG_DIR, f"{timestamp}_{label}.png")
    cv2.imwrite(path, frame)
    print(f"[{serial}] [DEBUG] Saved: {path}")


def _make_detector():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")
    return GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)


# ─────────────────────────────────────────────
# TEST 1: Full Alliance Technology Donate (end-to-end)
# ─────────────────────────────────────────────
def test_full_donate(serial):
    """Run the full donate_alliance_technology workflow."""
    print(f"\n[TEST] === Full Alliance Technology Donate on {serial} ===")

    detector = _make_detector()

    print(f"\n[TEST] Running donate_alliance_technology()...")
    print("-" * 50)

    try:
        result = core_actions.donate_alliance_technology(serial, detector)
        print("-" * 50)
        ok = result.get("ok", False)
        err = result.get("error", "")
        print(f"[TEST] {'OK' if ok else 'FAIL'} Result: {result}")
        if err:
            print(f"[TEST] Error: {err}")
    except KeyboardInterrupt:
        print(f"\n[TEST] Aborted by user.")
    except Exception as e:
        print(f"\n[TEST] Exception: {e}")
        import traceback
        traceback.print_exc()


# ─────────────────────────────────────────────
# TEST 2: Donate Button Template Detection
# ─────────────────────────────────────────────
def test_donate_detection(serial):
    """Test ALLIANCE_DONATE_BTN template detection on Technology screen.

    Steps:
    1. Navigate to Alliance Menu
    2. Tap Technology tab (530, 465)
    3. Detect ALLIANCE_DONATE_BTN with retry
    """
    print(f"\n[TEST] === Donate Button Detection on {serial} ===")

    detector = _make_detector()

    # Step 1: Navigate to Alliance
    print(f"\n[TEST] Step 1: Navigating to Alliance Menu...")
    result = core_actions.go_to_alliance(serial, detector)
    if not core_actions._is_ok(result):
        print(f"[TEST] FAIL - Could not reach Alliance Menu. Aborting.")
        return

    # Step 2: Tap Technology tab
    print(f"\n[TEST] Step 2: Tapping Technology tab (530, 465)...")
    adb_helper.tap(serial, 530, 465)
    time.sleep(3)

    # Step 3: Detect donate button
    print(f"\n[TEST] Step 3: Detecting ALLIANCE_DONATE_BTN...")
    save_frame(serial, detector, "tech_tab_before_detect")

    donate_match = None
    for attempt in range(5):
        detector._screen_cache = None
        donate_match = detector.check_alliance(serial, target="ALLIANCE_DONATE_BTN", threshold=0.8)
        if donate_match:
            print(f"[TEST] OK - ALLIANCE_DONATE_BTN found at ({donate_match[1]}, {donate_match[2]}) on attempt {attempt + 1}")
            save_frame(serial, detector, f"donate_found_{attempt}")
            break
        print(f"[TEST] Not found on attempt {attempt + 1}/5. Waiting 2s...")
        time.sleep(2)

    if not donate_match:
        print(f"[TEST] FAIL - ALLIANCE_DONATE_BTN not found after 5 attempts.")
        save_frame(serial, detector, "donate_not_found")

    # Cleanup
    adb_helper.press_back(serial)
    time.sleep(2)

    # Summary
    print(f"\n{'=' * 50}")
    print(f"[TEST] === SUMMARY ===")
    if donate_match:
        print(f"  ALLIANCE_DONATE_BTN: OK at ({donate_match[1]}, {donate_match[2]})")
    else:
        print(f"  ALLIANCE_DONATE_BTN: NOT FOUND")
    print(f"  Debug screenshots: {DEBUG_DIR}")
    print(f"{'=' * 50}")


# ─────────────────────────────────────────────
# TEST 3: Alliance Navigation Only
# ─────────────────────────────────────────────
def test_alliance_nav(serial):
    """Test go_to_alliance navigation only (no donate)."""
    print(f"\n[TEST] === Alliance Navigation on {serial} ===")

    detector = _make_detector()

    print(f"\n[TEST] Running go_to_alliance()...")
    result = core_actions.go_to_alliance(serial, detector)
    ok = core_actions._is_ok(result)
    print(f"[TEST] {'OK' if ok else 'FAIL'} Result: {result}")

    if ok:
        save_frame(serial, detector, "alliance_menu_reached")
        # Also tap Technology to verify tab switch
        print(f"[TEST] Tapping Technology tab (530, 465)...")
        adb_helper.tap(serial, 530, 465)
        time.sleep(3)
        save_frame(serial, detector, "technology_tab")

    # Cleanup
    adb_helper.press_back(serial)
    time.sleep(2)

    print(f"\n{'=' * 50}")
    print(f"[TEST] === SUMMARY ===")
    print(f"  Alliance Navigation: {'OK' if ok else 'FAIL'}")
    print(f"  Debug screenshots: {DEBUG_DIR}")
    print(f"{'=' * 50}")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(description="Test Alliance Technology Donate workflow")
    parser.add_argument("test", choices=["full", "detect", "nav", "all"],
                        help="Which test to run")
    parser.add_argument("--serial", default="emulator-5556", help="Emulator serial (default: emulator-5556)")
    args = parser.parse_args()

    if args.test == "full":
        test_full_donate(args.serial)
    elif args.test == "detect":
        test_donate_detection(args.serial)
    elif args.test == "nav":
        test_alliance_nav(args.serial)
    elif args.test == "all":
        test_alliance_nav(args.serial)
        test_donate_detection(args.serial)
        test_full_donate(args.serial)
