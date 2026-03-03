# Account Rotation Strategy (30 phút/account)

## 1) Mục tiêu vận hành
- Đảm bảo **mọi account đều được chạy đủ lượt** theo vòng quay.
- Mỗi account chạy tối đa **30 phút**, hết slot thì chuyển account kế tiếp.
- Dễ quản lý với mô hình hiện tại:
  - 1 Emulator
  - 2 email login / emulator
  - 1 email chứa 2 account
  - => mỗi emulator có thể phục vụ 4 account.

## 2) Mô hình dữ liệu nên chuẩn hoá
Tách dữ liệu thành 4 lớp để quản trị rõ ràng:

1. `emulators`
   - `emulator_id`, `status`, `last_seen_at`, `max_parallel=1`
2. `email_profiles`
   - `email_id`, `emulator_id`, `email`, `provider`, `cooldown_until`
3. `accounts`
   - `account_id`, `email_id`, `account_name`, `priority`, `enabled`
4. `account_runtime_state`
   - `last_run_at`, `last_duration_sec`, `success_streak`, `fail_streak`, `next_eligible_at`

> Điểm mấu chốt: account là đơn vị schedule, email chỉ là "container" đăng nhập.

## 3) Thuật toán scheduler khuyến nghị
Dùng **Weighted Round Robin + Aging**:

- Base theo vòng tròn để công bằng.
- Weight ưu tiên account chính (`priority`).
- Aging tăng điểm cho account lâu chưa chạy để tránh bị đói lượt.

Điểm chọn account:

`score = wait_minutes * 1.0 + priority * 0.7 - fail_streak * 2.0`

Chỉ lấy account thỏa:
- `enabled = true`
- `next_eligible_at <= now`
- không bị lock bởi session khác

Account có score cao nhất sẽ vào slot 30 phút kế tiếp.

## 4) Vòng đời 1 slot 30 phút
1. Scheduler pick account.
2. Lock emulator (mutex 1 tác vụ).
3. Nếu cần, switch email rồi switch account trong game.
4. Chạy workflow trong `time_budget = 27 phút`.
5. `3 phút` còn lại dành cho save state + logout/switch an toàn.
6. Update runtime state:
   - success: `last_run_at`, reset fail nhẹ
   - fail: tăng `fail_streak`, set `next_eligible_at` lùi 10-20 phút
7. Unlock emulator.

## 5) Chống lệch lượt (đảm bảo chạy đủ)
Áp dụng 3 guardrail:

- **Daily quota check**: mỗi account phải đạt `N` lượt/ngày (ví dụ 6).
- **Max gap**: không account nào bị bỏ quá `X` giờ (ví dụ 6h).
- **Catch-up mode**: nếu gần cuối ngày còn thiếu lượt, tạm tăng weight account thiếu.

## 6) Cách map với workflow hiện tại
Trong workflow page/backend run API, thêm metadata bắt buộc cho mỗi lần chạy:

- `account_id`
- `email_id`
- `emulator_id`
- `timeslot_id`
- `time_budget_sec`

Và ghi log theo cấu trúc:
- `SLOT_START`
- `SWITCH_EMAIL`
- `SWITCH_ACCOUNT`
- `WORKFLOW_DONE`
- `SLOT_END`

Nhờ đó có thể audit: account nào thiếu lượt, lỗi ở bước nào.

## 7) Khuyến nghị UX để dễ quản lý
Thêm 3 màn hình/khối thông tin:

1. **Rotation Board**
   - Emulator -> Email -> Account dạng cây
   - hiển thị: last run, next run, fail streak, quota hôm nay
2. **Fairness Dashboard**
   - biểu đồ số slot/account theo ngày
   - cảnh báo account lệch chuẩn >20%
3. **Queue Preview (2-4 giờ tới)**
   - cho thấy thứ tự account sắp chạy
   - hỗ trợ pin account khẩn cấp (override 1 slot)

## 8) Rule set đề xuất cho mô hình của bạn
Với 1 emulator có 4 account:

- Chu kỳ lý thuyết: `4 * 30 = 120 phút` quay lại account cũ.
- Cấu hình đề xuất:
  - `time_budget_sec = 1620` (27 phút)
  - `switch_buffer_sec = 180`
  - `max_fail_streak = 3` -> đưa account vào cooldown 60 phút
  - `min_runs_per_day = 6`

Nếu có nhiều emulator, chạy scheduler theo từng emulator độc lập để giảm khóa chéo.

## 9) Pseudocode
```text
loop every 15s:
  for each emulator in ONLINE:
    if emulator.locked: continue

    candidates = get_accounts(emulator)
      .filter(enabled)
      .filter(next_eligible_at <= now)

    if empty(candidates): continue

    pick = max_by_score(candidates)

    create_timeslot(emulator, pick.account_id, 30m)
    run_slot(emulator, pick, budget=27m, buffer=3m)
```

## 10) KPI theo dõi sau khi áp dụng
- `%account đạt min_runs_per_day`
- `median wait time giữa 2 lần chạy/account`
- `slot success rate`
- `%slot mất >3 phút chỉ cho switch`
- `fairness index` (độ lệch slot giữa account)

Nếu 5 KPI này ổn định trong 3-7 ngày thì lịch chạy đã đủ công bằng + tối ưu vận hành.