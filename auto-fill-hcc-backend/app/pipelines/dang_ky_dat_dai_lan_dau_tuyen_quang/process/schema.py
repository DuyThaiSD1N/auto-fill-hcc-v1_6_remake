"""Facts nguồn cho "Tuyên Quang - Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận ... lần đầu" (1.013978).

Đi từ link kê khai DVCQG (ke_khai_links cùng key) sang cổng iGate Tuyên Quang. FIELDS dùng chung cho ba form; file
mapping Mapping_Cap_GCN_lan_dau:

Form "5 bước 20 ngày" (sheet cùng tên) — Form.io bước 1, cùng khung với form 1 của đính chính GCN / giao đất Tuyên Quang:
  Phần I  — người nộp: fullname, identityNumber, gender, province, address ("Tổ, thôn"), fullname1 ("Cơ quan/Tổ
            chức"), identityDate, nation, district ("Phường/Xã"), phoneNumber, hinhThucNop, identityAgency, birthday,
            email, agency1 ("Số đăng ký kinh doanh"), tenHoSo, textField ("Ghi chú Khác")
  Phần II — "Thông tin người ủy quyền (nếu có)": Hovaten, Sogiaytotuythan, sodienthoai, diachi
  Form KHÔNG có ô thửa đất (file mapping cảnh báo cả mục 2 của Đơn không có chỗ điền).
Form "iLis cấp xã - 30 ngày" — xem process_ilis/schema.py; form "VBDLIS 20 ngày" — xem process_vbdlis/schema.py.

Cố ý KHÔNG khai: data[fullname1], data[agency1] (người nộp là cá nhân); data[tenHoSo] và data[textField] (file
mapping: "do người nộp tự đặt" / "để trống", giấy tờ không có nguồn).

Vai: CHỦ HỒ SƠ là người sử dụng đất đứng Đơn đăng ký đất đai (Mẫu số 19). NguoiNop_* chỉ có khi hồ sơ có văn bản ủy
quyền/văn bản về việc đại diện — lúc đó Phần I là bên được ủy quyền, Phần II là chủ hồ sơ; không có thì Phần I là chủ
hồ sơ, Phần II trống. Cổng điền sẵn theo TÀI KHOẢN đăng nhập: giới tính, ngày sinh, nơi cấp của chủ tài khoản và tỉnh
thửa đất "Tỉnh Tuyên Quang" — mapper xoá trắng các ô đó khi giấy tờ không có nguồn để đổi.
"""

_ONLY_AUTHORIZED = " CHỈ trả khi hồ sơ có văn bản ủy quyền/văn bản về việc đại diện; không có thì BỎ field."

