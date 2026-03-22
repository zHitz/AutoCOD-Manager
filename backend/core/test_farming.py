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
DEBUG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_farming")


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


# ─────────────────────────────────────────────
# TEST 1: Full Farming Workflow (end-to-end)
# ─────────────────────────────────────────────
def test_full_farming(serial, resource_type="wood"):
    """Run the full go_to_farming workflow and observe results."""
    print(f"\n[TEST] === Full Farming Workflow ({resource_type.upper()}) on {serial} ===")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    print(f"\n[TEST] Running go_to_farming(resource_type='{resource_type}')...")
    print("-" * 50)

    try:
        result = core_actions.go_to_farming(serial, detector, resource_type=resource_type)
        print("-" * 50)
        ok = result.get("ok", False)
        print(f"[TEST] {'✅' if ok else '❌'} Result: {result}")
    except KeyboardInterrupt:
        print(f"\n[TEST] ⏭️ Aborted by user.")
    except Exception as e:
        print(f"\n[TEST] ❌ Exception: {e}")


# ─────────────────────────────────────────────
# TEST 2: Verify Search Panel Detection
# ─────────────────────────────────────────────
def test_search_panel_detection(serial):
    """Test if FARM_SEARCH_BTN template detects the search panel correctly.
    
    Steps:
    1. Navigate to OUT_CITY
    2. Open search menu
    3. Check if FARM_SEARCH_BTN is detected (should be YES)
    4. Close menu and check again (should be NO)
    """
    print(f"\n[TEST] === Search Panel Detection Test on {serial} ===")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    # Step 1: Go to OUT_CITY
    print(f"\n[TEST] Step 1: Navigating to OUT_CITY...")
    lobby_result = core_actions.back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)")
    if not core_actions._is_ok(lobby_result):
        print(f"[TEST] ❌ Could not reach OUT_CITY. Aborting.")
        return

    # Step 2: Open search menu
    print(f"\n[TEST] Step 2: Opening Search Menu (42, 422)...")
    adb_helper.tap(serial, 42, 422)
    time.sleep(4)

    # Step 3: Check detection — should find FARM_SEARCH_BTN
    print(f"\n[TEST] Step 3: Detecting FARM_SEARCH_BTN (expected: FOUND)...")
    save_frame(serial, detector, "panel_open")
    detector._screen_cache = None
    result_open = detector.check_activity(serial, target="FARM_SEARCH_BTN", threshold=0.8)
    if result_open:
        print(f"[TEST] ✅ FARM_SEARCH_BTN detected at ({result_open[1]}, {result_open[2]})")
    else:
        print(f"[TEST] ❌ FARM_SEARCH_BTN NOT detected — template may need updating")

    # Step 4: Close menu and check again — should NOT find it
    print(f"\n[TEST] Step 4: Closing menu, detecting again (expected: NOT FOUND)...")
    adb_helper.press_back(serial)
    time.sleep(3)
    save_frame(serial, detector, "panel_closed")
    detector._screen_cache = None
    result_closed = detector.check_activity(serial, target="FARM_SEARCH_BTN", threshold=0.8)
    if not result_closed:
        print(f"[TEST] ✅ FARM_SEARCH_BTN correctly NOT detected on world map")
    else:
        print(f"[TEST] ❌ FALSE POSITIVE — FARM_SEARCH_BTN detected on world map! Threshold too low?")

    # Summary
    print(f"\n{'=' * 50}")
    print(f"[TEST] === SUMMARY ===")
    print(f"  Panel OPEN  → FARM_SEARCH_BTN: {'✅ FOUND' if result_open else '❌ MISSING'}")
    print(f"  Panel CLOSED → FARM_SEARCH_BTN: {'❌ FALSE POSITIVE' if result_closed else '✅ CORRECT (not found)'}")
    print(f"  Debug screenshots: {DEBUG_DIR}")
    print(f"{'=' * 50}")


