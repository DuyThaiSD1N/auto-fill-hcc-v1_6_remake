"""Compact schema cho thủ tục 1.115591 — Tổ chức kinh tế nhận chuyển nhượng QSDĐ để thực hiện dự án (Lai Châu).

LLM chỉ trả dữ kiện nguồn đọc từ giấy tờ; ô UI ``CongDan_*`` do mapper dựng. Bước 2 của cổng là bộ ô ``CongDan_*`` của
eForm Lai Châu (file mapping "Mapping_TTHC_1.115591_ToChucKinhTe_NhanCNQSDD_DuAn_DVC_LaiChau") + ô "Đối tượng nộp"
(``CongDan__select_1``: Cá nhân / Tổ chức — thủ tục dành cho tổ chức kinh tế nên luôn Tổ chức). Ô bắt buộc (*): Họ và
tên, Ngày Sinh, Giới tính, Dân tộc, Số CMND/CCCD, Tỉnh/Thành phố, Phường/Xã, Đối tượng nộp, Số nhà/Đường/Tổ/Ấp/Thôn/Xóm.

Nguồn theo mapping (giấy đứng trước là nguồn chuẩn):
  - ô TỔ CHỨC (tên, MSDN/MST, Số/Ngày/Nơi cấp GCN/GP = giấy chứng nhận đăng ký doanh nghiệp, trụ sở) lấy từ mục 1 + 3
    (+ mục 4 dự phòng) của văn bản đề nghị Mẫu số 30; mảnh trích đo chỉ để đối chiếu tỉnh/xã khi văn bản thiếu;
  - ô CÁ NHÂN (người nộp = người đại diện hợp pháp ở mục 2): CCCD → văn bản đề nghị (họ tên, ngày sinh, giới tính, số
    định danh); ngày cấp, nơi cấp, dân tộc, thường trú CHỈ có trên thẻ.

Cố ý KHÔNG phát (theo file mapping: tự nhập / tự sinh / khối ẩn): Quốc gia (chọn sẽ chèn hàng địa chỉ #row-7b chưa có
DOM, như 1.115577/1.115578), Fax, Website, "Địa chỉ chi tiết" readonly, ô ẩn maDMDiaChi, ô tra cứu doanh nghiệp ẩn
``code-dkdn`` và khối ẩn ``ChuHoSo_*``.
"""

