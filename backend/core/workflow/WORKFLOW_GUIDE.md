# Workflow Module — Developer Guide
_Hệ thống Game Automation cho Call of Dragons_

---

## 1. Kiến Trúc Tổng Quan

```
backend/core/workflow/
├── state_detector.py      # Đôi mắt — Nhận diện trạng thái màn hình
├── core_actions.py        # Bộ não — Các hành động điều hướng cấp cao
├── adb_helper.py          # Bàn tay — Thao tác ADB cơ bản (tap, swipe, back)
├── clipper_helper.py      # Cảm giác — Clipboard intercept, kiểm tra app
├── construction_data.py   # Dữ liệu toạ độ cho từng công trình
├── executor.py            # Bộ thực thi — Chạy Recipe/Workflow từ Registry
├── workflow_registry.py   # Catalog tất cả hàm + Recipe Template
├── bot_orchestrator.py    # Điều phối multi-bot
├── templates/             # Thư mục chứa ảnh template cho nhận diện
│   ├── *.png              # State templates (lobby, loading, items...)
│   ├── contructions/      # Construction templates (hall, market...)
│   ├── special/           # Special screen templates (mail, note...)
│   ├── activities/        # Activity templates (legion, training...)
│   ├── alliance/          # Alliance templates
│   ├── accounts/          # Account management templates
│   ├── icon_markers/      # Icon/marker templates for locating items
│   └── _unknown_captures/ # Auto-saved UNKNOWN screenshots (debug mode)
└── activities/            # Các activity script riêng lẻ
```

### Luồng hoạt động

```
┌──────────────┐    screencap    ┌──────────────────┐
│  ADB Helper  │◄──────────────►│  State Detector   │
│  (tap/back)  │                │  (check_state)    │
└──────┬───────┘                └────────┬──────────┘
       │                                 │
       ▼                                 ▼
┌──────────────────────────────────────────────────┐
│              Core Actions                         │
│  back_to_lobby() / go_to_profile() / ...         │
│  Kết hợp ADB + Detector để điều hướng thông minh │
└──────────────────────┬───────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────────┐
    │ Executor │ │ FullScan │ │ Orchestrator │
    │ (Recipe) │ │ Pipeline │ │ (Multi-Bot)  │
    └──────────┘ └──────────┘ └──────────────┘
```

---

## 2. State Detector — Hệ Thống Nhận Diện

### 2.1 Performance Optimizations

State Detector sử dụng **5 tối ưu** để đạt tốc độ cao nhất:

| # | Optimization | Mô tả | Tốc độ tăng |
|---|-------------|-------|------------|
| 1 | **Grayscale Matching** | Match trên ảnh 1-channel thay vì 3-channel BGR | ~3x nhanh hơn |
| 2 | **ROI Cropping** | Chỉ scan vùng nhỏ trên screen thay vì full 960×540 | ~5-10x nhanh hơn |
| 3 | **Early Exit Cache** | Check state trước đó TRƯỚC, nếu match thì return ngay | ~90% skip |
| 4 | **Screenshot Cache** | Nếu 2 lần gọi liên tiếp < 100ms, dùng lại screenshot cũ | Giảm ADB calls |
| 5 | **Unified Loader** | Load tất cả template categories bằng 1 method | Clean code |

### 2.2 Template Storage Format

Mỗi template được lưu trong RAM dưới dạng dict:

```python
# Cấu trúc: {state_name: [entry, entry, ...]}
# Mỗi entry:
{
    "color": np.ndarray,   # Ảnh gốc BGR (dùng cho debug/display)
    "gray": np.ndarray,    # Ảnh grayscale (dùng cho matching — nhanh 3x)
    "roi": (x1, y1, x2, y2) | None   # Vùng scan trên screen (None = full screen)
}
```

### 2.3 Các loại Template

| Loại | Config Dict | Dùng bởi | Trả về | Threshold |
|------|-----------|---------|--------|-----------|
| **State** | `state_configs` | `check_state()` | State name (`str`) | 0.8 |
| **Construction** | `construction_configs` | `check_construction()` | Name (`str`) hoặc `None` | 0.8 |
| **Special** | `special_configs` | `check_special_state()` | Name (`str`) hoặc `None` | 0.8 |
| **Activity** | `activity_configs` | `check_activity()` | `(name, x, y)` hoặc `None` | 0.98 |
| **Alliance** | `alliance_configs` | `check_alliance()` | `(name, x, y)` hoặc `None` | 0.98 |
| **Icon** | `icon_configs` | `locate_icon()` | `(name, x, y)` hoặc `None` | 0.8 |
| **Account** | `account_configs` | `check_account_state()` | `(name, x, y)` hoặc `None` | 0.95 |

### 2.4 Matching Pipeline

