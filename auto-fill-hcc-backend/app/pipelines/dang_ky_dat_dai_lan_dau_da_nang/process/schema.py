"""Compact schema cho "Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận QSDĐ lần đầu (hộ gia
đình, cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở nước ngoài)" — cổng DVC TP Đà Nẵng
dichvucong.danang.gov.vn (Form.io).

Form UI field-key data[...] Y HỆT #136 giao_thue_chuyen_muc_dich (contact-block 2 vai + panel thửa đất).
KHÁC bản chất: đăng ký/cấp GCN LẦN ĐẦU → chưa có GCN; nguồn thửa đất là Đơn Mẫu 15 + Hồ sơ đo đạc.

Phần I là 1 panel chứa HAI vai:
- ChuHoSo_*  : CHỦ HỒ SƠ = người sử dụng đất / người ĐỀ NGHỊ đăng ký, cấp GCN lần đầu (đứng tên Đơn đăng
               ký Mẫu số 15). Nếu hộ gia đình/nhiều người chung/thừa kế có Văn bản thỏa thuận cử người đại
               diện → chủ hồ sơ là NGƯỜI ĐƯỢC CỬ ĐẠI DIỆN đứng tên GCN. Có thể CÁ NHÂN / TỔ CHỨC.
- NguoiNop_* : NGƯỜI NỘP HỒ SƠ = người trực tiếp thao tác nộp (có thể được ỦY QUYỀN/đại diện). Tự nộp thì
               NguoiNop = ChuHoSo.
Thửa đất (ThuaDat_*) là THÔNG TIN NGHIỆP VỤ của thửa đất đăng ký, KHÔNG phải địa chỉ của người.
"""

# --- Chủ hồ sơ (subject = người đề nghị đăng ký, cấp GCN lần đầu) ---
FIELDS: list[dict] = [
    {"name": "ChuHoSo_LoaiChuThe", "desc": '"Tổ chức" nếu chủ hồ sơ là công ty/doanh nghiệp/HTX/cơ quan '
        '(tên có "Công ty", "Doanh nghiệp", "HTX", "Hợp tác xã"); "Cá nhân" nếu là một người (kể cả hộ gia '
        'đình, cộng đồng dân cư, người gốc Việt Nam định cư ở nước ngoài). Chủ hồ sơ là người sử dụng đất/'
        'người ĐỀ NGHỊ đăng ký, cấp GCN lần đầu (đứng tên Đơn đăng ký Mẫu số 15).'},
    {"name": "ChuHoSo_HoTen", "desc": "Tên CHỦ HỒ SƠ — nếu CÁ NHÂN: họ và tên (IN HOA); nếu TỔ CHỨC: tên "
        "đầy đủ tổ chức. Lấy ở Đơn đăng ký đất đai Mẫu số 15 (Người sử dụng đất, chủ sở hữu tài sản gắn "
        "liền với đất). ⚠ Nếu có Văn bản thỏa thuận cử người đại diện (hộ gia đình/nhiều người chung/thừa "
        "kế) → lấy NGƯỜI ĐƯỢC CỬ ĐẠI DIỆN đứng tên trong GCN. KHÔNG lấy người đã chết trong giấy chứng "
        "tử/trích lục khai tử."},
    {"name": "ChuHoSo_DiaChi", "desc": "Địa chỉ THƯỜNG TRÚ/nơi ở của CHỦ HỒ SƠ (người sử dụng đất/người "
        "đại diện), object {quocGia,tinh,xa,diaChi}. ƯU TIÊN địa chỉ ghi trên GIẤY TỜ HỒ SƠ do người khai "
        "lập: Tờ khai thuế ('Địa chỉ cư trú'/'Địa chỉ thường trú' — thường có đủ số nhà, tổ, phường/xã, "
        "tỉnh), Đơn cam kết ('Địa chỉ thường trú'), Đơn đăng ký Mẫu 15 (mục 1c 'Địa chỉ'). CHỈ dùng 'Nơi "
        "thường trú' trên CCCD/Căn cước khi các giấy tờ trên KHÔNG ghi địa chỉ — vì CCCD hay bị đọc lệch "
        "hoặc còn ghi tên đơn vị hành chính CŨ. GOM đủ {tinh, xa, diaChi} từ nhiều giấy tờ: nếu Đơn M15 chỉ "
        "ghi số nhà thì lấy thêm phường/tỉnh từ Tờ khai thuế/Đơn cam kết. ⚠ TUYỆT ĐỐI KHÔNG lấy 'địa chỉ "
        "thửa đất/khu đất' (vị trí lô đất) làm địa chỉ người — dù trong hồ sơ chúng có thể trùng nhau. "
        "tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường/tổ/thôn."},
]

