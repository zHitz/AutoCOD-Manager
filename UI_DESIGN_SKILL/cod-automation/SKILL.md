# AI Agent Guide — Call of Dragons Automation System

> **Đọc file này TRƯỚC KHI làm bất kỳ task nào.**
> File này chứa tất cả kiến thức cần thiết để implement, debug, và test bất kỳ function nào trong hệ thống.

---

## 1. Kiến Trúc Hệ Thống

### 3-Layer Architecture (Không được mix)

```
Layer 3: workflow scripts (tasks/xxx_workflow.py)
    │ Gọi core_actions, KHÔNG gọi trực tiếp adb_helper hoặc state_detector
    │
Layer 2: core_actions.py — Bộ não (123K+ lines)
    │ Logic phức tạp: navigation, popup handling, recovery
    │ Gọi state_detector + adb_helper
    │
Layer 1: state_detector.py — Đôi mắt | adb_helper.py — Bàn tay
    │ Template matching (cv2)       │ tap, swipe, screencap, press_back
    │                               │
Layer 0: ADB protocol → Android emulator (MuMu/LDPlayer)
```

### Golden Rule — Detect → Validate → Act → Verify → Recover

```python
state = detector.check_state(serial)        # DETECT
if state != expected:                        # VALIDATE
    core_actions.back_to_lobby(...)          # RECOVER
adb_helper.tap(serial, x, y)                # ACT
result = wait_for_state(serial, ...)        # VERIFY
```

**KHÔNG BAO GIỜ** thực hiện action mà không verify kết quả.

---

## 2. Project Structure

```
Part3_Control_EMU/
├── workflow/
│   ├── core_actions.py          # 🧠 Brain — ALL game actions
│   ├── state_detector.py        # 👁️ Eyes — template matching
│   ├── adb_helper.py            # ✋ Hands — ADB commands
│   ├── ocr_helper.py            # 📖 OCR — Tesseract text reading
│   ├── emu_tool.py              # 🔧 ALL-IN-ONE debug tool (8 commands)
│   ├── _debug/                  # Auto-generated debug images
│   │
│   ├── policy/                  # Season Policies automation
│   │   ├── engine.py            # V3 Smart Path Engine
│   │   ├── data.py              # Config loader
│   │   ├── season_config.json   # 🔧 EDIT: season-specific data
│   │   └── README.md            # Full policy docs
│   │
│   ├── templates/               # Template images (14 categories)
│   ├── tasks/                   # Workflow scripts
│   ├── NEW_TASKS-MODIFY_TASKS/  # Docs & specs
│   └── MERGE_GUIDE*.md          # Integration guides
│
└── UI_MANAGER/backend/config.py # adb_path, tesseract_path, etc.
```

---

## 3. Core APIs

### 3.1 `adb_helper` — Bàn tay

```python
import adb_helper

adb_helper.tap(serial, x, y)                          # Tap tại toạ độ
adb_helper.swipe(serial, x1, y1, x2, y2, duration)    # Swipe (scroll)
adb_helper.press_back(serial)                          # Nút BACK
adb_helper.press_back_n(serial, count, delay)          # Multi BACK
adb_helper.screencap(serial, local_path) -> bool       # Chụp screenshot
adb_helper.list_devices() -> list[str]                 # List connected emulators
adb_helper.ping_device(serial) -> bool                 # Check emulator alive
```

**Resolution: 960×540** — Tất cả toạ độ dùng resolution này.

### 3.2 `GameStateDetector` — Đôi mắt

