"""Compact schema cho "Cấp GCN đủ điều kiện kinh doanh dược (Sở Y tế)" — cổng Bộ Y tế (Form.io). Field-key data[...]
theo bảng mapping 18/11/2026, TRÙNG KHÍT thủ tục cấp lại / điều chỉnh (1.014104) cộng data[ownerFax], và data[fullname] /
data[identityNumber] (chỉ phát ở chế độ "Lấy người nộp theo tờ khai", kèm enableInput).

HAI vai:
- CHỦ HỒ SƠ (ChuHoSo_*) = người đại diện theo pháp luật của cơ sở kinh doanh dược.
- NGƯỜI NỘP (NguoiNop_*) = tài khoản đăng nhập; chỉ trích khi hồ sơ có CCCD KHỚP tài khoản (<nguoi_nop_context>).
Thông tin CƠ SỞ (CoSo_*) không có ô riêng — chỉ để soạn ô Ghi chú.

Mỗi data[key] xuất hiện 1 lần → KHÔNG occurrence.
"""

_PERSON_FIELDS = [
    ("HoTen", "Họ và tên {who}. Lấy từ {src}. Ghi đúng như giấy tờ, BỎ tiền tố chức danh/trình độ "
        '("Ông", "Bà", "DS.", "Dược sĩ", "Giám đốc").'),
    ("NgaySinh", "Ngày sinh {who}, dd/mm/yyyy — {src}."),
    ("GioiTinh", 'Giới tính {who}: "Nam" hoặc "Nữ" — {src}.'),
    ("SoDinhDanh", "Số CCCD/căn cước/số định danh cá nhân {who} (12 chữ số; CMND cũ 9 chữ số) — {src}. Chỉ chữ số. "
        "KHÔNG lấy Mã số doanh nghiệp, số CCHN dược."),
    ("NgayCap", "Ngày cấp CCCD/căn cước {who} (mặt sau thẻ, hoặc GCN đăng ký doanh nghiệp 'Ngày cấp' của giấy tờ pháp "
        "lý cá nhân), dd/mm/yyyy. KHÔNG lấy 'Năm cấp' / 'Ngày cấp chứng chỉ' của Chứng chỉ hành nghề dược."),
    ("NoiCap", 'Nơi cấp CCCD/căn cước {who}. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → '
        '"Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới → "Bộ Công an". KHÔNG lấy "Nơi cấp: Sở '
        'Y tế ..." của Chứng chỉ hành nghề dược.'),
    ("ThuongTru", "NƠI THƯỜNG TRÚ / nơi cư trú CÁ NHÂN {who}, object {{quocGia,tinh,xa,chiTietDuoiXa}} — {src}. "
        "tinh='Tỉnh/Thành phố …', xa=phường/xã, chiTietDuoiXa=số nhà/ngõ/đường/thôn (KHÔNG kèm phường/xã/tỉnh)."),
]

_CHU_SRC = (
    "CCCD của người đại diện → GCN đăng ký doanh nghiệp mục 'Người đại diện theo pháp luật' (Họ và tên, Giới tính, "
    "Sinh ngày, Số giấy tờ pháp lý, Ngày cấp, Nơi cấp, Địa chỉ thường trú) → Đơn đề nghị (người ký 'NGƯỜI ĐẠI DIỆN "
    "THEO PHÁP LUẬT') → Tài liệu thuyết minh Mẫu 11 mục A.3 → Tài liệu kỹ thuật mục 'Người đại diện theo pháp luật'"
)

FIELDS: list[dict] = []
# === CHỦ HỒ SƠ = người đại diện theo pháp luật của cơ sở ===
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({
        "name": f"ChuHoSo_{_name}",
        "desc": _tmpl.format(who="CHỦ HỒ SƠ (người đại diện theo pháp luật của cơ sở)", src=_CHU_SRC),
    })
FIELDS += [
    {
        "name": "ChuHoSo_DienThoai",
        "desc": "Số điện thoại DI ĐỘNG của cơ sở / người đại diện — Đơn đề nghị 'Số điện thoại liên hệ' phần 'Di "
                "động'. Chỉ chữ số. KHÔNG lấy số máy bàn (024…, 028…) ở GCN đăng ký doanh nghiệp / Mẫu 11.",
    },
    {
        "name": "ChuHoSo_Email",
        "desc": "Email của cơ sở — GCN đăng ký doanh nghiệp mục 'Địa chỉ trụ sở chính' → 'Email', hoặc Tài liệu kỹ "
                "thuật 'Điện thoại / Fax / Email'. Trống thì bỏ.",
    },
    {
        "name": "ChuHoSo_Fax",
        "desc": "Số Fax của cơ sở — GCN đăng ký doanh nghiệp 'Fax' → Mẫu 11 'Fax' → Tài liệu kỹ thuật. Trống thì bỏ.",
    },
    {
        "name": "CoSo_Ten",
        "desc": "Tên cơ sở đề nghị cấp — Đơn 'Tên cơ sở' / GCN đăng ký doanh nghiệp 'Tên công ty viết bằng tiếng "
                "Việt' (vd 'CÔNG TY TNHH …', 'NHÀ THUỐC …').",
    },
    {
        "name": "CoSo_MaSoDoanhNghiep",
        "desc": "Mã số doanh nghiệp / mã số hộ kinh doanh của cơ sở (GCN đăng ký doanh nghiệp). Chỉ chữ số.",
    },
    {
        "name": "CoSo_LoaiHinh",
        "desc": "Loại hình cơ sở kinh doanh ghi ở Đơn ('+ Loại hình cơ sở kinh doanh:'), vd 'Cơ sở bán buôn thuốc, "
                "nguyên liệu làm thuốc', 'Nhà thuốc', 'Quầy thuốc'. Chép nguyên văn.",
    },
    {
        "name": "CoSo_DiaDiemKinhDoanh",
        "desc": "Địa chỉ ĐỊA ĐIỂM KINH DOANH (kho / nhà thuốc) ghi ở Đơn ('Địa chỉ địa điểm kinh doanh' / '+ Địa điểm "
                "kinh doanh'), chuỗi đầy đủ. KHÔNG lấy địa chỉ trụ sở chính.",
    },
]
# === NGƯỜI NỘP — chỉ trích khi hồ sơ CÓ CCCD khớp tài khoản đăng nhập (xem <nguoi_nop_context>). ===
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({
        "name": f"NguoiNop_{_name}",
        "desc": _tmpl.format(who="NGƯỜI NỘP (tài khoản đăng nhập)", src="CCCD của NGƯỜI NỘP"),
    })

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _p in ("ChuHoSo_", "NguoiNop_"):
    COMPACT_COMP_BY_NAME[f"{_p}NgaySinh"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_p}NgayCap"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_p}ThuongTru"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Tên lấy từ HTML thật (file mapping). data[chonDoiTuong] khoá "Cá
# nhân" và các ô tổ chức ẩn → KHÔNG khai. data[fullname]/data[identityNumber] khoá theo tài khoản: mapper chỉ phát ở
# chế độ "Lấy người nộp theo tờ khai" (kèm enableInput).
UI_COMP_BY_NAME = {
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

    # LUÔN bỏ tích để mở + ghi đè Phần II.
    "data[isOwnerDossierCheck]": "dom-checkbox",

    # Phần II — CHỦ HỒ SƠ.
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
    "data[ghiChu]": "dom-input",
}
