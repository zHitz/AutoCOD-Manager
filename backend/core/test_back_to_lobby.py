import os
import sys

# Khai báo đường dẫn để kéo các thư viện từ ngoài vào
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(root_dir)

# Đảm bảo UI_MANAGER cũng nằm trong sys.path nếu cần thiết cho config
ui_manager_dir = os.path.abspath(os.path.join(root_dir, "..", "UI_MANAGER"))
if ui_manager_dir not in sys.path:
    sys.path.append(ui_manager_dir)

from backend.config import config
config.load()

from backend.core.workflow.state_detector import GameStateDetector
from backend.core.workflow import core_actions

def test_back_to_lobby(emulator_index=1):
    serial = f"emulator-{5554 + emulator_index * 2}"
    print(f"\n[TEST] Bắt đầu test back_to_lobby trên {serial}...")

    # Khởi tạo Detector
    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "workflow", "templates")
    
    print(f"[TEST] Đang nạp Mắt Thần (Detector) từ {templates_dir}...")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

    # Chạy back_to_lobby với timeout rộng rãi để test vòng lặp
    print(f"\n[TEST] 🚀 Bắt đầu gọi core_actions.back_to_lobby()...")
    print("-" * 50)
    
    result = core_actions.back_to_lobby(serial, detector, timeout_sec=60, debug=True)
    
    print("-" * 50)
    if result:
        print(f"[TEST] ✅ KẾT QUẢ: THÀNH CÔNG (Đã về tới Lobby)")
    else:
        print(f"[TEST] ❌ KẾT QUẢ: THẤT BẠI (Không thể về Lobby sau 60s)")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test back_to_lobby function")
    parser.add_argument("emulator_index", type=int, nargs="?", default=1, help="Index of emulator (default: 1)")
    args = parser.parse_args()

    # Xử lý encoding cho Windows CMD/PowerShell để in đc Tiếng Việt
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    test_back_to_lobby(args.emulator_index)
