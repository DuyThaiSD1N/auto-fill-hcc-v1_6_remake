"""Bổ sung ô còn trống trên tờ khai xóa đăng ký phương tiện thủy nội địa (Form.io, cổng Bộ Xây dựng dvc.moc.gov.vn)."""

PROCEDURE_KEYS = ("xoa-dang-ky-phuong-tien-thuy",)

# Form.io gắn class "required" cho ô bắt buộc ngay từ đầu và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" là ô tự do của cán bộ; số điện thoại người được ủy quyền chỉ có khi nộp thay theo ủy quyền; người đại diện
# các đồng sở hữu (cá nhân / tổ chức) chỉ có khi phương tiện có nhiều đồng sở hữu.
NO_ASK = ("tenHoSo", "AuthorityApplicantPhoneNumber", "nguoiDaiDien", "dongSoHuu")