```
screencap_memory(serial)
    │
    ▼ (cached nếu < 100ms)
screen (BGR) ──► cvtColor ──► screen_gray (1-channel)
                                    │
              ┌─────────────────────┤
              ▼                     ▼
    [Early Exit Cache]      [Priority Scan]
    Check last matched      Check all templates
    state FIRST              in priority order
              │                     │
              ▼                     ▼
         _match_single(screen_gray, entry, threshold)
              │
              ├── ROI crop (nếu roi_hints có entry cho template)
              │   screen_gray[y1:y2, x1:x2]
              │
              ├── cv2.matchTemplate(region, tmpl_gray, TM_CCOEFF_NORMED)
              │
              └── max_val >= threshold? → MATCH!
                  (coordinates auto-adjusted nếu dùng ROI)
```

### 2.5 `check_state_full()` — Method Quan Trọng Nhất

```python
result = detector.check_state_full(serial)
# result = {
#     "state": "UNKNOWN / TRANSITION",    # hoặc tên state
#     "construction": "HALL",              # hoặc None
#     "special": "MAIL_MENU",             # hoặc None
#     "screen": <numpy array>             # screenshot BGR, tái sử dụng được
# }
```

**Khi nào dùng `check_state()` vs `check_state_full()`:**
- `check_state()` — Khi chỉ cần biết state chính
- `check_state_full()` — Khi cần xác định chính xác (dùng trong `back_to_lobby`)

### 2.6 Priority Order trong `check_state()`

```
0. [Early Exit] Last matched state     ← Check trước nhất (90% hit)
─── Nếu miss ───
1. LOADING SCREEN (NETWORK ISSUE)      ← Priority checks
2. LOADING SCREEN
3. IN-GAME LOBBY (PROFILE MENU DETAIL)
4. IN-GAME LOBBY (PROFILE MENU)
5. IN-GAME LOBBY (EVENTS MENU)
6. IN-GAME LOBBY (BAZAAR)
7. IN-GAME LOBBY (HALL_NEW)
8. IN-GAME ITEMS (ARTIFACTS)
9. IN-GAME ITEMS (RESOURCES)
─── Base states ───
10. IN-GAME LOBBY (IN_CITY)
11. IN-GAME LOBBY (OUT_CITY)
─── Fallback ───
12. "UNKNOWN / TRANSITION"
```

---

## 3. Core Actions — Các Hàm Điều Hướng

### 3.1 `back_to_lobby(serial, detector, timeout_sec=30, target_lobby=None, debug=False)`

Hàm cốt lõi nhất. Tự động quay về Lobby từ **bất kỳ state nào**.

**Cơ chế:**
- Vòng lặp **dựa trên thời gian** (`timeout_sec`)
- Mỗi vòng gọi `check_state_full()` — **1 lần ADB screencap** cho tất cả checks
- Xử lý theo state:

| State | Hành động | Sleep |
|-------|----------|-------|
| Lobby | Return True ✓ | — |
| BLACK SCREEN (brightness < 15) | Chờ kiên nhẫn, **KHÔNG bấm BACK** | 5s |
| LOADING SCREEN | Chờ kiên nhẫn | 10s |
| NETWORK ISSUE | Tap Confirm | 2s |
| Construction | Press BACK ngay | 1.5s |
| Special | Press BACK ngay | 1.5s |
| UNKNOWN (grace < 5s) | Chờ thêm | 1.5s |
| UNKNOWN (grace >= 5s) | Press BACK | 1.5s |
| Known menu | Press BACK (max 3/state) | 1.5s |

**Tham số `debug=True`:** Khi bật, tự động lưu screenshot mỗi lần gặp UNKNOWN vào `templates/_unknown_captures/` để review và tạo template mới.

### 3.2 Các hàm khác

| Hàm | Yêu cầu đang ở | Đi đến |
|-----|----------------|--------|
| `go_to_profile()` | Lobby | Profile Menu |
| `go_to_profile_details()` | Lobby | Profile Menu Detail |
| `go_to_resources()` | Lobby | Items → Resources tab |
| `go_to_construction(name)` | Lobby | Construction screen |
| `go_to_farming(resource_type)` | Lobby (OUT_CITY) | World Map → Gather |
| `ensure_app_running(serial, pkg)` | Any | Check app, boot nếu cần |
| `startup_to_lobby(serial, detector)` | Any | Boot game + vào lobby |
| `wait_for_state(serial, detector, targets)` | Any | Block cho đến target |

---

## 4. Hướng Dẫn Mở Rộng

### 4.1 Thêm Template mới (Giảm UNKNOWN)

#### Bước 1: Thu thập screenshot

