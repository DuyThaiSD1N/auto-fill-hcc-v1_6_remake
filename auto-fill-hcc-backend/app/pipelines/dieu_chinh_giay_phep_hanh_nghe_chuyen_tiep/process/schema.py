"""Compact schema cho "Điều chỉnh giấy phép hành nghề trong giai đoạn chuyển tiếp..." (cổng Bộ Y tế —
Form.io). Field-key data[...] TRÙNG KHÍT cap_moi_giay_phep_hanh_nghe_chuyen_tiep, thêm data[ghiChu].

HAI vai (thường trùng, nhưng có thể NỘP THAY):
- NGƯỜI HÀNH NGHỀ (NguoiHanhNghe_*) = CHỦ HỒ SƠ = người đề nghị điều chỉnh GPHN → Phần II data[owner*].
- NGƯỜI NỘP (NguoiNop_*) = người đứng nộp trên cổng (tài khoản VNeID) → Phần I data[fullname...]. Tự nộp
  → TRÙNG người hành nghề. Nộp thay → KHÁC, chỉ trích khi hồ sơ CÓ CCCD người nộp.

Nội dung đề nghị (HoSo_*) lấy từ Đơn Mẫu 08 → mapper ghép thành data[ghiChu].
"""

_PERSON_FIELDS = [
    ("HoTen", "Họ và tên {who}. Lấy từ {src}. Ghi IN HOA đúng như trên giấy tờ."),
    ("NgaySinh", "Ngày sinh {who}, dd/mm/yyyy — {src}."),
    ("GioiTinh", 'Giới tính {who}: "Nam" hoặc "Nữ" — CCCD / chứng chỉ đào tạo có ô "Giới tính". Mẫu 08 '
        "không có giới tính; KHÔNG suy từ tên."),
    ("SoDinhDanh", "Số CCCD/căn cước/định danh cá nhân {who}, 12 chữ số — CCCD hoặc Đơn Mẫu 08. Chỉ chữ số. "
        "KHÔNG lấy số CMND 9 chữ số in trên chứng chỉ hành nghề cũ."),
    ("NgayCap", "Ngày cấp CCCD/căn cước {who}, dd/mm/yyyy — CCCD hoặc Đơn Mẫu 08 'Ngày cấp'. KHÔNG lấy "
        "'Cấp ngày' của CMND cũ in trên chứng chỉ hành nghề."),
    ("NoiCap", 'Nơi cấp CCCD/căn cước {who} — CCCD hoặc Đơn Mẫu 08 "Nơi cấp". "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN '
        'LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; "BỘ CÔNG AN" '
        '→ "Bộ Công an". KHÔNG lấy nơi cấp CMND cũ in trên chứng chỉ hành nghề.'),
    ("ThuongTru", "NƠI CƯ TRÚ HIỆN TẠI {who}, object {{quocGia,tinh,xa,diaChi}}. Lấy ở CCCD (Nơi cư trú/Nơi "
        "thường trú) hoặc Đơn Mẫu 08 (Địa chỉ cư trú). tinh='Tỉnh/Thành phố …' (viết đầy đủ, 't.p' → 'Thành "
        "phố'), xa='Phường/Xã …', diaChi=số nhà/đường/tổ/thôn (KHÔNG kèm phường/xã/tỉnh; giấy tờ không ghi "
        "thì để trống). KHÔNG lấy địa chỉ trên chứng chỉ hành nghề / văn bằng / chứng chỉ đào tạo (địa chỉ cũ)."),
    ("DienThoai", "Số điện thoại DI ĐỘNG {who} — Đơn Mẫu 08 'Điện thoại'. Chỉ chữ số; KHÔNG lấy số bàn."),
    ("Email", "Email {who} — Đơn Mẫu 08 'Email (nếu có)'. Không có thì bỏ."),
]

_HANHNGHE_SRC = "CCCD / Đơn đề nghị (Mẫu 08) của NGƯỜI HÀNH NGHỀ"

FIELDS: list[dict] = []
# === NGƯỜI HÀNH NGHỀ = chủ hồ sơ (người chính) ===
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({
        "name": f"NguoiHanhNghe_{_name}",
        "desc": _tmpl.format(who="NGƯỜI HÀNH NGHỀ (người đề nghị điều chỉnh GPHN)", src=_HANHNGHE_SRC),
    })
# === NGƯỜI NỘP (Phần I khi NỘP THAY) — chỉ trích khi hồ sơ CÓ CCCD người nộp riêng. ===
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({
        "name": f"NguoiNop_{_name}",
        "desc": _tmpl.format(who="NGƯỜI NỘP (chỉ khi nộp thay & có CCCD người nộp)", src="CCCD của NGƯỜI NỘP"),
    })
# === Nội dung đề nghị trên Đơn Mẫu 08 → data[ghiChu] ===
FIELDS += [
    {"name": "HoSo_TruongHopDeNghi", "desc": 'Đơn Mẫu 08 mục "Trường hợp đề nghị cấp" (và "Hồ sơ đề nghị …"), '
        'viết lại gọn, chuẩn chính tả, vd "Cấp điều chỉnh giấy phép hành nghề (bổ sung phạm vi hành nghề)".'},
    {"name": "HoSo_PhamViHanhNghe", "desc": 'Đơn Mẫu 08 mục "Phạm vi hành nghề đề nghị cấp", liệt kê ngăn cách '
        'dấu phẩy, viết hoa chữ đầu mỗi mục, vd "Nội khoa, Hồi sức cấp cứu".'},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _p in ("NguoiHanhNghe_", "NguoiNop_"):
    COMPACT_COMP_BY_NAME[f"{_p}NgaySinh"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_p}NgayCap"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_p}ThuongTru"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Tên lấy từ HTML thật (sheet mapping). Mỗi key 1×.
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

    # Tự nộp → True (cổng để trống mặc định), nộp thay → False. Engine tick SAU cùng nên cổng nhân bản
    # Phần 1 đã điền sang Phần 2.
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
    "data[ghiChu]": "dom-input",
}
