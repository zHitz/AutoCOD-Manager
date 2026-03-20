# Guide: Writing Core Actions with Dynamic Cooldown

Hướng dẫn chi tiết cho dev viết `core_actions.py` functions tương thích Dynamic Cooldown.

**Đọc trước:** [DYNAMIC_COOLDOWN.md](./DYNAMIC_COOLDOWN.md) để hiểu cơ chế hoạt động.

---

## 1. Return Types — Hai Loại Hợp Lệ

### Type A: `bool` (Activities KHÔNG cần dynamic cooldown)

```python
def alliance_help(serial: str, detector: GameStateDetector) -> bool:
    """Activity đơn giản — không cần dynamic cooldown."""
    # ... game logic ...
    return True   # SUCCESS → cooldown dùng static cooldown_minutes
    return False  # FAILED → không cooldown, retry lần sau
```

- Cooldown: dùng static `cooldown_minutes` từ config UI
- **Đây là behavior mặc định**, tất cả activities cũ đều hoạt động y nguyên

### Type B: `dict` (Activities CÓ dynamic cooldown hoặc cần error message)

```python
def go_to_farming(serial: str, detector: GameStateDetector, resource_type: str = "wood") -> dict:
    """Activity cần dynamic cooldown — return dict."""
    # ... game logic ...
    return {"ok": True, "dynamic_cooldown_sec": 12000}
    return {"ok": False, "dynamic_cooldown_sec": 12000}  # partial fail
    return {"ok": False, "error": "Could not find RSS tile"}  # fail with reason
    return {"ok": False}  # complete fail — no dynamic CD
    return True  # fallback — cũng hợp lệ (executor handle cả hai)
```

- `ok`: **Bắt buộc** — `True` = SUCCESS, `False` = FAILED
- `dynamic_cooldown_sec`: **Optional** — số giây cooldown override
- `error`: **Optional** — lý do fail hiển thị trên UI (thay vì generic "fn_id failed")

---

## 2. Return Value Decision Tree

```
Activity chạy xong
  │
  ├─ Có cần dynamic cooldown HOẶC error message?
  │   │
  │   ├─ KHÔNG (simple action) → return True / return False (bool)
  │   │           └─ Dùng static cooldown_minutes config
  │   │           └─ Error trên UI: "fn_id failed" (generic)
  │   │
  │   └─ CÓ → return dict:
  │       │
  │       ├─ Game action committed + thành công?
  │       │   └─ return {"ok": True, "dynamic_cooldown_sec": <seconds>}
  │       │
  │       ├─ Game action committed + verify FAIL?
  │       │   └─ return {"ok": False, "dynamic_cooldown_sec": <seconds>,
  │       │              "error": "March sent but verify failed"}
  │       │     (March đã đi → vẫn cần chờ dù verify fail)
  │       │
  │       ├─ Game action CHƯA committed + fail?
  │       │   └─ return {"ok": False, "error": "Could not navigate to RSS tile"}
  │       │     (Không gửi quân → không cần dynamic CD → retry bình thường)
  │       │
  │       └─ Không đọc được timer (OCR fail)?
  │           └─ return True  (bool fallback → dùng static config)
  │
```

---

## 3. Tính dynamic_cooldown_sec

### Công thức

```python
dynamic_cooldown_sec = game_duration_sec + buffer_sec
```

| Thành phần | Mô tả | Ví dụ |
|-----------|-------|-------|
| `game_duration_sec` | Thời gian thực từ game (march time, train time, ...) | 11700 (3h15m) |
| `buffer_sec` | Thời gian chờ thêm để đảm bảo action hoàn tất | 300 (5 phút) |

### Tại sao cần buffer?

- March về → cần thời gian unload RSS
- Training xong → có thể cần chờ animation
- OCR có thể đọc sai ±1-2 phút
- **Khuyến nghị:** buffer 3-5 phút cho farming, 1-2 phút cho training

### Chuyển đổi thời gian

