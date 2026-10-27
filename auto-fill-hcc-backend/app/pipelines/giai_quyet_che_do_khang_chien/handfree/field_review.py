"""Bổ sung ô còn trống trên tờ khai giải quyết chế độ người hoạt động kháng chiến
(Form.io, cổng Bộ Nội vụ dichvucongbnv.moha.gov.vn)."""

PROCEDURE_KEYS = ("giai-quyet-che-do-khang-chien",)

# Cổng đánh dấu ô bắt buộc trên nhãn (label.field-required) / class "required" và báo lỗi dưới ô sau khi bấm Tiếp tục —
# extension đọc thẳng các dấu đó (cả form người nộp lẫn eForm thủ tục) nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" của chủ hồ sơ là ô tự do, không phải thông tin trên giấy tờ.
NO_ASK = ("ghiChu",)
