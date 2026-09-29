"""Compact schema cho "Cấp mới giấy phép hoạt động cơ sở khám bệnh, chữa bệnh" (cổng Bộ Y tế — Form.io).
Field-key data[...] TRÙNG KHÍT dieu_chinh_giay_phep_hanh_nghe_chuyen_tiep (sheet mapping 1.012278).

HAI vai (thường trùng, nhưng có thể NỘP THAY):
- CHỦ HỒ SƠ (ChuHoSo_*) = người đại diện cơ sở đề nghị (chủ hộ kinh doanh / người đại diện theo pháp luật)
  → Phần II data[owner*].
- NGƯỜI NỘP (NguoiNop_*) = người đứng nộp trên cổng (tài khoản VNeID) → Phần I data[fullname...]. Tự nộp
  → TRÙNG chủ hồ sơ. Nộp thay → KHÁC, chỉ trích khi hồ sơ CÓ CCCD người nộp.

Thông tin cơ sở (CoSo_*) + trường hợp đề nghị (HoSo_*) không có ô riêng → mapper ghép thành data[ghiChu].
"""

_PERSON_FIELDS = [
    ("HoTen", "Họ và tên {who}. Lấy từ {src}. Ghi IN HOA đúng như trên giấy tờ; KHÔNG kèm học vị/chức danh "
        "(ThS., BS., TS.BS…)."),
    ("NgaySinh", "Ngày sinh {who}, dd/mm/yyyy — {src}. Giấy chỉ ghi năm sinh thì không dùng."),
    ("GioiTinh", 'Giới tính {who}: "Nam" hoặc "Nữ" — CCCD / GCN đăng ký hộ kinh doanh ô "Giới tính". Không có '
        'ô giới tính thì suy từ danh xưng "Ông"/"Bà" trên văn bằng, chứng chỉ, quyết định; KHÔNG suy từ tên.'),
    ("SoDinhDanh", "Số CCCD/căn cước/định danh cá nhân {who}, 12 chữ số — CCCD, GCN đăng ký hộ kinh doanh "
        "('Số định danh cá nhân'), giấy xác nhận quá trình hành nghề ('Căn cước công dân số'). Chỉ chữ số. "
        "KHÔNG lấy số CMND 9 chữ số in trên chứng chỉ hành nghề cũ; KHÔNG lấy mã số doanh nghiệp."),
    ("NgayCap", "Ngày cấp CCCD/căn cước {who}, dd/mm/yyyy — CCCD hoặc giấy xác nhận quá trình hành nghề 'Ngày "
        "cấp'. KHÔNG lấy 'Ngày cấp' của CMND cũ in trên chứng chỉ hành nghề."),
    ("NoiCap", 'Nơi cấp CCCD/căn cước {who} — CCCD hoặc giấy xác nhận quá trình hành nghề "Nơi cấp". "CỤC '
        'TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật '
        'tự xã hội"; "BỘ CÔNG AN" → "Bộ Công an". KHÔNG lấy nơi cấp CMND cũ in trên chứng chỉ hành nghề.'),
    ("ThuongTru", "NƠI CƯ TRÚ của CÁ NHÂN {who}, object {{quocGia,tinh,xa,diaChi}}. Lấy ở CCCD (Nơi cư trú) → "
        "GCN đăng ký hộ kinh doanh mục chủ hộ 'Nơi thường trú' → giấy xác nhận quá trình hành nghề 'Địa chỉ "
        "cư trú'. tinh='Tỉnh/Thành phố …' (viết đầy đủ), xa='Phường/Xã/Đặc khu …', diaChi=số nhà/đường/tổ/thôn "
        "(KHÔNG kèm phường/xã/tỉnh). ⚠ KHÔNG lấy địa chỉ CƠ SỞ (Đơn 'Địa chỉ', GCN 'Trụ sở') và KHÔNG lấy "
        "địa chỉ trên chứng chỉ hành nghề / văn bằng (địa chỉ cũ)."),
    ("DienThoai", "Số điện thoại DI ĐỘNG {who} — Đơn đề nghị 'Điện thoại' / GCN đăng ký hộ kinh doanh 'Điện "
        "thoại' / Bản kê khai Mẫu 08. Chỉ chữ số; KHÔNG lấy số bàn."),
    ("Email", "Email {who} — GCN đăng ký hộ kinh doanh 'Thư điện tử' / Bản kê khai 'Email'. Ô để trống / "
        "chấm chấm thì bỏ."),
]

