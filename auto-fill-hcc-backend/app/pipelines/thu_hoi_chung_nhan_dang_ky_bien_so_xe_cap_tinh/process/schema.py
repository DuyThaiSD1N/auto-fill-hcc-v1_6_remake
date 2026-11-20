"""Compact schema cho thủ tục 2.001485 — Thu hồi chứng nhận đăng ký xe, biển số xe thực hiện tại Công an cấp tỉnh.

LLM chỉ trả dữ kiện nguồn đọc từ giấy tờ (tiền tố theo giấy); ô UI ``CongDan__fs*`` / ``CongDan_*`` do mapper dựng theo
file mapping "Mapping_Thu_hoi_CNDK_BSX" (form-builder Nth cổng DVC Bộ Công an, bước kê khai "Nộp hồ sơ trực tuyến").

Giấy tờ theo mapping: Giấy chứng nhận đăng ký xe (Giấy ĐKX, có khi chỉ ảnh một phần) · Hợp đồng mua bán xe có lời chứng
công chứng viên (HĐMB) · thẻ căn cước / CCCD của chủ xe, bên mua. Thêm khi có: Giấy khai thu hồi chứng nhận đăng ký xe,
biển số xe (Mẫu ĐKX011 — lý do thu hồi, liên hệ chủ xe), giấy ủy quyền của chủ xe + thẻ người được ủy quyền (khai hộ).

Cố ý KHÔNG phát:
- Mã bảo mật (captcha) và nút Tra cứu — người dân tự nhập / bấm.
- Tên / mã điểm đăng ký (hệ thống tự gán), Loại xe Phần VI (JS gán theo ô Ô tô / Xe máy), ô Quận/Huyện đang ẩn, ô kỹ
  thuật ẩn Phần VIII, nơi tạm trú / nơi ở hiện tại (giấy tờ không ghi).
- Chủ xe tự nộp: Mã định danh, Họ tên, Ngày sinh chủ xe cổng khoá theo tài khoản VNeID; khối người làm thủ tục bị khoá.
"""

_CARD_ISSUER = (
    'Cơ quan cấp thẻ in mặt sau: "BỘ CÔNG AN" → "Bộ Công an"; "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ '
    'HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội".'
)
_CARD_ISSUE_DATE = (
    "Ngày cấp thẻ (\"Ngày, tháng, năm cấp / Date of issue\" hoặc \"Ngày, tháng, năm\" mặt sau), dd/mm/yyyy. KHÔNG lấy "
    "ngày hết hạn / \"Có giá trị đến\"."
)

