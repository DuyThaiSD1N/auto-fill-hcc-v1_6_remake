"""Compact schema cho "Cấp, cấp lại Giấy phép khai thác thủy sản" (cổng Nông nghiệp & Môi trường —
Form.io). Field-key nhân thân data[...] TRÙNG KHÍT #97/#92.

Form CHỈ có nhân thân Phần I/II — thông tin tàu nằm trong file Đơn Mẫu 04/05.KT đính kèm, KHÔNG nhập form.

Nhóm field: NguoiDeNghi_* (chủ tàu = chủ hồ sơ) / NguoiNop_* (tài khoản nộp — chỉ khi nộp thay).
"""

_PERSON_FIELDS = [
    ("HoTen", "Họ và tên {who}. Lấy từ {src}. Ghi IN HOA đúng như trên giấy tờ."),
    ("NgaySinh", "Ngày sinh {who}, dd/mm/yyyy. CHỈ lấy từ CCCD (dòng 'Ngày sinh/Date of birth' mặt trước). "
        "Đơn Mẫu 04/05.KT KHÔNG có mục ngày sinh → nếu hồ sơ KHÔNG có CCCD hoặc không thấy ngày sinh rõ ràng "
        "thì BỎ TRỐNG. TUYỆT ĐỐI KHÔNG lấy 'Ngày cấp'/'Ngày cấp CCCD'/ngày trên giấy phép làm ngày sinh. "
        "KHÔNG bịa."),
    ("GioiTinh", 'Giới tính {who}: "Nam" hoặc "Nữ" — CCCD.'),
    ("SoDinhDanh", "Số CCCD/CMND/căn cước/định danh cá nhân {who}. Đọc CCCD (mặt trước/MRZ) hoặc Đơn Mẫu "
        "04/05.KT mục 'Mã định danh/Số CCCD'. Chỉ chữ số. Ưu tiên số 12 chữ số (CCCD/căn cước) hơn số 9 "
        "chữ số (CMND) nếu có cả hai."),
    ("NgayCap", "Ngày cấp CCCD/CMND {who}, dd/mm/yyyy. Lấy thông tin 'Ngày cấp' ghi trên Đơn Mẫu 04/05.KT (mục "
        "'Ngày cấp'/'Ngày cấp CCCD')."),
    ("NoiCap", 'Nơi cấp/cơ quan cấp giấy tờ {who}. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ '
        'XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → '
        '"Bộ Công an". CCCD gắn chip không in nhãn "Nơi cấp" riêng → lấy ở Đơn Mẫu 04/05.KT (mục Cơ quan cấp).'),
    ("ThuongTru", "NƠI THƯỜNG TRÚ {who}, object {{quocGia,tinh,xa,diaChi}}. Lấy ở CCCD (Nơi thường trú) / "
        "Đơn Mẫu 04/05.KT (Nơi thường trú chủ tàu). tinh=CHỈ TÊN tỉnh/thành phố, KHÔNG kèm tiền tố "
        "'Tỉnh'/'Thành phố'/'TP'/'T.P' (vd 'Đà Nẵng', 'Nghệ An' — KHÔNG phải 'T.P Đà Nẵng'). xa=phường/xã, diaChi=số nhà/"
        "khóm/ấp/thôn/tổ (KHÔNG kèm phường/xã/tỉnh)."),
    ("DienThoai", "Số điện thoại DI ĐỘNG {who} — Đơn Mẫu 04/05.KT mục 'Điện thoại' nếu có. Chỉ chữ số; "
        "KHÔNG lấy số bàn."),
    ("Email", "Email liên hệ {who} nếu giấy tờ có; thường không có → bỏ."),
]

_DENGHI_SRC = "CCCD / Đơn Mẫu 04.KT (cấp mới) hoặc Mẫu 05.KT (cấp lại) của NGƯỜI ĐỀ NGHỊ (chủ tàu)"

