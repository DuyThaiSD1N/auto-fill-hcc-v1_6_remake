"""Bổ sung ô còn trống trên tờ khai đính chính Giấy chứng nhận đã cấp lần đầu có sai sót — cổng iGate Tuyên Quang
(Form.io, hai form theo quy trình).

Trợ lý chạy key gốc cho cả quy trình thường lẫn quy trình iLis, nên một cấu hình phủ tên ô của cả hai form.
"""

PROCEDURE_KEYS = ("dinh-chinh-gcn-cap-lan-dau-sai-sot-tuyen-quang",)

# Cổng đánh dấu ô bắt buộc trên component / nhãn và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng các dấu
# đó nên không khai thêm tên ô.
REQUIRED = ()

# Ô tự do hoặc không áp dụng cho hồ sơ cá nhân tự nộp: tên hồ sơ, ghi chú (nội dung đính chính lấy từ Đơn), cơ quan/tổ
# chức, số đăng ký kinh doanh, khối "Thông tin người ủy quyền (nếu có)" của form 1, ngày hiệu lực / hết hạn giấy phép
# của form iLis (Giấy chứng nhận không ghi).
NO_ASK = (
    "textField", "tenHoSo", "fullname1", "agency1", "Hovaten", "Sogiaytotuythan", "sodienthoai", "diachi",
    "organization", "ghiChu", "effectiveDate", "expirationDate",
)
