"""Compact schema cho "[Lâm Đồng] Giao đất, cho thuê đất, chuyển mục đích sử dụng đất …; giao đất và giao rừng; cho
thuê đất và cho thuê rừng, gia hạn sử dụng đất khi hết thời hạn sử dụng đất" (1.116366).

LLM CHỈ trả FACT nguồn: người từ CCCD / Đơn (Mẫu số 01 Phụ lục VI QĐ 40/2026/QĐ-UBND) / mục 6 Giấy chứng nhận / Giấy
ủy quyền, địa chỉ thửa đất từ Đơn / GCN / mảnh trích đo. `mapper.enrich` suy ra tất định các ô Form.io.

Form (file mapping "mapping_chuyen_muc_dich_su_dung_dat_Lam_Dong.xlsx") cùng khuôn ô với 1.116365 Lâm Đồng, 3 khối:
  Phần I   Người nộp  → data[fullname]..data[address], data[organization], data[ghiChu]
  Phần II  Thửa đất   → data[province2], data[village2] (CHỈ Tỉnh + Phường/Xã, không có ô số thửa / diện tích)
  Phần III Chủ hồ sơ  → data[ownerFullname]..data[ownerAddress]; tự nộp thì bấm nút "Người nộp là chủ hồ sơ"
KHÔNG có Phần IV chi tiết Giấy chứng nhận như 1.116365. Ô "Ghi chú" để người dân tự ghi (mapping: không lấy từ giấy tờ).
"""

