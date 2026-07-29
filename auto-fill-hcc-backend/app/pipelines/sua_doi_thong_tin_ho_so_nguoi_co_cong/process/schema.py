"""Compact schema cho "Sửa đổi, bổ sung thông tin cá nhân trong hồ sơ người có công"
(cổng Bộ Nội vụ — Form.io).

HAI vai (có thể NỘP THAY — như giai_quyet / di_chuyen):
- NGƯỜI KHAI ĐƠN (NguoiKhai_*) = chủ hồ sơ = người đứng đơn Mẫu 26 đề nghị sửa hồ sơ → Phần II owner +
  Phần IV occ1. Đây là đối tượng chính.
- NGƯỜI NỘP (NguoiNop_*) = người đứng nộp trên cổng → Phần I occ0. Tự nộp → trùng người khai.
Người có công (liệt sĩ) chỉ ở text đơn: tenHSncc/ThuocDienNcc/ThongTinHs/ThongTinSdBs.

Cấu trúc form (field-key lấy CHUẨN từ HTML thật):
  Phần I  Người nộp   → occurrence 0 các key dùng chung (Form.io editable — CÓ điền).
  Phần II Chủ hồ sơ   → data[owner*]. BỎ TÍCH data[isOwnerDossierCheck] để mở + điền (như giai_quyet).
  Phần III            → data[ghiChu], data[hoSoDinhKem][0][textField1/2] (để trống).
  Phần IV Nội dung đơn (Mẫu 26) → key dùng chung ở OCCURRENCE 1 + identityAgency/province1/district1/
                        address1 (QUÊ QUÁN) + kinhgui/tenHSncc/ThuocDienNcc/ThongTinHs/ThongTinSdBs.
      Lưu ý: province/district/address occ0 (Phần I) VÀ occ1 (Phần IV) đều = NƠI THƯỜNG TRÚ; province1/
      district1/address1 = QUÊ QUÁN (KHÁC di_chuyen — nơi occ1 là quê quán).
"""

