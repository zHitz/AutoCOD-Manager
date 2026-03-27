# GameStateDetector — API Reference & Test Writing Guide

> **Purpose:** This document is the single source of truth for AI agents writing test files that use `GameStateDetector`.
> Read this BEFORE writing any test file.

---

## Quick Start — Test File Boilerplate

Every test file in `TEST/` folder MUST follow this exact pattern:

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


# ── Main ──
if __name__ == "__main__":
    import argparse

    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(description="Test <feature_name>")
    parser.add_argument("test", choices=["full", "nav", "templates", "all"])
    parser.add_argument("--serial", default=DEFAULT_SERIAL)
    args = parser.parse_args()
    # ... dispatch to test functions
```

---

## Architecture Overview

```
GameStateDetector
├── __init__(adb_path, templates_dir)
│   ├── Loads ALL template images into RAM (color + grayscale)
│   ├── 7 categories: state, construction, special, activity, alliance, icon, account
│   └── Templates stored in self._registry dict
│
├── Screen Capture
│   ├── screencap_memory(serial) → np.ndarray    # ADB screencap to RAM (cached 100ms)
│   └── get_frame(serial) → np.ndarray            # Alias for screencap_memory
│
├── Detection Methods (Public API)
│   ├── check_state(serial)           → str                    # "IN-GAME LOBBY (IN_CITY)" etc
│   ├── check_state_full(serial)      → dict                   # {state, construction, special, screen}
│   ├── is_menu_expanded(serial)      → bool                   # Is lobby menu open?
│   ├── check_construction(serial)    → str | None             # Building name or None
│   ├── check_special_state(serial)   → str | None             # Special screen name or None
│   ├── check_activity(serial)        → (name, cx, cy) | None  # With coordinates
│   ├── check_alliance(serial)        → (name, cx, cy) | None  # With coordinates
│   ├── locate_icon(serial)           → (name, cx, cy) | None  # With coordinates
│   ├── check_account_state(serial)   → (name, cx, cy) | None  # With coordinates
│   └── find_all_activity_matches()   → [(cx, cy), ...]        # Multi-match with NMS
│
├── Diagnostic API
│   ├── diagnostic_mode = True/False  # Toggle instrumentation
│   ├── clear_diagnostics()           # Reset diagnostic log
│   ├── get_diagnostics()             # Raw diagnostic entries
│   └── print_diagnostics()           # Formatted console report
│
└── Internal Engine
    ├── _match_single()               # Core cv2.matchTemplate wrapper
    ├── _find_template()              # Unified finder (activity, alliance, icon, account)
    ├── _find_name_only()             # Name-only finder (construction, special)
    └── _match_state_from_screen()    # State detection with priority + cache
```

---

## Detection Methods — Detailed Reference

### `check_state(serial, threshold=0.80) → str`

Returns the current game screen state. Always returns a string (never None).

**Possible return values:**
| Return Value | Meaning |
|---|---|
| `"IN-GAME LOBBY (IN_CITY)"` | Player is inside city view |
| `"IN-GAME LOBBY (OUT_CITY)"` | Player is on the world map |
| `"IN-GAME LOBBY (PROFILE MENU)"` | Profile panel is open |
| `"IN-GAME LOBBY (PROFILE MENU DETAIL)"` | Profile detail panel is open |
| `"IN-GAME LOBBY (EVENTS MENU)"` | Events panel is open |
| `"IN-GAME LOBBY (BAZAAR)"` | Bazaar is open |
| `"IN-GAME ITEMS (ARTIFACTS)"` | Items → Artifacts tab |
| `"IN-GAME ITEMS (RESOURCES)"` | Items → Resources tab |
| `"LOADING SCREEN"` | Game is loading |
| `"LOADING SCREEN (NETWORK ISSUE)"` | Network connection lost |
| `"LOBBY_MENU_EXPANDED"` | Bottom menu expanded (icons visible) |
| `"UNKNOWN / TRANSITION"` | No matched state — game is transitioning |
| `"ERROR_CAPTURE"` | ADB screenshot failed |

**Usage:**
```python
state = detector.check_state(serial)
if state == "IN-GAME LOBBY (IN_CITY)":
    # Safe to proceed with city actions
```

### `check_state_full(serial, threshold=0.80) → dict`

Single screencap, checks state + construction + special in one call.

**Returns:**
```python
{
    "state": "IN-GAME LOBBY (IN_CITY)",   # Always present
    "construction": "HALL",                # Only if state is UNKNOWN / TRANSITION
    "special": "SETTINGS",                 # Only if state AND construction are None
    "screen": np.ndarray                   # Raw frame for reuse
}
```

### `check_construction(serial, target=None, threshold=0.80) → str | None`

Checks if a construction building menu is currently visible.

**Valid target values:**
`"HALL"`, `"MARKET"`, `"ELIXIR_HEALING"`, `"PET_SANCTUARY"`, `"PET_ENCLOSURE"`, `"MARKERS_MENU"`, `"ALLIANCE_MENU"`, `"TRAIN_UNITS"`, `"SCOUT_SENTRY_POST"`, `"TAVERN"`, `"HALFLING_HOUSE"`, `"BUILDING_UPGRADE"`, `"RESEARCH_CENTER"`

**Usage:**
```python
# Check for specific building
result = detector.check_construction(serial, target="HALL")
if result:
    print("Hall menu is open")

