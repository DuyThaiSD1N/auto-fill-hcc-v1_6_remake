"""Compact schema for "Thực hiện, điều chỉnh, thôi hưởng trợ cấp hưu trí xã hội".

Hợp đồng nguồn chỉ có tối đa hai chủ thể nghiệp vụ:
- ChuHoSo: người đề nghị/người đang hưởng tại mục I Mẫu số 01.
- NguoiNop: người thực sự nộp hồ sơ, đã khớp mỏ neo tên + CCCD từ UI.

LLM hợp nhất dữ liệu của cùng một chủ thể từ Mẫu số 01 và CCCD. Mapper chỉ xác
thực lại vai trò bằng formContext rồi đổi sang tên field của eForm.
"""

FIELDS: list[dict] = [
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên CHỦ HỒ SƠ: người đề nghị/người đang hưởng tại mục I Mẫu số 01. Nếu có CCCD khớp số định danh thì ưu tiên chính tả họ tên trên CCCD.",
    },
    {
        "name": "ChuHoSo_NgaySinh",
        "desc": "Ngày sinh chủ hồ sơ, dd/mm/yyyy. Ưu tiên CCCD khớp chủ hồ sơ; nếu không có thì lấy đúng mục I Mẫu số 01.",
    },
    {
        "name": "ChuHoSo_GioiTinh",
        "desc": 'Giới tính chủ hồ sơ, chỉ "Nam" hoặc "Nữ" khi CCCD hoặc mục I ghi rõ; không suy từ họ tên.',
    },
    {
        "name": "ChuHoSo_SoDinhDanh",
        "desc": "Số định danh/CCCD/CMND chủ hồ sơ. Ưu tiên CCCD khớp người tại mục I; có thể đọc từ MRZ.",
    },
    {
        "name": "ChuHoSo_NgayCap",
        "desc": "Ngày cấp giấy tờ chủ hồ sơ, dd/mm/yyyy, chỉ khi OCR có ngày rõ. Ưu tiên mặt sau CCCD khớp chủ hồ sơ; không đảo hoặc đoán ngày mơ hồ.",
    },
    {
        "name": "ChuHoSo_NoiCap",
        "desc": "Nơi cấp giấy tờ chủ hồ sơ, chỉ lấy khi CCCD hoặc mục I ghi rõ; không tự suy từ ngày cấp.",
    },
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": "Địa chỉ chủ hồ sơ, object {quocGia,tinh,xa,diaChi}. Nếu mục I Mẫu số 01 có Nơi cư trú/Địa chỉ liên lạc thì BẮT BUỘC lấy trọn địa chỉ tại mục I, không lấy địa chỉ CCCD. Tách theo thứ tự chi tiết → xã/phường → tỉnh; CCCD chỉ bổ sung khi cả hai dòng địa chỉ mục I đều trống.",
    },
    {
        "name": "ChuHoSo_DienThoai",
        "desc": "Số điện thoại chủ hồ sơ tại mục I Mẫu số 01 nếu đọc được; CCCD không có số điện thoại.",
    },
    {
        "name": "ChuHoSo_QuocTich",
        "desc": "Quốc tịch chủ hồ sơ khi giấy tờ ghi rõ.",
    },
    {
        "name": "NguoiNop_HoTen",
        "desc": "Họ tên NGƯỜI NỘP HỒ SƠ. Khi requester_context xác nhận section II khớp UI thì BẮT BUỘC trả field này từ mục II; ưu tiên chính tả CCCD riêng khớp nếu có.",
    },
    {
        "name": "NguoiNop_NgaySinh",
        "desc": "Ngày sinh người nộp, dd/mm/yyyy, lấy từ CCCD khớp hoặc mục II Mẫu số 01.",
    },
    {
        "name": "NguoiNop_GioiTinh",
        "desc": 'Giới tính người nộp, chỉ "Nam" hoặc "Nữ" khi tài liệu ghi rõ; không suy từ tên, quan hệ hoặc danh xưng.',
    },
    {
        "name": "NguoiNop_SoDinhDanh",
        "desc": "Số định danh/CCCD/CMND người nộp; phải khớp mỏ neo người nộp từ UI khi UI có số định danh.",
    },
    {
        "name": "NguoiNop_NgayCap",
        "desc": "Ngày cấp giấy tờ người nộp, dd/mm/yyyy, chỉ khi OCR ghi rõ; ưu tiên mặt sau CCCD khớp, sau đó mới đến mục II.",
    },
    {
        "name": "NguoiNop_NoiCap",
        "desc": "Nơi cấp giấy tờ người nộp, chỉ lấy khi tài liệu ghi rõ; không tự suy từ ngày cấp.",
    },
    {
        "name": "NguoiNop_NoiCuTru",
        "desc": "Địa chỉ liên hệ người nộp, object {quocGia,tinh,xa,diaChi}. Ưu tiên mục II Mẫu số 01; CCCD chỉ bổ sung khi mục II thiếu.",
    },
    {
        "name": "NguoiNop_DienThoai",
        "desc": "Số điện thoại người nộp tại mục II Mẫu số 01 nếu đọc được.",
    },
    {
        "name": "NguoiNop_QuocTich",
        "desc": "Quốc tịch người nộp khi giấy tờ ghi rõ.",
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
    # Checkbox action phải đứng trước các field của hai khối.
    "data[isOwnerDossierCheck]": "dom-checkbox",

    # Người nộp hồ sơ.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[idIssuePlace]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",

    # Chủ hồ sơ.
    "data[ownerFullname]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[ownerGender]": "dom-select",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerIdIssuePlace]": "dom-input",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerProvince]": "dom-select",
    "data[ownerDistrict]": "dom-select",
    "data[ownerAddress]": "dom-input",
    "data[ownerNation]": "dom-select",
}
