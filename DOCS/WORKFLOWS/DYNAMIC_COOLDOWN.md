# Dynamic Activity Cooldown

Cho phép activity tự xác định thời gian cooldown thực tế dựa trên thông tin trong game, thay vì dùng cố định `cooldown_minutes` trong config.

---

## 1. Tổng Quan Cơ Chế

### 1.1 Static Cooldown (Cơ chế cũ - vẫn hoạt động)

User set cứng `cooldown_minutes` trong UI config → mọi lần chạy đều chờ đúng thời gian đó.

```
Config: cooldown_minutes = 240 (4h)
Activity chạy xong → chờ 4h → chạy lại
```

### 1.2 Dynamic Cooldown (Cơ chế mới - opt-in)

Activity đọc thông tin trong game (VD: thời gian march), trả về cooldown thực tế → hệ thống ưu tiên dùng giá trị đó.

```
Activity chạy xong → return dynamic_cooldown_sec = 11700 (3h15m)
→ Hệ thống chờ 3h15m thay vì 4h
→ Tiết kiệm 45 phút mỗi lần chạy
```

### 1.3 Priority Rule

```
effective_cooldown = dynamic_cooldown_sec > 0
                   ? dynamic_cooldown_sec
                   : cooldown_minutes × 60    ← static fallback
```

**Dynamic luôn ưu tiên hơn static.** Nếu không có dynamic (activity return bool hoặc không có key `dynamic_cooldown_sec`) → fallback 100% về static. **Không có gì thay đổi cho activities cũ.**

---

## 2. Data Flow Chi Tiết

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: Activity Execution                                    │
│                                                                 │
│  core_actions.py                                                │
│  └─ go_to_farming(serial, detector, ...)                       │
│     └─ Đọc game screen → march_time = 11700s (3h15m)          │
│     └─ return {"ok": True, "dynamic_cooldown_sec": 12000}      │
│                           ↑ march_time + 300s buffer            │
│                                                                 │
│  executor.py                                                    │
│  └─ ok = core_actions.go_to_farming(...)                       │
│  └─ isinstance(ok, dict) → True                                │
│  └─ _activity_meta.update(ok)  ← lưu dynamic_cooldown_sec     │
│  └─ ok = ok.get("ok", False)   ← extract bool cho step logic  │
│  └─ return {"success": True, "dynamic_cooldown_sec": 12000}    │
│                                                                 │
│  bot_orchestrator.py                                            │
│  └─ result = await _execute_current_account(...)                │
│  └─ result = {"success": True, "dynamic_cooldown_sec": 12000}  │
│  └─ finish_account_activity(result=result)                      │
│                                                                 │
│  execution_log.py                                               │
│  └─ UPDATE account_activity_logs SET                            │
│       result_json = '{"success":true,"dynamic_cooldown_sec":12000}'
│     WHERE id = <log_id>                                         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2: Cooldown Check (Lần chạy tiếp)                       │
│                                                                 │
│  bot_orchestrator.py  (3 nơi check)                            │
│  └─ get_effective_cooldown_sec(acc_id, activity_id)            │
│     └─ Query: SELECT started_at, result_json                   │
│        FROM account_activity_logs                               │
│        WHERE account_id=? AND activity_id=? AND status='SUCCESS'│
│        ORDER BY started_at DESC LIMIT 1                         │
│     └─ Parse result_json → extract dynamic_cooldown_sec         │
│     └─ Return (last_run_epoch, dynamic_cooldown_sec)            │
│                                                                 │
│  Tính effective_cooldown:                                       │
│  └─ dynamic_cd > 0 ? dynamic_cd : (cd_minutes × 60)           │
│  └─ time.time() - last_run < effective_cd → SKIP (on cooldown) │
│  └─ else → RUN (cooldown expired)                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 3: Frontend Display                                       │
│                                                                 │
│  api.py  GET /api/monitor/account-activities                    │
│  └─ get_effective_cooldown_sec(account_id, act_id)              │
│  └─ effective_cd = dynamic_cd > 0 ? dynamic_cd : cd_minutes*60 │
│  └─ cd_remaining = max(0, effective_cd - elapsed)               │
│  └─ Response: { cooldown_remaining_sec: 7200 }                  │
│                                                                 │
│  Frontend (KHÔNG thay đổi)                                      │
│  └─ Nhận cooldown_remaining_sec → hiển thị countdown            │
│  └─ CooldownPolicy.js, workflow.js, Monitor tab                 │
│  └─ Tất cả đọc cooldown_remaining_sec từ API → hoạt động y nguyên
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Database Schema

Sử dụng cột `result_json` đã có sẵn trong bảng `account_activity_logs`.

