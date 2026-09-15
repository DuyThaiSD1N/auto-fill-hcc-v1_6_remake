"""Compact schema for procedure 1.013978.

The LLM returns only OCR-derived source facts from CCCD/CMND and land-use
certificate documents. UI fields and deterministic defaults are derived in
Python to keep the model output short.

Cổng: dichvucong.laichau.gov.vn — eForm Lai Châu, bước 2 "Thông tin người nộp" render ĐÚNG 26 ô
``CongDan_*`` (đã grep 'fill lai châu.html'). Ô bắt buộc (*) gồm: Họ và tên, Ngày Sinh, Giới tính,
Dân tộc, Số CMND/CCCD, Tỉnh/Thành phố, Phường/Xã/Thị trấn và Số nhà/Đường/Tổ/Ấp/Thôn/Xóm — ba ô địa
chỉ cuối trước đây KHÔNG được phát nên hồ sơ luôn kẹt ở bước validate.

Ba ô cố ý KHÔNG phát (không có nguồn trên giấy tờ → bịa là sai, xem quy tắc "thà thiếu còn hơn sai"):
  - CongDan_fax, CongDan_website: giấy tờ cá nhân không bao giờ ghi;
  - CongDan_maDMDiaChi: nằm trong ``<div id="column-24" style="display: none">`` → ô ẩn, cổng tự quản.
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
    {"name": "Cccd_NoiCuTru",
     "desc": "Địa chỉ cư trú/thường trú ĐỌC TRÊN THẺ CCCD/CMND, object {quocGia,tinh,xa,diaChi} nếu "
             "đọc chắc chắn. Đây là nguồn CUỐI CÙNG cho nơi cư trú: thẻ cấp trước sắp xếp đơn vị hành "
             "chính thường còn ghi tỉnh/huyện CŨ đã sáp nhập. Hễ ĐƠN/TỜ KHAI có ghi địa chỉ thì phải "
             "dùng Don_DiaChi, không dùng field này."},

    # Đơn/tờ khai do chính người dân lập — nguồn ƯU TIÊN cho địa chỉ và liên hệ.
    {"name": "Don_DiaChi",
     "desc": "ĐỊA CHỈ của người sử dụng đất/người đứng đơn GHI TRÊN ĐƠN hoặc TỜ KHAI do chính người "
             "dân lập, object {quocGia,tinh,xa,diaChi}. Nhận BẤT KỲ mẫu nào thực tế có trong hồ sơ "
             "(Đơn đăng ký đất đai Mẫu số 13, Mẫu số 15, danh sách người sử dụng chung Mẫu số 13a, "
             "đơn đề nghị...). TUYỆT ĐỐI KHÔNG lấy từ CCCD/CMND, Giấy chứng nhận, mảnh trích đo hay "
             "công văn; đơn không ghi thì BỎ FIELD, không thay bằng nguồn khác. Dòng địa chỉ trên đơn "
             "thường viết LIỀN, không có nhãn con, dạng "
             "'<số nhà/đường/tổ/bản/thôn>, <xã/phường> <tỉnh/thành phố>': tách bằng cách lấy cụm CUỐI "
             "làm tinh, cụm ngay TRƯỚC nó làm xa (thêm tiền tố 'Xã'/'Phường' nếu đơn viết trống), "
             "phần còn lại cho vào diaChi. ĐÂY KHÔNG PHẢI địa chỉ thửa đất xin cấp Giấy chứng nhận."},
    {"name": "Don_DienThoai",
     "desc": 'Số điện thoại liên hệ của người đứng đơn, lấy tại mục "Điện thoại"/"Điện thoại liên hệ '
             '(nếu có)" trên Đơn đăng ký đất đai hoặc tờ khai. Chỉ trả số điện thoại; KHÔNG lấy số '
             "CCCD, số thửa, số tờ bản đồ, số phát hành Giấy chứng nhận hay mã số thuế. Đơn hay viết "
             "số có dấu chấm (0xxx.xxx.xxx) — bỏ dấu chấm, giữ chữ số."},
    {"name": "Don_Email",
     "desc": 'Hộp thư điện tử của người đứng đơn nếu đơn có ghi (mục "Email"/"Hộp thư điện tử (nếu '
             'có)"). Mục này thường bỏ trống — không có thì BỎ FIELD, tuyệt đối không tự tạo email.'},

    # Giấy chứng nhận quyền sử dụng đất/quyền sở hữu tài sản gắn liền với đất.
    {"name": "ToChuc_Ten",
     "desc": "Tên CƠ QUAN/TỔ CHỨC đứng hồ sơ, CHỈ điền khi người sử dụng đất là PHÁP NHÂN (công ty, hợp tác xã, UBND, trường học, tổ chức tôn giáo...). Lấy nguyên văn tên tổ chức trên quyết định thành lập/đăng ký kinh doanh/giấy tờ pháp nhân. Hồ sơ của CÁ NHÂN hoặc HỘ GIA ĐÌNH thì BỎ FIELD — tuyệt đối KHÔNG lấy họ tên người dân làm tên tổ chức."},
    {"name": "ToChuc_MaSoThue",
     "desc": "Mã số doanh nghiệp/mã số thuế (MSDN/MST) của cơ quan, tổ chức — chuỗi 10 hoặc 13 chữ số ghi trên giấy chứng nhận đăng ký doanh nghiệp/đăng ký thuế. CHỈ điền khi giấy tờ ghi RÕ là mã số thuế. TUYỆT ĐỐI KHÔNG lấy số CCCD/CMND/số định danh cá nhân làm mã số thuế; cá nhân không có MST thì BỎ FIELD."},
    {"name": "Gcn_SoPhatHanh",
     "desc": "Số phát hành GCN trên bìa, thường 2 chữ cái + 6 số."},
    {"name": "Gcn_SoVaoSo",
     "desc": 'Số vào sổ cấp GCN nếu có. Không dùng field này làm Số GCN/GP.'},
    {"name": "Gcn_NgayCap",
     "desc": "Ngày ký/cấp giấy chứng nhận ở phần cuối hoặc gần chữ ký, dd/mm/yyyy."},
    {"name": "Gcn_CoQuanCap",
     "desc": "Cơ quan cấp giấy chứng nhận gần chữ ký/con dấu."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Cccd_NgaySinh", "Cccd_NgayCap", "Gcn_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Cccd_NoiCuTru", "Don_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# comp lấy đúng tag thật trên 'fill lai châu.html': <select> -> dom-select, <input type=text> -> dom-input.
UI_COMP_BY_NAME = {
    "CongDan_tenCongDan": "dom-input",            # Họ và tên (*)
    "CongDan_tenCoQuanToChuc": "dom-input",       # Tên cơ quan/tổ chức
    "CongDan_maSoThueNguoiNop": "dom-input",      # MSDN/MST
    "CongDan_ngaySinhCongDan": "dom-input",       # Ngày Sinh (*) — input text, KHÔNG phải datepicker riêng.
    "CongDan_gioiTinhCongDan": "dom-select",      # Giới tính (*) — option "Nữ"/"Nam".
    "CongDan_danTocCongDan": "dom-select",        # Dân tộc (*) — 498 option.
    "CongDan_soCmnd": "dom-input",                # Số CMND/CCCD (*)
    "CongDan_ngayCapCmnd": "dom-input",           # Ngày cấp CMND/CCCD
    "CongDan_noiCapCmnd": "dom-input",            # Nơi cấp CMND/CCCD
    # Nơi cư trú (eForm Lai Châu 2 cấp: tỉnh → xã, KHÔNG có huyện). maPhuongXa nạp động qua AJAX sau
    # khi chọn tỉnh nên phải phát maTinhThanh TRƯỚC; extension isAreaSelectName đã nhận 2 tên này.
    "CongDan_maTinhThanh": "dom-select",          # Tỉnh/Thành phố (*) — option dạng "Tỉnh Lai Châu".
    "CongDan_maPhuongXa": "dom-select",           # Phường/Xã/Thị trấn (*)
    "CongDan_diaChi": "dom-input",                # Số nhà/Đường/Tổ/Ấp/Thôn/Xóm (*)
    "CongDan_diDong": "dom-input",                # Di động
    "CongDan_maTinhCapCMND": "dom-select",        # Nơi cấp CMND (CA Tỉnh) — danh mục tỉnh, không phải text.
    "CongDan_maDMQuocGia": "dom-select",          # Quốc gia
    "CongDan_diaChiNuocNgoai": "dom-input",       # Địa chỉ chi tiết (readonly, cổng tự set theo quốc gia)
    "CongDan_email": "dom-input",                 # Email
    "CongDan_soGCNGP": "dom-input",               # Số GCN/GP
    "CongDan_ngayCapGCNGP": "dom-input",          # Ngày cấp GCN/GP
    "CongDan_noiCapGCNGP": "dom-input",           # Nơi cấp GCN/GP
    "CongDan_soCCCD": "dom-input",                # Số CCCD
    "CongDan_noiOHienTai": "dom-input",           # Nơi ở hiện tại (chuỗi địa chỉ đầy đủ)
    "CongDan_diaChiThuongTru": "dom-input",       # Địa chỉ thường trú (chuỗi địa chỉ đầy đủ)
    # 3 ô còn lại của form (đủ 26) khai ở đây để ai sửa sau biết chúng CÓ THẬT, nhưng mapper cố ý
    # KHÔNG gọi add() cho chúng — xem docstring đầu file.
    "CongDan_fax": "dom-input",                   # Số Fax — không có nguồn.
    "CongDan_website": "dom-input",               # Website — không có nguồn.
    "CongDan_maDMDiaChi": "dom-input",            # Địa chỉ chi tiết (ô ẩn trong column-24).
}

UI_ALIASES = {
    "CongDan_soGCNGP": ["soGCNGP"],
    "CongDan_ngayCapGCNGP": ["ngayCapGCNGP"],
    "CongDan_noiCapGCNGP": ["noiCapGCNGP"],
    "CongDan_soCCCD": ["soCCCD"],
}

