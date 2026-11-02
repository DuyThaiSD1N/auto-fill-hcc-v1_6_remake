"""Bổ sung ô còn trống trên tờ khai gia hạn giấy phép xây dựng (Form.io, cổng Bộ Xây dựng dvc.moc.gov.vn)."""

PROCEDURE_KEYS = ("gia-han-giay-phep-xay-dung",)

# Form.io gắn class "required" cho ô bắt buộc ngay từ đầu và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó (cả form người nộp, khối chủ đầu tư lẫn giấy phép đã cấp) nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" của hồ sơ là ô tự do của cán bộ, không phải thông tin trên giấy tờ. Số điện thoại người được ủy quyền chỉ
# có khi nộp thay theo ủy quyền, giấy tờ người nộp không có số này.
NO_ASK = ("tenHoSo", "AuthorityApplicantPhoneNumber")
