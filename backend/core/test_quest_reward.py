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
DEBUG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_quest_reward")


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
# TEST 1: Full Quest Reward Workflow (end-to-end)
# ─────────────────────────────────────────────
def test_full_quest_reward(serial):
    """Run the full claim_quest_reward workflow and observe results."""
    print(f"\n[TEST] === Full Quest Reward Workflow on {serial} ===")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    print(f"\n[TEST] Running claim_quest_reward()...")
    print("-" * 50)

    try:
        result = core_actions.claim_quest_reward(serial, detector)
        print("-" * 50)
        ok = result.get("ok", False)
        print(f"[TEST] {'✅' if ok else '❌'} Result: {result}")
    except KeyboardInterrupt:
        print(f"\n[TEST] ⏭️ Aborted by user.")
    except Exception as e:
        print(f"\n[TEST] ❌ Exception: {e}")


# ─────────────────────────────────────────────
# TEST 2: Quest Menu Template Detection
# ─────────────────────────────────────────────
def test_quest_menu_detection(serial):
    """Test if QUEST_MENU template detects correctly.

    Steps:
    1. Navigate to IN_CITY
    2. Tap Events icon (35, 100)
    3. Check if QUEST_MENU is detected (should be YES)
    4. Close menu and check again (should be NO)
    """
    print(f"\n[TEST] === Quest Menu Detection Test on {serial} ===")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    # Step 1: Go to IN_CITY
    print(f"\n[TEST] Step 1: Navigating to IN_CITY...")
    lobby_result = core_actions.back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not core_actions._is_ok(lobby_result):
        print(f"[TEST] ❌ Could not reach IN_CITY. Aborting.")
        return

    # Step 2: Open Events menu
    print(f"\n[TEST] Step 2: Opening Events Menu (35, 100)...")
    adb_helper.tap(serial, 35, 100)
    time.sleep(3)

    # Step 3: Check detection — should find QUEST_MENU
    print(f"\n[TEST] Step 3: Detecting QUEST_MENU (expected: FOUND)...")
    save_frame(serial, detector, "quest_menu_open")
    detector._screen_cache = None
    result_open = detector.check_special_state(serial, target="QUEST_MENU")
    if result_open:
        print(f"[TEST] ✅ QUEST_MENU detected: {result_open}")
    else:
        print(f"[TEST] ❌ QUEST_MENU NOT detected — template may need updating")

    # Step 4: Close menu and check again — should NOT find it
    print(f"\n[TEST] Step 4: Closing menu, detecting again (expected: NOT FOUND)...")
    adb_helper.press_back(serial)
    time.sleep(3)
    save_frame(serial, detector, "quest_menu_closed")
    detector._screen_cache = None
    result_closed = detector.check_special_state(serial, target="QUEST_MENU")
    if not result_closed:
        print(f"[TEST] ✅ QUEST_MENU correctly NOT detected on lobby")
    else:
        print(f"[TEST] ❌ FALSE POSITIVE — QUEST_MENU detected on lobby! Threshold too low?")

    # Summary
    print(f"\n{'=' * 50}")
    print(f"[TEST] === SUMMARY ===")
    print(f"  Menu OPEN  → QUEST_MENU: {'✅ FOUND' if result_open else '❌ MISSING'}")
    print(f"  Menu CLOSED → QUEST_MENU: {'❌ FALSE POSITIVE' if result_closed else '✅ CORRECT (not found)'}")
    print(f"  Debug screenshots: {DEBUG_DIR}")
    print(f"{'=' * 50}")