```python
from workflow.state_detector import GameStateDetector

detector = GameStateDetector(adb_path=config.adb_path, templates_dir="workflow/templates")

# Main state detection
detector.check_state(serial) -> str
    # Returns: "IN-GAME LOBBY (IN_CITY)", "LOADING SCREEN", "UNKNOWN / TRANSITION", etc.

# Building/construction screen
detector.check_construction(serial, target="RESEARCH_CENTER") -> Optional[str]

# Special states (popups, headers)
detector.check_special_state(serial, target="POLICY_SCREEN") -> Optional[str]

# Activity buttons (returns position!)
detector.check_activity(serial, target="POLICY_ENACT_BTN", threshold=0.85) -> Optional[tuple(name, x, y)]

# Alliance buttons
detector.check_alliance(serial, target="ALLIANCE_WAR") -> Optional[tuple(name, x, y)]

# Small icons
detector.locate_icon(serial, target="ICON_NAME") -> Optional[tuple(name, x, y)]

# Get raw frame (cv2 image)
detector.get_frame(serial) -> Optional[np.ndarray]

# Menu state
detector.is_menu_expanded(serial) -> bool
```

### 3.3 `core_actions` — Bộ não

Key functions:

```python
from workflow import core_actions

# Navigation
core_actions.back_to_lobby(serial, detector, max_attempts=15, target_lobby="IN-GAME LOBBY (IN_CITY)")
core_actions.go_to_profile(serial, detector) -> bool
core_actions.go_to_construction(serial, detector, name) -> bool
core_actions.go_to_alliance(serial, detector) -> bool
core_actions.go_to_resources(serial, detector) -> bool
core_actions.ensure_lobby_menu_open(serial, detector) -> bool

# Waiting
core_actions.wait_for_state(serial, detector, target_states, timeout_sec=60, check_mode="state")
    # check_mode: "state" | "construction" | "special" | "activity" | "account"

# App management
core_actions.startup_to_lobby(serial, detector, package_name) -> bool
core_actions.check_app_crash(serial, package_name) -> bool
```

### 3.4 `ocr_helper` — OCR

```python
from workflow.ocr_helper import parse_game_timer, read_text_region

parse_game_timer("3h 15m") -> int  # Returns seconds (11700)
parse_game_timer("00:20:58") -> int  # Returns seconds (1258)
```

---

## 4. Template System

### Template Categories

| Dict trong `state_detector.py` | Method detect | Return | Khi nào dùng |
|------|--------|--------|------|
| `state_configs` | `check_state()` | `str` state name | Màn hình chính (lobby, loading) |
| `construction_configs` | `check_construction()` | `str` name or None | Màn hình building |
| `special_configs` | `check_special_state()` | `str` name or None | popup, header |
| `activity_configs` | `check_activity()` | `(name, x, y)` or None | **Buttons cần tap** (trả tọa độ) |
| `alliance_configs` | `check_alliance()` | `(name, x, y)` or None | Alliance buttons |

### Thêm template mới (3 bước dùng `emu_tool.py`)

1. **Screenshot + Crop**:
   ```bash
   python workflow/emu_tool.py screenshot           # chụp → _debug/screenshot.png
   python workflow/emu_tool.py grid                  # chụp + grid → _debug/grid.png (xem toạ độ)
   python workflow/emu_tool.py crop --region 400,390,500,420 -o workflow/templates/category/name.png
   ```

2. **Register**: Mở `state_detector.py`, thêm vào dict phù hợp:
   ```python
   self.activity_configs = {
       "category/name.png": "TEMPLATE_ID",  # <-- thêm dòng này
   }
   ```

3. **Verify**:
   ```bash
   python workflow/emu_tool.py locate -t workflow/templates/category/name.png
   python workflow/emu_tool.py match -t workflow/templates/category/name.png
   ```

---

## 5. Emulator Management

### Test Emulator: `emulator-5568`

```python
SERIAL = "emulator-5568"
PACKAGE = "com.farlightgames.samo.gp.vn"  # Call of Dragons VN
```

### Setup Emulator (tự động)

```python
import os, sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)
ui_mgr = os.path.abspath(os.path.join(root_dir, "..", "UI_MANAGER"))
sys.path.append(ui_mgr)

from backend.config import config
config.load()

import adb_helper
from workflow.state_detector import GameStateDetector
from workflow import core_actions

SERIAL = "emulator-5568"
PACKAGE = "com.farlightgames.samo.gp.vn"

# Init detector
templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
detector = GameStateDetector(adb_path=config.adb_path, templates_dir=templates_dir)

# Check emulator connected
if not adb_helper.ping_device(SERIAL):
    print(f"[ERROR] {SERIAL} not connected. Start MuMu/LDPlayer first.")
    sys.exit(1)

# Start game and wait for lobby
core_actions.startup_to_lobby(SERIAL, detector, PACKAGE)
```

