"""Compact schema cho "Thực hiện trợ cấp xã hội và nhận chăm sóc, nuôi dưỡng, hỗ trợ kinh phí nhận chăm
sóc, nuôi dưỡng hằng tháng" (NĐ 335/2026/NĐ-CP, cổng Bộ Y tế — Form.io).

HAI vai:
- ĐỐI TƯỢNG hưởng trợ cấp (DoiTuong_*) = CHỦ HỒ SƠ → Phần II data[owner*]. Nguồn: Tờ khai Mẫu 01 mục I.1
  (hoặc Mẫu 02 mục IV — người được nhận chăm sóc, nuôi dưỡng), CCCD/thẻ căn cước, Giấy khai sinh.
- NGƯỜI NỘP (NguoiNop_*) = người khai thay → Phần I data[fullname...]. Nguồn: Mẫu 01 mục I.2 "Thông tin
  người giám hộ" (thiếu thì mục III.1 người nhận thay, nếu khác đối tượng); Mẫu 02 mục I người đại diện hộ
  gia đình. Không có người khai thay → mapper dùng đối tượng cho Phần I.

Cấu trúc form (field-key lấy từ file mapping HTML thật; mỗi key XUẤT HIỆN 1 LẦN → KHÔNG occurrence):
  Phần 1 Người nộp  → data[fullname/birthday/gender/identityNumber/identityDate/idIssuePlace/province/
                      district/address/phoneNumber/email] + chonDoiTuong="Cá nhân".
  Phần 2 Chủ hồ sơ  → data[owner*] + data[ghiChu]. BỎ TÍCH data[isOwnerDossierCheck] để mở + điền.
  Trường ẩn (organization, taxCode, ownerOrganizationFullname, ownerTaxCode, copyDuLieu3) chỉ hiện với tổ
  chức → không điền. data[fax]/data[ownerFax] không có nguồn → không điền.
"""

