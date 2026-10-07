"""Compact facts và contract Form.io cho thủ tục hỗ trợ thiệt hại do dịch bệnh động vật (1.013997).

Phần I (người nộp) lấy từ tài khoản: chỉ được ghi thêm khi chủ hộ trên giấy tờ khớp tài khoản trong
``formContext``. Phần II là chủ hộ chăn nuôi/cơ sở sản xuất bị thiệt hại. Cổng không có ô riêng cho dữ liệu
tiêu hủy nên mapper tóm tắt các Biên bản vào ``data[ghiChu]``.
"""

FIELDS: list[dict] = [
    # Các CCCD vật lý trong file upload, chưa gán vai trò. Mapper dùng formContext để tìm người nộp.
    {"name": "Cccd1_HoTen", "desc": "Họ tên trên thẻ CCCD/căn cước vật lý thứ nhất. Chỉ lấy từ mặt thẻ thật, "
        "không lấy số định danh được nhắc trong Đơn hoặc Biên bản."},
    {"name": "Cccd1_SoDinhDanh", "desc": "Số định danh trên thẻ thứ nhất; chỉ chữ số, có thể đọc từ MRZ."},
    {"name": "Cccd1_NgaySinh", "desc": "Ngày sinh trên thẻ thứ nhất, dd/mm/yyyy."},
    {"name": "Cccd1_GioiTinh", "desc": 'Giới tính trên thẻ thứ nhất: "Nam" hoặc "Nữ".'},
    {"name": "Cccd1_NgayCap", "desc": "Ngày cấp ở mặt sau thẻ thứ nhất, dd/mm/yyyy; không lấy ngày hết hạn."},
    {"name": "Cccd1_NoiCap", "desc": "Cơ quan cấp ở mặt sau thẻ thứ nhất."},
    {"name": "Cccd1_ThuongTru", "desc": "Nơi thường trú trên thẻ thứ nhất, object {quocGia,tinh,xa,diaChi}. "
        "Không lấy quê quán."},
    {"name": "Cccd2_HoTen", "desc": "Họ tên trên thẻ CCCD/căn cước vật lý thứ hai nếu hồ sơ có hai người khác "
        "nhau. Không tự quyết định đây là người nộp hay chủ hộ."},
    {"name": "Cccd2_SoDinhDanh", "desc": "Số định danh trên thẻ thứ hai; chỉ chữ số."},
    {"name": "Cccd2_NgaySinh", "desc": "Ngày sinh trên thẻ thứ hai, dd/mm/yyyy."},
    {"name": "Cccd2_GioiTinh", "desc": 'Giới tính trên thẻ thứ hai: "Nam" hoặc "Nữ".'},
    {"name": "Cccd2_NgayCap", "desc": "Ngày cấp ở mặt sau thẻ thứ hai, dd/mm/yyyy."},
    {"name": "Cccd2_NoiCap", "desc": "Cơ quan cấp ở mặt sau thẻ thứ hai."},
    {"name": "Cccd2_ThuongTru", "desc": "Nơi thường trú trên thẻ thứ hai, object {quocGia,tinh,xa,diaChi}."},

    # Chủ hồ sơ = chủ hộ chăn nuôi / cơ sở sản xuất bị thiệt hại.
    {"name": "ChuHo_HoTen", "desc": "Họ tên CHỦ HỘ CHĂN NUÔI đề nghị hỗ trợ: dòng 'Tôi tên là' của Đơn đề nghị; "
        "không có Đơn thì lấy người ở mục I.3 'Đại diện (chủ hộ chăn nuôi) cơ sở sản xuất có động vật ... buộc "
        "phải tiêu hủy' của Biên bản tiêu hủy. KHÔNG lấy đại diện UBND xã, trưởng bản, trưởng ban CTMT bản "
        "hoặc người ký hộ."},
    {"name": "ChuHo_DanhXung", "desc": "Danh xưng đứng ngay trước tên chủ hộ ở mục I.3 Biên bản: 'Ông' hoặc 'Bà'."},
    {"name": "ChuHo_SoDinhDanh", "desc": "Số Căn cước/CCCD của chủ hộ ghi trên Đơn đề nghị hoặc CCCD đúng người; "
        "chỉ chữ số."},
    {"name": "ChuHo_NgaySinh", "desc": "Ngày sinh chủ hộ, dd/mm/yyyy — chỉ từ CCCD đúng người; Đơn/Biên bản "
        "không ghi thì bỏ."},
    {"name": "ChuHo_NgayCap", "desc": "Ngày cấp CCCD chủ hộ ghi trên Đơn ('Ngày cấp') hoặc mặt sau CCCD, "
        "dd/mm/yyyy."},
    {"name": "ChuHo_NoiCap", "desc": "Nơi cấp CCCD chủ hộ ghi trên Đơn ('Nơi cấp') hoặc mặt sau CCCD."},
    {"name": "ChuHo_ThuongTru", "desc": "Địa chỉ thường trú chủ hộ, object {quocGia,tinh,xa,diaChi}: Đơn "
        "'Địa chỉ thường trú' > Biên bản mục I.3 'Địa chỉ' > CCCD. diaChi chỉ gồm thôn/bản/xóm/số nhà."},
    {"name": "ChuHo_DienThoai", "desc": "Số điện thoại trên Đơn đề nghị; dòng chấm/bỏ trống thì bỏ field."},
    {"name": "CoSo_Ten", "desc": "Tên cơ sở sản xuất ghi ở dòng 'Tên cơ sở sản xuất (nếu có)' của Đơn. Dòng "
        "chấm/bỏ trống thì bỏ field; không lấy tên chủ hộ thay thế."},
    {"name": "CoSo_MaSoThue", "desc": "Mã số thuế/mã số doanh nghiệp/HTX của cơ sở nếu giấy tờ ghi; không bịa."},

    # Thiệt hại.
    {"name": "DichBenh_Ten", "desc": "Tên dịch bệnh ghi trên Biên bản/Đơn, ví dụ 'Bệnh Dịch tả lợn Châu Phi'."},
    {"name": "BienBan_DanhSach", "desc": "MẢNG mọi Biên bản tiêu hủy động vật trong hồ sơ, theo thứ tự trang, "
        "mỗi phần tử {so, ngay, doiTuong:[{ten, soLuong, khoiLuong}], tongSoLuong, tongKhoiLuong}. so chép "
        "nguyên văn sau 'Số:' (vd '12/BBTH'); ngay là ngày ở dòng 'Hôm nay ... ngày ... tháng ... năm', "
        "dd/mm/yyyy; doiTuong chỉ gồm các dòng 'Đối tượng tiêu hủy' có ghi tên (bỏ dòng chấm); soLuong là số "
        "con (vd '01'), khoiLuong là số kg (vd '57'). Đơn đề nghị nhắc lại số biên bản thì KHÔNG tạo phần tử mới "
        "nếu đã có Biên bản đó; chỉ có Đơn thì lấy theo Đơn."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Cccd1_NgaySinh", "Cccd1_NgayCap", "Cccd2_NgaySinh", "Cccd2_NgayCap", "ChuHo_NgaySinh",
              "ChuHo_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Cccd1_ThuongTru", "Cccd2_ThuongTru", "ChuHo_ThuongTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    "data[chonDoiTuong]": "dom-select",
    "data[organization]": "dom-input",
    "data[taxCode]": "dom-input",
    # Phần I chỉ được mapper trả khi chủ hộ khớp tài khoản đang đăng nhập.
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
    "data[isOwnerDossierCheck]": "dom-checkbox",
    "data[ownerOrganizationFullname]": "dom-input",
    "data[ownerTaxCode]": "dom-input",
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
    "data[ownerNation]": "dom-select",
    "data[ghiChu]": "dom-input",
}
