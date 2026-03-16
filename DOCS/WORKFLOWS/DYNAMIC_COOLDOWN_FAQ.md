# Dynamic Cooldown — Scenarios & Edge Cases (FAQ)

Tài liệu này ghi lại các scenarios, edge cases, và giải thích logic cooldown chi tiết.  
Thêm mới bằng cách copy template ở cuối file.

---

## FAQ-001: Activity FAIL hoàn toàn → có bị kẹt cooldown cũ không?

**Tình huống:** Activity SUCCESS trước đó có `dynamic_cooldown_sec`, lần chạy tiếp FAIL (return `False`).

**Trace:**
```
T0 = 0h:    Activity SUCCESS → result_json = {dynamic_cooldown_sec: 12000}
T1 = 3h20:  Cooldown hết → activity chạy lại → FAIL (return False)
             └─ FAILED log saved (result_json = "{}")
T1 + 0:     Next cycle cooldown check:
             └─ Query: WHERE status='SUCCESS' ORDER BY started_at DESC LIMIT 1
             └─ Tìm log T0 → last_run = T0, dynamic_cd = 12000
             └─ time.time() - T0 = 3h20+ → ≥ 12000s
             └─ Cooldown ĐÃ HẾT → retry ✅
```

**Kết luận:** ❌ Không kẹt. Activity chỉ chạy lại khi CD đã expired → log SUCCESS cũ chắc chắn đã hết hạn.

---

## FAQ-002: FAIL liên tục, chưa bao giờ SUCCESS

**Tình huống:** Activity chạy lần đầu FAIL, chạy lại FAIL, liên tục FAIL.

**Trace:**
```
T0: Activity FAIL → FAILED log (result_json = "{}")
T1: Activity FAIL → FAILED log (result_json = "{}")
T2: Cooldown check:
    └─ Query SUCCESS → không tìm thấy log nào
    └─ Return (0, 0)
    └─ last_run = 0 → activity chưa bao giờ chạy thành công
    └─ Không áp cooldown → retry ✅
```

**Kết luận:** ❌ Không kẹt. Không có SUCCESS log → `(0, 0)` → activity luôn chạy lại.

**Lưu ý:** Hiện tại không có retry delay cho repeated failures. Nếu cần chống spam, core_action có thể return `{"ok": False, "dynamic_cooldown_sec": 300}` (chờ 5 phút).

---

## FAQ-003: skip_cooldown=True → FAIL → cooldown trở lại

**Tình huống:** Bot chạy với `skip_cooldown=True`, activity FAIL, rồi cycle tiếp chạy bình thường.

**Trace:**
```
T0 = 0h:    Activity SUCCESS → dynamic_cd = 12000 (3h20)
T1 = 1h:    Bot chạy lại với skip_cooldown=True → activity FAIL
             └─ CD bị skip nên activity chạy dù chưa hết CD
             └─ FAIL → FAILED log saved
T1 + 0:     Next cycle (skip_cooldown=False):
             └─ Query SUCCESS → tìm T0 → dynamic_cd = 12000
             └─ time.time() - T0 = 1h → 3600 < 12000
             └─ CÒN COOLDOWN → skip ⏳
T0 + 3h20:  Cooldown hết → retry ✅
```

**Kết luận:** ✅ Behavior đúng. March từ T0 vẫn đang chạy → đúng là nên chờ hết CD.

---

## FAQ-004: Dynamic CD ngắn hơn Static → swap sớm hơn

**Tình huống:** Config `cooldown_minutes=240` (4h), nhưng dynamic chỉ 3h20.

**Trace:**
```
Config: cooldown_minutes = 240 (static 4h)
Farm:   march_time = 11700s → dynamic_cooldown_sec = 12000 (3h20)

T0 = 0h:    Activity SUCCESS → dynamic_cd = 12000
T0 + 3h20:  _all_activities_on_cooldown() check:
             └─ effective_cd = 12000 (dynamic > 0 → dùng dynamic)
             └─ time.time() - T0 = 3h20 → ≥ 12000
             └─ has_any_runnable = True → swap vào account ✅

CŨ (static only):  Chờ đến T0 + 4h mới swap
MỚI (dynamic):     Swap sớm hơn 40 phút
```

**Kết luận:** ✅ Optimization hoạt động đúng. Smart wait timer cũng chính xác hơn.

---

## FAQ-005: Dynamic CD dài hơn Static → chờ lâu hơn

**Tình huống:** Config `cooldown_minutes=120` (2h) nhưng march thực tế mất 3h.

**Trace:**
```
Config: cooldown_minutes = 120 (static 2h)
Farm:   march_time = 10800s → dynamic_cooldown_sec = 11100 (3h05)

T0 = 0h:    Activity SUCCESS → dynamic_cd = 11100
T0 + 2h:    Cooldown check:
             └─ effective_cd = 11100 (dynamic > 0 → dùng dynamic)
             └─ time.time() - T0 = 2h → 7200 < 11100
             └─ CÒN COOLDOWN → skip ⏳ (đúng! march vẫn đang chạy)

CŨ (static): Chạy lại lúc T0+2h → lãng phí vì march chưa về
MỚI (dynamic): Chờ thêm 1h05 → chạy lại đúng lúc march về
```