FIELDS: list[dict] = [
    {
        "name": "ChuHoSo_LoaiChuThe",
        "desc": '"Tổ chức" nếu người sử dụng đất đứng đơn là công ty/doanh nghiệp/HTX/cơ quan; "Cá nhân" nếu là một '
        "người (kể cả đại diện hộ gia đình, cộng đồng dân cư, người gốc Việt Nam định cư ở nước ngoài).",
    },
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên CHỦ HỒ SƠ = người sử dụng đất/chủ sở hữu tài sản đứng Đơn đăng ký đất đai, tài sản gắn liền với "
        "đất (Mẫu số 19, trước đây Mẫu số 15), mục '1. Người sử dụng đất, chủ sở hữu tài sản gắn liền với đất, người "
        "quản lý đất' – tiểu mục 'a) Họ và tên'. Chỉ lấy HỌ TÊN, bỏ phần 'SN: …'/'sinh năm …' viết liền phía sau. "
        "Thiếu đơn thì lấy người nộp thuế trên tờ khai lệ phí trước bạ ([04]), rồi người NHẬN chuyển nhượng trên tờ "
        "khai thuế thu nhập cá nhân ([11.2]). Viết đúng chữ, GIỮ NGUYÊN DẤU (đối chiếu CCCD/giấy khai sinh của chính "
        "người đó nếu có). KHÔNG lấy tài khoản dịch vụ công đang đăng nhập.",
    },
    {
        "name": "ChuHoSo_NgaySinh",
        "desc": "Ngày sinh đầy đủ của CHỦ HỒ SƠ, dd/mm/yyyy. Ưu tiên: CCCD đúng người -> giấy khai sinh CỦA CHÍNH người "
        "đó (ngày sinh người được khai sinh, KHÔNG phải năm sinh cha mẹ) -> Đơn Mẫu số 19 mục 1a (hay viết liền sau họ "
        "tên dạng 'SN: dd/mm/yyyy') -> tờ khai lệ phí trước bạ [05] -> tờ khai thuế TNCN [11.4]. Chỉ có NĂM sinh thì "
        "bỏ field.",
    },
    {
        "name": "ChuHoSo_GioiTinh",
        "desc": "Giới tính CHỦ HỒ SƠ: Nam/Nữ. Nguồn: mục 'Giới tính'/'Sex' trên CCCD hoặc giấy khai sinh của CHÍNH người "
        "đó; danh xưng Ông/Bà gắn trực tiếp với người đó trong hợp đồng/đơn. Không suy từ tên.",
    },
    {
        "name": "ChuHoSo_SoDinhDanh",
        "desc": "Số định danh cá nhân/CCCD/CMND của CHỦ HỒ SƠ, chỉ chữ số. Nguồn: CCCD đúng người; Đơn Mẫu số 19 mục "
        "'b) Giấy tờ nhân thân/pháp nhân'; tờ khai lệ phí trước bạ [07]; tờ khai thuế TNCN [11.3]. Số CMND 9 chữ số "
        "cũ trong hợp đồng chỉ dùng khi hồ sơ không có số 12 chữ số nào của người đó.",
    },
    {
        "name": "ChuHoSo_NgayCap",
        "desc": "Ngày cấp GIẤY TỜ TÙY THÂN của CHỦ HỒ SƠ, dd/mm/yyyy (mặt sau CCCD đúng người). TUYỆT ĐỐI không lấy "
        "ngày cấp Giấy chứng nhận, ngày lập đơn, ngày đo đạc hay ngày ký hợp đồng.",
    },
    {
        "name": "ChuHoSo_NoiCap",
        "desc": "Cơ quan cấp giấy tờ tùy thân của CHỦ HỒ SƠ, CÙNG giấy tờ với số và ngày cấp. CCCD không in nhãn 'Nơi "
        "cấp': lấy cơ quan trong chức danh người ký mặt sau ('Cục Cảnh sát quản lý hành chính về trật tự xã hội') "
        "hoặc 'Bộ Công an' trên thẻ căn cước mới. Hồ sơ không có CCCD thì bỏ field.",
    },
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": "Địa chỉ THƯỜNG TRÚ/nơi ở của CHỦ HỒ SƠ, object {quocGia,tinh,xa,chiTietDuoiXa}. Ưu tiên: 'Nơi thường "
        "trú' trên CCCD đúng người -> Đơn Mẫu số 19 mục '1c) Địa chỉ' -> tờ khai lệ phí trước bạ [08] Địa chỉ + [09] "
        "Xã/phường + [10] Tỉnh -> tờ khai thuế TNCN. Phiếu đo đạc, hợp đồng nhiều năm trước ghi địa chỉ CŨ: chỉ dùng "
        "khi không còn nguồn nào. Giấy khai sinh ghi nơi thường trú của CHA MẸ — không dùng. Dòng địa chỉ trên đơn hay "
        "viết liền '<tổ/thôn/số nhà>, <p./x. tên phường xã>, <tỉnh>': cụm cuối là tinh, cụm trước nó là xa (đổi 'p.' "
        "thành 'Phường', 'x.' thành 'Xã'), phần còn lại là chiTietDuoiXa. TUYỆT ĐỐI KHÔNG lấy địa chỉ thửa đất.",
    },
    {
        "name": "ChuHoSo_DienThoai",
        "desc": "Số điện thoại của CHỦ HỒ SƠ, chỉ chữ số. Nguồn: Đơn Mẫu số 19 mục '1d) Điện thoại liên hệ', tờ khai lệ "
        "phí trước bạ [11] Điện thoại, tờ khai thuế. Bỏ dấu chấm/khoảng trắng.",
    },
    {"name": "ChuHoSo_Email", "desc": "Email (hộp thư điện tử) của CHỦ HỒ SƠ nếu giấy tờ có ghi; ô bỏ trống thì bỏ field."},
    {"name": "NguoiNop_HoTen", "desc": "Họ tên BÊN ĐƯỢC ỦY QUYỀN/người đại diện nộp hồ sơ." + _ONLY_AUTHORIZED},
    {"name": "NguoiNop_NgaySinh",
     "desc": "Ngày sinh đầy đủ của BÊN ĐƯỢC ỦY QUYỀN, dd/mm/yyyy; chỉ có năm thì bỏ field." + _ONLY_AUTHORIZED},
    {"name": "NguoiNop_GioiTinh",
     "desc": "Giới tính BÊN ĐƯỢC ỦY QUYỀN: Nam/Nữ, theo CCCD hoặc danh xưng Ông/Bà gắn với chính người đó." + _ONLY_AUTHORIZED},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/định danh của BÊN ĐƯỢC ỦY QUYỀN, chỉ chữ số." + _ONLY_AUTHORIZED},
    {"name": "NguoiNop_NgayCap",
     "desc": "Ngày cấp giấy tờ tùy thân của BÊN ĐƯỢC ỦY QUYỀN, dd/mm/yyyy, đi cùng đúng số giấy tờ." + _ONLY_AUTHORIZED},
    {"name": "NguoiNop_NoiCap",
     "desc": "Cơ quan cấp giấy tờ tùy thân của BÊN ĐƯỢC ỦY QUYỀN, đi cùng đúng số và ngày cấp." + _ONLY_AUTHORIZED},
    {"name": "NguoiNop_NoiCuTru",
     "desc": "NƠI CƯ TRÚ của BÊN ĐƯỢC ỦY QUYỀN, object {quocGia,tinh,xa,chiTietDuoiXa}, theo văn bản ủy quyền hoặc CCCD "
     "của người đó." + _ONLY_AUTHORIZED},
    {"name": "NguoiNop_DienThoai",
     "desc": "Số điện thoại của BÊN ĐƯỢC ỦY QUYỀN ghi trên văn bản ủy quyền, chỉ chữ số; không lấy số của chủ hồ sơ."},
    {"name": "NguoiNop_Email", "desc": "Email của BÊN ĐƯỢC ỦY QUYỀN nếu có; không tự tạo."},
    {
        "name": "Don_NoiDungDeNghi",
        "desc": "Nội dung ĐỀ NGHỊ tại mục '4. Đề nghị của người sử dụng đất, chủ sở hữu tài sản gắn liền với đất' của Đơn "
        "Mẫu số 19: CHỈ các ý có ô ĐÃ ĐÁNH DẤU (a) Đề nghị đăng ký đất đai, tài sản gắn liền với đất; b) Đề nghị cấp "
        "Giấy chứng nhận; c) Đề nghị ghi nợ tiền sử dụng đất; d) Đề nghị khác: <nội dung ghi tay>). Chép nguyên văn "
        "câu đề nghị, bỏ ký hiệu a)/b), nối nhiều ý bằng '; '. Ô trống không tích thì không đưa vào. Không có ý nào "
        "thì bỏ field.",
    },
    {
        "name": "ThuaDat_DiaChi",
        "desc": "ĐỊA CHỈ THỬA ĐẤT đăng ký (địa điểm khu đất, KHÔNG phải nơi cư trú), object {quocGia,tinh,xa,"
        "chiTietDuoiXa}. Phường/xã + chi tiết ưu tiên: Đơn Mẫu số 19 mục '2. Thửa đất đăng ký – b) Địa chỉ' -> tờ khai "
        "lệ phí trước bạ '1.2. Địa chỉ thửa đất' (1.2.1–1.2.3) -> tờ khai thuế TNCN [20.3]–[20.5] -> phiếu xác nhận "
        "kết quả đo đạc/mảnh trích đo. Đơn mục 2b hay KHÔNG ghi tỉnh: lấy tỉnh ở tờ khai lệ phí trước bạ 1.2.3, tờ khai "
        "thuế [20.5], phiếu đo đạc mục 4 hoặc tiêu đề mảnh trích đo. Phiếu đo đạc, mảnh trích đo cũ hay ghi xã TRƯỚC "
        "sắp xếp — đơn ghi phường mới thì theo đơn. Giữ tổ/thôn/số nhà trong chiTietDuoiXa (bỏ ghi chú tên cũ trong "
        "ngoặc). TUYỆT ĐỐI không lấy nơi cư trú của người làm địa chỉ thửa đất.",
    },
    {
        "name": "ThuaDat_SoThua",
        "desc": "Số thửa đất ĐANG đăng ký: Đơn Mẫu số 19 mục '2a) Thửa đất số' -> tờ khai lệ phí trước bạ 1.1 -> tờ khai "
        "thuế [20.1] -> phiếu đo đạc/mảnh trích đo. Chỉ lấy số. KHÔNG lấy số thửa cũ ghi trong hợp đồng chuyển "
        "nhượng nhiều năm trước khi đơn/phiếu đo đạc đã ghi số khác.",
    },
    {
        "name": "ThuaDat_SoTo",
        "desc": "Số tờ bản đồ ĐANG đăng ký: Đơn Mẫu số 19 mục '2.2. Tờ bản đồ số' -> tờ khai lệ phí trước bạ 1.1 -> tờ "
        "khai thuế [20.2] -> phiếu đo đạc/mảnh trích đo. Chỉ lấy số tờ, bỏ mã mảnh trong ngoặc (vd '12 (123456-7-a)' "
        "-> '12'). KHÔNG lấy số tờ cũ trong hợp đồng chuyển nhượng cũ.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

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
    # Phần II — Thông tin người ủy quyền (nếu có)
    "data[Hovaten]": "dom-input",
    "data[Sogiaytotuythan]": "dom-input",
    "data[sodienthoai]": "dom-input",
    "data[diachi]": "dom-input",
}
