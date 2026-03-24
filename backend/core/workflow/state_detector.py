import os
import cv2
import numpy as np
import subprocess
import time

class GameStateDetector:
    """
    Modular State Detector.
    Loads templates into RAM once and uses ADB screencap to memory for zero disk I/O.
    
    Optimizations:
    - Grayscale matching: 3x faster than color (1 channel vs 3)
    - ROI cropping: scan only relevant screen region per template
    - Early exit cache: check last matched state first (~90% hit rate)
    - Screenshot cache: skip ADB if last capture < 100ms ago
    - Unified template loader: DRY code
    """
    def __init__(self, adb_path: str, templates_dir: str):
        self.adb_path = adb_path
        self.templates_dir = templates_dir

        # Template storage format: {state_name: [{"color": np.array, "gray": np.array, "roi": tuple|None}]}
        self.templates = {}
        self.construction_templates = {}
        self.special_templates = {}
        self.activity_templates = {}
        self.alliance_templates = {}
        self.icon_templates = {}
        self.account_templates = {}

        # ── OPT-3: Early exit cache ──
        self._last_matched_state = None

        # ── OPT-5b: Screenshot cache ──
        self._screen_cache = None
        self._screen_gray_cache = None
        self._screen_cache_time = 0
        self._SCREEN_CACHE_MAX_AGE_MS = 100  # Reuse screenshot if < 100ms old

        # ── State definitions ──
        self.state_configs = {
            "fixing_network.png": "LOADING SCREEN (NETWORK ISSUE)",
            "lobby_loading.png": "LOADING SCREEN",
            "lobby_loading_2.png": "LOADING SCREEN",
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
        
        # Construction templates — loaded separately, NOT part of check_state
        self.construction_configs = {
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
            # Research Center — detect via tab headers (economy/military)
            "research/research_economy_tech.png": "RESEARCH_CENTER",
            "research/research_military_tech.png": "RESEARCH_CENTER",
        }
        
        # Special templates — loaded separately, called on specific conditions
        self.special_configs = {
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
            # Policy screen verification
            "policy/policy_header.png": "POLICY_SCREEN",
            "policy/governance_header.png": "GOVERNANCE_HEADER",
            # Research Technology
            "research/research_no_resource.png": "RESEARCH_NO_RESOURCE",
            "research/research_no_confirm.png": "RESEARCH_NO_CONFIRM",
            # Quest reward screen
            "quests/quests_menu.png": "QUEST_MENU",
        }
        
        # Activity templates — returns name + center coordinates when matched
        self.activity_configs = {
            "activities/legion_1.png": "LEGION_1",
            "activities/legion_2.png": "LEGION_2",
            "activities/legion_3.png": "LEGION_3",
            "activities/legion_4.png": "LEGION_4",
            "activities/legion_5.png": "LEGION_5",
            "activities/legion_idle.png": "LEGION_IDLE",
            "activities/create_legion.png": "CREATE_LEGION",
            "icon_markers/rss_center.png": "RSS_CENTER_MARKER",
            "activities/legion_view.png": "RSS_VIEW",
            "activities/legion_gather.png": "RSS_GATHER",
            "activities/train_icon.png": "TRAINING_ICON",
            "activities/btn_train.png": "BTN_TRAIN",
            "activities/build.png": "RSS_BUILD",
            "tavern/free_draw_btn.png": "TAVERN_FREE_DRAW",
            "tavern/draw_x10_btn.png": "TAVERN_DRAW_X10",
            "activities/farm_search_btn.png": "FARM_SEARCH_BTN",
            # Policy button detection
            "policy/enact_btn.png": "POLICY_ENACT_BTN",
            "policy/go_btn.png": "POLICY_GO_BTN",
            "policy/go_btn_uppercase.png": "POLICY_GO_BTN",
            "policy/go_btn_governance.png": "POLICY_GO_BTN",
            "policy/select_btn.png": "POLICY_SELECT_BTN",
            "policy/target_default.png": "POLICY_TARGET_DEFAULT",
            "policy/replenish_resources.png": "POLICY_REPLENISH",
            "policy/alliance_help_btn.png": "POLICY_ALLIANCE_HELP",
            # Research Technology
            "research/research_empty_slot.png": "RESEARCH_EMPTY_SLOT",
            "research/research_confirm.png": "RESEARCH_CONFIRM",
            "research/research_allaince_help_btn.png": "RESEARCH_ALLIANCE_HELP",
            "research/research_use_bag.png": "RESEARCH_USE_BAG",
            "research/research_economy_tech.png": "RESEARCH_ECONOMY_TECH",
            "research/research_military_tech.png": "RESEARCH_MILITARY_TECH",
            # Construction Upgrade
            "contructions/upgrade_btn.png": "CONSTRUCTION_UPGRADE_BTN",
            "contructions/upgrade_icon.png": "CONSTRUCTION_UPGRADE_ICON",
            "contructions/research_icon.png": "CONSTRUCTION_RESEARCH_ICON",
            "contructions/build_btn.png": "CONSTRUCTION_BUILD_BTN",
            "contructions/unlock_permanently_btn.png": "CONSTRUCTION_UNLOCK_PERMANENTLY_BTN",
            "contructions/hire_btn.png": "CONSTRUCTION_HIRE_BTN",
            "contructions/confirm_btn_gold_color.png": "CONSTRUCTION_CONFIRM_BTN",
            "contructions/building_go_btn.png": "CONSTRUCTION_GO_BTN",
            "contructions/con_info_btn.png": "CONSTRUCTION_INFO_BTN",
            # Quest claim button
            "quests/claim_btn.png": "QUEST_CLAIM_BTN",
            # Scout Sentry Post buttons
            "contructions/scout_sentry_post_btn.png": "SCOUT_SENTRY_POST_BTN",
            "contructions/scout_quick_help_btn.png": "SCOUT_QUICK_HELP_BTN",
            "contructions/scout_claim_all.btn.png": "SCOUT_CLAIM_ALL_BTN",
        }

        # Alliance templates
        self.alliance_configs = {
            "alliance/war.png": "ALLIANCE_WAR",
            "alliance/no_rally.png": "NO_RALLY",
            "alliance/already_join_rally.png": "ALREADY_JOIN_RALLY",
            "alliance/alliance_help_btn.png": "ALLIANCE_HELP",
            "alliance/alliance_donate_btn.png": "ALLIANCE_DONATE_BTN",
        }
        
        # Icon templates — dedicated detector for locating items/markers with coordinates
        self.icon_configs = {
            "icon_markers/city_rss_gold_full.png": "CITY_RSS_GOLD",
            "icon_markers/city_rss_wood_full.png": "CITY_RSS_WOOD",
            "icon_markers/city_rss_ore_full.png": "CITY_RSS_ORE",
            "icon_markers/city_rss_mana_full.png": "CITY_RSS_MANA",
            "icon_markers/heal_icon.png": "HEALING_ICON",
        }
        
        # Account templates — for swap_account flow
        self.account_configs = {
            # Account name templates — add per-account entries here
            # "accounts/account_main.png": "ACCOUNT_MAIN",
            # "accounts/account_farm1.png": "ACCOUNT_FARM1",
        }

        # ── OPT-1: ROI hints per template ──
        # Format: "filename.png" -> (x1, y1, x2, y2)
        # Only scan this screen region for matching (massive speedup)
        # If a template is NOT listed here, full screen is scanned (safe default)
        # 
        # HOW TO ADD ROIs:
        #   1. Run collect_unknown_states.py to capture screenshots
        #   2. Open screenshot, note the (x, y) region where the template icon appears
        #   3. Add entry here with some padding (50-100px margin)
        #
        # Screen resolution: 960 x 540
        self.roi_hints = {
            # Lobby indicators — bottom-left area
            # "lobby_hammer.png": (0, 380, 250, 540),
            # "lobby_magnifier.png": (0, 380, 250, 540),
            # "lobby_mini_magnifier.png": (0, 380, 250, 540),
            # "lobby_out_city_icon.png": (0, 380, 250, 540),
            # Profile — top-left area
            # "lobby_profile_menu.png": (0, 0, 250, 120),
            # "lobby_profile_detail.png": (0, 0, 250, 120),
            # "lobby_profile.png": (0, 0, 250, 120),
            # Pet capture — bottom button area only
            "pets/Auto-capture_in_progress.png": (305, 411, 761, 509),
            "pets/Auto-capture_start_icon.png": (305, 411, 761, 509),
        }

        self._load_templates()

    # ── OPT-4: Unified template loader ──

    def _load_template_group(self, configs: dict, target_dict: dict, label: str):
        """Generic template loader for any category. Stores color + grayscale + ROI."""
        loaded = 0
        for filename, name in configs.items():
            path = os.path.join(self.templates_dir, filename)
            if not os.path.exists(path):
                print(f"[WARNING] {label} template missing: {path}")
                continue

            img = cv2.imread(path, cv2.IMREAD_COLOR)
            if img is None:
                print(f"[ERROR] Failed to load: {path}")
                continue

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            roi = self.roi_hints.get(filename)

            target_dict.setdefault(name, []).append({
                "color": img,
                "gray": gray,
                "roi": roi,
            })
            loaded += 1

        if loaded > 0:
            print(f"[INFO] Loaded {loaded} {label} templates.")

    def _load_templates(self):
        print("[INFO] Pre-loading image templates into RAM...")
        self._load_template_group(self.state_configs, self.templates, "State")
        self._load_template_group(self.construction_configs, self.construction_templates, "Construction")
        self._load_template_group(self.special_configs, self.special_templates, "Special")
        self._load_template_group(self.activity_configs, self.activity_templates, "Activity")
        self._load_template_group(self.alliance_configs, self.alliance_templates, "Alliance")
        self._load_template_group(self.icon_configs, self.icon_templates, "Icon")
        self._load_template_group(self.account_configs, self.account_templates, "Account")
        print("[INFO] Template loading complete.")

    # ── Screencap ──

    def screencap_memory(self, serial: str) -> np.ndarray:
        """Captures screen directly to RAM with caching (OPT-5b)."""
        # Return cached screenshot if fresh enough
        now = time.time() * 1000
        if self._screen_cache is not None and (now - self._screen_cache_time) < self._SCREEN_CACHE_MAX_AGE_MS:
            return self._screen_cache

        cmd = [self.adb_path, "-s", serial, "exec-out", "screencap", "-p"]
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        try:
            result = subprocess.run(cmd, capture_output=True, startupinfo=startupinfo, timeout=5)
            if not result.stdout:
                return None
                
            image_array = np.frombuffer(result.stdout, np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            # Update cache
            self._screen_cache = img
            self._screen_gray_cache = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img is not None else None
            self._screen_cache_time = time.time() * 1000
            return img
        except subprocess.TimeoutExpired:
            print(f"[WARNING] Screencap timeout on {serial}")
            return None
        except Exception as e:
            print(f"[ERROR] Screencap failed on {serial}: {e}")
            return None

    def _get_gray(self, screen: np.ndarray) -> np.ndarray:
        """Get grayscale version of screen, using cache if available."""
        if self._screen_cache is not None and screen is self._screen_cache and self._screen_gray_cache is not None:
            return self._screen_gray_cache
        return cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)

    # ── Core matching engine (OPT-1 ROI + OPT-2 Grayscale) ──

    def _match_single(self, screen_gray: np.ndarray, entry: dict, threshold: float):
        """
        Match one template entry against screen. Uses grayscale + ROI.
        Returns (max_val, max_loc_on_screen).
        max_loc is adjusted to absolute screen coordinates if ROI was used.
        """
        tmpl_gray = entry["gray"]
        roi = entry.get("roi")

        if roi:
            x1, y1, x2, y2 = roi
            region = screen_gray[y1:y2, x1:x2]
            # Safety: ROI must be larger than template
            if region.shape[0] < tmpl_gray.shape[0] or region.shape[1] < tmpl_gray.shape[1]:
                region = screen_gray
                roi = None  # Fallback to full screen
        else:
            region = screen_gray

        # Safety: region must be larger than template for matchTemplate
        if region.shape[0] < tmpl_gray.shape[0] or region.shape[1] < tmpl_gray.shape[1]:
            return 0.0, (0, 0)

        res = cv2.matchTemplate(region, tmpl_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        # Adjust coordinates to absolute screen position
        if roi:
            max_loc = (max_loc[0] + roi[0], max_loc[1] + roi[1])

        return max_val, max_loc

    # ── Internal _from_screen methods ──

    def _match_state_from_screen(self, screen: np.ndarray, threshold: float = 0.8) -> str:
        """Core state matching with early-exit cache (OPT-3) + grayscale (OPT-2) + ROI (OPT-1)."""
        screen_gray = self._get_gray(screen)

        # OPT-3: Try last matched state FIRST (high hit rate in steady states)
        if self._last_matched_state and self._last_matched_state in self.templates:
            for entry in self.templates[self._last_matched_state]:
                max_val, _ = self._match_single(screen_gray, entry, threshold)
                if max_val >= threshold:
                    return self._last_matched_state

        # Full priority scan
        priority_checks = [
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

        for state_name in priority_checks:
            if state_name == self._last_matched_state:
                continue  # Already checked above
            if state_name in self.templates:
                for entry in self.templates[state_name]:
                    max_val, _ = self._match_single(screen_gray, entry, threshold)
                    if max_val >= threshold:
                        self._last_matched_state = state_name
                        return state_name

        base_states = ["IN-GAME LOBBY (IN_CITY)", "IN-GAME LOBBY (OUT_CITY)"]
        for state_name in base_states:
            if state_name == self._last_matched_state:
                continue
            if state_name in self.templates:
                for entry in self.templates[state_name]:
                    max_val, _ = self._match_single(screen_gray, entry, threshold)
                    if max_val >= threshold:
                        self._last_matched_state = state_name
                        return state_name

        self._last_matched_state = None  # Clear cache on miss
        return "UNKNOWN / TRANSITION"

    def _match_construction_from_screen(self, screen: np.ndarray, target: str = None, threshold: float = 0.8) -> str:
        """Construction matching with grayscale + ROI."""
        screen_gray = self._get_gray(screen)
        if target:
            if target not in self.construction_templates:
                return None
            checks = {target: self.construction_templates[target]}
        else:
            checks = self.construction_templates
        for name, entries in checks.items():
            for entry in entries:
                max_val, _ = self._match_single(screen_gray, entry, threshold)
                if max_val >= threshold:
                    return name
        return None

    def _match_special_from_screen(self, screen: np.ndarray, target: str = None, threshold: float = 0.8) -> str:
        """Special state matching with grayscale + ROI."""
        screen_gray = self._get_gray(screen)
        if target:
            if target not in self.special_templates:
                return None
            checks = {target: self.special_templates[target]}
        else:
            checks = self.special_templates
        for name, entries in checks.items():
            for entry in entries:
                max_val, _ = self._match_single(screen_gray, entry, threshold)
                if max_val >= threshold:
                    return name
        return None

    # ── Public API methods ──

    def get_frame(self, serial: str) -> np.ndarray:
        """Capture and return the current screen frame (alias for screencap_memory)."""
        return self.screencap_memory(serial)

    def check_state(self, serial: str, threshold: float = 0.8) -> str:
        """Determines the current game state via OpenCV Template Matching."""
        screen = self.screencap_memory(serial)
        if screen is None:
            return "ERROR_CAPTURE"
        return self._match_state_from_screen(screen, threshold)

    def check_state_full(self, serial: str, threshold: float = 0.8) -> dict:
        """
        Comprehensive state check. Single screencap, checks ALL categories.
        Returns dict with: state, construction, special, screen (numpy array).
        """
        screen = self.screencap_memory(serial)
        if screen is None:
            return {"state": "ERROR_CAPTURE", "construction": None, "special": None, "screen": None}

        state = self._match_state_from_screen(screen, threshold)
        construction = None
        special = None

        if state == "UNKNOWN / TRANSITION":
            construction = self._match_construction_from_screen(screen, threshold=threshold)
            if not construction:
                special = self._match_special_from_screen(screen, threshold=threshold)

        return {"state": state, "construction": construction, "special": special, "screen": screen}

    def is_menu_expanded(self, serial: str, threshold: float = 0.8) -> bool:
        """Checks if the expandable lobby menu is currently open."""
        if "LOBBY_MENU_EXPANDED" not in self.templates:
            return False
        screen = self.screencap_memory(serial)
        if screen is None:
            return False
        screen_gray = self._get_gray(screen)
        for entry in self.templates["LOBBY_MENU_EXPANDED"]:
            max_val, _ = self._match_single(screen_gray, entry, threshold)
            if max_val >= threshold:
                return True
        return False

    def check_construction(self, serial: str, target: str = None, threshold: float = 0.8) -> str:
        """Checks for construction buildings. Returns matched name or None."""
        screen = self.screencap_memory(serial)
        if screen is None:
            return None
        return self._match_construction_from_screen(screen, target, threshold)

    def check_special_state(self, serial: str, target: str = None, threshold: float = 0.8, frame=None) -> str:
        """Checks for special screens (e.g. Server Maintenance). Returns matched name or None.
        If frame is provided, uses it instead of capturing a new screenshot."""
        screen = frame if frame is not None else self.screencap_memory(serial)
        if screen is None:
            return None
        return self._match_special_from_screen(screen, target, threshold)

    def check_activity(self, serial: str, target: str = None, threshold: float = 0.98, frame=None) -> tuple:
        """
        Activity Detector — finds a template on screen and returns its name + center coordinates.
        Returns: (name, center_x, center_y) if found, or None if not found.
        If frame is provided, uses it instead of capturing a new screenshot.
        """
        screen = frame if frame is not None else self.screencap_memory(serial)
        if screen is None:
            return None
        screen_gray = self._get_gray(screen)

        if target:
            if target not in self.activity_templates:
                return None
            checks = {target: self.activity_templates[target]}
        else:
            checks = self.activity_templates
        
        for name, entries in checks.items():
            for entry in entries:
                max_val, max_loc = self._match_single(screen_gray, entry, threshold)
                if max_val >= threshold:
                    h, w = entry["gray"].shape[:2]
                    center_x = max_loc[0] + w // 2
                    center_y = max_loc[1] + h // 2
                    print(f"[ACTIVITY] '{name}' found at center ({center_x}, {center_y}) | confidence: {max_val:.3f}")
                    return (name, center_x, center_y)
                
        return None

    def find_all_activity_matches(self, serial: str, target: str, threshold: float = 0.8) -> list:
        """
        Multi-match activity detector with Non-Maximum Suppression.
        Returns ALL matching positions for a given target template.
        Used for counting BUILD buttons and detecting multiple GO buttons.

        Returns: list of (center_x, center_y) tuples, sorted top-to-bottom.
        """
        screen = self.screencap_memory(serial)
        if screen is None:
            return []
        screen_gray = self._get_gray(screen)

        if target not in self.activity_templates:
            print(f"[ACTIVITY-MULTI] Target '{target}' not found in activity_templates.")
            return []

        results = []
        entries = self.activity_templates[target]

        for entry in entries:
            tmpl_gray = entry["gray"]
            roi = entry.get("roi")

            if roi:
                x1, y1, x2, y2 = roi
                region = screen_gray[y1:y2, x1:x2]
                if region.shape[0] < tmpl_gray.shape[0] or region.shape[1] < tmpl_gray.shape[1]:
                    region = screen_gray
                    roi = None
            else:
                region = screen_gray

            res = cv2.matchTemplate(region, tmpl_gray, cv2.TM_CCOEFF_NORMED)
            h, w = tmpl_gray.shape[:2]

            # Find all locations above threshold with NMS
            while True:
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                if max_val < threshold:
                    break

                # Calculate absolute center position
                offset_x = roi[0] if roi else 0
                offset_y = roi[1] if roi else 0
                center_x = offset_x + max_loc[0] + w // 2
                center_y = offset_y + max_loc[1] + h // 2
                results.append((center_x, center_y))

                # Suppress this match region (NMS)
                sx = max(0, max_loc[0] - w // 2)
                sy = max(0, max_loc[1] - h // 2)
                ex = min(res.shape[1], max_loc[0] + w // 2 + 1)
                ey = min(res.shape[0], max_loc[1] + h // 2 + 1)
                res[sy:ey, sx:ex] = 0

        # Sort top-to-bottom
        results.sort(key=lambda p: p[1])
        if results:
            print(f"[ACTIVITY-MULTI] '{target}' found {len(results)} match(es): {results}")
        return results

    def check_alliance(self, serial: str, target: str = None, threshold: float = 0.98) -> tuple:
        """
        Alliance Detector — finds an alliance template on screen and returns its name + center coordinates.
        Returns: (name, center_x, center_y) if found, or None if not found.
        """
        screen = self.screencap_memory(serial)
        if screen is None:
            return None
        screen_gray = self._get_gray(screen)

        if target:
            if target not in self.alliance_templates:
                return None
            checks = {target: self.alliance_templates[target]}
        else:
            checks = self.alliance_templates
        
        for name, entries in checks.items():
            for entry in entries:
                max_val, max_loc = self._match_single(screen_gray, entry, threshold)
                if max_val >= threshold:
                    h, w = entry["gray"].shape[:2]
                    center_x = max_loc[0] + w // 2
                    center_y = max_loc[1] + h // 2
                    print(f"[ALLIANCE] '{name}' found at center ({center_x}, {center_y}) | confidence: {max_val:.3f}")
                    return (name, center_x, center_y)
                
        return None

    def locate_icon(self, serial: str, target: str = None, threshold: float = 0.8) -> tuple:
        """
        Icon/Marker Detector — finds a template on screen and returns its name + center coordinates.
        Returns: (name, center_x, center_y) if found, or None if not found.
        """
        screen = self.screencap_memory(serial)
        if screen is None:
            return None
        screen_gray = self._get_gray(screen)

        if target:
            if target not in self.icon_templates:
                return None
            checks = {target: self.icon_templates[target]}
        else:
            checks = self.icon_templates
        
        for name, entries in checks.items():
            for entry in entries:
                max_val, max_loc = self._match_single(screen_gray, entry, threshold)
                if max_val >= threshold:
                    h, w = entry["gray"].shape[:2]
                    center_x = max_loc[0] + w // 2
                    center_y = max_loc[1] + h // 2
                    print(f"[ICON] '{name}' found at center ({center_x}, {center_y}) | confidence: {max_val:.3f}")
                    return (name, center_x, center_y)
                
        return None

    def check_account_state(self, serial: str, target: str = None, threshold: float = 0.95) -> tuple:
        """
        Account Detector — finds account name template on screen.
        Returns: (name, center_x, center_y) if found, or None if not found.
        """
        screen = self.screencap_memory(serial)
        if screen is None:
            return None
        screen_gray = self._get_gray(screen)

        if target:
            if target not in self.account_templates:
                return None
            checks = {target: self.account_templates[target]}
        else:
            checks = self.account_templates
        
        for name, entries in checks.items():
            for entry in entries:
                max_val, max_loc = self._match_single(screen_gray, entry, threshold)
                if max_val >= threshold:
                    h, w = entry["gray"].shape[:2]
                    center_x = max_loc[0] + w // 2
                    center_y = max_loc[1] + h // 2
                    return (name, center_x, center_y)
                
        return None
