"""Compact schema cho "Đăng ký biến động ... do chia, tách, hợp nhất, sáp nhập tổ chức hoặc chuyển đổi mô hình tổ
chức, chuyển đổi loại hình doanh nghiệp..." (mã 1.013977) — cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn
(Form.io). CÙNG field-key panel "Thông tin chung" với dang_ky_tai_san_gan_lien_thua_dat_da_cap_gcn (1.013995).

BA vai:
- ChuHoSo_*  : CHỦ HỒ SƠ = TỔ CHỨC sử dụng đất theo TÊN MỚI (sau chia/tách/sáp nhập/đổi tên/chuyển đổi) —
               người đứng tên Đơn Mẫu 18 mục 1. KHÔNG lấy tên CŨ in trên GCN quyền sử dụng đất.
- UyQuyen_*  : BÊN ĐƯỢC ỦY QUYỀN trên Giấy/Hợp đồng ủy quyền (mục "Bên được ủy quyền") — thường chính là
               người nộp. Giấy UQ ghi cấp ngày/nơi cấp/điện thoại của họ nhưng KHÔNG ghi giới tính.
- NguoiNop_* : NGƯỜI NỘP = tài khoản đăng nhập. Họ tên, ngày sinh, số định danh cổng tự đổ từ tài khoản (ô
               khoá) → chỉ trích giới tính/ngày cấp/nơi cấp từ CCCD KHỚP tài khoản (runner neo thẻ).
"""

