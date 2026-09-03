"""Schema nguồn cho đơn hỗ trợ chi phí hỏa táng và khối người được ủy quyền."""

FIELDS: list[dict] = [
    {"name": "Don_KinhGui", "desc": "Cơ quan ở dòng Kính gửi của Đơn đề nghị hỗ trợ kinh phí hỏa táng."},
    {"name": "NguoiChet_HoTen", "desc": "Họ tên NGƯỜI CHẾT tại mục I của Đơn; không lấy người làm đơn/người được ủy quyền."},
    {"name": "NguoiChet_NgaySinh", "desc": "Ngày sinh người chết, dd/mm/yyyy."},
    {"name": "NguoiChet_GioiTinh", "desc": "Giới tính người chết, chỉ trả Nam hoặc Nữ khi hồ sơ ghi rõ."},
    {"name": "NguoiChet_DanToc", "desc": "Dân tộc của người chết tại mục I."},
    {"name": "NguoiChet_SoDinhDanh", "desc": "Số CCCD/định danh của người chết, chỉ giữ chữ số."},
    {"name": "NguoiChet_NgayCap", "desc": "Ngày cấp CCCD của người chết, dd/mm/yyyy; không lấy ngày cấp trích lục khai tử."},
    {"name": "NguoiChet_NoiCap", "desc": "Nơi cấp CCCD của người chết."},
    {"name": "NguoiChet_DiaChiThuongTru", "desc": "Nguyên văn địa chỉ thường trú của người chết để điền vào một ô textarea; không rút gọn."},
    {"name": "NguoiChet_NgayChet", "desc": "Ngày chết theo giấy báo tử/trích lục khai tử, dd/mm/yyyy."},
    {"name": "KhaiTu_So", "desc": "Số giấy báo tử hoặc số trích lục khai tử của người chết; giữ nguyên toàn bộ mã và hậu tố như /TLKT nếu có."},
    {"name": "KhaiTu_CoQuanCap", "desc": "Cơ quan cấp giấy báo tử/trích lục khai tử."},
    {"name": "KhaiTu_NgayCap", "desc": "Ngày cấp giấy báo tử/trích lục khai tử, dd/mm/yyyy; không lấy ngày đăng ký khai tử nếu khác."},
    {"name": "HoaTang_ThoiGian", "desc": "Thời gian hỏa táng ghi trong Đơn/Hợp đồng, giữ đủ giờ phút và ngày nếu có."},
    {"name": "HoaTang_DiaDiem", "desc": "Tên và/hoặc địa chỉ cơ sở thực hiện hỏa táng."},
    {"name": "NguoiDungRa_HoTen", "desc": "Họ tên CHỦ HỘ/NGƯỜI ĐẠI DIỆN đứng ra thực hiện hỏa táng tại mục II của Đơn; không lấy người chết."},
    {"name": "NguoiDungRa_NgaySinh", "desc": "Ngày sinh người đứng ra hỏa táng, dd/mm/yyyy."},
    {"name": "NguoiDungRa_SoDinhDanh", "desc": "Số CCCD/định danh của người đứng ra hỏa táng, chỉ giữ chữ số."},
    {"name": "NguoiDungRa_NgayCap", "desc": "Ngày cấp CCCD của người đứng ra hỏa táng, dd/mm/yyyy."},
    {"name": "NguoiDungRa_NoiCap", "desc": "Nơi cấp CCCD của người đứng ra hỏa táng."},
    {"name": "NguoiDungRa_DiaChiThuongTru", "desc": "Nguyên văn địa chỉ thường trú của người đứng ra hỏa táng để điền vào một ô textarea."},
    {"name": "NguoiDungRa_SoDienThoai", "desc": "Số điện thoại của người đứng ra hỏa táng."},
    {"name": "NguoiDungRa_SoTaiKhoan", "desc": "Số tài khoản nhận hỗ trợ của người đứng ra hỏa táng/người được chỉ định trong Đơn."},
    {"name": "NguoiDungRa_NganHang", "desc": "Tên ngân hàng mở tài khoản nhận hỗ trợ."},
    {"name": "NguoiDungRa_QuanHeVoiNguoiChet", "desc": "Quan hệ của người đứng ra hỏa táng với người chết, ví dụ con, con dâu; giữ theo hồ sơ."},
    {"name": "Don_CoQuanDeNghi", "desc": "Tên UBND xã/phường ở câu 'Trân trọng đề nghị ... hỗ trợ'."},
    {"name": "Don_NgayLap", "desc": "Ngày lập/ký Đơn đề nghị hỗ trợ kinh phí hỏa táng, dd/mm/yyyy."},
    {
        "name": "UyQuyen_CoBienBan",
        "desc": "Boolean true CHỈ khi hồ sơ có tài liệu độc lập mang tiêu đề/nội dung Biên bản hoặc Văn bản ủy quyền; không suy từ việc người làm đơn khác người chết.",
    },
    {"name": "NguoiDuocUyQuyen_HoTen", "desc": "Họ tên BÊN ĐƯỢC ỦY QUYỀN trong Biên bản/Văn bản ủy quyền; không lấy bên ủy quyền."},
    {"name": "NguoiDuocUyQuyen_NgaySinh", "desc": "Ngày sinh bên được ủy quyền, dd/mm/yyyy."},
    {"name": "NguoiDuocUyQuyen_GioiTinh", "desc": "Giới tính bên được ủy quyền, chỉ Nam hoặc Nữ khi giấy tờ ghi rõ."},
    {"name": "NguoiDuocUyQuyen_SoDinhDanh", "desc": "Số CCCD/định danh của bên được ủy quyền, chỉ giữ chữ số."},
    {"name": "NguoiDuocUyQuyen_NgayCap", "desc": "Ngày cấp CCCD của bên được ủy quyền, dd/mm/yyyy."},
    {"name": "NguoiDuocUyQuyen_NoiCap", "desc": "Nơi cấp CCCD của bên được ủy quyền."},
    {
        "name": "NguoiDuocUyQuyen_ThuongTru",
        "desc": "Địa chỉ của bên được ủy quyền, object {quocGia,tinh,xa,diaChi}; ưu tiên Biên bản ủy quyền rồi CCCD đúng người.",
    },
    {"name": "NguoiDuocUyQuyen_Email", "desc": "Email của bên được ủy quyền nếu hồ sơ ghi rõ; không tự tạo."},
    {"name": "NguoiDuocUyQuyen_SoDienThoai", "desc": "Số điện thoại của bên được ủy quyền nếu hồ sơ ghi rõ."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "NguoiChet_NgaySinh",
    "NguoiChet_NgayCap",
    "NguoiChet_NgayChet",
    "KhaiTu_NgayCap",
    "NguoiDungRa_NgaySinh",
    "NguoiDungRa_NgayCap",
    "Don_NgayLap",
    "NguoiDuocUyQuyen_NgaySinh",
    "NguoiDuocUyQuyen_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
COMPACT_COMP_BY_NAME["NguoiDuocUyQuyen_ThuongTru"] = "x-select-area"
