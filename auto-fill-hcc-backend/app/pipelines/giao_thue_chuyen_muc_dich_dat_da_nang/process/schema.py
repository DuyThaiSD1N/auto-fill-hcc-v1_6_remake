"""Compact schema cho "Giao đất, cho thuê đất, chuyển mục đích sử dụng đất; giao đất và giao rừng; cho
thuê đất và cho thuê rừng; gia hạn sử dụng đất" — cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn (Form.io).

CÙNG contact-block với #75/chuyen_muc_dich/tach_hop_thua — UI field-key data[...] cho người nộp/chủ hồ sơ
Y HỆT. KHÁC: form này có THÊM 1 panel "Thông tin thửa đất" (Số thửa/Số tờ/Địa chỉ thửa đất +
province2/district2/nation2) mà chuyển mục đích/tách thửa KHÔNG có → phải điền thêm.

Phần I là 1 panel chứa HAI vai:
- ChuHoSo_*  : CHỦ HỒ SƠ = người sử dụng đất / người ĐỀ NGHỊ giao đất/thuê đất/chuyển mục đích/gia hạn
               (đứng tên Đơn Mẫu 01, Giấy chứng nhận QSDĐ). Có thể CÁ NHÂN / TỔ CHỨC.
- NguoiNop_* : NGƯỜI NỘP HỒ SƠ = người trực tiếp thao tác nộp (có thể được ỦY QUYỀN). Tự nộp thì
               NguoiNop = ChuHoSo.
Thửa đất (ThuaDat_*) là THÔNG TIN NGHIỆP VỤ của thửa đất trong hồ sơ, KHÔNG phải địa chỉ của người.
"""

# --- Chủ hồ sơ (subject = người đề nghị giao/thuê đất, chuyển mục đích) ---
FIELDS: list[dict] = [
    {"name": "ChuHoSo_LoaiChuThe", "desc": '"Tổ chức" nếu chủ hồ sơ là công ty/doanh nghiệp/HTX/cơ quan '
        '(tên có "Công ty", "Doanh nghiệp", "HTX", "Hợp tác xã"); "Cá nhân" nếu là một người. Chủ hồ sơ là '
        'người sử dụng đất/người ĐỀ NGHỊ giao đất, cho thuê đất, chuyển mục đích sử dụng đất hoặc gia hạn '
        '(người đứng tên Đơn Mẫu số 01 / Giấy chứng nhận QSDĐ).'},
    {"name": "ChuHoSo_HoTen", "desc": "Tên CHỦ HỒ SƠ — nếu CÁ NHÂN: họ và tên (IN HOA); nếu TỔ CHỨC: tên "
        "đầy đủ tổ chức. Lấy ở Đơn đề nghị Mẫu số 01 (người đề nghị/Tôi tên là), Giấy chứng nhận QSDĐ "
        "(người sử dụng đất đứng tên), Tờ khai thuế (người nộp thuế/người sử dụng đất), hoặc Giấy chứng "
        "nhận ĐKKD."},
    {"name": "ChuHoSo_DiaChi", "desc": "Địa chỉ THƯỜNG TRÚ/nơi ở của CHỦ HỒ SƠ (người đề nghị), object "
        "{quocGia,tinh,xa,diaChi}. Lấy ở địa chỉ người đề nghị trong Đơn Mẫu 01 hoặc Nơi thường trú trên "
        "CCCD của chủ hồ sơ. ⚠ TUYỆT ĐỐI KHÔNG lấy 'địa chỉ thửa đất/khu đất' (vị trí lô đất) làm địa chỉ "
        "người — dù trong hồ sơ chúng có thể trùng nhau. tinh='Tỉnh/Thành phố …', xa=phường/xã, "
        "diaChi=số nhà/đường/thôn (nếu chỉ ghi cấp phường thì để diaChi trống)."},
]

# --- Nội dung nghiệp vụ: mô tả việc giao/thuê đất, chuyển mục đích, gia hạn (điền textarea "Nội dung yêu
#     cầu giải quyết") ---
FIELDS += [
    {"name": "NoiDungYeuCau", "desc": "Nội dung yêu cầu giải quyết — CHÉP ĐẦY ĐỦ nội dung đề nghị của Đơn "
        "Mẫu số 01 (mục 'đề nghị được giao đất/thuê đất/chuyển mục đích sử dụng đất/gia hạn...'), KHÔNG rút "
        "gọn, KHÔNG tóm tắt. BẮT BUỘC giữ MỌI chi tiết: hình thức đề nghị (giao đất / cho thuê đất / chuyển "
        "mục đích / giao rừng / cho thuê rừng / gia hạn), diện tích (m²), loại đất TRƯỚC và SAU (mục đích "
        "hiện trạng → mục đích đề nghị), số thửa, số tờ bản đồ, địa chỉ/vị trí thửa đất, thời hạn (nếu có). "
        "Nếu có nhiều thửa/nhiều hạng mục thì mỗi mục MỘT DÒNG riêng. Bỏ các dấu chấm chấm (.....) "
        "placeholder trống trên đơn. Ví dụ KHUÔN (thay bằng số liệu THẬT): 'Chuyển [..] m² đất [loại đất "
        "hiện trạng] sang [loại đất đề nghị] tại thửa đất số [..], tờ bản đồ số [..], địa chỉ [..]'. Không "
        "có nội dung thì bỏ trống."},
]

