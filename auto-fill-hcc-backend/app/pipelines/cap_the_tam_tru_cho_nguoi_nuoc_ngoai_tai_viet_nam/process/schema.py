"""Compact schema cho thủ tục 1.003460 — Cấp thẻ tạm trú cho người nước ngoài tại Việt Nam (Công an cấp tỉnh).

LLM chỉ trả dữ kiện nguồn đọc từ giấy tờ (tiền tố theo giấy); ô UI ``CongDan__fs*`` / ``CongDan_*`` / ``HoSoOnline_*``
do mapper dựng theo file mapping "Mapping_Cap_the_tam_tru_NNN_1.003460" (sheet "Cấp thẻ tạm trú NNN - BCA").

Giấy tờ: Tờ khai đề nghị cấp thẻ tạm trú (Mẫu NA8) · Văn bản đề nghị cấp thẻ tạm trú (Mẫu NA6 của cơ quan, tổ chức /
NA7 của cá nhân) · hộ chiếu (trang nhân thân + MRZ, trang thị thực, dấu kiểm chứng nhập cảnh) · giấy tờ chứng minh thuộc
diện xem xét cấp thẻ (giấy phép lao động …) · có khi kèm thẻ căn cước của người đăng nhập / bảo lãnh. Thứ tự nguồn
(mapping): người nước ngoài Hộ chiếu → Tờ khai NA8 → Văn bản NA6 → GPLĐ → Danh mục; bên bảo lãnh CCCD / NA6.

Cố ý KHÔNG phát:
- Hai ô tải ảnh .jpg đầu form KHÔNG đi qua LLM: runner tự PHÁT (comp ``bca-photo``, JPEG dưới 2 MB) ảnh chân dung
  (``filename46``, tệp ảnh gần như không chữ — dùng chung hộ chiếu 1.001456) và ảnh trang nhân thân hộ chiếu
  (``filenamehc``, trang có MRZ — ``attach/dinh_kem_khong_tach/planner.passport_page_field``).
- Ô readonly theo tài khoản đăng nhập: Thân nhân bảo lãnh (họ tên), Ngày sinh, ``CongDan_soCmnd``; khối Cơ quan/tổ chức
  bảo lãnh + tra cứu doanh nghiệp đang ẨN (form khoá "Thân nhân") — mapping ghi CẦN XÁC NHẬN.
- Cơ quan tiếp nhận (theo cơ quan đã chọn ở bước chọn trường hợp), nơi nhận kết quả (công dân tự chọn), "Về việc" (ẩn),
  ô hidden hệ thống.
"""