**Cách nhanh:** Chạy `test_back_to_lobby.py` với `debug=True`:
```bash
python backend\core\test_back_to_lobby.py 1
```
Hoặc chạy collector chuyên dụng:
```bash
python backend\core\collect_unknown_states.py 1 120
```
Screenshots UNKNOWN tự lưu vào `templates/_unknown_captures/`.

#### Bước 2: Crop template

Mở screenshot, crop phần **đặc trưng nhất** (icon, nút bấm, text nổi bật):
- **Không crop quá lớn** — template nhỏ match nhanh hơn
- **Không crop quá nhỏ** — dễ false positive
- **Kích thước lý tưởng:** 50×50 ~ 150×80 pixels
- **Chọn vùng ÍT thay đổi** — tránh crop vùng có animation/counter

#### Bước 3: Lưu file

```
templates/              ← State chính (lobby_xxx.png)
templates/contructions/ ← Construction buildings (con_xxx.png)
templates/special/      ← Special popup (xxx.png)
templates/activities/   ← Activity icons
templates/alliance/     ← Alliance screens
templates/icon_markers/ ← Map icons
templates/accounts/     ← Account names
```

#### Bước 4: Đăng ký trong `state_detector.py`

```python
# Ví dụ: Thêm state chính
self.state_configs = {
    "lobby_alliance.png": "IN-GAME LOBBY (ALLIANCE MENU)",   # ← THÊM
    # ... các state cũ ...
}

# Ví dụ: Thêm construction
self.construction_configs = {
    "contructions/con_forge.png": "FORGE",   # ← THÊM
    # ...
}

# Ví dụ: Thêm special screen
self.special_configs = {
    "special/gift_popup.png": "GIFT_POPUP",   # ← THÊM
    # ...
}
```

#### Bước 5 (Optional): Thêm ROI cho template mới

Nếu biết template chỉ xuất hiện ở vùng cố định trên screen:

```python
self.roi_hints = {
    # Format: "filename.png": (x1, y1, x2, y2)
    # Screen size: 960 × 540
    "lobby_alliance.png": (700, 0, 960, 100),   # Top-right area
}
```

**Cách xác định ROI:**
1. Mở screenshot gốc (960×540)
2. Xác định vùng mà template icon **luôn xuất hiện** trên screen
3. Thêm padding ~50px mỗi chiều cho an toàn
4. Ghi vào `roi_hints`

> ⚠️ **Nếu không chắc toạ độ ROI, ĐỪNG thêm.** Để `None` (full screen) vẫn hoạt động đúng, chỉ chậm hơn. ROI sai = template không bao giờ match!

#### Bước 6 (Nếu state chính): Thêm vào Priority List

Nếu state mới cần priority cao (check trước các state khác):

```python
# Trong _match_state_from_screen():
priority_checks = [
    "LOADING SCREEN (NETWORK ISSUE)",
    "LOADING SCREEN",
    "IN-GAME LOBBY (ALLIANCE MENU)",   # ← THÊM VÀO ĐÂY
    # ...
]
```

---

### 4.2 Thêm ROI cho Template đã có

**Mục đích:** Tăng tốc matching ~5-10x cho template cụ thể.

```python
# Trong state_detector.py > self.roi_hints:
self.roi_hints = {
    # ── Lobby indicators ── (thường ở bottom-left)
    "lobby_hammer.png": (0, 380, 250, 540),
    "lobby_magnifier.png": (0, 380, 250, 540),

    # ── Profile buttons ── (thường ở top-left)
    "lobby_profile_menu.png": (0, 0, 250, 120),

    # ── Construction ── (thường ở top-center)
    "contructions/con_hall.png": (300, 50, 700, 200),
}
```

**Quy tắc:**
1. ROI phải **LỚN HƠN** template image (nếu nhỏ hơn → auto fallback full screen)
2. Padding 50-100px quanh vùng thực tế
3. Test lại sau khi thêm ROI — nếu template không match nữa → ROI sai, bỏ ra

---

### 4.3 Thêm Hàm Action mới vào `core_actions.py`

**Pattern chuẩn:**

```python
def go_to_something(serial: str, detector: GameStateDetector) -> bool:
    """Mô tả ngắn. Returns True nếu thành công."""
    print(f"[{serial}] Navigating to Something...")

    # 1. Đảm bảo đúng lobby
    if not back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)"):
        return False

    # 2. Tap
    adb_helper.tap(serial, x, y)
    time.sleep(2)

    # 3. Xác nhận
    state = wait_for_state(serial, detector, ["TARGET_STATE"], timeout_sec=10)
    if not state:
        return False

    print(f"[{serial}] -> Target reached!")
    return True
```

**Quy tắc:**
1. Return `bool` — True = OK, False = fail
2. Dùng `wait_for_state()` để xác nhận — không đoán bằng `time.sleep()`
3. Log format: `[{serial}] [LEVEL] Message`
4. Gọi `back_to_lobby()` ở đầu nếu cần vị trí bắt đầu

