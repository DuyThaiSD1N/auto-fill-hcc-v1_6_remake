"""Facts nguồn cho hồ sơ chấm dứt hoạt động hộ kinh doanh."""

FIELDS: list[dict] = [
    {"name": "HoKinhDoanh_MaSo", "desc": (
        "Mã số hộ kinh doanh. "
        "CHỈ lấy khi có nhãn rõ ràng 'Mã số hộ kinh doanh', 'MST', 'Số đăng ký' trên Thông báo chấm dứt hoặc GCN đăng ký HKD. "
        "TUYỆT ĐỐI KHÔNG lấy số định danh/CCCD/CMND của bất kỳ cá nhân nào (dù xuất hiện dưới bất kỳ nhãn nào). "
        "Nếu không tìm thấy nhãn rõ ràng → để trống."
    )},
    {"name": "HoKinhDoanh_MaDangKy", "desc": (
        "Mã số đăng ký hộ kinh doanh nếu giấy tờ ghi riêng (khác HoKinhDoanh_MaSo). "
        "TUYỆT ĐỐI KHÔNG lấy số CCCD/CMND."
    )},
    {"name": "HoKinhDoanh_MaNoiBo", "desc": "Mã số nội bộ trong Hệ thống nếu tài liệu có ghi; không tự suy ra."},
    {"name": "HienTai_Ten", "desc": "Tên hộ kinh doanh hiện tại trên GCN hoặc Thông báo chấm dứt."},
    {"name": "ChamDut_LoaiHinh", "desc": "Loại hình/lý do chấm dứt nếu tài liệu ghi rõ; không rõ thì để trống để mapper chọn Lý do khác."},
    {"name": "ChamDut_LyDo", "desc": "Một câu lý do giải thể dựa trên Thông báo chấm dứt và Thông báo hoàn thành nghĩa vụ thuế; nếu có thì giữ số, ngày và cơ quan của thông báo thuế."},
    {"name": "ChuHo", "desc": "Chủ hộ hiện tại theo GCN, object {hoTen,ngaySinh,gioiTinh,soDinhDanh,diaChi,dienThoai,email}; diaChi là {quocGia,tinh,xa,diaChi}."},
    {"name": "NguoiNop", "desc": "Người ký Thông báo chấm dứt hoặc người được ủy quyền, object {hoTen,ngaySinh,gioiTinh,soDinhDanh,diaChi}; không suy từ tên file."},
    {"name": "Cccd_DanhSach", "desc": "Mọi CCCD/căn cước vật lý trong hồ sơ, array {hoTen,ngaySinh,gioiTinh,soDinhDanh,ngayCap,noiCap,diaChi}; mỗi thẻ một object, không tự gán vai trò."},

    # ===== GIẤY ỦY QUYỀN =====
    # Người nộp thay có thể CHỈ xuất hiện trong Giấy ủy quyền (hồ sơ không kèm CCCD của họ). Nhóm
    # field này là nguồn nhân thân cho trường hợp đó; mapper gộp vào __identityCandidates để extension
    # đối chiếu với tài khoản đang đăng nhập y như đối chiếu CCCD.
    {
        "name": "UyQuyen_CoGiayUyQuyen",
        "desc": "Boolean: true nếu hồ sơ có văn bản GIẤY ỦY QUYỀN riêng (không phải chỉ có 2 CCCD).",
    },
    {
        "name": "UyQuyen_NguoiUyQuyen_HoTen",
        "desc": 'Họ tên BÊN ỦY QUYỀN (thường là chủ hộ kinh doanh), đọc ở mục "Bên ủy quyền".',
    },
    {
        "name": "UyQuyen_NguoiUyQuyen_SoDinhDanh",
        "desc": "Số định danh/CCCD của bên ủy quyền.",
    },
    {
        "name": "UyQuyen_NguoiDuocUyQuyen_HoTen",
        "desc": 'Họ tên BÊN ĐƯỢC ỦY QUYỀN (người đi nộp hồ sơ thay), đọc ở mục "Bên được ủy quyền".',
    },
    {
        "name": "UyQuyen_NguoiDuocUyQuyen_SoDinhDanh",
        "desc": "Số định danh/CCCD của bên được ủy quyền.",
    },
    {
        "name": "UyQuyen_NguoiDuocUyQuyen_GioiTinh",
        "desc": 'Giới tính bên được ủy quyền: "Nam" hoặc "Nữ"; chỉ trả khi giấy tờ ghi rõ.',
    },
    {
        "name": "UyQuyen_NguoiDuocUyQuyen_NgaySinh",
        "desc": "Ngày sinh bên được ủy quyền, dd/mm/yyyy; chỉ trả khi giấy tờ ghi rõ.",
    },
    {
        "name": "UyQuyen_NguoiDuocUyQuyen_DiaChi",
        "desc": (
            "Địa chỉ bên được ủy quyền, object {quocGia,tinh,xa,diaChi}; ưu tiên 'Nơi thường trú' trên "
            "CCCD của người đó, không có thẻ thì lấy dòng Địa chỉ trong Giấy ủy quyền. BỎ cấp huyện."
        ),
    },
    {
        "name": "UyQuyen_NguoiDuocUyQuyen_DienThoai",
        "desc": "Số điện thoại bên được ủy quyền nếu Giấy ủy quyền có ghi.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "raw" for name in ALLOWED}