FIELDS: list[dict] = [
    # Giấy chứng nhận đăng ký xe — chủ xe đang đứng tên + đặc điểm xe (ưu tiên 1 cho thông tin xe).
    {"name": "Dkx_TenChuXe", "desc": "\"Tên chủ xe (Owner's full name)\" trên Giấy chứng nhận đăng ký xe."},
    {"name": "Dkx_BienSo", "desc": "\"Biển số đăng ký (N°Plate)\", vd \"30A-123.45\", như trên giấy."},
    {"name": "Dkx_MauBien",
     "desc": "Màu biển số: chữ trong ngoặc ngay sau nhãn \"Biển số đăng ký (N°Plate)\" (vd \"T\") hoặc dòng \"Màu biển\" "
             "(vd \"Nền màu vàng, chữ và số màu đen\"), chép nguyên văn. KHÔNG lấy \"Màu sơn\"."},
    {"name": "Dkx_LoaiXe", "desc": "\"Loại xe (Type)\" (vd \"Ô tô con\", \"Xe mô tô hai bánh\")."},
    {"name": "Dkx_NhanHieu", "desc": "\"Nhãn hiệu (Brand)\"."},
    {"name": "Dkx_SoLoai", "desc": "\"Số loại (Model code)\", bỏ dấu chấm cuối dòng."},
    {"name": "Dkx_SoKhung",
     "desc": "\"Số khung (Chassis N°)\", viết liền như trên giấy; phần bị che / cắt mất thì chỉ chép phần đọc được."},
    {"name": "Dkx_SoMay", "desc": "\"Số máy (Engine N°)\", viết liền như trên giấy."},
    {"name": "Dkx_DungTich", "desc": "\"Dung tích (Capacity)\" (vd \"1368\")."},
    {"name": "Dkx_CongSuat", "desc": "\"Công suất\" nếu giấy có ghi."},
    {"name": "Dkx_TaiTrong", "desc": "Tải trọng hàng hóa (kg) nếu có ghi số; dòng để trống → bỏ field."},
    {"name": "Dkx_SoChoNgoi", "desc": "\"Số chỗ ngồi (Sit)\"."},
    {"name": "Dkx_SoChoDung", "desc": "\"đứng (Stand)\" nếu có ghi số; để trống → bỏ field."},
    {"name": "Dkx_SoChoNam", "desc": "\"nằm (Lie)\" nếu có ghi số; để trống → bỏ field."},
    {"name": "Dkx_NamSanXuat", "desc": "\"Năm sản xuất\" nếu giấy có ghi (4 chữ số). KHÔNG lấy năm đăng ký."},

    # Hợp đồng mua bán / tặng cho xe (kèm lời chứng công chứng viên).
    {"name": "Hdmb_TenVanBan", "desc": "Tên văn bản ở đầu hợp đồng (vd \"HỢP ĐỒNG MUA BÁN XE Ô TÔ\")."},
    {"name": "Hdmb_BenBanHoTen",
     "desc": "Họ tên người ĐẦU TIÊN của BÊN BÁN / bên tặng cho (bên A). KHÔNG lấy vợ/chồng cùng bên A hay người được ủy "
             "quyền ký thay."},
    {"name": "Hdmb_BenBanSoCccd", "desc": "\"Căn cước công dân số\" của người đầu tiên bên bán, chỉ chữ số."},
    {"name": "Hdmb_BenBanNgaySinh", "desc": "\"Sinh ngày\" của người đầu tiên bên bán, dd/mm/yyyy."},
    {"name": "Hdmb_BenBanNgayCapCccd", "desc": "Ngày cấp căn cước của người đầu tiên bên bán (\"... cấp ngày\")."},
    {"name": "Hdmb_BenBanNoiCapCccd", "desc": "Cơ quan cấp căn cước của người đầu tiên bên bán (cụm sau chữ \"do\")."},
    {"name": "Hdmb_BenBanDiaChi",
     "desc": "\"Địa chỉ thường trú\" của người đầu tiên bên bán, object {quocGia,tinh,xa,chiTietDuoiXa}."},
    {"name": "Hdmb_BenMuaHoTen", "desc": "Họ tên BÊN MUA / bên nhận (bên B)."},
    {"name": "Hdmb_BenMuaSoCccd", "desc": "\"Căn cước công dân số\" của bên mua, chỉ chữ số."},
    {"name": "Hdmb_BenMuaNgayCapCccd", "desc": "Ngày cấp căn cước của bên mua (\"... cấp ngày\"), dd/mm/yyyy."},
    {"name": "Hdmb_BenMuaNoiCapCccd", "desc": "Cơ quan cấp căn cước của bên mua (cụm sau chữ \"do\")."},
    {"name": "Hdmb_BenMuaDiaChi",
     "desc": "\"Địa chỉ thường trú\" của bên mua, object {quocGia,tinh,xa,chiTietDuoiXa}."},
    {"name": "Hdmb_BienSo", "desc": "Biển số xe ghi ở Điều 1 hợp đồng (\"mang biển số đăng ký\")."},
    {"name": "Hdmb_LoaiXe", "desc": "\"Loại xe\" ở phần đặc điểm xe của hợp đồng (vd \"Ô tô con\")."},
    {"name": "Hdmb_NhanHieu", "desc": "Nhãn hiệu xe ghi trong hợp đồng."},
    {"name": "Hdmb_SoLoai", "desc": "\"Số loại\" xe ghi trong hợp đồng."},
    {"name": "Hdmb_SoKhung", "desc": "\"Số khung\" trong hợp đồng, viết liền đủ ký tự."},
    {"name": "Hdmb_SoMay", "desc": "\"Số máy\" trong hợp đồng, viết liền đủ ký tự."},
    {"name": "Hdmb_DungTich", "desc": "\"Dung tích\" trong hợp đồng (vd \"1368 cm3\")."},
    {"name": "Hdmb_SoChoNgoi", "desc": "\"Số chỗ ngồi\" trong hợp đồng."},

    # Thẻ căn cước / CCCD của CHỦ XE (người đứng tên trên Giấy chứng nhận đăng ký xe).
    {"name": "Cccd_HoTen", "desc": "Họ, chữ đệm và tên trên thẻ căn cước/CCCD của chủ xe."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh cá nhân / số CCCD trên thẻ, chỉ chữ số."},
    {"name": "Cccd_NgaySinh", "desc": "Ngày sinh trên thẻ, dd/mm/yyyy."},
    {"name": "Cccd_QuocTich", "desc": "Quốc tịch trên thẻ (vd \"Việt Nam\")."},
    {"name": "Cccd_NgayCap", "desc": _CARD_ISSUE_DATE},
    {"name": "Cccd_NoiCap", "desc": _CARD_ISSUER},
    {"name": "Cccd_NoiCuTru", "desc": "Nơi cư trú / nơi thường trú IN TRÊN THẺ, object {quocGia,tinh,xa,chiTietDuoiXa}."},

    # Thẻ căn cước của CHỦ XE MỚI (bên mua).
    {"name": "CccdChuMoi_HoTen", "desc": "Họ tên trên thẻ căn cước của bên mua (chủ xe mới)."},
    {"name": "CccdChuMoi_SoDinhDanh", "desc": "Số định danh trên thẻ đó, chỉ chữ số."},
    {"name": "CccdChuMoi_NgayCap", "desc": _CARD_ISSUE_DATE},
    {"name": "CccdChuMoi_NoiCap", "desc": _CARD_ISSUER},
    {"name": "CccdChuMoi_NoiCuTru", "desc": "Nơi cư trú in trên thẻ đó, object {quocGia,tinh,xa,chiTietDuoiXa}."},

    # Giấy khai thu hồi chứng nhận đăng ký xe, biển số xe (nếu hồ sơ có).
    {"name": "ToKhai_TenChuXe", "desc": "Dòng \"Tên chủ xe\" của Giấy khai thu hồi."},
    {"name": "ToKhai_LyDoThuHoi", "desc": "Dòng \"Lý do thu hồi\" của Giấy khai thu hồi, nguyên văn."},
    {"name": "ToKhai_DiaChi",
     "desc": "Dòng \"Địa chỉ\" của chủ xe trên Giấy khai thu hồi, object {quocGia,tinh,xa,chiTietDuoiXa}."},
    {"name": "ToKhai_DienThoai", "desc": "Dòng \"Điện thoại\" của chủ xe trên Giấy khai thu hồi; bỏ dấu chấm/khoảng trắng."},
    {"name": "ToKhai_Email", "desc": "Email chủ xe nếu Giấy khai thu hồi có ghi. Không có → bỏ field."},

    # Giấy / hợp đồng ủy quyền làm thủ tục của CHỦ XE (kịch bản khai hộ).
    {"name": "UyQuyen_BenUyQuyenHoTen", "desc": "Họ tên bên ủy quyền (chủ xe) trên giấy ủy quyền làm thủ tục."},
    {"name": "UyQuyen_HoTen", "desc": "Họ tên bên ĐƯỢC ủy quyền làm thủ tục."},
    {"name": "UyQuyen_SoDinhDanh", "desc": "Số CCCD / định danh của bên được ủy quyền, chỉ chữ số."},
    {"name": "UyQuyen_NgayCap", "desc": "Ngày cấp giấy tờ tùy thân của bên được ủy quyền, dd/mm/yyyy."},
    {"name": "UyQuyen_NoiCap", "desc": "Cơ quan cấp giấy tờ tùy thân của bên được ủy quyền (cụm sau chữ \"do\")."},
    {"name": "UyQuyen_DienThoai", "desc": "Số điện thoại của bên được ủy quyền nếu có ghi, chỉ chữ số."},
    {"name": "UyQuyen_Email", "desc": "Email của bên được ủy quyền nếu có ghi."},

    # Thẻ căn cước của NGƯỜI LÀM THỦ TỤC (người được chủ xe ủy quyền), không phải chủ xe / bên mua.
    {"name": "CccdNduq_HoTen", "desc": "Họ tên trên thẻ căn cước của người được chủ xe ủy quyền làm thủ tục."},
    {"name": "CccdNduq_SoDinhDanh", "desc": "Số định danh trên thẻ đó, chỉ chữ số."},
    {"name": "CccdNduq_NgayCap", "desc": "Ngày cấp thẻ đó, dd/mm/yyyy."},
    {"name": "CccdNduq_NoiCap", "desc": "Cơ quan cấp thẻ đó (quy đổi như Cccd_NoiCap)."},

    # Trang thông tin hồ sơ (nếu có).
    {"name": "HoSo_HinhThucNhanKetQua",
     "desc": "\"Hình thức nhận kết quả\" nếu hồ sơ có ghi (vd \"Qua dịch vụ bưu chính công ích\", \"Trực tiếp tại cơ "
             "quan\"). Không có → bỏ field."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Hdmb_BenBanNgaySinh", "Hdmb_BenBanNgayCapCccd", "Hdmb_BenMuaNgayCapCccd", "Cccd_NgaySinh", "Cccd_NgayCap",
    "CccdChuMoi_NgayCap", "UyQuyen_NgayCap", "CccdNduq_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Hdmb_BenBanDiaChi", "Hdmb_BenMuaDiaChi", "Cccd_NoiCuTru", "CccdChuMoi_NoiCuTru", "ToKhai_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô form theo file mapping (name trong DOM, số trong ngoặc là STT mapping). <select> → dom-select (cả native lẫn
# bootstrap-select); ô tích iCheck → dom-checkbox; còn lại dom-input. Ô ngày form-builder nhận gõ dd/mm/yyyy.
UI_COMP_BY_NAME = {
    # Phần I — người nộp hồ sơ (chọn 1 trong 2; "khai hộ" mở khối người làm thủ tục, mở khoá ô chủ xe).
    "CongDan__fsLaChuXe": "dom-checkbox",            # (1) Người nộp hồ sơ là chủ xe — cổng tích sẵn
    "CongDan__fsLaNguoiKhaiHo": "dom-checkbox",      # (2) Người nộp hồ sơ là người khai hộ
    # Phần II — tra cứu thông tin xe (người dân tự nhập Mã bảo mật rồi bấm Tra cứu). Ô tô / Xe máy đứng đầu: đổi ô này
    # cổng gọi resetData() và nạp lại danh mục Màu biển.
    "CongDan__fsRadioLoaiXe": "dom-select",          # (3) Ô tô / Xe máy (*)
    "CongDan__fstracuuBienSo": "dom-input",          # (4) Biển số (*) — nhập liền, không dấu
    "CongDan__fstracuuMauBien": "dom-select",        # (5) Màu biển (*)
    "CongDan__fstracuuSoMay": "dom-input",           # (6) Số máy (không gửi lên API tra cứu)
    "CongDan__fstracuuSoKhung": "dom-input",         # (7) Số khung (*)
    "CongDan__fslyDoThuHoi": "dom-select",           # (8) Lý do thu hồi (*)
    # Phần III — thông tin chủ xe. Mã định danh / Họ tên / Ngày sinh chỉ phát khi khai hộ (tự nộp: cổng khoá).
    "CongDan_soCmnd": "dom-input",                   # (11) Mã định danh của chủ xe (*)
    "CongDan__fsLoaiGiayToChuXe": "dom-select",      # (12) Loại giấy tờ (*)
    "CongDan__fsngayCapCmnd": "dom-input",           # (13) Cấp ngày (*)
    "CongDan__fsnoiCapCmnd": "dom-input",            # (14) Nơi cấp (*)
    "CongDan_tenCongDan": "dom-input",               # (15) Họ và tên chủ xe (*)
    "CongDan__fsnamSinh": "dom-input",               # (16) Ngày/tháng/Năm sinh (*)
    "CongDan__fsQuocTichChuXe": "dom-select",        # (17) Quốc tịch (*)
    "CongDan__fsBCAHKTTTinh": "dom-select",          # (20) Tỉnh/Thành phố thường trú (*)
    "CongDan__fsBCAHKTTXa": "dom-select",            # (22) Phường/Xã thường trú — nạp theo Tỉnh
    "CongDan__fsBCAHKTTDCChiTiet": "dom-input",      # (23) Nơi thường trú (số nhà/tên đường) (*)
    "CongDan_diDong": "dom-input",                   # (29) Số điện thoại của chủ xe (*)
    "CongDan_email": "dom-input",                    # (30) Email của chủ xe
    # Phần IV — người được ủy quyền làm thủ tục (chỉ mở khi tích "người khai hộ"; cổng đổ sẵn theo tài khoản).
    "CongDan__fsNDUQHoTen": "dom-input",             # (31)
    "CongDan__fsNDUQMaDinhDanh": "dom-input",        # (32) (*)
    "CongDan__fsNDUQLoaiGiayTo": "dom-select",       # (33) (*) — option như (12)
    "CongDan__fsNDUQNgayCap": "dom-input",           # (34) (*)
    "CongDan__fsNDUQCoQuanCap": "dom-input",         # (35) (*)
    "CongDan__fsDiDongNDUQ": "dom-input",            # (36) (*)
    "CongDan__fsEmailNDUQ": "dom-input",             # (37)
    # Phần V — chủ xe mới (bắt buộc khi Lý do thu hồi là 13/17/18/19).
    "CongDan__fsChuMoiHoTen": "dom-input",           # (38)
    "CongDan__fsChuMoiDiaChi": "dom-input",          # (39) một ô, ghi đủ địa chỉ
    "CongDan__fsChuMoiMaDinhDanh": "dom-input",      # (40)
    "CongDan__fsChuMoiSDT": "dom-input",             # (41)
    # Phần VI — thông tin xe: cổng tự điền sau Tra cứu (ô có dữ liệu bị khoá); Năm sản xuất, dung tích, số chỗ… API
    # không trả → điền sẵn theo giấy. Loại xe (46) JS gán theo ô (3), không phát.
    "CongDan__fsnhanHieu": "dom-input",              # (42)
    "CongDan__fssoLoai": "dom-input",                # (43)
    "CongDan__fsSoMay1": "dom-input",                # (44)
    "CongDan__fsSoKhung": "dom-input",               # (45)
    "CongDan__fsNamSanXuat": "dom-input",            # (47) (*)
    "CongDan__fsDungTich": "dom-input",              # (48)
    "CongDan__fscongSuat": "dom-input",              # (49)
    "CongDan__fstrongTai": "dom-input",              # (50)
    "CongDan__fsSoChoNgoi": "dom-input",             # (51)
    "CongDan__fsSoChoDung": "dom-input",             # (52)
    "CongDan__fsSoChoNam": "dom-input",              # (53)
    # Phần VII — hình thức nhận kết quả. Tỉnh phát TRƯỚC Xã (danh mục xã nạp theo tỉnh).
    "CongDan__fsHinhThucNhanKQ": "dom-select",       # (54) (*)
    "CongDan__fsTenNguoiNhanKQ": "dom-input",        # (55)
    "CongDan__fsSoDienThoaiNguoiNhan": "dom-input",  # (56)
    "CongDan__fsTinhNhanKQ": "dom-select",           # (57)
    "CongDan__fsXaNhanKQ": "dom-select",             # (59)
    "CongDan__fsDiaChiChiTietNhanKQ": "dom-input",   # (60)
}

# Ô Xã thường trú nạp chậm qua API sau khi chọn Tỉnh; regex ô địa chỉ của extension chưa nhận tên này → chờ thêm.
WAIT_MS = {
    "CongDan__fsBCAHKTTXa": 8000,
}

# Option "Lý do thu hồi" đúng chữ trên cổng (mapping, mã trong ngoặc là value của <option>).
LY_DO_THU_HOI = {
    "hong": "Xe hỏng không sử dụng được hoặc xe bị phá huỷ do nguyên nhân khách quan.",  # 01
    "thao_may": "Xe tháo máy, khung để thay thế cho xe khác.",  # 02
    "mat_cap": "Xe bị mất cắp, chiếm đoạt không tìm được, chủ xe đề nghị thu hồi giấy chứng nhận đăng ký xe.",  # 06
    "nien_han": "Xe hết niên hạn sử dụng; xe không được phép lưu hành theo quy định của pháp luật.",  # 07
    "tich_thu": "Xe tịch thu sung quỹ nhà nước",  # 10
    "di_chuyen": "Di chuyển đi tỉnh, TP trực thuộc TW khác",  # 13
    "sai_he_bien": "Xe không đúng hệ biển",  # 14
    "ho_so_gia": "Hồ sơ giả",  # 15
    "cap_bien_dau_gia": "Thu hồi để cấp biển đấu giá",  # 16
    "mien_thue": (
        "Xe miễn thuế nhập khẩu hoặc xe tạm nhập của cơ quan, tổ chức, cá nhân nước ngoài tái xuất hoặc chuyển nhượng "
        "tại VN"
    ),  # 17
    "chuyen_quyen": "Chuyển quyền sở hữu",  # 18
    "sang_ten_dau_gia": "Sang tên kèm theo biển trúng đấu giá",  # 19
    "nghiep_vu": "Thu hồi biển số xe nghiệp vụ",  # 20
}
# Lý do 13/17/18/19: cổng bắt buộc khối "Thông tin chủ xe mới".
LY_DO_CAN_CHU_MOI = {
    LY_DO_THU_HOI["di_chuyen"], LY_DO_THU_HOI["mien_thue"], LY_DO_THU_HOI["chuyen_quyen"],
    LY_DO_THU_HOI["sang_ten_dau_gia"],
}
