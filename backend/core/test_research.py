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

# Debug output directory
DEBUG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_research")


def save_frame(serial, detector, label):
    """Save annotated frame for visual debug."""
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
# TEST 1: Full Research Workflow (end-to-end)
# ─────────────────────────────────────────────
def test_full_research(serial, research_type="default"):
    """Run the full research_technology workflow."""
    print(f"\n[TEST] === Full Research Workflow (type={research_type}) on {serial} ===")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    print(f"\n[TEST] Running research_technology(research_type='{research_type}')...")
    print("-" * 50)

    try:
        result = core_actions.research_technology(serial, detector, research_type=research_type)
        print("-" * 50)
        # research_technology returns bool (True = at least 1 slot researched)
        if isinstance(result, dict):
            ok = result.get("ok", False)
        else:
            ok = bool(result)
        print(f"[TEST] {'✅' if ok else '❌'} Result: {result}")
    except KeyboardInterrupt:
        print(f"\n[TEST] ⏭️ Aborted by user.")
    except Exception as e:
        print(f"\n[TEST] ❌ Exception: {e}")


# ─────────────────────────────────────────────
# TEST 2: Navigate to Research Center
# ─────────────────────────────────────────────
def test_navigate_research_center(serial):
    """Test if we can successfully navigate to Research Center and detect it."""
    print(f"\n[TEST] === Navigate to Research Center on {serial} ===")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    # Step 1: Navigate
    print(f"\n[TEST] Step 1: go_to_construction('RESEARCH_CENTER')...")
    result = core_actions.go_to_construction(serial, detector, "RESEARCH_CENTER")
    if not core_actions._is_ok(result):
        print(f"[TEST] ❌ Could not navigate to Research Center: {result}")
        return

    # Step 2: Verify state
    print(f"\n[TEST] Step 2: Verifying RESEARCH_CENTER state...")
    state = core_actions.wait_for_state(serial, detector, ["RESEARCH_CENTER"], timeout_sec=10, check_mode="construction")
    save_frame(serial, detector, "research_center")

    if state == "RESEARCH_CENTER":
        print(f"[TEST] ✅ RESEARCH_CENTER state confirmed!")
    else:
        print(f"[TEST] ❌ State mismatch: got '{state}'")

    # Cleanup
    adb_helper.press_back(serial)
    time.sleep(2)

    print(f"\n{'=' * 50}")
    print(f"[TEST] === SUMMARY ===")
    print(f"  Navigation: {'✅' if core_actions._is_ok(result) else '❌'}")
    print(f"  State Detection: {'✅ RESEARCH_CENTER' if state == 'RESEARCH_CENTER' else '❌ ' + str(state)}")
    print(f"  Debug screenshots: {DEBUG_DIR}")
    print(f"{'=' * 50}")