### 4.4 Đăng ký hàm vào Workflow Registry

**workflow_registry.py:**
```python
{
    "id": "go_to_something",
    "label": "Go to Something",
    "category": "Core Actions",
    "icon": "🎯",
    "color": "#6366f1",
    "description": "Navigate to Something screen",
    "params": [],
},
```

**executor.py:**
```python
elif fn_id == "go_to_something":
    ok = await asyncio.to_thread(core_actions.go_to_something, serial, detector)
```

### 4.5 Thêm Construction mới

1. Template → `contructions/con_xxx.png`
2. Đăng ký → `state_detector.py > construction_configs`
3. Tap sequence → `construction_data.py`:
```python
CONSTRUCTION_TAPS = {
    "XXX": [(x1, y1), (x2, y2)],  # Tên PHẢI khớp construction_configs
}
```

### 4.6 Chế độ Bỏ qua lỗi (continue_on_error)

Mặc định, nếu một Activity bị lỗi (ví dụ `scan_full` thất bại), Orchestrator sẽ dừng tiến trình của account hiện tại và lập tức chuyển (swap) sang account tiếp theo để đảm bảo an toàn, tránh các trạng thái không lường trước. 
Để cho phép Orchestrator tiếp tục chạy các Activity phía sau dù cho Activity hiện tại bị lỗi, bạn có thể thiết lập cờ `continue_on_error` thành `true` trong tab cấu hình phần **Misc** (Miscellaneous Settings) khi chạy một Workflow hay Target Group.

**Cấu trúc cấu hình tại backend:**
```json
{
    "group_id": 1,
    "misc_config": {
        "skip_cooldown": false,
        "cooldown_min": 0,
        "continue_on_error": true
    }
}
```

---

## 5. Danh Sách States Hiện Có

### Main States (`check_state`)
| State | Mô tả |
|-------|--------|
| `LOADING SCREEN` | Đang tải game |
| `LOADING SCREEN (NETWORK ISSUE)` | Lỗi mạng, cần tap Confirm |
| `IN-GAME LOBBY (IN_CITY)` | Lobby — trong thành |
| `IN-GAME LOBBY (OUT_CITY)` | Lobby — ngoài thành |
| `IN-GAME LOBBY (PROFILE MENU)` | Menu profile |
| `IN-GAME LOBBY (PROFILE MENU DETAIL)` | Chi tiết profile |
| `IN-GAME LOBBY (EVENTS MENU)` | Menu sự kiện |
| `IN-GAME LOBBY (BAZAAR)` | Cửa hàng |
| `IN-GAME LOBBY (HALL_NEW)` | Hall mới |
| `IN-GAME ITEMS (ARTIFACTS)` | Tab Artifacts |
| `IN-GAME ITEMS (RESOURCES)` | Tab Resources |
| `LOBBY_MENU_EXPANDED` | Menu mở rộng |
| `UNKNOWN / TRANSITION` | Không nhận diện được |
| `ERROR_CAPTURE` | Lỗi ADB screencap |

### Construction States
`HALL` · `MARKET` · `ELIXIR_HEALING` · `PET_SANCTUARY` · `PET_ENCLOSURE` · `MARKERS_MENU` · `ALLIANCE_MENU` · `TRAIN_UNITS` · `SCOUT_SENTRY_POST` · `TAVERN`

### Special States
`SERVER_MAINTENANCE` · `AUTO_CAPTURE_PET` · `SETTINGS` · `CHARACTER_MANAGEMENT` · `MAIL_MENU` · `NOTE` · `RESOURCE_STATISTICS` · `MARKET_MENU`

---

## 6. Debug & Troubleshooting

### Scripts hỗ trợ

| Script | Mục đích |
|--------|---------|
| `test_back_to_lobby.py 1` | Test back_to_lobby trên emulator index 1 (debug=True) |
| `test_full_scan.py 1` | Test toàn bộ full scan pipeline |
| `collect_unknown_states.py 1 120` | Thu thập UNKNOWN screenshots trong 120s |

### Template không match?

1. **Threshold quá cao** → giảm từ 0.8 xuống 0.75
2. **Template quá lớn** → crop nhỏ hơn, lấy phần đặc trưng nhất
3. **ROI sai** → bỏ ROI entry trong `roi_hints` (full screen fallback)
4. **Game resolution khác** → templates phải crop từ cùng resolution

### back_to_lobby chậm?

1. Nhiều UNKNOWN → thêm templates (xem mục 4.1)
2. Grace period quá dài → giảm trong `core_actions.py`
3. Chưa có ROI → thêm ROI vào `roi_hints` (xem mục 4.2)
