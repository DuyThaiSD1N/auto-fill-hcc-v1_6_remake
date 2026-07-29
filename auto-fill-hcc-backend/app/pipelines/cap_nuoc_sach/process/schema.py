"""Compact schema for "Thủ tục đăng ký lắp đặt sử dụng nước sạch".

The LLM returns only OCR-derived source facts from CCCD, the water-supply
application form, and the land-use certificate. UI DOM fields are derived in
Python to keep output stable and prevent the model from filling web element
names directly.
"""

FIELDS: list[dict] = [
    # CCCD/CMND người nộp hồ sơ.
    {"name": "Cccd_HoTen", "desc": "Họ tên trên CCCD/CMND của người nộp hồ sơ."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh/CCCD/CMND; có thể đọc từ MRZ mặt sau."},
    {"name": "Cccd_NgaySinh", "desc": "Ngày sinh trên CCCD/CMND, dd/mm/yyyy."},
    {"name": "Cccd_GioiTinh", "desc": 'Giới tính trên CCCD/CMND: "Nam" hoặc "Nữ".'},
    {"name": "Cccd_DanToc", "desc": "Dân tộc nếu giấy tờ/tài khoản định danh OCR có thể hiện rõ."},
    {"name": "Cccd_NgayCap", "desc": "Ngày cấp CCCD/CMND, dd/mm/yyyy."},
    {
        "name": "Cccd_NoiCap",
        "desc": 'Nơi cấp CCCD/CMND từ mặt sau. Nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT..." '
                'thì trả "Cục Cảnh sát quản lý hành chính về trật tự xã hội".',
    },
    {
        "name": "Cccd_QueQuan",
        "desc": "Quê quán/place of origin, object {tinh, xa, diaChi}; ví dụ {tinh:Hải Phòng, xa:Vĩnh Bảo, diaChi:Trung Lập}.",
    },
    {
        "name": "Cccd_ThuongTru",
        "desc": "Nơi thường trú/place of residence, object {tinh, xa, diaChi, fullText} nếu đọc chắc chắn.",
    },

    # Đơn đăng ký/đề nghị cấp nước sạch.
    {"name": "Don_SoDienThoai", "desc": "Số điện thoại/điện thoại liên hệ trong đơn đăng ký cấp nước; số di động VN 10 số."},
    {"name": "Don_DiaChiDeNghiCapNuoc", "desc": "Địa chỉ đề nghị cấp nước/địa chỉ lắp đặt trong đơn đăng ký."},
    {"name": "Don_TenCoQuanToChuc", "desc": "Tên doanh nghiệp/cơ quan/tổ chức đăng ký lắp đặt nếu có."},
    {"name": "Don_MaSoThue", "desc": "Mã số doanh nghiệp/MST của doanh nghiệp/cơ quan/tổ chức nếu có."},

    # Giấy chứng nhận quyền sử dụng đất/quyền sở hữu tài sản gắn liền với đất.
    {"name": "Gcn_SoPhatHanh", "desc": "Số phát hành GCN trên bìa, thường 2 chữ cái + 6-8 số."},
    {"name": "Gcn_SoVaoSo", "desc": 'Số vào sổ cấp GCN nếu có; ví dụ "V.P. 2144". Không dùng field này làm Số GCN/GP.'},
    {"name": "Gcn_NgayCap", "desc": "Ngày ký/cấp giấy chứng nhận ở phần cuối hoặc gần chữ ký, dd/mm/yyyy."},
    {"name": "Gcn_CoQuanCap", "desc": "Cơ quan cấp giấy chứng nhận gần chữ ký/con dấu."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Cccd_NgaySinh", "Cccd_NgayCap", "Gcn_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Cccd_QueQuan", "Cccd_ThuongTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    "CongDan_tenCongDan": "dom-input",
    "CongDan_tenCoQuanToChuc": "dom-input",
    "CongDan_maSoThueNguoiNop": "dom-input",
    "CongDan_ngaySinhCongDan": "dom-input",
    "CongDan_gioiTinhCongDan": "dom-select",
    "CongDan_danTocCongDan": "dom-select",
    "CongDan_soCmnd": "dom-input",
    "CongDan_ngayCapCmnd": "dom-input",
    "CongDan_noiCapCmnd": "dom-input",
    "CongDan_maTinhThanh": "dom-select",
    "CongDan_maPhuongXa": "dom-select",
    "CongDan_diaChi": "dom-input",
    "CongDan_diDong": "dom-input",
    "CongDan_maDMQuocGia": "dom-select",
    "CongDan_diaChiNuocNgoai": "dom-input",
    "CongDan_soGCNGP": "dom-input",
    "CongDan_ngayCapGCNGP": "dom-input",
    "CongDan_noiCapGCNGP": "dom-input",
    "CongDan_soCCCD": "dom-input",
    "CongDan_noiOHienTai": "dom-input",
    "CongDan_diaChiThuongTru": "dom-input",
}

UI_ALIASES = {
    "CongDan_tenCoQuanToChuc": ["tenCoQuanToChuc"],
    "CongDan_maSoThueNguoiNop": ["maSoThueNguoiNop"],
    "CongDan_maTinhThanh": ["maTinhThanh"],
    "CongDan_maPhuongXa": ["maPhuongXa"],
    "CongDan_diaChi": ["diaChi"],
    "CongDan_diDong": ["diDong"],
    "CongDan_maDMQuocGia": ["maDMQuocGia"],
    "CongDan_diaChiNuocNgoai": ["diaChiNuocNgoai"],
    "CongDan_soGCNGP": ["soGCNGP"],
    "CongDan_ngayCapGCNGP": ["ngayCapGCNGP"],
    "CongDan_noiCapGCNGP": ["noiCapGCNGP"],
    "CongDan_soCCCD": ["soCCCD"],
    "CongDan_noiOHienTai": ["noiOHienTai"],
    "CongDan_diaChiThuongTru": ["diaChiThuongTru"],
}
