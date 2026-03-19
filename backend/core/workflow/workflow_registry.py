"""
Workflow Function Registry — Central catalog of all composable workflow functions.
Serves the frontend Recipe Builder with available functions + metadata.
"""

FUNCTION_REGISTRY = [
    # ── Core Actions ──
    {
        "id": "startup_to_lobby",
        "label": "Boot to Lobby",
        "category": "Core Actions",
        "icon": "🚀",
        "color": "#6366f1",
        "description": "Boot game if not running, then navigate to lobby",
        "params": [
            {
                "key": "timeout",
                "label": "Load Timeout (sec)",
                "type": "number",
                "default": 120,
                "min": 30,
                "max": 300,
            }
        ],
    },
    {
        "id": "go_to_profile",
        "label": "Open Profile",
        "category": "Core Actions",
        "icon": "👤",
        "color": "#6366f1",
        "description": "Navigate to profile menu from lobby",
        "params": [],
    },
    {
        "id": "go_to_profile_details",
        "label": "Open Profile Details",
        "category": "Core Actions",
        "icon": "📋",
        "color": "#6366f1",
        "description": "Navigate to profile details from profile menu",
        "params": [],
    },
    {
        "id": "extract_player_id",
        "label": "Extract Player ID",
        "category": "Core Actions",
        "icon": "🆔",
        "color": "#6366f1",
        "description": "Copy player ID from profile via clipboard intercept",
        "params": [],
    },
    {
        "id": "back_to_lobby",
        "label": "Back to Lobby",
        "category": "Core Actions",
        "icon": "↩️",
        "color": "#6366f1",
        "description": "Navigate back to lobby from any state",
        "params": [
            {
                "key": "timeout_sec",
                "label": "Timeout (sec)",
                "type": "number",
                "default": 30,
                "min": 10,
                "max": 120,
            }
        ],
    },
    {
        "id": "wait_for_state",
        "label": "Wait for State",
        "category": "Core Actions",
        "icon": "⏳",
        "color": "#6366f1",
        "description": "Block until emulator reaches a target game state",
        "params": [
            {
                "key": "target_state",
                "label": "Target State",
                "type": "select",
                "default": "IN-GAME LOBBY (IN_CITY)",
                "options": [
                    "IN-GAME LOBBY (IN_CITY)",
                    "IN-GAME LOBBY (OUT_CITY)",
                    "IN-GAME LOBBY (PROFILE MENU)",
                    "IN-GAME LOBBY (PROFILE MENU DETAIL)",
                    "LOADING SCREEN",
                ],
            },
            {
                "key": "timeout_sec",
                "label": "Timeout (sec)",
                "type": "number",
                "default": 60,
                "min": 10,
                "max": 300,
            },
        ],
    },
    # ── ADB Actions ──
    {
        "id": "adb_tap",
        "label": "Tap Screen",
        "category": "ADB Actions",
        "icon": "👆",
        "color": "#fb923c",
        "description": "Tap a specific X,Y coordinate on device screen",
        "params": [
            {
                "key": "x",
                "label": "X",
                "type": "number",
                "default": 540,
                "min": 0,
                "max": 1920,
            },
            {
                "key": "y",
                "label": "Y",
                "type": "number",
                "default": 960,
                "min": 0,
                "max": 1080,
            },
        ],
    },
    {
        "id": "adb_swipe",
        "label": "Swipe Screen",
        "category": "ADB Actions",
        "icon": "👋",
        "color": "#fb923c",
        "description": "Swipe from (x1,y1) to (x2,y2) on device",
        "params": [
            {"key": "x1", "label": "From X", "type": "number", "default": 540},
            {"key": "y1", "label": "From Y", "type": "number", "default": 800},
            {"key": "x2", "label": "To X", "type": "number", "default": 540},
            {"key": "y2", "label": "To Y", "type": "number", "default": 300},
            {
                "key": "duration",
                "label": "Duration (ms)",
                "type": "number",
                "default": 300,
            },
        ],
    },
    {
        "id": "adb_press_back",
        "label": "Press Back",
        "category": "ADB Actions",
        "icon": "⬅️",
        "color": "#fb923c",
        "description": "Send BACK key event to device",
        "params": [
            {
                "key": "count",
                "label": "Times",
                "type": "number",
                "default": 1,
                "min": 1,
                "max": 10,
            },
            {
                "key": "delay",
                "label": "Delay Between (sec)",
                "type": "number",
                "default": 1.5,
            },
        ],
    },
    {
        "id": "adb_screencap",
        "label": "Screenshot",
        "category": "ADB Actions",
        "icon": "📸",
        "color": "#fb923c",
        "description": "Capture screenshot from device",
        "params": [],
    },
    # ── App Control ──
    {
        "id": "open_app",
        "label": "Launch App",
        "category": "App Control",
        "icon": "📱",
        "color": "#22c55e",
        "description": "Launch the game application on device",
        "params": [],
    },
    {
        "id": "check_app_foreground",
        "label": "Check App Running",
        "category": "App Control",
        "icon": "🔍",
        "color": "#22c55e",
        "description": "Check if game app is in foreground",
        "params": [],
    },
    # ── Scan Operations ──
    {
        "id": "scan_full",
        "label": "Full Scan",
        "category": "Scan Operations",
        "icon": "🔬",
        "color": "#38bdf8",
        "description": "Complete data scan (profile, resources, levels)",
        "params": [],
    },
    {
        "id": "scan_profile",
        "label": "Profile Scan",
        "category": "Scan Operations",
        "icon": "👤",
        "color": "#38bdf8",
        "description": "Scan player name and power level only",
        "params": [],
    },
    # ── Scripts ──
    {
        "id": "run_macro",
        "label": "Run Macro",
        "category": "Scripts",
        "icon": "⚡",
        "color": "#a855f7",
        "description": "Execute a recorded .record macro file",
        "params": [
            {"key": "file", "label": "Macro File", "type": "text", "default": ""},
            {
                "key": "loop",
                "label": "Loop Count",
                "type": "number",
                "default": 1,
                "min": 1,
                "max": 100,
            },
        ],
    },
    # ── Flow Control ──
    {
        "id": "flow_delay",
        "label": "Delay",
        "category": "Flow Control",
        "icon": "⏱️",
        "color": "#f59e0b",
        "description": "Wait for a specified number of seconds",
        "params": [
            {
                "key": "seconds",
                "label": "Duration (sec)",
                "type": "number",
                "default": 10,
                "min": 1,
                "max": 3600,
            }
        ],
    },
    {
        "id": "check_state",
        "label": "Detect Game State",
        "category": "Flow Control",
        "icon": "🧠",
        "color": "#f59e0b",
        "description": "Use OpenCV to detect the current game state",
        "params": [
            {
                "key": "threshold",
                "label": "Match Threshold",
                "type": "number",
                "default": 0.8,
            }
        ],
    },
    {
        "id": "check_mail",
        "label": "Check Mail",
        "category": "Core Actions",
        "icon": "✉️",
        "color": "#6366f1",
        "description": "Checks and claims mail in the game",
        "params": [
            {
                "key": "mail_type",
                "label": "Mail Type",
                "type": "select",
                "default": "all",
                "options": ["all", "events", "system", "alliance"],
            }
        ],
    },
    {
        "id": "claim_city_resources",
        "label": "Claim City Resources",
        "category": "Core Actions",
        "icon": "💰",
        "color": "#6366f1",
        "description": "Claims all available resources (Gold, Wood, Ore, Mana) in the city",
        "params": [],
    },
    {
        "id": "train_troops",
        "label": "Train Troops",
        "category": "Core Actions",
        "icon": "⚔️",
        "color": "#6366f1",
        "description": "Trains troops at the specified training houses and tiers",
        "params": [
            {
                "key": "tier_infantry",
                "label": "Infantry Tier",
                "type": "select",
                "options": ["skip", "default", "1", "2", "3", "4", "5"],
                "default": "default",
            },
            {
                "key": "tier_cavalry",
                "label": "Cavalry Tier",
                "type": "select",
                "options": ["skip", "default", "1", "2", "3", "4", "5"],
                "default": "default",
            },
            {
                "key": "tier_archer",
                "label": "Archer Tier",
                "type": "select",
                "options": ["skip", "default", "1", "2", "3", "4", "5"],
                "default": "default",
            },
            {
                "key": "tier_mage",
                "label": "Mage Tier",
                "type": "select",
                "options": ["skip", "default", "1", "2", "3", "4", "5"],
                "default": "default",
            },
            {
                "key": "tier_siege",
                "label": "Siege Tier",
                "type": "select",
                "options": ["skip", "default", "1", "2", "3", "4", "5"],
                "default": "default",
            },
        ],
    },
    # ── Merged Workflow Functions ──
    {
        "id": "nav_to_alliance_help",
        "label": "Alliance Help",
        "category": "Core Actions",
        "icon": "🤝",
        "color": "#6366f1",
        "description": "Navigate to Alliance Menu and tap Help button",
        "params": [],
    },
    {
        "id": "nav_to_tavern_chest",
        "label": "Tavern Chest Draw",
        "category": "Core Actions",
        "icon": "🎰",
        "color": "#6366f1",
        "description": "Claim daily free Hero & Artifact chest draws at the Tavern",
        "params": [
            {
                "key": "draw_x10_silver",
                "label": "x10 Silver Draw",
                "type": "select",
                "options": ["false", "true"],
                "default": "false",
            },
            {
                "key": "draw_x10_gold",
                "label": "x10 Gold Draw",
                "type": "select",
                "options": ["false", "true"],
                "default": "false",
            },
            {
                "key": "draw_x10_artifact",
                "label": "x10 Artifact Draw",
                "type": "select",
                "options": ["false", "true"],
                "default": "false",
            },
        ],
    },
    {
        "id": "nav_to_heal_troops",
        "label": "Heal Troops",
        "category": "Core Actions",
        "icon": "💊",
        "color": "#6366f1",
        "description": "Heal wounded troops via Elixir Healing building",
        "params": [],
    },
    {
        "id": "nav_to_darkling_legions",
        "label": "Attack Darkling Legions",
        "category": "Core Actions",
        "icon": "⚔️",
        "color": "#6366f1",
        "description": "Search and dispatch troops to attack Darkling Legions",
        "params": [],
    },
    {
        "id": "nav_to_chat_hero",
        "label": "Chat With Hero",
        "category": "Core Actions",
        "icon": "💬",
        "color": "#6366f1",
        "description": "Chat with heroes on the IN_CITY map (clockwise viewport scan)",
        "params": [],
    },
    {
        "id": "nav_to_research_tech",
        "label": "Research Technology",
        "category": "Core Actions",
        "icon": "🔬",
        "color": "#6366f1",
        "description": "Research technology in the Academy",
        "params": [
            {
                "key": "research_type",
                "label": "Research Type",
                "type": "select",
                "options": ["default", "economy", "military", "balance"],
                "default": "default",
            },
        ],
    },
    {
        "id": "nav_to_buy_merchant",
        "label": "Buy Merchant Items",
        "category": "Core Actions",
        "icon": "🛒",
        "color": "#6366f1",
        "description": "Buy items from the Merchant shop",
        "params": [
            {
                "key": "max_refreshes",
                "label": "Max Refreshes",
                "type": "number",
                "default": 5,
                "min": 0,
                "max": 20,
            },
        ],
    },
    {
        "id": "nav_to_claim_vip_gift",
        "label": "Claim VIP Daily Gift",
        "category": "Core Actions",
        "icon": "🎁",
        "color": "#6366f1",
        "description": "Claim daily VIP gift reward",
        "params": [],
    },
    {
        "id": "nav_to_festival_of_fortitude",
        "label": "Festival of Fortitude",
        "category": "Core Actions",
        "icon": "🎪",
        "color": "#6366f1",
        "description": "Process Festival of Fortitude event tasks",
        "params": [],
    },
    {
        "id": "nav_to_clean_trash",
        "label": "Clean Trash (Pet Sanctuary)",
        "category": "Core Actions",
        "icon": "🧹",
        "color": "#6366f1",
        "description": "Detect and clean trash at Pet Sanctuary",
        "params": [
            {
                "key": "duration",
                "label": "Duration (sec)",
                "type": "number",
                "default": 60,
                "min": 15,
                "max": 180,
            },
            {
                "key": "score_threshold",
                "label": "Score Threshold",
                "type": "number",
                "default": 0.30,
            },
        ],
    },
    {
        "id": "nav_to_season_policies",
        "label": "Season Policies",
        "category": "Core Actions",
        "icon": "📜",
        "color": "#6366f1",
        "description": "Automate Season Policies tech tree progression",
        "params": [],
    },
]


