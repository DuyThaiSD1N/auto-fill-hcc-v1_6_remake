"""Compact schema cho thủ tục 1.115578 — Chuyển mục đích sử dụng đất (xã miền núi, biên giới...) — Lai Châu.

LLM chỉ trả dữ kiện nguồn đọc từ giấy tờ; ô UI ``CongDan_*`` do mapper dựng. Bước 2 của cổng là đúng bộ ô
``CongDan_*`` của eForm Lai Châu (file mapping "Mapping_Chuyen_MDSDD_Buoc2"); ô bắt buộc (*): Họ và tên, Ngày Sinh,
Giới tính, Dân tộc, Số CMND/CCCD, Tỉnh/Thành phố, Phường/Xã/Thị trấn, Số nhà/Đường/Tổ/Ấp/Thôn/Xóm.

Thứ tự nguồn theo mapping: thẻ CCCD → Đơn đề nghị Mẫu số 02 → Giấy chứng nhận QSDĐ (mục I + trang thay đổi) → Trích
lục bản đồ địa chính (chỉ họ tên). Giấy chứng nhận/Trích lục đứng tên CẢ hai vợ chồng: chỉ lấy người đề nghị.

Cố ý KHÔNG phát (theo file mapping: để trống hoặc không có nguồn): Quốc gia (chọn sẽ sinh dòng địa chỉ nước ngoài), Fax,
Website, Số/Ngày/Nơi cấp GCN/GP (dành cho tổ chức — KHÔNG nhập số seri Giấy chứng nhận QSDĐ), "Địa chỉ chi tiết" nước
ngoài (readonly), ô ẩn maDMDiaChi và khối ẩn ``ChuHoSo_*`` (cổng không render: choPhepHienThiChuHoSo rỗng).
"""

