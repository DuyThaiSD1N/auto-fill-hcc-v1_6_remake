"""Facts nguồn cho "Khánh Hòa - Đăng ký biến động quyền sử dụng đất … chuyển nhượng, thừa kế, tặng cho" (1.013831).

Đi từ link kê khai DVCQG (chỉ chọn Tỉnh, bấm thẻ Chi nhánh VPĐK đất đai theo xã) sang cổng tỉnh iGate Khánh Hòa. Form
Form.io CÙNG TEMPLATE ba khối với đăng ký đất đai lần đầu / cấp đổi GCN Khánh Hòa (file mapping trùng khít tập
data[...]) nên dùng chung UI_COMP_BY_NAME. Panel "Thông tin tổ chức" chỉ hiện khi tick radio data[CaNhan_ToChuc][<hậu tố
ngẫu nhiên>] = Tổ chức — không điền được theo tên nên không khai.

Nguồn: Đơn đăng ký biến động Mẫu số 18 (viết tay), GCN đã cấp cho BÊN CHUYỂN, hợp đồng/văn bản chuyển quyền có công
chứng (chuyển nhượng, tặng cho, thỏa thuận/khai nhận/phân chia di sản), tờ khai lệ phí trước bạ + thuế TNCN, phiếu đo
đạc chỉnh lý/mảnh trích đo, chứng từ nộp tiền, CCCD. Bẫy chính: chủ hồ sơ là BÊN NHẬN chuyển quyền, không phải người ở
mục I của GCN hay bên tặng cho; thửa đất sau đo đạc chỉnh lý có số MỚI, giấy tờ cũ ghi số CŨ.
"""

from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.process.schema import UI_COMP_BY_NAME  # noqa: F401

