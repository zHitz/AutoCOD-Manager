# Error Code Architecture — core_actions.py

Tài liệu chuẩn hóa error code cho tất cả hàm `core_actions.py`.  
**Mục đích:** Dev dùng doc này để refactor `return False` → `return {"ok": False, "error": "..."}` theo format đồng bộ.

---

## 1. Error Code Format

```
<CATEGORY>_<SPECIFIC_REASON>
```

| Phần | Mô tả | Ví dụ |
|------|--------|-------|
| `CATEGORY` | Loại lỗi (xem bảng dưới) | `NAV`, `TIMEOUT`, `STATE` |
| `SPECIFIC_REASON` | Lý do cụ thể | `LOBBY_UNREACHABLE`, `TEMPLATE_MISSING` |

**Error message = Error code + mô tả ngắn:**

```python
return {"ok": False, "error": "NAV_LOBBY_UNREACHABLE: Could not reach lobby within 30s"}
#       ↑ bool        ↑ code: NAV_LOBBY_UNREACHABLE
#                     ↑ message: mô tả cho dev/UI đọc
```

---

## 2. Error Categories

| Code Prefix | Category | Khi nào dùng | Severity |
|-------------|----------|-------------|----------|
| `NAV_` | Navigation | Không thể navigate đến đúng screen/menu | 🟡 Medium |
| `STATE_` | State Mismatch | Game state không đúng expected | 🟡 Medium |
| `TIMEOUT_` | Timeout | Chờ quá lâu không có response | 🟠 High |
| `TEMPLATE_` | Template Match | Template image không match / không tìm thấy | 🟡 Medium |
| `OCR_` | OCR / Text | Đọc text, timer, số bị fail | 🟢 Low |
| `RESOURCE_` | Resource | Không đủ resource, slot đầy, queue full | 🟢 Low |
| `CRASH_` | App Crash | Game crash, app not responding | 🔴 Critical |
| `CONFIG_` | Configuration | Config thiếu, sai param, data không hợp lệ | 🟡 Medium |
| `ACTION_` | Action Failed | Tap/swipe/interact fail, button not found | 🟡 Medium |
| `LOCK_` | Locked | Feature bị khóa, cooldown chưa hết | 🟢 Low |

---

## 3. Standard Error Codes

### NAV_ — Navigation Errors

| Error Code | Mô tả | Ví dụ hàm |
|-----------|-------|----------|
| `NAV_LOBBY_UNREACHABLE` | Không về được lobby | `back_to_lobby`, `startup_to_lobby` |
| `NAV_MENU_OPEN_FAILED` | Không mở được menu | `ensure_lobby_menu_open` |
| `NAV_TARGET_NOT_REACHED` | Không đến target screen | `go_to_construction`, `go_to_alliance` |
| `NAV_SWAP_FAILED` | Không swap được IN_CITY ↔ OUT_CITY | `back_to_lobby(target_lobby=...)` |
| `NAV_SCROLL_EXHAUSTED` | Scroll hết mà không tìm thấy target | `swap_account` |

### STATE_ — State Errors

| Error Code | Mô tả | Ví dụ hàm |
|-----------|-------|----------|
| `STATE_WRONG_SCREEN` | Đang ở sai screen | `go_to_construction` (not IN_CITY) |
| `STATE_UNEXPECTED` | State không nằm trong expected list | `wait_for_state` timeout |
| `STATE_STUCK` | State không thay đổi sau nhiều lần retry | `back_to_lobby` loop |

### TIMEOUT_ — Timeout Errors

| Error Code | Mô tả | Ví dụ hàm |
|-----------|-------|----------|
| `TIMEOUT_LOAD` | Game loading quá lâu | `startup_to_lobby` |
| `TIMEOUT_STATE_WAIT` | Chờ state change quá lâu | `wait_for_state` |
| `TIMEOUT_ACTION` | Action không phản hồi | `capture_pet`, `train_troops` |

### TEMPLATE_ — Template Matching Errors

