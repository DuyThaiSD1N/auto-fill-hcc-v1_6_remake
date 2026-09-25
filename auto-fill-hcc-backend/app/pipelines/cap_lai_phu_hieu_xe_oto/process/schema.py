"""Compact schema cho "Cấp, cấp lại Phù hiệu cho xe ô tô, xe bốn bánh có gắn động cơ kinh doanh vận tải"
(TTHC 2.002288) — cổng DVC Bộ Xây dựng dvc.moc.gov.vn (Form.io). LLM chỉ trả FACT nguồn; `mapper.enrich` suy
ra tất định các ô data[...].

- Phần I    Người nộp            : data[...] PHẲNG — từ CCCD người nộp (nếu có); không có thì tài khoản tự đổ.
- Phần II   Doanh nghiệp người nộp: data[organization/address1/taxCode/province1/district1/...] — đơn vị KDVT.
- Phần III  Văn bản đề nghị      : data[SoVanBan/TinhThanh/DT/T_CoQuan/dichVu] — Giấy đề nghị.
- Phần IV   Đơn vị KDVT          : data[T_DonViKinhDoanh][...] — Giấy đề nghị / HĐ dịch vụ / GCN ĐK / GPKDVT.
- Phần V    Thẩm định            : data[ThamDinh][SoLuongNopLai/DeNghiDuocCap].
- Phần VI-VII Phương tiện        : bấm "Thêm phương tiện" (comp dom-click) rồi điền panel
                                   data[ThamDinh][ThemPhuongTienRaw][...] cho xe ĐẦU TIÊN. Nút "Thêm" lưu xe
                                   vào danh sách để người dùng tự bấm sau khi soát.
"""

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
        "Thành phố …', xa='Phường/Xã …', diaChi=số nhà/đường/thôn/tổ (KHÔNG kèm phường/xã/tỉnh)."),
    ("DienThoai", "Số điện thoại DI ĐỘNG của NGƯỜI NỘP nếu giấy tờ ghi rõ là của người đó (vd Bên B của hợp "
        "đồng CÙNG họ tên người trên CCCD → số 'Điện thoại' của Bên B). KHÔNG lấy số của đơn vị KDVT/Bên A. "
        "Chép nguyên phần đọc được, bị che thì KHÔNG đoán thêm chữ số."),
    ("Email", "Email cá nhân NGƯỜI NỘP nếu có; thường không có → bỏ."),
]

FIELDS: list[dict] = [{"name": f"NguoiNop_{n}", "desc": d} for n, d in _NOP_FIELDS]

