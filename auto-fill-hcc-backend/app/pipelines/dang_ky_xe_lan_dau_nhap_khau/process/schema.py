"""Compact schema cho thủ tục 1.013066 — Đăng ký xe lần đầu toàn trình đối với xe nhập khẩu.

LLM chỉ trả dữ kiện nguồn đọc từ giấy tờ (tiền tố theo giấy); ô UI ``CongDan__fs*`` / ``CongDan_*`` do mapper dựng
theo file mapping "Mapping_DK_xe_lan_dau_nhap_khau_1.013066" (DOM ô tô; xe máy cùng bộ ô, Công suất (79) bắt buộc
với ô tô).

Giấy tờ theo mapping: thẻ căn cước chủ xe · Giấy chứng nhận thu hồi đăng ký, biển số xe (GCN thu hồi) · Hợp đồng mua
bán xe (HĐMB, có lời chứng công chứng) · Dữ liệu điện tử về lệ phí trước bạ / Thông báo nộp LPTB. Thêm các giấy hồ sơ
xe nhập khẩu hay có: Hóa đơn bán xe, Tờ khai hàng hóa nhập khẩu (hải quan), Giấy khai đăng ký xe; có khi kèm trang
thông tin hồ sơ (hình thức nhận kết quả).

Cố ý KHÔNG phát:
- Ô readonly cổng lấy từ CSDLQG về dân cư theo tài khoản VNeID (Mã định danh, Họ tên, Ngày sinh, Phân loại quản lý,
  nơi thường trú / tạm trú / ở hiện tại, điểm đăng ký xe, loại xe mô tô) và ô khoá theo thủ tục (Xe nhập khẩu, Loại
  địa chỉ đăng ký).
- Mã bảo mật (captcha) và nút Tra cứu — người dân tự nhập / bấm.
- Ảnh phương tiện, ảnh chứng từ nguồn gốc (người dân tự tải lên), ô ẩn kỹ thuật (đánh dấu tra cứu, mã cơ quan thu,
  mã điểm đăng ký), seri phiếu KTCLXX (chỉ xe trong nước, đang ẩn), khối biển số trúng đấu giá, Mã hồ sơ nguồn gốc /
  Mã nhóm / Mã loại phương tiện và thông số chỉ CSDL Hải quan / Cục Đăng kiểm trả về, ô người khai hộ / doanh nghiệp
  đang ẩn.
"""

