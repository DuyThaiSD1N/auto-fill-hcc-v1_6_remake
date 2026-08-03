"""Facts nguồn cho hồ sơ chấm dứt hoạt động hộ kinh doanh."""

FIELDS: list[dict] = [
    {"name": "HoKinhDoanh_MaSo", "desc": "Mã số hộ kinh doanh, ưu tiên trên Thông báo chấm dứt hoặc GCN đăng ký HKD; chỉ giữ chữ số."},
    {"name": "HoKinhDoanh_MaDangKy", "desc": "Mã số đăng ký hộ kinh doanh nếu giấy tờ có ghi riêng."},
    {"name": "HoKinhDoanh_MaNoiBo", "desc": "Mã số nội bộ trong Hệ thống nếu tài liệu có ghi; không tự suy ra."},
    {"name": "HienTai_Ten", "desc": "Tên hộ kinh doanh hiện tại trên GCN hoặc Thông báo chấm dứt."},
    {"name": "ChamDut_LoaiHinh", "desc": "Loại hình/lý do chấm dứt nếu tài liệu ghi rõ; không rõ thì để trống để mapper chọn Lý do khác."},
    {"name": "ChamDut_LyDo", "desc": "Một câu lý do giải thể dựa trên Thông báo chấm dứt và Thông báo hoàn thành nghĩa vụ thuế; nếu có thì giữ số, ngày và cơ quan của thông báo thuế."},
    {"name": "ChuHo", "desc": "Chủ hộ hiện tại theo GCN, object {hoTen,ngaySinh,gioiTinh,soDinhDanh,diaChi,dienThoai,email}; diaChi là {quocGia,tinh,xa,diaChi}."},
    {"name": "NguoiNop", "desc": "Người ký Thông báo chấm dứt hoặc người được ủy quyền, object {hoTen,ngaySinh,gioiTinh,soDinhDanh,diaChi}; không suy từ tên file."},
    {"name": "Cccd_DanhSach", "desc": "Mọi CCCD/căn cước vật lý trong hồ sơ, array {hoTen,ngaySinh,gioiTinh,soDinhDanh,ngayCap,noiCap,diaChi}; mỗi thẻ một object, không tự gán vai trò."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "raw" for name in ALLOWED}
