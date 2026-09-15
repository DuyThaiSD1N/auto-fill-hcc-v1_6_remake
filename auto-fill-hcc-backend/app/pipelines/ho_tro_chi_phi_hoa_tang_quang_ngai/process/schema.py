"""Facts nguồn cho thủ tục hỗ trợ chi phí khuyến khích sử dụng hình thức hỏa táng (Quảng Ngãi).

Form Form.io của cổng dichvucong.quangngai.gov.vn dùng CHUNG một template 23 ô data[...] cho nhiều
thủ tục (đã grep 'quảng ngãi khuyến khích hoả táng fill.html': đúng 23 name, nhãn trùng khít bản
'giao đất fill.html'). Vì là template dùng chung nên:
  - KHÔNG có khối riêng cho người nộp: ô DUY NHẤT của người nộp là data[fullname] ("Họ và tên người
    nộp hồ sơ"); toàn bộ panel "Thông tin chung" (ngày sinh, giới tính, email, số điện thoại, số
    định danh, ngày/nơi cấp, quốc gia/tỉnh/phường/địa chỉ) là của CHỦ HỒ SƠ.
  - data[ProcedureDossierQuantity] ("Số bộ hồ sơ", portal để sẵn "1") và data[hinhThucNop] ("Hình
    thức nộp hồ sơ", portal chọn sẵn "Trực tuyến") là field HÀNH CHÍNH của cổng, không đọc được từ
    giấy tờ người dân -> KHÔNG khai trong UI_COMP_BY_NAME để mapper không bao giờ phát (chống bịa).
  - KHỐI "Địa chỉ thửa đất/ địa chỉ xây dựng" (data[diaChiThuaDat], data[province2], data[village2],
    data[nation2]) là panel THỪA của template đất đai/xây dựng. Thủ tục hỏa táng KHÔNG phát sinh
    thửa đất -> cố ý KHÔNG khai 4 ô này, để không có đường nào nhét nhầm nơi cư trú hay địa điểm
    cơ sở hỏa táng vào đó (bảng MAPPING của thủ tục cũng ghi "để trống toàn bộ panel").

Ba người xuất hiện trong hồ sơ hỏa táng nhưng form CHỈ có hai vai:
  - CHỦ HỒ SƠ  = người đứng Tờ khai đề nghị hỗ trợ (thân nhân đứng ra lo hỏa táng, nhận tiền hỗ trợ).
  - NGƯỜI NỘP  = bên được ủy quyền/người được giới thiệu đi nộp thay; không có ủy quyền thì trùng
    chủ hồ sơ.
  - NGƯỜI CHẾT (người được hỏa táng) chỉ là dữ kiện nghiệp vụ, form KHÔNG có ô nào -> cố ý KHÔNG
    khai field NguoiChet_* để không có chỗ nào lỡ đẩy người chết lên hai vai trên (prompt có rule
    loại trừ tường minh).
"""