# --- Đơn vị kinh doanh vận tải (Phần II + IV) ---
FIELDS += [
    {"name": "DonVi_Ten", "desc": "Tên ĐẦY ĐỦ của ĐƠN VỊ KINH DOANH VẬN TẢI (doanh nghiệp/HTX/hộ KD). Nguồn: "
        "Giấy đề nghị '1. Tên đơn vị kinh doanh vận tải' → HĐ dịch vụ/HĐ thuê xe 'BÊN A' → GCN đăng ký DN/HTX → "
        "GPKDVT. Giấy đề nghị hay VIẾT TẮT ('HTX DV …', 'CTY TNHH …') → nếu giấy khác (HĐ, con dấu, GCN) ghi "
        "bản ĐẦY ĐỦ ('HTX DỊCH VỤ …', 'CÔNG TY TNHH …') thì lấy bản đầy đủ. Giữ chữ HOA như giấy tờ."},
    {"name": "DonVi_LoaiHinh", "desc": 'Loại hình đơn vị KDVT — MỘT trong: "Hợp tác xã", "Công ty Cổ phần, '
        'TNHH, TNHH MTV", "Doanh nghiệp tư nhân", "Hộ kinh doanh", "Công ty liên doanh", "Doanh nghiệp nhà '
        'nước". Suy từ tên đơn vị (HTX…→"Hợp tác xã"; Công ty CP/TNHH→"Công ty Cổ phần, TNHH, TNHH MTV").'},
    {"name": "DonVi_MaSoThue", "desc": "Mã số thuế / mã số doanh nghiệp / mã số HTX của đơn vị KDVT (HĐ 'Mã số "
        "thuế', GCN đăng ký, GPKDVT, số S.G.C.N trên con dấu). Chỉ chữ số (và dấu '-' nếu có mã chi nhánh). "
        "Chữ số bị che/mờ → giữ phần đọc được, KHÔNG đoán thêm."},
    {"name": "DonVi_TenQuocTe", "desc": "Tên quốc tế/tên tiếng Anh của đơn vị nếu giấy tờ ghi (thường ở GCN "
        "đăng ký). Không có → bỏ."},
    {"name": "DonVi_DiaChi", "desc": "Địa chỉ TRỤ SỞ đơn vị KDVT, object {quocGia,tinh,xa,diaChi}. Nguồn: Giấy "
        "đề nghị '2. Địa chỉ' → HĐ 'Bên A - Địa chỉ' → GCN đăng ký. tinh='Tỉnh/Thành phố …', xa='Phường/Xã …' "
        "(giữ tiền tố), diaChi=số nhà/thôn/tổ dân phố (KHÔNG kèm phường/xã/tỉnh)."},
    {"name": "DonVi_DienThoai", "desc": "Số điện thoại của đơn vị KDVT — Giấy đề nghị '3. Số điện thoại' → HĐ "
        "'Bên A - Điện thoại'. Có nhiều số → lấy số ĐẦU TIÊN. Chép nguyên như giấy (kể cả dấu chấm)."},
    {"name": "DonVi_Email", "desc": "Email liên hệ của đơn vị KDVT nếu giấy tờ ghi rõ 'Email'/'Thư điện tử'. "
        "⚠ KHÔNG lấy 'Tài khoản' đăng nhập hệ thống giám sát hành trình (khung 'Đơn vị lắp đặt/Trang web/Tài "
        "khoản/Mật khẩu') — đó không phải email liên hệ."},
    {"name": "DonVi_Fax", "desc": "Số fax của đơn vị nếu có."},
    {"name": "DonVi_NguoiDaiDien", "desc": "Họ tên NGƯỜI ĐẠI DIỆN đơn vị KDVT — tên dưới chữ ký 'Đại diện đơn vị "
        "kinh doanh vận tải' của Giấy đề nghị, hoặc 'Bên A - Đại diện: Ông/Bà …' của HĐ. Không kèm 'Ông/Bà'."},
    {"name": "HopDong_BenB_HoTen", "desc": "Họ tên BÊN B của hợp đồng dịch vụ xã viên/HĐ thuê xe/HĐ hợp tác — "
        "bên KHÔNG phải đơn vị KDVT (xã viên, bên cho thuê). Không kèm 'Ông/Bà'. Không có hợp đồng → bỏ."},
    {"name": "HopDong_BenB_DienThoai", "desc": "Số điện thoại của BÊN B trong hợp đồng (dòng 'Số điện thoại' "
        "dưới Bên B). Chép nguyên phần đọc được, bị che thì KHÔNG đoán thêm chữ số."},
    {"name": "HopDong_BenB_DiaChi", "desc": "Địa chỉ của BÊN B trong hợp đồng, object {quocGia,tinh,xa,diaChi}. "
        "tinh='Tỉnh/Thành phố …', xa='Phường/Xã …', diaChi=số nhà/thôn/tổ dân phố (KHÔNG kèm phường/xã/tỉnh)."},
    {"name": "HopDong_BenB_SoCCCD", "desc": "Số CCCD/CMND của BÊN B ghi trong hợp đồng. Chỉ chữ số, bị che thì "
        "giữ phần đọc được, KHÔNG đoán thêm."},
    {"name": "HopDong_BenB_NgayCapCCCD", "desc": "Ngày cấp CCCD của BÊN B ghi trong hợp đồng, dd/mm/yyyy. Bị "
        "che/thiếu → bỏ."},
    {"name": "HopDong_BenB_NoiCapCCCD", "desc": "Nơi cấp CCCD của BÊN B ghi trong hợp đồng ('Cục Cảnh sát QLHC "
        "về TTXH' → 'Cục Cảnh sát quản lý hành chính về trật tự xã hội')."},
    {"name": "GCNDK_SoGiay", "desc": "Số Giấy chứng nhận đăng ký doanh nghiệp/HTX/hộ kinh doanh — CHỈ khi có "
        "GCN đăng ký trong hồ sơ. Không có → bỏ."},
    {"name": "GCNDK_CoQuanCap", "desc": "Cơ quan cấp GCN đăng ký doanh nghiệp/HTX (vd 'Phòng Đăng ký kinh "
        "doanh - Sở Tài chính …'). Chỉ khi có GCN đăng ký."},
    {"name": "GCNDK_NgayCap", "desc": "Ngày đăng ký lần đầu / ngày cấp GCN đăng ký doanh nghiệp/HTX, dd/mm/yyyy."},
    {"name": "GPKD_SoGiay", "desc": "Số GIẤY PHÉP KINH DOANH VẬN TẢI BẰNG XE Ô TÔ (GPKDVT) — CHỈ khi có "
        "GPKDVT trong hồ sơ."},
    {"name": "GPKD_NgayCap", "desc": "Ngày cấp GPKDVT, dd/mm/yyyy."},
    {"name": "GPKD_CapLanThu", "desc": "GPKDVT 'Cấp lần thứ …' / 'Đăng ký lần thứ …' — chỉ số."},
    {"name": "GPKD_CoQuanCap", "desc": "Cơ quan cấp GPKDVT (vd 'Sở Xây dựng tỉnh …', 'Sở Giao thông vận tải "
        "…'). Chép nguyên văn."},
]