FIELDS: list[dict] = []
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({
        "name": f"NguoiDeNghi_{_name}",
        "desc": _tmpl.format(who="NGƯỜI ĐỀ NGHỊ (chủ tàu/cá nhân, tổ chức đề nghị)", src=_DENGHI_SRC),
    })
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({
        "name": f"NguoiNop_{_name}",
        "desc": _tmpl.format(who="NGƯỜI NỘP (chỉ khi nộp thay & có CCCD người nộp)", src="CCCD của NGƯỜI NỘP"),
    })

# --- Nội dung Đơn đề nghị (Phần III) — chung cho cả 2 trường hợp ---
FIELDS += [
    {"name": "ToKhai_KinhGui", "desc": "Mục 'Kính gửi' của Đơn Mẫu 04/05.KT — tên cơ quan quản lý nhà "
        "nước về thủy sản cấp tỉnh (vd 'Sở Nông nghiệp và Môi trường …'). Chép nguyên văn."},
    {"name": "ToKhai_DiaDanh", "desc": "Địa danh nơi lập đơn — phần '……, ngày … tháng … năm …' của Đơn "
        "(tên tỉnh/thành phố). Chỉ lấy tên địa danh (vd 'Tỉnh Cà Mau')."},
    {"name": "ToKhai_LoaiGiayTo", "desc": "Loại giấy tờ tùy thân ghi ở Đơn ('Loại giấy tờ'). Không ghi mà "
        "số định danh 12 chữ số → 'Thẻ Căn cước công dân'."},
    {"name": "ToKhai_CoQuanCap", "desc": "Cơ quan cấp giấy tờ tùy thân ghi ở Đơn ('Cơ quan cấp'). Chuẩn "
        "hóa như NoiCap."},
]

# --- Trường hợp CẤP MỚI (Đơn Mẫu 04.KT — thông tin tàu) ---
FIELDS += [
    {"name": "CapMoi_SoDangKy", "desc": "CHỈ khi CẤP MỚI (Đơn Mẫu 04): 'Số đăng ký tàu/Số Giấy chứng nhận "
        "đăng ký tàu cá'. Chép nguyên."},
    {"name": "CapMoi_SoGcnAtkt", "desc": "CHỈ khi CẤP MỚI: 'Số Giấy chứng nhận an toàn kỹ thuật tàu cá'."},
    {"name": "CapMoi_TrangThietBi", "desc": "CHỈ khi CẤP MỚI: 'Trang thiết bị thông tin liên lạc' trên tàu."},
    {"name": "CapMoi_ThietBiGsht", "desc": "CHỈ khi CẤP MỚI: 'Loại thiết bị, mã nhận dạng thiết bị giám "
        "sát hành trình tàu cá' (tàu dài ≥ 15m)."},
    {"name": "CapMoi_NgheChinh", "desc": "CHỈ khi CẤP MỚI: 'Nghề khai thác chính' (vd Lưới rê, Lưới kéo)."},
    {"name": "CapMoi_NghePhu", "desc": "CHỈ khi CẤP MỚI: 'Nghề phụ' nếu có."},
]

