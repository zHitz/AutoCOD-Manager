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
│   └── icon_markers/      # Icon/marker templates for locating items
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

### 2.1 Các loại Template

| Loại | Config Dict | Dùng bởi | Mục đích |
|------|------------|---------|---------|
| **State** | `state_configs` | `check_state()` | Nhận diện trạng thái chính (Lobby, Loading, Menu...) |
| **Construction** | `construction_configs` | `check_construction()` | Nhận diện buildings (Hall, Market, Tavern...) |
| **Special** | `special_configs` | `check_special_state()` | Nhận diện popup đặc biệt (Server Maintenance, Mail...) |
| **Activity** | `activity_configs` | `check_activity()` | Tìm vị trí icons + trả toạ độ center |
| **Alliance** | `alliance_configs` | `check_alliance()` | Nhận diện giao diện alliance |
| **Icon** | `icon_configs` | `locate_icon()` | Tìm vị trí icon tài nguyên trên bản đồ |
| **Account** | `account_configs` | `check_account_state()` | Nhận diện tên account đang login |

### 2.2 Phân cấp Methods

```
                    ┌─ check_state()         # 1 screencap, check state_configs
                    │
screencap_memory()─►├─ check_state_full()    # 1 screencap, check TẤT CẢ (state → construction → special)
                    │
                    ├─ check_construction()   # 1 screencap, check construction_configs
                    │
                    ├─ check_special_state()  # 1 screencap, check special_configs
                    │
                    └─ check_activity()       # 1 screencap, trả (name, x, y)

Internal (no ADB):
  _match_state_from_screen(screen)         # Dùng nội bộ, nhận numpy array
  _match_construction_from_screen(screen)  # Dùng nội bộ, nhận numpy array
  _match_special_from_screen(screen)       # Dùng nội bộ, nhận numpy array
```

### 2.3 `check_state_full()` — Method Quan Trọng Nhất

```python
result = detector.check_state_full(serial)
# result = {
#     "state": "UNKNOWN / TRANSITION",    # hoặc tên state
#     "construction": "HALL",              # hoặc None
#     "special": "MAIL_MENU",             # hoặc None
#     "screen": <numpy array>             # screenshot, tái sử dụng được
# }
```

**Khi nào dùng `check_state()` vs `check_state_full()`:**
- `check_state()` — Khi chỉ cần biết state chính, không cần check construction/special
- `check_state_full()` — Khi cần xác định chính xác game đang ở đâu (dùng trong `back_to_lobby`)

### 2.4 Quy tắc Priority trong `check_state()`

Templates được check **theo thứ tự ưu tiên** — match đầu tiên sẽ return ngay:

```
1. LOADING SCREEN (NETWORK ISSUE)    ← Ưu tiên cao nhất
2. LOADING SCREEN
3. IN-GAME LOBBY (PROFILE MENU DETAIL)
4. IN-GAME LOBBY (PROFILE MENU)
5. IN-GAME LOBBY (EVENTS MENU)
6. IN-GAME LOBBY (BAZAAR)
7. IN-GAME LOBBY (HALL_NEW)
8. IN-GAME ITEMS (ARTIFACTS)
9. IN-GAME ITEMS (RESOURCES)
--- Nếu không match ---
10. IN-GAME LOBBY (IN_CITY)           ← Lobby states check cuối
11. IN-GAME LOBBY (OUT_CITY)
--- Nếu vẫn không match ---
12. "UNKNOWN / TRANSITION"            ← Fallback
```

---

## 3. Core Actions — Các Hàm Điều Hướng

### 3.1 `back_to_lobby(serial, detector, timeout_sec=30, target_lobby=None)`

Hàm cốt lõi nhất. Tự động quay về Lobby từ **bất kỳ state nào**.

**Cơ chế hoạt động:**
- Dùng vòng lặp **dựa trên thời gian** (`timeout_sec`), không phải số lần thử
- Mỗi vòng lặp gọi `check_state_full()` — **1 lần ADB screencap** cho tất cả checks
- Xử lý theo từng loại state:

| State phát hiện | Hành động | Sleep |
|-----------------|----------|-------|
| Lobby (IN_CITY / OUT_CITY) | Return True ✓ | — |
| LOADING SCREEN | Chờ kiên nhẫn | 10s |
| NETWORK ISSUE | Tap Confirm | 2s |
| Construction (HALL, MARKET...) | Press BACK ngay | 1.5s |
| Special (MAIL, NOTE...) | Press BACK ngay | 1.5s |
| UNKNOWN (grace < 5s) | Chờ thêm | 1.5s |
| UNKNOWN (grace >= 5s) | Press BACK | 1.5s |
| Known menu (Profile, Events...) | Press BACK (max 3 lần/state) | 1.5s |

**Tham số `target_lobby`:**
```python
back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
# → Về lobby, rồi nếu đang ở OUT_CITY thì tap (50, 500) để swap sang IN_CITY
```

### 3.2 Các hàm điều hướng khác

| Hàm | Yêu cầu đang ở | Đi đến |
|-----|----------------|--------|
| `go_to_profile()` | Lobby | Profile Menu |
| `go_to_profile_details()` | Lobby | Profile Menu Detail |
| `go_to_resources()` | Lobby | Items → Resources tab |
| `go_to_construction(name)` | Lobby | Construction screen (HALL, MARKET...) |
| `go_to_farming(resource_type)` | Lobby (OUT_CITY) | World Map → Gather resource |
| `capture_pet()` | Lobby (OUT_CITY) | Auto Capture Pet |
| `go_to_pet_sanctuary()` | Lobby (OUT_CITY) | Pet Sanctuary |

### 3.3 Hàm hỗ trợ

| Hàm | Mô tả |
|-----|-------|
| `ensure_app_running(serial, pkg)` | Check app, boot nếu cần. Return True/False/None |
| `startup_to_lobby(serial, detector, pkg)` | Boot game + chờ vào lobby (all-in-one) |
| `wait_for_state(serial, detector, targets, timeout)` | Block cho đến khi đạt target state |
| `check_app_crash(serial)` | Phát hiện app crash/freeze bằng pixel comparison |
| `ensure_lobby_menu_open(serial, detector)` | Đảm bảo menu expand đang mở |

---

## 4. Hướng Dẫn Mở Rộng

### 4.1 Thêm State mới vào Nhận Diện

**Bước 1:** Chụp screenshot trong game, crop phần nhận diện đặc trưng (icon, text nổi bật).

**Bước 2:** Lưu vào đúng thư mục template:
```
templates/              ← State chính (lobby_xxx.png)
templates/contructions/ ← Construction buildings
templates/special/      ← Special popup screens
templates/activities/   ← Activity icons
templates/alliance/     ← Alliance screens
templates/icon_markers/ ← Map icons
```

**Bước 3:** Đăng ký trong `state_detector.py`:
```python
# Thêm state chính (check_state sẽ nhận diện được)
self.state_configs = {
    "lobby_alliance.png": "IN-GAME LOBBY (ALLIANCE MENU)",   # ← THÊM
    # ... các state cũ ...
}

# Thêm construction (check_construction + check_state_full sẽ nhận diện được)
self.construction_configs = {
    "contructions/con_forge.png": "FORGE",   # ← THÊM
    # ...
}
```

**Bước 4:** Nếu state mới cần priority cao, thêm vào `priority_checks` trong `_match_state_from_screen()`.

### 4.2 Thêm Hàm Action mới vào `core_actions.py`

**Pattern chuẩn** — mọi nav function nên tuân theo:

```python
def go_to_something(serial: str, detector: GameStateDetector) -> bool:
    """
    Mô tả ngắn. Yêu cầu đang ở state nào.
    Returns True nếu thành công, False nếu thất bại.
    """
    print(f"[{serial}] Navigating to Something...")

    # 1. Đảm bảo đúng lobby (nếu cần)
    if not back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)"):
        print(f"[{serial}] [FAILED] Could not reach lobby.")
        return False

    # 2. Thực hiện tap sequence
    adb_helper.tap(serial, x, y)
    time.sleep(2)

    # 3. Xác nhận bằng wait_for_state
    state = wait_for_state(serial, detector, ["TARGET_STATE"], timeout_sec=10)
    if not state:
        print(f"[{serial}] [FAILED] Did not reach target.")
        return False

    print(f"[{serial}] -> Target reached!")
    return True
```

**Quy tắc bắt buộc:**
1. **Luôn return `bool`** — True = thành công, False = thất bại
2. **Luôn dùng `wait_for_state()` để xác nhận** — không đoán mò bằng `time.sleep()` dài
3. **Luôn log rõ ràng** — format: `[{serial}] [LEVEL] Message`
4. **Gọi `back_to_lobby()` ở đầu** nếu cần đảm bảo vị trí bắt đầu

### 4.3 Đăng ký hàm mới vào Workflow Registry

Thêm vào `FUNCTION_REGISTRY` trong `workflow_registry.py`:

```python
{
    "id": "go_to_something",           # Khớp với tên trong executor.py
    "label": "Go to Something",         # Hiển thị trên UI
    "category": "Core Actions",
    "icon": "🎯",
    "color": "#6366f1",
    "description": "Navigate to Something screen",
    "params": [],                        # Thêm param nếu cần
},
```

Rồi thêm handler trong `executor.py`:
```python
elif fn_id == "go_to_something":
    ok = await asyncio.to_thread(
        core_actions.go_to_something, serial, detector
    )
```

### 4.4 Thêm Construction mới

**Bước 1:** Thêm template vào `contructions/` folder
**Bước 2:** Đăng ký trong `state_detector.py > construction_configs`
**Bước 3:** Thêm tap sequence trong `construction_data.py`:
```python
CONSTRUCTION_TAPS = {
    "FORGE": [           # Tên PHẢI khớp với construction_configs
        (x1, y1),        # Tap 1
        (x2, y2),        # Tap 2
    ],
}
```

---

## 5. Danh Sách States Hiện Có

### Main States (`check_state`)
| State | Mô tả |
|-------|--------|
| `LOADING SCREEN` | Đang tải game |
| `LOADING SCREEN (NETWORK ISSUE)` | Lỗi mạng, cần tap Confirm |
| `IN-GAME LOBBY (IN_CITY)` | Lobby chính — trong thành |
| `IN-GAME LOBBY (OUT_CITY)` | Lobby chính — ngoài thành |
| `IN-GAME LOBBY (PROFILE MENU)` | Menu profile |
| `IN-GAME LOBBY (PROFILE MENU DETAIL)` | Chi tiết profile |
| `IN-GAME LOBBY (EVENTS MENU)` | Menu sự kiện |
| `IN-GAME LOBBY (BAZAAR)` | Cửa hàng Bazaar |
| `IN-GAME LOBBY (HALL_NEW)` | Màn hình Hall mới |
| `IN-GAME ITEMS (ARTIFACTS)` | Tab Artifacts |
| `IN-GAME ITEMS (RESOURCES)` | Tab Resources |
| `LOBBY_MENU_EXPANDED` | Menu mở rộng (chỉ dùng bởi `is_menu_expanded`) |
| `UNKNOWN / TRANSITION` | Không nhận diện được |
| `ERROR_CAPTURE` | Lỗi ADB screencap |

### Construction States (`check_construction`)
`HALL` · `MARKET` · `ELIXIR_HEALING` · `PET_SANCTUARY` · `PET_ENCLOSURE` · `MARKERS_MENU` · `ALLIANCE_MENU` · `TRAIN_UNITS` · `SCOUT_SENTRY_POST` · `TAVERN`

### Special States (`check_special_state`)
`SERVER_MAINTENANCE` · `AUTO_CAPTURE_PET` · `SETTINGS` · `CHARACTER_MANAGEMENT` · `MAIL_MENU` · `NOTE`
