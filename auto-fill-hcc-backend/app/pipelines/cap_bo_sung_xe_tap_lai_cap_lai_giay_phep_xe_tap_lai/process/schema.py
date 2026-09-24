"""Compact schema cho "Cấp bổ sung xe tập lái, cấp lại Giấy phép xe tập lái" — cổng DVC Bộ Xây dựng
dvc.moc.gov.vn (Form.io). LLM chỉ trả FACT nguồn; `mapper.enrich` suy ra tất định các ô data[...].

- Phần I   Người nộp       : data[...] PHẲNG — từ CCCD người nộp (nếu có).
- Phần II  Cơ sở đào tạo   : data[organization1/organization2/organization] — DS đề nghị.
- Phần II.a Bảng xe        : DATAGRID data[tbantest][i][...] (x-array XeTapLai).
- Phần II.b Ký             : data[TinTTTe] (select tỉnh) + data[kyTenDongDau]. TDTTK disabled → bỏ.
"""

_MAX_XE = 20  # số dòng xe tối đa trên datagrid.

# --- Người nộp hồ sơ (Phần I) — CHỈ từ thẻ CCCD ---
_NOP_FIELDS = [
    ("HoTen", "Họ và tên NGƯỜI NỘP trên thẻ CCCD/CMND. IN HOA như thẻ. Không có thẻ CCCD → bỏ."),
    ("NgaySinh", "Ngày sinh NGƯỜI NỘP, dd/mm/yyyy — CCCD."),
    ("GioiTinh", 'Giới tính NGƯỜI NỘP: "Nam"/"Nữ" — CCCD.'),
    ("SoDinhDanh", "Số CCCD/định danh NGƯỜI NỘP (12 chữ số). Chỉ chữ số."),
    ("NgayCap", "Ngày cấp CCCD NGƯỜI NỘP, dd/mm/yyyy."),
    ("NoiCap", 'Nơi cấp/cơ quan cấp CCCD NGƯỜI NỘP. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT '
        'TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ căn cước mới ghi "BỘ CÔNG AN" '
        '→ "Bộ Công an".'),
    ("QuocTich", 'Quốc tịch NGƯỜI NỘP (CCCD). Mặc định "Việt Nam".'),
    ("ThuongTru", "NƠI THƯỜNG TRÚ/cư trú NGƯỜI NỘP trên CCCD, object {quocGia,tinh,xa,diaChi}. tinh='Tỉnh/"
        "Thành phố …', xa=phường/xã, diaChi=số nhà/đường/thôn/tổ (KHÔNG kèm phường/xã/tỉnh)."),
    ("DienThoai", "Số điện thoại DI ĐỘNG của NGƯỜI NỘP nếu giấy tờ ghi rõ là của người đó. Chỉ chữ số. KHÔNG "
        "lấy số máy bàn/điện thoại của trường."),
    ("Email", "Email cá nhân NGƯỜI NỘP nếu có; thường không có → bỏ."),
]

FIELDS: list[dict] = [{"name": f"NguoiNop_{n}", "desc": d} for n, d in _NOP_FIELDS]

# --- Cơ sở đào tạo + văn bản đề nghị (Phần II) — DS đề nghị ---
FIELDS += [
    {"name": "CoSo_CoQuanChuQuan", "desc": "Tên CƠ QUAN CHỦ QUẢN — dòng 1 góc trên bên trái DS đề nghị, phía "
        "trên tên trường (vd 'UBND TỈNH HÀ TĨNH', 'SỞ LAO ĐỘNG …'). Chép nguyên văn."},
    {"name": "CoSo_Ten", "desc": "Tên CƠ SỞ ĐÀO TẠO lái xe — dòng tên đơn vị ban hành góc trên bên trái DS "
        "đề nghị (ngay dưới cơ quan chủ quản, trên dòng 'Số: …'). Giữ nguyên chữ HOA như văn bản, ghép các "
        "dòng xuống hàng thành một tên. DS không có → lấy 'BÊN THUÊ XE' trong HĐ thuê xe."},
    {"name": "CoSo_TenTrongCau", "desc": "Tên trường/trung tâm như viết trong CÂU ĐỀ NGHỊ mở đầu DS ('<Tên "
        "trường> đề nghị Sở Xây dựng … xem xét, cấp giấy phép xe tập lái …'). Chép nguyên văn, giữ hoa/thường."},
    {"name": "CoSo_Email", "desc": "Email nhận kết quả của cơ sở đào tạo — DS đề nghị mục 'Trực tuyến: trên hòm "
        "thư điện tử: …'."},
    {"name": "DeNghi_KinhGui", "desc": "Dòng 'Kính gửi' của DS đề nghị (vd 'Sở Xây dựng Hà Tĩnh'). Chép nguyên văn."},
    {"name": "DeNghi_DiaDanh", "desc": "Địa danh ở dòng '<Địa danh>, ngày … tháng … năm …' cuối DS đề nghị — "
        "chỉ lấy TÊN TỈNH/THÀNH PHỐ (vd 'Hà Tĩnh')."},
    {"name": "DeNghi_ChucDanhKy", "desc": "Chức danh người ký DS đề nghị, gồm cả dòng 'KT.'/'TL.' nếu có (vd "
        "'KT. HIỆU TRƯỞNG - PHÓ HIỆU TRƯỞNG', 'GIÁM ĐỐC')."},
    {"name": "DeNghi_NguoiKy", "desc": "Họ tên người ký DS đề nghị (dòng tên dưới chữ ký/dấu)."},
]

