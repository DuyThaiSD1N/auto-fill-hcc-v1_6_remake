"""Bổ sung ô còn trống trên tờ khai cấp điều chỉnh giấy phép xây dựng (Form.io, cổng Bộ Xây dựng dvc.moc.gov.vn)."""

PROCEDURE_KEYS = ("dieu-chinh-giay-phep-xay-dung",)

# Form.io gắn class "required" cho ô bắt buộc ngay từ đầu và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó (cả form người nộp lẫn form chủ đầu tư / công trình) nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" của hồ sơ là ô tự do của cán bộ, không phải thông tin trên giấy tờ.
NO_ASK = ("tenHoSo",)
