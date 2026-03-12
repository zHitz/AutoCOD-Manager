# 🚀 Release Notes - Version 1.1.6
*Install Apps System, Full Scan Fix, OCR Validation, Daily Delta Tracking & Workflow V3 Theme Sync*

Bản cập nhật tập trung vào **bảo vệ dữ liệu scan** (OCR Validation Gate, Smart Merge), **theo dõi biến động tài nguyên** (Scan Comparison với delta ▲/▼ hằng ngày), **hệ thống cài app** (APK Manager) và đồng bộ theme Workflow.

---

## ✨ Features & Enhancements

### 1. 📦 Install Apps System
Hệ thống quản lý APK tích hợp — download, cài đặt ứng dụng hỗ trợ trên emulator.
- **APK Registry:** 4 apps (ADB Clipper, ZArchiver, GSpace, QuickTouch) với version, size, download URL.
- **Download & Install Flow:** Kiểm tra đã tải chưa → ConfirmModal hỏi tải → download → `adb install -r` trên **đúng emulator đã chọn**.
- **Target Emulator Fix:** Backend nhận `{indices}` → chỉ cài trên emulators user đã tick, không phải all online.
- **Post-install:** Clipper tự khởi động ClipboardService sau khi cài.

### 2. 🛡️ OCR Data Validation Gate
Bảo vệ dữ liệu scan khỏi bị ghi đè bởi OCR lỗi (trả toàn 0).
- **Gate 1 — Hard Reject:** Nếu TẤT CẢ fields = 0 → abort scan, không ghi DB.
- **Gate 2 — Smart Merge:** So sánh với snapshot trước. Nếu field cũ có giá trị (VD: Hall=25) mà OCR mới trả 0 → giữ giá trị cũ.
- Áp dụng cho: `hall_level`, `market_level`, `power`, `gold`, `wood`, `ore`, `mana`.

### 3. 📊 Scan Comparison — Daily Delta Tracking
Theo dõi biến động tài nguyên theo ngày, so sánh scan hiện tại vs scan ≥24h trước.
- **Backend:** `get_scan_comparison(game_id)` query latest vs 24h-ago scan, tính delta tất cả fields.
- **API:** `GET /api/accounts/{game_id}/comparison` → `{current, previous, delta}`.
- **Frontend Resources tab:**
  - Mỗi resource card hiện delta thực: `▲ +12.5M` (xanh) hoặc `▼ -3.2K` (đỏ).
  - Header: `vs 03/02/2026` (ngày scan trước).
  - AI Daily Summary: dựa trên data thực (power change, resource trends).
  - Chưa đủ data → placeholder "—" + hướng dẫn scan thêm.

### 4. 🔧 Full Scan Fix
- **Bug:** `run_all_tasks(full_scan)` submit vào generic queue thay vì routing qua `full_scan.start_full_scan()`.
- **Fix:** Thêm `FULL_SCAN` routing vào `run_all_tasks()`.

### 5. 🎨 Workflow V3 — Theme Sync
- **Full CSS Rewrite:** 20+ hardcoded dark colors → design-system variables.
- **Button Standardization:** `btn btn-primary/outline/ghost btn-sm` giống pattern app.
- **Thêm nút Refresh** trên List View.

### 6. 🐛 Settings Hotfix
- **Root Cause:** `const ocrKeys` khai báo 2 lần → `SyntaxError` → app UI freeze hoàn toàn.
- **4 lỗi đã fix:** Duplicate const, duplicate HTML, duplicate API call, duplicate init().

---

## 🔌 API Changes

| Endpoint | Method | Thay đổi |
|----------|--------|----------|
| `/api/apks` | GET | **Mới** — List APK registry + download status |
| `/api/apks/{id}/download` | POST | **Mới** — Download APK |
| `/api/apks/{id}/install` | POST | **Mới** — Install single emulator |
| `/api/apks/{id}/install-all` | POST | **Mới** — Install on selected emulators |
| `/api/accounts/{game_id}/comparison` | GET | **Mới** — Scan delta comparison |
| `/api/tasks/run-all` | POST | **Fix** — Full Scan routing |

---

## 🗂️ Files Changed

| File | Hành động |
|------|-----------|
| `backend/core/apk_manager.py` | **Mới** — APK download & install manager |
| `backend/core/full_scan.py` | OCR Validation Gate (2-gate system) |
| `backend/storage/database.py` | `get_scan_comparison()` method |
| `backend/api.py` | 5 endpoints mới + Full Scan fix |
| `frontend/js/pages/task-runner.js` | Install Apps UI (cards, download, install) |
| `frontend/js/pages/accounts.js` | Resources tab delta display + Daily Summary |
| `frontend/js/pages/settings.js` | Hotfix duplicate const/HTML |
| `frontend/css/workflow.css` | Theme sync rewrite |
| `update.md` | v1.0.9 changelog |
