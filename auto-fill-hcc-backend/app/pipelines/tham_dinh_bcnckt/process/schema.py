"""Compact schema cho "Thẩm định Báo cáo nghiên cứu khả thi đầu tư xây dựng / BCNCKT điều chỉnh" — cổng
DVC Bộ Xây dựng dvc.moc.gov.vn (Form.io, engine fillFormStandard dom-*). CÙNG cổng #113/#91/#76.

Nguồn CHÍNH: Tờ trình thẩm định (Mẫu số 01) — 1 văn bản chứa gần như toàn bộ thông tin (chủ đầu tư, dự án,
quy hoạch/phê duyệt, năng lực nhà thầu). Người nộp (Phần I) lấy từ CCCD NGƯỜI NỘP tải lên (xác định qua
VNeID: formContext truyền tên + số CCCD tài khoản).

⚠ ĐẶC THÙ:
- Field-key data[...] TRÙNG 2×: province/district/address → OCCURRENCE 0 (nơi ở người nộp, Phần I) / 1
  (ĐỊA ĐIỂM XÂY DỰNG dự án, Phần IV). Doanh nghiệp (Phần II, khi Tổ chức) dùng province1/district1/
  address1 (KEY RIÊNG).
- Nhà thầu THẨM TRA dùng key đặt NHẦM theo "KhaoSat": tenChuNhiemKhaoSatXayDung1 / maSoChungChiChuNhiemKhaoSat1.
- Datagrid bộ môn THIẾT KẾ dùng key `khaoSatXayDung[]`; bộ môn THẨM TRA dùng `thamTraThietKe[]` (giữ theo DOM).
- Quy hoạch/phê duyệt = 4 khối container: container6 (căn cứ lập DA), container1 (căn cứ lập QH),
  container[G17-KQ002911] (chủ trương ĐT), container[G17-KQ002916] (môi trường).
- Nhiều field KHÔNG có trong Tờ trình (loaiDuAn, dienTich, chiPhiXayDung/ThietBi, mucTieuDauTu, hinhThucQLDA,
  PCCC, ATGT, loaiHinhBatDongSan, giải thưởng) → KHÔNG bịa, để trống cho cán bộ bổ sung.

Mẫu = Tờ trình 139/TTr-TĐDPSB — Dự án Khách sạn Đồng Nà, CĐT Cty CP Thủy điện Đạt Phương Sông Bung.
"""

_MAX_BO_MON = 8  # số dòng datagrid chủ trì bộ môn (thiết kế / thẩm tra) tối đa.

# --- Người nộp hồ sơ (Phần I) — từ CCCD người nộp ---
_NOP = [
    ("HoTen", "Họ tên NGƯỜI NỘP HỒ SƠ (chủ tài khoản đăng nhập/đại diện nộp) — CCCD. IN HOA."),
    ("SoDinhDanh", "Số CCCD/định danh NGƯỜI NỘP — CCCD. Chỉ chữ số, ưu tiên 12 số."),
    ("NgaySinh", "Ngày sinh người nộp, dd/mm/yyyy — CCCD."),
    ("GioiTinh", 'Giới tính người nộp: "Nam"/"Nữ" — CCCD.'),
    ("NgayCap", "Ngày cấp CCCD người nộp, dd/mm/yyyy."),
    ("NoiCap", 'Nơi cấp CCCD người nộp. CCCD gắn chip: "Cục Cảnh sát quản lý hành chính về trật tự xã '
        'hội"; thẻ căn cước mới: "Bộ Công an".'),
    ("NoiCuTru", "Nơi thường trú NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi}. tinh='Tỉnh/Thành phố …', "
        "xa=phường/xã, diaChi=số nhà/đường (KHÔNG kèm phường/xã/tỉnh)."),
    ("DienThoai", "Số điện thoại người nộp. Chỉ chữ số. CCCD không in SĐT → thường bỏ."),
    ("Email", "Email người nộp nếu có; thường không có → bỏ."),
]
FIELDS: list[dict] = [{"name": f"NguoiNop_{n}", "desc": d} for n, d in _NOP]

