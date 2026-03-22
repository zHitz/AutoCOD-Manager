"""
APK Manager — Download and install APK files on emulators via ADB.

Provides a registry of known apps, download management, and ADB install commands.
APK files are stored in data/apks/.
"""

import os
import subprocess
import tempfile
import urllib.request
import zipfile
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
    "cod": {
        "id": "cod",
        "name": "Call of Dragons",
        "package": "com.farlightgames.samo.gp.vn",
        "version": "latest",
        "size": "~1.6 GB",
        "note": "Main game client — Call of Dragons VN",
        "download_url": None,
        "filename": "cod.xapk",
        "post_install": None,
        "is_xapk": True,
    },
    "codf": {
        "id": "codf",
        "name": "Call of Dragons Farm",
        "package": "com.farlightgames.samo.gp.vn",
        "version": "latest",
        "size": "~1.9 GB",
        "note": "Farm/secondary game client",
        "download_url": None,
        "filename": "codf.xapk",
        "post_install": None,
        "is_xapk": True,
    },
}


def _ensure_adb_connected(serial: str) -> str:
    """Ensure ADB device is reachable, using connect fallback if needed.

    LDPlayer devices don't always auto-register in `adb devices`.
    Falls back to `adb connect 127.0.0.1:<tcp_port>` when not found.
    Returns the working serial (may be TCP format).
    """
    adb_path = config.adb_path
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    # Check if device is already visible
    try:
        result = subprocess.run(
            [adb_path, "devices"],
            capture_output=True, text=True, startupinfo=si, timeout=10,
        )
        for line in result.stdout.splitlines():
            if serial in line and "device" in line:
                return serial
    except Exception:
        pass

    # Not found — try TCP connect fallback
    # serial "emulator-XXXX" → port XXXX, TCP port = XXXX + 1
    try:
        port = int(serial.split("-")[1])
        tcp_port = port + 1
        tcp_serial = f"127.0.0.1:{tcp_port}"
        print(f"[APK] Device {serial} not in adb devices. Trying adb connect {tcp_serial}...")
        subprocess.run(
            [adb_path, "connect", tcp_serial],
            capture_output=True, text=True, startupinfo=si, timeout=10,
        )
        # Verify connection
        result = subprocess.run(
            [adb_path, "devices"],
            capture_output=True, text=True, startupinfo=si, timeout=10,
        )
        for line in result.stdout.splitlines():
            if tcp_serial in line and "device" in line:
                print(f"[APK] Connected via {tcp_serial}")
                return tcp_serial
            if serial in line and "device" in line:
                return serial
    except Exception as e:
        print(f"[APK] ADB connect fallback failed: {e}")

    # Return original serial as last resort
    return serial


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


def install_xapk(app_id: str, serial: str) -> dict:
    """Install XAPK (split-APK bundle) on a single emulator via ADB."""
    app = APK_REGISTRY.get(app_id)
    if not app:
        return {"success": False, "error": f"Unknown app: {app_id}"}

    xapk_path = APK_DIR / app["filename"]
    if not xapk_path.exists():
        return {"success": False, "error": f"XAPK not found: {app['filename']}"}

    serial = _ensure_adb_connected(serial)

    adb_path = config.adb_path
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    try:
        with tempfile.TemporaryDirectory(prefix="xapk_") as tmp_dir:
            print(f"[APK] Extracting {app['filename']} to temp dir...")
            with zipfile.ZipFile(str(xapk_path), "r") as zf:
                zf.extractall(tmp_dir)

            # Find all .apk files inside extracted contents
            apk_files = list(Path(tmp_dir).rglob("*.apk"))
            if not apk_files:
                return {"success": False, "error": "No .apk files found inside XAPK"}

            print(
                f"[APK] Found {len(apk_files)} split APK(s), "
                f"installing on {serial}..."
            )
            cmd = (
                [adb_path, "-s", serial, "install-multiple", "-r"]
                + [str(f) for f in apk_files]
            )
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                startupinfo=startupinfo,
                timeout=300,
            )

            if "Success" in result.stdout:
                print(f"[APK] {app['name']} installed on {serial}")
                return {"success": True, "message": f"Installed on {serial}"}

            error_msg = (
                result.stdout.strip() or result.stderr.strip() or "Unknown error"
            )
            print(f"[APK] XAPK install failed on {serial}: {error_msg}")
            return {"success": False, "error": error_msg}

    except zipfile.BadZipFile:
        return {"success": False, "error": f"{app['filename']} is not a valid ZIP/XAPK"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Install timed out (300s)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def install_apk(app_id: str, serial: str) -> dict:
    """Install APK on a single emulator via ADB."""
    app = APK_REGISTRY.get(app_id)
    if not app:
        return {"success": False, "error": f"Unknown app: {app_id}"}

    # Route XAPK to split-APK installer
    if app.get("is_xapk"):
        return install_xapk(app_id, serial)

    apk_path = APK_DIR / app["filename"]
    if not apk_path.exists():
        return {"success": False, "error": f"APK not downloaded: {app['filename']}"}

    adb_path = config.adb_path
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    serial = _ensure_adb_connected(serial)

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
