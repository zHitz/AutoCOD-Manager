# COD Game Automation Manager - Update Log

## Version 1.1.0 (Current)
*Workflow Bot Run Execution, Emulator Index Architecture Fix & UI/UX Real-time Logging*

- **Workflow Bot Run Engine (`backend/api.py`, `backend/core/workflow/executor.py`)**
  - **Live Execution Endpoint:** Thêm `POST /api/bot/run` để nhận danh sách hoạt động (activities) và group_id. Tự động parse danh sách action thành chuỗi `steps` cho Executor chạy thực tế thay vì mock data.
  - **Activity-to-Step Mapping:** Xây dựng dictionary `_ACTIVITY_TO_STEPS` để map tên hoạt động trên UI (Capture Pet, Market, Resources...) thành dãy lệnh function_id tương ứng (`nav_to_capture_pet`, `nav_to_market`...).
  - **Streaming Logs (`ws_client`):** Tích hợp WebSocket trực tiếp vào process `execute_recipe()`. Toàn bộ log console in ra từ giả lập giờ sẽ được stream ngược thẳng về trình duyệt.

- **Frontend Bot Run & Real-time Console (`frontend/js/pages/workflow.js`)**
  - **Start Bot Action:** Bổ sung nút "▶ Start Bot" góc phải Tab Activity Log. Khi nhấn, tự động trích xuất các hoạt động đang Enable của Group, gửi request REST API và tự động chuyển view sang tab Log.
  - **Activity Console System:** Triển khai khung Terminal dạng `div` với hiệu ứng màu chữ log (Info=White, Success=Green, Warning=Yellow, Error=Red), hỗ trợ tự động cuộn (auto-scroll) xuống cuối khi có dòng mới.
  - **Global WebSocket Routing (`app.js`):** Bổ sung event listener cho `workflow_log` và `workflow_status` tại `setupWSEvents()`. Dữ liệu realtime từ WebSocket được chặn và truyền thẳng vào `WF3.addBotLog()` khi user đang dừng ở trang Workflow.

- **Emulator Resolution Architecture Fix (Critical)**
  - **The Bug ("No emulators found for this group"):** Quá trình Start Bot liên tục bị từ chối do Backend không thể tra cứu được ID giả lập dựa vào danh sách `account_ids`, nguyên nhân bảng `accounts` lưu FK (`emulator_id`) nhưng API lại cần `emu_index`.
  - **JS Object Key Mismatch:** Trên giao diện, API trả về danh sách có khóa `account_id` nhưng code JS bộ lọc Group Account lại so sánh nhầm qua khóa `id` (undefined), dẫn đến việc lấy danh sách ID rỗng gửi cho Backend.
  - **The Fix:**
    1. Viết lại hàm `runBotActivities()` đẩy việc tính toán `emulator_indices` lên Frontend. Frontend sẽ lặp qua danh sách `accountsData`, lọc ra `account_id` và trích xuất `emu_index` chính xác, nhét trực tiếp vào mảng payload.
    2. Sửa lỗi syntax `acc.id` thành `acc.account_id` ở logic render Checkbox của bảng Edit Group.
    3. Cập nhật giao diện cột Emulator fix lỗi hiển thị cọc cạch `?`: Chuyển cách đọc từ `emulator_name`/`emulator_id` sang đúng cấu trúc API mới nhất: `${acc.emu_name || (acc.emu_index != null ? 'Emulator ' + acc.emu_index : '?')}`.

- **Core Actions Expansions (`backend/core/workflow/core_actions.py`)**
  - **Capture Pet Flow:** Implement mới logic `go_to_capture_pet()` bằng cách tận dụng hàm `back_to_lobby(target_lobby="OUT_CITY")` để game thoát ra world map, sau đó nhấn mục Pet để mở tính năng bắt thú.
  - Cập nhật Executor để ghi nhận và thông dịch được các ID action mới: `nav_to_capture_pet`, `nav_to_pet_token`, `nav_to_market`...

---

## Version 1.0.9

- **Critical Bug Fix — App UI Freeze (`frontend/js/pages/settings.js`)**
  - **Root Cause:** `const ocrKeys` bị khai báo **2 lần** trong cùng scope tại `loadOcrKeys()` → `SyntaxError` → `SettingsPage` không tồn tại → `app.js` crash khi build `router._pages` → `ReferenceError: SettingsPage is not defined`.
  - **Cascade Failure:** WebSocket `wsClient.connect()` và `router.navigate('dashboard')` không bao giờ chạy → UI đơ hoàn toàn: sidebar tĩnh, content trống, trạng thái "Disconnected".
  - **4 Lỗi Đã Fix:**
    1. `const ocrKeys` duplicate (dòng 260 & 263) → xóa bản copy thừa
    2. HTML OCR section bị copy-paste (dòng 122-134) → block trùng lặp gây duplicate DOM IDs (`cfg-ocr-keys` x2)
    3. `API.saveOcrKeys()` gọi 2 lần liên tiếp trong `saveConfig()` → xóa bản thừa
    4. `loadConfig()` + `loadOcrKeys()` gọi 2 lần trong `init()` → xóa bản thừa

