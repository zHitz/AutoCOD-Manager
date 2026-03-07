"""
COD Game Automation Manager — Desktop App Entry Point
Launches FastAPI backend + pywebview window.
"""

import sys
import os
import threading
import time

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# Load config before anything else
from backend.config import config

config.load()


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
        webview.create_window(
            title="COD Game Automation Manager",
            html=loading_html,
            width=1400,
            height=900,
            min_size=(1024, 700),
            resizable=True,
            text_select=True,
        )
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
