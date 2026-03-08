import os
import cv2
import numpy as np
import subprocess
import time

class GameStateDetector:
    """
    Modular State Detector. 
    Loads templates into RAM once and uses ADB screencap to memory for zero disk I/O.
    """
    def __init__(self, adb_path: str, templates_dir: str):
        self.adb_path = adb_path
        self.templates_dir = templates_dir
        self.templates = {}
        self.construction_templates = {}
        
        # State definitions mapping filenames to logical states
        self.state_configs = {
            "fixing_network.png": "LOADING SCREEN (NETWORK ISSUE)",
            "lobby_loading.png": "LOADING SCREEN",
            "lobby_profile_detail.png": "IN-GAME LOBBY (PROFILE MENU DETAIL)",
            "lobby_profile_menu.png": "IN-GAME LOBBY (PROFILE MENU)",
            "lobby_events.png": "IN-GAME LOBBY (EVENTS MENU)",
            "lobby_hammer.png": "IN-GAME LOBBY (IN_CITY)",
            "lobby_magnifier.png": "IN-GAME LOBBY (OUT_CITY)",
            "lobby_mini_magnifier.png": "IN-GAME LOBBY (OUT_CITY)",
            "lobby_out_city_icon.png": "IN-GAME LOBBY (OUT_CITY)",
            "items_artifacts.png": "IN-GAME ITEMS (ARTIFACTS)",
            "items_resources.png": "IN-GAME ITEMS (RESOURCES)",
            "lobby_icons.png": "LOBBY_MENU_EXPANDED"
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
        }
        
        # Special templates — loaded separately, called on specific conditions
        self.special_configs = {
            "loading_server_maintenance.png": "SERVER_MAINTENANCE",
            "auto_capture_pet.png": "AUTO_CAPTURE_PET",
            "accounts/settings.png": "SETTINGS",
            "accounts/character_management.png": "CHARACTER_MANAGEMENT",
            "special/mail_menu.png": "MAIL_MENU",
            "special/note.png": "NOTE",
        }
        self.special_templates = {}
        
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
        }
        self.activity_templates = {}

        # Alliance templates
        self.alliance_configs = {
            "alliance/war.png": "ALLIANCE_WAR",
            "alliance/no_rally.png": "NO_RALLY",
            "alliance/already_join_rally.png": "ALREADY_JOIN_RALLY",
        }
        self.alliance_templates = {}
        
        # Icon templates — dedicated detector for locating items/markers with coordinates
        self.icon_configs = {
            "icon_markers/city_rss_gold_full.png": "CITY_RSS_GOLD",
            "icon_markers/city_rss_wood_full.png": "CITY_RSS_WOOD",
            "icon_markers/city_rss_ore_full.png": "CITY_RSS_ORE",
            "icon_markers/city_rss_mana_full.png": "CITY_RSS_MANA",
        }
        self.icon_templates = {}
        
        # Account templates — separate detector for swap_account flow
        # Includes screen detection (Settings, CharManagement) and account name templates
        # Returns name + center coordinates when matched (like check_activity)
        self.account_configs = {
            # Screen state templates

            # Account name templates — add per-account entries here
            # Crop account name text from Character Management screen
            # Save to templates/accounts/
            # "accounts/account_main.png": "ACCOUNT_MAIN",
            # "accounts/account_farm1.png": "ACCOUNT_FARM1",
        }
        self.account_templates = {}
        self._load_templates()

    def _load_templates(self):
        print("[INFO] Pre-loading image templates into RAM...")
        for filename, state_name in self.state_configs.items():
            path = os.path.join(self.templates_dir, filename)
            if not os.path.exists(path):
                print(f"[ERROR] Template missing: {path}")
                continue
            
            img = cv2.imread(path, cv2.IMREAD_COLOR)
            if img is not None:
                if state_name not in self.templates:
                    self.templates[state_name] = []
                self.templates[state_name].append(img)
            else:
                print(f"[ERROR] Failed to load OpenCV image from: {path}")
        
        # Load construction templates separately
        for filename, name in self.construction_configs.items():
            path = os.path.join(self.templates_dir, filename)
            if not os.path.exists(path):
                print(f"[WARNING] Construction template missing: {path}")
                continue
            img = cv2.imread(path, cv2.IMREAD_COLOR)
            if img is not None:
                if name not in self.construction_templates:
                    self.construction_templates[name] = []
                self.construction_templates[name].append(img)
                
        # Load special templates separately
        for filename, name in self.special_configs.items():
            path = os.path.join(self.templates_dir, filename)
            if not os.path.exists(path):
                print(f"[WARNING] Special template missing: {path}")
                continue
            img = cv2.imread(path, cv2.IMREAD_COLOR)
            if img is not None:
                if name not in self.special_templates:
                    self.special_templates[name] = []
                self.special_templates[name].append(img)

        # Load activity templates separately
        for filename, name in self.activity_configs.items():
            path = os.path.join(self.templates_dir, filename)
            if not os.path.exists(path):
                print(f"[WARNING] Activity template missing: {path}")
                continue
            img = cv2.imread(path, cv2.IMREAD_COLOR)
            if img is not None:
                if name not in self.activity_templates:
                    self.activity_templates[name] = []
                self.activity_templates[name].append(img)
                
        # Load alliance templates separately
        for filename, name in self.alliance_configs.items():
            path = os.path.join(self.templates_dir, filename)
            if not os.path.exists(path):
                print(f"[WARNING] Alliance template missing: {path}")
                continue
            img = cv2.imread(path, cv2.IMREAD_COLOR)
            if img is not None:
                if name not in self.alliance_templates:
                    self.alliance_templates[name] = []
                self.alliance_templates[name].append(img)
                
        # Load icon templates separately
        for filename, name in self.icon_configs.items():
            path = os.path.join(self.templates_dir, filename)
            if not os.path.exists(path):
                print(f"[WARNING] Icon template missing: {path}")
                continue
            img = cv2.imread(path, cv2.IMREAD_COLOR)
            if img is not None:
                if name not in self.icon_templates:
                    self.icon_templates[name] = []
                self.icon_templates[name].append(img)

        # Load account templates separately
        for filename, name in self.account_configs.items():
            path = os.path.join(self.templates_dir, filename)
            if not os.path.exists(path):
                print(f"[WARNING] Account template missing: {path}")
                continue
            img = cv2.imread(path, cv2.IMREAD_COLOR)
            if img is not None:
                if name not in self.account_templates:
                    self.account_templates[name] = []
                self.account_templates[name].append(img)

    def screencap_memory(self, serial: str) -> np.ndarray:
        """Captures screen directly to RAM, no disk IO. Faster and cleaner for Multi-Emulator."""
        cmd = [self.adb_path, "-s", serial, "exec-out", "screencap", "-p"]
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        try:
            result = subprocess.run(cmd, capture_output=True, startupinfo=startupinfo, timeout=5)
            if not result.stdout:
                return None
                
            image_array = np.frombuffer(result.stdout, np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            return img
        except subprocess.TimeoutExpired:
            print(f"[WARNING] Screencap timeout on {serial}")
            return None
        except Exception as e:
            print(f"[ERROR] Screencap failed on {serial}: {e}")
            return None

    def check_state(self, serial: str, threshold: float = 0.8) -> str:
        """Determines the current game state via OpenCV Template Matching."""
        screen = self.screencap_memory(serial)
        
        if screen is None:
            return "ERROR_CAPTURE"

        # Check in priority order: Loading screens mask everything else
        priority_checks = [
            "LOADING SCREEN (NETWORK ISSUE)",
            "LOADING SCREEN",
            "IN-GAME LOBBY (PROFILE MENU DETAIL)",
            "IN-GAME LOBBY (PROFILE MENU)", 
            "IN-GAME LOBBY (EVENTS MENU)",
            "IN-GAME ITEMS (ARTIFACTS)",
            "IN-GAME ITEMS (RESOURCES)"
        ]
        
        for state_name in priority_checks:
            if state_name in self.templates:
                for template in self.templates[state_name]:
                    res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(res)
                    if max_val >= threshold:
                        return state_name
                    
        # Check standard Lobby States (Hammer/Magnifier)
        base_states = ["IN-GAME LOBBY (IN_CITY)", "IN-GAME LOBBY (OUT_CITY)"]
        for state_name in base_states:
            if state_name in self.templates:
                for template in self.templates[state_name]:
                    res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(res)
                    if max_val >= threshold:
                        return state_name

        return "UNKNOWN / TRANSITION"

    def is_menu_expanded(self, serial: str, threshold: float = 0.8) -> bool:
        """Checks if the expandable lobby menu is currently open. Does NOT affect check_state results."""
        if "LOBBY_MENU_EXPANDED" not in self.templates:
            return False
        
        screen = self.screencap_memory(serial)
        if screen is None:
            return False
        
        for template in self.templates["LOBBY_MENU_EXPANDED"]:
            res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            if max_val >= threshold:
                return True
        return False

    def check_construction(self, serial: str, target: str = None, threshold: float = 0.8) -> str:
        """
        Checks for construction buildings on screen. Separate from check_state to keep it lightweight.
        If target is specified, only checks that specific construction (e.g. 'HALL').
        Returns the matched construction name or None.
        """
        screen = self.screencap_memory(serial)
        if screen is None:
            return None
        
        checks = {target: self.construction_templates[target]} if target and target in self.construction_templates else self.construction_templates
        
        for name, templates in checks.items():
            for template in templates:
                res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                if max_val >= threshold:
                    return name
        
        return None

    def check_special_state(self, serial: str, target: str = None, threshold: float = 0.8) -> str:
        """
        Checks for special screens on demand (e.g. Server Maintenance).
        Returns the matched special state name or None.
        """
        screen = self.screencap_memory(serial)
        if screen is None:
            return None
            
        checks = {target: self.special_templates[target]} if target and target in self.special_templates else self.special_templates
        
        for name, templates in checks.items():
            for template in templates:
                res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                if max_val >= threshold:
                    return name
                
        return None

    def check_activity(self, serial: str, target: str = None, threshold: float = 0.98) -> tuple:
        """
        Activity Detector — finds a template on screen and returns its name + center coordinates.
        Unlike other check methods, this returns WHERE the match is, not just WHAT it is.
        
        Returns: (name, center_x, center_y) if found, or None if not found.
        Usage in wait_for_state: check_mode="activity"
        """
        screen = self.screencap_memory(serial)
        if screen is None:
            return None
            
        checks = {target: self.activity_templates[target]} if target and target in self.activity_templates else self.activity_templates
        
        for name, templates in checks.items():
            for template in templates:
                res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                if max_val >= threshold:
                    h, w = template.shape[:2]
                    center_x = max_loc[0] + w // 2
                    center_y = max_loc[1] + h // 2
                    print(f"[ACTIVITY] '{name}' found at center ({center_x}, {center_y}) | confidence: {max_val:.3f}")
                    return (name, center_x, center_y)
                
        return None

    def check_alliance(self, serial: str, target: str = None, threshold: float = 0.98) -> tuple:
        """
        Alliance Detector — finds an alliance template on screen and returns its name + center coordinates.
        Returns: (name, center_x, center_y) if found, or None if not found.
        """
        screen = self.screencap_memory(serial)
        if screen is None:
            return None
            
        checks = {target: self.alliance_templates[target]} if target and target in self.alliance_templates else self.alliance_templates
        
        for name, templates in checks.items():
            for template in templates:
                res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                if max_val >= threshold:
                    h, w = template.shape[:2]
                    center_x = max_loc[0] + w // 2
                    center_y = max_loc[1] + h // 2
                    print(f"[ALLIANCE] '{name}' found at center ({center_x}, {center_y}) | confidence: {max_val:.3f}")
                    return (name, center_x, center_y)
                
        return None

    def locate_icon(self, serial: str, target: str = None, threshold: float = 0.8) -> tuple:
        """
        Icon/Marker Detector — finds a template on screen and returns its name + center coordinates.
        Uses exact same logic as tool_template_locator.py.
        Returns: (name, center_x, center_y) if found, or None if not found.
        """
        screen = self.screencap_memory(serial)
        if screen is None:
            return None
            
        checks = {target: self.icon_templates[target]} if target and target in self.icon_templates else self.icon_templates
        
        for name, templates in checks.items():
            for template in templates:
                res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                if max_val >= threshold:
                    h, w = template.shape[:2]
                    center_x = max_loc[0] + w // 2
                    center_y = max_loc[1] + h // 2
                    print(f"[ICON] '{name}' found at center ({center_x}, {center_y}) | confidence: {max_val:.3f}")
                    return (name, center_x, center_y)
                
        return None