# ─────────────────────────────────────────────
# TEST 3: Claim Button Detection
# ─────────────────────────────────────────────
def test_claim_btn_detection(serial):
    """Test if QUEST_CLAIM_BTN template detects on Quest screen.

    Steps:
    1. Navigate to IN_CITY → open Events → verify QUEST_MENU
    2. Tap Quest tab (80, 175)
    3. Use find_all_activity_matches to detect all Claim buttons
    """
    print(f"\n[TEST] === Claim Button Detection Test on {serial} ===")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    # Step 1: Navigate to Quest Menu
    print(f"\n[TEST] Step 1: Navigate to Quest Menu...")
    lobby_result = core_actions.back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not core_actions._is_ok(lobby_result):
        print(f"[TEST] ❌ Could not reach IN_CITY.")
        return

    adb_helper.tap(serial, 35, 100)
    time.sleep(3)

    detector._screen_cache = None
    if not detector.check_special_state(serial, target="QUEST_MENU"):
        print(f"[TEST] ❌ Could not verify QUEST_MENU. Aborting.")
        return

    # Step 2: Tap Quest tab
    print(f"\n[TEST] Step 2: Tapping Quest tab (80, 175)...")
    adb_helper.tap(serial, 80, 175)
    time.sleep(2)

    # Step 3: Detect Claim buttons
    print(f"\n[TEST] Step 3: Detecting QUEST_CLAIM_BTN...")
    save_frame(serial, detector, "quest_tab_claim_check")
    detector._screen_cache = None
    matches = detector.find_all_activity_matches(serial, target="QUEST_CLAIM_BTN", threshold=0.8)

    if matches:
        print(f"[TEST] ✅ Found {len(matches)} Claim button(s):")
        for i, (cx, cy) in enumerate(matches):
            print(f"  [{i+1}] at ({cx}, {cy})")
    else:
        print(f"[TEST] ⚠️ No Claim buttons found (quests may not be completed yet)")

    # Cleanup
    adb_helper.press_back(serial)
    time.sleep(2)

    # Summary
    print(f"\n{'=' * 50}")
    print(f"[TEST] === SUMMARY ===")
    print(f"  QUEST_CLAIM_BTN: {'✅ FOUND ' + str(len(matches)) + ' match(es)' if matches else '⚠️ NONE (expected if no quests completed)'}")
    print(f"  Debug screenshots: {DEBUG_DIR}")
    print(f"{'=' * 50}")


# ─────────────────────────────────────────────
# TEST 4: Tab Navigation
# ─────────────────────────────────────────────
def test_navigate_tabs(serial):
    """Navigate between all 3 Quest tabs and save debug frames.

    Steps:
    1. Open Quest Menu
    2. Tap each tab, save frame for visual inspection
    """
    print(f"\n[TEST] === Tab Navigation Test on {serial} ===")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    # Navigate to Quest Menu
    lobby_result = core_actions.back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not core_actions._is_ok(lobby_result):
        print(f"[TEST] ❌ Could not reach IN_CITY.")
        return

    adb_helper.tap(serial, 35, 100)
    time.sleep(3)

    TABS = {
        "quest": (80, 175),
        "challenges": (80, 265),
        "dark_chests": (80, 360),
    }

    for tab_name, (tx, ty) in TABS.items():
        print(f"\n[TEST] Tapping {tab_name} tab ({tx}, {ty})...")
        adb_helper.tap(serial, tx, ty)
        time.sleep(2)
        save_frame(serial, detector, f"tab_{tab_name}")
        print(f"[TEST] ✅ Saved frame for {tab_name}")

    # Cleanup
    adb_helper.press_back(serial)
    time.sleep(2)

    print(f"\n{'=' * 50}")
    print(f"[TEST] === SUMMARY ===")
    print(f"  All 3 tabs navigated and frames saved.")
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

    parser = argparse.ArgumentParser(description="Test claim_quest_reward workflow")
    parser.add_argument("test", choices=["full", "templates", "claim", "tabs", "all"],
                        help="Which test to run")
    parser.add_argument("--serial", default="emulator-5556", help="Emulator serial (default: emulator-5556)")
    args = parser.parse_args()

    if args.test == "full":
        test_full_quest_reward(args.serial)
    elif args.test == "templates":
        test_quest_menu_detection(args.serial)
    elif args.test == "claim":
        test_claim_btn_detection(args.serial)
    elif args.test == "tabs":
        test_navigate_tabs(args.serial)
    elif args.test == "all":
        test_quest_menu_detection(args.serial)
        test_claim_btn_detection(args.serial)
        test_navigate_tabs(args.serial)
        test_full_quest_reward(args.serial)