| Error Code | Mô tả | Ví dụ hàm |
|-----------|-------|----------|
| `TEMPLATE_NOT_FOUND` | Template file không tồn tại | `_is_pet_slot_blank` |
| `TEMPLATE_NO_MATCH` | Template tồn tại nhưng không match screen | `go_to_farming` |
| `TEMPLATE_MULTI_MATCH` | Nhiều match không xác định được target | - |

### OCR_ — OCR / Text Errors

| Error Code | Mô tả | Ví dụ hàm |
|-----------|-------|----------|
| `OCR_READ_FAILED` | Không đọc được text/số | `research_technology` |
| `OCR_TIMER_INVALID` | Timer format không parse được | `go_to_rss_center_farm` |
| `OCR_VALUE_OUT_OF_RANGE` | Giá trị đọc được ngoài range hợp lệ | - |

### RESOURCE_ — Resource Errors

| Error Code | Mô tả | Ví dụ hàm |
|-----------|-------|----------|
| `RESOURCE_INSUFFICIENT` | Không đủ resource để thực hiện | `research_technology` |
| `RESOURCE_SLOT_FULL` | Không còn slot trống | `train_troops`, `check_builder_slots` |
| `RESOURCE_QUEUE_BUSY` | Queue đang chạy, không thể thêm | `research_technology` |

### CRASH_ — App Crash Errors

| Error Code | Mô tả | Ví dụ hàm |
|-----------|-------|----------|
| `CRASH_APP_DIED` | App bị tắt/crash giữa chừng | `check_app_crash` |
| `CRASH_LAUNCH_FAILED` | Không bật được app | `ensure_app_running` |
| `CRASH_ADB_DISCONNECTED` | ADB mất kết nối | - |

### CONFIG_ — Configuration Errors

| Error Code | Mô tả | Ví dụ hàm |
|-----------|-------|----------|
| `CONFIG_INVALID_PARAM` | Param không hợp lệ | `go_to_construction(name="???")` |
| `CONFIG_MISSING_DATA` | Thiếu data cần thiết | construction_data missing |

### ACTION_ — Action Errors

| Error Code | Mô tả | Ví dụ hàm |
|-----------|-------|----------|
| `ACTION_BUTTON_NOT_FOUND` | Button/UI element không tìm thấy | `alliance_help`, `claim_daily_chests` |
| `ACTION_TAP_NO_RESPONSE` | Tap xong nhưng không có phản hồi | - |
| `ACTION_VERIFY_FAILED` | Action đã thực hiện nhưng verify fail | `capture_pet`, `go_to_farming` |

### LOCK_ — Lock / Cooldown Errors

| Error Code | Mô tả | Ví dụ hàm |
|-----------|-------|----------|
| `LOCK_FEATURE_LOCKED` | Feature chưa unlock | - |
| `LOCK_COOLDOWN_ACTIVE` | Cooldown chưa hết | `research_technology` |
| `LOCK_PET_LOCKED` | Pet bị khóa không release được | `release_pet` |

---

## 4. Helper Functions (đã thêm vào `core_actions.py`)

4 helper functions sẵn sàng dùng — dev KHÔNG cần tự tạo:

```python
# ── Return helpers ──
_ok()                                    # → {"ok": True}
_ok(dynamic_cooldown_sec=12000)          # → {"ok": True, "dynamic_cooldown_sec": 12000}

_fail("NAV_LOBBY_UNREACHABLE: msg")      # → {"ok": False, "error": "NAV_LOBBY_UNREACHABLE: msg"}
_fail("RESOURCE_QUEUE_BUSY: msg",        # → {"ok": False, "error": "...",
      dynamic_cooldown_sec=600)          #    "dynamic_cooldown_sec": 600}

# ── Check helpers ──
_is_ok(result)    # True nếu result là True, hoặc dict có {"ok": True}
                  # False nếu result là False, hoặc dict có {"ok": False}
                  # AN TOÀN cho cả bool lẫn dict — thay thế "if not result"

_bubble(result, "FALLBACK_ERROR: msg")
                  # Nếu result là dict → trả nguyên dict (giữ error + cooldown)
                  # Nếu result là bool False → trả {"ok": False, "error": "FALLBACK_ERROR: msg"}
```

