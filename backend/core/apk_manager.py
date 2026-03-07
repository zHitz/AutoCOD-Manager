"""
APK Manager — Download and install APK files on emulators via ADB.

Provides a registry of known apps, download management, and ADB install commands.
APK files are stored in data/apks/.
"""

import os
import subprocess
import urllib.request
from pathlib import Path

from backend.config import config

# APK storage directory
APK_DIR = (
    Path(os.path.dirname(os.path.abspath(__file__))).parent.parent / "data" / "apks"
)
APK_DIR.mkdir(parents=True, exist_ok=True)

# ── App Registry ──
# Each entry defines an installable app with optional download URL and post-install commands.
APK_REGISTRY = {
    "clipper": {
        "id": "clipper",
        "name": "ADB Clipper",
        "package": "ca.zgrs.clipper",
        "version": "1.2.1",
        "size": "45 KB",
        "note": "Clipboard access helper — required for ID extraction workflow",
        "download_url": "https://github.com/majido/clipper/releases/download/v1.2.1/clipper.apk",
        "filename": "clipper.apk",
        "post_install": [
            "shell",
            "am",
            "startservice",
            "ca.zgrs.clipper/.ClipboardService",
        ],
    },
    "zarchiver": {
        "id": "zarchiver",
        "name": "ZArchiver",
        "package": "ru.zdevs.zarchiver",
        "version": "1.0.10",
        "size": "5.4 MB",
        "note": "Extract files inside emulator",
        "download_url": None,
        "filename": "zarchiver.apk",
        "post_install": None,
    },
    "gspace": {
        "id": "gspace",
        "name": "GSpace",
        "package": "com.gspace.android",
        "version": "2.2.9",
        "size": "18.2 MB",
        "note": "Google services helper for non-GMS emulators",
        "download_url": None,
        "filename": "gspace.apk",
        "post_install": None,
    },
    "quicktouch": {
        "id": "quicktouch",
        "name": "QuickTouch Auto Clicker",
        "package": "simplehat.clicker",
        "version": "4.8.3",
        "size": "9.1 MB",
        "note": "Optional auto-tap support",
        "download_url": None,
        "filename": "quicktouch.apk",
        "post_install": None,
    },
}


def get_apk_list() -> list[dict]:
    """Return all registered APKs with download status."""
    result = []
    for app_id, app in APK_REGISTRY.items():
        apk_path = APK_DIR / app["filename"]
        result.append(
            {
                **app,
                "downloaded": apk_path.exists(),
                "has_url": app["download_url"] is not None,
            }
        )
    return result


def get_apk_status(app_id: str) -> dict | None:
    """Get status of a single APK."""
    app = APK_REGISTRY.get(app_id)
    if not app:
        return None
    apk_path = APK_DIR / app["filename"]
    return {
        **app,
        "downloaded": apk_path.exists(),
        "has_url": app["download_url"] is not None,
        "local_path": str(apk_path),
    }


def download_apk(app_id: str, progress_callback=None) -> dict:
    """Download APK from registry URL. Returns success/error dict."""
    app = APK_REGISTRY.get(app_id)
    if not app:
        return {"success": False, "error": f"Unknown app: {app_id}"}

    if not app["download_url"]:
        return {
            "success": False,
            "error": f"No download URL for {app['name']}. Place APK manually in data/apks/",
        }

    apk_path = APK_DIR / app["filename"]

    # Already downloaded
    if apk_path.exists():
        return {"success": True, "message": "Already downloaded", "path": str(apk_path)}

    try:
        print(f"[APK] Downloading {app['name']} from {app['download_url']}...")

        def _report(block_num, block_size, total_size):
            if progress_callback and total_size > 0:
                progress_callback(
                    min(100, int(block_num * block_size / total_size * 100))
                )

        urllib.request.urlretrieve(
            app["download_url"], str(apk_path), reporthook=_report
        )
        print(f"[APK] Downloaded: {apk_path}")
        return {"success": True, "message": "Download complete", "path": str(apk_path)}
    except Exception as e:
        # Clean up partial download
        if apk_path.exists():
            apk_path.unlink()
        print(f"[APK] Download failed: {e}")
        return {"success": False, "error": str(e)}


def install_apk(app_id: str, serial: str) -> dict:
    """Install APK on a single emulator via ADB."""
    app = APK_REGISTRY.get(app_id)
    if not app:
        return {"success": False, "error": f"Unknown app: {app_id}"}

    apk_path = APK_DIR / app["filename"]
    if not apk_path.exists():
        return {"success": False, "error": f"APK not downloaded: {app['filename']}"}

    adb_path = config.adb_path
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    try:
        # Install with -r (replace existing)
        print(f"[APK] Installing {app['name']} on {serial}...")
        cmd = [adb_path, "-s", serial, "install", "-r", str(apk_path)]
        result = subprocess.run(
            cmd, capture_output=True, text=True, startupinfo=startupinfo, timeout=120
        )

        if "Success" in result.stdout:
            print(f"[APK] {app['name']} installed on {serial}")

            # Run post-install command if defined
            if app.get("post_install"):
                post_cmd = [adb_path, "-s", serial] + app["post_install"]
                subprocess.run(
                    post_cmd, capture_output=True, startupinfo=startupinfo, timeout=10
                )
                print(f"[APK] Post-install command executed on {serial}")

            return {"success": True, "message": f"Installed on {serial}"}
        else:
            error_msg = (
                result.stdout.strip() or result.stderr.strip() or "Unknown error"
            )
            print(f"[APK] Install failed on {serial}: {error_msg}")
            return {"success": False, "error": error_msg}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Install timed out (120s)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def install_apk_on_multiple(app_id: str, serials: list[str], ws_callback=None) -> dict:
    """Install APK on multiple emulators. Returns summary."""
    results = []
    for i, serial in enumerate(serials):
        result = install_apk(app_id, serial)
        result["serial"] = serial
        results.append(result)

        if ws_callback:
            ws_callback(
                "apk_install_progress",
                {
                    "app_id": app_id,
                    "serial": serial,
                    "step": i + 1,
                    "total": len(serials),
                    "success": result["success"],
                },
            )

    success_count = sum(1 for r in results if r["success"])
    return {
        "success": success_count > 0,
        "installed": success_count,
        "failed": len(serials) - success_count,
        "total": len(serials),
        "results": results,
    }
