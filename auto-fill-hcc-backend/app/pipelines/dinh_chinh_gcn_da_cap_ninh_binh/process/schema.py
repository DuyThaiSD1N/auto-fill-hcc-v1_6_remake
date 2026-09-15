"""Facts nguồn cho thủ tục đính chính Giấy chứng nhận đã cấp tại Ninh Bình."""

FIELDS: list[dict] = [
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên CHỦ HỒ SƠ/người sử dụng đất chính đề nghị đính chính. Ưu tiên người đứng đầu phần I của Đơn Mẫu 18; có ủy quyền thì đây là BÊN ỦY QUYỀN/người có quyền sử dụng đất, không phải BÊN ĐƯỢC ỦY QUYỀN. Nếu nhiều đồng sử dụng thì lấy người chính/đứng đầu, không lấy người phối ngẫu hoặc đồng sở hữu khác thay thế.",
    },
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh đầy đủ của CHỦ HỒ SƠ, dd/mm/yyyy. Ưu tiên CCCD đúng người; chỉ có năm sinh thì bỏ field."},
    {"name": "ChuHoSo_GioiTinh", "desc": "Giới tính CHỦ HỒ SƠ: Nam/Nữ. Chỉ suy từ danh xưng gắn trực tiếp với người đó: Ông=Nam, Bà=Nữ."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/CMND/định danh của CHỦ HỒ SƠ, chỉ chữ số. Thuộc tính phải đi đúng người."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp giấy tờ định danh của CHỦ HỒ SƠ, dd/mm/yyyy. Ưu tiên CCCD đúng người."},
    {"name": "ChuHoSo_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh của CHỦ HỒ SƠ, lấy cùng giấy tờ với số và ngày cấp."},
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": "Nơi cư trú của CHỦ HỒ SƠ, object {quocGia,tinh,xa,diaChi}. Ưu tiên mục I.c) Địa chỉ trên Đơn Mẫu 18; nếu thiếu mới lấy CCCD đúng người, văn bản ủy quyền rồi GCN. Giữ đủ thôn/xóm/tổ/số nhà trong diaChi; không để GCN rút gọn ghi đè địa chỉ đầy đủ.",
    },
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại liên hệ của CHỦ HỒ SƠ tại mục I.d) Đơn Mẫu 18, chỉ chữ số. Không dùng số của người khác."},
    {"name": "ChuHoSo_Email", "desc": "Email của CHỦ HỒ SƠ tại mục I.d) Đơn Mẫu 18 nếu có."},
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
    {"name": "Don_NoiDungDeNghi", "desc": "Nội dung đính chính thực tế tại mục II/2 'Nội dung biến động' của Đơn Mẫu 18. Chép nguyên văn phần người dân khai và dừng trước mục III/3 'Giấy tờ liên quan'; số CCCD/CMND nằm trong chính nội dung viết tay vẫn phải giữ. Không lấy tiêu đề thủ tục và không tự suy diễn."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"

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
    "data[noidungyeucaugiaiquyet]": "dom-input",
    "data[hoTen]": "dom-input",
    "data[soCCCD]": "dom-input",
    "data[diaChi]": "dom-input",
}
