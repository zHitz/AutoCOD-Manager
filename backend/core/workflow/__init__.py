"""
Workflow Module — Game automation core actions.
Moved from TEST/WORKFLOW into the app as a production-ready module.

Usage:
    from backend.core.workflow import core_actions, GameStateDetector
"""
from backend.core.workflow.state_detector import GameStateDetector
from backend.core.workflow import core_actions
from backend.core.workflow import clipper_helper
from backend.core.workflow import adb_helper
