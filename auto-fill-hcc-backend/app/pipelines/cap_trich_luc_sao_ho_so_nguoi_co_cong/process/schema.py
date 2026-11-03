"""Compact schema cho "Cấp trích lục hoặc sao hồ sơ người có công với cách mạng" (1.010828).

LLM chỉ trả FACT NGUỒN đọc từ giấy tờ (Đơn đề nghị + CCCD). Mapper map sang field Form.io `data[...]` theo
"Mapping - Cấp trích lục hồ sơ NCC - Bộ Nội vụ.xlsx": Phần I người nộp, Phần II chủ hồ sơ, bảng "Hồ sơ kèm theo
gồm" (datagrid hoSoDinhKem). Form KHÔNG có mẫu khai đơn riêng như 1.010814 → mỗi key chỉ xuất hiện 1 lần.
"""

FIELDS: list[dict] = [
    # Đơn đề nghị — nguồn thứ hai cho nhân thân, nguồn duy nhất cho SĐT.
    {
        "name": "Don_TieuDe",
        "desc": (
            "Tiêu đề Đơn đề nghị, nguyên văn kèm phần viết tay ở chỗ trống (vd 'ĐƠN ĐỀ NGHỊ cấp trích lục hồ sơ "
            "người có công', 'ĐƠN ĐỀ NGHỊ Di chuyển hồ sơ trợ cấp một lần')."
        ),
    },
    {"name": "Don_HoTen", "desc": "Họ và tên người làm đơn, dòng 'Họ và tên' của Đơn."},
    {"name": "Don_NgaySinh", "desc": "Ngày tháng năm sinh người làm đơn, dd/mm/yyyy."},
    {"name": "Don_GioiTinh", "desc": 'Giới tính người làm đơn, dòng "Nam/Nữ": "Nam" hoặc "Nữ".'},
    {"name": "Don_SoDinhDanh", "desc": "Số CCCD/CMND người làm đơn, dòng 'CCCD/CMND số'. Chỉ chữ số."},
    {"name": "Don_NgayCap", "desc": "Dòng 'Ngày cấp' của Đơn, dd/mm/yyyy."},
    {"name": "Don_NoiCap", "desc": "Dòng 'Nơi cấp' của Đơn, nguyên văn."},
    {"name": "Don_NoiThuongTru", "desc": "Dòng 'Nơi thường trú' của Đơn, object {quocGia,tinh,xa,chiTietDuoiXa}."},
    {"name": "Don_DienThoai", "desc": "Dòng 'Số điện thoại' của Đơn, chỉ chữ số."},
    # CCCD người làm đơn — nguồn ưu tiên cho nhân thân và địa chỉ.
    {"name": "Person1_HoTen", "desc": "Họ, chữ đệm và tên khai sinh trên CCCD/thẻ căn cước."},
    {"name": "Person1_SoDinhDanh", "desc": "Số định danh cá nhân trên CCCD (12 chữ số)."},
    {"name": "Person1_NgaySinh", "desc": "Ngày sinh trên CCCD, dd/mm/yyyy."},
    {"name": "Person1_GioiTinh", "desc": 'Giới tính trên CCCD: "Nam" hoặc "Nữ".'},
    {"name": "Person1_NgayCap", "desc": "Ngày cấp CCCD, dd/mm/yyyy. Không lấy ngày sinh/ngày hết hạn."},
    {"name": "Person1_NoiCap", "desc": "Cơ quan cấp CCCD (thẻ CĂN CƯỚC mẫu mới in 'BỘ CÔNG AN')."},
    {"name": "Person1_NoiCuTru", "desc": "Nơi cư trú trên CCCD, object {quocGia,tinh,xa,chiTietDuoiXa}."},
    # Người nộp = người đăng nhập VNeID, KHÁC người làm đơn (nộp thay). Chỉ trích từ giấy tờ mà khối
    # <nguoi_nop_context> chỉ ra; tự nộp hoặc không có giấy tờ của người nộp thì bỏ trống.
    {"name": "NguoiNop_HoTen", "desc": "Họ tên NGƯỜI NỘP (nộp thay) trên CCCD của chính người đó."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/định danh NGƯỜI NỘP. Chỉ chữ số."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh NGƯỜI NỘP, dd/mm/yyyy."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính NGƯỜI NỘP: "Nam" hoặc "Nữ".'},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD NGƯỜI NỘP, dd/mm/yyyy. Không lấy ngày sinh/ngày hết hạn."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp CCCD NGƯỜI NỘP."},
    {
        "name": "NguoiNop_NoiCuTru",
        "desc": "Nơi thường trú/cư trú NGƯỜI NỘP trên CCCD của người đó, object {quocGia,tinh,xa,chiTietDuoiXa}.",
    },
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Don_NgaySinh", "Don_NgayCap", "Person1_NgaySinh", "Person1_NgayCap", "NguoiNop_NgaySinh",
              "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Don_NoiThuongTru", "Person1_NoiCuTru", "NguoiNop_NoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

MAX_HO_SO_ROWS = 4

UI_COMP_BY_NAME = {
    # Phần I — người nộp. chonDoiTuong/fullname/birthday/identityNumber cổng khoá theo tài khoản VNeID → chỉ phát
    # ở chế độ "Lấy người nộp theo tờ khai" (fullname/identityNumber kèm enableInput).
    "data[chonDoiTuong]": "dom-select",
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[identityNumber]": "dom-input",
    "data[gender]": "dom-select",
    "data[identityDate]": "dom-date",
    "data[idIssuePlace]": "dom-input",
    "data[province]": "dom-select",
    "data[district]": "dom-select",  # Nhãn Phường/Xã.
    "data[address]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[isOwnerDossierCheck]": "dom-checkbox",
    # Phần II — chủ hồ sơ (người làm đơn).
    "data[chonDoiTuong1]": "dom-select",
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
    "data[ownerNation]": "dom-select",
}
for _i in range(MAX_HO_SO_ROWS):
    UI_COMP_BY_NAME[f"data[hoSoDinhKem][{_i}][textField1]"] = "dom-input"
    UI_COMP_BY_NAME[f"data[hoSoDinhKem][{_i}][textField2]"] = "dom-input"
