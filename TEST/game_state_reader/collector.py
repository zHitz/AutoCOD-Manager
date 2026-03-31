"""Screenshot and UI hierarchy collection for PET SANCTUARY research."""

from __future__ import annotations

import subprocess
from pathlib import Path

try:
    from .config import ResearchConfig
except ImportError:  # pragma: no cover - direct script execution fallback
    from config import ResearchConfig


REMOTE_XML_PATH = "/sdcard/pet_sanctuary_window_dump.xml"


def _build_startupinfo():
    if not hasattr(subprocess, "STARTUPINFO"):
        return None
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return startupinfo


class HierarchyCollector:
    """Collect screenshot and UI hierarchy evidence from a target emulator."""

    def __init__(self, settings: ResearchConfig):
        self.settings = settings
        self._startupinfo = _build_startupinfo()

    def _run(self, *adb_args: str, timeout: int = 20, text: bool = False):
        cmd = [self.settings.adb_path, "-s", self.settings.serial, *adb_args]
        return subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            text=text,
            startupinfo=self._startupinfo,
        )

    def capture_screenshot(self, output_path: Path) -> bool:
        """Capture a raw PNG screenshot from the emulator."""
        result = self._run("exec-out", "screencap", "-p", timeout=15, text=False)
        if result.returncode != 0 or not result.stdout:
            return False
        output_path.write_bytes(result.stdout)
        return True

    def dump_hierarchy(self, output_path: Path) -> tuple[bool, str]:
        """Run uiautomator dump and persist the resulting XML locally."""
        try:
            dump_result = self._run(
                "shell",
                "uiautomator",
                "dump",
                REMOTE_XML_PATH,
                timeout=20,
                text=True,
            )
        except subprocess.TimeoutExpired:
            return False, "uiautomator dump timed out"

        dump_stdout = (dump_result.stdout or "").strip()
        dump_stderr = (dump_result.stderr or "").strip()
        if dump_result.returncode != 0:
            message = dump_stderr or dump_stdout or "uiautomator dump failed"
            return False, message

        if "dumped to" not in dump_stdout.lower():
            message = dump_stdout or dump_stderr or "uiautomator dump did not report success"
            return False, message

        try:
            cat_result = self._run("exec-out", "cat", REMOTE_XML_PATH, timeout=15, text=False)
        except subprocess.TimeoutExpired:
            return False, "cat remote hierarchy file timed out"

        if cat_result.returncode != 0 or not cat_result.stdout:
            message = (cat_result.stderr or b"").decode("utf-8", errors="replace").strip()
            return False, message or "remote hierarchy XML was empty"

        output_path.write_bytes(cat_result.stdout)
        return True, dump_stdout
