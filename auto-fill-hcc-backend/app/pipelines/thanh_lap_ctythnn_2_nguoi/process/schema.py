"""Compact schema cho thủ tục "Đăng ký thành lập công ty TNHH hai thành viên trở lên".

Cùng mô hình với app/pipelines/thanh_lap_ctcp: LLM trả MỘT bộ "facts" thô đọc từ giấy tờ, mapper
chọn field UI cho từng trang WebForms để extension điền lần lượt từng trang một.

Nguồn giấy tờ (theo cột "Dữ liệu được lấy từ" của bảng đặc tả 9 sheet):
  - Giấy đề nghị đăng ký doanh nghiệp (GĐN, mẫu theo Nghị định 168/2025/NĐ-CP) — nguồn CHÍNH.
  - Điều lệ công ty — nguồn của bảng vốn góp từng thành viên, quyền hạn người đại diện.
  - Danh sách thành viên — nguồn CHÍNH của trang "Thông tin thành viên".
  - Danh sách chủ sở hữu hưởng lợi của doanh nghiệp — nguồn ĐỐI CHIẾU cho nhân thân thành viên.
  - Giấy ủy quyền — nguồn của vai trò + nhân thân người nộp hồ sơ.
  - CCCD — nguồn nhân thân (họ tên, giới tính, ngày sinh, số định danh, nơi thường trú).

KHÁC CTCP ở ba điểm:
  1. KHÔNG có trang "Thông tin về cổ phần" (mệnh giá/loại cổ phần) — loại hình này không có cổ phần.
  2. THÊM trang "Thông tin thành viên" và "Người đại diện theo pháp luật".
  3. Trang "Người đại diện của tổ chức" (InfoAuthorizedrepforforeignfounderE.aspx) CHỈ xuất hiện khi
     thành viên là TỔ CHỨC. Bảng đặc tả ghi rõ "không áp dụng" cho mọi dòng nên KHÔNG khai ở đây —
     khai mà không có nguồn dữ liệu là điền mò vào hồ sơ thật.
"""

PAGES: list[dict] = [
    {"key": "hinh-thuc-dang-ky", "label": "Hình thức đăng ký"},
    {"key": "dia-chi", "label": "Địa chỉ"},
    {"key": "nganh-nghe-kinh-doanh", "label": "Ngành nghề kinh doanh"},
    {"key": "ten-doanh-nghiep", "label": "Tên doanh nghiệp/đơn vị trực thuộc"},
    {"key": "thong-tin-ve-von", "label": "Thông tin về vốn"},
    {"key": "thong-tin-thanh-vien", "label": "Thông tin thành viên"},
    {"key": "nguoi-dai-dien-phap-luat", "label": "Người đại diện theo pháp luật"},
    {"key": "thong-tin-ve-thue", "label": "Thông tin về thuế"},
    {"key": "nguoi-nop-ho-so", "label": "Người nộp hồ sơ"},
]

DEFAULT_PAGE = "hinh-thuc-dang-ky"

