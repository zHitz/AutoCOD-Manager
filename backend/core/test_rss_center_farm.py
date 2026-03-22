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
DEBUG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_rss_center")


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
# TEST 1: Full RSS Center Farm Workflow (end-to-end)
# ─────────────────────────────────────────────
def test_full_rss_center_farm(serial):
    """Run the full go_to_rss_center_farm workflow."""
    print(f"\n[TEST] === Full RSS Center Farm Workflow on {serial} ===")

    detector = _make_detector()

    print(f"\n[TEST] Running go_to_rss_center_farm()...")
    print("-" * 50)

    try:
        result = core_actions.go_to_rss_center_farm(serial, detector)
        print("-" * 50)
        ok = result.get("ok", False)
        cd = result.get("dynamic_cooldown_sec", 0)
        cd_min = round(cd / 60, 1) if cd else 0
        print(f"[TEST] {'OK' if ok else 'FAIL'} Result: {result}")
        if cd:
            print(f"[TEST] Dynamic cooldown: {cd}s ({cd_min}m)")
    except KeyboardInterrupt:
        print(f"\n[TEST] Aborted by user.")
    except Exception as e:
        print(f"\n[TEST] Exception: {e}")
        import traceback
        traceback.print_exc()


# ─────────────────────────────────────────────
# TEST 2: RSS Center Marker Detection (with scroll)
# ─────────────────────────────────────────────
def test_marker_detection(serial):
    """Test if RSS_CENTER_MARKER is found in Markers Menu, with scroll.

    Steps:
    1. Navigate to OUT_CITY
    2. Open Markers Menu
    3. Search for RSS_CENTER_MARKER (scrolling down each attempt)
    """
    print(f"\n[TEST] === RSS Center Marker Detection on {serial} ===")

    detector = _make_detector()

    # Step 1: Go to OUT_CITY
    print(f"\n[TEST] Step 1: Navigating to OUT_CITY...")
    lobby_result = core_actions.back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)")
    if not core_actions._is_ok(lobby_result):
        print(f"[TEST] FAIL - Could not reach OUT_CITY. Aborting.")
        return

    # Step 2: Open Markers Menu
    print(f"\n[TEST] Step 2: Opening Markers Menu (180, 16)...")
    adb_helper.tap(serial, 180, 16)
    time.sleep(3)

    state = core_actions.wait_for_state(serial, detector, ["MARKERS_MENU"], timeout_sec=10, check_mode="construction")
    if state != "MARKERS_MENU":
        print(f"[TEST] FAIL - Markers Menu not detected. Aborting.")
        return
    print(f"[TEST] Markers Menu opened.")

    # Step 3: Search for RSS_CENTER_MARKER with scroll
    print(f"\n[TEST] Step 3: Searching for RSS_CENTER_MARKER (with scroll)...")
    rss_marker = None
    for attempt in range(5):
        save_frame(serial, detector, f"markers_scroll_{attempt}")
        detector._screen_cache = None
        rss_marker = detector.check_activity(serial, target="RSS_CENTER_MARKER", threshold=0.8)
        if rss_marker:
            print(f"[TEST] OK - RSS_CENTER_MARKER found at ({rss_marker[1]}, {rss_marker[2]}) on attempt {attempt + 1}")
            break
        print(f"[TEST] Not found on attempt {attempt + 1}/5. Scrolling down...")
        adb_helper.swipe(serial, 480, 400, 480, 250, 300)
        time.sleep(2)

    if not rss_marker:
        print(f"[TEST] FAIL - RSS_CENTER_MARKER not found after 5 scroll attempts.")

    # Cleanup
    adb_helper.press_back(serial)
    time.sleep(2)

    # Summary
    print(f"\n{'=' * 50}")
    print(f"[TEST] === SUMMARY ===")
    if rss_marker:
        print(f"  RSS_CENTER_MARKER: OK at ({rss_marker[1]}, {rss_marker[2]})")
    else:
        print(f"  RSS_CENTER_MARKER: NOT FOUND")
    print(f"  Debug screenshots: {DEBUG_DIR}")
    print(f"{'=' * 50}")