FIELDS: list[dict] = [
    # --- NGƯỜI ĐƯỢC ỦY QUYỀN (điểm neo, TRÍCH ĐẦU TIÊN) — gộp 1 object để LLM khỏi phân tán/ngại điền.
    {"name": "NguoiDuocUyQuyen",
     "desc": "TRÍCH ĐẦU TIÊN. CHỈ điền khi hồ sơ có MỘT FILE RIÊNG tiêu đề 'GIẤY ỦY QUYỀN'/'HỢP ĐỒNG ỦY "
             "QUYỀN'/'VĂN BẢN ỦY QUYỀN' (có dòng 'ủy quyền cho' + số CCCD của bên B). Chép người đứng NGAY "
             "SAU 'ủy quyền cho:' (bên B) vào object: {\"hoTen\", \"ngaySinh\" (dd/mm/yyyy), \"gioiTinh\" "
             "('Nam'/'Nữ'), \"soDinhDanh\", \"ngayCapCccd\" (dd/mm/yyyy), \"noiCapCccd\", \"dienThoai\", "
             "\"thuongTru\":{\"quocGia\",\"tinh\",\"xa\",\"chiTietDuoiXa\"}}. BỎ TRỐNG object này nếu: KHÔNG có file "
             "ủy quyền (chữ 'Giấy ủy quyền' liệt kê trong mục 'Tài liệu gửi kèm' của Đơn KHÔNG tính); hoặc chỉ "
             "có CCCD rời; hoặc chỉ có người ĐỒNG KÝ Đơn / ĐỒNG SỬ DỤNG đất (vd vợ/chồng). Đừng bịa."},

    # --- CHỦ HỒ SƠ = NGƯỜI ĐỀ NGHỊ (người sử dụng đất đứng Đơn).
    {"name": "Nguoi_HoTen", "desc": "Họ tên CHỦ HỒ SƠ = mục '1. Người đề nghị' của Đơn (người làm đơn). Đối chiếu tên "
        "người sử dụng đất trên GCN — nếu đất đã sang tên thì tên chủ MỚI nằm ở mục 6 'Những thay đổi sau khi cấp Giấy "
        "chứng nhận' (vd 'Tặng cho bà …'), KHÔNG lấy người in sẵn ở trang 1. Không phải bên được ủy quyền."},
    {"name": "Nguoi_NgaySinh", "desc": "Ngày sinh chủ hồ sơ, dd/mm/yyyy — từ CCCD của đúng người này."},
    {"name": "Nguoi_GioiTinh", "desc": 'Giới tính chủ hồ sơ: "Nam" hoặc "Nữ" (từ CCCD).'},
    {"name": "Nguoi_SoDinhDanh", "desc": "Số CCCD/căn cước của chủ hồ sơ (mặt trước, MRZ mặt sau, hoặc dòng 'CCCD số' "
        "ở mục 6 GCN / Giấy ủy quyền)."},
    {"name": "Nguoi_NgayCapCccd", "desc": "Ngày cấp CCCD của chủ hồ sơ (mặt sau, dòng 'Ngày, tháng, năm'), dd/mm/yyyy."},
    {"name": "Nguoi_NoiCapCccd",
     "desc": 'Nơi cấp CCCD của chủ hồ sơ (mặt sau). "CỤC TRƯỞNG CỤC CẢNH SÁT..." → '
             '"Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → '
             '"Bộ Công an".'},
    {"name": "Nguoi_ThuongTru",
     "desc": "Nơi cư trú của CHỦ HỒ SƠ, object {quocGia,tinh,xa,chiTietDuoiXa}. Lấy mục '2. Địa chỉ/trụ sở chính' "
             "hoặc '3. Địa chỉ liên hệ' của Đơn, đối chiếu 'Nơi thường trú' trên CCCD. ƯU TIÊN tên phường/xã HIỆN "
             "HÀNH ghi trong Đơn / GCN; CCCD in trước sáp nhập hay còn tên CŨ (vd 'Phường 9, Thành phố Đà Lạt'). "
             "chiTietDuoiXa = số nhà/đường/tổ. Đây là NƠI Ở của người, KHÔNG phải địa chỉ thửa đất."},
    {"name": "Nguoi_DienThoai", "desc": "Số điện thoại của CHỦ HỒ SƠ ở dòng 'SĐT'/'Điện thoại' của Đơn. Đơn ghi hai số "
        "(số thứ hai trong ngoặc) → CHỈ lấy số ĐẦU TIÊN. Chỉ chữ số."},
    {"name": "Nguoi_Email", "desc": "Email của chủ hồ sơ nếu Đơn ghi; không có thì bỏ qua."},

    # --- NGƯỜI ĐẠI DIỆN (chỉ khi có Giấy ủy quyền) — dạng phẳng dự phòng cho object NguoiDuocUyQuyen.
    {"name": "DaiDien_HoTen", "desc": "Họ tên NGƯỜI ĐƯỢC ỦY QUYỀN (bên B, sau cụm 'ủy quyền cho') trong Giấy ủy quyền. "
        "KHÔNG có Giấy ủy quyền → bỏ TRỐNG mọi DaiDien_*, kể cả khi hồ sơ có CCCD rời của người khác."},
    {"name": "DaiDien_SoDinhDanh", "desc": "Số CCCD của người được ủy quyền ghi trong Giấy ủy quyền."},
    {"name": "DaiDien_DienThoai", "desc": "Số điện thoại người được ủy quyền nếu giấy ủy quyền có ghi. Chỉ chữ số."},
    {"name": "DaiDien_Email", "desc": "Email người được ủy quyền nếu có."},

    # --- TỔ CHỨC (chỉ khi người đề nghị là PHÁP NHÂN) — ô "Cơ quan/ tổ chức" Phần I.
    {"name": "ToChuc_Ten",
     "desc": "Tên CƠ QUAN/TỔ CHỨC đứng đơn, CHỈ khi người đề nghị là PHÁP NHÂN (công ty, hợp tác xã, đơn vị sự nghiệp, "
             "tổ chức tôn giáo…) ghi rõ ở mục '1. Người đề nghị' / '2. Địa chỉ/trụ sở chính'. Hồ sơ CÁ NHÂN/HỘ GIA "
             "ĐÌNH → BỎ FIELD. KHÔNG lấy họ tên người dân, KHÔNG lấy cơ quan CẤP giấy (UBND, Văn phòng đăng ký đất "
             "đai, Văn phòng công chứng)."},

    # --- THỬA ĐẤT (Phần II) — chỉ Tỉnh + Phường/Xã.
    {"name": "ThuaDat_DiaChi",
     "desc": "Địa chỉ THỬA ĐẤT đề nghị, object {tinh,xa}. Lấy mục '4. Địa điểm thửa đất/khu đất (tại xã…, tỉnh…)' của "
             "Đơn, đối chiếu mục 2 'Địa chỉ' của GCN / 'Địa điểm đo đạc' của mảnh trích đo. ƯU TIÊN tên phường/xã "
             "HIỆN HÀNH. KHÁC nơi ở của người — đừng gán trùng Nguoi_ThuongTru nếu giấy tờ ghi khác."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Nguoi_NgaySinh", "Nguoi_NgayCapCccd"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Nguoi_ThuongTru", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# ---- UI fields Form.io (data[...]) — comp dom-* cho engine fill standard ----
UI_COMP_BY_NAME = {
    # Phần I — Thông tin người nộp.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[phoneNumber]": "dom-input",
    "data[email]": "dom-input",
    "data[organization]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",

    # Phần II — Thông tin thửa đất.
    "data[province2]": "dom-select",
    "data[village2]": "dom-select",

    # Phần III — Thông tin chủ hồ sơ.
    "data[ownerFullname]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[gender1]": "dom-select",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerEmail]": "dom-input",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerIdentityAgency]": "dom-select",
    "data[nation1]": "dom-select",
    "data[province1]": "dom-select",
    "data[district1]": "dom-select",
    "data[ownerAddress]": "dom-input",
    # Nút "Người nộp là chủ hồ sơ" — tự nộp thì FE bấm ở hook post-fill để form tự chép Phần I xuống Phần III.
    "data[BUTTON3]": "dom-owner-copy",
}
