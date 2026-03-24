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
DEBUG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_go_to_construction")

AVAILABLE_V2 = list(CONSTRUCTION_DATA.keys())


def _init_detector():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")
    return GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)


def save_frame(serial, detector, label):
    """Save annotated frame for visual debugging."""
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
# TEST 1: Full V2 go_to_construction (with timing)
# ─────────────────────────────────────────────
def test_full_v2(serial, building="HALL", feature="info"):
    """Run go_to_construction V2 with per-step timing measurement."""
    print(f"\n[TEST] === Full go_to_construction V2 ({building} -> {feature}) on {serial} ===")

    detector = _init_detector()

    print(f"\n[TEST] Running go_to_construction('{building}', feature='{feature}')...")
    print("-" * 60)

    try:
        t_start = time.time()
        result = core_actions.go_to_construction(serial, detector, building, feature=feature)
        t_total = time.time() - t_start

        print("-" * 60)
        ok = result.get("ok", False)
        print(f"[TEST] {'✅' if ok else '❌'} Result: {result}")
        print(f"[TEST] ⏱️  Total time: {t_total:.2f}s")

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
# TEST 2: Timing Breakdown — step-by-step
# ─────────────────────────────────────────────
def test_timing_breakdown(serial, building="HALL", feature="info"):
    """Manually run each V2 step with timing to find bottlenecks.

    Measures:
      T1: back_to_lobby → IN_CITY
      T2: check_state verification
      T3: tap base + wait
      T4: template detection (feature button)
      T5: tap feature + wait
      T6: verify construction screen
    """
    print(f"\n[TEST] === Timing Breakdown ({building} -> {feature}) on {serial} ===")

    detector = _init_detector()

    if building not in CONSTRUCTION_DATA:
        print(f"[TEST] ❌ '{building}' not in CONSTRUCTION_DATA.")
        return
    data = CONSTRUCTION_DATA[building]
    feat_lower = feature.lower()
    if feat_lower not in data["features"]:
        print(f"[TEST] ❌ '{feature}' not in {building} features.")
        return
    feat_config = data["features"][feat_lower]

    timings = {}
    t_workflow = time.time()

    # ── T1: Navigate to IN_CITY ──
    t0 = time.time()
    lobby_result = core_actions.back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    timings["T1_back_to_lobby"] = time.time() - t0
    if not core_actions._is_ok(lobby_result):
        print(f"[TEST] ❌ Could not reach IN_CITY. Aborting.")
        _print_timings(timings)
        return

    # ── T2: check_state verify ──
    t0 = time.time()
    state = detector.check_state(serial)
    timings["T2_check_state"] = time.time() - t0
    print(f"[TEST] State: {state}")
    if state != "IN-GAME LOBBY (IN_CITY)":
        print(f"[TEST] ❌ Not IN_CITY. Aborting.")
        _print_timings(timings)
        return

    # ── T3: Tap base ──
    base_x, base_y = data["base"]
    t0 = time.time()
    adb_helper.tap(serial, base_x, base_y)
    timings["T3_tap_base_cmd"] = time.time() - t0

    # Wait for popup
    t0 = time.time()
    time.sleep(1.2)
    timings["T3_tap_base_wait"] = time.time() - t0

    save_frame(serial, detector, f"after_base_tap_{building.lower()}")

    # ── T4: Detect feature template ──
    template_name = feat_config.get("template", "CONSTRUCTION_INFO_BTN")

    # T4a: Fast detect (single shot)
    t0 = time.time()
    detector._screen_cache = None
    match = detector.check_activity(serial, target=template_name, threshold=0.8)
    timings["T4a_fast_detect"] = time.time() - t0

    if match:
        print(f"[TEST] ✅ Fast detect hit: {template_name} at ({match[1]}, {match[2]})")
    else:
        print(f"[TEST] ⚠️ Fast detect miss. Running slow path...")

        # T4b: Slow detect retry
        t0 = time.time()
        time.sleep(0.8)
        timings["T4b_slow_wait"] = time.time() - t0

        t0 = time.time()
        match = core_actions._detect_with_retry(
            serial, detector, template_name, threshold=0.8, attempts=2, delay=1.0
        )
        timings["T4c_slow_detect"] = time.time() - t0

        if match:
            print(f"[TEST] ✅ Slow detect hit: {template_name} at ({match[1]}, {match[2]})")
        else:
            print(f"[TEST] ❌ Detection failed. Checking fallback...")
            fallback = feat_config.get("fallback")
            if fallback:
                print(f"[TEST] ⚠️ Would use fallback coords ({fallback['x']}, {fallback['y']})")
            else:
                print(f"[TEST] ❌ No fallback configured.")
            _print_timings(timings)
            adb_helper.press_back(serial)
            return

    # ── T5: Tap feature ──
    _, mx, my = match
    t0 = time.time()
    adb_helper.tap(serial, mx, my)
    timings["T5_tap_feature_cmd"] = time.time() - t0

    t0 = time.time()
    time.sleep(1.2)
    timings["T5_tap_feature_wait"] = time.time() - t0

    save_frame(serial, detector, f"after_feature_tap_{building.lower()}_{feature}")

    # ── T6: Verify construction ──
    verify_name = feat_config.get("verify", data["verify"])
    for attempt in range(3):
        t0 = time.time()
        detector._screen_cache = None
        result = detector.check_construction(serial, target=verify_name)
        detect_time = time.time() - t0
        timings[f"T6_verify_attempt_{attempt+1}"] = detect_time

        if result:
            print(f"[TEST] ✅ Verify hit: {verify_name} (attempt {attempt+1}, {detect_time:.3f}s)")
            break
        else:
            print(f"[TEST] ⚠️ Verify miss attempt {attempt+1} ({detect_time:.3f}s)")
            if attempt < 2:
                time.sleep(1.0)

    timings["T_TOTAL"] = time.time() - t_workflow

    # ── Summary ──
    _print_timings(timings)

    # Cleanup
    adb_helper.press_back(serial)
    time.sleep(1)


