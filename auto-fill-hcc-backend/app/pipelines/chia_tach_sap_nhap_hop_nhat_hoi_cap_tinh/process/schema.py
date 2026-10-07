"""Compact schema cho "Thủ tục chia, tách; sáp nhập; hợp nhất hội (cấp tỉnh)" (mã 1.012945) — cổng DVCQG (Form.io).

Hồ sơ mẫu: Đơn đề nghị (Mẫu số 10) + Biên bản họp + Nghị quyết BCH + Danh sách BCH/BKT + Đề án + Dự thảo Điều lệ +
Phiếu LLTP số 1 (+ Sơ yếu lý lịch Mẫu 17, văn bản xác nhận trụ sở, CCCD nếu có).

BA vai:
- NguoiNop_*   : NGƯỜI NỘP = tài khoản đăng nhập = người được BCH giao làm thủ tục (thường ký "TM. BCH" trên
                 Đơn). Họ tên, ngày sinh, số định danh cổng tự đổ (ô khoá) → chỉ lấy giới tính, ngày cấp, nơi
                 cấp, nơi thường trú từ CCCD KHỚP tài khoản.
- ChuHoSo_*    : CHỦ HỒ SƠ = người đứng đầu dự kiến của hội hình thành/tiếp tục tồn tại (Chủ tịch dự kiến — người
                 có Phiếu LLTP số 1 / Sơ yếu lý lịch trong hồ sơ).
- NguoiLienHe_*: người liên hệ ở cuối mẫu đơn (thường = người nộp).

Tên hội KHÔNG tách theo từng mẫu đơn: LLM trả HoiThamGia (hội đang tồn tại) + HoiMoi (hội sau thay đổi), mapper
xếp vào đúng cặp ô của fieldset tương ứng LoaiThuTuc.
"""

