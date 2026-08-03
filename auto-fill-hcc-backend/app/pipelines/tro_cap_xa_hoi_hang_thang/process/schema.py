"""Compact schema cho "Thực hiện, điều chỉnh, thôi hưởng trợ cấp xã hội hàng tháng, hỗ trợ kinh phí
chăm sóc, nuôi dưỡng hàng tháng" (cổng Bộ Y tế — Form.io).

HAI vai (có thể NỘP THAY — như sua_doi / di_chuyen):
- ĐỐI TƯỢNG hưởng trợ cấp (DoiTuong_*) = CHỦ HỒ SƠ → Phần II data[owner*]. Đây là đối tượng chính (người
  khuyết tật / trẻ em / NCT / người đơn thân...). TRẺ EM không có CCCD → lấy từ Giấy khai sinh.
- NGƯỜI NỘP (NguoiNop_*) = người đứng nộp / khai thay → Phần I data[fullname...]. Tự nộp → trùng đối tượng.

Cấu trúc form (field-key CHUẨN từ HTML thật; mỗi key XUẤT HIỆN 1 LẦN → KHÔNG occurrence):
  Phần 1 Người nộp  → data[fullname/birthday/gender/identityNumber/identityDate/idIssuePlace/province/
                      district/address/phoneNumber/email] + chonDoiTuong="Cá nhân".
  Phần 2 Chủ hồ sơ  → data[owner*] + data[ghiChu]. BỎ TÍCH data[isOwnerDossierCheck] để mở + điền.
"""

FIELDS: list[dict] = [
    # === ĐỐI TƯỢNG hưởng trợ cấp = chủ hồ sơ (đối tượng chính) ===
    {"name": "DoiTuong_HoTen", "desc": "Họ và tên ĐỐI TƯỢNG hưởng trợ cấp (người khuyết tật / trẻ em / NCT / "
        "người đơn thân... — người đứng tên hồ sơ). Lấy từ CCCD / Tờ khai (Mẫu 1a-1đ, 2a, 2b, 03) / Giấy xác "
        "nhận khuyết tật / Biên bản giám định y khoa / Giấy khai sinh (nếu đối tượng là trẻ em). Ghi IN HOA "
        "như trên giấy tờ. KHÔNG lấy tên người nộp/khai thay vào đây."},
    {"name": "DoiTuong_NgaySinh", "desc": "Ngày sinh đối tượng, dd/mm/yyyy — CCCD / Tờ khai / Giấy khai sinh "
        "(trẻ em) / Biên bản giám định y khoa / Giấy xác nhận khuyết tật."},
    {"name": "DoiTuong_GioiTinh", "desc": 'Giới tính đối tượng: "Nam" hoặc "Nữ".'},
    {"name": "DoiTuong_SoDinhDanh", "desc": "Số CCCD/CMND đối tượng; đọc CCCD (mặt trước/MRZ) hoặc Tờ khai / "
        "Biên bản giám định. Chỉ chữ số. TRẺ EM chưa có CCCD → để trống (không bịa)."},
    {"name": "DoiTuong_NgayCap", "desc": "Ngày cấp CCCD/CMND đối tượng (mặt sau CCCD) hoặc Tờ khai, dd/mm/yyyy."},
    {"name": "DoiTuong_NoiCap",
     "desc": 'Nơi cấp CCCD/CMND đối tượng. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → '
             '"Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → '
             '"Bộ Công an". CCCD gắn chip không in nhãn "Nơi cấp" riêng → ưu tiên lấy ở Tờ khai.'},
    {"name": "DoiTuong_ThuongTru",
     "desc": "NƠI THƯỜNG TRÚ đối tượng, object {quocGia,tinh,xa,diaChi}. Ưu tiên Tờ khai (lập gần đây, ghi "
             "địa giới MỚI sau sáp nhập); CCCD cũ có thể ghi tên CŨ. tinh='Tỉnh/Thành phố …', xa=phường/xã "
             "(tên MỚI nếu biết), diaChi=số nhà/đường/tổ dân phố/thôn (KHÔNG kèm xã/huyện/tỉnh)."},
    {"name": "DoiTuong_DienThoai", "desc": "Số điện thoại đối tượng nếu Tờ khai có. Chỉ chữ số; không lấy SĐT bàn."},
    {"name": "DoiTuong_Email", "desc": "Email đối tượng nếu giấy tờ có (thường không có → bỏ)."},
    {"name": "DoiTuong_GhiChu", "desc": "Ghi chú về đối tượng — dạng tật + MỨC ĐỘ khuyết tật (vd 'Khuyết tật "
        "vận động, mức độ Nặng') lấy ở Giấy xác nhận khuyết tật / Biên bản giám định y khoa / Tờ khai; hoặc "
        "diện đối tượng bảo trợ (trẻ mồ côi, hộ nghèo...). Chép ngắn gọn nếu có, không thì bỏ."},

    # === NGƯỜI NỘP (Phần I) — khi NỘP THAY thì KHÁC đối tượng. Chỉ trích khi hồ sơ CÓ CCCD người nộp
    # (xem <nguoi_nop_context>). Tự nộp → để trống, mapper tự lấy đối tượng cho Phần I. ===
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI NỘP (chỉ khi nộp thay & có CCCD người nộp). IN HOA."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh NGƯỜI NỘP, dd/mm/yyyy — CCCD người nộp."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính NGƯỜI NỘP: "Nam"/"Nữ" — CCCD người nộp.'},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND NGƯỜI NỘP — CCCD người nộp. Chỉ chữ số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD/CMND NGƯỜI NỘP, dd/mm/yyyy."},
    {"name": "NguoiNop_NoiCap", "desc": "Nơi cấp CCCD/CMND NGƯỜI NỘP. Chuẩn hóa như DoiTuong_NoiCap."},
    {"name": "NguoiNop_ThuongTru",
     "desc": "Nơi thường trú NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi} — CCCD người nộp. KHÁC đối tượng."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại NGƯỜI NỘP nếu giấy tờ có."},
    {"name": "NguoiNop_Email", "desc": "Email NGƯỜI NỘP nếu có."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("DoiTuong_NgaySinh", "DoiTuong_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("DoiTuong_ThuongTru", "NguoiNop_ThuongTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Tên lấy CHUẨN từ HTML thật. Mỗi key 1× → không occurrence.
UI_COMP_BY_NAME = {
    # Phần 1 — NGƯỜI NỘP HỒ SƠ (Form.io editable → CÓ điền).
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

    # BỎ TÍCH ô này để mở Phần II + chủ hồ sơ (= đối tượng).
    "data[isOwnerDossierCheck]": "dom-checkbox",

    # Phần 2 — chủ hồ sơ = ĐỐI TƯỢNG hưởng trợ cấp.
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
