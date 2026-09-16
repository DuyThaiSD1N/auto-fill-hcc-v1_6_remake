"""Compact schema cho "Công bố cơ sở đủ điều kiện tiêm chủng" (mã 2.000655 — Sở Y tế, Form.io trên Cổng DVC
quốc gia).

Nhóm field:
- CoSo_*     : đọc ở TỜ THÔNG BÁO cơ sở đủ điều kiện tiêm chủng (tên cơ sở, địa chỉ, người đứng đầu, SĐT, email).
- DauCoSo_*  : nhân thân NGƯỜI ĐỨNG ĐẦU CƠ SỞ — đọc ở CCCD của người này (Phần II).
- NguoiNop_* : nhân thân NGƯỜI NỘP = tài khoản đang đăng nhập — CHỈ đọc ở CCCD khớp tài khoản (Phần I).
"""

_TB_SRC = "TỜ THÔNG BÁO cơ sở đủ điều kiện tiêm chủng"

_PERSON_FIELDS = [
    ("HoTen", "Họ và tên {who}, lấy từ {src}. Ghi đúng như trên thẻ."),
    ("NgaySinh", "Ngày sinh {who}, dd/mm/yyyy — {src}."),
    ("GioiTinh", 'Giới tính {who}: "Nam" hoặc "Nữ", đọc ở {src}. KHÔNG suy từ họ tên.'),
    ("SoDinhDanh", "Số CCCD/căn cước/định danh {who} — {src}. Chỉ chữ số, ưu tiên số 12 chữ số."),
    ("NgayCap", "Ngày cấp CCCD {who} (mặt sau thẻ), dd/mm/yyyy — {src}."),
    ("NoiCap", 'Nơi cấp CCCD {who}. Mặt sau CCCD ghi "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ '
        'HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ Căn cước mới ghi "BỘ CÔNG AN" → '
        '"Bộ Công an".'),
    ("ThuongTru", "NƠI THƯỜNG TRÚ {who} trên {src}, object {{quocGia,tinh,xa,diaChi}}. tinh='Tỉnh/Thành phố "
        "…', xa=phường/xã, diaChi=số nhà/đường/thôn/tổ (KHÔNG kèm phường/xã/huyện/tỉnh)."),
]

FIELDS: list[dict] = [
    {"name": "CoSo_Ten", "desc": f"Tên cơ sở thông báo — dòng 'Tên cơ sở thông báo' của {_TB_SRC} (vd 'Khoa "
        "Nhi, bệnh viện đa khoa Sìn Hồ'). Chép nguyên văn."},
    {"name": "CoSo_DiaChi", "desc": f"ĐỊA CHỈ cơ sở — dòng 'Địa chỉ' của {_TB_SRC}, object "
        "{quocGia,tinh,xa,diaChi}. tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường/thôn/bản/tổ "
        "(KHÔNG kèm phường/xã/tỉnh)."},
    {"name": "CoSo_NguoiDungDau", "desc": f"Họ tên NGƯỜI ĐỨNG ĐẦU CƠ SỞ — dòng 'Người đứng đầu cơ sở' của "
        f"{_TB_SRC}, hoặc người ký dưới chữ GIÁM ĐỐC. BỎ học hàm/chức danh đứng trước tên (BS, BS CK1, BSCKII, "
        "ThS, TS, DS…): 'BS CK1 Hoàng Việt Bắc' → 'Hoàng Việt Bắc'."},
    {"name": "CoSo_DienThoai", "desc": f"Số điện thoại liên hệ — dòng 'Điện thoại liên hệ' của {_TB_SRC}. Chỉ "
        "chữ số."},
    {"name": "CoSo_Email", "desc": f"Email — mục 'Email (nếu có)' của {_TB_SRC}. Không có thì bỏ."},
    {"name": "CoSo_CacCoSoKhac", "desc": "Hồ sơ có NHIỀU tờ Thông báo của CÁC CƠ SỞ khác nhau (vd nhiều khoa): "
        "liệt kê tên các cơ sở CÒN LẠI (ngoài CoSo_Ten), ngăn cách bằng ';'. Chỉ một → bỏ trống."},
]

_DAU_CO_SO = "NGƯỜI ĐỨNG ĐẦU CƠ SỞ"
_DAU_CO_SO_SRC = "CCCD / thẻ Căn cước của NGƯỜI ĐỨNG ĐẦU CƠ SỞ (trùng họ tên CoSo_NguoiDungDau)"
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({"name": f"DauCoSo_{_name}", "desc": _tmpl.format(who=_DAU_CO_SO, src=_DAU_CO_SO_SRC)})

_NOP = "NGƯỜI NỘP (tài khoản đăng nhập)"
_NOP_SRC = "CCCD của NGƯỜI NỘP — CHỈ CCCD được chỉ ra trong <nguoi_nop_context>; không có thì bỏ trống"
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({"name": f"NguoiNop_{_name}", "desc": _tmpl.format(who=_NOP, src=_NOP_SRC)})

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["CoSo_DiaChi"] = "x-select-area"
for _p in ("DauCoSo_", "NguoiNop_"):
    COMPACT_COMP_BY_NAME[f"{_p}NgaySinh"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_p}NgayCap"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_p}ThuongTru"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*, tên theo bảng mapping nghiệp vụ. Mỗi key 1× trong DOM.
UI_COMP_BY_NAME = {
    # --- Phần I "THÔNG TIN NGƯỜI NỘP HỒ SƠ" = tài khoản đăng nhập — CHỈ khi có CCCD khớp tài khoản ---
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

    # Bỏ tích "Người nộp hồ sơ là chủ hồ sơ" để mở khoá Phần II.
    "data[isOwnerDossierCheck]": "dom-checkbox",

    # --- Phần II "THÔNG TIN CHỦ HỒ SƠ" = theo tờ Thông báo ---
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
    # data[fax] / data[ownerFax] / data[ghiChu]: không có trong giấy tờ → người khai tự nhập.
}
