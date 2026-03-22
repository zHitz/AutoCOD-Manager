# Hướng Dẫn Viết Workflow Function — core_actions.py

> **Đối tượng:** Dev viết/sửa function trong `core_actions.py`
> **Mục đích:** Đảm bảo mọi workflow function đều robust, chống bot-detection, và dễ debug.
> **Tham khảo thêm:** `error_code_architecture.md` (error codes), `DYNAMIC_COOLDOWN.md` (cooldown system)

---

## 1. Nguyên Tắc Vàng

### 1.1 KHÔNG BAO GIỜ tap mù

```python
# ❌ SAI — tap rồi sleep cố định, không verify
adb_helper.tap(serial, 42, 422)
time.sleep(3)
# tiếp tục code... (giả định UI đã đổi)

# ✅ ĐÚNG — tap → delay → verify UI đã đổi
adb_helper.tap(serial, 42, 422)
_human_delay(1.5)
panel = _detect_with_retry(serial, detector, "FARM_SEARCH_BTN", threshold=0.8, attempts=3, delay=1)
if not panel:
    print(f"[{serial}] [FAILED] Panel did not open.")
    return _fail("ACTION_TAP_NO_RESPONSE: Search panel did not open")
```

**Quy tắc:** Sau MỖI tap quan trọng → phải verify bằng template detection hoặc `wait_for_state`.

### 1.2 KHÔNG dùng `time.sleep()` trực tiếp

```python
# ❌ SAI — delay cố định, dễ bị phát hiện bot
time.sleep(3)

# ✅ ĐÚNG — delay ngẫu nhiên ±40%
_human_delay(2)  # thực tế sleep 1.2s ~ 2.8s
```

### 1.3 KHÔNG dùng `if not result` cho dict

```python
# ❌ SAI — dict luôn truthy, sẽ KHÔNG bắt được fail
if not back_to_lobby(serial, detector):
    return _fail("...")

# ✅ ĐÚNG — dùng _is_ok()
if not _is_ok(back_to_lobby(serial, detector)):
    return _fail("...")
```

---

## 2. Cấu Trúc Chuẩn Của 1 Workflow Function

Mọi workflow function PHẢI tuân theo cấu trúc sau:

```python
def my_workflow(serial: str, detector: GameStateDetector, param: str = "default") -> dict:
    """
    Mô tả workflow:
    1. Step 1: Navigate
    2. Step 2: Action
    3. Step 3: Verify
    ...
    """
    print(f"[{serial}] === MY WORKFLOW ===")

    # ── Phase 1: Navigate ──
    result = back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (IN_CITY)")
    if not _is_ok(result):
        return _bubble(result, "NAV_LOBBY_UNREACHABLE: Could not reach lobby")

    # ── Phase 2: Action + Verify ──
    print(f"[{serial}] Tapping button...")
    adb_helper.tap(serial, x, y)
    _human_delay(1.5)

    match = _detect_with_retry(serial, detector, "TARGET_TEMPLATE", threshold=0.8, attempts=3, delay=1)
    if not match:
        return _fail("ACTION_TAP_NO_RESPONSE: Target did not appear")

    # ── Phase 3: Return ──
    return _ok()
    # hoặc: return _ok(dynamic_cooldown_sec=21600)
```

---

## 3. API Reference — Các Hàm Helper Bắt Buộc

### 3.1 Return Helpers

| Hàm | Dùng khi | Output |
|-----|----------|--------|
| `_ok()` | Thành công | `{"ok": True}` |
| `_ok(dynamic_cooldown_sec=N)` | Thành công + set cooldown | `{"ok": True, "dynamic_cooldown_sec": N}` |
| `_fail("CODE: message")` | Thất bại | `{"ok": False, "error": "CODE: message"}` |
| `_fail("CODE: msg", dynamic_cooldown_sec=N)` | Fail nhưng đã commit action | `{"ok": False, "error": "...", "dynamic_cooldown_sec": N}` |
| `_is_ok(result)` | Check kết quả (bool hoặc dict) | `True` / `False` |
| `_bubble(result, "FALLBACK: msg")` | Forward error từ child lên | dict gốc hoặc dict mới |

### 3.2 Delay Helpers

| Hàm | Dùng khi | Behavior |
|-----|----------|----------|
| `_human_delay(base_sec, variance=0.4)` | Thay thế `time.sleep()` | Sleep `base_sec ± 40%`, min 0.5s |

