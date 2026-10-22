"""Facts nguồn cho thủ tục "Hỗ trợ chi phí vận chuyển người tử vong đến cơ sở hỏa táng" (mã 3.000721).

Thủ tục theo Nghị quyết 75/2026/NQ-HĐND TP Đà Nẵng; form Form.io của cổng DVC Đà Nẵng dùng CHUNG contact
block với cap_doi_gcn_da_nang (đối chiếu Mapping_HoTroChiPhiVanChuyenHoaTang_DaNang.xlsx):
  - Phần I "Thông tin chung": data[ownerFullname] (chủ hồ sơ), data[isOwnerDossier] (checkbox "Chủ hồ sơ
    cũng là người nộp hồ sơ"), data[organization] (khi cơ quan, tổ chức đứng ra hỏa táng).
  - Phần II là khối NGƯỜI NỘP: họ tên, ngày sinh, giới tính, email, SĐT, số định danh, ngày/nơi cấp,
    Chọn đối tượng, Quốc gia/Tỉnh/Phường/Địa chỉ. Tự nộp thì khối này mang chính thông tin chủ hồ sơ.
  - data[noidungyeucaugiaiquyet]: cổng để sẵn câu khung "ÔNG/BÀ:  (chủ hồ sơ) ĐỀ NGHỊ GIẢI QUYẾT ..." —
    mapper điền tên chủ hồ sơ vào chỗ trống, không cần fact riêng.
  - Cố ý KHÔNG khai: data[hinhThucNop] (cổng chọn sẵn "Trực tuyến"), data[taxCode] (Đơn không có ô mã
    định danh tổ chức), data[note] (không tự sinh ghi chú), data[tenCoQuan]/data[donvihotrophidiagioi]
    (chức năng quản lý văn bản / phi địa giới của cán bộ).

Ba người xuất hiện trong hồ sơ nhưng form CHỈ có hai vai:
  - CHỦ HỒ SƠ = người đứng ra hỏa táng ở Mục II Đơn đề nghị (II.2 hộ gia đình, cá nhân; II.1 cơ quan, tổ
    chức thì là người đại diện + tên tổ chức).
  - NGƯỜI NỘP = bên được ủy quyền/người được giới thiệu; không có thì trùng chủ hồ sơ.
  - NGƯỜI CHẾT (Mục I Đơn, Điều 1 Hợp đồng) không có ô nào -> cố ý KHÔNG khai NguoiChet_*.
"""