- **Install Apps System (`backend/core/apk_manager.py` — MỚI)**
  - **APK Manager Module:** Registry 4 apps (ADB Clipper, ZArchiver, GSpace, QuickTouch) với download URL, version, post-install commands. APK files lưu trong `data/apks/`.
  - **Download & Install Flow:** User bấm Install → nếu chưa tải → `ConfirmModal` hỏi tải → download từ URL → cài qua `adb install -r` trên **đúng emulator đã chọn** (không phải tất cả online).
  - **Target Emulator Fix:** Backend `install-all` nhận `{indices}` từ frontend, chuyển thành ADB serial → chỉ cài trên emulator user đã tick trong Target Emulators tab.
  - **UI Rewrite (`frontend/js/pages/task-runner.js`):** Cards load động từ API, badge 🟢 DOWNLOADED / ⬜ NOT DOWNLOADED / 🟡 NO URL, spinner khi downloading/installing, kết quả ✓/✗ hiển thị inline.
  - **4 API Endpoints:**
    - `GET /api/apks` — list registry + download status
    - `POST /api/apks/{id}/download` — download APK
    - `POST /api/apks/{id}/install?serial=...` — install single
    - `POST /api/apks/{id}/install-all` — install trên selected emulators (body: `{indices}`)
  - **Post-install:** Clipper tự start `ClipboardService` sau khi cài.

- **Full Scan Fix (`backend/api.py`)**
  - **Bug:** `POST /api/tasks/run-all?task_type=full_scan` submit vào generic `task_queue` nhưng Full Scan cần routing đặc biệt qua `full_scan.start_full_scan()`. Endpoint `run_task` (single) đã xử lý đúng, `run_all_tasks` thì không → bấm Full Scan từ Scan Operations tab ghi "queued" nhưng không có gì xảy ra.
  - **Fix:** Thêm `FULL_SCAN` routing vào `run_all_tasks()` — route từng emulator online qua `full_scan.start_full_scan()`.

- **OCR Data Validation Gate (`backend/core/full_scan.py`)**
  - **Vấn đề:** Nếu screenshot capture lỗi → OCR trả toàn 0 → ghi đè data tốt (ví dụ Hall 25 → 0).
  - **Gate 1 — Hard Reject:** Nếu TẤT CẢ fields (`power`, `hall_level`, `market_level`, `resources`) đều = 0 → abort scan, không ghi DB.
  - **Gate 2 — Smart Merge:** So sánh với snapshot trước đó trong DB. Nếu field cũ có giá trị (ví dụ Hall=25) mà OCR mới trả 0 → giữ giá trị cũ, không ghi đè.
  - Áp dụng cho: `hall_level`, `market_level`, `power`, `gold`, `wood`, `ore`, `mana`.

- **Scan Comparison — Daily Delta Tracking**
  - **Backend:** Thêm `get_scan_comparison(game_id)` trong `database.py` — query latest scan vs scan ≥24h trước, tính delta cho tất cả fields.
  - **API:** `GET /api/accounts/{game_id}/comparison` trả `{current, previous, delta}`.
  - **Frontend:** Account detail → Resources tab hiện delta thực (▲/▼ + giá trị) cho Gold, Wood, Ore, Mana, Pet Token.
  - **AI Daily Summary:** Thay hardcoded "AI Insight" bằng daily summary dựa trên data thực (power change, resource trends).
  - Nếu chưa có 2 scans cách nhau 24h thì hiện placeholder "—" và hướng dẫn scan thêm.

- **Workflow V3 — UI/UX Theme Synchronization (`frontend/css/workflow.css`)**
  - **Full CSS Rewrite:** Thay thế toàn bộ **20+ hardcoded dark colors** (`#0c0e14`, `#252a3a`, `#64748b`…) bằng design-system variables (`var(--card)`, `var(--border)`, `var(--muted-foreground)`, `var(--accent)`…). Workflow giờ dùng chung Light Theme với toàn bộ app — không còn hiệu ứng "split-screen" dark/light.
  - **Button Standardization:** Chuyển từ custom `wf-tb-btn` sang app classes: `btn btn-primary btn-sm` (Create New, Run), `btn btn-outline btn-sm` (Save, Refresh), `btn btn-ghost btn-sm` (Back) — giống pattern `scheduled.js`.
  - **Thêm nút Refresh** trên List View + method `refreshList()`.

- **History Page Fixes (`backend/storage/database.py`, `backend/api.py`, `frontend/js/pages/history.js`)**
  - **Bug:** Trang History luôn báo lỗi hoặc hiện empty mock data. Nguyên nhân là frontend gọi endpoint `/api/tasks/history` không tồn tại, và Full Scan module không ghi data vào bảng `task_runs`.
  - **Fix Database:** Thêm DB method `get_task_history()` query gộp 2 bảng: `task_runs` cho các task xếp hàng, và `scan_snapshots` cho các Full Scan chạy direct. Lọc trùng data dựa vào serial+timestamp và sort theo thời gian mới nhất.
  - **Fix API:** Thêm endpoint `GET /api/tasks/history` public method cho frontend.
  - **Fix UI Detail Panel:**
    - Cập nhật mapping `history.js` để parse cấu trúc trả về mới.
    - Thêm object details: hiển thị Output JSON, Runtime Logs, Status Info và lỗi.
    - Thêm CSS classes (`.history-expand-row`, `.expand-panel`, `.expand-grid`) cho Grid layout 4 columns render thông tin expand.