```python
# Format "3h 15m" → seconds
def parse_game_timer(timer_str: str) -> int:
    """Convert game timer string to seconds. Returns 0 if parse fails."""
    hours, minutes = 0, 0
    import re
    h_match = re.search(r'(\d+)\s*h', timer_str)
    m_match = re.search(r'(\d+)\s*m', timer_str)
    if h_match: hours = int(h_match.group(1))
    if m_match: minutes = int(m_match.group(1))
    total = hours * 3600 + minutes * 60
    return total if total > 0 else 0

# Usage:
timer_sec = parse_game_timer("3h 15m")  # → 11700
dynamic_cooldown_sec = timer_sec + 300   # → 12000 (3h20)
```

---

## 4. Ví Dụ Thực Tế (Full Pattern)

### 4.1 Farming (có dynamic cooldown)

```python
def go_to_farming(serial: str, detector: GameStateDetector, resource_type: str = "wood") -> dict:
    """
    Farming Workflow with Dynamic Cooldown.
    Dynamic CD = march time + 5min buffer.
    """
    print(f"[{serial}] Starting Farming for: {resource_type.upper()}")

    # 1. Navigate
    if not back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)"):
        return False  # ← Complete fail → bool fallback → dùng static CD

    # 2. Send march
    march_sent = _send_farm_march(serial, detector, resource_type)
    if not march_sent:
        return {"ok": False}  # ← Không gửi được quân → no dynamic CD

    # 3. Read march timer (Optional — Phase 2)
    march_time_sec = _read_march_timer(serial, detector)

    if march_time_sec and march_time_sec > 0:
        # Timer đọc được → dynamic cooldown
        buffer = 300  # 5 phút
        return {"ok": True, "dynamic_cooldown_sec": march_time_sec + buffer}
    
    # Timer không đọc được → fallback static config
    return True
```

### 4.2 Train Troops (có dynamic cooldown)

```python
def train_troops(serial: str, detector: GameStateDetector, training_list: list = None) -> dict:
    """
    Train Troops with Dynamic Cooldown.
    Dynamic CD = training queue time + 2min buffer.
    """
    if training_list is None:
        training_list = [("infantry", 1)]

    # ... training logic ...
    success = _execute_training(serial, detector, training_list)
    if not success:
        return {"ok": False}  # ← Training fail → no dynamic CD

    # Read training queue time
    train_time_sec = _read_training_queue(serial, detector)

    if train_time_sec and train_time_sec > 0:
        return {"ok": True, "dynamic_cooldown_sec": train_time_sec + 120}

    return {"ok": success}  # ← Không đọc được timer → static CD
```

### 4.3 Alliance Help (KHÔNG cần dynamic cooldown)

```python
def alliance_help(serial: str, detector: GameStateDetector) -> bool:
    """Alliance Help — instant action, no dynamic cooldown needed."""
    # ... tap help button logic ...
    return True  # ← Bool → static cooldown_minutes
```

---

## 5. Executor Processing Flow

Dev **KHÔNG cần sửa** `executor.py`. Executor tự xử lý cả 2 return types:

```python
# executor.py (đã tích hợp sẵn)
ok = await asyncio.to_thread(core_actions.go_to_farming, serial, detector, ...)

# ── Dict return handling ──
if isinstance(ok, dict):
    _activity_meta.update(ok)           # Lưu dynamic_cooldown_sec
    ok = ok.get("ok", False)            # Extract bool cho pass/fail

# ── Bool return → unchanged ──
# ok vẫn là True/False

# ── Final result ──
result = {"success": all_ok}
if _activity_meta.get("dynamic_cooldown_sec"):
    result["dynamic_cooldown_sec"] = _activity_meta["dynamic_cooldown_sec"]
# → {"success": true, "dynamic_cooldown_sec": 12000}
```

**Kết quả cuối** được truyền đến `bot_orchestrator.py` → save vào DB (`result_json`) → đọc lại khi check cooldown.

---

## 6. Lưu Trữ DB

`result_json` column trong `account_activity_logs`:

```
SUCCESS + dynamic CD:  {"success": true, "dynamic_cooldown_sec": 12000}
SUCCESS + no dynamic:  {"success": true}
FAILED  + dynamic CD:  {"success": false, "dynamic_cooldown_sec": 12000}
FAILED  + no dynamic:  {}
```

Query khi check cooldown:
```sql
-- Hiện tại: chỉ đọc SUCCESS logs
SELECT started_at, result_json FROM account_activity_logs
WHERE account_id = ? AND activity_id = ? AND status = 'SUCCESS'
ORDER BY started_at DESC LIMIT 1;
```