# --- Nội dung nghiệp vụ: đề nghị đăng ký/cấp GCN (điền textarea "Nội dung yêu cầu giải quyết") ---
FIELDS += [
    {"name": "NoiDungYeuCau", "desc": "Nội dung yêu cầu giải quyết — CHÉP ĐẦY ĐỦ nội dung đề nghị của Đơn "
        "đăng ký đất đai Mẫu số 15 (mục 'Đề nghị của người sử dụng đất, chủ sở hữu tài sản gắn liền với "
        "đất' / mục đề nghị cấp Giấy chứng nhận), KHÔNG rút gọn, KHÔNG tự mở rộng. Giữ chi tiết: đề nghị "
        "đăng ký/cấp GCN cho thửa đất số, tờ bản đồ số, diện tích, loại đất, mục đích sử dụng, tài sản gắn "
        "liền với đất (nhà ở/công trình nếu có), địa chỉ thửa đất. Nếu nhiều mục thì mỗi mục MỘT DÒNG. Bỏ "
        "các dấu chấm chấm (.....) placeholder trống. Không có nội dung thì bỏ trống."},
]

# --- Thông tin thửa đất (nghiệp vụ — panel riêng của form) ---
FIELDS += [
    {"name": "ThuaDat_DiaChi", "desc": "Địa chỉ/vị trí THỬA ĐẤT (địa chỉ thửa đất/địa chỉ xây dựng), object "
        "{quocGia,tinh,xa,diaChi}. Ưu tiên Đơn Mẫu 15 (Thửa đất đăng ký — Địa chỉ), rồi Hồ sơ đo đạc (Địa "
        "chỉ thửa đất), giấy tờ nhà đất cũ (vị trí nhà đất). Đây là VỊ TRÍ LÔ ĐẤT — KHÔNG phải nơi thường "
        "trú của người. tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường/thôn/tổ."},
    {"name": "ThuaDat_SoThua", "desc": "Số thửa đất (Thửa đất số). Ưu tiên Đơn Mẫu 15, rồi Hồ sơ đo đạc. "
        "Chỉ lấy số/ký hiệu thửa, KHÔNG kèm chữ 'thửa đất số'."},
    {"name": "ThuaDat_SoTo", "desc": "Số tờ bản đồ (Tờ bản đồ số). Ưu tiên Đơn Mẫu 15, rồi Hồ sơ đo đạc. "
        "Chỉ lấy số tờ, KHÔNG kèm chữ 'tờ bản đồ số'."},
]

