"""Compact schema cho thủ tục "Đăng ký thành lập công ty cổ phần".

Cùng mô hình với app/pipelines/dang_ky_kinh_doanh: LLM trả MỘT bộ "facts" thô đọc từ giấy tờ, mapper
chọn field UI cho từng trang WebForms để extension điền lần lượt từng trang một.

Nguồn giấy tờ (theo cột "Dữ liệu được lấy từ" của bảng đặc tả):
  - Mẫu 4-CP: Giấy đề nghị đăng ký doanh nghiệp (công ty cổ phần) — nguồn CHÍNH.
  - Mẫu 7-DSCĐ: Danh sách cổ đông sáng lập — nguồn của bảng tài sản góp vốn / số lượng cổ phần.
  - Quyết định thành lập, GCN ĐKDN: nguồn bù cho tên công ty, vốn điều lệ, thông tin liên hệ.
  - CCCD: nhân thân người nộp hồ sơ.
  - Giấy tiếp nhận hồ sơ: họ tên/điện thoại/email người nộp.

CHỈ khai 7 trang ĐÃ CÓ ĐẶC TẢ. Menu khối dữ liệu của cổng còn các trang khác (Cổ đông sáng lập,
Cổ đông là nhà đầu tư nước ngoài, Người đại diện theo pháp luật, Chủ sở hữu hưởng lợi, Đại diện của
tổ chức, Bảo hiểm xã hội) — chưa có đặc tả field nên CHƯA khai, tránh điền mò vào hồ sơ thật.
"""

PAGES: list[dict] = [
    {"key": "hinh-thuc-dang-ky", "label": "Hình thức đăng ký"},
    {"key": "dia-chi", "label": "Địa chỉ"},
    {"key": "nganh-nghe-kinh-doanh", "label": "Ngành nghề kinh doanh"},
    {"key": "ten-doanh-nghiep", "label": "Tên doanh nghiệp/đơn vị trực thuộc"},
    {"key": "thong-tin-ve-von", "label": "Thông tin về vốn"},
    {"key": "thong-tin-ve-co-phan", "label": "Thông tin về cổ phần"},
    {"key": "thong-tin-ve-thue", "label": "Thông tin về thuế"},
    {"key": "nguoi-nop-ho-so", "label": "Người nộp hồ sơ"},
]

DEFAULT_PAGE = "hinh-thuc-dang-ky"

