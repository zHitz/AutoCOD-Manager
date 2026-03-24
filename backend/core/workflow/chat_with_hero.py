import os
import time
from typing import Optional

import cv2

from backend.config import config
from backend.core.workflow import adb_helper, core_actions
from backend.core.workflow.state_detector import GameStateDetector

APP_PACKAGE = core_actions.get_package_for_provider()
HERO_TEMPLATE_NAMES = ["hero_chat_1.png", "hero_chat_2.png", "hero_chat_3.png"]
MATCH_THRESHOLD = 0.82
CHAT_BUTTON_Y_OFFSET = 100
SKIP_BUTTON = (910, 30)
YES_BUTTON = (377, 340)
POST_TAP_DELAY_SEC = 1.5
BACK_DELAY_SEC = 1.5

# (x, y, x1, y1) bounding box for hero detection to avoid UI borders
SCAN_ROI = (100, 120, 900, 360)

# Viewport scan order based on a 9-key keypad:
# 5 (center) -> 2 -> 3 -> 6 -> 9 -> 8 -> 7 -> 4 -> 1
SCAN_ORDER = ["5", "2", "3", "6", "9", "8", "7", "4", "1"]
KEYPAD_POSITIONS = {
    "1": (-1, -1),
    "2": (0, -1),
    "3": (1, -1),
    "4": (-1, 0),
    "5": (0, 0),
    "6": (1, 0),
    "7": (-1, 1),
    "8": (0, 1),
    "9": (1, 1),
}

# Finger drag starts near screen center. The resulting viewport moves in the
# opposite direction, which lets us scan around the city from the original center.
SWIPE_CENTER = (480, 270)
PAN_STEP_X = 400
PAN_STEP_Y = 250
SWIPE_DURATION_MS = 500
SCAN_SETTLE_SEC = 2.0


def _get_hero_template_paths() -> list:
    """Resolve hero template paths relative to the templates directory."""
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "icon_markers")
    return [os.path.join(templates_dir, name) for name in HERO_TEMPLATE_NAMES]


def load_template(template_path: str):
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if template is None:
        print(f"[TEMPLATE] [FAILED] Could not load template: {template_path}")
        return None
    return template


