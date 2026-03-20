"""
Test GO button detection — captures screenshot, runs detection,
draws red circle on match location, saves debug image.

Usage:
    python backend\core\test_go_detection.py
    python backend\core\test_go_detection.py 4   (emulator index)

IMPORTANT: Navigate the game to a policy popup with GO button BEFORE running!
"""
import os
import sys
import time

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(root_dir)
ui_manager_dir = os.path.abspath(os.path.join(root_dir, "..", "UI_MANAGER"))
if ui_manager_dir not in sys.path:
    sys.path.append(ui_manager_dir)

from backend.config import config
config.load()

import cv2
import numpy as np
from backend.core.workflow.state_detector import GameStateDetector
from backend.core.workflow import adb_helper


def test_go_detection(emulator_index=4):
    serial = f"emulator-{5554 + emulator_index * 2}"
    print(f"\n[TEST] GO Button Detection Test on {serial}")
    print("=" * 60)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    # Capture screenshot
    print(f"\n[1] Capturing screenshot...")
    screen = detector.get_frame(serial)
    if screen is None:
        print("[FAIL] Could not capture screenshot!")
        return

    h, w = screen.shape[:2]
    print(f"    Screen size: {w}x{h}")

    # Load GO template
    tmpl_path = os.path.join(templates_dir, "policy", "go_btn.png")
    tmpl = cv2.imread(tmpl_path, cv2.IMREAD_COLOR)
    if tmpl is None:
        print(f"[FAIL] Could not load template: {tmpl_path}")
        return

    th, tw = tmpl.shape[:2]
    print(f"    Template size: {tw}x{th}")

    debug_img = screen.copy()
    output_dir = os.path.join(current_dir, "workflow", "debug_policy")
    os.makedirs(output_dir, exist_ok=True)

    # ── Test 1: Grayscale matching (old method) ──
    print(f"\n[2] GRAYSCALE matching (full screen)...")
    screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
    tmpl_gray = cv2.cvtColor(tmpl, cv2.COLOR_BGR2GRAY)

    result_gray = cv2.matchTemplate(screen_gray, tmpl_gray, cv2.TM_CCOEFF_NORMED)
    _, max_val_g, _, max_loc_g = cv2.minMaxLoc(result_gray)
    cx_g = max_loc_g[0] + tw // 2
    cy_g = max_loc_g[1] + th // 2
    print(f"    Confidence: {max_val_g:.4f}")
    print(f"    Match top-left: {max_loc_g}")
    print(f"    Tap center: ({cx_g}, {cy_g})")

    # Draw BLUE circle for grayscale match
    cv2.circle(debug_img, (cx_g, cy_g), 25, (255, 0, 0), 2)  # Blue
    cv2.putText(debug_img, f"GRAY {max_val_g:.3f}", (cx_g + 30, cy_g),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

    # ── Test 2: COLOR matching (new method) ──
    print(f"\n[3] COLOR matching (full screen)...")
    result_color = cv2.matchTemplate(screen, tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val_c, _, max_loc_c = cv2.minMaxLoc(result_color)
    cx_c = max_loc_c[0] + tw // 2
    cy_c = max_loc_c[1] + th // 2
    print(f"    Confidence: {max_val_c:.4f}")
    print(f"    Match top-left: {max_loc_c}")
    print(f"    Tap center: ({cx_c}, {cy_c})")

    # Draw GREEN circle for color match
    cv2.circle(debug_img, (cx_c, cy_c), 25, (0, 255, 0), 2)  # Green
    cv2.putText(debug_img, f"COLOR {max_val_c:.3f}", (cx_c + 30, cy_c),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    # ── Test 3: COLOR matching with ROI ──
    ROI = (200, 150, 760, 500)
    print(f"\n[4] COLOR matching with ROI {ROI}...")
    region = screen[ROI[1]:ROI[3], ROI[0]:ROI[2]]
    result_roi = cv2.matchTemplate(region, tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val_r, _, max_loc_r = cv2.minMaxLoc(result_roi)
    cx_r = ROI[0] + max_loc_r[0] + tw // 2
    cy_r = ROI[1] + max_loc_r[1] + th // 2
    print(f"    Confidence: {max_val_r:.4f}")
    print(f"    Match top-left (abs): ({ROI[0] + max_loc_r[0]}, {ROI[1] + max_loc_r[1]})")
    print(f"    Tap center: ({cx_r}, {cy_r})")

    # Draw RED circle for ROI color match (this is what we'd tap)
    cv2.circle(debug_img, (cx_r, cy_r), 25, (0, 0, 255), 2)  # Red
    cv2.putText(debug_img, f"ROI-COLOR {max_val_r:.3f}", (cx_r + 30, cy_r),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    # Draw ROI rectangle
    cv2.rectangle(debug_img, (ROI[0], ROI[1]), (ROI[2], ROI[3]), (0, 255, 255), 1)

    # ── Test 4: check_activity (current detector method) ──
    print(f"\n[5] check_activity (detector grayscale pipeline)...")
    match_detector = detector.check_activity(serial, target="POLICY_GO_BTN", threshold=0.70)
    if match_detector:
        _, dx, dy = match_detector
        print(f"    Found at: ({dx}, {dy})")
        cv2.circle(debug_img, (dx, dy), 25, (255, 0, 255), 2)  # Magenta
        cv2.putText(debug_img, f"DETECTOR", (dx + 30, dy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
    else:
        print(f"    Not found (threshold 0.70)")

    # ── Save debug image ──
    ts = time.strftime("%H%M%S")
    debug_path = os.path.join(output_dir, f"go_test_{ts}.png")
    cv2.imwrite(debug_path, debug_img)
    print(f"\n{'=' * 60}")
    print(f"[SAVED] Debug image: {debug_path}")
    print(f"  BLUE circle   = Grayscale match")
    print(f"  GREEN circle  = Color match (full screen)")
    print(f"  RED circle    = Color match (ROI)")
    print(f"  MAGENTA circle = check_activity detector")
    print(f"  YELLOW rect   = ROI search area")

    # Also save raw screenshot
    raw_path = os.path.join(output_dir, f"go_raw_{ts}.png")
    cv2.imwrite(raw_path, screen)
    print(f"[SAVED] Raw screenshot: {raw_path}")


if __name__ == "__main__":
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    import argparse
    parser = argparse.ArgumentParser(description="Test GO button detection")
    parser.add_argument("emulator_index", type=int, nargs="?", default=4)
    args = parser.parse_args()
    test_go_detection(args.emulator_index)
