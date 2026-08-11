"""Compact schema cho "Cấp văn bản chấp thuận đóng mới, cải hoán, thuê, mua tàu cá Việt Nam" (cổng
Nông nghiệp & Môi trường — Form.io). Field-key nhân thân data[...] TRÙNG KHÍT #92/#101.

Nhóm field:
- NguoiDeNghi_* / NguoiNop_* : nhân thân (như #92 — 2 vai, tự nộp/nộp thay qua formContext).
- ToKhai_*   : nội dung tờ khai Mẫu 12 (kính gửi, địa danh, loại giấy tờ, cơ quan cấp).
- DongMoi_*  : thông số tàu trường hợp ĐÓNG MỚI (vật liệu vỏ, nghề, vùng hoạt động).
- CaiHoan_*  : thông số tàu trường hợp CẢI HOÁN/THUÊ/MUA (kích thước, chiều chìm, công suất, vật liệu,
               nghề, vùng, nội dung cải hoán). LOẠI TRỪ với DongMoi_* — Tờ khai chỉ khai 1 trong 2.
"""

# --- Nhân thân (dùng chung template cho NguoiDeNghi_ và NguoiNop_) ---
_PERSON_FIELDS = [
    ("HoTen", "Họ và tên {who}. Lấy từ {src}. Ghi IN HOA đúng như trên giấy tờ."),
    ("NgaySinh", "Ngày sinh {who}, dd/mm/yyyy — CCCD."),
    ("GioiTinh", 'Giới tính {who}: "Nam" hoặc "Nữ" — CCCD.'),
    ("SoDinhDanh", "Số CCCD/CMND/căn cước/định danh cá nhân {who}. Đọc CCCD (mặt trước/MRZ) hoặc Tờ khai "
        "Mẫu 12 mục 'Mã định danh'. Chỉ chữ số. Ưu tiên số 12 chữ số (CCCD/căn cước/định danh) hơn số 9 "
        "chữ số (CMND) nếu có cả hai."),
    ("NgayCap", "Ngày cấp CCCD/CMND {who} (mặt sau CCCD) hoặc Tờ khai Mẫu 12 'ngày cấp', dd/mm/yyyy."),
    ("NoiCap", 'Nơi cấp/cơ quan cấp giấy tờ {who}. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ '
        'XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → '
        '"Bộ Công an". CCCD gắn chip không in nhãn "Nơi cấp" riêng → lấy ở Tờ khai Mẫu 12 (mục Cơ quan cấp).'),
    ("ThuongTru", "NƠI THƯỜNG TRÚ {who}, object {{quocGia,tinh,xa,diaChi}}. Lấy ở CCCD (Nơi thường trú) / "
        "Tờ khai Mẫu 12 (Địa chỉ thường trú). tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/khóm/"
        "ấp/thôn/tổ (KHÔNG kèm phường/xã/tỉnh)."),
    ("DienThoai", "Số điện thoại DI ĐỘNG {who}. Chỉ chữ số; KHÔNG lấy số bàn. Thường không có trên giấy tờ."),
    ("Email", "Email liên hệ {who} nếu giấy tờ có; thường không có → bỏ."),
]

_DENGHI_SRC = "CCCD / Tờ khai Mẫu 12 của NGƯỜI ĐỀ NGHỊ (chủ tàu/cá nhân đề nghị)"

FIELDS: list[dict] = []
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({
        "name": f"NguoiDeNghi_{_name}",
        "desc": _tmpl.format(who="NGƯỜI ĐỀ NGHỊ (chủ tàu/cá nhân, tổ chức đề nghị)", src=_DENGHI_SRC),
    })
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({
        "name": f"NguoiNop_{_name}",
        "desc": _tmpl.format(who="NGƯỜI NỘP (chỉ khi nộp thay & có CCCD người nộp)", src="CCCD của NGƯỜI NỘP"),
    })

# --- Nội dung tờ khai Mẫu 12 ---
FIELDS += [
    {"name": "ToKhai_KinhGui", "desc": "Nơi nhận tờ khai — mục 'Kính gửi' của Tờ khai Mẫu 12 (thường là "
        "UBND tỉnh/Sở Nông nghiệp và Môi trường …). Chép nguyên văn."},
    {"name": "ToKhai_DiaDanh", "desc": "Địa danh nơi lập tờ khai — phần '……, ngày … tháng … năm …' đầu/"
        "cuối Tờ khai Mẫu 12 (tên tỉnh/thành phố). Chỉ lấy tên địa danh (vd 'Tỉnh Cà Mau')."},
    {"name": "ToKhai_LoaiGiayTo", "desc": "Loại giấy tờ tùy thân ghi ở Tờ khai Mẫu 12 mục 'Loại giấy tờ' "
        "(vd 'Thẻ Căn cước công dân' / 'CCCD gắn chip' / 'Hộ chiếu'). Nếu tờ khai không ghi mà có số định "
        "danh 12 chữ số → 'Thẻ Căn cước công dân'."},
    {"name": "ToKhai_CoQuanCap", "desc": "Cơ quan cấp giấy tờ tùy thân ghi ở Tờ khai Mẫu 12 mục 'Cơ quan "
        "cấp'. Chuẩn hóa như NoiCap."},
]

