"""
Season Policies Automation Package
===================================
Edit season_config.json when a new season starts.
See README.md for full documentation.
"""
from backend.core.workflow.policy.data import (
    COLUMNS, TARGET_COLUMNS, MAX_TARGET_COL, COL_SIZES,
    COLUMN_Y_POSITIONS, SCROLL_RIGHT, SCROLL_LEFT_RESET,
    CLOSE_POPUP_POS, GOVERNANCE_CARD_POSITIONS,
    PROGRESS_FILE, load_progress, save_progress,
)

# Lazy import — PolicyV3Engine depends on adb_helper which needs sys.path setup
def get_engine_class():
    from backend.core.workflow.policy.engine import PolicyV3Engine
    return PolicyV3Engine