# --- Trường hợp CẤP LẠI (Đơn Mẫu 05.KT — GP cũ + lý do) ---
FIELDS += [
    # SỐ GP cũ tách 2 NGUỒN riêng để mapper CHỌN tất định (LLM hay bám số ghi ở đơn nên không tự ưu tiên được):
    {"name": "CapLai_SoGiayPhep_GiayPhep", "desc": "CHỈ khi CẤP LẠI: SỐ in trên CHÍNH tờ 'GIẤY PHÉP KHAI "
        "THÁC THỦY SẢN' đính kèm (dòng 'Số: …', vd '30/LC/2025/ĐNa-GPKTTS'). CHỈ lấy từ tờ GIẤY PHÉP; "
        "KHÔNG lấy từ Đơn/Tờ khai. Hồ sơ không kèm tờ giấy phép → BỎ TRỐNG."},
    {"name": "CapLai_SoGiayPhep_ToKhai", "desc": "CHỈ khi CẤP LẠI: SỐ giấy phép GHI TRONG Đơn Mẫu 05 (dòng "
        "'Tôi đã được cấp Giấy phép khai thác thủy sản số: …'). CHỈ lấy từ Đơn/Tờ khai; KHÔNG lấy từ tờ giấy phép."},
    {"name": "CapLai_NgayCap", "desc": "CHỈ khi CẤP LẠI: ngày cấp Giấy phép cũ, dd/mm/yyyy. ƯU TIÊN đọc ở "
        "chính tờ GIẤY PHÉP; dự phòng Đơn Mẫu 05."},
    {"name": "CapLai_NgayHetHan", "desc": "CHỈ khi CẤP LẠI: ngày hết hạn Giấy phép cũ, dd/mm/yyyy. ƯU TIÊN "
        "đọc ở chính tờ GIẤY PHÉP (dòng 'Thời hạn … đến hết ngày'); dự phòng Đơn Mẫu 05."},
    {"name": "CapLai_LyDo", "desc": "CHỈ khi CẤP LẠI: LÝ DO đề nghị cấp lại — chọn theo ô đã tích trên Đơn "
        "Mẫu 05, trả CHÍNH XÁC một hoặc nhiều trong: 'Giấy phép bị mất' / 'Giấy phép bị hư hỏng' / 'Thay "
        "đổi thông tin' / 'Giấy phép hết hạn'. Nếu nhiều lý do, nối bằng ';'."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _p in ("NguoiDeNghi_", "NguoiNop_"):
    COMPACT_COMP_BY_NAME[f"{_p}NgaySinh"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_p}NgayCap"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_p}ThuongTru"] = "x-select-area"
COMPACT_COMP_BY_NAME["CapLai_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["CapLai_NgayHetHan"] = "x-date"

# ---- UI Form.io fields (data[...]) — comp dom-*. Tên lấy CHUẨN từ HTML thật (trùng khít #97).
UI_COMP_BY_NAME = {
    # Phần 1 — NGƯỜI NỘP HỒ SƠ.
    "data[chonDoiTuong]": "dom-select",   # "Cá nhân".
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[idIssuePlace]": "dom-input",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[email]": "dom-input",

    # Ô mặc định CHƯA tick — tự nộp TICH (True); nộp thay để False.
    "data[isOwnerDossierCheck]": "dom-checkbox",

    # Phần 2 — CHỦ HỒ SƠ (= chủ tàu). Chỉ điền khi nộp thay.
    "data[ownerFullname]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[ownerGender]": "dom-select",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerIdIssuePlace]": "dom-input",
    "data[ownerProvince]": "dom-select",
    "data[ownerDistrict]": "dom-select",
    "data[ownerAddress]": "dom-input",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerEmail]": "dom-input",
    "data[ownerNation]": "dom-select",

    # Phần 3 — ĐƠN ĐỀ NGHỊ (chung). Các key trùng Phần 1 điền bằng occurrence=1.
    "data[kinhgui]": "dom-input",
    "data[diaDanh]": "dom-select",
    "data[loaiGT]": "dom-input",
    "data[tenCQ]": "dom-input",
    "data[chuCS]": "dom-input",

    # Cấp mới (Đơn Mẫu 04) — thông tin tàu.
    "data[soGDK]": "dom-input",
    "data[soGCN]": "dom-input",
    "data[trangThietBi]": "dom-input",
    "data[loaiThietBi]": "dom-input",
    "data[ngheChinh]": "dom-input",
    "data[nghePhu]": "dom-input",

    # Cấp lại (Đơn Mẫu 05) — GP cũ + lý do (checkbox).
    "data[soGP]": "dom-input",
    "data[ngayCap1]": "dom-date",
    "data[ngayHH]": "dom-date",
    "data[biMat]": "dom-checkbox",
    "data[huHong]": "dom-checkbox",
    "data[thayDoiTT]": "dom-checkbox",
    "data[gpHetHan]": "dom-checkbox",
}
