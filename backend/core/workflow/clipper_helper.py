"""
Clipper Helper — ADB Clipper broadcast logic for clipboard access.
Copied from TEST/WORKFLOW/clipper_helper.py (unchanged logic).
"""
import subprocess
import os

def get_clipper_data(adb_path: str, serial: str) -> str:
    """Fetch clipboard data safely using ADB Clipper broadcast logic."""
    cmd = [adb_path, "-s", serial, "shell", "am", "broadcast", "-a", "clipper.get"]
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, timeout=5)
        for line in result.stdout.strip().split('\n'):
            if "data=" in line:
                parts = line.split('data="')
                if len(parts) > 1:
                    data = parts[1].split('"')[0]
                    return data
    except Exception as e:
        print(f"[ERROR] Clipper Helper failed on {serial}: {e}")
    return ""

def is_app_foreground(adb_path: str, serial: str, package_name: str) -> bool:
    """Check if the target app is currently running in the foreground."""
    cmd = [adb_path, "-s", serial, "shell", "dumpsys", "window", "windows"]
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, timeout=5)
        for line in result.stdout.split('\n'):
            if "mCurrentFocus" in line or "mFocusedApp" in line:
                if package_name in line:
                    return True
        return False
    except Exception:
        return False

def open_app(adb_path: str, serial: str, package_name: str):
    """Launch the application using monkeys intent."""
    print(f"[INFO] Launching app {package_name} on {serial}...")
    cmd = [adb_path, "-s", serial, "shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"]
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    subprocess.run(cmd, startupinfo=startupinfo, capture_output=True)