# ─────────────────────────────────────────────
# TEST 3: Detection Speed Benchmark
# ─────────────────────────────────────────────
def test_detection_speed(serial, building="HALL"):
    """Benchmark template detection speed.

    Taps the base building, then measures how fast each template is detected.
    Runs detection 5 times in a row to find avg/min/max detection time.
    """
    print(f"\n[TEST] === Detection Speed Benchmark ({building}) on {serial} ===")

    detector = _init_detector()

    if building not in CONSTRUCTION_DATA:
        print(f"[TEST] ❌ '{building}' not in CONSTRUCTION_DATA.")
        return

    data = CONSTRUCTION_DATA[building]

    # Navigate to IN_CITY
    lobby_result = core_actions.back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not core_actions._is_ok(lobby_result):
        print(f"[TEST] ❌ Could not reach IN_CITY.")
        return

    # Tap base to show popup
    base_x, base_y = data["base"]
    adb_helper.tap(serial, base_x, base_y)
    time.sleep(2)
    save_frame(serial, detector, f"benchmark_{building.lower()}_popup")

    # Benchmark each feature template
    for feat_name, feat_cfg in data["features"].items():
        template_name = feat_cfg.get("template")
        if not template_name:
            continue

        print(f"\n[TEST] --- {feat_name}: {template_name} ---")
        detect_times = []

        for i in range(5):
            detector._screen_cache = None
            t0 = time.time()
            match = detector.check_activity(serial, target=template_name, threshold=0.8)
            dt = time.time() - t0
            detect_times.append(dt)
            status = f"({match[1]},{match[2]})" if match else "MISS"
            print(f"  Run {i+1}: {dt*1000:.1f}ms — {status}")

        avg = sum(detect_times) / len(detect_times)
        mn = min(detect_times)
        mx = max(detect_times)
        print(f"  Avg: {avg*1000:.1f}ms | Min: {mn*1000:.1f}ms | Max: {mx*1000:.1f}ms")

    # Benchmark screencap alone
    print(f"\n[TEST] --- Screencap Only (no matching) ---")
    cap_times = []
    for i in range(5):
        detector._screen_cache = None
        t0 = time.time()
        _ = detector.screencap_memory(serial)
        dt = time.time() - t0
        cap_times.append(dt)
        print(f"  Run {i+1}: {dt*1000:.1f}ms")
    avg = sum(cap_times) / len(cap_times)
    print(f"  Avg: {avg*1000:.1f}ms | Min: {min(cap_times)*1000:.1f}ms | Max: {max(cap_times)*1000:.1f}ms")

    # Cleanup
    adb_helper.press_back(serial)
    time.sleep(1)