# --- Người nộp hồ sơ (người thao tác nộp; có thể được ủy quyền/đại diện) ---
FIELDS += [
    {"name": "NguoiNop_LoaiDoiTuong", "desc": '"Tổ chức" nếu người nộp là tổ chức; "Cá nhân" nếu là một '
        'người. Đa số người nộp là CÁ NHÂN (kể cả khi được tổ chức/hộ gia đình ủy quyền).'},
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI NỘP HỒ SƠ. Nếu có Hợp đồng/Giấy ủy quyền hoặc Văn "
        "bản thỏa thuận cử người đại diện: lấy BÊN ĐƯỢC ỦY QUYỀN/người được cử đại diện. Nếu KHÔNG có (tự "
        "nộp): người nộp CHÍNH LÀ chủ hồ sơ. IN HOA như CCCD."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh NGƯỜI NỘP (cá nhân), dd/mm/yyyy — CCCD / Giấy ủy quyền / VB thỏa thuận."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính NGƯỜI NỘP: "Nam"/"Nữ" — CCCD, hoặc suy từ danh xưng '
        'Ông/Bà trong Giấy ủy quyền/VB thỏa thuận.'},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND/định danh cá nhân NGƯỜI NỘP. Đọc CCCD hoặc Giấy "
        "ủy quyền/VB thỏa thuận ('Căn cước công dân số'). Chỉ chữ số. Ưu tiên 12 chữ số."},
    {"name": "NguoiNop_MaSoThue", "desc": "Mã số thuế / mã định danh tổ chức NGƯỜI NỘP (CHỈ khi người nộp "
        "là TỔ CHỨC). Chỉ chữ số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD NGƯỜI NỘP, dd/mm/yyyy — mặt sau CCCD / Giấy ủy quyền / VB thỏa thuận."},
    {"name": "NguoiNop_NoiCap", "desc": 'Cơ quan cấp CCCD NGƯỜI NỘP — GHI ĐẦY ĐỦ, KHÔNG viết tắt. Giấy tờ '
        'hay ghi tắt "CCSQLHC TTXH" / "CCSVLHC TTXH" / "CCS QLHC về TTXH" / "Cục CSQLHC" → PHẢI ghi thành '
        '"Cục Cảnh sát quản lý hành chính về trật tự xã hội". Thẻ căn cước mới ghi "Bộ Công an".'},
    {"name": "NguoiNop_DiaChi", "desc": "Địa chỉ THƯỜNG TRÚ của CHÍNH NGƯỜI NỘP, object {quocGia,tinh,xa,"
        "diaChi}. Nếu người nộp CHÍNH LÀ người sử dụng đất/người kê khai trên hồ sơ (tự nộp) → lấy GIỐNG "
        "ChuHoSo_DiaChi: ƯU TIÊN Tờ khai thuế ('Địa chỉ cư trú'), Đơn cam kết ('Địa chỉ thường trú'), Đơn "
        "Mẫu 15; KHÔNG ưu tiên CCCD (CCCD hay đọc lệch/còn tên đơn vị hành chính cũ). Nếu là người ĐƯỢC ỦY "
        "QUYỀN/đại diện KHÁC → lấy địa chỉ Bên được ủy quyền/người đại diện trên Giấy ủy quyền/VB thỏa "
        "thuận (hoặc CCCD của chính người đó). ⚠ Giấy giới thiệu THƯỜNG KHÔNG có địa chỉ thường trú → nếu "
        "không có, BỎ TRỐNG toàn bộ (đừng đoán). TUYỆT ĐỐI KHÔNG lấy địa chỉ thửa đất, trụ sở tổ chức, hay "
        "tỉnh của thửa đất làm địa chỉ người nộp. tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/"
        "đường/tổ/thôn."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại NGƯỜI NỘP. Chỉ chữ số. Thường không có trên giấy tờ."},
    {"name": "NguoiNop_Email", "desc": "Email NGƯỜI NỘP nếu giấy tờ có; thường không có → bỏ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["NguoiNop_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_DiaChi"] = "x-select-area"
COMPACT_COMP_BY_NAME["ChuHoSo_DiaChi"] = "x-select-area"
COMPACT_COMP_BY_NAME["ThuaDat_DiaChi"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Contact block + panel thửa đất Y HỆT #136 giao_thue.
UI_COMP_BY_NAME = {
    # Chủ hồ sơ.
    "data[ownerFullname]": "dom-input",
    "data[isOwnerDossier]": "dom-checkbox",
    "data[organization]": "dom-input",
    # Người nộp hồ sơ.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[email]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[note]": "dom-input",
    "data[noidungyeucaugiaiquyet]": "dom-input",
    "data[taxCode]": "dom-input",
    "data[chonDoiTuong]": "dom-select",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    # Thông tin thửa đất (panel riêng).
    "data[SoThuaDat]": "dom-input",
    "data[SoToBanDo]": "dom-input",
    "data[diaChiThuaDat]": "dom-input",
    "data[nation2]": "dom-select",
    "data[province2]": "dom-select",
    "data[district2]": "dom-select",
}
