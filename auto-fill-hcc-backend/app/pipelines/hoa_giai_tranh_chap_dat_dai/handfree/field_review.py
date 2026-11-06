"""Bổ sung ô còn trống trên tờ khai Hòa giải tranh chấp đất đai (Form.io, cổng NN&MT dichvucongnnmt.mae.gov.vn)."""

PROCEDURE_KEYS = ("hoa-giai-tranh-chap-dat-dai",)

# Cổng đánh dấu ô bắt buộc trên nhãn (label.field-required) / class "required" và báo lỗi dưới ô sau khi bấm Tiếp tục —
# extension đọc thẳng các dấu đó nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" là nội dung Đơn do trợ lý chép từ giấy tờ, không phải câu hỏi cho người dân.
NO_ASK = ("ghiChu",)
