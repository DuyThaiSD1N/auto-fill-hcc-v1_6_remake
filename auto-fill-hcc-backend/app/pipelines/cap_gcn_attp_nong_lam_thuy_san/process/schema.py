"""Compact schema cho thủ tục cấp GCN ATTP nông, lâm, thủy sản.

LLM chỉ trả facts đọc từ hồ sơ. Mapper chịu trách nhiệm xác định người nộp/chủ hồ sơ
theo ``formContext`` và ánh xạ sang field Form.io của cổng MAE.
"""

FIELDS: list[dict] = [
    # Có thể có CCCD người nộp và CCCD đại diện/chủ cơ sở là hai người khác nhau.
    {"name": "Person1_HoTen", "desc": "Họ tên trên CCCD/CMND/thẻ căn cước của người thứ nhất."},
    {"name": "Person1_SoDinhDanh", "desc": "Số CCCD/CMND/định danh của người thứ nhất; chỉ giữ chữ số."},
    {"name": "Person1_NgaySinh", "desc": "Ngày sinh người thứ nhất trên giấy tờ định danh, dd/mm/yyyy."},
    {"name": "Person1_GioiTinh", "desc": 'Giới tính người thứ nhất: "Nam" hoặc "Nữ".'},
    {"name": "Person1_QuocTich", "desc": "Quốc tịch người thứ nhất; mặc định Việt Nam chỉ khi giấy tờ là CCCD Việt Nam."},
    {"name": "Person1_NgayCap", "desc": "Ngày cấp giấy tờ định danh người thứ nhất, dd/mm/yyyy; không lấy ngày sinh/hết hạn."},
    {"name": "Person1_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh người thứ nhất ở mặt sau thẻ."},
    {"name": "Person1_NoiCuTru", "desc": "Nơi thường trú/cư trú người thứ nhất, object {quocGia,tinh,xa,diaChi}; diaChi không lặp xã/tỉnh."},
    {"name": "Person2_HoTen", "desc": "Họ tên trên CCCD/CMND/thẻ căn cước của người thứ hai nếu có."},
    {"name": "Person2_SoDinhDanh", "desc": "Số CCCD/CMND/định danh của người thứ hai; chỉ giữ chữ số."},
    {"name": "Person2_NgaySinh", "desc": "Ngày sinh người thứ hai trên giấy tờ định danh, dd/mm/yyyy."},
    {"name": "Person2_GioiTinh", "desc": 'Giới tính người thứ hai: "Nam" hoặc "Nữ".'},
    {"name": "Person2_QuocTich", "desc": "Quốc tịch người thứ hai; mặc định Việt Nam chỉ khi giấy tờ là CCCD Việt Nam."},
    {"name": "Person2_NgayCap", "desc": "Ngày cấp giấy tờ định danh người thứ hai, dd/mm/yyyy; không lấy ngày sinh/hết hạn."},
    {"name": "Person2_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh người thứ hai ở mặt sau thẻ."},
    {"name": "Person2_NoiCuTru", "desc": "Nơi thường trú/cư trú người thứ hai, object {quocGia,tinh,xa,diaChi}; diaChi không lặp xã/tỉnh."},

    # Đơn đề nghị Phụ lục I Thông tư 17/2025/TT-BNNMT.
    {"name": "Don_DiaDanh", "desc": "Địa danh ở dòng ngày tháng trên Đơn đề nghị Phụ lục I, không kèm chữ ngày/tháng/năm."},
    {"name": "Don_NgayDon", "desc": "Ngày làm Đơn đề nghị Phụ lục I, dd/mm/yyyy."},
    {"name": "Don_KinhGui", "desc": "Tên đầy đủ cơ quan có thẩm quyền sau nhãn Kính gửi trên Đơn đề nghị."},
    {"name": "Don_TenCoSo", "desc": "Mục 1 - Tên cơ sở sản xuất, kinh doanh trên Đơn; đây là tên cơ sở, không phải mặc định họ tên đại diện."},
    {"name": "Don_DiaChiCoSo", "desc": "Mục 2 - Địa chỉ cơ sở trên Đơn, object {quocGia,tinh,xa,diaChi}; giữ đủ địa chỉ đọc được."},
    {"name": "Don_DienThoai", "desc": "Mục 3 - Điện thoại của cơ sở trên Đơn; không coi là điện thoại người nộp."},
    {"name": "Don_Email", "desc": "Mục 3 - Email của cơ sở trên Đơn nếu có."},
    {"name": "Don_MaSoDKKD", "desc": "Mục 4 - Mã số đăng ký kinh doanh trên Đơn; giữ nguyên chữ và số."},
    {"name": "Don_SoDangKy", "desc": "Mục 5 - Số đăng ký kinh doanh trên Đơn; có thể là cụm như Đăng ký lần đầu nếu đơn ghi vậy."},
    {"name": "Don_NgayCapDKKD", "desc": "Mục 5 - Ngày cấp đăng ký kinh doanh, dd/mm/yyyy."},
    {"name": "Don_NoiCapDKKD", "desc": "Mục 5 - Cơ quan cấp đăng ký kinh doanh."},
    {"name": "Don_MatHang", "desc": "Mục 6 - Mặt hàng sản xuất, kinh doanh trên Đơn."},
    {"name": "Don_LyDoCap", "desc": "Nội dung sau nhãn Lý do cấp trên Đơn, ví dụ Cấp mới; không tự suy diễn nếu bỏ trống."},
    {"name": "Don_DaiDienCoSo", "desc": "Họ tên người tại mục Đại diện cơ sở hoặc người ký cuối Đơn; không lấy tên cơ sở ở mục 1."},

    # Bản thuyết minh Phụ lục II chỉ là nguồn đối chiếu/fallback vì cổng không dựng eForm riêng.
    {"name": "ThuyetMinh_TenCoSo", "desc": "Mục I.1 - Tên cơ sở trong Bản thuyết minh Phụ lục II."},
    {"name": "ThuyetMinh_DiaChiCoSo", "desc": "Mục I.2 - Địa chỉ cơ sở trong Bản thuyết minh, object {quocGia,tinh,xa,diaChi}."},
    {"name": "ThuyetMinh_MatHang", "desc": "Tên sản phẩm/mặt hàng tại Mục II của Bản thuyết minh; gộp ngắn gọn nếu có nhiều dòng."},
    {"name": "ThuyetMinh_DaiDienCoSo", "desc": "Họ tên đại diện cơ sở tại phần ký cuối Bản thuyết minh nếu đọc rõ."},

    # Giấy đăng ký kinh doanh chỉ là nguồn đối chiếu/fallback, không có dòng đính kèm riêng trên cổng.
    {"name": "DangKy_TenCoSo", "desc": "Tên cơ sở/hộ kinh doanh/doanh nghiệp trên Giấy đăng ký kinh doanh."},
    {"name": "DangKy_DiaChiCoSo", "desc": "Địa chỉ trụ sở/địa điểm trên Giấy đăng ký, object {quocGia,tinh,xa,diaChi}."},
    {"name": "DangKy_MaSo", "desc": "Mã số đăng ký kinh doanh/mã số doanh nghiệp/mã số hộ kinh doanh."},
    {"name": "DangKy_SoDangKy", "desc": "Số Giấy chứng nhận đăng ký kinh doanh nếu tách biệt với mã số."},
    {"name": "DangKy_NgayCap", "desc": "Ngày cấp hoặc ngày đăng ký lần đầu trên Giấy đăng ký, dd/mm/yyyy."},
    {"name": "DangKy_NoiCap", "desc": "Cơ quan cấp Giấy đăng ký kinh doanh."},
    {"name": "DangKy_NguoiDaiDien", "desc": "Họ tên chủ hộ/người đại diện theo pháp luật trên Giấy đăng ký."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Person1_NgaySinh", "Person1_NgayCap", "Person2_NgaySinh", "Person2_NgayCap",
    "Don_NgayDon", "Don_NgayCapDKKD", "DangKy_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in (
    "Person1_NoiCuTru", "Person2_NoiCuTru", "Don_DiaChiCoSo",
    "ThuyetMinh_DiaChiCoSo", "DangKy_DiaChiCoSo",
):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    "data[chonDoiTuong]": "dom-select",
    "data[isOwnerDossierCheck]": "dom-checkbox",

    # Phần I - người nộp.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[idIssuePlace]": "dom-input",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[email]": "dom-input",
    "data[fax]": "dom-input",

    # Phần II - chủ hồ sơ/đại diện cơ sở.
    "data[ownerFullname]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[ownerGender]": "dom-select",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerIdIssuePlace]": "dom-input",
    "data[ownerProvince]": "dom-select",
    "data[ownerDistrict]": "dom-select",
    "data[ownerAddress]": "dom-input",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerEmail]": "dom-input",
    "data[ownerFax]": "dom-input",
    "data[ownerNation]": "dom-select",
    "data[ghiChu]": "dom-input",

    # Phần III - eForm Đơn đề nghị Phụ lục I.
    "data[diaDanh]": "dom-select",
    "data[ngayBC]": "dom-date",
    "data[kinhGui1]": "dom-input",
    "data[organization]": "dom-input",
    "data[email2]": "dom-input",
    "data[maso]": "dom-input",
    "data[soGDK]": "dom-input",
    "data[ngayCap]": "dom-date",
    "data[noiCap]": "dom-input",
    "data[mathangsx]": "dom-input",
    "data[lydocaplai]": "dom-input",
    "data[daidiencoso]": "dom-input",
}