# ─────────────────────────────────────────────
# TEST 3: Template Detection Scan
# ─────────────────────────────────────────────
def test_template_detection(serial):
    """Navigate to Research Center and scan all research-related templates.
    
    Checks: RESEARCH_EMPTY_SLOT, RESEARCH_CONFIRM, RESEARCH_ALLIANCE_HELP,
            RESEARCH_ECONOMY_TECH, RESEARCH_MILITARY_TECH
    """
    print(f"\n[TEST] === Research Template Detection Test on {serial} ===")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    # Navigate to Research Center
    print(f"\n[TEST] Step 1: Navigating to Research Center...")
    result = core_actions.go_to_construction(serial, detector, "RESEARCH_CENTER")
    if not core_actions._is_ok(result):
        print(f"[TEST] ❌ Could not navigate to Research Center.")
        return

    state = core_actions.wait_for_state(serial, detector, ["RESEARCH_CENTER"], timeout_sec=10, check_mode="construction")
    if state != "RESEARCH_CENTER":
        print(f"[TEST] ❌ Did not reach RESEARCH_CENTER. Got: {state}")
        return

    # Dismiss auto-popup
    print(f"[TEST] Dismissing auto-popup (415, 520)...")
    adb_helper.tap(serial, 415, 520)
    time.sleep(2)

    save_frame(serial, detector, "research_main_view")

    # Scan all templates
    TEMPLATES_TO_CHECK = [
        "RESEARCH_EMPTY_SLOT",
        "RESEARCH_ALLIANCE_HELP",
        "RESEARCH_ECONOMY_TECH",
        "RESEARCH_MILITARY_TECH",
        "RESEARCH_CONFIRM",
        "RESEARCH_USE_BAG",
    ]

    print(f"\n[TEST] Step 2: Scanning templates on Research Center screen...")
    print("-" * 50)

    results = {}
    for tpl_name in TEMPLATES_TO_CHECK:
        detector._screen_cache = None
        match = detector.check_activity(serial, target=tpl_name, threshold=0.8)
        if match:
            results[tpl_name] = f"✅ FOUND at ({match[1]}, {match[2]})"
            print(f"[TEST]   {tpl_name}: ✅ at ({match[1]}, {match[2]})")
        else:
            results[tpl_name] = "❌ NOT FOUND"
            print(f"[TEST]   {tpl_name}: ❌ not detected")

    # Also check special states
    SPECIAL_TO_CHECK = ["RESEARCH_NO_RESOURCE", "RESEARCH_NO_CONFIRM"]
    for sp_name in SPECIAL_TO_CHECK:
        detector._screen_cache = None
        match = detector.check_special_state(serial, target=sp_name)
        if match:
            results[sp_name] = "✅ FOUND (special)"
            print(f"[TEST]   {sp_name}: ✅ detected (special)")
        else:
            results[sp_name] = "❌ NOT FOUND (special)"
            print(f"[TEST]   {sp_name}: ❌ not detected (special)")

    # Cleanup
    adb_helper.press_back(serial)
    time.sleep(2)

    # Summary
    print(f"\n{'=' * 50}")
    print(f"[TEST] === TEMPLATE DETECTION SUMMARY ===")
    for name, status in results.items():
        print(f"  {name}: {status}")
    print(f"  Debug screenshots: {DEBUG_DIR}")
    print(f"{'=' * 50}")


# ─────────────────────────────────────────────
# TEST 4: Tab Selection Verification
# ─────────────────────────────────────────────
def test_tab_selection(serial):
    """Verify that economy/military tab tapping correctly switches tabs.
    
    Checks if RESEARCH_ECONOMY_TECH and RESEARCH_MILITARY_TECH templates
    detect the correct active tab after tapping.
    """
    print(f"\n[TEST] === Tab Selection Test on {serial} ===")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    ECONOMY_TAP = (30, 190)
    MILITARY_TAP = (30, 320)

    # Navigate
    result = core_actions.go_to_construction(serial, detector, "RESEARCH_CENTER")
    if not core_actions._is_ok(result):
        print(f"[TEST] ❌ Could not navigate to Research Center.")
        return

    state = core_actions.wait_for_state(serial, detector, ["RESEARCH_CENTER"], timeout_sec=10, check_mode="construction")
    if state != "RESEARCH_CENTER":
        print(f"[TEST] ❌ Did not reach RESEARCH_CENTER.")
        return

    adb_helper.tap(serial, 415, 520)
    time.sleep(2)

    # Test Economy tab
    print(f"\n[TEST] Step 1: Tapping Economy tab {ECONOMY_TAP}...")
    adb_helper.tap(serial, ECONOMY_TAP[0], ECONOMY_TAP[1])
    time.sleep(2)
    save_frame(serial, detector, "tab_economy")
    detector._screen_cache = None
    eco_match = detector.check_activity(serial, target="RESEARCH_ECONOMY_TECH", threshold=0.8)
    eco_ok = eco_match is not None
    print(f"[TEST]   RESEARCH_ECONOMY_TECH: {'✅ FOUND' if eco_ok else '❌ NOT FOUND'}")

    # Test Military tab
    print(f"\n[TEST] Step 2: Tapping Military tab {MILITARY_TAP}...")
    adb_helper.tap(serial, MILITARY_TAP[0], MILITARY_TAP[1])
    time.sleep(2)
    save_frame(serial, detector, "tab_military")
    detector._screen_cache = None
    mil_match = detector.check_activity(serial, target="RESEARCH_MILITARY_TECH", threshold=0.8)
    mil_ok = mil_match is not None
    print(f"[TEST]   RESEARCH_MILITARY_TECH: {'✅ FOUND' if mil_ok else '❌ NOT FOUND'}")

    # Cleanup
    adb_helper.press_back(serial)
    time.sleep(2)

    # Summary
    print(f"\n{'=' * 50}")
    print(f"[TEST] === TAB SELECTION SUMMARY ===")
    print(f"  Economy tab detect:  {'✅' if eco_ok else '❌'}")
    print(f"  Military tab detect: {'✅' if mil_ok else '❌'}")
    print(f"  Debug screenshots: {DEBUG_DIR}")
    print(f"{'=' * 50}")


