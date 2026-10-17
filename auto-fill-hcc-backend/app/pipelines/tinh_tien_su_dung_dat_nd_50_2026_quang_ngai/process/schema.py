"""Facts nguồn cho thủ tục tính hoặc tính lại tiền sử dụng đất theo các điểm a, b, c và d khoản 2 Điều 12
Nghị định 50/2026/NĐ-CP — cổng dịch vụ công tỉnh Quảng Ngãi (1.115148).

Form Form.io của cổng dichvucong.quangngai.gov.vn dùng CÙNG họ template 23 ô data[...] với thủ tục "Đăng ký
đất đai lần đầu" cùng cổng (theo file mapping của bộ phận một cửa):
  - Panel "Thông tin chung": ownerFullname, birthday, gender, email, phoneNumber, phoneNumber1, fullname,
    identityNumber, identityDate, identityAgency, note, ProcedureDossierQuantity, noidungyeucaugiaiquyet,
    chonDoiTuong, hinhThucNop, nation, province, district (nhãn "Phường/xã"), address.
  - Panel "Địa chỉ thửa đất/ địa chỉ xây dựng": diaChiThuaDat, province2, nation2, village2.
  - data[district2] có div nhưng RỖNG (formio-hidden, cấp huyện đã bỏ) -> không khai.
  - data[ProcedureDossierQuantity] (portal để "1") và data[hinhThucNop] (portal chọn sẵn "Trực tuyến") là
    field HÀNH CHÍNH của cổng, không đọc được từ giấy tờ -> không khai (chống bịa).

Bộ hồ sơ điển hình: Đơn đề nghị tính lại tiền sử dụng đất (2 trang) + Bản cam kết + Bản sao Giấy chứng nhận
QSDĐ, thường quét GỘP một PDF. Đơn có đủ nhân thân người sử dụng đất (số CCCD, ngày cấp, nơi cấp, địa chỉ
thường trú, điện thoại) và thông tin thửa đất; Bản cam kết có thêm NGÀY SINH.
"""

