"""Compact schema cho "Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót" — cổng DVC TP Đà Nẵng
dichvucong.danang.gov.vn (Form.io). CÙNG cổng/engine + field-key contact block Y HỆT #110
(cap_gcn_so_nha_da_nang); THÊM Phần II (thửa đất) + nội dung đính chính.

Phần I là 1 panel chứa HAI vai:
- ChuHoSo_*  : CHỦ HỒ SƠ = người được cấp GCN (người đề nghị đính chính, đứng tên trên GCN/Đơn Mẫu 18).
- NguoiNop_* : NGƯỜI NỘP. Mặc định TỰ NỘP → NguoiNop = ChuHoSo; chỉ ỦY QUYỀN khi có văn bản ủy quyền.
Phần II: thông tin THỬA ĐẤT/công trình được đính chính (lấy ở GCN đã cấp).
"""

# --- Chủ hồ sơ (người được cấp GCN, đề nghị đính chính) ---
FIELDS: list[dict] = [
    {"name": "ChuHoSo_LoaiChuThe", "desc": '"Tổ chức" nếu chủ hồ sơ là công ty/doanh nghiệp/cơ quan; '
        '"Cá nhân" nếu là một người. Chủ hồ sơ là NGƯỜI ĐỀ NGHỊ ĐÍNH CHÍNH = người đứng tên trên Đơn Mẫu '
        '18 / người được cấp Giấy chứng nhận cần đính chính.'},
    {"name": "ChuHoSo_HoTen", "desc": "Tên CHỦ HỒ SƠ — nếu CÁ NHÂN: họ và tên IN HOA; nếu TỔ CHỨC: tên "
        "đầy đủ. Lấy theo CCCD (tên ĐÚNG) của người đề nghị đính chính, hoặc mục 1.e Đơn Mẫu 18. ⚠ Nếu "
        "GCN ghi tên SAI (chính là nội dung cần đính chính) thì lấy tên ĐÚNG theo CCCD, KHÔNG lấy tên sai."},

    # --- Nội dung đính chính (mục 2 Đơn Mẫu 18) ---
    {"name": "NoiDungDinhChinh", "desc": "Nội dung yêu cầu đính chính — CHÉP NGUYÊN VĂN mục '2. Nội dung "
        "biến động' của Đơn đăng ký biến động (Mẫu số 18). Thường dạng 'Đính chính {thông tin sai} thành "
        "{thông tin đúng}' (vd 'Đính chính Bà Bùi Thị Quí thành Bà Bùi Thị Quý'). Nếu đơn không ghi rõ, "
        "mô tả sai sót cần đính chính (tên/số giấy tờ/địa chỉ/thửa đất...)."},
]

# --- Người nộp hồ sơ ---
FIELDS += [
    {"name": "NguoiNop_LoaiDoiTuong", "desc": '"Tổ chức" nếu người nộp là tổ chức; "Cá nhân" nếu là một '
        'người. Đa số CÁ NHÂN.'},
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI NỘP HỒ SƠ. Nếu có Văn bản ủy quyền (nộp thay): lấy "
        "người ĐƯỢC ỦY QUYỀN. Nếu KHÔNG có ủy quyền (tự nộp): người nộp CHÍNH LÀ chủ hồ sơ. IN HOA như CCCD."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh NGƯỜI NỘP, dd/mm/yyyy — CCCD (ưu tiên, đủ ngày tháng)."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính NGƯỜI NỘP: "Nam"/"Nữ" — CCCD; hoặc suy từ danh xưng '
        'Ông/Bà / nhãn quan hệ (vợ/mẹ → Nữ).'},
    {"name": "NguoiNop_MaSoThue", "desc": "Mã số thuế/mã định danh tổ chức NGƯỜI NỘP (CHỈ khi tổ chức). Chỉ chữ số."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND/định danh cá nhân NGƯỜI NỘP. ƯU TIÊN số CCCD hiện "
        "tại (12 số) theo thẻ CCCD; số CMND cũ (9 số) chỉ để đối chiếu. Chỉ chữ số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD NGƯỜI NỘP, dd/mm/yyyy — mặt sau CCCD."},
    {"name": "NguoiNop_NoiCap", "desc": 'Cơ quan cấp CCCD NGƯỜI NỘP. CCCD gắn chip: "Cục Cảnh sát quản lý '
        'hành chính về trật tự xã hội"; thẻ căn cước mới: "Bộ Công an".'},
    {"name": "NguoiNop_DiaChi", "desc": "Địa chỉ thường trú NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi}. Lấy "
        "ở CCCD (Nơi thường trú). tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường (KHÔNG kèm "
        "phường/xã/tỉnh). KHÁC địa chỉ THỬA ĐẤT."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại NGƯỜI NỘP (Đơn Mẫu 18 mục 1.d/1.h). Chỉ chữ số."},
    {"name": "NguoiNop_Email", "desc": "Email NGƯỜI NỘP nếu giấy tờ có; thường không có → bỏ."},

    # --- Phần II: thửa đất/công trình được đính chính (lấy ở GCN đã cấp) ---
    {"name": "ThuaDat_DiaChi", "desc": "Địa chỉ thửa đất/địa chỉ xây dựng ghi trên GCN đã cấp (mục II — "
        "Nhà ở/Đất ở), object {quocGia,tinh,xa,diaChi} hoặc chuỗi. ĐÂY LÀ ĐỊA CHỈ TÀI SẢN. Ưu tiên GCN "
        "(giấy đang đề nghị đính chính)."},
    {"name": "ThuaDat_SoTo", "desc": "Số tờ bản đồ (GCN mục II — b/ Đất ở — Tờ bản đồ số). Chỉ số. Bỏ nếu không có."},
    {"name": "ThuaDat_SoThua", "desc": "Số thửa đất (GCN mục II — b/ Đất ở — Thửa đất số). Chỉ số. Bỏ nếu không có."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["NguoiNop_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_DiaChi"] = "x-select-area"
COMPACT_COMP_BY_NAME["ThuaDat_DiaChi"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Field-key CHUẨN từ HTML thật.
UI_COMP_BY_NAME = {
    # Phần I — chủ hồ sơ.
    "data[ownerFullname]": "dom-input",
    "data[isOwnerDossier]": "dom-checkbox",
    "data[organization]": "dom-input",
    # Phần I — người nộp.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[email]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[note]": "dom-input",
    "data[noidungyeucaugiaiquyet]": "dom-input",   # textarea — nội dung ĐÍNH CHÍNH.
    "data[taxCode]": "dom-input",
    "data[chonDoiTuong]": "dom-select",            # Cá nhân/Tổ chức.
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    # Phần II — thửa đất.
    "data[diaChiThuaDat]": "dom-input",            # textarea địa chỉ thửa đất.
    "data[SoToBanDo]": "dom-input",
    "data[SoThuaDat]": "dom-input",
    "data[nation2]": "dom-select",
    "data[province2]": "dom-select",
    "data[district2]": "dom-select",
}
