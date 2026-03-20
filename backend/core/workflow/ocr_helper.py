import os
import sys
import re
import cv2
import numpy as np
import pytesseract

# Root directory (Part3_Control_EMU)
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)

# UI_MANAGER directory for config
ui_manager_dir = os.path.abspath(os.path.join(root_dir, "..", "UI_MANAGER"))
sys.path.append(ui_manager_dir)

from backend.config import config

_tesseract_initialized = False

def _ensure_tesseract():
    """Lazy init — set tesseract path only when first needed (after config.load())."""
    global _tesseract_initialized
    if not _tesseract_initialized:
        pytesseract.pytesseract.tesseract_cmd = config.tesseract_path
        _tesseract_initialized = True


def parse_game_timer(timer_str: str) -> int:
    """
    Convert game timer to seconds. Supports multiple formats:
    - 'Xh Ym' (e.g. '3h 15m')
    - 'HH:MM:SS' (e.g. '00:20:58')
    - 'MM:SS' (e.g. '20:58')
    Returns 0 if parse fails.
    """
    if not timer_str:
        return 0

    MAX_RSS_SEC = 43200  # 12 hours max for RSS Center

    # Try HH:MM:SS or MM:SS format first
    colon_parts = timer_str.strip().split(':')
    if len(colon_parts) == 3:
        try:
            h, m, s = int(colon_parts[0]), int(colon_parts[1]), int(colon_parts[2])
            # Sanitize each segment for OCR noise:
            # Hours: max 2 digits (12h cap). e.g. 110 → 10
            if h >= 100:
                h = h % 100
            # Minutes: max 2 digits. e.g. 118 → 18
            if m >= 100:
                m = m % 100
            # Seconds: don't let bad seconds ruin the result, clamp to 59
            if s < 0 or s >= 60:
                s = 59
            if m < 60:
                total = h * 3600 + m * 60 + s
                return min(total, MAX_RSS_SEC) if total > 0 else 0
        except ValueError:
            pass
    elif len(colon_parts) == 2:
        try:
            first, second = int(colon_parts[0]), int(colon_parts[1])
            # If first >= 100, OCR dropped a colon: e.g. '1110:43' = '11:10:43'
            if first >= 100:
                h = first // 100
                m = first % 100
                if m >= 100:
                    m = m % 100
                s = min(second, 59) if second >= 0 else 59
                total = h * 3600 + m * 60 + s
                return min(total, MAX_RSS_SEC) if total > 0 else 0
            else:
                m = first
                s = min(second, 59) if 0 <= second else 59
                total = m * 60 + s
                return min(total, MAX_RSS_SEC) if total > 0 else 0
        except ValueError:
            pass

    # Fallback: pure digits where OCR dropped colons (e.g. '114550' = 11:45:50)
    stripped = re.sub(r'[^0-9]', '', timer_str)
    if len(stripped) == 6:
        try:
            h, m, s = int(stripped[0:2]), int(stripped[2:4]), int(stripped[4:6])
            if m >= 60:
                m = m % 100 if m >= 100 else 59
            s = min(s, 59)
            total = h * 3600 + m * 60 + s
            return min(total, MAX_RSS_SEC) if total > 0 else 0
        except ValueError:
            pass
    elif len(stripped) == 4:
        try:
            m, s = int(stripped[0:2]), int(stripped[2:4])
            s = min(s, 59)
            total = m * 60 + s
            return min(total, MAX_RSS_SEC) if total > 0 else 0
        except ValueError:
            pass

    # Fallback: Xh Ym format
    hours, minutes = 0, 0
    h_match = re.search(r'(\d+)\s*h', timer_str, re.IGNORECASE)
    m_match = re.search(r'(\d+)\s*m', timer_str, re.IGNORECASE)
    if h_match:
        hours = int(h_match.group(1))
    if m_match:
        minutes = int(m_match.group(1))
    total = hours * 3600 + minutes * 60
    return total if total > 0 else 0


def parse_builder_count(text: str) -> int:
    """
    Parse builder count from OCR text like '1/36', '12/36', '1/336' (OCR noise).
    Returns the first number (current count). Returns 0 if parse fails.
    """
    if not text:
        return 0
    # Match pattern: number / number
    match = re.search(r'(\d+)\s*/\s*(\d+)', text)
    if match:
        return int(match.group(1))
    # Fallback: just first number
    digits = re.findall(r'\d+', text)
    return int(digits[0]) if digits else 0


def ocr_region_text(serial: str, detector, roi_box: tuple, style: str = "standard") -> str:
    """
    OCR a specific pixel region (x1, y1, x2, y2) from a fresh screenshot.
    style: 'standard' (dark text on light bg) or 'outline' (white text, black outline, light bg)
    """
    _ensure_tesseract()
    screen = detector.screencap_memory(serial)
    if screen is None:
        print(f"[{serial}] [OCR] Screenshot failed.")
        return ""

    return ocr_from_frame(serial, screen, roi_box, style=style)


def ocr_region_with_retry(serial: str, detector, roi_box: tuple,
                          attempts: int = 3, style: str = "standard",
                          validator=None) -> str:
    """
    OCR with multiple attempts + majority voting for reliability.
    validator: optional function(text) -> bool to filter valid results.
    Returns the most common valid result, or best available.
    """
    import time
    from collections import Counter
    results = []
    for i in range(attempts):
        text = ocr_region_text(serial, detector, roi_box, style=style)
        if text:
            results.append(text)
        if i < attempts - 1:
            time.sleep(0.3)

    if not results:
        return ""

    # Filter by validator if provided
    if validator:
        valid = [r for r in results if validator(r)]
        if valid:
            results = valid

    # Return most common result
    counter = Counter(results)
    best = counter.most_common(1)[0][0]
    print(f"[{serial}] [OCR-RETRY] {attempts} attempts, results: {dict(counter)}, best: '{best}'")
    return best


def ocr_from_frame(serial: str, screen: np.ndarray, roi_box: tuple, style: str = "standard") -> str:
    """
    OCR a specific pixel region (x1, y1, x2, y2) from a provided frame.
    style: 'standard' (OTSU threshold) or 'outline' (isolate dark outline from white text)
    """
    _ensure_tesseract()
    x1, y1, x2, y2 = roi_box
    h, w = screen.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)

    if x2 <= x1 or y2 <= y1:
        print(f"[{serial}] [OCR] Invalid ROI: {roi_box}")
        return ""

    crop = screen[y1:y2, x1:x2]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    if style == "outline":
        # Black Hat morphology: extracts dark features on bright backgrounds.
        # Perfect for white text with dark outline on light bg.
        scale = 4
        crop_large = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        bh_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        blackhat = cv2.morphologyEx(crop_large, cv2.MORPH_BLACKHAT, bh_kernel)
        _, binary = cv2.threshold(blackhat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        binary = cv2.bitwise_not(binary)
        # Clean up: clear left 10% margin (clock icon noise) and small components
        margin = int(binary.shape[1] * 0.10)
        binary[:, :margin] = 255  # white = background for tesseract
    else:
        # Standard: upscale 3x + OTSU
        scale = 3
        crop_large = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        _, binary = cv2.threshold(crop_large, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    text = pytesseract.image_to_string(
        binary,
        config='--psm 7 -c tessedit_char_whitelist=0123456789dhm/:'
    ).strip()
    print(f"[{serial}] [OCR] ROI {roi_box} [{style}] -> '{text}'")
    return text