FIELDS: list[dict] = [
    # Thẻ căn cước / CCCD của CHỦ XE (người đứng tên đăng ký) — nguồn chuẩn cho nhân thân.
    {"name": "Cccd_HoTen", "desc": "Họ, chữ đệm và tên trên thẻ căn cước/CCCD của chủ xe."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh cá nhân / số CCCD trên thẻ, chỉ chữ số."},
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

    # Giấy chứng nhận thu hồi đăng ký, biển số xe.
    {"name": "GcnThuHoi_ChuXe", "desc": "Dòng \"Chủ xe\" (chủ xe CŨ, người bị thu hồi đăng ký) trên GCN thu hồi."},
    {"name": "GcnThuHoi_DiaChiChuXe", "desc": "Dòng \"Địa chỉ\" ngay dưới \"Chủ xe\" (chủ xe CŨ), chuỗi nguyên văn."},
    {"name": "GcnThuHoi_ChuMoiHoTen", "desc": "Dòng \"Sang tên cho chủ xe mới (nếu có)\": họ tên chủ xe MỚI."},
    {"name": "GcnThuHoi_ChuMoiMaDinhDanh",
     "desc": "\"Mã định danh\" ở mục Sang tên cho chủ xe mới (KHÔNG lấy mã định danh của chủ xe cũ), chỉ chữ số."},
    {"name": "GcnThuHoi_ChuMoiDienThoai",
     "desc": "\"Số điện thoại\" ở mục Sang tên cho chủ xe mới, chỉ chữ số (chép đúng kể cả dãy toàn số 0)."},
    {"name": "GcnThuHoi_ChuMoiDiaChi",
     "desc": "\"Địa chỉ\" ở mục Sang tên cho chủ xe mới, object {quocGia,tinh,xa,chiTietDuoiXa}."},

    # Hợp đồng mua bán xe (công chứng).
    {"name": "Hdmb_SoCongChung", "desc": "\"Số công chứng\" của hợp đồng mua bán xe (vd \"123/2026/CCGD\")."},
    {"name": "Hdmb_NgayKy",
     "desc": "Ngày lập/công chứng hợp đồng (\"Hôm nay, ngày ... tháng ... năm ...\"), dd/mm/yyyy."},
    {"name": "Hdmb_MoTaXe",
     "desc": "Ở Điều 1, cụm mô tả xe từ chữ \"chiếc xe\" tới trước chữ \"theo Chứng nhận đăng ký\" (vd \"chiếc xe ô tô "
             "mang nhãn hiệu: X, số loại Y, mang biển số đăng ký: 00A-000.00\"), chép nguyên văn."},
    {"name": "Hdmb_GiaMuaBan", "desc": "Giá mua bán ở Điều 2 bằng số, giữ chữ số như trên giấy (vd \"100.000.000\")."},
    {"name": "Hdmb_GiaBangChu", "desc": "Giá mua bán \"Bằng chữ\" ở Điều 2, bỏ ngoặc."},
    {"name": "Hdmb_BenBanHoTen",
     "desc": "Họ tên người ĐẦU TIÊN của BÊN BÁN (bên A). KHÔNG lấy người được ủy quyền ký thay."},
    {"name": "Hdmb_BenBanDiaChi", "desc": "\"Địa chỉ thường trú\" của người đầu tiên bên bán, chuỗi nguyên văn."},
    {"name": "Hdmb_BenMuaHoTen", "desc": "Họ tên BÊN MUA (bên B)."},
    {"name": "Hdmb_BenMuaDanhXung", "desc": "Danh xưng trước tên bên mua: \"Ông\" hoặc \"Bà\"."},
    {"name": "Hdmb_BenMuaSoCccd", "desc": "\"Căn cước công dân số\" của bên mua, chỉ chữ số."},
    {"name": "Hdmb_BenMuaNgayCapCccd", "desc": "Ngày cấp căn cước của bên mua (\"... cấp ngày dd/mm/yyyy\")."},
    {"name": "Hdmb_BenMuaNoiCapCccd",
     "desc": "Cơ quan cấp căn cước của bên mua (cụm sau chữ \"do\", vd \"Cục Cảnh sát quản lý hành chính về trật tự "
             "xã hội\")."},
    {"name": "Hdmb_BenMuaDiaChi",
     "desc": "\"Địa chỉ thường trú\" của bên mua, object {quocGia,tinh,xa,chiTietDuoiXa}."},

    # Dữ liệu điện tử về lệ phí trước bạ / Thông báo nộp lệ phí trước bạ.
    {"name": "Lptb_MaHoSo", "desc": "\"Mã hồ sơ lệ phí trước bạ\" / \"Mã hồ sơ\", chỉ chữ số."},
    {"name": "Lptb_NgayNop", "desc": "Dòng \"Ngày nộp\" của Dữ liệu điện tử về LPTB, dd/mm/yyyy."},
    {"name": "Lptb_NgayThongBao",
     "desc": "Ngày ban hành Thông báo nộp LPTB (dòng \"<địa danh>, ngày ... tháng ... năm ...\") hoặc dòng \"Thông báo "
             "của cơ quan thuế ngày\" nếu có ghi số, dd/mm/yyyy."},
    {"name": "Lptb_CoQuanThue", "desc": "\"Tên cơ quan quản lý thuế thu\" / cơ quan thuế ban hành, nguyên văn."},
    {"name": "Lptb_TenNguoiNop", "desc": "\"Tên người nộp thuế\" / \"Tên người nộp\", chép đúng chữ hoa/thường."},
    {"name": "Lptb_MaDinhDanh", "desc": "\"Mã định danh\" của người nộp thuế, chỉ chữ số."},
    {"name": "Lptb_MstNguoiNop", "desc": "\"Mã số thuế\" người nộp, chỉ khi giấy in nhãn Mã số thuế; chỉ chữ số."},
    {"name": "Lptb_DienThoai", "desc": "\"Số điện thoại\" người nộp thuế, chỉ chữ số."},
    {"name": "Lptb_DiaChi", "desc": "\"Địa chỉ\" người nộp thuế, chuỗi nguyên văn."},
    {"name": "Lptb_LoaiXe", "desc": "\"Loại xe\" / \"Loại tài sản\" trên giấy LPTB. Để trống/gạch → bỏ field."},
    {"name": "Lptb_NhanHieu", "desc": "\"Nhãn hiệu\" trên giấy LPTB."},
    {"name": "Lptb_SoLoai",
     "desc": "\"Số loại\" trên giấy LPTB, chép ĐỦ cả phần mã trong ngoặc (vd \"ABC GLX (XY12ZT)\")."},
    {"name": "Lptb_NamSanXuat", "desc": "\"Năm sản xuất\" trên giấy LPTB, 4 chữ số."},
    {"name": "Lptb_SoMay", "desc": "\"Số máy\" trên giấy LPTB, viết liền như trên giấy."},
    {"name": "Lptb_SoKhung", "desc": "\"Số khung\" trên giấy LPTB, viết liền như trên giấy."},
    {"name": "Lptb_DungTich", "desc": "\"Dung tích\" trên giấy LPTB, CHỈ SỐ theo cm3."},
    {"name": "Lptb_CongSuat", "desc": "\"Công suất\" trên giấy LPTB, CHỈ SỐ kW. Để chấm/trống → bỏ field."},
    {"name": "Lptb_TrongTai", "desc": "\"Trọng tải\" trên giấy LPTB, CHỈ SỐ kg (ghi \"0 kg\" → \"0\")."},
    {"name": "Lptb_SoChoNgoi", "desc": "\"Số chỗ ngồi\" trên giấy LPTB, chỉ số."},
    {"name": "Lptb_GiaTriTinh", "desc": "\"Giá trị tài sản tính LPTB\", giữ chữ số như trên giấy."},
    {"name": "Lptb_SoTien", "desc": "\"Số tiền lệ phí trước bạ phải nộp\", giữ chữ số như trên giấy."},
    {"name": "Lptb_SoTienBangChu", "desc": "Dòng \"Bằng chữ\" của số tiền LPTB — CHỈ khi giấy có in; không có → bỏ field."},
    {"name": "Lptb_CanCuMienThu", "desc": "\"Căn cứ miễn thu\" — CHỈ khi có ghi nội dung; để trống/gạch → bỏ field."},

    # Hóa đơn bán xe (hóa đơn GTGT điện tử) — chỉ khi hồ sơ có hóa đơn thật.
    {"name": "HoaDon_Loai", "desc": "Tên loại hóa đơn ở tiêu đề (vd \"Hóa đơn giá trị gia tăng\")."},
    {"name": "HoaDon_KyHieu", "desc": "\"Ký hiệu\" hóa đơn."},
    {"name": "HoaDon_MauSo", "desc": "\"Mẫu số\" hóa đơn."},
    {"name": "HoaDon_So", "desc": "\"Số\" hóa đơn, GIỮ đủ số 0 đầu."},
    {"name": "HoaDon_Ngay", "desc": "Ngày lập hóa đơn (\"Ngày ... tháng ... năm ...\"), dd/mm/yyyy."},
    {"name": "HoaDon_TenHangHoa",
     "desc": "Chép NGUYÊN VĂN, ĐỦ CHỮ cả ô \"Tên hàng hóa, dịch vụ\" của dòng xe (kể cả \"Số khung: ...\", \"Số máy: "
             "...\"), nối các dòng bằng \", \"."},
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

    # Tờ khai hàng hóa nhập khẩu (hải quan) — chứng từ nguồn gốc xe nhập khẩu.
    {"name": "ToKhaiHq_SoToKhai", "desc": "\"Số tờ khai\" hàng hóa nhập khẩu, giữ nguyên chữ số."},
    {"name": "ToKhaiHq_NgayDangKy", "desc": "\"Ngày đăng ký\" tờ khai, dd/mm/yyyy."},
    {"name": "ToKhaiHq_CoQuanHaiQuan", "desc": "\"Tên cơ quan Hải quan tiếp nhận tờ khai\", nguyên văn."},
    {"name": "ToKhaiHq_TenNguoiNhapKhau", "desc": "Tên người/đơn vị nhập khẩu trên tờ khai."},
    {"name": "ToKhaiHq_DiaChiNguoiNhapKhau", "desc": "Địa chỉ người/đơn vị nhập khẩu trên tờ khai, nguyên văn."},
    {"name": "ToKhaiHq_XuatXu", "desc": "\"Mã/Nước xuất xứ\" của xe trên tờ khai, ghi tên nước (vd \"Nhật Bản\")."},

    # Giấy khai đăng ký xe (nếu hồ sơ có).
    {"name": "ToKhai_TenChuXe", "desc": "Dòng \"Tên chủ xe\" của Giấy khai đăng ký xe."},
    {"name": "ToKhai_DiaChi",
     "desc": "Dòng \"Địa chỉ\" của chủ xe trên Giấy khai đăng ký xe, object {quocGia,tinh,xa,chiTietDuoiXa}."},
    {"name": "ToKhai_DienThoai", "desc": "Dòng \"Điện thoại\" của chủ xe trên Giấy khai; bỏ dấu chấm/khoảng trắng."},
    {"name": "ToKhai_Email", "desc": "Email chủ xe nếu Giấy khai có ghi. Không có → bỏ field."},

    # Đặc điểm xe theo giấy đăng ký / đăng kiểm — ưu tiên GCN thu hồi → Giấy khai → HĐMB → Tờ khai HQ → Hóa đơn.
    {"name": "Xe_LoaiXe", "desc": "Loại xe (vd \"Ô tô con\", \"Xe mô tô hai bánh\")."},
    {"name": "Xe_NhanHieu", "desc": "Nhãn hiệu xe."},
    {"name": "Xe_SoLoai", "desc": "Số loại (model) xe như ghi trên GCN thu hồi / HĐMB."},
    {"name": "Xe_MauSon", "desc": "Màu sơn, giữ nguyên chữ (vd \"Xám, Bạc\"). KHÔNG lấy \"Màu biển\" của biển số."},
    {"name": "Xe_SoKhung", "desc": "Số khung, viết liền chữ IN HOA và số như trên giấy."},
    {"name": "Xe_SoMay", "desc": "Số máy / số động cơ, viết liền như trên giấy."},
    {"name": "Xe_NamSanXuat", "desc": "Năm sản xuất, 4 chữ số."},
    {"name": "Xe_DungTich", "desc": "Dung tích xi lanh, CHỈ SỐ theo cm3 (vd \"1499 cm³\" → \"1499\")."},
    {"name": "Xe_CongSuat", "desc": "Công suất, CHỈ SỐ theo kW. Để chấm/trống → bỏ field."},
    {"name": "Xe_SoChoNgoi", "desc": "Số chỗ ngồi, chỉ số."},
    {"name": "Xe_SoChoDung", "desc": "Số chỗ đứng nếu có ghi số. Để chấm/trống → bỏ field."},
    {"name": "Xe_SoChoNam", "desc": "Số chỗ nằm nếu có ghi số. Để chấm/trống → bỏ field."},
    {"name": "Xe_TrongTai", "desc": "Trọng tải (kg) nếu có ghi số. Để chấm/trống → bỏ field."},

    # Trang thông tin hồ sơ (nếu có).
    {"name": "HoSo_HinhThucNhanKetQua",
     "desc": "\"Hình thức nhận kết quả\" nếu hồ sơ có ghi (vd \"Qua dịch vụ bưu chính công ích\", \"Trực tiếp tại cơ "
             "quan\"). Không có → bỏ field."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Cccd_NgayCap", "Hdmb_NgayKy", "Hdmb_BenMuaNgayCapCccd", "Lptb_NgayNop", "Lptb_NgayThongBao", "HoaDon_Ngay",
    "ToKhaiHq_NgayDangKy",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Cccd_NoiCuTru", "GcnThuHoi_ChuMoiDiaChi", "Hdmb_BenMuaDiaChi", "ToKhai_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô form theo file mapping (name trong DOM, số trong ngoặc là số thứ tự trên form). <select> + bootstrap-select →
# dom-select; còn lại dom-input. Ô ngày "custom datetime" của form-builder nhận gõ dd/mm/yyyy → dom-input.
UI_COMP_BY_NAME = {
    # Phần tra cứu (người dân tự nhập mã bảo mật rồi bấm Tra cứu).
    "CongDan__fsRadioLoaiXe": "dom-select",          # Ô tô / xe máy (*) — option "Xe máy" / "Ô tô"
    "CongDan__fstracuuSoKhung": "dom-input",         # Số khung (*)
    "CongDan__fsTraCuMaHsLPTB": "dom-input",         # Mã hồ sơ lệ phí trước bạ (*)
    # Phần I — ô chủ xe cổng cho sửa (ô readonly CSDL dân cư không phát).
    "CongDan__fs_BCAGioiTinhCd": "dom-select",       # (4) Giới tính
    "CongDan__fsLoaiGiayToChuXe": "dom-select",      # (5) Loại giấy tờ (*)
    "CongDan__fsngayCapCmnd": "dom-input",           # (6) Cấp ngày (*)
    "CongDan__fsnoiCapCmnd": "dom-input",            # (7) Nơi cấp (*)
    "CongDan__fsQuocTichChuXe": "dom-select",        # (8) Quốc tịch (*) — DOM chọn sẵn Việt Nam
    "CongDan_diDong": "dom-input",                   # (10) Số điện thoại (*)
    "CongDan_email": "dom-input",                    # (11) Email (*)
    # Phần III — lệ phí trước bạ (cổng tự điền sau Tra cứu; ô vẫn cho sửa).
    "CongDan__fsMaHsLPTBDienTu": "dom-input",        # (30)
    "CongDan__fsNgayCapLPTB": "dom-input",           # (31) ↔ LPTB "Ngày nộp"
    "CongDan__fsCoQuanCapLPTB": "dom-input",         # (32)
    "CongDan__fsCMNDNguoiNopThueLPTB": "dom-input",  # (33)
    "CongDan__fsMSTnguoiNopThueLPTB": "dom-input",   # (34)
    "CongDan__fsTenNguoiNopThue": "dom-input",       # (35)
    "CongDan__fsSDTNguoiNopThue": "dom-input",       # (36)
    "CongDan__fsDiaChiNguoiNopThue": "dom-input",    # (37)
    "CongDan__fsLoaiXe": "dom-input",                # (38)
    "CongDan__fsnhanHieu": "dom-input",              # (39)
    "CongDan__fssoLoai": "dom-input",                # (40)
    "CongDan__fsNamSanXuat": "dom-input",            # (41)
    "CongDan__fsSoMay1": "dom-input",                # (42)
    "CongDan__fsSoKhung": "dom-input",               # (43)
    "CongDan__fsDungTich": "dom-input",              # (44)
    "CongDan__fsCongSuat": "dom-input",              # (45)
    "CongDan__fsCanCuMienThuLPTB": "dom-input",      # (46)
    "CongDan__fsSoTienLPTB": "dom-input",            # (47)
    "CongDan__fsGiaTriTinhLPTB": "dom-input",        # (48)
    "CongDan__fsSoTienBangChuLPTB": "dom-input",     # (49)
    # Phần IV — hóa đơn điện tử (không có hóa đơn: tương đương theo HĐMB, mapping).
    "CongDan__fsLoaiHoaDon": "dom-input",            # (50)
    "CongDan__fsKyHieu": "dom-input",                # (51)
    "CongDan__fsHDDTMauSoHoaDon": "dom-input",       # (52)
    "CongDan__fsSoHoaDon": "dom-input",              # (53)
    "CongDan__fsTenHangHoa": "dom-input",            # (54)
    "CongDan__fsDonViBanHang": "dom-input",          # (55)
    "CongDan__fsMSTNguoiBan": "dom-input",           # (56)
    "CongDan__fsDiaChiNguoiBan": "dom-input",        # (57)
    "CongDan__fsDonViNguoiMua": "dom-input",         # (58)
    "CongDan__fsHoTenNguoiMua": "dom-input",         # (59)
    "CongDan__fsMSTNguoiMua": "dom-input",           # (60)
    "CongDan__fsDiaChiNguoiMua": "dom-input",        # (61)
    "CongDan__fsTienthue": "dom-input",              # (62)
    "CongDan__fsTongCongTienThanhToan": "dom-input",          # (63)
    "CongDan__fsTongCongTienThanhToanBangChu": "dom-input",   # (64)
    "CongDan__fsHDDTNgayCap": "dom-input",           # (65)
    # Phần V — thông tin xe (Hải quan + Cục Đăng kiểm). Tên ô kỹ thuật lấy lại của bản xe trong nước: SoMay2DK là "Số
    # tờ khai nhập khẩu", TenDonViSanXuat là "Tên đơn vị nhập khẩu", DkNgayXuatXuong là "Ngày cấp tờ khai".
    "CongDan__fsTenDonViSanXuat": "dom-input",       # (67) Tên đơn vị nhập khẩu
    "CongDan__fsDiaChiDK": "dom-input",              # (68) Địa chỉ đơn vị nhập khẩu
    "CongDan__fsSoMay2DK": "dom-input",              # (69) Số tờ khai nhập khẩu
    "CongDan__fsDkNgayXuatXuong": "dom-input",       # (70) Ngày cấp tờ khai
    "CongDan__fsCoQuanHaiQuanDK": "dom-input",       # (71) Cơ quan hải quan nhập khẩu
    "CongDan__fsnhanHieuDK": "dom-input",            # (72)
    "CongDan__fsSoLoaiDK": "dom-input",              # (73)
    "CongDan__fsMauSonDK": "dom-input",              # (74)
    "CongDan__fsNamSanXuatDK": "dom-input",          # (75)
    "CongDan__fsSoMay1DK": "dom-input",              # (76)
    "CongDan__fsSoKhungDK": "dom-input",             # (77)
    "CongDan__fsDungTichXiLanhDK": "dom-input",      # (78) cm3, chỉ số
    "CongDan__fsCongSuatDK": "dom-input",            # (79) kW, chỉ số — ô tô bắt buộc
    "CongDan__fsLoaiXeDK": "dom-input",              # (82)
    "CongDan__fsTrongTaiDK": "dom-input",            # (86) kg
    "CongDan__fsSoChoNgoiDK": "dom-input",           # (87)
    "CongDan__fsSoChoDungDK": "dom-input",           # (88)
    "CongDan__fsSoChoNamDK": "dom-input",            # (89)
    "CongDan__fsNuocSanXuatDK": "dom-input",         # (94)
    # Phần VII — hình thức nhận kết quả. Tỉnh phát TRƯỚC Xã (danh mục xã nạp theo tỉnh).
    "CongDan__fsHinhThucNhanKQ": "dom-select",       # (103) (*)
    "CongDan__fsTenNguoiNhanKQ": "dom-input",        # (104)
    "CongDan__fsSoDienThoaiNguoiNhan": "dom-input",  # (105)
    "CongDan__fsTinhNhanKQ": "dom-select",           # (106)
    "CongDan__fsXaNhanKQ": "dom-select",             # (108) (*)
    "CongDan__fsDiaChiChiTietNhanKQ": "dom-input",   # (109)
}

# Option "Ô tô / xe máy" và "Hình thức nhận kết quả" đúng chữ trên cổng.
LOAI_XE = {"o_to": "Ô tô", "xe_may": "Xe máy"}
HINH_THUC_NHAN_KQ = {
    "co_quan": "Đến cơ quan giải quyết để nhận kết quả",
    "dia_chi": "Gửi hồ sơ đến địa chỉ của tôi",
    "qua_mang": "Nhận kết quả qua mạng",
    "buu_dien": "Qua bưu điện, tại nhà",
}
