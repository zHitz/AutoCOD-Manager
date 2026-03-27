# Test File Writing Guide — Complete Reference

> **Purpose:** This is the definitive guide for writing test files in the `TEST/` folder.
> Every test file MUST follow these patterns exactly. Read this BEFORE creating any test.

---

## 1. Boilerplate — Copy This Exactly

```python
import os
import sys
import time
import cv2

# ── Path setup (MANDATORY — copy exactly) ──
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from backend.config import config
config.load()

from backend.core.workflow.state_detector import GameStateDetector
from backend.core.workflow import core_actions
from backend.core.workflow import adb_helper

# ── Constants ──
TEMPLATES_DIR = os.path.join(ROOT_DIR, "backend", "core", "workflow", "templates")
DEFAULT_SERIAL = "emulator-5556"
DEBUG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_<feature_name>")


def _make_detector():
    return GameStateDetector(adb_path=config.adb_path, templates_dir=TEMPLATES_DIR)


def save_frame(serial, detector, label):
    """Save full frame for visual debugging. Returns frame for reuse."""
    os.makedirs(DEBUG_DIR, exist_ok=True)
    frame = detector.get_frame(serial)
    if frame is None:
        print(f"[{serial}] [DEBUG] Could not capture frame for {label}")
        return None
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(DEBUG_DIR, f"{ts}_{label}.png")
    cv2.imwrite(path, frame)
    print(f"[DEBUG] Saved: {path}")
    return frame


def _phase_timer(label):
    """Context manager for timing phases."""
    class Timer:
        def __init__(self):
            self.elapsed = 0
        def __enter__(self):
            self._start = time.time()
            return self
        def __exit__(self, *_):
            self.elapsed = time.time() - self._start
            print(f"  ⏱  {label}: {self.elapsed:.1f}s")
    return Timer()
```

---

## 2. Main Block — Always Use argparse

```python
if __name__ == "__main__":
    import argparse

    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(description="Test <feature_name>")
    parser.add_argument("test", choices=["full", "nav", "templates", "all"],
                        help="full=E2E workflow | nav=navigation only | templates=in-place scan | all=run all")
    parser.add_argument("--serial", default=DEFAULT_SERIAL, help="Emulator serial")
    args = parser.parse_args()

    if args.test == "full":
        test_full_workflow(args.serial)
    elif args.test == "nav":
        test_navigation(args.serial)
    elif args.test == "templates":
        test_template_detection(args.serial)
    elif args.test == "all":
        test_navigation(args.serial)
        test_template_detection(args.serial)
        test_full_workflow(args.serial)
```

**Run command:**
```bash
python TEST/test_<feature_name>.py <test_name> --serial emulator-5556
```

---

## 3. Three Standard Test Types

Every test file should have these 3 tests:

### Test 1: Full E2E Workflow (`full`)

Runs the complete workflow from `core_actions` with diagnostics.

```python
def test_full_workflow(serial):
    print(f"\n{'═' * 60}")
    print(f"  TEST: Full <Feature> Workflow")
    print(f"  Serial: {serial}")
    print(f"{'═' * 60}")

    detector = _make_detector()
    detector.diagnostic_mode = True      # ← ALWAYS enable
    detector.clear_diagnostics()         # ← ALWAYS clear

    t0 = time.time()

    try:
        result = core_actions.<workflow_function>(serial, detector)
        elapsed = time.time() - t0
        ok = result.get("ok", False)

        # ── Result Summary ──
        print(f"\n{'─' * 60}")
        print(f"  RESULT: {'✅ OK' if ok else '❌ FAIL'}")
        print(f"  Time:   {elapsed:.1f}s")
        if not ok:
            print(f"  Error:  {result.get('error', 'unknown')}")
        print(f"{'─' * 60}")

        # ── Diagnostic Report ──
        print(f"\n  📊 DETECTION DIAGNOSTICS")
        print(f"{'─' * 60}")
        detector.print_diagnostics()

        # ── Near-miss Analysis ──
        near_misses = [
            e for e in detector.get_diagnostics()
            if not e.matched and e.confidence > 0.5
        ]
        if near_misses:
            print(f"\n  ⚠️  NEAR MISSES (conf > 0.50 but below threshold)")
            print(f"{'─' * 60}")
            for e in near_misses:
                gap = e.threshold - e.confidence
                print(f"  {e.target:35s}  conf={e.confidence:.3f}  thr={e.threshold:.2f}  gap={gap:.3f}  [{e.caller}]")

        # ── Matched Items Summary ──
        matched = [e for e in detector.get_diagnostics() if e.matched]
        if matched:
            print(f"\n  ✅ MATCHED TEMPLATES ({len(matched)})")
            print(f"{'─' * 60}")
            for e in matched:
                print(f"  {e.target:35s}  conf={e.confidence:.3f}  {e.time_ms:.0f}ms  [{e.caller}]")

    except KeyboardInterrupt:
        print(f"\n[TEST] Aborted by user.")
    except Exception as e:
        print(f"\n[TEST] Exception: {e}")
        import traceback
        traceback.print_exc()
```

