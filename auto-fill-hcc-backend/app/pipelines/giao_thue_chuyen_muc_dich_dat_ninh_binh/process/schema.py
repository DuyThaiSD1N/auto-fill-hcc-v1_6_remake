"""Facts nguồn cho thủ tục giao/thuê/chuyển mục đích sử dụng đất tại Ninh Bình."""

FIELDS: list[dict] = [
    {"name": "ChuHoSo_HoTen", "desc": "Họ tên CHỦ HỒ SƠ/người sử dụng đất chính. Ưu tiên người đề nghị trong Đơn Mẫu 04; nếu thiếu mới lấy BÊN ỦY QUYỀN hoặc người đứng tên chính trên Giấy chứng nhận. Không lấy người phối ngẫu/đồng sở hữu làm chủ chính."},
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh đầy đủ của CHỦ HỒ SƠ, dd/mm/yyyy. Chỉ có năm sinh thì bỏ field."},
    {"name": "ChuHoSo_GioiTinh", "desc": "Giới tính CHỦ HỒ SƠ: Nam/Nữ. Chỉ suy từ danh xưng gắn trực tiếp với người đó: Ông=Nam, Bà=Nữ."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/CMND/định danh của CHỦ HỒ SƠ, chỉ chữ số."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp giấy tờ định danh của CHỦ HỒ SƠ, dd/mm/yyyy."},
    {"name": "ChuHoSo_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh của CHỦ HỒ SƠ."},
    {"name": "ChuHoSo_NoiCuTru", "desc": "Nơi cư trú của CHỦ HỒ SƠ, object {quocGia,tinh,xa,diaChi}. Trong Đơn đề nghị, dòng đánh số '2. Địa chỉ:' ngay sau thông tin người đề nghị CHÍNH LÀ địa chỉ thường trú/nơi cư trú, không phải địa chỉ liên hệ; bắt buộc ưu tiên dòng này và giữ đủ thôn/xóm/số nhà trong diaChi. Chỉ dùng GCN nếu Đơn không có địa chỉ; GCN rút gọn không được ghi đè địa chỉ đầy đủ trên Đơn."},
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại của CHỦ HỒ SƠ, chỉ chữ số. Không dùng số của người khác."},
    {"name": "ChuHoSo_Email", "desc": "Email của CHỦ HỒ SƠ nếu có."},
    {"name": "NguoiNop_HoTen", "desc": "Họ tên NGƯỜI NỘP. Có văn bản ủy quyền thì bắt buộc lấy BÊN ĐƯỢC ỦY QUYỀN; không có ủy quyền thì người nộp chính là CHỦ HỒ SƠ."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh đầy đủ của NGƯỜI NỘP, dd/mm/yyyy. Chỉ có năm sinh thì bỏ field, không tự đặt ngày/tháng."},
    {"name": "NguoiNop_GioiTinh", "desc": "Giới tính NGƯỜI NỘP: Nam/Nữ. Chỉ suy từ danh xưng gắn trực tiếp: Ông=Nam, Bà=Nữ."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND/định danh của NGƯỜI NỘP, chỉ chữ số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp giấy tờ định danh của NGƯỜI NỘP, dd/mm/yyyy."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh của NGƯỜI NỘP."},
    {"name": "NguoiNop_NoiCuTru", "desc": "Nơi cư trú của NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi}. Nếu không có ủy quyền thì sao chép NGUYÊN VẸN ChuHoSo_NoiCuTru, gồm cả thôn/xóm/số nhà trong diaChi; không lấy bản địa chỉ rút gọn từ GCN. Nếu có ủy quyền thì lấy địa chỉ của BÊN ĐƯỢC ỦY QUYỀN."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại của NGƯỜI NỘP, chỉ chữ số. Không lấy số của chủ hồ sơ khi hai người khác nhau."},
    {"name": "NguoiNop_Email", "desc": "Email của NGƯỜI NỘP nếu có."},
    {"name": "Don_NoiDungDeNghi", "desc": "Nội dung đề nghị tại mục 5 của Đơn Mẫu 04. Giữ đúng nội dung người dân khai, không tự suy diễn."},
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
