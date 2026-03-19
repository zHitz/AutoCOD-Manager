"""
Policy Automation V3 -- Column Grid Config
===========================================
Loads season config from season_policy_config.json.
Edit that JSON file when a new season starts.
"""
import os
import json

_DIR = os.path.dirname(__file__)
_CONFIG_FILE = os.path.join(_DIR, "season_config.json")

# ═══════════════════════════════════════════════════════════
# LOAD SEASON CONFIG
# ═══════════════════════════════════════════════════════════

def _load_config():
    with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    columns = []
    for entry in cfg["columns"]:
        col = {
            "size": entry["size"],
            "target_pos": entry.get("path"),
            "names": entry.get("names", []),
        }
        if "governance" in entry:
            col["governance"] = entry["governance"]
        if "tap_order" in entry:
            col["tap_order"] = entry["tap_order"]
        if entry.get("is_target"):
            col["is_target"] = True
        if "fallback_col" in entry:
            col["fallback_col"] = entry["fallback_col"]
        columns.append(col)

    target_cols = cfg.get("target_columns", [4, 9])
    return columns, target_cols

COLUMNS, TARGET_COLUMNS = _load_config()
MAX_TARGET_COL = max(TARGET_COLUMNS) if TARGET_COLUMNS else 9
COL_SIZES = [c["size"] for c in COLUMNS]


# ═══════════════════════════════════════════════════════════
# Y POSITIONS — verified from grid overlay test
# ═══════════════════════════════════════════════════════════

COLUMN_Y_POSITIONS = {
    2: {"top": 130, "bottom": 400},
    3: {"top": 130, "mid": 260, "bottom": 400},
    4: {"pos_0": 80, "pos_1": 210, "pos_2": 330, "pos_3": 460},
}


# ═══════════════════════════════════════════════════════════
# SCROLL CONFIG
# ═══════════════════════════════════════════════════════════

SCROLL_RIGHT = {"start_x": 700, "end_x": 160, "y": 300, "duration": 800}
SCROLL_LEFT_RESET = {"start_x": 200, "end_x": 800, "y": 300, "duration": 300}
CLOSE_POPUP_POS = (515, 10)


# ═══════════════════════════════════════════════════════════
# GOVERNANCE CARD POSITIONS
# ═══════════════════════════════════════════════════════════

GOVERNANCE_CARD_POSITIONS = [
    (250, 230),   # Card 0 (left)
    (480, 230),   # Card 1 (center)
    (690, 230),   # Card 2 (right)
]


# ═══════════════════════════════════════════════════════════
# PROGRESS FILE (per-account)
# ═══════════════════════════════════════════════════════════

PROGRESS_FILE = os.path.join(_DIR, "policy_progress.json")


def load_progress(account_id: str = "default"):
    """Load progress for a specific account.
    Returns {'last_col': N} where N is last completed column (-1 = none)."""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r") as f:
                all_progress = json.load(f)
            if isinstance(all_progress, dict) and account_id in all_progress:
                return all_progress[account_id]
            # Legacy single-account format migration
            if isinstance(all_progress, dict) and "last_col" in all_progress:
                return all_progress
        except Exception:
            pass
    return {"last_col": -1}


def save_progress(last_col, account_id: str = "default"):
    """Save progress for a specific account after successfully completing a column."""
    all_progress = {}
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r") as f:
                all_progress = json.load(f)
            if isinstance(all_progress, dict) and "last_col" in all_progress and account_id == "default":
                all_progress = {"default": all_progress}
        except Exception:
            all_progress = {}
    all_progress[account_id] = {"last_col": last_col}
    with open(PROGRESS_FILE, "w") as f:
        json.dump(all_progress, f, indent=2)
    print(f"[POLICY] Progress saved: account={account_id}, last_col={last_col}")


# ═══════════════════════════════════════════════════════════
# LEGACY — backward compat for core_actions.py
# ═══════════════════════════════════════════════════════════

GOVERNANCE_CHOICE = 0
COLUMN_SLOT_X = {0: 150, 1: 390, 2: 570, 3: 810}
SCREEN_COLUMN_X = {0: [150, 390, 570, 810]}
ICON_Y_OFFSET = -45
DEFAULT_TARGET_POLICY = "POLICY_TARGET_DEFAULT"
POLICY_UPGRADE_PATH = [
    ("Command", 10), ("Spread", 10), ("Supplies", 10),
    ("Sentinel", 5), ("Administrative", 1),
]