FIELDS: list[dict] = [
    # ===== TRANG "ĐỊA CHỈ" =====
    {
        "name": "TruSo_DiaChi",
        "desc": ("Địa chỉ trụ sở chính, object {quocGia,tinh,xa,diaChi}. Mẫu 4-CP mục 3 / GCN ĐKDN "
                 "dòng \"Địa chỉ trụ sở chính\". BỎ cấp huyện/quận (biểu mẫu chỉ có xã và tỉnh)."),
    },
    {
        "name": "TruSo_KhuVuc",
        "desc": ('Doanh nghiệp nằm trong khu nào, array các chuỗi trong {"khu cong nghiep",'
                 '"khu che xuat","khu kinh te","khu cong nghe cao"}; chỉ trả ô ĐƯỢC TÍCH ở mục 3 '
                 "Mẫu 4-CP. Không tích ô nào thì bỏ field."),
    },
    {"name": "TruSo_DienThoai", "desc": "Điện thoại của doanh nghiệp (Mẫu 4-CP mục 3 / GCN ĐKDN)."},
    {"name": "TruSo_Fax", "desc": "Số fax của doanh nghiệp nếu có."},
    {"name": "TruSo_Email", "desc": "Thư điện tử của doanh nghiệp nếu có."},
    {"name": "TruSo_Website", "desc": "Website của doanh nghiệp nếu có."},

    # ===== TRANG "NGÀNH NGHỀ KINH DOANH" =====
    {
        "name": "NganhNghe_DanhSach",
        "desc": ("Bảng ngành, nghề kinh doanh ở Mẫu 4-CP mục 4, array object {ma,ten,chinh}. LẤY MỌI "
                 "dòng có tên ngành KỂ CẢ khi cột mã ngành trống (ma=\"\"). Có mã thì ma phải là đúng "
                 "4 chữ số liền nhau. chinh=true cho dòng được đánh dấu X ở cột \"Ngành, nghề kinh "
                 "doanh chính\" (chỉ MỘT dòng)."),
    },
    {"name": "NganhNghe_MaChinh", "desc": "Mã ngành nghề kinh doanh chính, đúng 4 chữ số liền nhau."},
    {"name": "NganhNghe_TenChinh", "desc": "Tên ngành nghề kinh doanh chính."},
    {
        "name": "NganhNghe_NgoaiHeThong",
        "desc": ("Phần ghi chi tiết ngành, nghề kinh doanh KHÔNG có trong Hệ thống ngành kinh tế Việt "
                 "Nam (Mẫu 4-CP mục 4, phần diễn giải dưới bảng). Trả nguyên văn, tối đa 20.000 ký tự."),
    },

    # ===== TRANG "TÊN DOANH NGHIỆP" =====
    {
        "name": "DoanhNghiep_TenLoaiHinh",
        "desc": ('Tiền tố loại hình trong tên tiếng Việt, CHỈ một trong "CÔNG TY CỔ PHẦN" hoặc '
                 '"CÔNG TY CP" theo đúng chữ ghi trên Mẫu 4-CP mục 2 / Quyết định thành lập.'),
    },
    {
        "name": "DoanhNghiep_TenRieng",
        "desc": ("Phần TÊN RIÊNG của công ty (đã BỎ tiền tố loại hình), viết hoa. Mẫu 4-CP mục 2 / "
                 "Quyết định thành lập Điều 1 / GCN ĐKDN."),
    },
    {"name": "DoanhNghiep_TenNuocNgoai", "desc": "Tên công ty bằng tiếng nước ngoài nếu có."},
    {"name": "DoanhNghiep_TenVietTat", "desc": "Tên công ty viết tắt nếu có."},

    # ===== TRANG "THÔNG TIN VỀ VỐN" =====
    {"name": "Von_DieuLe", "desc": "Vốn điều lệ bằng số, đơn vị đồng (Mẫu 4-CP mục 5 / Quyết định thành lập / GCN ĐKDN)."},
    {"name": "Von_NgoaiTe_GiaTri", "desc": "Giá trị tương đương theo đơn vị tiền nước ngoài, bằng số, nếu Mẫu 4-CP có ghi."},
    {"name": "Von_NgoaiTe_LoaiTien", "desc": 'Loại ngoại tệ tương ứng, mã 3 ký tự: USD, EUR, CHF, SGD, JPY, KRW, CNY, TWD.'},
    {
        "name": "Von_NguonVon",
        "desc": ("Bảng \"Nguồn vốn điều lệ\" ở Mẫu 4-CP mục 6, array object {loai,tyLe,soTien}. "
                 "loai CHỈ nhận: \"ngan_sach\" (Vốn ngân sách nhà nước), \"tu_nhan\" (Vốn tư nhân), "
                 "\"nuoc_ngoai\" (Vốn nước ngoài), \"khac\" (Vốn khác). tyLe là % dạng số, soTien là "
                 "VNĐ dạng số. BỎ dòng \"Tổng cộng\" — cổng tự cộng."),
    },
    {
        "name": "Von_TaiSanGopVon",
        "desc": ("Bảng tài sản góp vốn ở Mẫu 7-DSCĐ cột 15 (\"Loại tài sản, số lượng, giá trị tài sản "
                 "góp vốn\"), array object {loai,tyLe,giaTri}. loai CHỈ nhận: \"dong_vn\", \"ngoai_te\", "
                 "\"vang\", \"quyen_su_dung_dat\", \"so_huu_tri_tue\", \"khac\". BỎ dòng tổng."),
    },

    # ===== TRANG "THÔNG TIN VỀ CỔ PHẦN" =====
    {"name": "CoPhan_MenhGia", "desc": "Mệnh giá cổ phần (VNĐ) bằng số — Mẫu 4-CP mục 7 / GCN ĐKDN."},
    {
        "name": "CoPhan_DanhSach",
        "desc": ("Bảng loại và số lượng cổ phần ở Mẫu 4-CP mục 7 (đối chiếu Mẫu 7-DSCĐ cột 9/10/11), "
                 "array object {loai,soLuong,menhGia,giaTri,tyLe}. loai CHỈ nhận: \"pho_thong\", "
                 "\"uu_dai_bieu_quyet\", \"uu_dai_co_tuc\", \"uu_dai_hoan_lai\", \"uu_dai_khac\". "
                 "Tất cả là số. BỎ dòng \"Tổng số\" — cổng tự cộng."),
    },
    {
        "name": "CoPhan_ChaoBan",
        "desc": ("Bảng \"Thông tin về cổ phần được quyền chào bán\" ở Mẫu 4-CP mục 7, array object "
                 "{loai,soLuong}; loai dùng đúng bộ giá trị như CoPhan_DanhSach. BỎ dòng tổng."),
    },

    # ===== TRANG "THÔNG TIN VỀ THUẾ" =====
    {
        "name": "Thue_DiaChiNhanThongBao",
        "desc": ("Địa chỉ nhận thông báo thuế ở Mẫu 4-CP mục 11.3, object {quocGia,tinh,xa,diaChi}. "
                 "CHỈ trả khi mục này được kê khai KHÁC trụ sở chính; để trống nghĩa là giống trụ sở."),
    },
    {"name": "Thue_DienThoai", "desc": "Điện thoại nhận thông báo thuế (Mẫu 4-CP mục 11.3)."},
    {"name": "Thue_Fax", "desc": "Fax nhận thông báo thuế nếu có."},
    {"name": "Thue_Email", "desc": "Thư điện tử nhận thông báo thuế nếu có."},
    {
        "name": "Thue_HinhThucHachToan",
        "desc": 'Ô được tích ở Mẫu 4-CP mục 11.5: "Hạch toán độc lập" hoặc "Hạch toán phụ thuộc".',
    },
    {"name": "Thue_CoBaoCaoHopNhat", "desc": 'Boolean: ô "Có báo cáo tài chính hợp nhất" ở mục 11.5 có được tích không.'},
    {
        "name": "Thue_NamTaiChinh",
        "desc": ("Năm tài chính ở Mẫu 4-CP mục 11.6, object {ngayBatDau,thangBatDau,ngayKetThuc,"
                 "thangKetThuc}; tất cả là SỐ (vd ngayBatDau=1, thangBatDau=1, ngayKetThuc=31, "
                 "thangKetThuc=12)."),
    },
    {"name": "Thue_NgayBatDauHoatDong", "desc": "Ngày bắt đầu hoạt động (Mẫu 4-CP mục 11.4), dd/mm/yyyy."},
    {"name": "Thue_SoLaoDong", "desc": 'Tổng số lao động dự kiến (Mẫu 4-CP mục 11.7); chỉ trả chữ số.'},
    {
        "name": "Thue_PhuongPhapGTGT",
        "desc": ('Ô được tích ở Mẫu 4-CP mục 11.9, CHỈ một trong: "Khấu trừ", "Trực tiếp trên GTGT", '
                 '"Trực tiếp trên doanh số", "Không phải nộp thuế GTGT".'),
    },
    {"name": "Thue_DuAnBOT", "desc": "Boolean: mục 11.8 có tích hoạt động theo dự án BOT/BTO/BT/BOO/BLT/BTL/O&M không."},

    # ===== TRANG "NGƯỜI NỘP HỒ SƠ" =====
    {
        "name": "NguoiNop_VaiTro",
        "desc": ('Vai trò người nộp ở phần ký cuối Mẫu 4-CP, CHỈ một trong: "Người được ủy quyền" '
                 '(có kèm văn bản uỷ quyền) hoặc "Người có thẩm quyền ký" (người đại diện theo pháp '
                 "luật / chủ tịch hội đồng quản trị tự ký)."),
    },
    {"name": "NguoiNop_HoTen", "desc": "Họ tên người nộp hồ sơ (CCCD / Mẫu 4-CP phần ký / Giấy tiếp nhận hồ sơ)."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính người nộp hồ sơ: "Nam" hoặc "Nữ".'},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh người nộp hồ sơ, dd/mm/yyyy."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số định danh cá nhân/CCCD của người nộp hồ sơ."},
    {
        "name": "NguoiNop_DiaChi",
        "desc": ("Địa chỉ liên lạc của người nộp hồ sơ, object {quocGia,tinh,xa,diaChi}; ưu tiên "
                 "\"Nơi thường trú\" trên CCCD, không có thì lấy địa chỉ liên lạc ở phần mở đầu Mẫu 4-CP."),
    },
    {"name": "NguoiNop_DienThoai", "desc": "Điện thoại người nộp hồ sơ."},
    {"name": "NguoiNop_Fax", "desc": "Fax người nộp hồ sơ nếu có."},
    {"name": "NguoiNop_Email", "desc": "Thư điện tử người nộp hồ sơ."},
    {
        "name": "NguoiNop_DiaChiNhanKetQua",
        "desc": ('Địa chỉ nhận kết quả qua đường bưu điện — CHỈ lấy từ Giấy tiếp nhận hồ sơ mục "Nơi '
                 'nhận kết quả bản giấy". Không có thì bỏ field (mặc định nhận trực tiếp).'),
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
for _name in ("TruSo_DiaChi", "Thue_DiaChiNhanThongBao", "NguoiNop_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"
for _name in ("Thue_NgayBatDauHoatDong", "NguoiNop_NgaySinh"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("TruSo_KhuVuc", "NganhNghe_DanhSach", "Von_NguonVon", "Von_TaiSanGopVon",
              "CoPhan_DanhSach", "CoPhan_ChaoBan", "Thue_NamTaiChinh", "Cccd_DanhSach"):
    COMPACT_COMP_BY_NAME[_name] = "raw"
