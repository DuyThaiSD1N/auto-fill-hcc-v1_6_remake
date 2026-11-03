"""Bổ sung ô còn trống trên tờ khai cấp, cấp lại Giấy phép liên vận Việt Nam – Lào (Form.io, cổng Bộ Xây dựng
dvc.moc.gov.vn)."""

PROCEDURE_KEYS = ("cap-giay-phep-lien-van-viet-lao",)

# Form.io gắn class "required" cho ô bắt buộc ngay từ đầu và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" của hồ sơ là ô tự do của cán bộ, không phải thông tin trên giấy tờ. Số điện thoại người được ủy quyền chỉ
# có khi nộp thay theo ủy quyền, giấy tờ người nộp không có số này. Bảng danh sách phương tiện (Phần III) do người
# dân chọn biển số từ hồ sơ xe của tài khoản ("Thêm xe"), cổng tự đổ các cột còn lại theo xe đã chọn — hỏi từng cột
# bằng lời sẽ ghi đè/ lệch với dữ liệu xe đã đăng ký.
NO_ASK = (
    "tenHoSo", "AuthorityApplicantPhoneNumber",
    "LoaiPhuongTien", "BienSoXe", "MauSon", "NienHanSuDung", "HinhThucHoatDong", "CuaKhau", "NhanHieu",
    "NamSanXuat", "SoChoNgoi", "SoKhung", "NgayCap", "NgayHetHan", "SoMay",
)