FIELDS: list[dict] = [
    {"name": "LoaiThuTuc", "desc": 'Trường hợp đề nghị: "sáp nhập" / "hợp nhất" / "chia" / "tách". Hồ sơ ghi '
        'gộp "sáp nhập, hợp nhất" thì xét bản chất: các hội cũ CHẤM DỨT, hình thành hội MỚI (ghi "(mới)", bầu BCH '
        'mới, Điều lệ mới) → "hợp nhất"; một hội giữ nguyên tư cách, hội kia nhập vào → "sáp nhập".'},
    {"name": "HoiThamGia", "desc": "Mảng tên các hội ĐANG TỒN TẠI tham gia thủ tục, theo thứ tự ghi trên Đơn/Nghị "
        "quyết. Sáp nhập: [hội bị sáp nhập, hội nhận sáp nhập]. Hợp nhất: [hội 1, hội 2, ...]. Chia/tách: [hội bị "
        "chia/tách]. Viết tên CHUẨN đầy đủ (vd 'Hội Cờ tướng tỉnh Bình An'), sửa lỗi gõ/OCR hiển nhiên, "
        "KHÔNG viết IN HOA toàn bộ, bỏ chú thích '(cũ)'."},
    {"name": "HoiMoi", "desc": "Mảng tên hội SAU thay đổi. Sáp nhập: [hội nhận sáp nhập]. Hợp nhất: [hội hình thành "
        "mới]. Chia: [hội mới 1, hội mới 2, ...]. Tách: [hội bị tách sau khi tách, hội mới tách ra]. Tên chính thức "
        "theo Điều lệ Điều 1 / Nghị quyết, BỎ chú thích '(mới)'."},
    {"name": "KinhGui_Tinh", "desc": "Tỉnh/thành phố của cơ quan ở dòng 'Kính gửi' của Đơn (vd 'UBND Thành phố Hải "
        "Phòng' → 'Thành phố Hải Phòng')."},
    {"name": "NghiDinhSo", "desc": "Số Nghị định của Chính phủ quy định về tổ chức, hoạt động và quản lý hội nêu ở "
        "phần căn cứ (vd '126/2024/NĐ-CP')."},
    {"name": "NgayNghiDinh", "desc": "Ngày ban hành Nghị định đó, dd/mm/yyyy (vd '08/10/2024')."},
    {"name": "LyDo", "desc": "Lý do, sự cần thiết chia/tách/sáp nhập/hợp nhất — CHÉP NGUYÊN VĂN đoạn 'Cơ sở và lý "
        "do' của Đề án (ưu tiên) hoặc đoạn đề nghị trong Đơn. KHÔNG chép phần 'Căn cứ ...', KHÔNG tự viết."},
    {"name": "DanhMucHoSo", "desc": "Mảng giấy tờ CÓ trong bộ hồ sơ tải lên, mỗi phần tử một chuỗi 'Tên giấy tờ – "
        "Số: ..., ngày ...' (bỏ phần số/ngày nếu giấy không ghi). Thứ tự: Đơn → Biên bản họp → Nghị quyết → Danh "
        "sách BCH → Đề án → Điều lệ → Sơ yếu lý lịch / Phiếu LLTP. KHÔNG liệt kê CCCD/căn cước."},
    {"name": "TruSo_DiaChi", "desc": "Địa chỉ trụ sở của hội sau thay đổi, object {quocGia,tinh,xa,diaChi}. Nguồn: "
        "Đề án mục 'Địa chỉ đặt trụ sở' → Dự thảo Điều lệ điều 'trụ sở'. diaChi = tên công trình/số nhà/đường "
        "(KHÔNG kèm phường/tỉnh)."},
    {"name": "NguoiKy_TMBCH", "desc": "Họ tên người ký 'TM. BAN CHẤP HÀNH' trên Đơn đề nghị (Nghị quyết / Đề án nếu "
        "Đơn không có), viết hoa chữ cái đầu mỗi từ."},
    {"name": "NguoiKy_HoiKhac", "desc": "CHỈ khi Đơn có CHỮ KÝ THỨ HAI 'TM. BCH' của hội còn lại (hội bị sáp nhập / "
        "hội hợp nhất kia): họ tên người đó. Đơn chỉ có một chữ ký thì BỎ."},
    {"name": "NguoiLienHe_HoTen", "desc": "Người được Ban chấp hành giao làm thủ tục (Biên bản họp / Nghị quyết "
        "'thống nhất giao cho ông/bà ...') — không có thì người ký Đơn."},
    {"name": "NguoiLienHe_DienThoai", "desc": "Số điện thoại liên hệ ghi trên Đơn/Đề án. Không có thì bỏ."},
    {"name": "ChuHoSo_HoTen", "desc": "Họ tên CHỦ TỊCH DỰ KIẾN của hội sau thay đổi (Danh sách BCH: chức danh "
        "'Chủ tịch'), đồng thời là người có Phiếu LLTP số 1 / Sơ yếu lý lịch trong hồ sơ. IN HOA như trên LLTP."},
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh chủ hồ sơ, dd/mm/yyyy. Nguồn: CCCD của người đó → Phiếu LLTP."},
    {"name": "ChuHoSo_GioiTinh", "desc": 'Giới tính chủ hồ sơ: "Nam"/"Nữ" (CCCD → Phiếu LLTP).'},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/thẻ căn cước của chủ hồ sơ (CCCD → Phiếu LLTP mục 8). Chỉ chữ "
        "số. KHÔNG lấy số phiếu LLTP."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD của chủ hồ sơ (Phiếu LLTP ghi 'Cấp ngày ...'), dd/mm/yyyy. "
        "KHÔNG lấy ngày cấp phiếu LLTP."},
    {"name": "ChuHoSo_NoiCap", "desc": "Nơi cấp CCCD của chủ hồ sơ, chép đúng (vd 'Bộ Công an'). KHÔNG lấy cơ quan "
        "cấp phiếu LLTP (Công an tỉnh/TP)."},
    {"name": "ChuHoSo_DiaChi", "desc": "Nơi thường trú của chủ hồ sơ (CCCD → Phiếu LLTP mục 9), object {quocGia,"
        "tinh,xa,diaChi}."},
    {"name": "ChuHoSo_QuocTich", "desc": "Quốc tịch của chủ hồ sơ (vd 'Việt Nam')."},
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên in trên thẻ CCCD của NGƯỜI NỘP (xem nguoi_nop_context) — không có "
        "thẻ đó thì bỏ."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số định danh 12 số trên CHÍNH thẻ CCCD người nộp."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính trên thẻ CCCD người nộp: "Nam"/"Nữ".'},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CHÍNH thẻ CCCD người nộp, dd/mm/yyyy. KHÔNG lấy ngày hết hạn."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp thẻ CCCD người nộp, chép đúng như in trên thẻ. Thẻ không in thì "
        "bỏ."},
    {"name": "NguoiNop_DiaChi", "desc": "Nơi thường trú / nơi cư trú trên thẻ CCCD người nộp, object {quocGia,tinh,"
        "xa,diaChi}."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("NgayNghiDinh", "ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("TruSo_DiaChi", "ChuHoSo_DiaChi", "NguoiNop_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"
for _name in ("HoiThamGia", "HoiMoi", "DanhMucHoSo"):
    COMPACT_COMP_BY_NAME[_name] = "x-array"

# ---- UI Form.io fields (data[...]) — field-key lấy từ DOM thật (mapping 1.012945). data[chonDoiTuong],
# data[chonDoiTuong1], data[ngayHt] cổng khoá → KHÔNG phát. data[fullname], data[birthday], data[identityNumber] cổng
# khoá theo VNeID → chỉ phát ở chế độ người nộp theo tờ khai (kèm enableInput + occurrence 0).
UI_COMP_BY_NAME: dict[str, str] = {
    # Phần I — người nộp.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[identityNumber]": "dom-input",
    "data[gender]": "dom-select",
    "data[identityDate]": "dom-date",
    "data[idIssuePlace]": "dom-input",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[isOwnerDossierCheck]": "dom-checkbox",
    # Phần II — chủ hồ sơ.
    "data[ownerFullname]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[ownerGender]": "dom-select",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerIdIssuePlace]": "dom-input",
    "data[ownerProvince]": "dom-select",
    "data[ownerDistrict]": "dom-select",
    "data[ownerAddress]": "dom-input",
    "data[ownerNation]": "dom-select",
    # Phần IV — đầu panel "Thông tin chi tiết".
    "data[noiGui]": "dom-select",
    "data[ChonTruongHop]": "dom-select",
}

# Datagrid "Hồ sơ kèm theo gồm" — mỗi giấy tờ một dòng (FE tự bấm "Thêm dòng").
MAX_HO_SO_ROWS = 15
for _i in range(MAX_HO_SO_ROWS):
    UI_COMP_BY_NAME[f"data[hoSoDinhKem][{_i}][textField1]"] = "dom-input"
    UI_COMP_BY_NAME[f"data[hoSoDinhKem][{_i}][textField2]"] = "dom-input"

# Mỗi mẫu đơn (fieldset) một bộ field-key. Vai trò → field-key. "tmbch_hoi_khac" = ô TM. BCH của hội bị sáp
# nhập / bị hợp nhất; "tmbch" = ô TM. BCH của hội nhận sáp nhập / hội mới / hội bị chia, tách.
MAU_DON: dict[str, dict[str, str]] = {
    "chia": {
        "label": "Đơn đề nghị chia hội",
        "hoi_goc": "data[ChiaHoi]",
        "hoi_moi_1": "data[ThanhHoi]",
        "hoi_moi_2": "data[VaHoi]",
        "nghi_dinh": "data[NghiDinhSo]",
        "ngay_nd": "data[NgayNd]",
        "ly_do": "data[LyDoChia]",
        "ho_so": "data[HoSoChia]",
        "ho_ten": "data[fullname1]",
        "dien_thoai": "data[phoneNumber1]",
        "tinh": "data[province1]",
        "xa": "data[district1]",
        "dia_chi": "data[address1]",
        "tmbch": "data[TM.BCH]",
    },
    "tach": {
        "label": "Đơn đề nghị tách hội",
        "hoi_goc": "data[TachHoi]",
        "hoi_moi_1": "data[ThanhHoi2]",
        "hoi_moi_2": "data[VaHoi2]",
        "nghi_dinh": "data[NghiDinhSo1]",
        "ngay_nd": "data[NgayNd1]",
        "ly_do": "data[LyDoTach]",
        "ho_so": "data[HoSoTach]",
        # ⚠ Mẫu tách dùng TRÙNG field-key Phần I → mapper gắn TACH_SCOPE.
        "ho_ten": "data[fullname]",
        "dien_thoai": "data[phoneNumber]",
        "tinh": "data[province]",
        "xa": "data[district]",
        "dia_chi": "data[address]",
        "tmbch": "data[TM.BCH1]",
    },
    "sap_nhap": {
        "label": "Đơn đề nghị sáp nhập hội",
        "hoi_goc": "data[SapNhapHoi]",      # hội BỊ sáp nhập
        "hoi_moi_1": "data[VaoHoi4]",       # hội NHẬN sáp nhập
        "nghi_dinh": "data[NghiDinhSo2]",
        "ngay_nd": "data[NgayNd2]",
        "ly_do": "data[LyDoSapNhap]",
        "ho_so": "data[HoSoSapNhap]",
        "ho_ten": "data[fullname2]",
        "dien_thoai": "data[phoneNumber2]",
        "tinh": "data[province2]",
        "xa": "data[district2]",
        "dia_chi": "data[address2]",
        "tmbch_hoi_khac": "data[TM.BCH2]",
        "tmbch": "data[TM.BCH3]",
    },
    "hop_nhat": {
        "label": "Đơn đề nghị hợp nhất hội",
        "hoi_goc": "data[HopNhatHoi]",      # hội hợp nhất 1
        "hoi_goc_2": "data[VaHoi7]",        # hội hợp nhất 2
        "hoi_moi_1": "data[ThanhHoi9]",     # hội thành lập mới
        "nghi_dinh": "data[NghiDinhSo3]",
        "ngay_nd": "data[NgayNd3]",
        "ly_do": "data[LyDoHopNhat]",
        "ho_so": "data[HoSoHopNhat]",
        "ho_ten": "data[fullname3]",
        "dien_thoai": "data[phoneNumber3]",
        "tinh": "data[province3]",
        "xa": "data[district3]",
        "dia_chi": "data[address3]",
        "tmbch_hoi_khac": "data[TM.BCH4]",
        "tmbch": "data[TM.BCH5]",
    },
}

_COMP_BY_ROLE = {"tinh": "dom-select", "xa": "dom-select", "ngay_nd": "dom-date"}
MAU_DON_COMP: dict[str, str] = {}
for _mau in MAU_DON.values():
    for _role, _key in _mau.items():
        if _role != "label":
            MAU_DON_COMP[_key] = _COMP_BY_ROLE.get(_role, "dom-input")

# Mẫu tách: field-key trùng Phần I. Chỉ điền trong fieldset tách (fieldset2); scopeNear/scopeAway để extension
# thu hẹp khi selector bọc cả khối người nộp, không tách được thì BỎ ô — thà trống còn hơn ghi đè Phần I.
TACH_SCOPE = ".formio-component-fieldset2"
TACH_SCOPE_NEAR = "data[TachHoi]"
NGUOI_NOP_MARKERS = (
    "data[chonDoiTuong]",
    "data[isOwnerDossierCheck]",
    "data[ownerFullname]",
)
