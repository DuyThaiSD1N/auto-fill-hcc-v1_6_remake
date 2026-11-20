"""Compact schema cho thủ tục 2.000076 — Đăng ký sang tên, di chuyển xe thực hiện tại Công an cấp tỉnh.

LLM chỉ trả dữ kiện nguồn đọc từ giấy tờ (tiền tố theo giấy); ô UI ``CongDan__fs*`` / ``CongDan_*`` do mapper dựng theo
file mapping "Mapping_Dang_ky_sang_ten_xe_o_to_BCA" (DOM ô tô, hai sheet: chủ xe tự nộp / người khai hộ).

Giấy tờ theo mapping: thẻ căn cước chủ xe (mới) · Giấy chứng nhận thu hồi đăng ký, biển số xe (GCN thu hồi) · Hợp đồng
mua bán xe có lời chứng công chứng (HĐMB) · Dữ liệu điện tử về lệ phí trước bạ (LPTB). Kịch bản khai hộ thêm giấy ủy
quyền làm thủ tục của chủ xe + thẻ căn cước người được ủy quyền; có khi kèm Giấy khai đăng ký xe, giấy phép kinh doanh
vận tải, giấy xác nhận trúng đấu giá biển số, trang thông tin hồ sơ (hình thức nhận kết quả).

Cố ý KHÔNG phát:
- Mã bảo mật (captcha) và nút Tra cứu — người dân tự nhập / bấm.
- Ô readonly / disabled cổng tự điền sau Tra cứu (chứng từ chuyển quyền sở hữu, số máy / số khung / loại xe / nhãn hiệu /
  số loại, khối lệ phí trước bạ điện tử, trạng thái LPTB), tên / mã điểm đăng ký, ô Quận/Huyện đang ẩn, ô kỹ thuật ẩn
  (đánh dấu tra cứu), nơi tạm trú / nơi ở hiện tại (giấy tờ không ghi).
- Chủ xe tự nộp: Mã định danh, Họ tên, Ngày sinh chủ xe cổng khoá theo tài khoản VNeID; khối người làm thủ tục bị khoá.
"""

