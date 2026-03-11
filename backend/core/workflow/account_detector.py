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
from workflow.ocr_swap_logger import log_ocr_swap_attempt


class AccountNotFoundError(Exception):
    """Raised when the target account is not found in the Character Management list."""
    pass


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


def _search_ocr_data(data: dict, search_term: str, scale: int) -> tuple:
    """Searches OCR output data for a target text match. Returns (cx, cy, word, conf) or None."""
    for i in range(len(data["text"])):
        word = data["text"][i].strip()
        if word and search_term in word.lower():
            x = data["left"][i]
            y = data["top"][i]
            w_box = data["width"][i]
            h_box = data["height"][i]
            conf = data["conf"][i]

            if conf != "-1" and int(conf) > 30:
                center_x = (x + w_box // 2) // scale
                center_y = (y + h_box // 2) // scale
                return (center_x, center_y, word, int(conf))
    return None


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
        Multi-strategy OCR: tries multiple preprocessing + PSM modes to find target.
        Returns (target, center_x, center_y) on match, or None if all strategies fail.

        Uses multi-strategy search for both image preprocessing and name matching:
          Image: CLAHE -> AdaptiveThreshold -> OTSU (x2 PSM modes each)
          Name:  Exact substring match -> Sanitized name fallback
        """
        if check_type != "text":
            return None

        screen_img = self.screencap_memory(serial)
        if screen_img is None:
            return None

        # --- IMAGE PRE-PROCESSING ---
        scale = 3
        h, w = screen_img.shape[:2]
        scaled = cv2.resize(
            screen_img, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC
        )
        gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)

        # Build search candidates: exact first, sanitized fallback
        raw_lower = target.lower().strip()
        sanitized = sanitize_lord_name(target).lower()

        candidates = [raw_lower]
        if sanitized and sanitized != raw_lower:
            candidates.append(sanitized)

        psm_modes = ["--psm 6", "--psm 11"]

        # Try each preprocessing strategy x each PSM mode x each name candidate
        for strategy_name, processed_img in _preprocess_strategies(gray):
            for psm in psm_modes:
                data = pytesseract.image_to_data(
                    processed_img, config=psm, output_type=Output.DICT
                )

                for search_term in candidates:
                    result = _search_ocr_data(data, search_term, scale)
                    if result:
                        cx, cy, word, conf = result
                        label = "exact" if search_term == raw_lower else "sanitized"
                        print(
                            f"[OCR] Matched via {label} strategy: '{search_term}' "
                            f"| word='{word}' at ({cx}, {cy}) conf:{conf}% "
                            f"| img:{strategy_name} {psm}"
                        )
                        all_words = [w.strip() for w in data["text"] if w.strip()]
                        log_ocr_swap_attempt(
                            serial=serial,
                            raw_target=target,
                            candidates=candidates,
                            ocr_words=all_words,
                            matched_strategy=f"{label}|{strategy_name}|{psm}",
                            matched_term=search_term,
                        )
                        return (target, cx, cy)

        # Debug: dump all words from the best strategy (AdaptiveThresh) so user can see what OCR read
        print(f"[OCR] All strategies failed for '{target}' (candidates: {candidates}).")
        print("[OCR] Words from AdaptiveThresh --psm 6:")
        best_img = _preprocess_strategies(gray)[1][1]  # AdaptiveThresh
        data = pytesseract.image_to_data(best_img, config="--psm 6", output_type=Output.DICT)
        all_words = []
        for i in range(len(data["text"])):
            w = data["text"][i].strip()
            if w:
                all_words.append(w)
                print(f"  '{w}' (conf:{data['conf'][i]})")

        log_ocr_swap_attempt(
            serial=serial,
            raw_target=target,
            candidates=candidates,
            ocr_words=all_words[:30],
            matched_strategy=None,
            matched_term=None,
        )
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
