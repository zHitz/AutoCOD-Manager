"""
Detector Configs — Template registry, ROI hints, and constants for GameStateDetector.

Extracted from state_detector.py to keep the detection engine lean.
"""

# ── Template Configs ──────────────────────────────────────────────
# Format: {filename_relative_to_templates_dir: state_name}

STATE_CONFIGS = {
    "fixing_network.png": "LOADING SCREEN (NETWORK ISSUE)",
    "lobby_loading.png": "LOADING SCREEN",
    "lobby_loading_2.png": "LOADING SCREEN",
    "lobby_loading_3.png": "LOADING SCREEN",    
    "lobby_profile_detail.png": "IN-GAME LOBBY (PROFILE MENU DETAIL)",
    "lobby_profile_menu.png": "IN-GAME LOBBY (PROFILE MENU)",
    "lobby_events.png": "IN-GAME LOBBY (EVENTS MENU)",
    "lobby_bazzar.png": "IN-GAME LOBBY (BAZAAR)",
    "lobby_hammer.png": "IN-GAME LOBBY (IN_CITY)",
    "lobby_in_city_icon.png": "IN-GAME LOBBY (IN_CITY)",
    "lobby_magnifier.png": "IN-GAME LOBBY (OUT_CITY)",
    "lobby_mini_magnifier.png": "IN-GAME LOBBY (OUT_CITY)",
    "lobby_out_city_icon.png": "IN-GAME LOBBY (OUT_CITY)",
    "items_artifacts.png": "IN-GAME ITEMS (ARTIFACTS)",
    "items_resources.png": "IN-GAME ITEMS (RESOURCES)",
    "lobby_icons.png": "LOBBY_MENU_EXPANDED",
    "lobby_icons_war_pet.png": "LOBBY_MENU_EXPANDED",
}

CONSTRUCTION_CONFIGS = {
    "contructions/con_hall.png": "HALL",
    "contructions/con_market.png": "MARKET",
    "contructions/con_elixir_healing.png": "ELIXIR_HEALING",
    "contructions/con_pet_sanctuary.png": "PET_SANCTUARY",
    "contructions/con_pet_enclosure.png": "PET_ENCLOSURE",
    "contructions/con_markers.png": "MARKERS_MENU",
    "contructions/con_alliance_menu.png": "ALLIANCE_MENU",
    "contructions/con_train_units.png": "TRAIN_UNITS",
    "contructions/con_scout_sentry_post.png": "SCOUT_SENTRY_POST",
    "contructions/con_tavern.png": "TAVERN",
    "contructions/con_halfling_house.png": "HALFLING_HOUSE",
    "contructions/buiding_upgrade.png": "BUILDING_UPGRADE",
    "research/research_economy_tech.png": "RESEARCH_CENTER",
    "research/research_military_tech.png": "RESEARCH_CENTER",
    "contructions/season_menu.png": "SEASON_MENU",
}

SPECIAL_CONFIGS = {
    "special/popup_X_btn.png": "POPUP_X_BTN",
    "loading_server_maintenance.png": "SERVER_MAINTENANCE",
    "auto_capture_pet.png": "AUTO_CAPTURE_PET",
    "pets/Auto-capture_in_progress.png": "AUTO_CAPTURE_IN_PROGRESS",
    "pets/Auto-capture_start_icon.png": "AUTO_CAPTURE_START",
    "accounts/settings.png": "SETTINGS",
    "accounts/character_management.png": "CHARACTER_MANAGEMENT",
    "special/mail_menu.png": "MAIL_MENU",
    "special/note.png": "NOTE",
    "special/rss_statistics.png": "RESOURCE_STATISTICS",
    "special/market.png": "MARKET_MENU",
    "auto-peacekeeping.png": "AUTO_PEACEKEEPING",
    "icon_markers/skip.png": "SKIP",
    "policy/policy_header.png": "POLICY_SCREEN",
    "policy/governance_header.png": "GOVERNANCE_HEADER",
    "research/research_no_resource.png": "RESEARCH_NO_RESOURCE",
    "research/research_no_confirm.png": "RESEARCH_NO_CONFIRM",
    "quests/quests_menu.png": "QUEST_MENU",
}

