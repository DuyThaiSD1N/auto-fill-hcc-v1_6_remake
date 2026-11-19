"""Bổ sung ô còn trống trên tờ khai công nhận, giải quyết chế độ người hoạt động kháng chiến bị nhiễm chất độc hóa học
(Form.io, cổng Bộ Nội vụ)."""

PROCEDURE_KEYS = ("cong-nhan-che-do-khang-chien-nhiem-chat-doc-hoa-hoc",)

# Cổng đánh dấu ô bắt buộc trên nhãn (label.field-required) / class "required" và báo lỗi dưới ô sau khi bấm Tiếp tục —
# extension đọc thẳng các dấu đó (cả form người nộp lẫn eForm Bản khai) nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" của chủ hồ sơ là ô tự do, không phải thông tin trên giấy tờ.
NO_ASK = ("ghiChu",)
