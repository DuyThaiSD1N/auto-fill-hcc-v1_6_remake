"""Bổ sung ô còn trống trên tờ khai cấp phép sử dụng tạm thời lòng đường, vỉa hè vào mục đích khác (Form.io, cổng Bộ
Xây dựng dvc.moc.gov.vn)."""

PROCEDURE_KEYS = ("cap-phep-long-duong-via-he",)

# Form.io gắn class "required" cho ô bắt buộc ngay từ đầu và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó (cả form người nộp, khối doanh nghiệp lẫn đơn đề nghị) nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" của hồ sơ là ô tự do của cán bộ, không phải thông tin trên giấy tờ. Số điện thoại người được ủy quyền chỉ
# có khi nộp thay theo ủy quyền, giấy tờ người nộp không có số này.
NO_ASK = ("tenHoSo", "AuthorityApplicantPhoneNumber")
