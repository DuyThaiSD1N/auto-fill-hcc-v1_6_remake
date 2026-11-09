"""Compact schema cho thủ tục 1.115557 — Cấp lại Giấy chứng nhận do bị mất — Lai Châu.

LLM chỉ trả dữ kiện nguồn đọc từ giấy tờ; ô UI ``CongDan_*`` do mapper dựng. Bước 2 của cổng là đúng bộ ô
``CongDan_*`` của eForm Lai Châu (file mapping "Mapping_CapLaiGCN_DoBiMat_Buoc2"); ô bắt buộc (*): Họ và tên, Ngày
Sinh, Giới tính, Dân tộc, Số CMND/CCCD, Tỉnh/Thành phố, Phường/Xã/Thị trấn, Số nhà/Đường/Tổ/Ấp/Thôn/Xóm.

Thứ tự nguồn theo mapping: thẻ CCCD → Đơn đăng ký biến động Mẫu số 16 → Bảng 16a / Đơn xác nhận lại thời hạn Mẫu
số 09 / Phiếu yêu cầu xóa đăng ký biện pháp bảo đảm Mẫu số 03a → Giấy chứng nhận / Sổ địa chính (chỉ danh xưng
"Ông/Bà" và họ tên). Hồ sơ hay scan CHUNG mọi giấy vào một file, kèm thẻ của cả người đồng sử dụng (vợ/chồng): chỉ
lấy người viết đơn.

Cố ý KHÔNG phát (theo file mapping: để trống hoặc không có nguồn): Quốc gia (chọn sẽ sinh dòng địa chỉ nước ngoài), Fax,
Website, Số/Ngày/Nơi cấp GCN/GP (dành cho tổ chức — KHÔNG nhập số seri Giấy chứng nhận QSDĐ bị mất), "Địa chỉ chi
tiết" nước ngoài (readonly), ô ẩn maDMDiaChi và khối ẩn ``ChuHoSo_*`` (cổng không render: choPhepHienThiChuHoSo rỗng).
"""

