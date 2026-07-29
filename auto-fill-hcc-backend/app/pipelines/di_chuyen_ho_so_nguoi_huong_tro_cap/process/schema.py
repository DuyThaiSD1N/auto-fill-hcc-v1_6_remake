"""Compact schema cho "Di chuyển hồ sơ khi người hưởng trợ cấp ưu đãi thay đổi nơi thường trú"
(cổng Bộ Nội vụ — Form.io).

HAI vai (có thể nộp thay):
- NGƯỜI HƯỞNG TRỢ CẤP (NguoiHuong_*) = chủ hồ sơ = người làm đơn Mẫu 27 → Phần II owner + Phần III occ1.
- NGƯỜI NỘP (NguoiNop_*) = người đứng nộp trên cổng → Phần I occ0. Khi tự nộp thì trùng người hưởng.
Người có công gốc (liệt sĩ) chỉ ở text đơn: DcHsNcc + ThuocDienNcc.

Occurrence (verify HTML, 9 key xuất hiện 2×): occ0=Phần I, occ1=Phần III.
⚠️ province/district/address occ1 = QUÊ QUÁN; province1/district1/address1 = NƠI THƯỜNG TRÚ (Phần III).
"""

FIELDS: list[dict] = [
    # === NGƯỜI HƯỞNG TRỢ CẤP = chủ hồ sơ = người làm đơn Mẫu 27 (đối tượng chính) ===
    {"name": "NguoiHuong_HoTen", "desc": "Họ và tên NGƯỜI HƯỞNG TRỢ CẤP ưu đãi (người làm đơn Mẫu 27, ký "
        "'Người làm đơn', đề nghị di chuyển hồ sơ của chính mình). Lấy từ Đơn Mẫu 27 / CCCD / Bản khai. "
        "Ghi IN HOA như giấy tờ. KHÔNG lấy tên người có công gốc (liệt sĩ) vào đây."},
    {"name": "NguoiHuong_NgaySinh", "desc": "Ngày sinh người hưởng, dd/mm/yyyy — Đơn Mẫu 27 / CCCD / Bản khai."},
    {"name": "NguoiHuong_GioiTinh", "desc": 'Giới tính người hưởng: "Nam" hoặc "Nữ".'},
    {"name": "NguoiHuong_SoDinhDanh", "desc": "Số CCCD/CMND người hưởng; đọc CCCD (mặt trước/MRZ) hoặc Đơn/Bản "
        "khai. Chỉ chữ số."},
    {"name": "NguoiHuong_NgayCap", "desc": "Ngày cấp CCCD/CMND người hưởng (mặt sau CCCD) hoặc Đơn/Bản khai, dd/mm/yyyy."},
    {"name": "NguoiHuong_NoiCap",
     "desc": 'Nơi cấp CCCD/CMND người hưởng. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" '
             '→ "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → '
             '"Bộ Công an". CCCD gắn chip không in nhãn "Nơi cấp" riêng → ưu tiên lấy ở Đơn/Bản khai.'},
    {"name": "NguoiHuong_ThuongTru",
     "desc": "NƠI THƯỜNG TRÚ HIỆN NAY (nơi chuyển đến) của người hưởng, object {quocGia,tinh,xa,diaChi}. Ưu "
             "tiên Xác nhận cư trú CT07 / Đơn Mẫu 27 / CCCD (địa giới MỚI sau sáp nhập). tinh='Tỉnh/Thành phố …', "
             "xa=phường/xã, diaChi=số nhà/đường/khu phố/tổ (KHÔNG kèm tên phường/xã/huyện/tỉnh)."},
    {"name": "NguoiHuong_QueQuan",
     "desc": "QUÊ QUÁN người hưởng (KHÁC nơi thường trú), object {quocGia,tinh,xa,diaChi}. Lấy ở Đơn Mẫu 27 "
             "(Quê quán) / Giấy khai sinh (Nơi sinh). Giấy khai sinh có thể ghi địa danh CŨ trước sáp nhập; ưu "
             "tiên tên theo Đơn Mẫu 27 nếu có. tinh/xa/diaChi tách riêng."},
    {"name": "NguoiHuong_DienThoai", "desc": "Số điện thoại người hưởng — Đơn Mẫu 27 / Bản khai (CCCD không có). "
        "Chỉ chữ số; không lấy số điện thoại bàn."},
    {"name": "NguoiHuong_Email", "desc": "Email người hưởng nếu giấy tờ có (thường không có → bỏ)."},

    # === NỘI DUNG ĐƠN Mẫu 27 (về việc di chuyển hồ sơ người có công) ===
    {"name": "Don_TenHoSoNCC", "desc": "Tên loại hồ sơ người có công cần di chuyển — điền vào chỗ trống dòng "
        "tiêu đề 'Di chuyển hồ sơ …' của Đơn Mẫu 27, hoặc Phiếu báo di chuyển. Vd 'hồ sơ liệt sĩ', 'hồ sơ "
        "thương binh', 'hồ sơ bệnh binh'. Chỉ ghi cụm loại hồ sơ, viết thường."},
    {"name": "Don_ThuocDienNCC", "desc": "Người hưởng thuộc diện người có công nào / quan hệ với người có công — "
        "dòng 'Thuộc diện người có công' của Đơn Mẫu 27, hoặc 'Mối quan hệ với liệt sĩ' của Bản khai / cột "
        "'Quan hệ với liệt sĩ' của Giấy chứng nhận GĐ liệt sĩ. Vd 'Con ruột của Liệt sĩ Lê Kiệm'. Chép nguyên văn."},

    # === NGƯỜI NỘP HỒ SƠ (Phần I) — khi NỘP THAY thì KHÁC người hưởng. Chỉ trích khi hồ sơ CÓ CCCD người
    # nộp (xem <nguoi_nop_context>). Tự nộp → để trống, mapper tự lấy người hưởng cho Phần I. ===
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI NỘP (chỉ khi nộp thay & có CCCD người nộp). IN HOA."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh NGƯỜI NỘP, dd/mm/yyyy — CCCD người nộp."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính NGƯỜI NỘP: "Nam"/"Nữ" — CCCD người nộp.'},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND NGƯỜI NỘP — CCCD người nộp. Chỉ chữ số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD/CMND NGƯỜI NỘP, dd/mm/yyyy."},
    {"name": "NguoiNop_NoiCap", "desc": "Nơi cấp CCCD/CMND NGƯỜI NỘP. Chuẩn hóa như NguoiHuong_NoiCap."},
    {"name": "NguoiNop_ThuongTru",
     "desc": "Nơi thường trú NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi} — CCCD người nộp. KHÁC người hưởng."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại NGƯỜI NỘP nếu giấy tờ có."},
    {"name": "NguoiNop_Email", "desc": "Email NGƯỜI NỘP nếu có."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("NguoiHuong_NgaySinh", "NguoiHuong_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("NguoiHuong_ThuongTru", "NguoiHuong_QueQuan", "NguoiNop_ThuongTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Tên CHUẨN từ HTML thật ----
# Key dùng chung Phần I ↔ Phần III (2× trong DOM) → mapper phân biệt bằng occurrence 0/1.
UI_COMP_BY_NAME = {
    # Phần I — NGƯỜI NỘP (occurrence 0).
    "data[chonDoiTuong]": "dom-select",   # "Cá nhân".
    "data[idIssuePlace]": "dom-input",    # Nơi cấp Phần I (key riêng, 1×).

    # Mở khoá Phần II (BỎ TÍCH) + chủ hồ sơ.
    "data[isOwnerDossierCheck]": "dom-checkbox",
    "data[chonDoiTuong1]": "dom-select",
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
    "data[ownerNation]": "dom-select",

    # Phần III — Đơn Mẫu 27. Key RIÊNG (1×):
    "data[DcHsNcc]": "dom-input",         # Tên hồ sơ người có công di chuyển.
    "data[identityAgency]": "dom-input",  # Nơi cấp (Phần III) — KHÔNG đồng bộ idIssuePlace.
    "data[province1]": "dom-select",      # NƠI THƯỜNG TRÚ tỉnh (Phần III).
    "data[district1]": "dom-select",      # NƠI THƯỜNG TRÚ phường/xã.
    "data[address1]": "dom-input",        # NƠI THƯỜNG TRÚ chi tiết.
    "data[ThuocDienNcc]": "dom-input",

    # Key DÙNG CHUNG Phần I (occ 0 = người nộp) ↔ Phần III (occ 1 = người hưởng):
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[phoneNumber]": "dom-input",
    # ⚠️ province/district/address: occ0 = thường trú người nộp; occ1 = QUÊ QUÁN người hưởng.
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
}
