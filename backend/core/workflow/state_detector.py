"""
Game State Detector — OpenCV template matching for game state detection.
Copied from TEST/WORKFLOW/state_detector.py (unchanged logic).
"""
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
        
        # State definitions mapping filenames to logical states
        self.state_configs = {
            "lobby_loading.png": "LOADING SCREEN",
            "lobby_profile_detail.png": "IN-GAME LOBBY (PROFILE MENU DETAIL)",
            "lobby_profile_menu.png": "IN-GAME LOBBY (PROFILE MENU)",
            "lobby_events.png": "IN-GAME LOBBY (EVENTS MENU)",
            "lobby_hammer.png": "IN-GAME LOBBY (IN_CITY)",
            "lobby_magnifier.png": "IN-GAME LOBBY (OUT_CITY)"
        }
        
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
                self.templates[state_name] = img
                # print(f"  -> Loaded: {filename} mapped to '{state_name}'")
            else:
                print(f"[ERROR] Failed to load OpenCV image from: {path}")

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
            "LOADING SCREEN",
            "IN-GAME LOBBY (PROFILE MENU DETAIL)",
            "IN-GAME LOBBY (PROFILE MENU)", 
            "IN-GAME LOBBY (EVENTS MENU)"
        ]
        
        for state_name in priority_checks:
            if state_name in self.templates:
                template = self.templates[state_name]
                res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                if max_val >= threshold:
                    return state_name
                    
        # Check standard Lobby States (Hammer/Magnifier)
        base_states = ["IN-GAME LOBBY (IN_CITY)", "IN-GAME LOBBY (OUT_CITY)"]
        for state_name in base_states:
            if state_name in self.templates:
                template = self.templates[state_name]
                res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                if max_val >= threshold:
                    return state_name

        return "UNKNOWN / TRANSITION"