FIELDS: list[dict] = [
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên CHỦ HỒ SƠ = người sử dụng đất đứng Đơn đề nghị tính lại tiền sử dụng đất, mục '1. Thông tin người sử dụng đất' – dòng 'Họ và tên cá nhân/đại diện hộ gia đình'. Thiếu thì lấy 'Tên tôi là' trên Bản cam kết, rồi mục '1. Người sử dụng đất' trên Giấy chứng nhận (bỏ danh xưng Ông/Bà). Viết hoa chữ cái đầu mỗi tiếng.",
    },
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh đầy đủ của CHỦ HỒ SƠ, dd/mm/yyyy. Nguồn: CCCD đúng người -> dòng 'Ngày sinh' trên Bản cam kết. Đơn đề nghị và Giấy chứng nhận KHÔNG ghi ngày sinh. Chỉ có năm sinh thì bỏ field."},
    {"name": "ChuHoSo_GioiTinh", "desc": "Giới tính CHỦ HỒ SƠ: Nam/Nữ. Lấy mục 'Giới tính' trên CCCD của đúng người; không có CCCD thì suy từ danh xưng gắn trực tiếp với chính người đó trên Giấy chứng nhận ('Ông'=Nam, 'Bà'=Nữ). Không suy từ tên."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/định danh cá nhân của CHỦ HỒ SƠ, chỉ chữ số (12 số). Nguồn: CCCD -> 'Số CCCD/Định danh cá nhân' trên Đơn -> 'Số CCCD' trên Bản cam kết -> 'CCCD:' cạnh tên người sử dụng đất trên Giấy chứng nhận. Chữ viết tay khó đọc thì đối chiếu các nguồn, lấy số trùng nhiều nguồn nhất (số in máy trên Giấy chứng nhận đáng tin hơn chữ viết tay)."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD của CHỦ HỒ SƠ, dd/mm/yyyy. Nguồn: CCCD -> 'Ngày cấp' ở dòng Số CCCD của Đơn -> 'Cấp ngày' trên Bản cam kết. TUYỆT ĐỐI không lấy ngày cấp Giấy chứng nhận (dòng 'Số phát hành Giấy chứng nhận ... Ngày cấp' của mục 2 Đơn), ngày làm đơn hay ngày ký."},
    {"name": "ChuHoSo_NoiCap", "desc": "Nơi cấp CCCD của CHỦ HỒ SƠ (mặt sau CCCD hoặc dòng 'Nơi cấp' ở mục 1 Đơn), viết đầy đủ: 'Cục CS QLHC về TTXH'/'Cục cảnh sát QLHC về TTXH' -> 'Cục Cảnh sát quản lý hành chính về trật tự xã hội'."},
    {
        "name": "ChuHoSo_DonDiaChi",
        "desc": "ĐỊA CHỈ THƯỜNG TRÚ của CHỦ HỒ SƠ ghi trên ĐƠN đề nghị (mục 1, dòng 'Địa chỉ thường trú'); đơn không ghi thì lấy dòng 'Địa chỉ' trên Bản cam kết. Object {quocGia,tinh,xa,diaChi}. KHÔNG lấy 'Địa chỉ thửa đất'. Dòng viết liền dạng '<số nhà, đường>, P./X. <phường/xã>, T./TP. <tỉnh>': cụm CUỐI là tỉnh, cụm ngay TRƯỚC là xã/phường, phần còn lại vào diaChi; khai triển viết tắt 'P.'->'Phường', 'X.'->'Xã', 'T.'->'Tỉnh', 'TP.'->'Thành phố'.",
    },
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": "NƠI THƯỜNG TRÚ của CHỦ HỒ SƠ trên CCCD, object {quocGia,tinh,xa,diaChi}. Chỉ dùng khi Đơn và Bản cam kết đều không ghi địa chỉ. ĐÂY KHÔNG PHẢI địa chỉ thửa đất.",
    },
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại liên hệ của CHỦ HỒ SƠ (dòng 'Số điện thoại liên hệ' trên Đơn hoặc Bản cam kết), chỉ chữ số, bỏ dấu chấm/cách."},
    {"name": "ChuHoSo_Email", "desc": "Email của CHỦ HỒ SƠ nếu giấy tờ có ghi; không có thì bỏ field."},
    {"name": "NguoiNop_HoTen", "desc": "Họ tên NGƯỜI NỘP hồ sơ. Có giấy/văn bản ủy quyền thì lấy BÊN ĐƯỢC ỦY QUYỀN; không có thì người nộp CHÍNH LÀ chủ hồ sơ (người làm đơn)."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền thì lấy số của BÊN ĐƯỢC ỦY QUYỀN ghi trên văn bản ủy quyền; không có ủy quyền thì dùng số liên hệ trên Đơn/Bản cam kết."},
    {
        "name": "Don_NoiDungDeNghi",
        "desc": "NỘI DUNG ĐỀ NGHỊ tại mục '3. Nội dung đề nghị' của Đơn: chép NGUYÊN VĂN đoạn 'Tôi nhận thấy hồ sơ/thửa đất của tôi thuộc trường hợp...' và đoạn tiếp theo 'Do đó, tôi kính đề nghị ... theo quy định.', nối bằng một dấu cách. DỪNG trước đoạn 'Tôi cam kết chọn thửa đất số...' và mục '4. Giấy tờ liên quan kèm theo'. Sửa lỗi xuống dòng/ngắt trang do OCR nhưng không thêm bớt chữ.",
    },
    {"name": "ThuaDat_SoThua", "desc": "Số thửa đất đề nghị tính lại ('Thửa đất số' ở mục 2 Đơn; đối chiếu Giấy chứng nhận mục 2.a). Chỉ chữ số."},
    {"name": "ThuaDat_SoTo", "desc": "Số tờ bản đồ của thửa đất ('Tờ bản đồ số' ở mục 2 Đơn; đối chiếu Giấy chứng nhận mục 2.a). Chỉ chữ số."},
    {
        "name": "ThuaDat_DiaChi",
        "desc": "ĐỊA CHỈ THỬA ĐẤT (địa điểm khu đất, KHÔNG phải nơi cư trú), object {quocGia,tinh,xa,diaChi}. Nguồn ưu tiên: mục '2.e Địa chỉ' (hoặc 'Địa chỉ thửa đất') trên Giấy chứng nhận -> dòng 'Địa chỉ thửa đất' ở mục 2 Đơn -> địa chỉ thửa đất trên Bản cam kết. diaChi chỉ giữ thôn/tổ/đường nếu nguồn có ghi; KHÔNG ghi số thửa/tờ bản đồ vào diaChi. TUYỆT ĐỐI không lấy địa chỉ thường trú của người sử dụng đất.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap"):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_DonDiaChi", "ChuHoSo_NoiCuTru", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"

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
    "data[noidungyeucaugiaiquyet]": "dom-input",
    # Khối THỬA ĐẤT (panel "Địa chỉ thửa đất/ địa chỉ xây dựng"), tách hẳn khối địa chỉ cư trú ở trên.
    "data[diaChiThuaDat]": "dom-input",
    "data[province2]": "dom-select",
    "data[village2]": "dom-select",
    "data[nation2]": "dom-select",
}
