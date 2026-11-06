"""Facts nguồn cho "Khánh Hòa - Cấp đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất" (1.012783).

Đi từ link kê khai DVCQG sang cổng tỉnh iGate Khánh Hòa. Hai quy trình 1.012783-1.1 (trường hợp còn lại) và
1.012783-1.2 (xã miền núi, hải đảo, vùng sâu, vùng xa…) ra CÙNG một form; form Form.io cùng template ba khối với thủ tục
đăng ký đất đai lần đầu Khánh Hòa (file mapping trùng khít tập data[...]) nên dùng chung UI_COMP_BY_NAME: Phần I người
nộp, Phần II chủ hồ sơ, Phần III thửa đất. Panel "Thông tin tổ chức" (tenToChuc, emailNDD…) chỉ hiện khi tick radio
data[CaNhan_ToChuc][<hậu tố ngẫu nhiên>] = Tổ chức — không điền được theo tên nên không khai.

Nguồn: Đơn đăng ký biến động đất đai (Mẫu số 18, thường viết tay), BẢN GỐC Giấy chứng nhận đã cấp (kèm trang bổ sung),
CCCD nếu có. Bẫy chính: mục I của GCN là người được cấp BAN ĐẦU; người sử dụng đất hiện tại là người nhận chuyển nhượng/
tặng cho/thừa kế ở mục cuối cùng của phần "IV. Những thay đổi sau khi cấp giấy chứng nhận"/Trang bổ sung.
"""

from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.process.schema import UI_COMP_BY_NAME  # noqa: F401

