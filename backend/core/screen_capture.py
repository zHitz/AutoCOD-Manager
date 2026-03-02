"""
Screen Capture — ADB-based screenshot pipeline for game data extraction.

Navigates through 5 game phases using robust state-based navigation via core_actions,
captures screenshots, crops relevant regions, and combines them into a single PDF.
"""
import os
import time
import cv2
from PIL import Image, ImageOps

from backend.config import config
from backend.core.workflow import adb_helper
from backend.core.workflow import core_actions
from backend.core.workflow.state_detector import GameStateDetector

# Crop regions for each scan phase (x1, y1, x2, y2)
REGIONS_MAP = {
    "profile": {"profile_area": (100, 320, 275, 500)},
    "resources": {"resources_area": (300, 150, 725, 400)},
    "hall": {"hall_area": (500, 200, 750, 275)},
    "market": {"market_area": (500, 200, 750, 275)},
    "pet_token": {"pet_token_area": (875, 0, 950, 30)},
}

def combine_to_pdf(image_paths: list[str], output_path: str) -> bool:
    """Combine multiple images into a single-page PDF with OCR enhancements."""
    try:
        images = []
        for p in image_paths:
            if not os.path.exists(p):
                continue
            img = Image.open(p).convert("L") # grayscale for better OCR
            img = ImageOps.autocontrast(img) # enhance contrast
            images.append(img.convert("RGB"))
            
        if not images:
            return False

        max_width = max(img.width for img in images)
        total_height = sum(img.height for img in images)

        canvas = Image.new("RGB", (max_width, total_height), "white")
        y_offset = 0
        for img in images:
            canvas.paste(img, (0, y_offset))
            y_offset += img.height

        # Upscale canvas for OCR
        SCALE = 4
        canvas = canvas.resize(
            (canvas.width * SCALE, canvas.height * SCALE),
            Image.Resampling.LANCZOS
        )

        canvas.save(output_path, "PDF", resolution=300.0)
        print(f"[Capture] PDF created successfully at: {output_path}")
        return True
    except Exception as e:
        print(f"[Capture] PDF creation failed: {e}")
        return False

def crop_regions(screenshot_path: str, phase: str, output_dir: str) -> list[str]:
    """Crop relevant regions from a screenshot."""
    regions = REGIONS_MAP.get(phase, {})
    if not regions or not os.path.exists(screenshot_path):
        return []

    img = cv2.imread(screenshot_path)
    if img is None:
        return []

    cropped = []
    for name, (x1, y1, x2, y2) in regions.items():
        if x2 <= img.shape[1] and y2 <= img.shape[0]:
            roi = img[y1:y2, x1:x2]
            path = os.path.join(output_dir, f"{phase}_{name}.png")
            cv2.imwrite(path, roi)
            cropped.append(path)
    return cropped

def run_full_capture_modern(serial: str, detector: GameStateDetector, work_dir: str, progress_callback=None) -> str | None:
    """Run all 5 capture phases intelligently and combine into PDF."""
    safe_serial = serial.replace(":", "_").replace(".", "_")
    device_dir = os.path.join(work_dir, safe_serial)
    os.makedirs(device_dir, exist_ok=True)

    phases = ["profile", "resources", "hall", "market", "pet_token"]
    all_crops = []

    # Map phases to navigation actions
    nav_actions = {
        "profile": core_actions.go_to_profile_details,
        "resources": core_actions.go_to_resources,
        "hall": lambda s, d: core_actions.go_to_construction(serial, detector, "HALL"),
        "market": lambda s, d: core_actions.go_to_construction(serial, detector, "MARKET"),
        "pet_token": core_actions.go_to_pet_token
    }

    for idx, phase in enumerate(phases):
        step = idx + 1
        total = len(phases)

        if progress_callback:
            progress_callback(phase, step, total)

        print(f"[Capture] Phase {step}/{total}: {phase} on {serial}")

        # 1. Enforce Lobby starting state for each phase
        if not core_actions.back_to_lobby(serial, detector):
            print(f"[Capture] Failed to reach Lobby before {phase}. Aborting capture.")
            return None

        # 2. Navigate to target screen
        nav_func = nav_actions.get(phase)
        if nav_func:
            nav_func(serial, detector)
        else:
            print(f"[Capture] No navigation defined for {phase}.")

        # 3. Capture screenshot
        screenshot_path = os.path.join(device_dir, f"{phase}_full.png")
        success = adb_helper.screencap(serial, screenshot_path)
        
        if success:
            # 4. Crop
            crops = crop_regions(screenshot_path, phase, device_dir)
            all_crops.extend(crops)
        else:
            print(f"[Capture] Failed to capture screenshot for {phase}")

    # Return to lobby at the end of the full capture
    core_actions.back_to_lobby(serial, detector)

    if not all_crops:
        print(f"[Capture] No images captured for {serial}")
        return None

    # 5. Combine to PDF in expected order
    expected_order = [
        os.path.join(device_dir, "resources_resources_area.png"),
        os.path.join(device_dir, "profile_profile_area.png"),
        os.path.join(device_dir, "hall_hall_area.png"),
        os.path.join(device_dir, "market_market_area.png"),
        os.path.join(device_dir, "pet_token_pet_token_area.png"),
    ]
    ordered_crops = [p for p in expected_order if os.path.exists(p)]

    pdf_path = os.path.join(device_dir, "COMBINED_OCR.pdf")
    if combine_to_pdf(ordered_crops, pdf_path):
        return pdf_path

    return None