def locate_template(
    serial: str, 
    detector: GameStateDetector, 
    template, 
    threshold: float = MATCH_THRESHOLD,
    roi: Optional[tuple] = None
):
    screen = detector.screencap_memory(serial)
    if screen is None:
        print(f"[{serial}] [FAILED] Could not capture screen for template matching.")
        return None

    offset_x, offset_y = 0, 0
    if roi:
        x, y, x1, y1 = roi
        screen = screen[y:y1, x:x1]
        offset_x, offset_y = x, y

    screen_h, screen_w = screen.shape[:2]
    template_h, template_w = template.shape[:2]
    if template_h > screen_h or template_w > screen_w:
        print(f"[{serial}] [FAILED] Template is larger than search area.")
        return None

    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    if max_val < threshold:
        return None

    center_x = offset_x + max_loc[0] + (template_w // 2)
    center_y = offset_y + max_loc[1] + (template_h // 2)
    print(f"[{serial}] Template found at ({center_x}, {center_y}) | conf: {max_val:.3f}")
    return center_x, center_y, max_val


def pan_viewport(serial: str, from_key: str, to_key: str) -> None:
    from_x, from_y = KEYPAD_POSITIONS[from_key]
    to_x, to_y = KEYPAD_POSITIONS[to_key]

    delta_x = to_x - from_x
    delta_y = to_y - from_y

    start_x, start_y = SWIPE_CENTER
    end_x = start_x - (delta_x * PAN_STEP_X)
    end_y = start_y - (delta_y * PAN_STEP_Y)

    print(
        f"[{serial}] Panning viewport {from_key} -> {to_key} "
        f"with swipe ({start_x}, {start_y}) -> ({end_x}, {end_y})"
    )
    adb_helper.swipe(serial, start_x, start_y, end_x, end_y, duration=SWIPE_DURATION_MS)
    time.sleep(SCAN_SETTLE_SEC)


def handle_chat_flow(serial: str, detector: GameStateDetector, hero_x: int, hero_y: int) -> None:
    chat_x = hero_x
    chat_y = hero_y + CHAT_BUTTON_Y_OFFSET

    print(f"[{serial}] Tapping chat button at ({chat_x}, {chat_y})...")
    adb_helper.tap(serial, chat_x, chat_y)
    time.sleep(POST_TAP_DELAY_SEC)

    special_state = detector.check_special_state(serial, target="SKIP")
    print(f"[{serial}] Special state after chat tap: {special_state}")
    if special_state == "SKIP":
        print(f"[{serial}] SKIP detected. Tapping skip at {SKIP_BUTTON}...")
        adb_helper.tap(serial, SKIP_BUTTON[0], SKIP_BUTTON[1])
        time.sleep(POST_TAP_DELAY_SEC)

        print(f"[{serial}] Tapping yes at {YES_BUTTON}...")
        adb_helper.tap(serial, YES_BUTTON[0], YES_BUTTON[1])
        time.sleep(POST_TAP_DELAY_SEC)

    print(f"[{serial}] Returning with BACK...")
    adb_helper.press_back(serial)
    time.sleep(BACK_DELAY_SEC)


def process_visible_heroes(serial: str, detector: GameStateDetector, templates: list, max_retries: int = 3) -> int:
    total_handled = 0

    for attempt in range(max_retries):
        if attempt > 0:
            print(f"[{serial}] Viewport scan retry {attempt + 1}/{max_retries}...")
        
        handled_this_attempt = 0
        found_any = True
        
        while found_any:
            found_any = False
            for template in templates:
                match = locate_template(serial, detector, template, roi=SCAN_ROI)
                if match:
                    hero_x, hero_y, _ = match
                    print(f"[{serial}] Hero chat target detected at ({hero_x}, {hero_y}). Tapping hero...")
                    adb_helper.tap(serial, hero_x, hero_y)
                    time.sleep(POST_TAP_DELAY_SEC)

                    handle_chat_flow(serial, detector, hero_x, hero_y)
                    handled_this_attempt += 1
                    total_handled += 1
                    found_any = True
                    time.sleep(POST_TAP_DELAY_SEC)
                    break

        if handled_this_attempt == 0 and attempt < max_retries - 1:
            time.sleep(1.0)
        elif handled_this_attempt > 0 and attempt < max_retries - 1:
            time.sleep(0.5)

    print(f"[{serial}] Total hero chats handled on current viewport after {max_retries} attempts: {total_handled}")
    return total_handled


def run_chat_with_hero(serial: str, detector: GameStateDetector) -> bool:
    """
    Entry point called by executor.py.
    Runs one clockwise viewport scan around IN_CITY and chats with all visible heroes.
    Returns True if at least one hero was chatted with, or if the scan completed without errors.
    """
    print(f"\n[WORKFLOW] CHAT_WITH_HERO on {serial}\n")

    template_paths = _get_hero_template_paths()
    templates = []
    for path in template_paths:
        t = load_template(path)
        if t is not None:
            templates.append(t)
    
    if not templates:
        print(f"[{serial}] [WARNING] No hero chat templates found. Skipping.")
        return True  # Graceful skip

    if not core_actions.back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)"):
        print(f"[{serial}] [FAILED] Could not reach IN_CITY lobby.")
        return False

    total_handled = 0
    current_key = SCAN_ORDER[0]

    print(f"[{serial}] Scanning viewport {current_key} (center)...")
    total_handled += process_visible_heroes(serial, detector, templates)

    for next_key in SCAN_ORDER[1:]:
        pan_viewport(serial, current_key, next_key)
        current_key = next_key

        print(f"[{serial}] Scanning viewport {current_key}...")
        total_handled += process_visible_heroes(serial, detector, templates)

    print(f"[{serial}] Finished one clockwise round. Total hero chats handled: {total_handled}")
    return True
