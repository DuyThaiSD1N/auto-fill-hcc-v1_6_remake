"""Bổ sung ô còn trống trên tờ khai cấp mới chứng chỉ hành nghề môi giới bất động sản (Form.io, cổng Bộ Xây dựng
dvc.moc.gov.vn)."""

PROCEDURE_KEYS = ("cap-moi-chung-chi-hanh-nghe-moi-gioi-bat-dong-san",)

# Form.io gắn class "required" cho ô bắt buộc ngay từ đầu và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" của hồ sơ là ô tự do của cán bộ, không phải thông tin trên giấy tờ.
NO_ASK = ("tenHoSo",)
