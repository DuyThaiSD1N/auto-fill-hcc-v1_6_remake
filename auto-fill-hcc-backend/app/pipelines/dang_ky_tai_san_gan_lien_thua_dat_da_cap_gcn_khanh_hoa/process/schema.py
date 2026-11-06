"""Facts nguồn cho "Khánh Hòa - Đăng ký tài sản gắn liền với thửa đất đã được cấp Giấy chứng nhận hoặc đăng ký thay đổi về
tài sản gắn liền với đất…" (1.013995).

Đi từ link kê khai DVCQG (chỉ chọn Tỉnh, bấm thẻ Chi nhánh VPĐK đất đai theo xã) sang cổng tỉnh iGate Khánh Hòa: trang
"Chọn trường hợp giải quyết" ra 4 quy trình (1.013995-1.1/1.2 đăng ký quyền sở hữu tài sản, -2.1/2.2 đăng ký thay đổi về
tài sản) rồi tới form Form.io CÙNG TEMPLATE ba khối với cấp đổi GCN / đăng ký biến động Khánh Hòa (file mapping
1.013995-1.1 trùng khít tập data[...]) nên dùng chung UI_COMP_BY_NAME. Panel "Thông tin tổ chức" chỉ hiện khi tick radio
data[CaNhan_ToChuc][<hậu tố ngẫu nhiên>] = Tổ chức — không điền được theo tên nên không khai.

Nguồn (thứ tự ưu tiên theo file mapping): CCCD -> Đơn đăng ký biến động Mẫu số 18 -> tờ khai lệ phí trước bạ (01/LPTB)
-> Giấy chứng nhận đã cấp -> giấy phép xây dựng -> hồ sơ thiết kế xin phép xây dựng -> biên lai/giấy nộp tiền. Bẫy chính:
hồ sơ thường có HAI đồng chủ (vợ chồng) mà form chỉ có một chủ hồ sơ; giấy phép xây dựng, hồ sơ thiết kế, biên lai cũ
ghi địa danh/địa chỉ CŨ; mục 1 của Giấy chứng nhận có thể là chủ cũ khi phần "Những thay đổi" có dòng tặng cho/chuyển
nhượng mới hơn.
"""

from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.process.schema import UI_COMP_BY_NAME  # noqa: F401

