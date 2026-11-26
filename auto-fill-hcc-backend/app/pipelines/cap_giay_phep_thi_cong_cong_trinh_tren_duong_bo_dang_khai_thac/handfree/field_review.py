"""Bổ sung ô còn trống trên tờ khai cấp giấy phép thi công công trình trên đường bộ đang khai thác (Form.io, cổng
Bộ Xây dựng dvc.moc.gov.vn)."""

PROCEDURE_KEYS = ("cap-giay-phep-thi-cong-cong-trinh-tren-duong-bo-dang-khai-thac",)

# Form.io gắn class "required" cho ô bắt buộc ngay từ đầu và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" (tenHoSo) là ô tự do; SĐT người được ủy quyền chỉ khi nộp thay theo ủy quyền.
NO_ASK = ("tenHoSo", "AuthorityApplicantPhoneNumber")
