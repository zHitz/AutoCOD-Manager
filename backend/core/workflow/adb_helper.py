"""
ADB Helper — Low-level ADB command wrapper.
Copied from TEST/WORKFLOW/adb_helper.py with import paths adapted for app context.
"""
import subprocess
import time
from backend.config import config


def _run_adb(cmd_list: list[str], serial: str = None) -> str:
    """Execute an ADB command and return stdout."""
    try:
        base = [config.adb_path]
        if serial:
            base += ["-s", serial]
        base += cmd_list

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        result = subprocess.run(
            base,
            capture_output=True,
            text=True,
            startupinfo=startupinfo,
            timeout=30,
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return ""
    except Exception as e:
        print(f"[ADB] Error: {e}")
        return ""


def list_devices() -> list[str]:
    """Get list of connected ADB device serials."""
    out = _run_adb(["devices"])
    serials = []
    for line in out.split("\n")[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            serials.append(parts[0])
    return sorted(serials)


def ping_device(serial: str) -> bool:
    """Check if a device is responsive via ADB shell echo."""
    try:
        result = _run_adb(["shell", "echo", "ping"], serial=serial)
        return "ping" in result
    except Exception:
        return False


def tap(serial: str, x: int, y: int):
    """Send tap event to device."""
    _run_adb(["shell", "input", "tap", str(x), str(y)], serial=serial)


def swipe(serial: str, x1: int, y1: int, x2: int, y2: int, duration: int = 300):
    """Send swipe event to device."""
    _run_adb(
        ["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration)],
        serial=serial,
    )


def press_back(serial: str):
    """Send BACK key event."""
    _run_adb(["shell", "input", "keyevent", "4"], serial=serial)


def press_back_n(serial: str, count: int = 1, delay: float = 1.5):
    """Send BACK key event multiple times with delay."""
    for _ in range(count):
        press_back(serial)
        time.sleep(delay)


def screencap(serial: str, local_path: str) -> bool:
    """Capture screenshot from device and pull to local path.

    Returns True on success.
    """
    try:
        # Using exec-out to bypass the shell's CRLF line ending conversions
        # and avoid writing an intermediate file to /sdcard/
        cmd = [config.adb_path, "-s", serial, "exec-out", "screencap", "-p"]
        
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            startupinfo=startupinfo,
            timeout=15,
        )
        
        if result.returncode == 0 and len(result.stdout) > 0:
            with open(local_path, "wb") as f:
                f.write(result.stdout)
            return True
        else:
            print(f"[ADB] Screencap returned code {result.returncode}, len {len(result.stdout)}")
            return False
            
    except Exception as e:
        print(f"[ADB] Screencap failed for {serial}: {e}")
        return False
