"""Schema nguồn cho thông tin người cao tuổi trong khối ủy quyền Bắc Ninh."""

FIELDS = [
    {"name": "NguoiCaoTuoi_HoTen", "desc": "Họ tên người cao tuổi được đề nghị hỗ trợ, lấy từ CCCD hoặc tờ khai."},
    {"name": "NguoiCaoTuoi_GioiTinh", "desc": "Giới tính người cao tuổi, chỉ trả Nam hoặc Nữ nếu giấy tờ có."},
    {"name": "NguoiCaoTuoi_SoDinhDanh", "desc": "Số CCCD/số định danh cá nhân của người cao tuổi."},
    {"name": "NguoiCaoTuoi_NgayCap", "desc": "Ngày cấp CCCD, định dạng dd/mm/yyyy."},
    {"name": "NguoiCaoTuoi_NoiCap", "desc": "Nơi cấp CCCD."},
    {"name": "NguoiCaoTuoi_NgaySinh", "desc": "Ngày sinh, định dạng dd/mm/yyyy."},
    {"name": "NguoiCaoTuoi_ThuongTru", "desc": "Địa chỉ hiện tại dạng object quocGia/tinh/xa/diaChi."},
    {"name": "NguoiCaoTuoi_Email", "desc": "Email nếu có trong hồ sơ."},
    {"name": "NguoiCaoTuoi_SoDienThoai", "desc": "Số điện thoại nếu có trong hồ sơ."},
]
ALLOWED = {f["name"] for f in FIELDS}
ALIASES = {}
COMPACT_COMP_BY_NAME = {f["name"]: "x-input" for f in FIELDS}