# --- Bảng xe (Phần II.a — datagrid) ---
FIELDS += [
    {"name": "XeTapLai", "desc": "MẢNG các xe đề nghị cấp giấy phép xe tập lái — mỗi xe 1 object, đúng số "
        "dòng trong bảng DS đề nghị, theo thứ tự TT. Khoá (bỏ khoá nếu không có): "
        "\"stt\" (cột TT), "
        "\"bienSo\" (biển số đăng ký ĐẦY ĐỦ như GCN ĐK xe, gồm cả ký hiệu xe tập lái, vd '38A-123.45 (T)'), "
        "\"loaiSoHuu\" ('hop_dong' nếu DS đánh dấu cột 'Xe hợp đồng' HOẶC có HĐ thuê xe cho xe đó HOẶC chủ xe "
        "trên GCN ĐK là người/đơn vị khác cơ sở đào tạo; 'co_so' nếu DS đánh dấu cột 'Xe của cơ sở đào tạo' "
        "hoặc chủ xe chính là cơ sở đào tạo), "
        "\"chuXe\" (tên chủ xe trên GCN ĐK xe), "
        "\"nhanHieu\" (nhãn hiệu — CHỈ tên hãng như GCN ĐK 'Nhãn hiệu', vd 'KIA'; GCN kiểm định ghi kèm tên "
        "thương mại 'KIA SOLUTO…' → chỉ lấy 'KIA'), "
        "\"loaiXe\" (GCN ĐK 'Loại xe', vd 'Ô tô con tập lái'), "
        "\"soDongCo\" (số máy/số động cơ đầy đủ), "
        "\"soKhung\" (số khung đầy đủ), "
        "\"ngayCapKiemDinh\" (GCN kiểm định 'Ngày KĐ' / DS cột 'Ngày cấp', dd/mm/yyyy), "
        "\"ngayHetHanKiemDinh\" (GCN kiểm định 'có hiệu lực đến hết ngày' / DS cột 'Ngày hết hạn', dd/mm/yyyy), "
        "\"soGiayKiemDinh\" (DS cột 'Số giấy chứng nhận' / số seri tem kiểm định), "
        "\"ghiChu\" (DS cột 'Ghi chú' nếu có chữ). "
        "Ví dụ: [{\"stt\":\"1\",\"bienSo\":\"38A-123.45 (T)\",\"loaiSoHuu\":\"hop_dong\",\"chuXe\":\"LÊ VĂN AN\","
        "\"nhanHieu\":\"KIA\",\"loaiXe\":\"Ô tô con tập lái\",\"soDongCo\":\"G4LAKP123456\",\"soKhung\":"
        "\"RNYAB51BAKC012345\",\"ngayCapKiemDinh\":\"15/03/2026\",\"ngayHetHanKiemDinh\":\"14/03/2028\"}]."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["NguoiNop_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_ThuongTru"] = "x-select-area"
COMPACT_COMP_BY_NAME["XeTapLai"] = "x-array"

# ---- UI Form.io fields (data[...]) — comp dom-*. Field-key lấy từ HTML thật (file mapping).
UI_COMP_BY_NAME = {
    # ----- Phần I: NGƯỜI NỘP HỒ SƠ -----
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
    "data[district]": "dom-select",   # nhãn "Phường/xã"
    "data[address]": "dom-input",

    # ----- Phần II: cơ sở đào tạo -----
    "data[organization1]": "dom-input",  # "Cơ quản chủ quản" (lỗi chính tả của form)
    "data[organization2]": "dom-input",  # "Cơ sở đào tạo"
    "data[organization]": "dom-input",   # "Trường (Trung tâm):"

    # ----- Phần II.b: ký -----
    "data[TinTTTe]": "dom-select",       # "Tại" — mặc định Thành phố Đà Nẵng, phải đổi
    "data[kyTenDongDau]": "dom-input",   # THỦ TRƯỞNG CƠ SỞ ĐÀO TẠO
}

# ----- Phần II.a: DATAGRID bảng xe (data[tbantest][i][...]) -----
# ⚠ key KHÔNG trùng nghĩa nhãn cột (giữ nguyên theo DOM):
#   trongtai = Xe của cơ sở đào tạo · namsanxuat = Xe hợp đồng · sokhung = Loại xe · mauson = Số khung ·
#   cuakhaunhapxuat = Ghi chú · ngayCap…Bvmt = Ngày cấp GCN kiểm định · ngayCap…Bvmt1 = Ngày hết hạn.
XE_COLS = {
    "stt": "dom-input",
    "biensoxe": "dom-input",
    "trongtai": "dom-input",
    "namsanxuat": "dom-input",
    "nhanhieu": "dom-input",
    "sokhung": "dom-input",
    "somay": "dom-input",
    "mauson": "dom-input",
    # Ô NGÀY (flatpickr) trong datagrid → dom-date để FE setDate + reapplyStandardDatagridDates.
    "ngayCapGiayChungNhanKiemDinhAtktBvmt": "dom-date",
    "ngayCapGiayChungNhanKiemDinhAtktBvmt1": "dom-date",
    "cuakhaunhapxuat": "dom-input",
}
for _i in range(_MAX_XE):
    for _col, _comp in XE_COLS.items():
        UI_COMP_BY_NAME[f"data[tbantest][{_i}][{_col}]"] = _comp