### Test 2: Navigation Only (`nav`)

Tests if the bot can reach the target screen without running the full workflow.

```python
def test_navigation(serial):
    print(f"\n{'═' * 60}")
    print(f"  TEST: <Feature> Navigation")
    print(f"  Serial: {serial}")
    print(f"{'═' * 60}")

    detector = _make_detector()
    detector.diagnostic_mode = True
    detector.clear_diagnostics()

    # Step 1: Navigate
    print(f"\n  [Step 1] Navigating to <target>...")
    with _phase_timer("navigation"):
        result = core_actions.<nav_function>(serial, detector)
    if not core_actions._is_ok(result):
        print(f"  ❌ FAIL — Could not reach <target>")
        return
    print(f"  ✅ <Target> reached")

    # Step 2: Tap to open target screen
    print(f"\n  [Step 2] Tapping <button> (x, y)...")
    adb_helper.tap(serial, x, y)
    time.sleep(3)
    save_frame(serial, detector, "target_opened")

    # Step 3: Verify target template
    print(f"\n  [Step 3] Detecting <TEMPLATE_NAME>...")
    detector._screen_cache = None
    match = detector.check_activity(serial, target="<TEMPLATE_NAME>", threshold=0.8)

    # ── Summary ──
    print(f"\n{'─' * 60}")
    if match:
        print(f"  ✅ <TEMPLATE_NAME> found at ({match[1]}, {match[2]})")
    else:
        print(f"  ❌ <TEMPLATE_NAME> NOT FOUND")
    print(f"  📁 Debug: {DEBUG_DIR}")
    print(f"{'─' * 60}")

    detector.print_diagnostics()

    # Cleanup
    adb_helper.press_back(serial)
    time.sleep(2)
```

### Test 3: Template Detection (`templates`)

Scans current screen for templates without navigation. Uses single frame reuse.

```python
def test_template_detection(serial):
    print(f"\n{'═' * 60}")
    print(f"  TEST: <Feature> Template Detection (in-place)")
    print(f"  Serial: {serial}")
    print(f"{'═' * 60}")

    detector = _make_detector()
    detector.diagnostic_mode = True
    detector.clear_diagnostics()

    targets = [
        "<TEMPLATE_1>",
        "<TEMPLATE_2>",
        "<TEMPLATE_3>",
    ]

    # Capture one frame, reuse for ALL checks
    detector._screen_cache = None
    frame = save_frame(serial, detector, "<feature>_templates")
    if frame is None:
        print(f"  ❌ Could not capture screen.")
        return

    # ── Single-match detection ──
    print(f"\n  SINGLE-MATCH DETECTION (threshold=0.80)")
    print(f"{'─' * 60}")
    results = {}
    for target in targets:
        match = detector.check_activity(serial, target=target, threshold=0.80, frame=frame)
        results[target] = match
        if match:
            print(f"  ✅ {target:30s}  → ({match[1]:3d}, {match[2]:3d})")
        else:
            print(f"  ❌ {target:30s}  → not detected")

    # ── Multi-match detection ──
    print(f"\n  MULTI-MATCH DETECTION (threshold=0.80)")
    print(f"{'─' * 60}")
    for target in targets:
        matches = detector.find_all_activity_matches(serial, target=target, threshold=0.80)
        if matches:
            coords = "  ".join(f"({cx},{cy})" for cx, cy in matches)
            print(f"  ✅ {target:30s}  → {len(matches)} hit(s): {coords}")
        else:
            print(f"  ❌ {target:30s}  → 0 hits")

    # ── Diagnostic Report ──
    print(f"\n  📊 DETECTION DIAGNOSTICS")
    print(f"{'─' * 60}")
    detector.print_diagnostics()

    # ── Near-miss for tuning ──
    near_misses = [
        e for e in detector.get_diagnostics()
        if not e.matched and e.confidence > 0.50
    ]
    if near_misses:
        print(f"\n  ⚠️  NEAR MISSES — Use these to TUNE thresholds")
        print(f"{'─' * 60}")
        for e in near_misses:
            gap = e.threshold - e.confidence
            bar = "█" * int(e.confidence * 30) + "░" * (30 - int(e.confidence * 30))
            print(f"  {e.target:30s}  [{bar}] {e.confidence:.3f}  (need {e.threshold:.2f}, gap={gap:.3f})")

    # ── Summary ──
    print(f"\n{'═' * 60}")
    found = sum(1 for v in results.values() if v)
    print(f"  SUMMARY: {found}/{len(targets)} templates detected")
    print(f"  📁 Debug: {DEBUG_DIR}")
    print(f"{'═' * 60}")
```

