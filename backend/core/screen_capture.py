"""
Screen Capture — ADB-based screenshot pipeline for game data extraction.

Navigates through 5 game phases via ADB taps, captures screenshots,
crops relevant regions, and combines them into a single PDF.
"""
import subprocess
import os
import time
import cv2
from PIL import Image
from backend.config import config


# Crop regions for each scan phase (x1, y1, x2, y2)
REGIONS_MAP = {
    "profile": {
        "profile_area": (100, 320, 275, 500),
    },
    "resources": {
        "resources_area": (300, 150, 725, 400),
    },
    "hall": {
        "hall_area": (500, 200, 750, 275),
    },
    "market": {
        "market_area": (500, 200, 750, 275),
    },
    "pet_token": {
        "pet_token_area": (875, 0, 950, 30),
    },
}

# Navigation sequences for each phase: list of (action, *args, wait_seconds)
# Actions: "tap" (x, y), "swipe" (x1, y1, x2, y2, duration), "back"
NAVIGATION = {
    "profile": [
        ("tap", 18, 10, 5.0),
        ("tap", 550, 200, 0.5),
        ("tap", 550, 200, 3.0),
    ],
    "resources": [
        ("tap", 925, 500, 5.0),
        ("tap", 780, 500, 5.0),
        ("tap", 75, 180, 5.0),
        ("tap", 620, 100, 5.0),
    ],
    "hall": [
        ("tap", 50, 500, 5.0),
        ("tap", 456, 111, 5.0),
        ("tap", 380, 116, 5.0),
    ],
    "market": [
        ("tap", 639, 232, 5.0),
        ("tap", 545, 267, 5.0),
    ],
    "pet_token": [
        ("tap", 750, 80, 5.0),
        ("swipe", 100, 450, 100, 100, 500, 1.0),
        ("swipe", 100, 450, 100, 100, 500, 1.0),
        ("swipe", 100, 450, 100, 100, 500, 1.0),
        ("tap", 100, 375, 5.0),
    ],
}

# How to exit each phase: number of BACK presses
EXIT_BACKS = {
    "profile": 2,
    "resources": 2,
    "hall": 1,
    "market": 1,
    "pet_token": 1,
}


def _adb(serial: str, args: list):
    """Run an ADB command silently."""
    try:
        subprocess.run(
            [config.adb_path, "-s", serial] + args,
            capture_output=True, timeout=10,
        )
    except Exception as e:
        print(f"[Capture] ADB error on {serial}: {e}")


def _tap(serial: str, x: int, y: int):
    _adb(serial, ["shell", "input", "tap", str(x), str(y)])


def _swipe(serial: str, x1, y1, x2, y2, duration=300):
    _adb(serial, ["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration)])


def _back(serial: str):
    _adb(serial, ["shell", "input", "keyevent", "4"])


def _navigate(serial: str, phase: str):
    """Execute the navigation sequence for a scan phase."""
    steps = NAVIGATION.get(phase, [])
    for step in steps:
        action = step[0]
        if action == "tap":
            _tap(serial, step[1], step[2])
            time.sleep(step[3])
        elif action == "swipe":
            _swipe(serial, step[1], step[2], step[3], step[4], step[5])
            time.sleep(step[6] if len(step) > 6 else 1.0)


def _exit_phase(serial: str, phase: str):
    """Press BACK to exit current phase."""
    backs = EXIT_BACKS.get(phase, 1)
    for _ in range(backs):
        _back(serial)
        time.sleep(1.5)


def capture_screenshot(serial: str, save_path: str) -> bool:
    """Take a screenshot and pull it to local filesystem."""
    try:
        _adb(serial, ["shell", "screencap", "-p", "/sdcard/screen.png"])
        subprocess.run(
            [config.adb_path, "-s", serial, "pull", "/sdcard/screen.png", save_path],
            capture_output=True, timeout=10,
        )
        return os.path.exists(save_path)
    except Exception as e:
        print(f"[Capture] Screenshot failed: {e}")
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


def combine_to_pdf(image_paths: list[str], output_path: str) -> bool:
    """Combine multiple images into a single-page PDF with OCR enhancements."""
    from PIL import ImageOps
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


def run_full_capture(serial: str, work_dir: str,
                      progress_callback=None) -> str | None:
    """Run all 5 capture phases and combine into PDF.

    Args:
        serial: ADB device serial (e.g., "emulator-5556")
        work_dir: Directory to save screenshots and PDF
        progress_callback: optional fn(phase, step, total_steps)

    Returns: path to combined PDF, or None on failure
    """
    safe_serial = serial.replace(":", "_").replace(".", "_")
    device_dir = os.path.join(work_dir, safe_serial)
    os.makedirs(device_dir, exist_ok=True)

    phases = ["profile", "resources", "hall", "market", "pet_token"]
    all_crops = []

    for idx, phase in enumerate(phases):
        step = idx + 1
        total = len(phases)

        if progress_callback:
            progress_callback(phase, step, total)

        print(f"[Capture] Phase {step}/{total}: {phase} on {serial}")

        # Navigate
        _navigate(serial, phase)

        # Screenshot
        screenshot_path = os.path.join(device_dir, f"{phase}_full.png")
        if not capture_screenshot(serial, screenshot_path):
            print(f"[Capture] Failed to capture {phase}")
            _exit_phase(serial, phase)
            continue

        # Crop
        crops = crop_regions(screenshot_path, phase, device_dir)
        all_crops.extend(crops)

        # Exit
        _exit_phase(serial, phase)
        time.sleep(2.0)

    if not all_crops:
        print(f"[Capture] No images captured for {serial}")
        return None

    # Combine to PDF
    # Order: resources, profile, hall, market, pet_token
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