### Quick Debug via CLI (dùng `emu_tool.py`)

```bash
# Screenshot
python workflow/emu_tool.py screenshot

# Screenshot + grid overlay
python workflow/emu_tool.py grid --size 25

# Check pixel color
python workflow/emu_tool.py pixel --pos 480,270 --area

# Find template (NO side effects)
python workflow/emu_tool.py locate -t workflow/templates/policy/enact_btn.png

# Test multiple thresholds
python workflow/emu_tool.py match -t template.png --thresholds 0.7,0.8,0.85,0.9

# Tap with before/after comparison
python workflow/emu_tool.py tap --pos 480,270 --wait 3

# Check game state
python workflow/emu_tool.py state -v
```

All output goes to `workflow/_debug/`. JSON result on last line for machine parsing.

---

## 6. Quy Trình Implement Function Mới (4 Bước)

> Khi nhận function spec mới, AI PHẢI làm theo quy trình này:

### Bước 1: Phân tích & Lập kế hoạch

1. Đọc function spec → xác định precondition, các bước, expected states
2. Xác định cần templates nào (buttons, screens, popups)
3. List ra tất cả states cần detect
4. Xác định edge cases: lag, popup bất ngờ, không đủ resource, button không có...

### Bước 2: Capture Templates & Register (dùng `emu_tool.py`)

```bash
# 1. Chụp screen + grid để tìm toạ độ
python workflow/emu_tool.py grid --size 25
# → Mở _debug/grid.png, xác định vùng cần crop (x1,y1,x2,y2)

# 2. Crop template
python workflow/emu_tool.py crop --region 400,390,500,420 -o workflow/templates/category/new_btn.png
# → Kiểm tra _debug/crop_overlay.png xem crop đúng chưa

# 3. Verify template match
python workflow/emu_tool.py match -t workflow/templates/category/new_btn.png
# → Xem confidence ở threshold nào match

# 4. Register vào state_detector.py
# Thêm: "category/new_btn.png": "NEW_BUTTON",
```

### Bước 3: Implement Function

- Đặt trong `core_actions.py` (Layer 2)
- Tuân thủ pattern: Detect → Validate → Act → Verify → Recover
- Signature: `def new_function(serial: str, detector: GameStateDetector) -> bool:`
- Luôn bắt đầu bằng `back_to_lobby()` nếu cần navigate từ đầu

### Bước 4: Self-Test (dùng `emu_tool.py`)

```bash
# Test từng step:
python workflow/emu_tool.py state                    # Đang ở đâu?
python workflow/emu_tool.py tap --pos 815,80 --wait 3  # Tap + before/after
python workflow/emu_tool.py locate -t template.png     # Button ở đâu?
python workflow/emu_tool.py state -v                   # State sau action?
```

---

## 7. `emu_tool.py` — All-in-One Debug Tool

> **AI agent PHẢI dùng tool này** để tự chụp ảnh, phân tích, debug, và giải quyết vấn đề.
> **KHÔNG chờ user chụp ảnh hoặc chỉ dẫn debug.**

### 8 Commands:

| Command | Mô tả | Key Output |
|---------|-------|------------|
| `screenshot` | Chụp screenshot | `_debug/screenshot.png` |
| `grid` | Screenshot + coordinate grid overlay | `_debug/grid.png` |
| `crop` | Crop region → save template | `_debug/cropped.png` + `crop_overlay.png` |
| `locate` | Find template (READ-ONLY, ko tap) | JSON: `{found, x, y, confidence}` |
| `pixel` | Get pixel color at position | JSON: `{r, g, b, h, s, v}` |
| `state` | Detect game state | JSON: `{state}` |
| `match` | Test template ở nhiều thresholds | Table: `threshold → ✅/❌` |
| `tap` | Tap + before/after comparison | `tap_before/after/diff.png` + `change_pct` |