# --- Thông số tàu: ĐÓNG MỚI ---
FIELDS += [
    {"name": "DongMoi_VatLieuVo", "desc": "CHỈ khi Tờ khai khai TRƯỜNG HỢP ĐÓNG MỚI: vật liệu vỏ tàu đóng "
        "mới (vd Gỗ / Composite / Thép). Lấy ở khối 'Trường hợp đóng mới tàu cá'."},
    {"name": "DongMoi_NgheKhaiThac", "desc": "CHỈ khi ĐÓNG MỚI: nghề khai thác thủy sản (vd Lưới rê, Lưới "
        "kéo, Câu). Khối 'Trường hợp đóng mới tàu cá'."},
    {"name": "DongMoi_VungHoatDong", "desc": "CHỈ khi ĐÓNG MỚI: vùng hoạt động (vd Vùng khơi / Vùng lộng / "
        "Vùng ven bờ). Khối 'Trường hợp đóng mới tàu cá'."},
]

# --- Thông số tàu: CẢI HOÁN / THUÊ / MUA ---
FIELDS += [
    {"name": "CaiHoan_KichThuoc", "desc": "CHỈ khi Tờ khai khai TRƯỜNG HỢP CẢI HOÁN/THUÊ/MUA: kích thước "
        "chính Lmax x Bmax x D (đơn vị m), chép nguyên dạng vd '15 x 4.5 x 1.8'. Khối 'Trường hợp cải "
        "hoán/thuê/mua tàu cá'."},
    {"name": "CaiHoan_ChieuChim", "desc": "CHỈ khi CẢI HOÁN/THUÊ/MUA: chiều chìm d (m), chỉ SỐ (vd '1.8')."},
    {"name": "CaiHoan_CongSuat", "desc": "CHỈ khi CẢI HOÁN/THUÊ/MUA: công suất máy (kW), chỉ SỐ (vd '165')."},
    {"name": "CaiHoan_VatLieuVo", "desc": "CHỈ khi CẢI HOÁN/THUÊ/MUA: vật liệu vỏ tàu (Gỗ/Composite/Thép)."},
    {"name": "CaiHoan_NgheKhaiThac", "desc": "CHỈ khi CẢI HOÁN/THUÊ/MUA: nghề khai thác thủy sản."},
    {"name": "CaiHoan_VungHoatDong", "desc": "CHỈ khi CẢI HOÁN/THUÊ/MUA: vùng hoạt động."},
    {"name": "CaiHoan_NoiDung", "desc": "CHỈ khi CẢI HOÁN: nội dung đề nghị cải hoán (mô tả chi tiết sửa "
        "đổi vd 'Cải hoán hầm bảo quản'). Khối 'Nội dung đề nghị cải hoán'. Thuê/mua có thể bỏ trống."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _p in ("NguoiDeNghi_", "NguoiNop_"):
    COMPACT_COMP_BY_NAME[f"{_p}NgaySinh"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_p}NgayCap"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_p}ThuongTru"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Tên lấy CHUẨN từ HTML thật.
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

    # BỎ TÍCH khi nộp thay. Tự nộp → không emit (giữ tích mặc định).
    "data[isOwnerDossierCheck]": "dom-checkbox",

    # Phần 2 — CHỦ HỒ SƠ (= người đề nghị). Chỉ điền khi nộp thay.
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

    # Phần 3 — NỘI DUNG TỜ KHAI (occurrence=1 cho các key trùng Phần 1).
    "data[kinhgui]": "dom-input",
    "data[diaDanh]": "dom-select",
    "data[loaiGT]": "dom-input",
    "data[tenCQ]": "dom-input",
    "data[ngayBC]": "dom-date",

    # Phần 4 — ĐÓNG MỚI.
    "data[vatLieuVo]": "dom-input",
    "data[ngheKhaiThac]": "dom-input",
    "data[vungHoatDong]": "dom-input",

    # Phần 5 — CẢI HOÁN/THUÊ/MUA.
    "data[kichThuocChinh]": "dom-input",
    "data[chieuChim]": "dom-input",
    "data[congSuat]": "dom-input",
    "data[vatLieuVo1]": "dom-input",
    "data[ngheKhaiThac1]": "dom-input",
    "data[vungHoatDong1]": "dom-input",
    "data[noiDungCaiHoan]": "dom-input",

    # Phần 6 — CAM KẾT.
    "data[chuCS]": "dom-input",
}
