"""Compact schema cho thủ tục 1.012575 — Đăng ký xe lần đầu toàn trình, xe sản xuất, lắp ráp trong nước.

LLM chỉ trả dữ kiện nguồn đọc từ giấy tờ (tiền tố theo giấy); ô UI ``CongDan__fs*`` / ``CongDan_*`` do mapper dựng
theo file mapping "Mapping_DangKyXeLanDau_SXLR_TrongNuoc_1.012575" (sheet Xe máy / Ô tô cùng bộ ô, chỉ khác ô loại xe
bị khoá và Công suất (81) bắt buộc với ô tô).

Giấy tờ: Giấy khai đăng ký xe (Mẫu ĐKX10/79) · Phiếu kiểm tra chất lượng xuất xưởng (Phiếu KTCLXX) · Hóa đơn GTGT điện
tử bán xe · Thông báo nộp lệ phí trước bạ (TB LPTB) · Giấy nộp tiền vào NSNN (Mẫu C1-02/NS) · thẻ căn cước chủ xe ·
có khi kèm trang thông tin hồ sơ (hình thức nhận kết quả).

Cố ý KHÔNG phát:
- Ô readonly cổng lấy từ CSDLQG về dân cư theo tài khoản VNeID (Mã định danh, Họ tên, Ngày sinh, Phân loại quản lý,
  nơi thường trú / tạm trú / ở hiện tại, điểm đăng ký xe, loại xe mô tô) và ô khoá theo thủ tục (Ô tô/xe máy, nguồn
  gốc xe, Loại địa chỉ đăng ký).
- Mã bảo mật (captcha) và nút Tra cứu — người dân tự nhập / bấm.
- Ảnh phương tiện, ảnh chứng từ nguồn gốc (người dân tự tải lên), ô ẩn kỹ thuật (đánh dấu tra cứu, mã cơ quan thu,
  mã điểm đăng ký, mã xi lanh), khối biển số trúng đấu giá (khoá, hồ sơ cấp biển mới), Mã nhóm / Mã loại phương tiện
  (chỉ CSDL Cục Đăng kiểm trả về), ô người khai hộ / doanh nghiệp đang ẩn.
"""