```sql
-- Bảng account_activity_logs (đã tồn tại, KHÔNG cần migration)
CREATE TABLE account_activity_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id    INTEGER,
    group_id      INTEGER,
    activity_id   TEXT,
    activity_name TEXT,
    status        TEXT,        -- 'RUNNING', 'SUCCESS', 'FAILED'
    error_code    TEXT,
    error_message TEXT,
    started_at    TEXT,        -- ISO 8601
    finished_at   TEXT,        -- ISO 8601
    duration_ms   INTEGER,
    result_json   TEXT         -- ← dynamic_cooldown_sec lưu ở đây
);
```

### result_json Format

**Khi KHÔNG có dynamic cooldown** (activities cũ):
```json
{"success": true}
```

**Khi CÓ dynamic cooldown**:
```json
{"success": true, "dynamic_cooldown_sec": 12000}
```

Query đọc dynamic cooldown:
```sql
SELECT started_at, result_json
FROM account_activity_logs
WHERE account_id = ? AND activity_id = ? AND status = 'SUCCESS'
ORDER BY started_at DESC LIMIT 1;
```

---

## 4. Các File Liên Quan

### Backend

| File | Vai trò | Thay đổi |
|------|---------|----------|
| `backend/core/workflow/execution_log.py` | Query DB cho cooldown data | Thêm `get_effective_cooldown_sec()` |
| `backend/core/workflow/executor.py` | Chạy steps, trả result | Handle dict return từ core_actions, propagate `dynamic_cooldown_sec` |
| `backend/core/workflow/bot_orchestrator.py` | Orchestrate accounts/activities | 3 nơi cooldown check dùng `get_effective_cooldown_sec()` |
| `backend/api.py` | Monitor API endpoint | Tính `cooldown_remaining_sec` dùng dynamic override |
| `backend/core/workflow/core_actions.py` | Game logic thực tế | Activities opt-in bằng return dict |

### Frontend (KHÔNG thay đổi)

| File | Vai trò |
|------|---------|
| `frontend/js/domain/workflow/policies/CooldownPolicy.js` | Check + format cooldown (dùng `cooldown_remaining_sec` từ API) |
| `frontend/js/pages/workflow.js` | Config panel, Monitor tab (dùng `cooldown_remaining_sec` từ API/WS) |

---

## 5. Cooldown Check Locations (bot_orchestrator.py)

Có **3 nơi** kiểm tra activity cooldown, tất cả dùng cùng logic:

### 5.1 B1: Pre-Execution Check (L1018-1030)

Trước khi chạy từng activity cho mỗi account.

```python
# ── ACTIVITY-LEVEL COOLDOWN (dynamic override > static config) ──
if not self.skip_cooldown and act_cfg.get("cooldown_enabled"):
    cd_minutes = act_cfg.get("cooldown_minutes", 0)
    if cd_minutes > 0:
        last_act_run, dynamic_cd = await execution_log.get_effective_cooldown_sec(
            int(acc_id), act_id_or_name
        )
        effective_cd = dynamic_cd if dynamic_cd > 0 else (cd_minutes * 60)
        if last_act_run > 0 and (time.time() - last_act_run) < effective_cd:
            # → SKIP activity
```

### 5.2 B2: All-Activities Guard (_all_activities_on_cooldown)

Kiểm tra trước swap: nếu TẤT CẢ activities đều on cooldown → không cần swap vào account này.

```python
last_act_run, dynamic_cd = await execution_log.get_effective_cooldown_sec(
    int(acc_id), act_id_or_name
)
effective_cd = dynamic_cd if dynamic_cd > 0 else (cd_minutes * 60)
if last_act_run <= 0 or (now - last_act_run) >= effective_cd:
    has_any_runnable = True  # Có ít nhất 1 activity ready → swap vào
```

### 5.3 B3: Earliest Ready Timer (_earliest_activity_ready_sec)

Tính thời gian chờ tối thiểu để activity sớm nhất hết cooldown (cho smart wait).

```python
last_run, dynamic_cd = await execution_log.get_effective_cooldown_sec(int(aid), act_id)
effective_cd = dynamic_cd if dynamic_cd > 0 else (cd_minutes * 60)
remaining = effective_cd - (now - last_run)
min_remaining = min(min_remaining, remaining)
```

---

## 6. Cách Thêm Dynamic Cooldown Cho Một Activity

### Bước 1: Xác định data source

Xác định activity nào có thể đọc thời gian thực từ game. Ví dụ:
- **Gather Resource (farm RSS)**: march time hiển thị trên game screen
- **Train Troops**: training queue time
- **Research**: research timer

### Bước 2: Sửa core_action return type