FIELDS: list[dict] = [
    # Thẻ CCCD/CMND/Căn cước của NGƯỜI VIẾT ĐƠN — nguồn ưu tiên 1 cho nhân thân.
    {"name": "Cccd_HoTen", "desc": "Họ tên trên thẻ CCCD/CMND/Căn cước của người viết Đơn Mẫu số 16."},
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
             "thị trấn/huyện/tỉnh trước sáp nhập."},

    # Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 16) — mục I người sử dụng đất.
    {"name": "Don_HoTen",
     "desc": "Mục I \"Người sử dụng đất, chủ sở hữu tài sản gắn liền với đất\" của Đơn Mẫu số 16 — dòng \"Tên\" "
             "(hoặc họ tên dưới \"Người viết đơn\")."},
    {"name": "Don_NgaySinh", "desc": "Dòng \"Ngày tháng năm sinh\" ở mục I của Đơn Mẫu số 16, dd/mm/yyyy."},
    {"name": "Don_SoGiayTo",
     "desc": "Dòng \"Giấy tờ nhân thân/pháp nhân: CCCD (CC) số\" ở mục I của Đơn Mẫu số 16, chỉ chữ số."},
    {"name": "Don_CoQuanCap", "desc": "Dòng \"Cơ quan cấp\" ở mục I của Đơn Mẫu số 16, chép nguyên chữ."},
    {"name": "Don_NgayCap", "desc": "Dòng \"Ngày cấp\" ở mục I của Đơn Mẫu số 16, dd/mm/yyyy."},
    {"name": "Don_DiaChi",
     "desc": "Dòng \"Địa chỉ\" ở mục I của Đơn Mẫu số 16, object {quocGia,tinh,xa,chiTietDuoiXa}. Đơn viết liền "
             "không dấu phẩy \"Bản A Xã B Tỉnh C\": tách theo chữ Xã/Phường/Thị trấn/Tỉnh — phần sau \"Tỉnh\" = tinh, "
             "\"Xã/Phường/Thị trấn ...\" = xa, phần còn lại = chiTietDuoiXa giữ nguyên chữ."},
    {"name": "Don_MaSoThue", "desc": "Dòng \"Mã số thuế (nếu có)\" ở mục I của Đơn Mẫu số 16. Để trống → bỏ field."},
    {"name": "Don_DienThoai",
     "desc": "Dòng \"Điện thoại liên hệ (nếu có)\" ở mục I của Đơn Mẫu số 16; bỏ dấu chấm/khoảng trắng, giữ chữ số."},
    {"name": "Don_Email", "desc": "Dòng \"Hộp thư điện tử (nếu có)\" của Đơn Mẫu số 16. Để trống → bỏ field."},
    {"name": "ToChuc_Ten",
     "desc": "Tên CƠ QUAN/TỔ CHỨC ở mục I của Đơn Mẫu số 16, CHỈ khi người sử dụng đất là tổ chức. Cá nhân, hộ gia "
             "đình → BỎ FIELD; không lấy họ tên người dân."},

    # Giấy kèm theo (dự phòng khi Đơn Mẫu 16 bỏ trống/đọc không ra) — chỉ của CHÍNH người viết đơn.
    {"name": "DonKhac_HoTen",
     "desc": "Họ tên người viết đơn ở giấy kèm theo: mục 1 \"Người sử dụng đất\" của Đơn xin xác nhận lại thời hạn "
             "sử dụng đất nông nghiệp (Mẫu số 09), hoặc \"Họ và tên\" mục 1 của Phiếu yêu cầu xóa đăng ký biện pháp "
             "bảo đảm (Mẫu số 03a), hoặc dòng 01 Bảng 16a."},
    {"name": "DonKhac_SoCccd",
     "desc": "\"CCCD số\" của người viết đơn ở Mẫu số 09 / Mẫu số 03a / cột số định danh dòng 01 Bảng 16a, chỉ chữ số."},
    {"name": "DonKhac_NgaySinh", "desc": "\"sinh ngày\" ở mục 1 Mẫu số 09, dd/mm/yyyy."},
    {"name": "DonKhac_NgayCap", "desc": "\"cấp ngày\" của CCCD ở Mẫu số 09 / Mẫu số 03a, dd/mm/yyyy."},
    {"name": "DonKhac_NoiCap", "desc": "\"Cơ quan cấp\"/\"do\" của CCCD ở Mẫu số 03a / Mẫu số 09, chép nguyên chữ."},
    {"name": "DonKhac_DiaChi",
     "desc": "Địa chỉ liên hệ của người viết đơn, object {quocGia,tinh,xa,chiTietDuoiXa}. ƯU TIÊN dòng ĐÁNH MÁY "
             "\"Địa chỉ để cơ quan đăng ký liên hệ khi cần thiết\" của Mẫu số 03a; không có thì mục 2 \"Địa chỉ liên "
             "hệ\" Mẫu số 09 hoặc cột Địa chỉ dòng 01 Bảng 16a. TRẢ CẢ KHI Đơn Mẫu 16 đã ghi địa chỉ (để đối chiếu chữ "
             "viết tay). KHÔNG lấy mục 3.7 \"Địa điểm thửa đất\" của Mẫu số 09."},
    {"name": "DonKhac_DienThoai",
     "desc": "\"Điện thoại\" mục 2 Mẫu số 09 hoặc \"Số điện thoại\" Mẫu số 03a; bỏ dấu chấm/khoảng trắng."},

    # Giấy chứng nhận (bản sao GCN bị mất) / Sổ địa chính — chỉ dự phòng họ tên + giới tính.
    {"name": "Gcn_HoTen",
     "desc": "Họ tên người sử dụng đất đứng ĐẦU ở mục I của Giấy chứng nhận hoặc mục \"I - Người sử dụng đất\" của "
             "Sổ địa chính (\"Ông/Bà: ...\"), bỏ danh xưng. Không lấy người đứng sau chữ \"Và bà/Và ông\"."},
    {"name": "NguoiSdd_GioiTinh",
     "desc": "Giới tính người viết đơn suy từ danh xưng đứng trước tên ở mục I Giấy chứng nhận / Sổ địa chính: "
             "\"Ông\" → \"Nam\", \"Bà\" → \"Nữ\". Không có danh xưng → bỏ field."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Cccd_NgaySinh", "Cccd_NgayCap", "Don_NgaySinh", "Don_NgayCap", "DonKhac_NgaySinh", "DonKhac_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Cccd_NoiCuTru", "Don_DiaChi", "DonKhac_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô bước 2 theo file mapping (field-key Nth FormBuilder): <select> -> dom-select, <input> -> dom-input.
UI_COMP_BY_NAME = {
    "CongDan_tenCongDan": "dom-input",            # Họ và tên (*) — cổng tự chuyển IN HOA.
    "CongDan_tenCoQuanToChuc": "dom-input",       # Tên cơ quan/tổ chức — chỉ khi người sử dụng đất là tổ chức.
    "CongDan_maSoThueNguoiNop": "dom-input",      # MSDN/MST — Đơn Mẫu 16 "Mã số thuế (nếu có)".
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