FIELDS: list[dict] = [
    # ===== TRANG "ĐỊA CHỈ" =====
    {
        "name": "TruSo_DiaChi",
        "desc": ("Địa chỉ trụ sở chính, object {quocGia,tinh,xa,diaChi}. GĐN mục 3 / Điều lệ Điều 3 "
                 "\"Trụ sở chính\". BỎ cấp huyện/quận (biểu mẫu chỉ có xã và tỉnh)."),
    },
    {
        "name": "TruSo_KhuVuc",
        "desc": ('Doanh nghiệp nằm trong khu nào, array các chuỗi trong {"khu cong nghiep",'
                 '"khu che xuat","khu kinh te","khu cong nghe cao"}; chỉ trả ô ĐƯỢC TÍCH ở mục 3 '
                 "GĐN. Không tích ô nào thì bỏ field."),
    },
    {"name": "TruSo_DienThoai", "desc": "Điện thoại của doanh nghiệp (GĐN mục 3 / Điều lệ Điều 3)."},
    {"name": "TruSo_Fax", "desc": "Số fax của doanh nghiệp nếu có."},
    {"name": "TruSo_Email", "desc": "Thư điện tử của doanh nghiệp nếu có."},
    {"name": "TruSo_Website", "desc": "Website của doanh nghiệp nếu có."},

    # ===== TRANG "NGÀNH NGHỀ KINH DOANH" =====
    {
        "name": "NganhNghe_DanhSach",
        "desc": ("Bảng ngành, nghề kinh doanh ở GĐN mục 4 (đối chiếu Điều lệ Điều 5), array object "
                 "{ma,ten,chinh}. LẤY MỌI dòng có tên ngành KỂ CẢ khi cột mã ngành trống (ma=\"\"). "
                 "Có mã thì ma phải là đúng 4 chữ số liền nhau. chinh=true cho dòng được đánh dấu X ở "
                 "cột \"Ngành, nghề kinh doanh chính\" (chỉ MỘT dòng)."),
    },
    {"name": "NganhNghe_MaChinh", "desc": "Mã ngành nghề kinh doanh chính, đúng 4 chữ số liền nhau."},
    {"name": "NganhNghe_TenChinh", "desc": "Tên ngành nghề kinh doanh chính."},
    {
        "name": "NganhNghe_NgoaiHeThong",
        "desc": ("Phần ghi chi tiết ngành, nghề kinh doanh KHÔNG có trong Hệ thống ngành kinh tế Việt "
                 "Nam (GĐN mục 4, phần diễn giải dưới bảng). Trả nguyên văn, tối đa 20.000 ký tự."),
    },

    # ===== TRANG "TÊN DOANH NGHIỆP" =====
    {
        "name": "DoanhNghiep_TenLoaiHinh",
        "desc": ('Tiền tố loại hình trong tên tiếng Việt, CHỈ một trong "CÔNG TY TNHH" hoặc '
                 '"CÔNG TY TRÁCH NHIỆM HỮU HẠN" theo đúng chữ ghi ở GĐN mục 2. TUYỆT ĐỐI KHÔNG trả '
                 '"CÔNG TY TNHH MTV"/"MỘT THÀNH VIÊN" — hồ sơ này là hai thành viên trở lên.'),
    },
    {
        "name": "DoanhNghiep_TenRieng",
        "desc": ("Phần TÊN RIÊNG của công ty (đã BỎ tiền tố loại hình), viết hoa. GĐN mục 2 / Điều lệ "
                 "Điều 2 \"Tên doanh nghiệp\"."),
    },
    {"name": "DoanhNghiep_TenNuocNgoai", "desc": "Tên công ty bằng tiếng nước ngoài nếu có (GĐN mục 2)."},
    {"name": "DoanhNghiep_TenVietTat", "desc": "Tên công ty viết tắt nếu có (GĐN mục 2)."},

    # ===== TRANG "THÔNG TIN VỀ VỐN" =====
    {"name": "Von_DieuLe", "desc": "Vốn điều lệ bằng số, đơn vị đồng (GĐN mục 5 / Điều lệ Điều 8)."},
    {"name": "Von_NgoaiTe_GiaTri", "desc": "Giá trị tương đương theo đơn vị tiền nước ngoài, bằng số, nếu GĐN có ghi."},
    {"name": "Von_NgoaiTe_LoaiTien", "desc": 'Loại ngoại tệ tương ứng, mã 3 ký tự: USD, EUR, CHF, SGD, JPY, KRW, CNY, TWD.'},
    {
        "name": "Von_NguonVon",
        "desc": ("Bảng \"Nguồn vốn điều lệ\" ở GĐN mục 6, array object {loai,tyLe,soTien}. "
                 "loai CHỈ nhận: \"ngan_sach\" (Vốn ngân sách nhà nước), \"tu_nhan\" (Vốn tư nhân), "
                 "\"nuoc_ngoai\" (Vốn nước ngoài), \"khac\" (Vốn khác). tyLe là % dạng số, soTien là "
                 "VNĐ dạng số. BỎ dòng \"Tổng cộng\" — cổng tự cộng."),
    },
    {
        "name": "Von_TaiSanGopVon",
        "desc": ("Bảng tài sản góp vốn (Điều lệ Điều 8 \"Bảng vốn góp\" / cột loại tài sản góp vốn của "
                 "Danh sách thành viên), array object {loai,tyLe,giaTri}. loai CHỈ nhận: \"dong_vn\", "
                 "\"ngoai_te\", \"vang\", \"quyen_su_dung_dat\", \"so_huu_tri_tue\", \"khac\". Đây là "
                 "TỔNG của công ty theo từng loại tài sản, KHÔNG phải phần góp của một thành viên. "
                 "BỎ dòng tổng."),
    },

    # ===== TRANG "THÔNG TIN THÀNH VIÊN" =====
    {
        "name": "ThanhVien_DanhSach",
        "desc": ("Danh sách THÀNH VIÊN GÓP VỐN của công ty (Danh sách thành viên là nguồn chính; đối "
                 "chiếu Điều lệ Điều 8 và Danh sách chủ sở hữu hưởng lợi), array object: "
                 "{hoTen,gioiTinh,ngaySinh,soGiayToPhapLy,quocTich,danToc,diaChiLienLac,dienThoai,"
                 "fax,website,email,vonGop,tyLeSoHuu,soNgayGopVon,ngayGopVonCuThe,ghiChu}. "
                 "diaChiLienLac là object {quocGia,tinh,xa,diaChi}. vonGop và tyLeSoHuu là SỐ "
                 "(VNĐ và %). soNgayGopVon là SỐ NGÀY khi hồ sơ ghi thời hạn dạng \"trong vòng 90 "
                 "ngày kể từ ngày cấp GCN ĐKDN\"; ngayGopVonCuThe dd/mm/yyyy chỉ khi hồ sơ ấn định "
                 "một NGÀY cụ thể. GIỮ ĐÚNG THỨ TỰ các dòng in trên Danh sách thành viên."),
    },

    # ===== TRANG "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT" =====
    {"name": "NguoiDaiDien_HoTen", "desc": "Họ tên người đại diện theo pháp luật (GĐN mục 8 / Điều lệ Điều 7)."},
    {"name": "NguoiDaiDien_GioiTinh", "desc": 'Giới tính người đại diện theo pháp luật: "Nam" hoặc "Nữ".'},
    {"name": "NguoiDaiDien_NgaySinh", "desc": "Ngày sinh người đại diện theo pháp luật, dd/mm/yyyy."},
    {"name": "NguoiDaiDien_SoDinhDanh", "desc": "Số định danh cá nhân/số giấy tờ pháp lý của người đại diện theo pháp luật."},
    {
        "name": "NguoiDaiDien_DiaChi",
        "desc": ("Địa chỉ liên lạc của người đại diện theo pháp luật, object {quocGia,tinh,xa,diaChi}; "
                 "ưu tiên \"Nơi thường trú\" trên CCCD, không có thì lấy địa chỉ liên lạc ở GĐN mục 8."),
    },
    {"name": "NguoiDaiDien_DienThoai", "desc": "Điện thoại người đại diện theo pháp luật (GĐN mục 9.1)."},
    {"name": "NguoiDaiDien_Fax", "desc": "Fax người đại diện theo pháp luật nếu có."},
    {"name": "NguoiDaiDien_Website", "desc": "Website người đại diện theo pháp luật nếu có."},
    {"name": "NguoiDaiDien_Email", "desc": "Thư điện tử người đại diện theo pháp luật."},
    {
        "name": "NguoiDaiDien_QuyenHan",
        "desc": ("Quyền hạn/chức danh của người đại diện theo pháp luật, trả NGUYÊN VĂN đoạn mô tả ở "
                 "Điều lệ (vd Điều 7 \"Giám đốc là người đại diện theo pháp luật của công ty...\") "
                 "hoặc GĐN. Tối đa 4000 ký tự."),
    },

    # ===== TRANG "THÔNG TIN VỀ THUẾ" =====
    {
        "name": "Thue_DiaChiNhanThongBao",
        "desc": ("Địa chỉ nhận thông báo thuế ở GĐN mục 9.3, object {quocGia,tinh,xa,diaChi}. "
                 "CHỈ trả khi mục này được kê khai KHÁC trụ sở chính; để trống nghĩa là giống trụ sở."),
    },
    {"name": "Thue_DienThoai", "desc": "Điện thoại nhận thông báo thuế (GĐN mục 9.3)."},
    {"name": "Thue_Fax", "desc": "Fax nhận thông báo thuế nếu có."},
    {"name": "Thue_Email", "desc": "Thư điện tử nhận thông báo thuế nếu có."},
    {
        "name": "Thue_HinhThucHachToan",
        "desc": 'Ô được tích ở GĐN mục 9.5: "Hạch toán độc lập" hoặc "Hạch toán phụ thuộc".',
    },
    {"name": "Thue_CoBaoCaoHopNhat", "desc": 'Boolean: ô "Có báo cáo tài chính hợp nhất" ở mục 9.5 có được tích không.'},
    {
        "name": "Thue_NamTaiChinh",
        "desc": ("Năm tài chính ở GĐN mục 9.6, object {ngayBatDau,thangBatDau,ngayKetThuc,"
                 "thangKetThuc}; tất cả là SỐ (vd ngayBatDau=1, thangBatDau=1, ngayKetThuc=31, "
                 "thangKetThuc=12)."),
    },
    {"name": "Thue_NgayBatDauHoatDong", "desc": "Ngày bắt đầu hoạt động (GĐN mục 9.4), dd/mm/yyyy."},
    {"name": "Thue_SoLaoDong", "desc": 'Tổng số lao động dự kiến (GĐN mục 9.7); chỉ trả chữ số.'},
    {
        "name": "Thue_PhuongPhapGTGT",
        "desc": ('Ô được tích ở GĐN mục 9.9, CHỈ một trong: "Khấu trừ", "Trực tiếp trên GTGT", '
                 '"Trực tiếp trên doanh số", "Không phải nộp thuế GTGT".'),
    },
    {"name": "Thue_DuAnBOT", "desc": "Boolean: mục 9.8 có tích hoạt động theo dự án BOT/BTO/BT/BOO/BLT/BTL/O&M không."},

    # ===== TRANG "NGƯỜI NỘP HỒ SƠ" =====
    {
        "name": "NguoiNop_VaiTro",
        "desc": ('Vai trò người nộp ở phần ký cuối GĐN, CHỈ một trong: "Người được ủy quyền" (hồ sơ có '
                 'kèm Giấy ủy quyền và người ký/đi nộp là bên ĐƯỢC ủy quyền) hoặc "Người có thẩm quyền '
                 'ký" (người đại diện theo pháp luật tự ký, không có giấy ủy quyền).'),
    },
    {"name": "NguoiNop_HoTen", "desc": "Họ tên người nộp hồ sơ (Giấy ủy quyền phần \"Bên được ủy quyền\" / CCCD / GĐN phần ký)."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính người nộp hồ sơ: "Nam" hoặc "Nữ".'},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh người nộp hồ sơ, dd/mm/yyyy."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số định danh cá nhân/CCCD của người nộp hồ sơ."},
    {
        "name": "NguoiNop_DiaChi",
        "desc": ("Địa chỉ liên lạc của người nộp hồ sơ, object {quocGia,tinh,xa,diaChi}; ưu tiên "
                 "\"Nơi thường trú\" trên CCCD, không có thì lấy địa chỉ liên lạc ghi ở Giấy ủy quyền."),
    },
    {"name": "NguoiNop_DienThoai", "desc": "Điện thoại người nộp hồ sơ."},
    {"name": "NguoiNop_Fax", "desc": "Fax người nộp hồ sơ nếu có."},
    {"name": "NguoiNop_Email", "desc": "Thư điện tử người nộp hồ sơ."},
    {
        "name": "NguoiNop_DiaChiNhanKetQua",
        "desc": ('Hình thức/địa chỉ nhận kết quả qua đường bưu điện — lấy ở Giấy ủy quyền mục "Nội dung '
                 'ủy quyền" (vd "Nhận kết quả của công ty") hoặc Giấy tiếp nhận hồ sơ. Không có thì bỏ '
                 "field (mặc định nhận trực tiếp)."),
    },
    {
        "name": "Cccd_DanhSach",
        "desc": ("Danh sách MỌI thẻ căn cước/CCCD/CMND có trong hồ sơ, array object "
                 "{hoTen,gioiTinh,ngaySinh,soDinhDanh,diaChi}; diaChi là object {quocGia,tinh,xa,diaChi} "
                 "đọc từ \"Nơi thường trú\". Mặt trước + mặt sau của cùng một thẻ chỉ là MỘT object. "
                 "KHÔNG suy vai trò từ thứ tự file — cứ liệt kê đủ để extension đối chiếu với tài khoản "
                 "đang đăng nhập."),
    },
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("TruSo_DiaChi", "Thue_DiaChiNhanThongBao", "NguoiDaiDien_DiaChi", "NguoiNop_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"
for _name in ("Thue_NgayBatDauHoatDong", "NguoiDaiDien_NgaySinh", "NguoiNop_NgaySinh"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("TruSo_KhuVuc", "NganhNghe_DanhSach", "Von_NguonVon", "Von_TaiSanGopVon",
              "ThanhVien_DanhSach", "Thue_NamTaiChinh", "Cccd_DanhSach"):
    COMPACT_COMP_BY_NAME[_name] = "raw"
