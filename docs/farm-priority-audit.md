# Audit thứ tự farm và ưu tiên

Ngày: 2026-09-27.

Lộ trình hiển thị từng mục tiêu nhân vật/component theo rank. Today chọn mục tiêu khả dụng đầu tiên trong thứ tự đó; Talent Book đóng cửa cho phép chọn mục tiêu tiếp theo. Các nguồn farm nằm trong mục tiêu đã chọn.

Lỗi đã sửa: CharacterPriority được lưu nhưng không được đưa vào PlannerInput; overview luôn trả AUTO và badge ưu tiên bị ẩn. Reader cấu hình hiện đọc ưu tiên theo account, application truyền vào engine, overview và giao diện hiển thị đúng trạng thái.

Cách dùng:
1. Import snapshot, chấm tier ở Tier List.
2. Xem Lộ trình theo #1, #2, #3 để biết thứ tự nâng cấp.
3. Xem Tiếp theo để biết mục tiêu hôm nay và phương thức farm.
4. Trong Nhân vật, mở cấu hình và chọn Ưu tiên / Bình thường / Hạ ưu tiên, rồi lưu để tính lại lộ trình.
5. Ghim Today khi muốn tập trung nhân vật cụ thể. Ghim là cấu hình riêng với ưu tiên chiến lược.

Xác minh: 314 passed, 1 skipped; compileall thành công. Môi trường Python kiểm thử thiếu PySide6 nên suite giao diện native bị skip; thay đổi badge chưa được xác minh bằng UI trong lượt audit này. Có 40 cảnh báo SQLAlchemy teardown hiện hữu.

Build Knowledge Standard/Deep vẫn cần bổ sung theo hợp đồng hiện tại; không coi kết quả audit này là chứng nhận chất lượng toàn bộ dữ liệu build.