FIELDS: list[dict] = [
    # === ĐỐI TƯỢNG hưởng trợ cấp = chủ hồ sơ ===
    {"name": "DoiTuong_HoTen", "desc": "Họ và tên ĐỐI TƯỢNG hưởng trợ cấp xã hội (Tờ khai Mẫu 01 mục I.1.1 / "
        "Mẫu 02 mục IV người được nhận chăm sóc, nuôi dưỡng) — người khuyết tật / trẻ em / người cao tuổi / "
        "người đơn thân... đứng tên hồ sơ. Lấy từ CCCD/thẻ căn cước, Tờ khai, Giấy xác nhận khuyết tật, Giấy "
        "khai sinh. Ghi IN HOA như trên giấy tờ. KHÔNG lấy tên người giám hộ/người khai/người nhận thay."},
    {"name": "DoiTuong_NgaySinh", "desc": "Ngày sinh đối tượng, dd/mm/yyyy — CCCD / Tờ khai / Giấy khai sinh."},
    {"name": "DoiTuong_GioiTinh", "desc": 'Giới tính đối tượng: "Nam" hoặc "Nữ".'},
    {"name": "DoiTuong_SoDinhDanh", "desc": "Số căn cước / số định danh cá nhân của đối tượng (CCCD, thẻ căn "
        "cước, dòng \"Số căn cước/Số định danh cá nhân\" mục I.1.1 của Tờ khai, Giấy khai sinh). Chỉ chữ số."},
    {"name": "DoiTuong_NgayCap", "desc": "Ngày cấp căn cước của đối tượng (mặt sau thẻ hoặc \"ngày cấp\" mục "
        "I.1.1 Tờ khai), dd/mm/yyyy."},
    {"name": "DoiTuong_NoiCap",
     "desc": 'Nơi cấp căn cước của đối tượng. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → '
             '"Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới (cấp từ 01/07/2024) ghi '
             '"BỘ CÔNG AN" → "Bộ Công an". Thẻ không in nhãn "Nơi cấp" → lấy ở Tờ khai.'},
    {"name": "DoiTuong_NoiCuTru",
     "desc": 'NƠI CƯ TRÚ đối tượng (Tờ khai mục I.1.2 "Nơi cư trú"), object {quocGia,tinh,xa,chiTietDuoiXa}. Ưu tiên '
             "Tờ khai (ghi địa giới MỚI sau sáp nhập); CCCD cũ có thể ghi tên CŨ. tinh='Tỉnh/Thành phố …', "
             "xa=phường/xã/đặc khu, chiTietDuoiXa=số nhà/đường/tổ dân phố/thôn (KHÔNG kèm xã/huyện/tỉnh)."},
    {"name": "DoiTuong_DienThoai", "desc": "Số điện thoại đối tượng (Tờ khai mục I.1.4). Chỉ chữ số; bỏ SĐT bàn."},
    {"name": "DoiTuong_Email", "desc": "Email đối tượng nếu giấy tờ có (thường không có → bỏ)."},

    # === NGƯỜI NỘP (Phần I) = người khai thay ===
    {"name": "NguoiNop_HoTen",
     "desc": 'Họ tên NGƯỜI KHAI THAY: Mẫu 01 mục I.2 "Thông tin người giám hộ" (block trống thì mục III.1 '
             '"Thông tin người nhận" nếu là người khác đối tượng); Mẫu 02 mục I người đại diện hộ gia đình. '
             "Ghi IN HOA. Không lấy cán bộ tiếp nhận hay cha/mẹ chỉ được nhắc ở mục II.1.1."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh người khai thay, dd/mm/yyyy, lấy trong đúng block đó hoặc "
        "CCCD riêng khớp đúng họ tên/số giấy tờ."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính người khai thay: "Nam"/"Nữ"; không suy từ tên.'},
    {"name": "NguoiNop_SoDinhDanh",
     "desc": "Số căn cước/định danh của người khai thay trong đúng block đó hoặc CCCD riêng khớp đúng người. "
             "Chỉ trả dãy 9 hoặc 12 chữ số; số thừa/thiếu chữ số thì bỏ, không tự sửa đoán."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp căn cước người khai thay, dd/mm/yyyy."},
    {"name": "NguoiNop_NoiCap",
     "desc": "Nơi cấp căn cước người khai thay. Ưu tiên CCCD riêng của người này; không có thì lấy ở Tờ khai. "
             "Hai mục của Tờ khai ghi khác nhau (I.2 vs III.1) thì lấy cơ quan cụ thể hơn (Cục Cảnh sát QLHC "
             "về TTXH). Chuẩn hóa như DoiTuong_NoiCap."},
    {"name": "NguoiNop_NoiCuTru",
     "desc": "Nơi cư trú người khai thay (mục I.2.2 / III.1 / Mẫu 02 mục I), object {quocGia,tinh,xa,chiTietDuoiXa}."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại người khai thay (mục I.2.4 / Mẫu 02 mục I.4)."},
    {"name": "NguoiNop_Email", "desc": "Email người khai thay nếu giấy tờ có."},
    {"name": "NguoiNop_QuanHe",
     "desc": 'Mối quan hệ của người khai thay với đối tượng (Mẫu 01 mục I.2.5 "Mối quan hệ với người đề nghị '
             'hưởng chính sách"), ví dụ "Bố đẻ", "Mẹ đẻ", "Ông nội". Không có thì bỏ.'},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("DoiTuong_NgaySinh", "DoiTuong_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("DoiTuong_NoiCuTru", "NguoiNop_NoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Mỗi key 1× → không occurrence.
UI_COMP_BY_NAME = {
    # Phần 1 — NGƯỜI NỘP HỒ SƠ.
    "data[chonDoiTuong]": "dom-select",   # "Cá nhân".
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[idIssuePlace]": "dom-input",
    "data[province]": "dom-select",   # Nơi cư trú tỉnh.
    "data[district]": "dom-select",   # Nơi cư trú phường/xã (key "district", nhãn "Phường/Xã").
    "data[address]": "dom-input",     # Địa chỉ chi tiết.
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
