"""
Account Detector Tool (OCR)
Finds a specific text string (like an account name "GOHAN") on the emulator screen 
and returns its center coordinates based on bounding boxes.

Usage: python workflow/account_detector.py "ACCOUNT_NAME" [serial]
"""
import os
import sys
import cv2
import numpy as np
import pytesseract
from pytesseract import Output
import subprocess

# Root directory (Part3_Control_EMU)
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)

# UI_MANAGER directory for config
ui_manager_dir = os.path.abspath(os.path.join(root_dir, "..", "UI_MANAGER"))
sys.path.append(ui_manager_dir)

from backend.config import config
config.load()

# Tesseract setup
pytesseract.pytesseract.tesseract_cmd = config.tesseract_path

from workflow import adb_helper

def _preprocess_strategies(scaled_gray: np.ndarray) -> list:
    """
    Returns a list of (name, preprocessed_image) tuples.
    Multiple strategies handle different game font styles and backgrounds.
    """
    strategies = []
    
    # Strategy 1: CLAHE (good for standard text with uneven lighting)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(scaled_gray)
    strategies.append(("CLAHE", enhanced))
    
    # Strategy 2: Adaptive Threshold (best for stylized game fonts on gradient backgrounds)
    thresh_adaptive = cv2.adaptiveThreshold(
        scaled_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10
    )
    strategies.append(("AdaptiveThresh", thresh_adaptive))
    
    # Strategy 3: OTSU Threshold (good global binarization)
    _, thresh_otsu = cv2.threshold(scaled_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    strategies.append(("OTSU", thresh_otsu))
    
    return strategies


def _search_ocr_data(data: dict, target_lower: str, scale: int) -> tuple:
    """Searches OCR output data for a target text match. Returns (cx, cy, word) or None."""
    for i in range(len(data['text'])):
        word = data['text'][i].strip()
        if word and target_lower in word.lower():
            x = data['left'][i]
            y = data['top'][i]
            w_box = data['width'][i]
            h_box = data['height'][i]
            conf = data['conf'][i]
            
            if conf != '-1' and int(conf) > 30:
                center_x = (x + w_box // 2) // scale
                center_y = (y + h_box // 2) // scale
                return (center_x, center_y, word, int(conf))
    return None


def locate_text_on_screen(screen_img: np.ndarray, target_text: str) -> tuple:
    """
    Multi-strategy OCR: tries multiple preprocessing + PSM modes to find target_text.
    Returns (x, y, matched_text) on first match, or None if all strategies fail.
    """
    if screen_img is None:
        return None

    scale = 3
    h, w = screen_img.shape[:2]
    scaled = cv2.resize(screen_img, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)

    target_lower = target_text.lower().strip()
    psm_modes = ['--psm 6', '--psm 11']

    for strategy_name, processed_img in _preprocess_strategies(gray):
        for psm in psm_modes:
            data = pytesseract.image_to_data(processed_img, config=psm, output_type=Output.DICT)
            result = _search_ocr_data(data, target_lower, scale)
            if result:
                cx, cy, word, conf = result
                print(f"[OCR] Found '{word}' at ({cx}, {cy}) | conf:{conf}% | strategy:{strategy_name} {psm}")
                return (cx, cy, word)

    # Debug: dump all words from the best strategy (AdaptiveThresh) so user can see what OCR read
    print("[OCR] All strategies failed. Words from AdaptiveThresh --psm 6:")
    best_img = _preprocess_strategies(gray)[1][1]  # AdaptiveThresh
    data = pytesseract.image_to_data(best_img, config='--psm 6', output_type=Output.DICT)
    for i in range(len(data['text'])):
        w = data['text'][i].strip()
        if w:
            print(f"  '{w}' (conf:{data['conf'][i]})")
    
    return None


def screencap_memory(adb_path: str, serial: str) -> np.ndarray:
    """Captures screen directly to RAM."""
    cmd = [adb_path, "-s", serial, "exec-out", "screencap", "-p"]
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    
    try:
        result = subprocess.run(cmd, capture_output=True, startupinfo=startupinfo, timeout=5)
        if not result.stdout:
            return None
        image_array = np.frombuffer(result.stdout, np.uint8)
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print(f"[ERROR] Screencap failed: {e}")
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python name_detector.py <target_text> [serial]")
        print('Example: python name_detector.py "Goten" emulator-5556')
        return
        
    target_text = sys.argv[1]
    serial = sys.argv[2] if len(sys.argv) > 2 else "emulator-5556"
    
    print(f"[INFO] Target OCR Text: '{target_text}'")
    print(f"[INFO] Serial: {serial}")
    print(f"[INFO] Capturing screen...")
    
    screen = screencap_memory(config.adb_path, serial)
    if screen is None:
        print("[ERROR] Could not capture screen.")
        return
        
    sh, sw = screen.shape[:2]
    print(f"[INFO] Screen resolution: {sw}x{sh}")
    
    result = locate_text_on_screen(screen, target_text)
    
    if result:
        cx, cy, matched_text = result
        print(f"\n{'='*50}")
        print(f"  [FOUND] TEXT!")
        print(f"  Matched:    '{matched_text}'")
        print(f"  Center:     ({cx}, {cy})")
        print(f"{'='*50}\n")
        
        # Uncomment to tap immediately
        adb_helper.tap(serial, cx, cy)
        
        # Save debug image
        debug_path = os.path.join(root_dir, "debug_ocr_locator.png")
        debug_img = screen.copy()
        
        # Draw finding
        cv2.circle(debug_img, (cx, cy), 15, (0, 0, 255), 3)
        cv2.putText(debug_img, f"{matched_text} ({cx}, {cy})", (cx + 20, cy - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        cv2.imwrite(debug_path, debug_img)
        print(f"[INFO] Saved debug image: {debug_path}")
    else:
        print(f"\n  [FAILED] NOT FOUND: Could not OCR text containing '{target_text}'")

if __name__ == "__main__":
    main()
