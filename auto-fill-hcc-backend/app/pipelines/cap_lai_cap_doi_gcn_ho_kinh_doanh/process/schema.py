"""Facts nguồn cho hồ sơ cấp lại/cấp đổi GCN đăng ký hộ kinh doanh."""

FIELDS: list[dict] = [
    {"name": "HoKinhDoanh_MaSo", "desc": "Mã số hộ kinh doanh trên Giấy đề nghị hoặc GCN; chỉ bỏ ký tự phân cách, không ép độ dài."},
    {"name": "HoKinhDoanh_MaDangKy", "desc": "Mã số đăng ký hộ kinh doanh nếu tài liệu ghi riêng; không tự suy ra."},
    {"name": "HoKinhDoanh_MaNoiBo", "desc": "Mã số nội bộ trong Hệ thống nếu tài liệu ghi; không tự suy ra."},
    {"name": "HienTai_Ten", "desc": "Tên hộ kinh doanh hiện tại trên Giấy đề nghị hoặc GCN."},
    {"name": "DeNghi_Loai", "desc": "Loại yêu cầu: cap_lai nếu xin cấp lại; cap_doi nếu xin cấp đổi sang GCN đăng ký HKD."},
    {"name": "DeNghi_LyDo", "desc": "Lý do cấp lại/cấp đổi đúng nội dung người khai, ví dụ bị mất, hư hỏng hoặc nhu cầu cấp đổi; không tự bịa."},
    {"name": "ChuHo", "desc": "Chủ hộ hiện tại, object {hoTen,ngaySinh,gioiTinh,soDinhDanh,ngayCap,noiCap,diaChi,dienThoai,email}; diaChi là {quocGia,tinh,xa,diaChi}."},
    {"name": "NguoiKy", "desc": "Người ký Giấy đề nghị hoặc người được ủy quyền, object {hoTen,ngaySinh,gioiTinh,soDinhDanh,ngayCap,noiCap,diaChi}; không suy từ tên file."},
    {"name": "Cccd_DanhSach", "desc": "Mọi CCCD/căn cước vật lý trong hồ sơ, array {hoTen,ngaySinh,gioiTinh,soDinhDanh,ngayCap,noiCap,diaChi}; mỗi thẻ một object, không tự gán vai trò."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "raw" for name in ALLOWED}
