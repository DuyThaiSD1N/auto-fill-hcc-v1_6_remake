"""Facts nguồn cho "Khánh Hòa - Đính chính Giấy chứng nhận đã cấp" (1.012790).

Đi từ link kê khai DVCQG (chỉ chọn Tỉnh, bấm thẻ Chi nhánh VPĐK đất đai theo xã) sang cổng tỉnh iGate Khánh Hòa, quy
trình 1.012790-1.1. Form Form.io CÙNG template ba khối với cấp đổi GCN Khánh Hòa (file mapping
"Mapping-Dinh-chinh-GCN-Khanh-Hoa.xlsx" trùng khít tập data[...]) nên dùng chung UI_COMP_BY_NAME: Phần I người nộp, Phần
II chủ hồ sơ, Phần III thửa đất. Panel "Thông tin tổ chức" chỉ hiện khi tick radio Tổ chức — không khai.

Nguồn: Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 27), BẢN GỐC Giấy chứng nhận đã cấp, CCCD, Giấy
xác nhận thông tin cư trú, văn bản ủy quyền nếu nộp thay. Bẫy chính của đính chính: Giấy chứng nhận mang thông tin CŨ/SAI
(CMND 9 số, địa chỉ trước sắp xếp, tên viết sai) — ô của form lấy thông tin ĐÚNG hiện tại ở Đơn mục 2 ("từ … sang/thành
…") và CCCD, không chép giá trị sai trên Giấy chứng nhận.
"""

from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.process.schema import UI_COMP_BY_NAME  # noqa: F401

