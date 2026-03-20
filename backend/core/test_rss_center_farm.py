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
from backend.core.workflow.ocr_helper import ocr_region_text, ocr_region_with_retry, parse_game_timer


# Same ROI constants as go_to_rss_center_farm
ROI_BUILDER_COUNT = (750, 265, 800, 290)
ROI_BUILDING_TIME = (725, 350, 800, 370)
ROI_REMAINING_TIME = (655, 222, 725, 240)

# Output directory for debug screenshots
DEBUG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_rss_timer")


def save_roi_debug(serial, detector, label, roi_box):
    """Capture screenshot and save both the full frame and the ROI crop for debugging."""
    os.makedirs(DEBUG_DIR, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    frame = detector.get_frame(serial)
    if frame is None:
        print(f"[{serial}] [DEBUG] Could not capture frame for {label}")
        return

    x1, y1, x2, y2 = roi_box

    # Save ROI crop
    roi_crop = frame[y1:y2, x1:x2]
    crop_path = os.path.join(DEBUG_DIR, f"{timestamp}_{label}_roi.png")
    cv2.imwrite(crop_path, roi_crop)
    print(f"[{serial}] [DEBUG] Saved ROI crop: {crop_path}")

    # Save full frame with ROI rectangle drawn
    frame_annotated = frame.copy()
    cv2.rectangle(frame_annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)
    cv2.putText(frame_annotated, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
    full_path = os.path.join(DEBUG_DIR, f"{timestamp}_{label}_full.png")
    cv2.imwrite(full_path, frame_annotated)
    print(f"[{serial}] [DEBUG] Saved full frame: {full_path}")


def test_rss_center_farm(serial="emulator-5556"):
    print(f"\n[TEST] === Alliance Resource Center Farming Test on {serial} ===")

    # Init Detector
    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")
    print(f"[TEST] Loading Detector from {templates_dir}...")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    # --- Step 1: Navigate to RSS Center info panel (same as the function does) ---
    print(f"\n[TEST] Step 1: Navigating to RSS Center...")
    print("-" * 50)

    if not core_actions.back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)"):
        print(f"[TEST] ❌ Could not reach OUT_CITY. Aborting.")
        return

    core_actions.adb_helper.tap(serial, 180, 16)
    time.sleep(3)

    state = core_actions.wait_for_state(serial, detector, ["MARKERS_MENU"], timeout_sec=10, check_mode="construction")
    if state != "MARKERS_MENU":
        print(f"[TEST] ❌ Could not open Markers Menu. Aborting.")
        return

    rss_marker = None
    for attempt in range(3):
        rss_marker = detector.check_activity(serial, target="RSS_CENTER_MARKER", threshold=0.8)
        if rss_marker:
            break
        time.sleep(2)

    if not rss_marker:
        print(f"[TEST] ❌ RSS Center marker not found. Aborting.")
        return

    center_x, center_y = rss_marker[1], rss_marker[2]
    go_x, go_y = center_x + 570, center_y
    print(f"[TEST] Found RSS Center. Tapping GO ({go_x}, {go_y})...")
    core_actions.adb_helper.tap(serial, go_x, go_y)
    time.sleep(6)

    print(f"[TEST] Tapping RSS Center on map (479, 254)...")
    core_actions.adb_helper.tap(serial, 479, 254)
    time.sleep(3)

    # --- Step 2: Capture timer ROI screenshots BEFORE any action ---
    print(f"\n[TEST] Step 2: Capturing timer ROI debug screenshots...")
    print("-" * 50)

    save_roi_debug(serial, detector, "BUILDER_COUNT", ROI_BUILDER_COUNT)
    save_roi_debug(serial, detector, "BUILDING_TIME", ROI_BUILDING_TIME)
    save_roi_debug(serial, detector, "REMAINING_TIME", ROI_REMAINING_TIME)

    # --- Step 3: OCR all timer values ---
    print(f"\n[TEST] Step 3: OCR timer values...")
    print("-" * 50)

    building_time_text = ocr_region_text(serial, detector, ROI_BUILDING_TIME)
    building_sec = parse_game_timer(building_time_text) if building_time_text else 0
    print(f"[TEST] BUILDING_TIME: raw='{building_time_text}' → {building_sec}s")

    remaining_text = ocr_region_with_retry(
        serial, detector, ROI_REMAINING_TIME,
        attempts=5, style="outline",
        validator=lambda t: parse_game_timer(t) > 0
    )
    remaining_sec = parse_game_timer(remaining_text) if remaining_text else 0
    print(f"[TEST] REMAINING_TIME: raw='{remaining_text}' → {remaining_sec}s")

    builder_text = ocr_region_text(serial, detector, ROI_BUILDER_COUNT)
    print(f"[TEST] BUILDER_COUNT: raw='{builder_text}'")

    # --- Step 4: Run the actual function ---
    print(f"\n[TEST] Step 4: Running go_to_rss_center_farm (press Ctrl+C to skip)...")
    print("-" * 50)

    try:
        # Go back first since we already navigated manually above
        core_actions.adb_helper.press_back(serial)
        time.sleep(2)
        core_actions.adb_helper.tap(serial, 50, 500)
        time.sleep(2)

        result = core_actions.go_to_rss_center_farm(serial, detector)
        print(f"\n[TEST] ✅ Result: {result}")
    except KeyboardInterrupt:
        print(f"\n[TEST] ⏭️ Skipped actual farming execution.")

    # --- Summary ---
    print(f"\n{'=' * 50}")
    print(f"[TEST] === SUMMARY ===")
    print(f"  BUILDING_TIME: '{building_time_text}' → {building_sec}s")
    print(f"  REMAINING_TIME: '{remaining_text}' → {remaining_sec}s")
    print(f"  BUILDER_COUNT: '{builder_text}'")
    print(f"  Debug screenshots saved to: {DEBUG_DIR}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    test_rss_center_farm("emulator-5556")
