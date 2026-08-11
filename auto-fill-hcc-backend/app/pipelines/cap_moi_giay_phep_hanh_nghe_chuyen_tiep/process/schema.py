"""Compact schema cho "Cấp mới giấy phép hành nghề trong giai đoạn chuyển tiếp..." (cổng Bộ Y tế —
Form.io). Field-key data[...] TRÙNG KHÍT với tro_cap_xa_hoi_hang_thang (cùng cổng).

HAI vai (thường trùng, nhưng có thể NỘP THAY):
- NGƯỜI HÀNH NGHỀ (NguoiHanhNghe_*) = CHỦ HỒ SƠ = người đề nghị cấp GPHN → Phần II data[owner*]. Đây là
  người chính; giấy tờ (CCCD + Đơn Mẫu 08 + Sơ yếu lý lịch Mẫu 09) đều của người này.
- NGƯỜI NỘP (NguoiNop_*) = người đứng nộp trên cổng (tài khoản VNeID) → Phần I data[fullname...]. Tự nộp
  → TRÙNG người hành nghề. Nộp thay (vd người nhà nộp hộ) → KHÁC, chỉ trích khi hồ sơ CÓ CCCD người nộp.

Quyết định tự-nộp / nộp-thay dựa vào formContext (tên + CCCD tài khoản cổng tự đổ vào Phần I) — xem mapper.

Cấu trúc form (mỗi data[key] XUẤT HIỆN 1 LẦN → KHÔNG occurrence):
  Phần 1 Người nộp  → data[fullname/birthday/gender/identityNumber/identityDate/idIssuePlace/province/
                      district/address/phoneNumber/email] + chonDoiTuong="Cá nhân".
  Phần 2 Chủ hồ sơ  → data[owner*] + data[ownerNation]. TỰ NỘP: giữ tích data[isOwnerDossierCheck] (cổng
                      tự nhân bản Phần I → Phần II). NỘP THAY: BỎ TÍCH rồi điền owner_* tường minh.
"""

_PERSON_FIELDS = [
    ("HoTen", "Họ và tên {who}. Lấy từ {src}. Ghi IN HOA đúng như trên giấy tờ."),
    ("NgaySinh", "Ngày sinh {who}, dd/mm/yyyy — {src}."),
    ("GioiTinh", 'Giới tính {who}: "Nam" hoặc "Nữ" — CCCD / Mẫu 09 (ô "Nam, nữ"). Mẫu 08 không có giới '
        "tính; suy từ CCCD/Mẫu 09."),
    ("SoDinhDanh", "Số CCCD/CMND/căn cước/định danh cá nhân {who}. Đọc CCCD (mặt trước/MRZ) hoặc Mẫu 08/09. "
        "Chỉ chữ số. Ưu tiên số 12 chữ số (CCCD/căn cước/định danh) hơn số 9 chữ số (CMND) nếu có cả hai."),
    ("NgayCap", "Ngày cấp CCCD/CMND {who} (mặt sau CCCD) hoặc Mẫu 08/09 'Ngày cấp', dd/mm/yyyy."),
    ("NoiCap", 'Nơi cấp CCCD/CMND {who}. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → '
        '"Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → "Bộ Công '
        'an". CCCD gắn chip không in nhãn "Nơi cấp" riêng → lấy ở Mẫu 08/09 nếu có.'),
    ("ThuongTru", "NƠI THƯỜNG TRÚ {who}, object {{quocGia,tinh,xa,diaChi}}. Lấy ở CCCD (Nơi thường trú) / "
        "Mẫu 08 (Địa chỉ cư trú) / Mẫu 09 (Nơi thường trú hiện nay). tinh='Tỉnh/Thành phố …', xa=phường/xã "
        "(tên MỚI sau sáp nhập nếu giấy tờ ghi), diaChi=số nhà/đường/tổ/thôn (KHÔNG kèm phường/xã/huyện/tỉnh)."),
    ("DienThoai", "Số điện thoại DI ĐỘNG {who} — Mẫu 08 'Điện thoại' / Mẫu 09 'Di động'. Chỉ chữ số; "
        "KHÔNG lấy số điện thoại bàn/nhà riêng."),
    ("Email", "Email liên hệ {who} nếu Mẫu 08 có ('Email (nếu có)'). CCCD và Mẫu 09 không có email → thường bỏ."),
]

_HANHNGHE_SRC = "CCCD / Đơn đề nghị (Mẫu 08) / Sơ yếu lý lịch (Mẫu 09) của NGƯỜI HÀNH NGHỀ"

FIELDS: list[dict] = []
# === NGƯỜI HÀNH NGHỀ = chủ hồ sơ (người chính) ===
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({
        "name": f"NguoiHanhNghe_{_name}",
        "desc": _tmpl.format(who="NGƯỜI HÀNH NGHỀ (người đề nghị cấp GPHN)", src=_HANHNGHE_SRC),
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

    # BỎ TÍCH ô này CHỈ KHI nộp thay (để mở + điền Phần II). Tự nộp → KHÔNG emit (giữ tích mặc định).
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