---

## 4. Detection API Reference

### Screen Capture

| Method | Returns | Notes |
|---|---|---|
| `detector.screencap_memory(serial)` | `np.ndarray \| None` | Raw ADB screenshot, cached 100ms |
| `detector.get_frame(serial)` | `np.ndarray \| None` | Alias for screencap_memory |

### Detection Methods

| Method | Returns | Use Case |
|---|---|---|
| `check_state(serial, threshold=0.80)` | `str` | Game screen state (always returns a string) |
| `check_state_full(serial)` | `dict` | State + construction + special in one call |
| `check_construction(serial, target=None)` | `str \| None` | Building menu detection |
| `check_special_state(serial, target=None, frame=None)` | `str \| None` | Popup/overlay detection |
| `check_activity(serial, target=None, threshold=0.98, frame=None)` | `(name, cx, cy) \| None` | Button/element detection WITH coordinates |
| `check_alliance(serial, target=None)` | `(name, cx, cy) \| None` | Alliance UI elements |
| `locate_icon(serial, target=None)` | `(name, cx, cy) \| None` | In-game markers (RSS icons, heal) |
| `check_account_state(serial)` | `(name, cx, cy) \| None` | Account state detection |
| `find_all_activity_matches(serial, target, threshold=0.80)` | `[(cx, cy), ...]` | Find ALL occurrences (with NMS) |
| `is_menu_expanded(serial)` | `bool` | Is lobby bottom menu open? |

### Which Methods Log to Diagnostics?

| Method | Logs to Diagnostics? |
|---|---|
| `check_state()` | ✅ Yes |
| `check_construction()` | ✅ Yes |
| `check_special_state()` | ✅ Yes |
| `check_activity()` | ✅ Yes |
| `check_alliance()` | ✅ Yes |
| `locate_icon()` | ✅ Yes |
| `check_account_state()` | ✅ Yes |
| `find_all_activity_matches()` | ❌ No — use `check_activity()` for diagnostic data |

### Default Thresholds

| Category | Default | When To Lower |
|---|---|---|
| `check_state` | 0.80 | Rarely — states are stable |
| `check_construction` | 0.80 | If building icons partially obscured |
| `check_special_state` | 0.80 | If popups overlap |
| `check_activity` | 0.98 | **Often** — use 0.75–0.80 for buttons |
| `check_alliance` | 0.98 | If alliance UI varies |
| `locate_icon` | 0.80 | Rarely |

### Valid Targets

**check_construction:**
`HALL`, `MARKET`, `ELIXIR_HEALING`, `PET_SANCTUARY`, `PET_ENCLOSURE`, `MARKERS_MENU`, `ALLIANCE_MENU`, `TRAIN_UNITS`, `SCOUT_SENTRY_POST`, `TAVERN`, `HALFLING_HOUSE`, `BUILDING_UPGRADE`, `RESEARCH_CENTER`

