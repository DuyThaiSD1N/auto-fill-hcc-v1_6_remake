"""Facts nguồn cho thủ tục "Xác nhận về điều kiện diện tích bình quân nhà ở để đăng ký thường trú vào chỗ ở
do thuê, mượn, ở nhờ; nhà ở, đất ở không có tranh chấp ..." (mã TTHC 1.013314).

Đi từ link kê khai DVCQG, chọn tỉnh + phường/xã như bình thường; cổng tỉnh (bản mapping lấy ở
dichvucong.quangngai.gov.vn) render eForm Form.io CÙNG HỌ TEMPLATE 23 ô data[...] với thủ tục đăng ký đất
đai lần đầu Quảng Ngãi:

    ownerFullname, birthday, gender, email, phoneNumber, phoneNumber1, fullname, identityNumber,
    identityDate, identityAgency, note, ProcedureDossierQuantity, noidungyeucaugiaiquyet,
    chonDoiTuong, hinhThucNop, nation, province, district, address,
    diaChiThuaDat, province2, nation2, village2   (+ district2 rỗng, formio-hidden)

  - data[ProcedureDossierQuantity] (portal để "1") và data[hinhThucNop] (portal chọn "Trực tuyến") là field
    HÀNH CHÍNH, không đọc được từ giấy tờ -> KHÔNG khai trong UI_COMP_BY_NAME (chống bịa).
  - data[district2] có div nhưng rỗng (cấp huyện đã bỏ) -> không khai.
  - data[ghiChu] (panel "Ghi chú đồng bộ") do hệ thống đồng bộ, chỉ đọc -> không khai.

Panel "Thông tin chung" là của CHỦ HỒ SƠ = NGƯỜI ĐỀ NGHỊ trên Tờ khai Mẫu số 02 (NĐ 154/2024/NĐ-CP). Người nộp
chỉ có data[fullname] và data[phoneNumber1] ("Số điện thoại ủy quyền").

Panel "Địa chỉ thửa đất/ địa chỉ xây dựng" ở thủ tục này là ĐỊA CHỈ CHỖ Ở HỢP PHÁP đề nghị xác nhận (Tờ khai
mục II.1, căn cứ pháp lý là thửa đất trên Giấy chứng nhận). Các mục chuyên môn của Tờ khai (diện tích thửa,
diện tích xây dựng/sàn, số người đăng ký thường trú...) KHÔNG có ô trên form -> chỉ nộp qua file đính kèm.
"""