---

## Version 1.0.8
*Workflow V3 Recipe Builder, App Loading Screen, Custom Modals, Workflow Migration R2 & System Controls*

- **Workflow V3: Recipe Builder (`backend/core/workflow/workflow_registry.py` — MỚI)**
  - **Backend Function Registry:** Tạo mới `workflow_registry.py` — catalog tập trung **16 core functions** phân thành 6 categories: Core Actions (Boot to Lobby, Open Profile, Extract Player ID…), ADB Actions (Tap, Swipe, Back, Screenshot), App Control (Launch, Check Running), Scan Operations (Full Scan), Flow Control (Delay) và Advanced (Wait for State).
  - **4 Pre-built Templates:** Farm Loop (5 steps), ID Extraction (4 steps), Full Scan Cycle (3 steps), Swap & Repeat (4 steps) — user click để dùng ngay.
  - **4 API Endpoints mới (`backend/api.py`):**
    - `GET /api/workflow/functions` — trả toàn bộ registry kèm icon, params, defaults
    - `GET /api/workflow/templates` — danh sách template có sẵn
    - `GET /api/workflow/recipes` & `POST` — CRUD recipe (lưu in-memory)
    - `DELETE /api/workflow/recipes/{id}` — xóa recipe

- **Two-Layer Workflow UI (`frontend/js/pages/workflow.js`)**
  - **Layer 1 — Recipe List View:** Trang gallery hiển thị Template cards (viền trái xanh, badge `TEMPLATE`) và My Recipes (grid responsive `auto-fill 300px`). Header dạng `page-header` chuẩn app với nút `Refresh` + `Create New`. Empty state với hướng dẫn rõ ràng.
  - **Layer 2 — Recipe Editor View:** Click template/recipe → chuyển sang Editor. Sidebar trái chứa function library (search filter), center là step cards sequential (numbered, config fields inline: number/text/select). Insert `[+]` button giữa mỗi step. Nút Back/Save/Run trên toolbar. Execution Panel trượt lên từ bottom với progress bar + log timeline.
  - **Function Picker Modal:** Overlay modal phân category, tìm kiếm real-time, click chọn function → tự thêm step với default config.

- **UI/UX Theme Synchronization (`frontend/css/workflow.css`)**
  - **Full CSS Rewrite:** Thay thế toàn bộ **20+ hardcoded dark colors** (`#0c0e14`, `#252a3a`, `#64748b`…) bằng design-system variables (`var(--card)`, `var(--border)`, `var(--muted-foreground)`, `var(--accent)`…). Workflow giờ dùng chung Light Theme với toàn bộ app.
  - **Button Standardization:** Chuyển từ custom `wf-tb-btn` sang app classes: `btn btn-primary btn-sm` (Create New, Run), `btn btn-outline btn-sm` (Save, Refresh), `btn btn-ghost btn-sm` (Back) — giống hệt pattern `scheduled.js`.
  - **Component Sync:** Cards dùng `var(--card)` + `var(--shadow-sm)`, config fields dùng `var(--muted)` background, modals dùng `var(--shadow-xl)`, spinners dùng `var(--indigo-500)`.

- **Custom Confirm Modal (`frontend/js/components/confirm-modal.js` — MỚI)**
  - **Thay thế native `confirm()`:** Popup xác nhận tùy chỉnh đồng bộ design system, sử dụng Promise-based API: `const ok = await ConfirmModal.show({title, message, icon, variant})`.
  - **5 Icon variants:** `restart`, `shutdown`, `warning`, `danger`, `info` — SVG inline.
  - **2 Style variants:** `default` (nút xanh) và `danger` (nút đỏ destructive).
  - **UX hoàn chỉnh:** Backdrop blur + scale animation vào/ra, keyboard support (Escape = Cancel, Enter = Confirm), click backdrop = dismiss.
  - **Áp dụng:** `restartServer()` dùng icon restart + variant default, `exitApp()` dùng icon shutdown + variant danger.

- **App Loading Screen (`frontend/loading.html` — MỚI)**
  - **Giải quyết "Can't reach 127.0.0.1":** Thay vì pywebview mở thẳng server URL (gây lỗi khi server chưa boot), giờ load loading.html trước — hiển thị logo + spinner dark theme.
  - **Auto-poll & Redirect:** Loading screen poll `GET /api/config` mỗi 500ms, khi server sẵn sàng → spinner xanh + "Connected" → tự redirect vào app.
  - **Timeout Warning:** Sau >5s hiển thị "Server is taking longer than usual..."
  - **`main.py` Updated:** Đọc loading.html → inject port → truyền qua pywebview `html=` parameter. Xóa bỏ `time.sleep(1.5)` hardcoded.

