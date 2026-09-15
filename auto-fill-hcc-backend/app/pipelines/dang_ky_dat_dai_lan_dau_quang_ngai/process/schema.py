"""Facts nguồn cho thủ tục đăng ký đất đai, cấp Giấy chứng nhận LẦN ĐẦU tại Quảng Ngãi.

Form Form.io của cổng dichvucong.quangngai.gov.vn dùng ĐÚNG CÙNG TEMPLATE 23 ô data[...] với thủ tục
"Giao đất, cho thuê đất, chuyển mục đích sử dụng đất" của cùng cổng (đã grep 'đki dd fill.html': tập
data[...] trùng khít 100%). Vì vậy khối nguồn/mapper bám nguyên bản Quảng Ngãi giao đất, KHÁC hẳn bản
Ninh Bình cùng tên thủ tục:
  - KHÔNG có data[isOwnerDossier], data[organization], data[hoTen], data[soCCCD], data[diaChi]
    (đó là ô của cổng Ninh Bình) -> mapper không phát các ô này.
  - CÓ data[phoneNumber1] ("Số điện thoại ủy quyền") và KHỐI THỬA ĐẤT gồm data[diaChiThuaDat] +
    data[province2] + data[village2] + data[nation2] (panel "Địa chỉ thửa đất/ địa chỉ xây dựng").
  - data[ProcedureDossierQuantity] ("Số bộ hồ sơ", portal để sẵn "1") và data[hinhThucNop] ("Hình
    thức nộp hồ sơ", portal chọn sẵn "Trực tuyến") là field HÀNH CHÍNH của cổng, KHÔNG đọc được từ
    giấy tờ người dân -> KHÔNG khai trong UI_COMP_BY_NAME để mapper không bao giờ phát (chống bịa).
  - data[district2] có div nhưng RỖNG (formio-hidden, cấp huyện đã bỏ theo mô hình 2 cấp) -> không khai.

Vai trên cổng này chỉ có ĐÚNG MỘT ô của người nộp là data[fullname] ("Họ và tên người nộp hồ sơ");
toàn bộ panel "Thông tin chung" còn lại là của CHỦ HỒ SƠ (xem mapper.owner_val).
"""