FIELDS: list[dict] = [
    # === NGƯỜI KHAI ĐƠN = người nộp = chủ hồ sơ (thân nhân đứng đơn đề nghị sửa) ===
    {"name": "NguoiKhai_HoTen", "desc": "Họ và tên NGƯỜI KHAI ĐƠN (người đứng đơn đề nghị sửa hồ sơ, ký tên "
        "'Người khai'). Lấy từ CCCD / Đơn đề nghị Mẫu số 26 / Bản khai. Ghi IN HOA như trên giấy tờ. "
        "KHÔNG lấy tên của người có công/liệt sĩ (người được sửa hồ sơ) vào đây."},
    {"name": "NguoiKhai_NgaySinh", "desc": "Ngày sinh người khai đơn, dd/mm/yyyy — CCCD / Đơn Mẫu 26 / Bản khai."},
    {"name": "NguoiKhai_GioiTinh", "desc": 'Giới tính người khai đơn: "Nam" hoặc "Nữ".'},
    {"name": "NguoiKhai_SoDinhDanh", "desc": "Số CCCD/CMND người khai đơn; đọc CCCD (mặt trước/MRZ) hoặc Đơn/Bản "
        "khai. Chỉ chữ số."},
    {"name": "NguoiKhai_NgayCap", "desc": "Ngày cấp CCCD/CMND người khai (mặt sau CCCD) hoặc Đơn/Bản khai, dd/mm/yyyy."},
    {"name": "NguoiKhai_NoiCap",
     "desc": 'Nơi cấp CCCD/CMND người khai. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" '
             '→ "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → '
             '"Bộ Công an". CCCD gắn chip không in nhãn "Nơi cấp" riêng → ưu tiên lấy ở Đơn/Bản khai.'},
    {"name": "NguoiKhai_ThuongTru",
     "desc": "NƠI THƯỜNG TRÚ người khai, object {quocGia,tinh,xa,diaChi}. Ưu tiên Đơn Mẫu 26/Bản khai (lập gần "
             "đây, ghi địa giới MỚI sau sáp nhập); CCCD cũ có thể ghi tên CŨ. tinh='Tỉnh/Thành phố …', "
             "xa=phường/xã (tên MỚI nếu biết), diaChi=số nhà/đường/tổ dân phố/thôn (KHÔNG kèm xã/huyện/tỉnh)."},
    {"name": "NguoiKhai_QueQuan",
     "desc": "QUÊ QUÁN người khai (KHÁC nơi thường trú), object {quocGia,tinh,xa,diaChi}. Lấy ở CCCD (Quê quán/"
             "Place of origin) / Đơn Mẫu 26 / Bản khai. Quê quán giữ tên địa danh gốc theo giấy tờ."},
    {"name": "NguoiKhai_DienThoai", "desc": "Số điện thoại người khai — Đơn Mẫu 26 / Bản khai (CCCD không có). "
        "Chỉ chữ số; không lấy số điện thoại bàn."},
    {"name": "NguoiKhai_Email", "desc": "Email người khai nếu giấy tờ có (thường không có → bỏ)."},

    # === NỘI DUNG ĐƠN ĐỀ NGHỊ (Mẫu số 26) — về việc sửa hồ sơ NGƯỜI CÓ CÔNG (liệt sĩ/thương binh) ===
    {"name": "Don_KinhGui", "desc": "Nơi nhận đơn (dòng 'Kính gửi') — thường là Sở Nội vụ Tỉnh/Thành phố. "
        "Lấy ở Đơn Mẫu 26 / Tờ trình. Chép nguyên văn."},
    {"name": "Don_TenHoSoNCC", "desc": "Tên hồ sơ người có công cần sửa — theo tiêu đề Đơn 'Sửa đổi, bổ sung "
        "thông tin trong hồ sơ …' hoặc Tờ trình. Vd 'Hồ sơ liệt sĩ Huỳnh Kim Khoa', 'Hồ sơ thương binh …'. "
        "Ghép 'Hồ sơ <loại NCC> <họ tên người có công>'."},
    {"name": "Don_ThuocDienNCC", "desc": "Người khai thuộc diện người có công nào / quan hệ với người có công — "
        "dòng 'Thuộc diện người có công' của Đơn hoặc 'Mối quan hệ với liệt sĩ' của Bản khai. Vd 'Con đẻ của "
        "liệt sĩ Huỳnh Kim Khoa'. Chép nguyên văn."},
    {"name": "Don_ThongTinHienTai", "desc": "THÔNG TIN ĐANG GHI trong hồ sơ (thông tin HIỆN TẠI, có thể sai) — "
        "dòng 'Thông tin đang ghi trong hồ sơ' của Đơn Mẫu 26 / Công văn Sở Nội vụ. Chép NGUYÊN VĂN toàn bộ, "
        "giữ nguyên tên/năm sinh liệt kê, không tóm tắt."},
    {"name": "Don_ThongTinDeNghiSua", "desc": "THÔNG TIN ĐỀ NGHỊ SỬA ĐỔI, BỔ SUNG (thông tin ĐÚNG) — dòng "
        "'Thông tin đề nghị sửa đổi, bổ sung' của Đơn Mẫu 26. Chép NGUYÊN VĂN toàn bộ, không tóm tắt."},

    # === NGƯỜI NỘP HỒ SƠ (Phần I) — khi NỘP THAY thì KHÁC người khai đơn. Chỉ trích khi hồ sơ CÓ CCCD
    # người nộp (xem <nguoi_nop_context>). Tự nộp → để trống, mapper tự lấy người khai cho Phần I. ===
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI NỘP (chỉ khi nộp thay & có CCCD người nộp). IN HOA."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh NGƯỜI NỘP, dd/mm/yyyy — CCCD người nộp."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính NGƯỜI NỘP: "Nam"/"Nữ" — CCCD người nộp.'},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND NGƯỜI NỘP — CCCD người nộp. Chỉ chữ số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD/CMND NGƯỜI NỘP, dd/mm/yyyy."},
    {"name": "NguoiNop_NoiCap", "desc": "Nơi cấp CCCD/CMND NGƯỜI NỘP. Chuẩn hóa như NguoiKhai_NoiCap."},
    {"name": "NguoiNop_ThuongTru",
     "desc": "Nơi thường trú NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi} — CCCD người nộp. KHÁC người khai."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại NGƯỜI NỘP nếu giấy tờ có."},
    {"name": "NguoiNop_Email", "desc": "Email NGƯỜI NỘP nếu có."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("NguoiKhai_NgaySinh", "NguoiKhai_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("NguoiKhai_ThuongTru", "NguoiKhai_QueQuan", "NguoiNop_ThuongTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Tên lấy CHUẨN từ HTML thật ----
# Key dùng chung Phần I ↔ Phần IV (xuất hiện 2× trong DOM) → mapper phân biệt bằng occurrence 0/1.
UI_COMP_BY_NAME = {
    # Phần I — NGƯỜI NỘP HỒ SƠ (occurrence 0). Form.io editable → CÓ điền.
    "data[chonDoiTuong]": "dom-select",   # "Cá nhân".
    "data[idIssuePlace]": "dom-input",    # Nơi cấp (Phần I, key riêng — 1×).
    "data[email]": "dom-input",

    # BỎ TÍCH ô này để mở Phần II + chủ hồ sơ (= người khai đơn).
    "data[isOwnerDossierCheck]": "dom-checkbox",
    "data[chonDoiTuong1]": "dom-select",

    # Phần II — chủ hồ sơ = NGƯỜI KHAI ĐƠN.
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

    # Phần IV Mục — nội dung đơn. Key RIÊNG (1×):
    "data[identityAgency]": "dom-input",  # Nơi cấp (Phần IV) — KHÔNG đồng bộ idIssuePlace.
    "data[province1]": "dom-select",      # QUÊ QUÁN tỉnh.
    "data[district1]": "dom-select",      # QUÊ QUÁN phường/xã.
    "data[address1]": "dom-input",        # QUÊ QUÁN chi tiết.
    "data[kinhgui]": "dom-input",
    "data[tenHSncc]": "dom-input",
    "data[ThuocDienNcc]": "dom-input",    # textarea → dom-input (engine set value giống input).
    "data[ThongTinHs]": "dom-input",
    "data[ThongTinSdBs]": "dom-input",

    # Key DÙNG CHUNG Phần I (occ 0) ↔ Phần IV (occ 1) — cùng người, cùng giá trị:
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[phoneNumber]": "dom-input",
    "data[province]": "dom-select",   # Nơi thường trú tỉnh.
    "data[district]": "dom-select",   # Nơi thường trú phường/xã.
    "data[address]": "dom-input",     # Nơi thường trú chi tiết.
}