# ─────────────────────────────────────────────
# TEST 3: Verify Gather Button Detection (RSS_GATHER)
# ─────────────────────────────────────────────
def test_gather_button_detection(serial, resource_type="wood"):
    """Test if RSS_GATHER template detects gather button on mine popup.

    Steps:
    1. Navigate to OUT_CITY → open search → tap search
    2. After map pans, check if RSS_GATHER is detected on the mine popup
    """
    print(f"\n[TEST] === Gather Button Detection Test on {serial} ===")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    RESOURCE_TAPS = {
        "gold": (320, 485), "wood": (475, 485),
        "stone": (640, 485), "mana": (795, 485)
    }
    SEARCH_TAPS = {
        "gold": (320, 400), "wood": (475, 400),
        "stone": (640, 400), "mana": (795, 400)
    }

    r_type = resource_type.lower()

    # Step 1: Navigate + open search + find mine
    print(f"\n[TEST] Step 1: Navigate to OUT_CITY...")
    lobby_result = core_actions.back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)")
    if not core_actions._is_ok(lobby_result):
        print(f"[TEST] ❌ Could not reach OUT_CITY.")
        return

    print(f"[TEST] Opening Search Menu...")
    adb_helper.tap(serial, 42, 422)
    time.sleep(4)

    print(f"[TEST] Selecting {r_type.upper()}...")
    rx, ry = RESOURCE_TAPS[r_type]
    adb_helper.tap(serial, rx, ry)
    time.sleep(2)

    print(f"[TEST] Tapping Search...")
    sx, sy = SEARCH_TAPS[r_type]
    adb_helper.tap(serial, sx, sy)
    time.sleep(6)

    # Check if mine was found
    detector._screen_cache = None
    still_open = detector.check_activity(serial, target="FARM_SEARCH_BTN", threshold=0.8)
    if still_open:
        print(f"[TEST] ⚠️ No mine found (search panel still open). Cannot test gather button.")
        adb_helper.press_back(serial)
        return

    # Step 2: Check RSS_GATHER detection
    print(f"\n[TEST] Step 2: Mine found! Checking RSS_GATHER detection...")
    save_frame(serial, detector, "mine_popup")
    detector._screen_cache = None
    gather_result = detector.check_activity(serial, target="RSS_GATHER", threshold=0.8)

    if gather_result:
        print(f"[TEST] ✅ RSS_GATHER detected at ({gather_result[1]}, {gather_result[2]})")
    else:
        print(f"[TEST] ❌ RSS_GATHER NOT detected — template may need updating or mine popup not loaded")

    # Cleanup
    adb_helper.press_back(serial)
    time.sleep(2)

    # Summary
    print(f"\n{'=' * 50}")
    print(f"[TEST] === SUMMARY ===")
    print(f"  RSS_GATHER: {'✅ FOUND at (' + str(gather_result[1]) + ', ' + str(gather_result[2]) + ')' if gather_result else '❌ NOT FOUND'}")
    print(f"  Debug screenshots: {DEBUG_DIR}")
    print(f"{'=' * 50}")


# ─────────────────────────────────────────────
# TEST 4: No Mine Edge Case
# ─────────────────────────────────────────────
def test_no_mine_detection(serial, resource_type="mana"):
    """Test the no-mine detection path.
    
    Uses 'mana' by default since it's most likely to have no nearby mines.
    Verifies the workflow correctly detects no mine and breaks early.
    """
    print(f"\n[TEST] === No Mine Detection Test ({resource_type.upper()}) on {serial} ===")
    print(f"[TEST] TIP: Use a resource type with no nearby mines for best results")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    print(f"\n[TEST] Running go_to_farming(resource_type='{resource_type}')...")
    print("-" * 50)

    result = core_actions.go_to_farming(serial, detector, resource_type=resource_type)

    print("-" * 50)
    ok = result.get("ok", False)
    print(f"[TEST] {'✅' if ok else '❌'} Result: {result}")
    print(f"[TEST] Check logs above for '[NO MINE]' message to confirm detection worked.")


# ─────────────────────────────────────────────
# TEST 5: _human_delay randomization check
# ─────────────────────────────────────────────
def test_human_delay():
    """Verify _human_delay produces randomized timings (no ADB needed)."""
    print(f"\n[TEST] === _human_delay Randomization Test ===")

    timings = []
    for i in range(10):
        start = time.time()
        core_actions._human_delay(2.0, variance=0.4)
        elapsed = time.time() - start
        timings.append(elapsed)
        print(f"[TEST] Delay #{i+1}: {elapsed:.3f}s")

    min_t, max_t = min(timings), max(timings)
    spread = max_t - min_t
    avg = sum(timings) / len(timings)

    print(f"\n[TEST] === SUMMARY ===")
    print(f"  Base: 2.0s ± 40%  →  Expected range: ~1.2s - 2.8s")
    print(f"  Actual: min={min_t:.3f}s, max={max_t:.3f}s, avg={avg:.3f}s, spread={spread:.3f}s")

    if spread > 0.3:
        print(f"[TEST] ✅ Timing is randomized (spread > 0.3s)")
    else:
        print(f"[TEST] ❌ Timing is NOT randomized enough (spread <= 0.3s)")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(description="Test go_to_farming workflow")
    parser.add_argument("test", choices=["full", "search", "gather", "nomine", "delay", "all"],
                        help="Which test to run")
    parser.add_argument("--serial", default="emulator-5556", help="Emulator serial (default: emulator-5556)")
    parser.add_argument("--resource", default="wood", choices=["gold", "wood", "stone", "mana"],
                        help="Resource type (default: wood)")
    args = parser.parse_args()

    if args.test == "full":
        test_full_farming(args.serial, args.resource)
    elif args.test == "search":
        test_search_panel_detection(args.serial)
    elif args.test == "gather":
        test_gather_button_detection(args.serial, args.resource)
    elif args.test == "nomine":
        test_no_mine_detection(args.serial, args.resource)
    elif args.test == "delay":
        test_human_delay()
    elif args.test == "all":
        test_human_delay()
        test_search_panel_detection(args.serial)
        test_gather_button_detection(args.serial, args.resource)
        test_no_mine_detection(args.serial, args.resource)
        test_full_farming(args.serial, args.resource)
