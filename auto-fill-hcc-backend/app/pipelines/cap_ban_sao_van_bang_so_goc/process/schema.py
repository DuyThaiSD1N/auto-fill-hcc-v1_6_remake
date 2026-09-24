
"""Compact schema cho "Cấp bản sao văn bằng, chứng chỉ từ sổ gốc" — cổng DVC Bộ GD&ĐT dvc.moet.gov.vn
(Form.io). TẤT CẢ field-key PHẲNG data[...] (không lồng panel).

BA NHÓM NHÂN THÂN — TÁCH RIÊNG (có thể là 2 người khác nhau: chủ văn bằng vs người nộp thay):
- VanBang_* : nhân thân + học vấn CHỦ VĂN BẰNG lấy TỪ CHÍNH VĂN BẰNG / Phiếu BM04 (nguồn GỐC, không phải
  CCCD). VanBang_HoTen là NEO xác định ai là chủ hồ sơ.
- ChuHoSo_* : CCCD của CHỦ VĂN BẰNG — tức CCCD có họ tên TRÙNG với văn bằng (số định danh, ngày cấp, nơi
  cấp, thường trú). Kèm ChuHoSo_HoTen (tên IN trên CCCD đó) để mapper kiểm tra khớp.
- NguoiNop_* : CCCD của NGƯỜI NỘP THAY — CCCD có họ tên KHÁC văn bằng (hoặc tài khoản đăng nhập). Điền Phần I.

Mapper định tuyến TẤT ĐỊNH theo khớp tên (không tin LLM phân nhóm): CCCD nào khớp VanBang_HoTen → chủ hồ
sơ; CCCD còn lại → người nộp.

Cấu trúc form:
- Phần I   Người nộp (data[fullname]/[identityNumber]/[gender]/[birthday]/[identityDate]/[idIssuePlace]/
  [province]/[district]/[address]/[phoneNumber]/[email]) — từ NguoiNop_* (CCCD người nộp) hoặc tài khoản.
  Nút "Người nộp là chủ hồ sơ" (data[isOwnerDossier]) checkbox — KHÔNG tick.
- Phần II  data[ChuHS] = loại chủ hồ sơ.
- Phần III-V data[owner...] : chủ văn bằng (cá nhân owner*; tổ chức/DN ownerOrganizationFullname/ownerTaxCode).
- Panel "Phieu" (data[Kinhgui]/[ToiTen]/[Sodinhdanh]/[Duoccap]/[do]/[Sohieu]/[requestQty]/[sogoc]/
  [lydo]/[thongtinkhac]/[lienhe]/[ngay]/[nguoidenghi]) : chép gần NGUYÊN VĂN Phiếu đề nghị BM04.
  ⚠ Form đã ĐỔI (2026-09): panel này thay panel "Thongtincanhan" cũ (data[Nam]/[DaHocLop12]/[THPT]/
  [KhoaThi]/[SoGiayTo]/[select]… đã BỎ). Xem field-key thật bằng probe DOM panel formio-component-Phieu.
"""

# Địa chỉ trên CCCD/phiếu thường là địa danh CŨ 3 cấp (trước sáp nhập) → giữ cấp huyện ở khoá "huyen" để
# mapper remap đúng xã mới (vd "Tuy Lộc, TP Yên Bái" → Phường Nam Cường, Lào Cai).
_AREA_DESC = ("object {quocGia,tinh,huyen,xa,diaChi}. tinh=tỉnh/thành phố; huyen=quận/huyện/thị xã/thành phố "
              "thuộc tỉnh NẾU giấy ghi (địa danh cũ — BẮT BUỘC giữ, mapper cần để quy đổi sang xã mới); "
              "xa=phường/xã/thị trấn; diaChi=số nhà/đường/thôn/tổ. Chép đúng địa danh trên giấy, KHÔNG tự đổi "
              "sang tên sau sáp nhập.")

