"""Bổ sung ô còn trống trên tờ khai hỗ trợ chi phí mai táng cho đối tượng bảo trợ xã hội (mã 1.116910) (Form.io, cổng Bộ Y tế dichvucongbyt.moh.gov.vn)."""

PROCEDURE_KEYS = ("ho-tro-mai-tang-1116910",)

# Cổng đánh dấu ô bắt buộc trên nhãn (label.field-required) và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" của chủ hồ sơ là ô tự do, không phải thông tin trên giấy tờ.
NO_ASK = ("ghiChu",)
