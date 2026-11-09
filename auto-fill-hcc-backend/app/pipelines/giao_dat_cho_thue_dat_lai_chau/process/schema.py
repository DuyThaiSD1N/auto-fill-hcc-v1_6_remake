"""Compact schema cho thủ tục 1.115577 — Giao đất, cho thuê đất (Lai Châu).

LLM chỉ trả dữ kiện nguồn đọc từ giấy tờ; ô UI ``CongDan_*`` do mapper dựng. Bước 2 của cổng là bộ ô ``CongDan_*`` của
eForm Lai Châu (file mapping "Mapping_GiaoDat_Buoc2_ThongTinNguoiNop") + ô "Đối tượng nộp" (``CongDan__select_1``:
Cá nhân / Tổ chức). Ô bắt buộc (*): Họ và tên, Ngày Sinh, Giới tính, Dân tộc, Số CMND/CCCD, Tỉnh/Thành phố, Phường/Xã,
Đối tượng nộp, Số nhà/Đường/Tổ/Ấp/Thôn/Xóm.

Hai bộ nguồn theo mapping:
  - ô TỔ CHỨC (tên cơ quan/tổ chức, Số/Ngày/Nơi cấp GCN/GP = quyết định thành lập, địa chỉ trụ sở, điện thoại) lấy từ
    mục 1–3 của Đơn đề nghị giao đất Mẫu số 01 (tên dự phòng: "Chủ đầu tư" trong quyết định phê duyệt dự án);
  - ô CÁ NHÂN (họ tên, ngày sinh, giới tính, dân tộc, số/ngày/nơi cấp căn cước, nơi ở, thường trú) chỉ lấy từ thẻ CCCD
    của người đi nộp. Hồ sơ mẫu không có thẻ → giữ giá trị cổng đổ theo tài khoản đăng nhập (người nộp = chủ tài khoản).

Cố ý KHÔNG phát (theo file mapping: tự nhập / tự sinh / không có nguồn): Quốc gia (chọn sẽ sinh dòng địa chỉ nước ngoài),
Fax, Website, "Địa chỉ chi tiết" nước ngoài (readonly), ô ẩn maDMDiaChi và khối ẩn ``ChuHoSo_*``.
"""

