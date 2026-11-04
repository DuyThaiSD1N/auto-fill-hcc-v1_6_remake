"""Facts nguồn cho thủ tục đính chính Giấy chứng nhận đã cấp lần đầu có sai sót — cổng iGate Tuyên Quang.

Đi từ link kê khai DVCQG (ke_khai_links cùng key) sang cổng iGate Tuyên Quang. Bước 1 "Thông tin hồ sơ" là Form.io
(file mapping Mapping_Dinh_chinh_GCN_da_cap_lan_dau_co_sai_sot, sheet "Đính chính GCN - Tuyên Quang"):

  Phần I  — người nộp/chủ hồ sơ: fullname, identityNumber, gender, province, address ("Tổ, thôn"), fullname1
            ("Cơ quan/Tổ chức"), identityDate, nation, district ("Phường/Xã"), phoneNumber, hinhThucNop,
            identityAgency, birthday, email, agency1 ("Số đăng ký kinh doanh"), tenHoSo, textField ("Ghi chú Khác")
  Phần II — "Thông tin người ủy quyền (nếu có)": Hovaten, Sogiaytotuythan, sodienthoai, diachi

Cổng điền sẵn theo TÀI KHOẢN đăng nhập: giới tính "Nam", tỉnh "Tỉnh Tuyên Quang", ngày sinh của chủ tài khoản. Các ô
này PHẢI đổi theo chủ hồ sơ — mapper cảnh báo khi giấy tờ không có nguồn để đổi.

Cố ý KHÔNG khai data[fullname1] (Cơ quan/Tổ chức) và data[agency1] (Số đăng ký kinh doanh): thủ tục của hộ gia đình,
cá nhân, giấy tờ không có nguồn.

Vai (xem mapper.enrich): không có văn bản ủy quyền thì Phần I là CHỦ HỒ SƠ, Phần II để trống. Có văn bản ủy quyền
thì Phần I là BÊN ĐƯỢC ỦY QUYỀN (người nộp), Phần II là BÊN ỦY QUYỀN = chủ hồ sơ.
"""