FIELDS: list[dict] = [
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên CHỦ HỒ SƠ = người sử dụng đất/chủ sở hữu tài sản gắn liền với đất đứng Đơn đăng ký đất đai (Mẫu số 15), mục '1. Người sử dụng đất, chủ sở hữu tài sản gắn liền với đất, người quản lý đất' – tiểu mục 'Họ và tên'. Thiếu thì lấy BÊN ỦY QUYỀN/người được đại diện, rồi người đứng đầu Danh sách người sử dụng chung (Mẫu số 15a), rồi người nộp thuế trên tờ khai thuế/lệ phí trước bạ. Hộ gia đình/cộng đồng dân cư thì lấy người đại diện đứng đơn. KHÔNG lấy người đồng sử dụng thứ hai trở đi làm chủ chính.",
    },
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh đầy đủ của CHỦ HỒ SƠ, dd/mm/yyyy. Ưu tiên CCCD/thẻ căn cước đúng người, rồi giấy xác nhận thông tin về cư trú/xác nhận số định danh. Danh sách Mẫu số 15a thường chỉ ghi NĂM sinh -> chỉ có năm thì bỏ field."},
    {"name": "ChuHoSo_GioiTinh", "desc": "Giới tính CHỦ HỒ SƠ: Nam/Nữ. Chỉ suy từ danh xưng gắn trực tiếp với chính người đó (Ông=Nam, Bà=Nữ) hoặc mục 'Giới tính'/'Sex' trên giấy tờ tùy thân của đúng người đó; không suy từ tên."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số định danh cá nhân/CCCD/CMND/mã số thuế của CHỦ HỒ SƠ, chỉ chữ số. Nguồn: CCCD của đúng người; Đơn Mẫu số 15 mục 'Giấy tờ nhân thân/pháp nhân'; Mẫu số 15a cột 'Số' giấy tờ; ô 'Số CMND/CCCD/Hộ chiếu' trên tờ khai thuế/lệ phí trước bạ. Thuộc tính phải đi đúng người."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp GIẤY TỜ TÙY THÂN của CHỦ HỒ SƠ, dd/mm/yyyy. Ưu tiên CCCD đúng người, rồi cột 'Ngày, tháng, năm cấp' của Mẫu số 15a, rồi ô 'Ngày cấp' trên tờ khai thuế. TUYỆT ĐỐI không lấy ngày cấp Giấy chứng nhận, ngày lập đơn hay ngày đo đạc."},
    {"name": "ChuHoSo_NoiCap", "desc": "Cơ quan cấp giấy tờ tùy thân của CHỦ HỒ SƠ, lấy CÙNG giấy tờ với số và ngày cấp (mặt sau CCCD, cột 'Cơ quan cấp' của Mẫu số 15a, ô 'Nơi cấp' trên tờ khai thuế)."},
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": "NƠI CƯ TRÚ (thường trú/chỗ ở) của CHỦ HỒ SƠ, object {quocGia,tinh,xa,diaChi}. Nguồn ưu tiên: mục 'Địa chỉ' của người sử dụng đất trên ĐƠN/TỜ KHAI người dân lập (nhận BẤT KỲ mẫu nào thực tế có trong hồ sơ: Mẫu số 15, Mẫu số 18, đơn đề nghị... — không đòi đúng một số hiệu mẫu) -> giấy xác nhận cư trú/xác nhận số định danh mới nhất -> ô 'Địa chỉ'/'Địa chỉ chỗ ở hiện tại' trên tờ khai thuế, lệ phí trước bạ -> CUỐI CÙNG mới đến CCCD. CCCD hay ghi nơi thường trú CŨ/khác tỉnh: hễ đơn đã ghi địa chỉ thì phải theo đơn, không để thẻ ghi đè. Giữ đủ số nhà/đường/tổ/thôn trong diaChi. Giấy tờ tùy thân cũ có thể còn ghi đơn vị hành chính TRƯỚC sắp xếp — nếu đơn/giấy xác nhận mới hơn ghi khác thì theo giấy tờ MỚI. ĐÂY KHÔNG PHẢI địa chỉ thửa đất — tuyệt đối không lấy nhầm địa điểm thửa đất đăng ký.",
    },
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại liên hệ của CHỦ HỒ SƠ (người sử dụng đất), chỉ chữ số. PHẢI lấy khi hồ sơ có: mục 'Điện thoại liên hệ' của Đơn đăng ký đất đai Mẫu số 15, ô 'Điện thoại' trên tờ khai thuế sử dụng đất nông nghiệp/phi nông nghiệp, tờ khai thuế thu nhập cá nhân, tờ khai lệ phí trước bạ. Số ghi trong đơn/tờ khai do chính người đó đứng tên mặc nhiên là số của người đó. Nếu một ô ghi NHIỀU số thì lấy số xuất hiện ở nhiều giấy tờ nhất làm số chính. Không dùng số của người khác."},
    {"name": "ChuHoSo_Email", "desc": "Email (hộp thư điện tử) của CHỦ HỒ SƠ nếu giấy tờ có ghi; đơn thường bỏ trống mục này -> không có thì bỏ field."},
    {"name": "NguoiNop_HoTen", "desc": "Họ tên NGƯỜI NỘP hồ sơ. Có văn bản ủy quyền/văn bản về việc đại diện thì bắt buộc lấy BÊN ĐƯỢC ỦY QUYỀN/người đại diện; không có văn bản đó thì người nộp CHÍNH LÀ chủ hồ sơ."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh đầy đủ của NGƯỜI NỘP, dd/mm/yyyy. Ưu tiên CCCD đúng người; chỉ có năm sinh thì bỏ field, không tự đặt ngày/tháng."},
    {
        "name": "NguoiNop_GioiTinh",
        "desc": "Giới tính NGƯỜI NỘP: Nam/Nữ. Chỉ suy từ danh xưng gắn trực tiếp với chính người đó: Ông=Nam, Bà=Nữ; không suy từ tên. Danh xưng có thể nằm ở mục 'BÊN ĐƯỢC ỦY QUYỀN'/'Người đại diện', dòng ký tên, hoặc danh sách người ký trong phần LỜI CHỨNG THỰC cuối văn bản ủy quyền ('3. Bà: <họ tên> - Giấy tờ tùy thân: <số>') — phần chứng thực vẫn là nguồn hợp lệ để lấy thuộc tính của bên được ủy quyền.",
    },
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND/định danh của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền phải lấy của BÊN ĐƯỢC ỦY QUYỀN."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp giấy tờ tùy thân của NGƯỜI NỘP, dd/mm/yyyy, đi cùng đúng số giấy tờ."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp giấy tờ tùy thân của NGƯỜI NỘP, đi cùng đúng số và ngày cấp."},
    {
        "name": "NguoiNop_NoiCuTru",
        "desc": "NƠI CƯ TRÚ của NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi}. Không có ủy quyền/văn bản đại diện thì sao chép NGUYÊN VẸN ChuHoSo_NoiCuTru, gồm cả số nhà/thôn trong diaChi. Có ủy quyền thì lấy nơi cư trú của BÊN ĐƯỢC ỦY QUYỀN. ĐÂY KHÔNG PHẢI địa chỉ thửa đất.",
    },
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền thì lấy số của BÊN ĐƯỢC ỦY QUYỀN ghi trên văn bản ủy quyền/văn bản đại diện; không có ủy quyền thì người nộp chính là chủ hồ sơ nên dùng số liên hệ trên Đơn Mẫu số 15/tờ khai thuế. Không lấy số của chủ hồ sơ khi hai người thực sự khác nhau."},
    {"name": "NguoiNop_Email", "desc": "Email của NGƯỜI NỘP nếu có."},
    {
        "name": "ChuHoSo_DonDiaChi",
        "desc": "ĐỊA CHỈ CỦA CHỦ HỒ SƠ GHI TRÊN ĐƠN/TỜ KHAI — object {quocGia,tinh,xa,diaChi}. CHỈ lấy từ mục 'Địa chỉ' trong khối người đề nghị/người sử dụng đất của Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 15, Mẫu số 18...); nhận BẤT KỲ mẫu nào thực tế có trong hồ sơ. TUYỆT ĐỐI KHÔNG lấy từ CCCD/CMND, Giấy chứng nhận, công văn hay giấy tờ khác; đơn không ghi thì BỎ FIELD, không thay bằng nguồn khác. Dòng địa chỉ trên đơn thường viết LIỀN, không nhãn con, dạng '<số nhà/đường/tổ/thôn>, <xã/phường> <tỉnh/thành phố>': tách bằng cách lấy cụm CUỐI làm tinh, cụm ngay TRƯỚC nó làm xa (thêm tiền tố 'Phường'/'Xã' nếu đơn viết trống), phần còn lại cho vào diaChi.",
    },
    {
        "name": "NguoiNop_DonDiaChi",
        "desc": "ĐỊA CHỈ CỦA NGƯỜI NỘP GHI TRÊN GIẤY TỜ NGƯỜI DÂN LẬP — object {quocGia,tinh,xa,diaChi}. Có văn bản ủy quyền/đại diện thì lấy địa chỉ của BÊN ĐƯỢC ỦY QUYỀN ghi trong chính văn bản đó; KHÔNG có ủy quyền thì chép nguyên vẹn ChuHoSo_DonDiaChi. TUYỆT ĐỐI KHÔNG lấy từ CCCD/CMND hay Giấy chứng nhận; không có nguồn thì BỎ FIELD. Cách tách chuỗi địa chỉ viết liền giống ChuHoSo_DonDiaChi.",
    },
    {
        "name": "Don_NoiDungDangKy",
        "desc": "Nội dung ĐỀ NGHỊ của Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 15), mục 'Đề nghị của người sử dụng đất, chủ sở hữu tài sản gắn liền với đất' (các ý: đề nghị đăng ký đất đai/tài sản gắn liền với đất; đề nghị CẤP GIẤY CHỨNG NHẬN quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất; đề nghị ghi nợ tiền sử dụng đất; đề nghị khác). Chép NGUYÊN VĂN ý người dân đã tích/ghi; nhiều ý thì nối bằng dấu chấm phẩy. Nếu đơn không tích ý nào thì mô tả gọn theo phần kê khai thửa đất/tài sản trong chính đơn. KHÔNG lấy tiêu đề thủ tục trên cổng thay nội dung đơn; ĐÂY KHÔNG PHẢI nội dung đăng ký biến động, đính chính hay cấp đổi Giấy chứng nhận.",
    },
    {
        "name": "ThuaDat_DiaChi",
        "desc": "ĐỊA CHỈ THỬA ĐẤT/địa chỉ xây dựng đăng ký (địa điểm khu đất, KHÔNG phải nơi cư trú), object {quocGia,tinh,xa,diaChi}. Nguồn ưu tiên: mục 'Địa chỉ' của phần 'Thửa đất đăng ký' trên Đơn đăng ký đất đai Mẫu số 15 -> mục 'Địa chỉ thửa đất' trên Mảnh trích đo/Phiếu xác nhận kết quả đo đạc hiện trạng thửa đất -> ô 'Địa chỉ thửa đất' trên tờ khai thuế sử dụng đất phi nông nghiệp/thuế thu nhập cá nhân/lệ phí trước bạ. Giữ số thửa/tờ bản đồ/đường/tổ/thôn trong diaChi nếu tài liệu ghi kèm địa chỉ. TUYỆT ĐỐI không lấy địa chỉ cư trú/thường trú của chủ hồ sơ hoặc người nộp làm địa chỉ thửa đất. Không có nguồn ghi rõ thì bỏ field.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru", "ThuaDat_DiaChi", "ChuHoSo_DonDiaChi", "NguoiNop_DonDiaChi"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"

# CHỈ các ô có mặt trong 'đki dd fill.html' (23 ô data[...], trừ 2 ô hành chính). Cố ý KHÔNG khai:
#   - data[ProcedureDossierQuantity] (Số bộ hồ sơ, portal đã để "1")
#   - data[hinhThucNop] (Hình thức nộp hồ sơ, portal chọn sẵn)
# vì đây là field hành chính của cổng, không đọc được từ giấy tờ người dân (chống bịa).
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
    # Khối THỬA ĐẤT (panel "Địa chỉ thửa đất/ địa chỉ xây dựng"), tách hẳn khối địa chỉ cư trú ở trên.
    "data[diaChiThuaDat]": "dom-input",
    "data[province2]": "dom-select",
    "data[village2]": "dom-select",
    "data[nation2]": "dom-select",
}
