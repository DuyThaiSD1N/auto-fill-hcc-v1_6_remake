"""Facts nguồn cho "Khánh Hòa - Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận ... lần đầu" (1.013978).

Đi từ link kê khai DVCQG sang cổng tỉnh iGate Khánh Hòa (Form.io). Form chia BA khối, KHÁC bản Quảng Ngãi (một
panel chủ hồ sơ + ô tên người nộp) và bản Đà Nẵng (một panel hai vai + checkbox isOwnerDossier):
  - Phần I  "Thông tin người nộp": data[fullname], phoneNumber, birthday, email, identityNumber, identityDate,
    identityAgency_text (ô CHỮ, không phải select), province, village (Phường/xã), address, noidungyeucaugiaiquyet.
    Cổng điền sẵn khối này theo tài khoản đăng nhập; pipeline ghi đè bằng người nộp trong hồ sơ.
  - Phần II "Thông tin chủ hồ sơ": data[chonDoiTuong], ownerFullname, ownerPhoneNumber, ownerBirthday, ownerEmail,
    ownerIdentityNumber, ownerIdentityDate, ownerIdentityAgency (ô chữ), province1, village1, ownerAddress.
  - Phần III "Địa chỉ thửa đất/ địa chỉ xây dựng": data[diaChiThuaDat] (textarea), SoThuaDat, SoToBanDo, province2,
    nation2, village2.
Không khai các ô ẩn (district, district1, district2, thongtinTC, LaQuyTrinhCapTinh, is2Cap, nvtcDate), radio
data[CaNhan_ToChuc][...] (key có hậu tố ngẫu nhiên) và ô Bưu chính công ích — mapper không bao giờ phát.
"""

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
        "Thiếu đơn thì lấy người nộp thuế trên tờ khai lệ phí trước bạ ([04]), rồi người nhận chuyển nhượng trên tờ "
        "khai thuế thu nhập cá nhân ([11.2]). Chép đúng chữ, GIỮ NGUYÊN DẤU.",
    },
    {
        "name": "ChuHoSo_NgaySinh",
        "desc": "Ngày sinh đầy đủ của CHỦ HỒ SƠ, dd/mm/yyyy. Nguồn: CCCD đúng người; Đơn Mẫu số 19 mục 1a (ngày sinh "
        "hay viết liền sau họ tên dạng 'SN: dd/mm/yyyy'); tờ khai lệ phí trước bạ [05]; tờ khai thuế TNCN [11.4]; "
        "giấy khai sinh của đúng người. Chỉ có NĂM sinh thì bỏ field.",
    },
    {
        "name": "ChuHoSo_SoDinhDanh",
        "desc": "Số định danh cá nhân/CCCD/CMND của CHỦ HỒ SƠ, chỉ chữ số. Nguồn: CCCD đúng người; Đơn Mẫu số 19 mục "
        "'b) Giấy tờ nhân thân/pháp nhân'; tờ khai lệ phí trước bạ [07]; tờ khai thuế TNCN [11.3].",
    },
    {
        "name": "ChuHoSo_NgayCap",
        "desc": "Ngày cấp GIẤY TỜ TÙY THÂN của CHỦ HỒ SƠ, dd/mm/yyyy (mặt sau CCCD đúng người). TUYỆT ĐỐI không lấy "
        "ngày cấp Giấy chứng nhận, ngày lập đơn, ngày đo đạc hay ngày ký hợp đồng.",
    },
    {
        "name": "ChuHoSo_NoiCap",
        "desc": "Cơ quan cấp giấy tờ tùy thân của CHỦ HỒ SƠ, lấy CÙNG giấy tờ với số và ngày cấp (mặt sau CCCD).",
    },
    {
        "name": "ChuHoSo_DiaChi",
        "desc": "Địa chỉ THƯỜNG TRÚ/nơi ở của CHỦ HỒ SƠ, object {quocGia,tinh,xa,chiTietDuoiXa}. Ưu tiên: Đơn Mẫu số 19 "
        "mục '1c) Địa chỉ' -> tờ khai lệ phí trước bạ [08] Địa chỉ + [09] Xã/phường + [10] Tỉnh -> tờ khai thuế -> "
        "CUỐI CÙNG mới đến CCCD. Giấy tờ cũ (phiếu đo đạc, hợp đồng nhiều năm trước) hay ghi xã/huyện TRƯỚC sắp xếp: "
        "đơn mới hơn ghi khác thì theo đơn. Dòng địa chỉ trên đơn hay viết liền '<tổ/thôn/số nhà>, <p./x. tên phường "
        "xã>, <tỉnh>': cụm cuối là tinh, cụm trước nó là xa (đổi 'p.' thành 'Phường', 'x.' thành 'Xã'), phần còn lại "
        "là chiTietDuoiXa. TUYỆT ĐỐI KHÔNG lấy địa chỉ thửa đất làm địa chỉ người.",
    },
    {
        "name": "ChuHoSo_DienThoai",
        "desc": "Số điện thoại của CHỦ HỒ SƠ, chỉ chữ số. Nguồn: Đơn Mẫu số 19 mục '1d) Điện thoại liên hệ', tờ khai lệ "
        "phí trước bạ [11] Điện thoại, tờ khai thuế. Số ghi trong đơn/tờ khai do chính người đó đứng tên là số của "
        "người đó.",
    },
    {"name": "ChuHoSo_Email", "desc": "Email (hộp thư điện tử) của CHỦ HỒ SƠ nếu giấy tờ có ghi; không có thì bỏ field."},
    {
        "name": "NguoiNop_HoTen",
        "desc": "Họ tên NGƯỜI NỘP hồ sơ. Có văn bản ủy quyền/văn bản về việc đại diện thì lấy BÊN ĐƯỢC ỦY QUYỀN/người "
        "đại diện; KHÔNG có văn bản đó thì người nộp CHÍNH LÀ chủ hồ sơ -> chép y hệt ChuHoSo_HoTen.",
    },
    {
        "name": "NguoiNop_NgaySinh",
        "desc": "Ngày sinh đầy đủ của NGƯỜI NỘP, dd/mm/yyyy, đi đúng người; tự nộp thì giống ChuHoSo_NgaySinh. Chỉ có "
        "năm thì bỏ field.",
    },
    {
        "name": "NguoiNop_SoDinhDanh",
        "desc": "Số CCCD/CMND/định danh của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền phải lấy của BÊN ĐƯỢC ỦY QUYỀN.",
    },
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp giấy tờ tùy thân của NGƯỜI NỘP, dd/mm/yyyy, đi cùng đúng số giấy tờ."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp giấy tờ tùy thân của NGƯỜI NỘP, đi cùng đúng số và ngày cấp."},
    {
        "name": "NguoiNop_DiaChi",
        "desc": "Địa chỉ THƯỜNG TRÚ của NGƯỜI NỘP, object {quocGia,tinh,xa,chiTietDuoiXa}. Tự nộp thì chép NGUYÊN VẸN "
        "ChuHoSo_DiaChi. Có ủy quyền thì lấy địa chỉ BÊN ĐƯỢC ỦY QUYỀN trên văn bản ủy quyền (hoặc CCCD của chính "
        "người đó); không có thì bỏ field. KHÔNG lấy địa chỉ thửa đất.",
    },
    {
        "name": "NguoiNop_DienThoai",
        "desc": "Số điện thoại NGƯỜI NỘP, chỉ chữ số. Tự nộp thì dùng số liên hệ trên Đơn Mẫu số 19/tờ khai; có ủy quyền "
        "thì lấy số của BÊN ĐƯỢC ỦY QUYỀN, không mượn số chủ hồ sơ.",
    },
    {"name": "NguoiNop_Email", "desc": "Email của NGƯỜI NỘP nếu có."},
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
        "chiTietDuoiXa}. Ưu tiên: Đơn Mẫu số 19 mục '2. Thửa đất đăng ký – b) Địa chỉ' -> tờ khai lệ phí trước bạ "
        "'1.2. Địa chỉ thửa đất' (1.2.1–1.2.3) -> tờ khai thuế TNCN [20.3]–[20.5] -> phiếu xác nhận kết quả đo đạc/"
        "mảnh trích đo. Phiếu đo đạc, mảnh trích đo cũ hay ghi xã TRƯỚC sắp xếp — đơn ghi phường mới thì theo đơn. "
        "Giữ tổ/thôn/số nhà trong chiTietDuoiXa (bỏ ghi chú tên cũ trong ngoặc). TUYỆT ĐỐI không lấy nơi cư trú "
        "của người làm địa chỉ thửa đất.",
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
for name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_DiaChi", "NguoiNop_DiaChi", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"

UI_COMP_BY_NAME = {
    # Phần I — người nộp.
    "data[fullname]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[birthday]": "dom-date",
    "data[email]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency_text]": "dom-input",
    "data[province]": "dom-select",
    "data[village]": "dom-select",  # Nhãn "Phường/xã".
    "data[address]": "dom-input",
    "data[noidungyeucaugiaiquyet]": "dom-input",
    # Phần II — chủ hồ sơ.
    "data[chonDoiTuong]": "dom-select",
    "data[ownerFullname]": "dom-input",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[ownerEmail]": "dom-input",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerIdentityAgency]": "dom-input",
    "data[province1]": "dom-select",
    "data[village1]": "dom-select",
    "data[ownerAddress]": "dom-input",
    # Phần III — thửa đất.
    "data[diaChiThuaDat]": "dom-input",
    "data[SoThuaDat]": "dom-input",
    "data[SoToBanDo]": "dom-input",
    "data[province2]": "dom-select",
    "data[nation2]": "dom-select",
    "data[village2]": "dom-select",
}