ACTIVITY_CONFIGS = {
    "activities/legion_1.png": "LEGION_1",
    "activities/legion_2.png": "LEGION_2",
    "activities/legion_3.png": "LEGION_3",
    "activities/legion_4.png": "LEGION_4",
    "activities/legion_5.png": "LEGION_5",
    "activities/legion_idle.png": "LEGION_IDLE",
    "activities/create_legion.png": "CREATE_LEGION",
    "activities/create_legion_in_rss_center.png": "CREATE_LEGION_RSS",
    "icon_markers/rss_center.png": "RSS_CENTER_MARKER",
    "activities/legion_view.png": "RSS_VIEW",
    "activities/legion_gather.png": "RSS_GATHER",
    "activities/train_icon.png": "TRAINING_ICON",
    "activities/btn_train.png": "BTN_TRAIN",
    "activities/build.png": "RSS_BUILD",
    "tavern/free_draw_btn.png": "TAVERN_FREE_DRAW",
    "tavern/draw_x10_btn.png": "TAVERN_DRAW_X10",
    "activities/farm_search_btn.png": "FARM_SEARCH_BTN",
    "policy/enact_btn.png": "POLICY_ENACT_BTN",
    "policy/go_btn.png": "POLICY_GO_BTN",
    "policy/go_btn_uppercase.png": "POLICY_GO_BTN",
    "policy/go_btn_governance.png": "POLICY_GO_BTN",
    "policy/select_btn.png": "POLICY_SELECT_BTN",
    "policy/target_default.png": "POLICY_TARGET_DEFAULT",
    "policy/replenish_resources.png": "POLICY_REPLENISH",
    "policy/alliance_help_btn.png": "POLICY_ALLIANCE_HELP",
    "research/research_empty_slot.png": "RESEARCH_EMPTY_SLOT",
    "research/research_confirm.png": "RESEARCH_CONFIRM",
    "research/research_allaince_help_btn.png": "RESEARCH_ALLIANCE_HELP",
    "research/research_use_bag.png": "RESEARCH_USE_BAG",
    "research/research_economy_tech.png": "RESEARCH_ECONOMY_TECH",
    "research/research_military_tech.png": "RESEARCH_MILITARY_TECH",
    "contructions/upgrade_btn.png": "CONSTRUCTION_UPGRADE_BTN",
    "contructions/upgrade_icon.png": "CONSTRUCTION_UPGRADE_ICON",
    "contructions/research_icon.png": "CONSTRUCTION_RESEARCH_ICON",
    "contructions/build_btn.png": "CONSTRUCTION_BUILD_BTN",
    "contructions/unlock_permanently_btn.png": "CONSTRUCTION_UNLOCK_PERMANENTLY_BTN",
    "contructions/hire_btn.png": "CONSTRUCTION_HIRE_BTN",
    "contructions/confirm_btn_gold_color.png": "CONSTRUCTION_CONFIRM_BTN",
    "contructions/building_go_btn.png": "CONSTRUCTION_GO_BTN",
    "contructions/con_info_btn.png": "CONSTRUCTION_INFO_BTN",
    "quests/claim_btn.png": "QUEST_CLAIM_BTN",
    "contructions/scout_sentry_post_btn.png": "SCOUT_SENTRY_POST_BTN",
    "contructions/scout_quick_help_btn.png": "SCOUT_QUICK_HELP_BTN",
    "contructions/scout_claim_all.btn.png": "SCOUT_CLAIM_ALL_BTN",
    "merchant/rss_multi_use.png": "RSS_MULTI_USE_BTN",
    "merchant/rss_confirm.png": "RSS_CONFIRM_BTN",
    "alliance/goblin_merchant.png": "GOBLIN_MERCHANT_ICON",
    "alliance/merchant_rss_1.png": "MERCHANT_RSS_ITEM_1",
    "alliance/merchant_rss_2.png": "MERCHANT_RSS_ITEM_2",
    "alliance/merchant_rss_3.png": "MERCHANT_RSS_ITEM_3",
    "special/back_btn.png": "BACK_ARROW",
    "alliance/honorary_membership_icon.png": "HONORARY_MEMBERSHIP_ICON",
}

ALLIANCE_CONFIGS = {
    "alliance/war.png": "ALLIANCE_WAR",
    "alliance/no_rally.png": "NO_RALLY",
    "alliance/already_join_rally.png": "ALREADY_JOIN_RALLY",
    "alliance/alliance_help_btn.png": "ALLIANCE_HELP",
    "alliance/alliance_donate_btn.png": "ALLIANCE_DONATE_BTN",
}

ICON_CONFIGS = {
    "icon_markers/city_rss_gold_full.png": "CITY_RSS_GOLD",
    "icon_markers/city_rss_wood_full.png": "CITY_RSS_WOOD",
    "icon_markers/city_rss_ore_full.png": "CITY_RSS_ORE",
    "icon_markers/city_rss_mana_full.png": "CITY_RSS_MANA",
    "icon_markers/heal_icon.png": "HEALING_ICON",
}

ACCOUNT_CONFIGS: dict = {}

# ── ROI Hints ─────────────────────────────────────────────────────
# filename -> (x1, y1, x2, y2)
# Only scan this screen region for matching (massive speedup).
# If a template is NOT listed here, full screen is scanned (safe default).
# Padding: +20px on each side for safety margin.
# Screen resolution: 960×540

