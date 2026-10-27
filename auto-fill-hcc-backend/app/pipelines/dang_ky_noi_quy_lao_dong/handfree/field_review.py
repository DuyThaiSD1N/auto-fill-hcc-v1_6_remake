"""Bổ sung ô còn trống trên tờ khai đăng ký nội quy lao động của doanh nghiệp
(Form.io, cổng Bộ Nội vụ dichvucongbnv.moha.gov.vn)."""

PROCEDURE_KEYS = ("dang-ky-noi-quy-lao-dong",)

# Cổng đánh dấu ô bắt buộc trên nhãn (label.field-required) / class "required" và báo lỗi dưới ô sau khi bấm Tiếp tục —
# extension đọc thẳng các dấu đó (cả form người nộp lẫn eForm thủ tục) nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" của chủ hồ sơ là ô tự do, không phải thông tin trên giấy tờ.
NO_ASK = ("ghiChu",)