# --- Thông tin thửa đất (nghiệp vụ — panel riêng của form giao/thuê/chuyển mục đích) ---
FIELDS += [
    {"name": "ThuaDat_DiaChi", "desc": "Địa chỉ/vị trí THỬA ĐẤT (địa chỉ thửa đất/địa chỉ xây dựng), object "
        "{quocGia,tinh,xa,diaChi}. Ưu tiên Giấy chứng nhận QSDĐ (địa chỉ/vị trí thửa), rồi Đơn Mẫu 01 "
        "(Địa điểm thửa đất/khu đất), Tờ khai thuế (Địa chỉ thửa đất). Đây là VỊ TRÍ LÔ ĐẤT — KHÔNG phải "
        "nơi thường trú của người. tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường/thôn/tổ."},
    {"name": "ThuaDat_SoThua", "desc": "Số thửa đất (Thửa đất số / Số hiệu thửa đất). Ưu tiên Giấy chứng "
        "nhận QSDĐ, rồi Tờ khai thuế/Đơn Mẫu 01. Chỉ lấy số/ký hiệu thửa, KHÔNG kèm chữ 'thửa đất số'."},
    {"name": "ThuaDat_SoTo", "desc": "Số tờ bản đồ (Tờ bản đồ số). Ưu tiên Giấy chứng nhận QSDĐ, rồi Tờ "
        "khai thuế/Đơn Mẫu 01. Chỉ lấy số tờ, KHÔNG kèm chữ 'tờ bản đồ số'."},
]

# --- Người nộp hồ sơ (người thao tác nộp; có thể được ủy quyền) ---
FIELDS += [
    {"name": "NguoiNop_LoaiDoiTuong", "desc": '"Tổ chức" nếu người nộp là tổ chức; "Cá nhân" nếu là một '
        'người. Đa số người nộp là CÁ NHÂN (kể cả khi được tổ chức ủy quyền).'},
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI NỘP HỒ SƠ. Nếu có Hợp đồng/Giấy ủy quyền: lấy BÊN "
        "ĐƯỢC ỦY QUYỀN (Bên B/người được ủy quyền). Nếu KHÔNG có ủy quyền (tự nộp): người nộp CHÍNH LÀ chủ "
        "hồ sơ. IN HOA như CCCD."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh NGƯỜI NỘP (cá nhân), dd/mm/yyyy — CCCD / Giấy ủy quyền."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính NGƯỜI NỘP: "Nam"/"Nữ" — CCCD, hoặc suy từ danh xưng '
        'Ông/Bà trong Giấy ủy quyền.'},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND/định danh cá nhân NGƯỜI NỘP. Đọc CCCD hoặc Giấy "
        "ủy quyền (Bên B 'Căn cước công dân số'). Chỉ chữ số. Ưu tiên 12 chữ số."},
    {"name": "NguoiNop_MaSoThue", "desc": "Mã số thuế / mã định danh tổ chức NGƯỜI NỘP (CHỈ khi người nộp "
        "là TỔ CHỨC). Chỉ chữ số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD NGƯỜI NỘP, dd/mm/yyyy — mặt sau CCCD / Giấy ủy quyền."},
    {"name": "NguoiNop_NoiCap", "desc": 'Cơ quan cấp CCCD NGƯỜI NỘP — GHI ĐẦY ĐỦ, KHÔNG viết tắt. Giấy tờ '
        'hay ghi tắt "CCSQLHC TTXH" / "CCSVLHC TTXH" / "CCS QLHC về TTXH" / "Cục CSQLHC" → PHẢI ghi thành '
        '"Cục Cảnh sát quản lý hành chính về trật tự xã hội". Thẻ căn cước mới ghi "Bộ Công an".'},
    {"name": "NguoiNop_DiaChi", "desc": "Địa chỉ THƯỜNG TRÚ của CHÍNH NGƯỜI NỘP, object {quocGia,tinh,xa,"
        "diaChi}. CHỈ lấy ở CCCD người nộp (Nơi thường trú) hoặc Giấy ủy quyền (địa chỉ Bên được ủy quyền). "
        "⚠ Giấy giới thiệu THƯỜNG KHÔNG có địa chỉ thường trú → nếu không có, BỎ TRỐNG toàn bộ (đừng đoán). "
        "TUYỆT ĐỐI KHÔNG lấy địa chỉ thửa đất, trụ sở tổ chức, hay tỉnh của thửa đất làm địa chỉ người nộp. "
        "tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường/thôn."},
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

# ---- UI Form.io fields (data[...]) — comp dom-*. Contact block Y HỆT #75/chuyen_muc_dich + panel thửa đất.
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
