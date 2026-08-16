"""Compact schema for "Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót".

The LLM returns only OCR-derived source facts from the change application,
CCCD/CMND and land-use certificate documents. UI fields and deterministic
defaults are derived in Python to keep the model output short.
"""

FIELDS: list[dict] = [
    # Người nộp hồ sơ: một vai trò, có thể được xác minh từ CCCD/CMND hoặc khối người sử dụng đất trên Đơn.
    {"name": "NguoiNop_HoTen",
     "desc": 'Họ tên người nộp hồ sơ. Ưu tiên CCCD/CMND; nếu không có file căn cước thì lấy từ đúng '
             'khối "Người sử dụng đất, chủ sở hữu tài sản gắn liền với đất" trên Đơn.'},
    {"name": "NguoiNop_SoDinhDanh",
     "desc": 'Số định danh/CCCD/CMND của người nộp. Ưu tiên giấy căn cước; nếu không có thì lấy tại '
             'dòng "Giấy tờ nhân thân/pháp nhân" của đúng người trên Đơn.'},
    {"name": "NguoiNop_NgaySinh",
     "desc": "Ngày sinh người nộp, dd/mm/yyyy; lấy từ CCCD/CMND hoặc đúng khối người trên Đơn."},
    {"name": "NguoiNop_GioiTinh",
     "desc": 'Giới tính người nộp: "Nam" hoặc "Nữ" khi giấy tờ ghi rõ; không suy đoán từ họ tên.'},
    {"name": "NguoiNop_DanToc",
     "desc": "Dân tộc người nộp khi CCCD/CMND hoặc Đơn ghi rõ; không suy đoán."},
    {"name": "NguoiNop_NgayCapGiayTo",
     "desc": 'Ngày cấp CCCD/CMND của người nộp, dd/mm/yyyy. Ưu tiên giấy căn cước; nếu không có '
             'file căn cước thì BẮT BUỘC lấy từ đúng cụm "Giấy tờ nhân thân/pháp nhân" trên Đơn, '
             'ngay sau nhãn "ngày cấp" của cùng số CCCD/CMND.'},
    {"name": "NguoiNop_NoiCapGiayTo",
     "desc": 'Nơi cấp CCCD/CMND từ mặt sau, hoặc từ đúng cụm "Giấy tờ nhân thân/pháp nhân" trên '
             'Đơn khi không có file căn cước. Nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT..." '
             'thì trả "Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},
    {"name": "NguoiNop_NoiCuTru",
     "desc": "Địa chỉ cư trú/thường trú người nộp, object {quocGia,tinh,xa,diaChi}; ưu tiên CCCD, "
             "không có thì lấy địa chỉ của đúng người trong khối trên Đơn."},
    {"name": "NguoiNop_DienThoai",
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
for _name in ("NguoiNop_NgaySinh", "NguoiNop_NgayCapGiayTo", "Gcn_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_NoiCuTru"] = "x-select-area"

UI_COMP_BY_NAME = {
    "CongDan_tenCongDan": "dom-input",
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