# Pre-built recipe templates
RECIPE_TEMPLATES = [
    {
        "id": "tpl_farm_loop",
        "name": "Farm Loop",
        "description": "Boot → Run farm macro → Scan → Back to lobby",
        "icon": "🌾",
        "steps": [
            {"function_id": "startup_to_lobby", "config": {"timeout": 120}},
            {"function_id": "run_macro", "config": {"file": "FARM +4", "loop": 1}},
            {"function_id": "flow_delay", "config": {"seconds": 30}},
            {"function_id": "scan_full", "config": {}},
            {"function_id": "back_to_lobby", "config": {"timeout_sec": 45}},
        ],
    },
    {
        "id": "tpl_id_extract",
        "name": "ID Extraction",
        "description": "Boot → Profile → Extract Player ID → Back",
        "icon": "🆔",
        "steps": [
            {"function_id": "startup_to_lobby", "config": {"timeout": 120}},
            {"function_id": "go_to_profile", "config": {}},
            {"function_id": "extract_player_id", "config": {}},
            {"function_id": "back_to_lobby", "config": {"timeout_sec": 45}},
        ],
    },
    {
        "id": "tpl_full_scan",
        "name": "Full Scan Cycle",
        "description": "Boot → Full Scan → Save to DB",
        "icon": "🔬",
        "steps": [
            {"function_id": "startup_to_lobby", "config": {"timeout": 120}},
            {"function_id": "scan_full", "config": {}},
            {"function_id": "back_to_lobby", "config": {"timeout_sec": 45}},
        ],
    },
    {
        "id": "tpl_swap_macro",
        "name": "Swap & Repeat",
        "description": "Run character swap macro in a loop",
        "icon": "🔁",
        "steps": [
            {"function_id": "startup_to_lobby", "config": {"timeout": 120}},
            {
                "function_id": "run_macro",
                "config": {"file": "Swap_Charactor", "loop": 5},
            },
            {"function_id": "flow_delay", "config": {"seconds": 10}},
            {"function_id": "back_to_lobby", "config": {"timeout_sec": 45}},
        ],
    },
]


