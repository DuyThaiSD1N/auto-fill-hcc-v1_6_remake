"""Compact facts và contract Form.io cho thủ tục Hòa giải tranh chấp đất đai (1.012812).

Field-key lấy theo file mapping (3 DOM Cá nhân / Tổ chức-Doanh nghiệp / Cơ quan nhà nước, cùng một bộ key):
Phần I người nộp ``data[fullname]``…``data[district]``/``data[address]`` (họ tên, ngày sinh, CCCD đổ sẵn theo tài
khoản; CCCD khoá), Phần II chủ hồ sơ ``data[owner*]``, ô ``data[ghiChu]``. Nguồn: Đơn yêu cầu hòa giải (nguồn chính
về người yêu cầu), CCCD, sổ hộ khẩu, hợp đồng ủy quyền, giấy chuyển nhượng, bản mô tả ranh giới, phiếu đo đạc.
"""

_CARD_FIELDS = (
    ("HoTen", "Họ tên trên thẻ CCCD/căn cước/CMND vật lý {n}. Chỉ lấy từ mặt thẻ thật, không lấy tên nhắc trong Đơn."),
    ("SoDinhDanh", "Số định danh/số CCCD trên thẻ {n}; chỉ chữ số."),
    ("NgaySinh", "Ngày sinh trên thẻ {n}, dd/mm/yyyy."),
    ("GioiTinh", 'Giới tính trên thẻ {n}: "Nam" hoặc "Nữ".'),
    ("NgayCap", "Ngày cấp ở mặt sau thẻ {n}, dd/mm/yyyy; không lấy ngày hết hạn."),
    ("NoiCap", "Cơ quan cấp in trên thẻ {n} (vd 'BỘ CÔNG AN', 'Cục Cảnh sát QLHC về TTXH')."),
    ("ThuongTru", "Nơi thường trú/nơi cư trú trên thẻ {n}, object {{quocGia,tinh,xa,chiTietDuoiXa}}. Không lấy quê quán."),
)