FIELDS: list[dict] = [
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên CHỦ HỒ SƠ = NGƯỜI ĐỀ NGHỊ trên Tờ khai xác nhận tình trạng chỗ ở hợp pháp, diện tích nhà ở tối thiểu (Mẫu số 02), mục 'I. THÔNG TIN NGƯỜI ĐỀ NGHỊ – 1. Họ, chữ đệm và tên'. Đối chiếu CCCD/thẻ căn cước đúng người ('Họ, chữ đệm và tên khai sinh'); CCCD khớp thì ưu tiên chính tả trên CCCD. Thiếu Tờ khai thì lấy người sử dụng đất/chủ sở hữu ĐẦU TIÊN ghi trên Giấy chứng nhận ('Ông'/'Bà' đầu mục I).",
    },
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh đầy đủ của CHỦ HỒ SƠ, dd/mm/yyyy. Ưu tiên CCCD đúng người, rồi Tờ khai mục 'I.2. Ngày, tháng, năm sinh'. Giấy chứng nhận thường chỉ ghi 'Sinh năm' -> chỉ có năm thì bỏ field."},
    {"name": "ChuHoSo_GioiTinh", "desc": "Giới tính CHỦ HỒ SƠ: Nam/Nữ. Lấy mục 'Giới tính/Sex' trên CCCD đúng người, hoặc danh xưng gắn trực tiếp với chính người đó trên Giấy chứng nhận (Ông=Nam, Bà=Nữ). Tờ khai Mẫu 02 không có mục giới tính; không suy từ tên."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số định danh cá nhân 12 chữ số của CHỦ HỒ SƠ. Nguồn: CCCD/thẻ căn cước đúng người, Tờ khai mục 'I.3. Số định danh cá nhân'. TUYỆT ĐỐI KHÔNG lấy số CMND 9 số cũ ghi trên Giấy chứng nhận."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD/thẻ căn cước của CHỦ HỒ SƠ ('Ngày, tháng, năm cấp/Date of issue'), dd/mm/yyyy. CHỈ lấy từ chính thẻ đó. TUYỆT ĐỐI không lấy 'Cấp ngày' của CMND cũ ghi trên Giấy chứng nhận, ngày cấp Giấy chứng nhận hay ngày ký Tờ khai."},
    {"name": "ChuHoSo_NoiCap", "desc": "Cơ quan cấp CCCD/thẻ căn cước của CHỦ HỒ SƠ, lấy CÙNG thẻ với số và ngày cấp (thẻ mẫu mới in 'BỘ CÔNG AN'). KHÔNG lấy 'Nơi cấp' của CMND cũ trên Giấy chứng nhận."},
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": "NƠI CƯ TRÚ của CHỦ HỒ SƠ, object {quocGia,tinh,xa,diaChi}. Ưu tiên: mục 'Nơi cư trú/Place of residence' trên CCCD/thẻ căn cước đúng người -> Tờ khai mục 'I.4. Nơi cư trú' -> 'Địa chỉ thường trú' trên Giấy chứng nhận. Tờ khai hay chỉ ghi số nhà/đường/tổ dân phố ở mục I.4 mà KHÔNG ghi phường/tỉnh: khi đó lấy xa theo cơ quan ở dòng 'Kính gửi: UBND <phường/xã>' (hoặc tên UBND ở góc trái trên) của chính Tờ khai. Giữ đủ số nhà/đường/tổ/thôn trong diaChi, không lặp xã/tỉnh trong diaChi.",
    },
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại của CHỦ HỒ SƠ nếu giấy tờ có ghi (chỉ chữ số). Tờ khai Mẫu 02 thường KHÔNG có mục này -> không có thì bỏ field."},
    {"name": "ChuHoSo_Email", "desc": "Email của CHỦ HỒ SƠ nếu giấy tờ có ghi; không có thì bỏ field."},
    {"name": "NguoiNop_HoTen", "desc": "Họ tên NGƯỜI NỘP hồ sơ. Có văn bản ủy quyền thì lấy BÊN ĐƯỢC ỦY QUYỀN; không có thì người nộp CHÍNH LÀ người đề nghị trên Tờ khai."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/định danh của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền phải lấy của BÊN ĐƯỢC ỦY QUYỀN."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền thì lấy số của BÊN ĐƯỢC ỦY QUYỀN ghi trên văn bản ủy quyền; không có thì bỏ field."},
    {
        "name": "ChoO_DiaChi",
        "desc": "ĐỊA CHỈ CHỖ Ở HỢP PHÁP đề nghị xác nhận, object {quocGia,tinh,xa,diaChi}. Ưu tiên: Tờ khai mục 'II. THÔNG TIN VỀ CHỖ Ở HỢP PHÁP – 1. Địa chỉ chỗ ở hợp pháp' -> Giấy chứng nhận mục 'Địa chỉ thửa đất'/'Địa chỉ' của nhà ở -> nơi cư trú trên CCCD (chỉ khi người đề nghị cư trú ngay tại chỗ ở này). Tờ khai không ghi phường/tỉnh thì lấy xa theo dòng 'Kính gửi: UBND <phường/xã>' của Tờ khai. Giấy chứng nhận cũ có thể ghi đơn vị hành chính TRƯỚC sắp xếp: Tờ khai ghi khác thì theo Tờ khai. Không có nguồn ghi rõ thì bỏ field.",
    },
    {"name": "ThuaDat_So", "desc": "Số thửa đất ('Thửa đất số') ghi trên Giấy chứng nhận của chỗ ở hợp pháp. Chỉ chữ số/ký hiệu, không kèm chữ 'Thửa'. Không có thì bỏ field."},
    {"name": "ThuaDat_ToBanDo", "desc": "Số tờ bản đồ ('Tờ bản đồ số') ghi trên Giấy chứng nhận của chỗ ở hợp pháp. Không có thì bỏ field."},
    {"name": "ToKhai_TinhTrangChoO", "desc": "Nội dung người đề nghị ghi tại Tờ khai mục 'III. NỘI DUNG ĐỀ NGHỊ ... XÁC NHẬN – 1. Tình trạng chỗ ở để đăng ký thường trú, tạm trú', chép NGUYÊN VĂN. Bỏ trống/chỉ có dấu chấm thì bỏ field."},
    {"name": "ToKhai_SoNguoiThueMuon", "desc": "Tờ khai mục 'III.2 ... Tổng số người thuê, mượn, ở nhờ', chép nguyên văn kèm đơn vị (vd '3 người'). Bỏ trống thì bỏ field."},
    {"name": "ToKhai_DienTichThueMuon", "desc": "Tờ khai mục 'III.2 ... Tổng số diện tích chỗ ở hợp pháp thuê, mượn, ở nhờ', chép nguyên văn kèm đơn vị. Bỏ trống thì bỏ field."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap"):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_NoiCuTru", "ChoO_DiaChi"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"

# Tên thủ tục — portal đã điền sẵn vào data[noidungyeucaugiaiquyet]; mapper giữ làm phần đầu nội dung.
TEN_THU_TUC = (
    "Xác nhận về điều kiện diện tích bình quân nhà ở để đăng ký thường trú vào chỗ ở do thuê, mượn, ở nhờ; "
    "nhà ở, đất ở không có tranh chấp quyền sở hữu nhà ở, quyền sử dụng đất ở, không thuộc địa điểm không "
    "được đăng ký thường trú mới"
)

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
    # Panel "Địa chỉ thửa đất/ địa chỉ xây dựng" = địa chỉ CHỖ Ở HỢP PHÁP đề nghị xác nhận.
    "data[diaChiThuaDat]": "dom-input",
    "data[province2]": "dom-select",
    "data[village2]": "dom-select",
    "data[nation2]": "dom-select",
}
