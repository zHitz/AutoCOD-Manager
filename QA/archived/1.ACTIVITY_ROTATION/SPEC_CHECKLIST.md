# WORKFLOWS PAGE:
---

# Feature Specification Checklist

## Feature: Activity Rotation

### Description

Activity Rotation là cơ chế cho phép hệ thống **tự động thực thi các activity theo thứ tự từ trên xuống dưới trong Activity List**, dựa trên **các activity được user chọn (checked)**.

Chỉ những activity được user **tick chọn** mới được thực thi.

---

# Functional Requirements

## Requirement 1 — Activity Execution Order

**Description**
System phải thực thi activity **từ trên xuống dưới theo đúng thứ tự hiển thị trong Activity List**.

**Expected Behavior**

1. System đọc danh sách Activity List theo thứ tự UI.
2. Kiểm tra activity nào được user **checked**.
3. Chỉ thực thi activity được check.
4. Sau khi hoàn thành activity hiện tại → chuyển sang activity tiếp theo trong list.
5. Khi chạy hết list → kết thúc vòng activity.

**Acceptance Criteria**

* [ ] Activity được chạy **đúng thứ tự từ trên xuống dưới**
* [ ] Không được chạy activity nằm dưới trước activity phía trên
* [ ] Activity không được tick phải **bị bỏ qua**
* [ ] Sau khi hoàn thành 1 activity phải **chuyển sang activity tiếp theo**

---

## Requirement 2 — User Selection Control

**Description**
User có thể **bật / tắt activity** thông qua checkbox trong Activity List.

**Expected Behavior**

* Nếu activity **checked** → activity được đưa vào queue chạy
* Nếu activity **unchecked** → activity bị bỏ qua hoàn toàn

**Acceptance Criteria**

* [ ] Activity unchecked **không bao giờ được execute**
* [ ] Activity checked **phải được execute khi rotation tới**
* [ ] Thay đổi checkbox phải được áp dụng **ngay cho lần chạy tiếp theo**

---

## Requirement 3 — Activity Completion Handling

**Description**
Sau khi một activity hoàn thành, hệ thống phải chuyển sang activity tiếp theo trong danh sách.

**Expected Behavior**

1. Activity bắt đầu
2. Activity hoàn thành
3. System chuyển sang activity tiếp theo

**Acceptance Criteria**

* [ ] Activity không được chạy lặp vô hạn
* [ ] Activity phải kết thúc trước khi activity tiếp theo bắt đầu
* [ ] Không được chạy nhiều activity cùng lúc (trừ khi hệ thống hỗ trợ parallel)

---

## Requirement 4 — Empty Activity Handling

**Description**
Nếu **không có activity nào được check**, hệ thống không được thực thi activity.

**Expected Behavior**

* System detect rằng không có activity nào enabled
* Workflow kết thúc hoặc idle

**Acceptance Criteria**

* [ ] System không crash
* [ ] System không chạy activity nào
* [ ] Có log hoặc thông báo trạng thái

---

# Activity List Example

Dựa trên UI hình bạn gửi:

Possible Activities:

1. New Player Tutorial
2. Technology Research
3. City Upgrade
4. Alliance Donation
5. Train Troops
6. Alliance Help
7. Gather Resources
8. Goblin Market
9. Attack Darkling Patrols
10. Enact Policies
11. Explore Fog
12. Visit explorable sites
13. Build Alliance Constructions
14. Gather Alliance Resource Center

---

# Expected Execution Example

User selection:

```
[ ] New Player Tutorial
[ ] Technology Research
[x] City Upgrade
[x] Alliance Donation
[x] Train Troops
[ ] Alliance Help
[ ] Gather Resources
[x] Goblin Market
```

Expected execution order:

```
1 → City Upgrade
2 → Alliance Donation
3 → Train Troops
4 → Goblin Market
```

---

# QA Validation Points

Tester cần verify:

### Order Validation

* Activity phải chạy **đúng thứ tự UI**

### Selection Validation

* Unchecked activity không được chạy

### Execution Validation

* Activity phải **chạy xong mới qua activity tiếp theo**

### Stability

* Không crash nếu activity fail
* Không stuck ở activity

---

# Possible Edge Cases

1️⃣ Activity fail giữa chừng
→ system phải tiếp tục activity tiếp theo

2️⃣ User uncheck activity khi workflow đang chạy
→ thay đổi áp dụng cho **rotation tiếp theo**

3️⃣ Activity mất điều kiện runtime
ví dụ: không đủ resource
→ activity bị skip

---

# QA Result Format (để AI Tester dùng)

```
Requirement 1 — Order Execution
Status: PASS / FAIL

Requirement 2 — User Selection
Status: PASS / FAIL

Requirement 3 — Completion Handling
Status: PASS / FAIL

Requirement 4 — Empty Activity Handling
Status: PASS / FAIL
```

---