FIELDS: list[dict] = [
    {
        "name": "ChuHoSo_LoaiChuThe",
        "desc": '"Tổ chức" nếu người đứng Đơn là công ty/doanh nghiệp/HTX/cơ quan; "Cá nhân" nếu là người (kể cả vợ '
        "chồng cùng đứng tên).",
    },
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên CHỦ HỒ SƠ = NGƯỜI THỨ NHẤT đứng Đơn đăng ký biến động mục '1. Người sử dụng đất, chủ sở hữu tài "
        "sản gắn liền với đất…' (dòng '1.1. Tên' hoặc 'a) Tên'). Nguồn theo thứ tự: CCCD của đúng người -> Đơn -> tờ khai "
        "lệ phí trước bạ [04] Người nộp thuế (tên ĐẦU TIÊN) -> Giấy chứng nhận: người NHẬN ở dòng tặng cho/chuyển "
        "nhượng MỚI NHẤT của phần 'Những thay đổi sau khi cấp Giấy chứng nhận', không có dòng đó thì mục '1. Người sử "
        "dụng đất…' -> giấy phép xây dựng '1. Cấp cho' -> hồ sơ thiết kế 'Chủ sở hữu'. Chỉ lấy HỌ TÊN (bỏ 'Ông'/'Bà', "
        "số CCCD viết liền sau), GIỮ NGUYÊN DẤU.",
    },
    {
        "name": "ChuHoSo_NguoiCungSuDung",
        "desc": "Họ tên NGƯỜI THỨ HAI trở đi cùng đứng tên (Đơn '1.2. Tên', 'Và vợ: Bà …', tờ khai [04] ghi hai tên), "
        "nối bằng '; '. Một người thì bỏ field.",
    },
    {
        "name": "ChuHoSo_NgaySinh",
        "desc": "Ngày sinh đầy đủ của CHỦ HỒ SƠ, dd/mm/yyyy, CHỈ từ thẻ CCCD của đúng người hoặc Đơn ghi đủ 'sinh ngày …'. "
        "Giấy chỉ ghi năm sinh, hoặc chỉ suy được năm từ số CCCD thì bỏ field, không bịa 01/01.",
    },
    {
        "name": "ChuHoSo_SoDinhDanh",
        "desc": "Số CCCD/căn cước/định danh của CHỦ HỒ SƠ, chỉ chữ số: CCCD -> Đơn '1.1. … Số CCCD' -> tờ khai [06] (số "
        "ĐẦU TIÊN khi ghi hai số) -> 'CCCD:' cạnh tên ở Giấy chứng nhận. Đơn đánh máy có thể lặp số ('Số CCCD: X X'): "
        "chỉ lấy một số khớp các giấy khác.",
    },
    {
        "name": "ChuHoSo_NgayCap",
        "desc": "Ngày cấp CCCD/căn cước của CHỦ HỒ SƠ, dd/mm/yyyy: thẻ CCCD (mặt sau) -> cụm 'cấp ngày …' ngay sau số "
        "CCCD của CHÍNH người này trên Đơn. TUYỆT ĐỐI không lấy ngày cấp Giấy chứng nhận, ngày cấp giấy phép xây dựng, "
        "ngày lập đơn.",
    },
    {
        "name": "ChuHoSo_NoiCap",
        "desc": "Cơ quan cấp CCCD/căn cước của CHỦ HỒ SƠ: thẻ CCCD -> cụm 'do … cấp' của CHÍNH người này trên Đơn (vd "
        "'Cục Cảnh sát quản lý hành chính về trật tự xã hội').",
    },
    {
        "name": "ChuHoSo_DiaChi",
        "desc": "Nơi THƯỜNG TRÚ hiện tại của CHỦ HỒ SƠ, object {quocGia,tinh,xa,chiTietDuoiXa}. Ưu tiên: CCCD -> Đơn 'Địa "
        "chỉ thường trú'/'Địa chỉ' -> tờ khai [07] Địa chỉ -> 'cùng trú tại' ở dòng thay đổi của Giấy chứng nhận. Giấy "
        "phép xây dựng, biên lai thuế cũ ghi địa chỉ/phường CŨ: chỉ dùng khi không còn nguồn nào. KHÔNG lấy địa chỉ "
        "thửa đất.",
    },
    {
        "name": "ChuHoSo_DienThoai",
        "desc": "Số điện thoại của CHỦ HỒ SƠ, chỉ chữ số: Đơn 'Điện thoại liên hệ' -> tờ khai [10] Điện thoại. KHÔNG lấy "
        "số ghi trên giấy phép xây dựng, biên lai (giấy cũ, có thể đã đổi số).",
    },
    {"name": "ChuHoSo_Email", "desc": "Email của CHỦ HỒ SƠ: Đơn 'Hộp thư điện tử' -> tờ khai [12] Email. Trống thì bỏ."},
    {
        "name": "NguoiNop_HoTen",
        "desc": "Họ tên NGƯỜI NỘP. Có văn bản ủy quyền/đại diện cho CÁ NHÂN làm thủ tục: họ tên BÊN ĐƯỢC ỦY QUYỀN in trên "
        "văn bản đó. Không có ủy quyền thì chép y hệt ChuHoSo_HoTen (người thứ hai đứng Đơn KHÔNG phải người nộp).",
    },
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh đầy đủ của NGƯỜI NỘP, dd/mm/yyyy. Tự nộp thì giống chủ hồ sơ."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/định danh của NGƯỜI NỘP, chỉ chữ số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD của NGƯỜI NỘP, dd/mm/yyyy."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp CCCD của NGƯỜI NỘP, đi cùng đúng số và ngày cấp."},
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
        "desc": "Chép NGUYÊN VĂN, ĐẦY ĐỦ mục 'Nội dung biến động' của Đơn (vd 'Bổ sung tài sản gắn liền với đất.' kèm các "
        "dòng '- Giấy chứng nhận đã cấp; Giấy phép xây dựng số …' liệt kê giấy tờ), giữ xuống dòng, dừng trước câu 'Cam "
        "đoan…'/'Tôi cam đoan…'. Không diễn đạt lại, không sửa số giấy phép. Mục để trống thì bỏ field.",
    },
    {
        "name": "ThuaDat_DiaChi",
        "desc": "ĐỊA CHỈ THỬA ĐẤT, object {quocGia,tinh,xa,chiTietDuoiXa}, xa là phường/xã HIỆN HÀNH: tờ khai lệ phí "
        "trước bạ '1.2. Địa chỉ thửa đất' (+ 1.2.2 Phường/xã, 1.2.4 Tỉnh) -> Giấy chứng nhận dòng 'Địa chỉ' của thửa đất "
        "('e. Địa chỉ' mẫu mới, 'II.1 b) Địa chỉ' mẫu cũ) -> giấy phép xây dựng 'Vị trí xây dựng' -> hồ sơ thiết kế 'Địa "
        "chỉ'/'Địa điểm'. KHÔNG lấy nơi thường trú của người.",
    },
    {
        "name": "ThuaDat_DiaChiDayDu",
        "desc": "Địa chỉ thửa đất dạng chữ, chép NGUYÊN VĂN theo nguồn địa danh mới nhất: tờ khai '1.2. Địa chỉ thửa đất' "
        "-> dòng 'Địa chỉ' của thửa đất trên Giấy chứng nhận. Không chép địa chỉ còn tên phường/thành phố cũ khi đã có "
        "nguồn ghi địa danh mới.",
    },
    {
        "name": "ThuaDat_SoThua",
        "desc": "Số thửa: tờ khai '1.1. Thửa đất số' -> Giấy chứng nhận 'Thửa đất số' -> giấy phép xây dựng 'thửa đất số'. "
        "Chỉ lấy số. Không lấy số thửa liền kề ghi trong sơ đồ/bản vẽ ('Thửa 401', 'Thửa 429').",
    },
    {
        "name": "ThuaDat_SoTo",
        "desc": "Số tờ bản đồ: tờ khai '1.1. Tờ bản đồ số' -> Giấy chứng nhận 'tờ bản đồ số' -> giấy phép xây dựng. Chỉ "
        "lấy số.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_DiaChi", "NguoiNop_DiaChi", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"
