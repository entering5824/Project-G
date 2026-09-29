# Project G — brief để xin tư vấn thiết kế giao diện

## Điều cần giải quyết

Project G là ứng dụng Windows viết bằng PySide6, giúp người chơi Genshin Impact biết **nên nâng cấp nhân vật nào và làm việc gì tiếp theo** từ dữ liệu tài khoản của họ. Kế hoạch được tính trên máy. Người dùng nhập Account Snapshot hoặc tệp GOOD; ứng dụng chọn mục tiêu nâng cấp và lộ trình. Người dùng có thể xếp ưu tiên nhân vật, nhưng không phải tự chọn một build đầy đủ để máy mới lập kế hoạch.

Giao diện hiện tại đã được rút gọn nhiều lần nhưng vẫn giống bảng điều khiển kỹ thuật: nhiều vùng, nhiều lựa chọn, nhiều thuật ngữ và quá ít chỉ dẫn về bước tiếp theo. Xin đề xuất **cấu trúc trải nghiệm mới**, không chỉ đổi màu, bo góc hoặc ẩn thêm vài thành phần trong bố cục cũ.

Người dùng mục tiêu có thể chưa biết thuật ngữ phần mềm. Họ phải hiểu được màn hình chính và thao tác đầu tiên mà không đọc tài liệu. Hướng thẩm mỹ mong muốn: liquid glass tinh tế, ít thông tin, sang trọng, dễ đọc. Có thể đề xuất một hướng thị giác khác nếu giải thích được vì sao nó phục vụ trải nghiệm tốt hơn. Không cần giữ hệ thống thẻ, bảng, sidebar hoặc thứ tự bốn trang hiện tại.

## Bốn nhóm chức năng cần được giải quyết

Đây là chức năng hiện có, **không phải yêu cầu giữ nguyên thành bốn màn hình**. Có thể gộp, tách hoặc đổi tên nếu đường đi của người dùng rõ hơn.

### 1. Việc tiếp theo

- Nêu một việc đáng làm nhất, nhân vật liên quan và kết quả của bước nâng cấp.
- Cho biết việc có thể làm ngay, đang chờ ngày mở, hay bị chặn bởi điều kiện khác.
- Nếu việc chính đang chờ, đưa ra việc khác có thể làm trong lúc đó.
- Cho phép đi tới mục tương ứng trong lộ trình hoặc hồ sơ nhân vật.
- Chi tiết nguồn thực hiện, lý do đề xuất và nhựa chỉ hiện khi có dữ liệu hữu ích. Không có bảng “Chuẩn bị nguyên liệu” trên màn hình chính. Không lặp tên nhân vật.
- Khi chưa có tài khoản hoặc chưa đủ dữ liệu, nêu một bước cụ thể để bắt đầu.

### 2. Lộ trình

- Trình bày các bước nâng cấp theo thứ tự ưu tiên, với nhân vật, mốc hiện tại → mốc kế tiếp và trạng thái.
- Tìm nhân vật, lọc theo việc có thể làm/đang chờ/đã đạt và xem giải thích chi tiết cho một bước.
- Có đường đi tới nhân vật liên quan; vẫn dùng được khi danh sách dài.
- Các số liệu và cột kỹ thuật là thông tin phụ, không cần xuất hiện trong cái nhìn đầu tiên.

### 3. Nhân vật

- Tìm và chọn nhân vật trong tài khoản.
- Nhìn nhanh cấp, thiên phú, vũ khí và tiến độ; khi cần có thể xem năm món thánh di vật, chỉ số và RV đã biết/chưa biết.
- Người dùng có thể đánh dấu muốn nâng cấp, ưu tiên một nhân vật cho hôm nay, hoặc mở các thao tác bổ sung như cấu hình, preset và cập nhật RV.
- Trạng thái đang chọn phải rõ mà không tạo các đường viền hoặc ô lưới rối mắt.

### 4. Ưu tiên nhân vật (Tier List)

- Chọn hạng S+, S, A, B, C, D hoặc chưa xếp cho từng nhân vật; lưu thay đổi để cập nhật lộ trình.
- Tìm nhân vật. Khi cần, có thể đặt hạng thấp nhất được xét, chỉnh điểm chính xác 0–100, chọn luôn xét/bỏ qua, ghi chú, bộ thánh di vật và nhập/xuất tệp.
- Phải phân biệt rõ thay đổi đã lưu với chưa lưu và xử lý điểm không hợp lệ.
- Nên là thao tác chọn ưu tiên dễ hiểu, không mang cảm giác điền một bảng tính cũ.

## Luồng chung và ranh giới sản phẩm

