# ProjectG — giao diện liquid glass

> Bản tinh chỉnh premium hiện tại dùng kính khói, bạc và nền trung tính.
> Xem [PREMIUM_UI_REFINEMENT.md](PREMIUM_UI_REFINEMENT.md). Nội dung bên dưới
> ghi lại đợt triển khai liquid glass đầu tiên.

Yêu cầu thực hiện: làm lại UI/UX theo phong cách liquid glass, ít thông tin,
sang trọng; đồng thời chia lại cấu trúc code giao diện. Tài liệu này mô tả
bản hiện tại, thay thế hướng graphite/amber trong các audit giao diện trước.

## Giao diện và thao tác

- Bốn trang dùng nền gradient được vẽ bằng Qt, bề mặt trong, viền sáng,
  màu nhấn xanh bạc và thanh điều hướng nổi phía trên.
- Trang Tiếp theo ưu tiên hành động chính. Dữ kiện tài khoản và giải thích
  nằm trong phần mở rộng; thẻ nguyên liệu chỉ xuất hiện khi có nguyên liệu.
- Trang Nhân vật mở thông tin build theo yêu cầu. Ba hành động thường dùng
  ở cuối trang; cấu hình và nhập RV chuyển vào menu, giữ trạng thái khả dụng.
- Lộ trình và Tier List giữ tìm kiếm, bộ lọc, chỉnh sửa và các cột chi tiết
  theo yêu cầu trong hệ thống trình bày mới.
- Các hộp thoại dùng chung nền kính, tiêu đề, nội dung cuộn và vùng xác nhận
  cố định. Cài đặt chia thành Tài khoản, Kế hoạch, Thánh di vật; nhập mục tiêu
  chia thành JSON/Prompt, các thao tác sao chép tài liệu nằm trong menu.
- Phím Ctrl+1..4, Ctrl+F, Ctrl+R, retry, loading và chống kết quả cũ được giữ.

## Cấu trúc để tự sửa

Trong `src/projectg/presentation/desktop/pyside6/`:

- `main_window.py`: ghép cửa sổ, điều hướng và controller.
- `pages/`: bố cục và trình bày từng trang.
- `actions/`: xử lý thao tác nhập/xuất và lập kế hoạch qua controller.
- `dialogs.py`, `dialog_shell.py`: form và khung hộp thoại dùng chung.
- `workers.py`: công việc nền; `assets.py`: ảnh và fallback.
- `theme.py`, `glass.py`, `navigation.py`: màu, style và cách vẽ.

Không thay đổi domain, application, schema tài khoản, dữ liệu game hoặc
cơ sở dữ liệu người dùng trong đợt làm lại UI này.

## Kiểm chứng

- Suite đầy đủ: 359 passed; 42 cảnh báo SQLAlchemy về teardown fixture.
- `verify_desktop_ui.py`: bốn trang có dữ liệu minh họa tại 800×560,
  1260×780 và 1600×1000; 11 hộp thoại tại 800×560; trạng thái rỗng và lỗi.
- DPI 100%, 125%, 150%; ảnh và JSON xác minh nằm trong
  `docs/ui-preview/liquid-glass/scale-*`.
- Kiểm tra hộp thoại: tiêu đề không chồng nội dung, không cuộn ngang toàn
  form, nút nằm trong cửa sổ; chuyển tab và mở lại không làm mất giá trị.
- Compilation: `python -m compileall -q src tests scripts`.

Ảnh dùng dữ liệu minh họa. Kiểm tra ứng dụng dùng DB fixture riêng.
Hiệu ứng kính được vẽ trong Qt, không dùng blur nền desktop của hệ điều hành.
Chưa build lại executable đóng gói hoặc kiểm thử thủ công trên màn hình thật.

## Chạy và kiểm tra

```powershell
.venv\Scripts\python.exe -m projectg.main
.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp-liquid-glass
$env:PYTHONPATH = 'src'
.venv\Scripts\python.exe scripts\verify_desktop_ui.py --output docs\ui-preview\liquid-glass\scale-100
```