# --- Chủ đầu tư (Tờ trình mục I.4-I.5) ---
FIELDS += [
    {"name": "ChuDauTu_Ten", "desc": "Tên CHỦ ĐẦU TƯ (tổ chức) — Tờ trình mục I.5 'Chủ đầu tư'. Chép đầy đủ."},
    {"name": "ChuDauTu_MaSoThue", "desc": "Mã số thuế/mã doanh nghiệp CHỦ ĐẦU TƯ — Tờ trình I.5 'Mã số "
        "thuế'. Chỉ chữ số."},
    {"name": "ChuDauTu_DiaChi", "desc": "Địa chỉ trụ sở CHỦ ĐẦU TƯ, object {quocGia,tinh,xa,diaChi} — Tờ "
        "trình I.5 'Địa chỉ'. tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/thôn/đường."},
    {"name": "ChuDauTu_DienThoai", "desc": "Điện thoại CHỦ ĐẦU TƯ — Tờ trình I.5 'Điện thoại'. Chỉ chữ số."},
    {"name": "ChuDauTu_NguoiQuyetDinhDauTu", "desc": "Người quyết định đầu tư — Tờ trình mục I.4 'Người "
        "quyết định đầu tư' (vd 'Chủ tịch HĐQT Công ty …'). Chép nguyên văn."},
]

# --- Thông tin chung dự án (Tờ trình mục I) ---
FIELDS += [
    {"name": "DuAn_Ten", "desc": "Tên dự án — Tờ trình mục I.1 'Tên dự án'."},
    {"name": "DuAn_DiaDiem", "desc": "ĐỊA ĐIỂM XÂY DỰNG dự án, object {quocGia,tinh,xa,diaChi} — Tờ trình "
        "(địa điểm/khu vực dự án). tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=chi tiết. KHÁC địa chỉ "
        "chủ đầu tư."},
    {"name": "DuAn_Nhom", "desc": 'Nhóm dự án — Tờ trình I.2 "Nhóm dự án" (vd "Nhóm A"/"Nhóm B"/"Nhóm C").'},
    {"name": "DuAn_LoaiCongTrinh", "desc": "Loại công trình chính — Tờ trình I.3 'Loại...công trình chính' "
        "(vd 'Công trình dân dụng')."},
    {"name": "DuAn_CapCongTrinh", "desc": "Cấp công trình chính — Tờ trình I.3 'cấp công trình chính' (vd "
        "'Công trình cấp II', 'Cấp I', 'Cấp đặc biệt')."},
    {"name": "DuAn_ThoiHanSuDung", "desc": "Thời hạn sử dụng công trình chính theo thiết kế — Tờ trình I.3. "
        "CHỈ SỐ NĂM (vd '50')."},
    {"name": "DuAn_TongMucDauTu", "desc": "Giá trị tổng mức đầu tư — Tờ trình I.7. CHỈ CHỮ SỐ (đồng), bỏ "
        "dấu chấm/'đồng' (vd '774477000000')."},
    {"name": "DuAn_NguonVon", "desc": "Nguồn vốn đầu tư — Tờ trình I.8 'Nguồn vốn đầu tư' (chép nguyên văn, "
        "vd 'Vốn tự có, vốn vay ngân hàng và các nguồn vốn hợp pháp khác')."},
    {"name": "DuAn_QuyMo", "desc": "Quy mô đầu tư — Tờ trình I.15 'Phạm vi trình thẩm định' / quy mô (vd "
        "'250 phòng, 1 tầng hầm, 6 tầng nổi và mái'). Chép mô tả quy mô."},
    {"name": "DuAn_TienDoTuNgay", "desc": "Ngày BẮT ĐẦU tiến độ dự án, dd/mm/yyyy — Tờ trình I.9 'Tiến độ "
        "thực hiện'. Nếu ghi theo quý → quy đổi ngày đầu quý (vd 'quý II/2026'→'01/04/2026')."},
    {"name": "DuAn_TienDoDenNgay", "desc": "Ngày KẾT THÚC tiến độ dự án, dd/mm/yyyy — Tờ trình I.9. Nếu "
        "ghi theo quý → quy đổi ngày cuối quý (vd 'quý III/2028'→'30/09/2028')."},
    {"name": "DuAn_LaDieuChinh", "desc": 'true nếu đây là hồ sơ thẩm định BCNCKT ĐIỀU CHỈNH (tiêu đề/nội '
        'dung Tờ trình ghi "điều chỉnh"); false/bỏ nếu thẩm định LẦN ĐẦU.'},
    {"name": "DuAn_LoaiHinhBDS", "desc": 'Loại hình bất động sản của dự án — chọn 1 nhóm theo công năng: '
        '"1" nếu là NHÀ Ở (nhà ở riêng lẻ/thương mại/công vụ/tái định cư/xã hội/lưu trú công nhân/lực lượng '
        'vũ trang); "2" nếu là công trình có CÔNG NĂNG phục vụ giáo dục/y tế/thể thao/văn hóa/văn phòng/'
        'thương mại/dịch vụ/DU LỊCH/LƯU TRÚ/công nghiệp hoặc HỖN HỢP (vd KHÁCH SẠN, trường, bệnh viện, văn '
        'phòng, TTTM); "3" nếu loại công trình xây dựng khác. Suy từ tên dự án + loại công trình chính.'},
]

