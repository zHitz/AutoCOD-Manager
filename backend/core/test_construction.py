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
from backend.core.workflow.construction_data import CONSTRUCTION_TAPS, CONSTRUCTION_DATA
import adb_helper

# Output directory for debug screenshots
DEBUG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_construction")

AVAILABLE_CONSTRUCTIONS = list(CONSTRUCTION_TAPS.keys())


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


def _init_detector():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")
    return GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)


# ─────────────────────────────────────────────
# TEST 1: Full go_to_construction (end-to-end)
# ─────────────────────────────────────────────
def test_full_construction(serial, building="HALL"):
    """Run go_to_construction and observe result."""
    print(f"\n[TEST] === Full go_to_construction ({building}) on {serial} ===")

    detector = _init_detector()

    print(f"\n[TEST] Running go_to_construction('{building}')...")
    print("-" * 50)

    try:
        result = core_actions.go_to_construction(serial, detector, building)
        print("-" * 50)
        ok = result.get("ok", False)
        print(f"[TEST] {'✅' if ok else '❌'} Result: {result}")

        # Save debug screenshot after navigation
        save_frame(serial, detector, f"after_nav_{building.lower()}")

        # Cleanup: press back to return
        print(f"\n[TEST] Pressing BACK to cleanup...")
        adb_helper.press_back(serial)
        time.sleep(2)
    except KeyboardInterrupt:
        print(f"\n[TEST] ⏭️ Aborted by user.")
    except Exception as e:
        print(f"\n[TEST] ❌ Exception: {e}")


# ─────────────────────────────────────────────
# TEST 2: Construction Template Detection
# ─────────────────────────────────────────────
def test_template_detection(serial, building="HALL"):
    """Navigate to a construction and verify template detection works.

    Steps:
    1. Navigate to IN_CITY
    2. Execute tap sequence for the building
    3. Check if check_construction detects the building
    4. Save debug screenshot for visual verification
    """
    print(f"\n[TEST] === Construction Template Detection ({building}) on {serial} ===")

    detector = _init_detector()

    # Step 1: Navigate to IN_CITY
    print(f"\n[TEST] Step 1: Navigating to IN_CITY...")
    lobby_result = core_actions.back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not core_actions._is_ok(lobby_result):
        print(f"[TEST] ❌ Could not reach IN_CITY. Aborting.")
        return

    # Step 2: Execute tap sequence manually
    taps = CONSTRUCTION_TAPS[building]
    print(f"\n[TEST] Step 2: Tapping building sequence: {taps}")
    for i, (x, y) in enumerate(taps):
        print(f"[TEST]   Tap #{i+1}: ({x}, {y})")
        adb_helper.tap(serial, x, y)
        time.sleep(2)
    time.sleep(3)

    # Step 3: Check detection
    print(f"\n[TEST] Step 3: Checking check_construction(target='{building}')...")
    save_frame(serial, detector, f"detection_{building.lower()}")
    detector._screen_cache = None
    result = detector.check_construction(serial, target=building)

    if result:
        print(f"[TEST] ✅ {building} detected successfully!")
    else:
        print(f"[TEST] ❌ {building} NOT detected — template may need updating")

    # Step 4: Check false negative — scan all constructions
    print(f"\n[TEST] Step 4: Scanning ALL construction templates...")
    detector._screen_cache = None
    any_match = detector.check_construction(serial)
    if any_match:
        print(f"[TEST]   Found: {any_match}")
        if any_match != building:
            print(f"[TEST]   ⚠️ Mismatch! Expected '{building}' but detected '{any_match}'")
    else:
        print(f"[TEST]   No construction template matched at all.")

    # Cleanup
    adb_helper.press_back(serial)
    time.sleep(2)

    # Summary
    print(f"\n{'=' * 50}")
    print(f"[TEST] === SUMMARY ===")
    print(f"  Target: {building}")
    print(f"  Detected: {'✅ ' + result if result else '❌ NOT FOUND'}")
    print(f"  All-scan: {any_match if any_match else 'NONE'}")
    print(f"  Debug screenshots: {DEBUG_DIR}")
    print(f"{'=' * 50}")