FIELDS: list[dict] = [
    # Thẻ CCCD/CMND/Căn cước của người đi nộp (nếu hồ sơ có).
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

    # Đơn đề nghị giao đất / cho thuê đất (Mẫu số 01) — nguồn chính.
    {"name": "Don_NguoiDeNghi",
     "desc": "Mục 1 \"Người đề nghị\" của Đơn: tên tổ chức chép nguyên văn, hoặc họ tên nếu là cá nhân. KHÔNG lấy "
             "\"Người làm đơn\" ký cuối đơn."},
    {"name": "Don_LoaiNguoiDeNghi",
     "desc": "\"Tổ chức\" nếu người đề nghị là cơ quan/tổ chức (ban quản lý dự án, công ty, UBND, trung tâm, hợp tác "
             "xã...), \"Cá nhân\" nếu là cá nhân/hộ gia đình."},
    {"name": "Don_QdThanhLapSo",
     "desc": "Số quyết định thành lập tổ chức ở dòng \"Thành lập theo Quyết định ...\" dưới mục 1 (vd \"123/QĐ-UBND\")."},
    {"name": "Don_QdThanhLapNgay", "desc": "Ngày của quyết định thành lập đó, dd/mm/yyyy."},
    {"name": "Don_QdThanhLapCoQuan",
     "desc": "Cơ quan ban hành quyết định thành lập (phần \"của ...\" ngay sau ngày, vd \"UBND tỉnh ...\")."},
    {"name": "Don_DiaChi",
     "desc": "Mục 2 \"Địa chỉ/trụ sở chính\" của Đơn, object {quocGia,tinh,xa,chiTietDuoiXa}: cụm cuối = tinh, cụm "
             "trước = xa, phần còn lại (số nhà, đường, thôn) = chiTietDuoiXa. KHÔNG lấy mục 4 \"Địa điểm khu đất\"."},
    {"name": "Don_DienThoai",
     "desc": "Điện thoại ở mục 3 \"Địa chỉ liên hệ\" của Đơn; bỏ dấu chấm/khoảng trắng, giữ chữ số."},
    {"name": "Don_Email", "desc": "Email ở mục 3 của Đơn. Thường không có → bỏ field."},
    {"name": "Don_MaSoThue", "desc": "Mã số thuế / mã số doanh nghiệp của người đề nghị nếu Đơn ghi. Không có → bỏ."},
    {"name": "Don_SoGiayTo",
     "desc": "CHỈ khi người đề nghị là cá nhân: số CCCD/giấy tờ nhân thân ghi ở mục 1 Đơn; chỉ trả chữ số."},

    # Quyết định phê duyệt dự án / chủ trương đầu tư — dự phòng tên tổ chức.
    {"name": "Pd_ChuDauTu",
     "desc": "Mục \"Chủ đầu tư\" trong quyết định phê duyệt dự án đầu tư hoặc quyết định chủ trương đầu tư, chép "
             "nguyên văn."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Cccd_NgaySinh", "Cccd_NgayCap", "Don_QdThanhLapNgay"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Cccd_NoiCuTru", "Don_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô bước 2 theo file mapping (field-key Nth FormBuilder): <select> -> dom-select, <input> -> dom-input.
UI_COMP_BY_NAME = {
    "CongDan_tenCongDan": "dom-input",            # Họ và tên (*) — cổng tự chuyển IN HOA.
    "CongDan_tenCoQuanToChuc": "dom-input",       # Tên cơ quan/tổ chức.
    "CongDan_maSoThueNguoiNop": "dom-input",      # MSDN/MST.
    "CongDan_ngaySinhCongDan": "dom-input",       # Ngày Sinh (*) dd/mm/yyyy.
    "CongDan_gioiTinhCongDan": "dom-select",      # Giới tính (*) — mặc định "Nữ".
    "CongDan_danTocCongDan": "dom-select",        # Dân tộc (*) — selectpicker.
    "CongDan_soCmnd": "dom-input",                # Số CMND/CCCD (*)
    "CongDan_ngayCapCmnd": "dom-input",           # Ngày cấp CMND/CCCD
    "CongDan_noiCapCmnd": "dom-input",            # Nơi cấp CMND/CCCD
    # Địa chỉ 2 cấp tỉnh → xã: phát maTinhThanh TRƯỚC (danh mục xã nạp theo tỉnh).
    "CongDan_maTinhThanh": "dom-select",          # Tỉnh/Thành phố (*)
    "CongDan_maPhuongXa": "dom-select",           # Phường/Xã/Thị trấn (*)
    "CongDan__select_1": "dom-select",            # Đối tượng nộp (*): Cá nhân / Tổ chức.
    "CongDan_diaChi": "dom-input",                # Số nhà/Đường/Tổ/Ấp/Thôn/Xóm (*)
    "CongDan_diDong": "dom-input",                # Di động — nhập liền.
    "CongDan_maTinhCapCMND": "dom-select",        # Nơi cấp CMND (CA Tỉnh) — chỉ CMND do công an tỉnh cấp.
    "CongDan_email": "dom-input",                 # Email
    "CongDan_soGCNGP": "dom-input",               # Số GCN/GP — quyết định thành lập tổ chức.
    "CongDan_ngayCapGCNGP": "dom-input",          # Ngày cấp GCN/GP dd/mm/yyyy.
    "CongDan_noiCapGCNGP": "dom-input",           # Nơi cấp GCN/GP.
    "CongDan_soCCCD": "dom-input",                # Số CCCD (trùng Số CMND/CCCD)
    "CongDan_noiOHienTai": "dom-input",           # Nơi ở hiện tại (chuỗi đầy đủ)
    "CongDan_diaChiThuongTru": "dom-input",       # Địa chỉ thường trú (chuỗi đầy đủ)
}

UI_ALIASES = {"CongDan_soCCCD": ["soCCCD"]}

# Người đề nghị là CÁ NHÂN (người nộp có thể khác chủ tài khoản): ô chữ cá nhân không có nguồn thì xoá giá trị cổng đổ
# theo tài khoản. Người đề nghị là TỔ CHỨC thì người nộp = chủ tài khoản → giữ ô cá nhân của cổng. Ô chọn không xoá:
# engine trợ lý chưa có nhánh bỏ chọn.
PERSONAL_TEXT_FIELDS = (
    "CongDan_tenCongDan", "CongDan_ngaySinhCongDan", "CongDan_soCmnd", "CongDan_ngayCapCmnd", "CongDan_noiCapCmnd",
    "CongDan_soCCCD", "CongDan_noiOHienTai", "CongDan_diaChiThuongTru", "CongDan_diaChi", "CongDan_diDong",
    "CongDan_email",
)
REQUIRED_BLANK = {"CongDan_tenCongDan", "CongDan_ngaySinhCongDan", "CongDan_soCmnd", "CongDan_diaChi"}
