"""Facts nguồn cho thủ tục [Lào Cai] Đăng ký biến động thay đổi quyền sử dụng đất do CHIA, TÁCH, HỢP
NHẤT, SÁP NHẬP TỔ CHỨC hoặc chuyển đổi mô hình tổ chức/loại hình doanh nghiệp; điều chỉnh quy hoạch
xây dựng chi tiết; cấp Giấy chứng nhận cho từng thửa đất theo quy hoạch (mã 1.115670).

Cổng `dichvucong.laocai.gov.vn` dùng eForm iGate legacy (bộ ô `CongDan_*` / `ChuHoSo_*`) — CÙNG 35 ô
với các thủ tục Lào Cai khác nên engine `fill-legacy.js` của extension chạy được ngay.

Trang nhập liệu CHỈ có 2 khối nhân thân (người nộp + chủ hồ sơ) và 2 textarea ở bước thành phần hồ sơ;
KHÔNG có phần thân đơn (thửa đất, nội dung biến động) → các field nghiệp vụ vẫn trích để lưu trace và
để dựng trích yếu, nhưng không khai trong UI_COMP_BY_NAME nên mapper không phát.

⚑ Chủ hồ sơ của thủ tục này gần như luôn là TỔ CHỨC (doanh nghiệp sau chuyển đổi, đơn vị sự nghiệp sau
sáp nhập). Khi chọn đối tượng "Tổ chức", cổng ẨN 7 ô cá nhân của khối chủ hồ sơ (họ tên, ngày sinh,
giới tính, dân tộc, số/nơi cấp/ngày cấp căn cước) — mapper không phát các ô đó để khỏi điền vào ô ẩn.
"""

