# HƯỚNG DẪN XÂY DỰNG KỊCH BẢN (WORKFLOW GUIDE)
_Dành cho hệ thống Auto Control Emulator (Call of Dragons)_

Tài liệu này hướng dẫn bạn cách sử dụng các tệp tin trong thư mục `PRODUCTION` để tự lắp ráp bất kỳ Kịch Bản Auto (Macro Workflow) nào bạn muốn, mà không cần phải viết lại code phức tạp từ đầu.

---

## 1. TỔNG QUAN KIẾN TRÚC (ARCHITECTURE)

Thư mục `PRODUCTION` được thiết kế theo dạng **Lego Blocks (Khối Lắp Ráp)**. Có 3 lõi chính:

1. **`state_detector.py` (Đôi Mắt):** Nhiệm vụ duy nhất của nó là nhìn vào màn hình và trả về tên Trạng thái hiện tại (Ví dụ: `"LOADING SCREEN"`, `"IN-GAME LOBBY (IN_CITY)"`, `"UNKNOWN / TRANSITION"`).
2. **`clipper_helper.py` (Bàn Tay / Cảm Giác):** Hỗ trợ tương tác ngầm qua Android (Kiểm tra app đang chạy không, Mở App, Đọc dữ liệu Clipboard chính xác 100%).
3. **`core_actions.py` (Bộ Não Cấp Thấp):** Gói những thao tác tẻ nhạt thành 1 dòng code dễ hiểu. (Ví dụ: Code `go_to_profile` sẽ tự bấm tọa độ 25,25 và tự kiên nhẫn chờ đến khi cửa sổ Profile mở ra).

Nhờ 3 lõi này, bạn chỉ việc tạo ra các tệp `macro_xyz.py` (Bộ Não Cấp Cao) và gọi hàm từ `core_actions.py` theo thứ tự chiến thuật bạn muốn (Ví dụ: Vào Game -> Nhận Quà -> Vào Profile -> Copy ID).

---

## 2. CÁC HÀM CƠ BẢN BẠN CÓ THỂ SỬ DỤNG

Bạn cần quan tâm nhất đến file `core_actions.py` vì nó cung cấp cho bạn các nút bấm sau:

### ✅ `ensure_app_running(serial, package_name)`
- **Dùng làm gì:** Dùng ở đầu mỗi Script. Nó sẽ check xem game đang mở chưa, nếu chưa thì nó tự bật game lên. Nó không mở lại nếu game đã đang chạy.

### ✅ `wait_for_state(serial, detector, target_states, timeout_sec)`
- **Dùng làm gì:** Đây là hàm quyền lực nhất! Nó bắt chương trình DỪNG LẠI và CHỜ ĐỢI cho đến khi màn hình Game rơi vào đúng cái Trạng Thái mà bạn mong muốn.
- **Ví dụ:** Vừa mở game xong, gọi hàm này để chờ tới state `["IN-GAME LOBBY (IN_CITY)", "IN-GAME LOBBY (OUT_CITY)"]`. Game load bao lâu thì vòng lặp nó chờ bấy lâu (tối đa bằng `timeout_sec`), load xong nó mới chạy lệnh tiếp theo.

### ✅ `go_to_profile(serial, detector)`
- **Dùng làm gì:** Yêu cầu bạn đang đứng ở sảnh LOBBY. Nó tự bấm nút Avatar (25,25) và tự gọi `wait_for_state` để chờ đến khi xác nhận là Bảng Profile đã hiện lên đàng hoàng rồi báo cáo `True/False`.

### ✅ `extract_player_id(serial, detector)`
- **Dùng làm gì:** Bấm nút Copy ở toạ độ (425, 200) và lấy Data từ Clipboard nội bộ. Có thuật toán tự động bấm lại nếu thao tác bị lag hụt (Thử 3 lần).

---

## 3. HƯỚNG DẪN VIẾT 1 KỊCH BẢN MỚI (STEP-BY-STEP)

Hãy xem ví dụ mẫu `example_workflow.py`. Dưới đây là cách bạn tư duy để viết một kịch bản mới tên là `custom_macro.py`.

### Bước 1: Khai báo Template (Chuẩn Bị)
Luôn bắt đầu mọi Script bằng mấy dòng import này để hệ thống nạp Config và load Cấu trúc Mắt thần (Image Templates):

```python
import os
import sys

# Khai báo đường dẫn để kéo các thư viện từ ngoài vào
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)
sys.path.append(os.path.abspath(os.path.join(root_dir, "..", "UI_MANAGER")))

from backend.config import config
config.load()
import adb_helper
from PRODUCTION.state_detector import GameStateDetector
from PRODUCTION import core_actions

SERIAL = "emulator-5560" # ID giả lập muốn chạy
```

### Bước 2: Bật Mắt Thần
Trong hàm main, khởi tạo Detector để nó tải hết hình nền vào RAM.
```python
def main():
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)
```

### Bước 3: Lắp ráp Điều Kiện Logic (Logic Flow)
Bạn lên kịch bản như chơi xếp hình: "Mình muốn vào Game, Đợi nhảy vào City, rồi bấm vào sự kiện". Ném nó thành code:

```python
    # 1. Bật app
    core_actions.ensure_app_running(SERIAL, "com.farlightgames.samo.gp.vn")
    
    # 2. Đợi vào trong City
    state = core_actions.wait_for_state(SERIAL, detector, ["IN-GAME LOBBY (IN_CITY)"], timeout_sec=60)
    
    if state == "IN-GAME LOBBY (IN_CITY)":
        print("Đã vào được thành công!")
        
        # 3. Code hành động tiếp theo
        # Ví dụ nhấp vào Icon Events (Giả sử toạ độ nút Events là 900, 50)
        adb_helper.tap(SERIAL, 900, 50)
        
        # 4. Và lại chờ đợi để xác nhận là nó thật sự vào được Menu Events
        event_state = core_actions.wait_for_state(SERIAL, detector, ["IN-GAME LOBBY (EVENTS MENU)"], timeout_sec=10)
        if event_state:
            print("Đang ở trong Event! Bắt đầu cày sự kiện thôi!")
            # Code bấm cày sự kiện...
    else:
        print("Vào game thất bại, kẹt ở Loading Screen quá lâu.")
```

---

## 4. CÁCH MỞ RỘNG THÊM TRẠNG THÁI (ADD NEW STATES)

Nếu trong game có một cái Bảng (Screen) mới bạn muốn nó tự nhận diện được (Ví dụ: *Bảng Liên Minh - ALLIANCE MENU*):
1. **Chụp ảnh:** Lấy Tool Xén của bạn (`tool_region_selector.py` ở ngoài) tự cắt một cái viền nhỏ chứa chữ "Alliance" hoặc vương miện nổi bật.
2. **Lưu:** File cắt bỏ vào `PRODUCTION/templates/lobby_alliance.png`.
3. **Khai báo Code:** Mở file `PRODUCTION/state_detector.py` lên, thêm vào biến `self.state_configs`:
```python
self.state_configs = {
    "lobby_loading.png": "LOADING SCREEN",
    "lobby_alliance.png": "ALLIANCE MENU", # <--- THÊM DÒNG NÀY ĐỂ MẮT THẦN HỌC
    # ... các state cũ ...
}
```
4. **Sử Dụng:** Giờ trong Workflow của bạn, bạn hoàn toàn có thể tự tin gọi hàm: `core_actions.wait_for_state(SERIAL, detector, ["ALLIANCE MENU"])` một cách ngon lành!