# Scan all buildings (slower)
result = detector.check_construction(serial)
```

### `check_special_state(serial, target=None, threshold=0.80, frame=None) → str | None`

Checks for special screens (overlays, popups, system screens).

**Valid target values:**
`"SERVER_MAINTENANCE"`, `"AUTO_CAPTURE_PET"`, `"AUTO_CAPTURE_IN_PROGRESS"`, `"AUTO_CAPTURE_START"`, `"SETTINGS"`, `"CHARACTER_MANAGEMENT"`, `"MAIL_MENU"`, `"NOTE"`, `"RESOURCE_STATISTICS"`, `"MARKET_MENU"`, `"AUTO_PEACEKEEPING"`, `"SKIP"`, `"POLICY_SCREEN"`, `"GOVERNANCE_HEADER"`, `"RESEARCH_NO_RESOURCE"`, `"RESEARCH_NO_CONFIRM"`, `"QUEST_MENU"`

**Usage:**
```python
# Reuse existing frame (avoids extra ADB call)
frame = detector.get_frame(serial)
special = detector.check_special_state(serial, target="SETTINGS", frame=frame)
```

### `check_activity(serial, target=None, threshold=0.98, frame=None) → (name, cx, cy) | None`

Finds UI buttons/elements and returns their **center coordinates** for tapping.
Uses **COLOR matching** (more accurate for buttons).

**Valid target values:**
`"LEGION_1"` to `"LEGION_5"`, `"LEGION_IDLE"`, `"CREATE_LEGION"`, `"CREATE_LEGION_RSS"`, `"RSS_CENTER_MARKER"`, `"RSS_VIEW"`, `"RSS_GATHER"`, `"TRAINING_ICON"`, `"BTN_TRAIN"`, `"RSS_BUILD"`, `"TAVERN_FREE_DRAW"`, `"TAVERN_DRAW_X10"`, `"FARM_SEARCH_BTN"`, `"POLICY_ENACT_BTN"`, `"POLICY_GO_BTN"`, `"POLICY_SELECT_BTN"`, `"POLICY_TARGET_DEFAULT"`, `"POLICY_REPLENISH"`, `"POLICY_ALLIANCE_HELP"`, `"RESEARCH_EMPTY_SLOT"`, `"RESEARCH_CONFIRM"`, `"RESEARCH_ALLIANCE_HELP"`, `"RESEARCH_USE_BAG"`, `"RESEARCH_ECONOMY_TECH"`, `"RESEARCH_MILITARY_TECH"`, `"CONSTRUCTION_UPGRADE_BTN"`, `"CONSTRUCTION_UPGRADE_ICON"`, `"CONSTRUCTION_RESEARCH_ICON"`, `"CONSTRUCTION_BUILD_BTN"`, `"CONSTRUCTION_UNLOCK_PERMANENTLY_BTN"`, `"CONSTRUCTION_HIRE_BTN"`, `"CONSTRUCTION_CONFIRM_BTN"`, `"CONSTRUCTION_GO_BTN"`, `"CONSTRUCTION_INFO_BTN"`, `"QUEST_CLAIM_BTN"`, `"SCOUT_SENTRY_POST_BTN"`, `"SCOUT_QUICK_HELP_BTN"`, `"SCOUT_CLAIM_ALL_BTN"`, `"GOBLIN_MERCHANT_ICON"`, `"MERCHANT_RSS_ITEM_1"`, `"MERCHANT_RSS_ITEM_2"`, `"MERCHANT_RSS_ITEM_3"`, `"VIP_STORE_ICON"`, `"BACK_ARROW"`

**Usage pattern — detect then tap:**
```python
match = detector.check_activity(serial, target="CREATE_LEGION", threshold=0.8)
if match:
    name, cx, cy = match
    adb_helper.tap(serial, cx, cy)
    time.sleep(2)
```

### `check_alliance(serial, target=None, threshold=0.98) → (name, cx, cy) | None`

**Valid targets:** `"ALLIANCE_WAR"`, `"NO_RALLY"`, `"ALREADY_JOIN_RALLY"`, `"ALLIANCE_HELP"`, `"ALLIANCE_DONATE_BTN"`

### `locate_icon(serial, target=None, threshold=0.80) → (name, cx, cy) | None`

**Valid targets:** `"CITY_RSS_GOLD"`, `"CITY_RSS_WOOD"`, `"CITY_RSS_ORE"`, `"CITY_RSS_MANA"`, `"HEALING_ICON"`

### `find_all_activity_matches(serial, target, threshold=0.80) → [(cx, cy), ...]`

Finds ALL occurrences of a template (e.g., multiple GO buttons). Uses NMS. Results sorted top-to-bottom.

```python
matches = detector.find_all_activity_matches(serial, target="CONSTRUCTION_GO_BTN", threshold=0.8)
for cx, cy in matches:
    adb_helper.tap(serial, cx, cy)
    time.sleep(1)
