"""Compact schema for food safety certificate procedure.

The LLM returns OCR-derived source facts only. The mapper decides requester vs
dossier owner from the portal form context, then emits Form.io DOM actions.
"""

FIELDS: list[dict] = [
    # CCCD/CMND uploads. There can be one requester CCCD, or requester + owner.
    {"name": "Person1_HoTen", "desc": "Họ tên trên CCCD/CMND của người thứ nhất."},
    {"name": "Person1_SoDinhDanh", "desc": "Số định danh/CCCD/CMND người thứ nhất; có thể đọc từ MRZ mặt sau."},
    {"name": "Person1_NgaySinh", "desc": "Ngày sinh người thứ nhất, dd/mm/yyyy."},
    {"name": "Person1_GioiTinh", "desc": 'Giới tính người thứ nhất: "Nam" hoặc "Nữ".'},
    {"name": "Person1_QuocTich", "desc": "Quốc tịch nếu giấy tờ ghi rõ hoặc khác Việt Nam."},
    {"name": "Person1_NgayCap", "desc": "Ngày cấp CCCD/CMND người thứ nhất, dd/mm/yyyy."},
    {"name": "Person1_NoiCap", "desc": "Nơi cấp CCCD/CMND người thứ nhất."},
    {"name": "Person1_NoiCuTru", "desc": "Nơi thường trú/cư trú trên CCCD, object {quocGia,tinh,xa,diaChi}."},

    {"name": "Person2_HoTen", "desc": "Họ tên trên CCCD/CMND của người thứ hai, nếu có."},
    {"name": "Person2_SoDinhDanh", "desc": "Số định danh/CCCD/CMND người thứ hai; có thể đọc từ MRZ mặt sau."},
    {"name": "Person2_NgaySinh", "desc": "Ngày sinh người thứ hai, dd/mm/yyyy."},
    {"name": "Person2_GioiTinh", "desc": 'Giới tính người thứ hai: "Nam" hoặc "Nữ".'},
    {"name": "Person2_QuocTich", "desc": "Quốc tịch nếu giấy tờ ghi rõ hoặc khác Việt Nam."},
    {"name": "Person2_NgayCap", "desc": "Ngày cấp CCCD/CMND người thứ hai, dd/mm/yyyy."},
    {"name": "Person2_NoiCap", "desc": "Nơi cấp CCCD/CMND người thứ hai."},
    {"name": "Person2_NoiCuTru", "desc": "Nơi thường trú/cư trú trên CCCD, object {quocGia,tinh,xa,diaChi}."},

    # Đơn đề nghị cấp Giấy chứng nhận cơ sở đủ điều kiện ATTP.
    {"name": "DonDeNghi_ChuCoSoHoTen", "desc": "Họ tên chủ cơ sở/chủ hồ sơ trong Đơn đề nghị cấp giấy chứng nhận ATTP."},
    {"name": "DonDeNghi_TenCoSo", "desc": "Tên cơ sở kinh doanh/sản xuất thực phẩm trong đơn."},
    {"name": "DonDeNghi_DiaChiChuCoSo", "desc": "Địa chỉ cư trú của chủ cơ sở nếu đơn có ghi riêng, object {quocGia,tinh,xa,diaChi}."},
    {"name": "DonDeNghi_DiaChiCoSo", "desc": "Địa chỉ cơ sở kinh doanh/sản xuất thực phẩm, object {quocGia,tinh,xa,diaChi} nếu tách được."},
    {"name": "DonDeNghi_DienThoai", "desc": "Số điện thoại liên hệ trong đơn đề nghị; chỉ trả số di động rõ ràng."},
    {"name": "DonDeNghi_NganhNghe", "desc": "Nội dung/ngành nghề đề nghị cấp giấy chứng nhận, ví dụ kinh doanh dịch vụ ăn uống."},

    # Giấy khám sức khỏe đi kèm hồ sơ ATTP.
    {"name": "GiayKham_HoTen", "desc": "Họ tên trên Giấy khám sức khỏe."},
    {"name": "GiayKham_NgaySinh", "desc": "Ngày sinh trên Giấy khám sức khỏe, dd/mm/yyyy."},
    {"name": "GiayKham_GioiTinh", "desc": 'Giới tính trên Giấy khám sức khỏe: "Nam" hoặc "Nữ".'},
    {"name": "GiayKham_SoDinhDanh", "desc": "Số CCCD/CMND trên Giấy khám sức khỏe."},
    {"name": "GiayKham_NgayCap", "desc": "Ngày cấp CCCD/CMND ghi trên Giấy khám sức khỏe, dd/mm/yyyy."},
    {"name": "GiayKham_NoiCap", "desc": "Nơi cấp CCCD/CMND ghi trên Giấy khám sức khỏe."},
    {"name": "GiayKham_NoiOHienTai", "desc": "Nơi ở hiện tại/nơi cư trú trên Giấy khám sức khỏe, object {quocGia,tinh,xa,diaChi}."},
    {"name": "GiayKham_KetLuan", "desc": "Kết luận sức khỏe nếu đọc chắc chắn, ví dụ sức khỏe loại II."},

    # Optional: if a true medical assessment record is uploaded in another case.
    {"name": "GiamDinh_HoTen", "desc": "Họ tên người trong Biên bản/Kết luận giám định y khoa nếu có."},
    {"name": "GiamDinh_NgaySinh", "desc": "Ngày sinh trong Biên bản/Kết luận giám định y khoa, dd/mm/yyyy."},
    {"name": "GiamDinh_GioiTinh", "desc": 'Giới tính trong Biên bản/Kết luận giám định y khoa: "Nam" hoặc "Nữ".'},
    {"name": "GiamDinh_SoDinhDanh", "desc": "Số CCCD/CMND trong Biên bản/Kết luận giám định y khoa nếu có."},
    {"name": "GiamDinh_NgayCap", "desc": "Ngày cấp giấy tờ định danh trong Biên bản/Kết luận giám định y khoa nếu có."},
    {"name": "GiamDinh_NoiCap", "desc": "Nơi cấp giấy tờ định danh trong Biên bản/Kết luận giám định y khoa nếu có."},
    {"name": "GiamDinh_NoiCuTru", "desc": "Nơi thường trú/cư trú trong Biên bản/Kết luận giám định y khoa, object {quocGia,tinh,xa,diaChi}."},
    {"name": "GiamDinh_MucDo", "desc": "Mức độ khuyết tật/suy giảm nếu tài liệu giám định ghi rõ; không suy từ giấy khám sức khỏe."},
    {"name": "GiamDinh_KetLuan", "desc": "Kết luận chính của Biên bản/Kết luận giám định y khoa nếu có."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Person1_NgaySinh",
    "Person1_NgayCap",
    "Person2_NgaySinh",
    "Person2_NgayCap",
    "GiayKham_NgaySinh",
    "GiayKham_NgayCap",
    "GiamDinh_NgaySinh",
    "GiamDinh_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in (
    "Person1_NoiCuTru",
    "Person2_NoiCuTru",
    "DonDeNghi_DiaChiChuCoSo",
    "DonDeNghi_DiaChiCoSo",
    "GiayKham_NoiOHienTai",
    "GiamDinh_NoiCuTru",
):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
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
    "data[fax]": "dom-input",

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
    "data[ownerFax]": "dom-input",
    "data[ownerNation]": "dom-select",
    "data[ghiChu]": "dom-input",
}

