"""
Pet Skill Drop Rate Analyzer
Extracts skill pool + obtained skill data from release screenshots -> JSON.
"""

import os
import json
import re
import cv2
import numpy as np
from datetime import datetime


# ── Slot Grid Layout ──────────────────────────────────────────────
# Within the cropped "available" image (450×150px, from 250,150->700,300)
# 8 slots: 4 cols × 2 rows. Pet avatar occupies left ~80px.
_SLOT_ROIS = [
    # Row 1 (top): y = 5–70
    (100, 5, 165, 70),   # Slot 1
    (165, 5, 230, 70),   # Slot 2
    (230, 5, 295, 70),   # Slot 3
    (295, 5, 360, 70),   # Slot 4
    # Row 2 (bottom): y = 70–135
    (100, 70, 165, 135),  # Slot 5
    (165, 70, 230, 135),  # Slot 6
    (230, 70, 295, 135),  # Slot 7
    (295, 70, 360, 135),  # Slot 8
]

# Variance thresholds:
# - Pure background (no slot): < 30
# - Empty frame (slot exists but no skill): 30–500
# - Filled skill icon: > 500
_FRAME_THRESHOLD = 30
_SKILL_THRESHOLD = 500

DATA_DIR = os.path.join("data", "pet_releases")
OUTPUT_FILE = os.path.join(DATA_DIR, "skill_data.json")


def _to_gray(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img


def _is_slot_filled(slot_crop: np.ndarray) -> bool:
    """Check if a slot has a skill icon based on pixel variance."""
    variance = float(np.var(_to_gray(slot_crop)))
    return variance > _SKILL_THRESHOLD


def _is_slot_present(slot_crop: np.ndarray) -> bool:
    """Check if a slot exists (frame or filled) vs pure background."""
    variance = float(np.var(_to_gray(slot_crop)))
    return variance > _FRAME_THRESHOLD


def _detect_slots(available_img: np.ndarray) -> tuple[int, int]:
    """Detect filled skill count and total slot count.

    Returns: (filled_count, total_count)
    """
    filled = 0
    total = 0
    for x1, y1, x2, y2 in _SLOT_ROIS:
        slot_crop = available_img[y1:y2, x1:x2]
        if slot_crop.size == 0:
            continue
        if _is_slot_present(slot_crop):
            total += 1
            if _is_slot_filled(slot_crop):
                filled += 1
    return filled, total


# Star template for rating detection (loaded once)
_STAR_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "star_template.png")
_STAR_TEMPLATE = None
_STAR_MATCH_THRESHOLD = 0.7


def _load_star_template():
    global _STAR_TEMPLATE
    if _STAR_TEMPLATE is None:
        _STAR_TEMPLATE = cv2.imread(_STAR_TEMPLATE_PATH)
    return _STAR_TEMPLATE