- **Workflow Migration Round 2 (`backend/core/workflow/`)**
  - **`state_detector.py` — Construction System:** Thêm `construction_templates` dict + `construction_configs` mapping (HALL, MARKET, ELIXIR_HEALING). Method mới: `is_menu_expanded()` kiểm tra lobby menu mở rộng, `check_construction()` nhận diện building trên màn hình. Thay thế `lobby_resources` state bằng `items_artifacts` / `items_resources`.
  - **`core_actions.py` — 6 Functions mới:** `ensure_lobby_menu_open()` (kiểm tra/mở menu lobby), `go_to_resources()` (navigate Items → Resources tab), `go_to_construction(name)` (generic construction nav via data lookup), `go_to_hall()`, `go_to_market()`, `go_to_pet_token()`. Update `back_to_lobby()` thêm `target_lobby` swap (IN_CITY ↔ OUT_CITY).
  - **`clipper_helper.py` — Multi-Fallback:** Fallback 1: native `cmd clipboard get` (Android 9+). Fallback 2: wake Clipper service trước khi broadcast (chống Android Memory kill).
  - **`construction_data.py` — MỚI:** Tap coordinates cho HALL, MARKET, ELIXIR_HEALING.
  - **`screen_capture.py` — MỚI:** 5-phase capture pipeline (profile → resources → hall → market → pet_token) + crop regions + combine PDF.
  - **Template Images:** Thêm `items_artifacts.png`, `items_resources.png`, folder `contructions/` (3 ảnh). Xóa `lobby_resources.png` cũ.

- **System Endpoints (`backend/api.py`)**
  - **`POST /api/restart`:** Restart backend server — spawn process mới với `timeout /t 2` chờ port release trước khi khởi lại.
  - **`POST /api/shutdown`:** Tắt server hoàn toàn.
  - **CORS Middleware:** Thêm `CORSMiddleware(allow_origins=["*"])` hỗ trợ loading screen (origin null) gọi API.

- **OCR Parser Fix (`backend/core/ocr_client.py`)**
  - **Lord Name Multi-line:** Fix lỗi tên Lord dùng special characters (chữ nhỏ) bị OCR thành 2 dòng (VD: `dragonball` + `Goten`). Parser giờ collect tất cả dòng giữa "Lord" và keyword tiếp theo ("Power"/"Merits"), ghép bằng dấu cách → `dragonball Goten`.

---

## Version 1.0.7
*Scheduled Tasks, Account UX Fixes & Workflow V2*

- **Scheduled Tasks Page (`frontend/js/pages/scheduled.js` — MỚI)**
  - Trang quản lý lịch trình chạy macro tự động hoàn chỉnh: List View (bảng 10 cột) + Detail View (form tạo/sửa).
  - Hỗ trợ 4 loại schedule: Once (datetime), Interval (30m/2h), Daily (HH:MM), Cron expression.
  - Target mode: All Online hoặc chọn Specific emulators (checkbox list).
  - Actions: Toggle Enable/Disable, Execute Now, Delete. API CRUD đầy đủ.

- **Account Page Fixes (`frontend/js/pages/accounts.js`)**
  - Fix detail panel click — bấm vào Account row giờ mở chi tiết đúng cách.
  - Pet Token format: thêm dấu phân cách nghìn (1245 → 1,245).
  - Resource hiển thị: tự động chuyển đơn vị M → B khi vượt 1000M.
  - Hall Level max 25, Market Level max 25.

- **Workflow V2 (`frontend/js/pages/workflow.js`)**
  - Trang Workflow Basic — linear builder không kéo thả, palette cố định.

---

## Version 1.0.6
*Account-GameID Architecture & WORKFLOW Module Integration*

- **Account Architecture Overhaul (`backend/storage/database.py`)**
  - **Game ID là Primary Identity:** Mỗi Account giờ dùng `game_id` (ID in-game duy nhất) làm khóa chính thay vì `emulator_id`. Cho phép **nhiều Account trên cùng một Emulator**.
  - **Schema Migration:** Tự động migrate DB cũ — Account cũ không có Game ID sẽ nhận placeholder `LEGACY-{id}`. Migration chạy tự động khi khởi động, idempotent.
  - **Bảng `pending_accounts` (Mới):** Account mới phát hiện qua Full Scan sẽ vào **hàng chờ** để User xác nhận thay vì tạo thẳng. Hỗ trợ trạng thái `pending` / `confirmed` / `dismissed`.
  - **Auto-Link Logic (`auto_link_account`):** Sau mỗi lần Scan, hệ thống tự nhận diện — nếu `game_id` đã tồn tại thì cập nhật trạng thái Active, nếu chưa thì đưa vào Pending Queue.
  - **`scan_snapshots`** giờ có cột `game_id` liên kết trực tiếp scan data với Account cụ thể.
  - Viết lại toàn bộ CRUD: `upsert_account`, `get_all_accounts` (LEFT JOIN), `update_account`, `delete_account` — tất cả dùng `game_id`.

- **WORKFLOW Module Integration (`backend/core/workflow/`)**
  - **Di chuyển TEST/WORKFLOW vào App Core:** Toàn bộ module `adb_helper`, `clipper_helper`, `core_actions`, `state_detector` + templates được tích hợp thành package `backend.core.workflow`.
  - **Logic giữ nguyên 100%:** Tất cả hàm (`extract_player_id`, `go_to_profile`, `wait_for_state`, `back_to_lobby`) hoạt động y hệt gốc — chỉ adapt import path cho app context.
  - **State Detection:** Sử dụng OpenCV template matching để nhận diện trạng thái game (Loading, Lobby, Profile Menu...) trước khi thao tác.

