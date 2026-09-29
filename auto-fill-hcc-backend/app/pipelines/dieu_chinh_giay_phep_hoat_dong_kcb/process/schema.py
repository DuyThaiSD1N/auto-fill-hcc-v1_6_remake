"""Compact schema cho "Điều chỉnh giấy phép hoạt động khám bệnh, chữa bệnh" (cổng Bộ Y tế — Form.io).
Field-key data[...] TRÙNG KHÍT các thủ tục BYT (cap_moi_giay_phep_hanh_nghe_chuyen_tiep…) + fax/ownerFax và
4 ô TỔ CHỨC (organization/taxCode/ownerOrganizationFullname/ownerTaxCode) chỉ hiện khi Đối tượng nộp hồ sơ
là tổ chức.

CHỦ HỒ SƠ = CƠ SỞ KHÁM BỆNH, CHỮA BỆNH (tổ chức) — nguồn: Đơn đề nghị Mẫu 02, giấy phép hoạt động đã cấp.
NGƯỜI ĐẠI DIỆN = người ký Đơn (Giám đốc/Phó Giám đốc) → ô họ tên Phần II; nhân thân khác chỉ khi hồ sơ có
CCCD của chính người này. NGƯỜI NỘP thay (tài khoản đăng nhập) chỉ trích khi hồ sơ có CCCD riêng của họ.
Mỗi data[key] XUẤT HIỆN 1 LẦN → KHÔNG occurrence.
"""

_DON = "Đơn đề nghị cấp điều chỉnh giấy phép hoạt động (Mẫu 02)"
_GPHD = "giấy phép hoạt động khám bệnh, chữa bệnh đã được cấp"

FIELDS: list[dict] = [
    {"name": "CoSo_Ten", "desc": f"Tên cơ sở khám bệnh, chữa bệnh HIỆN TẠI (đang đứng tên trên {_GPHD}): dòng "
        f"'Tên cơ sở đề nghị' / 'Tên cơ sở đã được cấp' trên {_DON}, hoặc 'Tên cơ sở khám bệnh, chữa bệnh' trên "
        "giấy phép. KHÔNG lấy 'Tên cơ sở đề nghị điều chỉnh' (tên MỚI xin đổi). Viết hoa như trên giấy."},
    {"name": "CoSo_LoaiDoiTuong", "desc": 'Loại chủ thể của cơ sở, đúng MỘT trong hai: "Cơ quan nhà nước" khi '
        "cơ sở là đơn vị công lập (trung tâm y tế, bệnh viện, trạm y tế… trực thuộc Sở Y tế / UBND / bộ ngành, "
        'giấy tờ có quyết định tổ chức lại của UBND/Sở); "Tổ chức/Doanh nghiệp" khi là cơ sở tư nhân (công '
        "ty, phòng khám tư, bệnh viện tư nhân…). Không đủ căn cứ thì bỏ field."},
    {"name": "CoSo_DiaChi", "desc": "Địa chỉ HIỆN TẠI của cơ sở, object {quocGia,tinh,xa,diaChi}: dòng 'Địa "
        f"chỉ' / 'Địa điểm hoạt động đã được cấp' trên {_DON}, hoặc 'Địa chỉ hoạt động' trên giấy phép. KHÔNG "
        "lấy 'Địa điểm đề nghị điều chỉnh'. diaChi CHỈ phần chi tiết (số nhà/đường/tổ dân phố/thôn), không "
        "kèm xã/tỉnh."},
    {"name": "CoSo_DienThoai", "desc": f"Số 'Điện thoại' của cơ sở trên {_DON}. Giữ nguyên chữ số (có thể là "
        "số máy bàn của cơ sở)."},
    {"name": "CoSo_Fax", "desc": f"'Số Fax' của cơ sở trên {_DON}. Không có thì bỏ field."},
    {"name": "CoSo_Email", "desc": f"'Email' của cơ sở trên {_DON}. Để trống trên Đơn thì bỏ field."},
]

_PERSON_FIELDS = [
    ("HoTen", "Họ và tên {who}. {src} Ghi đúng như trên giấy tờ."),
    ("NgaySinh", "Ngày sinh {who}, dd/mm/yyyy — CHỈ lấy từ CCCD của chính người này."),
    ("GioiTinh", 'Giới tính {who}: "Nam" hoặc "Nữ" — CHỈ lấy từ CCCD của chính người này.'),
    ("SoDinhDanh", "Số CCCD/căn cước {who} — CHỈ lấy từ CCCD của chính người này. Chỉ chữ số."),
    ("NgayCap", "Ngày cấp CCCD {who}, dd/mm/yyyy — cùng thẻ CCCD với số định danh."),
    ("NoiCap", 'Nơi cấp CCCD {who}: dòng chức danh người ký mặt sau thẻ ("CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH '
        'CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; "BỘ CÔNG AN" → "Bộ '
        'Công an").'),
]

for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({"name": f"DaiDien_{_name}", "desc": _tmpl.format(
        who="NGƯỜI ĐẠI DIỆN của cơ sở (người KÝ Đơn — Giám đốc / Phó Giám đốc / người được ủy quyền)",
        src=f"Lấy tên người ký ở cuối {_DON} (dưới chức danh, trên con dấu cơ sở).",
    )})
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({"name": f"NguoiNop_{_name}", "desc": _tmpl.format(
        who="NGƯỜI NỘP thay (chỉ khi hồ sơ có CCCD riêng của người nộp, xem <nguoi_nop_context>)",
        src="Lấy từ CCCD của NGƯỜI NỘP.",
    )})

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["CoSo_DiaChi"] = "x-select-area"
for _p in ("DaiDien_", "NguoiNop_"):
    COMPACT_COMP_BY_NAME[f"{_p}NgaySinh"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_p}NgayCap"] = "x-date"

# ---- UI Form.io fields (data[...]) — comp dom-*. Mỗi key 1× → không occurrence.
UI_COMP_BY_NAME = {
    # Phần 1 — NGƯỜI NỘP HỒ SƠ. Phát chonDoiTuong TRƯỚC: ô organization/taxCode chỉ hiện sau khi chọn tổ chức.
    "data[chonDoiTuong]": "dom-select",   # "Cá nhân" / "Tổ chức/Doanh nghiệp" / "Cơ quan nhà nước".
    "data[organization]": "dom-input",
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
    "data[fax]": "dom-input",

    # Tự nộp → True (cổng tự nhân bản Phần I sang Phần II); nộp thay → False rồi điền Phần II.
    "data[isOwnerDossierCheck]": "dom-checkbox",

    # Phần 2 — CHỦ HỒ SƠ = cơ sở KCB + người đại diện. CHỈ điền khi nộp thay.
    "data[ownerOrganizationFullname]": "dom-input",
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
    "data[ownerFax]": "dom-input",
    "data[ownerNation]": "dom-select",
}