def get_functions():
    """Return the full function registry."""
    return FUNCTION_REGISTRY


def get_templates():
    """Return all pre-built recipe templates."""
    return RECIPE_TEMPLATES


def get_function_by_id(func_id: str):
    """Find a function definition by its ID."""
    for fn in FUNCTION_REGISTRY:
        if fn["id"] == func_id:
            return fn
    return None


ACTIVITY_REGISTRY = [
    {
        "id": "gather_rss_center",
        "name": "Gather Resource Center",
        "icon": "🏛️",
        "description": "Farm resources at the Resource Center",
        "weight": "heavy",
        "steps": [
            {"function_id": "startup_to_lobby", "config": {}},
            {"function_id": "nav_to_rss_center_farm", "config": {}},
        ],
        "config_fields": [],
        "defaults": {"cooldown_enabled": False, "cooldown_minutes": 60},
    },
    {
        "id": "gather_resource",
        "name": "Gather Resource",
        "icon": "⛏️",
        "description": "Gather resources on the world map",
        "weight": "heavy",
        "steps": [
            {"function_id": "startup_to_lobby", "config": {}},
            {"function_id": "nav_to_farming", "config": {"resource_type": "wood"}},
        ],
        "config_fields": [
            {
                "key": "resource_type",
                "label": "Farm Resource Type",
                "type": "select",
                "options": ["gold", "wood", "stone", "mana"],
                "default": "wood",
            },
        ],
        "defaults": {"cooldown_enabled": False, "cooldown_minutes": 60},
    },
    {
        "id": "full_scan",
        "name": "Full Scan",
        "icon": "🔬",
        "description": "Boot to lobby and run full data scan",
        "weight": "heavy",
        "steps": [
            {"function_id": "startup_to_lobby", "config": {}},
            {"function_id": "scan_full", "config": {}},
        ],
        "config_fields": [],
        "defaults": {"cooldown_enabled": False, "cooldown_minutes": 60},
    },
    {
        "id": "catch_pet",
        "name": "Catch Pet",
        "icon": "🐾",
        "description": "Capture pet on the world map",
        "weight": "heavy",
        "steps": [
            {"function_id": "startup_to_lobby", "config": {}},
            {"function_id": "nav_to_capture_pet", "config": {}},
        ],
        "config_fields": [],
        "defaults": {"cooldown_enabled": False, "cooldown_minutes": 60},
    },
    {
        "id": "claim_mail_reward",
        "name": "Claim Mail Reward",
        "icon": "✉️",
        "description": "Automatically check and claim mail rewards",
        "weight": "light",
        "steps": [
            {"function_id": "startup_to_lobby", "config": {}},
            {"function_id": "check_mail", "config": {"mail_type": "all"}},
        ],
        "config_fields": [
            {
                "key": "mail_type",
                "label": "Mail Type",
                "type": "select",
                "options": ["all", "events", "system", "alliance"],
                "default": "all",
            },
        ],
        "defaults": {"cooldown_enabled": False, "cooldown_minutes": 60},
    },
    {
        "id": "claim_resources",
        "name": "Claim Resources",
        "icon": "💰",
        "description": "Claim resources in your city",
        "weight": "light",
        "steps": [
            {"function_id": "startup_to_lobby", "config": {}},
            {"function_id": "claim_city_resources", "config": {}},
        ],
        "config_fields": [],
        "defaults": {"cooldown_enabled": False, "cooldown_minutes": 60},
    },
    {
        "id": "train_troops",
        "name": "Train Troops",
        "icon": "⚔️",
        "description": "Train troops in your city",
        "weight": "heavy",
        "steps": [
            {"function_id": "startup_to_lobby", "config": {}},
            {"function_id": "train_troops", "config": {}},
        ],
        "config_fields": [
            {
                "key": "tier_infantry",
                "label": "Infantry Tier",
                "type": "select",
                "options": ["skip", "default", "1", "2", "3", "4", "5"],
                "default": "default"
            },
            {
                "key": "tier_cavalry",
                "label": "Cavalry Tier",
                "type": "select",
                "options": ["skip", "default", "1", "2", "3", "4", "5"],
                "default": "default"
            },
            {
                "key": "tier_archer",
                "label": "Archer Tier",
                "type": "select",
                "options": ["skip", "default", "1", "2", "3", "4", "5"],
                "default": "default"
            },
            {
                "key": "tier_mage",
                "label": "Mage Tier",
                "type": "select",
                "options": ["skip", "default", "1", "2", "3", "4", "5"],
                "default": "default"
            },
            {
                "key": "tier_siege",
                "label": "Siege Tier",
                "type": "select",
                "options": ["skip", "default", "1", "2", "3", "4", "5"],
                "default": "default"
            }
        ],
        "defaults": {"cooldown_enabled": False, "cooldown_minutes": 60},
    },
    {
        "id": "claim_alliance_resource",
        "name": "Claim Alliance Resource",
        "icon": "💎",
        "description": "Claim alliance territory resources",
        "weight": "light",
        "steps": [
            {"function_id": "startup_to_lobby", "config": {}},
            {"function_id": "claim_alliance_resource", "config": {}},
        ],
        "config_fields": [],
        "defaults": {"cooldown_enabled": False, "cooldown_minutes": 60},
    },
    # ── Merged Workflow Activities ──
    {
        "id": "alliance_help",
        "name": "Alliance Help",
        "icon": "🤝",
        "description": "Navigate to Alliance Menu, detect & tap Help button",
        "weight": "light",
        "steps": [
            {"function_id": "startup_to_lobby", "config": {}},
            {"function_id": "nav_to_alliance_help", "config": {}},
        ],
        "config_fields": [],
        "defaults": {"cooldown_enabled": True, "cooldown_minutes": 15},
    },
    {
        "id": "tavern_chest_draw",
        "name": "Tavern Chest Draw",
        "icon": "🎰",
        "description": "Claim daily free Hero & Artifact chest draws at the Tavern",
        "weight": "light",
        "steps": [
            {"function_id": "startup_to_lobby", "config": {}},
            {"function_id": "nav_to_tavern_chest", "config": {}},
        ],
        "config_fields": [
            {
                "key": "draw_x10_silver",
                "label": "x10 Silver Draw",
                "type": "select",
                "options": ["false", "true"],
                "default": "false",
            },
            {
                "key": "draw_x10_gold",
                "label": "x10 Gold Draw",
                "type": "select",
                "options": ["false", "true"],
                "default": "false",
            },
            {
                "key": "draw_x10_artifact",
                "label": "x10 Artifact Draw",
                "type": "select",
                "options": ["false", "true"],
                "default": "false",
            },
        ],
        "defaults": {"cooldown_enabled": True, "cooldown_minutes": 720},
    },
    {
        "id": "heal_troops_task",
        "name": "Heal Troops",
        "icon": "💊",
        "description": "Heal wounded troops via Elixir Healing building",
        "weight": "heavy",
        "steps": [
            {"function_id": "startup_to_lobby", "config": {}},
            {"function_id": "nav_to_heal_troops", "config": {}},
        ],
        "config_fields": [],
        "defaults": {"cooldown_enabled": True, "cooldown_minutes": 60},
    },
    {
        "id": "attack_darkling_legions",
        "name": "Attack Darkling Legions",
        "icon": "⚔️",
        "description": "Search and dispatch troops to attack Darkling Legions",
        "weight": "heavy",
        "steps": [
            {"function_id": "startup_to_lobby", "config": {}},
            {"function_id": "nav_to_darkling_legions", "config": {}},
        ],
        "config_fields": [],
        "defaults": {"cooldown_enabled": True, "cooldown_minutes": 60},
    },
    {
        "id": "chat_with_hero_task",
        "name": "Chat With Hero",
        "icon": "💬",
        "description": "Chat with heroes on the IN_CITY map (clockwise viewport scan)",
        "weight": "light",
        "steps": [
            {"function_id": "startup_to_lobby", "config": {}},
            {"function_id": "nav_to_chat_hero", "config": {}},
        ],
        "config_fields": [],
        "defaults": {"cooldown_enabled": True, "cooldown_minutes": 180},
    },
    {
        "id": "research_technology_task",
        "name": "Research Technology",
        "icon": "🔬",
        "description": "Research technology in the Academy",
        "weight": "heavy",
        "steps": [
            {"function_id": "startup_to_lobby", "config": {}},
            {"function_id": "nav_to_research_tech", "config": {}},
        ],
        "config_fields": [
            {
                "key": "research_type",
                "label": "Research Type",
                "type": "select",
                "options": ["default", "economy", "military", "balance"],
                "default": "default",
            },
        ],
        "defaults": {"cooldown_enabled": True, "cooldown_minutes": 60},
    },
    {
        "id": "buy_merchant_items_task",
        "name": "Buy Merchant Items",
        "icon": "🛒",
        "description": "Buy items from the Merchant shop",
        "weight": "light",
        "steps": [
            {"function_id": "startup_to_lobby", "config": {}},
            {"function_id": "nav_to_buy_merchant", "config": {}},
        ],
        "config_fields": [
            {
                "key": "max_refreshes",
                "label": "Max Refreshes",
                "type": "number",
                "default": 5,
                "min": 0,
                "max": 20,
            },
        ],
        "defaults": {"cooldown_enabled": True, "cooldown_minutes": 720},
    },
    {
        "id": "claim_daily_vip_gift_task",
        "name": "Claim VIP Daily Gift",
        "icon": "🎁",
        "description": "Claim daily VIP gift reward",
        "weight": "light",
        "steps": [
            {"function_id": "startup_to_lobby", "config": {}},
            {"function_id": "nav_to_claim_vip_gift", "config": {}},
        ],
        "config_fields": [],
        "defaults": {"cooldown_enabled": True, "cooldown_minutes": 1440},
    },
    {
        "id": "rotating_event",
        "name": "Event",
        "icon": "🎯",
        "description": "Aggregate activity that rotates through enabled sub-events",
        "weight": "heavy",
        "type": "event",
        "sub_events": [
            {
                "id": "festival_of_fortitude",
                "name": "Festival of Fortitude",
                "description": "Process Festival of Fortitude event tasks",
                "steps": [
                    {"function_id": "startup_to_lobby", "config": {}},
                    {"function_id": "nav_to_festival_of_fortitude", "config": {}},
                ],
                "config_fields": [],
                "defaults": {"cooldown_enabled": True, "cooldown_minutes": 360},
            },
        ],
        "steps": [],
        "config_fields": [],
        "defaults": {"cooldown_enabled": False, "cooldown_minutes": 60},
    },
    {
        "id": "clean_trash_pet_sanctuary_task",
        "name": "Clean Trash (Pet Sanctuary)",
        "icon": "🧹",
        "description": "Detect and clean trash at Pet Sanctuary using computer vision",
        "weight": "light",
        "steps": [
            {"function_id": "startup_to_lobby", "config": {}},
            {"function_id": "nav_to_clean_trash", "config": {}},
        ],
        "config_fields": [
            {
                "key": "duration",
                "label": "Duration (sec)",
                "type": "number",
                "default": 60,
                "min": 15,
                "max": 180,
            },
            {
                "key": "score_threshold",
                "label": "Score Threshold",
                "type": "number",
                "default": 0.30,
            },
        ],
        "defaults": {"cooldown_enabled": True, "cooldown_minutes": 120},
    },
    {
        "id": "season_policies_task",
        "name": "Season Policies",
        "icon": "📜",
        "description": "Automate Season Policies tech tree (enact, governance, GO chains)",
        "weight": "heavy",
        "steps": [
            {"function_id": "startup_to_lobby", "config": {}},
            {"function_id": "nav_to_season_policies", "config": {}},
        ],
        "config_fields": [],
        "defaults": {"cooldown_enabled": True, "cooldown_minutes": 60},
    },
]