# --- Giấy đề nghị cấp (cấp lại) phù hiệu (Phần III + V) ---
FIELDS += [
    {"name": "DeNghi_SoVanBan", "desc": "Số văn bản của GIẤY ĐỀ NGHỊ — dòng 'Số: …' góc trên bên trái, dưới tên "
        "đơn vị. Chép NGUYÊN VĂN cả chuỗi, KHÔNG cắt hậu tố viết tắt tên đơn vị sau dấu '-' (vd 'Số: 05/2026/GĐN-"
        "VTAB' → '05/2026/GĐN-VTAB'). KHÔNG lấy số của Hợp đồng dịch vụ/HĐ thuê xe."},
    {"name": "DeNghi_DiaDanh", "desc": "Địa danh ở dòng '<Địa danh>, ngày … tháng … năm …' của Giấy đề nghị — "
        "chỉ TÊN TỈNH/THÀNH PHỐ (vd 'Nghệ An')."},
    {"name": "DeNghi_NgayLap", "desc": "Ngày lập Giấy đề nghị (dòng địa danh, ngày tháng năm), dd/mm/yyyy."},
    {"name": "DeNghi_KinhGui", "desc": "Dòng 'Kính gửi' của Giấy đề nghị (vd 'Sở Xây dựng tỉnh Nghệ An'). Chép "
        "nguyên văn."},
    {"name": "DeNghi_LoaiDeNghi", "desc": '"cap_lai" nếu tiêu đề là "GIẤY ĐỀ NGHỊ CẤP LẠI PHÙ HIỆU" hoặc dòng '
        '"Đề nghị được cấp" ghi "cấp lại"; "cap" nếu đề nghị cấp mới.'},
    {"name": "DeNghi_SoLuongNopLai", "desc": "Giấy đề nghị 'Số lượng phù hiệu nộp lại: …' — chép nguyên (vd "
        "'Không', '02')."},
    {"name": "DeNghi_DuocCap", "desc": "Giấy đề nghị 'Đề nghị được cấp: …' — chép nguyên cụm sau dấu hai chấm "
        "(vd 'cấp lại 01 phù hiệu')."},
]

