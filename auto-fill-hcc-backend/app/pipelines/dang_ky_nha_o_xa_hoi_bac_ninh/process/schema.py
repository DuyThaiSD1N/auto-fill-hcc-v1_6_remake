"""Schema nguồn cho Đơn đăng ký nhà ở xã hội (Giấy xác nhận điều kiện nhà ở, Mẫu 02) + khối ủy quyền.

Nguồn hồ sơ: CCCD (2 vợ chồng), Giấy chứng nhận kết hôn, 2 bản Giấy xác nhận điều kiện nhà ở (Mẫu 02).
NGƯỜI KÊ KHAI (mục 2-5) và VỢ/CHỒNG (mục 6) là HAI người khác nhau — tách riêng, không lẫn.
"""

FIELDS: list[dict] = [
    # --- Đơn Mẫu 02 (Giấy xác nhận về điều kiện nhà ở) ---
    {"name": "Don_KinhGui", "desc": "Cơ quan ở dòng '1. Kính gửi' đầu Giấy xác nhận điều kiện nhà ở "
        "(Mẫu 02) — cơ quan có thẩm quyền cấp GCN QSDĐ nơi có dự án nhà ở xã hội."},

    # NGƯỜI KÊ KHAI (chủ hồ sơ đứng đơn, mục 2-5).
    {"name": "NguoiKeKhai_HoTen", "desc": "Họ và tên NGƯỜI KÊ KHAI (người đứng đơn) — mục '2. Họ và tên'. "
        "Ưu tiên CCCD (viết HOA), đối chiếu tờ khai. KHÔNG lấy tên vợ/chồng ở mục 6."},
    {"name": "NguoiKeKhai_SoCCCD", "desc": "Số CCCD/định danh NGƯỜI KÊ KHAI — mục '3. Căn cước công dân số'. "
        "Ưu tiên CCCD, chỉ chữ số, đủ 12 số. KHÔNG lấy số CMND 9 số cũ trên Giấy chứng nhận kết hôn."},
    {"name": "NguoiKeKhai_NgayCap", "desc": "Ngày cấp CCCD NGƯỜI KÊ KHAI (mặt sau CCCD / 'cấp ngày' mục 3), "
        "dd/mm/yyyy."},
    {"name": "NguoiKeKhai_NoiCap", "desc": "Nơi cấp CCCD NGƯỜI KÊ KHAI ('tại' mục 3). CCCD gắn chip không in "
        "nhãn 'Nơi cấp' → ghi 'Cục Cảnh sát quản lý hành chính về trật tự xã hội'; căn cước mới → 'Bộ Công an'."},
    {"name": "NguoiKeKhai_NoiOHienTai", "desc": "NƠI Ở HIỆN TẠI người kê khai — mục '4. Nơi ở hiện tại'. "
        "CHUỖI địa chỉ đầy đủ MỘT DÒNG (số nhà/đường/tổ + phường/xã + tỉnh), ghi theo tên hành chính hiện "
        "hành. Ưu tiên tờ khai Mẫu 02 (chi tiết nhất)."},
    {"name": "NguoiKeKhai_DangKyThuongTru", "desc": "ĐĂNG KÝ THƯỜNG TRÚ (đăng ký tạm trú) — mục '5'. CHUỖI "
        "địa chỉ đầy đủ MỘT DÒNG. Ưu tiên nơi thường trú trên CCCD (quy đổi tên hành chính hiện hành)."},

    # VỢ/CHỒNG (mục 6) — người khác người kê khai.
    {"name": "VoChong_HoTen", "desc": "Họ và tên VỢ/CHỒNG người kê khai — mục '6. Họ và tên vợ/chồng (nếu "
        "có)'. Lấy ở Giấy chứng nhận kết hôn / CCCD của người vợ/chồng. Bỏ nếu độc thân."},
    {"name": "VoChong_SoCCCD", "desc": "Số CCCD/định danh VỢ/CHỒNG (mục 6). Ưu tiên CCCD của vợ/chồng, chỉ "
        "chữ số. KHÔNG lấy số CMND 9 số cũ trên Giấy chứng nhận kết hôn."},
    {"name": "VoChong_NgayCap", "desc": "Ngày cấp CCCD VỢ/CHỒNG (mặt sau CCCD của họ), dd/mm/yyyy."},
    {"name": "VoChong_NoiCap", "desc": "Nơi cấp CCCD VỢ/CHỒNG. Chuẩn hóa 'Cục Cảnh sát quản lý hành chính "
        "về trật tự xã hội' / 'Bộ Công an'."},

    {"name": "DangKyKetHon_So", "desc": "Số đăng ký kết hôn — mục '7. Đăng ký kết hôn số (nếu có)'. Lấy ở "
        "Giấy chứng nhận kết hôn (mục 'Số:'/'Quyển số:'). Bỏ nếu độc thân."},
    {"name": "DoiTuong", "desc": "Nội dung '8. Là đối tượng' — 1 trong các nhóm đối tượng hưởng nhà ở xã hội "
        "ghi trên tờ khai Mẫu 02 (vd 'Công nhân, người lao động đang làm việc tại doanh nghiệp...'). Chép "
        "NGUYÊN VĂN nhóm đã ghi trong đơn."},
    {"name": "TinhDuAn", "desc": "Tên tỉnh/thành phố nơi có dự án nhà ở xã hội — mục 9 ('...tại tỉnh/Thành "
        "phố ...'). Thường là 'Tỉnh Bắc Ninh'."},

    {"name": "Don_NoiKhai", "desc": "Địa danh nơi khai đơn (dòng ký cuối Mẫu 02) — thường 'Bắc Ninh'. Nếu "
        "không rõ, bỏ (cổng để sẵn 'Bắc Ninh')."},
    {"name": "Don_NgayKhai", "desc": "Ngày ký/khai đơn ở dòng ký cuối Mẫu 02, dd/mm/yyyy. Lấy đúng ngày trên "
        "bản giấy đã ký."},

    # --- Khối NGƯỜI ĐƯỢC ỦY QUYỀN (chỉ khi nộp thay & có Văn bản ủy quyền độc lập) ---
    {"name": "UyQuyen_CoVanBan", "desc": "Boolean true CHỈ khi hồ sơ có tài liệu độc lập mang tiêu đề/nội "
        "dung Giấy/Văn bản ủy quyền; không suy từ việc hồ sơ có 2 vợ chồng."},
    {"name": "NguoiDuocUyQuyen_HoTen", "desc": "Họ tên BÊN ĐƯỢC ỦY QUYỀN trong Văn bản ủy quyền; không lấy "
        "bên ủy quyền."},
    {"name": "NguoiDuocUyQuyen_GioiTinh", "desc": "Giới tính bên được ủy quyền, chỉ 'Nam' hoặc 'Nữ' khi giấy "
        "tờ ghi rõ."},
    {"name": "NguoiDuocUyQuyen_SoDinhDanh", "desc": "Số CCCD/định danh bên được ủy quyền, chỉ chữ số."},
    {"name": "NguoiDuocUyQuyen_NgayCap", "desc": "Ngày cấp CCCD bên được ủy quyền, dd/mm/yyyy."},
    {"name": "NguoiDuocUyQuyen_NoiCap", "desc": "Nơi cấp CCCD bên được ủy quyền."},
    {"name": "NguoiDuocUyQuyen_NgaySinh", "desc": "Ngày sinh bên được ủy quyền, dd/mm/yyyy."},
    {"name": "NguoiDuocUyQuyen_ThuongTru", "desc": "Địa chỉ bên được ủy quyền, object {quocGia,tinh,xa,"
        "diaChi}; ưu tiên Văn bản ủy quyền rồi CCCD đúng người. Dùng cho dropdown Tỉnh/Xã của khối ủy quyền."},
    {"name": "NguoiDuocUyQuyen_Email", "desc": "Email bên được ủy quyền nếu hồ sơ ghi rõ; không tự tạo."},
    {"name": "NguoiDuocUyQuyen_SoDienThoai", "desc": "Số điện thoại bên được ủy quyền nếu hồ sơ ghi rõ."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "NguoiKeKhai_NgayCap",
    "VoChong_NgayCap",
    "Don_NgayKhai",
    "NguoiDuocUyQuyen_NgaySinh",
    "NguoiDuocUyQuyen_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
COMPACT_COMP_BY_NAME["NguoiDuocUyQuyen_ThuongTru"] = "x-select-area"
