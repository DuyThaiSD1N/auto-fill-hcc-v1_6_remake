"""Schema hai vai trò cho thủ tục mai táng người hưởng hưu trí xã hội.

- ChuHoSo: cá nhân/hộ gia đình đứng ra mai táng tại mục II.2 Mẫu số 04.
- NguoiNop: người thực sự nộp hồ sơ, chỉ khi tài liệu khớp mỏ neo UI.

Người chết ở mục I không phải chủ thể của hai khối UI và không được trích.
"""

FIELDS: list[dict] = [
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên CHỦ HỒ SƠ: chủ hộ/người đại diện đứng ra mai táng tại mục II.2.a Mẫu số 04. Không lấy họ tên người chết ở mục I.",
    },
    {
        "name": "ChuHoSo_NgaySinh",
        "desc": "Ngày sinh chủ hồ sơ tại mục II.2, dd/mm/yyyy; ưu tiên CCCD đúng người nếu có giấy tờ riêng rõ hơn.",
    },
    {
        "name": "ChuHoSo_GioiTinh",
        "desc": 'Giới tính chủ hồ sơ, chỉ "Nam" hoặc "Nữ" khi tài liệu của đúng người ghi rõ; không suy từ tên hoặc quan hệ.',
    },
    {
        "name": "ChuHoSo_SoDinhDanh",
        "desc": "Số CMND/CCCD/số định danh của chủ hồ sơ ở mục II.2; chỉ giữ chữ số. Có CCCD đúng người thì ưu tiên số trên CCCD.",
    },
    {
        "name": "ChuHoSo_NgayCap",
        "desc": "Ngày cấp giấy tờ định danh của chủ hồ sơ, dd/mm/yyyy, lấy từ mục II.2 hoặc giấy tờ đúng người khi OCR ghi rõ.",
    },
    {
        "name": "ChuHoSo_NoiCap",
        "desc": "Nơi cấp giấy tờ định danh của chủ hồ sơ từ mục II.2 hoặc giấy tờ đúng người; không lấy chữ trên logo/dấu.",
    },
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": "Hộ khẩu thường trú/Nơi ở của chủ hồ sơ tại mục II.2, object {quocGia,tinh,xa,diaChi}. Ưu tiên tờ khai; giấy tờ khác chỉ bổ sung khi cả hai dòng địa chỉ mục II.2 trống.",
    },
    {
        "name": "ChuHoSo_DienThoai",
        "desc": "Số điện thoại của chủ hồ sơ tại mục II.2 nếu có.",
    },
    {
        "name": "ChuHoSo_QuocTich",
        "desc": "Quốc tịch chủ hồ sơ khi giấy tờ của đúng người ghi rõ.",
    },
    {
        "name": "NguoiNop_HoTen",
        "desc": "Họ tên NGƯỜI NỘP HỒ SƠ khác chủ hồ sơ, chỉ trả khi requester_context xác nhận tài liệu của người này khớp UI.",
    },
    {
        "name": "NguoiNop_NgaySinh",
        "desc": "Ngày sinh người nộp, dd/mm/yyyy, lấy từ đúng giấy tờ hoặc khối người nộp đã được requester_context xác nhận.",
    },
    {
        "name": "NguoiNop_GioiTinh",
        "desc": 'Giới tính người nộp, chỉ "Nam" hoặc "Nữ" khi tài liệu ghi rõ; không suy từ tên hoặc quan hệ.',
    },
    {
        "name": "NguoiNop_SoDinhDanh",
        "desc": "Số CMND/CCCD/số định danh người nộp; phải thuộc tài liệu khớp mỏ neo UI.",
    },
    {
        "name": "NguoiNop_NgayCap",
        "desc": "Ngày cấp giấy tờ người nộp, dd/mm/yyyy, chỉ khi tài liệu đúng người ghi rõ.",
    },
    {
        "name": "NguoiNop_NoiCap",
        "desc": "Nơi cấp giấy tờ người nộp, chỉ lấy từ tài liệu đúng người; không tự suy.",
    },
    {
        "name": "NguoiNop_NoiCuTru",
        "desc": "Nơi cư trú người nộp, object {quocGia,tinh,xa,diaChi}, chỉ lấy từ tài liệu đúng người.",
    },
    {
        "name": "NguoiNop_DienThoai",
        "desc": "Số điện thoại người nộp nếu tài liệu đúng người ghi rõ.",
    },
    {
        "name": "NguoiNop_QuocTich",
        "desc": "Quốc tịch người nộp khi tài liệu đúng người ghi rõ.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "ChuHoSo_NgaySinh",
    "ChuHoSo_NgayCap",
    "NguoiNop_NgaySinh",
    "NguoiNop_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    "data[isOwnerDossierCheck]": "dom-checkbox",

    # Người nộp hồ sơ.
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

    # Chủ hồ sơ.
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
