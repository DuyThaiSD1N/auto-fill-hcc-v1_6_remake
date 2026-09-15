"""Facts nguồn cho thủ tục giao/thuê/chuyển mục đích sử dụng đất tại Quảng Ngãi.

Form Form.io của cổng dichvucong.quangngai.gov.vn có 23 ô data[...]. So với bản Ninh Bình cùng họ
thủ tục, cổng Quảng Ngãi:
  - KHÔNG có data[isOwnerDossier], data[organization], data[hoTen], data[soCCCD], data[diaChi]
    (đã grep xác nhận trên 'giao đất fill.html') -> mapper không phát các ô này.
  - CÓ THÊM data[phoneNumber1] ("Số điện thoại ủy quyền") và KHỐI THỬA ĐẤT gồm
    data[diaChiThuaDat] + data[province2] + data[village2] + data[nation2].
  - data[ProcedureDossierQuantity] ("Số bộ hồ sơ", portal để sẵn "1") và data[hinhThucNop]
    ("Hình thức nộp hồ sơ", portal chọn sẵn) là field HÀNH CHÍNH của cổng, KHÔNG lấy từ giấy tờ
    người dân -> KHÔNG khai trong UI_COMP_BY_NAME để mapper không bao giờ phát (không bịa).
"""

FIELDS: list[dict] = [
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên CHỦ HỒ SƠ/người sử dụng đất chính đứng đơn. Ưu tiên người đề nghị trong Đơn đề nghị giao đất/thuê đất/chuyển mục đích sử dụng đất (hoặc Đơn đề nghị gia hạn sử dụng đất); nếu thiếu mới lấy BÊN ỦY QUYỀN rồi người đứng tên chính trên Giấy chứng nhận. Không lấy người phối ngẫu/đồng sử dụng làm chủ chính.",
    },
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh đầy đủ của CHỦ HỒ SƠ, dd/mm/yyyy. Ưu tiên CCCD đúng người; chỉ có năm sinh thì bỏ field."},
    {"name": "ChuHoSo_GioiTinh", "desc": "Giới tính CHỦ HỒ SƠ: Nam/Nữ. Chỉ suy từ danh xưng gắn trực tiếp với người đó: Ông=Nam, Bà=Nữ."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/CMND/định danh của CHỦ HỒ SƠ, chỉ chữ số. Thuộc tính phải đi đúng người."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp giấy tờ định danh của CHỦ HỒ SƠ, dd/mm/yyyy. Ưu tiên CCCD đúng người."},
    {"name": "ChuHoSo_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh của CHỦ HỒ SƠ, lấy cùng giấy tờ với số và ngày cấp."},
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": "NƠI CƯ TRÚ (thường trú) của CHỦ HỒ SƠ, object {quocGia,tinh,xa,diaChi}. Trong Đơn đề nghị, dòng đánh số '2. Địa chỉ:' ngay sau thông tin người đề nghị CHÍNH LÀ nơi cư trú, không phải địa chỉ liên hệ; ưu tiên dòng này và giữ đủ thôn/xóm/tổ/số nhà trong diaChi. Thiếu thì lấy CCCD đúng người rồi mới đến Giấy chứng nhận. ĐÂY KHÔNG PHẢI địa chỉ thửa đất — tuyệt đối không lấy nhầm địa điểm thửa đất xin giao/thuê/chuyển mục đích.",
    },
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại liên hệ của CHỦ HỒ SƠ (người sử dụng đất/người đề nghị), chỉ chữ số. PHẢI lấy khi hồ sơ có: mục 'Địa chỉ liên hệ (điện thoại, fax, email...)' của Đơn đề nghị giao đất/thuê đất/chuyển mục đích, mục 'Điện thoại liên hệ' của Đơn đăng ký biến động Mẫu số 18, hoặc ô 'Điện thoại' trên tờ khai thuế/lệ phí trước bạ. Số ghi trong đơn/tờ khai do chính người đó đứng tên mặc nhiên là số của người đó. Không dùng số của người khác."},
    {"name": "ChuHoSo_Email", "desc": "Email của CHỦ HỒ SƠ nếu có."},
    {"name": "NguoiNop_HoTen", "desc": "Họ tên NGƯỜI NỘP. Có văn bản ủy quyền thì bắt buộc lấy BÊN ĐƯỢC ỦY QUYỀN; không có văn bản ủy quyền thì người nộp chính là CHỦ HỒ SƠ."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh đầy đủ của NGƯỜI NỘP, dd/mm/yyyy. Ưu tiên CCCD đúng người; chỉ có năm sinh thì bỏ field, không tự đặt ngày/tháng."},
    {
        "name": "NguoiNop_GioiTinh",
        "desc": "Giới tính NGƯỜI NỘP: Nam/Nữ. Chỉ suy từ danh xưng gắn trực tiếp với chính người đó: Ông=Nam, Bà=Nữ; không suy từ tên. Danh xưng có thể nằm ở mục 'BÊN ĐƯỢC ỦY QUYỀN', dòng ký tên, hoặc danh sách người ký trong phần LỜI CHỨNG THỰC cuối văn bản ủy quyền ('3. Bà: <họ tên> - Giấy tờ tùy thân: <số>') — phần chứng thực vẫn là nguồn hợp lệ để lấy thuộc tính của bên được ủy quyền.",
    },
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND/định danh của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền phải lấy của BÊN ĐƯỢC ỦY QUYỀN."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp giấy tờ định danh của NGƯỜI NỘP, dd/mm/yyyy, đi cùng đúng số giấy tờ."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh của NGƯỜI NỘP, đi cùng đúng số và ngày cấp."},
    {
        "name": "NguoiNop_NoiCuTru",
        "desc": "NƠI CƯ TRÚ của NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi}. Không có ủy quyền thì sao chép NGUYÊN VẸN ChuHoSo_NoiCuTru, gồm cả thôn/xóm/số nhà trong diaChi. Có ủy quyền thì lấy nơi cư trú của BÊN ĐƯỢC ỦY QUYỀN. ĐÂY KHÔNG PHẢI địa chỉ thửa đất.",
    },
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền thì lấy số của BÊN ĐƯỢC ỦY QUYỀN ghi trên văn bản ủy quyền; không có ủy quyền thì người nộp chính là chủ hồ sơ nên dùng số liên hệ trên Đơn đề nghị/Đơn Mẫu số 18/tờ khai thuế. Không lấy số của chủ hồ sơ khi hai người thực sự khác nhau."},
    {"name": "NguoiNop_Email", "desc": "Email của NGƯỜI NỘP nếu có."},
    {
        "name": "ChuHoSo_DonDiaChi",
        "desc": "ĐỊA CHỈ CỦA CHỦ HỒ SƠ GHI TRÊN ĐƠN/TỜ KHAI — object {quocGia,tinh,xa,diaChi}. CHỈ lấy từ mục 'Địa chỉ' trong khối người đề nghị/người sử dụng đất của Đơn đề nghị giao đất/thuê đất/chuyển mục đích sử dụng đất/gia hạn sử dụng đất; nhận BẤT KỲ mẫu nào thực tế có trong hồ sơ. TUYỆT ĐỐI KHÔNG lấy từ CCCD/CMND, Giấy chứng nhận, công văn hay giấy tờ khác; đơn không ghi thì BỎ FIELD, không thay bằng nguồn khác. Dòng địa chỉ trên đơn thường viết LIỀN, không nhãn con, dạng '<số nhà/đường/tổ/thôn>, <xã/phường> <tỉnh/thành phố>': tách bằng cách lấy cụm CUỐI làm tinh, cụm ngay TRƯỚC nó làm xa (thêm tiền tố 'Phường'/'Xã' nếu đơn viết trống), phần còn lại cho vào diaChi.",
    },
    {
        "name": "NguoiNop_DonDiaChi",
        "desc": "ĐỊA CHỈ CỦA NGƯỜI NỘP GHI TRÊN GIẤY TỜ NGƯỜI DÂN LẬP — object {quocGia,tinh,xa,diaChi}. Có văn bản ủy quyền/đại diện thì lấy địa chỉ của BÊN ĐƯỢC ỦY QUYỀN ghi trong chính văn bản đó; KHÔNG có ủy quyền thì chép nguyên vẹn ChuHoSo_DonDiaChi. TUYỆT ĐỐI KHÔNG lấy từ CCCD/CMND hay Giấy chứng nhận; không có nguồn thì BỎ FIELD. Cách tách chuỗi địa chỉ viết liền giống ChuHoSo_DonDiaChi.",
    },
    {
        "name": "Don_NoiDungDeNghi",
        "desc": "Nội dung ĐỀ NGHỊ của Đơn đề nghị giao đất/thuê đất/chuyển mục đích sử dụng đất/giao đất và giao rừng/cho thuê đất và cho thuê rừng, hoặc Đơn đề nghị gia hạn sử dụng đất (mục 'đề nghị'/'nội dung đề nghị' người dân khai). Chép NGUYÊN VĂN phần người dân khai. KHÔNG lấy tiêu đề thủ tục trên cổng thay nội dung đơn, KHÔNG tự suy diễn.",
    },
    {
        "name": "ThuaDat_DiaChi",
        "desc": "ĐỊA CHỈ THỬA ĐẤT xin giao/thuê/chuyển mục đích/gia hạn (địa điểm khu đất, KHÔNG phải nơi cư trú), object {quocGia,tinh,xa,diaChi}. Nguồn ưu tiên: mục 'Địa điểm thửa đất'/'Địa điểm khu đất'/'Vị trí khu đất' trên Đơn đề nghị giao đất/thuê đất/chuyển mục đích (hoặc Đơn đề nghị gia hạn); phụ trợ: mục 'Thửa đất' trên Giấy chứng nhận. Giữ số thửa/tờ bản đồ/đường/tổ/thôn trong diaChi nếu tài liệu ghi kèm địa chỉ. TUYỆT ĐỐI không lấy địa chỉ cư trú/thường trú của người nộp hoặc chủ hồ sơ làm địa chỉ thửa đất. Không có nguồn ghi rõ thì bỏ field.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru", "ThuaDat_DiaChi", "ChuHoSo_DonDiaChi", "NguoiNop_DonDiaChi"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"

# CHỈ các ô có mặt trong 'giao đất fill.html'. Cố ý KHÔNG khai:
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
    # Khối THỬA ĐẤT (địa điểm khu đất), tách hẳn khối địa chỉ cư trú ở trên.
    "data[diaChiThuaDat]": "dom-input",
    "data[province2]": "dom-select",
    "data[village2]": "dom-select",
    "data[nation2]": "dom-select",
}