FIELDS: list[dict] = [
    {
        "name": "ChuHoSo_LoaiChuThe",
        "desc": '"Tổ chức" nếu bên nhận chuyển quyền là công ty/doanh nghiệp/HTX/cơ quan; "Cá nhân" nếu là một người.',
    },
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên CHỦ HỒ SƠ = BÊN NHẬN chuyển nhượng/tặng cho/thừa kế. Nguồn theo thứ tự: CCCD của đúng người -> Đơn "
        "đăng ký biến động mục I 'Tên' (hướng dẫn mẫu: nhận chuyển quyền thì ghi bên nhận) -> tờ khai lệ phí trước bạ "
        "[04] Người nộp thuế -> tờ khai thuế TNCN mục II [11.2] (người nhận) -> hợp đồng 'Bên được tặng cho'/'Bên nhận "
        "chuyển nhượng' (bên B) -> văn bản thừa kế: người ĐƯỢC NHẬN di sản. Chỉ lấy HỌ TÊN, giữ nguyên dấu.",
    },
    {
        "name": "ChuHoSo_NguoiCungSuDung",
        "desc": "Họ tên người CÙNG nhận chuyển quyền với chủ hồ sơ (vd vợ chồng cùng nhận chuyển nhượng), nối bằng '; '. "
        "Một người nhận thì bỏ field.",
    },
    {
        "name": "ChuHoSo_NgaySinh",
        "desc": "Ngày sinh đầy đủ của CHỦ HỒ SƠ, dd/mm/yyyy. Nguồn: CCCD -> Đơn mục I (dòng 'Sinh năm dd/mm/yyyy' có đủ "
        "ngày tháng thì dùng) -> tờ khai TNCN [11.4] -> văn bản công chứng/quyết định ghi 'sinh ngày'. Giấy chỉ ghi "
        "năm sinh thì không dùng.",
    },
    {
        "name": "ChuHoSo_SoDinhDanh",
        "desc": "Số CCCD/căn cước/định danh của CHỦ HỒ SƠ, chỉ chữ số: CCCD -> Đơn 'Giấy tờ nhân thân' -> tờ khai LPTB "
        "[07] -> tờ khai TNCN [11.3] -> văn bản công chứng. Lấy số khớp ở nhiều giấy nhất.",
    },
    {
        "name": "ChuHoSo_NgayCap",
        "desc": "Ngày cấp CCCD/căn cước của CHỦ HỒ SƠ, dd/mm/yyyy: CCCD -> Đơn 'Cấp ngày' -> văn bản công chứng/quyết định "
        "('… cấp ngày …'). Cùng một số mà các giấy ghi NHIỀU ngày cấp (thẻ CCCD cũ, thẻ căn cước mới) thì lấy ngày MỚI "
        "NHẤT. Không lấy ngày ký hợp đồng, ngày công chứng, ngày lập đơn.",
    },
    {
        "name": "ChuHoSo_NoiCap",
        "desc": "Cơ quan cấp CCCD/căn cước của CHỦ HỒ SƠ, đi cùng ĐÚNG lần cấp của ChuHoSo_NgayCap ('do Bộ Công an cấp', "
        "'tại Cục Cảnh sát quản lý hành chính về trật tự xã hội').",
    },
    {
        "name": "ChuHoSo_DiaChi",
        "desc": "Nơi THƯỜNG TRÚ hiện tại của CHỦ HỒ SƠ, object {quocGia,tinh,xa,chiTietDuoiXa}. Ưu tiên: CCCD -> Đơn mục I "
        "'Địa chỉ' -> tờ khai LPTB [08]–[10] -> văn bản công chứng (thường địa danh CŨ trước sắp xếp). KHÔNG lấy địa "
        "chỉ thửa đất, địa chỉ ghi theo Giấy chứng nhận cũ.",
    },
    {
        "name": "ChuHoSo_DienThoai",
        "desc": "Số điện thoại của CHỦ HỒ SƠ, chỉ chữ số: Đơn mục I 'Điện thoại liên hệ' -> tờ khai LPTB [11] -> tờ khai "
        "TNCN [04.8] CHỈ khi dòng đó ghi đúng tên chủ hồ sơ.",
    },
    {
        "name": "ChuHoSo_Email",
        "desc": "Email của CHỦ HỒ SƠ: Đơn 'Hộp thư điện tử' -> tờ khai LPTB [13] -> tờ khai TNCN [04.9] (chỉ khi đúng tên "
        "chủ hồ sơ). Chép đúng ký tự, chữ thường.",
    },
    {
        "name": "NguoiNop_HoTen",
        "desc": "Họ tên NGƯỜI NỘP. Có văn bản ủy quyền/đại diện cho CÁ NHÂN làm thủ tục: họ tên BÊN ĐƯỢC ỦY QUYỀN in trên "
        "văn bản đó. Không có ủy quyền thì chép y hệt ChuHoSo_HoTen.",
    },
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh đầy đủ của NGƯỜI NỘP, dd/mm/yyyy. Tự nộp thì giống chủ hồ sơ."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/định danh của NGƯỜI NỘP, chỉ chữ số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD của NGƯỜI NỘP, dd/mm/yyyy (lấy lần cấp mới nhất)."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp CCCD của NGƯỜI NỘP, đi cùng đúng lần cấp."},
    {
        "name": "NguoiNop_DiaChi",
        "desc": "Nơi THƯỜNG TRÚ của NGƯỜI NỘP, object {quocGia,tinh,xa,chiTietDuoiXa}. Tự nộp thì chép nguyên ChuHoSo_DiaChi.",
    },
    {
        "name": "NguoiNop_DienThoai",
        "desc": "Số điện thoại của chính NGƯỜI NỘP, chỉ chữ số. Có ủy quyền: không lấy số của chủ hồ sơ.",
    },
    {"name": "NguoiNop_Email", "desc": "Email của chính NGƯỜI NỘP nếu có."},
    {
        "name": "Don_NoiDungBienDong",
        "desc": "Chép NGUYÊN VĂN, ĐẦY ĐỦ mục 'II. Nội dung biến động' của Đơn (thường viết tay, nhiều dòng), nối các dòng "
        "bằng khoảng trắng, không cắt bớt, không diễn đạt lại. Mục để trống thì bỏ field.",
    },
    {
        "name": "ThuaDat_SoThua",
        "desc": "Số thửa HIỆN HÀNH: theo phiếu đo đạc chỉnh lý/mảnh trích đo mới ('Thửa đất số') hoặc tờ khai ghi dạng "
        "'1016 (257 cũ)' -> 1016. Hồ sơ không có số mới thì lấy số trên Giấy chứng nhận/Đơn. Chỉ lấy số, bỏ '(trích "
        "một phần)'.",
    },
    {
        "name": "ThuaDat_SoThuaCu",
        "desc": "Số thửa CŨ theo Giấy chứng nhận/Đơn/hợp đồng khi khác số hiện hành (vd tờ khai '1016 (257 cũ)' -> 257). "
        "Giống số hiện hành hoặc không có số mới thì bỏ field.",
    },
    {
        "name": "ThuaDat_SoTo",
        "desc": "Số tờ bản đồ HIỆN HÀNH: phiếu đo đạc chỉnh lý/tờ khai ('255 (22 cũ)' -> 255); không có số mới thì theo "
        "Giấy chứng nhận. Chỉ lấy số, bỏ mã mảnh trong ngoặc ('22 (350 599-4-c)' -> 22).",
    },
    {
        "name": "ThuaDat_SoToCu",
        "desc": "Số tờ bản đồ CŨ theo Giấy chứng nhận (in) khi khác số hiện hành, GIỮ mã mảnh trong ngoặc nếu có (vd '3 "
        "(123 456-7-a)'). Không có thì bỏ field.",
    },
    {
        "name": "ThuaDat_DiaChi",
        "desc": "ĐỊA CHỈ THỬA ĐẤT, object {quocGia,tinh,xa,chiTietDuoiXa}, xa là phường/xã HIỆN HÀNH: Đơn mục II ('tọa lạc "
        "tại …') -> phiếu đo đạc mục 2 -> tờ khai LPTB 1.2 / TNCN [20.3]–[20.5] -> Giấy chứng nhận (địa danh cũ). KHÔNG "
        "lấy nơi thường trú của người.",
    },
    {
        "name": "ThuaDat_DiaChiDayDu",
        "desc": "Địa chỉ thửa đất dạng chữ, chép NGUYÊN VĂN theo nguồn mới nhất: cụm sau 'tọa lạc tại' ở mục II của Đơn -> "
        "'2. Địa chỉ thửa đất' của phiếu đo đạc -> tờ khai -> dòng 'Địa chỉ thửa đất' của Giấy chứng nhận.",
    },
    {
        "name": "GCN_SoPhatHanh",
        "desc": "Số phát hành (serial) của Giấy chứng nhận đã cấp, 2 chữ cái + 6 chữ số (vd 'AB 123456'). Không lấy số "
        "vào sổ ('H…', 'CH…').",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_DiaChi", "NguoiNop_DiaChi", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"