FIELDS: list[dict] = [
    {"name": "ChuHoSo_LoaiChuThe", "desc": '"Tổ chức" nếu chủ hồ sơ là công ty/doanh nghiệp/HTX/cơ quan/đơn vị; '
        '"Cá nhân" nếu là một người. Chủ hồ sơ là người đứng tên Đơn Mẫu 18 mục 1a "Tên".'},
    {"name": "ChuHoSo_HoTen", "desc": "Tên CHỦ HỒ SƠ = tổ chức sử dụng đất theo TÊN MỚI sau thay đổi, viết ĐẦY "
        "ĐỦ bằng tiếng Việt, KHÔNG viết tắt. Nguồn ưu tiên: Giấy chứng nhận đăng ký doanh nghiệp mục 1 'Tên "
        "công ty viết bằng tiếng Việt' (bản thay đổi MỚI NHẤT) → Đơn Mẫu 18 mục 1a 'Tên' → tờ khai lệ phí trước "
        "bạ [04]. KHÔNG lấy tên cũ trên GCN quyền sử dụng đất mục I hay dòng 'Tên cũ' của Đơn; KHÔNG lấy tên "
        "tiếng nước ngoài/tên viết tắt; KHÔNG lấy tên người đại diện theo pháp luật."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "TỔ CHỨC: MÃ SỐ DOANH NGHIỆP / MST (GCN đăng ký doanh nghiệp, Đơn Mẫu "
        "18 mục 1b, tờ khai thuế [06]). CÁ NHÂN: số CCCD. CHỈ chữ số. KHÔNG lấy số phát hành/số vào sổ GCN, số "
        "CCCD người đại diện theo pháp luật."},
    {"name": "ChuHoSo_DiaChi", "desc": "Địa chỉ TRỤ SỞ CHÍNH hiện tại của chủ hồ sơ, object {quocGia,tinh,xa,"
        "diaChi}. Nguồn: Đơn Mẫu 18 mục 1c 'Địa chỉ' (đã theo đơn vị hành chính mới) → GCN đăng ký doanh nghiệp "
        "mục 2 'Địa chỉ trụ sở chính'. tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường/khu (KHÔNG "
        "kèm phường/xã/tỉnh). KHÔNG lấy địa chỉ CŨ ở GCN quyền sử dụng đất mục I, KHÔNG lấy địa chỉ THỬA ĐẤT, "
        "KHÔNG lấy địa chỉ liên lạc của người đại diện."},
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại ở Đơn Mẫu 18 mục 1 'Điện thoại liên hệ'. Có nhiều số thì "
        "ghi TẤT CẢ, cách nhau bằng ' / '. Không có thì bỏ."},
    {"name": "ChuHoSo_Email", "desc": "Hộp thư điện tử của chủ hồ sơ ở Đơn Mẫu 18 / GCN đăng ký doanh nghiệp "
        "'Thư điện tử' — CHỈ khi đúng dạng email (có '@'); địa chỉ website (www...) thì BỎ. Không có thì bỏ."},
    {"name": "ThuaDat_DiaChi", "desc": "Địa chỉ THỬA ĐẤT / khu đất đăng ký biến động theo đơn vị hành chính HIỆN "
        "HÀNH, object {quocGia,tinh,xa,diaChi}. Nguồn ưu tiên: tờ khai lệ phí trước bạ mục 'Địa chỉ thửa đất' "
        "(Số nhà, Đường/phố, Xã/phường, Tỉnh/thành phố) → trang bổ sung GCN ghi 'tên phường thay đổi ... thành "
        "phường ...' (lấy tên MỚI) → GCN mục II 'Địa chỉ' của thửa đất. xa=phường/xã, diaChi=lô/số nhà/đường/khu "
        "(KHÔNG kèm phường/quận/tỉnh). KHÔNG lấy địa chỉ trụ sở của tổ chức."},
    {"name": "NoiDungBienDong", "desc": "Đơn Mẫu 18 mục '2. Nội dung biến động' — CHÉP NGUYÊN VĂN câu/đoạn "
        "đầu (vd 'Thay đổi tên người sử dụng đất trên Giấy chứng nhận ... số AB 123456 ... cấp ngày ...'); "
        "KHÔNG chép các khối liệt kê 'Tên cũ/Tên mới' bên dưới. KHÔNG tự bịa/suy đoán."},
    {"name": "UyQuyen_HoTen", "desc": "Họ và tên BÊN ĐƯỢC ỦY QUYỀN trên Giấy/Hợp đồng ủy quyền (mục 'Bên được "
        "ủy quyền'), IN HOA. KHÔNG lấy người đại diện BÊN ỦY QUYỀN. Không có giấy ủy quyền thì bỏ."},
    {"name": "UyQuyen_SoDinhDanh", "desc": "Số CCCD của BÊN ĐƯỢC ỦY QUYỀN trên giấy ủy quyền. Chỉ chữ số."},
    {"name": "UyQuyen_NgayCap", "desc": "Ngày cấp CCCD của BÊN ĐƯỢC ỦY QUYỀN ('Cấp ngày' trên giấy ủy quyền), "
        "dd/mm/yyyy. KHÔNG lấy ngày lập giấy ủy quyền."},
    {"name": "UyQuyen_NoiCap", "desc": "Nơi cấp CCCD của BÊN ĐƯỢC ỦY QUYỀN, chép đúng như trên giấy (vd 'Cục "
        "QLHC về TTXH', 'Bộ Công an')."},
    {"name": "UyQuyen_DienThoai", "desc": "Điện thoại của BÊN ĐƯỢC ỦY QUYỀN trên giấy ủy quyền. KHÔNG lấy số "
        "hotline/điện thoại in ở tiêu đề thư của tổ chức ủy quyền."},
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên in trên thẻ CCCD của NGƯỜI NỘP (tài khoản đăng nhập) — CHỈ khi "
        "hồ sơ có thẻ CCCD KHỚP tài khoản (xem nguoi_nop_context). Không có thì bỏ."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số định danh (12 số) trên CHÍNH thẻ CCCD người nộp. Chỉ chữ số."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính trên thẻ CCCD người nộp: "Nam"/"Nữ".'},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CHÍNH thẻ CCCD người nộp (mặt sau 'Ngày, tháng, năm cấp / "
        "Date of issue'), dd/mm/yyyy. KHÔNG lấy ngày hết hạn, ngày ký đơn, ngày cấp GCN."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp thẻ CCCD người nộp, chép ĐÚNG như in trên thẻ (vd 'Bộ Công "
        "an', 'Cục Cảnh sát quản lý hành chính về trật tự xã hội'). Thẻ không in cơ quan cấp → BỎ TRỐNG."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["NguoiNop_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["UyQuyen_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["ChuHoSo_DiaChi"] = "x-select-area"
COMPACT_COMP_BY_NAME["ThuaDat_DiaChi"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — field-key lấy từ DOM thật (mapping 1.013977). data[fullname],
# data[birthday], data[identityNumber], data[nation], data[hinhThucNop] cổng đổ sẵn → KHÔNG phát.
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
