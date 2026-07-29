"""Compact schema cho "[Lâm Đồng] Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót".

LLM CHỈ trả FACT nguồn (giống bản Lai Châu `dinh_chinh_sai_sot`): thông tin người từ
CCCD, chi tiết GCN từ Giấy chứng nhận, nội dung/thửa đất từ Đơn ĐKBĐ Mẫu số 18, và
ngày sinh đúng từ Giấy khai sinh khi cần. `mapper.enrich` suy ra tất định các ô Form.io.

KHÁC bản Lai Châu (form phẳng `CongDan_*`) và bản Bắc Ninh (Liferay `bn-*` khớp nhãn):
cổng Lâm Đồng là Form.io — ô UI là `data[...]` với comp `dom-*`, chia 4 khối:
  Phần I  Người nộp   → data[fullname]..data[address], data[ghiChu]
  Phần II Thửa đất    → data[province2], data[village2]
  Phần III Chủ hồ sơ  → data[ownerFullname]..data[ownerAddress]
  Phần IV Chi tiết GCN→ data[licenseCode]..data[expirationDate]
Ủy quyền: Người nộp (Phần I) là NGƯỜI ĐẠI DIỆN, Chủ hồ sơ (Phần III) là chủ GCN.
"""

FIELDS: list[dict] = [
    # --- NGƯỜI CÓ SAI SÓT / CHỦ HỒ SƠ (chủ Giấy chứng nhận) — nguồn chính CCCD + Đơn + khai sinh.
    {"name": "Nguoi_HoTen", "desc": "Họ tên CHỦ HỒ SƠ = người đứng tên trên Giấy chứng nhận (người có "
        "thông tin sai sót). Lấy từ CCCD / mục a) Tên của Đơn Mẫu 18 / tên người sử dụng đất trên GCN."},
    {"name": "Nguoi_NgaySinh", "desc": "Ngày sinh ĐÚNG của chủ hồ sơ, dd/mm/yyyy — lấy từ CCCD hoặc Giấy "
        "khai sinh (đây thường là giá trị cần đính chính). TUYỆT ĐỐI KHÔNG lấy năm sinh SAI ghi trên GCN cũ."},
    {"name": "Nguoi_GioiTinh", "desc": 'Giới tính chủ hồ sơ: "Nam" hoặc "Nữ" (từ CCCD/khai sinh).'},
    {"name": "Nguoi_SoDinhDanh", "desc": "Số định danh/CCCD/CMND của chủ hồ sơ; đọc mặt trước hoặc MRZ mặt sau, "
        "hoặc mục b) 'CCCD số' của Đơn Mẫu 18."},
    {"name": "Nguoi_NgayCapCccd", "desc": "Ngày cấp CCCD/CMND của chủ hồ sơ (mặt sau), dd/mm/yyyy. Chỉ có nếu upload CCCD."},
    {"name": "Nguoi_NoiCapCccd",
     "desc": 'Nơi cấp CCCD/CMND của chủ hồ sơ (mặt sau). "CỤC TRƯỞNG CỤC CẢNH SÁT..." → '
             '"Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → '
             '"Bộ Công an". Chỉ có nếu upload CCCD.'},
    {"name": "Nguoi_ThuongTru",
     "desc": "Nơi thường trú của chủ hồ sơ, object {quocGia,tinh,xa,diaChi}. ƯU TIÊN tên phường/xã MỚI ghi "
             "ở mục 1c 'Địa chỉ' của Đơn Mẫu 18; nếu CCCD ghi tên CŨ (vd 'Phường 9') mà Đơn ghi tên mới "
             "('Phường Lâm Viên - Đà Lạt') thì lấy theo Đơn. diaChi = số nhà/đường."},
    {"name": "Nguoi_DienThoai", "desc": "Số điện thoại liên hệ của chủ hồ sơ — lấy ở mục 1d của Đơn Mẫu 18. Chỉ chữ số."},
    {"name": "Nguoi_Email", "desc": "Hộp thư điện tử ở mục 1d Đơn Mẫu 18 nếu có; đơn bỏ trống thì bỏ qua."},

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

    # --- THỬA ĐẤT (Phần II) — địa chỉ thửa đất cần đính chính.
    {"name": "ThuaDat_DiaChi",
     "desc": "Địa chỉ THỬA ĐẤT ghi trên GCN / mục 2 Đơn Mẫu 18, object {tinh,xa}. ƯU TIÊN tên phường/xã MỚI "
             "trong Đơn ('Phường Lâm Viên - Đà Lạt'); GCN ghi tên cũ ('Phường 09') thì vẫn chọn tên mới theo Đơn."},
    {"name": "ThuaDat_So", "desc": "Thửa đất số (vd '17'), từ GCN/Đơn."},
    {"name": "ThuaDat_ToBanDo", "desc": "Tờ bản đồ số (vd '09'), từ GCN/Đơn."},

    # --- NỘI DUNG ĐÍNH CHÍNH (Phần ghi chú) — mục 2 Đơn Mẫu 18.
    {"name": "Don_NoiDungDinhChinh",
     "desc": "Nội dung đề nghị đính chính ghi ở mục 2 'Nội dung biến động' của Đơn Mẫu 18, NGUYÊN VĂN "
             "(vd 'Xin điều chỉnh năm sinh trên GCN từ 1964 sang 1965 cho phù hợp giấy khai sinh'). Không tự bịa."},

    # --- CHI TIẾT GIẤY CHỨNG NHẬN đã cấp cần đính chính (Phần IV) — CHỈ từ GCN.
    {"name": "Gcn_SoPhatHanh", "desc": "Số phát hành/số hiệu GCN trên bìa, thường 2 chữ cái + số (vd 'AB 373405'). "
        "KHÔNG lấy 'Số vào sổ cấp GCN' (vd 'H00166') vào field này."},
    {"name": "Gcn_NgayCap", "desc": "Ngày ký/cấp GCN (gần chữ ký TM. UBND, trang cuối), dd/mm/yyyy. Không lấy ngày biến động/ngày in."},
    {"name": "Gcn_DonViCap", "desc": "Đơn vị/cơ quan KÝ CẤP GCN gần chữ ký-con dấu (vd 'UBND Thành phố Đà Lạt'). "
        "'TM. ỦY BAN NHÂN DÂN ...' → chuẩn hóa 'UBND ...'."},
    {"name": "Gcn_NoiCap", "desc": "Địa danh NƠI CẤP ghi trên GCN (vd 'Tỉnh Lâm Đồng')."},
    {"name": "Gcn_ThoiHan", "desc": "Thời hạn sử dụng đất ghi trên GCN (vd 'Lâu dài' hoặc một ngày dd/mm/yyyy). "
        "Nếu 'Lâu dài'/'lâu dài' thì trả đúng chữ đó."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Nguoi_NgaySinh", "Nguoi_NgayCapCccd",
    "DaiDien_NgaySinh", "DaiDien_NgayCapCccd",
    "Gcn_NgayCap",
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
    "data[ghiChu]": "dom-input",

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

    # Phần IV — Chi tiết Giấy chứng nhận cần đính chính.
    "data[licenseCode]": "dom-input",
    "data[licenseDate]": "dom-date",
    "data[licensingPlace]": "dom-input",
    "data[licensingAgency]": "dom-input",
    "data[effectiveDate]": "dom-date",
    "data[expirationDate]": "dom-date",
}
