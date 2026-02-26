"""
OCR Engine — Image processing and text extraction pipeline.
Enhanced from cod_app_sync.py with dual-strategy OCR.
"""
import cv2
import numpy as np
import pytesseract
import json
import os
from backend.config import config


class OCREngine:
    """Handles all image processing and OCR operations."""

    def __init__(self):
        pytesseract.pytesseract.tesseract_cmd = config.tesseract_path
        self._regions = {}
        self._load_coordinate_map()

    def _load_coordinate_map(self):
        """Load OCR regions from coordinate map JSON."""
        map_path = config.get_coordinate_map_path()
        if os.path.exists(map_path):
            with open(map_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._regions = data.get("regions", {})
        else:
            print(f"[OCR] Warning: Coordinate map not found at {map_path}")

    @property
    def regions(self) -> dict:
        return self._regions

    def load_image(self, image_path: str) -> np.ndarray | None:
        """Load and normalize image to configured resolution."""
        if not os.path.exists(image_path):
            return None
        img = cv2.imread(image_path)
        if img is None:
            return None

        # Parse target resolution
        res = config.resolution.split("x")
        target_w, target_h = int(res[0]), int(res[1])

        h, w = img.shape[:2]
        if h != target_h or w != target_w:
            img = cv2.resize(img, (target_w, target_h))

        # Sharpen
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        img = cv2.filter2D(img, -1, kernel)
        return img

    def extract_roi(self, img: np.ndarray, region_name: str) -> np.ndarray | None:
        """Extract a region of interest (ROI) by name."""
        if region_name not in self._regions:
            return None
        x1, y1, x2, y2 = self._regions[region_name]
        roi = img[y1:y2, x1:x2]
        if roi.size == 0:
            return None
        return roi

    def preprocess(self, roi: np.ndarray, scale: float = 2.0, invert: bool = True) -> np.ndarray:
        """Standard preprocessing: scale up, grayscale, threshold, border."""
        if roi is None or roi.size == 0:
            return roi
        scaled = cv2.resize(roi, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        if invert:
            final = cv2.bitwise_not(thresh)
        else:
            final = thresh
        final = cv2.copyMakeBorder(final, 10, 10, 15, 15, cv2.BORDER_CONSTANT, value=255)
        return final

    def ocr_text(self, img: np.ndarray, whitelist: str = None) -> str:
        """Run Tesseract OCR on a preprocessed image."""
        if img is None:
            return ""
        cfg = "--psm 7"
        if whitelist:
            cfg += f" -c tessedit_char_whitelist={whitelist}"
        try:
            return pytesseract.image_to_string(img, config=cfg).strip()
        except Exception as e:
            print(f"[OCR] Error: {e}")
            return ""

    def ocr_pet_token(self, roi: np.ndarray) -> str:
        """Dual-strategy OCR for pet token (small, tricky region).
        
        Pipeline A: Standard scale x4
        Pipeline B: Erode + threshold
        Picks the longer result.
        """
        if roi is None or roi.size == 0:
            return "0"

        # Pipeline A: Standard
        scaled = cv2.resize(roi, None, fx=4.0, fy=4.0, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
        _, thresh_a = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        img_a = cv2.copyMakeBorder(thresh_a, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)

        # Pipeline B: Erode
        kernel = np.ones((2, 2), np.uint8)
        gray_b = cv2.erode(gray, kernel, iterations=1)
        _, thresh_b = cv2.threshold(gray_b, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        img_b = cv2.copyMakeBorder(thresh_b, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)

        cfg = "--psm 7 -c tessedit_char_whitelist=0123456789"
        text_a = pytesseract.image_to_string(img_a, config=cfg).strip()
        text_b = pytesseract.image_to_string(img_b, config=cfg).strip()

        return text_b if len(text_b) > len(text_a) else text_a

    def parse_number(self, text: str) -> int:
        """Parse OCR text into integer, handling K/M/B suffixes."""
        text = text.upper().strip().replace(" ", "").replace(",", "").replace(".", "")
        multiplier = 1
        if text.endswith("K"):
            multiplier = 1_000
            text = text[:-1]
        elif text.endswith("M"):
            multiplier = 1_000_000
            text = text[:-1]
        elif text.endswith("B"):
            multiplier = 1_000_000_000
            text = text[:-1]
        try:
            return int(float(text) * multiplier)
        except (ValueError, TypeError):
            return 0

    # ──────────────────────────────────────────────
    # High-level scan methods
    # ──────────────────────────────────────────────

    def scan_profile(self, img: np.ndarray) -> dict:
        """Extract profile name and power from screenshot."""
        name_roi = self.extract_roi(img, "profile_name")
        power_roi = self.extract_roi(img, "profile_power")

        name = self.ocr_text(self.preprocess(name_roi))
        power_text = self.ocr_text(self.preprocess(power_roi), "0123456789.,KMB")
        power = self.parse_number(power_text)

        return {"name": name, "power": power, "power_raw": power_text}

    def scan_resources(self, img: np.ndarray) -> dict:
        """Extract gold/wood/ore/mana item and total values."""
        result = {}
        for res_type in ["gold", "wood", "ore", "mana"]:
            item_roi = self.extract_roi(img, f"res_{res_type}_item")
            total_roi = self.extract_roi(img, f"res_{res_type}_total")

            item_text = self.ocr_text(self.preprocess(item_roi), "0123456789.,KMB")
            total_text = self.ocr_text(self.preprocess(total_roi), "0123456789.,KMB")

            result[res_type] = {
                "bag": self.parse_number(item_text),
                "total": self.parse_number(total_text),
                "bag_raw": item_text,
                "total_raw": total_text,
            }
        return result

    def scan_building_level(self, img: np.ndarray) -> int:
        """Extract building level number."""
        roi = self.extract_roi(img, "building_level")
        text = self.ocr_text(self.preprocess(roi), "0123456789")
        try:
            return int(text) if text.isdigit() else 0
        except (ValueError, TypeError):
            return 0

    def scan_pet_token(self, img: np.ndarray) -> int:
        """Extract pet token count using dual-strategy OCR."""
        roi = self.extract_roi(img, "pet_token")
        text = self.ocr_pet_token(roi)
        try:
            return int(text) if text.isdigit() else 0
        except (ValueError, TypeError):
            return 0


# Lazy singleton — defer creation until config is loaded
_ocr_engine = None

def get_ocr_engine():
    """Return the OCR engine singleton, creating it lazily."""
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = OCREngine()
    return _ocr_engine

# Alias for backward compatibility
class _LazyOCRProxy:
    """Proxy that defers OCREngine creation until first attribute access."""
    def __getattr__(self, name):
        return getattr(get_ocr_engine(), name)

ocr_engine = _LazyOCRProxy()
