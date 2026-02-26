"""
COD LDPlayer Automation (Sync Mode)
Controls ONE Master instance (via ADB).
User ENABLEs LDPlayer Sync so others follow.
Captures and OCRs on ALL connected instances.
"""
import subprocess
import os
import sys
import time
import cv2
import numpy as np
import pytesseract
import csv

# ==============================================================================
# CONFIGURATION
# ==============================================================================
ADB_PATH = r"C:\LDPlayer\LDPlayer9\adb.exe"
WORK_DIR = r"f:\COD_CHECK"
DEBUG_DIR = r"f:\COD_CHECK\debug"
CSV_FILE = r"f:\COD_CHECK\APP\COD_SYNC_REPORT.csv"
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
if not os.path.exists(DEBUG_DIR): os.makedirs(DEBUG_DIR, exist_ok=True)

# 960x540 Coordinate Map
REGIONS = {
    "profile_name":  (100, 320, 275, 370),
    "profile_power": (100, 405, 250, 435),
    "res_gold_item": (360, 130, 540, 180),
    "res_wood_item": (360, 210, 540, 260),
    "res_ore_item":  (360, 290, 540, 340),
    "res_mana_item": (360, 370, 540, 420),
    "res_gold_total": (580, 130, 740, 180),
    "res_wood_total": (580, 210, 740, 260),
    "res_ore_total":  (580, 290, 740, 340),
    "res_mana_total": (580, 370, 740, 420),
    "pet_token": (875, 0, 960, 50),
    "building_level": (550, 250, 600, 275),
}

# ==============================================================================
# ADB HELPERS
# ==============================================================================
def run_adb(cmd_list):
    try:
        # Hide console window
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        result = subprocess.run([ADB_PATH] + cmd_list, capture_output=True, text=True, startupinfo=startupinfo)
        return result.stdout.strip()
    except Exception as e:
        print(f"ADB Error: {e}")
        return ""

def get_devices():
    out = run_adb(['devices'])
    devs = []
    for line in out.split('\n')[1:]:
        p = line.split()
        if len(p) >= 2 and p[1] == 'device': devs.append(p[0])
    return sorted(devs)

def adb_tap(serial, x, y):
    subprocess.run([ADB_PATH, "-s", serial, "shell", "input", "tap", str(x), str(y)])

