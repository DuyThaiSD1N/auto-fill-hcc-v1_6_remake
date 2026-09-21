"""Compact schema cho "Cấp giấy phép xuất bản tài liệu không kinh doanh" (mã 1.003868).

Cổng Bộ VHTTDL `dichvucong.bvhttdl.gov.vn` — Angular Material bọc trong `liz-*`, form và bảng thành
phần hồ sơ NẰM CHUNG một trang `/nop-ho-so`. LLM chỉ trả FACT nguồn; `mapper.enrich` suy tất định ra
ô UI theo (section = `.group-header`, name = `<mat-label>`) cho engine `fill-liz.js`.

⚑ BA VAI KHÁC NHAU trên cùng một trang, rất dễ trộn:
  - NGƯỜI NỘP (Phần II) — cá nhân đăng nhập, cổng tự điền từ tài khoản định danh.
  - TỔ CHỨC ĐỀ NGHỊ cấp giấy phép (Phần III "Người được giải quyết") — mục 1-2 Đơn Mẫu 04.
  - DOANH NGHIỆP (Phần IV) — là **CƠ SỞ IN**, lấy từ Giấy chứng nhận ĐKDN + Giấy phép hoạt động in
    của nhà in, KHÔNG phải tổ chức đề nghị.
"""

FIELDS: list[dict] = [
    # ---- NGƯỜI NỘP (cá nhân đi nộp; cổng tự điền tên + số định danh nên chỉ cần phần còn lại) ----
    {"name": "NguoiNop_HoTen", "desc": "Họ tên NGƯỜI NỘP hồ sơ (cá nhân đi nộp), lấy từ CCCD của người đó. Không lấy tên tổ chức, không lấy người ký đơn nếu người ký không phải người nộp."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh người nộp, dd/mm/yyyy, lấy từ CCCD. Chỉ có năm thì bỏ field."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số định danh/CCCD của NGƯỜI NỘP, chỉ chữ số."},
    {"name": "NguoiNop_NgayCapCccd", "desc": "Ngày cấp CCCD của người nộp (mặt sau), dd/mm/yyyy."},
    {"name": "NguoiNop_NoiCapCccd", "desc": "Nơi cấp CCCD của người nộp: 'BỘ CÔNG AN' (thẻ căn cước 2024) hoặc 'CỤC TRƯỞNG CỤC CẢNH SÁT…' → 'Cục Cảnh sát quản lý hành chính về trật tự xã hội'."},
    {"name": "NguoiNop_NoiCuTru", "desc": "Nơi cư trú của NGƯỜI NỘP trên CCCD, object {tinh,xa,diaChi}."},
    {"name": "NguoiNop_DienThoai", "desc": "Điện thoại của người nộp, chỉ chữ số. Không có trên CCCD — chỉ lấy khi giấy tờ ghi rõ là số của chính người nộp."},
    {"name": "NguoiNop_Email", "desc": "Email của người nộp nếu giấy tờ ghi rõ."},

    # ---- TỔ CHỨC ĐỀ NGHỊ CẤP GIẤY PHÉP (Đơn Mẫu 04 mục 1-2) ----
    {
        "name": "ToChucDeNghi_Ten",
        "desc": "Tên CƠ QUAN, TỔ CHỨC ĐỀ NGHỊ cấp giấy phép xuất bản — mục 1 Đơn Mẫu 04 ('Tên cơ quan, "
                "tổ chức đề nghị cấp giấy phép xuất bản'), nguyên văn. TUYỆT ĐỐI không lấy tên nhà in / "
                "công ty in trong hồ sơ.",
    },
    {"name": "ToChucDeNghi_CoQuanChuQuan", "desc": "Tên CƠ QUAN CHỦ QUẢN của tổ chức đề nghị — dòng tiêu đề góc trái trên đầu Đơn Mẫu 04 (cấp trên của tổ chức đứng đơn). Không có thì bỏ field."},
    {"name": "ToChucDeNghi_DiaChi", "desc": "Địa chỉ của tổ chức đề nghị — mục 2 Đơn Mẫu 04, object {tinh,xa,diaChi}. Không phải địa chỉ cơ sở in."},
    {"name": "ToChucDeNghi_DienThoai", "desc": "Số điện thoại ghi ở mục 2 Đơn Mẫu 04 (của tổ chức đề nghị), chỉ chữ số."},
    {"name": "ToChucDeNghi_Email", "desc": "Email của tổ chức đề nghị nếu đơn ghi rõ. Đơn Mẫu 04 thường không có mục này → bỏ field."},
    {
        "name": "ToChucDeNghi_SoGcnDangKyKinhDoanh",
        "desc": "Số GCN đăng ký kinh doanh / GCN đầu tư / GCN đăng ký doanh nghiệp CỦA CHÍNH TỔ CHỨC ĐỀ "
                "NGHỊ (mục 1 Đơn Mẫu 04, chỉ áp dụng khi tổ chức đề nghị là doanh nghiệp). ⚠ Tổ chức đề "
                "nghị là đơn vị quân đội/công an/cơ quan nhà nước thì BỎ FIELD — không mượn số trên GCN "
                "đăng ký doanh nghiệp của cơ sở in.",
    },
    {"name": "ToChucDeNghi_SoQuyetDinhThanhLap", "desc": "Số quyết định thành lập của tổ chức đề nghị (chỉ khi là đơn vị sự nghiệp công lập), ghi ở mục 1 Đơn Mẫu 04. Không có thì bỏ field."},
    {"name": "ToChucDeNghi_SoGiayPhepHoatDong", "desc": "Số giấy phép hoạt động của tổ chức đề nghị (chỉ khi là cơ quan, tổ chức NƯỚC NGOÀI). ⚠ KHÔNG phải giấy phép hoạt động in của nhà in. Không có thì bỏ field."},
    {"name": "ToChucDeNghi_CoQuanCapGiayTo", "desc": "Cơ quan cấp giấy tờ pháp lý nêu trên của TỔ CHỨC ĐỀ NGHỊ. Bỏ field nếu không có giấy tờ tương ứng."},
    {"name": "ToChucDeNghi_NgayCapGiayTo", "desc": "Ngày cấp giấy tờ pháp lý nêu trên của TỔ CHỨC ĐỀ NGHỊ, dd/mm/yyyy. Bỏ field nếu không có."},

    # ---- CƠ SỞ IN = khối "Thông tin doanh nghiệp" (GCN ĐKDN + Giấy phép hoạt động in) ----
    {"name": "CoSoIn_MaSoThue", "desc": "Mã số doanh nghiệp/mã số thuế của CƠ SỞ IN trên Giấy chứng nhận đăng ký doanh nghiệp. Chỉ chữ số."},
    {"name": "CoSoIn_CoQuanCap", "desc": "Cơ quan cấp Giấy chứng nhận đăng ký doanh nghiệp của cơ sở in (vd 'Phòng Đăng ký kinh doanh - Sở Kế hoạch và Đầu tư tỉnh …')."},
    {"name": "CoSoIn_NgayDangKyLanDau", "desc": "Ngày 'Đăng ký lần đầu' trên GCN đăng ký doanh nghiệp của cơ sở in, dd/mm/yyyy."},
    {"name": "CoSoIn_NgayDangKyThayDoi", "desc": "Ngày 'Đăng ký thay đổi lần thứ …' gần nhất trên GCN đăng ký doanh nghiệp của cơ sở in, dd/mm/yyyy. Không có thì bỏ field."},
    {"name": "CoSoIn_TenTiengViet", "desc": "Tên cơ sở in viết bằng tiếng Việt, nguyên văn trên GCN đăng ký doanh nghiệp hoặc Giấy phép hoạt động in."},
    {"name": "CoSoIn_TenNuocNgoai", "desc": "Tên cơ sở in bằng tiếng nước ngoài trên GCN ĐKDN nếu có."},
    {"name": "CoSoIn_TenVietTat", "desc": "Tên viết tắt của cơ sở in trên GCN ĐKDN nếu có."},
    {"name": "CoSoIn_DienThoai", "desc": "Điện thoại của cơ sở in trên GCN ĐKDN nếu có, chỉ chữ số."},
    {"name": "CoSoIn_Fax", "desc": "Số fax của cơ sở in nếu có."},
    {"name": "CoSoIn_Email", "desc": "Email của cơ sở in nếu có."},
    {"name": "CoSoIn_Website", "desc": "Website của cơ sở in nếu có."},
    {"name": "CoSoIn_TruSo", "desc": "Địa chỉ trụ sở chính của CƠ SỞ IN, object {tinh,xa,diaChi}. Nguồn: GCN ĐKDN hoặc Giấy phép hoạt động in."},
    {"name": "CoSoIn_NguoiDaiDien_HoTen", "desc": "Họ tên người đại diện theo pháp luật của cơ sở in (GCN ĐKDN: 'Người đại diện theo pháp luật'; Giấy phép hoạt động in: người đứng đầu cơ sở in)."},
    {"name": "CoSoIn_NguoiDaiDien_SoDinhDanh", "desc": "Số CCCD/CMND của người đại diện theo pháp luật của cơ sở in, chỉ chữ số."},
    {"name": "CoSoIn_NguoiDaiDien_DiaChi", "desc": "Địa chỉ của người đại diện theo pháp luật của cơ sở in, object {tinh,xa,diaChi}. Không có thì bỏ field."},

    # ---- NỘI DUNG ĐƠN ĐỀ NGHỊ (Đơn Mẫu 04, mục 3-13) ----
    {"name": "TaiLieu_Ten", "desc": "Tên tài liệu xin cấp phép xuất bản — mục 3 Đơn Mẫu 04, đối chiếu tiêu đề trang bìa bản thảo."},
    {"name": "TaiLieu_XuatXu", "desc": "Xuất xứ tài liệu — mục 4 Đơn Mẫu 04, CHỈ khi là tài liệu dịch từ tiếng nước ngoài. Tài liệu tiếng Việt thì BỎ FIELD, không bịa."},
    {"name": "TaiLieu_NguoiDich", "desc": "Người dịch (cá nhân hoặc tập thể) — mục 4 Đơn Mẫu 04. Tài liệu không phải bản dịch thì bỏ field."},
    {"name": "TaiLieu_HinhThuc", "desc": "Hình thức tài liệu — mục 5 Đơn Mẫu 04 (vd 'tờ gấp', 'sách', 'đĩa CD')."},
    {"name": "TaiLieu_SoTrang", "desc": "Số trang (hoặc dung lượng byte với tài liệu điện tử) — mục 6 Đơn Mẫu 04."},
    {"name": "TaiLieu_PhuBan", "desc": "Phụ bản/phụ lục kèm theo nếu có — mục 6 Đơn Mẫu 04."},
    {"name": "TaiLieu_KhuonKho", "desc": "Khuôn khổ (định dạng) tính bằng cm — mục 7 Đơn Mẫu 04 (vd '21x29,7')."},
    {"name": "TaiLieu_SoLuongIn", "desc": "Số lượng in, đơn vị bản — mục 7 Đơn Mẫu 04. Chỉ chữ số."},
    {"name": "TaiLieu_NgonNgu", "desc": "Ngôn ngữ xuất bản của tài liệu (vd 'Tiếng Việt'). Đơn có thể không ghi — suy từ ngôn ngữ nội dung bản thảo."},
    {"name": "TaiLieu_TenCoSoIn", "desc": "Tên cơ sở in ghi ở mục 8 Đơn Mẫu 04. Thường trùng CoSoIn_TenTiengViet; đơn không ghi thì bỏ field."},
    {"name": "TaiLieu_DiaChiCoSoIn", "desc": "Địa chỉ cơ sở in ghi ở mục 8 Đơn Mẫu 04, dạng chuỗi nguyên văn."},
    {"name": "TaiLieu_MucDichXuatBan", "desc": "Mục đích xuất bản — mục 9 Đơn Mẫu 04, chép nguyên văn."},
    {"name": "TaiLieu_TomTatNoiDung", "desc": "Nội dung tóm tắt của tài liệu — mục 12 Đơn Mẫu 04, chép nguyên văn (có thể dài)."},
    {"name": "TaiLieu_KemTheoDon", "desc": "Nội dung mục 13 'Kèm theo đơn này gồm …' của Đơn Mẫu 04, chép nguyên văn (vd '02 bản thảo tài liệu')."},
    {"name": "Don_CoQuanNhan", "desc": "Cơ quan nhận đơn ghi ở dòng 'Kính gửi' đầu Đơn Mẫu 04 (vd 'Sở Văn hóa, Thể thao và Du lịch tỉnh …')."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _n in ("NguoiNop_NgaySinh", "NguoiNop_NgayCapCccd", "ToChucDeNghi_NgayCapGiayTo",
           "CoSoIn_NgayDangKyLanDau", "CoSoIn_NgayDangKyThayDoi"):
    COMPACT_COMP_BY_NAME[_n] = "x-date"
for _n in ("NguoiNop_NoiCuTru", "ToChucDeNghi_DiaChi", "CoSoIn_TruSo", "CoSoIn_NguoiDaiDien_DiaChi"):
    COMPACT_COMP_BY_NAME[_n] = "x-select-area"

# ---- UI fields cho engine fill-liz.js — khớp (section, mat-label) ----
S_NOP = "Thông tin người nộp hồ sơ"
S_GQ = "Thông tin người được giải quyết"
S_DN = "Thông tin doanh nghiệp"
S_DON = "Thông tin đơn đề nghị cấp giấy phép xuất bản"

# comp: liz-input (text/textarea) | liz-date (datepicker dd/mm/yyyy) | liz-select (mat-select overlay).
# Danh sách (section, label, comp) chép đúng <mat-label> trong DOM thật — kể cả "Tên tiếng việt" viết
# thường và "Địa chỉ trụ sở - Xã" dùng dấu gạch nối thường.
# Cố ý BỎ các ô cổng render `disabled` (Tên người nộp, CMND/Hộ chiếu/MST, Địa chỉ hành chính ở cả hai
# khối) — cổng tự điền từ tài khoản định danh, engine bơm vào cũng bị chặn.
UI_FIELDS: list[tuple[str, str, str]] = [
    (S_NOP, "Ngày sinh", "liz-date"),
    (S_NOP, "Số điện thoại", "liz-input"),
    (S_NOP, "Email", "liz-input"),
    (S_NOP, "Ngày cấp", "liz-date"),
    (S_NOP, "Nơi cấp", "liz-input"),
    (S_NOP, "Địa chỉ", "liz-input"),

    (S_GQ, "Tên người / Tên đơn vị được giải quyết", "liz-input"),
    (S_GQ, "Ngày sinh", "liz-date"),
    (S_GQ, "CMND/Hộ chiếu", "liz-input"),
    (S_GQ, "Số điện thoại", "liz-input"),
    (S_GQ, "Email", "liz-input"),
    (S_GQ, "Ngày cấp", "liz-date"),
    (S_GQ, "Nơi cấp", "liz-input"),
    (S_GQ, "Địa chỉ", "liz-input"),

    (S_DN, "Mã số thuế", "liz-input"),
    (S_DN, "Cơ quan cấp", "liz-input"),
    (S_DN, "Đăng ký lần đầu", "liz-date"),
    (S_DN, "Ngày đăng ký thay đổi", "liz-date"),
    (S_DN, "Tên tiếng việt", "liz-input"),
    (S_DN, "Tên nước ngoài", "liz-input"),
    (S_DN, "Tên viết tắt", "liz-input"),
    (S_DN, "Điện thoại", "liz-input"),
    (S_DN, "Fax", "liz-input"),
    (S_DN, "Email", "liz-input"),
    (S_DN, "Website", "liz-input"),
    (S_DN, "Địa chỉ trụ sở - Tỉnh/TP", "liz-input"),
    (S_DN, "Địa chỉ trụ sở - Xã", "liz-input"),
    (S_DN, "Địa chỉ chi tiết trụ sở", "liz-input"),
    (S_DN, "Số CCCD người đại diện pháp luật", "liz-input"),
    (S_DN, "Tên người đại diện pháp luật", "liz-input"),
    (S_DN, "Địa chỉ người đại diện pháp luật", "liz-input"),

    (S_DON, "TÊN CƠ QUAN CHỦ QUẢN (NẾU CÓ)", "liz-input"),
    (S_DON, "Số GCN đăng ký kinh doanh/ GCN đầu tư/ GCN đăng ký doanh nghiệp (đối với doanh nghiệp)", "liz-input"),
    (S_DON, "Số quyết định thành lập (đối với đơn vị sự nghiệp công lập)", "liz-input"),
    (S_DON, "Số giấy phép hoạt động (đối với cơ quan, tổ chức nước ngoài)", "liz-input"),
    (S_DON, "Cơ quan cấp", "liz-input"),
    (S_DON, "Ngày cấp", "liz-date"),
    (S_DON, "Tên tài liệu", "liz-input"),
    (S_DON, "Xuất xứ (nếu là tài liệu dịch từ tiếng nước ngoài)", "liz-input"),
    (S_DON, "Người dịch (cá nhân hoặc tập thể)", "liz-input"),
    (S_DON, "Hình thức tài liệu", "liz-input"),
    (S_DON, "Số trang (hoặc dung lượng - byte)", "liz-input"),
    (S_DON, "Phụ bản (nếu có)", "liz-input"),
    (S_DON, "Khuôn khổ (định dạng) (cm)", "liz-input"),
    (S_DON, "Số lượng in (bản)", "liz-input"),
    (S_DON, "Ngôn ngữ xuất bản", "liz-input"),
    (S_DON, "Tên cơ sở in", "liz-input"),
    (S_DON, "Địa chỉ cơ sở in", "liz-input"),
    (S_DON, "Mục đích xuất bản", "liz-input"),
    (S_DON, "Nội dung tóm tắt của tài liệu", "liz-input"),
    (S_DON, "Kèm theo đơn này gồm", "liz-input"),
]

COMP_BY_UI = {(s, l): c for s, l, c in UI_FIELDS}