**TRƯỚC** (return bool):
```python
# core_actions.py
def go_to_farming(serial, detector, resource_type="wood"):
    # ... game logic ...
    return True  # success
```

**SAU** (return dict với dynamic_cooldown_sec):
```python
# core_actions.py
def go_to_farming(serial, detector, resource_type="wood"):
    # ... game logic: gửi quân farm ...

    # Đọc march time từ game screen (OCR/template matching)
    march_time_sec = _read_march_timer(serial, detector)  # VD: 11700 (3h15m)

    if march_time_sec and march_time_sec > 0:
        buffer_sec = 300  # 5 phút buffer an toàn
        return {
            "ok": True,
            "dynamic_cooldown_sec": march_time_sec + buffer_sec
        }

    # Fallback: nếu không đọc được timer → return bool → dùng static config
    return True
```

### Bước 3: KHÔNG cần sửa gì thêm

- `executor.py` tự xử lý cả `bool` và `dict` return
- `bot_orchestrator.py` tự đọc `dynamic_cooldown_sec` từ DB
- Frontend tự hiển thị `cooldown_remaining_sec` đúng
- Config `cooldown_minutes` vẫn là fallback

---

## 7. Key Functions Reference

### execution_log.get_effective_cooldown_sec()

```python
async def get_effective_cooldown_sec(account_id: int, activity_id: str) -> tuple:
    """Return (last_run_epoch, dynamic_cooldown_sec).

    - last_run_epoch: float — epoch timestamp của lần SUCCESS gần nhất
    - dynamic_cooldown_sec: int — cooldown override từ result_json
      • > 0: dùng giá trị này thay vì static config
      • = 0: không có dynamic data → caller phải dùng static cooldown_minutes
    """
```

### executor.py — Dict Normalization

```python
# Sau khi core_action trả kết quả:
ok = core_actions.some_function(serial, detector, ...)

if isinstance(ok, dict):
    _activity_meta.update(ok)      # Lưu dynamic_cooldown_sec
    ok = ok.get("ok", False)       # Extract bool cho step pass/fail
# else: ok vẫn là bool → hoạt động y nguyên

# Khi trả kết quả cuối:
result = {"success": all_ok}
if _activity_meta.get("dynamic_cooldown_sec"):
    result["dynamic_cooldown_sec"] = _activity_meta["dynamic_cooldown_sec"]
return result
```

---

## 8. Edge Cases

| Scenario | Behavior |
|----------|----------|
| Activity return `True` (bool) | Dùng static `cooldown_minutes` — y nguyên |
| Activity return `{"ok": True}` (không có `dynamic_cooldown_sec`) | Dùng static `cooldown_minutes` |
| Activity return `{"ok": True, "dynamic_cooldown_sec": 0}` | Dùng static `cooldown_minutes` (0 = không override) |
| Activity return `{"ok": True, "dynamic_cooldown_sec": 12000}` | Dùng 12000s = 200 phút thay vì static |
| Activity return `{"ok": False, "dynamic_cooldown_sec": 12000}` | Activity FAILED → status = 'FAILED' → cooldown **không áp dụng** (chỉ đọc từ SUCCESS logs) |
| `cooldown_enabled = false` | Không check cooldown → activity luôn chạy |
| `cooldown_minutes = 0` | Không check cooldown → activity luôn chạy |
| Lần đầu tiên chạy (chưa có log) | `get_effective_cooldown_sec()` → `(0, 0)` → activity chạy ngay |
| OCR fail, không đọc được timer | Activity nên `return True` (bool) → fallback static config |

---

## 9. Console Log Format

Khi activity bị skip do cooldown, log mới hiển thị nguồn và thời gian còn lại:

```
[BotOrchestrator] Activity 'gather_rss' on cooldown (dynamic: 200m, 45.3m left) for Account 12. Skipping.
[BotOrchestrator] Activity 'train_troops' on cooldown (static: 240m, 120.0m left) for Account 12. Skipping.
```

- `dynamic`: cooldown từ `result_json.dynamic_cooldown_sec`
- `static`: cooldown từ config `cooldown_minutes`

---

## 10. Checklist Cho Dev

Khi thêm dynamic cooldown cho activity mới:

- [ ] Xác định cách đọc timer/duration từ game screen
- [ ] Sửa core_action: return `{"ok": True, "dynamic_cooldown_sec": <seconds>}`
- [ ] Handle fallback: nếu không đọc được timer → `return True`
- [ ] Test: chạy activity → check DB `result_json` có `dynamic_cooldown_sec`
- [ ] Test: lần chạy tiếp → kiểm tra cooldown đúng giá trị dynamic
- [ ] Test: xóa `result_json` dynamic → verify fallback về static config