FIELDS: list[dict] = [
    # Thẻ căn cước / CCCD của CHỦ XE (chủ xe mới khi sang tên; chủ xe khi di chuyển) — nguồn chuẩn cho nhân thân.
    {"name": "Cccd_HoTen", "desc": "Họ, chữ đệm và tên trên thẻ căn cước/CCCD của chủ xe."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh cá nhân / số CCCD trên thẻ, chỉ chữ số."},
    {"name": "Cccd_NgaySinh", "desc": "Ngày sinh trên thẻ, dd/mm/yyyy."},
    {"name": "Cccd_QuocTich", "desc": "Quốc tịch trên thẻ (vd \"Việt Nam\")."},
    {"name": "Cccd_NgayCap",
     "desc": "Ngày cấp thẻ (\"Ngày, tháng, năm cấp / Date of issue\" hoặc \"Ngày, tháng, năm\" mặt sau), dd/mm/yyyy. "
             "KHÔNG lấy ngày hết hạn / \"Có giá trị đến\"."},
    {"name": "Cccd_NoiCap",
     "desc": 'Cơ quan cấp thẻ in mặt sau: "BỘ CÔNG AN" → "Bộ Công an"; "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ '
             'TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},
    {"name": "Cccd_NoiCuTru",
     "desc": "Nơi cư trú / nơi thường trú IN TRÊN THẺ, object {quocGia,tinh,xa,chiTietDuoiXa}."},

    # Giấy chứng nhận thu hồi đăng ký, biển số xe.
    {"name": "GcnThuHoi_LyDo", "desc": "Dòng \"Lý do thu hồi\" (vd \"Chuyển quyền sở hữu\", \"Di chuyển\"), nguyên văn."},
    {"name": "GcnThuHoi_ChuXe", "desc": "Dòng \"Chủ xe\" (chủ xe CŨ, người bị thu hồi đăng ký) trên GCN thu hồi."},
    {"name": "GcnThuHoi_ChuXeMaDinhDanh",
     "desc": "\"Mã định danh\" trên dòng ngay dưới \"Chủ xe\" (của chủ xe CŨ), chỉ chữ số."},
    {"name": "GcnThuHoi_ChuXeNgayCap", "desc": "\"Ngày cấp\" cạnh mã định danh của chủ xe CŨ, dd/mm/yyyy."},
    {"name": "GcnThuHoi_ChuXeDienThoai", "desc": "\"Số điện thoại\" của chủ xe CŨ, chỉ chữ số."},
    {"name": "GcnThuHoi_DiaChiChuXe", "desc": "Dòng \"Địa chỉ\" ngay dưới \"Chủ xe\" (chủ xe CŨ), chuỗi nguyên văn."},
    {"name": "GcnThuHoi_ChuMoiHoTen", "desc": "Dòng \"Sang tên cho chủ xe mới (nếu có)\": họ tên chủ xe MỚI."},
    {"name": "GcnThuHoi_ChuMoiMaDinhDanh",
     "desc": "\"Mã định danh\" ở mục Sang tên cho chủ xe mới (KHÔNG lấy mã định danh của chủ xe cũ), chỉ chữ số."},
    {"name": "GcnThuHoi_ChuMoiDienThoai",
     "desc": "\"Số điện thoại\" ở mục Sang tên cho chủ xe mới, chỉ chữ số (chép đúng kể cả dãy toàn số 0)."},
    {"name": "GcnThuHoi_ChuMoiDiaChi",
     "desc": "\"Địa chỉ\" ở mục Sang tên cho chủ xe mới, object {quocGia,tinh,xa,chiTietDuoiXa}."},

    # Hợp đồng mua bán / tặng cho xe (công chứng).
    {"name": "Hdmb_BenBanHoTen",
     "desc": "Họ tên người ĐẦU TIÊN của BÊN BÁN / bên tặng cho (bên A). KHÔNG lấy người được ủy quyền ký thay."},
    {"name": "Hdmb_BenMuaHoTen", "desc": "Họ tên BÊN MUA / bên nhận (bên B)."},
    {"name": "Hdmb_BenMuaSoCccd", "desc": "\"Căn cước công dân số\" của bên mua, chỉ chữ số."},
    {"name": "Hdmb_BenMuaNgaySinh", "desc": "\"Sinh ngày\" của bên mua, dd/mm/yyyy."},
    {"name": "Hdmb_BenMuaNgayCapCccd", "desc": "Ngày cấp căn cước của bên mua (\"... cấp ngày dd/mm/yyyy\")."},
    {"name": "Hdmb_BenMuaNoiCapCccd",
     "desc": "Cơ quan cấp căn cước của bên mua (cụm sau chữ \"do\", vd \"Cục Cảnh sát quản lý hành chính về trật tự "
             "xã hội\")."},
    {"name": "Hdmb_BenMuaDiaChi",
     "desc": "\"Địa chỉ thường trú\" của bên mua, object {quocGia,tinh,xa,chiTietDuoiXa}."},

    # Dữ liệu điện tử về lệ phí trước bạ / Thông báo nộp lệ phí trước bạ.
    {"name": "Lptb_MaHoSo",
     "desc": "\"Mã hồ sơ lệ phí trước bạ\", chỉ chữ số. KHÔNG lấy \"Mã hồ sơ trực tuyến\" của GCN thu hồi."},
    {"name": "Lptb_TenNguoiNop", "desc": "\"Tên người nộp thuế\" / \"Tên người nộp\", chép đúng chữ hoa/thường."},
    {"name": "Lptb_MaDinhDanh", "desc": "\"Mã định danh\" của người nộp thuế, chỉ chữ số."},
    {"name": "Lptb_DienThoai", "desc": "\"Số điện thoại\" người nộp thuế, chỉ chữ số."},
    {"name": "Lptb_BienSo", "desc": "\"Biển số\" trên giấy LPTB nếu có ghi."},
    {"name": "Lptb_SoMay", "desc": "\"Số máy\" trên giấy LPTB, viết liền như trên giấy."},
    {"name": "Lptb_SoKhung", "desc": "\"Số khung\" trên giấy LPTB, viết liền như trên giấy."},

    # Đặc điểm xe theo giấy đăng ký — ưu tiên GCN thu hồi → HĐMB → Giấy khai.
    {"name": "Xe_BienSo", "desc": "Biển số xe đang đăng ký (biển số cũ), vd \"30A-123.45\", như trên giấy."},
    {"name": "Xe_MauBien",
     "desc": "\"Màu biển\" (màu nền và màu chữ của biển số, vd \"Nền màu trắng, chữ và số màu đen\"). KHÔNG lấy màu sơn."},
    {"name": "Xe_LoaiXe", "desc": "Loại xe (vd \"Ô tô con\", \"Xe mô tô hai bánh\")."},
    {"name": "Xe_SoKhung", "desc": "Số khung, viết liền chữ IN HOA và số như trên giấy."},
    {"name": "Xe_SoMay", "desc": "Số máy / số động cơ, viết liền như trên giấy."},

    # Giấy khai đăng ký xe (nếu hồ sơ có).
    {"name": "ToKhai_TenChuXe", "desc": "Dòng \"Tên chủ xe\" của Giấy khai đăng ký xe."},
    {"name": "ToKhai_DiaChi",
     "desc": "Dòng \"Địa chỉ\" của chủ xe trên Giấy khai đăng ký xe, object {quocGia,tinh,xa,chiTietDuoiXa}."},
    {"name": "ToKhai_DienThoai", "desc": "Dòng \"Điện thoại\" của chủ xe trên Giấy khai; bỏ dấu chấm/khoảng trắng."},
    {"name": "ToKhai_Email", "desc": "Email chủ xe nếu Giấy khai có ghi. Không có → bỏ field."},

    # Giấy / hợp đồng ủy quyền làm thủ tục đăng ký xe của CHỦ XE (kịch bản khai hộ).
    {"name": "UyQuyen_BenUyQuyenHoTen", "desc": "Họ tên bên ủy quyền (chủ xe) trên giấy ủy quyền làm thủ tục đăng ký xe."},
    {"name": "UyQuyen_HoTen", "desc": "Họ tên bên ĐƯỢC ủy quyền làm thủ tục đăng ký xe."},
    {"name": "UyQuyen_SoDinhDanh", "desc": "Số CCCD / định danh của bên được ủy quyền, chỉ chữ số."},
    {"name": "UyQuyen_NgayCap", "desc": "Ngày cấp giấy tờ tùy thân của bên được ủy quyền, dd/mm/yyyy."},
    {"name": "UyQuyen_NoiCap", "desc": "Cơ quan cấp giấy tờ tùy thân của bên được ủy quyền (cụm sau chữ \"do\")."},
    {"name": "UyQuyen_DienThoai", "desc": "Số điện thoại của bên được ủy quyền nếu có ghi, chỉ chữ số."},
    {"name": "UyQuyen_Email", "desc": "Email của bên được ủy quyền nếu có ghi."},

    # Thẻ căn cước của NGƯỜI LÀM THỦ TỤC (người được chủ xe ủy quyền / người khai hộ), không phải chủ xe.
    {"name": "CccdNduq_HoTen", "desc": "Họ tên trên thẻ căn cước của người được chủ xe ủy quyền làm thủ tục."},
    {"name": "CccdNduq_SoDinhDanh", "desc": "Số định danh trên thẻ đó, chỉ chữ số."},
    {"name": "CccdNduq_NgayCap", "desc": "Ngày cấp thẻ đó, dd/mm/yyyy."},
    {"name": "CccdNduq_NoiCap", "desc": "Cơ quan cấp thẻ đó (quy đổi như Cccd_NoiCap)."},

    # Giấy phép kinh doanh vận tải bằng xe ô tô (chỉ khi hồ sơ có).
    {"name": "GpKdvt_SoGiayPhep", "desc": "Số giấy phép kinh doanh vận tải bằng xe ô tô."},
    {"name": "GpKdvt_NgayCap", "desc": "Ngày cấp giấy phép kinh doanh vận tải, dd/mm/yyyy."},
    {"name": "GpKdvt_NoiCap", "desc": "Cơ quan cấp giấy phép kinh doanh vận tải (vd \"Sở Xây dựng tỉnh ...\")."},

    # Giấy xác nhận trúng đấu giá biển số xe (chỉ khi hồ sơ có).
    {"name": "DauGia_BienSo", "desc": "Biển số trúng đấu giá trên giấy xác nhận trúng đấu giá biển số xe."},
    {"name": "DauGia_SoGiay", "desc": "Số giấy xác nhận trúng đấu giá biển số."},
    {"name": "DauGia_NgayCap", "desc": "Ngày cấp giấy xác nhận trúng đấu giá, dd/mm/yyyy."},
    {"name": "DauGia_CoQuanCap", "desc": "Cơ quan cấp giấy xác nhận trúng đấu giá."},

    # Trang thông tin hồ sơ (nếu có).
    {"name": "HoSo_HinhThucNhanKetQua",
     "desc": "\"Hình thức nhận kết quả\" nếu hồ sơ có ghi (vd \"Qua dịch vụ bưu chính công ích\", \"Trực tiếp tại cơ "
             "quan\"). Không có → bỏ field."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Cccd_NgaySinh", "Cccd_NgayCap", "GcnThuHoi_ChuXeNgayCap", "Hdmb_BenMuaNgaySinh", "Hdmb_BenMuaNgayCapCccd",
    "UyQuyen_NgayCap", "CccdNduq_NgayCap", "GpKdvt_NgayCap", "DauGia_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Cccd_NoiCuTru", "GcnThuHoi_ChuMoiDiaChi", "Hdmb_BenMuaDiaChi", "ToKhai_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô form theo file mapping (name trong DOM, số trong ngoặc là STT mapping). <select> + bootstrap-select → dom-select;
# ô tích iCheck → dom-checkbox; còn lại dom-input. Ô ngày "custom datetime" của form-builder nhận gõ dd/mm/yyyy.
UI_COMP_BY_NAME = {
    # Phần I — đối tượng nộp hồ sơ (chọn 1 trong 2; "khai hộ" mở khối người làm thủ tục).
    "CongDan__fsLaChuXe": "dom-checkbox",            # (1) Người nộp hồ sơ là chủ xe
    "CongDan__fsLaNguoiKhaiHo": "dom-checkbox",      # (2) Người nộp hồ sơ là người khai hộ
    # Phần II — tra cứu thông tin xe (người dân tự nhập Mã bảo mật rồi bấm Tra cứu).
    "CongDan__fstracuuLoaiDangKy": "dom-select",     # (3) Loại đăng ký (*)
    "CongDan__fsRadioLoaiXe": "dom-select",          # (4) Loại xe (*) — option "Xe máy" / "Ô tô"
    "CongDan__fstracuuMauBien": "dom-select",        # (5) Màu biển (*)
    "CongDan__fstracuuBienSo": "dom-input",          # (6) Biển số cũ (*)
    "CongDan__fstracuuSoKhung": "dom-input",         # (7) Số khung (*)
    "CongDan__fstracuuSoMay": "dom-input",           # (8) Số máy (*)
    "CongDan__fsTraCuMaHsLPTB": "dom-input",         # (9) Mã hồ sơ lệ phí trước bạ (*)
    # Phần III — thông tin chủ xe. Ba ô đầu chỉ phát khi khai hộ (chủ xe tự nộp: cổng khoá theo tài khoản).
    "CongDan_soCmnd": "dom-input",                   # (12) Mã định danh của chủ xe (*)
    "CongDan__fsLoaiGiayToChuXe": "dom-select",      # (13) Loại giấy tờ (*)
    "CongDan__fsngayCapCmnd": "dom-input",           # (14) Cấp ngày (*)
    "CongDan__fsnoiCapCmnd": "dom-input",            # (15) Nơi cấp (*)
    "CongDan_tenCongDan": "dom-input",               # (16) Họ và tên chủ xe (*)
    "CongDan__fsnamSinh": "dom-input",               # (17) Ngày/tháng/Năm sinh (*)
    "CongDan__fsQuocTichChuXe": "dom-select",        # (18) Quốc tịch (*)
    "CongDan__fsBCAHKTTTinh": "dom-select",          # (21) Tỉnh/Thành phố thường trú (*)
    "CongDan__fsBCAHKTTXa": "dom-select",            # (23) Phường/Xã thường trú — nạp theo Tỉnh
    "CongDan__fsBCAHKTTDCChiTiet": "dom-input",      # (24) Nơi thường trú (số nhà/tên đường) (*)
    "CongDan_diDong": "dom-input",                   # (30) Số điện thoại của chủ xe (*)
    "CongDan_email": "dom-input",                    # (31) Email của chủ xe
    # Phần IV — người được ủy quyền làm thủ tục (chỉ mở khi tích "người khai hộ").
    "CongDan__fsNDUQHoTen": "dom-input",             # (32)
    "CongDan__fsNDUQMaDinhDanh": "dom-input",        # (33) (*)
    "CongDan__fsNDUQLoaiGiayTo": "dom-select",       # (34) (*) — option như (13)
    "CongDan__fsNDUQNgayCap": "dom-input",           # (35) (*)
    "CongDan__fsNDUQCoQuanCap": "dom-input",         # (36) (*)
    "CongDan__fsDiDongNDUQ": "dom-input",            # (37) (*)
    "CongDan__fsEmailNDUQ": "dom-input",             # (38)
    # Phần V — kinh doanh vận tải (3 ô giấy phép chỉ mở khi chọn "Có kinh doanh vận tải").
    "CongDan__fsCoKinhDoanhvanTai": "dom-select",    # (42)
    "CongDan__fsSoGiayPhepKinhDoanh": "dom-input",   # (43)
    "CongDan__fsngayCapGPKD": "dom-input",           # (44)
    "CongDan__fsNoiCapGPKD": "dom-input",            # (45)
    # Phần VII — biển số trúng đấu giá.
    "CongDan__fs359581_checkbox_1": "dom-checkbox",  # (62) Là biển số đấu giá
    "CongDan__fsBienSoTrungDauGia": "dom-input",     # (63)
    "CongDan__fsSoGiayXnTrungDauGia": "dom-input",   # (64)
    "CongDan__fsNGayCapBienDauGia": "dom-input",     # (65)
    "CongDan__fsCoQuanCapBienDauGia": "dom-input",   # (66)
    # Phần VIII — hình thức nhận kết quả. Tỉnh phát TRƯỚC Xã (danh mục xã nạp theo tỉnh).
    "CongDan__fsHinhThucNhanKQ": "dom-select",       # (67) (*)
    "CongDan__fsTenNguoiNhanKQ": "dom-input",        # (68)
    "CongDan__fsSoDienThoaiNguoiNhan": "dom-input",  # (69)
    "CongDan__fsTinhNhanKQ": "dom-select",           # (70)
    "CongDan__fsXaNhanKQ": "dom-select",             # (72)
    "CongDan__fsDiaChiChiTietNhanKQ": "dom-input",   # (73)
}

# Ô có danh sách nạp chậm qua API → extension chờ thêm tới waitMs (ms) rồi thử lại (content.js / fill-core.js). Ô Xã
# nhận kết quả đã được extension nhận là ô địa chỉ (tinhnhankq/xanhankq); ô Xã thường trú thì chưa.
WAIT_MS = {
    "CongDan__fsBCAHKTTXa": 8000,
}

# Option đúng chữ trên cổng (mapping).
LOAI_DANG_KY = {"sang_ten": "Đăng ký sang tên xe", "di_chuyen": "Đăng ký di chuyển xe"}
MAU_BIEN = {
    "trang": "Nền màu trắng, chữ và số màu đen",
    "xanh": "Nền màu xanh, chữ và số màu trắng",
    "vang_den": "Nền màu vàng, chữ và số màu đen",
    "vang_do": "Nền màu vàng, chữ và số màu đỏ",
}
KINH_DOANH_VAN_TAI = {"co": "Có kinh doanh vận tải", "khong": "Không kinh doanh vận tải"}
