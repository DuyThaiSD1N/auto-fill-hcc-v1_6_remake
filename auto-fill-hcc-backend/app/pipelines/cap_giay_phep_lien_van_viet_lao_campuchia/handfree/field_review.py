"""Bổ sung ô còn trống trên tờ khai cấp, cấp lại Giấy phép liên vận giữa Việt Nam, Lào và Campuchia (1.002877, Form.io
cổng Bộ Xây dựng) — cùng khuôn bản Việt – Lào."""

PROCEDURE_KEYS = ("cap-giay-phep-lien-van-viet-lao-campuchia",)

# Form.io gắn class "required" cho ô bắt buộc và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng các dấu đó.
REQUIRED = ()

# "Ghi chú" là ô tự do của cán bộ; SĐT người được ủy quyền chỉ có khi nộp thay theo ủy quyền. Khối tuyến cố định (tuyến,
# bến xe, cự ly, công văn) và Loại hình / Tuyến vận tải quốc tế chỉ dành cho xe chở khách tuyến cố định — Giấy đề nghị phi
# thương mại không có. Cột bảng danh sách phương tiện do cổng đổ theo biển số chọn từ tài khoản: không hỏi từng cột.
NO_ASK = (
    "tenHoSo", "AuthorityApplicantPhoneNumber",
    "LoaiHinhKinhDoanhQuocTe1", "T_TuyenVanTaiQuocTe", "tuyendi", "diemden", "benxedi", "tinhdi", "benxeden", "tinhden",
    "culy", "hanhtrinh", "thongbao", "congvan", "ngaycongvan",
    "LoaiPhuongTien", "BienSoXe", "MauSon", "NienHanSuDung", "HinhThucHoatDong", "CuaKhau", "NhanHieu",
    "NamSanXuat", "SoChoNgoi", "SoKhung", "NgayCap", "NgayHetHan", "SoMay",
)
