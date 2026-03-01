# 🚀 Release Notes - Version 1.0.6
*Account-GameID Architecture & WORKFLOW Module Integration*

Bản cập nhật kiến trúc lớn (Architecture Update) tái thiết toàn bộ hệ thống quản lý Account. Chuyển từ mô hình **1 Emulator = 1 Account** sang kiến trúc **Game ID là danh tính duy nhất**, cho phép nhiều Account trên cùng một Emulator và tích hợp module tự động nhận dạng ID trực tiếp từ game.

---

## ✨ Features & Enhancements

### 1. 🆔 Account-GameID Architecture
Tái cấu trúc toàn bộ hệ thống Account lấy Game ID làm trung tâm thay vì Emulator Index.
- **Game ID là Primary Key:** Mỗi Account được định danh bằng ID in-game duy nhất — không còn phụ thuộc vào Emulator.
- **Multi-Account per Emulator:** Một Emulator giờ có thể chứa nhiều Account game khác nhau. Emulator chỉ là công cụ, Account mới là mục tiêu quản lý.
- **Active Status Tracking:** Hệ thống theo dõi trạng thái Active/Idle cho từng Account trên từng Emulator.
- **Schema Migration tự động:** Database cũ được migrate an toàn — Account cũ nhận placeholder `LEGACY-{id}` cho đến khi được gán Game ID thật.

### 2. 📋 Pending Account Queue
Cơ chế xác nhận Account mới phát hiện qua Full Scan.
- **Hàng chờ xác nhận:** Khi Scan phát hiện Game ID chưa tồn tại trong hệ thống → tự động đưa vào **Pending Queue** thay vì tạo thẳng.
- **User Confirmation:** Người dùng xem xét, bổ sung thông tin (Login Method, Email, Alliance...) rồi Confirm hoặc Dismiss.
- **API Endpoints mới:** `GET /api/pending-accounts`, `POST .../confirm`, `POST .../dismiss`.

### 3. 🔧 WORKFLOW Module Integration
Di chuyển toàn bộ hệ thống tự động hoá game từ `TEST/WORKFLOW` vào App Core.
- **Package `backend/core/workflow/`:** Gồm 4 module + 10 template images:
  - `adb_helper.py` — ADB command wrapper
  - `clipper_helper.py` — Clipboard access qua ADB Clipper broadcast
  - `core_actions.py` — `extract_player_id()`, `go_to_profile()`, `wait_for_state()`, `back_to_lobby()`
  - `state_detector.py` — OpenCV template matching nhận diện trạng thái game
- **Logic giữ nguyên 100%** so với bản gốc — chỉ adapt import path cho app context.

### 4. 🎯 Full Scan — Game ID Capture
Tích hợp bước trích xuất Game ID vào pipeline Full Scan.
- **Step 0 (Mới):** Trước khi chụp screenshot, hệ thống tự động:
  1. Chờ game vào Lobby (State Detection)
  2. Navigate tới Profile Menu
  3. Tap nút Copy ID → Đọc clipboard qua ADB Clipper (100% chính xác, không OCR)
  4. Quay về Lobby để tiếp tục scan bình thường
- **Auto-Link:** Sau khi save scan data, gọi `auto_link_account()` để liên kết hoặc tạo pending.

### 5. 🖥️ Account Page UI Updates
Cập nhật giao diện trang Account đồng bộ với kiến trúc mới.
- **Cột Game ID:** Hiển thị ID in-game, Legacy account đánh dấu ⚠️.
- **Cột Status:** Badge trạng thái 🟢 Active / ⚪ Idle / 🔴 None thay cho cột Target cũ.
- **Form Add/Edit:** Game ID là trường bắt buộc (monospace), Emulator Index là tùy chọn.
- **Slide Panel:** Header hiển thị Game ID, nút Delete/Edit dùng `game_id`.
- **Provider Column:** Thay cột "Accs" cũ bằng cột Provider (Global/Sub-account).

---

## 🔌 API Changes

| Endpoint | Method | Thay đổi |
|----------|--------|----------|
| `/api/accounts` | POST | Yêu cầu `game_id` (bắt buộc), `emu_index` tùy chọn |
| `/api/accounts/{game_id}` | GET/PUT/DELETE | Dùng `game_id` thay cho `emu_index` |
| `/api/pending-accounts` | GET | **Mới** — Lấy danh sách pending |
| `/api/pending-accounts/{id}/confirm` | POST | **Mới** — Xác nhận account |
| `/api/pending-accounts/{id}/dismiss` | POST | **Mới** — Bỏ qua account |

---

## 🗂️ Files Changed

| File | Hành động |
|------|-----------|
| `backend/storage/database.py` | Schema + Migration + CRUD rewrite |
| `backend/core/full_scan.py` | Step 0 Game ID capture |
| `backend/api.py` | Endpoints updated + 3 mới |
| `frontend/js/pages/accounts.js` | UI overhaul |
| `backend/core/workflow/__init__.py` | **Mới** — Package init |
| `backend/core/workflow/adb_helper.py` | **Mới** — ADB wrapper |
| `backend/core/workflow/clipper_helper.py` | **Mới** — Clipboard helper |
| `backend/core/workflow/core_actions.py` | **Mới** — Game automation |
| `backend/core/workflow/state_detector.py` | **Mới** — State detection |
| `backend/core/workflow/templates/` | **Mới** — 10 template images |

---

> ⚠️ **Migration Note:** Khi khởi động lần đầu sau update, hệ thống sẽ tự động migrate database. Account cũ sẽ nhận Game ID dạng `LEGACY-{id}` — cần chạy Full Scan hoặc cập nhật thủ công để gán Game ID thật.
