"""
Trash Detector — Rule-based trash detection for Pet Sanctuary.

Detects trash (leaf piles, mushrooms, poop) by comparing a real screenshot
against a clean baseline image. Includes multi-frame voting and pixel stability
to reject pet idle animations.

Adapted from standalone clean_game_trash module for production use.
Uses detector.screencap_memory() instead of file-based screenshots.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Sequence

import cv2
import numpy as np

_REF_WIDTH = 1920
_REF_HEIGHT = 1080

# Multi-frame voting defaults
_NUM_FRAMES = 3
_FRAME_INTERVAL = 2.0
_MATCH_RADIUS = 20
_STABILITY_THRESHOLD = 14.0


# ---------------------------------------------------------------------------
# Detection dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Detection:
    bbox: tuple[int, int, int, int]    # (x, y, w, h)
    center: tuple[int, int]            # (cx, cy)
    label: str
    score: float


# ---------------------------------------------------------------------------
# Core detection pipeline
# ---------------------------------------------------------------------------

def detect_trash(
    real_img: np.ndarray,
    clean_img: np.ndarray,
    *,
    score_threshold: float = 0.0,
    return_debug: bool = False,
) -> list[Detection] | tuple[list[Detection], np.ndarray]:
    """Detect trash piles present in `real_img` but absent in `clean_img`."""
    _validate_images(real_img, clean_img)

    scale = _compute_scale(real_img.shape[:2])
    roi_mask = _build_roi_mask(real_img.shape[:2])
    diff_mask = _build_diff_mask(real_img, clean_img, roi_mask, scale)
    contours = _extract_candidate_contours(diff_mask)

    accepted: list[tuple[int, int, int, int, float]] = []
    rejected: list[tuple[int, int, int, int]] = []

    for contour in contours:
        bbox, score = _score_candidate(contour, real_img, diff_mask, scale)
        if bbox is None:
            x, y, w, h = cv2.boundingRect(contour)
            rejected.append((x, y, w, h))
            continue
        accepted.append((*bbox, score))

    merged = _merge_boxes(accepted, scale)
    detections: list[Detection] = []
    for x, y, w, h, score in sorted(merged, key=lambda item: (item[1], item[0])):
        rounded_score = round(score, 3)
        if rounded_score < score_threshold:
            rejected.append((x, y, w, h))
            continue
        detections.append(
            Detection(
                bbox=(x, y, w, h),
                center=(x + w // 2, y + h // 2),
                label="trash",
                score=rounded_score,
            )
        )

    if not return_debug:
        return detections

    debug_image = _build_debug_image(real_img, roi_mask, diff_mask, detections, rejected)
    return detections, debug_image


# ---------------------------------------------------------------------------
# Multi-frame voting + pixel stability
# ---------------------------------------------------------------------------

def detect_with_voting(
    serial: str,
    detector,
    clean_img: np.ndarray,
    score_threshold: float = 0.30,
    num_frames: int = _NUM_FRAMES,
    frame_interval: float = _FRAME_INTERVAL,
    match_radius: float = _MATCH_RADIUS,
    stability_threshold: float = _STABILITY_THRESHOLD,
) -> list[Detection]:
    """
    Capture N frames via detector.screencap_memory(), detect trash on each,
    apply position voting + pixel stability to filter false positives.

    Returns list of confirmed Detection objects.
    """
    frames_detections: list[list[Detection]] = []
    frame_images: list[np.ndarray] = []

    for i in range(num_frames):
        if i > 0:
            time.sleep(frame_interval)

        screen = detector.screencap_memory(serial)
        if screen is None:
            frames_detections.append([])
            continue

        frame_images.append(screen)
        detections = detect_trash(screen, clean_img, score_threshold=score_threshold)
        frames_detections.append(detections)
        print(f"[{serial}] [TRASH]   Frame {i + 1}: {len(detections)} candidate(s)")

    # Step 1: Position voting
    confirmed = _vote_detections(frames_detections, min_votes=num_frames, match_radius=match_radius)
    total_candidates = sum(len(d) for d in frames_detections)
    print(f"[{serial}] [TRASH]   Position vote: {total_candidates} -> {len(confirmed)}")

    # Step 2: Pixel stability
    if confirmed:
        confirmed = _check_pixel_stability(serial, confirmed, frame_images, max_diff=stability_threshold)
        print(f"[{serial}] [TRASH]   Pixel stable: {len(confirmed)} confirmed")

    return confirmed


# ---------------------------------------------------------------------------
# Voting helpers
# ---------------------------------------------------------------------------

def _distance(a: tuple[int, int], b: tuple[int, int]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def _vote_detections(
    frames_detections: list[list[Detection]],
    min_votes: int,
    match_radius: float = _MATCH_RADIUS,
) -> list[Detection]:
    """Keep only detections that appear in >= min_votes frames at the same position."""
    if not frames_detections:
        return []

    # Collect unique anchor positions across all frames
    anchors: list[Detection] = []
    for frame_dets in frames_detections:
        for det in frame_dets:
            is_duplicate = any(
                _distance(det.center, a.center) <= match_radius for a in anchors
            )
            if not is_duplicate:
                anchors.append(det)

    # Count votes per anchor
    confirmed: list[Detection] = []
    for anchor in anchors:
        votes = 0
        best_score = 0.0
        best_det = anchor

        for frame_dets in frames_detections:
            for det in frame_dets:
                if _distance(anchor.center, det.center) <= match_radius:
                    votes += 1
                    if det.score > best_score:
                        best_score = det.score
                        best_det = det
                    break

        if votes >= min_votes:
            confirmed.append(best_det)

    confirmed.sort(key=lambda d: (d.center[1], d.center[0]))
    return confirmed


def _check_pixel_stability(
    serial: str,
    confirmed: list[Detection],
    frame_images: list[np.ndarray],
    max_diff: float = _STABILITY_THRESHOLD,
) -> list[Detection]:
    """Reject detections whose bbox pixels differ across frames (pet idle animation)."""
    if len(frame_images) < 2:
        return confirmed

    stable: list[Detection] = []
    for det in confirmed:
        x, y, w, h = det.bbox
        patches = [img[y:y + h, x:x + w] for img in frame_images]

        diffs = []
        for i in range(len(patches)):
            for j in range(i + 1, len(patches)):
                if patches[i].shape == patches[j].shape:
                    diff = cv2.absdiff(patches[i], patches[j]).astype(np.float32)
                    diffs.append(float(np.mean(diff)))

        if not diffs:
            stable.append(det)
            continue

        avg_diff = sum(diffs) / len(diffs)
        if avg_diff <= max_diff:
            stable.append(det)
            print(f"[{serial}] [TRASH]   OK ({det.center[0]}, {det.center[1]}) diff={avg_diff:.1f} -> STABLE")
        else:
            print(f"[{serial}] [TRASH]   XX ({det.center[0]}, {det.center[1]}) diff={avg_diff:.1f} -> REJECTED (animation)")

    return stable


# ---------------------------------------------------------------------------
# Image validation & scaling
# ---------------------------------------------------------------------------

def _validate_images(real_img: np.ndarray, clean_img: np.ndarray) -> None:
    if real_img is None or clean_img is None:
        raise ValueError("real_img and clean_img must be valid images")
    if real_img.shape != clean_img.shape:
        raise ValueError(
            "real_img and clean_img must have the same shape; "
            f"got {real_img.shape} vs {clean_img.shape}"
        )
    if real_img.ndim != 3 or real_img.shape[2] != 3:
        raise ValueError("Images must be BGR color arrays with shape (H, W, 3)")


def _compute_scale(shape: tuple[int, int]) -> float:
    """Compute linear scale factor relative to 1920x1080 reference."""
    height, width = shape
    return min(width / _REF_WIDTH, height / _REF_HEIGHT)


# ---------------------------------------------------------------------------
# ROI & diff mask
# ---------------------------------------------------------------------------

def _build_roi_mask(shape: tuple[int, int]) -> np.ndarray:
    height, width = shape
    mask = np.zeros((height, width), dtype=np.uint8)

    def scale(points):
        return np.array(
            [[int(px * width), int(py * height)] for px, py in points],
            dtype=np.int32,
        )

    playable_polygon = scale([
        (0.07, 0.20), (0.18, 0.15), (0.44, 0.11), (0.77, 0.14),
        (0.88, 0.24), (0.90, 0.55), (0.83, 0.84), (0.66, 0.91),
        (0.51, 0.96), (0.34, 0.92), (0.17, 0.84), (0.08, 0.65),
    ])
    cv2.fillPoly(mask, [playable_polygon], 255)

    exclusions = [
        (0.0, 0.0, 0.78, 0.10), (0.78, 0.0, 1.0, 0.20),
        (0.86, 0.12, 1.0, 0.72), (0.0, 0.88, 1.0, 1.0),
        (0.0, 0.0, 0.07, 1.0), (0.93, 0.0, 1.0, 1.0),
    ]
    for x0, y0, x1, y1 in exclusions:
        cv2.rectangle(
            mask,
            (int(x0 * width), int(y0 * height)),
            (int(x1 * width), int(y1 * height)),
            0, thickness=-1,
        )

    return mask


def _build_diff_mask(
    real_img: np.ndarray, clean_img: np.ndarray, roi_mask: np.ndarray, scale: float = 1.0,
) -> np.ndarray:
    real_lab = cv2.cvtColor(real_img, cv2.COLOR_BGR2LAB)
    clean_lab = cv2.cvtColor(clean_img, cv2.COLOR_BGR2LAB)
    delta_lab = cv2.absdiff(real_lab, clean_lab).astype(np.int16)

    delta_l = delta_lab[:, :, 0]
    delta_a = delta_lab[:, :, 1]
    delta_b = delta_lab[:, :, 2]
    delta_score = (0.7 * delta_l) + (1.2 * delta_a) + (1.2 * delta_b)
    diff_mask = ((delta_score >= 42) | ((delta_l >= 20) & ((delta_a + delta_b) >= 22))).astype(
        np.uint8
    ) * 255

    hsv = cv2.cvtColor(real_img, cv2.COLOR_BGR2HSV)
    h = hsv[:, :, 0]
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]

    green_mask = (h >= 18) & (h <= 48) & (s >= 55) & (v >= 55)
    yellow_mask = (h >= 10) & (h <= 25) & (s >= 70) & (v >= 75)
    brown_mask = (h >= 5) & (h <= 20) & (s >= 45) & (v >= 35) & (v <= 175)
    trash_color_mask = (green_mask | yellow_mask | brown_mask).astype(np.uint8) * 255

    candidate_mask = cv2.bitwise_and(diff_mask, trash_color_mask)
    candidate_mask = cv2.bitwise_and(candidate_mask, roi_mask)

    # Scale morphological kernels by resolution
    k_open = max(int(round(5 * scale)), 3) | 1
    k_close = max(int(round(11 * scale)), 3) | 1
    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_open, k_open))
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_close, k_close))
    candidate_mask = cv2.morphologyEx(candidate_mask, cv2.MORPH_OPEN, kernel_open)
    candidate_mask = cv2.morphologyEx(candidate_mask, cv2.MORPH_CLOSE, kernel_close)

    return candidate_mask


# ---------------------------------------------------------------------------
# Contour extraction & scoring
# ---------------------------------------------------------------------------

def _extract_candidate_contours(mask: np.ndarray) -> list[np.ndarray]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours


def _score_candidate(
    contour: np.ndarray,
    real_img: np.ndarray,
    diff_mask: np.ndarray,
    scale: float = 1.0,
) -> tuple[tuple[int, int, int, int] | None, float]:
    area = cv2.contourArea(contour)
    x, y, w, h = cv2.boundingRect(contour)

    # Scale area and bbox thresholds by resolution
    s2 = scale * scale
    min_area = max(int(110 * s2), 20)
    max_area = int(6500 * s2)
    min_dim = max(int(12 * scale), 5)
    max_dim = int(150 * scale)
    max_bbox_area = int(12000 * s2)

    if area < min_area or area > max_area:
        return None, 0.0
    if w < min_dim or h < min_dim or w > max_dim or h > max_dim:
        return None, 0.0
    if w * h > max_bbox_area:
        return None, 0.0

    aspect_ratio = w / float(h)
    if not 0.35 <= aspect_ratio <= 3.2:
        return None, 0.0

    hull = cv2.convexHull(contour)
    hull_area = max(cv2.contourArea(hull), 1.0)
    solidity = float(area / hull_area)
    extent = float(area / max(w * h, 1))
    perimeter = max(cv2.arcLength(contour, True), 1.0)
    compactness = float((4.0 * np.pi * area) / (perimeter * perimeter))

    if solidity < 0.35 or extent < 0.12 or compactness < 0.12:
        return None, 0.0

    contour_mask = np.zeros(diff_mask.shape, dtype=np.uint8)
    cv2.drawContours(contour_mask, [contour], -1, 255, thickness=-1)
    active_pixels = cv2.countNonZero(cv2.bitwise_and(diff_mask, contour_mask))
    color_ratio = active_pixels / float(max(w * h, 1))
    if color_ratio < 0.11:
        return None, 0.0

    patch = real_img[y: y + h, x: x + w]
    hsv_patch = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    pink_mask = cv2.inRange(hsv_patch, (135, 50, 120), (179, 255, 255))
    blue_mask = cv2.inRange(hsv_patch, (85, 40, 60), (125, 255, 255))
    pink_ratio = cv2.countNonZero(pink_mask) / float(max(w * h, 1))
    blue_ratio = cv2.countNonZero(blue_mask) / float(max(w * h, 1))

    if pink_ratio > 0.12 or blue_ratio > 0.28:
        return None, 0.0

    # Scale score normalization area
    norm_area = 1400.0 * s2
    score = (
        min(area / norm_area, 1.0) * 0.35
        + min(color_ratio / 0.4, 1.0) * 0.35
        + min(solidity, 1.0) * 0.15
        + min(compactness, 1.0) * 0.15
    )
    return (x, y, w, h), min(score, 0.999)


# ---------------------------------------------------------------------------
# Box merging
# ---------------------------------------------------------------------------

def _merge_boxes(
    boxes: Sequence[tuple[int, int, int, int, float]], scale: float = 1.0,
) -> list[tuple[int, int, int, int, float]]:
    merge_gap = max(int(round(18 * scale)), 6)
    merged = list(boxes)
    changed = True
    while changed:
        changed = False
        result: list[tuple[int, int, int, int, float]] = []
        used = [False] * len(merged)

        for idx, current in enumerate(merged):
            if used[idx]:
                continue
            x, y, w, h, score = current
            x2 = x + w
            y2 = y + h
            combined_score = score
            used[idx] = True

            for jdx in range(idx + 1, len(merged)):
                if used[jdx]:
                    continue
                ox, oy, ow, oh, oscore = merged[jdx]
                ox2 = ox + ow
                oy2 = oy + oh

                close_x = not (x2 + merge_gap < ox or ox2 + merge_gap < x)
                close_y = not (y2 + merge_gap < oy or oy2 + merge_gap < y)
                if not (close_x and close_y):
                    continue

                x = min(x, ox)
                y = min(y, oy)
                x2 = max(x2, ox2)
                y2 = max(y2, oy2)
                combined_score = max(combined_score, oscore)
                used[jdx] = True
                changed = True

            result.append((x, y, x2 - x, y2 - y, combined_score))
        merged = result

    return merged


# ---------------------------------------------------------------------------
# Debug image builder
# ---------------------------------------------------------------------------

def _build_debug_image(
    real_img: np.ndarray,
    roi_mask: np.ndarray,
    diff_mask: np.ndarray,
    detections: Sequence[Detection],
    rejected: Sequence[tuple[int, int, int, int]],
) -> np.ndarray:
    overlay = real_img.copy()
    roi_outline, _ = cv2.findContours(roi_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(overlay, roi_outline, -1, (255, 255, 255), thickness=2)

    diff_bgr = cv2.cvtColor(diff_mask, cv2.COLOR_GRAY2BGR)
    overlay = cv2.addWeighted(overlay, 1.0, diff_bgr, 0.18, 0.0)

    for x, y, w, h in rejected:
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (32, 32, 255), 1)

    for detection in detections:
        x, y, w, h = detection.bbox
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (50, 220, 50), 2)
        center_x, center_y = detection.center
        radius = max(int(round(max(w, h) * 0.65)), 14)
        cv2.circle(overlay, (center_x, center_y), radius, (0, 0, 255), 3)
        cv2.putText(
            overlay,
            f"{detection.score:.2f}",
            (x, max(y - 6, 0)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (50, 220, 50),
            2,
            cv2.LINE_AA,
        )

    return overlay


# ---------------------------------------------------------------------------
# Utility exports
# ---------------------------------------------------------------------------

def load_image(path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Unable to read image: {path}")
    return image


def save_debug_image(path, image: np.ndarray) -> None:
    ok = cv2.imwrite(str(path), image)
    if not ok:
        raise OSError(f"Unable to write debug image: {path}")


def detections_to_json(detections: Sequence[Detection]) -> str:
    import json
    return json.dumps([asdict(detection) for detection in detections], indent=2)