# --- Quy hoạch làm căn cứ (Tờ trình mục IV.1.c) ---
FIELDS += [
    {"name": "QHDuAn_Ten", "desc": "Tên quy hoạch làm CĂN CỨ LẬP DỰ ÁN — Tờ trình IV.1.c (vd 'Quy hoạch chi "
        "tiết xây dựng 1/500 Khu đô thị …')."},
    {"name": "QHDuAn_So", "desc": "Số quyết định phê duyệt quy hoạch (căn cứ lập dự án) — Tờ trình IV.1.c "
        "(vd '3283/QĐ-UBND')."},
    {"name": "QHDuAn_Ngay", "desc": "Ngày QĐ phê duyệt quy hoạch (căn cứ lập dự án), dd/mm/yyyy."},
    {"name": "QHDuAn_CoQuan", "desc": "Cơ quan ban hành QĐ quy hoạch (căn cứ lập dự án) — vd 'UBND tỉnh …'."},
    {"name": "QHQuyHoach_Ten", "desc": "Tên quy hoạch/điều chỉnh làm CĂN CỨ LẬP QUY HOẠCH (nếu có văn bản "
        "quy hoạch thứ 2, vd điều chỉnh cục bộ) — Tờ trình IV.1.c. Bỏ nếu chỉ 1 quy hoạch."},
    {"name": "QHQuyHoach_So", "desc": "Số QĐ phê duyệt (căn cứ lập quy hoạch) — vd '1889/QĐ-UBND'."},
    {"name": "QHQuyHoach_Ngay", "desc": "Ngày QĐ (căn cứ lập quy hoạch), dd/mm/yyyy."},
    {"name": "QHQuyHoach_CoQuan", "desc": "Cơ quan ban hành QĐ (căn cứ lập quy hoạch)."},
]

# --- Văn bản chủ trương đầu tư & môi trường (Tờ trình mục IV.1.a-b) ---
FIELDS += [
    {"name": "ChuTruong_So", "desc": "Số văn bản CHỦ TRƯƠNG/chấp thuận đầu tư — Tờ trình IV.1.a (vd "
        "'2383/STC-KTTN')."},
    {"name": "ChuTruong_Ngay", "desc": "Ngày văn bản chủ trương đầu tư, dd/mm/yyyy."},
    {"name": "ChuTruong_CoQuan", "desc": "Cơ quan ban hành văn bản chủ trương đầu tư (vd 'Sở Tài chính …')."},
    {"name": "MoiTruong_So", "desc": "Số QĐ phê duyệt ĐTM/giấy phép MÔI TRƯỜNG — Tờ trình IV.1.b (vd "
        "'3647/QĐ-UBND'). Bỏ nếu không có."},
    {"name": "MoiTruong_Ngay", "desc": "Ngày QĐ môi trường, dd/mm/yyyy."},
    {"name": "MoiTruong_CoQuan", "desc": "Cơ quan ban hành QĐ môi trường (vd 'UBND tỉnh …')."},
]

