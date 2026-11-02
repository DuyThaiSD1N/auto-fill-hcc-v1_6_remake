"""Bổ sung ô còn trống trên tờ khai cấp bổ sung, cấp lại giấy phép xe tập lái (Form.io, cổng Bộ
Xây dựng dvc.moc.gov.vn)."""

PROCEDURE_KEYS = ("cap-bo-sung-xe-tap-lai-cap-lai-giay-phep-xe-tap-lai",)

# Form.io gắn class "required" cho ô bắt buộc ngay từ đầu và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó (cả form người nộp, cơ sở đào tạo lẫn bảng danh sách xe) nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" của hồ sơ là ô tự do của cán bộ, không phải thông tin trên giấy tờ. Số điện thoại người được ủy quyền chỉ
# có khi nộp thay theo ủy quyền, giấy tờ người nộp không có số này.
NO_ASK = ("tenHoSo", "AuthorityApplicantPhoneNumber")
