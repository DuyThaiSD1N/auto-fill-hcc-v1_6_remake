"""Bổ sung ô còn trống trên tờ khai cấp giấy phép xây dựng sửa chữa, cải tạo (Form.io, cổng Bộ Xây dựng dvc.moc.gov.vn)."""

PROCEDURE_KEYS = ("sua-chua-cai-tao-gpxd-nha-o-rieng-le", "sua-chua-cai-tao-gpxd-cong-trinh")

# Form.io gắn class "required" cho ô bắt buộc ngay từ đầu và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó (gồm cả khối ô của loại hình công trình đang chọn) nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" của hồ sơ là ô tự do của cán bộ, không phải thông tin trên giấy tờ.
NO_ASK = ("tenHoSo",)
