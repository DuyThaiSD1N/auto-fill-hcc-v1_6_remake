"""Facts nguồn cho thủ tục xác định lại diện tích đất ở (GCN cấp trước 01/7/2004) — Quảng Ngãi.

Form Form.io của cổng dichvucong.quangngai.gov.vn dùng cùng họ template với 3 thủ tục Quảng Ngãi đã
hỗ trợ, NHƯNG bản dựng cho thủ tục này CHỈ RENDER 19 ô ``data[...]`` (đã grep 'fill .html' và
'đinmhs kèm.html': cả hai snapshot đều đúng 19 name, trùng khít nhau):

    ownerFullname, birthday, gender, email, phoneNumber, phoneNumber1, fullname, identityNumber,
    identityDate, identityAgency, note, ProcedureDossierQuantity, noidungyeucaugiaiquyet,
    chonDoiTuong, hinhThucNop, nation, province, district, address

KHÁC bản 'đăng ký đất đai lần đầu' cùng cổng (23 ô): ở đây panel "Địa chỉ thửa đất/ địa chỉ xây
dựng" chỉ còn ĐÚNG CÁI HEADER (``aria-expanded="false"``, icon fa-plus-square-o = đang thu gọn) và
Form.io KHÔNG render ``card-body`` của panel -> 4 ô data[diaChiThuaDat] / data[province2] /
data[village2] / data[nation2] KHÔNG TỒN TẠI trong DOM (grep = 0 hit ở cả 2 snapshot), ô ẩn
data[district2] cũng không. Vì vậy:
  - UI_COMP_BY_NAME cố ý KHÔNG khai khối thửa đất -> mapper không có đường nào phát ra chúng;
  - FIELDS cố ý KHÔNG có field nguồn ThuaDat_DiaChi -> LLM không được yêu cầu đọc địa chỉ thửa đất,
    tránh chi phí và tránh nguy cơ địa chỉ thửa đất bị đẩy nhầm sang ô nơi cư trú.
  (Cách xử lý này giống package ho_tro_chi_phi_hoa_tang_quang_ngai — thủ tục cũng không dùng panel đó.)

Hai ô HÀNH CHÍNH của cổng cũng cố ý KHÔNG khai (chống bịa, portal đã điền sẵn):
  - data[ProcedureDossierQuantity] ("Số bộ hồ sơ", portal để sẵn "1");
  - data[hinhThucNop] ("Hình thức nộp hồ sơ", portal chọn sẵn "Trực tuyến").

Vai trên cổng Quảng Ngãi (KHÁC cổng Ninh Bình): ô DUY NHẤT của người nộp là data[fullname] ("Họ và
tên người nộp hồ sơ"); nhãn đầu khối còn lại ghi rõ "Thông tin chủ hồ sơ" nên toàn bộ ngày sinh,
giới tính, email, điện thoại, số định danh, ngày/nơi cấp và nhóm quốc gia/tỉnh/phường/địa chỉ đều là
của CHỦ HỒ SƠ (xem mapper.owner_val). Riêng data[phoneNumber1] ("Số điện thoại ủy quyền") là số của
người trực tiếp đi nộp.

ĐƠN của thủ tục này là "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 11/ĐK"
(cổng treo sẵn file mẫu 'Mẫu số 11.docx'), KHÔNG phải Mẫu số 15 của thủ tục đăng ký lần đầu. Thực tế
người dân hay nộp đơn biến động theo mẫu cũ (Mẫu số 18) — prompt vì thế nhận BẤT KỲ mẫu đơn biến
động nào có trong hồ sơ, không đòi đúng số hiệu mẫu.
"""