### Quy trình Debug với emu_tool:

```bash
# 1. Xem đang ở đâu
python workflow/emu_tool.py state -v
python workflow/emu_tool.py screenshot

# 2. Tìm toạ độ element
python workflow/emu_tool.py grid --size 25
# → Mở _debug/grid.png → tìm x,y

# 3. Kiểm tra pixel tại vị trí
python workflow/emu_tool.py pixel --pos 480,270 --area

# 4. Locate template (KHÔNG tap)
python workflow/emu_tool.py locate -t path/to/template.png
# → Output: FOUND/NOT_FOUND + center coordinates + confidence

# 5. Test template ở nhiều thresholds cùng lúc
python workflow/emu_tool.py match -t template.png --thresholds 0.7,0.8,0.85,0.9

# 6. Crop vùng từ screen hiện tại
python workflow/emu_tool.py crop --region 400,200,550,250 -o workflow/templates/new_btn.png
# → Xem _debug/crop_overlay.png kiểm tra

# 7. Tap + xem kết quả (before/after + diff)
python workflow/emu_tool.py tap --pos 480,270 --wait 3
# → Output: change_pct = % pixel changed → biết tap có effect hay không
```

### Troubleshooting Decision Tree

```
Function failed?
│
├─ State detection sai?
│   └─ emu_tool.py state -v → check state
│   └─ emu_tool.py match -t template → check confidence
│   └─ Template not matching → emu_tool.py crop → crop lại
│
├─ Tap miss?
│   └─ emu_tool.py tap --pos x,y → check change_pct
│   └─ change_pct ≈ 0% → sai vị trí → emu_tool.py grid → tìm lại
│   └─ Dùng emu_tool.py locate thay vì hardcode
│
├─ Popup bất ngờ?
│   └─ emu_tool.py screenshot → xem popup
│   └─ emu_tool.py crop --region → crop header → register template
│
├─ Timeout?
│   └─ Game lag → tăng --wait
│   └─ emu_tool.py state → wrong expected state?
│
└─ Recovery failed?
    └─ back_to_lobby() stuck → emu_tool.py state → diagnose
```

### Output Format

Mỗi command output JSON trên dòng `[RESULT]`:
```
[RESULT] {"found": true, "x": 450, "y": 410, "confidence": 0.9523}
```
AI parse dòng `[RESULT]` để lấy data tự động.

Debug images luôn ở `workflow/_debug/` — **tự dọn khi xong**.

---

## 8. Coding Standards

### Naming Conventions

```python
# Function names: snake_case, verb first
def go_to_alliance(serial, detector) -> bool:
def collect_daily_rewards(serial, detector) -> bool:
def research_technology(serial, detector, tech_name) -> bool:

# Template IDs: SCREAMING_SNAKE_CASE
"POLICY_ENACT_BTN", "ALLIANCE_WAR", "RESEARCH_CENTER"

# Print format: always include serial
print(f"[{serial}] [MODULE] Message...")
```

### Return Types

```python
# Simple action → bool
def alliance_help(serial, detector) -> bool:
    return True   # success
    return False  # failed

# Action with dynamic cooldown → dict
def go_to_farming(serial, detector) -> dict:
    return {"ok": True, "dynamic_cooldown_sec": 12000}
    return {"ok": False}
```

### Error Handling Pattern

```python
def new_function(serial, detector) -> bool:
    # 1. Navigate to base state
    if not core_actions.back_to_lobby(serial, detector):
        return False

    # 2. Navigate to target
    adb_helper.tap(serial, x, y)
    state = core_actions.wait_for_state(serial, detector, ["TARGET"], timeout_sec=10)
    if not state:
        print(f"[{serial}] Failed to reach TARGET")
        return False

    # 3. Find button (retry 3x)
    match = None
    for attempt in range(3):
        match = detector.check_activity(serial, target="BUTTON", threshold=0.85)
        if match:
            break
        time.sleep(2)

    if not match:
        print(f"[{serial}] BUTTON not found")
        adb_helper.press_back(serial)
        return False

    # 4. Tap + verify
    _, bx, by = match
    adb_helper.tap(serial, bx, by)
    time.sleep(2)

    # 5. Check result
    result_state = detector.check_state(serial)
    if result_state != "EXPECTED":
        print(f"[{serial}] Unexpected state: {result_state}")
        return False

    return True
```

