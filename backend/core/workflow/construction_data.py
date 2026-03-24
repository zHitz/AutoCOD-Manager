# Construction data: maps construction names to their tap sequences.
# Each entry is a list of (x, y) coordinates to tap in order.
# The construction name must match the key in state_detector's construction_configs.

# ── V1 (Legacy) — DO NOT DELETE until all callers are migrated ──
CONSTRUCTION_TAPS = {
    "HALL": [
        (456, 111),
        (380, 116),
    ],
    "MARKET": [
        (639, 232),
        (545, 267),
    ],
    "ELIXIR_HEALING": [
        (705, 380),
        (793, 405),
    ],
    "SHOP": [
        (702, 279),
        (693, 351),
    ],
    "RESEARCH_CENTER": [
        (535, 210),   # Tap College of Orther building
        (615, 230),   # Confirm enter Research Center
    ],
    "TAVERN": [
        # TODO: User cần cung cấp tọa độ navigate từ IN_CITY
        (610, 365),
        (523, 327),
    ],
    "HALFLING_HOUSE": [
        (715, 210),   # Tap Halfling House building
        (760, 260),   # Open Halfling House menu
    ],
}

# ── V2 (Feature-based navigation) ──
# Each construction has:
#   - base: (x, y) tap coordinate on the building in city
#   - verify: template name for check_construction() verification
#   - features: dict of named sub-buttons, each with:
#       - type: "fixed" (hardcoded x,y) or "template" (detect via activity template)
#       - For "fixed": x, y coordinates
#       - For "template": template name registered in state_detector.activity_configs
#
# Usage: go_to_construction(serial, detector, "HALL", feature="upgrade")
CONSTRUCTION_DATA = {
    "HALL": {
        "base": (456, 111),
        "verify": "HALL",
        "features": {
            "info":    {"type": "template", "template": "CONSTRUCTION_INFO_BTN", "fallback": {"x": 380, "y": 116}},
            "upgrade": {"type": "template", "template": "CONSTRUCTION_UPGRADE_ICON", "verify": "BUILDING_UPGRADE"},
        },
    },
    "MARKET": {
        "base": (639, 232),
        "verify": "MARKET",
        "features": {
            "info":    {"type": "template", "template": "CONSTRUCTION_INFO_BTN", "fallback": {"x": 545, "y": 267}},
            "upgrade": {"type": "template", "template": "CONSTRUCTION_UPGRADE_ICON", "verify": "BUILDING_UPGRADE"},
        },
    },
    "ELIXIR_HEALING": {
        "base": (705, 380),
        "verify": "ELIXIR_HEALING",
        "features": {
            "info":    {"type": "template", "template": "CONSTRUCTION_INFO_BTN", "fallback": {"x": 793, "y": 405}},
            "upgrade": {"type": "template", "template": "CONSTRUCTION_UPGRADE_ICON", "verify": "BUILDING_UPGRADE"},
        },
    },
    "SHOP": {
        "base": (702, 279),
        "verify": "SHOP",
        "features": {
            "info":    {"type": "template", "template": "CONSTRUCTION_INFO_BTN", "fallback": {"x": 693, "y": 351}},
        },
    },
    "RESEARCH_CENTER": {
        "base": (535, 210),
        "verify": "RESEARCH_CENTER",
        "features": {
            "info":     {"type": "template", "template": "CONSTRUCTION_INFO_BTN", "fallback": {"x": 615, "y": 230}},
            "upgrade":  {"type": "template", "template": "CONSTRUCTION_UPGRADE_ICON", "verify": "BUILDING_UPGRADE"},
            "research": {"type": "template", "template": "CONSTRUCTION_RESEARCH_ICON", "verify": "RESEARCH_CENTER", "fallback": {"x": 615, "y": 230}},
        },
    },
    "TAVERN": {
        "base": (610, 365),
        "verify": "TAVERN",
        "features": {
            "info":    {"type": "template", "template": "CONSTRUCTION_INFO_BTN", "fallback": {"x": 523, "y": 327}},
        },
    },
    "HALFLING_HOUSE": {
        "base": (715, 210),
        "verify": "HALFLING_HOUSE",
        "features": {
            "info":    {"type": "template", "template": "CONSTRUCTION_INFO_BTN", "fallback": {"x": 760, "y": 260}},
            "upgrade": {"type": "template", "template": "CONSTRUCTION_UPGRADE_ICON", "verify": "BUILDING_UPGRADE"},
        },
    },
    "SCOUT_SENTRY_POST": {
        "base": (755, 235),
        "verify": "SCOUT_SENTRY_POST",
        "features": {
            "info":    {"type": "template", "template": "CONSTRUCTION_INFO_BTN", "fallback": {"x": 715, "y": 300}},
            "scout":   {"type": "template", "template": "SCOUT_SENTRY_POST_BTN", "verify": "SCOUT_SENTRY_POST"},
        },
    },
}