**check_special_state:**
`SERVER_MAINTENANCE`, `AUTO_CAPTURE_PET`, `AUTO_CAPTURE_IN_PROGRESS`, `AUTO_CAPTURE_START`, `SETTINGS`, `CHARACTER_MANAGEMENT`, `MAIL_MENU`, `NOTE`, `RESOURCE_STATISTICS`, `MARKET_MENU`, `AUTO_PEACEKEEPING`, `SKIP`, `POLICY_SCREEN`, `GOVERNANCE_HEADER`, `RESEARCH_NO_RESOURCE`, `RESEARCH_NO_CONFIRM`, `QUEST_MENU`

**check_activity:**
`LEGION_1`–`LEGION_5`, `LEGION_IDLE`, `CREATE_LEGION`, `CREATE_LEGION_RSS`, `RSS_CENTER_MARKER`, `RSS_VIEW`, `RSS_GATHER`, `TRAINING_ICON`, `BTN_TRAIN`, `RSS_BUILD`, `TAVERN_FREE_DRAW`, `TAVERN_DRAW_X10`, `FARM_SEARCH_BTN`, `POLICY_ENACT_BTN`, `POLICY_GO_BTN`, `POLICY_SELECT_BTN`, `POLICY_TARGET_DEFAULT`, `POLICY_REPLENISH`, `POLICY_ALLIANCE_HELP`, `RESEARCH_EMPTY_SLOT`, `RESEARCH_CONFIRM`, `RESEARCH_ALLIANCE_HELP`, `RESEARCH_USE_BAG`, `RESEARCH_ECONOMY_TECH`, `RESEARCH_MILITARY_TECH`, `CONSTRUCTION_UPGRADE_BTN`, `CONSTRUCTION_UPGRADE_ICON`, `CONSTRUCTION_RESEARCH_ICON`, `CONSTRUCTION_BUILD_BTN`, `CONSTRUCTION_UNLOCK_PERMANENTLY_BTN`, `CONSTRUCTION_HIRE_BTN`, `CONSTRUCTION_CONFIRM_BTN`, `CONSTRUCTION_GO_BTN`, `CONSTRUCTION_INFO_BTN`, `QUEST_CLAIM_BTN`, `SCOUT_SENTRY_POST_BTN`, `SCOUT_QUICK_HELP_BTN`, `SCOUT_CLAIM_ALL_BTN`, `GOBLIN_MERCHANT_ICON`, `MERCHANT_RSS_ITEM_1`, `MERCHANT_RSS_ITEM_2`, `MERCHANT_RSS_ITEM_3`, `VIP_STORE_ICON`

**check_alliance:**
`ALLIANCE_WAR`, `NO_RALLY`, `ALREADY_JOIN_RALLY`, `ALLIANCE_HELP`, `ALLIANCE_DONATE_BTN`

**locate_icon:**
`CITY_RSS_GOLD`, `CITY_RSS_WOOD`, `CITY_RSS_ORE`, `CITY_RSS_MANA`, `HEALING_ICON`

---

## 5. Diagnostic Mode — ALWAYS Enable In Tests

```python
detector = _make_detector()
detector.diagnostic_mode = True     # Enable BEFORE running workflow
detector.clear_diagnostics()        # Reset log

# ... run workflow ...

detector.print_diagnostics()        # Compact report (matches + near-misses)
# detector.print_diagnostics(show_all=True)  # Full: every single attempt
```

### Diagnostic Entry Fields

| Field | Type | Description |
|---|---|---|
| `caller` | str | `"check_state"`, `"check_activity"`, `"check_construction"`, etc. |
| `target` | str | Template name, e.g. `"GOBLIN_MERCHANT_ICON"` |
| `confidence` | float | cv2.matchTemplate max_val (0.0–1.0) |
| `threshold` | float | Threshold used for this call |
| `time_ms` | float | Time taken for this match in milliseconds |
| `matched` | bool | `True` if confidence ≥ threshold |
| `use_color` | bool | Whether COLOR or GRAY matching was used |

### Near-Miss Analysis Pattern

```python
near_misses = [
    e for e in detector.get_diagnostics()
    if not e.matched and e.confidence > 0.5
]
for e in near_misses:
    gap = e.threshold - e.confidence
    print(f"  ⚠ {e.target}: conf={e.confidence:.3f} (need {e.threshold:.2f}, gap={gap:.3f})")
```

