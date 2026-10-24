"""Bổ sung ô còn trống trên tờ khai cấp giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm (Form.io, cổng Bộ Y tế
dichvucongbyt.moh.gov.vn)."""

PROCEDURE_KEYS = ("cap-giay-chung-nhan-co-so-du-dieu-kien-an-toan-thuc-pham",)

# Cổng đánh dấu ô bắt buộc trên nhãn (label.field-required) và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" của chủ hồ sơ là ô tự do, không phải thông tin trên giấy tờ.
NO_ASK = ("ghiChu",)