FIELDS: list[dict] = [
    # Người yêu cầu hòa giải = người viết đơn = CHỦ HỒ SƠ.
    {"name": "NguoiYeuCau_LoaiChuThe", "desc": '"Cá nhân" nếu người viết đơn là một người (kể cả đại diện hộ gia đình); '
        '"Tổ chức" nếu là công ty/doanh nghiệp/HTX; "Cơ quan nhà nước" nếu là cơ quan, đơn vị nhà nước.'},
    {"name": "NguoiYeuCau_HoTen", "desc": "Họ tên NGƯỜI YÊU CẦU HÒA GIẢI = người viết đơn: dòng 'Tôi tên'/'Tôi là' và "
        "mục 'Người viết đơn' của Đơn. Tổ chức thì là người đại diện ký đơn. KHÔNG lấy người bị yêu cầu/người tranh "
        "chấp, người được ủy quyền, bên chuyển nhượng, chủ đất liền kề hay cán bộ đo đạc. Chép đúng chữ, giữ dấu."},
    {"name": "NguoiYeuCau_TenToChuc", "desc": "Tên tổ chức/cơ quan đứng đơn (chỉ khi người yêu cầu là tổ chức/cơ quan). "
        "KHÔNG lấy đơn vị đo đạc, văn phòng công chứng, văn phòng đăng ký đất đai."},
    {"name": "NguoiYeuCau_MaSoThue", "desc": "Mã số thuế/mã số doanh nghiệp/HTX của tổ chức đứng đơn; chỉ chữ số. Không "
        "lấy mã số in trên con dấu của đơn vị đo đạc hay tổ chức khác."},
    {"name": "NguoiYeuCau_NgaySinh", "desc": "Ngày sinh ĐẦY ĐỦ của người yêu cầu, dd/mm/yyyy: Đơn ('sinh ngày …', vd "
        "'5/6/1980' = 05/06/1980) → CCCD. Giấy tờ chỉ ghi 'Sinh năm'/năm sinh thì bỏ field."},
    {"name": "NguoiYeuCau_GioiTinh", "desc": 'Giới tính người yêu cầu: "Nam"/"Nữ" theo CCCD → sổ hộ khẩu (ô Giới tính, '
        'chữ bị gạch là chữ bị loại). Không có thì bỏ field.'},
    {"name": "NguoiYeuCau_DanhXung", "desc": "Danh xưng đứng ngay trước tên người yêu cầu ở hợp đồng ủy quyền, giấy "
        "chuyển nhượng, lời chứng: 'Ông' hoặc 'Bà'. Không suy từ tên."},
    {"name": "NguoiYeuCau_SoDinhDanh", "desc": "Số căn cước/CCCD 12 số của người yêu cầu (Đơn 'Căn cước'/'CCCD số' → "
        "CCCD). Chỉ chữ số. Số CMND 9 số trong giấy tờ cũ chỉ dùng khi không có số 12 số nào."},
    {"name": "NguoiYeuCau_NgayCap", "desc": "Ngày cấp của ĐÚNG số căn cước ở NguoiYeuCau_SoDinhDanh, dd/mm/yyyy (Đơn "
        "'cấp ngày …' hoặc mặt sau thẻ). Không lấy ngày cấp CMND cũ, ngày lập đơn, ngày công chứng."},
    {"name": "NguoiYeuCau_NoiCap", "desc": "Cơ quan cấp của đúng số căn cước đó (mặt sau thẻ, hoặc '… cấp tại …' đi "
        "liền số). 'Cấp tại công an …' của CMND cũ thì KHÔNG dùng cho số căn cước 12 số. Không có thì bỏ field."},
    {"name": "NguoiYeuCau_DiaChi", "desc": "Nơi cư trú HIỆN TẠI của người yêu cầu, object {quocGia,tinh,xa,chiTietDuoiXa}"
        ": Đơn 'Địa chỉ'/'Trú tại' (mới nhất) → CCCD → sổ hộ khẩu/giấy tờ cũ. KHÔNG lấy địa chỉ thửa đất tranh chấp."},
    {"name": "NguoiYeuCau_DienThoai", "desc": "Số điện thoại của người yêu cầu ghi trên Đơn; chỉ chữ số."},
    {"name": "NguoiYeuCau_Email", "desc": "Email của người yêu cầu nếu Đơn ghi; không có thì bỏ field."},
    # Nội dung đơn → ô Ghi chú.
    {"name": "Don_NoiDung", "desc": "Chép NGUYÊN VĂN thân Đơn yêu cầu hòa giải: từ câu đầu tiên sau phần thông tin "
        "người viết đơn (họ tên, căn cước, địa chỉ, số điện thoại) đến hết câu đề nghị cuối (trước dòng địa danh, "
        "ngày tháng và 'Người viết đơn'). Giữ đúng chữ, số, dấu câu; nối các đoạn bằng một khoảng trắng; không tóm "
        "tắt, không thêm lời. Có ghi chú viết tay cạnh chữ ký thì thêm vào cuối sau cụm ' Ghi chú: '."},
]
for _n in (1, 2):
    for _part, _desc in _CARD_FIELDS:
        FIELDS.append({"name": f"Cccd{_n}_{_part}", "desc": _desc.format(n="thứ nhất" if _n == 1 else "thứ hai")})

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("NguoiYeuCau_NgaySinh", "NguoiYeuCau_NgayCap", "Cccd1_NgaySinh", "Cccd1_NgayCap", "Cccd2_NgaySinh",
              "Cccd2_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("NguoiYeuCau_DiaChi", "Cccd1_ThuongTru", "Cccd2_ThuongTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    "data[chonDoiTuong]": "dom-select",
    # Phần I người nộp.
    "data[organization]": "dom-input",
    "data[taxCode]": "dom-input",
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    # Ô khoá theo tài khoản: chỉ phát (kèm enableInput) khi bật cài đặt "Lấy người nộp theo tờ khai".
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[idIssuePlace]": "dom-input",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[email]": "dom-input",
    "data[isOwnerDossierCheck]": "dom-checkbox",
    # Phần II chủ hồ sơ.
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
