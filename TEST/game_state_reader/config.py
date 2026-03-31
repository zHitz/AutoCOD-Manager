"""Runtime configuration helpers for the PET SANCTUARY reader."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from backend.config import config as app_config


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACTS_ROOT = Path(__file__).resolve().parent / "artifacts"
DEFAULT_TEMPLATES_DIR = PROJECT_ROOT / "backend" / "core" / "workflow" / "templates"


def load_app_config():
    """Ensure the shared app config singleton is loaded before use."""
    if not app_config.is_loaded:
        app_config.load()
    return app_config


@dataclass(slots=True)
class ResearchConfig:
    """Resolved runtime settings for the PET SANCTUARY reader."""

    adb_path: str
    resolution: str
    serial: str
    artifacts_root: Path
    templates_dir: Path

    @classmethod
    def from_app_config(cls, serial: str, output_dir: str | None = None) -> "ResearchConfig":
        cfg = load_app_config()
        artifacts_root = Path(output_dir) if output_dir else DEFAULT_ARTIFACTS_ROOT
        return cls(
            adb_path=cfg.adb_path,
            resolution=cfg.resolution,
            serial=serial,
            artifacts_root=artifacts_root,
            templates_dir=DEFAULT_TEMPLATES_DIR,
        )

    def create_run_dir(self) -> Path:
        """Create a timestamped artifact directory for a single run."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = self.artifacts_root / self.serial / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir
