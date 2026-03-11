"""
UNKNOWN State Collector — Tự động lưu screenshot khi gặp UNKNOWN / TRANSITION.
Chạy script này, để game ở bất kỳ màn hình nào, nó sẽ liên tục check state
và lưu lại những screenshot bị phân loại là UNKNOWN vào thư mục output.

Dùng xong, mở thư mục output, review từng ảnh, crop phần đặc trưng,
rồi đăng ký vào state_detector.py.

Usage:
    python backend/core/collect_unknown_states.py [emulator_index] [duration_sec]
    python backend/core/collect_unknown_states.py 1 60
"""

import os
import sys
import time
import cv2

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(root_dir)

from backend.config import config
config.load()

from backend.core.workflow.state_detector import GameStateDetector
import numpy as np


def collect_unknowns(emulator_index=1, duration_sec=60):
    serial = f"emulator-{5554 + emulator_index * 2}"

    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")
    output_dir = os.path.join(current_dir, "workflow", "templates", "_unknown_captures")
    os.makedirs(output_dir, exist_ok=True)

    print(f"[Collector] Loading detector...")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    print(f"[Collector] Target: {serial}")
    print(f"[Collector] Duration: {duration_sec}s")
    print(f"[Collector] Output: {output_dir}")
    print(f"[Collector] Starting in 3s... Navigate game to different screens now!")
    print("-" * 60)
    time.sleep(3)

    start = time.time()
    saved_count = 0
    check_count = 0
    state_counts = {}

    while time.time() - start < duration_sec:
        check_count += 1
        result = detector.check_state_full(serial)
        state = result["state"]
        construction = result["construction"]
        special = result["special"]
        screen = result["screen"]

        # Track state counts
        label = state
        if construction:
            label += f" (con:{construction})"
        if special:
            label += f" (spc:{special})"
        state_counts[label] = state_counts.get(label, 0) + 1

        elapsed = time.time() - start

        if state == "UNKNOWN / TRANSITION" and not construction and not special:
            # Skip black screens
            if screen is not None and np.mean(screen) < 15:
                print(f"  [{elapsed:.1f}s] BLACK SCREEN (skipped)")
                time.sleep(2)
                continue

            # Save the unknown screenshot
            if screen is not None:
                saved_count += 1
                timestamp = time.strftime("%H%M%S")
                filename = f"unknown_{timestamp}_{saved_count:03d}.png"
                filepath = os.path.join(output_dir, filename)
                cv2.imwrite(filepath, screen)
                print(f"  [{elapsed:.1f}s] UNKNOWN -> SAVED: {filename}")
            else:
                print(f"  [{elapsed:.1f}s] UNKNOWN (no screen captured)")
        else:
            print(f"  [{elapsed:.1f}s] {label}")

        time.sleep(2)

    # Summary
    print("\n" + "=" * 60)
    print(f"[Collector] DONE! {check_count} checks in {duration_sec}s")
    print(f"[Collector] Saved {saved_count} UNKNOWN screenshots to:")
    print(f"  {output_dir}")
    print(f"\n[Collector] State frequency:")
    for s, count in sorted(state_counts.items(), key=lambda x: -x[1]):
        pct = count / check_count * 100
        bar = "#" * int(pct / 2)
        print(f"  {count:3d}x ({pct:4.1f}%) {s} {bar}")

    if saved_count > 0:
        print(f"\n[Collector] Next steps:")
        print(f"  1. Open folder: {output_dir}")
        print(f"  2. Review each screenshot — group similar ones")
        print(f"  3. Crop the distinctive part (icon, button, text)")
        print(f"  4. Save cropped template to templates/ or templates/contructions/")
        print(f"  5. Register in state_detector.py > state_configs or construction_configs")
    else:
        print(f"\n[Collector] No UNKNOWN states found! Detection coverage is good.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Collect UNKNOWN state screenshots")
    parser.add_argument("emulator_index", type=int, nargs="?", default=1, help="Emulator index (default: 1)")
    parser.add_argument("duration_sec", type=int, nargs="?", default=60, help="Collection duration in seconds (default: 60)")
    args = parser.parse_args()

    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    collect_unknowns(args.emulator_index, args.duration_sec)
