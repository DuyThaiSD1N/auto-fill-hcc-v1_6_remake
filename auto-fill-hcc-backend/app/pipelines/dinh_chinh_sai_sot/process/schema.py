"""Compact schema for "Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót".

The LLM returns only OCR-derived source facts from the change application,
CCCD/CMND and land-use certificate documents. UI fields and deterministic
defaults are derived in Python to keep the model output short.
"""

FIELDS: list[dict] = [
    # CCCD/CMND người nộp hồ sơ.
    {"name": "Cccd_HoTen", "desc": "Họ tên trên CCCD/CMND của người nộp hồ sơ."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh/CCCD/CMND; có thể đọc từ MRZ mặt sau."},
    {"name": "Cccd_NgaySinh", "desc": "Ngày sinh trên CCCD/CMND, dd/mm/yyyy."},
    {"name": "Cccd_GioiTinh", "desc": 'Giới tính trên CCCD/CMND: "Nam" hoặc "Nữ".'},
    {"name": "Cccd_DanToc", "desc": "Dân tộc trên CCCD/CMND nếu có."},
    {"name": "Cccd_NgayCap", "desc": "Ngày cấp CCCD/CMND, dd/mm/yyyy."},
    {"name": "Cccd_NoiCap",
     "desc": 'Nơi cấp CCCD/CMND từ mặt sau. Nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT..." '
             'thì trả "Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},
    {"name": "Cccd_NoiCuTru", "desc": "Địa chỉ cư trú/thường trú, object {quocGia,tinh,xa,diaChi} nếu đọc chắc chắn."},

    # Đơn đăng ký biến động đất đai.
    {"name": "Don_DienThoaiLienHe",
     "desc": 'Số tại mục "Điện thoại liên hệ (nếu có)" trên Đơn đăng ký biến động đất đai; '
             "chỉ trả số điện thoại, không lấy số CCCD, số GCN hoặc mã số thuế."},

    # Giấy chứng nhận quyền sử dụng đất/quyền sở hữu tài sản gắn liền với đất.
    {"name": "Gcn_SoPhatHanh",
     "desc": 'Số phát hành GCN trên bìa, thường 2 chữ cái + 6 số;.'},
    {"name": "Gcn_SoVaoSo",
     "desc": 'Số vào sổ cấp GCN nếu có; ví dụ "CH 00120". Không dùng field này làm Số GCN/GP.'},
    {"name": "Gcn_NgayCap",
     "desc": "Ngày ký/cấp giấy chứng nhận ở phần cuối hoặc gần chữ ký, dd/mm/yyyy."},
    {"name": "Gcn_CoQuanCap",
     "desc": 'Cơ quan cấp giấy chứng nhận gần chữ ký/con dấu; ví dụ "UBND Thị xã Lai Châu, tỉnh Lai Châu".'},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Cccd_NgaySinh", "Cccd_NgayCap", "Gcn_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
COMPACT_COMP_BY_NAME["Cccd_NoiCuTru"] = "x-select-area"

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
    "CongDan_maDMQuocGia": "dom-select",
    "CongDan_diaChiNuocNgoai": "dom-input",
    # Địa chỉ nơi cư trú (eForm Lai Châu 2 cấp: tỉnh → xã, KHÔNG huyện). Select cascade như các thủ tục
    # laichau khác (xet_tuyen); extension isAreaSelectName đã nhận maTinhThanh/maPhuongXa.
    "CongDan_maTinhThanh": "dom-select",     # Tỉnh/Thành phố.
    "CongDan_maPhuongXa": "dom-select",      # Phường/Xã (load qua API sau khi chọn tỉnh).
    "CongDan_diaChi": "dom-input",           # Số nhà/đường/bản/tổ/thôn.
    "CongDan_diaChiThuongTru": "dom-input",  # Địa chỉ thường trú (chuỗi đầy đủ).
    "CongDan_noiOHienTai": "dom-input",      # Nơi ở hiện tại (chuỗi đầy đủ).
    "CongDan_diDong": "dom-input",           # Điện thoại liên hệ trên Đơn đăng ký biến động.
    "CongDan_soGCNGP": "dom-input",
    "CongDan_ngayCapGCNGP": "dom-input",
    "CongDan_noiCapGCNGP": "dom-input",
    "CongDan_soCCCD": "dom-input",
}

UI_ALIASES = {
    "CongDan_soGCNGP": ["soGCNGP"],
    "CongDan_ngayCapGCNGP": ["ngayCapGCNGP"],
    "CongDan_noiCapGCNGP": ["noiCapGCNGP"],
    "CongDan_soCCCD": ["soCCCD"],
}
