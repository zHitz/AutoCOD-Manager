import urllib.request
import os
import subprocess
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "UI_MANAGER")))
from backend.config import config
config.load()

def main():
    apk_url = "https://github.com/majido/clipper/releases/download/v1.2.1/clipper.apk"
    apk_path = os.path.join(os.path.dirname(__file__), "clipper.apk")
    
    print("[INFO] Fetching ADB Clipper APK...")
    if not os.path.exists(apk_path):
        urllib.request.urlretrieve(apk_url, apk_path)
        print("[SUCCESS] Downloaded Clipper APK.")
    # Get all running emulators
    import subprocess
    result = subprocess.run([config.adb_path, "devices"], capture_output=True, text=True)
    serials = []
    for line in result.stdout.split('\n')[1:]:
        if "device" in line and "emulator-" in line:
            serials.append(line.split()[0])
            
    if not serials:
        print("[WARNING] No emulators found running.")
        return
        
    for serial in serials:
        print(f"\n[INFO] Installing Clipper on {serial}...")
        install_cmd = [config.adb_path, "-s", serial, "install", "-r", apk_path]
        result = subprocess.run(install_cmd, capture_output=True, text=True)
        
        if "Success" in result.stdout:
            print(f"[SUCCESS] Clipper Installed on {serial}!")
        else:
            print(f"[ERROR] Installation failed on {serial}: {result.stdout}")
            continue

        # Start the service
        print(f"[INFO] Launching Clipper background service on {serial}...")
        start_cmd = [
            config.adb_path, "-s", serial, "shell", "am", "startservice", 
            "ca.zgrs.clipper/.ClipboardService"
        ]
        subprocess.run(start_cmd, capture_output=True)
    
    # We are ready
    print("\n=============================================")
    print(f"[READY] Clipper is active on: {', '.join(serials)}")
    print("=============================================\n")

if __name__ == "__main__":
    main()