- **Full Scan — Game ID Capture (`backend/core/full_scan.py`)**
  - **Step 0 (Mới):** Trước khi chụp screenshot, Full Scan sẽ chạy WORKFLOW module:
    1. `wait_for_state()` — Chờ game vào Lobby
    2. `go_to_profile()` — Navigate tới Profile Menu (có state detection)
    3. `extract_player_id()` — Tap nút Copy ID + đọc clipboard qua ADB Clipper
    4. `back_to_lobby()` — Quay về Lobby để tiếp tục scan
  - Game ID được ghi vào `scan_snapshots` và gọi `auto_link_account()` sau khi save.

- **API Endpoints Rework (`backend/api.py`)**
  - `POST /api/accounts` giờ yêu cầu `game_id` (bắt buộc), `emu_index` là tùy chọn.
  - `GET/PUT/DELETE /api/accounts/{game_id}` — dùng Game ID thay cho emu_index.
  - **3 Endpoint mới:** `GET /api/pending-accounts`, `POST .../confirm`, `POST .../dismiss`.

- **Account Page UI (`frontend/js/pages/accounts.js`)**
  - **Cột Game ID:** Hiển thị ID in-game, Legacy account có icon ⚠️ cảnh báo.
  - **Cột Status:** Badge trạng thái 🟢 Active / ⚪ Idle / 🔴 None thay cho cột Target cũ.
  - **Form Add/Edit:** Game ID là trường bắt buộc (monospace font), Emulator Index chuyển thành tùy chọn.
  - **Slide Panel:** Header hiển thị `ID: 12345678`, nút Delete dùng `game_id`.
  - Cập nhật Grid View, `_saveNote()`, tất cả API call — đồng bộ hoàn toàn với backend mới.

---

## Version 1.0.4
*Emulator Workspace Organization, Menus & UX Polish*

- **Chrome-Style Tabs (`frontend/js/pages/emulators.js`)**
  - **Tab Management System:** Đã tích hợp hệ thống tab đa cửa sổ mang phong cách trình duyệt Chrome cho giao diện quản lý Emulator Instances. Người dùng có thể nhóm máy ảo (Phân lô Farming, Scanners, v.v.) vào các tab riêng biệt.
  - **Dynamic Badge Count:** Hiển thị tự động số lượng máy ảo hiển thị (count pill badge) cho từng tab, phân màu nền nổi bật cho Active Tab.
  - **Tab Editing (Inline):** Tạo tab mới qua dấu `+`. Có thể nhấp đúp (double-click) vào bất kỳ nhãn tab nào để vào chế độ đổi tên nhanh. Có nút `✕` để xóa Tab tùy chỉnh (các máy ảo bên trong tự động hoàn về Tab "All Instances").

- **Card Context Menu Redesign (`frontend/js/pages/emulators.js`)**
  - **Modern Dropdown (···):** Loại bỏ nút "Rename" cồng kềnh, chuyển mọi tương tác nâng cao vào Menu thả xuống dạng bóng đổ kích hoạt khi click nút More (···) khi Hover qua card máy.
  - **Right-Click Context Menu:** Hệ thống Menu ngữ cảnh hoàn toàn mới cho từng giả lập. Hỗ trợ truy cập nhanh thao tác: `Copy Name`, `Copy ADB Serial`, `Copy Index`, `Rename` và `Start/Stop` mà không cần di chuột qua lại.
  - **Quick Copy Actions:** Hỗ trợ Copy ADB serial hoặc Instance Name vào clipboard, tích hợp bộ thay biểu tượng tick `✓` cực kì nhanh và phản hồi Animation trượt thả trực quan.
  - **Move To Tab Workflow:** Thêm tuỳ chọn "Move to Tab" liệt kê danh sách toàn bộ tab đang mở. Click để gán máy ảo đang chọn qua Tab khác tiện lợi (sẽ tự làm mờ tên Tab hiện tại).
  - Tích hợp thêm các nút Context: **Rename**, **Start/Stop Instance** vào cùng menu.

- **Enhanced Interaction (`frontend/js/pages/emulators.js`)**
  - **Inline Rename:** Cung cấp tính năng Double-Click trực tiếp lên tên Emulator để chỉnh sửa tại chỗ (Inline Focus) thay vì mở modal. Tự động gọi API rename và cập nhật UI.
  - **Bulk Safety:** Các nút thao tác hàng loạt "Stop All" và "Stop Selected" giờ đã có hộp thoại `confirm()` chống click nhầm gây tắt máy đột ngột.
  - **ADB Copier:** Thêm link Copy icon tiện lợi bên cạnh ID mạng (VD: `emulator-5554`), nhấn để đưa thẳng serial vào Clipboard.
  - **Action-centric Control Panel:** Đã thêm thanh công cụ trên cùng chứa Search Bar, Filter Tabs (All, Running, Stopped) và các nút Bulk Actions.
  - **Batch Operations:** Nâng cấp hệ thống Multi-select thông qua Checkbox ở mỗi hàng, cho phép chọn nhiều Emulator và Start/Stop hàng loạt chỉ với 1 click.
  - **Pro UX Hover Actions:** Thay vì để sẵn nút Start/Stop chiếm diện tích và mất tập trung, Action Buttons (Start, Stop, Restart) giờ đây ẩn dưới dạng Hover Quick Actions — chỉ xuất hiện khi người dùng rê chuột vào Emulator cụ thể.
  - **Auto-Refresh Toggle:** Bổ sung tính năng bật/tắt Auto Refresh ngay trên Toolbar giúp dễ dàng theo dõi Dashboard realtime mà không bị làm phiền lúc debug.

