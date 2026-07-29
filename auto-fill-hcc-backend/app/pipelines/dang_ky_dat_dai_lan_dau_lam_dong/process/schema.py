"""Compact schema cho "[Lâm Đồng] Đăng ký đất đai, cấp GCN lần đầu (hộ gia đình, cá nhân...)".

LLM CHỈ trả FACT nguồn: thông tin người từ CCCD, địa chỉ thửa đất từ Đơn đăng ký đất đai / sơ đồ
ranh giới / trích lục bản đồ. `mapper.enrich` suy ra tất định các ô Form.io.

CÙNG form/nền tảng với dinh_chinh_sai_sot_lam_dong (Form.io, ô data[...] comp dom-*, nút copy
data[BUTTON3]), chia 3 khối cần điền:
  Phần I  Người nộp   → data[fullname]..data[address]
  Phần II Thửa đất    → data[province2], data[village2]
  Phần III Chủ hồ sơ  → data[ownerFullname]..data[ownerAddress]
KHÁC đính chính: Phần IV "Thông tin chi tiết" (GCN) = "không cần điền" (đăng ký LẦN ĐẦU, chưa có
GCN) → KHÔNG trích Gcn_*; ô Ghi chú để trống.
Ủy quyền: Người nộp (Phần I) là NGƯỜI ĐẠI DIỆN, Chủ hồ sơ (Phần III) là chủ hộ đứng đơn.
"""

