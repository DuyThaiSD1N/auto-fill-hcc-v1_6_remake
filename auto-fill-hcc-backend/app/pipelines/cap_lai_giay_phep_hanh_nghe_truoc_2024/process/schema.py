"""Compact schema cho "Cấp lại giấy phép hành nghề đối với trường hợp được cấp trước ngày 01/01/2024..."
(cổng Bộ Y tế — Form.io). Field-key data[...] TRÙNG KHÍT cap_moi_giay_phep_hanh_nghe_chuyen_tiep / #62.

HAI vai (thường trùng, nhưng có thể NỘP THAY):
- NGƯỜI HÀNH NGHỀ (NguoiHanhNghe_*) = CHỦ HỒ SƠ = người đề nghị cấp lại → Phần II data[owner*]. Giấy tờ
  nguồn: CCCD, Đơn đề nghị (Mẫu 08), giấy phép / chứng chỉ hành nghề đã được cấp.
- NGƯỜI NỘP (NguoiNop_*) = người đứng nộp trên cổng (tài khoản VNeID) → Phần I data[fullname...]. Chỉ
  trích khi hồ sơ CÓ CCCD riêng của người nộp thay.

Hai chế độ người nộp (theo tài khoản / người nộp = chủ hồ sơ) quyết ở mapper.
Mỗi data[key] XUẤT HIỆN 1 LẦN → KHÔNG occurrence.
"""

_PERSON_FIELDS = [
    ("HoTen", "Họ và tên {who}. Lấy từ {src}. Ghi IN HOA đúng như trên giấy tờ."),
    ("NgaySinh", "Ngày sinh {who}, dd/mm/yyyy — {src}."),
    ("GioiTinh", 'Giới tính {who}: "Nam" hoặc "Nữ" — lấy ở CCCD (Đơn Mẫu 08 và giấy phép/chứng chỉ '
        "hành nghề không in giới tính). Không có CCCD thì bỏ field."),
    ("SoDinhDanh", "Số CCCD/CMND/căn cước/định danh cá nhân {who}. Đọc CCCD (mặt trước/MRZ), Đơn Mẫu 08 hoặc dòng "
        "'Thẻ Căn cước công dân số' trên giấy phép/chứng chỉ hành nghề. "
        "Chỉ chữ số. Ưu tiên số 12 chữ số (CCCD/căn cước/định danh) hơn số 9 chữ số (CMND) nếu có cả hai."),
    ("NgayCap", "Ngày cấp CCCD/CMND {who} (mặt sau CCCD) hoặc 'Ngày cấp' đi CÙNG số định danh trên Đơn Mẫu 08 / "
        "giấy phép hành nghề, dd/mm/yyyy. Chỉ lấy khi đi cùng đúng số định danh đã chọn."),
    ("NoiCap", 'Nơi cấp CCCD/CMND {who}. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → '
        '"Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → "Bộ Công '
        'an". Lấy ở dòng chức danh người ký mặt sau CCCD, hoặc "Nơi cấp" đi cùng số định danh trên Đơn Mẫu '
        '08 / giấy phép hành nghề.'),
    ("ThuongTru", "NƠI THƯỜNG TRÚ {who}, object {{quocGia,tinh,xa,diaChi}}. Ưu tiên Đơn Mẫu 08 (Địa chỉ cư "
        "trú — thường ghi địa giới MỚI), rồi CCCD (Nơi thường trú); giấy phép hành nghề cũ chỉ bổ khuyết. "
        "tinh='Tỉnh/Thành phố …', xa=phường/xã (tên MỚI sau sáp nhập nếu giấy tờ ghi), diaChi=số nhà/đường/tổ/thôn (KHÔNG kèm phường/xã/huyện/tỉnh)."),
    ("DienThoai", "Số điện thoại DI ĐỘNG {who} — Đơn Mẫu 08 'Điện thoại'. Chỉ chữ số; "
        "KHÔNG lấy số điện thoại bàn/nhà riêng."),
    ("Email", "Email liên hệ {who} nếu Đơn Mẫu 08 có ('Email (nếu có)'). Giấy tờ khác không có email → bỏ."),
]

_HANHNGHE_SRC = "CCCD / Đơn đề nghị (Mẫu 08) / giấy phép hoặc chứng chỉ hành nghề đã cấp của NGƯỜI HÀNH NGHỀ"

FIELDS: list[dict] = []
# === NGƯỜI HÀNH NGHỀ = chủ hồ sơ (người chính) ===
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({
        "name": f"NguoiHanhNghe_{_name}",
        "desc": _tmpl.format(who="NGƯỜI HÀNH NGHỀ (người đề nghị cấp lại GPHN)", src=_HANHNGHE_SRC),
    })
# === NGƯỜI NỘP (Phần I khi NỘP THAY) — chỉ trích khi hồ sơ CÓ CCCD người nộp riêng (xem
# <nguoi_nop_context>). Tự nộp → để trống, mapper tự lấy người hành nghề cho Phần I. ===
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({
        "name": f"NguoiNop_{_name}",
        "desc": _tmpl.format(who="NGƯỜI NỘP (chỉ khi nộp thay & có CCCD người nộp)", src="CCCD của NGƯỜI NỘP"),
    })

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _p in ("NguoiHanhNghe_", "NguoiNop_"):
    COMPACT_COMP_BY_NAME[f"{_p}NgaySinh"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_p}NgayCap"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_p}ThuongTru"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Tên lấy CHUẨN từ HTML thật (trùng khít #62). Mỗi key
# 1× → không occurrence.
UI_COMP_BY_NAME = {
    # Phần 1 — NGƯỜI NỘP HỒ SƠ.
    "data[chonDoiTuong]": "dom-select",   # "Cá nhân".
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[idIssuePlace]": "dom-input",
    "data[province]": "dom-select",   # Nơi thường trú tỉnh.
    "data[district]": "dom-select",   # Nơi thường trú phường/xã.
    "data[address]": "dom-input",     # Nơi thường trú chi tiết.
    "data[phoneNumber]": "dom-input",
    "data[email]": "dom-input",

    # Tự nộp → True (cổng tự nhân bản Phần I sang Phần II); nộp thay → False rồi điền Phần II.
    "data[isOwnerDossierCheck]": "dom-checkbox",

    # Phần 2 — CHỦ HỒ SƠ (= người hành nghề). CHỈ điền khi nộp thay.
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
}
