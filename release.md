# 🚀 Release Notes - Version 1.0.8
*Workflow V3 Recipe Builder, App Loading Screen, Custom Modals, Workflow Migration R2 & System Controls*

Bản cập nhật lớn tập trung vào **trải nghiệm người dùng** (Loading Screen, Custom Modals), **mở rộng hệ thống workflow** (6 navigation functions mới, construction system, screen capture pipeline) và **Workflow V3 Recipe Builder** cho phép người dùng tự xây dựng workflow từ các function có sẵn.

---

## ✨ Features & Enhancements

### 1. 🧩 Workflow V3: Recipe Builder
Hệ thống visual workflow builder — cho phép lắp ghép các core function thành workflow hoàn chỉnh.
- **Function Registry:** 16 core functions phân 6 categories (Core Actions, ADB, App Control, Scan, Flow Control, Advanced).
- **4 Pre-built Templates:** Farm Loop, ID Extraction, Full Scan Cycle, Swap & Repeat — click để dùng ngay.
- **Two-Layer UI:** Recipe gallery (grid view) → Recipe editor (function sidebar + step builder + execution panel).
- **API:** `GET/POST /api/workflow/recipes`, `GET /api/workflow/functions`, `GET /api/workflow/templates`.

### 2. 🎨 Custom Confirm Modal
Thay thế hoàn toàn native `confirm()` bằng modal đồng bộ design system.
- **Promise-based API:** `const ok = await ConfirmModal.show({title, message, icon, variant})`.
- **5 Icon variants:** restart, shutdown, warning, danger, info (SVG inline).
- **2 Style variants:** `default` (nút xanh) và `danger` (nút đỏ destructive).
- **Full UX:** Backdrop blur, scale animation, keyboard (Escape/Enter), backdrop click dismiss.
- **Áp dụng:** Restart Server (icon restart, default) và Exit App (icon shutdown, danger).

### 3. 🔄 App Loading Screen
Giải quyết triệt để lỗi "Can't reach 127.0.0.1" khi mở app.
- **Loading Screen:** pywebview load `loading.html` ngay lập tức thay vì chờ server → hiển thị logo + spinner dark theme.
- **Auto-poll:** Poll `GET /api/config` mỗi 500ms → khi server ready → spinner xanh "Connected" → tự redirect.
- **Timeout Warning:** Sau 5s hiển thị thông báo server đang khởi động lâu hơn bình thường.
- **main.py:** Xóa bỏ `time.sleep(1.5)` hardcoded, inject port vào HTML qua `html=` parameter.

### 4. 🏗️ Workflow Migration Round 2
Đồng bộ toàn bộ cập nhật mới từ `TEST/workflow` vào production `backend/core/workflow/`.
- **Construction System:** `state_detector.py` thêm `construction_templates`, `check_construction()`, `is_menu_expanded()`.
- **6 Functions mới trong `core_actions.py`:**
  - `ensure_lobby_menu_open()` — kiểm tra/mở lobby expandable menu
  - `go_to_resources()` — navigate Items → Resources tab (retry logic)
  - `go_to_construction(name)` — generic construction nav via data lookup
  - `go_to_hall()`, `go_to_market()`, `go_to_pet_token()` — shortcuts
- **`back_to_lobby()` upgraded:** Thêm `target_lobby` param cho lobby swap (IN_CITY ↔ OUT_CITY).
- **`clipper_helper.py` Multi-Fallback:** Native `cmd clipboard get` (Android 9+) + Clipper service wake-up.
- **New Files:** `construction_data.py` (tap coordinates), `screen_capture.py` (5-phase capture pipeline → PDF).
- **Template Images:** `items_artifacts.png`, `items_resources.png`, `contructions/` folder (3 ảnh).

### 5. ⚙️ System Controls
Endpoints quản lý server từ UI.
- **`POST /api/restart`:** Spawn process mới với `timeout /t 2` chờ port release (fix lỗi `EADDRINUSE`).
- **`POST /api/shutdown`:** Tắt server hoàn toàn, đóng pywebview.
- **CORS Middleware:** `allow_origins=["*"]` cho loading screen (origin null) gọi được API.

### 6. 🔧 OCR Parser Fix
- **Lord Name Multi-line:** Fix lỗi tên Lord dùng special characters bị OCR thành 2 dòng. Parser giờ collect tất cả dòng giữa "Lord" và "Power"/"Merits", ghép bằng dấu cách.

---

## 🔌 API Changes

| Endpoint | Method | Thay đổi |
|----------|--------|----------|
| `/api/restart` | POST | **Mới** — Restart backend server |
| `/api/shutdown` | POST | **Mới** — Shutdown server |
| `/api/workflow/functions` | GET | **Mới** — Function registry |
| `/api/workflow/templates` | GET | **Mới** — Pre-built templates |
| `/api/workflow/recipes` | GET/POST | **Mới** — CRUD recipes |
| `/api/workflow/recipes/{id}` | DELETE | **Mới** — Delete recipe |

---

## 🗂️ Files Changed

| File | Hành động |
|------|-----------|
| `frontend/js/components/confirm-modal.js` | **Mới** — Custom confirm modal |
| `frontend/css/components.css` | Thêm confirm modal CSS |
| `frontend/loading.html` | **Mới** — App loading screen |
| `frontend/js/app.js` | restartServer/exitApp dùng ConfirmModal |
| `frontend/index.html` | Thêm confirm-modal.js script |
| `main.py` | Loading screen integration |
| `backend/api.py` | restart/shutdown endpoints + CORS |
| `backend/core/ocr_client.py` | Lord name multi-line fix |
| `backend/core/workflow/state_detector.py` | Construction system + menu expansion |
| `backend/core/workflow/core_actions.py` | 6 new functions + target_lobby |
| `backend/core/workflow/clipper_helper.py` | Multi-fallback clipboard |
| `backend/core/workflow/construction_data.py` | **Mới** — Construction tap data |
| `backend/core/workflow/screen_capture.py` | **Mới** — 5-phase capture pipeline |
| `backend/core/workflow/__init__.py` | Thêm exports |
| `backend/core/workflow/templates/` | 3 ảnh mới + contructions/ folder |
| `frontend/js/pages/workflow.js` | Recipe Builder UI |
| `frontend/css/workflow.css` | Theme sync rewrite |
| `backend/core/workflow/workflow_registry.py` | **Mới** — Function registry |