FIELDS: list[dict] = [
    # Thẻ căn cước / CCCD của CHỦ XE — nguồn chuẩn cho nhân thân.
    {"name": "Cccd_HoTen", "desc": "Họ, chữ đệm và tên trên thẻ căn cước/CCCD của chủ xe."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh cá nhân / số CCCD trên thẻ, chỉ chữ số."},
    {"name": "Cccd_NgaySinh", "desc": "Ngày sinh trên thẻ, dd/mm/yyyy."},
    {"name": "Cccd_GioiTinh", "desc": 'Giới tính trên thẻ: "Nam" hoặc "Nữ".'},
    {"name": "Cccd_QuocTich", "desc": "Quốc tịch trên thẻ (vd \"Việt Nam\")."},
    {"name": "Cccd_NgayCap",
     "desc": "Ngày cấp thẻ (\"Ngày, tháng, năm cấp / Date of issue\" hoặc \"Ngày, tháng, năm\" mặt sau), dd/mm/yyyy. "
             "KHÔNG lấy ngày hết hạn / \"Có giá trị đến\"."},
    {"name": "Cccd_NoiCap",
     "desc": 'Cơ quan cấp thẻ in mặt sau: "BỘ CÔNG AN" → "Bộ Công an"; "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ '
             'TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},
    {"name": "Cccd_NoiCuTru",
     "desc": "Nơi cư trú / nơi thường trú IN TRÊN THẺ, object {quocGia,tinh,xa,chiTietDuoiXa}."},

    # Giấy khai đăng ký xe (Mẫu ĐKX10/79) — mục THÔNG TIN CHỦ XE.
    {"name": "ToKhai_TenChuXe", "desc": "Dòng \"Tên chủ xe\" của Giấy khai đăng ký xe."},
    {"name": "ToKhai_DiaChi",
     "desc": "Dòng \"Địa chỉ\" của chủ xe trên Giấy khai đăng ký xe, object {quocGia,tinh,xa,chiTietDuoiXa}."},
    {"name": "ToKhai_DienThoai", "desc": "Dòng \"Điện thoại\" của chủ xe trên Giấy khai; bỏ dấu chấm/khoảng trắng."},
    {"name": "ToKhai_Email", "desc": "Email chủ xe nếu Giấy khai có ghi. Không có → bỏ field."},
    {"name": "ToKhai_MaDinhDanh", "desc": "Dòng \"Mã định danh\" của chủ xe trên Giấy khai, chỉ chữ số."},
    {"name": "ToKhai_LoaiGiayTo", "desc": "Dòng \"Loại giấy tờ\" trên Giấy khai (vd \"Thẻ căn cước\", \"CCCD\")."},
    {"name": "ToKhai_CoQuanCap", "desc": "Dòng \"Cơ quan cấp\" giấy tờ của chủ xe trên Giấy khai (KHÔNG phải GPKDVT)."},
    {"name": "ToKhai_NgayCap", "desc": "Dòng \"Ngày cấp\" giấy tờ của chủ xe trên Giấy khai, dd/mm/yyyy."},
    {"name": "ToKhai_NguoiLamThuTuc", "desc": "Dòng \"Người làm thủ tục\" trên Giấy khai."},
    {"name": "ToKhai_DienThoaiNguoiLamThuTuc", "desc": "Dòng \"Số điện thoại người làm thủ tục\" trên Giấy khai."},
    {"name": "ToKhai_MaChungTuLptb", "desc": "Dòng \"Mã chứng từ lệ phí trước bạ\" trên Giấy khai, giữ nguyên chữ số."},
    {"name": "ToKhai_SoSeriPhieu",
     "desc": "Số seri Phiếu kiểm tra chất lượng xuất xưởng ghi trong dòng \"Nguồn gốc xe\" hoặc \"Giấy tờ kèm theo\" "
             "của Giấy khai (vd \"... số seri AB 0000001\" → \"AB 0000001\")."},

    # Đặc điểm xe — giá trị IN TRÊN GIẤY, ưu tiên Phiếu KTCLXX → Giấy khai → TB LPTB → Hóa đơn.
    {"name": "Xe_LoaiXe",
     "desc": "Loại xe: \"Loại phương tiện\" của Phiếu KTCLXX (vd \"Xe mô tô hai bánh\"), không có thì \"Loại xe\" của "
             "Giấy khai."},
    {"name": "Xe_NhanHieu", "desc": "Nhãn hiệu xe."},
    {"name": "Xe_SoLoai", "desc": "Số loại (model) xe."},
    {"name": "Xe_MauSon", "desc": "Màu sơn, giữ nguyên chữ (vd \"Đỏ - Đen\")."},
    {"name": "Xe_SoKhung", "desc": "Số khung, viết liền chữ IN HOA và số như trên giấy."},
    {"name": "Xe_SoMay", "desc": "Số máy / Số động cơ (Phiếu KTCLXX gọi là \"Số động cơ\"), viết liền như trên giấy."},
    {"name": "Xe_SoMay2", "desc": "Số máy thứ 2 nếu giấy có ghi riêng (xe hybrid). Không có → bỏ field."},
    {"name": "Xe_NamSanXuat", "desc": "Năm sản xuất, 4 chữ số."},
    {"name": "Xe_DungTich",
     "desc": "Dung tích xi lanh, CHỈ SỐ theo cm3, dấu phẩy thập phân như trên giấy (vd \"109,5 cm³\" → \"109,5\")."},
    {"name": "Xe_CongSuat",
     "desc": "Công suất (lớn nhất), CHỈ SỐ theo kW (vd \"6,4 kW / 7.500 vòng/phút\" → \"6,4\")."},
    {"name": "Xe_KhoiLuongBanThan", "desc": "Khối lượng bản thân, CHỈ SỐ kg (vd \"98\")."},
    {"name": "Xe_KhoiLuongToanBo", "desc": "Khối lượng toàn bộ, CHỈ SỐ kg."},
    {"name": "Xe_SoChoNgoi",
     "desc": "Số chỗ ngồi (Giấy khai \"Số chỗ ngồi\" hoặc Phiếu \"Số người cho phép chở (kể cả người lái)\"), chỉ số."},
    {"name": "Xe_SoChoDung", "desc": "Số chỗ đứng nếu có ghi số. Để chấm/trống → bỏ field."},
    {"name": "Xe_SoChoNam", "desc": "Số chỗ nằm nếu có ghi số. Để chấm/trống → bỏ field."},
    {"name": "Xe_TrongTai", "desc": "Trọng tải (kg) nếu có ghi số. Để chấm/trống → bỏ field."},
    {"name": "Xe_KhoiLuongKeoTheo", "desc": "Khối lượng kéo theo (kg) nếu có ghi số. Để chấm/trống → bỏ field."},
    {"name": "Xe_KichThuocBao", "desc": "Kích thước bao (dài × rộng × cao) giữ nguyên chữ, kèm đơn vị."},
    {"name": "Xe_KichThuocThung", "desc": "Kích thước thùng hàng (dài × rộng × cao) nếu có. Không có → bỏ field."},
    {"name": "Xe_ChieuDaiCoSo", "desc": "Chiều dài cơ sở giữ nguyên chữ, kèm đơn vị (vd \"1.230 mm\")."},
    {"name": "Xe_CoLop", "desc": "Cỡ lốp trước / sau giữ nguyên chữ (vd \"70/90-17 / 80/90-17\")."},
    {"name": "Xe_LoaiNhienLieu", "desc": "Loại nhiên liệu (vd \"Xăng\", \"Dầu\", \"Điện\")."},

    # Phiếu kiểm tra chất lượng xuất xưởng.
    {"name": "Pkt_SoSeri", "desc": "Dòng \"Số seri phiếu\" của Phiếu KTCLXX, giữ nguyên chữ và khoảng trắng."},
    {"name": "Pkt_TenCoSoSanXuat", "desc": "Tên doanh nghiệp/cơ sở sản xuất, lắp ráp ở đầu Phiếu KTCLXX."},
    {"name": "Pkt_DiaChiCoSoSanXuat", "desc": "Dòng \"Địa chỉ\" của cơ sở sản xuất ở đầu Phiếu KTCLXX."},
    {"name": "Pkt_NgayXuatXuong", "desc": "\"Ngày xuất xưởng\" trên Phiếu KTCLXX, dd/mm/yyyy."},

    # Hóa đơn giá trị gia tăng điện tử bán xe.
    {"name": "HoaDon_Loai", "desc": "Tên loại hóa đơn ở tiêu đề (vd \"Hóa đơn giá trị gia tăng\")."},
    {"name": "HoaDon_KyHieu", "desc": "\"Ký hiệu\" hóa đơn."},
    {"name": "HoaDon_MauSo", "desc": "\"Mẫu số\" hóa đơn."},
    {"name": "HoaDon_So", "desc": "\"Số\" hóa đơn, GIỮ đủ số 0 đầu."},
    {"name": "HoaDon_Ngay", "desc": "Ngày lập hóa đơn (\"Ngày ... tháng ... năm ...\"), dd/mm/yyyy."},
    {"name": "HoaDon_TenHangHoa",
     "desc": "Chép NGUYÊN VĂN, ĐỦ CHỮ cả ô \"Tên hàng hóa, dịch vụ\" của dòng xe, gồm mọi dòng xuống trong ô (kể cả "
             "\"Số khung: ...\", \"Số máy: ...\", \"Phiếu kiểm tra chất lượng xuất xưởng số ...\"), nối bằng \", \". "
             "Không rút gọn, không bỏ chữ."},
    {"name": "HoaDon_DonViBan", "desc": "\"Đơn vị bán hàng\"."},
    {"name": "HoaDon_MstNguoiBan", "desc": "\"Mã số thuế\" của đơn vị bán hàng."},
    {"name": "HoaDon_DiaChiNguoiBan", "desc": "\"Địa chỉ\" của đơn vị bán hàng, chuỗi nguyên văn."},
    {"name": "HoaDon_TenDonViMua", "desc": "\"Tên đơn vị\" người mua — chỉ khi ghi tên tổ chức; chấm chấm → bỏ field."},
    {"name": "HoaDon_HoTenNguoiMua", "desc": "\"Họ tên người mua hàng\"."},
    {"name": "HoaDon_MstNguoiMua",
     "desc": "\"Mã số thuế\" hoặc \"Số định danh cá nhân\" của người mua, chỉ chữ số."},
    {"name": "HoaDon_DiaChiNguoiMua", "desc": "\"Địa chỉ\" của người mua, chuỗi nguyên văn."},
    {"name": "HoaDon_TienThue", "desc": "\"Tiền thuế GTGT\", giữ chữ số như trên giấy."},
    {"name": "HoaDon_TongCong", "desc": "\"Tổng cộng tiền thanh toán\", giữ chữ số như trên giấy."},
    {"name": "HoaDon_TongCongBangChu", "desc": "\"Số tiền viết bằng chữ\" của hóa đơn."},

    # Thông báo nộp lệ phí trước bạ.
    {"name": "Lptb_MaHoSo", "desc": "\"Mã hồ sơ\" của Thông báo nộp lệ phí trước bạ, chỉ chữ số."},
    {"name": "Lptb_NgayThongBao",
     "desc": "Ngày ban hành Thông báo (dòng \"<địa danh>, ngày ... tháng ... năm ...\"), dd/mm/yyyy."},
    {"name": "Lptb_CoQuanThue",
     "desc": "Cơ quan thuế ban hành ở góc trái Thông báo — dòng dưới cùng (vd \"CỤC THUẾ / THUẾ TỈNH X\" → "
             "\"Thuế tỉnh X\")."},
    {"name": "Lptb_TenNguoiNop", "desc": "\"Tên người nộp\" lệ phí trước bạ."},
    {"name": "Lptb_MstNguoiNop", "desc": "\"Mã số thuế\" người nộp lệ phí trước bạ, chỉ chữ số."},
    {"name": "Lptb_DiaChiNguoiNop", "desc": "\"Địa chỉ\" người nộp lệ phí trước bạ, chuỗi nguyên văn."},
    {"name": "Lptb_LoaiTaiSan", "desc": "\"Loại tài sản\" ở mục Thông tin tài sản (vd \"Xe máy\", \"Ô tô\")."},
    {"name": "Lptb_GiaTriTinh", "desc": "\"Giá trị tài sản tính lệ phí trước bạ\", giữ chữ số như trên giấy."},
    {"name": "Lptb_SoTien", "desc": "\"Số tiền lệ phí trước bạ phải nộp\", giữ chữ số như trên giấy."},
    {"name": "Lptb_SoTienBangChu", "desc": "Dòng \"Bằng chữ\" của số tiền lệ phí trước bạ."},
    {"name": "Lptb_CanCuMienThu", "desc": "Căn cứ miễn lệ phí trước bạ — CHỈ khi Thông báo ghi miễn; không có → bỏ field."},

    # Giấy nộp tiền vào ngân sách nhà nước (lệ phí trước bạ).
    {"name": "Gnt_MaHoSo",
     "desc": "Cột \"Số tờ khai/Số quyết định/Số thông báo/Mã định danh hồ sơ\" của dòng lệ phí trước bạ."},
    {"name": "Gnt_NgayThongBao",
     "desc": "Cột \"Kỳ thuế/Ngày thông báo\", dd/mm/yyyy. KHÔNG lấy \"Ngày nộp\"."},
    {"name": "Gnt_CoQuanQuanLyThu", "desc": "\"Tên cơ quan quản lý thu\"."},
    {"name": "Gnt_NguoiNopThue", "desc": "\"Người nộp thuế\"."},
    {"name": "Gnt_MstNguoiNop", "desc": "\"Mã số thuế\" người nộp thuế, chỉ chữ số."},
    {"name": "Gnt_DiaChi", "desc": "\"Địa chỉ\" người nộp thuế, chuỗi nguyên văn."},
    {"name": "Gnt_SoTien", "desc": "Cột \"Số tiền (VND)\" của dòng lệ phí trước bạ, giữ chữ số như trên giấy."},
    {"name": "Gnt_SoTienBangChu", "desc": "\"Tổng số tiền ghi bằng chữ\"."},

    # Trang thông tin hồ sơ (nếu có).
    {"name": "HoSo_HinhThucNhanKetQua",
     "desc": "\"Hình thức nhận kết quả\" nếu hồ sơ có ghi (vd \"Qua dịch vụ bưu chính công ích\", \"Trực tiếp tại cơ "
             "quan\"). Không có → bỏ field."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Cccd_NgaySinh", "Cccd_NgayCap", "ToKhai_NgayCap", "Pkt_NgayXuatXuong", "HoaDon_Ngay", "Lptb_NgayThongBao",
    "Gnt_NgayThongBao",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Cccd_NoiCuTru", "ToKhai_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô form theo file mapping (name trong DOM). <select> + bootstrap-select → dom-select; còn lại dom-input. Ô ngày
# "custom datetime" của form-builder nhận gõ dd/mm/yyyy như eForm Lai Châu → dom-input.
UI_COMP_BY_NAME = {
    # Phần B — tra cứu (người dân tự nhập mã bảo mật rồi bấm Tra cứu).
    "CongDan__fsSeriChatLuongXuatXuong": "dom-input",
    "CongDan__fsTraCuMaHsLPTB": "dom-input",
    # Phần I — ô chủ xe cổng cho sửa (ô readonly CSDL dân cư không phát).
    "CongDan__fs_BCAGioiTinhCd": "dom-select",       # (4) Giới tính
    "CongDan__fsLoaiGiayToChuXe": "dom-select",      # (5) Loại giấy tờ (*)
    "CongDan__fsngayCapCmnd": "dom-input",           # (6) Cấp ngày (*)
    "CongDan__fsnoiCapCmnd": "dom-input",            # (7) Nơi cấp (*)
    "CongDan__fsQuocTichChuXe": "dom-select",        # (8) Quốc tịch (*) — DOM chọn sẵn Việt Nam
    "CongDan_diDong": "dom-input",                   # (10) Số điện thoại (*) — 10 số
    "CongDan_email": "dom-input",                    # (11) Email (*)
    # Phần III — lệ phí trước bạ (cổng tự điền sau Tra cứu; ô vẫn cho sửa).
    "CongDan__fsMaHsLPTBDienTu": "dom-input",        # (30)
    "CongDan__fsNgayCapLPTB": "dom-input",           # (31)
    "CongDan__fsCoQuanCapLPTB": "dom-input",         # (32)
    "CongDan__fsCMNDNguoiNopThueLPTB": "dom-input",  # (33)
    "CongDan__fsMSTnguoiNopThueLPTB": "dom-input",   # (34)
    "CongDan__fsTenNguoiNopThue": "dom-input",       # (35)
    "CongDan__fsSDTNguoiNopThue": "dom-input",       # (36)
    "CongDan__fsDiaChiNguoiNopThue": "dom-input",    # (37)
    "CongDan__fsLPTBMauSon": "dom-input",            # (38)
    "CongDan__fsLoaiXe": "dom-input",                # (39)
    "CongDan__fsnhanHieu": "dom-input",              # (40)
    "CongDan__fssoLoai": "dom-input",                # (41)
    "CongDan__fsNamSanXuat": "dom-input",            # (42)
    "CongDan__fsSoMay1": "dom-input",                # (43)
    "CongDan__fsSoKhung": "dom-input",               # (44)
    "CongDan__fsDungTich": "dom-input",              # (45)
    "CongDan__fsCongSuat": "dom-input",              # (46)
    "CongDan__fsCanCuMienThuLPTB": "dom-input",      # (47)
    "CongDan__fsSoTienLPTB": "dom-input",            # (48)
    "CongDan__fsGiaTriTinhLPTB": "dom-input",        # (49)
    "CongDan__fsSoTienBangChuLPTB": "dom-input",     # (50)
    # Phần IV — hóa đơn điện tử.
    "CongDan__fsLoaiHoaDon": "dom-input",            # (51)
    "CongDan__fsKyHieu": "dom-input",                # (52)
    "CongDan__fsHDDTMauSoHoaDon": "dom-input",       # (53)
    "CongDan__fsSoHoaDon": "dom-input",              # (54)
    "CongDan__fsTenHangHoa": "dom-input",            # (55)
    "CongDan__fsDonViBanHang": "dom-input",          # (56)
    "CongDan__fsMSTNguoiBan": "dom-input",           # (57)
    "CongDan__fsDiaChiNguoiBan": "dom-input",        # (58)
    "CongDan__fsDonViNguoiMua": "dom-input",         # (59)
    "CongDan__fsHoTenNguoiMua": "dom-input",         # (60)
    "CongDan__fsMSTNguoiMua": "dom-input",           # (61)
    "CongDan__fsDiaChiNguoiMua": "dom-input",        # (62)
    "CongDan__fsTienthue": "dom-input",              # (63)
    "CongDan__fsTongCongTienThanhToan": "dom-input",          # (64)
    "CongDan__fsTongCongTienThanhToanBangChu": "dom-input",   # (65)
    "CongDan__fsHDDTNgayCap": "dom-input",           # (66)
    # Phần V — thông tin xe (Cục Đăng kiểm).
    "CongDan__fsSoSeriKTCLXX": "dom-input",          # (67)
    "CongDan__fsTenDonViSanXuat": "dom-input",       # (68)
    "CongDan__fsDkNgayXuatXuong": "dom-input",       # (69)
    "CongDan__fsDiaChiDK": "dom-input",              # (70)
    "CongDan__fsLoaiXeDK": "dom-input",              # (73)
    "CongDan__fsnhanHieuDK_1": "dom-input",          # (74)
    "CongDan__fsSoLoaiDK": "dom-input",              # (75)
    "CongDan__fsSoMay1DK": "dom-input",              # (76)
    "CongDan__fsSoMay2DK": "dom-input",              # (77)
    "CongDan__fsSoKhungDK": "dom-input",             # (78)
    "CongDan__fsNamSanXuatDK": "dom-input",          # (79)
    "CongDan__fsDungTichXiLanhDK": "dom-input",      # (80) cm3, chỉ số
    "CongDan__fsCongSuatDK": "dom-input",            # (81) kW, chỉ số — ô tô bắt buộc
    "CongDan__fsMauSonDK": "dom-input",              # (82)
    "CongDan__fsTrongLuongBanThanDK": "dom-input",   # (83) kg, chỉ số
    "CongDan__fsSoChoNgoiDK": "dom-input",           # (84)
    "CongDan__fsSoChoDungDK": "dom-input",           # (85)
    "CongDan__fsSoChoNamDK": "dom-input",            # (86)
    "CongDan__fsKichCoLopDK": "dom-input",           # (87)
    "CongDan__fsTrongTaiDK": "dom-input",            # (88) kg
    "CongDan__fsTrongLuongKeoTheoDK": "dom-input",   # (89)
    "CongDan__fsKichThuocThungDK": "dom-input",      # (90)
    "CongDan__fsKichThuocBaoDK": "dom-input",        # (91)
    "CongDan__fsTrongLuongToanBoDK": "dom-input",    # (92)
    "CongDan__fsChieuDaiCoSoDK": "dom-input",        # (93)
    "CongDan__fsNuocSanXuatDK": "dom-input",         # (94)
    "CongDan__fsLoaiNhienLieuDK": "dom-input",       # (95)
    # Phần VII — hình thức nhận kết quả. Tỉnh phát TRƯỚC Xã (danh mục xã nạp theo tỉnh).
    "CongDan__fsHinhThucNhanKQ": "dom-select",       # (100) (*)
    "CongDan__fsTenNguoiNhanKQ": "dom-input",        # (101)
    "CongDan__fsSoDienThoaiNguoiNhan": "dom-input",  # (102)
    "CongDan__fsTinhNhanKQ": "dom-select",           # (103)
    "CongDan__fsXaNhanKQ": "dom-select",             # (105) (*)
    "CongDan__fsDiaChiChiTietNhanKQ": "dom-input",   # (106)
}

# Option "Hình thức nhận kết quả" đúng chữ trên cổng.
HINH_THUC_NHAN_KQ = {
    "co_quan": "Đến cơ quan giải quyết để nhận kết quả",
    "dia_chi": "Gửi hồ sơ đến địa chỉ của tôi",
    "qua_mang": "Nhận kết quả qua mạng",
    "buu_dien": "Qua bưu điện, tại nhà",
}
