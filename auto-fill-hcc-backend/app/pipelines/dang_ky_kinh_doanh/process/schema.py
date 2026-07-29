"""Compact schema for "Đăng ký kinh doanh hộ kinh doanh".

The model returns source facts once. The mapper chooses the concrete UI fields
for the requested page so the extension can fill one WebForms page at a time.
"""

PAGES: list[dict] = [
    {"key": "hinh-thuc-dang-ky", "label": "Hình thức đăng ký"},
    {"key": "dia-chi", "label": "Địa chỉ"},
    {"key": "nganh-nghe-kinh-doanh", "label": "Ngành nghề kinh doanh"},
    {"key": "ten-ho-kinh-doanh", "label": "Tên hộ kinh doanh"},
    {"key": "chu-ho-kinh-doanh", "label": "Thông tin về chủ hộ kinh doanh"},
    {"key": "thong-tin-ve-von", "label": "Thông tin về vốn"},
    {"key": "thong-tin-ve-thue", "label": "Thông tin về thuế"},
    {"key": "nguoi-nop-ho-so", "label": "Người nộp hồ sơ"},
]

DEFAULT_PAGE = "hinh-thuc-dang-ky"

FIELDS: list[dict] = [
    {
        "name": "HinhThucDangKy",
        "desc": 'Hình thức đăng ký hồ sơ, thường là "Thành lập mới hộ kinh doanh".',
    },
    {"name": "HoKinhDoanh_Ten", "desc": "Tên hộ kinh doanh bằng tiếng Việt."},
    {"name": "HoKinhDoanh_TenNuocNgoai", "desc": "Tên hộ kinh doanh bằng tiếng nước ngoài nếu có."},
    {"name": "HoKinhDoanh_TenVietTat", "desc": "Tên hộ kinh doanh viết tắt nếu có."},
    {
        "name": "TruSo_DiaChi",
        "desc": "Địa chỉ trụ sở hộ kinh doanh, object {quocGia,tinh,xa,diaChi}.",
    },
    {"name": "TruSo_DienThoai", "desc": "Số điện thoại trụ sở/hộ kinh doanh."},
    {"name": "TruSo_Email", "desc": "Email liên hệ của hộ kinh doanh."},
    {"name": "TruSo_Fax", "desc": "Fax của hộ kinh doanh nếu có."},
    {"name": "TruSo_Website", "desc": "Website của hộ kinh doanh nếu có."},
    {
        "name": "NganhNghe_DanhSach",
        "desc": ("Danh sách ngành nghề, array object {ma,ten,chinh}. LẤY MỌI dòng có tên ngành KỂ CẢ khi cột "
                 "mã ngành trống (ma=\"\", vẫn phải có ten). chinh=true nếu là ngành nghề kinh doanh chính."),
    },
    {"name": "NganhNghe_MaChinh", "desc": "Mã ngành nghề kinh doanh chính nếu đọc được."},
    {"name": "NganhNghe_TenChinh", "desc": "Tên ngành nghề kinh doanh chính nếu đọc được."},
    {"name": "ChuHo_HoTen", "desc": "Họ tên chủ hộ kinh doanh."},
    {"name": "ChuHo_GioiTinh", "desc": 'Giới tính chủ hộ: "Nam" hoặc "Nữ".'},
    {"name": "ChuHo_NgaySinh", "desc": "Ngày sinh chủ hộ, dd/mm/yyyy hoặc mm/yyyy/năm nếu giấy chỉ ghi vậy."},
    {"name": "ChuHo_SoDinhDanh", "desc": "Số định danh cá nhân/CCCD của chủ hộ."},
    {
        "name": "ChuHo_DiaChi",
        "desc": "Nơi ở hiện tại/thường trú của chủ hộ, object {quocGia,tinh,xa,diaChi}.",
    },
    {"name": "ChuHo_DienThoai", "desc": "Số điện thoại của chủ hộ."},
    {"name": "ChuHo_Email", "desc": "Email của chủ hộ."},
    {"name": "ChuHo_Fax", "desc": "Fax của chủ hộ nếu có."},
    {"name": "ChuHo_Website", "desc": "Website của chủ hộ nếu có."},
    {"name": "Von_SoTien", "desc": "Vốn kinh doanh, chỉ lấy số tiền, đơn vị đồng."},
    {
        "name": "Thue_DiaChiNhanThongBao",
        "desc": "Địa chỉ nhận thông báo thuế nếu khác trụ sở, object {quocGia,tinh,xa,diaChi}.",
    },
    {"name": "Thue_DienThoai", "desc": "Điện thoại người/địa chỉ nhận thông báo thuế."},
    {"name": "Thue_Fax", "desc": "Fax nhận thông báo thuế nếu có."},
    {"name": "Thue_Email", "desc": "Email nhận thông báo thuế."},
    {"name": "Thue_NgayBatDau", "desc": "Ngày bắt đầu hoạt động kinh doanh, dd/mm/yyyy."},
    {"name": "Thue_SoLaoDong", "desc": "Số lượng lao động dự kiến."},
    {
        "name": "Thue_PhuongPhapTinh",
        "desc": 'Phương pháp tính thuế nếu giấy ghi rõ, ví dụ "Phương pháp kê khai".',
    },
    {"name": "NguoiNop_HoTen", "desc": "Họ tên người nộp hồ sơ."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh người nộp hồ sơ."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số định danh cá nhân/CCCD của người nộp hồ sơ."},
    {
        "name": "NguoiNop_DiaChi",
        "desc": "Nơi ở hiện tại của người nộp hồ sơ, object {quocGia,tinh,xa,diaChi}.",
    },
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại người nộp hồ sơ."},
    {"name": "NguoiNop_Email", "desc": "Email người nộp hồ sơ."},
    {"name": "NguoiNop_Fax", "desc": "Fax người nộp hồ sơ nếu có."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("TruSo_DiaChi", "ChuHo_DiaChi", "Thue_DiaChiNhanThongBao", "NguoiNop_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"
for _name in ("ChuHo_NgaySinh", "Thue_NgayBatDau", "NguoiNop_NgaySinh"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
COMPACT_COMP_BY_NAME["NganhNghe_DanhSach"] = "raw"