ROI_HINTS = {
    # ── STATE: Bottom-left HUD icons (hammer, magnifier) ──
    "lobby_hammer.png":            (0, 379, 91, 475),
    "lobby_in_city_icon.png":      (0, 440, 120, 540),
    "lobby_magnifier.png":         (0, 379, 91, 475),
    "lobby_mini_magnifier.png":    (168, 0, 242, 54),
    "lobby_out_city_icon.png":     (0, 440, 120, 540),

    # ── STATE: Top-center headers (profile, events, bazaar) ──
    "lobby_profile_menu.png":      (0, 0, 230, 80),
    "lobby_profile_detail.png":    (0, 0, 230, 80),
    "lobby_events.png":            (0, 0, 230, 80),
    "lobby_bazzar.png":            (200, 0, 760, 100),
    "items_artifacts.png":         (0, 0, 250, 80),
    "items_resources.png":         (0, 0, 250, 80),

    # ── STATE: Bottom-right menu icons ──
    "lobby_icons.png":             (735, 458, 841, 540),
    "lobby_icons_war_pet.png":     (451, 456, 567, 540),

    # ── STATE: Center screen (loading/network) ──
    "lobby_loading.png":           (0, 0, 350, 220),
    "lobby_loading_2.png":         (0, 0, 350, 220),
    "lobby_loading_3.png":         (0, 0, 960, 540),
    "fixing_network.png":          (0, 0, 950, 540),

    # ── CONSTRUCTION: Top-center building headers ──
    "contructions/con_hall.png":           (461, 190, 785, 282),
    "contructions/con_market.png":         (461, 190, 785, 282),
    "contructions/con_elixir_healing.png": (470, 105, 704, 205),
    "contructions/con_pet_sanctuary.png":  (10, 0, 250, 65),
    "contructions/con_pet_enclosure.png":  (10, 0, 250, 65),
    "contructions/con_markers.png":        (364, 25, 590, 109),
    "contructions/con_alliance_menu.png":  (10, 0, 250, 65),
    "contructions/con_train_units.png":    (10, 0, 250, 65),
    "contructions/con_scout_sentry_post.png": (10, 0, 320, 65),
    "contructions/con_halfling_house.png": (10, 0, 250, 65),
    "contructions/buiding_upgrade.png":    (10, 0, 310, 65),
    "research/research_economy_tech.png":  (10, 0, 250, 65),
    "research/research_military_tech.png": (10, 0, 250, 65),
    "contructions/season_menu.png": (10, 0, 250, 65),

    # ── SPECIAL: Center popups + headers ──
    "special/popup_X_btn.png": (700, 100, 900, 250),
    "loading_server_maintenance.png": (0, 0, 950, 540),
    "auto_capture_pet.png":           (350, 27, 630, 115),
    "pets/Auto-capture_in_progress.png": (305, 411, 761, 509),
    "pets/Auto-capture_start_icon.png":  (305, 411, 761, 509),
    "accounts/settings.png":          (10, 0, 250, 65),
    "accounts/character_management.png": (291, 30, 675, 116),
    "special/mail_menu.png":          (850, 0, 960, 80),
    "special/note.png":               (280, 100, 680, 200),
    "special/rss_statistics.png":     (300, 20, 650, 110),
    "special/market.png":             (10, 0, 250, 65),
    "auto-peacekeeping.png":          (96, 84, 206, 198),
    "icon_markers/skip.png":          (866, 0, 960, 98),
    "policy/policy_header.png":       (10, 0, 290, 70),
    "policy/governance_header.png":   (290, 29, 668, 117),
    "quests/quests_menu.png":         (10, 0, 250, 65),

    # ── ACTIVITY: Bottom-center action buttons ──
    "activities/create_legion.png":         (665, 70, 855, 165),
    "activities/create_legion_in_rss_center.png": (665, 70, 855, 165),
    "activities/legion_view.png":           (100, 100, 900, 540),
    "activities/legion_gather.png":         (500, 300, 800, 500),
    "activities/build.png":                 (100, 100, 900, 540),
    "activities/train_icon.png":            (710, 410, 860, 500),
    "activities/btn_train.png":             (710, 410, 860, 500),
    "activities/farm_search_btn.png":       (50,300, 900, 500),

    # ── ACTIVITY: Legion slots (right-side panel) ──
    "activities/legion_1.png":  (780, 0, 880, 60),
    "activities/legion_2.png":  (780, 0, 880, 60),
    "activities/legion_3.png":  (780, 0, 880, 60),
    "activities/legion_4.png":  (780, 0, 880, 60),
    "activities/legion_5.png":  (780, 0, 880, 60),
    "activities/legion_idle.png": (475, 50, 570, 550),

    # ── ACTIVITY: Construction action buttons ──
    "contructions/upgrade_btn.png":           (700, 450, 885, 535),
    "contructions/build_btn.png":             (100, 100, 900, 540),
    "contructions/hire_btn.png":              (100, 100, 900, 540),
    "contructions/confirm_btn_gold_color.png": (100, 100, 900, 540),
    "contructions/building_go_btn.png":       (100, 400, 900, 540),
    "contructions/unlock_permanently_btn.png": (100, 100, 900, 540),

    # ── ACTIVITY: Construction/Research icons ──
    "contructions/upgrade_icon.png":  (100, 100, 900, 540),
    "contructions/research_icon.png": (100, 100, 900, 540),
    "contructions/con_info_btn.png":  (100, 100, 900, 540),

    # ── ACTIVITY: Scout sentry buttons ──
    "contructions/scout_sentry_post_btn.png": (100, 100, 900, 540),
    "contructions/scout_quick_help_btn.png":  (365, 450, 595, 540),
    "contructions/scout_claim_all.btn.png":   (369, 454, 591, 540),

    # ── ACTIVITY: Policy buttons ──
    "policy/enact_btn.png":          (100, 100, 900, 540),
    "policy/go_btn.png":             (100, 100, 900, 540),
    "policy/go_btn_uppercase.png":   (100, 100, 900, 540),
    "policy/go_btn_governance.png":  (100, 100, 900, 540),
    "policy/select_btn.png":         (100, 100, 900, 540),
    "policy/alliance_help_btn.png":  (840, 465, 960, 540),

    # ── ACTIVITY: Research buttons ──
    "research/research_empty_slot.png":        (575, 10, 960, 90),
    "research/research_confirm.png":           (100, 100, 900, 540),
    "research/research_allaince_help_btn.png": (575, 0, 960, 90),

    # ── ACTIVITY: Quest claim ──
    "quests/claim_btn.png": (100, 100, 900, 540),

    # ── ACTIVITY: RSS popup (construction upgrade) ──
    "merchant/rss_multi_use.png": (200, 300, 760, 500),
    "merchant/rss_confirm.png": (200, 300, 760, 500),

    # ── ACTIVITY: Merchant area ──
    "alliance/goblin_merchant.png":  (200, 450, 310, 540),
    "alliance/merchant_rss_1.png":   (225, 225, 725, 425),
    "alliance/merchant_rss_2.png":   (225, 225, 725, 425),
    "alliance/merchant_rss_3.png":   (225, 225, 725, 425),

    # ── ACTIVITY: Back arrow (top-left corner) ──
    "special/back_btn.png":           (0, 0, 50, 50),

    # ── ACTIVITY: Honorary membership (alliance store) ──
    "alliance/honorary_membership_icon.png": (250, 450, 400, 540),

    # ── ALLIANCE ──
    "alliance/war.png":              (10, 60, 200, 300),
    "alliance/alliance_help_btn.png": (100, 100, 900, 540),
    "alliance/alliance_donate_btn.png": (100, 100, 900, 540),

    # ── ICON: City RSS icons (top-left HUD) ──
    "icon_markers/city_rss_gold_full.png": (450,250,700,450),
    "icon_markers/city_rss_wood_full.png": (450,250,700,450),
    "icon_markers/city_rss_ore_full.png":  (450,250,700,450),
    "icon_markers/city_rss_mana_full.png": (450,250,700,450),
    "icon_markers/heal_icon.png":          (650,200,850,400),
}

# ── Derived Registries ────────────────────────────────────────────

CATEGORY_REGISTRY = {
    "state": STATE_CONFIGS,
    "construction": CONSTRUCTION_CONFIGS,
    "special": SPECIAL_CONFIGS,
    "activity": ACTIVITY_CONFIGS,
    "alliance": ALLIANCE_CONFIGS,
    "icon": ICON_CONFIGS,
    "account": ACCOUNT_CONFIGS,
}

STATE_PRIORITY = [
    "LOADING SCREEN (NETWORK ISSUE)",
    "LOADING SCREEN",
    "IN-GAME LOBBY (PROFILE MENU DETAIL)",
    "IN-GAME LOBBY (PROFILE MENU)",
    "IN-GAME LOBBY (EVENTS MENU)",
    "IN-GAME LOBBY (BAZAAR)",
    "IN-GAME LOBBY (HALL_NEW)",
    "IN-GAME ITEMS (ARTIFACTS)",
    "IN-GAME ITEMS (RESOURCES)",
]

STATE_BASE = ["IN-GAME LOBBY (IN_CITY)", "IN-GAME LOBBY (OUT_CITY)"]
