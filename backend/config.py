"""
Configuration Manager
Loads and validates config from config.yaml, exposes via singleton.
"""
import os
import yaml
from pathlib import Path


# Resolve paths relative to the project root (UI_MANAGER/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


class AppConfig:
    """Singleton configuration manager."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def load(self, config_path: str = None):
        """Load configuration from YAML file."""
        path = Path(config_path) if config_path else CONFIG_PATH
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.adb_path = data.get("adb_path", r"C:\LDPlayer\LDPlayer9\adb.exe")
        self.tesseract_path = data.get(
            "tesseract_path", r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        )
        self.resolution = data.get("resolution", "960x540")
        self.coordinate_map = data.get("coordinate_map", "960x540_v1")
        self.work_dir = data.get("work_dir", str(PROJECT_ROOT.parent))
        self.debug_screenshots = data.get("debug_screenshots", True)
        self.db_path = data.get("db_path", "data/cod_manager.db")
        self.server_port = data.get("server_port", 8000)

        # Resolve relative db_path to absolute
        if not os.path.isabs(self.db_path):
            self.db_path = str(PROJECT_ROOT / self.db_path)

        # Ensure directories exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        debug_dir = os.path.join(self.work_dir, "debug")
        os.makedirs(debug_dir, exist_ok=True)

        self._loaded = True
        return self

    @property
    def is_loaded(self):
        return self._loaded

    def get_coordinate_map_path(self) -> str:
        return str(
            PROJECT_ROOT / "data" / "coordinate_maps" / f"{self.coordinate_map}.json"
        )

    def to_dict(self) -> dict:
        """Serialize config for API response."""
        return {
            "adb_path": self.adb_path,
            "tesseract_path": self.tesseract_path,
            "resolution": self.resolution,
            "coordinate_map": self.coordinate_map,
            "work_dir": self.work_dir,
            "debug_screenshots": self.debug_screenshots,
            "server_port": self.server_port,
        }


# Global singleton
config = AppConfig()
