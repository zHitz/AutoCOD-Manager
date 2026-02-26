"""
Game Navigator — Screen navigation sequences.
Extracted from cod_app_sync.py, driven by coordinate map data.
"""
import json
import os
import time
from backend.core import adb_helper
from backend.config import config


class GameNavigator:
    """Encapsulates tap/swipe sequences to reach each game screen."""

    def __init__(self):
        self._nav_data = {}
        self._load_navigation()

    def _load_navigation(self):
        """Load navigation sequences from coordinate map."""
        map_path = config.get_coordinate_map_path()
        if os.path.exists(map_path):
            with open(map_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._nav_data = data.get("navigation", {})

    def _execute_steps(self, serial: str, steps: list):
        """Execute a navigation sequence on a device."""
        for step in steps:
            action = step.get("action")
            wait = step.get("wait", 1.0)

            if action == "tap":
                adb_helper.tap(serial, step["x"], step["y"])
            elif action == "swipe":
                repeat = step.get("repeat", 1)
                for _ in range(repeat):
                    adb_helper.swipe(
                        serial,
                        step["x1"], step["y1"],
                        step["x2"], step["y2"],
                        step.get("duration", 300),
                    )
                    time.sleep(wait)
                continue  # Skip the final sleep since swipe has its own
            time.sleep(wait)

    def navigate_to(self, serial: str, screen: str) -> bool:
        """Navigate to a specific game screen.

        Args:
            serial: Device serial
            screen: Screen name (profile, resources, hall, market, pet)

        Returns:
            True if navigation was attempted
        """
        nav = self._nav_data.get(screen)
        if not nav:
            print(f"[Navigator] Unknown screen: {screen}")
            return False

        steps = nav.get("steps", [])
        self._execute_steps(serial, steps)
        return True

    def go_back(self, serial: str, screen: str):
        """Exit from a screen using configured back count."""
        nav = self._nav_data.get(screen, {})
        backs = nav.get("exit_backs", 1)
        adb_helper.press_back_n(serial, count=backs)

    # Convenience methods
    def go_to_profile(self, serial: str):
        return self.navigate_to(serial, "profile")

    def go_to_resources(self, serial: str):
        return self.navigate_to(serial, "resources")

    def go_to_hall(self, serial: str):
        return self.navigate_to(serial, "hall")

    def go_to_market(self, serial: str):
        return self.navigate_to(serial, "market")

    def go_to_pet(self, serial: str):
        return self.navigate_to(serial, "pet")


# Global singleton
navigator = GameNavigator()