# ─────────────────────────────────────────────
# TEST 4: All Buildings V2 Sweep (with timing)
# ─────────────────────────────────────────────
def test_sweep_v2(serial, feature="info"):
    """Run go_to_construction V2 for every building and report per-building timing."""
    print(f"\n[TEST] === V2 Sweep (feature={feature}) on {serial} ===")
    print(f"[TEST] Buildings: {AVAILABLE_V2}")

    detector = _init_detector()
    results = {}

    for building in AVAILABLE_V2:
        if feature not in CONSTRUCTION_DATA[building]["features"]:
            results[building] = "⏭️ SKIP (no feature)"
            continue

        print(f"\n{'─' * 50}")
        print(f"[TEST] Testing: {building} -> {feature}")
        print(f"{'─' * 50}")

        try:
            t0 = time.time()
            result = core_actions.go_to_construction(serial, detector, building, feature=feature)
            dt = time.time() - t0
            ok = result.get("ok", False)
            results[building] = f"{'✅' if ok else '❌'} {dt:.2f}s"
        except Exception as e:
            results[building] = f"❌ EXCEPTION ({e})"

        # Cleanup
        adb_helper.press_back(serial)
        time.sleep(2)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"[TEST] === V2 SWEEP SUMMARY (feature={feature}) ===")
    for building, status in results.items():
        print(f"  {building:25s} {status}")
    print(f"{'=' * 60}")


def _print_timings(timings):
    """Print timing summary table."""
    print(f"\n{'=' * 60}")
    print(f"[TEST] === TIMING BREAKDOWN ===")
    total = timings.get("T_TOTAL", 0)
    for key, val in timings.items():
        if key == "T_TOTAL":
            continue
        pct = (val / total * 100) if total > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"  {key:30s} {val:6.3f}s  ({pct:5.1f}%)  {bar}")
    print(f"  {'─' * 50}")
    print(f"  {'T_TOTAL':30s} {total:6.3f}s")
    print(f"{'=' * 60}")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(description="Test go_to_construction V2 workflow with timing")
    parser.add_argument("test", choices=["full", "timing", "speed", "sweep", "all"],
                        help="Which test to run")
    parser.add_argument("--serial", default="emulator-5556", help="Emulator serial")
    parser.add_argument("--building", default="HALL", choices=AVAILABLE_V2,
                        help=f"Construction name (default: HALL)")
    parser.add_argument("--feature", default="info",
                        help="Feature name (default: info)")
    args = parser.parse_args()

    if args.test == "full":
        test_full_v2(args.serial, args.building, args.feature)
    elif args.test == "timing":
        test_timing_breakdown(args.serial, args.building, args.feature)
    elif args.test == "speed":
        test_detection_speed(args.serial, args.building)
    elif args.test == "sweep":
        test_sweep_v2(args.serial, args.feature)
    elif args.test == "all":
        test_detection_speed(args.serial, args.building)
        test_timing_breakdown(args.serial, args.building, args.feature)
        test_full_v2(args.serial, args.building, args.feature)