# ─────────────────────────────────────────────
# TEST 3: All Constructions Sweep
# ─────────────────────────────────────────────
def test_all_constructions(serial):
    """Run go_to_construction for every building in CONSTRUCTION_TAPS.

    Reports pass/fail summary at the end.
    """
    print(f"\n[TEST] === All Constructions Sweep on {serial} ===")
    print(f"[TEST] Buildings to test: {AVAILABLE_CONSTRUCTIONS}")

    detector = _init_detector()
    results = {}

    for building in AVAILABLE_CONSTRUCTIONS:
        print(f"\n{'─' * 50}")
        print(f"[TEST] Testing: {building}")
        print(f"{'─' * 50}")

        try:
            result = core_actions.go_to_construction(serial, detector, building)
            ok = result.get("ok", False)
            results[building] = "✅ PASS" if ok else f"❌ FAIL ({result.get('error', '')})"
            save_frame(serial, detector, f"sweep_{building.lower()}")
        except Exception as e:
            results[building] = f"❌ EXCEPTION ({e})"

        # Cleanup: back to lobby
        adb_helper.press_back(serial)
        time.sleep(2)

    # Summary
    print(f"\n{'=' * 50}")
    print(f"[TEST] === ALL CONSTRUCTIONS SUMMARY ===")
    for building, status in results.items():
        print(f"  {building:25s} {status}")
    passed = sum(1 for v in results.values() if v.startswith("✅"))
    print(f"\n  Total: {passed}/{len(results)} passed")
    print(f"  Debug screenshots: {DEBUG_DIR}")
    print(f"{'=' * 50}")


# ─────────────────────────────────────────────
# TEST 4: Invalid Construction Name
# ─────────────────────────────────────────────
def test_invalid_name(serial):
    """Test that an invalid construction name returns CONFIG_INVALID_PARAM."""
    print(f"\n[TEST] === Invalid Construction Name Test ===")

    detector = _init_detector()

    result = core_actions.go_to_construction(serial, detector, "FAKE_BUILDING_XYZ")
    error = result.get("error", "")

    if "CONFIG_INVALID_PARAM" in error:
        print(f"[TEST] ✅ Correctly returned CONFIG_INVALID_PARAM: {error}")
    else:
        print(f"[TEST] ❌ Expected CONFIG_INVALID_PARAM, got: {result}")


# ─────────────────────────────────────────────
# TEST 5: V2 Feature-Based Navigation
# ─────────────────────────────────────────────
def test_v2_feature(serial, building="HALL", feature="info"):
    """Test V2 feature-based navigation.

    Steps:
    1. Call go_to_construction with feature param
    2. Verify it reaches the correct construction screen
    3. Save debug screenshot
    """
    print(f"\n[TEST] === V2 Feature Navigation ({building} -> {feature}) on {serial} ===")

    # Validate inputs
    if building not in CONSTRUCTION_DATA:
        print(f"[TEST] ❌ '{building}' not in CONSTRUCTION_DATA. Available: {list(CONSTRUCTION_DATA.keys())}")
        return
    features = list(CONSTRUCTION_DATA[building]["features"].keys())
    if feature not in features:
        print(f"[TEST] ❌ '{feature}' not available for {building}. Available: {features}")
        return

    detector = _init_detector()

    print(f"\n[TEST] Running go_to_construction('{building}', feature='{feature}')...")
    print("-" * 50)

    try:
        result = core_actions.go_to_construction(serial, detector, building, feature=feature)
        print("-" * 50)
        ok = result.get("ok", False)
        print(f"[TEST] {'✅' if ok else '❌'} Result: {result}")

        save_frame(serial, detector, f"v2_{building.lower()}_{feature}")

        # Cleanup
        print(f"\n[TEST] Pressing BACK to cleanup...")
        adb_helper.press_back(serial)
        time.sleep(2)
    except KeyboardInterrupt:
        print(f"\n[TEST] ⏭️ Aborted by user.")
    except Exception as e:
        print(f"\n[TEST] ❌ Exception: {e}")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(description="Test go_to_construction workflow")
    parser.add_argument("test", choices=["full", "detect", "sweep", "invalid", "v2", "all"],
                        help="Which test to run")
    parser.add_argument("--serial", default="emulator-5556", help="Emulator serial (default: emulator-5556)")
    parser.add_argument("--building", default="HALL", choices=AVAILABLE_CONSTRUCTIONS,
                        help=f"Construction name (default: HALL)")
    parser.add_argument("--feature", default="info",
                        help="Feature name for V2 test (default: info)")
    args = parser.parse_args()

    if args.test == "full":
        test_full_construction(args.serial, args.building)
    elif args.test == "detect":
        test_template_detection(args.serial, args.building)
    elif args.test == "sweep":
        test_all_constructions(args.serial)
    elif args.test == "invalid":
        test_invalid_name(args.serial)
    elif args.test == "v2":
        test_v2_feature(args.serial, args.building, args.feature)
    elif args.test == "all":
        test_invalid_name(args.serial)
        test_template_detection(args.serial, args.building)
        test_full_construction(args.serial, args.building)
        test_v2_feature(args.serial, args.building, args.feature)
