"""
Emulator State Machine & Manager
Enhanced emulator management with status tracking, locking, and health checks.
"""
import os
import time
import threading
from backend.core import adb_helper
from backend.config import config


class EmulatorStatus:
    ONLINE = "ONLINE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"
    ERROR = "ERROR"


class Emulator:
    """Represents a single emulator instance with state management."""

    def __init__(self, serial: str):
        self.serial = serial
        self.status = EmulatorStatus.ONLINE
        self.lock = threading.Lock()
        self.last_activity = time.time()
        self.error_msg = ""
        self.current_task = None

        # Screenshot storage
        self.temp_dir = os.path.join(config.work_dir, "debug")
        os.makedirs(self.temp_dir, exist_ok=True)
        self.screenshot_path = os.path.join(self.temp_dir, f"screen_{serial}.png")

    def acquire(self, task_name: str = "unknown") -> bool:
        """Try to lock the emulator for a task."""
        if self.lock.acquire(blocking=False):
            self.status = EmulatorStatus.BUSY
            self.last_activity = time.time()
            self.current_task = task_name
            return True
        return False

    def release(self):
        """Unlock the emulator after task completion."""
        self.status = EmulatorStatus.ONLINE
        self.current_task = None
        try:
            self.lock.release()
        except RuntimeError:
            pass  # Already released

    def ping(self) -> bool:
        """Check if device is responsive."""
        alive = adb_helper.ping_device(self.serial)
        if not alive:
            self.status = EmulatorStatus.OFFLINE
        elif self.status == EmulatorStatus.OFFLINE:
            self.status = EmulatorStatus.ONLINE
        return alive

    def check_timeout(self, max_seconds: int = 120) -> bool:
        """Check if a running task has exceeded its timeout."""
        if self.status != EmulatorStatus.BUSY:
            return False
        elapsed = time.time() - self.last_activity
        if elapsed > max_seconds:
            self.status = EmulatorStatus.ERROR
            self.error_msg = f"Task timeout after {int(elapsed)}s"
            try:
                self.lock.release()
            except RuntimeError:
                pass
            return True
        return False

    def capture(self) -> str | None:
        """Capture screenshot via ADB. Returns file path on success."""
        success = adb_helper.screencap(self.serial, self.screenshot_path)
        if success and os.path.exists(self.screenshot_path):
            return self.screenshot_path
        self.error_msg = "Screenshot capture failed"
        return None

    def to_dict(self) -> dict:
        """Serialize emulator state for API response."""
        return {
            "serial": self.serial,
            "status": self.status,
            "current_task": self.current_task,
            "error_msg": self.error_msg,
            "last_activity": self.last_activity,
        }


class EmulatorManager:
    """Registry and lifecycle manager for all emulators."""

    def __init__(self):
        self._instances: dict[str, Emulator] = {}
        self._lock = threading.Lock()

    def get(self, serial: str) -> Emulator:
        """Get or create an emulator instance."""
        with self._lock:
            if serial not in self._instances:
                self._instances[serial] = Emulator(serial)
            return self._instances[serial]

    def get_all(self) -> list[Emulator]:
        """Get all registered emulators."""
        return list(self._instances.values())

    def get_online(self) -> list[Emulator]:
        """Get all ONLINE emulators."""
        return [e for e in self._instances.values() if e.status == EmulatorStatus.ONLINE]

    def discover(self) -> list[Emulator]:
        """Refresh device list from ADB and update registry."""
        serials = adb_helper.list_devices()

        # Mark missing devices as OFFLINE
        with self._lock:
            for serial, emu in self._instances.items():
                if serial not in serials and emu.status != EmulatorStatus.BUSY:
                    emu.status = EmulatorStatus.OFFLINE

        # Register new devices
        result = []
        for serial in serials:
            emu = self.get(serial)
            if emu.status == EmulatorStatus.OFFLINE:
                emu.status = EmulatorStatus.ONLINE
            result.append(emu)

        return result

    def health_check(self) -> dict:
        """Ping all registered emulators, return health summary."""
        summary = {"total": 0, "online": 0, "busy": 0, "offline": 0, "error": 0}
        for emu in self._instances.values():
            summary["total"] += 1
            emu.check_timeout()  # Auto-detect stuck tasks
            if emu.status == EmulatorStatus.BUSY:
                summary["busy"] += 1
            elif emu.status == EmulatorStatus.ERROR:
                summary["error"] += 1
            elif emu.ping():
                summary["online"] += 1
            else:
                summary["offline"] += 1
        return summary


# Global singleton
emulator_manager = EmulatorManager()