FIELDS: list[dict] = [
    # --- CHỦ HỒ SƠ = người sử dụng đất khai ở Đơn Mẫu 24 (tổ chức SAU khi chia/tách/sáp nhập) ---
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên người đứng tên CHỦ HỒ SƠ khi chủ hồ sơ là CÁ NHÂN. Hồ sơ tổ chức thì BỎ FIELD "
                "này — không lấy tên giám đốc/người ký đơn thay cho tên tổ chức.",
    },
    {
        "name": "ChuHoSo_LaToChuc",
        "desc": "true nếu CHỦ HỒ SƠ là TỔ CHỨC (doanh nghiệp, trung tâm, ban quản lý, đơn vị sự nghiệp "
                "công lập…), false nếu cá nhân/hộ gia đình. Mục 1.1 của Đơn Mẫu 24 ghi tên tổ chức, "
                "hoặc có quyết định thành lập/ĐKDN → true.",
    },
    {
        "name": "ChuHoSo_TenToChuc",
        "desc": "Tên đầy đủ của TỔ CHỨC đứng đơn, NGUYÊN VĂN. Nguồn ưu tiên: mục 1.1 'Tên' của Đơn Mẫu "
                "24; không rõ thì lấy tên tổ chức MỚI ở trích yếu/Điều 1 của quyết định thành lập, tổ "
                "chức lại. TUYỆT ĐỐI không lấy tên tổ chức CŨ (tổ chức trước khi chia/tách/sáp nhập).",
    },
    {
        "name": "ChuHoSo_MaSoThue",
        "desc": "Mã số thuế/mã số doanh nghiệp của tổ chức đứng đơn (có thể có đuôi -001). Chỉ lấy khi "
                "giấy tờ ghi rõ — mục 1.2 Đơn Mẫu 24 hoặc Giấy chứng nhận đăng ký doanh nghiệp. Đơn vị "
                "sự nghiệp công lập thường KHÔNG có; không có thì bỏ field, không suy từ quyết định.",
    },
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh đầy đủ của chủ hồ sơ CÁ NHÂN, dd/mm/yyyy. Chủ hồ sơ là tổ chức thì bỏ field. Chỉ có năm sinh cũng bỏ field, không tự đặt ngày/tháng."},
    {"name": "ChuHoSo_GioiTinh", "desc": "Giới tính chủ hồ sơ CÁ NHÂN: Nam/Nữ, suy từ danh xưng gắn trực tiếp với người đó (Ông=Nam, Bà=Nữ) hoặc chữ số thứ 4 của CCCD 12 số. Tổ chức thì bỏ field."},
    {"name": "ChuHoSo_DanToc", "desc": "Dân tộc của chủ hồ sơ CÁ NHÂN nếu giấy tờ ghi rõ. Tổ chức thì bỏ field."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/CMND của chủ hồ sơ CÁ NHÂN, chỉ chữ số. Tổ chức thì bỏ field — không điền số căn cước của người đại diện vào đây."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp giấy tờ định danh của chủ hồ sơ cá nhân, dd/mm/yyyy, đi cùng đúng số giấy tờ. Tổ chức thì bỏ field."},
    {"name": "ChuHoSo_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh của chủ hồ sơ cá nhân. Tổ chức thì bỏ field — KHÔNG lấy cơ quan ban hành quyết định thành lập thay vào đây."},
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": "Địa chỉ của CHỦ HỒ SƠ, object {quocGia,tinh,xa,diaChi}. Tổ chức thì đây là ĐỊA CHỈ TRỤ "
                "SỞ ở mục 1.3 Đơn Mẫu 24 (giữ đủ thôn/tổ/số nhà trong diaChi); cá nhân thì là nơi thường "
                "trú. ĐÂY KHÔNG PHẢI địa chỉ thửa đất — tuyệt đối không lấy nhầm.",
    },
    {"name": "ChuHoSo_DienThoai", "desc": "Điện thoại liên hệ của chủ hồ sơ, chỉ chữ số. Nguồn: mục 1.4 Đơn Mẫu 24."},
    {"name": "ChuHoSo_Email", "desc": "Hộp thư điện tử của chủ hồ sơ nếu đơn ghi rõ (mục 1.4). Đơn để trống thì bỏ field."},
    {"name": "ChuHoSo_Fax", "desc": "Số fax của chủ hồ sơ nếu giấy tờ ghi rõ."},

    # --- NGƯỜI NỘP HỒ SƠ = người viết/ký Đơn Mẫu 24 (hoặc bên được ủy quyền) ---
    {
        "name": "NguoiNop_HoTen",
        "desc": "Họ tên NGƯỜI NỘP — người viết đơn ở dòng ký tên cuối Đơn Mẫu 24. Có văn bản ủy quyền "
                "thì lấy BÊN ĐƯỢC ỦY QUYỀN. Đây là CÁ NHÂN, không phải tên tổ chức.",
    },
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh đầy đủ của NGƯỜI NỘP, dd/mm/yyyy (nguồn: CCCD). Chỉ có năm sinh thì bỏ field."},
    {"name": "NguoiNop_GioiTinh", "desc": "Giới tính NGƯỜI NỘP: Nam/Nữ. Suy từ danh xưng gắn trực tiếp với chính người đó hoặc chữ số thứ 4 của CCCD 12 số."},
    {"name": "NguoiNop_DanToc", "desc": "Dân tộc của NGƯỜI NỘP nếu giấy tờ ghi rõ."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền thì lấy của BÊN ĐƯỢC ỦY QUYỀN."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp giấy tờ định danh của NGƯỜI NỘP, dd/mm/yyyy, đi cùng đúng số giấy tờ."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh của NGƯỜI NỘP, đi cùng đúng số và ngày cấp."},
    {
        "name": "NguoiNop_NoiCuTru",
        "desc": "Địa chỉ của NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi}. Nguồn: nơi thường trú trên CCCD "
                "của chính người đó; không có thì dùng địa chỉ trụ sở của tổ chức ở Đơn Mẫu 24.",
    },
    {"name": "NguoiNop_DienThoai", "desc": "Điện thoại của NGƯỜI NỘP, chỉ chữ số. Không có riêng thì dùng số liên hệ trên đơn."},
    {"name": "NguoiNop_Email", "desc": "Email của NGƯỜI NỘP nếu có."},
    {"name": "NguoiNop_Fax", "desc": "Số fax của NGƯỜI NỘP nếu có."},

    # --- Nghiệp vụ (dựng trích yếu + lưu trace) ---
    {
        "name": "Don_TrichYeu",
        "desc": "TRÍCH YẾU hồ sơ (ô 'Về việc' ở bước Thành phần hồ sơ). Viết theo nội dung THẬT của Đơn "
                "Mẫu 24, dạng: \"Đăng ký biến động - <nội dung biến động> thửa <số thửa>, tờ bản đồ <số "
                "tờ>, <địa chỉ thửa đất>\". TUYỆT ĐỐI KHÔNG chép tên thủ tục trên cổng.",
    },
    {
        "name": "Don_NoiDungBienDong",
        "desc": "Nội dung biến động khai ở mục 2 Đơn Mẫu 24, chép NGUYÊN VĂN (vd 'sáp nhập tổ chức', "
                "'chuyển đổi loại hình doanh nghiệp', 'thay đổi tên người sử dụng đất'). Không lấy tiêu "
                "đề thủ tục trên cổng.",
    },
    {
        "name": "ToChucCu_Ten",
        "desc": "Tên TỔ CHỨC CŨ — tổ chức đứng tên trên Giấy chứng nhận đã cấp, trước khi chia/tách/hợp "
                "nhất/sáp nhập/chuyển đổi. Lấy ở Giấy chứng nhận hoặc phần căn cứ của quyết định.",
    },
    {
        "name": "QuyetDinh_So",
        "desc": "Số quyết định về việc chia/tách/hợp nhất/sáp nhập/tổ chức lại (vd '1387/QĐ-UBND'). Có "
                "nhiều quyết định thì lấy quyết định LÀM THAY ĐỔI TỔ CHỨC, không lấy quyết định đất đai cũ.",
    },
    {"name": "QuyetDinh_Ngay", "desc": "Ngày ban hành của quyết định nêu trên, dd/mm/yyyy. Thiếu ngày/tháng thì bỏ field."},
    {"name": "QuyetDinh_CoQuan", "desc": "Cơ quan ban hành quyết định nêu trên, nguyên văn (vd 'Ủy ban nhân dân xã ...')."},
    {"name": "Gcn_SoPhatHanh", "desc": "Số phát hành (seri) của Giấy chứng nhận đã cấp, vd 'S929126'. Bỏ nếu không đọc được."},
    {"name": "Gcn_SoVaoSo", "desc": "Số vào sổ cấp Giấy chứng nhận, vd '01439/QSDĐ'. Bỏ nếu không đọc được."},
    {"name": "ThuaDat_SoThua", "desc": "Số thửa đất, chỉ chữ số. Lấy ở Giấy chứng nhận hoặc Đơn Mẫu 24."},
    {"name": "ThuaDat_ToBanDo", "desc": "Số tờ bản đồ, chỉ chữ số. Lấy cùng nguồn với số thửa."},
    {
        "name": "ThuaDat_DiaChi",
        "desc": "ĐỊA CHỈ THỬA ĐẤT (KHÔNG phải trụ sở/nơi cư trú), object {quocGia,tinh,xa,diaChi}. Nguồn: "
                "Giấy chứng nhận hoặc Đơn Mẫu 24. Không có nguồn ghi rõ thì bỏ field.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap",
             "QuyetDinh_Ngay"):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"

# CHỈ các ô CÓ THẬT trên trang fill của 1.115670 (đã đối chiếu theo thứ tự DOM của snapshot).
# Cố ý KHÔNG khai `chkbox_nguoinoplachuhs`: checkbox đó của cổng chỉ copy sang khối chủ hồ sơ tới
# Nơi cấp/Ngày cấp căn cước, KHÔNG copy địa chỉ — mapper phát thẳng đủ cả khối chủ hồ sơ.
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
    # --- Bước "Thành phần hồ sơ" (cùng trang nhap-thong-tin-ho-so) ---
    "HoSoOnline_veViec": "dom-input",   # textarea "Về việc" (*) — trích yếu hồ sơ.
    "HoSoOnline_ghiChu": "dom-input",   # textarea "Ghi chú" — liệt kê văn bản trong từng tệp gộp.
}

# 7 ô cá nhân của khối chủ hồ sơ bị display:none khi đối tượng nộp = Tổ chức.
UI_CHU_HO_SO_CA_NHAN = (
    "ChuHoSo_tenChuHoSo",
    "ChuHoSo_ngaySinhChuHoSo",
    "ChuHoSo_gioiTinhChuHoSo",
    "ChuHoSo_danTocChuHoSo",
    "ChuHoSo_soCMNDChuHoSo",
    "ChuHoSo_noiCapCMNDCHS",
    "ChuHoSo_ngayCapCMNDCHS",
)

UI_ALIASES: dict[str, list[str]] = {}
