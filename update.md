# COD Game Automation Manager - Update Log

## Version 1.0.2 (Current)
*UI/UX Improvements for Accounts Page*

- **Accounts Table Redesign (`frontend/js/pages/accounts.js`)**
  - Áp dụng các **Quick Fixes** cho bảng hiển thị:
    - **Group Headers:** Chia Header thành 4 nhóm chính (Identity & Core, Account Details, Progress & Social, Resources) để giảm tải nhận thức (cognitive load).
    - **Frozen Columns:** Cố định 3 cột đầu (STT, Emu Name, In-game Name) khi lướt theo chiều ngang.
    - **Data Highlighting:** Tô đậm và gán màu (Color Coding) cho chỉ số POW, Hall, Market và toàn bộ 4 cột Resources (thêm hậu tố 'M').
    - **Tooltip + Status Badges:** Cột Match được nâng cấp với Badge Yes/No thay cho icon text khô khan, kèm thao tác hover-tooltip để giải nghĩa.
    - **Quick Actions:** Thêm các nút thao tác nhanh (View, Sync) dưới dạng bóng (ghost buttons) chỉ xuất hiện khi di chuột (hover) qua từng hàng.

- **Account Detail Page (New Feature)**
  - Click vào bất kỳ dòng nào trên bảng để mở **Profile Page** riêng cho thông tin Account thay vì nhảy modal.
  - Sử dụng Layout hai cột màn hình chia dọc:
    - **Left Sidebar:** Chứa Avatar/tên in-game, POW và Metadata cốt lõi (Emulator, Target ID, Provider).
    - **Main Content:** Bộ Grid Card hiển thị 4 chỉ số sinh tồn rút gọn.
    - **System Tabs:** Bố trí một thẻ chức năng bên dưới, cho phép cuộn các tab Overview, Resources, và Notes mà không rối dữ liệu. Trải nghiệm mượt mà giống Dashboard chuẩn.
  - Nút Back (`←`) quay lại bảng và các Quick Button (Force Sync, Edit, Delete) ở góc phải trên cùng.

- **Advanced UI/UX Polish (Request Update)**
  - **Slide-Over Panel Detail UX:** Thay vì chuyển cảnh mất context, click `View` sẽ trượt một panel từ bên phải sang (Off-canvas) giống Jira/Linear, giữ nguyên bảng số liệu phía dưới.
  - **Visual Hierarchy & Formatting:**
    - Shrink cột STT (cố định 56px) theo đúng chuẩn. Tăng khoảng cách margin-bottom phần Group Headers.
    - Các số liệu Tài nguyên được tăng `font-weight: 600` và `letter-spacing` dễ đọc hơn, đính kèm trend marker (mũi tên `↑`/`↓`).
    - Nút Quick Action Hover hiện ra biểu tượng mũi tên rõ ràng (`View ➔`) để thu hút tương tác.
  - **Profile Overhaul:** Badge **POW** mang style gradient vàng cam đẳng cấp. Thu nhỏ Avatar xuống 56px cân đối hơn. Chia Layout Tab Overview thành Grid thẻ lưới 2 cột chống khoảng trắng cụt.
  - **Visual Bugs Fix (CSS Layout):**
    - Sửa lỗi trong suốt (Transparent background) khi mở Slide Panel Panel do biến màu `var(--surface-50)` bị đè nét, gây ra hiện tượng chữ chồng lên bảng dữ liệu (text overlapping). Thiết lập lại biến solid background thành `var(--surface-100) / #ffffff`.
    - Fix triệt để lỗi Frozen Columns đầu bảng bị xuyên thấu nội dung khi lướt ngang. Nâng Z-index layer cục bộ và bắt buộc phủ nền solid trắng để không bao giờ bị các cột sau trượt đè lên text.
  - **Account Detail Tabs Restructure:**
    - Cấu trúc lại dữ liệu Tab **Overview**: Chia thành 2 cột cân bằng (Login & Access, Emulator Info vs Game Status, Match). Thêm icon chấm phân cách và các đường gạch ngang mờ (border-bottom) giống hệt thiết kế tham chiếu.
    - Làm lại Tab **Resources**: Thay thế hiển thị Grid cục mịch cũ bằng hệ thống 3 Card Tài nguyên nằm ngang với **Progress Bar theo %** cực kỳ sắc nét (tự đánh dấu xanh lá/cam/đỏ tùy mức độ đầy), và thêm một Block ngang nổi bật màu tím cho Pet Tokens. Phía dưới cùng chèn màng lọc **AI Insight** chữ xanh cảnh báo sản xuất quặng.
    - Làm mới Tab **Notes**: Chuyển định nghĩa từ Notes sang **Activity Log**. Sắp xếp theo chiều dọc với Textarea (Operator Notes) nằm trên, và phần hiển thị lịch sử thao tác dạng **Timeline List** (Recent History) có gạch dọc và chấm tròn ở phía dưới.
    - Thêm Text phụ "Last synced 2m ago" nhỏ mờ ở góc phải phía trên cùng của Header bảng Detail.
  - **Account View Layout Switcher:** Thêm cụm nút bấm chuyển đổi nhanh giữa 2 chế độ hiển thị Dạng Bảng (List) cũ và Dạng Thẻ Lưới (Grid) mới tại Header trang Dashboard. Chế độ Grid được code bám sát theo mẫu mock HTML cung cấp, với Card border nhô lên tương tác hover và thanh mini-progressbar hiển thị sức mạnh. Cả 2 chế độ đều hỗ trợ Click để mở Panel trượt góc phải trơn tru.
  - **AI UI Integration:** Hoàn thiện code giao diện mẫu do AI tạo. Chuyển đổi toàn bộ các tham số CSS không tồn tại (ảo) về hệ thống Core System Variable (`--card`, `--muted`, `--foreground`...), vá lỗi giao diện trong suốt và tối ưu code DOM logic chuẩn hóa hoàn toàn với cấu trúc app.



