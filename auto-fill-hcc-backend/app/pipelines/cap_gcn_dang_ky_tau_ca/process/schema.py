"""Compact schema cho "Cấp giấy chứng nhận đăng ký tàu cá, tàu phục vụ nuôi trồng thủy sản" (cổng Nông
nghiệp & Môi trường — Form.io). Field-key nhân thân data[...] TRÙNG KHÍT #66/#92/#101.

Form CHỈ thu NHÂN THÂN 2 vai (KHÔNG có ô thông số tàu — xem __init__). Nhóm field nguồn:
- NguoiDeNghi_* : nhân thân CHỦ TÀU = CHỦ HỒ SƠ (người CHÍNH, chủ MỚI đứng tên đăng ký).
- NguoiNop_*    : nhân thân NGƯỜI NỘP (chỉ khi có người khác nộp thay & có CCCD riêng).
- ChuTau_*      : loại chủ thể (Cá nhân/Tổ chức) + tên tổ chức + mã số thuế/mã số DN (khi chủ là Tổ chức).
"""

# --- Nhân thân (dùng chung template cho NguoiDeNghi_ và NguoiNop_) ---
_PERSON_FIELDS = [
    ("HoTen", "Họ và tên {who}. Lấy từ {src}. Ghi IN HOA đúng như trên CCCD."),
    ("NgaySinh", "Ngày sinh {who}, dd/mm/yyyy — CCCD (hoặc 'Bên mua – Sinh ngày' của Hợp đồng mua bán)."),
    ("GioiTinh", 'Giới tính {who}: "Nam" hoặc "Nữ" — CCCD.'),
    ("SoDinhDanh", "Số CCCD/CMND/căn cước/định danh cá nhân {who}. Đọc CCCD (mặt trước/MRZ), hoặc Tờ khai "
        "02a.ĐKT mục 'Số CCCD/CC', hoặc Hợp đồng mua bán ('Căn cước công dân số'). Chỉ chữ số. Ưu tiên số "
        "12 chữ số (CCCD/căn cước/định danh) hơn số 9 chữ số (CMND) nếu có cả hai."),
    ("NgayCap", "Ngày cấp CCCD/CMND {who}, dd/mm/yyyy — mặt sau CCCD hoặc dòng '… cấp ngày' của Hợp đồng "
        "mua bán."),
    ("NoiCap", 'Nơi cấp/cơ quan cấp giấy tờ tùy thân {who}. CCCD gắn chip KHÔNG in nhãn "Nơi cấp" riêng → '
        'ghi "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → '
        '"Bộ Công an". Có thể lấy ở Quyết định chấp thuận (mục "Cơ quan cấp") nếu hồ sơ có.'),
    ("ThuongTru", "NƠI THƯỜNG TRÚ {who}, object {{quocGia,tinh,xa,diaChi}}. Ưu tiên CCCD (Nơi thường trú); "
        "bổ sung Tờ khai 02a.ĐKT (Thường trú tại) / Hợp đồng mua bán (Nơi cư trú). tinh='Tỉnh/Thành phố …', "
        "xa=phường/xã, diaChi=số nhà/khóm/ấp/thôn/tổ (KHÔNG kèm phường/xã/tỉnh). ⚠ Giấy chứng nhận đăng ký "
        "tàu cá cũ có thể còn ghi địa danh CŨ trước sáp nhập → ưu tiên CCCD/Hợp đồng."),
    ("DienThoai", "Số điện thoại DI ĐỘNG {who}. Ưu tiên Tờ khai 02a.ĐKT (Số điện thoại) / Thông báo thuế "
        "(Điện thoại). Chỉ chữ số; KHÔNG có trên CCCD."),
    ("Email", "Email liên hệ {who} nếu giấy tờ có; thường không có → bỏ."),
    ("QuocTich", 'Quốc tịch {who} từ CCCD/Hợp đồng; thường là "Việt Nam".'),
]

_DENGHI_SRC = "CCCD / Tờ khai 02a.ĐKT / Hợp đồng mua bán của CHỦ TÀU (chủ mới đứng tên đăng ký)"