FIELDS: list[dict] = [
    {
        "name": "ChuHoSo_LoaiChuThe",
        "desc": '"Tổ chức" nếu người sử dụng đất là công ty/doanh nghiệp/HTX/cơ quan; "Cá nhân" nếu là một người (kể '
        "cả hộ gia đình, vợ chồng).",
    },
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên CHỦ HỒ SƠ = NGƯỜI SỬ DỤNG ĐẤT đề nghị đính chính, người ĐỨNG ĐẦU ở Đơn mục '1. Người sử dụng đất, "
        "chủ sở hữu tài sản gắn liền với đất, người quản lý đất' – 'a) Tên' (hoặc chữ ghi rõ họ tên dưới 'Người viết "
        "đơn'). Nguồn theo thứ tự: CCCD của đúng người -> Đơn mục 1a -> Giấy chứng nhận mục 'I. Người sử dụng đất…'. Đơn "
        "ghi hai người ('ông A … và vợ là bà B') thì lấy người đứng trước. Chỉ lấy HỌ TÊN (bỏ 'Ông'/'Bà', 'sinh năm'). "
        "Tên ĐÚNG hiện tại: nếu Đơn mục 2 đính chính tên ('từ … thành …') thì lấy tên MỚI. GIỮ NGUYÊN DẤU.",
    },
    {
        "name": "ChuHoSo_NguoiCungSuDung",
        "desc": "Họ tên NGƯỜI CÙNG SỬ DỤNG ĐẤT với chủ hồ sơ (vợ/chồng, thành viên hộ) nếu Đơn mục 1a ghi hai người trở "
        "lên ('ông A và vợ là bà B'); nối bằng '; '. Một người thì bỏ field.",
    },
    {
        "name": "ChuHoSo_NgaySinh",
        "desc": "Ngày sinh đầy đủ của CHỦ HỒ SƠ, dd/mm/yyyy. Nguồn: CCCD -> Giấy xác nhận thông tin cư trú -> Đơn mục 1a. "
        "Đơn và Giấy chứng nhận thường chỉ ghi 'sinh năm'/'Năm sinh' -> chỉ có năm thì bỏ field.",
    },
    {
        "name": "ChuHoSo_SoDinhDanh",
        "desc": "Số CCCD/căn cước/định danh HIỆN TẠI của CHỦ HỒ SƠ (12 chữ số), chỉ chữ số. Nguồn: CCCD -> Đơn mục '1b) "
        "Giấy tờ nhân thân/pháp nhân' ('CCCD số …') -> số MỚI trong Đơn mục 2 ('từ CMND số X sang CCCD số Y' -> Y) -> "
        "Giấy xác nhận cư trú 'Số định danh cá nhân'. KHÔNG lấy số CMND cũ in trên Giấy chứng nhận khi đã có số mới.",
    },
    {
        "name": "ChuHoSo_NgayCap",
        "desc": "Ngày cấp CCCD/căn cước của CHỦ HỒ SƠ, dd/mm/yyyy: thẻ CCCD (mặt sau) hoặc cụm '<số> cấp ngày …' ở Đơn mục "
        "1b. TUYỆT ĐỐI không lấy ngày cấp CMND cũ in trên Giấy chứng nhận, ngày ký GCN, ngày xác nhận thay đổi, ngày "
        "lập đơn.",
    },
    {
        "name": "ChuHoSo_NoiCap",
        "desc": "Cơ quan cấp CCCD/căn cước của CHỦ HỒ SƠ (chức danh ký mặt sau thẻ hoặc chữ 'tại …' ở Đơn mục 1b, vd 'Cục "
        "Cảnh sát quản lý hành chính về trật tự xã hội', 'Bộ Công an'). Không lấy nơi cấp CMND cũ trên Giấy chứng nhận.",
    },
    {
        "name": "ChuHoSo_DiaChi",
        "desc": "Nơi THƯỜNG TRÚ HIỆN TẠI của CHỦ HỒ SƠ, object {quocGia,tinh,xa,chiTietDuoiXa}. Ưu tiên: CCCD 'Nơi thường "
        "trú'/'Nơi cư trú' -> Đơn mục '1c) Địa chỉ' -> Giấy xác nhận cư trú -> địa chỉ MỚI trong Đơn mục 2 ('thay đổi "
        "địa chỉ: từ … thành …' -> phần sau 'thành'). Địa chỉ trên Giấy chứng nhận thường là địa danh CŨ trước sắp xếp — "
        "chỉ dùng khi không còn nguồn nào. KHÔNG lấy địa chỉ thửa đất.",
    },
    {
        "name": "ChuHoSo_DienThoai",
        "desc": "Số điện thoại của CHỦ HỒ SƠ, chỉ chữ số: Đơn mục '1d) Điện thoại liên hệ'.",
    },
    {"name": "ChuHoSo_Email", "desc": "Email của CHỦ HỒ SƠ nếu Đơn mục 1d 'Hộp thư điện tử' có ghi; không có thì bỏ."},
    {
        "name": "NguoiNop_HoTen",
        "desc": "Họ tên NGƯỜI NỘP. Có giấy/hợp đồng ủy quyền cho CÁ NHÂN làm thủ tục đính chính: họ tên BÊN ĐƯỢC ỦY QUYỀN "
        "in trên giấy ủy quyền. Không có ủy quyền thì chép y hệt ChuHoSo_HoTen.",
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
        "desc": "Chép NGUYÊN VĂN, ĐỦ mọi đoạn và gạch đầu dòng của mục '2. Nội dung biến động' trong Đơn (câu đăng ký thay "
        "đổi/đính chính + các dòng '- Thay đổi …: từ … sang/thành …'), giữ xuống dòng giữa các đoạn, không rút gọn. "
        "Dừng trước '3. Giấy tờ liên quan…'. Mục để trống/dấu chấm thì bỏ field, không bịa.",
    },
    {
        "name": "GCN_SoPhatHanh",
        "desc": "Số phát hành (số serial) của Giấy chứng nhận cần đính chính: 2 chữ cái + 6 chữ số in ở góc dưới trang "
        "bìa (vd 'AB 123456') hoặc 'số phát hành' ghi trong Đơn mục 2. Không lấy số vào sổ cấp GCN ('CH…', 'CS…').",
    },
    {
        "name": "GCN_NguoiSuDung",
        "desc": "Họ tên người sử dụng đất IN TRÊN Giấy chứng nhận: mục 'I. Người sử dụng đất…' ('Ông'/'Bà' …), hoặc người "
        "nhận ở dòng chuyển nhượng/tặng cho/thừa kế MỚI NHẤT của 'IV. Những thay đổi sau khi cấp giấy chứng nhận'. Chép "
        "đúng chữ in trên GCN (kể cả khi tên đó đang bị đính chính). TUYỆT ĐỐI không lấy tên ở Đơn (mục 1a, 'Người viết "
        "đơn') — hai tên khác nhau là chứng cứ Đơn và GCN lệch hồ sơ. Không có trang GCN thì bỏ field.",
    },
    {
        "name": "ThuaDat_DiaChi",
        "desc": "ĐỊA CHỈ THỬA ĐẤT, object {quocGia,tinh,xa,chiTietDuoiXa}. Ưu tiên cụm 'địa chỉ thửa đất: …' trong Đơn mục "
        "2 (địa danh mới sau sắp xếp), không có mới lấy Giấy chứng nhận mục 'II. Thửa đất… – Địa chỉ' (dạng 'bản/thôn A, "
        "xã B, huyện C, tỉnh D': huyện/thành phố cũ BỎ). KHÔNG lấy nơi thường trú của người.",
    },
    {
        "name": "ThuaDat_DiaChiDayDu",
        "desc": "Chép NGUYÊN VĂN địa chỉ thửa đất: cụm sau 'địa chỉ thửa đất:' trong Đơn mục 2 (tới dấu ';' hoặc ', đã "
        "được cấp'); Đơn không ghi thì dòng 'Địa chỉ' của thửa đất trên Giấy chứng nhận (mục II).",
    },
    {
        "name": "ThuaDat_SoThua",
        "desc": "Số thửa: 'thửa đất số' trong Đơn mục 2 hoặc Giấy chứng nhận mục II 'a) Thửa đất số'. Chỉ lấy số. Đính "
        "chính chính số thửa ('từ … thành …') thì lấy số MỚI.",
    },
    {
        "name": "ThuaDat_SoTo",
        "desc": "Số tờ bản đồ: 'tờ bản đồ số' trong Đơn mục 2 hoặc Giấy chứng nhận mục II. Chỉ lấy số. Đính chính chính "
        "số tờ thì lấy số MỚI.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_DiaChi", "NguoiNop_DiaChi", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"
