"""Compact schema cho thủ tục 1.001194 — Cấp thị thực cho người nước ngoài tại Việt Nam (thực hiện tại cấp tỉnh).

LLM chỉ trả dữ kiện nguồn đọc từ giấy tờ (tiền tố theo giấy); ô UI ``CongDan__fs*`` / ``CongDan_*`` do mapper dựng
theo file mapping "Mapping_Cap_thi_thuc_NNN_tai_VN_cap_tinh" (sheet "Cấp thị thực NNN – BCA").

Giấy tờ: Tờ khai đề nghị cấp thị thực, gia hạn tạm trú (Mẫu NA5, mục I–IV) · hộ chiếu của người nước ngoài (trang nhân
thân + MRZ + trang dấu kiểm chứng nhập cảnh) · giấy tờ chứng minh quan hệ / lý do (giấy chứng nhận kết hôn …) · thẻ căn
cước của người bảo lãnh. Thứ tự nguồn (mapping): người đề nghị Hộ chiếu → Giấy KH → Tờ khai; người bảo lãnh CCCD → Giấy
KH → Tờ khai.

Cố ý KHÔNG phát:
- Ảnh chân dung 4x6 (``filename46``) và ảnh trang nhân thân hộ chiếu (``filenamehc``) ở đầu form — ô tải ảnh .jpg
  riêng, không thuộc bảng Thành phần hồ sơ; LLM không phát. Từ 19/11/2026 runner tự gắn (comp ``bca-photo``, khuôn thẻ
  tạm trú 1.003460: ``runner.photo_fields``); thiếu ảnh thì cảnh báo tải tay.
- Ô readonly cổng lấy từ tài khoản đăng nhập của người bảo lãnh: Thân nhân bảo lãnh (họ tên), Ngày sinh, Giấy CCCD
  (``CongDan_soCmnd``). Ô "Cơ quan/Tổ chức hoặc Thân nhân" khoá sẵn "Thân nhân" → khối cơ quan bảo lãnh (ẩn) bỏ qua.
- Cơ quan tiếp nhận (``CongDan__fs_BCANoiNopHS``) — danh sách chỉ có cơ quan đã chọn ở bước "Chọn trường hợp hồ sơ"
  (như ô 17 hộ chiếu); nơi nhận thị thực (trực tiếp / bưu chính) — giấy tờ không ghi, người nộp tự chọn.
- Ô hidden hệ thống tự sinh (Ngày/giờ hẹn).
"""

