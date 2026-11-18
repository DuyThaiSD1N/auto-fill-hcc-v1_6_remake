"""Compact schema cho thủ tục 2.001428 — Đăng ký mẫu con dấu mới (thực hiện tại cấp tỉnh).

LLM chỉ trả dữ kiện nguồn đọc từ giấy tờ (tiền tố theo giấy); ô UI ``CongDan__fs*`` / ``CongDan_*`` do mapper dựng
theo file mapping "Mapping_Dang_ky_mau_con_dau_moi" (24 ô, khớp schema nhúng trong trang).

Giấy tờ: Văn bản đề nghị đăng ký mẫu con dấu (Mẫu số 03, nguồn thao tác chính — nhãn khớp form) · Quyết định thành
lập / cho phép hoạt động của cơ quan, tổ chức · Văn bản của cơ quan có thẩm quyền đồng ý khắc dấu (vd công văn của Ban
tổ chức cấp ủy cấp trên) · thẻ căn cước / CCCD của người được giới thiệu nộp hồ sơ (có thể có).

Cố ý KHÔNG phát:
- Tên cơ sở sản xuất con dấu (18) — danh mục cổng, giấy tờ không có; Thông tin liên hệ cơ sở (19), Phí bưu chính (24)
  — cổng tự điền.
- Hình thức nhận kết quả (22) / Địa chỉ nhận kết quả (23) — giấy tờ không ghi; người nộp tự chọn.
- Khối tra cứu doanh nghiệp (#form-search-dn) — chỉ hiện với cơ quan Sở Công thương / TT&TT…, không áp dụng Công an.
"""