---

## 9. Existing Workflows Reference

| File | Chức năng | Entry function |
|------|-----------|----------------|
| `train_troops.py` | Huấn luyện quân | `train_troops()` |
| `farming_workflow.py` | Farm tài nguyên | `go_to_farming()` |
| `alliance_help_workflow.py` | Alliance help | `alliance_help()` |
| `alliance_war_workflow.py` | Alliance war | `alliance_war()` |
| `troop_healing_workflow.py` | Chữa thương | `heal_troops()` |
| `claim_mail_reward.py` | Nhận mail | `claim_mail()` |
| `tavern_chest_workflow.py` | Mở rương tavern | `tavern_chest()` |
| `pet_workflow.py` | Pet farming | `pet_workflow()` |
| `swap_account_workflow.py` | Đổi account | `swap_account()` |
| `policy/engine.py` | Season Policies V3 | `PolicyV3Engine.run()` |
| `festival_of_fortitude_workflow.py` | Festival event | `festival_workflow()` |

---

## 10. Developer Tools

| Tool | Path | Dùng khi nào |
|------|------|-----------|
| **`emu_tool.py`** | `workflow/` | **ALL-IN-ONE**: screenshot, grid, crop, locate, pixel, state, match, tap |
| `tool_app_guardian_cli.py` | `tool/` | Monitor app crash |
| `live_tracker_cli.py` | `tool/` | Track toạ độ real-time (interactive, dùng bằng tay) |

---

## 11. Terminal & Command Rules (Windows PowerShell)

> **AI agent PHẢI tuân thủ rules này** khi chạy terminal commands.
> Mục đích: chạy 1 lần ăn luôn, KHÔNG retry.

### 11.1 Golden Rule: Viết script file thay vì one-liner phức tạp

```
❌ SAI: Chạy Python one-liner dài với quotes lồng nhau
   python -c "from x import y; print(f'val={y(\"arg\")}')"

✅ ĐÚNG: Viết vào file .py rồi chạy
   1. Tạo file /tmp/test_xyz.py
   2. python /tmp/test_xyz.py
   3. Xoá file sau khi xong
```

**Ngưỡng**: Nếu command > 100 ký tự hoặc có quotes lồng → **PHẢI viết file**.

### 11.2 PowerShell Pitfalls (Phải nhớ)

| Pitfall | Sai | Đúng |
|---------|-----|------|
| String quotes | `python -c "print('he said "hi"')"` | Viết file `.py` |
| Path separator | `workflow\policy\data.py` | `workflow/policy/data.py` hoặc dùng raw string |
| Multi-line | `python -c "line1\nline2"` | Viết file `.py` |
| Pipe + grep | `cmd | grep pattern` | `cmd | Select-String pattern` |
| Semicolons | `cmd1; cmd2` (unreliable) | Dùng newlines hoặc `&&` |
| UTF-8 output | Lỗi encoding | Thêm `$OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8` |

### 11.3 Python CLI Patterns (An toàn)

```powershell
# Simple import test — OK as one-liner
python -c "from workflow.policy.data import COLUMNS; print(len(COLUMNS))"

# Anything complex — WRITE FILE
# Tạo file test → chạy → xoá
```

### 11.4 emu_tool.py — Dùng thay CLI phức tạp

Thay vì viết Python screencap code trong terminal:
```powershell
# ❌ SAI: Python one-liner với subprocess, cv2, numpy
python -c "import cv2, numpy as np, subprocess; ..."

# ✅ ĐÚNG: Dùng emu_tool
python workflow/emu_tool.py screenshot
python workflow/emu_tool.py crop --region 100,50,300,200 -o template.png
python workflow/emu_tool.py locate -t template.png
```

### 11.5 File Operations (PowerShell)