**Bảng delay khuyến nghị:**

| Action | Delay (giây) | Lý do |
|--------|-------------|-------|
| Mở menu/popup nhỏ | 1.0 - 1.5 | Popup load nhanh |
| Chuyển tab | 1.0 | Chỉ switch UI |
| Search/Navigate (map pan) | 2.0 - 3.0 | Camera pan animation |
| Load screen mới | 2.0 | Cần render full |
| Sau dispatch/confirm | 2.0 | Wait server response |
| Giữa các retry | 1.0 | Đủ cho UI settle |

> **⚠️ QUAN TRỌNG:** Delay quá lớn (>5s) vừa chậm vừa vô nghĩa. Delay quá nhỏ (<0.5s) sẽ tap trước khi UI kịp render.

### 3.3 Detection Helpers

| Hàm | Dùng khi | Behavior |
|-----|----------|----------|
| `_detect_with_retry(serial, detector, "TPL", threshold=0.8, attempts=3, delay=1)` | Detect template có retry | Return `(name, x, y)` hoặc `None` |
| `detector.check_activity(serial, target="TPL", threshold=0.8)` | Detect 1 lần không retry | Return `(name, x, y)` hoặc `None` |
| `detector.check_special_state(serial, target="TPL")` | Check special state (popup) | Return match hoặc `None` |
| `wait_for_state(serial, detector, ["STATE_A"], timeout_sec=10, check_mode="state")` | Chờ đến khi đúng state | Return state name hoặc `None` |

> **Lưu ý:** Trước khi gọi `check_activity` hoặc `check_special_state`, nếu cần screenshot mới thì set `detector._screen_cache = None`.

---

## 4. Patterns Bắt Buộc

### 4.1 Pattern: Tap → Verify → Act

Mọi bước quan trọng đều phải theo pattern này:

```python
# Step: Open search panel
adb_helper.tap(serial, 42, 422)
_human_delay(1.5)

panel = _detect_with_retry(serial, detector, "FARM_SEARCH_BTN", threshold=0.8, attempts=3, delay=1)
if not panel:
    # Handle failure
    adb_helper.press_back(serial)
    return _fail("ACTION_TAP_NO_RESPONSE: Search panel did not open")

# Panel confirmed → safe to continue
```

### 4.2 Pattern: Fallback / Edge Case Handling

Khi 1 action fail, CÓ THỂ thử phương án B thay vì return fail ngay:

```python
# Tìm mine gold — không có → thử loại khác
search_btn = detector.check_activity(serial, target="FARM_SEARCH_BTN", threshold=0.8)
if search_btn:
    # No mine for current type → try alternatives
    ALL_TYPES = ["gold", "wood", "stone", "mana"]
    fallback_found = False

    for alt_type in ALL_TYPES:
        if alt_type == current_type:
            continue
        # Tap alt type → search → check
        adb_helper.tap(serial, RESOURCE_TAPS[alt_type][0], RESOURCE_TAPS[alt_type][1])
        _human_delay(1)
        adb_helper.tap(serial, SEARCH_TAPS[alt_type][0], SEARCH_TAPS[alt_type][1])
        _human_delay(3)

        detector._screen_cache = None
        still_open = detector.check_activity(serial, target="FARM_SEARCH_BTN", threshold=0.8)
        if not still_open:
            current_type = alt_type
            fallback_found = True
            break

    if not fallback_found:
        return _fail("RESOURCE_INSUFFICIENT: No mines available for any resource type")
```

### 4.3 Pattern: Loop với Max Retries

Khi cần lặp action nhiều lần (dispatch, upgrade...):

```python
MAX_ITERATIONS = 5

for idx in range(MAX_ITERATIONS):
    print(f"[{serial}] --- Attempt #{idx + 1} ---")

    # ... do action ...

    # Break conditions
    if no_more_slots:
        print(f"[{serial}] All slots used. Done.")
        break

    if error_occurred:
        print(f"[{serial}] Error at attempt #{idx + 1}. Stopping.")
        break

# After loop — always cleanup
adb_helper.press_back(serial)
_human_delay(1)
return _ok()
```

### 4.4 Pattern: Navigate → Verify State

Bắt buộc verify state sau navigation:

```python
result = go_to_construction(serial, detector, "RESEARCH_CENTER")
if not _is_ok(result):
    return _bubble(result, "NAV_TARGET_NOT_REACHED: Could not reach Research Center")

# PHẢI verify state, không giả định navigation thành công
state = wait_for_state(serial, detector, ["RESEARCH_CENTER"], timeout_sec=10, check_mode="construction")
if state != "RESEARCH_CENTER":
    return _fail("STATE_WRONG_SCREEN: Expected RESEARCH_CENTER")
```

### 4.5 Pattern: Detect Click Coordinate từ Template

Dùng tọa độ detect được thay vì hardcode:

```python
# ❌ SAI — hardcode tọa độ
adb_helper.tap(serial, 658, 394)  # "Gather button"

# ✅ ĐÚNG — detect rồi tap vào tọa độ trả về
gather_btn = _detect_with_retry(serial, detector, "RSS_GATHER", threshold=0.8, attempts=3, delay=1)
if not gather_btn:
    return _fail("TEMPLATE_NO_MATCH: Gather button not found")
_, gx, gy = gather_btn
adb_helper.tap(serial, gx, gy)
```

> **Ngoại lệ:** Có thể hardcode coordinate cho các vị trí CỐ ĐỊNH không bao giờ thay đổi
> (ví dụ: icon góc màn hình, tab bar, preset slot). Nhưng PHẢI comment rõ ràng.

---

## 5. Checklist Trước Khi Submit

Dùng checklist này cho MỖI function mới hoặc sửa:

### Code Quality
- [ ] Return type là `-> dict`, dùng `_ok()` / `_fail("CODE: msg")`
- [ ] Mọi child function check bằng `_is_ok()`, không `if not result`
- [ ] Error code theo format `CATEGORY_REASON` (xem `error_code_architecture.md`)
- [ ] Print log rõ ràng cho mỗi step: `[{serial}] Step description...`

### Anti-Detection
- [ ] KHÔNG có `time.sleep()` trực tiếp — chỉ dùng `_human_delay()`
- [ ] Delay hợp lý (1-3s), không quá lớn (>5s) hoặc quá nhỏ (<0.5s)

### Screen Verification
- [ ] Sau mỗi tap quan trọng → verify bằng template hoặc `wait_for_state`
- [ ] Dùng `_detect_with_retry()` thay vì single detect cho UI elements quan trọng
- [ ] Set `detector._screen_cache = None` trước khi detect lại (nếu cần fresh frame)

### Edge Cases
- [ ] Handle "không tìm thấy target" → press_back + return _fail
- [ ] Handle "action committed nhưng verify fail" → return _fail với dynamic_cooldown
- [ ] Handle "resource exhausted" → thử fallback nếu có ý nghĩa
- [ ] Handle "tab/state bị swap" → detect đúng state mới

### Dynamic Cooldown
- [ ] Nếu action thành công và có timer → `return _ok(dynamic_cooldown_sec=N)`
- [ ] Nếu resource maxed/exhausted → `return _ok(dynamic_cooldown_sec=N)` (vẫn OK, chỉ chờ lâu hơn)
- [ ] Nếu fail nhưng đã commit action → `return _fail("...", dynamic_cooldown_sec=N)`

---

## 6. Template Mới — Từ A đến Z

### 6.1 Tạo Template Image

1. **Crop screenshot** — dùng `tool_region_selector.py` hoặc Photoshop
2. **Lưu vào thư mục** — `backend/core/workflow/templates/<category>/<name>.png`
3. **Đặt tên rõ ràng** — `research_confirm.png`, `farm_search_btn.png`
4. **Kích thước nhỏ** — crop đúng vùng UI element, không quá lớn

### 6.2 Đăng Ký Template

Mở `state_detector.py`, thêm vào đúng section:

```python
# Activity templates (buttons, actions)
self.activity_configs = {
    "research/research_confirm.png": "RESEARCH_CONFIRM",
    ...
}

# Special templates (popups, warnings)
self.special_configs = {
    "research/research_no_resource.png": "RESEARCH_NO_RESOURCE",
    ...
}

# State templates (screens, menus)
self.state_configs = {
    "lobby_city.png": "IN-GAME LOBBY (IN_CITY)",
    ...
}

# Construction templates
self.construction_configs = {
    "construction/barracks.png": "BARRACKS",
    ...
}
```

