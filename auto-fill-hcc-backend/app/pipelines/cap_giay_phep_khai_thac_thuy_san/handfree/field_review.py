"""Bổ sung ô còn trống trên tờ khai cấp, cấp lại Giấy phép khai thác thủy sản (Form.io, cổng NN&MT
dichvucongnnmt.mae.gov.vn)."""

PROCEDURE_KEYS = ("cap-giay-phep-khai-thac-thuy-san",)

# Cổng đánh dấu ô bắt buộc trên nhãn (label.field-required) / class "required" và báo lỗi dưới ô sau khi bấm Tiếp tục —
# extension đọc thẳng các dấu đó nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" của chủ hồ sơ là ô tự do, không phải thông tin trên giấy tờ.
NO_ASK = ("ghiChu",)