**Kết luận:** ✅ Tránh chạy lại sớm khi march vẫn đang đi.

---

## FAQ-006: Activity FAIL nhưng game action đã committed

**Tình huống:** Gửi quân farm thành công (committed) → step verify FAIL (OCR lỗi).

**Trace (HIỆN TẠI — chưa implement):**
```
T0:  send_march() → OK (quân đã đi)
T0:  verify_march() → FAIL (OCR lỗi)
T0:  core_action return False (bool)
     └─ FAILED log saved, result_json = "{}"
T0+: Cooldown check:
     └─ Query SUCCESS → tìm log cũ hoặc không có
     └─ Retry ngay → nhưng quân ĐÃ ĐI rồi → swap vô ích
```

**Giải pháp (CẦN IMPLEMENT):**
```python
# core_actions.py
def go_to_farming(serial, detector):
    send_march(serial, detector)
    march_time = read_march_timer(serial, detector)

    if not verify_march(serial, detector):
        # March ĐÃ ĐI → vẫn cần cooldown dù verify fail
        return {"ok": False, "dynamic_cooldown_sec": march_time + 300}

    return {"ok": True, "dynamic_cooldown_sec": march_time + 300}
```

**Yêu cầu thay đổi:**
- Sửa `get_effective_cooldown_sec()` để cũng đọc `dynamic_cooldown_sec` từ log MỚI NHẤT (bất kể status), không chỉ SUCCESS.

**Status:** ⚠️ Chưa implement. Cần thêm logic mới.

---

## FAQ-007: 2 activities cùng dùng dynamic CD

**Tình huống:** `gather_rss` và `train_troops` đều return dynamic_cooldown_sec.

**Trace:**
```
T0:  gather_rss    SUCCESS → dynamic_cd = 12000 (3h20)
T0:  train_troops  SUCCESS → dynamic_cd = 3600  (1h)

T0 + 1h:   Cooldown check:
            └─ gather_rss:   12000 - 3600 = 8400s left → skip ⏳
            └─ train_troops: 3600 - 3600 = 0 → READY ✅
            └─ has_any_runnable = True → swap vào account
            └─ Chạy train_troops, skip gather_rss

T0 + 3h20: gather_rss cooldown hết → chạy ✅
```

**Kết luận:** ✅ Mỗi activity có cooldown **độc lập**. Dynamic CD áp dụng per (account_id, activity_id).

---

## FAQ-008: dynamic_cooldown_sec = 0 trong result_json

**Tình huống:** Core action return `{"ok": True, "dynamic_cooldown_sec": 0}`.

**Trace:**
```
get_effective_cooldown_sec():
  └─ dynamic_cd = int(result.get("dynamic_cooldown_sec", 0))
  └─ dynamic_cd = 0

bot_orchestrator cooldown check:
  └─ effective_cd = dynamic_cd if dynamic_cd > 0 else (cd_minutes * 60)
  └─ dynamic_cd = 0 → dùng static cd_minutes * 60
```

**Kết luận:** ✅ `0` = "không override" → fallback về static config. **Không** disable cooldown.

---

## FAQ-009: Account-level cooldown vs Activity-level cooldown

**Tình huống:** Account có `misc.cooldown_min = 30` (30 phút giữa 2 lần swap), activity có `cooldown_minutes = 240`.

**Trace:**
```
T0:       Account A swap vào → chạy hết activities → swap ra
T0 + 0:   Account-level: last_run_times[A] = T0, cooldown = 30m
T0 + 15m: Cycle mới:
           └─ Account cooldown check: 15m < 30m → skip account A ⏳
T0 + 30m: Account cooldown hết → swap vào A
           └─ Activity cooldown check (per activity):
              └─ Activity dynamic_cd hoặc static cd → check riêng
```

**Kết luận:** Hai tầng cooldown **hoàn toàn tách biệt**:
- **Account-level:** `misc.cooldown_min` — quản lý bởi `last_run_times` dict
- **Activity-level:** `cooldown_minutes` / `dynamic_cooldown_sec` — quản lý bởi SQLite logs

Dynamic cooldown **CHỈ ảnh hưởng activity-level**. Account-level không bị đụng vào.

---

## Template: Thêm Scenario Mới

Copy template dưới đây và điền vào:

```markdown
## FAQ-0XX: [Tiêu đề ngắn gọn]

**Tình huống:** [Mô tả scenario]

**Trace:**
\```
[Timeline trace chi tiết]
\```

**Kết luận:** [✅/❌/⚠️] [Kết luận + lý do]
```