FIELDS: list[dict] = [
    {
        "name": "ChuHoSo_HoTen",
        "desc": (
            "Họ tên CHỦ HỒ SƠ = người đứng ra hỏa táng cho người chết, ghi ở Mục II Đơn đề nghị hỗ trợ chi phí "
            "vận chuyển người tử vong đến cơ sở hỏa táng: mục II.2.a 'Họ và tên (Chủ hộ hoặc người đại diện)' "
            "khi hộ gia đình, cá nhân đứng ra; mục II.1.b 'Họ và tên người đại diện cơ quan' khi cơ quan, tổ "
            "chức đứng ra. Họ tên viết tay trên Đơn và bản in trên Hợp đồng hỏa táng (bên ĐẠI DIỆN GIA ĐÌNH) "
            "hay lệch dấu: có CCCD đúng người thì theo CCCD. TUYỆT ĐỐI KHÔNG lấy NGƯỜI CHẾT (Mục I Đơn, người "
            "được hỏa táng ở Điều 1 Hợp đồng, người trên Trích lục khai tử) làm chủ hồ sơ."
        ),
    },
    {
        "name": "ChuHoSo_TenToChuc",
        "desc": (
            "Tên cơ quan, tổ chức đứng ra hỏa táng — CHỈ lấy khi Đơn khai mục II.1.a 'Tên cơ quan, tổ chức'. "
            "Đơn bỏ trống mục II.1 (hộ gia đình, cá nhân khai ở II.2) thì BỎ FIELD. Không lấy tên cơ sở hỏa "
            "táng hay công ty dịch vụ ký hợp đồng."
        ),
    },
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh đầy đủ của CHỦ HỒ SƠ, dd/mm/yyyy. Ưu tiên CCCD đúng người, sau đó mục II.2.a 'Ngày/tháng/năm sinh' trên Đơn. Chỉ có năm sinh thì bỏ field. KHÔNG lấy năm sinh người chết."},
    {"name": "ChuHoSo_GioiTinh", "desc": "Giới tính CHỦ HỒ SƠ: Nam/Nữ. Lấy từ CCCD đúng người hoặc danh xưng gắn trực tiếp với chính người đó (Ông=Nam, Bà=Nữ); 'Ông/Bà' in sẵn chưa gạch thì không suy. Không suy từ tên, không lấy giới tính người chết ở Mục I Đơn."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/định danh của CHỦ HỒ SƠ (Đơn mục II.2.a 'Số định danh cá nhân/căn cước số', Hợp đồng 'Số CCCD' của bên đại diện gia đình), chỉ chữ số, bỏ dấu chấm ngăn cách, giữ các số 0 ở đầu."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD của CHỦ HỒ SƠ (Đơn mục II.2.a 'cấp ngày'), dd/mm/yyyy. KHÔNG lấy ngày cấp Trích lục khai tử, ngày ký hợp đồng hay ngày làm đơn."},
    {"name": "ChuHoSo_NoiCap", "desc": "Nơi cấp CCCD của CHỦ HỒ SƠ (Đơn mục II.2.a 'Nơi cấp', vd 'Cục CSQLHC về TTXH'), đi cùng đúng số và ngày cấp."},
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": (
            "NƠI THƯỜNG TRÚ của CHỦ HỒ SƠ, object {quocGia,tinh,xa,chiTietDuoiXa}. Nguồn ưu tiên: Đơn mục II.2.b 'Nơi "
            "thường trú' (cơ quan, tổ chức: mục II.1 'Địa chỉ') -> địa chỉ thường trú của bên ĐẠI DIỆN GIA ĐÌNH "
            "trên Hợp đồng hỏa táng -> CCCD đúng người. Dòng địa chỉ viết liền '<số nhà/kiệt/đường>, <phường/xã>, "
            "<tỉnh/thành phố>': cụm cuối là tinh, cụm trước nó là xa (thêm 'Phường'/'Xã' nếu đơn viết trống), "
            "phần còn lại vào chiTietDuoiXa. KHÔNG lấy địa chỉ cơ sở hỏa táng, địa điểm hỏa táng, cơ quan nhận đơn; "
            "nơi thường trú của NGƯỜI CHẾT (Mục I.2) chỉ dùng khi Đơn ghi đúng địa chỉ đó ở mục II.2.b."
        ),
    },
    {
        "name": "ChuHoSo_DienThoai",
        "desc": (
            "Số điện thoại của CHỦ HỒ SƠ, chỉ chữ số. Nguồn: số người khai ghi trên Đơn (kể cả số viết tay ngoài "
            "mẫu), 'Số điện thoại' của bên ĐẠI DIỆN GIA ĐÌNH trên Hợp đồng hỏa táng (bản in, ưu tiên khi số viết "
            "tay khó đọc), số điện thoại người nhận hũ tro cốt trên Biên bản giao nhận. KHÔNG lấy số tài khoản "
            "ngân hàng (mục II.2.d) và KHÔNG lấy điện thoại/ĐTDĐ của cơ sở hỏa táng, công ty dịch vụ."
        ),
    },
    {"name": "ChuHoSo_Email", "desc": "Email của CHỦ HỒ SƠ nếu hồ sơ ghi rõ; không tự tạo."},
    {
        "name": "NguoiNop_HoTen",
        "desc": (
            "Họ tên NGƯỜI NỘP. Có văn bản ủy quyền/giấy giới thiệu thì lấy BÊN ĐƯỢC ỦY QUYỀN/người được giới "
            "thiệu; không có thì người nộp chính là CHỦ HỒ SƠ (trả đúng ChuHoSo_HoTen). Không lấy người chết, "
            "cán bộ chứng thực, người đại diện cơ sở hỏa táng hay người giao hũ tro cốt."
        ),
    },
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh đầy đủ của NGƯỜI NỘP, dd/mm/yyyy; chỉ có năm sinh thì bỏ field."},
    {"name": "NguoiNop_GioiTinh", "desc": "Giới tính NGƯỜI NỘP: Nam/Nữ, theo CCCD hoặc danh xưng gắn trực tiếp với chính người đó (kể cả danh sách người ký trong LỜI CHỨNG THỰC cuối văn bản ủy quyền)."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/định danh của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền phải lấy của BÊN ĐƯỢC ỦY QUYỀN."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp giấy tờ định danh của NGƯỜI NỘP, dd/mm/yyyy, đi cùng đúng số giấy tờ."},
    {"name": "NguoiNop_NoiCap", "desc": "Nơi cấp giấy tờ định danh của NGƯỜI NỘP, đi cùng đúng số và ngày cấp."},
    {
        "name": "NguoiNop_NoiCuTru",
        "desc": (
            "NƠI CƯ TRÚ của NGƯỜI NỘP, object {quocGia,tinh,xa,chiTietDuoiXa}. Không có ủy quyền thì chép NGUYÊN VẸN "
            "ChuHoSo_NoiCuTru. Có ủy quyền thì lấy nơi cư trú của BÊN ĐƯỢC ỦY QUYỀN."
        ),
    },
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền thì lấy số của BÊN ĐƯỢC ỦY QUYỀN; không lấy số tài khoản ngân hàng hay số của cơ sở hỏa táng."},
    {"name": "NguoiNop_Email", "desc": "Email của NGƯỜI NỘP nếu hồ sơ ghi rõ; không tự tạo."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Chỉ các ô mapper được phép phát (xem docstring về các ô cố ý không khai).
UI_COMP_BY_NAME = {
    # Chủ hồ sơ.
    "data[ownerFullname]": "dom-input",
    "data[isOwnerDossier]": "dom-checkbox",
    "data[organization]": "dom-input",
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
    "data[district]": "dom-select",
    "data[address]": "dom-input",
}
