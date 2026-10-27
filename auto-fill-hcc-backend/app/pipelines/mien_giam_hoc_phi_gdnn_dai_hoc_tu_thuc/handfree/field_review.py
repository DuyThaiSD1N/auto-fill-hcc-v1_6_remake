"""Bổ sung ô còn trống trên tờ khai đề nghị miễn, giảm học phí trong cơ sở GDNN, GDĐH tư thục (Form.io, cổng Bộ GD&ĐT
dvc.moet.gov.vn)."""

PROCEDURE_KEYS = ("mien-giam-hoc-phi-gdnn-dai-hoc-tu-thuc",)

# Cổng đánh dấu ô bắt buộc trên nhãn (label.field-required) / class "required" và báo lỗi dưới ô sau khi bấm Tiếp tục —
# extension đọc thẳng các dấu đó (gồm cả phần Đơn Phụ lục IV: nơi sinh, nơi thường trú…) nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" của hồ sơ là ô tự do của cán bộ, không phải thông tin trên giấy tờ.
NO_ASK = ("tenHoSo",)