| Config | Detect bằng | Dùng cho |
|--------|------------|----------|
| `state_configs` | `detector.check_state()` | Xác định đang ở screen nào |
| `construction_configs` | `detector.check_construction()` | Xác định building nào |
| `activity_configs` | `detector.check_activity(target=)` | Detect buttons, tìm vị trí |
| `special_configs` | `detector.check_special_state(target=)` | Detect popups, warnings |

### 6.3 ROI (Region of Interest)

Nếu template chỉ xuất hiện ở 1 vùng cố định, đăng ký ROI để tránh false positive:

```python
self.custom_rois = {
    "pets/Auto-capture_in_progress.png": (305, 411, 761, 509),
    # format: (x1, y1, x2, y2) — chỉ scan vùng này
}
```

---

## 7. Viết Test File

Mỗi workflow function NÊN có test file tương ứng theo pattern:

```
backend/core/test_farming.py     → test go_to_farming
backend/core/test_research.py    → test research_technology
backend/core/test_construction.py → test upgrade_construction
```

### Structure chuẩn:

```python
import os, sys, time, cv2, argparse

# Path setup
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(root_dir)
from backend.config import config
config.load()
from backend.core.workflow.state_detector import GameStateDetector
from backend.core.workflow import core_actions
import adb_helper

DEBUG_DIR = os.path.join(os.path.dirname(__file__), "debug_<workflow>")

def save_frame(serial, detector, label):
    os.makedirs(DEBUG_DIR, exist_ok=True)
    frame = detector.get_frame(serial)
    if frame is None: return
    path = os.path.join(DEBUG_DIR, f"{time.strftime('%Y%m%d_%H%M%S')}_{label}.png")
    cv2.imwrite(path, frame)
    print(f"[{serial}] [DEBUG] Saved: {path}")

# Test functions...
def test_full_workflow(serial, param="default"):
    """End-to-end test."""
    ...

def test_specific_step(serial):
    """Test 1 step cụ thể."""
    ...

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("test", choices=["full", "step1", "all"])
    parser.add_argument("--serial", default="emulator-5556")
    args = parser.parse_args()
    ...
```

### Các test nên có:

| Test | Mô tả |
|------|--------|
| `test_full_<workflow>` | Chạy full E2E workflow |
| `test_<specific_step>` | Test 1 bước quan trọng (navigation, detection...) |
| `test_<edge_case>` | Test edge case (no resource, tab maxed...) |
| `test_template_detection` | Scan tất cả template liên quan |

### Chạy test:

```bash
# Full workflow
python backend/core/test_farming.py full --serial emulator-5568 --resource gold

# Specific test
python backend/core/test_research.py templates --serial emulator-5568

# All tests
python backend/core/test_farming.py all --serial emulator-5568
```

---

## 8. Ví Dụ Tham Khảo

| Function | File | Đặc điểm |
|----------|------|-----------|
| `go_to_farming` | core_actions.py | Loop dispatch, fallback resource type, template-based detect |
| `research_technology` | core_actions.py | Tab verification, no-resource handling, alliance help |
| `upgrade_construction` | core_actions.py | Recursive upgrade, fallback constructions, GO button path |
| `process_season_policies` | core_actions.py | PolicyV3Engine delegation, dynamic cooldown on lock |
| `back_to_lobby` | core_actions.py | State machine loop, special screen handling |

---

## 9. Tóm Tắt Nhanh

```
┌──────────────────────────────────────────────────────────────────┐
│ WORKFLOW FUNCTION CHEAT SHEET                                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Structure:                                                       │
│   1. Navigate (back_to_lobby / go_to_construction)               │
│   2. Verify state (wait_for_state / _detect_with_retry)          │
│   3. Action + Verify each step                                   │
│   4. Handle edge cases (fallback, retry)                         │
│   5. Return _ok() or _fail("CODE: message")                     │
│                                                                  │
│ Delay: _human_delay(1-3s), KHÔNG time.sleep()                   │
│ Detect: _detect_with_retry() cho buttons quan trọng              │
│ Return: _ok() | _fail("CODE: msg") | _bubble(result, "CODE")    │
│ Check:  _is_ok(result), KHÔNG "if not result"                   │
│ Cache:  detector._screen_cache = None trước detect mới           │
│                                                                  │
│ Anti-Detection:                                                  │
│   ✓ Random delay (±40%)                                         │
│   ✓ Verify trước khi act                                        │
│   ✓ Detect coordinate thay vì hardcode                          │
│   ✓ Fallback khi resource exhausted                             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```
