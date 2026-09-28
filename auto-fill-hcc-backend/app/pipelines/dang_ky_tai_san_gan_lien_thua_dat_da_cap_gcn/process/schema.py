"""Compact schema cho "Đăng ký tài sản gắn liền với thửa đất đã được cấp GCN hoặc đăng ký thay đổi về tài sản
gắn liền với đất..." (mã 1.013995) — cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn (Form.io). CÙNG field-key
panel "Thông tin chung" với dang_ky_bien_dong_dat_dai_da_nang.

HAI vai:
- ChuHoSo_* : CHỦ HỒ SƠ = người sử dụng đất / chủ sở hữu tài sản đứng tên Đơn Mẫu 18 mục 1. Hay là TỔ CHỨC
              (doanh nghiệp đăng ký công trình, nhà xưởng mới xây trên đất thuê KCN).
- NguoiNop_*: NGƯỜI NỘP = tài khoản đăng nhập. Họ tên, ngày sinh, số định danh cổng tự đổ từ tài khoản (ô
              khoá) → chỉ trích giới tính/ngày cấp/nơi cấp từ CCCD KHỚP tài khoản (runner neo thẻ).
"""

FIELDS: list[dict] = [
    {"name": "ChuHoSo_LoaiChuThe", "desc": '"Tổ chức" nếu chủ hồ sơ là công ty/doanh nghiệp/HTX/cơ quan; "Cá '
        'nhân" nếu là một người. Chủ hồ sơ là người đứng tên Đơn Mẫu 18 mục 1a "Tên".'},
    {"name": "ChuHoSo_HoTen", "desc": "Tên CHỦ HỒ SƠ — CÁ NHÂN: họ và tên (IN HOA); TỔ CHỨC: tên ĐẦY ĐỦ, KHÔNG "
        "viết tắt (Đơn hay viết tắt 'TM', 'DV', 'SX', 'XD' → lấy cách viết đầy đủ ở GCN mục IV 'Những thay đổi "
        "sau khi cấp GCN' / văn bản khác cùng mã số doanh nghiệp). Nguồn: Đơn Mẫu 18 mục 1a 'Tên'."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "TỔ CHỨC: MÃ SỐ DOANH NGHIỆP / MST (Đơn Mẫu 18 mục 1b 'Giấy tờ nhân "
        "thân/pháp nhân', GCN mục IV 'MSDN số'). CÁ NHÂN: số CCCD. CHỈ chữ số. KHÔNG lấy mã số dự án, số giấy "
        "phép kinh doanh của CHỦ CŨ ở GCN mục I, số phát hành/số vào sổ GCN."},
    {"name": "ChuHoSo_DiaChi", "desc": "Địa chỉ CHỦ HỒ SƠ (tổ chức = địa chỉ TRỤ SỞ), object {quocGia,tinh,xa,"
        "diaChi}. Nguồn: Đơn Mẫu 18 mục 1c 'Địa chỉ' (ưu tiên — đã theo đơn vị hành chính mới), GCN mục IV. "
        "tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=lô/số nhà/đường/khu (KHÔNG kèm phường/xã/tỉnh). KHÔNG "
        "lấy địa chỉ THỬA ĐẤT (GCN mục II) hay địa điểm xây dựng dự án."},
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại ở Đơn Mẫu 18 mục 1 'Điện thoại liên hệ'. Có nhiều số thì "
        "ghi TẤT CẢ, cách nhau bằng ' / ' theo thứ tự trên đơn. Không có thì bỏ."},
    {"name": "ChuHoSo_Email", "desc": "Hộp thư điện tử ở Đơn Mẫu 18 mục 1 'Hộp thư điện tử (nếu có)'. Chữ viết "
        "tay có thể xuống dòng giữa địa chỉ → nối liền, bỏ khoảng trắng. Không có thì bỏ."},
    {"name": "NoiDungBienDong", "desc": "Đơn Mẫu 18 mục '2. Nội dung biến động' — CHÉP NGUYÊN VĂN (vd 'Đăng ký "
        "bổ sung nhà xưởng xây dựng mới theo giấy phép số ...'). KHÔNG tự bịa/suy đoán."},
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên in trên thẻ CCCD của NGƯỜI NỘP (tài khoản đăng nhập) — CHỈ khi "
        "hồ sơ có thẻ CCCD KHỚP tài khoản (xem nguoi_nop_context). Không có thì bỏ."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số định danh (12 số) trên CHÍNH thẻ CCCD người nộp. Chỉ chữ số."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính trên thẻ CCCD người nộp: "Nam"/"Nữ".'},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CHÍNH thẻ CCCD người nộp (mặt sau 'Ngày, tháng, năm cấp / "
        "Date of issue'), dd/mm/yyyy. KHÔNG lấy ngày hết hạn, ngày ký đơn, ngày cấp GCN/giấy phép."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp thẻ CCCD người nộp, chép ĐÚNG như in trên thẻ (vd 'Bộ Công "
        "an', 'Cục Cảnh sát quản lý hành chính về trật tự xã hội'). Thẻ không in cơ quan cấp → BỎ TRỐNG."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["NguoiNop_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["ChuHoSo_DiaChi"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — field-key lấy từ DOM thật (mapping 1.013995). data[fullname],
# data[birthday], data[identityNumber] cổng đổ sẵn từ tài khoản → KHÔNG phát.
UI_COMP_BY_NAME = {
    "data[chonDoiTuong]": "dom-select",        # Cá nhân / Tổ chức — theo CHỦ HỒ SƠ.
    "data[isOwnerDossier]": "dom-checkbox",    # "Chủ hồ sơ cũng là người nộp hồ sơ".
    "data[ownerFullname]": "dom-input",
    "data[organization]": "dom-input",         # Tên cơ quan/doanh nghiệp/tổ chức (chủ hồ sơ tổ chức).
    "data[taxCode]": "dom-input",              # Mã định danh tổ chức, doanh nghiệp.
    "data[gender]": "dom-select",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[email]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    "data[noidungyeucaugiaiquyet]": "dom-input",
}