### Threshold Recommendation Pattern

```python
from collections import defaultdict
by_target = defaultdict(list)
for e in detector.get_diagnostics():
    by_target[e.target].append(e)

for target, entries in by_target.items():
    hits = [e for e in entries if e.matched]
    if hits:
        min_hit = min(e.confidence for e in hits)
        recommended = round(min_hit - 0.03, 2)
        print(f"  {target}: min_hit={min_hit:.3f} → recommend thr={recommended:.2f}")
```

---

## 6. Critical Rules

### Rule 1: Invalidate cache before fresh detection
```python
detector._screen_cache = None        # Force fresh screenshot
match = detector.check_activity(serial, target="CREATE_LEGION")
```

### Rule 2: Always sleep after ADB interactions
```python
adb_helper.tap(serial, cx, cy)
time.sleep(2)                         # Wait for animation/transition
detector._screen_cache = None         # Then capture fresh frame
```

### Rule 3: Reuse frames for same-screen checks
```python
# ❌ BAD — 3 separate ADB calls
detector.check_activity(serial, target="A")
detector.check_activity(serial, target="B")
detector.check_activity(serial, target="C")

# ✅ GOOD — 1 ADB call, reuse frame
detector._screen_cache = None
frame = detector.get_frame(serial)
a = detector.check_activity(serial, target="A", frame=frame)
b = detector.check_activity(serial, target="B", frame=frame)
c = detector.check_activity(serial, target="C", frame=frame)
```

### Rule 4: Use `_phase_timer` for timing
```python
with _phase_timer("go_to_alliance"):
    result = core_actions.go_to_alliance(serial, detector)
# Output: ⏱  go_to_alliance: 6.2s
```

### Rule 5: Structured output format
```python
# Use box-drawing characters for headers
print(f"{'═' * 60}")
print(f"  TEST: <Feature> Workflow")
print(f"{'═' * 60}")

# Use separators between sections
print(f"{'─' * 60}")

# Use status icons
print(f"  ✅ Template found")
print(f"  ❌ Template NOT FOUND")
print(f"  ⚠️  Near miss")
```

### Rule 6: Always handle exceptions in full tests
```python
try:
    result = core_actions.my_workflow(serial, detector)
except KeyboardInterrupt:
    print(f"\n[TEST] Aborted by user.")
except Exception as e:
    print(f"\n[TEST] Exception: {e}")
    import traceback
    traceback.print_exc()
```

### Rule 7: Coordinates use 960×540 resolution
All x,y coordinates are for LDPlayer at 960×540 resolution.

---

## 7. ADB Helper Functions

```python
adb_helper.tap(serial, x, y)                          # Tap with ±2px jitter
adb_helper.swipe(serial, x1, y1, x2, y2, duration)    # Swipe gesture
adb_helper.press_back(serial)                          # Android BACK key
adb_helper.press_back_n(serial, count=3, delay=1.5)    # Multiple backs
```

---

## 8. File Naming & Location

| Item | Location |
|---|---|
| Test files | `TEST/test_<feature_name>.py` |
| Debug screenshots | `TEST/debug_<feature_name>/` |
| Templates | `backend/core/workflow/templates/` |
| Core actions | `backend/core/workflow/core_actions.py` |

### Template Directory Structure

```
templates/
├── activities/          # Buttons: legion, train, build, farm, merchant
├── alliance/            # Alliance: war, rally, donate
├── contructions/        # Building menus: hall, market, upgrade buttons
├── research/            # Research: tech tabs, confirm, empty slot
├── policy/              # Season policy: enact, go, select buttons
├── quests/              # Quest menu, claim button
├── tavern/              # Tavern: free draw, draw x10
├── pets/                # Pet capture: auto-capture icons
├── accounts/            # Account: settings, character management
├── special/             # Special: mail, note, market, RSS stats
├── icon_markers/        # In-game markers: RSS icons, heal, skip
└── *.png                # Root-level: lobby states, loading screens
```

---

## 9. Complete Reference Test File

See `TEST/test_merchant.py` as the reference implementation that follows all patterns in this guide.
