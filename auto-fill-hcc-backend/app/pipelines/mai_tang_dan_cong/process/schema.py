"""Compact schema cho mai táng phí dân công hỏa tuyến (cổng MOHA — Form.io).

HAI vai trò tách RIÊNG (không dùng Person1/Person2 mơ hồ):
- ChuHoSo_* = CHỦ HỒ SƠ = người đứng khai nhận trợ cấp mai táng phí (thân nhân của người từ trần), lấy ở
  mục 1 Bản khai Mẫu 02-MTP + thẻ CCCD của chính người đó.
- NguoiNop_* = NGƯỜI NỘP = người có thẻ CCCD KHÁC người đứng khai (nộp thay). LLM trích theo quy tắc giấy
  tờ (thẻ CCCD ≠ người mục 1); MAPPER mới xác minh khớp tài khoản UI (formContext) và bật/tắt ô "Người
  nộp là chủ hồ sơ". Nếu mọi thẻ CCCD đều là của người đứng khai → bỏ trống NguoiNop_*.

LLM chỉ TRÍCH FACT hai vai; KHÔNG quyết định ai khớp UI — đó là việc của mapper.
"""

# --- Nhân thân (template dùng chung cho ChuHoSo_ và NguoiNop_) ---
_PERSON_FIELDS = [
    ("HoTen", "Họ và tên {who}. Lấy từ {src}."),
    ("NgaySinh", "Ngày sinh {who}, dd/mm/yyyy."),
    ("GioiTinh", 'Giới tính {who}: "Nam" hoặc "Nữ" — đọc từ thẻ CCCD (Bản khai Mẫu 02-MTP KHÔNG ghi giới '
        "tính thân nhân)."),
    ("SoDinhDanh", "Số CCCD/CMND/định danh {who}. Chỉ chữ số; ưu tiên 12 số. Đọc thẻ CCCD (mặt trước/MRZ) "
        "hoặc dòng 'CCCD số' trong {src}."),
    ("NgayCap", "Ngày cấp CCCD/CMND {who} (mặt sau thẻ CCCD, gần nhãn 'Ngày, tháng, năm' — KHÔNG lấy ngày "
        "sinh/ngày hết hạn) hoặc dòng 'ngày cấp' trong {src}, dd/mm/yyyy."),
    ("NoiCap", 'Nơi cấp CCCD/CMND {who}. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → '
        '"Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → "Bộ Công '
        'an".'),
    ("ThuongTru", "NƠI THƯỜNG TRÚ {who}, object {{quocGia,tinh,xa,diaChi}}. tinh='Tỉnh/Thành phố …', "
        "xa=phường/xã/thị trấn, diaChi=số nhà/thôn/tổ (KHÔNG kèm xã/huyện/tỉnh). Không lấy quê quán."),
    ("QuocTich", 'Quốc tịch {who}; thường "Việt Nam".'),
]

_CHUHOSO_SRC = "mục 1 Bản khai Mẫu 02-MTP (người đứng khai) và thẻ CCCD của chính người đó"
_NGUOINOP_SRC = "thẻ CCCD của NGƯỜI NỘP THAY (thẻ có họ tên/số KHÁC người đứng khai ở mục 1)"

FIELDS: list[dict] = []
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({
        "name": f"ChuHoSo_{_name}",
        "desc": _tmpl.format(who="CHỦ HỒ SƠ (người đứng khai nhận trợ cấp mai táng phí)", src=_CHUHOSO_SRC),
    })
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({
        "name": f"NguoiNop_{_name}",
        "desc": _tmpl.format(who="NGƯỜI NỘP THAY (chỉ khi có thẻ CCCD của người KHÁC người đứng khai)",
                             src=_NGUOINOP_SRC),
    })

# --- Field nghiệp vụ riêng (không phải vai trò) ---
FIELDS += [
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại CHỦ HỒ SƠ ghi ở mục 1 Bản khai Mẫu 02-MTP. Chỉ chữ số."},
    {"name": "ChuHoSo_QuanHeNguoiTuTran", "desc": "Quan hệ của chủ hồ sơ (người đứng khai) với người từ trần "
        "ghi ở mục 1 (vd 'Con đẻ', 'Vợ', 'Chồng'). Chỉ trả khi tờ khai ghi rõ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _p in ("ChuHoSo_", "NguoiNop_"):
    COMPACT_COMP_BY_NAME[f"{_p}NgaySinh"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_p}NgayCap"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_p}ThuongTru"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — contact block MOHA chuẩn. ----
UI_COMP_BY_NAME = {
    # Ô "Người nộp là chủ hồ sơ" phải phát TRƯỚC các field owner (điều khiển copy Phần I → Phần II).
    "data[isOwnerDossierCheck]": "dom-checkbox",

    # Phần I — NGƯỜI NỘP HỒ SƠ.
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

    # Phần II — CHỦ HỒ SƠ (điền tường minh khi nộp thay).
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
