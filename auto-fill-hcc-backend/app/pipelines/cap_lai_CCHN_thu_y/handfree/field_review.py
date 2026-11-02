"""Bổ sung ô còn trống trên tờ khai cấp lại chứng chỉ hành nghề thú y (Form.io, cổng NN&MT dichvucongnnmt.mae.gov.vn)."""

PROCEDURE_KEYS = ("cap-lai-chung-chi-hanh-nghe-thu-y",)

# Cổng đánh dấu ô bắt buộc trên nhãn (label.field-required) / class "required" và báo lỗi dưới ô sau khi bấm Tiếp tục —
# extension đọc thẳng các dấu đó nên không khai thêm tên ô. Mục "Đã được cấp chứng chỉ" (selectboxes) extension không hỏi.
REQUIRED = ()

# "Ghi chú" của chủ hồ sơ là ô tự do, không phải thông tin trên giấy tờ.
NO_ASK = ("ghiChu",)