FIELDS: list[dict] = [
    {
        "name": "ChuHoSo_HoTen",
        "desc": (
            "Họ tên CHỦ HỒ SƠ. Giấy chứng nhận và Đơn đăng ký biến động (Mẫu số 18 hoặc Mẫu số 11/ĐK) hay đứng tên "
            "NHIỀU người (vợ chồng, hộ gia đình); chủ hồ sơ là người KÝ ở dòng 'Người viết đơn' (đọc tên viết dưới "
            "chữ ký). Không đọc được người ký thì lấy người trong số những người kê khai ở mục 1 của Đơn mà hồ sơ có "
            "CCCD/thẻ căn cước; vẫn không xác định được thì lấy người kê khai đầu tiên ở mục 1. Có văn bản ủy quyền "
            "thì chủ hồ sơ là BÊN ỦY QUYỀN. Viết họ tên theo CCCD/giấy tờ hộ tịch của đúng người — KHÔNG theo Giấy "
            "chứng nhận (tên trên Giấy chứng nhận chính là chỗ bị sai cần đính chính). KHÔNG lấy tài khoản dịch vụ "
            "công đang đăng nhập."
        ),
    },
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh đầy đủ của CHỦ HỒ SƠ, dd/mm/yyyy. Ưu tiên CCCD/thẻ căn cước đúng người, rồi giấy tờ khác ghi đủ ngày sinh của chính người đó (hợp đồng 'Sinh ngày … tháng … năm'). Giấy chỉ ghi NĂM sinh (trích lục kết hôn, giấy khai sinh của con, Giấy chứng nhận) -> bỏ field, tuyệt đối không bịa ngày/tháng."},
    {"name": "ChuHoSo_GioiTinh", "desc": "Giới tính CHỦ HỒ SƠ: Nam/Nữ. Nguồn: mục 'Giới tính'/'Sex' trên CCCD đúng người; danh xưng gắn trực tiếp với chính người đó (Ông=Nam, Bà=Nữ); vai 'vợ'/'người mẹ' = Nữ, 'chồng'/'người cha' = Nam trên giấy tờ hộ tịch. Không suy từ tên."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số định danh cá nhân/CCCD của CHỦ HỒ SƠ, chỉ chữ số. Ưu tiên số 12 chữ số trên CCCD/thẻ căn cước đúng người, rồi mục 'Giấy tờ nhân thân/pháp nhân' của chính người đó trên Đơn. Số CMND 9 chữ số cũ (trích lục, hợp đồng) chỉ dùng khi hồ sơ KHÔNG có số 12 chữ số nào của người đó. Không lấy số của người đồng sử dụng."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp GIẤY TỜ TÙY THÂN của CHỦ HỒ SƠ, dd/mm/yyyy, cùng giấy tờ với ChuHoSo_SoDinhDanh (mặt sau CCCD: 'Ngày, tháng, năm / Date, month, year'). Số lấy từ CCCD thì ngày cấp cũng từ CCCD — KHÔNG lấy ngày cấp CMND cũ ghi trong hợp đồng. TUYỆT ĐỐI không lấy ngày cấp Giấy chứng nhận, ngày ký đơn hay ngày chứng thực."},
    {"name": "ChuHoSo_NoiCap", "desc": "Cơ quan cấp giấy tờ tùy thân của CHỦ HỒ SƠ, cùng giấy tờ với số và ngày cấp. CCCD không có nhãn 'Nơi cấp' riêng: lấy chức danh in ở mặt sau (vd 'Cục trưởng Cục Cảnh sát quản lý hành chính về trật tự xã hội' -> trả tên cơ quan) hoặc 'Bộ Công an' trên thẻ căn cước mới. KHÔNG lấy nơi cấp CMND cũ khi số lấy từ CCCD, KHÔNG lấy cơ quan cấp Giấy chứng nhận."},
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": (
            "NƠI CƯ TRÚ của CHỦ HỒ SƠ, object {quocGia,tinh,xa,chiTietDuoiXa}. Ưu tiên 'Nơi thường trú / Place of "
            "residence' trên CCCD/thẻ căn cước đúng người; không có thì mục 'Địa chỉ' của chính người đó trên Đơn. Chỉ "
            "khi cả hai không có mới lấy địa chỉ nhà ở trên Giấy chứng nhận, nơi cư trú trên giấy tờ hộ tịch hay nơi "
            "thường trú trên hợp đồng (các giấy này hay ghi địa chỉ CŨ). Đơn chỉ ghi số nhà/đường mà CCCD có đủ "
            "phường/xã, tỉnh thì theo CCCD. Giữ số nhà/kiệt/hẻm/đường/tổ/thôn trong chiTietDuoiXa."
        ),
    },
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại liên hệ ghi trên Đơn, chỉ chữ số. Ưu tiên số ở dòng của chính chủ hồ sơ. Dòng của chủ hồ sơ để trống mà Đơn chỉ ghi MỘT số điện thoại ở dòng người đồng sử dụng cùng đứng đơn (vợ/chồng, cùng hộ) thì dùng số đó làm số liên hệ của hồ sơ. Bỏ dấu chấm/khoảng trắng."},
    {"name": "ChuHoSo_Email", "desc": "Email (hộp thư điện tử) của CHỦ HỒ SƠ nếu giấy tờ có ghi; ô bỏ trống thì bỏ field, không tự tạo."},
    {"name": "NguoiNop_HoTen", "desc": "Họ tên BÊN ĐƯỢC ỦY QUYỀN/người đại diện, CHỈ khi hồ sơ có văn bản về việc ủy quyền theo quy định của pháp luật về dân sự. Không có văn bản ủy quyền thì BỎ field (người nộp chính là chủ hồ sơ)."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh đầy đủ của BÊN ĐƯỢC ỦY QUYỀN, dd/mm/yyyy; chỉ có năm thì bỏ field. Không có văn bản ủy quyền thì bỏ field."},
    {"name": "NguoiNop_GioiTinh", "desc": "Giới tính BÊN ĐƯỢC ỦY QUYỀN: Nam/Nữ, theo danh xưng Ông/Bà gắn với chính người đó trong văn bản ủy quyền hoặc lời chứng thực, hay CCCD của người đó. Không có văn bản ủy quyền thì bỏ field."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/định danh của BÊN ĐƯỢC ỦY QUYỀN, chỉ chữ số. Không có văn bản ủy quyền thì bỏ field."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp giấy tờ tùy thân của BÊN ĐƯỢC ỦY QUYỀN, dd/mm/yyyy, đi cùng đúng số giấy tờ. Không có văn bản ủy quyền thì bỏ field."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp giấy tờ tùy thân của BÊN ĐƯỢC ỦY QUYỀN, đi cùng đúng số và ngày cấp. Không có văn bản ủy quyền thì bỏ field."},
    {"name": "NguoiNop_NoiCuTru", "desc": "NƠI CƯ TRÚ của BÊN ĐƯỢC ỦY QUYỀN, object {quocGia,tinh,xa,chiTietDuoiXa}, theo văn bản ủy quyền hoặc CCCD của người đó. Không có văn bản ủy quyền thì bỏ field."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại của BÊN ĐƯỢC ỦY QUYỀN ghi trên văn bản ủy quyền, chỉ chữ số. Không lấy số của chủ hồ sơ."},
    {"name": "NguoiNop_Email", "desc": "Email của BÊN ĐƯỢC ỦY QUYỀN nếu có; không tự tạo."},
    {
        "name": "Don_NoiDungBienDong",
        "desc": (
            "Chép NGUYÊN VĂN mục '2. Nội dung biến động' (hoặc 'Nội dung đề nghị'/'Lý do biến động') của Đơn đăng ký "
            "biến động đất đai, tài sản gắn liền với đất — với thủ tục này là nội dung đề nghị đính chính (vd 'Đính "
            "chính tên ... thành ...'). Giữ đúng cách viết của người dân, kể cả cách viết sai trong phần nội dung cũ; "
            "nhiều ý thì nối bằng dấu chấm phẩy. KHÔNG thay bằng tiêu đề thủ tục."
        ),
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Tên thủ tục hiển thị trên cổng — ô "Tên hồ sơ" không có nguồn trong giấy tờ, file mapping đề xuất lấy đúng tên này.
TEN_HO_SO = "Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót"

UI_COMP_BY_NAME = {
    # Phần I
    "data[fullname]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[gender]": "dom-select",
    "data[birthday]": "dom-date",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",  # nhãn "Phường/Xã", field-key là district (mô hình 2 cấp)
    "data[address]": "dom-input",  # nhãn "Tổ, thôn"
    "data[phoneNumber]": "dom-input",
    "data[email]": "dom-input",
    "data[hinhThucNop]": "dom-select",
    "data[tenHoSo]": "dom-input",
    "data[textField]": "dom-input",  # nhãn "Ghi chú Khác"
    # Phần II — Thông tin người ủy quyền (nếu có)
    "data[Hovaten]": "dom-input",
    "data[Sogiaytotuythan]": "dom-input",
    "data[sodienthoai]": "dom-input",
    "data[diachi]": "dom-input",
}