---

## Version 1.0.1
*Bug Fixes and Stability Improvements*

- **API & Error Handling (`frontend/js/api.js`)**
  - Khắc phục lỗi báo "Network Error" chung chung. Bây giờ module fetch sẽ kiểm tra `!res.ok` và hiển thị trực tiếp thông điệp trả về từ backend thay vì im lặng nuốt lỗi.

- **UI & Memory Management (`frontend/js/pages/task-runner.js`)**
  - **Memory Leak Fix**: Khắc phục lỗi rò rỉ bộ đếm giờ (setInterval leak) khi chạy Macro thông qua việc tái sử dụng biến `_runningMacros` (kiểu Map) để quản lý bộ đếm dựa trên `filename`. Gọi thẻ `clearInterval` đúng lúc khi macro hoàn tất hoặc bị lỗi.
  - **WebSocket Integration**: Hoàn thiện Activity Feed để hiển thị dữ liệu real-time của Macro. Bổ sung các event handler `macro_started`, `macro_progress`, `macro_completed`, và `macro_failed` vào UI update loop từ WebSocket.

- **Networking & Server Optimization (`backend/core/macro_replay.py`)**
  - **WebSocket Throttling**: Tối ưu hóa backend bằng cách hạn chế tần suất bắn tín hiệu `macro_progress` qua WebSocket. Hiện tại, nó chỉ gửi dữ liệu progress tối đa 1 lần mỗi giây (throttle 1.0s), ngăn chặn dứt điểm hiện tượng spam tín hiệu khi macro chạy dày đặc làm treo trình duyệt.

- **UI & Consistency (`frontend/js/pages/task-runner.js`)**
  - **Tab Synchronization**: Đồng bộ hoá giao diện Tab 1 (Select Emulators) cho vừa khít với các Tab khác bằng cách sửa class body/padding.
  - **Multi-Emu Notification Fix**: Cập nhật logic Activity Feed nhằm thông báo riêng biệt `✓ Macro completed` cho **TỪNG** emulator thay vì chỉ xuất hiện một thông báo đầu tiên dù đã tick chọn chạy nhiều máy.
  - **Global Feed Timestamps**: Chỉnh lại toàn bộ Activity Feed (kèm theo dòng mô tả "Select emulators..." mặc định) đều có đầy đủ timestamp, chấm tròn trạng thái.

- **New Features (UI Demo)**
  - **Game Accounts Page (`frontend/js/pages/accounts.js`)**: Tạo mới UI trang "Game Accounts" trưng bày bảng dữ liệu chi tiết của từng Acc Game bao gồm: Tên Ingame, Mức Power, Phương thức Đăng nhập, Trạng thái (Matching), Liên Minh, Tài nguyên Thu thập (Gold, Wood, Ore, Pet) và thiết kế thanh hiển thị cuộn ngang chống ép cột. Đã đấu nối trang vào thanh điều hướng Sidebar.


