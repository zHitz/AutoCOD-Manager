"""
COD Game Automation Manager — Desktop App Entry Point
Launches FastAPI backend + pywebview window.
"""

import os
import struct
import sys
import ctypes
import threading
import time

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
APP_ICON_PNG = os.path.join(PROJECT_ROOT, "ICON_COD_MANAGER.png")
APP_ICON_ICO = os.path.join(PROJECT_ROOT, "ICON_COD_MANAGER.ico")

# Load config before anything else
from backend.config import config

config.load()


def ensure_windows_ico(png_path: str, ico_path: str) -> str | None:
    """Create a Windows .ico file that embeds the source PNG."""
    if not os.path.exists(png_path):
        return None

    if os.path.exists(ico_path) and os.path.getmtime(ico_path) >= os.path.getmtime(
        png_path
    ):
        return ico_path

    with open(png_path, "rb") as src:
        png_bytes = src.read()

    icon_dir = struct.pack("<HHH", 0, 1, 1)
    icon_entry = struct.pack(
        "<BBBBHHII",
        0,
        0,
        0,
        0,
        1,
        32,
        len(png_bytes),
        22,
    )

    with open(ico_path, "wb") as dst:
        dst.write(icon_dir)
        dst.write(icon_entry)
        dst.write(png_bytes)

    return ico_path


def apply_windows_app_icon(window) -> None:
    """Apply a custom icon to the native Windows window."""
    if sys.platform != "win32":
        return

    icon_path = ensure_windows_ico(APP_ICON_PNG, APP_ICON_ICO)
    if not icon_path or not os.path.exists(icon_path):
        return

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "cod.ui.manager.desktop"
        )

        hwnd = int(window.native.Handle)
        image_icon = 1
        load_from_file = 0x00000010
        wm_seticon = 0x0080
        icon_small = 0
        icon_big = 1

        hicon = ctypes.windll.user32.LoadImageW(
            None,
            icon_path,
            image_icon,
            0,
            0,
            load_from_file,
        )
        if hicon:
            ctypes.windll.user32.SendMessageW(hwnd, wm_seticon, icon_small, hicon)
            ctypes.windll.user32.SendMessageW(hwnd, wm_seticon, icon_big, hicon)
    except Exception as exc:
        print(f"[Desktop] Unable to apply app icon: {exc}")


def start_server():
    """Start FastAPI/Uvicorn server in background thread."""
    import uvicorn
    from backend.api import app

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=config.server_port,
        log_level="warning",
    )


def main():
    """Main entry point — start server then open desktop window."""
    print("=" * 50)
    print("  COD Game Automation Manager v1.0")
    print("=" * 50)

    # Start FastAPI server in background
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    url = f"http://127.0.0.1:{config.server_port}"

    # Loading screen (shown while server boots)
    loading_page = os.path.join(PROJECT_ROOT, "frontend", "loading.html")
    with open(loading_page, "r", encoding="utf-8") as f:
        loading_html = f.read().replace("|| '8000'", f"|| '{config.server_port}'")

    # Try pywebview for native window
    try:
        import webview

        print("[Desktop] Opening loading screen...")
        window = webview.create_window(
            title="COD Game Automation Manager",
            html=loading_html,
            width=1400,
            height=900,
            min_size=(1024, 700),
            resizable=True,
            text_select=True,
        )
        window.events.before_show += apply_windows_app_icon
        webview.start(debug=False)
    except ImportError:
        # Fallback: open in default browser
        print(f"[Desktop] pywebview not installed. Opening in browser: {url}")
        print(
            "[Desktop] Install pywebview for native desktop window: pip install pywebview"
        )
        import webbrowser

        # Wait for server in browser mode
        time.sleep(2)
        webbrowser.open(url)

        # Keep server alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[Desktop] Shutting down...")


if __name__ == "__main__":
    main()
