"""Compact schema cho "Khánh Hòa - Xác nhận về điều kiện diện tích bình quân nhà ở để đăng ký thường trú vào chỗ ở do thuê,
mượn, ở nhờ; nhà ở, đất ở không có tranh chấp …" (1.013314).

LLM CHỈ trả FACT nguồn: người đề nghị (chủ hồ sơ) từ Tờ khai xác nhận tình trạng chỗ ở hợp pháp, diện tích nhà ở tối thiểu
(Mẫu số 02, Phụ lục IV NĐ 58/2026/NĐ-CP) + CCCD của đúng người đó; người nộp thay từ Giấy ủy quyền hoặc CCCD của người
KHÁC; địa chỉ chỗ ở hợp pháp (mục II.1) và nội dung đề nghị (mục III). `mapper.enrich` suy ra tất định các ô Form.io.

Form bước 1 "Thông tin hồ sơ" cổng iGate Khánh Hòa (file "Mapping_XN-cho-o-hop-phap_Mau02_KhanhHoa.xlsx", 27/11/2026) —
TRÙNG form 1.115148 Khánh Hòa (tinh_tien_su_dung_dat_nd_50_2026_khanh_hoa):
  Chủ hồ sơ  → data[ownerFullname], ownerIdentityNumber, ownerBirthday, ownerPhoneNumber, ownerAddress (MỘT ô chữ gộp cả
               địa chỉ), checkbox data[isOwnerDossier] "Người nộp hồ sơ đồng thời là chủ hồ sơ".
  Người nộp  → data[fullname], birthday, gender, email, phoneNumber, identityNumber, identityDate, identityAgency (select
               "Bộ Công An" / "Cục cảnh sát quản lý hành chính về trật tự xã hội"), noidungyeucaugiaiquyet, chonDoiTuong,
               nation, province, district (nhãn "Phường/xã"), address.
Không khai: radio data[CaNhan_ToChuc] (cổng chọn sẵn "Cá nhân"), panel tổ chức thongtinTC (chỉ hiện khi chọn "Tổ chức";
giấy của tổ chức không thuộc thành phần hồ sơ), Bưu chính công ích, Ghi chú, Hình thức nộp (chonDoiTuong1, cổng để sẵn
"Trực tuyến"), các ô formio-hidden (dataTesting, village, noiCapLabel, is2Cap…).
Mục II.2 của Tờ khai (diện tích thửa / xây dựng / sàn, số người đang đăng ký thường trú) KHÔNG có ô trên form → chỉ nộp qua
file Tờ khai đính kèm.
"""