# --- Nhân thân + học vấn CHỦ VĂN BẰNG (nguồn: VĂN BẰNG / Phiếu BM04) ---
_VANBANG_FIELDS = [
    ("HoTen", "Họ và tên CHỦ VĂN BẰNG — người được cấp bản sao. LẤY TỪ VĂN BẰNG (bằng tốt nghiệp mục 'Họ "
        "và tên') hoặc Phiếu BM04 ('Tôi tên'). ĐÂY LÀ NEO: TUYỆT ĐỐI KHÔNG lấy tên trên CCCD của người "
        "nộp thay. IN HOA có dấu."),
    ("GioiTinh", 'Giới tính chủ văn bằng: "Nam"/"Nữ" — Văn bằng ("Giới tính") / Phiếu BM04 (ô tích Nam/Nữ).'),
    ("NgaySinh", "Ngày sinh chủ văn bằng, dd/mm/yyyy — Văn bằng ('Ngày, tháng, năm sinh') / Phiếu BM04 "
        "('Sinh ngày')."),
    ("NamSinh", "Năm sinh (4 chữ số) chủ văn bằng — Phiếu BM04 'Năm sinh' hoặc phần năm của ngày sinh."),
    ("NoiSinh", "Nơi sinh chủ văn bằng — Văn bằng/Phiếu BM04 'Nơi sinh' (ghi theo địa danh trên giấy, kể "
        "cả tên trước sáp nhập). KHÔNG lấy 'Quê quán' của CCCD."),
    ("DanToc", "Dân tộc chủ văn bằng — Văn bằng/Phiếu BM04 'Dân tộc' (vd 'Kinh'). CCCD gắn chip KHÔNG in dân tộc."),
    ("Truong", "Tên trường đã học/đã tốt nghiệp — Văn bằng 'Học sinh trường' / Phiếu BM04 'Đã học tại "
        "trường'. Chép nguyên văn."),
    ("TruongDiaChi", "Địa chỉ TRƯỜNG, object {tinh,xa}. Phiếu BM04 dòng 'Đã học tại trường … Phường/xã … "
        "Tỉnh/TP …'. tinh='Tỉnh/Thành phố …'; xa=phường/xã. Không có → bỏ."),
    ("LoaiTotNghiep", '⚠ BẮT BUỘC khi có văn bằng — MỘT trong "THPT"/"Bổ túc THPT"/"THCS". Căn cứ MẠNH '
        'nhất là TÊN văn bằng ("BẰNG TỐT NGHIỆP TRUNG HỌC PHỔ THÔNG"→"THPT"; có "BỔ TÚC"→"Bổ túc THPT"; '
        '"TRUNG HỌC CƠ SỞ"→"THCS") hoặc ô tích Phiếu BM04. KHÔNG bỏ trống khi tiêu đề bằng đã ghi rõ.'),
    ("KhoaThi", "Khóa thi — Văn bằng 'Khoá thi' / Phiếu BM04 'Khóa thi' (vd '2019-2020'). Chép nguyên văn."),
    ("HoiDongThi", "Hội đồng thi — Văn bằng 'Hội đồng thi' / Phiếu BM04 'Tại Hội đồng thi'. Chép nguyên văn."),
    ("LoaiGiayTo", 'Loại giấy tờ tùy thân của chủ văn bằng. ⚠ KHÔNG suy từ nhãn cố định "Số chứng minh '
        'nhân dân/Hộ chiếu" trên BM04 (đó chỉ là nhãn form). Xác định theo SỐ: 12 chữ số → "Căn cước công '
        'dân"; 9 chữ số → "Chứng minh nhân dân". Không rõ → bỏ trống.'),
    ("SoGiayTo", "Số CCCD/CMND của CHỦ VĂN BẰNG lấy từ Phiếu BM04 ('Số chứng minh nhân dân/Hộ chiếu') hoặc "
        "văn bằng. Chỉ chữ số. ĐÂY là số của chủ (KHÔNG phải của người nộp thay)."),
    ("NgayCap", "Ngày cấp giấy tờ của chủ văn bằng, dd/mm/yyyy — Phiếu BM04 'Ngày và nơi cấp'."),
    ("DienThoai", "Số điện thoại chủ văn bằng — Phiếu BM04 'Điện thoại'. Chỉ chữ số."),
    ("ThuongTru", "NƠI THƯỜNG TRÚ HIỆN NAY của chủ văn bằng, " + _AREA_DESC + " Phiếu BM04 'Địa chỉ thường "
        "trú'/'Nơi ở hiện nay'. ⚠ KHÔNG lấy địa chỉ LÚC DỰ THI ('Hộ khẩu thường trú khi dự thi', 'Địa chỉ "
        "dự thi', 'Nơi đăng ký dự thi'…) → cái đó vào VanBang_DiaChiDuThi. KHÔNG lấy nơi sinh, địa chỉ "
        "trường/hội đồng thi, địa chỉ trên CCCD của người nộp thay. Phiếu không có dòng thường trú hiện nay "
        "→ BỎ field này."),
    ("DiaChiDuThi", "Địa chỉ/hộ khẩu của chủ văn bằng LÚC DỰ THI — CHỈ dòng có chữ 'dự thi' ('Hộ khẩu "
        "thường trú khi dự thi', 'Địa chỉ dự thi', 'Nơi đăng ký dự thi'…) trên Phiếu BM04/văn bằng. Chép "
        "nguyên văn. KHÔNG lấy 'Nơi sinh'. CHỈ để đối chiếu, KHÔNG phải địa chỉ hiện tại."),
]