_CHU_SRC = "CCCD / GCN đăng ký hộ kinh doanh (chủ hộ) / giấy xác nhận quá trình hành nghề / chứng chỉ hành nghề"

FIELDS: list[dict] = []
# === CHỦ HỒ SƠ = người đại diện cơ sở đề nghị (người chính) ===
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({
        "name": f"ChuHoSo_{_name}",
        "desc": _tmpl.format(who="CHỦ HỒ SƠ (người đại diện cơ sở đề nghị)", src=_CHU_SRC),
    })
# === NGƯỜI NỘP (Phần I khi NỘP THAY) — chỉ trích khi hồ sơ CÓ CCCD người nộp riêng. ===
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({
        "name": f"NguoiNop_{_name}",
        "desc": _tmpl.format(who="NGƯỜI NỘP (chỉ khi nộp thay & có CCCD người nộp)", src="CCCD của NGƯỜI NỘP"),
    })
# === Thông tin cơ sở + trường hợp đề nghị trên Đơn Mẫu 02 → data[ghiChu] ===
FIELDS += [
    {"name": "HoSo_TruongHopDeNghi", "desc": 'Đơn Mẫu 02 mục "Trường hợp đề nghị", viết gọn, chuẩn chính tả, '
        'vd "Cấp mới giấy phép hoạt động cơ sở khám bệnh, chữa bệnh".'},
    {"name": "CoSo_Ten", "desc": 'Tên CƠ SỞ khám bệnh, chữa bệnh — Đơn Mẫu 02 "Tên cơ sở đề nghị" (hoặc Danh sách '
        'đăng ký hành nghề mục 1). Giữ nguyên cách viết hoa trên đơn.'},
    {"name": "CoSo_DiaChi", "desc": 'Địa chỉ CƠ SỞ — Đơn Mẫu 02 "Địa chỉ" (hoặc GCN đăng ký "Trụ sở"), một chuỗi '
        'đầy đủ số nhà, đường, phường/xã, tỉnh/thành phố.'},
    {"name": "CoSo_DienThoai", "desc": 'Điện thoại CƠ SỞ — Đơn Mẫu 02 "Điện thoại". Chỉ chữ số.'},
    {"name": "CoSo_HinhThucToChuc", "desc": 'Đơn Mẫu 02 "Hình thức tổ chức đề nghị cấp phép", vd "Phòng khám '
        'chuyên khoa Nội".'},
    {"name": "CoSo_ThoiGianLamViec", "desc": 'Đơn Mẫu 02 "Thời gian làm việc hằng ngày", viết gọn một dòng, các '
        'nhóm ngày ngăn cách "; ", vd "Thứ 2 đến thứ 6: sáng 7 giờ–11 giờ, chiều 13 giờ–17 giờ; Thứ 7, Chủ nhật: '
        'nghỉ". Viết "giờ" đầy đủ thay cho "g".'},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _p in ("ChuHoSo_", "NguoiNop_"):
    COMPACT_COMP_BY_NAME[f"{_p}NgaySinh"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_p}NgayCap"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_p}ThuongTru"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Tên lấy từ HTML thật (sheet mapping). Mỗi key 1×.
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

    # Tự nộp → True (cổng để trống mặc định), nộp thay → False. Engine tick SAU cùng nên cổng nhân bản
    # Phần 1 đã điền sang Phần 2.
    "data[isOwnerDossierCheck]": "dom-checkbox",

    # Phần 2 — CHỦ HỒ SƠ (= người đại diện cơ sở). CHỈ điền khi nộp thay.
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
