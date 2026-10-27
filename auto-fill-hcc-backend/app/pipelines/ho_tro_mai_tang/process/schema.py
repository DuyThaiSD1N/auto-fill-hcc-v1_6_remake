"""Schema ba nhóm người cho thủ tục hỗ trợ chi phí mai táng.

- NguoiMat: người chết được tổ chức mai táng — là CHỦ HỒ SƠ trên cổng (mọi tài khoản).
- ChuHoSo: cá nhân/thân nhân đứng ra mai táng (mục II.2 Mẫu số 04, mục 1/3.1 Mẫu số 02/03) — chỉ còn là
  ứng viên người nộp; tên nhóm giữ như pipeline hưu trí xã hội cho đồng bộ.
- NguoiNop: người thực sự nộp hồ sơ, chỉ khi tài liệu khớp mỏ neo UI.
"""

FIELDS: list[dict] = [
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên NGƯỜI ĐỨNG RA MAI TÁNG: chủ hộ/người đại diện tại mục II.2.a Mẫu số 04 (mục 3.1 Mẫu số 02/03). Không lấy họ tên người chết.",
    },
    {
        "name": "ChuHoSo_NgaySinh",
        "desc": "Ngày sinh người đứng ra mai táng tại mục II.2, dd/mm/yyyy; ưu tiên CCCD đúng người nếu có giấy tờ riêng rõ hơn.",
    },
    {
        "name": "ChuHoSo_GioiTinh",
        "desc": 'Giới tính người đứng ra mai táng, chỉ "Nam" hoặc "Nữ" khi tài liệu của đúng người ghi rõ; không suy từ tên hoặc quan hệ.',
    },
    {
        "name": "ChuHoSo_SoDinhDanh",
        "desc": "Số CMND/CCCD/số định danh của người đứng ra mai táng ở mục II.2; chỉ giữ chữ số. Có CCCD đúng người thì ưu tiên số trên CCCD.",
    },
    {
        "name": "ChuHoSo_NgayCap",
        "desc": "Ngày cấp giấy tờ định danh của người đứng ra mai táng, dd/mm/yyyy, lấy từ mục II.2 hoặc CCCD đúng người khi OCR ghi rõ.",
    },
    {
        "name": "ChuHoSo_NoiCap",
        "desc": "Nơi cấp giấy tờ định danh của người đứng ra mai táng từ mục II.2 hoặc CCCD đúng người; không lấy chữ trên logo/dấu.",
    },
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": "Hộ khẩu thường trú/Nơi ở của người đứng ra mai táng tại mục II.2, object {quocGia,tinh,xa,chiTietDuoiXa}. Ưu tiên tờ khai; CCCD chỉ bổ sung khi cả hai dòng địa chỉ mục II.2 trống.",
    },
    {
        "name": "ChuHoSo_DienThoai",
        "desc": "Số điện thoại của người đứng ra mai táng tại mục II.2 nếu có.",
    },
    {
        "name": "ChuHoSo_QuocTich",
        "desc": "Quốc tịch người đứng ra mai táng khi giấy tờ của đúng người ghi rõ.",
    },
    {
        "name": "NguoiNop_HoTen",
        "desc": "Họ tên NGƯỜI NỘP HỒ SƠ khác người đứng ra mai táng, chỉ trả khi requester_context xác nhận tài liệu của người này khớp UI.",
    },
    {
        "name": "NguoiNop_NgaySinh",
        "desc": "Ngày sinh người nộp, dd/mm/yyyy, lấy từ đúng CCCD/CMND hoặc khối người nộp đã được requester_context xác nhận.",
    },
    {
        "name": "NguoiNop_GioiTinh",
        "desc": 'Giới tính người nộp, chỉ "Nam" hoặc "Nữ" khi tài liệu ghi rõ; không suy từ tên.',
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
        "desc": "Nơi cư trú người nộp, object {quocGia,tinh,xa,chiTietDuoiXa}, chỉ lấy từ tài liệu đúng người.",
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

# Người chết là chủ hồ sơ trên cổng (giống cờ deceasedAsOwner của hưu trí xã hội, ở đây áp mọi tài khoản).
FIELDS += [
    {
        "name": "NguoiMat_HoTen",
        "desc": "Họ tên NGƯỜI CHẾT được tổ chức mai táng (mục thông tin người chết của tờ khai hoặc khối chính của Trích lục khai tử).",
    },
    {
        "name": "NguoiMat_NgaySinh",
        "desc": "Ngày sinh người chết, dd/mm/yyyy; ưu tiên Trích lục khai tử/giấy tờ định danh của người chết.",
    },
    {
        "name": "NguoiMat_GioiTinh",
        "desc": 'Giới tính người chết, chỉ "Nam" hoặc "Nữ" khi tài liệu ghi rõ.',
    },
    {
        "name": "NguoiMat_SoDinhDanh",
        "desc": "Số định danh/CCCD của người chết; chỉ giữ chữ số.",
    },
    {
        "name": "NguoiMat_NgayCap",
        "desc": "Ngày cấp giấy tờ định danh của người chết, dd/mm/yyyy, khi tài liệu ghi rõ.",
    },
    {
        "name": "NguoiMat_NoiCap",
        "desc": "Nơi cấp giấy tờ định danh của người chết; không lấy chữ trên logo/dấu.",
    },
    {
        "name": "NguoiMat_NoiCuTru",
        "desc": "Nơi cư trú của người chết trên tờ khai, object {quocGia,tinh,xa,chiTietDuoiXa}. Không lấy Nơi chết.",
    },
    {
        "name": "NguoiMat_QuocTich",
        "desc": "Quốc tịch người chết khi tài liệu ghi rõ.",
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
    "NguoiMat_NgaySinh",
    "NguoiMat_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru", "NguoiMat_NoiCuTru"):
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