FIELDS: list[dict] = [
    # Thẻ CCCD/CMND/Căn cước của người đề nghị — nguồn ưu tiên 1 cho nhân thân.
    {"name": "Cccd_HoTen", "desc": "Họ tên trên thẻ CCCD/CMND/Căn cước."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh/CCCD/CMND trên thẻ; có thể đọc từ MRZ mặt sau."},
    {"name": "Cccd_NgaySinh", "desc": "Ngày sinh trên thẻ, dd/mm/yyyy."},
    {"name": "Cccd_GioiTinh", "desc": 'Giới tính trên thẻ: "Nam" hoặc "Nữ".'},
    {"name": "Cccd_DanToc", "desc": "Dân tộc IN TRÊN THẺ. Thẻ gắn chip/Căn cước mẫu mới không in dân tộc → bỏ field."},
    {"name": "Cccd_NgayCap",
     "desc": "Ngày cấp thẻ (dòng \"Ngày, tháng, năm / Date, month, year\" mặt sau), dd/mm/yyyy. KHÔNG lấy ngày "
             "\"Có giá trị đến\"."},
    {"name": "Cccd_NoiCap",
     "desc": 'Nơi cấp thẻ. Thẻ Căn cước mới ghi "BỘ CÔNG AN" → "Bộ Công an"; thẻ in "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ '
             'HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},
    {"name": "Cccd_NoiCuTru",
     "desc": "Nơi thường trú/cư trú IN TRÊN THẺ, object {quocGia,tinh,xa,chiTietDuoiXa}. Thẻ cũ hay còn ghi "
             "tỉnh/huyện trước sáp nhập."},

    # Đơn đề nghị chuyển mục đích sử dụng đất (Mẫu số 02) — nguồn chính cho địa chỉ và liên hệ.
    {"name": "Don_HoTen",
     "desc": "Họ tên ở mục 1 \"Người đề nghị chuyển mục đích sử dụng đất\" của Đơn Mẫu số 02 (hoặc dòng họ tên dưới "
             "\"Người làm đơn\")."},
    {"name": "Don_DiaChi",
     "desc": "Mục 2 \"Địa chỉ/trụ sở chính\" của Đơn, object {quocGia,tinh,xa,chiTietDuoiXa}. Dòng viết liền "
             "\"<thôn/bản/tổ>, <xã/phường>, <tỉnh>\": cụm cuối = tinh, cụm trước = xa (thêm \"Xã\"/\"Phường\" nếu "
             "đơn viết trống), phần còn lại = chiTietDuoiXa giữ nguyên chữ. KHÔNG lấy mục 4 \"Địa điểm thửa đất\"."},
    {"name": "Don_DienThoai",
     "desc": "Số điện thoại ở mục 3 \"Thông tin liên hệ (điện thoại, fax, email...)\" của Đơn; bỏ dấu chấm/khoảng "
             "trắng, giữ chữ số."},
    {"name": "Don_Email", "desc": "Email ở mục 3 \"Thông tin liên hệ\" của Đơn. Thường để trống → bỏ field."},
    {"name": "ToChuc_Ten",
     "desc": "Tên CƠ QUAN/TỔ CHỨC ở mục 1 của Đơn, CHỈ khi người đề nghị là tổ chức. Cá nhân, hộ gia đình → BỎ "
             "FIELD; không lấy họ tên người dân."},

    # Giấy chứng nhận quyền sử dụng đất (bản gốc) — chỉ phần của NGƯỜI ĐỀ NGHỊ.
    {"name": "Gcn_HoTen",
     "desc": "Họ tên người sử dụng đất đứng ĐẦU ở mục I của Giấy chứng nhận (\"Ông/Bà: ...\"), bỏ danh xưng. Không "
             "lấy người đứng sau chữ \"Và bà/Và ông\"."},
    {"name": "Gcn_SoCccdMoi",
     "desc": "Số CCCD MỚI của người đề nghị ở trang thay đổi của Giấy chứng nhận (câu \"thay đổi CMND số ... về/"
             "thành CCCD số ...\"): lấy số SAU chữ \"về\"/\"thành\". KHÔNG lấy \"CMND số\" cũ ở mục I, không lấy số "
             "của vợ/chồng."},
    {"name": "Gcn_NgayCapCccd", "desc": "Ngày cấp CCCD mới của người đề nghị ghi ở trang thay đổi, dd/mm/yyyy."},
    {"name": "Gcn_NoiCapCccd", "desc": "Nơi cấp CCCD mới của người đề nghị ghi ở trang thay đổi, chép nguyên chữ."},
    {"name": "Gcn_ThuongTruMoi",
     "desc": "Địa chỉ thường trú MỚI ở trang thay đổi (câu \"thay đổi địa chỉ thường trú từ ... về/thành ...\": lấy "
             "phần SAU chữ \"về\"/\"thành\", bỏ phần \"theo hồ sơ số ...\"), CHUỖI nguyên văn. Không lấy địa chỉ "
             "thường trú cũ ở mục I."},
    {"name": "NguoiSdd_GioiTinh",
     "desc": "Giới tính người đề nghị suy từ danh xưng đứng trước tên ở mục I Giấy chứng nhận: \"Ông\" → \"Nam\", "
             "\"Bà\" → \"Nữ\". Không có danh xưng → bỏ field."},

    # Trích lục bản đồ địa chính — chỉ dự phòng họ tên.
    {"name": "TrichLuc_HoTen",
     "desc": "Mục 3 \"Tên người sử dụng đất, người quản lý đất\" của Trích lục: chỉ tên người ĐẦU, bỏ phần trong "
             "ngoặc (vợ/chồng)."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Cccd_NgaySinh", "Cccd_NgayCap", "Gcn_NgayCapCccd"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Cccd_NoiCuTru", "Don_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô bước 2 theo file mapping (field-key Nth FormBuilder): <select> -> dom-select, <input> -> dom-input.
UI_COMP_BY_NAME = {
    "CongDan_tenCongDan": "dom-input",            # Họ và tên (*) — cổng tự chuyển IN HOA.
    "CongDan_tenCoQuanToChuc": "dom-input",       # Tên cơ quan/tổ chức — chỉ khi người đề nghị là tổ chức.
    "CongDan_maSoThueNguoiNop": "dom-input",      # MSDN/MST — Đơn Mẫu 02 không có dòng này: chỉ xoá giá trị cũ.
    "CongDan_ngaySinhCongDan": "dom-input",       # Ngày Sinh (*) dd/mm/yyyy.
    "CongDan_gioiTinhCongDan": "dom-select",      # Giới tính (*) — mặc định "Nữ" nên luôn phải chọn lại.
    "CongDan_danTocCongDan": "dom-select",        # Dân tộc (*) — selectpicker; hồ sơ thường không có nguồn.
    "CongDan_soCmnd": "dom-input",                # Số CMND/CCCD (*)
    "CongDan_ngayCapCmnd": "dom-input",           # Ngày cấp CMND/CCCD
    "CongDan_noiCapCmnd": "dom-input",            # Nơi cấp CMND/CCCD
    # Địa chỉ 2 cấp tỉnh → xã: phát maTinhThanh TRƯỚC (danh mục xã nạp theo tỉnh).
    "CongDan_maTinhThanh": "dom-select",          # Tỉnh/Thành phố (*)
    "CongDan_maPhuongXa": "dom-select",           # Phường/Xã/Thị trấn (*)
    "CongDan_diaChi": "dom-input",                # Số nhà/Đường/Tổ/Ấp/Thôn/Xóm (*)
    "CongDan_diDong": "dom-input",                # Di động — nhập liền.
    "CongDan_maTinhCapCMND": "dom-select",        # Nơi cấp CMND (CA Tỉnh) — chỉ CMND do công an tỉnh cấp.
    "CongDan_email": "dom-input",                 # Email
    "CongDan_soCCCD": "dom-input",                # Số CCCD (trùng Số CMND/CCCD)
    "CongDan_noiOHienTai": "dom-input",           # Nơi ở hiện tại (chuỗi đầy đủ)
    "CongDan_diaChiThuongTru": "dom-input",       # Địa chỉ thường trú (chuỗi đầy đủ)
}

UI_ALIASES = {"CongDan_soCCCD": ["soCCCD"]}

# Cổng đổ sẵn bước 2 theo TÀI KHOẢN đăng nhập (cán bộ nộp thay) → ô chữ không có nguồn phải xoá về trống, không để lại
# dữ liệu người khác. Ô chọn (dom-select) không xoá: engine trợ lý chưa có nhánh bỏ chọn.
BLANK_TEXT_FIELDS = tuple(name for name, comp in UI_COMP_BY_NAME.items() if comp == "dom-input")
# Ô bắt buộc (*) mà xoá về trống thì tô đỏ để cán bộ thấy.
REQUIRED_BLANK = {"CongDan_tenCongDan", "CongDan_ngaySinhCongDan", "CongDan_soCmnd", "CongDan_diaChi"}