FIELDS: list[dict] = [
    # Thẻ căn cước / CCCD — CHỈ của người được giới thiệu/ủy quyền nộp hồ sơ (mục 6 văn bản đề nghị).
    {"name": "Cccd_HoTen", "desc": "Họ, chữ đệm và tên trên thẻ căn cước/CCCD."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh cá nhân / số CCCD trên thẻ, chỉ chữ số."},
    {"name": "Cccd_NgaySinh", "desc": "Ngày sinh trên thẻ, dd/mm/yyyy."},
    {"name": "Cccd_GioiTinh", "desc": 'Giới tính trên thẻ: "Nam" hoặc "Nữ".'},
    {"name": "Cccd_NgayCap",
     "desc": "Ngày cấp thẻ (\"Ngày, tháng, năm cấp / Date of issue\" hoặc \"Ngày, tháng, năm\" mặt sau), dd/mm/yyyy. "
             "KHÔNG lấy ngày hết hạn / \"Có giá trị đến\"."},
    {"name": "Cccd_NoiCap",
     "desc": 'Cơ quan cấp in mặt sau: "BỘ CÔNG AN" → "Bộ Công an"; "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ '
             'TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},

    # Văn bản đề nghị đăng ký mẫu con dấu (Mẫu số 03).
    {"name": "VanBan_KinhGui",
     "desc": "Cơ quan Công an ở dòng \"Kính gửi\" của văn bản đề nghị, chép nguyên tên (vd \"Công an tỉnh X\")."},
    {"name": "VanBan_So", "desc": "Số của văn bản đề nghị dưới tên cơ quan ban hành (vd \"05-CV/ĐU\"), chép đúng ký tự."},
    {"name": "VanBan_TenCoQuanBanHanh",
     "desc": "Tên cơ quan, tổ chức ban hành văn bản đề nghị ở góc trên bên trái (dòng in đậm ngay trên số văn bản), "
             "KHÔNG lấy dòng cơ quan cấp trên phía trên nó."},
    {"name": "VanBan_TenToChuc",
     "desc": "Mục 1 \"Cơ quan, tổ chức đề nghị đăng ký mẫu con dấu\" — dòng \"Tên cơ quan, tổ chức\", chép nguyên văn "
             "(giữ chữ viết tắt như trên giấy), bỏ dấu \";\" cuối."},
    {"name": "VanBan_DiaChiToChuc",
     "desc": "Mục 1 — dòng \"Địa chỉ\" của cơ quan, tổ chức, object {quocGia,tinh,xa,chiTietDuoiXa}; chiTietDuoiXa là "
             "phần đứng trước xã/phường (thôn, bản, tổ, số nhà, đường)."},
    {"name": "VanBan_SoDinhDanhToChuc",
     "desc": "Mục 1 — \"Số định danh của cơ quan, tổ chức\". Dòng để trống → bỏ field. KHÔNG lấy số định danh ở mục 3 "
             "(cơ quan quản lý trực tiếp) hay số giấy tờ của người."},
    {"name": "VanBan_DienThoaiToChuc", "desc": "Mục 1 — \"Số điện thoại\" của cơ quan, tổ chức. Trống → bỏ field."},
    {"name": "VanBan_EmailToChuc",
     "desc": "Mục 1 — \"Website/địa chỉ thư điện tử\": CHỈ địa chỉ email (có @). Website hoặc trống → bỏ field."},
    {"name": "VanBan_LoaiHinhToChuc",
     "desc": "Loại hình cơ quan, tổ chức đề nghị, CHỌN ĐÚNG MỘT chữ trong danh sách: "
             "\"Tổ chức Đảng\" (đảng ủy, đảng bộ, chi bộ, cơ quan của cấp ủy đảng; văn bản có quốc hiệu \"ĐẢNG CỘNG SẢN "
             "VIỆT NAM\"); \"Cơ quan có chức năng quản lý nhà nước, cơ quan chuyên môn\" (UBND, sở, phòng, ban của "
             "chính quyền); \"Tổ chức sự nghiệp\" (trường học, bệnh viện, trung tâm công lập); \"Mặt trận Tổ quốc Việt "
             "Nam, tổ chức chính trị - xã hội, tổ chức chính trị xã hội - nghề nghiệp, tổ chức xã hội, tổ chức xã hội - "
             "nghề nghiệp, quỹ xã hội, quỹ từ thiện, tổ chức phi chính phủ\" (Mặt trận, Đoàn TN, Hội LHPN, Hội Nông "
             "dân, Hội CCB, Công đoàn, hội, quỹ); \"Doanh nghiệp, hợp tác xã, liên hiệp hợp tác xã; chi nhánh, văn phòng "
             "đại diện của doanh nghiệp, hợp tác xã, liên hiệp hợp tác xã\"; \"Tổ chức tôn giáo\"; \"Tổ chức khác được "
             "thành lập, hoạt động theo quy định của pháp luật\". Không chắc → bỏ field."},
    {"name": "VanBan_NguoiDungDau_HoTen", "desc": "Mục 2 \"Người đứng đầu cơ quan, tổ chức\" — Họ và tên."},
    {"name": "VanBan_NguoiDungDau_NgaySinh", "desc": "Mục 2 — Ngày, tháng, năm sinh, dd/mm/yyyy."},
    {"name": "VanBan_NguoiDungDau_GioiTinh", "desc": "Mục 2 — Giới tính: \"Nam\" hoặc \"Nữ\"."},
    {"name": "VanBan_NguoiDungDau_SoGiayTo", "desc": "Mục 2 — \"Số CC/CCCD/HC\", chỉ chữ số (hộ chiếu giữ chữ cái)."},
    {"name": "VanBan_NguoiDungDau_NgayCap", "desc": "Mục 2 — \"Ngày cấp\", dd/mm/yyyy."},
    {"name": "VanBan_NguoiDungDau_NoiCap", "desc": "Mục 2 — \"Nơi cấp\", chép nguyên văn."},
    {"name": "VanBan_NoiDungDeNghi",
     "desc": "Mục 5 \"Nội dung đề nghị thực hiện thủ tục đăng ký mẫu con dấu\" — dòng nội dung ngay dưới tiêu đề mục "
             "(vd \"Đăng ký mẫu con dấu mới\"), KHÔNG gồm dòng \"Lý do\"."},
    {"name": "VanBan_LyDo", "desc": "Mục 5 — phần sau chữ \"Lý do:\", chép nguyên văn."},
    {"name": "VanBan_TaiLieuKemTheo",
     "desc": "Mục 5 — danh sách \"Các tài liệu trong hồ sơ gửi kèm theo\": chép NGUYÊN VĂN, ĐỦ CHỮ từng gạch đầu dòng "
             "(giữ \"- \" đầu dòng và dấu \";\" / \".\" cuối), mỗi tài liệu một dòng, nối bằng ký tự xuống dòng \\n. Không "
             "tóm tắt, không thêm tài liệu không có trong danh sách."},
    {"name": "VanBan_NguoiNop_HoTen",
     "desc": "Mục 6 \"Người được giới thiệu/uỷ quyền liên hệ nộp hồ sơ\" — Họ và tên."},
    {"name": "VanBan_NguoiNop_NgaySinh", "desc": "Mục 6 — Ngày, tháng, năm sinh, dd/mm/yyyy."},
    {"name": "VanBan_NguoiNop_GioiTinh", "desc": "Mục 6 — Giới tính: \"Nam\" hoặc \"Nữ\"."},
    {"name": "VanBan_NguoiNop_SoGiayTo", "desc": "Mục 6 — \"Số CC/CCCD/HC\", chỉ chữ số (hộ chiếu giữ chữ cái)."},
    {"name": "VanBan_NguoiNop_NgayCap", "desc": "Mục 6 — \"Ngày cấp\", dd/mm/yyyy."},
    {"name": "VanBan_NguoiNop_NoiCap", "desc": "Mục 6 — \"Nơi cấp\", chép nguyên văn."},
    {"name": "VanBan_NguoiNop_DienThoai",
     "desc": "Mục 6 — \"Số điện thoại liên hệ\", chỉ chữ số. KHÔNG lấy số điện thoại cơ quan ở mục 1."},

    # Quyết định thành lập / cho phép hoạt động.
    {"name": "QuyetDinh_So", "desc": "Số quyết định (vd \"12-QĐ/ĐU\", \"345/QĐ-UBND\"), chép đúng ký tự."},
    {"name": "QuyetDinh_Ngay", "desc": "Ngày ban hành quyết định (dòng \"<địa danh>, ngày ... tháng ... năm ...\"), dd/mm/yyyy."},
    {"name": "QuyetDinh_CoQuanBanHanh",
     "desc": "Cơ quan ban hành quyết định ở góc trên bên trái (dòng in đậm ngay trên số quyết định), viết hoa/thường "
             "như câu văn, giữ hoa tên riêng (vd \"ĐẢNG ỦY XÃ AN BÌNH\" → \"Đảng ủy xã An Bình\")."},
    {"name": "QuyetDinh_TrichYeu",
     "desc": "Trích yếu dưới chữ \"QUYẾT ĐỊNH\" (vd \"thành lập ...\"), chép nguyên văn trên một dòng."},

    # Văn bản đồng ý khắc dấu của cơ quan có thẩm quyền (vd công văn Ban Tổ chức cấp ủy cấp trên).
    {"name": "CongVan_So", "desc": "Số công văn (vd \"123-CV/BTCTU\"), chép đúng ký tự."},
    {"name": "CongVan_Ngay", "desc": "Ngày ban hành công văn (dòng \"<địa danh>, ngày ... tháng ... năm ...\"), dd/mm/yyyy."},
    {"name": "CongVan_CoQuanBanHanh",
     "desc": "Cơ quan ban hành công văn ở góc trên bên trái, ghép đủ các dòng, viết hoa/thường như câu văn (vd "
             "\"TỈNH ỦY AN BÌNH\" + \"BAN TỔ CHỨC\" → \"Ban Tổ chức Tỉnh ủy An Bình\")."},
    {"name": "CongVan_TrichYeu", "desc": "Dòng \"V/v ...\" của công văn, bỏ chữ \"V/v\", chép nguyên văn trên một dòng."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Cccd_NgaySinh", "Cccd_NgayCap", "VanBan_NguoiDungDau_NgaySinh", "VanBan_NguoiDungDau_NgayCap",
    "VanBan_NguoiNop_NgaySinh", "VanBan_NguoiNop_NgayCap", "QuyetDinh_Ngay", "CongVan_Ngay",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
COMPACT_COMP_BY_NAME["VanBan_DiaChiToChuc"] = "x-select-area"

# Ô form theo file mapping (name trong DOM). <select> (native hoặc bootstrap-select) → dom-select; còn lại dom-input
# (ô ngày date-picker của form-builder nhận gõ dd/mm/yyyy như eForm Lai Châu; textarea cũng là dom-input). Thứ tự
# phát theo thứ tự trên form: Loại hình (2) trước Mã định danh (3) vì script cổng bật/tắt bắt buộc ô (3) theo (2);
# Tỉnh (7) trước Xã (8) vì danh mục xã nạp qua API theo tỉnh.
UI_COMP_BY_NAME = {
    "CongDan__fs_BCANoiNopHS": "dom-select",         # (1) Chọn nơi tiếp nhận hồ sơ (*) — bootstrap-select
    "CongDan__fsLoaiHinhToChuc": "dom-select",       # (2) Loại hình cơ quan/tổ chức (*) — có / không mã định danh
    "CongDan__fs_BCAMaDinhDanh": "dom-input",        # (3) Mã định danh điện tử cơ quan tổ chức
    "CongDan__fs_BCATenCQDangKy": "dom-input",       # (4) Tên cơ quan, tổ chức đề nghị đăng ký mẫu con dấu (*)
    "CongDan__fs_BCATruongHop": "dom-select",        # (5) Loại hình Cơ quan/Tổ chức (*) — bootstrap-select, 14 option
    "CongDan__fs_BCADiaChiCQDangKy": "dom-input",    # (6) Địa chỉ (*) — phần chi tiết dưới xã
    "CongDan__fs_BCAQueQuanMaTinh": "dom-select",    # (7) Tỉnh/thành phố (*) — tỉnh của ĐỊA CHỈ CƠ QUAN
    "CongDan__fs_BCAQueQuanMaPX": "dom-select",      # (8) Phường/xã/thị trấn (*) — nạp theo tỉnh
    "CongDan_tenCongDan": "dom-input",               # (9) Họ và tên (*) — người nộp (mục 6)
    "CongDan_diDong": "dom-input",                   # (10) Số điện thoại liên hệ (*)
    "CongDan_email": "dom-input",                    # (11) Email
    "CongDan_soCmnd": "dom-input",                   # (12) Số CCCD/CMND/Hộ chiếu (*)
    "CongDan__fs_BCANgayCapCMND": "dom-input",       # (13) Ngày cấp (*)
    "CongDan__fs_BCANoiCapCMND": "dom-input",        # (14) Nơi cấp (*)
    "CongDan__fsNgaySinh": "dom-input",              # (15) Ngày sinh (*)
    "CongDan__fsDangKyDauGioiTinh": "dom-select",    # (16) Giới tính (*)
    "CongDan__fs_BCALoaiHinhConDau": "dom-select",   # (17) Loại hình con dấu (*)
    "CongDan__fs_BCANoiDungYeuCauGQ": "dom-input",   # (20) Nội dung yêu cầu giải quyết (*) — textarea
    "CongDan__fs_BCATenGiayToTaiLieu": "dom-input",  # (21) Các giấy tờ tài liệu có trong hồ sơ (*) — textarea
}

# Ô có danh sách nạp chậm qua API → extension chờ thêm tới waitMs (ms) rồi thử lại (content.js / fill-core.js).
WAIT_MS = {
    "CongDan__fs_BCATruongHop": 6000,     # (5) nạp lại sau khi chọn Nơi tiếp nhận (1)
    "CongDan__fs_BCAQueQuanMaPX": 8000,   # (8) Phường/xã nạp theo Tỉnh (7)
}

# Option đúng chữ trên cổng (mapping).
LOAI_HINH_CO_MA = "Cơ quan tổ chức có mã định danh"
LOAI_HINH_KHAC = "Cơ quan tổ chức khác"

TRUONG_HOP_DANG = "Tổ chức Đảng"
# Option ô (5) "Loại hình Cơ quan/Tổ chức" mà LLM được phép chọn (bỏ các option đặc thù: Quốc huy, Ban chỉ huy quân
# sự, Công an nhân dân, tổ chức nước ngoài, tổ chức trực thuộc… — giấy tờ không đủ để suy, người nộp chọn tay).
TRUONG_HOP_OPTIONS = (
    TRUONG_HOP_DANG,
    "Cơ quan có chức năng quản lý nhà nước, cơ quan chuyên môn",
    "Tổ chức sự nghiệp",
    "Mặt trận Tổ quốc Việt Nam, tổ chức chính trị - xã hội, tổ chức chính trị xã hội - nghề nghiệp, tổ chức xã hội, "
    "tổ chức xã hội - nghề nghiệp, quỹ xã hội, quỹ từ thiện, tổ chức phi chính phủ",
    "Doanh nghiệp, hợp tác xã, liên hiệp hợp tác xã; chi nhánh, văn phòng đại diện của doanh nghiệp, hợp tác xã, liên "
    "hiệp hợp tác xã",
    "Tổ chức tôn giáo",
    "Tổ chức khác được thành lập, hoạt động theo quy định của pháp luật",
)

# Option ô (17) "Loại hình con dấu".
CON_DAU_KHAC = "Con dấu của các cơ quan, tổ chức khác."
CON_DAU_DANG_TRUNG_UONG = "Con dấu của các Đảng ủy và các cơ quan Đảng trực thuộc Trung ương"
CON_DAU_BCH_TRUNG_UONG = "Con dấu của Ban chấp hành Trung ương"