FIELDS: list[dict] = [
    # --- NGƯỜI NỘP THAY (điểm neo, TRÍCH ĐẦU TIÊN) — gộp 1 object để LLM khỏi phân tán/ngại điền.
    {"name": "NguoiNopThay",
     "desc": "TRÍCH ĐẦU TIÊN. Người NỘP THAY, KHÁC người đề nghị, CHỈ điền khi hồ sơ có: (a) MỘT FILE RIÊNG tiêu đề "
             "'GIẤY ỦY QUYỀN'/'HỢP ĐỒNG ỦY QUYỀN'/'VĂN BẢN ỦY QUYỀN' → người đứng NGAY SAU 'ủy quyền cho:' (bên B); "
             "hoặc (b) thẻ CCCD/căn cước của một người mà HỌ TÊN VÀ SỐ ĐỊNH DANH đều KHÔNG khớp người đề nghị ở mục "
             "'I. THÔNG TIN NGƯỜI ĐỀ NGHỊ' của Tờ khai. Object: {\"hoTen\", \"ngaySinh\" (dd/mm/yyyy), \"gioiTinh\" "
             "('Nam'/'Nữ'), \"soDinhDanh\", \"ngayCapCccd\" (dd/mm/yyyy), \"noiCapCccd\", \"dienThoai\", "
             "\"thuongTru\":{\"quocGia\",\"tinh\",\"xa\",\"chiTietDuoiXa\"}}. BỎ TRỐNG nếu mọi CCCD đều là của người đề "
             "nghị. Chủ nhà / bên cho thuê, cho mượn, cho ở nhờ ghi trên hợp đồng hay Giấy chứng nhận KHÔNG phải người "
             "nộp thay. Đừng bịa."},

    # --- CHỦ HỒ SƠ = NGƯỜI ĐỀ NGHỊ trên Tờ khai Mẫu 02.
    {"name": "ChuHoSo_HoTen",
     "desc": "Họ tên CHỦ HỒ SƠ = NGƯỜI ĐỀ NGHỊ ở Tờ khai mục 'I. THÔNG TIN NGƯỜI ĐỀ NGHỊ – 1. Họ, chữ đệm và tên' (cũng là "
             "người ký 'Người đề nghị'). CCCD của đúng người này ghi khác dấu/chữ đệm → lấy theo CCCD. KHÔNG lấy chủ nhà "
             "/ người đứng tên Giấy chứng nhận / bên cho thuê, cho mượn."},
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh chủ hồ sơ, dd/mm/yyyy — CCCD của đúng người này, rồi Tờ khai mục "
        "'I.2. Ngày, tháng, năm sinh'. Chỉ có năm sinh → bỏ trống, không tự thêm ngày tháng."},
    {"name": "ChuHoSo_GioiTinh", "desc": 'Giới tính chủ hồ sơ: "Nam" hoặc "Nữ" — mục "Giới tính/Sex" trên CCCD (Tờ khai '
        'Mẫu 02 không có mục giới tính; không suy từ tên).'},
    {"name": "ChuHoSo_SoDinhDanh",
     "desc": "Số định danh cá nhân 12 chữ số của chủ hồ sơ: mặt trước / MRZ mặt sau CCCD, hoặc Tờ khai mục 'I.3. Số định "
             "danh cá nhân'. CCCD và Tờ khai lệch nhau → lấy theo CCCD. Chỉ chữ số."},
    {"name": "ChuHoSo_NgayCapCccd", "desc": "Ngày cấp CCCD của chủ hồ sơ (mặt sau, dòng 'Ngày, tháng, năm' / 'Ngày, tháng, "
        "năm cấp / Date of issue'), dd/mm/yyyy. CHỈ lấy trên chính thẻ; không lấy ngày ký Tờ khai."},
    {"name": "ChuHoSo_NoiCapCccd",
     "desc": 'Nơi cấp CCCD của chủ hồ sơ (mặt sau). "CỤC TRƯỞNG CỤC CẢNH SÁT..." → '
             '"Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → "Bộ Công an".'},
    {"name": "ChuHoSo_ThuongTru",
     "desc": "NƠI CƯ TRÚ HIỆN TẠI của CHỦ HỒ SƠ, object {quocGia,tinh,xa,chiTietDuoiXa}: 'Nơi thường trú' / 'Nơi cư trú' "
             "trên CCCD, hoặc Tờ khai mục 'I.4. Nơi cư trú'. CCCD cấp trước sắp xếp đơn vị hành chính 2025 còn ghi huyện / "
             "xã cũ mà Tờ khai ghi đơn vị mới → theo Tờ khai. KHÔNG lấy 'Địa chỉ chỗ ở hợp pháp' ở mục II.1 (chỗ ở đề "
             "nghị xác nhận, khác nơi cư trú hiện tại)."},
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại của CHỦ HỒ SƠ nếu giấy tờ có ghi (Tờ khai Mẫu 02 thường KHÔNG có "
        "mục này). Chỉ chữ số; không có thì bỏ field."},
    {"name": "ChuHoSo_Email", "desc": "Email của chủ hồ sơ nếu giấy tờ có ghi; không có thì bỏ field."},

    # --- CHỖ Ở HỢP PHÁP + NỘI DUNG ĐỀ NGHỊ (ghép vào ô "Nội dung yêu cầu giải quyết").
    {"name": "ChoO_DiaChi",
     "desc": "ĐỊA CHỈ CHỖ Ở HỢP PHÁP đề nghị xác nhận, object {quocGia,tinh,xa,chiTietDuoiXa}: Tờ khai mục 'II. THÔNG TIN "
             "VỀ CHỖ Ở HỢP PHÁP – 1. Địa chỉ chỗ ở hợp pháp' (số nhà, đường/thôn/tổ → chiTietDuoiXa). Tờ khai không ghi "
             "phường/tỉnh thì lấy xa theo dòng 'Kính gửi: Ủy ban nhân dân <phường/xã>' của chính Tờ khai. Không có Tờ "
             "khai thì lấy 'Địa chỉ' nhà ở trên Giấy chứng nhận / hợp đồng thuê, mượn, ở nhờ. Không có nguồn thì bỏ field."},
    {"name": "ToKhai_TinhTrangChoO",
     "desc": "Tờ khai mục 'III. NỘI DUNG ĐỀ NGHỊ … XÁC NHẬN – 1. Tình trạng chỗ ở để đăng ký thường trú, tạm trú': chép "
             "NGUYÊN VĂN chữ người dân viết (vd 'Đề nghị xác nhận chỗ ở hợp pháp tại địa chỉ nêu trên đang sử dụng ổn "
             "định, …'). Dòng chỉ có dấu chấm / để trống → bỏ field. KHÔNG lấy phần 'XÁC NHẬN CỦA UBND'."},
    {"name": "ToKhai_SoNguoiThueMuon", "desc": "Tờ khai mục 'III.2 … Tổng số người thuê, mượn, ở nhờ', chép nguyên văn kèm "
        "đơn vị (vd '01 người'). Bỏ trống thì bỏ field."},
    {"name": "ToKhai_DienTichThueMuon", "desc": "Tờ khai mục 'III.2 … Tổng số diện tích chỗ ở hợp pháp thuê, mượn, ở "
        "nhờ', chép nguyên văn kèm đơn vị (vd '20 m²'). Bỏ trống thì bỏ field."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCapCccd"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ChuHoSo_ThuongTru", "ChoO_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Tên thủ tục — nội dung yêu cầu mặc định khi Tờ khai không đọc được mục II.1 / III.
TEN_THU_TUC = (
    "Xác nhận về điều kiện diện tích bình quân nhà ở để đăng ký thường trú vào chỗ ở do thuê, mượn, ở nhờ; nhà ở, đất ở "
    "không có tranh chấp quyền sở hữu nhà ở, quyền sử dụng đất ở, không thuộc địa điểm không được đăng ký thường trú mới"
)

UI_COMP_BY_NAME = {
    # Chủ hồ sơ.
    "data[ownerFullname]": "dom-input",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerAddress]": "dom-input",
    "data[isOwnerDossier]": "dom-checkbox",
    # Người nộp hồ sơ.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[email]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[noidungyeucaugiaiquyet]": "dom-input",
    "data[chonDoiTuong]": "dom-select",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",  # nhãn "Phường/xã" (mô hình 2 cấp)
    "data[address]": "dom-input",
}
