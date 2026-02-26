OK, giờ mình **bỏ hẳn UI**, chuyển sang **phân tích logic nghiệp vụ (business logic)** của app **một cách có hệ thống**, để bạn kiểm tra **đã đủ chức năng chưa, thiếu gì, cần hoàn thiện gì**.

Mình sẽ nói như đang **spec một app hoàn chỉnh**, không dính code chi tiết, không dính UI.

---

# 🧠 BẢN CHẤT APP CỦA BẠN LÀ GÌ?

👉 Đây là một **Game Automation Control System**, không phải chỉ là OCR app.

**OCR chỉ là 1 công cụ con** trong hệ thống lớn hơn.

---

# 🎯 MỤC TIÊU NGHIỆP VỤ (Business Goals)

Ứng dụng cần cho phép người dùng:

1. Quản lý **nhiều emulator / instance game**
2. Thực hiện **các tác vụ đọc dữ liệu game** (OCR + automation)
3. Nhận về **dữ liệu đã được chuẩn hoá**
4. Dùng dữ liệu đó để:

   * Theo dõi tài khoản
   * So sánh
   * Quyết định hành động tiếp theo (sau này có thể auto)

---

# 🧩 CÁC NHÓM CHỨC NĂNG NGHIỆP VỤ CHÍNH

## 1️⃣ QUẢN LÝ EMULATOR (CORE)

### Yêu cầu nghiệp vụ

* Mỗi emulator là **một thực thể độc lập**
* Có trạng thái rõ ràng:

  * `ONLINE`
  * `BUSY`
  * `OFFLINE`
  * `ERROR` (rất nên có)
* App phải biết:

  * Emulator nào đang chạy
  * Emulator nào có thể nhận lệnh
  * Emulator nào đang bị kẹt

### Logic cần có

* Registry emulator (ID, type: BlueStacks / LDPlayer, port, adb id…)
* Heartbeat / ping định kỳ
* Lock emulator khi đang chạy task
* Timeout & recovery nếu task treo

📌 **Nếu thiếu phần này → app sẽ rất hay “đơ logic”**

---

## 2️⃣ TASK OCR = ĐƠN VỊ NGHIỆP VỤ CƠ BẢN

### Định nghĩa

> Một **Task** = một hành động nghiệp vụ hoàn chỉnh, không phải một lần OCR.

Ví dụ:

* `READ_PROFILE`
* `READ_RESOURCES`
* `READ_PET_TOKEN`
* `READ_BUILDING_LEVEL`

👉 Task **bao gồm nhiều bước**, OCR chỉ là 1 bước trong đó.

---

### Cấu trúc logic một Task (chuẩn)

1. Kiểm tra emulator ONLINE
2. Điều hướng game tới đúng màn hình
3. Chụp screenshot
4. OCR các vùng cần thiết
5. Parse + validate dữ liệu
6. Trả kết quả **đã chuẩn hoá**
7. Unlock emulator

📌 App của bạn **PHẢI coi Task là atomic unit**, không phải “bấm nút OCR”.

---

## 3️⃣ QUẢN LÝ COORDINATE MAP (NỘI BỘ)

Bạn đã có:

```python
REGIONS = {
  "profile_name": ...
  "res_gold_item": ...
}
```

### Về nghiệp vụ:

* REGIONS là **tài sản hệ thống**, không phải user config
* Mỗi version game → có thể cần version REGIONS khác

👉 Logic cần:

* Versioning coordinate map
* Gắn coordinate map với game version / resolution
* Fallback nếu OCR fail (retry / alternate region)

---

## 4️⃣ DATA MODEL – DỮ LIỆU SAU OCR (RẤT QUAN TRỌNG)

OCR output **KHÔNG BAO GIỜ là output cuối**.

### Bạn cần chuẩn hoá thành data model:

#### Profile

```json
{
  "name": "dragonball Goten",
  "power": 15144899
}
```

#### Resources

```json
{
  "gold": { "bag": 266300000, "total": 835000000 },
  "wood": { "bag": 258700000, "total": 832200000 },
  "ore":  { "bag": 139600000, "total": 343300000 },
  "mana": { "bag": 31300000,  "total": 41000000 }
}
```

👉 **Nghiệp vụ cần số INT, không cần string OCR**

---

## 5️⃣ VALIDATION & SANITY CHECK (BẮT BUỘC)

### Vì OCR KHÔNG BAO GIỜ 100%

Logic nghiệp vụ phải có:

* Check:

  * `total >= bag`
  * `power > 0`
  * Không có số âm
* Nếu fail:

  * Retry task
  * Hoặc đánh dấu `UNRELIABLE`

📌 Nếu không có bước này → dữ liệu rác sẽ phá toàn hệ thống sau này.

---

## 6️⃣ TASK COMPOSITION (TÍNH NĂNG NÂNG CAO NHƯNG RẤT ĐÁNG)

### Ví dụ:

**Quick Resource Check**

* Điều hướng
* Read bag
* Read total
* Gộp result
* Trả 1 object

👉 Đây là **task nghiệp vụ cao hơn**, user cần nhiều hơn từng OCR lẻ.

---

## 7️⃣ LỊCH SỬ & TRẠNG THÁI (OPERATIONS)

### App cần biết:

* Task nào chạy khi nào
* Kết quả lần trước là gì
* Emulator nào hay lỗi

👉 Nghiệp vụ:

* Logging
* Task result history
* Error classification:

  * OCR_FAIL
  * NAVIGATION_FAIL
  * TIMEOUT

---

## 8️⃣ MULTI-EMULATOR COORDINATION

### Các logic quan trọng:

* Không cho 2 task chạy song song trên cùng emulator
* Cho phép chạy song song trên **nhiều emulator khác nhau**
* Có hàng đợi task

📌 Đây là **core logic của app**, không phải phụ.

---

## 9️⃣ QUYỀN HẠN & MỨC ĐỘ TỰ ĐỘNG (FUTURE-PROOF)

Ngay cả nếu hiện tại:

* Chỉ 1 user
* Chỉ manual click

👉 Về nghiệp vụ, bạn NÊN chuẩn bị:

* Read-only vs Execute
* Manual vs Scheduled
* Auto retry vs Manual retry

---

# 🧠 TÓM TẮT KIẾN TRÚC NGHIỆP VỤ (MENTAL MODEL)

```
Emulator
  └── Task
        ├── Navigation
        ├── Screenshot
        ├── OCR
        ├── Parse
        ├── Validate
        └── Result
```

OCR = **1 node**, không phải trung tâm.

---

# ✅ CHECKLIST: APP BẠN ĐÃ / CHƯA ĐỦ?

| Mục                    | Có? |
| ---------------------- | --- |
| Emulator state machine | ⬜   |
| Task atomic logic      | ⬜   |
| Data normalization     | ⬜   |
| OCR validation         | ⬜   |
| Retry / fallback       | ⬜   |
| Multi-emulator lock    | ⬜   |
| Task composition       | ⬜   |
| Logging / history      | ⬜   |

---
