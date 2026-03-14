import os
import cv2
import numpy as np
import subprocess
import time
from typing import Optional


class GameStateDetector:
    """
    Optimized detector focused on:
    - one shared grayscale capture pipeline
    - ROI-aware template matching
    - lazy loading for non-core template groups
    - optional short-lived frame reuse per serial
    """

    FRAME_CACHE_TTL_SEC = 0.35

    def __init__(self, adb_path: str, templates_dir: str):
        self.adb_path = adb_path
        self.templates_dir = templates_dir

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
            "lobby_icons.png": "LOBBY_MENU_EXPANDED",
        }

        self.construction_configs = {
            "contructions/con_hall.png": "HALL",
            "contructions/con_market.png": "MARKET",
            "contructions/con_elixir_healing.png": "ELIXIR_HEALING",
            "contructions/con_pet_sanctuary.png": "PET_SANCTUARY",
            "contructions/con_pet_enclosure.png": "PET_ENCLOSURE",
            "contructions/con_markers.png": "MARKERS_MENU",
            "contructions/con_alliance_menu.png": "ALLIANCE_MENU",
            "contructions/con_train_units.png": "TRAIN_UNITS",
            "contructions/con_goblin_merchant.png": "GOBLIN_MERCHANT",
            "contructions/shop.png": "SHOP",
            "contructions/con_research_center.png": "RESEARCH_CENTER",
            "contructions/con_tavern.png": "TAVERN",
        }

        self.special_configs = {
            "loading_server_maintenance.png": "SERVER_MAINTENANCE",
            "pets/Auto-capture_in_progress.png": "AUTO_CAPTURE_IN_PROGRESS",
            "pets/Auto-capture_start_icon.png": "AUTO_CAPTURE_START",
            "auto_capture_pet.png": "AUTO_CAPTURE_PET",
            "auto-peacekeeping.png": "AUTO_PEACEKEEPING",
            "accounts/settings.png": "SETTINGS",
            "accounts/character_management.png": "CHARACTER_MANAGEMENT",
            "special/mail_menu.png": "MAIL_MENU",
            "special/note.png": "NOTE",
            "icon_markers/skip.png": "SKIP",
            "research/research_no_resource.png": "RESEARCH_NO_RESOURCE",
            "research/research_no_confirm.png": "RESEARCH_NO_CONFIRM",
        }

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
            "research/research_empty_slot.png": "RESEARCH_EMPTY_SLOT",
            "research/research_confirm.png": "RESEARCH_CONFIRM",
            "research/research_alliance_help.png": "RESEARCH_ALLIANCE_HELP",
            "research/research_use_bag.png": "RESEARCH_USE_BAG",
            # Tavern Chest Draw templates
            "tavern/free_draw_btn.png": "TAVERN_FREE_DRAW",
            "tavern/draw_x10_btn.png": "TAVERN_DRAW_X10",
        }

        self.alliance_configs = {
            "alliance/war.png": "ALLIANCE_WAR",
            "alliance/no_rally.png": "NO_RALLY",
            "alliance/already_join_rally.png": "ALREADY_JOIN_RALLY",
            "alliance/alliance_help_btn.png": "ALLIANCE_HELP",
        }

        self.icon_configs = {
            "icon_markers/city_rss_gold_full.png": "CITY_RSS_GOLD",
            "icon_markers/city_rss_wood_full.png": "CITY_RSS_WOOD",
            "icon_markers/city_rss_ore_full.png": "CITY_RSS_ORE",
            "icon_markers/city_rss_mana_full.png": "CITY_RSS_MANA",
            "icon_markers/healing_icon.png": "HEALING_ICON",
            "icon_markers/merchant_resource_icon.png": "MERCHANT_RESOURCE_ICON",
        }

        self.account_configs = {}

        self.state_roi = {
            "LOADING SCREEN (NETWORK ISSUE)": None,
            "LOADING SCREEN": None,
            "IN-GAME LOBBY (PROFILE MENU DETAIL)": (0.0, 0.0, 1.0, 0.35),
            "IN-GAME LOBBY (PROFILE MENU)": (0.0, 0.0, 1.0, 0.35),
            "IN-GAME LOBBY (EVENTS MENU)": (0.0, 0.0, 1.0, 0.35),
            "IN-GAME ITEMS (ARTIFACTS)": (0.0, 0.0, 1.0, 0.55),
            "IN-GAME ITEMS (RESOURCES)": (0.0, 0.0, 1.0, 0.55),
            "IN-GAME LOBBY (IN_CITY)": (0.0, 0.72, 1.0, 0.28),
            "IN-GAME LOBBY (OUT_CITY)": (0.0, 0.72, 1.0, 0.28),
            "LOBBY_MENU_EXPANDED": (0.0, 0.72, 1.0, 0.28),
        }
        self.construction_roi = {}
        self.special_roi = {
            "AUTO_PEACEKEEPING": (0.104, 0.093, 0.156, 0.463),
        }
        self.activity_roi = {}
        self.alliance_roi = {}
        self.icon_roi = {}
        self.account_roi = {}

        self.templates = {}
        self.construction_templates = {}
        self.special_templates = {}
        self.activity_templates = {}
        self.alliance_templates = {}
        self.icon_templates = {}
        self.account_templates = {}

        self._group_stores = {
            "state": self.templates,
            "construction": self.construction_templates,
            "special": self.special_templates,
            "activity": self.activity_templates,
            "alliance": self.alliance_templates,
            "icon": self.icon_templates,
            "account": self.account_templates,
        }
        self._group_configs = {
            "state": self.state_configs,
            "construction": self.construction_configs,
            "special": self.special_configs,
            "activity": self.activity_configs,
            "alliance": self.alliance_configs,
            "icon": self.icon_configs,
            "account": self.account_configs,
        }
        self._group_labels = {
            "state": "Template",
            "construction": "Construction template",
            "special": "Special template",
            "activity": "Activity template",
            "alliance": "Alliance template",
            "icon": "Icon template",
            "account": "Account template",
        }
        self._group_roi = {
            "state": self.state_roi,
            "construction": self.construction_roi,
            "special": self.special_roi,
            "activity": self.activity_roi,
            "alliance": self.alliance_roi,
            "icon": self.icon_roi,
            "account": self.account_roi,
        }
        self._loaded_groups = set()
        self._frame_cache = {}
        self.perf_stats = {
            "captures": 0,
            "cache_hits": 0,
            "matches": 0,
            "total_capture_ms": 0.0,
            "total_match_ms": 0.0,
        }

        self._load_group("state")

    def _load_group(self, group_name: str) -> None:
        if group_name in self._loaded_groups:
            return

        store = self._group_stores[group_name]
        config = self._group_configs[group_name]
        label = self._group_labels[group_name]

        for filename, logical_name in config.items():
            path = os.path.join(self.templates_dir, filename)
            if not os.path.exists(path):
                level = "ERROR" if group_name == "state" else "WARNING"
                print(f"[{level}] {label} missing: {path}")
                continue

            image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if image is None:
                print(f"[ERROR] Failed to load OpenCV image from: {path}")
                continue

            store.setdefault(logical_name, []).append(image)

        self._loaded_groups.add(group_name)

    def _get_group_templates(self, group_name: str) -> dict:
        self._load_group(group_name)
        return self._group_stores[group_name]

    def invalidate_frame_cache(self, serial: Optional[str] = None) -> None:
        if serial is None:
            self._frame_cache.clear()
            return
        self._frame_cache.pop(serial, None)

    def screencap_memory(self, serial: str) -> Optional[np.ndarray]:
        """Capture screen directly to grayscale memory without disk I/O."""
        cmd = [self.adb_path, "-s", serial, "exec-out", "screencap", "-p"]
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        started = time.perf_counter()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                startupinfo=startupinfo,
                timeout=5,
            )
            if not result.stdout:
                return None

            image_array = np.frombuffer(result.stdout, np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_GRAYSCALE)
            return image
        except subprocess.TimeoutExpired:
            print(f"[WARNING] Screencap timeout on {serial}")
            return None
        except Exception as exc:
            print(f"[ERROR] Screencap failed on {serial}: {exc}")
            return None
        finally:
            self.perf_stats["captures"] += 1
            self.perf_stats["total_capture_ms"] += (time.perf_counter() - started) * 1000.0

    def get_frame(
        self,
        serial: str,
        frame: Optional[np.ndarray] = None,
        use_cache: bool = False,
        max_age_sec: Optional[float] = None,
    ) -> Optional[np.ndarray]:
        if frame is not None:
            return frame

        if not use_cache:
            return self.screencap_memory(serial)

        ttl = self.FRAME_CACHE_TTL_SEC if max_age_sec is None else max_age_sec
        now = time.perf_counter()
        cached = self._frame_cache.get(serial)
        if cached and now - cached["timestamp"] <= ttl:
            self.perf_stats["cache_hits"] += 1
            return cached["frame"]

        fresh = self.screencap_memory(serial)
        if fresh is not None:
            self._frame_cache[serial] = {"frame": fresh, "timestamp": now}
        return fresh

    def _crop_roi(self, screen: np.ndarray, roi: Optional[tuple]) -> tuple[np.ndarray, int, int]:
        if roi is None:
            return screen, 0, 0

        height, width = screen.shape[:2]
        x1 = max(0, int(roi[0] * width))
        y1 = max(0, int(roi[1] * height))
        x2 = min(width, x1 + int(roi[2] * width))
        y2 = min(height, y1 + int(roi[3] * height))

        if x2 <= x1 or y2 <= y1:
            return screen, 0, 0

        return screen[y1:y2, x1:x2], x1, y1

    def _match_templates(
        self,
        screen: np.ndarray,
        templates_by_name: dict,
        roi_map: dict,
        threshold: float,
        target: Optional[str] = None,
        with_coords: bool = False,
        log_prefix: Optional[str] = None,
    ):
        if target and target in templates_by_name:
            checks = [(target, templates_by_name[target])]
        else:
            checks = templates_by_name.items()

        started = time.perf_counter()
        try:
            for name, templates in checks:
                region, offset_x, offset_y = self._crop_roi(screen, roi_map.get(name))
                if region is None or region.size == 0:
                    continue

                for template in templates:
                    template_h, template_w = template.shape[:2]
                    region_h, region_w = region.shape[:2]
                    if template_h > region_h or template_w > region_w:
                        continue

                    result = cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, max_loc = cv2.minMaxLoc(result)
                    self.perf_stats["matches"] += 1
                    if max_val < threshold:
                        continue

                    if not with_coords:
                        return name

                    center_x = offset_x + max_loc[0] + template_w // 2
                    center_y = offset_y + max_loc[1] + template_h // 2
                    if log_prefix:
                        print(
                            f"[{log_prefix}] '{name}' found at center ({center_x}, {center_y}) | confidence: {max_val:.3f}"
                        )
                    return name, center_x, center_y

            return None
        finally:
            self.perf_stats["total_match_ms"] += (time.perf_counter() - started) * 1000.0

    def check_state(
        self,
        serial: str,
        threshold: float = 0.8,
        frame: Optional[np.ndarray] = None,
        use_cache: bool = False,
    ) -> str:
        """Determines the current game state via ROI-aware grayscale matching."""
        screen = self.get_frame(serial, frame=frame, use_cache=use_cache)
        if screen is None:
            return "ERROR_CAPTURE"

        templates = self._get_group_templates("state")
        priority_checks = [
            "LOADING SCREEN (NETWORK ISSUE)",
            "LOADING SCREEN",
            "IN-GAME LOBBY (PROFILE MENU DETAIL)",
            "IN-GAME LOBBY (PROFILE MENU)",
            "IN-GAME LOBBY (EVENTS MENU)",
            "IN-GAME ITEMS (ARTIFACTS)",
            "IN-GAME ITEMS (RESOURCES)",
            "IN-GAME LOBBY (IN_CITY)",
            "IN-GAME LOBBY (OUT_CITY)",
        ]
        ordered_templates = {
            name: templates[name]
            for name in priority_checks
            if name in templates
        }
        match = self._match_templates(
            screen,
            ordered_templates,
            self.state_roi,
            threshold,
        )
        return match or "UNKNOWN / TRANSITION"

    def is_menu_expanded(
        self,
        serial: str,
        threshold: float = 0.8,
        frame: Optional[np.ndarray] = None,
        use_cache: bool = False,
    ) -> bool:
        templates = self._get_group_templates("state")
        if "LOBBY_MENU_EXPANDED" not in templates:
            return False

        screen = self.get_frame(serial, frame=frame, use_cache=use_cache)
        if screen is None:
            return False

        match = self._match_templates(
            screen,
            {"LOBBY_MENU_EXPANDED": templates["LOBBY_MENU_EXPANDED"]},
            self.state_roi,
            threshold,
        )
        return match is not None

    def check_construction(
        self,
        serial: str,
        target: Optional[str] = None,
        threshold: float = 0.8,
        frame: Optional[np.ndarray] = None,
        use_cache: bool = False,
    ) -> Optional[str]:
        screen = self.get_frame(serial, frame=frame, use_cache=use_cache)
        if screen is None:
            return None

        templates = self._get_group_templates("construction")
        normalized_target = target.upper() if isinstance(target, str) else target
        return self._match_templates(
            screen,
            templates,
            self.construction_roi,
            threshold,
            target=normalized_target,
        )

    def check_special_state(
        self,
        serial: str,
        target: Optional[str] = None,
        threshold: float = 0.8,
        frame: Optional[np.ndarray] = None,
        use_cache: bool = False,
    ) -> Optional[str]:
        screen = self.get_frame(serial, frame=frame, use_cache=use_cache)
        if screen is None:
            return None

        templates = self._get_group_templates("special")
        return self._match_templates(
            screen,
            templates,
            self.special_roi,
            threshold,
            target=target,
        )

    def check_activity(
        self,
        serial: str,
        target: Optional[str] = None,
        threshold: float = 0.98,
        frame: Optional[np.ndarray] = None,
        use_cache: bool = False,
    ) -> Optional[tuple]:
        screen = self.get_frame(serial, frame=frame, use_cache=use_cache)
        if screen is None:
            return None

        templates = self._get_group_templates("activity")
        return self._match_templates(
            screen,
            templates,
            self.activity_roi,
            threshold,
            target=target,
            with_coords=True,
            log_prefix="ACTIVITY",
        )

    def check_alliance(
        self,
        serial: str,
        target: Optional[str] = None,
        threshold: float = 0.98,
        frame: Optional[np.ndarray] = None,
        use_cache: bool = False,
    ) -> Optional[tuple]:
        screen = self.get_frame(serial, frame=frame, use_cache=use_cache)
        if screen is None:
            return None

        templates = self._get_group_templates("alliance")
        return self._match_templates(
            screen,
            templates,
            self.alliance_roi,
            threshold,
            target=target,
            with_coords=True,
            log_prefix="ALLIANCE",
        )

    def locate_icon(
        self,
        serial: str,
        target: Optional[str] = None,
        threshold: float = 0.8,
        frame: Optional[np.ndarray] = None,
        use_cache: bool = False,
    ) -> Optional[tuple]:
        screen = self.get_frame(serial, frame=frame, use_cache=use_cache)
        if screen is None:
            return None

        templates = self._get_group_templates("icon")
        return self._match_templates(
            screen,
            templates,
            self.icon_roi,
            threshold,
            target=target,
            with_coords=True,
            log_prefix="ICON",
        )

    def check_account_state(
        self,
        serial: str,
        target: Optional[str] = None,
        threshold: float = 0.8,
        frame: Optional[np.ndarray] = None,
        use_cache: bool = False,
    ) -> Optional[tuple]:
        screen = self.get_frame(serial, frame=frame, use_cache=use_cache)
        if screen is None:
            return None

        templates = self._get_group_templates("account")
        return self._match_templates(
            screen,
            templates,
            self.account_roi,
            threshold,
            target=target,
            with_coords=True,
            log_prefix="ACCOUNT",
        )

