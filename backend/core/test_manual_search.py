import os
import sys
import time
import subprocess
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

DEBUG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_manual_search")


def save_frame(serial, detector, label):
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


def _serial_to_index(serial):
    """Convert emulator serial to LDPlayer index. emulator-5574 → index 10."""
    port = int(serial.split("-")[1])
    return (port - 5554) // 2


def ldplayer_zoom_out(serial, count=1):
    ld_path = os.path.join(os.path.dirname(config.adb_path), "ldconsole.exe")
    index = _serial_to_index(serial)
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    for i in range(count):
        subprocess.run(
            [ld_path, "zoomOut", "--index", str(index)],
            capture_output=True, text=True, startupinfo=si, timeout=5
        )
        time.sleep(0.5)
    print(f"[ZOOM] zoomOut x{count} done")


def ldplayer_zoom_in(serial, count=1):
    ld_path = os.path.join(os.path.dirname(config.adb_path), "ldconsole.exe")
    index = _serial_to_index(serial)
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    for i in range(count):
        subprocess.run(
            [ld_path, "zoomIn", "--index", str(index)],
            capture_output=True, text=True, startupinfo=si, timeout=5
        )
        time.sleep(0.5)
    print(f"[ZOOM] zoomIn x{count} done")


def test_zoom_and_swipe(serial, resource_type="gold"):
    """Test zoom out to level 3 then random swipe map to scan area."""
    print(f"\n[TEST] === Zoom 3 + Random Swipe Scan ({resource_type.upper()}) on {serial} ===")

    import random

    detector = _make_detector()

    RESOURCE_TAPS = {
        "gold": (320, 485), "wood": (475, 485),
        "stone": (640, 485), "mana": (795, 485),
    }
    SEARCH_TAPS = {
        "gold": (320, 400), "wood": (475, 400),
        "stone": (640, 400), "mana": (795, 400),
    }

    r_type = resource_type.lower()

    # Step 1: Navigate to OUT_CITY
    print(f"\n[TEST] Step 1: Navigating to OUT_CITY...")
    lobby_result = core_actions.back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)")
    if not core_actions._is_ok(lobby_result):
        print(f"[TEST] FAIL - Could not reach OUT_CITY.")
        return

    # Step 2: Search mine to pan camera to mine area
    print(f"\n[TEST] Step 2: Searching for {r_type.upper()} mine...")
    adb_helper.tap(serial, 42, 422)
    time.sleep(2)
    res_x, res_y = RESOURCE_TAPS[r_type]
    adb_helper.tap(serial, res_x, res_y)
    time.sleep(1)
    search_x, search_y = SEARCH_TAPS[r_type]
    adb_helper.tap(serial, search_x, search_y)
    time.sleep(4)

    detector._screen_cache = None
    if detector.check_activity(serial, target="FARM_SEARCH_BTN", threshold=0.8):
        print(f"[TEST] FAIL - No mine found.")
        adb_helper.press_back(serial)
        return

    print(f"[TEST] Mine found!")
    save_frame(serial, detector, "00_baseline_zoom0")

    # Step 3: Zoom to consistent level
    # Strategy: zoom out to MAX first, then zoom in 1 step → guaranteed same level every time
    print(f"\n[TEST] Step 3: Zooming to consistent level (max out → in 1)...")
    ldplayer_zoom_out(serial, count=10)  # Hit max zoom
    time.sleep(2)
    save_frame(serial, detector, "01_zoom_max")
    ldplayer_zoom_in(serial, count=1)    # Back up 1 step from max
    time.sleep(2)
    save_frame(serial, detector, "02_zoom_target")

    # Step 4: Random swipes at zoom 3
    # Safe swipe zone: avoid top bar (y<50) and bottom bar (y>490)
    print(f"\n[TEST] Step 4: Random swipes at zoom 3...")
    for i in range(1, 7):
        # Random start and end points within safe zone
        x1 = random.randint(100, 860)
        y1 = random.randint(80, 460)
        x2 = random.randint(100, 860)
        y2 = random.randint(80, 460)

        # Ensure minimum swipe distance (at least 200px)
        while abs(x2 - x1) + abs(y2 - y1) < 200:
            x2 = random.randint(100, 860)
            y2 = random.randint(80, 460)

        duration = random.randint(400, 800)
        print(f"[TEST] Swipe #{i}: ({x1},{y1}) → ({x2},{y2}) dur={duration}ms")
        adb_helper.swipe(serial, x1, y1, x2, y2, duration)
        time.sleep(random.uniform(1.5, 3.0))
        save_frame(serial, detector, f"02_random_swipe_{i}")

    print(f"\n{'=' * 60}")
    print(f"[TEST] === SUMMARY ===")
    print(f"  Screenshots: {DEBUG_DIR}")
    print(f"  00_ = baseline (no zoom)")
    print(f"  01_ = zoom level 3 (center)")
    print(f"  02_ = random swipes at zoom 3")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    import argparse

    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(description="Test zoom + swipe for manual mine search")
    parser.add_argument("--serial", default="emulator-5556", help="Emulator serial")
    parser.add_argument("--resource", default="gold", choices=["gold", "wood", "stone", "mana"])
    args = parser.parse_args()

    test_zoom_and_swipe(args.serial, args.resource)