```powershell
# Copy file
Copy-Item "source.png" "workflow/templates/category/name.png"

# Move file
Move-Item "old.py" "new.py"

# Delete file
Remove-Item "temp.png" -Force

# Create directory
New-Item -ItemType Directory -Path "workflow/templates/new_category" -Force

# List files
Get-ChildItem "workflow/templates" -Recurse -Filter "*.png" | Select Name, Length
```

---

## 12. Template Auto-Capture Workflow

> AI PHẢI tự crop template từ emulator screenshot.
> KHÔNG yêu cầu user tự crop và copy file.

### 12.1 Quy trình đầy đủ (AI tự làm)

```bash
# Bước 1: Chụp + xem grid
python workflow/emu_tool.py grid --size 25
# → Mở _debug/grid.png → xác định vùng (x1, y1, x2, y2)

# Bước 2: Crop trực tiếp vào templates folder
python workflow/emu_tool.py crop --region 400,390,500,420 -o workflow/templates/category/button_name.png
# → Kiểm tra _debug/crop_overlay.png xem crop đúng chưa

# Bước 3: Verify match
python workflow/emu_tool.py match -t workflow/templates/category/button_name.png
# → Xem confidence ≥ 0.85?

# Bước 4: Register vào state_detector.py
# Thêm vào dict phù hợp: "category/button_name.png": "BUTTON_NAME",
```

### 12.2 Best Practices cho Crop

| Rule | Mô tả |
|------|-------|
| **Crop tight** | Cắt sát viền element, không lấy quá nhiều background |
| **Unique region** | Chọn vùng ĐẶC TRƯNG nhất (text, icon shape, color) |
| **Avoid dynamic** | KHÔNG crop vùng có số thay đổi (timer, resource count) |
| **Grayscale check** | Template matching dùng grayscale → đảm bảo contrast đủ |
| **Size nhỏ** | Template nhỏ hơn = match nhanh hơn + ít false positive |
| **Test nhiều state** | Crop xong → test trên nhiều screen states để đảm bảo không false positive |

### 12.3 Crop Size Guide

| Element | Recommended Size | Ví dụ |
|---------|-----------|-------|
| Button text | 60-120 x 15-25 px | "ENACT", "GO", "SELECT" |
| Screen header | 100-200 x 20-35 px | "SEASON POLICIES", "GOVERNANCE" |
| Icon/symbol | 30-60 x 30-60 px | building icons, star markers |
| Full button | 80-150 x 25-40 px | button with border + text |

### 12.4 Verify Template Quality

```bash
# Test trên screen hiện tại (phải đang ở đúng screen)
python workflow/emu_tool.py match -t workflow/templates/category/new.png --thresholds 0.7,0.8,0.85,0.9,0.95

# Kết quả mong muốn:
#   0.70 → ✅ (OK)
#   0.80 → ✅ (OK)
#   0.85 → ✅ (phải match ở mức này)
#   0.90 → ✅ (tốt nhất)
#   0.95 → ❌ (quá strict, bình thường)

# Nếu confidence < 0.80:
# → Template crop sai hoặc background quá nhiều
# → Crop lại nhỏ hơn, tập trung vào text/icon
```

### 12.5 Ví dụ: Crop button "ENACT" từ policy popup

```bash
# 1. Navigate đến screen có button
python workflow/emu_tool.py state    # verify đang ở policy screen

# 2. Grid screenshot
python workflow/emu_tool.py grid --size 10
# → Thấy "ENACT" tại khoảng x:430-510, y:395-415

# 3. Crop
python workflow/emu_tool.py crop --region 430,395,510,415 -o workflow/templates/policy/enact_btn.png

# 4. Verify
python workflow/emu_tool.py match -t workflow/templates/policy/enact_btn.png
# → confidence=0.97 ✅

# 5. Register vào state_detector.py
# "policy/enact_btn.png": "POLICY_ENACT_BTN",
```

---

## 13. Documentation & Merge Guide (PHẢI viết cho mỗi function mới)