### ⚠️ Quy tắc quan trọng

```python
# ❌ SAI — dict luôn truthy, sẽ KHÔNG bắt được fail
if not back_to_lobby(serial, detector):
    return _fail("...")

# ✅ ĐÚNG — dùng _is_ok() để check
if not _is_ok(back_to_lobby(serial, detector)):
    return _fail("...")

# ✅ ĐÚNG — bubble up error từ child
result = back_to_lobby(serial, detector)
if not _is_ok(result):
    return _bubble(result, "NAV_LOBBY_UNREACHABLE: Could not reach lobby")
```

---

## 5. Return Templates

### Template 1: Simple function (không gọi child)

```python
def alliance_help(serial, detector) -> dict:
    # ... logic ...
    if not found_help_button:
        print(f"[{serial}] [FAILED] Help button not found")
        return _fail("ACTION_BUTTON_NOT_FOUND: Help button not found")

    return _ok()
```

### Template 2: Function gọi child function

```python
def train_troops(serial, detector, training_list=None) -> dict:
    # Step 1: Navigate (child function)
    result = back_to_lobby(serial, detector)
    if not _is_ok(result):
        return _bubble(result, "NAV_LOBBY_UNREACHABLE: Could not reach lobby")

    # Step 2: Open building (child function)
    result = go_to_construction(serial, detector, "barracks")
    if not _is_ok(result):
        return _bubble(result, "NAV_TARGET_NOT_REACHED: Could not open Barracks")

    # Step 3: Own logic
    if _is_queue_full(serial, detector):
        return _fail("RESOURCE_QUEUE_BUSY: Training queue is full")

    success = _do_training(serial, detector, training_list)
    if not success:
        return _fail("ACTION_TAP_NO_RESPONSE: Train button did not respond")

    return _ok()
```

### Template 3: Function với dynamic cooldown

```python
def go_to_farming(serial, detector, resource_type="wood") -> dict:
    result = back_to_lobby(serial, detector, target_lobby="OUT_CITY")
    if not _is_ok(result):
        return _bubble(result, "NAV_LOBBY_UNREACHABLE: Could not reach OUT_CITY")

    march_sent = _send_march(serial, detector, resource_type)
    if not march_sent:
        return _fail("ACTION_BUTTON_NOT_FOUND: Send march button not found")

    timer_sec = _read_march_timer(serial, detector)
    if timer_sec and timer_sec > 0:
        return _ok(dynamic_cooldown_sec=timer_sec + 300)

    return _ok()  # fallback static cooldown
```

### Template 4: Partial fail (action committed)

```python
def capture_pet(serial, detector) -> dict:
    result = go_to_capture_pet(serial, detector)
    if not _is_ok(result):
        return _bubble(result, "NAV_TARGET_NOT_REACHED: Could not reach capture screen")

    capture_started = _tap_capture_button(serial)
    if not capture_started:
        return _fail("ACTION_BUTTON_NOT_FOUND: Capture button not found")

    # Action committed → cần cooldown dù verify fail
    verified = _verify_capture(serial, detector)
    if not verified:
        return _fail("ACTION_VERIFY_FAILED: Capture started but verify failed",
                     dynamic_cooldown_sec=600)

    return _ok()
```

---

## 6. Migration Guide — `return False` → `return dict`

### Quy tắc

1. **Mỗi `return False` phải có error code** — không có ngoại lệ
2. **Error code phải unique cho từng failure point** — dev phải biết CHÍNH XÁC dòng nào fail
3. **Message ngắn gọn** — dưới 80 ký tự
4. **Dùng print log + error code** — print vẫn giữ cho terminal, error code cho UI
5. **Migrate cả cha lẫn con** — nếu fix hàm cha, fix luôn hàm con nó gọi

### Checklist cho dev