- **Visual & Rendering Upgrades (`frontend/js/pages/emulators.js` & `components.css`)**
  - **Staggered Animations:** Giao diện load danh sách không còn chớp nháy mà trượt lên mượt mà theo từng mục (sử dụng CSS keyframe `fadeInSlideUp` kết hợp `animation-delay` động tính theo index).
  - **Auto-Refresh Ring:** Cải tiến thanh Toggle `Auto Refresh`. Thay vì chỉ gạt nút nhàm chán, hiển thị thêm một vòng tròn SVG đếm ngược 5 giây (`stroke-dashoffset`) giúp theo dõi được chính xác thời điểm gửi API quét dữ liệu. Thêm nút "Manual Refresh" và text Update Timestamp.
  - **Robustness:** Bọc `try...catch` bao toàn bộ logic map danh sách `renderList()`. Ngăn chặn hoàn toàn lỗi sập trắng UI khi render thẻ div và đổ log JSON stacktrace ra trực tiếp màn hình nếu xuất hiện cấu trúc data không hợp lệ.
  - **CSS Priority Fix:** Loại bỏ `opacity: 0` gây sập hiển thị list do class `.page-enter` xung đột với JS load động, và đệm padding chuẩn cho ô Search Box để không bị đè text lên kính lúp.
  - **Advanced Row Layout:** Cấu trúc lại dữ liệu hiển thị từng instance:
    - Hiển thị thông số runtime metrics chi tiết trên một dòng: PID, Resolution, DPI, CPU Usage, RAM Usage.
    - Status Badge với màu sắc chuẩn UI (Xanh lá cho Running, Xanh xám cho Stopped).
    - **[Hotfix]** Khắc phục lỗi raw string HTML: Loại bỏ các khoảng trắng thừa bị chèn vào thẻ DOM tag (`< div`, `< !--`) trong script JS để render UI thành DOM thật thay vì text tĩnh.
  - **UI Updates:** Bổ sung classes cho hiệu ứng hover `hover-actions-container` và `device-hover-actions` thân thiện.

---

## Version 1.0.3
*SPA State Persistence — Deep Root-Cause Fix (Production Safe)*

- **Global State Management (`frontend/js/store.js`)**
  - Cấu trúc lại **GlobalStore** sang dạng Singleton chuẩn Production: 
    - Serializable State (Array thay Set, Object thay Map). Không chứa DOM hay timer refs.
    - Tích hợp `sessionStorage` (auto save/load) để bảo vệ state ngay cả khi F5.
    - `subscribe()` trả về hàm `unsubscribe()` chống Memory Leak.
    - Thêm `currentTab` vào state → nhớ tab đang mở khi swap trang.
    - Debug: `window.__STORE_DEBUG__` để kiểm tra state real-time.

- **Root-Cause Bug Fixes (`frontend/js/pages/task-runner.js`)**
  - **Bug #1 — `addFeed()` ghi trực tiếp vào DOM:** Trước đây hàm này tạo `<div>` bằng `createElement()` rồi `prepend()` vào `#live-feed`. Khi DOM bị `innerHTML = render()` tái tạo → tất cả logs biến mất. **Fix:** `addFeed()` giờ gọi thẳng `GlobalStore.addActivityLog()`, feed được render từ Store.
  - **Bug #2 — `init()` luôn reset `_currentTab = 'emulators'`:** Mỗi lần Router gọi `init()` (khi quay lại trang Actions), tab luôn nhảy về Emulators thay vì ở Recorder. **Fix:** `init()` giờ đọc `GlobalStore.state.currentTab` để khôi phục đúng tab.
  - **Bug #3 — `switchTab()` không lưu tab:** Khi click chuyển tab, giá trị `_currentTab` chỉ lưu local. **Fix:** `switchTab()` giờ gọi `GlobalStore.setCurrentTab(tab)` để persist.
  - **Reconciliation:** Thêm `_reconcileMacroCards()` — khi quay lại trang, hệ thống tự động quét `GlobalStore.state.runningMacros` và gắn lại UI "Running..." + spinner cho đúng card, đồng thời tick bộ đếm thời gian từ `startTime` lưu trong Store.
  - **Bug #4 — `loadMacros()` luôn render card ở trạng thái idle:** Hàm `loadMacros()` trước đây hardcode mọi card với nút "Run Script" bất kể macro đang chạy hay không. **Fix:** Giờ `loadMacros()` kiểm tra `GlobalStore.state.runningMacros[filename]` khi render từng card → nếu đang chạy thì hiển thị spinner, nút disabled "Running...", và thanh progress bar ngay lập tức.