> Khi implement xong function mới, AI PHẢI tạo 2 file:
> 1. **Guide** cho user/dev hiểu cách dùng
> 2. **Merge Guide** cho dev merge vào main branch

### 13.1 Guide File — `guide_xxx.md`

Đặt tại: `workflow/NEW_TASKS-MODIFY_TASKS/guide_xxx.md`

**Format chuẩn:**

```markdown
# Guide: [Tên Feature] — [Version]

Mô tả ngắn về feature.

---

## 1. Tổng Quan
- Bài toán feature giải quyết
- Flow diagram hoặc state machine

## 2. Files Liên Quan
| File | Vai trò |
|------|---------|
| `core_actions.py` | Chứa logic chính |
| `xxx_workflow.py` | Runner script |
| `templates/xxx/` | Template images |

## 3. Cách Sử Dụng
- Command chạy
- Params cần config
- Expected output

## 4. Cấu Hình (nếu có)
- Config files, JSON data, constants

## 5. Edge Cases & Xử Lý
| Case | Xử lý |
|------|-------|
| Resource hết | Return False |
| Popup bất ngờ | Close + retry |

## 6. Troubleshooting
- Lỗi thường gặp + cách fix
```

### 13.2 Merge Guide — `MERGE_GUIDE_xxx.md` (Python format)

Đặt tại: `workflow/MERGE_GUIDE_XXX.md`

> File này là **Python executable** — chạy được để in checklist.

**10 Sections bắt buộc:**

```python
# -*- coding: utf-8 -*-
# [FEATURE NAME] — MERGE GUIDE
# Ngày tạo: YYYY-MM-DD

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ============================
# 1. FILE WORKFLOW MỚI
# ============================
WORKFLOW_FILES = [
    "workflow/xxx_workflow.py",
]

# ============================
# 2. HÀM MỚI TRONG core_actions.py
# ============================
CORE_ACTIONS_NEW_FUNCTIONS = {
    "function_name": {
        "called_by": "xxx_workflow.py",
        "description": "Mô tả ngắn",
        "depends_on_functions": ["back_to_lobby", "wait_for_state"],
        "depends_on_templates": ["TEMPLATE_ID_1", "TEMPLATE_ID_2"],
        "status": "Hoàn chỉnh / Placeholder / Stub",
    },
}

# ============================
# 3. HẰNG SỐ MỚI TRONG core_actions.py
# ============================
CORE_ACTIONS_NEW_CONSTANTS = {
    "CONSTANT_NAME": {
        "description": "Mô tả",
        "value": {...},
    },
}

# ============================
# 4. HÀM CŨ BẮT BUỘC PHẢI CÓ
# ============================
COMMON_REQUIRED_FUNCTIONS = [
    "startup_to_lobby",
    "wait_for_state",
    "back_to_lobby",
]

# ============================
# 5. THAY ĐỔI TRONG state_detector.py
# ============================
STATE_DETECTOR_CHANGES = {
    "construction_configs": {
        "NEW_ENTRIES": {
            '"category/file.png": "STATE_NAME"': "Mô tả",
        },
    },
    "activity_configs": {
        "NEW_ENTRIES": {
            '"category/btn.png": "BUTTON_NAME"': "Mô tả",
        },
    },
    "special_configs": {
        "NEW_ENTRIES": {},
    },
}

# ============================
# 6. TEMPLATE FILES CẦN TẠO
# ============================
TEMPLATE_FILES = {
    "EXISTING": ["templates/xxx/existing.png"],
    "NEED_CAPTURE": [
        {
            "path": "templates/xxx/new_btn.png",
            "used_by": "function_name()",
            "description": "Nút XYZ trên screen ABC",
            "priority": "CAO/TRUNG BÌNH/THẤP",
        },
    ],
}

# ============================
# 7. IMPORT MỚI
# ============================
NEW_IMPORTS_IN_CORE_ACTIONS = [
    "import xxx",
]

# ============================
# 8. SƠ ĐỒ PHỤ THUỘC
# ============================
DEPENDENCY_MAP = """
xxx_workflow.py
  │
  ├── core_actions.startup_to_lobby()   ← có sẵn
  ├── core_actions.back_to_lobby()      ← có sẵn
  │
  └── core_actions.new_function()       ← MỚI
        ├── detector.check_state()
        ├── detector.check_activity("TEMPLATE_ID")
        │     └── templates/xxx/btn.png     ← CẦN CHỤP
        └── adb_helper.tap()
"""

# ============================
# 9. CHECKLIST MERGE
# ============================
MERGE_CHECKLIST = """
+==============================================================+
|                    MERGE CHECKLIST                            |
+==============================================================+
|  [ ] 1. core_actions.py                                      |
|     [ ] Thêm hàm: new_function()                            |
|     [ ] Thêm hằng số: CONSTANT_NAME                         |
|  [ ] 2. state_detector.py                                    |
|     [ ] activity_configs: thêm xxx/btn.png                   |
|  [ ] 3. Template files                                       |
|     [ ] Chụp & đặt: templates/xxx/btn.png                    |
|  [ ] 4. Workflow file                                        |
|     [ ] Copy: xxx_workflow.py                                |
|  [ ] 5. Test thực tế                                         |
|     [ ] Chạy: python xxx_workflow.py emulator-5568           |
+==============================================================+
"""

# ============================
# 10. GHI CHÚ KỸ THUẬT
# ============================
TECHNICAL_NOTES = """
- Tọa độ dùng resolution 960×540
- ...
"""

if __name__ == "__main__":
    print(MERGE_CHECKLIST)
    print("\n=== DEPENDENCY MAP ===")
    print(DEPENDENCY_MAP)
```