- Luồng đầu tiên: nhập/cập nhật tài khoản → hiểu đề xuất → xem lộ trình/nhân vật → chọn ưu tiên nếu muốn → lưu → thấy kế hoạch cập nhật.
- Account Snapshot là đường nhập chính; GOOD là đường nhập thay thế. Dữ liệu được lưu trên máy.
- Ứng dụng **không theo dõi tồn kho nguyên liệu**. Lượng nguyên liệu nếu được hiển thị chỉ là ước tính cho mục tiêu, không phải số còn thiếu trong tài khoản.
- Cần thiết kế trạng thái trống, đang tải/tính, lỗi và thử lại, việc đang chờ, thay đổi chưa lưu và hộp thoại xác nhận có tác động.
- Các thao tác hiện có như nhập dữ liệu, tính lại, xuất kết quả, cài đặt, cấu hình nhân vật và phím tắt cần có đường tiếp cận. Có thể thay đổi cách trình bày và vị trí của chúng.
- Thiết kế cho cửa sổ tối thiểu 800×560, chuẩn 1260×780 và rộng 1600×1000; kiểm tra DPI 100%, 125%, 150%. Ưu tiên thao tác bằng chuột lẫn bàn phím, nhãn rõ, tương phản đọc được.
- Đây là UI desktop gốc, không phải trang web. Đề xuất cần khả thi với Qt/PySide6; hiệu ứng chuyển động nên tiết chế.

## Tư liệu hiện trạng

Ảnh dưới đây dùng dữ liệu minh họa để đánh giá bố cục, không chứa tài khoản thật:

- [Việc tiếp theo](ui-preview/simplified-2026-09-28/scale-100/page-0-1260x780.png)
- [Lộ trình](ui-preview/simplified-2026-09-28/scale-100/page-1-1260x780.png)
- [Nhân vật](ui-preview/simplified-2026-09-28/scale-100/page-2-1260x780.png)
- [Ưu tiên](ui-preview/simplified-2026-09-28/scale-100/page-3-1260x780.png)
- Ảnh cỡ nhỏ và các hộp thoại: `ui-preview/simplified-2026-09-28/scale-100/`. Các bản DPI 125% và 150% nằm ở hai thư mục cùng cấp.

## Kết quả mong muốn từ bên tư vấn

1. Chỉ ra 3–5 nguyên nhân cụ thể khiến trải nghiệm hiện tại khó hiểu, theo thứ tự ảnh hưởng đến người dùng mới.
2. Đưa **hai hướng cấu trúc khác nhau** cho luồng sử dụng chính; mô tả cách người dùng đi từ dữ liệu tài khoản tới hành động tiếp theo.
3. Chọn một hướng và thiết kế các màn hình/chặng cần thiết ở 1260×780 và 800×560, bao gồm trạng thái chưa có dữ liệu, đang chờ và chưa lưu.
4. Cung cấp bản đồ điều hướng, thứ bậc thông tin, cách mở chi tiết, hệ thống kiểu chữ/màu/khoảng cách, quy tắc chọn/focus/disabled và lời văn hướng tới người dùng phổ thông.
5. Nêu những gì cần thay đổi trong bố cục hoặc luồng hiện tại, cùng lý do. Có thể đề xuất bỏ hẳn bảng hoặc cách chia trang hiện tại nếu giải pháp mới tốt hơn.

## Prompt có thể gửi nguyên văn

> Tôi muốn tư vấn thiết kế lại UX/UI cho Project G, ứng dụng Windows PySide6 giúp người chơi Genshin Impact biết nên nâng cấp nhân vật nào và làm việc gì tiếp theo từ dữ liệu tài khoản. Xin đọc brief và xem bốn ảnh hiện trạng đính kèm. Giao diện hiện tại vẫn quá giống bảng điều khiển kỹ thuật dù đã rút gọn. Hãy chẩn đoán nguyên nhân và đề xuất hai cấu trúc trải nghiệm **khác nhau thực sự**; đừng chỉ thay màu, bo góc hoặc giấu các bảng cũ. Người dùng mới phải hiểu hành động đầu tiên mà không đọc hướng dẫn. Tôi thích cảm giác liquid glass, ít thông tin nhưng sang trọng; bạn có quyền đề xuất hướng khác nếu giải thích được. Hãy chọn một hướng, thể hiện các màn hình chính ở 1260×780 và 800×560, các trạng thái trống/đang chờ/chưa lưu, luồng nhập tài khoản → xem việc tiếp theo → xem lộ trình/nhân vật → chọn ưu tiên. Giữ chức năng, nhưng được đổi bố cục, tên gọi, điều hướng và cách mở chi tiết. Đây là ứng dụng desktop Qt, không phải website. Ưu tiên ý tưởng táo bạo, dễ hiểu và khả thi để triển khai.