FIELDS: list[dict] = [
    {
        "name": "ChuHoSo_HoTen",
        "desc": (
            "Họ tên CHỦ HỒ SƠ = người sử dụng đất đứng tên trên Giấy chứng nhận đã cấp và đứng Đơn "
            "đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 11/ĐK; hồ sơ có thể dùng "
            "mẫu đơn biến động khác như Mẫu số 18 — nhận mẫu nào thực tế có), mục 'Người sử dụng "
            "đất'/'Tên' của phần kê khai người sử dụng đất. Thiếu thì lấy BÊN ỦY QUYỀN/người được "
            "đại diện trên văn bản về việc đại diện, rồi người được chứng nhận quyền sử dụng đất "
            "ghi trên Giấy chứng nhận đã cấp, rồi người được nêu trên văn bản của cơ quan đăng ký "
            "đất đai trả lời về thửa đất. Hộ gia đình thì lấy người đại diện đứng đơn. KHÔNG lấy "
            "người đồng sử dụng thứ hai trở đi, KHÔNG lấy tài khoản dịch vụ công đang đăng nhập "
            "(cổng tự điền sẵn tên chủ tài khoản, đó KHÔNG phải chủ hồ sơ)."
        ),
    },
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh đầy đủ của CHỦ HỒ SƠ, dd/mm/yyyy. Ưu tiên CCCD/thẻ căn cước đúng người, rồi giấy xác nhận thông tin về cư trú/xác nhận số định danh. Chỉ có NĂM sinh thì bỏ field, tuyệt đối không bịa ngày/tháng. KHÔNG lấy ngày sinh của tài khoản dịch vụ công mà cổng điền sẵn."},
    {"name": "ChuHoSo_GioiTinh", "desc": "Giới tính CHỦ HỒ SƠ: Nam/Nữ. Chỉ suy từ danh xưng gắn trực tiếp với chính người đó (Ông=Nam, Bà=Nữ) hoặc mục 'Giới tính'/'Sex' trên giấy tờ tùy thân của đúng người đó; không suy từ tên."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số định danh cá nhân/CCCD/CMND/mã số thuế của CHỦ HỒ SƠ, chỉ chữ số. Nguồn: CCCD của đúng người; mục 'Giấy tờ nhân thân/pháp nhân' của Đơn đăng ký biến động; ô 'Số CMND/CCCD/Hộ chiếu' trên tờ khai thuế/lệ phí trước bạ nếu có. Thuộc tính phải đi đúng người."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp GIẤY TỜ TÙY THÂN của CHỦ HỒ SƠ, dd/mm/yyyy. Ưu tiên mặt sau CCCD đúng người. TUYỆT ĐỐI không lấy ngày cấp Giấy chứng nhận quyền sử dụng đất, ngày lập đơn, ngày ký văn bản của cơ quan đăng ký đất đai hay ngày đo đạc."},
    {"name": "ChuHoSo_NoiCap", "desc": "Cơ quan cấp giấy tờ tùy thân của CHỦ HỒ SƠ, lấy CÙNG giấy tờ với số và ngày cấp (mặt sau CCCD). KHÔNG lấy cơ quan cấp Giấy chứng nhận quyền sử dụng đất."},
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": (
            "NƠI CƯ TRÚ (thường trú/chỗ ở) của CHỦ HỒ SƠ, object {quocGia,tinh,xa,diaChi}. Nguồn ưu "
            "tiên: mục 'Địa chỉ' của người sử dụng đất trên ĐƠN/TỜ KHAI do chính người dân lập "
            "(nhận BẤT KỲ mẫu nào thực tế có trong hồ sơ: Mẫu số 11/ĐK, Mẫu số 18, đơn đề nghị... — "
            "không đòi đúng một số hiệu mẫu) -> giấy xác nhận thông tin về cư trú/xác nhận số định "
            "danh cá nhân mới nhất -> ô 'Địa chỉ'/'Địa chỉ chỗ ở hiện tại' trên tờ khai thuế, lệ "
            "phí trước bạ -> CUỐI CÙNG mới đến CCCD. CCCD cấp trước sắp xếp đơn vị hành chính hay "
            "ghi TỈNH/HUYỆN CŨ đã sáp nhập; hễ đơn đã ghi địa chỉ thì phải theo đơn, kể cả khi tên "
            "phường/xã trên đơn nghe giống địa danh tỉnh cũ. Giữ đủ số nhà/đường/tổ/thôn trong "
            "diaChi. ĐÂY KHÔNG PHẢI địa chỉ thửa đất ghi trên Giấy chứng nhận — tuyệt đối không lấy "
            "nhầm địa điểm thửa đất."
        ),
    },
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại liên hệ của CHỦ HỒ SƠ (người sử dụng đất), chỉ chữ số. PHẢI lấy khi hồ sơ có: mục 'Điện thoại liên hệ'/'Số điện thoại' của Đơn đăng ký biến động đất đai; ô 'Điện thoại' trên tờ khai thuế/lệ phí trước bạ; thông tin liên hệ ghi trong văn bản về việc đại diện. Số ghi trong đơn do chính người đó đứng tên mặc nhiên là số của người đó. Nếu một ô ghi NHIỀU số thì lấy số xuất hiện ở nhiều giấy tờ nhất làm số chính. Không dùng số của người khác."},
    {"name": "ChuHoSo_Email", "desc": "Email (hộp thư điện tử) của CHỦ HỒ SƠ nếu giấy tờ có ghi; đơn thường bỏ trống mục này -> không có thì bỏ field, không tự tạo."},
    {"name": "NguoiNop_HoTen", "desc": "Họ tên NGƯỜI NỘP hồ sơ. Có văn bản ủy quyền/'Văn bản về việc đại diện theo quy định của pháp luật về dân sự' thì bắt buộc lấy BÊN ĐƯỢC ỦY QUYỀN/người đại diện; không có văn bản đó thì người nộp CHÍNH LÀ chủ hồ sơ. KHÔNG lấy tên tài khoản dịch vụ công mà cổng điền sẵn nếu hồ sơ không có văn bản đại diện."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh đầy đủ của NGƯỜI NỘP, dd/mm/yyyy. Ưu tiên CCCD đúng người; chỉ có năm sinh thì bỏ field, không tự đặt ngày/tháng."},
    {
        "name": "NguoiNop_GioiTinh",
        "desc": (
            "Giới tính NGƯỜI NỘP: Nam/Nữ. Chỉ suy từ danh xưng gắn trực tiếp với chính người đó: "
            "Ông=Nam, Bà=Nữ; không suy từ tên. Danh xưng có thể nằm ở mục 'BÊN ĐƯỢC ỦY QUYỀN'/"
            "'Người đại diện', dòng ký tên, hoặc danh sách người ký trong phần LỜI CHỨNG THỰC cuối "
            "văn bản ủy quyền ('3. Bà: <họ tên> - Giấy tờ tùy thân: <số>') — phần chứng thực vẫn là "
            "nguồn hợp lệ để lấy thuộc tính của bên được ủy quyền."
        ),
    },
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND/định danh của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền phải lấy của BÊN ĐƯỢC ỦY QUYỀN."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp giấy tờ tùy thân của NGƯỜI NỘP, dd/mm/yyyy, đi cùng đúng số giấy tờ."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp giấy tờ tùy thân của NGƯỜI NỘP, đi cùng đúng số và ngày cấp."},
    {
        "name": "NguoiNop_NoiCuTru",
        "desc": (
            "NƠI CƯ TRÚ của NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi}. Không có ủy quyền/văn bản "
            "đại diện thì sao chép NGUYÊN VẸN ChuHoSo_NoiCuTru, gồm cả số nhà/thôn trong diaChi. Có "
            "ủy quyền thì lấy nơi cư trú của BÊN ĐƯỢC ỦY QUYỀN. ĐÂY KHÔNG PHẢI địa chỉ thửa đất."
        ),
    },
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền thì lấy số của BÊN ĐƯỢC ỦY QUYỀN ghi trên văn bản ủy quyền/văn bản đại diện; không có ủy quyền thì người nộp chính là chủ hồ sơ nên dùng số liên hệ trên Đơn đăng ký biến động. Không lấy số của chủ hồ sơ khi hai người thực sự khác nhau."},
    {"name": "NguoiNop_Email", "desc": "Email của NGƯỜI NỘP nếu có; không tự tạo."},
    {
        "name": "ChuHoSo_DonDiaChi",
        "desc": "ĐỊA CHỈ CỦA CHỦ HỒ SƠ GHI TRÊN ĐƠN/TỜ KHAI — object {quocGia,tinh,xa,diaChi}. CHỈ lấy từ mục 'Địa chỉ' nằm trong khối 'Người sử dụng đất/chủ sở hữu tài sản'/'Người đề nghị' của ĐƠN hoặc TỜ KHAI do chính người dân lập (Đơn đăng ký biến động Mẫu số 11/ĐK, Mẫu số 18, đơn đề nghị...; nhận BẤT KỲ mẫu nào có trong hồ sơ). TUYỆT ĐỐI KHÔNG lấy từ CCCD/CMND, Giấy chứng nhận, công văn hay giấy tờ khác; đơn không ghi thì BỎ FIELD, không thay bằng nguồn khác. Dòng địa chỉ trên đơn thường viết LIỀN, không nhãn con, dạng '<số nhà/đường/tổ/thôn>, <xã/phường> <tỉnh/thành phố>': tách bằng cách lấy cụm CUỐI làm tinh, cụm ngay TRƯỚC nó làm xa (thêm tiền tố 'Phường'/'Xã' nếu đơn viết trống), phần còn lại cho vào diaChi.",
    },
    {
        "name": "NguoiNop_DonDiaChi",
        "desc": "ĐỊA CHỈ CỦA NGƯỜI NỘP GHI TRÊN GIẤY TỜ NGƯỜI DÂN LẬP — object {quocGia,tinh,xa,diaChi}. Có văn bản ủy quyền/đại diện thì lấy địa chỉ của BÊN ĐƯỢC ỦY QUYỀN ghi trong chính văn bản đó; KHÔNG có ủy quyền thì người nộp chính là chủ hồ sơ nên chép nguyên vẹn ChuHoSo_DonDiaChi. TUYỆT ĐỐI KHÔNG lấy từ CCCD/CMND hay Giấy chứng nhận; không có nguồn thì BỎ FIELD. Cách tách chuỗi địa chỉ viết liền giống ChuHoSo_DonDiaChi.",
    },
    {
        "name": "Don_NoiDungDeNghi",
        "desc": (
            "Nội dung người dân khai tại mục 'Nội dung biến động'/'Nội dung đề nghị'/'Lý do biến "
            "động' của Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 11/ĐK; hồ sơ "
            "có thể dùng mẫu đơn biến động khác như Mẫu số 18 — nhận mẫu nào thực tế có). Với thủ "
            "tục này nội dung thường là đề nghị XÁC ĐỊNH LẠI DIỆN TÍCH ĐẤT Ở trên Giấy chứng nhận "
            "đã cấp TRƯỚC NGÀY 01/7/2004. Chép NGUYÊN VĂN phần người dân đã ghi/tích, kể cả khi câu "
            "chữ của dân khác cách gọi của thủ tục; nhiều ý thì nối bằng dấu chấm phẩy. Đơn không "
            "ghi ý nào thì mô tả gọn theo phần kê khai thửa đất/Giấy chứng nhận trong chính đơn. "
            "KHÔNG lấy tiêu đề thủ tục trên cổng (cổng đã điền sẵn tiêu đề vào ô này) thay nội dung "
            "đơn. ĐÂY KHÔNG PHẢI nội dung đăng ký đất đai lần đầu, KHÔNG PHẢI đính chính Giấy chứng "
            "nhận và KHÔNG PHẢI cấp đổi Giấy chứng nhận."
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

# ĐÚNG 17 ô = 19 ô data[...] có thật trên 'fill .html' TRỪ 2 ô hành chính. Cố ý KHÔNG khai (xem
# docstring): data[ProcedureDossierQuantity], data[hinhThucNop] và cả khối thửa đất
# data[diaChiThuaDat]/data[province2]/data[village2]/data[nation2] (form này KHÔNG render 4 ô đó).
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
