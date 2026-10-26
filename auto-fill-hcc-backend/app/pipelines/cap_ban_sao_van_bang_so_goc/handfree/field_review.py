"""Bổ sung ô còn trống trên tờ khai cấp bản sao văn bằng, chứng chỉ từ sổ gốc (Form.io, cổng Bộ GD&ĐT dvc.moet.gov.vn)."""

PROCEDURE_KEYS = ("cap-ban-sao-van-bang-so-goc",)

# Cổng đánh dấu ô bắt buộc trên nhãn (label.field-required) / class "required" và báo lỗi dưới ô sau khi bấm Tiếp tục —
# extension đọc thẳng các dấu đó (gồm cả phần Đơn đề nghị: lý do, thông tin khác…) nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" của hồ sơ là ô tự do của cán bộ, không phải thông tin trên giấy tờ.
NO_ASK = ("tenHoSo",)