```

---

## Diagnostic Mode — How To Use In Tests

**ALWAYS enable diagnostics in test files** to capture confidence and timing data:

```python
def test_my_workflow(serial):
    detector = _make_detector()
    detector.diagnostic_mode = True    # ← Enable BEFORE running workflow
    detector.clear_diagnostics()       # ← Reset log

    # Run the workflow
    result = core_actions.my_workflow(serial, detector)

    # Print diagnostic report — shows confidence, timing, near-misses
    detector.print_diagnostics()            # Compact: matches + near-misses only
    # detector.print_diagnostics(show_all=True)  # Full: every single match attempt

    # Access raw data for programmatic analysis
    for entry in detector.get_diagnostics():
        if not entry.matched and entry.confidence > 0.7:
            print(f"  ⚠ {entry.target}: conf={entry.confidence:.3f} (missed by {entry.threshold - entry.confidence:.3f})")
```

**Diagnostic entry fields:**
| Field | Type | Description |
|---|---|---|
| `caller` | str | Method name: `"check_state"`, `"check_activity"`, `"check_construction"`, etc. |
| `target` | str | Template name tested, e.g. `"GOBLIN_MERCHANT_ICON"` |
| `confidence` | float | cv2.matchTemplate max_val (0.0 — 1.0) |
| `threshold` | float | Threshold used for this call |
| `time_ms` | float | Time taken for this single match in milliseconds |
| `matched` | bool | `True` if confidence ≥ threshold |
| `use_color` | bool | Whether COLOR or GRAY matching was used |

---

## Key ADB Helper Functions

Test files also use `adb_helper` for emulator interaction:

```python
from backend.core.workflow import adb_helper

adb_helper.tap(serial, x, y)                          # Tap with ±2px jitter
adb_helper.swipe(serial, x1, y1, x2, y2, duration)    # Swipe gesture
adb_helper.press_back(serial)                          # Android BACK key
adb_helper.press_back_n(serial, count=3, delay=1.5)    # Multiple backs
```

---

## Critical Rules For Test Files

### 1. Always invalidate cache before detection
```python
detector._screen_cache = None        # Force fresh screenshot
match = detector.check_activity(serial, target="CREATE_LEGION")
```

### 2. Always use `time.sleep()` after ADB interactions
```python
adb_helper.tap(serial, cx, cy)
time.sleep(2)                         # Wait for animation/transition
detector._screen_cache = None         # Then capture fresh frame
```

### 3. Save debug frames for visual verification
```python
def save_frame(serial, detector, label):
    os.makedirs(DEBUG_DIR, exist_ok=True)
    frame = detector.get_frame(serial)
    if frame is None:
        return
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(DEBUG_DIR, f"{ts}_{label}.png")
    cv2.imwrite(path, frame)
    print(f"[DEBUG] Saved: {path}")
```

### 4. Reuse frames when checking multiple templates on the same screen
```python
# BAD — 3 separate ADB calls
detector.check_activity(serial, target="A")
detector.check_activity(serial, target="B")
detector.check_activity(serial, target="C")

# GOOD — 1 ADB call, reuse frame
detector._screen_cache = None
frame = detector.get_frame(serial)
a = detector.check_activity(serial, target="A", frame=frame)
b = detector.check_activity(serial, target="B", frame=frame)
c = detector.check_activity(serial, target="C", frame=frame)
```

### 5. Default thresholds per category
| Category | Default | When to lower |
|---|---|---|
| `check_state` | 0.80 | Rarely — states are stable |
| `check_construction` | 0.80 | If building icons are partially obscured |
| `check_special_state` | 0.80 | If popups overlap |
| `check_activity` | 0.98 | **Often** — use 0.80 for buttons that change color |
| `check_alliance` | 0.98 | If alliance UI varies |
| `locate_icon` | 0.80 | Rarely |

### 6. Test file naming and location
- All test files go in `TEST/` folder
- Name format: `test_<feature_name>.py`
- Debug screenshots go in `TEST/debug_<feature_name>/`
- Run command: `python TEST/test_<feature_name>.py <test_name> --serial emulator-5556`

---

## Screen Resolution

All coordinates are based on **960×540** resolution (LDPlayer default for this game).

---

## Template Images Location

Templates are stored in: `backend/core/workflow/templates/`

Subdirectory structure:
```
templates/
├── activities/          # Buttons: legion, train, build, farm
├── alliance/            # Alliance: war, rally, merchant, donate
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