FIELDS: list[dict] = [
    # Tờ khai đề nghị cấp thị thực, gia hạn tạm trú (Mẫu NA5).
    {"name": "ToKhai_HoTen", "desc": "Mục I.1 — Họ tên (chữ in hoa) của người đề nghị (người nước ngoài)."},
    {"name": "ToKhai_GioiTinh", "desc": "Mục I.2 — ô được đánh dấu: \"Nam\" hoặc \"Nữ\"."},
    {"name": "ToKhai_NgaySinh", "desc": "Mục I.3 — Sinh ngày … tháng … năm …, dd/mm/yyyy."},
    {"name": "ToKhai_QuocTichGoc", "desc": "Mục I.4 — Quốc tịch gốc, chép nguyên văn (vd \"Ca-na-đa\")."},
    {"name": "ToKhai_QuocTichHienNay", "desc": "Mục I.5 — Quốc tịch hiện nay, chép nguyên văn."},
    {"name": "ToKhai_NgheNghiep", "desc": "Mục I.6 — Nghề nghiệp/chức vụ, chép nguyên văn."},
    {"name": "ToKhai_SoHoChieu", "desc": "Mục I.7 — Hộ chiếu/Giấy tờ có giá trị đi lại quốc tế số (chữ + số liền nhau)."},
    {"name": "ToKhai_LoaiHoChieu", "desc": "Mục I.7 — \"loại\" hộ chiếu, chép nguyên văn (vd \"Hộ chiếu phổ thông\")."},
    {"name": "ToKhai_HoChieu_CoQuanCap", "desc": "Mục I.7 — \"Cơ quan cấp\" hộ chiếu, chép nguyên văn."},
    {"name": "ToKhai_HoChieu_DenNgay", "desc": "Mục I.7 — hộ chiếu \"có giá trị đến ngày\", dd/mm/yyyy."},
    {"name": "ToKhai_NgayNhapCanh", "desc": "Mục I.8 — \"Nhập cảnh Việt Nam gần nhất ngày\", dd/mm/yyyy."},
    {"name": "ToKhai_CuaKhau", "desc": "Mục I.8 — \"qua cửa khẩu\", chép nguyên văn (vd \"Cửa khẩu Sân bay quốc tế Nội Bài\")."},
    {"name": "ToKhai_MucDichNhapCanh", "desc": "Mục I.8 — \"Mục đích nhập cảnh\", chép nguyên văn (vd \"Thăm thân (thăm vợ)\")."},
    {"name": "ToKhai_TamTruDen", "desc": "Mục I.9 — \"Được phép tạm trú đến ngày\", dd/mm/yyyy."},
    {"name": "ToKhai_DiaChiTamTru",
     "desc": "Mục I.9 — \"Địa chỉ tạm trú tại Việt Nam\", object {quocGia,tinh,xa,chiTietDuoiXa}; chiTietDuoiXa là phần "
             "đứng trước xã/phường (số nhà, đường, tổ dân phố, thôn)."},
    {"name": "ToKhai_DienThoai", "desc": "Mục I.10 — phần số điện thoại của người đề nghị, chép nguyên văn."},
    {"name": "ToKhai_Email", "desc": "Mục I.10 — phần email của người đề nghị (có @). Không có → bỏ field."},
    {"name": "ToKhai_CoQuanBaoLanh",
     "desc": "Mục II.1 — \"Tên cơ quan, tổ chức\" mời, bảo lãnh. Dòng chấm chấm / để trống → bỏ field."},
    {"name": "ToKhai_BaoLanh_HoTen", "desc": "Mục II.2 — Thân nhân bảo lãnh (Họ tên)."},
    {"name": "ToKhai_BaoLanh_SoGiayTo",
     "desc": "Mục II.2 — số \"Căn cước công dân/Căn cước/Hộ chiếu số\" của người bảo lãnh, chỉ phần số."},
    {"name": "ToKhai_BaoLanh_NgayCap", "desc": "Mục II.2 — \"Cấp ngày\" của giấy tờ trên, dd/mm/yyyy."},
    {"name": "ToKhai_BaoLanh_CoQuanCap", "desc": "Mục II.2 — \"Cơ quan cấp\" của giấy tờ trên, chép nguyên văn."},
    {"name": "ToKhai_BaoLanh_TheTamTruSo",
     "desc": "Mục II.2 — \"Thẻ thường trú/Thẻ tạm trú số\" (chỉ khi người bảo lãnh là người nước ngoài). Trống → bỏ."},
    {"name": "ToKhai_BaoLanh_TheTamTru_NgayCap", "desc": "Mục II.2 — \"Ngày cấp\" của thẻ thường trú/tạm trú, dd/mm/yyyy."},
    {"name": "ToKhai_BaoLanh_TheTamTru_CoQuanCap", "desc": "Mục II.2 — \"Cơ quan cấp\" của thẻ thường trú/tạm trú."},
    {"name": "ToKhai_BaoLanh_QuanHe", "desc": "Mục II.2 — \"Quan hệ với người đề nghị\" (vd \"Vợ\"), bỏ số chú thích."},
    {"name": "ToKhai_BaoLanh_DiaChi",
     "desc": "Mục II.2 — \"Địa chỉ thường trú/tạm trú tại Việt Nam\" của người bảo lãnh, object "
             "{quocGia,tinh,xa,chiTietDuoiXa}."},
    {"name": "ToKhai_BaoLanh_DienThoai", "desc": "Mục II.2 — phần số điện thoại của người bảo lãnh."},
    {"name": "ToKhai_BaoLanh_Email", "desc": "Mục II.2 — phần email của người bảo lãnh (có @)."},
    {"name": "ToKhai_LoaiThiThuc",
     "desc": "Mục III.1 — ô được đánh dấu (☒, X, ✓) trong \"một lần\" / \"nhiều lần\": trả \"mot_lan\" hoặc \"nhieu_lan\". "
             "Không thấy rõ → bỏ field."},
    {"name": "ToKhai_ThiThuc_DenNgay", "desc": "Mục III.1 — thị thực \"có giá trị đến ngày\", dd/mm/yyyy."},
    {"name": "ToKhai_GiaHan_DenNgay",
     "desc": "Mục III.2 — \"Gia hạn tạm trú đến ngày\", dd/mm/yyyy. Dòng chấm chấm → bỏ field."},
    {"name": "ToKhai_LyDo", "desc": "Mục III.3 — \"Lý do\", chép NGUYÊN VĂN cả dòng."},
    {"name": "ToKhai_TrinhBayThem",
     "desc": "Mục IV — \"Những điều cần trình bày thêm\", chép nguyên văn. Chỉ có dòng chấm chấm → bỏ field."},

    # Hộ chiếu của người nước ngoài.
    {"name": "HoChieu_So", "desc": "Passport No. / Số hộ chiếu (chữ + số, vd \"HT482916\")."},
    {"name": "HoChieu_MRZ",
     "desc": "HAI dòng MRZ ở đáy trang nhân thân (dòng 1 bắt đầu \"P<\", dòng 2 bắt đầu bằng số hộ chiếu), chép nguyên "
             "văn, giữ dấu \"<\", hai dòng cách nhau một dấu xuống dòng."},
    {"name": "HoChieu_Ho", "desc": "Surname / Họ, chép nguyên văn chữ in hoa."},
    {"name": "HoChieu_Ten", "desc": "Given names / Tên, chép nguyên văn chữ in hoa."},
    {"name": "HoChieu_QuocTich", "desc": "Nationality / Quốc tịch, chép nguyên văn (vd \"CANADA\")."},
    {"name": "HoChieu_MaQuocGia", "desc": "Country code / Mã quốc gia 3 chữ cái (vd \"CAN\")."},
    {"name": "HoChieu_Loai", "desc": "Type / Loại: một chữ cái (\"P\" phổ thông, \"D\" ngoại giao, \"S\"/\"O\" công vụ)."},
    {"name": "HoChieu_NgaySinh", "desc": "Date of birth, dd/mm/yyyy."},
    {"name": "HoChieu_GioiTinh", "desc": "Sex: \"M\" hoặc \"F\"."},
    {"name": "HoChieu_NgayHetHan", "desc": "Date of expiry, dd/mm/yyyy."},
    {"name": "HoChieu_CoQuanCap", "desc": "Authority / Issuing authority, chép nguyên văn."},
    {"name": "HoChieu_NhapCanh_Ngay",
     "desc": "Dấu kiểm chứng NHẬP CẢNH Việt Nam (ARRIVAL) — Ngày / Date, dd/mm/yyyy. Không có dấu nhập cảnh → bỏ."},
    {"name": "HoChieu_NhapCanh_CuaKhau", "desc": "Dấu kiểm chứng nhập cảnh — Cửa khẩu / Port, chép nguyên văn."},
    {"name": "HoChieu_TamTruDen",
     "desc": "Dấu kiểm chứng nhập cảnh — \"Chứng nhận tạm trú đến / Permitted to stay until\", dd/mm/yyyy."},

    # Giấy chứng nhận kết hôn (giấy tờ chứng minh quan hệ).
    {"name": "KetHon_Chong_HoTen", "desc": "Giấy chứng nhận kết hôn — cột Người chồng: Họ, chữ đệm, tên."},
    {"name": "KetHon_Chong_GiayTo", "desc": "Giấy chứng nhận kết hôn — cột Người chồng: Giấy tờ tùy thân, chỉ phần số."},
    {"name": "KetHon_Chong_NoiCuTru",
     "desc": "Giấy chứng nhận kết hôn — cột Người chồng: Nơi cư trú, object {quocGia,tinh,xa,chiTietDuoiXa}."},
    {"name": "KetHon_Vo_HoTen", "desc": "Giấy chứng nhận kết hôn — cột Người vợ: Họ, chữ đệm, tên."},
    {"name": "KetHon_Vo_GiayTo", "desc": "Giấy chứng nhận kết hôn — cột Người vợ: Giấy tờ tùy thân, chỉ phần số."},
    {"name": "KetHon_Vo_NoiCuTru",
     "desc": "Giấy chứng nhận kết hôn — cột Người vợ: Nơi cư trú, object {quocGia,tinh,xa,chiTietDuoiXa}."},

    # Thẻ căn cước / CCCD của người bảo lãnh (công dân Việt Nam).
    {"name": "Cccd_HoTen", "desc": "Họ, chữ đệm và tên khai sinh trên thẻ căn cước/CCCD."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh cá nhân / số CCCD trên thẻ, chỉ chữ số."},
    {"name": "Cccd_NgayCap",
     "desc": "Ngày cấp thẻ (\"Ngày, tháng, năm cấp / Date of issue\"), dd/mm/yyyy. KHÔNG lấy ngày hết hạn."},
    {"name": "Cccd_NoiCap",
     "desc": 'Cơ quan cấp in trên thẻ: "BỘ CÔNG AN" → "Bộ Công an"; "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ '
             'TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},
    {"name": "Cccd_NoiCuTru",
     "desc": "Nơi cư trú / Nơi thường trú / Place of residence trên thẻ, object {quocGia,tinh,xa,chiTietDuoiXa}."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "ToKhai_NgaySinh", "ToKhai_HoChieu_DenNgay", "ToKhai_NgayNhapCanh", "ToKhai_TamTruDen", "ToKhai_BaoLanh_NgayCap",
    "ToKhai_BaoLanh_TheTamTru_NgayCap", "ToKhai_ThiThuc_DenNgay", "ToKhai_GiaHan_DenNgay", "HoChieu_NgaySinh",
    "HoChieu_NgayHetHan", "HoChieu_NhapCanh_Ngay", "HoChieu_TamTruDen", "Cccd_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ToKhai_DiaChiTamTru", "ToKhai_BaoLanh_DiaChi", "KetHon_Chong_NoiCuTru", "KetHon_Vo_NoiCuTru",
              "Cccd_NoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô form theo file mapping (name trong DOM), đúng thứ tự trên form. <select> (bootstrap-select) → dom-select; ô ngày
# date-picker của form-builder nhận gõ chữ dd/mm/yyyy (định dạng mặc định Ngày/Tháng/Năm) như hộ chiếu → dom-input.
# Tỉnh trước Phường/xã vì danh mục xã nạp qua API theo tỉnh.
UI_COMP_BY_NAME = {
    # Phần II — Người đề nghị.
    "CongDan_tenCongDan": "dom-input",                    # Họ và tên (*)
    "CongDan_ngaySinhCongDan": "dom-input",               # Ngày tháng năm sinh (*)
    "CongDan__fs_BCAGioiTinhCd": "dom-select",            # Giới tính (*)
    "CongDan__fs_BCAQuocTichHienNay": "dom-select",       # Quốc tịch hiện nay (*) — tên nước tiếng Anh
    "CongDan__fs_BCAQuocTichGoc": "dom-select",           # Quốc tịch gốc (*)
    "CongDan__fs_BCANgheNghiep": "dom-input",             # Nghề nghiệp/ chức vụ (*)
    "CongDan__fs_BCASoHoChieu": "dom-input",              # Số hộ chiếu (*)
    "CongDan__fs_BCALoaiHoChieu": "dom-select",           # Loại hộ chiếu (*) — cổng để sẵn "Khác"
    "CongDan__fs_BCACoQuanCap": "dom-input",              # Cơ quan cấp (hộ chiếu)
    "CongDan__fs_BCAHoChieuDenNgay": "dom-input",         # Có giá trị đến ngày (hộ chiếu) (*)
    "CongDan__fs_BCANgayNhapCanh": "dom-input",           # Nhập cảnh Việt Nam ngày
    "CongDan__fs_BCAQuaCuaKhau": "dom-select",            # Qua cửa khẩu — 243 mục ("SBQT Nội Bài")
    "CongDan__fs_BCATamTruDen": "dom-input",              # Được phép tạm trú đến ngày (*)
    "CongDan__fs_BCAMucDichNhapCanh": "dom-select",       # Mục đích nhập cảnh (*) — 37 mục ("thăm thân")
    "CongDan__fs_BCATinhTamTru": "dom-select",            # Địa chỉ tạm trú — Tỉnh/TP (*)
    "CongDan__fs_BCAXaTamTru": "dom-select",              # Địa chỉ tạm trú — Phường/xã (*) — nạp theo tỉnh
    "CongDan__fs_BCADiaChiTamTru": "dom-input",           # Địa chỉ tạm trú chi tiết (*)
    "CongDan_diDong": "dom-input",                        # Điện thoại (*)
    "CongDan_email": "dom-input",                         # Email liên hệ (*)
    # Phần III — Thân nhân bảo lãnh (họ tên, ngày sinh, số CCCD readonly theo tài khoản).
    "CongDan__fs_BCANgayCapCMNDBaoLanh": "dom-input",     # Cấp ngày (CCCD) (*)
    "CongDan__fs_BCACoQuanCapCMNDBaoLanh": "dom-input",   # Cơ quan cấp (CCCD)
    "CongDan__fs_BCATheTamTruSo": "dom-input",            # Thẻ thường trú/ thẻ tạm trú số
    "CongDan__fs_BCANgayCapTheTamTruSo": "dom-input",     # Cấp ngày (thẻ)
    "CongDan__fs_BCACoQuanCapTheTamTruSo": "dom-input",   # Cơ quan cấp (thẻ)
    "CongDan__fs_BCAQuanHeNguoiDeNghi": "dom-input",      # Quan hệ với người đề nghị (*)
    "CongDan__fs_BCATinhThuongTru": "dom-select",         # Thường trú tại VN — Tỉnh/TP (*)
    "CongDan__fs_BCAXaThuongTru": "dom-select",           # Thường trú tại VN — Phường/xã (*)
    "CongDan__fs_BCADiaChiThuongTruVNBaoLanh": "dom-input",  # Thường trú tại VN chi tiết (*)
    "CongDan__fs_BCATinhTamTruBaoLanh": "dom-select",     # Tạm trú tại VN (người bảo lãnh) — Tỉnh/TP (*)
    "CongDan__fs_BCAXaTamTruBaoLanh": "dom-select",       # Tạm trú tại VN (người bảo lãnh) — Phường/xã (*)
    "CongDan__fs_BCADiaChiTamTruBaoLanh": "dom-input",    # Tạm trú tại VN (người bảo lãnh) chi tiết (*)
    "CongDan__fs_BCADiDongBaoLanh": "dom-input",          # Điện thoại (người bảo lãnh) (*)
    "CongDan__fs_BCAEmailBaoLanh": "dom-input",           # Email liên hệ (người bảo lãnh) (*)
    # Phần IV — Nội dung đề nghị.
    "CongDan__fs_BCACapThiThucLan": "dom-select",         # Cấp thị thực: Nhiều lần / Một lần (*)
    "CongDan__fs_BCAThiThucDenNgay": "dom-input",         # Có giá trị đến ngày (thị thực) (*)
    "CongDan__fs_BCALyDoDeNghiCapThiThuc": "dom-input",   # Lý do (*)
    "CongDan__fs_BCADieuCanTrinhBayThem": "dom-input",    # Những điều cần trình bày thêm (textarea)
}

# Ô Phường/xã nạp chậm qua API theo tỉnh → extension chờ thêm tới waitMs (ms) rồi thử lại (như hộ chiếu).
WAIT_MS = {
    "CongDan__fs_BCAXaTamTru": 8000,
    "CongDan__fs_BCAXaThuongTru": 8000,
    "CongDan__fs_BCAXaTamTruBaoLanh": 8000,
}

GIOI_TINH_NAM = "Nam"
GIOI_TINH_NU = "Nữ"
THI_THUC_MOT_LAN = "Một lần"
THI_THUC_NHIEU_LAN = "Nhiều lần"
LOAI_HC_PHO_THONG = "Hộ chiếu phổ thông"
LOAI_HC_NGOAI_GIAO = "Hộ chiếu ngoại giao"
LOAI_HC_CONG_VU = "Hộ chiếu công vụ"
LOAI_HC_KHAC = "Khác"

# Option ô "Mục đích nhập cảnh" (37 mục). Mapping chỉ chụp được "thăm thân" — các mục khác SUY theo tên mục đích ở
# Luật Nhập cảnh (ký hiệu thị thực); extension khớp chứa chữ nên tên rút gọn vẫn chọn được option dài hơn.
MUC_DICH_BY_KEYWORD: tuple[tuple[str, str], ...] = (
    ("tham than", "thăm thân"),
    ("du lich", "du lịch"),
    ("lao dong", "lao động"),
    ("dau tu", "đầu tư"),
    ("du hoc", "du học"),
    ("hoc tap", "du học"),
    ("thuc tap", "thực tập"),
    ("hoi nghi", "hội nghị"),
    ("hoi thao", "hội nghị"),
    ("phong vien", "phóng viên"),
    ("bao chi", "phóng viên"),
    ("lam viec", "làm việc"),
    ("cong tac", "làm việc"),
)

# Cửa khẩu sân bay quốc tế → option dạng "SBQT <tên>" (mapping: "Cửa khẩu Sân bay quốc tế Nội Bài" → "SBQT Nội Bài").
CUA_KHAU_SAN_BAY_PREFIX = "SBQT"

# Mã quốc gia ICAO (MRZ / Country code) → tên nước tiếng Anh của danh mục cổng (203 mục). Mapping chỉ chụp "Canada";
# mapping thẻ tạm trú 1.003460 (19/11) chụp thêm "Republic of Korea" và "Korea Democratic Peoples Republic of" → danh mục
# theo tên chính thức; tên các nước khác SUY theo tên tiếng Anh thông dụng — khớp chứa chữ của extension đỡ được phần
# đuôi kiểu "Russian Federation", "Lao People's Democratic Republic", "Brunei Darussalam".
COUNTRY_BY_CODE: dict[str, str] = {
    "AFG": "Afghanistan", "ARG": "Argentina", "AUS": "Australia", "AUT": "Austria", "BGD": "Bangladesh",
    "BEL": "Belgium", "BRA": "Brazil", "BRN": "Brunei", "BGR": "Bulgaria", "KHM": "Cambodia", "CAN": "Canada",
    "CHE": "Switzerland", "CHL": "Chile", "CHN": "China", "COL": "Colombia", "CUB": "Cuba", "CZE": "Czech",
    "D": "Germany", "DEU": "Germany", "DNK": "Denmark", "EGY": "Egypt", "ESP": "Spain", "FIN": "Finland",
    "FRA": "France", "GBR": "United Kingdom", "GRC": "Greece", "HKG": "Hong Kong", "HUN": "Hungary",
    "IDN": "Indonesia", "IND": "India", "IRL": "Ireland", "IRN": "Iran", "ISR": "Israel", "ITA": "Italy",
    "JPN": "Japan", "KAZ": "Kazakhstan", "KOR": "Republic of Korea", "LAO": "Lao", "LKA": "Sri Lanka", "MEX": "Mexico",
    "MMR": "Myanmar", "MNG": "Mongolia", "MYS": "Malaysia", "NLD": "Netherlands", "NOR": "Norway", "NPL": "Nepal",
    "NZL": "New Zealand", "PAK": "Pakistan", "PHL": "Philippines", "POL": "Poland", "PRK": "Korea Democratic Peoples Republic of",
    "PRT": "Portugal", "ROU": "Romania", "RUS": "Russia", "SAU": "Saudi Arabia", "SGP": "Singapore",
    "SWE": "Sweden", "THA": "Thailand", "TUR": "Turkey", "TWN": "Taiwan", "UKR": "Ukraine", "USA": "United States",
    "ZAF": "South Africa",
}

# Tên nước tiếng Việt / phiên âm (đã fold, bỏ gạch nối) → mã quốc gia.
CODE_BY_VI_NAME: dict[str, str] = {
    "ca na da": "CAN", "canada": "CAN", "my": "USA", "hoa ky": "USA", "anh": "GBR", "vuong quoc anh": "GBR",
    "phap": "FRA", "duc": "DEU", "uc": "AUS", "o xtray lia": "AUS", "nhat ban": "JPN", "han quoc": "KOR",
    "trieu tien": "PRK", "trung quoc": "CHN", "dai loan": "TWN", "hong kong": "HKG", "nga": "RUS", "lien bang nga": "RUS",
    "lao": "LAO", "campuchia": "KHM", "cam pu chia": "KHM", "thai lan": "THA", "ma lai xi a": "MYS",
    "malaysia": "MYS", "xin ga po": "SGP", "singapore": "SGP", "in do ne xi a": "IDN", "indonesia": "IDN",
    "phi lip pin": "PHL", "philippines": "PHL", "my an ma": "MMR", "myanmar": "MMR", "an do": "IND", "y": "ITA",
    "tay ban nha": "ESP", "bo dao nha": "PRT", "ha lan": "NLD", "bi": "BEL", "thuy si": "CHE", "thuy dien": "SWE",
    "na uy": "NOR", "dan mach": "DNK", "phan lan": "FIN", "ba lan": "POL", "sec": "CZE", "hung ga ri": "HUN",
    "ru ma ni": "ROU", "bun ga ri": "BGR", "u crai na": "UKR", "tho nhi ky": "TUR", "ai len": "IRL",
    "niu di lan": "NZL", "mong co": "MNG", "ca dac xtan": "KAZ", "pa ki xtan": "PAK", "ban gla det": "BGD",
    "nam phi": "ZAF", "ai cap": "EGY", "bra xin": "BRA", "ac hen ti na": "ARG", "mexico": "MEX", "me hi co": "MEX",
    "cu ba": "CUB", "hy lap": "GRC", "i xra en": "ISR", "i ran": "IRN",
}
