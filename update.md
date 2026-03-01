# COD Game Automation Manager - Update Log

## Version 1.0.6 (Current)
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


