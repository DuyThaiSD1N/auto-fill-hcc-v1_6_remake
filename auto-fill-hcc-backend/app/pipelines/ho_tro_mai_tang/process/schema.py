"""Compact schema for "Hỗ trợ mai táng".

The LLM returns only OCR-derived CCCD/CMND facts. The mapper decides whether
the requester and dossier owner are the same person from file count and current
form context, then emits short DOM actions for the Form.io page.
"""

FIELDS: list[dict] = [
    {"name": "Person1_HoTen", "desc": "Họ tên trên CCCD/CMND của người thứ nhất."},
    {"name": "Person1_SoDinhDanh", "desc": "Số định danh/CCCD/CMND người thứ nhất; có thể đọc từ MRZ mặt sau."},
    {"name": "Person1_NgaySinh", "desc": "Ngày sinh người thứ nhất, dd/mm/yyyy."},
    {"name": "Person1_GioiTinh", "desc": 'Giới tính người thứ nhất: "Nam" hoặc "Nữ".'},
    {"name": "Person1_QuocTich", "desc": "Quốc tịch nếu CCCD/CMND ghi rõ hoặc khác Việt Nam."},
    {"name": "Person1_NgayCap",
     "desc": "Ngày cấp CCCD/CMND người thứ nhất, dd/mm/yyyy. Bắt buộc cố đọc từ mặt sau; không được bỏ trống khi đã nhận diện được CCCD."},
    {"name": "Person1_NoiCap",
     "desc": 'Nơi cấp CCCD/CMND từ mặt sau. Nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT..." '
             'thì trả "Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},
    {"name": "Person1_NoiCuTru", "desc": "Nơi thường trú/cư trú trên CCCD, object {quocGia,tinh,xa,diaChi} nếu đọc chắc chắn."},

    {"name": "Person2_HoTen", "desc": "Họ tên trên CCCD/CMND của người thứ hai, nếu có người thứ hai."},
    {"name": "Person2_SoDinhDanh", "desc": "Số định danh/CCCD/CMND người thứ hai; có thể đọc từ MRZ mặt sau."},
    {"name": "Person2_NgaySinh", "desc": "Ngày sinh người thứ hai, dd/mm/yyyy."},
    {"name": "Person2_GioiTinh", "desc": 'Giới tính người thứ hai: "Nam" hoặc "Nữ".'},
    {"name": "Person2_QuocTich", "desc": "Quốc tịch nếu CCCD/CMND ghi rõ hoặc khác Việt Nam."},
    {"name": "Person2_NgayCap",
     "desc": "Ngày cấp CCCD/CMND người thứ hai, dd/mm/yyyy. Bắt buộc cố đọc từ mặt sau; không được bỏ trống khi đã nhận diện được CCCD."},
    {"name": "Person2_NoiCap",
     "desc": 'Nơi cấp CCCD/CMND từ mặt sau. Nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT..." '
             'thì trả "Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},
    {"name": "Person2_NoiCuTru", "desc": "Nơi thường trú/cư trú trên CCCD, object {quocGia,tinh,xa,diaChi} nếu đọc chắc chắn."},

    # Chủ hồ sơ (người/hộ đứng ra mai táng) — lấy từ TỜ KHAI đề nghị hỗ trợ chi phí mai táng
    # (Mẫu số 04), CHỈ ở MỤC II.2 "Trường hợp hộ gia đình, cá nhân đứng ra mai táng". KHÔNG lấy từ
    # mục I (người chết) hay mục II.1 (cơ quan/tổ chức). Có tờ khai thì mới trả nhóm này.
    {"name": "ToKhai_ChuHoTen", "desc": "Họ tên chủ hộ/người đại diện đứng ra mai táng — mục II.2.a của tờ khai."},
    {"name": "ToKhai_ChuHoNamSinh", "desc": "Ngày/tháng/năm sinh chủ hộ ở mục II.2, dd/mm/yyyy nếu đủ; chỉ yyyy khi tờ khai chỉ ghi năm."},
    {"name": "ToKhai_ChuHoSoGiayTo", "desc": "Số CMND/CCCD của chủ hộ ghi ở mục II.2 (nhãn \"Giấy CMND số\"/\"CCCD số\")."},
    {"name": "ToKhai_ChuHoNgayCap", "desc": "Ngày cấp giấy tờ định danh của chủ hộ ở mục II.2, dd/mm/yyyy."},
    {"name": "ToKhai_ChuHoNoiCap", "desc": "Nơi cấp giấy tờ định danh của chủ hộ ở mục II.2 (vd \"Bộ Công an\")."},
    {"name": "ToKhai_ChuHoNoiCuTru",
     "desc": "Nơi cư trú chủ hộ ở mục II.2 (Hộ khẩu thường trú / Nơi ở), object {quocGia,tinh,xa,diaChi}. "
             "Địa chỉ 2 cấp: xa = xã/phường/thị trấn, tinh = tỉnh/thành phố; "
             "diaChi = phần chi tiết đứng TRƯỚC xã (tổ/thôn/xóm/bản/số nhà), KHÔNG lặp tên xã/tỉnh vào diaChi."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Person1_NgaySinh",
    "Person1_NgayCap",
    "Person2_NgaySinh",
    "Person2_NgayCap",
    "ToKhai_ChuHoNamSinh",
    "ToKhai_ChuHoNgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Person1_NoiCuTru", "Person2_NoiCuTru", "ToKhai_ChuHoNoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    # Checkbox action must be emitted first when present.
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

    # Owner section.
    "data[ownerFullname]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[ownerGender]": "dom-select",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerIdIssuePlace]": "dom-input",
    "data[ownerProvince]": "dom-select",
    "data[ownerDistrict]": "dom-select",
    "data[ownerAddress]": "dom-input",
    "data[ownerNation]": "dom-select",
}