# --- Phương tiện (Phần VI-VII) ---
FIELDS += [
    {"name": "PhuongTien", "desc": "MẢNG các xe đề nghị cấp phù hiệu — mỗi xe 1 object, theo thứ tự bảng "
        "'Danh sách xe đề nghị cấp phù hiệu' của Giấy đề nghị. Ghép thông tin CÙNG một xe từ các giấy tờ theo "
        "biển số. Khoá (bỏ khoá nếu không có): "
        "\"bienSo\" (biển số ĐẦY ĐỦ — ưu tiên Chứng nhận đăng ký xe, KHÔNG kèm ký hiệu nhỏ '(V)'/'(T)' in cạnh), "
        "\"loaiXe\" (Chứng nhận đăng ký 'Loại xe (type)' nguyên văn), "
        "\"loaiPhuHieu\" (Giấy đề nghị cột 'Loại phù hiệu', vd 'XE TẢI', 'XE HỢP ĐỒNG', 'XE TAXI'), "
        "\"hanPhuHieu\" (Giấy đề nghị cột 'Cấp hạn phù hiệu', vd '02 năm'), "
        "\"nhanHieu\" (Nhãn hiệu (Brand) như Chứng nhận đăng ký, giữ khoảng trắng), "
        "\"soKhung\" (Số khung (Chassis N°) đầy đủ), "
        "\"soMay\" (Số máy (Engine N°) đầy đủ), "
        "\"mauSon\" (Màu sơn (Color)), "
        "\"trongTai\" (Trọng tải (Gross weight) / 'Sức chứa' / 'Tải trọng' tính bằng kg, vd '6.750 KG'), "
        "\"soCho\" (Số chỗ ngồi (Seats) — chỉ số), "
        "\"namSanXuat\" (năm sản xuất, 4 chữ số — CHỈ khi đọc được ĐỦ 4 chữ số trên giấy tờ; bị che/cắt như "
        "'20.', '20__' → BỎ khoá, KHÔNG đoán), "
        "\"nuocSanXuat\" (nước sản xuất, tiếng Việt, vd 'Việt Nam', 'Hàn Quốc'), "
        "\"nienHan\" (năm hết niên hạn sử dụng: HĐ 'Niên hạn sử dụng' hoặc Chứng nhận đăng ký 'Giá trị đến "
        "ngày (date of expiry)' — chỉ lấy NĂM 4 chữ số đọc được nguyên văn; bị che/cắt → BỎ khoá, KHÔNG tự "
        "tính từ năm sản xuất), "
        "\"chuXe\" (Tên chủ xe (Owner's full name) trên Chứng nhận đăng ký), "
        "\"ngayDangKy\" (ngày cấp Chứng nhận đăng ký — dòng '<Địa danh>, ngày … tháng … năm …' cạnh chữ ký "
        "Trưởng phòng, dd/mm/yyyy), "
        "\"loaiHopDong\" (nếu xe KHÔNG thuộc sở hữu đơn vị KDVT: 'thanh_vien_htx' khi là 'HỢP ĐỒNG DỊCH VỤ GIỮA "
        "XÃ VIÊN VÀ HỢP TÁC XÃ' / xe của xã viên; 'thue' khi là hợp đồng thuê xe/thuê phương tiện; 'hop_tac' "
        "khi là hợp đồng hợp tác kinh doanh), "
        "\"hopDongTuNgay\" (ngày hợp đồng bắt đầu hiệu lực — thường là ngày ký, dd/mm/yyyy), "
        "\"hopDongDenNgay\" (ngày hợp đồng hết hiệu lực, dd/mm/yyyy — vd điều khoản 'có hiệu lực … đến ngày "
        "…'). "
        "Ví dụ: [{\"bienSo\":\"37C-123.45\",\"loaiXe\":\"Ô tô tải (thùng kín)\",\"loaiPhuHieu\":\"XE TẢI\","
        "\"hanPhuHieu\":\"02 năm\",\"nhanHieu\":\"HYUNDAI\",\"soKhung\":\"RNXAB12CDEF345678\",\"soMay\":"
        "\"D4CB1234567\",\"mauSon\":\"Trắng\",\"trongTai\":\"2.400 KG\",\"soCho\":\"3\",\"namSanXuat\":\"2019\","
        "\"nuocSanXuat\":\"Việt Nam\",\"nienHan\":\"2044\",\"chuXe\":\"LÊ VĂN AN\",\"ngayDangKy\":\"05/03/2024\","
        "\"loaiHopDong\":\"thanh_vien_htx\",\"hopDongTuNgay\":\"10/01/2026\",\"hopDongDenNgay\":\"31/01/2028\"}]."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _n in ("NguoiNop_NgaySinh", "NguoiNop_NgayCap", "GCNDK_NgayCap", "GPKD_NgayCap", "DeNghi_NgayLap"):
    COMPACT_COMP_BY_NAME[_n] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_ThuongTru"] = "x-select-area"
COMPACT_COMP_BY_NAME["DonVi_DiaChi"] = "x-select-area"
COMPACT_COMP_BY_NAME["HopDong_BenB_DiaChi"] = "x-select-area"
COMPACT_COMP_BY_NAME["PhuongTien"] = "x-array"

# ---- UI Form.io fields (data[...]) — comp dom-*. Field-key lấy từ HTML thật (file mapping).
_DV = "data[T_DonViKinhDoanh]"
_GP = f"{_DV}[HoatDongKinhDoanh][GiayCapPhepKinhDoanh]"
_PT = "data[ThamDinh][ThemPhuongTienRaw]"

UI_COMP_BY_NAME = {
    # ----- Phần I: NGƯỜI NỘP HỒ SƠ (chonDoiTuong disabled → bỏ) -----
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[email]": "dom-input",
    "data[tenHoSo]": "dom-input",          # nhãn hiển thị "Ghi chú"
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[phoneNumber]": "dom-input",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",        # nhãn "Phường/xã"
    "data[address]": "dom-input",

    # ----- Phần II: THÔNG TIN DOANH NGHIỆP CỦA NGƯỜI NỘP -----
    "data[organization]": "dom-input",
    "data[nation1]": "dom-select",
    "data[address1]": "dom-input",
    "data[taxCode]": "dom-input",
    "data[province1]": "dom-select",
    "data[organizationPhoneNumber]": "dom-input",
    "data[district1]": "dom-select",

    # ----- Phần III: GIẤY ĐỀ NGHỊ -----
    "data[SoVanBan]": "dom-input",
    "data[TinhThanh]": "dom-select",       # "Tại" — mặc định Thành phố Bắc Ninh, phải đổi
    "data[DT]": "dom-date",                # "Ngày tháng năm" — mặc định hôm nay
    "data[T_CoQuan]": "dom-select",        # "Kính gửi" — Sở Xây dựng các tỉnh / Cục Đường bộ
    "data[dichVu]": "dom-select",

    # ----- Phần IV: ĐƠN VỊ KINH DOANH VẬN TẢI -----
    f"{_DV}[LoaiHinhDoanhNghiep]": "dom-select",
    f"{_DV}[NguoiDaiDien.HoVaTen]": "dom-input",
    f"{_DV}[TenCoSoToChuc]": "dom-input",
    f"{_DV}[MaSoDoanhNghiep]": "dom-input",
    f"{_DV}[TenTiengAnh]": "dom-input",
    f"{_DV}[DiaChiHoatDong][SoNhaChiTiet]": "dom-input",
    f"{_DV}[DiaChiHoatDong][TinhThanh]": "dom-select",
    f"{_DV}[DiaChiHoatDong][XaPhuong]": "dom-select",
    f"{_DV}[DanhBaLienLac][SoDienThoai]": "dom-input",
    f"{_DV}[DanhBaLienLac][ThuDienTu]": "dom-input",
    f"{_DV}[DanhBaLienLac][Fax]": "dom-input",
    f"{_DV}[GiayDangKyToChuc][SoGiay]": "dom-input",
    f"{_DV}[GiayDangKyToChuc][CoQuanCap][TenCoSoToChuc]": "dom-input",
    f"{_DV}[GiayDangKyToChuc][NgayCap]": "dom-date",
    f"{_GP}[SoGiay]": "dom-input",
    f"{_GP}[NgayCap]": "dom-date",
    f"{_GP}[CapLanThu]": "dom-input",
    f"{_GP}[CoQuanCap]": "dom-select",
    f"{_GP}[HieuLucGiayToVanBan]": "dom-select",
    f"{_DV}[HoatDongKinhDoanh][LoaiHinhKinhDoanh]": "dom-select",  # select multiple

    # ----- Phần V: THẨM ĐỊNH -----
    "data[ThamDinh][SoLuongNopLai]": "dom-input",
    "data[ThamDinh][DeNghiDuocCap]": "dom-input",
    # Nút "Thêm phương tiện" mở panel formThemPhuongTien — FE bấm TRƯỚC khi điền các ô _PT bên dưới.
    "data[ThamDinh][themPhuongTien]": "dom-click",

    # ----- Phần VI: THÔNG TIN PHƯƠNG TIỆN (panel ThemPhuongTienRaw) -----
    # Radio "THÔNG TIN NGƯỜI SỞ HỮU": name DOM có đuôi [instance-id] ngẫu nhiên → gửi tên ổn định, FE khớp
    # tiền tố (formioRadioNameMatches).
    f"{_PT}[DVKDVT]": "dom-radio",
    f"{_PT}[BienDangKy]": "dom-input",
    f"{_PT}[SoKhung]": "dom-input",
    f"{_PT}[NienHan]": "dom-input",
    f"{_PT}[PhanLoaiXeCoGioi]": "dom-select",
    f"{_PT}[BienSoXe]": "dom-input",
    f"{_PT}[SoMay]": "dom-input",
    f"{_PT}[NuocSanXuat]": "dom-select",   # danh mục quốc gia tên TIẾNG ANH
    f"{_PT}[SoChoNgoi]": "dom-input",      # nhãn "Số người cho phép chở (trọng tải)"
    f"{_PT}[MauSon]": "dom-select",
    f"{_PT}[NamSanXuat]": "dom-input",
    f"{_PT}[NhanHieu]": "dom-input",
    f"{_PT}[TinhTrangPhuongTien]": "dom-select",
    # VII-A: xe thuộc sở hữu đơn vị KDVT
    f"{_PT}[ChuPhuongTien.HoVaTen]": "dom-input",
    f"{_PT}[GiayDangKyPhuongTien.NgayCap]": "dom-date",
    # VII-B: xe thuê / hợp tác kinh doanh / xe của thành viên HTX
    f"{_PT}[ChuPhuongTienThue.HoVaTen]": "dom-input",
    f"{_PT}[HopDongThueMuon][LoaiHinhChoThue]": "dom-select",
    f"{_PT}[HopDongThueMuon][ThoiGianBatDauThue]": "dom-date",
    f"{_PT}[HopDongThueMuon][ThoiGianHetHanThue]": "dom-date",
}
