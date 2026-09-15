"""Facts nguồn cho thủ tục Đăng ký biến động QSDĐ, tài sản gắn liền với đất tại Ninh Bình (đơn Mẫu số 18).

Thủ tục dùng Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18 để đề nghị đăng ký
biến động trong các trường hợp chuyển đổi/chuyển nhượng/thừa kế/tặng cho/góp vốn/cho thuê QSDĐ, quyền
sở hữu tài sản gắn liền với đất. Form CHỈ có 1 khối người: chủ hồ sơ = người ĐỨNG ĐƠN đăng ký biến động
(thường là BÊN NHẬN chuyển quyền). Các bên giao dịch (chuyển/nhận) nằm trong HỢP ĐỒNG đính kèm, KHÔNG
tách thành field bên A/bên B trên form.
"""

FIELDS: list[dict] = [
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên CHỦ HỒ SƠ/người sử dụng đất đứng đơn đăng ký biến động (thường là BÊN NHẬN chuyển quyền). Ưu tiên người đứng đầu mục 'Người sử dụng đất' của Đơn đăng ký biến động đất đai, tài sản gắn liền với đất Mẫu số 18; có ủy quyền thì đây là BÊN ỦY QUYỀN/người có quyền sử dụng đất, không phải BÊN ĐƯỢC ỦY QUYỀN. Nếu nhiều đồng sử dụng thì lấy người chính/đứng đầu, không lấy người phối ngẫu hoặc đồng sở hữu khác thay thế.",
    },
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh đầy đủ của CHỦ HỒ SƠ, dd/mm/yyyy. Ưu tiên CCCD đúng người; chỉ có năm sinh thì bỏ field."},
    {"name": "ChuHoSo_GioiTinh", "desc": "Giới tính CHỦ HỒ SƠ: Nam/Nữ. Chỉ suy từ danh xưng gắn trực tiếp với người đó: Ông=Nam, Bà=Nữ."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/CMND/định danh của CHỦ HỒ SƠ, chỉ chữ số. Thuộc tính phải đi đúng người."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp giấy tờ định danh của CHỦ HỒ SƠ, dd/mm/yyyy. Ưu tiên CCCD đúng người."},
    {"name": "ChuHoSo_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh của CHỦ HỒ SƠ, lấy cùng giấy tờ với số và ngày cấp."},
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": "Nơi cư trú của CHỦ HỒ SƠ, object {quocGia,tinh,xa,diaChi}. Ưu tiên mục 'Địa chỉ' của người sử dụng đất trên Đơn Mẫu số 18; nếu thiếu mới lấy CCCD đúng người, văn bản ủy quyền rồi Giấy chứng nhận. Giữ đủ thôn/xóm/tổ/số nhà trong diaChi; không để giấy tờ rút gọn ghi đè địa chỉ đầy đủ.",
    },
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại liên hệ của CHỦ HỒ SƠ trên Đơn Mẫu số 18, chỉ chữ số. Không dùng số của người khác."},
    {"name": "ChuHoSo_Email", "desc": "Email của CHỦ HỒ SƠ trên Đơn Mẫu số 18 nếu có."},
    {"name": "NguoiNop_HoTen", "desc": "Họ tên NGƯỜI NỘP. Có văn bản ủy quyền thì bắt buộc lấy BÊN ĐƯỢC ỦY QUYỀN; không có văn bản ủy quyền thì người nộp chính là CHỦ HỒ SƠ."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh đầy đủ của NGƯỜI NỘP, dd/mm/yyyy. Ưu tiên CCCD đúng người; chỉ có năm sinh thì bỏ field."},
    {"name": "NguoiNop_GioiTinh", "desc": "Giới tính NGƯỜI NỘP: Nam/Nữ. Chỉ suy từ danh xưng gắn trực tiếp với chính người đó: Ông=Nam, Bà=Nữ; không suy từ tên. Danh xưng có thể nằm ở mục 'BÊN ĐƯỢC ỦY QUYỀN', dòng ký tên, hoặc danh sách người ký trong phần LỜI CHỨNG THỰC của văn bản ủy quyền ('3. Bà: <họ tên> - Giấy tờ tùy thân: <số>') — phần chứng thực vẫn là nguồn hợp lệ để lấy thuộc tính của bên được ủy quyền."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND/định danh của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền phải lấy của BÊN ĐƯỢC ỦY QUYỀN."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp giấy tờ định danh của NGƯỜI NỘP, dd/mm/yyyy, đi cùng đúng số giấy tờ."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh của NGƯỜI NỘP, đi cùng đúng số và ngày cấp."},
    {
        "name": "NguoiNop_NoiCuTru",
        "desc": "Nơi cư trú NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi}. Không có ủy quyền thì sao chép nguyên vẹn ChuHoSo_NoiCuTru. Có ủy quyền thì lấy địa chỉ của BÊN ĐƯỢC ỦY QUYỀN, không lấy địa chỉ BÊN ỦY QUYỀN.",
    },
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại NGƯỜI NỘP, chỉ chữ số. Không lấy số của chủ hồ sơ khi hai người khác nhau."},
    {"name": "NguoiNop_Email", "desc": "Email của NGƯỜI NỘP nếu có."},
    {
        "name": "Don_NoiDungDeNghi",
        "desc": "Nội dung ĐỀ NGHỊ ĐĂNG KÝ BIẾN ĐỘNG tại mục 'Nội dung biến động'/'Đề nghị'/nội dung yêu cầu giải quyết của Đơn đăng ký biến động đất đai, tài sản gắn liền với đất Mẫu số 18 (chuyển đổi/chuyển nhượng/thừa kế/tặng cho/góp vốn/cho thuê quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất). Chép NGUYÊN VĂN phần người dân khai; số CCCD/CMND nằm trong chính nội dung viết tay để mô tả biến động vẫn phải giữ. KHÔNG lấy tiêu đề thủ tục và KHÔNG tự suy diễn. Đây KHÔNG phải nội dung đính chính / cấp đổi / đăng ký lần đầu.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"

# data[loaiVanBan] ("Loại liên thông QLVB iOffice v5" = "Văn bản đến") và data[hinhThucNopHs]
# ("Hình thức nộp hồ sơ" = "Trực tuyến") đã được portal chọn sẵn và KHÔNG lấy từ giấy tờ người dân
# → KHÔNG emit (không bịa option), để portal tự default. Vì vậy không khai trong UI_COMP_BY_NAME.
UI_COMP_BY_NAME = {
    "data[ownerFullname]": "dom-input",
    "data[organization]": "dom-input",
    "data[isOwnerDossier]": "dom-checkbox",
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[email]": "dom-input",
    "data[phoneNumber]": "dom-input",
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
    "data[hoTen]": "dom-input",
    "data[soCCCD]": "dom-input",
    "data[diaChi]": "dom-input",
}