FIELDS: list[dict] = [
    # Thẻ CCCD/CMND/Căn cước của người đại diện (nếu hồ sơ có).
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

    # Văn bản đề nghị chấp thuận (Mẫu số 30) — nguồn chính.
    {"name": "Vb_ToChuc",
     "desc": "Mục 1 \"Tổ chức đề nghị thực hiện dự án\": tên tổ chức kinh tế chép nguyên văn (vd \"Công ty TNHH ...\")."},
    {"name": "Vb_TenCoQuanBanHanh",
     "desc": "Tên tổ chức in ở GÓC TRÁI TRÊN văn bản (dòng tên cơ quan ban hành, ngang hàng Quốc hiệu, vd \"CÔNG TY TNHH "
             "MTV ...\"), chép nguyên văn."},
    {"name": "Vb_MaSoDoanhNghiep",
     "desc": "\"mã số doanh nghiệp\" trong dòng Giấy chứng nhận đăng ký doanh nghiệp dưới mục 1 (10 hoặc 13 chữ số)."},
    {"name": "Vb_GcnNgayCap",
     "desc": "Ngày \"cấp lần đầu\" của Giấy chứng nhận đăng ký doanh nghiệp dưới mục 1, dd/mm/yyyy. KHÔNG lấy ngày đăng ký "
             "thay đổi."},
    {"name": "Vb_GcnNoiCap",
     "desc": "Cơ quan cấp Giấy chứng nhận đăng ký doanh nghiệp (phần \"do ... cấp\" dưới mục 1), chép nguyên văn."},
    {"name": "Vb_NguoiDaiDien", "desc": "Mục 2 \"Người đại diện hợp pháp\": họ tên người đại diện."},
    {"name": "Vb_NgaySinh", "desc": "\"Ngày sinh\" của người đại diện ở mục 2, dd/mm/yyyy."},
    {"name": "Vb_GioiTinh", "desc": "\"Giới tính\" của người đại diện ở mục 2: \"Nam\" hoặc \"Nữ\"."},
    {"name": "Vb_SoDinhDanh", "desc": "\"Số định danh cá nhân\" của người đại diện ở mục 2; chỉ trả chữ số."},
    {"name": "Vb_DiaChiTruSo",
     "desc": "Mục 3 \"Địa chỉ/trụ sở chính\", object {quocGia,tinh,xa,chiTietDuoiXa}: cụm cuối = tinh, cụm trước = xa, "
             "phần còn lại (số nhà, đường, thôn, bản) = chiTietDuoiXa."},
    {"name": "Vb_DiaChiLienHe",
     "desc": "Mục 4 \"Địa chỉ liên hệ\", object {quocGia,tinh,xa,chiTietDuoiXa} như trên."},
    {"name": "Vb_DienThoai", "desc": "Số điện thoại của tổ chức nếu văn bản ghi; bỏ dấu chấm/khoảng trắng."},
    {"name": "Vb_Email", "desc": "Email của tổ chức nếu văn bản ghi. Thường không có → bỏ field."},

    # Mảnh trích đo / trích lục vị trí khu đất — chỉ để đối chiếu địa bàn.
    {"name": "TrichDo_DiaBan",
     "desc": "Địa bàn ghi ở đầu mảnh trích đo / trích lục vị trí khu đất (vd \"TỈNH LAI CHÂU - PHƯỜNG TÂN PHONG\"), "
             "object {quocGia,tinh,xa,chiTietDuoiXa}."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Cccd_NgaySinh", "Cccd_NgayCap", "Vb_GcnNgayCap", "Vb_NgaySinh"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Cccd_NoiCuTru", "Vb_DiaChiTruSo", "Vb_DiaChiLienHe", "TrichDo_DiaBan"):
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
    "CongDan_soGCNGP": "dom-input",               # Số GCN/GP — mã số doanh nghiệp.
    "CongDan_ngayCapGCNGP": "dom-input",          # Ngày cấp GCN/GP (cấp lần đầu) dd/mm/yyyy.
    "CongDan_noiCapGCNGP": "dom-input",           # Nơi cấp GCN/GP.
    "CongDan_soCCCD": "dom-input",                # Số CCCD (trùng Số CMND/CCCD)
    "CongDan_noiOHienTai": "dom-input",           # Nơi ở hiện tại (chuỗi đầy đủ)
    "CongDan_diaChiThuongTru": "dom-input",       # Địa chỉ thường trú (chuỗi đầy đủ)
}

UI_ALIASES = {"CongDan_soCCCD": ["soCCCD"]}

# Cổng đổ sẵn ô cá nhân theo TÀI KHOẢN đăng nhập (mapping cột D chữ đỏ: "phải sửa") → ô chữ không có nguồn thì xoá, trừ
# khi tài khoản chính là người đại diện. Ô chọn không xoá: engine chưa có nhánh bỏ chọn.
PERSONAL_TEXT_FIELDS = (
    "CongDan_tenCongDan", "CongDan_ngaySinhCongDan", "CongDan_soCmnd", "CongDan_ngayCapCmnd", "CongDan_noiCapCmnd",
    "CongDan_soCCCD", "CongDan_noiOHienTai", "CongDan_diaChiThuongTru", "CongDan_diDong", "CongDan_email",
)
REQUIRED_BLANK = {"CongDan_tenCongDan", "CongDan_ngaySinhCongDan", "CongDan_soCmnd"}