---

## 7. Activity Registry Config

Khi register activity trong `workflow_registry.py`, set **static fallback**:

```python
{
    "id": "gather_rss",
    "name": "Gather Resource",
    "steps": [...],
    "defaults": {
        "cooldown_enabled": True,
        "cooldown_minutes": 240,   # ← Static fallback (4h)
    },
}
```

- `cooldown_minutes` vẫn bắt buộc → đây là **fallback** khi dynamic CD không khả dụng
- **Khuyến nghị:** set static = thời gian tối đa có thể xảy ra (worst case)
- User vẫn có thể override trong UI

---

## 8. Rules & Anti-Patterns

### ✅ DO

```python
# Luôn có fallback an toàn
if march_time > 0:
    return {"ok": True, "dynamic_cooldown_sec": march_time + 300}
return True  # ← Safe fallback

# Game action committed nhưng verify fail → vẫn set CD
if not verify_march():
    return {"ok": False, "dynamic_cooldown_sec": march_time + 300}

# Buffer hợp lý
buffer = 300  # 5 phút cho farming
buffer = 120  # 2 phút cho training
```

### ❌ DON'T

```python
# ĐỪNG set CD quá ngắn
return {"ok": True, "dynamic_cooldown_sec": 10}  # ← 10 giây? Chắc chắn sai

# ĐỪNG set CD khi activity chưa commit game action
if not send_march():
    return {"ok": False, "dynamic_cooldown_sec": 12000}  # ← SAI! Quân chưa đi

# ĐỪNG dùng dynamic_cooldown_sec = 0 để "disable" cooldown
return {"ok": True, "dynamic_cooldown_sec": 0}  # ← 0 = fallback static, KHÔNG disable

# ĐỪNG throw exception thay vì return
raise Exception("failed!")  # ← Executor catch thành FAILED, result_json = {}
```

---

## 9. Testing Checklist

Khi thêm dynamic cooldown cho 1 activity:

- [ ] Core action return dict đúng format: `{"ok": bool, "dynamic_cooldown_sec": int}`
- [ ] Có fallback khi không đọc được timer: `return True`
- [ ] Partial fail scenario: game action committed nhưng verify fail → vẫn có dynamic CD
- [ ] Complete fail scenario: game action chưa committed → `return {"ok": False}` hoặc `return False`
- [ ] Static cooldown_minutes trong registry là worst-case value
- [ ] Chạy activity → check DB: `result_json` có `dynamic_cooldown_sec`
- [ ] Chạy lại → verify cooldown = dynamic value (không phải static)
- [ ] Xóa result_json → verify fallback về static config
- [ ] Monitor tab hiển thị cooldown countdown đúng

---

## 10. Quick Reference Card

```
┌────────────────────────────────────────────────────────────────┐
│ RETURN TYPE CHEAT SHEET                                        │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│ return True                        → SUCCESS + static CD       │
│ return False                       → FAILED  + generic error   │
│ return {"ok": True}                → SUCCESS + static CD       │
│ return {"ok": False}               → FAILED  + generic error   │
│ return {"ok": False,                                           │
│   "error": "reason"}               → FAILED  + specific error  │
│ return {"ok": True,                                            │
│   "dynamic_cooldown_sec": N}       → SUCCESS + dynamic CD      │
│ return {"ok": False,                                           │
│   "dynamic_cooldown_sec": N,                                   │
│   "error": "reason"}               → FAILED + dynamic CD       │
│                                      + specific error          │
│                                                                │
│ Fields:                                                        │
│   ok    (required)  → True=SUCCESS, False=FAILED               │
│   error (optional)  → reason hiển thị trên UI                  │
│   dynamic_cooldown_sec (optional) → override static CD         │
│                                                                │
│ Priority: dynamic_cooldown_sec > cooldown_minutes              │
│ Fallback: dynamic=0 hoặc missing → static config              │
│                                                                │
│ Buffer khuyến nghị:                                            │
│   Farming:  +5 phút (300s)                                     │
│   Training: +2 phút (120s)                                     │
│   Research: +2 phút (120s)                                     │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```
