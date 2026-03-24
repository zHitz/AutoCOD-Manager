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
DEBUG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_scout_sentry")


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
# TEST 1: Full Scout Sentry Post Claim (end-to-end)
# ─────────────────────────────────────────────
def test_full_claim(serial):
    """Run the full claim_scout_sentry_post workflow."""
    print(f"\n[TEST] === Full Scout Sentry Post Claim on {serial} ===")

    detector = _make_detector()

    print(f"\n[TEST] Running claim_scout_sentry_post()...")
    print("-" * 50)

    try:
        result = core_actions.claim_scout_sentry_post(serial, detector)
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
# TEST 2: V2 Construction Navigation
# ─────────────────────────────────────────────
def test_navigation(serial):
    """Test _go_to_construction_v2 navigation to Scout Sentry Post.

    Steps:
    1. Navigate to IN_CITY
    2. Use _go_to_construction_v2("SCOUT_SENTRY_POST", feature="scout")
    3. Verify the screen is at Scout Sentry Post
    """
    print(f"\n[TEST] === Scout Sentry Post Navigation on {serial} ===")

    detector = _make_detector()

    # Step 1: Navigate to IN_CITY
    print(f"\n[TEST] Step 1: Navigating to IN_CITY...")
    lobby_result = core_actions.back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not core_actions._is_ok(lobby_result):
        print(f"[TEST] FAIL - Could not reach IN_CITY. Aborting.")
        return

    # Step 2: Navigate via V2
    print(f"\n[TEST] Step 2: Running _go_to_construction_v2('SCOUT_SENTRY_POST', feature='scout')...")
    result = core_actions._go_to_construction_v2(serial, detector, "SCOUT_SENTRY_POST", feature="scout")
    ok = core_actions._is_ok(result)
    print(f"[TEST] Navigation: {'OK' if ok else 'FAIL'} Result: {result}")

    if ok:
        save_frame(serial, detector, "scout_post_reached")

    # Cleanup
    adb_helper.press_back(serial)
    time.sleep(2)

    # Summary
    print(f"\n{'=' * 50}")
    print(f"[TEST] === SUMMARY ===")
    print(f"  Navigation: {'OK' if ok else 'FAIL'}")
    print(f"  Debug screenshots: {DEBUG_DIR}")
    print(f"{'=' * 50}")


# ─────────────────────────────────────────────
# TEST 3: Template Detection (Quick Help + Claim All)
# ─────────────────────────────────────────────
def test_detect_templates(serial):
    """Test SCOUT_QUICK_HELP_BTN, SCOUT_CLAIM_ALL_BTN, SCOUT_SENTRY_POST_BTN detection.

    Prerequisite: emulator should be on the Scout Sentry Post screen.
    This test navigates to the screen first, then checks all templates.
    """
    print(f"\n[TEST] === Scout Template Detection on {serial} ===")

    detector = _make_detector()

    # Navigate to Scout Sentry Post screen
    print(f"\n[TEST] Navigating to Scout Sentry Post...")
    result = core_actions._go_to_construction_v2(serial, detector, "SCOUT_SENTRY_POST", feature="scout")
    if not core_actions._is_ok(result):
        print(f"[TEST] FAIL - Could not navigate to Scout Sentry Post. Aborting.")
        return

    time.sleep(2)
    save_frame(serial, detector, "scout_screen")

    # Check templates
    targets = ["SCOUT_QUICK_HELP_BTN", "SCOUT_CLAIM_ALL_BTN", "SCOUT_SENTRY_POST_BTN"]
    results = {}

    for target in targets:
        detector._screen_cache = None
        match = detector.check_activity(serial, target=target, threshold=0.8)
        results[target] = match
        if match:
            print(f"[TEST] {target}: FOUND at ({match[1]}, {match[2]})")
        else:
            print(f"[TEST] {target}: not detected")

    # Also check construction verify
    detector._screen_cache = None
    con_match = detector.check_construction(serial, target="SCOUT_SENTRY_POST")
    print(f"[TEST] SCOUT_SENTRY_POST (construction): {'FOUND' if con_match else 'not detected'}")

    # Cleanup
    adb_helper.press_back(serial)
    time.sleep(2)

    # Summary
    print(f"\n{'=' * 50}")
    print(f"[TEST] === SUMMARY ===")
    for target, match in results.items():
        status = f"OK at ({match[1]}, {match[2]})" if match else "NOT FOUND"
        print(f"  {target}: {status}")
    print(f"  SCOUT_SENTRY_POST (construction): {'OK' if con_match else 'NOT FOUND'}")
    print(f"  Debug screenshots: {DEBUG_DIR}")
    print(f"{'=' * 50}")


# ─────────────────────────────────────────────
# TEST 4: Construction Verify Template Only
# ─────────────────────────────────────────────
def test_construction_verify(serial):
    """Test SCOUT_SENTRY_POST construction template detection.

    Prerequisite: emulator should be at IN_CITY with Scout Sentry Post building visible.
    This test taps the building base coordinate and checks if verify template matches.
    """
    print(f"\n[TEST] === Scout Sentry Post Construction Verify on {serial} ===")

    detector = _make_detector()

    # Navigate to IN_CITY
    print(f"\n[TEST] Navigating to IN_CITY...")
    lobby_result = core_actions.back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not core_actions._is_ok(lobby_result):
        print(f"[TEST] FAIL - Could not reach IN_CITY.")
        return

    # Tap building base (755, 235)
    print(f"\n[TEST] Tapping Scout Sentry Post building at (755, 235)...")
    adb_helper.tap(serial, 755, 235)
    time.sleep(3)

    save_frame(serial, detector, "scout_building_popup")

    # Check construction verify
    detector._screen_cache = None
    con_match = detector.check_construction(serial, target="SCOUT_SENTRY_POST")

    # Check activity btn
    detector._screen_cache = None
    btn_match = detector.check_activity(serial, target="SCOUT_SENTRY_POST_BTN", threshold=0.8)

    print(f"[TEST] SCOUT_SENTRY_POST (construction): {'FOUND' if con_match else 'not detected'}")
    if btn_match:
        print(f"[TEST] SCOUT_SENTRY_POST_BTN: FOUND at ({btn_match[1]}, {btn_match[2]})")
    else:
        print(f"[TEST] SCOUT_SENTRY_POST_BTN: not detected")

    # Cleanup
    adb_helper.press_back(serial)
    time.sleep(2)

    # Summary
    print(f"\n{'=' * 50}")
    print(f"[TEST] === SUMMARY ===")
    print(f"  Construction verify: {'OK' if con_match else 'NOT FOUND'}")
    status = f"OK at ({btn_match[1]}, {btn_match[2]})" if btn_match else "NOT FOUND"
    print(f"  Scout BTN activity: {status}")
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

    parser = argparse.ArgumentParser(description="Test Scout Sentry Post workflow")
    parser.add_argument("test", choices=["full", "nav", "detect", "verify", "all"],
                        help="Which test to run")
    parser.add_argument("--serial", default="emulator-5556", help="Emulator serial (default: emulator-5556)")
    args = parser.parse_args()

    if args.test == "full":
        test_full_claim(args.serial)
    elif args.test == "nav":
        test_navigation(args.serial)
    elif args.test == "detect":
        test_detect_templates(args.serial)
    elif args.test == "verify":
        test_construction_verify(args.serial)
    elif args.test == "all":
        test_construction_verify(args.serial)
        test_navigation(args.serial)
        test_detect_templates(args.serial)
        test_full_claim(args.serial)
