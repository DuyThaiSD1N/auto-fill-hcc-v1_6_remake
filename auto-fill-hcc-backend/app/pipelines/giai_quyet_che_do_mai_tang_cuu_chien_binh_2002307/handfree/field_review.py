"""Bổ sung ô còn trống trên tờ khai giải quyết chế độ mai táng phí đối với cựu chiến binh (Form.io, cổng Bộ Nội vụ)."""

PROCEDURE_KEYS = ("giai-quyet-che-do-mai-tang-cuu-chien-binh-2002307",)

# Cổng đánh dấu ô bắt buộc trên nhãn (label.field-required) / class "required" và báo lỗi dưới ô sau khi bấm Tiếp tục —
# extension đọc thẳng các dấu đó (cả form người nộp lẫn eForm mẫu khai) nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" của chủ hồ sơ là ô tự do, không phải thông tin trên giấy tờ.
NO_ASK = ("ghiChu",)