def get_activity_registry():
    """Return the full bot activity registry."""
    return ACTIVITY_REGISTRY


def get_activity_by_id(activity_id: str):
    """Find a bot activity by its ID."""
    for act in ACTIVITY_REGISTRY:
        if act["id"] == activity_id:
            return act
    return None


def build_steps_for_activity(activity_id: str, user_config: dict = None):
    """Build executor steps with user config merged into defaults.
    For event-type activities, returns steps from all enabled sub-events."""
    act = get_activity_by_id(activity_id)
    if not act:
        return None

    cfg = user_config or {}

    # Handle event-type activities: dispatch to enabled sub-events
    if act.get("type") == "event":
        return _build_event_steps(act, cfg)

    steps = []

    for step_def in act.get("steps", []):
        # Deep copy to avoid mutating the registry
        step = {
            "function_id": step_def["function_id"],
            "config": step_def.get("config", {}).copy(),
        }

        # We simply merge all user_config into the step config where keys overlap.
        for key, val in cfg.items():
            if key in act.get("defaults", {}):
                # Ignore global defaults like 'cooldown_enabled' inside step configs
                continue
            step["config"][key] = val

        steps.append(step)

    return steps


def _build_event_steps(event_act: dict, user_config: dict) -> list:
    """Build combined steps from all enabled sub-events inside an event activity."""
    sub_events = event_act.get("sub_events", [])
    sub_cfg = user_config.get("sub_events_config", {})
    all_steps = []

    for sub in sub_events:
        sub_id = sub["id"]
        sub_user = sub_cfg.get(sub_id, {})

        # Skip disabled sub-events
        if not sub_user.get("enabled", False):
            continue

        sub_user_config = sub_user.get("config", {})
        for step_def in sub.get("steps", []):
            step = {
                "function_id": step_def["function_id"],
                "config": step_def.get("config", {}).copy(),
            }
            for key, val in sub_user_config.items():
                if key in sub.get("defaults", {}):
                    continue
                step["config"][key] = val
            all_steps.append(step)

    return all_steps


def get_sub_event_by_id(event_activity_id: str, sub_event_id: str):
    """Find a sub-event definition inside an event-type activity."""
    act = get_activity_by_id(event_activity_id)
    if not act or act.get("type") != "event":
        return None
    for sub in act.get("sub_events", []):
        if sub["id"] == sub_event_id:
            return sub
    return None