- **Full Scan OCR Pipeline Integration (Major Update)**
  - **Pipeline Orchestration (`backend/core/full_scan.py`)**: Hoàn thiện thuật toán Full Scan gom tụ 5 bước (Profile, Resources, Hall, Market, Pet Token). Chạy background thread (Async Worker) đảm bảo 100% không block main server.
  - **Thread-Safety Database Fix**: Khắc phục triệt để lỗi `RuntimeError: threads can only be started once` do xung đột `aiosqlite` event loop khi save data từ thread scan. Cấu trúc lại toàn bộ class `database.py` bỏ `await` kép.
  - **Image Processing Tweak (`backend/core/screen_capture.py`)**: Tích hợp module xử lý crop ảnh trước khi build PDF cho OCR: Convert ảnh màu sang Grayscale (`L`), ép tương phản (`ImageOps.autocontrast`) và Scaling 4x (`LANCZOS`) để Tesseract/Cloud OCR đọc mượt hơn chữ nhỏ bé xíu.
  - **API Payload Reshape (`backend/api.py`)**: Viết lại API `/api/devices` và `/devices/refresh` để chúng có thể chọc thẳng vào DB lấy data của `emulator_data` table. Gom các column phẳng: `gold, wood, ore, mana` thành nested object `resources` khớp 100% với Frontend struct.
  - **WebSocket Full Scan UI Hooks (`frontend/js/app.js` & `device-card.js`)**: Đi dây các listener event mới (`scan_progress`, `scan_completed`, `scan_failed`). Sửa thanh Task Progress nhảy tự động (20% -> 60% -> 80%...) thay vì kẹt vĩnh viễn ở chữ "Starting...". Đổ thẳng dữ liệu Name, Power, Tài nguyên, Hall vào trang Dashboard ngay khi chạy xong mà không cần tải lại trang.
  - **Hotfix Import Crashes**: Dọn dẹp module-level Constants `config.adb_path` bị gọi sai thời điểm ở các file `macro_replay.py`, `screen_capture.py`, `ldplayer_manager.py` gây lỗi 500 Network Error khi mới bật server.

---

## Version 1.0.2

- **Accounts Table Redesign (`frontend/js/pages/accounts.js`)**
  - Áp dụng các **Quick Fixes** cho bảng hiển thị:
    - **Group Headers:** Chia Header thành 4 nhóm chính (Identity & Core, Account Details, Progress & Social, Resources) để giảm tải nhận thức (cognitive load).
    - **Frozen Columns:** Cố định 3 cột đầu (STT, Emu Name, In-game Name) khi lướt theo chiều ngang.
    - **Data Highlighting:** Tô đậm và gán màu (Color Coding) cho chỉ số POW, Hall, Market và toàn bộ 4 cột Resources (thêm hậu tố 'M').
    - **Tooltip + Status Badges:** Cột Match được nâng cấp với Badge Yes/No thay cho icon text khô khan, kèm thao tác hover-tooltip để giải nghĩa.
    - **Quick Actions:** Thêm các nút thao tác nhanh (View, Sync) dưới dạng bóng (ghost buttons) chỉ xuất hiện khi di chuột (hover) qua từng hàng.

- **Account Detail Page (New Feature)**
  - Click vào bất kỳ dòng nào trên bảng để mở **Profile Page** riêng cho thông tin Account thay vì nhảy modal.
  - Sử dụng Layout hai cột màn hình chia dọc:
    - **Left Sidebar:** Chứa Avatar/tên in-game, POW và Metadata cốt lõi (Emulator, Target ID, Provider).
    - **Main Content:** Bộ Grid Card hiển thị 4 chỉ số sinh tồn rút gọn.
    - **System Tabs:** Bố trí một thẻ chức năng bên dưới, cho phép cuộn các tab Overview, Resources, và Notes mà không rối dữ liệu. Trải nghiệm mượt mà giống Dashboard chuẩn.
  - Nút Back (`←`) quay lại bảng và các Quick Button (Force Sync, Edit, Delete) ở góc phải trên cùng.