# --- Năng lực nhà thầu (Tờ trình mục IV.3) ---
FIELDS += [
    {"name": "KhaoSat_TenDN", "desc": "Tên đơn vị KHẢO SÁT xây dựng — Tờ trình IV.3.1."},
    {"name": "KhaoSat_MaDN", "desc": "Số chứng chỉ NĂNG LỰC hoạt động xây dựng của ĐƠN VỊ khảo sát — Tờ "
        "trình IV.3.1 (vd 'BXD-00012703'). ⚠ ĐÂY KHÔNG PHẢI mã số doanh nghiệp (MST) — form có ô riêng cho "
        "MST 10 số mà Tờ trình không có; chỉ trích để tham chiếu."},
    {"name": "KhaoSat_ChuNhiem", "desc": "Họ tên cá nhân chủ trì/chủ nhiệm khảo sát — Tờ trình IV.3.1."},
    {"name": "KhaoSat_MaCC", "desc": "Mã số chứng chỉ hành nghề chủ nhiệm khảo sát — Tờ trình IV.3.1 (vd "
        "'BXD-00039880')."},
    {"name": "ThietKe_TenDN", "desc": "Tên đơn vị TƯ VẤN THIẾT KẾ (chủ trì nếu nhiều) — Tờ trình IV.3.2."},
    {"name": "ThietKe_MaDN", "desc": "Số chứng chỉ NĂNG LỰC hoạt động của ĐƠN VỊ thiết kế — Tờ trình "
        "IV.3.2 (vd 'SOL-00060462'). ⚠ KHÔNG PHẢI MST; chỉ trích để tham chiếu."},
    {"name": "ThietKe_ChuNhiem", "desc": "Họ tên chủ nhiệm/chủ trì thiết kế — Tờ trình IV.3.2 (vd 'KTS …')."},
    {"name": "ThietKe_MaCC", "desc": "Mã số chứng chỉ hành nghề chủ nhiệm thiết kế — Tờ trình IV.3.2."},
    {"name": "ThamTra_TenDN", "desc": "Tên đơn vị TƯ VẤN THẨM TRA — Tờ trình IV.3.3.a."},
    {"name": "ThamTra_MaDN", "desc": "Số chứng chỉ NĂNG LỰC hoạt động của ĐƠN VỊ thẩm tra — Tờ trình "
        "IV.3.3.a (vd 'BXD-00016178'). ⚠ KHÔNG PHẢI MST; chỉ trích để tham chiếu."},
    {"name": "ThamTra_ChuNhiem", "desc": "Họ tên chủ nhiệm thẩm tra thiết kế — Tờ trình IV.3.3.a."},
    {"name": "ThamTra_MaCC", "desc": "Mã số chứng chỉ hành nghề chủ nhiệm thẩm tra — Tờ trình IV.3.3.a."},
    {"name": "BoMonThietKe", "desc": "MẢNG các cá nhân chủ trì BỘ MÔN THIẾT KẾ — Tờ trình IV.3.2. Mỗi phần "
        "tử {boMon, hoTen, maCC}: boMon=bộ môn (Kết cấu/Giao thông/Cấp-thoát nước/Cấp điện…); hoTen=họ tên "
        "chủ trì bộ môn; maCC=mã số chứng chỉ hành nghề. Trích đủ các dòng có trong Tờ trình."},
    {"name": "BoMonThamTra", "desc": "MẢNG các cá nhân chủ trì BỘ MÔN THẨM TRA — Tờ trình IV.3.3.a. Mỗi "
        "phần tử {boMon, hoTen, maCC}: boMon=bộ môn thẩm tra (Kiến trúc/Cơ điện/Cấp-thoát nước/Hạ tầng kỹ "
        "thuật…); hoTen=họ tên; maCC=mã số chứng chỉ. Trích đủ các dòng."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _d in ("NguoiNop_NgaySinh", "NguoiNop_NgayCap", "DuAn_TienDoTuNgay", "DuAn_TienDoDenNgay",
           "QHDuAn_Ngay", "QHQuyHoach_Ngay", "ChuTruong_Ngay", "MoiTruong_Ngay"):
    COMPACT_COMP_BY_NAME[_d] = "x-date"
for _a in ("NguoiNop_NoiCuTru", "ChuDauTu_DiaChi", "DuAn_DiaDiem"):
    COMPACT_COMP_BY_NAME[_a] = "x-select-area"
for _arr in ("BoMonThietKe", "BoMonThamTra"):
    COMPACT_COMP_BY_NAME[_arr] = "x-array"

# ---- UI Form.io fields (data[...]) — comp dom-*. Field-key CHUẨN từ HTML thật.
UI_COMP_BY_NAME = {
    # ===== Phần I: NGƯỜI NỘP (occurrence 0 cho province/district/address) =====
    "data[chonDoiTuong]": "dom-select",
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[email]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[phoneNumber]": "dom-input",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    # ===== Phần II: DOANH NGHIỆP (khi Tổ chức) = chủ đầu tư =====
    "data[organization]": "dom-input",
    "data[taxCode]": "dom-input",
    "data[nation1]": "dom-select",
    "data[province1]": "dom-select",
    "data[district1]": "dom-select",
    "data[address1]": "dom-input",
    "data[organizationPhoneNumber]": "dom-input",
    # ===== Phần III: CHỦ ĐẦU TƯ =====
    "data[nguoiQuyetDinhDauTu]": "dom-input",
    "data[chuDauTu]": "dom-input",
    "data[maChuDauTu]": "dom-input",
    "data[diaChiChuDauTu]": "dom-input",
    "data[soDienThoaiChuDauTu]": "dom-input",
    # ===== Phần IV: THÔNG TIN CHUNG DỰ ÁN (occurrence 1 cho địa điểm) =====
    "data[thBCNCKTDieuChinh]": "dom-checkbox",
    "data[tenDuAn]": "dom-input",
    "data[nhomDuAn]": "dom-select",
    "data[loaiDuAn]": "dom-select",
    "data[loaiCongTrinh]": "dom-select",
    "data[loaiHinhBatDongSan][]": "dom-checkbox",
    "data[capCongTrinh]": "dom-select",
    "data[thoiHanSuDungCongTrinhChinh]": "dom-input",
    "data[tongMucDauTu]": "dom-input",
    "data[nguonVonDauTu]": "dom-select",
    "data[quyMoDauTu]": "dom-input",
    "data[tuNgay]": "dom-date",
    "data[denNgay]": "dom-date",
    # ===== Phần VI: QUY HOẠCH / PHÊ DUYỆT (container nested) =====
    "data[container6][tenQuyHoachCanCuLapDuAn]": "dom-input",
    "data[container6][G17-KQ002914_soQuyetDinh]": "dom-input",
    "data[container6][G17-KQ002914_ngay]": "dom-date",
    "data[container6][G17-KQ002914_coQuan]": "dom-input",
    "data[container1][tenQuyHoachCanCuLapQuyHoach]": "dom-input",
    "data[container1][G17-KQ002915_soQuyetDinh]": "dom-input",
    "data[container1][G17-KQ002915_ngay]": "dom-date",
    "data[container1][G17-KQ002915_coQuan]": "dom-input",
    "data[container][G17-KQ002911_soQuyetDinh]": "dom-input",
    "data[container][G17-KQ002911_ngay]": "dom-date",
    "data[container][G17-KQ002911_coQuan]": "dom-input",
    "data[container][G17-KQ002916_soQuyetDinh]": "dom-input",
    "data[container][G17-KQ002916_ngay]": "dom-date",
    "data[container][G17-KQ002916_coQuan]": "dom-input",
    # ===== Phần VII: NĂNG LỰC NHÀ THẦU =====
    "data[tenDoanhNghiepKhaoSat]": "dom-input",
    "data[maSoDoanhNghiepKhaoSat]": "dom-input",
    "data[tenChuNhiemKhaoSatXayDung]": "dom-input",
    "data[maSoChungChiChuNhiemKhaoSat]": "dom-input",
    "data[tenDoanhNghiepTuVanThietKe]": "dom-input",
    "data[maSoDoanhNghiepTuVanThietKe]": "dom-input",
    "data[tenChuNhiemThietKe]": "dom-input",
    "data[maSoChungChiChuNhiemThietKe]": "dom-input",
    "data[tenDoanhNghiepThamTra]": "dom-input",
    "data[maSoDoanhNghiepThamTra]": "dom-input",
    "data[tenChuNhiemKhaoSatXayDung1]": "dom-input",       # ⚠ = chủ nhiệm THẨM TRA (key nhầm).
    "data[maSoChungChiChuNhiemKhaoSat1]": "dom-input",     # ⚠ = mã CC chủ nhiệm THẨM TRA.
}

# ===== Datagrid bộ môn thiết kế (khaoSatXayDung[i]) & thẩm tra (thamTraThietKe[i]) =====
for _i in range(_MAX_BO_MON):
    UI_COMP_BY_NAME[f"data[khaoSatXayDung][{_i}][boMonThietKe]"] = "dom-input"
    UI_COMP_BY_NAME[f"data[khaoSatXayDung][{_i}][hoVaTenThietKe]"] = "dom-input"
    UI_COMP_BY_NAME[f"data[khaoSatXayDung][{_i}][maSoChungChiHanhNgheThietKe]"] = "dom-input"
    UI_COMP_BY_NAME[f"data[thamTraThietKe][{_i}][boMonThamTra]"] = "dom-input"
    UI_COMP_BY_NAME[f"data[thamTraThietKe][{_i}][hoVaTenThamTra]"] = "dom-input"
    UI_COMP_BY_NAME[f"data[thamTraThietKe][{_i}][maSoChungChiHanhNgheThamTra]"] = "dom-input"