def _detect_star_count(slot_crop: np.ndarray) -> int:
    """Detect star rating (0-3) by template matching in bottom strip of slot."""
    tmpl = _load_star_template()
    if tmpl is None:
        return 0

    # Search in bottom 20px of slot
    bottom = slot_crop[45:65, :]
    if bottom.shape[0] < tmpl.shape[0] or bottom.shape[1] < tmpl.shape[1]:
        return 0

    result = cv2.matchTemplate(bottom, tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    return 1 if max_val >= _STAR_MATCH_THRESHOLD else 0


def _detect_skill_stars(available_img: np.ndarray) -> list[int]:
    """Detect star rating for each filled slot. Returns list of star counts."""
    stars = []
    for x1, y1, x2, y2 in _SLOT_ROIS:
        slot_crop = available_img[y1:y2, x1:x2]
        if slot_crop.size == 0 or not _is_slot_filled(slot_crop):
            continue
        stars.append(_detect_star_count(slot_crop))
    return stars


def _center_crop(img: np.ndarray, ratio: float = 0.6) -> np.ndarray:
    """Crop the center portion of an image, removing border/frame."""
    h, w = img.shape[:2]
    margin_x = int(w * (1 - ratio) / 2)
    margin_y = int(h * (1 - ratio) / 2)
    return img[margin_y:h - margin_y, margin_x:w - margin_x]


def _calc_color_histogram(img: np.ndarray) -> np.ndarray:
    """Calculate normalized HSV color histogram for an image."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV) if len(img.shape) == 3 else img
    hist = cv2.calcHist([hsv], [0, 1], None, [30, 32], [0, 180, 0, 256])
    cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
    return hist


def _find_best_matching_slot(get_img: np.ndarray, available_img: np.ndarray) -> tuple:
    """Match the get skill icon against each filled pool slot.

    Uses combined scoring:
    - HSV color histogram correlation (70% weight) - distinguishes by color
    - Normalized grayscale template matching (30% weight) - distinguishes by pattern

    Both images are center-cropped to 60% to remove gold borders/background noise.

    Returns: (best_slot_index, confidence, all_scores_dict)
    """
    # Center-crop get image to remove background padding
    get_center = _center_crop(get_img)
    get_hist = _calc_color_histogram(get_center)
    get_gray = _to_gray(get_center)

    best_slot = -1
    best_score = -1.0
    scores = {}

    for idx, (x1, y1, x2, y2) in enumerate(_SLOT_ROIS):
        slot_crop = available_img[y1:y2, x1:x2]
        if slot_crop.size == 0 or not _is_slot_filled(slot_crop):
            continue

        # Center-crop slot to remove frame
        slot_center = _center_crop(slot_crop)

        # Score 1: Color histogram correlation
        slot_hist = _calc_color_histogram(slot_center)
        hist_score = cv2.compareHist(get_hist, slot_hist, cv2.HISTCMP_CORREL)

        # Score 2: Template matching on grayscale (resize to same dimensions)
        slot_gray = _to_gray(slot_center)
        get_resized = cv2.resize(get_gray, (slot_gray.shape[1], slot_gray.shape[0]))
        result = cv2.matchTemplate(slot_gray, get_resized, cv2.TM_CCOEFF_NORMED)
        _, tmpl_score, _, _ = cv2.minMaxLoc(result)

        # Combined score: 70% color + 30% template
        combined = hist_score * 0.7 + tmpl_score * 0.3

        slot_num = idx + 1
        scores[slot_num] = round(combined, 4)

        if combined > best_score:
            best_score = combined
            best_slot = slot_num

    return best_slot, round(best_score, 4), scores


def _parse_filename(filename: str) -> tuple[str, str]:
    """Extract serial and timestamp from available_*.png filename."""
    match = re.match(r"available_(emulator-\d+)_(\d{8}_\d{6})\.png", filename)
    if not match:
        return "unknown", datetime.now().strftime("%Y%m%d_%H%M%S")
    return match.group(1), match.group(2)


def _timestamp_to_readable(ts: str) -> str:
    """Convert '20260321_030449' -> '2026-03-21 03:04:49'."""
    return f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[9:11]}:{ts[11:13]}:{ts[13:15]}"


def analyze_pair(available_path: str, get_path: str) -> dict | None:
    """Analyze a single pair of available + get images."""
    available_img = cv2.imread(available_path)
    get_img = cv2.imread(get_path)

    if available_img is None or get_img is None:
        print(f"[ANALYZER] Could not load images: {available_path} / {get_path}")
        return None

    filled_count, total_count = _detect_slots(available_img)
    matched_slot, confidence, all_scores = _find_best_matching_slot(get_img, available_img)
    skill_stars = _detect_skill_stars(available_img)

    serial, timestamp = _parse_filename(os.path.basename(available_path))

    return {
        "release_id": f"{serial}_{timestamp}",
        "emulator": serial,
        "datetime": _timestamp_to_readable(timestamp),
        "pool_total_slots": total_count,
        "pool_filled_count": filled_count,
        "skill_stars": skill_stars,
        "get_slot_position": matched_slot,
    }


def run_analysis(data_dir: str = DATA_DIR, output_file: str = OUTPUT_FILE):
    """Scan data directory for new pairs, analyze, and append to JSON."""
    # Load existing data
    existing = []
    existing_ids = set()
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            existing = json.load(f)
        existing_ids = {e["release_id"] for e in existing}

    # Find available_*.png files
    if not os.path.exists(data_dir):
        print(f"[ANALYZER] Data directory not found: {data_dir}")
        return []

    available_files = sorted([
        f for f in os.listdir(data_dir)
        if f.startswith("available_") and f.endswith(".png")
    ])

    new_count = 0
    for af in available_files:
        serial, timestamp = _parse_filename(af)
        release_id = f"{serial}_{timestamp}"

        if release_id in existing_ids:
            continue

        gf = f"get_{serial}_{timestamp}.png"
        get_path = os.path.join(data_dir, gf)
        if not os.path.exists(get_path):
            print(f"[ANALYZER] [WARN] Missing get file for {af}, skipping.")
            continue

        result = analyze_pair(os.path.join(data_dir, af), get_path)
        if result:
            existing.append(result)
            existing_ids.add(release_id)
            new_count += 1
            print(
                f"[ANALYZER] [OK] {release_id}: "
                f"pool={result['pool_filled_count']} skills, "
                f"get=slot#{result['get_slot_position']}"
            )

    # Save
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    print(f"\n[ANALYZER] Done. {new_count} new, {len(existing)} total.")
    print(f"[ANALYZER] Saved -> {os.path.abspath(output_file)}")

    return existing


def run_debug(data_dir: str = DATA_DIR):
    """Debug mode: save individual slot crops for ROI verification."""
    debug_dir = os.path.join(data_dir, "debug_slots")
    os.makedirs(debug_dir, exist_ok=True)

    available_files = [
        f for f in os.listdir(data_dir)
        if f.startswith("available_") and f.endswith(".png")
    ]

    if not available_files:
        print("[DEBUG] No available_*.png files found.")
        return

    # Use the first file for debug
    af = available_files[0]
    img = cv2.imread(os.path.join(data_dir, af))
    if img is None:
        print(f"[DEBUG] Could not load {af}")
        return

    print(f"[DEBUG] Using: {af} ({img.shape[1]}×{img.shape[0]})")
    print(f"[DEBUG] Saving slot crops to {debug_dir}/\n")

    for idx, (x1, y1, x2, y2) in enumerate(_SLOT_ROIS):
        slot_num = idx + 1
        slot_crop = img[y1:y2, x1:x2]
        variance = float(np.var(_to_gray(slot_crop)))
        if variance > _SKILL_THRESHOLD:
            status = "FILLED"
        elif variance > _FRAME_THRESHOLD:
            status = "FRAME"
        else:
            status = "EMPTY"

        fname = f"slot_{slot_num}_{status.lower()}_var{int(variance)}.png"
        cv2.imwrite(os.path.join(debug_dir, fname), slot_crop)
        print(f"  Slot {slot_num}: ROI=({x1},{y1},{x2},{y2}) variance={variance:.0f} -> {status}")

    # Also annotate full image with rectangles
    annotated = img.copy()
    for idx, (x1, y1, x2, y2) in enumerate(_SLOT_ROIS):
        slot_crop = img[y1:y2, x1:x2]
        variance = float(np.var(_to_gray(slot_crop)))
        if variance > _SKILL_THRESHOLD:
            color = (0, 255, 0)    # Green = filled
        elif variance > _FRAME_THRESHOLD:
            color = (0, 255, 255)  # Yellow = empty frame
        else:
            color = (0, 0, 255)    # Red = background
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        cv2.putText(annotated, str(idx + 1), (x1 + 5, y1 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    annotated_path = os.path.join(debug_dir, "annotated_grid.png")
    cv2.imwrite(annotated_path, annotated)
    print(f"\n[DEBUG] Annotated grid -> {annotated_path}")
    print("[DEBUG] Green=filled, Yellow=frame, Red=background.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pet Skill Drop Rate Analyzer")
    parser.add_argument("--debug", action="store_true",
                        help="Debug mode: save slot crops for ROI verification")
    parser.add_argument("--data-dir", default=DATA_DIR,
                        help=f"Data directory (default: {DATA_DIR})")
    args = parser.parse_args()

    if args.debug:
        run_debug(args.data_dir)
    else:
        run_analysis(args.data_dir)