Với MỖI hàm trong `core_actions.py`:

- [ ] Thay return type annotation: `-> bool` → `-> dict`
- [ ] Thay `return True` → `return _ok()`
- [ ] Thay `return False` → `return _fail("<CODE>: <message>")`
- [ ] Thay `if not child_func()` → `if not _is_ok(child_func())`
- [ ] Dùng `_bubble(result, "...")` để forward error từ child lên
- [ ] Nếu có dynamic cooldown → `return _ok(dynamic_cooldown_sec=N)`
- [ ] Nếu action committed + fail → `return _fail("...", dynamic_cooldown_sec=N)`
- [ ] Test: chạy activity → check UI hiển thị đúng error message

### Thứ tự ưu tiên migrate

| Priority | Hàm | Lý do |
|----------|-----|-------|
| 🔴 P0 | `startup_to_lobby` | Mọi workflow đều gọi |
| 🔴 P0 | `back_to_lobby` | Mọi workflow đều gọi |
| 🟠 P1 | `go_to_farming` | High frequency |
| 🟠 P1 | `train_troops` | High frequency |
| 🟠 P1 | `research_technology` | Đã return dict |
| 🟡 P2 | `alliance_help` | Simple |
| 🟡 P2 | `claim_alliance_resource` | Simple |
| 🟡 P2 | `check_mail` | Simple |
| 🟢 P3 | `capture_pet` | Moderate |
| 🟢 P3 | `release_pet` | Moderate |
| 🟢 P3 | Tất cả còn lại | Khi có thời gian |

---

## 7. Executor Processing (Tham khảo)

Dev **KHÔNG cần sửa** executor. Executor đã handle tự động:

```python
# executor.py — đã tích hợp sẵn

ok = await asyncio.to_thread(core_actions.some_function, serial, detector, ...)

# Dict return
if isinstance(ok, dict):
    _activity_meta.update(ok)   # lưu error + dynamic_cooldown_sec
    ok = ok.get("ok", False)

# Khi fail:
if not ok:
    err_reason = _activity_meta.get("error", "")
    result["error"] = f"{fn_id}: {err_reason}" if err_reason else f"{fn_id} failed"
    # → UI hiển thị: "nav_to_research_tech: RESOURCE_QUEUE_BUSY: Research queue is full"
```

**Kết quả trên UI** (ví dụ):

| Scenario | Error hiển thị trên UI |
|----------|----------------------|
| Core action return `False` | `nav_to_research_tech failed` |
| Core action return `{"ok": False}` | `nav_to_research_tech failed` |
| Core action return `{"ok": False, "error": "RESOURCE_QUEUE_BUSY: Queue full"}` | `nav_to_research_tech: RESOURCE_QUEUE_BUSY: Queue full` |
| Python exception | `Exception in nav_to_research_tech: No module named 'ocr_helper'` |

---

## 8. Quick Reference

```
┌──────────────────────────────────────────────────────────────────┐
│ ERROR CODE CHEAT SHEET                                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Format:  "<CATEGORY>_<REASON>: <human message>"                  │
│                                                                  │
│ Categories:                                                      │
│   NAV_       Navigation failures (lobby, menu, screen)           │
│   STATE_     Wrong game state                                    │
│   TIMEOUT_   Waited too long                                     │
│   TEMPLATE_  Image template issues                               │
│   OCR_       Text/number read failures                           │
│   RESOURCE_  Not enough resource/slot/queue                      │
│   CRASH_     App crash/disconnect                                │
│   CONFIG_    Bad params/missing data                             │
│   ACTION_    Button/tap/verify failures                          │
│   LOCK_      Feature locked/cooldown                             │
│                                                                  │
│ Return format:                                                   │
│   {"ok": False, "error": "NAV_LOBBY_UNREACHABLE: msg"}           │
│   {"ok": False, "error": "...", "dynamic_cooldown_sec": N}       │
│   {"ok": True}                                                   │
│   {"ok": True,  "dynamic_cooldown_sec": N}                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```