FIELDS: list[dict] = [
    # --- CHỦ HỒ SƠ (chủ hộ đứng đơn đăng ký đất đai) — nguồn chính CCCD + Đơn đăng ký đất đai.
    {"name": "Nguoi_HoTen", "desc": "Họ tên CHỦ HỒ SƠ = người sử dụng đất đứng đơn đăng ký. Lấy từ CCCD "
        "hoặc mục người sử dụng đất/người đăng ký của Đơn đăng ký đất đai (Mẫu 15/ĐK)."},
    {"name": "Nguoi_NgaySinh", "desc": "Ngày sinh chủ hồ sơ, dd/mm/yyyy — lấy từ CCCD."},
    {"name": "Nguoi_GioiTinh", "desc": 'Giới tính chủ hồ sơ: "Nam" hoặc "Nữ" (từ CCCD).'},
    {"name": "Nguoi_SoDinhDanh", "desc": "Số định danh/CCCD/CMND của chủ hồ sơ; đọc mặt trước hoặc MRZ mặt sau, "
        "hoặc dòng 'CCCD số' của Đơn đăng ký đất đai."},
    {"name": "Nguoi_NgayCapCccd", "desc": "Ngày cấp CCCD/CMND của chủ hồ sơ (mặt sau), dd/mm/yyyy. Chỉ có nếu upload CCCD."},
    {"name": "Nguoi_NoiCapCccd",
     "desc": 'Nơi cấp CCCD/CMND của chủ hồ sơ (mặt sau). "CỤC TRƯỞNG CỤC CẢNH SÁT..." → '
             '"Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → '
             '"Bộ Công an". Chỉ có nếu upload CCCD.'},
    {"name": "Nguoi_ThuongTru",
     "desc": "Nơi thường trú của chủ hồ sơ, object {quocGia,tinh,xa,diaChi}. ƯU TIÊN tên phường/xã MỚI ghi "
             "trong Đơn đăng ký đất đai; nếu CCCD ghi tên CŨ (vd 'Phường 9') mà Đơn ghi tên mới thì lấy "
             "theo Đơn. diaChi = số nhà/đường."},
    {"name": "Nguoi_DienThoai", "desc": "Số điện thoại liên hệ của chủ hồ sơ — lấy trong Đơn đăng ký đất đai nếu có. Chỉ chữ số."},
    {"name": "Nguoi_Email", "desc": "Hộp thư điện tử ghi trong Đơn đăng ký đất đai nếu có; bỏ trống thì bỏ qua."},

    # --- NGƯỜI ĐẠI DIỆN / ĐƯỢC ỦY QUYỀN (chỉ khi có Giấy ủy quyền) — đây là NGƯỜI NỘP, KHÁC chủ hồ sơ.
    {"name": "DaiDien_HoTen", "desc": "Họ tên NGƯỜI NỘP HỒ SƠ khi KHÁC chủ hồ sơ (nộp thay/đại diện). Xác "
        "định qua khối <nguoi_nop_context> (mỏ neo người nộp từ tài khoản) hoặc Giấy ủy quyền / mục 'người "
        "đại diện' trong Đơn. Người này KHÁC người đứng tên GCN/Đơn (Nguoi_HoTen). Tự nộp (trùng chủ hồ sơ) "
        "hoặc không có giấy tờ người nộp → bỏ trống toàn bộ DaiDien_*."},
    {"name": "DaiDien_NgaySinh", "desc": "Ngày sinh người đại diện, dd/mm/yyyy, nếu giấy ủy quyền/ CCCD người đại diện ghi rõ."},
    {"name": "DaiDien_GioiTinh", "desc": 'Giới tính người đại diện: "Nam"/"Nữ" nếu có.'},
    {"name": "DaiDien_SoDinhDanh", "desc": "Số CCCD/CMND của người đại diện (dòng 'Căn cước công dân số …' của Bên được ủy quyền)."},
    {"name": "DaiDien_NgayCapCccd", "desc": "Ngày cấp CCCD người đại diện, dd/mm/yyyy — thường ở dòng "
        "'CCCD số … cấp ngày <ngày> tại <nơi>' trong Giấy ủy quyền. Đừng bỏ trống nếu ủy quyền có ghi."},
    {"name": "DaiDien_NoiCapCccd", "desc": "Nơi cấp CCCD người đại diện — dòng 'CCCD số … cấp ngày … tại "
        "<nơi cấp>' trong Giấy ủy quyền; chuẩn hóa như Nguoi_NoiCapCccd."},
    {"name": "DaiDien_ThuongTru", "desc": "Nơi cư trú người đại diện, object {quocGia,tinh,xa,diaChi} nếu có."},
    {"name": "DaiDien_DienThoai", "desc": "Số điện thoại người đại diện nếu ghi trong đơn/ủy quyền. Chỉ chữ số."},
    {"name": "DaiDien_Email", "desc": "Email người đại diện nếu có."},

    # --- THỬA ĐẤT (Phần II) — địa chỉ thửa đất đăng ký.
    {"name": "ThuaDat_DiaChi",
     "desc": "Địa chỉ THỬA ĐẤT đăng ký, object {tinh,xa}. Lấy từ Đơn đăng ký đất đai / Sơ đồ ranh giới "
             "sử dụng đất / Trích lục bản đồ địa chính. ƯU TIÊN tên phường/xã MỚI (địa giới hiện hành)."},
    {"name": "ThuaDat_So", "desc": "Thửa đất số, từ Đơn/sơ đồ/trích lục."},
    {"name": "ThuaDat_ToBanDo", "desc": "Tờ bản đồ số, từ Đơn/sơ đồ/trích lục."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Nguoi_NgaySinh", "Nguoi_NgayCapCccd",
    "DaiDien_NgaySinh", "DaiDien_NgayCapCccd",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Nguoi_ThuongTru", "DaiDien_ThuongTru", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# ---- UI fields Form.io (data[...]) — comp dom-* cho engine fill standard ----
UI_COMP_BY_NAME = {
    # Phần I — Thông tin người nộp.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[phoneNumber]": "dom-input",
    "data[email]": "dom-input",
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
    # Nút "Người nộp là chủ hồ sơ" — khi tự nộp, bấm để form tự copy Phần I xuống Phần III
    # (thay vì fill tay). comp dom-owner-copy → FE bấm ở hook post-fill (reapplyOwnerDossierCopy).
    "data[BUTTON3]": "dom-owner-copy",
    # Phần IV "Thông tin chi tiết" (GCN) = KHÔNG cần điền với đăng ký lần đầu → không map.
}
