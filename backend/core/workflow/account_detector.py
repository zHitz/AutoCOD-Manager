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
from workflow.ocr_name_utils import sanitize_lord_name


class AccountDetector:
    def __init__(self, adb_path: str = None):
        self.adb_path = adb_path or config.adb_path

    def screencap_memory(self, serial: str) -> np.ndarray:
        """Captures screen directly to RAM."""
        cmd = [self.adb_path, "-s", serial, "exec-out", "screencap", "-p"]
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            result = subprocess.run(
                cmd, capture_output=True, startupinfo=startupinfo, timeout=5
            )
            if not result.stdout:
                return None
            image_array = np.frombuffer(result.stdout, np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            print(f"[ERROR] Screencap failed: {e}")
            return None

    def check_account_name(
        self,
        serial: str,
        target: str,
        check_type: str = "text",
        tesseract_config: str = "--psm 6",
    ) -> tuple:
        """
        Runs OCR on the given serial's screen. Finds the first occurrence of target (case-insensitive)
        and returns its center (x, y) along with the exact matched text.

        Uses multi-strategy search:
          Strategy 1: Exact substring match with raw target
          Strategy 2: Sanitized name fallback (strips OCR noise, alliance tags)

        Applies image preprocessing (Scaling + Contrast) to improve accuracy on game fonts.
        """
        if check_type != "text":
            return None

        screen_img = self.screencap_memory(serial)
        if screen_img is None:
            return None

        # --- IMAGE PRE-PROCESSING CHO TESSERACT ---
        scale = 2
        h, w = screen_img.shape[:2]
        scaled = cv2.resize(
            screen_img, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC
        )

        gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        data = pytesseract.image_to_data(
            enhanced, config=tesseract_config, output_type=Output.DICT
        )

        # Build search candidates: exact first, sanitized fallback
        raw_lower = target.lower().strip()
        sanitized = sanitize_lord_name(target).lower()

        candidates = [raw_lower]
        if sanitized and sanitized != raw_lower:
            candidates.append(sanitized)

        for search_term in candidates:
            result = self._find_text_in_ocr_data(data, search_term, scale)
            if result:
                label = "exact" if search_term == raw_lower else "sanitized"
                print(f"[OCR] Matched via {label} strategy: '{search_term}'")
                return (target, result[0], result[1])

        # Debug: dump OCR words when nothing matched
        all_words = [
            w.strip() for w in data["text"] if w.strip()
        ]
        print(
            f"[OCR] No match for '{target}' (candidates: {candidates}). "
            f"OCR words on screen: {all_words[:30]}"
        )
        return None

    def _find_text_in_ocr_data(
        self, data: dict, search_term: str, scale: int
    ) -> tuple:
        """Search for a term in OCR data dict. Returns (center_x, center_y) or None."""
        for i in range(len(data["text"])):
            word = data["text"][i].strip()
            if not word:
                continue

            if search_term in word.lower():
                x = data["left"][i]
                y = data["top"][i]
                w_box = data["width"][i]
                h_box = data["height"][i]
                conf = data["conf"][i]

                if conf != "-1" and int(conf) > 40:
                    center_x = (x + (w_box // 2)) // scale
                    center_y = (y + (h_box // 2)) // scale

                    print(
                        f"[OCR] Found '{word}' at center ({center_x}, {center_y}) | conf: {conf}%"
                    )
                    return (center_x, center_y)

        return None

    def check_account_name_basic(
        self,
        serial: str,
        target: str,
        check_type: str = "text",
        tesseract_config: str = "--psm 6",
    ) -> tuple:
        """
        Runs OCR on the given serial's screen using the basic/older method (No scaling, no CLAHE).
        Finds the first occurrence of target (case-insensitive) and returns its center (x, y).
        """
        if check_type != "text":
            return None

        screen_img = self.screencap_memory(serial)
        if screen_img is None:
            return None

        # 1. Grayscale only
        gray = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)

        # Output.DICT gives us access to coordinates and confidences
        data = pytesseract.image_to_data(
            gray, config=tesseract_config, output_type=Output.DICT
        )

        target_lower = target.lower().strip()

        for i in range(len(data["text"])):
            word = data["text"][i].strip()

            # Check if the word is non-empty and contains the search text
            if word and target_lower in word.lower():
                x = data["left"][i]
                y = data["top"][i]
                w = data["width"][i]
                h = data["height"][i]
                conf = data["conf"][i]

                # Filter low confidence results
                if conf != "-1" and int(conf) > 40:
                    center_x = x + (w // 2)
                    center_y = y + (h // 2)

                    print(
                        f"[OCR Basic] Found '{word}' at center ({center_x}, {center_y}) | conf: {conf}%"
                    )
                    return (target, center_x, center_y)

        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python account_detector.py <target_text> [serial]")
        print('Example: python account_detector.py "Goten" emulator-5556')
        return

    target_text = sys.argv[1]
    serial = sys.argv[2] if len(sys.argv) > 2 else "emulator-5556"

    print(f"[INFO] Target OCR Text: '{target_text}'")
    print(f"[INFO] Serial: {serial}")
    print("[INFO] Capturing screen and scanning...")

    detector = AccountDetector()
    result = detector.check_account_name(serial, target_text)

    if result:
        matched_text, cx, cy = result
        print(f"\n{'=' * 50}")
        print("  [FOUND] TEXT!")
        print(f"  Target:     '{target_text}'")
        print(f"  Center:     ({cx}, {cy})")
        print(f"{'=' * 50}\n")

        # Uncomment to tap immediately
        adb_helper.tap(serial, cx, cy)

        # Save debug image
        screen = detector.screencap_memory(serial)
        if screen is not None:
            debug_path = os.path.join(root_dir, "debug_ocr_locator.png")
            debug_img = screen.copy()

            cv2.circle(debug_img, (cx, cy), 15, (0, 0, 255), 3)
            cv2.putText(
                debug_img,
                f"{target_text} ({cx}, {cy})",
                (cx + 20, cy - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2,
            )

            cv2.imwrite(debug_path, debug_img)
            print(f"[INFO] Saved debug image: {debug_path}")
    else:
        print(f"\n  [FAILED] NOT FOUND: Could not OCR text containing '{target_text}'")


if __name__ == "__main__":
    main()