# ─────────────────────────────────────────────
# TEST 3: RSS View / Gather / Build Detection
# ─────────────────────────────────────────────
def test_view_gather_detection(serial):
    """Test RSS_VIEW, RSS_GATHER, RSS_BUILD template detection.

    Prerequisite: Emulator should be on OUT_CITY near RSS Center.
    This test navigates via Markers Menu, taps RSS Center on map,
    then checks which activity templates match.
    """
    print(f"\n[TEST] === RSS View/Gather/Build Detection on {serial} ===")

    detector = _make_detector()

    # Navigate to OUT_CITY
    print(f"\n[TEST] Navigating to OUT_CITY...")
    lobby_result = core_actions.back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)")
    if not core_actions._is_ok(lobby_result):
        print(f"[TEST] FAIL - Could not reach OUT_CITY.")
        return

    # Open Markers Menu
    print(f"[TEST] Opening Markers Menu...")
    adb_helper.tap(serial, 180, 16)
    time.sleep(3)

    state = core_actions.wait_for_state(serial, detector, ["MARKERS_MENU"], timeout_sec=10, check_mode="construction")
    if state != "MARKERS_MENU":
        print(f"[TEST] FAIL - Markers Menu not detected.")
        return

    # Find RSS Center marker (with scroll)
    rss_marker = None
    for attempt in range(5):
        detector._screen_cache = None
        rss_marker = detector.check_activity(serial, target="RSS_CENTER_MARKER", threshold=0.8)
        if rss_marker:
            break
        adb_helper.swipe(serial, 480, 400, 480, 250, 300)
        time.sleep(2)

    if not rss_marker:
        print(f"[TEST] FAIL - RSS_CENTER_MARKER not found. Cannot test view/gather.")
        adb_helper.press_back(serial)
        return

    # Tap GO on marker
    center_x, center_y = rss_marker[1], rss_marker[2]
    go_x = center_x + 570
    print(f"[TEST] Found marker at ({center_x}, {center_y}). Tapping GO ({go_x}, {center_y})...")
    adb_helper.tap(serial, go_x, center_y)
    time.sleep(6)

    # Tap RSS Center on map
    print(f"[TEST] Tapping RSS Center on map (479, 254)...")
    adb_helper.tap(serial, 479, 254)
    time.sleep(3)

    # Check templates
    save_frame(serial, detector, "rss_center_popup")
    detector._screen_cache = None

    targets = ["RSS_VIEW", "RSS_GATHER", "RSS_BUILD"]
    results = {}
    for target in targets:
        detector._screen_cache = None
        match = detector.check_activity(serial, target=target, threshold=0.8)
        results[target] = match
        if match:
            print(f"[TEST] {target}: FOUND at ({match[1]}, {match[2]})")
        else:
            print(f"[TEST] {target}: not detected")

    # Cleanup
    adb_helper.tap(serial, 50, 500)
    time.sleep(2)

    # Summary
    print(f"\n{'=' * 50}")
    print(f"[TEST] === SUMMARY ===")
    for target, match in results.items():
        status = f"OK at ({match[1]}, {match[2]})" if match else "NOT FOUND"
        print(f"  {target}: {status}")
    print(f"  Debug screenshots: {DEBUG_DIR}")
    print(f"{'=' * 50}")


# ─────────────────────────────────────────────
# TEST 4: OCR Building Time / Remaining Time
# ─────────────────────────────────────────────
def test_ocr_reading(serial):
    """Test OCR reading for building_time and remaining_time on RSS Center popup.

    Prerequisite: Emulator should be at the RSS Center info popup screen.
    """
    print(f"\n[TEST] === OCR Reading Test on {serial} ===")

    detector = _make_detector()
    from backend.core.workflow.ocr_helper import (
        ocr_region_text, ocr_region_with_retry, parse_game_timer, parse_builder_count
    )

    ROI_BUILDER_COUNT = (750, 265, 800, 290)
    ROI_BUILDING_TIME = (725, 350, 800, 370)
    ROI_REMAINING_TIME = (655, 222, 725, 240)

    save_frame(serial, detector, "ocr_test")

    print(f"\n[TEST] Reading Building Time ROI {ROI_BUILDING_TIME}...")
    building_text = ocr_region_text(serial, detector, ROI_BUILDING_TIME)
    building_sec = parse_game_timer(building_text) if building_text else 0
    print(f"[TEST] Building Time: '{building_text}' -> {building_sec}s ({round(building_sec/60, 1)}m)")

    print(f"\n[TEST] Reading Builder Count ROI {ROI_BUILDER_COUNT}...")
    builder_text = ocr_region_text(serial, detector, ROI_BUILDER_COUNT)
    builder_count = parse_builder_count(builder_text)
    print(f"[TEST] Builder Count: '{builder_text}' -> {builder_count}/36")

    print(f"\n[TEST] Reading Remaining Time ROI {ROI_REMAINING_TIME} (with retry)...")
    remaining_text = ocr_region_with_retry(
        serial, detector, ROI_REMAINING_TIME,
        attempts=5, style="outline",
        validator=lambda t: parse_game_timer(t) > 0
    )
    remaining_sec = parse_game_timer(remaining_text) if remaining_text else 0
    print(f"[TEST] Remaining Time: '{remaining_text}' -> {remaining_sec}s ({round(remaining_sec/60, 1)}m)")

    # Summary
    print(f"\n{'=' * 50}")
    print(f"[TEST] === OCR SUMMARY ===")
    print(f"  Building Time : '{building_text}' -> {building_sec}s")
    print(f"  Builder Count : '{builder_text}' -> {builder_count}/36")
    print(f"  Remaining Time: '{remaining_text}' -> {remaining_sec}s")
    if building_sec > 0:
        print(f"  State: TH1 (Build)")
    elif remaining_sec > 0:
        print(f"  State: TH2 (Gather)")
    else:
        print(f"  State: UNKNOWN (both OCR returned 0)")
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

    parser = argparse.ArgumentParser(description="Test RSS Center Farm workflow")
    parser.add_argument("test", choices=["full", "marker", "detect", "ocr", "all"],
                        help="Which test to run")
    parser.add_argument("--serial", default="emulator-5556", help="Emulator serial (default: emulator-5556)")
    args = parser.parse_args()

    if args.test == "full":
        test_full_rss_center_farm(args.serial)
    elif args.test == "marker":
        test_marker_detection(args.serial)
    elif args.test == "detect":
        test_view_gather_detection(args.serial)
    elif args.test == "ocr":
        test_ocr_reading(args.serial)
    elif args.test == "all":
        test_marker_detection(args.serial)
        test_view_gather_detection(args.serial)
        test_full_rss_center_farm(args.serial)