FIELDS: list[dict] = [
    {
        "name": "ChuHoSo_HoTen",
        "desc": (
            "Họ tên CHỦ HỒ SƠ = người đứng tên Tờ khai đề nghị hỗ trợ chi phí khuyến khích sử dụng "
            "hình thức hỏa táng (Mẫu số 01 dành cho cá nhân hoặc Mẫu số 02 dành cho cơ quan, tổ "
            "chức) — thân nhân đứng ra lo việc hỏa táng và đứng tên nhận tiền hỗ trợ. Ưu tiên mục "
            "'Tên tôi là'/'Họ và tên' ở đầu Tờ khai và dòng ký tên cuối Tờ khai. TUYỆT ĐỐI KHÔNG "
            "lấy NGƯỜI CHẾT (người được hỏa táng, người có tên trên Trích lục khai tử/Giấy báo tử) "
            "làm chủ hồ sơ."
        ),
    },
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh đầy đủ của CHỦ HỒ SƠ, dd/mm/yyyy. Ưu tiên CCCD đúng người, sau đó Tờ khai; văn bản ủy quyền thường chỉ ghi 'Sinh năm' nên chỉ dùng khi có đủ ngày-tháng. Chỉ có năm sinh thì bỏ field."},
    {"name": "ChuHoSo_GioiTinh", "desc": "Giới tính CHỦ HỒ SƠ: Nam/Nữ. Chỉ suy từ danh xưng gắn trực tiếp với chính người đó: Ông=Nam, Bà=Nữ; không suy từ tên."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/CMND/định danh của CHỦ HỒ SƠ, chỉ chữ số, giữ nguyên các số 0 ở đầu. Thuộc tính phải đi đúng người; không lấy số định danh của người chết trên Trích lục khai tử."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp giấy tờ định danh của CHỦ HỒ SƠ, dd/mm/yyyy, đi cùng đúng số giấy tờ. KHÔNG lấy ngày cấp Trích lục khai tử/Giấy báo tử, không lấy ngày lập Tờ khai hay ngày ký hợp đồng."},
    {"name": "ChuHoSo_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh của CHỦ HỒ SƠ, lấy cùng giấy tờ với số và ngày cấp. KHÔNG lấy cơ quan cấp Trích lục khai tử."},
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": (
            "NƠI CƯ TRÚ (thường trú) của CHỦ HỒ SƠ, object {quocGia,tinh,xa,diaChi}. Nguồn ưu tiên: "
            "mục 'Thường trú tại'/'Nơi cư trú' trên Tờ khai đề nghị -> địa chỉ đầy đủ trên CCCD đúng "
            "người -> địa chỉ ghi trong văn bản ủy quyền (thường bị rút gọn, chỉ dùng khi không có "
            "nguồn nào khác). Giữ đủ tổ dân phố/thôn/xóm/số nhà trong diaChi. ĐÂY KHÔNG PHẢI địa chỉ "
            "cơ sở hỏa táng và KHÔNG PHẢI nơi thường trú của người chết."
        ),
    },
    {
        "name": "ChuHoSo_DienThoai",
        "desc": (
            "Số điện thoại liên hệ của CHỦ HỒ SƠ, chỉ chữ số. PHẢI lấy khi hồ sơ có: mục 'Điện thoại "
            "liên hệ'/'Số điện thoại' trên Tờ khai đề nghị hỗ trợ; thông tin liên hệ của BÊN A (đại "
            "diện gia đình tang chủ) trên Hợp đồng dịch vụ hỏa táng; thông tin liên hệ trong văn bản "
            "ủy quyền. Số ghi trong tờ khai do chính người đó đứng tên mặc nhiên là số của người đó. "
            "KHÔNG lấy số tài khoản ngân hàng làm số điện thoại và KHÔNG lấy số điện thoại/đường dây "
            "nóng của cơ sở hỏa táng (bên B của hợp đồng, đơn vị phát hành hóa đơn)."
        ),
    },
    {"name": "ChuHoSo_Email", "desc": "Email của CHỦ HỒ SƠ nếu hồ sơ ghi rõ; không tự tạo."},
    {
        "name": "NguoiNop_HoTen",
        "desc": (
            "Họ tên NGƯỜI NỘP. Có văn bản ủy quyền được chứng thực hoặc giấy giới thiệu của cơ quan, "
            "tổ chức thì bắt buộc lấy BÊN ĐƯỢC ỦY QUYỀN/người được giới thiệu; không có thì người "
            "nộp chính là CHỦ HỒ SƠ. Không lấy người chết, không lấy cán bộ chứng thực, không lấy "
            "nhân viên cơ sở hỏa táng."
        ),
    },
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh đầy đủ của NGƯỜI NỘP, dd/mm/yyyy. Ưu tiên CCCD đúng người; chỉ có năm sinh thì bỏ field, không tự đặt ngày/tháng."},
    {
        "name": "NguoiNop_GioiTinh",
        "desc": (
            "Giới tính NGƯỜI NỘP: Nam/Nữ. Chỉ suy từ danh xưng gắn trực tiếp với chính người đó: "
            "Ông=Nam, Bà=Nữ; không suy từ tên. Danh xưng có thể nằm ở mục 'BÊN ĐƯỢC ỦY QUYỀN', dòng "
            "ký tên, hoặc danh sách người ký trong phần LỜI CHỨNG THỰC cuối văn bản ủy quyền "
            "('2. Ông: <họ tên> - Giấy tờ tùy thân: <số>') — phần chứng thực vẫn là nguồn hợp lệ để "
            "lấy thuộc tính của bên được ủy quyền."
        ),
    },
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND/định danh của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền phải lấy của BÊN ĐƯỢC ỦY QUYỀN."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp giấy tờ định danh của NGƯỜI NỘP, dd/mm/yyyy, đi cùng đúng số giấy tờ."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh của NGƯỜI NỘP, đi cùng đúng số và ngày cấp."},
    {
        "name": "NguoiNop_NoiCuTru",
        "desc": (
            "NƠI CƯ TRÚ của NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi}. Không có ủy quyền thì sao "
            "chép NGUYÊN VẸN ChuHoSo_NoiCuTru, gồm cả tổ dân phố/thôn/số nhà trong diaChi. Có ủy "
            "quyền thì lấy nơi cư trú của BÊN ĐƯỢC ỦY QUYỀN."
        ),
    },
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền thì lấy số của BÊN ĐƯỢC ỦY QUYỀN ghi trên văn bản ủy quyền/giấy giới thiệu hoặc trên CCCD đúng người; không có ủy quyền thì người nộp chính là chủ hồ sơ. Không lấy số của người khác, không lấy số tài khoản ngân hàng."},
    {"name": "NguoiNop_Email", "desc": "Email của NGƯỜI NỘP nếu hồ sơ ghi rõ; không tự tạo."},
    {
        "name": "ChuHoSo_DonDiaChi",
        "desc": "ĐỊA CHỈ CỦA CHỦ HỒ SƠ GHI TRÊN ĐƠN/TỜ KHAI — object {quocGia,tinh,xa,diaChi}. CHỈ lấy từ mục 'Địa chỉ' trong khối người đề nghị/người sử dụng đất của Tờ khai đề nghị hỗ trợ chi phí hỏa táng (Mẫu số 01/Mẫu số 02); nhận BẤT KỲ mẫu nào thực tế có trong hồ sơ. TUYỆT ĐỐI KHÔNG lấy từ CCCD/CMND, Giấy chứng nhận, công văn hay giấy tờ khác; đơn không ghi thì BỎ FIELD, không thay bằng nguồn khác. Dòng địa chỉ trên đơn thường viết LIỀN, không nhãn con, dạng '<số nhà/đường/tổ/thôn>, <xã/phường> <tỉnh/thành phố>': tách bằng cách lấy cụm CUỐI làm tinh, cụm ngay TRƯỚC nó làm xa (thêm tiền tố 'Phường'/'Xã' nếu đơn viết trống), phần còn lại cho vào diaChi.",
    },
    {
        "name": "NguoiNop_DonDiaChi",
        "desc": "ĐỊA CHỈ CỦA NGƯỜI NỘP GHI TRÊN GIẤY TỜ NGƯỜI DÂN LẬP — object {quocGia,tinh,xa,diaChi}. Có văn bản ủy quyền/đại diện thì lấy địa chỉ của BÊN ĐƯỢC ỦY QUYỀN ghi trong chính văn bản đó; KHÔNG có ủy quyền thì chép nguyên vẹn ChuHoSo_DonDiaChi. TUYỆT ĐỐI KHÔNG lấy từ CCCD/CMND hay Giấy chứng nhận; không có nguồn thì BỎ FIELD. Cách tách chuỗi địa chỉ viết liền giống ChuHoSo_DonDiaChi.",
    },
    {
        "name": "Don_NoiDungDeNghi",
        "desc": (
            "Nội dung ĐỀ NGHỊ người dân khai trên Tờ khai đề nghị hỗ trợ chi phí khuyến khích sử "
            "dụng hình thức hỏa táng (câu 'đề nghị ... xem xét, hỗ trợ ...' ở cuối tờ khai, kèm cơ "
            "quan được đề nghị nếu tờ khai ghi). Chép NGUYÊN VĂN phần người dân khai. KHÔNG lấy tiêu "
            "đề thủ tục trên cổng thay nội dung tờ khai, KHÔNG tự suy diễn, KHÔNG tự ghép thông tin "
            "người chết vào."
        ),
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru", "ChuHoSo_DonDiaChi", "NguoiNop_DonDiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# CHỈ các ô thực sự dùng cho thủ tục hỏa táng trên 'quảng ngãi khuyến khích hoả táng fill.html'.
# Cố ý KHÔNG khai (xem docstring): data[ProcedureDossierQuantity], data[hinhThucNop] và cả khối thửa
# đất data[diaChiThuaDat]/data[province2]/data[village2]/data[nation2].
UI_COMP_BY_NAME = {
    "data[ownerFullname]": "dom-input",
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[email]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[phoneNumber1]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[chonDoiTuong]": "dom-select",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    "data[note]": "dom-input",
    "data[noidungyeucaugiaiquyet]": "dom-input",
}
