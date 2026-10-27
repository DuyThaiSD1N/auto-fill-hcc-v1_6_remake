"""Bổ sung ô còn trống trên tờ khai chấp thuận vị trí đấu nối tạm vào đường bộ đang khai thác
(Form.io, cổng Bộ Xây dựng dvc.moc.gov.vn)."""

PROCEDURE_KEYS = ("chap-thuan-dau-noi-tam",)

# Form.io gắn class "required" cho ô bắt buộc ngay từ đầu và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó (cả form người nộp lẫn đơn đề nghị và khối theo trường hợp đấu nối) nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" của hồ sơ là ô tự do của cán bộ, không phải thông tin trên giấy tờ. Số điện thoại người được ủy quyền chỉ
# có khi nộp thay theo ủy quyền, giấy tờ người nộp không có số này.
NO_ASK = ("tenHoSo", "AuthorityApplicantPhoneNumber")
