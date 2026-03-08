# Feature Specification: Task Reordering (Drag & Drop)

## 1. Mục tiêu tính năng

Task List cho phép người dùng **thay đổi thứ tự các Task bằng thao tác kéo thả**.

Thứ tự Task trong danh sách **chính là thứ tự thực thi của hệ thống**, vì vậy khi người dùng thay đổi vị trí Task thì **execution order phải thay đổi tương ứng**.

---

# 2. Cấu trúc hiển thị Task

Mỗi Task trong Task List phải hiển thị theo cấu trúc sau:

```
[Drag Icon]   Task Name
              Task Description / Detail (nếu có)
```

Trong đó:

* **Drag Icon** nằm ở **bên trái Task**
* Icon này là **điểm tương tác để kéo thả Task**
* Phần nội dung Task (name, description…) **không dùng để kéo**

---

# 3. Hành vi kéo thả (User Interaction)

Người dùng thực hiện thao tác:

1. Di chuyển chuột đến **Drag Icon**
2. Nhấn giữ chuột
3. Kéo Task **lên hoặc xuống trong danh sách**
4. Thả chuột để đặt Task vào vị trí mới

Sau khi thả:

* Task sẽ nằm ở **vị trí mới trong danh sách**
* Các Task khác **tự động điều chỉnh thứ tự**

---

# 4. Phản hồi giao diện trong lúc kéo (UI Feedback)

Trong quá trình kéo Task, giao diện cần phản hồi rõ ràng để người dùng biết trạng thái hiện tại.

### 4.1 Task đang được kéo

Task đang được kéo phải có trạng thái khác với bình thường, ví dụ:

* hiển thị nổi bật hơn
* có hiệu ứng di chuyển
* tách nhẹ khỏi danh sách

Mục đích là giúp người dùng **xác định Task nào đang được kéo**.

---

### 4.2 Các Task còn lại

Khi Task được kéo:

* Các Task khác trong danh sách phải **dịch chuyển vị trí theo thời gian thực**
* Danh sách phải thể hiện rõ **vị trí mà Task sẽ được đặt khi thả**

Điều này giúp người dùng dễ dàng **chọn đúng vị trí mong muốn**.

---

# 5. Quy tắc thay đổi thứ tự

Task List luôn duy trì thứ tự **từ trên xuống dưới**.

Khi một Task được kéo sang vị trí mới:

* Task đó nhận **vị trí mới**
* Các Task khác **dịch chuyển lên hoặc xuống để đảm bảo thứ tự liên tục**

Ví dụ:

Ban đầu:

```
1. Task A
2. Task B
3. Task C
4. Task D
```

Người dùng kéo **Task C lên vị trí số 2**

Kết quả:

```
1. Task A
2. Task C
3. Task B
4. Task D
```

---

# 6. Ảnh hưởng tới Automation Execution

Automation Engine phải luôn:

* Lấy danh sách Task theo **thứ tự hiện tại**
* Thực thi Task **từ trên xuống dưới**

Nếu người dùng thay đổi thứ tự Task thì **thứ tự mới sẽ được áp dụng cho các lần chạy tiếp theo**.

---

# 7. Đồng bộ và lưu trạng thái

Sau khi người dùng thay đổi vị trí Task:

* Thứ tự mới phải được **cập nhật trong hệ thống**
* Khi reload hoặc mở lại page, Task List phải **giữ nguyên thứ tự đã sắp xếp**

---

# 8. Trường hợp đặc biệt

### Task kéo lên đầu danh sách

Task trở thành **Task đầu tiên**, các Task khác dịch xuống.

---

### Task kéo xuống cuối danh sách

Task trở thành **Task cuối cùng**.

---

### Task List chỉ có một Task

Không cần thay đổi thứ tự.

---

# 9. Kết quả mong muốn

Sau khi triển khai tính năng:

* Người dùng có thể **sắp xếp lại Task dễ dàng**
* Thứ tự hiển thị luôn phản ánh **đúng thứ tự thực thi**
* Task List luôn **ổn định và rõ ràng khi thao tác**

---
