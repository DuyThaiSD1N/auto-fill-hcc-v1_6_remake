"""Compact schema cho "Cấp Chứng chỉ hành nghề dược ... theo hình thức xét hồ sơ" (cổng Bộ Y tế —
Form.io). Field-key data[...] TRÙNG KHÍT với cap_moi_giay_phep_hanh_nghe_chuyen_tiep (#92) / #62.

HAI vai (thường trùng, có thể NỘP THAY):
- NGƯỜI ĐỀ NGHỊ (NguoiDeNghi_*) = CHỦ HỒ SƠ = dược sĩ đề nghị cấp CCHN dược → Phần II data[owner*].
  Giấy tờ (CCCD + Đơn đề nghị Mẫu 02 + Phiếu lý lịch tư pháp + văn bằng + giấy khám SK...) đều của họ.
- NGƯỜI NỘP (NguoiNop_*) = tài khoản đứng nộp (VNeID) → Phần I data[fullname...]. Tự nộp → TRÙNG người
  đề nghị. Nộp thay → KHÁC, chỉ trích khi hồ sơ CÓ CCCD người nộp riêng.

Quyết định tự-nộp / nộp-thay dựa vào formContext (tên + CCCD tài khoản cổng tự đổ vào Phần I) — xem mapper.

Cấu trúc form (mỗi data[key] XUẤT HIỆN 1 LẦN → KHÔNG occurrence):
  Phần 1 Người nộp  → data[fullname/birthday/gender/identityNumber/identityDate/idIssuePlace/province/
                      district/address/phoneNumber/email] + chonDoiTuong="Cá nhân".
  Phần 2 Chủ hồ sơ  → data[owner*] + data[ownerNation]. TỰ NỘP: giữ tích isOwnerDossierCheck (cổng tự
                      nhân bản). NỘP THAY: BỎ TÍCH rồi điền owner_*.
"""

_PERSON_FIELDS = [
    ("HoTen", "Họ và tên {who}. Lấy từ {src}. Ghi IN HOA đúng như trên giấy tờ."),
    ("NgaySinh", "Ngày sinh {who}, dd/mm/yyyy — {src}."),
    ("GioiTinh", 'Giới tính {who}: "Nam" hoặc "Nữ" — CCCD / Phiếu lý lịch tư pháp (mục Giới tính). Đơn đề '
        "nghị Mẫu 02 KHÔNG có mục giới tính; suy từ CCCD/Phiếu LLTP."),
    ("SoDinhDanh", "Số CCCD/CMND/căn cước/định danh cá nhân/hộ chiếu {who}. Đọc CCCD (mặt trước/MRZ) hoặc "
        "Đơn Mẫu 02 mục 5 ('Số Thẻ căn cước/Hộ chiếu/Các giấy tờ tương đương khác'). Chỉ chữ số. Ưu tiên "
        "số 12 chữ số (CCCD/căn cước/định danh) hơn số 9 chữ số (CMND) nếu có cả hai."),
    ("NgayCap", "Ngày cấp CCCD/CMND {who} (mặt sau CCCD) hoặc Đơn Mẫu 02 mục 5 'Ngày cấp', dd/mm/yyyy."),
    ("NoiCap", 'Nơi cấp giấy tờ tùy thân {who}. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ '
        'HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → '
        '"Bộ Công an". CCCD gắn chip không in nhãn "Nơi cấp" riêng → ưu tiên lấy ở Đơn Mẫu 02 mục 5 / Phiếu '
        "lý lịch tư pháp."),
    ("ThuongTru", "NƠI THƯỜNG TRÚ {who}, object {{quocGia,tinh,xa,diaChi}}. Lấy ở CCCD (Nơi thường trú) / "
        "Đơn Mẫu 02 mục 3 (Nơi đăng ký hộ khẩu thường trú) — ưu tiên tên địa giới MỚI sau sáp nhập ghi ở "
        "Đơn (Đơn lập gần đây; CCCD cũ có thể ghi tên tỉnh/xã CŨ). tinh='Tỉnh/Thành phố …', xa=phường/xã, "
        "diaChi=số nhà/đường/tổ/thôn (KHÔNG kèm phường/xã/huyện/tỉnh)."),
    ("DienThoai", "Số điện thoại DI ĐỘNG {who} — Đơn Mẫu 02 mục 6 'Điện thoại'. Chỉ chữ số; KHÔNG lấy số "
        "điện thoại bàn."),
    ("Email", "Email liên hệ {who} nếu Đơn Mẫu 02 mục 6 có ('Email (nếu có)'). Không có thì bỏ."),
]

_DENGHI_SRC = "CCCD / Đơn đề nghị Mẫu 02 / Phiếu lý lịch tư pháp của NGƯỜI ĐỀ NGHỊ cấp CCHN dược"

FIELDS: list[dict] = []
# === NGƯỜI ĐỀ NGHỊ = chủ hồ sơ (người chính) ===
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({
        "name": f"NguoiDeNghi_{_name}",
        "desc": _tmpl.format(who="NGƯỜI ĐỀ NGHỊ cấp CCHN dược (dược sĩ)", src=_DENGHI_SRC),
    })
# === NGƯỜI NỘP (Phần I khi NỘP THAY) — chỉ trích khi hồ sơ CÓ CCCD người nộp riêng (xem
# <nguoi_nop_context>). Tự nộp → để trống, mapper tự lấy người đề nghị cho Phần I. ===
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({
        "name": f"NguoiNop_{_name}",
        "desc": _tmpl.format(who="NGƯỜI NỘP (chỉ khi nộp thay & có CCCD người nộp)", src="CCCD của NGƯỜI NỘP"),
    })

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _p in ("NguoiDeNghi_", "NguoiNop_"):
    COMPACT_COMP_BY_NAME[f"{_p}NgaySinh"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_p}NgayCap"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_p}ThuongTru"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Tên lấy CHUẨN từ HTML thật (trùng khít #92). Mỗi key
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
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[email]": "dom-input",

    # BỎ TÍCH ô này CHỈ KHI nộp thay. Tự nộp → KHÔNG emit (giữ tích mặc định).
    "data[isOwnerDossierCheck]": "dom-checkbox",

    # Phần 2 — CHỦ HỒ SƠ (= người đề nghị). CHỈ điền khi nộp thay.
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
