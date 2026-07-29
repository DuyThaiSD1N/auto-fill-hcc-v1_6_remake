"""Compact schema for mai táng phí dân công hỏa tuyến.

The LLM returns OCR-derived facts only. The mapper decides requester/owner roles
from the declaration, uploaded CCCD, and current portal form context.
"""

FIELDS: list[dict] = [
    # CCCD/CMND upload. Usually this is the claimant/requester and dossier owner.
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

    # Bản khai thân nhân theo Quyết định 49/2015/QĐ-TTg. Only extract section 1.
    {"name": "ToKhai_ThanNhanHoTen", "desc": "Họ tên thân nhân/người đứng khai nhận trợ cấp ở mục 1 của bản khai."},
    {"name": "ToKhai_ThanNhanNgaySinh", "desc": "Ngày, tháng, năm sinh thân nhân ở mục 1, dd/mm/yyyy."},
    {"name": "ToKhai_ThanNhanSoDienThoai", "desc": "Số điện thoại thân nhân ở mục 1."},
    {"name": "ToKhai_ThanNhanTruQuan", "desc": "Trú quán/hiện cư trú của thân nhân ở mục 1, object {quocGia,tinh,xa,diaChi}."},
    {"name": "ToKhai_QuanHeNguoiTuTran", "desc": "Quan hệ của thân nhân với người từ trần nếu tờ khai ghi rõ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Person1_NgaySinh",
    "Person1_NgayCap",
    "Person2_NgaySinh",
    "Person2_NgayCap",
    "ToKhai_ThanNhanNgaySinh",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Person1_NoiCuTru", "Person2_NoiCuTru", "ToKhai_ThanNhanTruQuan"):
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

    # Dossier owner section.
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