FIELDS: list[dict] = [
    # Tờ khai đề nghị cấp thẻ tạm trú (Mẫu NA8).
    {"name": "ToKhai_HoTen", "desc": "Mục 1 — Họ tên (chữ in hoa) của người nước ngoài."},
    {"name": "ToKhai_GioiTinh", "desc": "Mục 2 — ô được đánh dấu: \"Nam\" hoặc \"Nữ\"."},
    {"name": "ToKhai_NgaySinh", "desc": "Mục 3 — Sinh ngày … tháng … năm …, dd/mm/yyyy."},
    {"name": "ToKhai_QuocTichGoc", "desc": "Mục 4 — Quốc tịch gốc, chép nguyên văn (vd \"Hàn Quốc\")."},
    {"name": "ToKhai_QuocTichHienNay", "desc": "Mục 5 — Quốc tịch hiện nay, chép nguyên văn."},
    {"name": "ToKhai_NgheNghiep", "desc": "Mục 6 — Nghề nghiệp/chức vụ, chép nguyên văn."},
    {"name": "ToKhai_SoHoChieu", "desc": "Mục 7 — Hộ chiếu số (chữ + số liền nhau)."},
    {"name": "ToKhai_LoaiHoChieu",
     "desc": "Mục 7 — ô \"Loại\" được đánh dấu (☒, X, ✓): \"Phổ thông\", \"Công vụ\" hoặc \"Ngoại giao\". Không rõ → bỏ."},
    {"name": "ToKhai_HoChieu_CoQuanCap", "desc": "Mục 7 — \"Cơ quan cấp\" hộ chiếu, chép nguyên văn."},
    {"name": "ToKhai_HoChieu_DenNgay", "desc": "Mục 7 — hộ chiếu \"có giá trị đến ngày\", dd/mm/yyyy."},
    {"name": "ToKhai_DiaChiCuTruNuocNgoai",
     "desc": "Mục 8 — \"Địa chỉ cư trú\" ở nước ngoài trước khi nhập cảnh Việt Nam, chép NGUYÊN VĂN một dòng."},
    {"name": "ToKhai_NoiLamViecNuocNgoai",
     "desc": "Mục 8 — \"Nơi làm việc\" ở nước ngoài trước khi nhập cảnh Việt Nam, chép NGUYÊN VĂN một dòng."},
    {"name": "ToKhai_NgayNhapCanh", "desc": "Mục 9 — \"Nhập cảnh Việt Nam gần nhất ngày\", dd/mm/yyyy."},
    {"name": "ToKhai_CuaKhau", "desc": "Mục 9 — \"qua cửa khẩu\", chép nguyên văn (vd \"Cửa khẩu Sân bay quốc tế Nội Bài\")."},
    {"name": "ToKhai_MucDichNhapCanh", "desc": "Mục 9 — \"Mục đích nhập cảnh\", chép nguyên văn cả dòng."},
    {"name": "ToKhai_TamTruDen", "desc": "Mục 10 — \"Được phép tạm trú đến ngày\", dd/mm/yyyy."},
    {"name": "ToKhai_DiaChiTamTru",
     "desc": "Mục 10 — \"Địa chỉ tạm trú tại Việt Nam\", object {quocGia,tinh,xa,chiTietDuoiXa}; chiTietDuoiXa là phần "
             "đứng trước xã/phường (số nhà, khu nhà ở, bản, thôn)."},
    {"name": "ToKhai_DienThoai", "desc": "Mục 11 — phần số điện thoại, chép nguyên văn."},
    {"name": "ToKhai_Email", "desc": "Mục 11 — phần email (có @). Không có → bỏ field."},
    {"name": "ToKhai_The_DenNgay",
     "desc": "Mục 12 — \"Cấp thẻ tạm trú có giá trị đến ngày\", dd/mm/yyyy."},
    {"name": "ToKhai_LyDo", "desc": "Mục 12 — \"Lý do\", chép NGUYÊN VĂN cả dòng."},

    # Văn bản đề nghị cấp thẻ tạm trú (NA6 của cơ quan, tổ chức / NA7 của cá nhân bảo lãnh).
    {"name": "VanBan_Loai", "desc": "Mẫu của văn bản: \"NA6\" (cơ quan, tổ chức) hoặc \"NA7\" (cá nhân bảo lãnh)."},
    {"name": "VanBan_BenBaoLanh",
     "desc": "NA6: tên cơ quan, tổ chức ở góc trái (vd \"CÔNG TY TNHH …\"); NA7: họ tên người bảo lãnh."},
    {"name": "VanBan_So", "desc": "Số văn bản (vd \"27/CV-HB\"), chỉ phần sau \"Số:\"."},
    {"name": "VanBan_Ngay", "desc": "Ngày ký văn bản (\"…, ngày … tháng … năm …\"), dd/mm/yyyy."},
    {"name": "VanBan_DiaChi",
     "desc": "NA6: \"Trụ sở tại\"; NA7: địa chỉ thường trú/tạm trú của người bảo lãnh — object "
             "{quocGia,tinh,xa,chiTietDuoiXa}."},
    {"name": "VanBan_DienThoai", "desc": "Số điện thoại của cơ quan / người bảo lãnh, chép nguyên văn."},
    {"name": "VanBan_Email", "desc": "Email của cơ quan / người bảo lãnh (có @). Không có → bỏ field."},
    {"name": "VanBan_QuanHe", "desc": "NA7: quan hệ của người bảo lãnh với người nước ngoài (vd \"Vợ\"). NA6 → bỏ."},
    {"name": "VanBan_ViTriCongViec",
     "desc": "Bảng danh sách người nước ngoài — cột \"Vị trí công việc\" ở dòng của người đề nghị."},

    # Hộ chiếu của người nước ngoài.
    {"name": "HoChieu_So", "desc": "Passport No. / Số hộ chiếu (chữ + số)."},
    {"name": "HoChieu_MRZ",
     "desc": "HAI dòng MRZ ở đáy trang nhân thân (dòng 1 bắt đầu \"P<\"), chép nguyên văn, giữ dấu \"<\", hai dòng cách "
             "nhau một dấu xuống dòng."},
    {"name": "HoChieu_Ho", "desc": "Surname / Họ, chép nguyên văn chữ in hoa."},
    {"name": "HoChieu_Ten", "desc": "Given names / Tên, chép nguyên văn chữ in hoa."},
    {"name": "HoChieu_QuocTich", "desc": "Nationality / Quốc tịch, chép nguyên văn (vd \"REPUBLIC OF KOREA\")."},
    {"name": "HoChieu_MaQuocGia", "desc": "Country code / Mã quốc gia 3 chữ cái (vd \"KOR\")."},
    {"name": "HoChieu_Loai", "desc": "Type / Loại: một chữ cái (\"P\" phổ thông, \"D\" ngoại giao, \"S\"/\"O\" công vụ)."},
    {"name": "HoChieu_NgaySinh", "desc": "Date of birth, dd/mm/yyyy."},
    {"name": "HoChieu_GioiTinh", "desc": "Sex: \"M\" hoặc \"F\"."},
    {"name": "HoChieu_NgayHetHan", "desc": "Date of expiry, dd/mm/yyyy."},
    {"name": "HoChieu_CoQuanCap", "desc": "Authority / Issuing authority, chép nguyên văn."},
    {"name": "HoChieu_ThiThuc_KyHieu",
     "desc": "Trang THỊ THỰC VIỆT NAM — \"Ký hiệu / Type\" (vd \"LĐ2\", \"DN1\", \"TT\"). Không có trang thị thực → bỏ."},
    {"name": "HoChieu_NhapCanh_Ngay",
     "desc": "Dấu kiểm chứng NHẬP CẢNH Việt Nam (ARRIVAL) — Ngày / Date, dd/mm/yyyy. Không có dấu nhập cảnh → bỏ."},
    {"name": "HoChieu_NhapCanh_CuaKhau", "desc": "Dấu kiểm chứng nhập cảnh — Cửa khẩu / Port, chép nguyên văn."},
    {"name": "HoChieu_TamTruDen",
     "desc": "Dấu kiểm chứng nhập cảnh — \"Chứng nhận tạm trú đến / Permitted to stay until\", dd/mm/yyyy."},

    # Giấy tờ chứng minh thuộc diện xem xét cấp thẻ (giấy phép lao động / work permit …).
    {"name": "GPLD_So", "desc": "Giấy phép lao động — \"Số / No.\" (vd \"LC-26-0127\")."},
    {"name": "GPLD_CoQuanCap",
     "desc": "Giấy phép lao động — cơ quan cấp ở góc trái tiêu đề, dòng DƯỚI CÙNG (vd \"SỞ NỘI VỤ\" dưới \"ỦY BAN NHÂN "
             "DÂN TỈNH LAI CHÂU\" → \"Sở Nội vụ tỉnh Lai Châu\")."},
    {"name": "GPLD_NgayCap", "desc": "Giấy phép lao động — ngày ký (\"…, ngày … tháng … năm …\" cuối giấy), dd/mm/yyyy."},
    {"name": "GPLD_HoTen", "desc": "Giấy phép lao động — mục 1 Họ và tên / Full name."},
    {"name": "GPLD_SoHoChieu", "desc": "Giấy phép lao động — Số hộ chiếu / Passport No."},
    {"name": "GPLD_ChucDanh", "desc": "Giấy phép lao động — Chức danh công việc / Job title."},
    {"name": "GPLD_TuNgay", "desc": "Giấy phép lao động — Thời hạn làm việc từ ngày / from, dd/mm/yyyy."},
    {"name": "GPLD_DenNgay", "desc": "Giấy phép lao động — Thời hạn làm việc đến ngày / to, dd/mm/yyyy."},

    # Trang bìa "HỒ SƠ THỦ TỤC HÀNH CHÍNH" (bảng thông tin chung) — chỉ hai mục giấy khác không có.
    {"name": "Bia_KyHieuThe", "desc": "Trang bìa — dòng \"Ký hiệu thẻ đề nghị\": chỉ ký hiệu (vd \"LĐ2\")."},
    {"name": "Bia_MaSoDoanhNghiep",
     "desc": "Trang bìa — dòng \"Cơ quan bảo lãnh\": phần \"mã số doanh nghiệp\" (chỉ chữ số)."},

    # Thẻ căn cước (nếu có) của người đăng nhập / người bảo lãnh là công dân Việt Nam.
    {"name": "Cccd_HoTen", "desc": "Họ, chữ đệm và tên khai sinh trên thẻ căn cước/CCCD."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh cá nhân / số CCCD, chỉ chữ số."},
    {"name": "Cccd_NgayCap",
     "desc": "Ngày cấp thẻ (\"Ngày, tháng, năm cấp / Date of issue\"), dd/mm/yyyy. KHÔNG lấy ngày hết hạn."},
    {"name": "Cccd_NoiCap", "desc": 'Cơ quan cấp in trên thẻ: "BỘ CÔNG AN" → "Bộ Công an".'},
    {"name": "Cccd_NoiCuTru",
     "desc": "Nơi cư trú / Nơi thường trú / Place of residence trên thẻ, object {quocGia,tinh,xa,chiTietDuoiXa}."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "ToKhai_NgaySinh", "ToKhai_HoChieu_DenNgay", "ToKhai_NgayNhapCanh", "ToKhai_TamTruDen", "ToKhai_The_DenNgay",
    "VanBan_Ngay", "HoChieu_NgaySinh", "HoChieu_NgayHetHan", "HoChieu_NhapCanh_Ngay", "HoChieu_TamTruDen",
    "GPLD_NgayCap", "GPLD_TuNgay", "GPLD_DenNgay", "Cccd_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ToKhai_DiaChiTamTru", "VanBan_DiaChi", "Cccd_NoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô form theo file mapping (name trong DOM), đúng thứ tự trên form. bootstrap-select → dom-select; ô ngày date-picker
# nhận gõ dd/mm/yyyy (định dạng mặc định Ngày/Tháng/Năm) như thị thực → dom-input. Tỉnh trước Phường/xã.
UI_COMP_BY_NAME = {
    # Phần III — Người đề nghị (người nước ngoài).
    "CongDan_tenCongDan": "dom-input",                    # Họ và tên (*)
    "CongDan__fs_BCAGioiTinhCd": "dom-select",            # Giới tính (*)
    "CongDan_ngaySinhCongDan": "dom-input",               # Ngày sinh (*)
    "CongDan__fs_BCAQuocTichGoc": "dom-select",           # Quốc tịch gốc (*) — tên nước tiếng Anh
    "CongDan__fs_BCAQuocTichHienNay": "dom-select",       # Quốc tịch hiện nay (*)
    "CongDan__fs_BCANgheNghiep": "dom-input",             # Nghề nghiệp/ chức vụ (*)
    "CongDan__fs_BCASoHoChieu": "dom-input",              # Số hộ chiếu (*)
    "CongDan__fs_BCALoaiHoChieu": "dom-select",           # Loại hộ chiếu (*)
    "CongDan__fs_BCACoQuanCap": "dom-input",              # Cơ quan cấp (hộ chiếu)
    "CongDan__fs_BCAHoChieuDenNgay": "dom-input",         # Có giá trị đến ngày (hộ chiếu) (*)
    "CongDan__fsDCCUTRU_NUOCNGOAI": "dom-input",          # Địa chỉ cư trú ở nước ngoài trước khi nhập cảnh (*)
    "CongDan__fsDCLAMVIEC_NUOCNGOAI": "dom-input",        # Địa chỉ nơi làm việc ở nước ngoài trước khi nhập cảnh (*)
    "CongDan__fs_BCANgayNhapCanh": "dom-input",           # Nhập cảnh Việt Nam ngày
    "CongDan__fs_BCAQuaCuaKhau": "dom-select",            # Qua cửa khẩu ("SBQT Nội Bài")
    "CongDan__fs_BCAMucDichNhapCanh": "dom-select",       # Mục đích nhập cảnh (*) — 36 mục
    "CongDan__fs_BCATamTruDen": "dom-input",              # Được phép tạm trú đến ngày (*)
    "CongDan__fs_BCATinhTamTru": "dom-select",            # Địa chỉ tạm trú tại VN — Tỉnh/TP (*)
    "CongDan__fs_BCAXaTamTru": "dom-select",              # — Phường/xã (*) — nạp theo tỉnh
    "CongDan__fs_BCADiaChiTamTru": "dom-input",           # — chi tiết (*)
    "CongDan_diDong": "dom-input",                        # Điện thoại liên hệ (*)
    "CongDan_email": "dom-input",                         # Email liên hệ (*)
    # Phần IV — Bên bảo lãnh (họ tên, ngày sinh, số giấy tờ readonly theo tài khoản).
    "CongDan__fs_BCACoQuanCapCMNDBaoLanh": "dom-input",   # Cơ quan cấp (giấy tờ bên bảo lãnh)
    "CongDan__fs_BCANgayCapCMNDBaoLanh": "dom-input",     # Cấp ngày (giấy tờ bên bảo lãnh) (*)
    "CongDan__fs_BCAQuanHeNguoiDeNghi": "dom-input",      # Quan hệ với người đề nghị (*)
    "CongDan__fs_BCATinhThuongTru": "dom-select",         # Địa chỉ thường trú/ tạm trú tại VN của bên bảo lãnh — Tỉnh (*)
    "CongDan__fs_BCAXaThuongTru": "dom-select",           # — Phường/xã (*)
    "CongDan__fs_BCADiaChiThuongTruVNBaoLanh": "dom-input",  # — chi tiết (*)
    "CongDan__fs_BCADiDongBaoLanh": "dom-input",          # Điện thoại (bên bảo lãnh) (*)
    "CongDan__fs_BCAEmailBaoLanh": "dom-input",           # Email liên hệ (bên bảo lãnh) (*)
    # Phần V — Nội dung đề nghị.
    "CongDan__fs_BCAGiaHanTamTruDenNgay": "dom-input",    # Cấp thẻ tạm trú đến ngày (*)
    "CongDan__fs_BCALyDoDeNghiCapThiThuc": "dom-input",   # Lý do (*) — tên kỹ thuật dùng lại của thị thực
    "CongDan__fs_BCADieuCanTrinhBayThem": "dom-input",    # Những điều cần trình bày thêm (*) (textarea)
    # Phần VIII — Thông tin khác (cùng trang, dưới bảng Thành phần hồ sơ).
    "HoSoOnline_ghiChu": "dom-input",                     # Ghi chú (textarea) — ghi rõ trang của tệp hồ sơ gộp
}

WAIT_MS = {
    "CongDan__fs_BCAXaTamTru": 8000,
    "CongDan__fs_BCAXaThuongTru": 8000,
}

# Ký hiệu thẻ / thị thực (Luật Nhập cảnh) → option "Mục đích nhập cảnh" (chữ thường như "thăm thân" của mapping thị thực).
# Mapping 1.003460: LĐ2 → "lao động" (ghi CẦN XÁC NHẬN vì danh mục còn "làm việc"). Các ký hiệu khác SUY theo luật.
MUC_DICH_BY_KY_HIEU: tuple[tuple[str, str], ...] = (
    ("LD", "lao động"),
    ("DN", "làm việc"),
    ("LV", "làm việc"),
    ("DT", "đầu tư"),
    ("DH", "du học"),
    ("TT", "thăm thân"),
    ("DL", "du lịch"),
    ("HN", "hội nghị"),
    ("PV", "phóng viên"),
)
