"""Compact schema cho "Cấp lại, điều chỉnh GCN đủ điều kiện kinh doanh dược (Sở Y tế)" — cổng Bộ Y tế
(Form.io). Field-key data[...] TRÙNG KHÍT cap_chung_chi_hanh_nghe_duoc / cong_bo_du_dk_tiem_chung, thêm
data[fax]/data[ownerFax] (không có nguồn → không điền) và data[ghiChu].

HAI vai:
- CHỦ HỒ SƠ (ChuHoSo_*) = chủ hộ kinh doanh / người đại diện theo pháp luật của cơ sở kinh doanh dược.
- NGƯỜI NỘP (NguoiNop_*) = tài khoản đăng nhập; chỉ trích khi hồ sơ có CCCD KHỚP tài khoản (xem
  <nguoi_nop_context> do runner dựng).

Mỗi data[key] xuất hiện 1 lần → KHÔNG occurrence.
"""

_PERSON_FIELDS = [
    ("HoTen", "Họ và tên {who}. Lấy từ {src}. Ghi đúng như giấy tờ, BỎ tiền tố trình độ/chức danh "
        '("DSĐH.", "DS.", "Dược sĩ", "BS."...).'),
    ("NgaySinh", "Ngày sinh {who}, dd/mm/yyyy — {src}."),
    ("GioiTinh", 'Giới tính {who}: "Nam" hoặc "Nữ" — {src}.'),
    ("SoDinhDanh", "Số CCCD/căn cước/số định danh cá nhân {who} (12 chữ số; CMND cũ 9 chữ số) — {src}. Chỉ "
        "chữ số."),
    ("NgayCap", "Ngày cấp CCCD/căn cước {who} (mặt sau CCCD / 'Ngày, tháng, năm cấp'), dd/mm/yyyy. CHỈ lấy "
        "trên thẻ CCCD — KHÔNG lấy 'Năm cấp'/'Ngày cấp' của Chứng chỉ hành nghề dược ghi trong Đơn."),
    ("NoiCap", 'Nơi cấp CCCD/căn cước {who}. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → '
        '"Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới → "Bộ Công an". KHÔNG lấy '
        '"Nơi cấp: Sở Y tế ..." của Chứng chỉ hành nghề dược ghi trong Đơn.'),
    ("ThuongTru", "NƠI THƯỜNG TRÚ / nơi cư trú CÁ NHÂN {who}, object {{quocGia,tinh,xa,diaChi}} — {src}. "
        "tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường/tổ/thôn (KHÔNG kèm phường/xã/tỉnh)."),
]

_CHU_SRC = (
    "CCCD của chủ cơ sở → Đơn đề nghị (người ký 'NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT' / 'Người phụ trách chuyên "
    "môn') → GCN đăng ký hộ kinh doanh mục 'Thông tin về chủ hộ kinh doanh' (hoặc GCN đăng ký doanh nghiệp "
    "mục 'Người đại diện theo pháp luật') → GCN đạt GPP"
)

FIELDS: list[dict] = []
# === CHỦ HỒ SƠ = chủ cơ sở kinh doanh dược ===
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({
        "name": f"ChuHoSo_{_name}",
        "desc": _tmpl.format(who="CHỦ HỒ SƠ (chủ hộ kinh doanh / người đại diện theo pháp luật của cơ sở)",
                             src=_CHU_SRC),
    })
FIELDS += [
    {
        "name": "ChuHoSo_DienThoai",
        "desc": "Số điện thoại DI ĐỘNG của cơ sở / chủ hồ sơ — Đơn đề nghị 'Số điện thoại liên hệ' hoặc GCN "
                "ĐKHKD mục 'Trụ sở' → 'Điện thoại'. Chỉ chữ số, KHÔNG lấy số bàn.",
    },
    {
        "name": "ChuHoSo_Email",
        "desc": "Email của cơ sở / chủ hồ sơ nếu Đơn hoặc GCN ĐKHKD ('Thư điện tử') có ghi. Trống thì bỏ.",
    },
    {
        "name": "NoiDungDeNghi",
        "desc": "Đơn Mẫu 12 (điều chỉnh): chép NGUYÊN VĂN mục 'Nội dung xin điều chỉnh' (bỏ nhãn). Đơn Mẫu 11 "
                "(cấp lại): chép 'Lý do đề nghị cấp lại'. Không có thì bỏ.",
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

# ---- UI Form.io fields (data[...]) — comp dom-*. Tên lấy từ HTML thật (file mapping). Ô khoá theo tài
# khoản (data[chonDoiTuong]/data[fullname]/data[identityNumber]) KHÔNG khai → mapper không thể phát nhầm.
UI_COMP_BY_NAME = {
    # Phần I — NGƯỜI NỘP HỒ SƠ.
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
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
    "data[ownerNation]": "dom-select",
    "data[ghiChu]": "dom-input",
}