# ─────────────────────────────────────────────
# TEST 5: Empty Slot Detection
# ─────────────────────────────────────────────
def test_empty_slot(serial):
    """Navigate to Research Center and check if any empty research slots exist."""
    print(f"\n[TEST] === Empty Slot Detection Test on {serial} ===")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    result = core_actions.go_to_construction(serial, detector, "RESEARCH_CENTER")
    if not core_actions._is_ok(result):
        print(f"[TEST] ❌ Could not navigate to Research Center.")
        return

    state = core_actions.wait_for_state(serial, detector, ["RESEARCH_CENTER"], timeout_sec=10, check_mode="construction")
    if state != "RESEARCH_CENTER":
        print(f"[TEST] ❌ Did not reach RESEARCH_CENTER.")
        return

    adb_helper.tap(serial, 415, 520)
    time.sleep(2)

    save_frame(serial, detector, "slot_check")
    detector._screen_cache = None
    slot_match = detector.check_activity(serial, target="RESEARCH_EMPTY_SLOT", threshold=0.8)

    if slot_match:
        print(f"[TEST] ✅ Empty slot found at ({slot_match[1]}, {slot_match[2]})")
        print(f"[TEST] → Workflow will attempt to research in this slot.")
    else:
        print(f"[TEST] ❌ No empty slot found.")
        print(f"[TEST] → All slots are occupied or research is in progress.")

    # Cleanup
    adb_helper.press_back(serial)
    time.sleep(2)

    print(f"\n{'=' * 50}")
    print(f"[TEST] === SUMMARY ===")
    print(f"  Empty Slot: {'✅ FOUND at (' + str(slot_match[1]) + ', ' + str(slot_match[2]) + ')' if slot_match else '❌ NONE'}")
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

    parser = argparse.ArgumentParser(description="Test research_technology workflow")
    parser.add_argument("test", choices=["full", "nav", "templates", "tabs", "slots", "all"],
                        help="Which test to run")
    parser.add_argument("--serial", default="emulator-5556", help="Emulator serial (default: emulator-5556)")
    parser.add_argument("--type", default="default", choices=["default", "economy", "military", "balance"],
                        dest="research_type", help="Research type (default: default)")
    args = parser.parse_args()

    if args.test == "full":
        test_full_research(args.serial, args.research_type)
    elif args.test == "nav":
        test_navigate_research_center(args.serial)
    elif args.test == "templates":
        test_template_detection(args.serial)
    elif args.test == "tabs":
        test_tab_selection(args.serial)
    elif args.test == "slots":
        test_empty_slot(args.serial)
    elif args.test == "all":
        test_navigate_research_center(args.serial)
        test_template_detection(args.serial)
        test_tab_selection(args.serial)
        test_empty_slot(args.serial)
        test_full_research(args.serial, args.research_type)