FIELDS: list[dict] = []
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({
        "name": f"NguoiDeNghi_{_name}",
        "desc": _tmpl.format(who="CHỦ TÀU (chủ hồ sơ, chủ MỚI đứng tên đăng ký)", src=_DENGHI_SRC),
    })
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({
        "name": f"NguoiNop_{_name}",
        "desc": _tmpl.format(who="NGƯỜI NỘP (chỉ khi nộp thay & có CCCD người nộp)", src="CCCD của NGƯỜI NỘP"),
    })

# --- Loại chủ thể chủ tàu (Cá nhân / Tổ chức) ---
FIELDS += [
    {"name": "ChuTau_LoaiChuThe", "desc": 'Loại chủ thể của CHỦ TÀU (chủ hồ sơ): trả "Tổ chức" nếu chủ '
        'tàu là công ty/hợp tác xã/doanh nghiệp/cơ quan (có tên tổ chức + mã số thuế/mã số DN trên Giấy '
        'chứng nhận ĐKDN, Hợp đồng, Thông báo thuế); ngược lại trả "Cá nhân". Đa số hồ sơ là "Cá nhân".'},
    {"name": "ChuTau_TenToChuc", "desc": "CHỈ khi ChuTau_LoaiChuThe='Tổ chức': tên đầy đủ tổ chức/doanh "
        "nghiệp/hợp tác xã chủ tàu (Giấy chứng nhận ĐKDN / Hợp đồng / Giấy chứng nhận đăng ký tàu cá)."},
    {"name": "ChuTau_MaSoThue", "desc": "CHỈ khi ChuTau_LoaiChuThe='Tổ chức': mã số thuế / mã số doanh "
        "nghiệp / mã số HTX của tổ chức chủ tàu. Chỉ chữ số. Nguồn: Thông báo thuế / Giấy chứng nhận ĐKDN."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _p in ("NguoiDeNghi_", "NguoiNop_"):
    COMPACT_COMP_BY_NAME[f"{_p}NgaySinh"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_p}NgayCap"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_p}ThuongTru"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Tên lấy CHUẨN từ HTML thật + mapping xlsx.
UI_COMP_BY_NAME = {
    # Phần I — THÔNG TIN NGƯỜI NỘP HỒ SƠ.
    "data[chonDoiTuong]": "dom-select",   # "Cá nhân" / "Tổ chức/Doanh nghiệp" / "Cơ quan nhà nước".
    "data[organization]": "dom-input",    # ẩn khi Cá nhân — tên tổ chức (Phần I) khi Đối tượng = Tổ chức.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[identityNumber]": "dom-input",  # DISABLED trên form (khóa theo VNeID) — điền vô hại, cổng tự khóa.
    "data[taxCode]": "dom-input",         # ẩn khi Cá nhân — mã số thuế (Phần I) khi Đối tượng = Tổ chức.
    "data[identityDate]": "dom-date",
    "data[idIssuePlace]": "dom-input",
    "data[province]": "dom-select",
    "data[district]": "dom-select",       # ⚠ label "Phường/Xã" nhưng field-key là district.
    "data[address]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[email]": "dom-input",

    # BỎ TÍCH khi nộp thay; tự nộp → TICH (True) để cổng tự đổ Phần I → Phần II.
    "data[isOwnerDossierCheck]": "dom-checkbox",

    # Phần II — THÔNG TIN CHỦ HỒ SƠ (chủ tàu). Chỉ điền khi nộp thay (hoặc chủ là Tổ chức).
    "data[ownerOrganizationFullname]": "dom-input",  # ẩn khi Cá nhân.
    "data[ownerFullname]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[ownerGender]": "dom-select",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerTaxCode]": "dom-input",               # ẩn khi Cá nhân.
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerIdIssuePlace]": "dom-input",
    "data[ownerProvince]": "dom-select",
    "data[ownerDistrict]": "dom-select",
    "data[ownerAddress]": "dom-input",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerEmail]": "dom-input",
    "data[ownerNation]": "dom-select",
}
