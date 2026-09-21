"""Facts nguồn cho thủ tục [Lào Cai] Đăng ký, cấp Giấy chứng nhận khi ĐÃ CHUYỂN QUYỀN sử dụng đất
TRƯỚC 01/8/2024 mà bên chuyển quyền đã được cấp Giấy chứng nhận nhưng chưa làm thủ tục chuyển quyền
(mã 1.115666).

Cổng `dichvucong.laocai.gov.vn` dùng eForm iGate legacy (bộ ô `CongDan_*` / `ChuHoSo_*`) — CÙNG nền
tảng với các thủ tục Lai Châu, nên engine `fill-legacy.js` của extension chạy được ngay.

Trang nhập liệu CHỈ có 2 khối nhân thân (người nộp + chủ hồ sơ), KHÔNG có phần thân đơn (nội dung đề
nghị, thửa đất) → các field nghiệp vụ vẫn trích để lưu trace nhưng KHÔNG khai trong UI_COMP_BY_NAME,
mapper sẽ không phát (chống bịa ô không tồn tại).

⚑ Hồ sơ thủ tục này thường là TỔ CHỨC/DOANH NGHIỆP xin thuê đất làm dự án → form có sẵn ô tên tổ chức
và mã số thuế cho cả hai khối.
"""

FIELDS: list[dict] = [
    # --- CHỦ HỒ SƠ (người/tổ chức sử dụng đất, đứng tên đơn) ---
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên người đứng tên CHỦ HỒ SƠ. Hồ sơ TỔ CHỨC thì lấy NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT "
                "ghi trong Đơn xin giao đất/thuê đất hoặc Giấy chứng nhận đăng ký doanh nghiệp; hồ sơ cá "
                "nhân thì lấy người đề nghị trong đơn. Không lấy người ký thay, người được ủy quyền nộp.",
    },
    {
        "name": "ChuHoSo_LaToChuc",
        "desc": "true nếu CHỦ HỒ SƠ là TỔ CHỨC/doanh nghiệp (đơn ghi tên công ty, có mã số doanh nghiệp/"
                "mã số thuế, có ĐKKD), false nếu là cá nhân/hộ gia đình. Không chắc thì bỏ field.",
    },
    {
        "name": "ChuHoSo_TenToChuc",
        "desc": "Tên đầy đủ của TỔ CHỨC/doanh nghiệp đứng đơn, lấy nguyên văn từ Đơn xin giao đất/thuê "
                "đất hoặc Giấy chứng nhận đăng ký doanh nghiệp. Hồ sơ cá nhân thì bỏ field.",
    },
    {
        "name": "ChuHoSo_MaSoThue",
        "desc": "Mã số thuế / mã số doanh nghiệp của tổ chức đứng đơn, chỉ chữ số (có thể có đuôi -001). "
                "Lấy từ Giấy chứng nhận đăng ký doanh nghiệp hoặc đơn. Hồ sơ cá nhân thì bỏ field.",
    },
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh đầy đủ của người đứng tên chủ hồ sơ, dd/mm/yyyy. Ưu tiên CCCD đúng người; chỉ có năm sinh thì BỎ FIELD, không tự đặt ngày/tháng."},
    {"name": "ChuHoSo_GioiTinh", "desc": "Giới tính người đứng tên chủ hồ sơ: Nam/Nữ. Chỉ suy từ danh xưng gắn trực tiếp với người đó (Ông=Nam, Bà=Nữ) hoặc chữ số thứ 4 của CCCD 12 số; không suy từ tên."},
    {"name": "ChuHoSo_DanToc", "desc": "Dân tộc của người đứng tên chủ hồ sơ nếu giấy tờ ghi rõ (vd Kinh). Không có thì bỏ field."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/CMND của người đứng tên CHỦ HỒ SƠ, chỉ chữ số. Thuộc tính phải đi đúng người."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp giấy tờ định danh của chủ hồ sơ, dd/mm/yyyy, đi cùng đúng số giấy tờ."},
    {"name": "ChuHoSo_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh của chủ hồ sơ, lấy cùng giấy tờ với số và ngày cấp."},
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": "Địa chỉ của CHỦ HỒ SƠ, object {quocGia,tinh,xa,diaChi}. Hồ sơ TỔ CHỨC thì đây là ĐỊA CHỈ "
                "TRỤ SỞ ghi trên đơn/ĐKKD; hồ sơ cá nhân thì là nơi thường trú trên CCCD hoặc mục 'Địa "
                "chỉ' của đơn. Giữ đủ số nhà/đường/tổ/thôn trong diaChi. ĐÂY KHÔNG PHẢI địa điểm khu đất "
                "xin giao/thuê — tuyệt đối không lấy nhầm.",
    },
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại liên hệ của chủ hồ sơ, chỉ chữ số. Lấy ở mục 'Địa chỉ liên hệ (điện thoại, fax, email)' của đơn hoặc trên ĐKKD."},
    {"name": "ChuHoSo_Email", "desc": "Email liên hệ của chủ hồ sơ nếu giấy tờ ghi rõ."},
    {"name": "ChuHoSo_Fax", "desc": "Số fax của chủ hồ sơ nếu giấy tờ ghi rõ."},

    # --- NGƯỜI NỘP HỒ SƠ ---
    {"name": "NguoiNop_HoTen", "desc": "Họ tên NGƯỜI NỘP. Có văn bản ủy quyền thì bắt buộc lấy BÊN ĐƯỢC ỦY QUYỀN; không có ủy quyền thì người nộp chính là người đứng tên chủ hồ sơ."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh đầy đủ của NGƯỜI NỘP, dd/mm/yyyy. Chỉ có năm sinh thì bỏ field."},
    {"name": "NguoiNop_GioiTinh", "desc": "Giới tính NGƯỜI NỘP: Nam/Nữ. Suy từ danh xưng gắn trực tiếp với chính người đó hoặc chữ số thứ 4 của CCCD 12 số."},
    {"name": "NguoiNop_DanToc", "desc": "Dân tộc của NGƯỜI NỘP nếu giấy tờ ghi rõ."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền phải lấy của BÊN ĐƯỢC ỦY QUYỀN."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp giấy tờ định danh của NGƯỜI NỘP, dd/mm/yyyy, đi cùng đúng số giấy tờ."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh của NGƯỜI NỘP, đi cùng đúng số và ngày cấp."},
    {
        "name": "NguoiNop_NoiCuTru",
        "desc": "Địa chỉ của NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi}. Không có ủy quyền thì sao chép "
                "NGUYÊN VẸN ChuHoSo_NoiCuTru; có ủy quyền thì lấy địa chỉ của BÊN ĐƯỢC ỦY QUYỀN.",
    },
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền thì lấy số của bên được ủy quyền; không có thì dùng số liên hệ trên đơn."},
    {"name": "NguoiNop_Email", "desc": "Email của NGƯỜI NỘP nếu có."},
    {"name": "NguoiNop_Fax", "desc": "Số fax của NGƯỜI NỘP nếu có."},

    # --- Nghiệp vụ ---
    {
        "name": "Don_TrichYeu",
        "desc": "TRÍCH YẾU hồ sơ (ô 'Về việc' ở bước Thành phần hồ sơ). Viết theo nội dung THẬT của "
                "Đơn Mẫu 24, dạng: \"Đăng ký biến động - nhận chuyển quyền sử dụng đất thửa <số thửa>, "
                "tờ bản đồ <số tờ>, <địa chỉ thửa đất>\". TUYỆT ĐỐI KHÔNG chép tên thủ tục trên cổng.",
    },
    {
        "name": "BenChuyenQuyen_HoTen",
        "desc": "Họ tên BÊN CHUYỂN QUYỀN (người bán/nhượng, người đứng tên trên Giấy chứng nhận đã cấp). "
                "Lấy ở hợp đồng/giấy tờ chuyển quyền hoặc mục 'Người sử dụng đất' của GCN.",
    },
    {
        "name": "BenNhanChuyenQuyen_HoTen",
        "desc": "Họ tên BÊN NHẬN CHUYỂN QUYỀN (người mua/nhận, chính là người làm đơn). Lấy ở hợp đồng/"
                "giấy tờ chuyển quyền và Đơn Mẫu 24.",
    },
    {"name": "Gcn_SoPhatHanh", "desc": "Số phát hành Giấy chứng nhận đã cấp cho bên chuyển quyền (vd 'K 895490'). Bỏ nếu không đọc được."},
    {"name": "ThuaDat_SoThua", "desc": "Số thửa đất, chỉ chữ số. Lấy ở Giấy chứng nhận hoặc Đơn Mẫu 24."},
    {"name": "ThuaDat_ToBanDo", "desc": "Số tờ bản đồ, chỉ chữ số. Lấy cùng nguồn với số thửa."},
    {
        "name": "ThuaDat_DiaChi",
        "desc": "ĐỊA CHỈ THỬA ĐẤT (KHÔNG phải nơi cư trú), object {quocGia,tinh,xa,diaChi}. Nguồn: Giấy "
                "chứng nhận hoặc Đơn Mẫu 24. Không có nguồn ghi rõ thì bỏ field.",
    },
    {
        "name": "Don_NoiDungBienDong",
        "desc": "Nội dung biến động người dân khai trong Đơn Mẫu 24. Chép NGUYÊN VĂN; KHÔNG lấy tiêu đề "
                "thủ tục trên cổng.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"

# CHỈ các ô CÓ THẬT trên 'Lào Cai Giao đất fill.html' (đã liệt kê theo thứ tự DOM).
# Cố ý KHÔNG khai `chkbox_nguoinoplachuhs`: nút/checkbox đó của cổng chỉ copy sang khối chủ hồ sơ tới
# Nơi cấp/Ngày cấp căn cước, KHÔNG copy địa chỉ — mapper phát thẳng đủ cả khối chủ hồ sơ thay vì
# trông vào nó (xem mapper.enrich).
UI_COMP_BY_NAME = {
    # Khối NGƯỜI NỘP
    "CongDan_tenCongDan": "dom-input",
    "CongDan_tenCoQuanToChuc": "dom-input",
    "CongDan_maSoThueNguoiNop": "dom-input",
    "CongDan_ngaySinhCongDan": "dom-input",
    "CongDan_gioiTinhCongDan": "dom-select",
    "CongDan_danTocCongDan": "dom-select",
    "CongDan_soCmnd": "dom-input",
    "CongDan_ngayCapCmnd": "dom-input",
    "CongDan_noiCapCmnd": "dom-input",
    "CongDan_maTinhThanh": "dom-select",   # Tỉnh/Thành phố (cascade 2 cấp, không có huyện).
    "CongDan_maPhuongXa": "dom-select",    # Phường/Xã (nạp sau khi chọn tỉnh).
    "CongDan_diaChi": "dom-input",
    "CongDan_diDong": "dom-input",
    "CongDan_email": "dom-input",
    "CongDan_fax": "dom-input",
    # Khối CHỦ HỒ SƠ
    "ChuHoSo_maDoiTuongNopHS": "dom-select",
    "ChuHoSo_tenChuHoSo": "dom-input",
    "ChuHoSo_tenCoQuanToChucCHS": "dom-input",
    "ChuHoSo_maSoThueChuHoSo": "dom-input",
    "ChuHoSo_ngaySinhChuHoSo": "dom-input",
    "ChuHoSo_gioiTinhChuHoSo": "dom-select",
    "ChuHoSo_danTocChuHoSo": "dom-select",
    "ChuHoSo_soCMNDChuHoSo": "dom-input",
    "ChuHoSo_noiCapCMNDCHS": "dom-input",
    "ChuHoSo_ngayCapCMNDCHS": "dom-input",
    "ChuHoSo_maTinhThanhCHS": "dom-select",
    "ChuHoSo_maPhuongXaCHS": "dom-select",
    "ChuHoSo_diaChiChuHoSo": "dom-input",
    "ChuHoSo_diDongLienLacCHS": "dom-input",
    "ChuHoSo_emailChuHoSo": "dom-input",
    "ChuHoSo_faxChuHoSo": "dom-input",
    # --- Bước "Thành phần hồ sơ" (trang nhap-thong-tin-ho-so) ---
    "HoSoOnline_veViec": "dom-input",   # textarea "Về việc" (*) — trích yếu hồ sơ.
    "HoSoOnline_ghiChu": "dom-input",   # textarea "Ghi chú" — liệt kê văn bản trong từng tệp đính kèm.
}

UI_ALIASES: dict[str, list[str]] = {}
