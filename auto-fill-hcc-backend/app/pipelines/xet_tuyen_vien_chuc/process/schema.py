"""Compact schema for "Thủ tục xét tuyển Viên chức (85/2023/NĐ-CP)".

The LLM returns OCR-derived source facts only. The mapper compares the candidate
in the application form with the applicant currently prefilled by the portal,
then emits Form.io DOM actions for requester and dossier owner fields.
"""

FIELDS: list[dict] = [
    # CCCD/CMND upload. This is usually the requester when requester != dossier owner.
    {"name": "Person1_HoTen", "desc": "Họ tên trên CCCD/CMND của người thứ nhất."},
    {"name": "Person1_SoDinhDanh", "desc": "Số định danh/CCCD/CMND người thứ nhất; có thể đọc từ MRZ mặt sau."},
    {"name": "Person1_NgaySinh", "desc": "Ngày sinh người thứ nhất, dd/mm/yyyy."},
    {"name": "Person1_GioiTinh", "desc": 'Giới tính người thứ nhất: "Nam" hoặc "Nữ".'},
    {"name": "Person1_QuocTich", "desc": "Quốc tịch nếu giấy tờ ghi rõ hoặc khác Việt Nam."},
    {"name": "Person1_NgayCap", "desc": "Ngày cấp CCCD/CMND người thứ nhất, dd/mm/yyyy."},
    {"name": "Person1_NoiCap", "desc": "Nơi cấp CCCD/CMND người thứ nhất."},
    {"name": "Person1_NoiCuTru", "desc": "Nơi thường trú/cư trú trên CCCD, object {quocGia,tinh,xa,diaChi} nếu đọc chắc chắn."},

    {"name": "Person2_HoTen", "desc": "Họ tên trên CCCD/CMND của người thứ hai, nếu có."},
    {"name": "Person2_SoDinhDanh", "desc": "Số định danh/CCCD/CMND người thứ hai; có thể đọc từ MRZ mặt sau."},
    {"name": "Person2_NgaySinh", "desc": "Ngày sinh người thứ hai, dd/mm/yyyy."},
    {"name": "Person2_GioiTinh", "desc": 'Giới tính người thứ hai: "Nam" hoặc "Nữ".'},
    {"name": "Person2_QuocTich", "desc": "Quốc tịch nếu giấy tờ ghi rõ hoặc khác Việt Nam."},
    {"name": "Person2_NgayCap", "desc": "Ngày cấp CCCD/CMND người thứ hai, dd/mm/yyyy."},
    {"name": "Person2_NoiCap", "desc": "Nơi cấp CCCD/CMND người thứ hai."},
    {"name": "Person2_NoiCuTru", "desc": "Nơi thường trú/cư trú trên CCCD, object {quocGia,tinh,xa,diaChi} nếu đọc chắc chắn."},

    # Phiếu đăng ký dự tuyển - source of truth for dossier owner/candidate.
    {"name": "Phieu_HoTen", "desc": "Họ tên người đăng ký dự tuyển/chủ hồ sơ trong Phiếu đăng ký dự tuyển."},
    {"name": "Phieu_NgaySinh", "desc": "Ngày sinh người đăng ký dự tuyển, dd/mm/yyyy."},
    {"name": "Phieu_GioiTinh", "desc": 'Giới tính người đăng ký dự tuyển: "Nam" hoặc "Nữ" nếu phiếu ghi rõ.'},
    {"name": "Phieu_SoDinhDanh", "desc": "Số CCCD/CMND/hộ chiếu của người đăng ký dự tuyển trên phiếu."},
    {"name": "Phieu_NgayCap", "desc": "Ngày cấp giấy tờ định danh của người đăng ký dự tuyển trên phiếu, dd/mm/yyyy."},
    {"name": "Phieu_NoiCap", "desc": "Nơi cấp giấy tờ định danh của người đăng ký dự tuyển trên phiếu."},
    {"name": "Phieu_HoKhau", "desc": "Thông tin về hộ khẩu của người đăng ký dự tuyển, object {quocGia,tinh,xa,diaChi}."},
    {"name": "Phieu_DiaChiNhanThongBao", "desc": "Địa chỉ nhận thông báo trong phiếu, object {quocGia,tinh,xa,diaChi}; chỉ dùng khi không có hộ khẩu."},
    {"name": "Phieu_DienThoai", "desc": "Số điện thoại liên hệ của người đăng ký dự tuyển nếu có."},
    {"name": "Phieu_Email", "desc": "Email của người đăng ký dự tuyển nếu có."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Person1_NgaySinh",
    "Person1_NgayCap",
    "Person2_NgaySinh",
    "Person2_NgayCap",
    "Phieu_NgaySinh",
    "Phieu_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Person1_NoiCuTru", "Person2_NoiCuTru", "Phieu_HoKhau", "Phieu_DiaChiNhanThongBao"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    # Checkbox action must be emitted before owner/requester fields.
    "data[isOwnerDossierCheck]": "dom-checkbox",

    # Requester section.
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

    # Dossier owner/candidate section.
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
}