FIELDS: list[dict] = [
    {
        "name": "ChuHoSo_LoaiChuThe",
        "desc": '"Tổ chức" nếu người sử dụng đất là công ty/doanh nghiệp/HTX/cơ quan; "Cá nhân" nếu là một người (kể '
        "cả đại diện hộ gia đình).",
    },
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên CHỦ HỒ SƠ = NGƯỜI SỬ DỤNG ĐẤT HIỆN TẠI. Nguồn theo thứ tự: CCCD của đúng người -> Đơn đăng ký biến "
        "động mục '1. Người sử dụng đất, chủ sở hữu tài sản gắn liền với đất, người quản lý đất' – 'a) Tên' (hoặc chữ "
        "ghi rõ họ tên dưới 'Người viết đơn') -> Giấy chứng nhận: người NHẬN ở dòng chuyển nhượng/tặng cho/thừa kế MỚI "
        "NHẤT trong 'IV. Những thay đổi sau khi cấp giấy chứng nhận' hoặc Trang bổ sung ('Chuyển nhượng cho bà …'); "
        "chỉ khi GCN không có dòng chuyển quyền nào mới lấy mục 'I. Người sử dụng đất…'. Chỉ lấy HỌ TÊN (bỏ 'Ông'/'Bà', "
        "ngày sinh, số giấy tờ viết liền sau). Chép đúng chữ, GIỮ NGUYÊN DẤU.",
    },
    {
        "name": "ChuHoSo_NguoiCungSuDung",
        "desc": "Họ tên NGƯỜI CÙNG SỬ DỤNG ĐẤT với chủ hồ sơ (vợ/chồng, thành viên hộ) nếu Đơn mục 1a hoặc dòng chuyển "
        "quyền mới nhất ghi hai người trở lên ('ông A và bà B'); nối bằng '; '. Một người thì bỏ field.",
    },
    {
        "name": "ChuHoSo_NgaySinh",
        "desc": "Ngày sinh đầy đủ của CHỦ HỒ SƠ, dd/mm/yyyy. Nguồn: CCCD -> Đơn mục 1a (ngày sinh viết tay sau tên, vd "
        "'1 - 2 - 1985' = 01/02/1985). Giấy chứng nhận chỉ ghi 'Năm sinh'/'sinh năm' -> chỉ có năm thì bỏ field.",
    },
    {
        "name": "ChuHoSo_SoDinhDanh",
        "desc": "Số CCCD/căn cước/định danh của CHỦ HỒ SƠ, chỉ chữ số. Nguồn: CCCD -> Đơn mục '1b) Giấy tờ nhân thân/pháp "
        "nhân' -> 'CCCD số' trong dòng chuyển quyền mới nhất của GCN. Chữ viết tay hay đọc lệch: lấy số khớp ở nhiều "
        "giấy nhất.",
    },
    {
        "name": "ChuHoSo_NgayCap",
        "desc": "Ngày cấp CCCD/căn cước của CHỦ HỒ SƠ, dd/mm/yyyy, CHỈ từ thẻ CCCD (mặt sau) hoặc cụm '<số> cấp ngày …'. "
        "TUYỆT ĐỐI không lấy ngày ký GCN, ngày xác nhận biến động, ngày lập đơn.",
    },
    {
        "name": "ChuHoSo_NoiCap",
        "desc": "Cơ quan cấp CCCD/căn cước của CHỦ HỒ SƠ (chức danh ký mặt sau thẻ, vd 'Cục Cảnh sát quản lý hành chính "
        "về trật tự xã hội', 'Bộ Công an'). Không có thẻ thì bỏ field.",
    },
    {
        "name": "ChuHoSo_DiaChi",
        "desc": "Nơi THƯỜNG TRÚ hiện tại của CHỦ HỒ SƠ, object {quocGia,tinh,xa,chiTietDuoiXa}. Ưu tiên: CCCD 'Nơi thường "
        "trú' -> Đơn mục '1c) Địa chỉ' -> 'thường trú' trong dòng chuyển quyền mới nhất của GCN (thường là địa danh "
        "CŨ). Đơn chỉ ghi tổ/thôn + phường mà thiếu tỉnh thì lấy tỉnh từ địa chỉ khác của CHÍNH người này. KHÔNG lấy "
        "địa chỉ thửa đất.",
    },
    {
        "name": "ChuHoSo_DienThoai",
        "desc": "Số điện thoại của CHỦ HỒ SƠ, chỉ chữ số: Đơn mục '1d) Điện thoại liên hệ'.",
    },
    {"name": "ChuHoSo_Email", "desc": "Email của CHỦ HỒ SƠ nếu Đơn mục 1d 'Hộp thư điện tử' có ghi; không có thì bỏ."},
    {
        "name": "NguoiNop_HoTen",
        "desc": "Họ tên NGƯỜI NỘP. Có giấy/hợp đồng ủy quyền cho CÁ NHÂN làm thủ tục cấp đổi: họ tên BÊN ĐƯỢC ỦY QUYỀN in "
        "trên giấy ủy quyền. Không có ủy quyền thì chép y hệt ChuHoSo_HoTen.",
    },
    {
        "name": "NguoiNop_NgaySinh",
        "desc": "Ngày sinh đầy đủ của NGƯỜI NỘP, dd/mm/yyyy. Tự nộp thì giống ChuHoSo_NgaySinh.",
    },
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/định danh của NGƯỜI NỘP, chỉ chữ số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD của NGƯỜI NỘP, dd/mm/yyyy."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp CCCD của NGƯỜI NỘP, đi cùng đúng số và ngày cấp."},
    {
        "name": "NguoiNop_DiaChi",
        "desc": "Nơi THƯỜNG TRÚ của NGƯỜI NỘP, object {quocGia,tinh,xa,chiTietDuoiXa}. Có ủy quyền: dòng 'Thường trú' của "
        "bên được ủy quyền. Tự nộp thì chép nguyên ChuHoSo_DiaChi. KHÔNG lấy địa chỉ thửa đất.",
    },
    {
        "name": "NguoiNop_DienThoai",
        "desc": "Số điện thoại của chính NGƯỜI NỘP, chỉ chữ số. Có ủy quyền: không lấy số ở Đơn mục 1d (của chủ hồ sơ).",
    },
    {"name": "NguoiNop_Email", "desc": "Email của chính NGƯỜI NỘP nếu có."},
    {
        "name": "Don_NoiDungBienDong",
        "desc": "Chép nguyên văn mục '2. Nội dung biến động' của Đơn đăng ký biến động (thường viết tay, vd 'Cấp đổi Giấy "
        "chứng nhận do bị rách'). Mục để trống/dấu chấm thì bỏ field, không bịa.",
    },
    {
        "name": "GCN_SoPhatHanh",
        "desc": "Số phát hành (số serial) của Giấy chứng nhận cần cấp đổi: 2 chữ cái + 6 chữ số in ở góc dưới trang bìa "
        "hoặc dòng 'Số phát hành GCN:' của Trang bổ sung (vd 'AB 123456'). Không lấy số vào sổ cấp GCN ('CH…', "
        "'CS…').",
    },
    {
        "name": "ThuaDat_DiaChi",
        "desc": "ĐỊA CHỈ THỬA ĐẤT, object {quocGia,tinh,xa,chiTietDuoiXa}: Giấy chứng nhận mục 'II.1. Thửa đất – b) Địa "
        "chỉ' (dạng 'Thôn A - Xã B - Nha Trang - Khánh Hòa': cụm cuối là tỉnh, cụm có chữ Xã/Phường là xa, cụm "
        "huyện/thành phố cũ BỎ, phần đầu là chiTietDuoiXa). KHÔNG lấy nơi thường trú của người.",
    },
    {
        "name": "ThuaDat_DiaChiDayDu",
        "desc": "Chép NGUYÊN VĂN dòng 'b) Địa chỉ' của thửa đất trên Giấy chứng nhận (mục II.1), giữ dấu gạch và tên đơn vị "
        "hành chính cũ.",
    },
    {
        "name": "ThuaDat_SoThua",
        "desc": "Số thửa: Giấy chứng nhận 'a) Thửa đất số' hoặc 'Thửa đất số' ở đầu Trang bổ sung. Chỉ lấy số.",
    },
    {
        "name": "ThuaDat_SoTo",
        "desc": "Số tờ bản đồ: Giấy chứng nhận 'tờ bản đồ số' hoặc 'Tờ bản đồ số' ở đầu Trang bổ sung. Chỉ lấy số.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_DiaChi", "NguoiNop_DiaChi", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"