- **Advanced UI/UX Polish (Request Update)**
  - **Slide-Over Panel Detail UX:** Thay vì chuyển cảnh mất context, click `View` sẽ trượt một panel từ bên phải sang (Off-canvas) giống Jira/Linear, giữ nguyên bảng số liệu phía dưới.
  - **Visual Hierarchy & Formatting:**
    - Shrink cột STT (cố định 56px) theo đúng chuẩn. Tăng khoảng cách margin-bottom phần Group Headers.
    - Các số liệu Tài nguyên được tăng `font-weight: 600` và `letter-spacing` dễ đọc hơn, đính kèm trend marker (mũi tên `↑`/`↓`).
    - Nút Quick Action Hover hiện ra biểu tượng mũi tên rõ ràng (`View ➔`) để thu hút tương tác.
  - **Profile Overhaul:** Badge **POW** mang style gradient vàng cam đẳng cấp. Thu nhỏ Avatar xuống 56px cân đối hơn. Chia Layout Tab Overview thành Grid thẻ lưới 2 cột chống khoảng trắng cụt.
  - **Visual Bugs Fix (CSS Layout):**
    - Sửa lỗi trong suốt (Transparent background) khi mở Slide Panel Panel do biến màu `var(--surface-50)` bị đè nét, gây ra hiện tượng chữ chồng lên bảng dữ liệu (text overlapping). Thiết lập lại biến solid background thành `var(--surface-100) / #ffffff`.
    - Fix triệt để lỗi Frozen Columns đầu bảng bị xuyên thấu nội dung khi lướt ngang. Nâng Z-index layer cục bộ và bắt buộc phủ nền solid trắng để không bao giờ bị các cột sau trượt đè lên text.
  - **Account Detail Tabs Restructure:**
    - Cấu trúc lại dữ liệu Tab **Overview**: Chia thành 2 cột cân bằng (Login & Access, Emulator Info vs Game Status, Match). Thêm icon chấm phân cách và các đường gạch ngang mờ (border-bottom) giống hệt thiết kế tham chiếu.
    - Làm lại Tab **Resources**: Thay thế hiển thị Grid cục mịch cũ bằng hệ thống 3 Card Tài nguyên nằm ngang với **Progress Bar theo %** cực kỳ sắc nét (tự đánh dấu xanh lá/cam/đỏ tùy mức độ đầy), và thêm một Block ngang nổi bật màu tím cho Pet Tokens. Phía dưới cùng chèn màng lọc **AI Insight** chữ xanh cảnh báo sản xuất quặng.
    - Làm mới Tab **Notes**: Chuyển định nghĩa từ Notes sang **Activity Log**. Sắp xếp theo chiều dọc với Textarea (Operator Notes) nằm trên, và phần hiển thị lịch sử thao tác dạng **Timeline List** (Recent History) có gạch dọc và chấm tròn ở phía dưới.
    - Thêm Text phụ "Last synced 2m ago" nhỏ mờ ở góc phải phía trên cùng của Header bảng Detail.
  - **Account View Layout Switcher:** Thêm cụm nút bấm chuyển đổi nhanh giữa 2 chế độ hiển thị Dạng Bảng (List) cũ và Dạng Thẻ Lưới (Grid) mới tại Header trang Dashboard. Chế độ Grid được code bám sát theo mẫu mock HTML cung cấp, với Card border nhô lên tương tác hover và thanh mini-progressbar hiển thị sức mạnh. Cả 2 chế độ đều hỗ trợ Click để mở Panel trượt góc phải trơn tru.
  - **AI UI Integration:** Hoàn thiện code giao diện mẫu do AI tạo. Chuyển đổi toàn bộ các tham số CSS không tồn tại (ảo) về hệ thống Core System Variable (`--card`, `--muted`, `--foreground`...), vá lỗi giao diện trong suốt và tối ưu code DOM logic chuẩn hóa hoàn toàn với cấu trúc app.



---

## Version 1.0.1
*Bug Fixes and Stability Improvements*

- **API & Error Handling (`frontend/js/api.js`)**
  - Khắc phục lỗi báo "Network Error" chung chung. Bây giờ module fetch sẽ kiểm tra `!res.ok` và hiển thị trực tiếp thông điệp trả về từ backend thay vì im lặng nuốt lỗi.

- **UI & Memory Management (`frontend/js/pages/task-runner.js`)**
  - **Memory Leak Fix**: Khắc phục lỗi rò rỉ bộ đếm giờ (setInterval leak) khi chạy Macro thông qua việc tái sử dụng biến `_runningMacros` (kiểu Map) để quản lý bộ đếm dựa trên `filename`. Gọi thẻ `clearInterval` đúng lúc khi macro hoàn tất hoặc bị lỗi.
  - **WebSocket Integration**: Hoàn thiện Activity Feed để hiển thị dữ liệu real-time của Macro. Bổ sung các event handler `macro_started`, `macro_progress`, `macro_completed`, và `macro_failed` vào UI update loop từ WebSocket.

- **Networking & Server Optimization (`backend/core/macro_replay.py`)**
  - **WebSocket Throttling**: Tối ưu hóa backend bằng cách hạn chế tần suất bắn tín hiệu `macro_progress` qua WebSocket. Hiện tại, nó chỉ gửi dữ liệu progress tối đa 1 lần mỗi giây (throttle 1.0s), ngăn chặn dứt điểm hiện tượng spam tín hiệu khi macro chạy dày đặc làm treo trình duyệt.

- **UI & Consistency (`frontend/js/pages/task-runner.js`)**
  - **Tab Synchronization**: Đồng bộ hoá giao diện Tab 1 (Select Emulators) cho vừa khít với các Tab khác bằng cách sửa class body/padding.
  - **Multi-Emu Notification Fix**: Cập nhật logic Activity Feed nhằm thông báo riêng biệt `✓ Macro completed` cho **TỪNG** emulator thay vì chỉ xuất hiện một thông báo đầu tiên dù đã tick chọn chạy nhiều máy.
  - **Global Feed Timestamps**: Chỉnh lại toàn bộ Activity Feed (kèm theo dòng mô tả "Select emulators..." mặc định) đều có đầy đủ timestamp, chấm tròn trạng thái.

- **New Features (UI Demo)**
  - **Game Accounts Page (`frontend/js/pages/accounts.js`)**: Tạo mới UI trang "Game Accounts" trưng bày bảng dữ liệu chi tiết của từng Acc Game bao gồm: Tên Ingame, Mức Power, Phương thức Đăng nhập, Trạng thái (Matching), Liên Minh, Tài nguyên Thu thập (Gold, Wood, Ore, Pet) và thiết kế thanh hiển thị cuộn ngang chống ép cột. Đã đấu nối trang vào thanh điều hướng Sidebar.