def adb_swipe(serial, x1, y1, x2, y2, duration=300):
    subprocess.run([ADB_PATH, "-s", serial, "shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration)])

def adb_back(serial, count=1):
    for _ in range(count):
        subprocess.run([ADB_PATH, "-s", serial, "shell", "input", "keyevent", "4"]) # KEYCODE_BACK
        time.sleep(1.5)

# ==============================================================================
# CLASS: LDPlayerScanner (Same as before)
# ==============================================================================
class LDPlayerScanner:
    def __init__(self, serial):
        self.serial = serial
        self.screenshot_path = os.path.join(DEBUG_DIR, f"screen_{serial}.png")

    def capture(self):
        try:
            subprocess.run([ADB_PATH, "-s", self.serial, "shell", "screencap", "-p", "/sdcard/screen.png"], capture_output=True)
            subprocess.run([ADB_PATH, "-s", self.serial, "pull", "/sdcard/screen.png", self.screenshot_path], capture_output=True)
            if not os.path.exists(self.screenshot_path): return None
            img = cv2.imread(self.screenshot_path)
            if img is None: return None
            h, w = img.shape[:2]
            if h != 540 or w != 960: img = cv2.resize(img, (960, 540))
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            final = cv2.filter2D(img, -1, kernel)
            cv2.imwrite(self.screenshot_path, final)
            return final
        except Exception as e:
            print(f"Capture Fail {self.serial}: {e}")
            return None

    def ocr(self, img, whitelist=None):
        if img is None: return ""
        cfg = r'--psm 7'
        if whitelist: cfg += f' -c tessedit_char_whitelist={whitelist}'
        return pytesseract.image_to_string(img, config=cfg).strip()

    def preprocess_roi(self, roi, invert=True):
        if roi is None or roi.size == 0: return roi
        scaled = cv2.resize(roi, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        if invert: final = cv2.bitwise_not(thresh)
        else: final = thresh
        final = cv2.copyMakeBorder(final, 10, 10, 15, 15, cv2.BORDER_CONSTANT, value=255)
        return final

    def parse_num(self, text):
        text = text.upper().strip().replace(' ', '').replace(',', '').replace('.', '')
        multiplier = 1
        if text.endswith('K'): multiplier = 1_000; text = text[:-1]
        elif text.endswith('M'): multiplier = 1_000_000; text = text[:-1]
        elif text.endswith('B'): multiplier = 1_000_000_000; text = text[:-1]
        try: return int(float(text) * multiplier)
        except: return 0

    def retry_scan(self, scan_func, validator, max_retries=3):
        last_val = None
        for i in range(max_retries):
            img = self.capture()
            if img is None: continue
            val = scan_func(img)
            if validator(val): return val
            last_val = val
            print(f"      [{self.serial}] Retry {i+1}...")
            time.sleep(1.0)
        return last_val

    # --- SCANNERS ---
    def scan_profile_data(self, img):
        if img is None: return {}
        res = {}
        x1, y1, x2, y2 = REGIONS["profile_name"]
        res['Name'] = self.ocr(self.preprocess_roi(img[y1:y2, x1:x2]))
        x1, y1, x2, y2 = REGIONS["profile_power"]
        res['Power'] = self.ocr(self.preprocess_roi(img[y1:y2, x1:x2]), "0123456789.,KMB")
        return res

    def scan_resources_data(self, img):
        if img is None: return []
        data = []
        for r in ['gold', 'wood', 'ore', 'mana']:
            x1, y1, x2, y2 = REGIONS[f"res_{r}_total"]
            val_t = self.parse_num(self.ocr(self.preprocess_roi(img[y1:y2, x1:x2]), "0123456789.,KMB"))
            data.append(val_t) # Just saving total for CSV simplicity
        return data

    def scan_building_level(self, img):
        if img is None: return "0"
        x1, y1, x2, y2 = REGIONS["building_level"]
        return self.ocr(self.preprocess_roi(img[y1:y2, x1:x2]), "0123456789")

    def scan_pet_token(self, img):
        if img is None: return "0"
        x1, y1, x2, y2 = REGIONS["pet_token"]
        roi = img[y1:y2, x1:x2]
        
        # === DUAL STRATEGY (Part1_OCR/ocr_pet_token.py) ===
        # Pipeline A: Standard (Scale x4)
        scaled = cv2.resize(roi, None, fx=4.0, fy=4.0, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
        _, thresh_a = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        img_a = cv2.copyMakeBorder(thresh_a, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)
        
        # Pipeline B: Erode
        kernel = np.ones((2,2), np.uint8)
        gray_b = cv2.erode(gray, kernel, iterations=1)
        _, thresh_b = cv2.threshold(gray_b, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        img_b = cv2.copyMakeBorder(thresh_b, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)
        
        # Text OCR
        cfg = r'--psm 7 -c tessedit_char_whitelist=0123456789'
        text_a = pytesseract.image_to_string(img_a, config=cfg).strip()
        text_b = pytesseract.image_to_string(img_b, config=cfg).strip()
        
        # Selection Logic: Pick the longest result (Pet Token is typically 3-4 digits)
        final_text = text_b if len(text_b) > len(text_a) else text_a
        return final_text

# ==============================================================================
# SYNC WORKFLOW
# ==============================================================================
# ==============================================================================
# BROADCAST HELPERS (Efficient Parallel-ish Actions)
# ==============================================================================
def broadcast_tap(devices, x, y):
    """Sends Tap to all devices sequentially (fast)"""
    for s in devices:
        adb_tap(s, x, y)

def broadcast_swipe(devices, x1, y1, x2, y2, duration=300):
    for s in devices:
        adb_swipe(s, x1, y1, x2, y2, duration)

def broadcast_back(devices, count=1):
    """Sends Back key with sleep in between repetitions, not per device"""
    for _ in range(count):
        for s in devices:
            subprocess.run([ADB_PATH, "-s", s, "shell", "input", "keyevent", "4"])
        time.sleep(1.5) # Wait once for all devices to react

def format_abbr(val):
    if not isinstance(val, (int, float)): return str(val)
    if val >= 1_000_000_000: return f"{val/1_000_000_000:.1f}B"
    if val >= 1_000_000: return f"{val/1_000_000:.1f}M"
    if val >= 1_000: return f"{val/1_000:.1f}K"
    return str(val)

def save_csv(report):
    print(f"\n[Saving Report to {CSV_FILE} (Mode: Append)]")
    headers = ['Serial', 'Name', 'Power', 'Gold', 'Wood', 'Ore', 'Mana', 'Hall', 'Market', 'PetToken']
    
    file_exists = os.path.isfile(CSV_FILE)
    
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(headers)
        
        for serial, data in report.items():
            row = [
                serial,
                data.get('profile', {}).get('Name', ''),
                data.get('profile', {}).get('Power', ''),
                data.get('resources', [0,0,0,0])[0], # Gold
                data.get('resources', [0,0,0,0])[1], # Wood
                data.get('resources', [0,0,0,0])[2], # Ore
                data.get('resources', [0,0,0,0])[3], # Mana
                data.get('hall', ''),
                data.get('market', ''),
                data.get('pet', '')
            ]
            writer.writerow(row)
    print("CSV Updated.")

def main():
    print("=== LDPlayer BROADCAST Automation ===")
    devices = get_devices()
    if not devices:
        print("No devices found!")
        return

    print(f"FOUND {len(devices)} DEVICES: {devices}")
    print("Mode: BROADCAST (Direct ADB Control on ALL devices)")
    
    print("\nStarting Automation Sequence...")
    
    # Init Report
    FINAL_REPORT = {s: {} for s in devices}
    
    # --- PHASE 1: PROFILE ---
    print("\n>>> PHASE 1: PROFILE CHECK")
    # Broadcast Navigate
    broadcast_tap(devices, 18, 10); time.sleep(5.0)
    broadcast_tap(devices, 550, 200); time.sleep(0.5)
    broadcast_tap(devices, 550, 200); time.sleep(3.0)
    
    # ALL Scan
    for serial in devices:
        print(f"   Scanning {serial}...", end="")
        s = LDPlayerScanner(serial)
        data = s.retry_scan(
            s.scan_profile_data, 
            lambda x: x and len(x.get('Name', '')) > 2
        )
        FINAL_REPORT[serial]['profile'] = data
        print(f" Name: {data.get('Name')} | Power: {data.get('Power')}")
        
    # Broadcast Exit
    broadcast_back(devices, 2)
    time.sleep(2.0)

    # --- PHASE 2: RESOURCES ---
    print("\n>>> PHASE 2: RESOURCES CHECK")
    # Broadcast Navigate
    broadcast_tap(devices, 925, 500); time.sleep(5.0)
    broadcast_tap(devices, 780, 500); time.sleep(5.0)
    broadcast_tap(devices, 75, 180); time.sleep(5.0)
    broadcast_tap(devices, 620, 100); time.sleep(5.0)
    
    # ALL Scan
    for serial in devices:
        print(f"   Scanning {serial}...", end="")
        s = LDPlayerScanner(serial)
        data = s.retry_scan(
            s.scan_resources_data,
            lambda x: x and any(v > 0 for v in x)
        )
        FINAL_REPORT[serial]['resources'] = data
        print(f" Res: {data}")
        
    # Broadcast Exit
    broadcast_back(devices, 2)

    # --- PHASE 3: HALL ---
    print("\n>>> PHASE 3: HALL CHECK")
    # Broadcast Navigate
    broadcast_tap(devices, 456, 111); time.sleep(5.0)
    broadcast_tap(devices, 380, 116); time.sleep(5.0)
    
    # ALL Scan
    for serial in devices:
        print(f"   Scanning {serial}...", end="")
        s = LDPlayerScanner(serial)
        val = s.retry_scan(s.scan_building_level, lambda x: x and x.isdigit())
        FINAL_REPORT[serial]['hall'] = val
        print(f" Lv: {val}")
        
    # Broadcast Exit
    broadcast_back(devices, 1)

    # --- PHASE 4: MARKET ---
    print("\n>>> PHASE 4: MARKET CHECK")
    # Broadcast Navigate
    broadcast_tap(devices, 639, 232); time.sleep(5.0)
    broadcast_tap(devices, 545, 267); time.sleep(5.0)
    
    # ALL Scan
    for serial in devices:
        print(f"   Scanning {serial}...", end="")
        s = LDPlayerScanner(serial)
        val = s.retry_scan(s.scan_building_level, lambda x: x and x.isdigit())
        FINAL_REPORT[serial]['market'] = val
        print(f" Lv: {val}")
        
    # Broadcast Exit
    broadcast_back(devices, 1)

    # --- PHASE 5: PET TOKEN ---
    print("\n>>> PHASE 5: PET TOKEN CHECK")
    # Broadcast Navigate
    broadcast_tap(devices, 750, 80); time.sleep(5.0)
    for _ in range(3):
        broadcast_swipe(devices, 100, 450, 100, 100, 500)
        time.sleep(1.0)
    broadcast_tap(devices, 100, 375); time.sleep(5.0)
    
    # ALL Scan
    for serial in devices:
        print(f"   Scanning {serial}...", end="")
        s = LDPlayerScanner(serial)
        val = s.retry_scan(s.scan_pet_token, lambda x: x is not None and x.isdigit())
        FINAL_REPORT[serial]['pet'] = val
        print(f" Token: {val}")
        
    # Broadcast Exit
    broadcast_back(devices, 1)

    # --- FINISH ---
    print_report(FINAL_REPORT)
    save_csv(FINAL_REPORT)
    print("\nALL DONE!")

def print_report(report):
    print("\n" + "="*120)
    print(f"{'SERIAL':<15} {'NAME':<15} {'POWER':<12} {'GOLD':<10} {'WOOD':<10} {'ORE':<10} {'MANA':<10} {'HALL':<5} {'MKT':<5} {'PET':<5}")
    print("-" * 120)
    
    for serial, data in report.items():
        name = data.get('profile', {}).get('Name', 'N/A')[:14]
        power = data.get('profile', {}).get('Power', '0')
        res = data.get('resources', [0,0,0,0])
        hall = data.get('hall', '0')
        mkt = data.get('market', '0')
        pet = data.get('pet', '0')
        
        # Use Helper to Format Numbers 
        res_str = [format_abbr(r) for r in res]
        
        print(f"{serial:<15} {name:<15} {power:<12} {res_str[0]:<10} {res_str[1]:<10} {res_str[2]:<10} {res_str[3]:<10} {hall:<5} {mkt:<5} {pet:<5}")
    print("="*120 + "\n")

if __name__ == "__main__":
    main()