### 13.3 Mandatory Deliverables Checklist

Khi implement function mới xong, AI PHẢI tạo:

| # | Deliverable | File | Bắt buộc |
|---|------------|------|----------|
| 1 | Function code | `core_actions.py` | ✅ |
| 2 | Templates | `templates/category/*.png` | ✅ |
| 3 | State detector entries | `state_detector.py` | ✅ |
| 4 | Workflow runner script | `tasks/xxx_workflow.py` | ✅ |
| 5 | **User guide** | `NEW_TASKS-MODIFY_TASKS/guide_xxx.md` | ✅ |
| 6 | **Merge guide** | `MERGE_GUIDE_XXX.md` | ✅ |
| 7 | Test script | `tasks/test_xxx.py` | Nên có |

### 13.4 Existing Merge Guides (tham khảo)

| File | Feature | Sections |
|------|---------|----------|
| `MERGE_GUIDE.md` | 5 workflows (tavern, heal, darkling, alliance, chat) | 8 sections |
| `MERGE_GUIDE_FESTIVAL.md` | Festival of Fortitude | 10 sections + dependency map |
| `MERGE_GUIDE_LEGION.md` | Legion management | 10 sections |
| `MERGE_GUIDE_RSS_CENTER.md` | RSS Center farm | 10 sections |

---

## 14. Critical Reminders for AI Agent

1. **Resolution: 960×540** — Tất cả toạ độ dùng resolution này
2. **Emulator serial format**: `emulator-5568` (port-based)
3. **Game package**: `com.farlightgames.samo.gp.vn`
4. **KHÔNG BAO GIỜ** tap mù (hard-code coordinates without verify)
5. **LUÔN** chụp screenshot trước và sau mỗi action khi debug
6. **LUÔN** check state sau khi navigate
7. **LUÔN** retry 3 lần trước khi fail
8. **LUÔN** dùng `back_to_lobby()` để recover khi stuck
9. **KHÔNG** dùng vòng lặp vô hạn
10. Template matching dùng **grayscale**, threshold mặc định **0.85**
11. Debug images lưu `workflow/_debug/`, **dọn dẹp sau khi xong**
12. Mọi function PHẢI có `serial: str` và `detector: GameStateDetector` params
13. **Command > 100 chars → viết file .py**, KHÔNG chạy one-liner phức tạp
14. **Template tự crop** bằng `emu_tool.py crop`, KHÔNG yêu cầu user crop
15. **CWD cho tất cả commands**: `f:\COD_CHECK\Part3_Control_EMU`