FIELDS: list[dict] = [{"name": f"VanBang_{n}", "desc": d} for n, d in _VANBANG_FIELDS]

# --- CCCD của CHỦ VĂN BẰNG (CCCD khớp tên văn bằng) + loại chủ thể ---
FIELDS += [
    {"name": "ChuHoSo_LoaiChuThe", "desc": '"Cá nhân" (mặc định) nếu chủ hồ sơ là một người; "Tổ chức" '
        'nếu là cơ quan/trường; "Doanh nghiệp" nếu là công ty. Chỉ chọn tổ chức/DN khi giấy tờ thực sự ghi.'},
    {"name": "ChuHoSo_TenToChuc", "desc": "Tên cơ quan/doanh nghiệp khi chủ hồ sơ là TỔ CHỨC/DOANH NGHIỆP. "
        "Cá nhân → bỏ."},
    {"name": "ChuHoSo_MaSoThue", "desc": "Mã số doanh nghiệp/mã số thuế khi chủ hồ sơ là TỔ CHỨC/DOANH "
        "NGHIỆP. Chỉ chữ số. Cá nhân → bỏ."},
    {"name": "ChuHoSo_HoTen", "desc": "Họ tên IN TRÊN CCCD mà bạn coi là của CHỦ VĂN BẰNG (phải TRÙNG "
        "VanBang_HoTen). Dùng để đối chiếu. Nếu KHÔNG có CCCD nào trùng tên văn bằng → bỏ."},
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh IN TRÊN CCCD của chủ văn bằng, dd/mm/yyyy (dự phòng khi "
        "không có văn bằng)."},
    {"name": "ChuHoSo_GioiTinh", "desc": 'Giới tính IN TRÊN CCCD của chủ văn bằng: "Nam"/"Nữ" (dự phòng khi '
        'không có văn bằng).'},
    {"name": "ChuHoSo_SoGiayTo", "desc": "Số CCCD/CMND của CHỦ VĂN BẰNG — lấy từ CCCD có họ tên TRÙNG "
        "VanBang_HoTen. Chỉ chữ số, ưu tiên 12 chữ số. ⚠ Nếu CCCD tải lên có tên KHÁC văn bằng, đó là của "
        "NGƯỜI NỘP THAY → KHÔNG lấy vào đây, để trống."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD của chủ văn bằng, dd/mm/yyyy (CCCD khớp tên văn bằng)."},
    {"name": "ChuHoSo_NoiCap", "desc": 'Nơi cấp CCCD chủ văn bằng. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH '
        'CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; "BỘ CÔNG AN" → '
        '"Bộ Công an".'},
    {"name": "ChuHoSo_QuocTich", "desc": 'Quốc tịch chủ văn bằng (CCCD "Quốc tịch"). Mặc định "Việt Nam".'},
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại chủ văn bằng — Phiếu BM04 'Điện thoại'. Chỉ chữ số."},
    {"name": "ChuHoSo_ThuongTru", "desc": "NƠI THƯỜNG TRÚ chủ văn bằng IN TRÊN CCCD (khớp tên văn bằng) "
        "'Nơi thường trú', " + _AREA_DESC + " CHỈ lấy từ CCCD — KHÔNG lấy từ Phiếu BM04 (phiếu hay ghi địa chỉ "
        "lúc dự thi)."},
]

# --- CCCD của NGƯỜI NỘP THAY (CCCD KHÁC tên văn bằng) ---
_NOP_FIELDS = [
    ("HoTen", "Họ tên NGƯỜI NỘP HỒ SƠ — chỉ điền khi có CCCD tải lên mang tên KHÁC với văn bằng (người "
        "nộp thay). IN HOA."),
    ("SoDinhDanh", "Số CCCD NGƯỜI NỘP (CCCD khác tên văn bằng). Chỉ chữ số."),
    ("NgaySinh", "Ngày sinh NGƯỜI NỘP, dd/mm/yyyy — CCCD người nộp."),
    ("GioiTinh", 'Giới tính NGƯỜI NỘP: "Nam"/"Nữ" — CCCD người nộp.'),
    ("NgayCap", "Ngày cấp CCCD NGƯỜI NỘP, dd/mm/yyyy."),
    ("NoiCap", 'Nơi cấp CCCD NGƯỜI NỘP (chuẩn hóa như ChuHoSo_NoiCap).'),
    ("ThuongTru", "NƠI THƯỜNG TRÚ NGƯỜI NỘP (CCCD người nộp), " + _AREA_DESC),
    ("DienThoai", "Số điện thoại NGƯỜI NỘP nếu có. Chỉ chữ số."),
    ("Email", "Email NGƯỜI NỘP nếu có; thường không có → bỏ."),
]

FIELDS += [{"name": f"NguoiNop_{n}", "desc": d} for n, d in _NOP_FIELDS]

# --- Phiếu đề nghị BM04 (panel "Phieu" trên form) — trích gần NGUYÊN VĂN theo phiếu ---
FIELDS += [
    {"name": "Phieu_KinhGui", "desc": "Cơ quan ở dòng 'Kính gửi' đầu Phiếu BM04 (vd 'SỞ GIÁO DỤC VÀ ĐÀO "
        "TẠO ĐÀ NẴNG'). Chép nguyên văn."},
    {"name": "Phieu_TenVanBang", "desc": "Nội dung dòng 'Đã được cấp (tên văn bằng, chứng chỉ)' trên Phiếu "
        "BM04 (vd 'BẰNG THPT', 'Bằng tốt nghiệp THPT'). Chép nguyên văn."},
    {"name": "Phieu_CoQuanCapVanBang", "desc": "Cơ quan ở dòng 'Do … cấp' trên Phiếu BM04 (nơi ĐÃ cấp văn "
        "bằng, vd 'Sở Giáo dục và Đào tạo Đà Nẵng'). Chép nguyên văn."},
    {"name": "Phieu_SoHieu", "desc": "Nội dung 'Số hiệu/hoặc số vào sổ gốc' trên Phiếu BM04/văn bằng. "
        "Không ghi → bỏ."},
    {"name": "Phieu_SoLuongBanSao", "desc": "Số lượng bản sao xin cấp — Phiếu BM04 'Đề nghị cấp … bản sao'. "
        "Chỉ chữ số. Không ghi → bỏ (mapper mặc định 1)."},
    {"name": "Phieu_LyDo", "desc": "Nội dung dòng 'Ghi rõ lý do cấp lại/nội dung đề nghị chỉnh sửa' trên "
        "Phiếu BM04. Không ghi → bỏ."},
    {"name": "Phieu_ThongTinKhac", "desc": "Nội dung dòng 'Thông tin khác' trên Phiếu BM04 (thường là tên "
        "trường + năm tốt nghiệp, vd 'THPT Ngô Quyền, 2020'). Chép nguyên văn."},
    {"name": "Phieu_LienHe", "desc": "Nội dung dòng 'Số điện thoại, E-mail, địa chỉ liên hệ' trên Phiếu "
        "BM04 — chép nguyên văn CẢ cụm (SĐT, email, địa chỉ)."},
    {"name": "Phieu_NgayLap", "desc": "Ngày lập phiếu, dd/mm/yyyy — dòng '…, ngày … tháng … năm …' cuối "
        "Phiếu BM04."},
    {"name": "Phieu_NguoiViet", "desc": "Họ tên người đề nghị/ký cuối Phiếu BM04. Thường trùng chủ văn "
        "bằng (hoặc người nộp thay nếu nộp thay)."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["VanBang_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["VanBang_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["VanBang_TruongDiaChi"] = "x-select-area"
COMPACT_COMP_BY_NAME["VanBang_ThuongTru"] = "x-select-area"
COMPACT_COMP_BY_NAME["ChuHoSo_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["ChuHoSo_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["ChuHoSo_ThuongTru"] = "x-select-area"
COMPACT_COMP_BY_NAME["NguoiNop_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_ThuongTru"] = "x-select-area"
COMPACT_COMP_BY_NAME["Phieu_NgayLap"] = "x-date"

# ---- UI Form.io fields (data[...]) — comp dom-*. Field-key lấy CHUẨN từ HTML thật (fill.html). ----
UI_COMP_BY_NAME = {
    # ----- Phần I: NGƯỜI NỘP HỒ SƠ -----
    "data[chonDoiTuong]": "dom-select",
    "data[isOwnerDossier]": "dom-checkbox",  # "Người nộp là chủ hồ sơ" — chỉ tick khi TỰ NỘP.
    "data[fullname]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[gender]": "dom-select",
    "data[birthday]": "dom-date",
    "data[identityDate]": "dom-date",
    "data[idIssuePlace]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[email]": "dom-input",

    # ----- Phần II: chọn loại chủ hồ sơ -----
    "data[ChuHS]": "dom-select",

    # ----- Phần III-V: CHỦ HỒ SƠ (chủ văn bằng) -----
    "data[ownerFullname]": "dom-input",
    "data[ownerGender]": "dom-select",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerBirthday]": "dom-date",
    "data[ownerIdentityAgency22]": "dom-select",
    "data[ownerNation]": "dom-select",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerProvince]": "dom-select",
    "data[ownerDistrict]": "dom-select",
    "data[ownerAddress]": "dom-input",
    "data[ownerEmail]": "dom-input",
    "data[ownerFax]": "dom-input",
    "data[ownerOrganizationFullname]": "dom-input",
    "data[ownerTaxCode]": "dom-input",

    # ----- Panel "Phieu" (Phiếu đề nghị BM04) — chép gần nguyên văn phiếu -----
    "data[Kinhgui]": "dom-input",
    "data[ToiTen]": "dom-input",
    "data[sinhNam]": "dom-input",        # hidden "Sinh ngày" = ngày sinh chủ văn bằng
    "data[Sodinhdanh]": "dom-input",
    "data[Duoccap]": "dom-input",        # "Đã được cấp (tên văn bằng)"
    "data[do]": "dom-input",             # "Do … cấp" (cơ quan cấp văn bằng)
    "data[Sohieu]": "dom-input",
    "data[requestQty]": "dom-input",     # "Đề nghị cấp … bản sao"
    "data[sogoc]": "dom-checkbox",       # "Bản sao từ sổ gốc" — thủ tục này → tick
    "data[caplai]": "dom-checkbox",
    "data[chinhsua]": "dom-checkbox",
    "data[lydo]": "dom-input",           # textarea (dom-input xử lý được)
    "data[hoso]": "dom-input",
    "data[thongtinkhac]": "dom-input",   # "Thông tin khác (tên trường, năm TN)"
    "data[lienhe]": "dom-input",         # "SĐT, E-mail, địa chỉ liên hệ"
    "data[ngay]": "dom-input",           # hidden ngày lập phiếu
    "data[nguoidenghi]": "dom-input",    # "Họ tên người đề nghị"
}
