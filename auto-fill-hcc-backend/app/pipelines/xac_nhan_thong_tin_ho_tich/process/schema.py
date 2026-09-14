"""Compact schema cho "Xác nhận thông tin hộ tịch" (mã 2.002516).

Hai người trong hồ sơ, tách nguồn giống trích lục hộ tịch:
- NGƯỜI YÊU CẦU: TkNyc_* đọc ở khối đầu TỜ KHAI, Nyc_* đọc ở CCCD của chính họ.
- NGƯỜI ĐƯỢC XÁC NHẬN: Dt_* đọc ở TỜ KHAI (khối "người được xác nhận") + GIẤY KHAI SINH, ChuThe_* đọc ở
  CCCD/CMND của chính họ.
- ToKhai_*: quan hệ, lý do, nội dung đề nghị xác nhận.

Mapper phát HAI bộ ô, mỗi bộ nằm ở một trang/frame khác nhau:
- Trang "Thông tin chủ hồ sơ" của cổng (Form.io, data[...]): Phần 1 người nộp + Phần 2 chủ hồ sơ.
- eForm tokhaidientu.moj.gov.vn (iframe bước "Kê khai thông tin", web-component x-*): Mục I người yêu cầu,
  Mục II người được xác nhận, nội dung + lý do. Extension lọc để mỗi frame chỉ nhận đúng bộ của mình.
"""

_TK = "TỜ KHAI đề nghị xác nhận thông tin hộ tịch"
_TK_NYC = f"khối NGƯỜI YÊU CẦU ở đầu {_TK} (từ 'Họ, chữ đệm, tên người yêu cầu' tới trước khối người được xác nhận)"
_TK_DT = f"khối NGƯỜI ĐƯỢC XÁC NHẬN thông tin hộ tịch trên {_TK}"
_ADDR = (
    "object {quocGia,tinh,xa,diaChi}: tinh = tỉnh/thành phố, xa = xã/phường, diaChi = chi tiết đứng TRƯỚC "
    "xã (tổ dân phố/thôn/bản/số nhà). Địa chỉ cũ 3 cấp '[chi tiết], [xã], [huyện], [tỉnh]' thì BỎ cấp huyện."
)
_NOI_CAP = (
    'CCCD cũ ghi "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý '
    'hành chính về trật tự xã hội"; thẻ Căn cước mới ghi "BỘ CÔNG AN" → "Bộ Công an"; CMND giữ nguyên '
    'cơ quan ghi trên giấy (vd "Công an tỉnh Lai Châu").'
)

FIELDS: list[dict] = [
    # --- Người yêu cầu trên TỜ KHAI (nguồn ưu tiên cho Phần 1) ---
    {"name": "TkNyc_HoTen", "desc": f"Họ tên người yêu cầu ở {_TK_NYC}."},
    {"name": "TkNyc_SoGiayToTuyThan", "desc": f"Số giấy tờ tùy thân / số định danh cá nhân của người yêu cầu ở {_TK_NYC}. Chỉ chữ số."},
    {"name": "TkNyc_NgayCapGiayToTuyThan", "desc": f"Ngày cấp giấy tờ tùy thân người yêu cầu ở {_TK_NYC}, dd/mm/yyyy."},
    {"name": "TkNyc_NoiCapGiayToTuyThan", "desc": f"Nơi cấp giấy tờ tùy thân người yêu cầu ở {_TK_NYC}. {_NOI_CAP}"},
    {"name": "TkNyc_NoiCuTru", "desc": f"Nơi cư trú người yêu cầu ở {_TK_NYC}, {_ADDR}"},

    # --- CCCD RIÊNG của người yêu cầu (bù ngày sinh, giới tính và field tờ khai bỏ trống) ---
    {"name": "Nyc_HoTen", "desc": "Họ tên trên CCCD/CMND của NGƯỜI YÊU CẦU."},
    {"name": "Nyc_SoDinhDanh", "desc": "Số CCCD/định danh trên CCCD của NGƯỜI YÊU CẦU; có thể đọc từ MRZ mặt sau."},
    {"name": "Nyc_NgaySinh", "desc": "Ngày sinh trên CCCD của NGƯỜI YÊU CẦU, dd/mm/yyyy."},
    {"name": "Nyc_GioiTinh", "desc": 'Giới tính trên CCCD của NGƯỜI YÊU CẦU: "Nam" hoặc "Nữ".'},
    {"name": "Nyc_NgayCap", "desc": "Ngày cấp CCCD của NGƯỜI YÊU CẦU (mặt sau), dd/mm/yyyy."},
    {"name": "Nyc_NoiCap", "desc": f"Nơi cấp CCCD của NGƯỜI YÊU CẦU. {_NOI_CAP}"},
    {"name": "Nyc_NoiCuTru", "desc": f"Nơi thường trú/cư trú trên CCCD của NGƯỜI YÊU CẦU, {_ADDR}"},

    # --- Người được xác nhận: TỜ KHAI + GIẤY KHAI SINH ---
    {"name": "Dt_HoTen", "desc": f"Họ tên NGƯỜI ĐƯỢC XÁC NHẬN: ưu tiên {_TK_DT}; không có tờ khai thì lấy người "
        "được khai sinh trên GIẤY KHAI SINH. KHÔNG lấy tên cha/mẹ trên giấy khai sinh."},
    {"name": "Dt_NgaySinh", "desc": "Ngày sinh người được xác nhận (tờ khai hoặc giấy khai sinh), dd/mm/yyyy."},
    {"name": "Dt_GioiTinh", "desc": 'Giới tính người được xác nhận (tờ khai hoặc giấy khai sinh): "Nam" hoặc "Nữ".'},
    {"name": "Dt_DanToc", "desc": "Dân tộc người được xác nhận (tờ khai hoặc giấy khai sinh), giữ nguyên chữ trên giấy."},
    {"name": "Dt_QuocTich", "desc": "Quốc tịch người được xác nhận (tờ khai hoặc giấy khai sinh)."},
    {"name": "Dt_SoGiayToTuyThan", "desc": f"Số giấy tờ tùy thân (CMND 9 số / CCCD 12 số) của người được xác nhận ở "
        f"{_TK_DT}. Trên GIẤY KHAI SINH, dòng giấy tờ tùy thân là của NGƯỜI ĐI KHAI SINH → KHÔNG lấy."},
    {"name": "Dt_NgayCapGiayToTuyThan", "desc": f"Ngày cấp giấy tờ tùy thân người được xác nhận ở {_TK_DT}, dd/mm/yyyy."},
    {"name": "Dt_NoiCapGiayToTuyThan", "desc": f"Nơi cấp giấy tờ tùy thân người được xác nhận ở {_TK_DT}. {_NOI_CAP}"},
    {"name": "Dt_NoiCuTru", "desc": f"Nơi cư trú người được xác nhận ghi ở {_TK_DT}, {_ADDR}"},

    # --- GIẤY KHAI SINH (bản đánh máy — chính tả tên chắc hơn chữ viết tay trên tờ khai) ---
    {"name": "Gks_HoTen", "desc": "Họ tên NGƯỜI ĐƯỢC KHAI SINH trên GIẤY KHAI SINH, chép đúng chính tả trên giấy."},
    {"name": "Gks_NgaySinh", "desc": "Ngày sinh (dạng số dd/mm/yyyy) trên GIẤY KHAI SINH."},
    {"name": "Gks_GioiTinh", "desc": 'Giới tính trên GIẤY KHAI SINH: "Nam" hoặc "Nữ".'},
    {"name": "Gks_DanToc", "desc": "Dân tộc người được khai sinh trên GIẤY KHAI SINH."},
    {"name": "Gks_QuocTich", "desc": "Quốc tịch người được khai sinh trên GIẤY KHAI SINH."},
    {"name": "Gks_HoTenMe", "desc": "Họ tên NGƯỜI MẸ trên GIẤY KHAI SINH, chép đúng chính tả trên giấy."},
    {"name": "Gks_HoTenCha", "desc": "Họ tên NGƯỜI CHA trên GIẤY KHAI SINH, chép đúng chính tả trên giấy."},

    # --- CCCD/CMND RIÊNG của người được xác nhận ---
    {"name": "ChuThe_HoTen", "desc": "Họ tên trên CCCD/CMND của chính NGƯỜI ĐƯỢC XÁC NHẬN."},
    {"name": "ChuThe_SoDinhDanh", "desc": "Số CCCD/CMND của chính NGƯỜI ĐƯỢC XÁC NHẬN; có thể đọc từ MRZ."},
    {"name": "ChuThe_NgaySinh", "desc": "Ngày sinh trên CCCD/CMND của NGƯỜI ĐƯỢC XÁC NHẬN, dd/mm/yyyy."},
    {"name": "ChuThe_GioiTinh", "desc": 'Giới tính trên CCCD/CMND của NGƯỜI ĐƯỢC XÁC NHẬN: "Nam" hoặc "Nữ".'},
    {"name": "ChuThe_NgayCap", "desc": "Ngày cấp CCCD/CMND của NGƯỜI ĐƯỢC XÁC NHẬN, dd/mm/yyyy."},
    {"name": "ChuThe_NoiCap", "desc": f"Nơi cấp CCCD/CMND của NGƯỜI ĐƯỢC XÁC NHẬN. {_NOI_CAP}"},
    {"name": "ChuThe_NoiCuTru", "desc": f"Nơi thường trú trên CCCD/CMND của NGƯỜI ĐƯỢC XÁC NHẬN, {_ADDR}"},

    # --- Nội dung đề nghị ---
    {"name": "ToKhai_QuanHe", "desc": f"Quan hệ của người yêu cầu với người được xác nhận, ĐÚNG chữ ghi trên {_TK} "
        "(vd 'Con đẻ', 'Bản thân', 'Vợ')."},
    {"name": "ToKhai_LyDo", "desc": f"Nội dung dòng 'Lý do đề nghị xác nhận' trên {_TK}, chép nguyên văn."},
    {"name": "ToKhai_NoiDung", "desc": f"Nội dung dòng/khối 'Nội dung đề nghị xác nhận' trên {_TK}, chép nguyên văn."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "TkNyc_NgayCapGiayToTuyThan", "Nyc_NgaySinh", "Nyc_NgayCap",
    "Dt_NgaySinh", "Dt_NgayCapGiayToTuyThan", "Gks_NgaySinh", "ChuThe_NgaySinh", "ChuThe_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("TkNyc_NoiCuTru", "Nyc_NoiCuTru", "Dt_NoiCuTru", "ChuThe_NoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# ---- UI Form.io trang "Thông tin chủ hồ sơ" — tên ô theo bảng mapping nghiệp vụ.
UI_COMP_BY_NAME = {
    "data[isOwnerDossierCheck]": "dom-checkbox",

    # --- Phần 1: người nộp hồ sơ = người yêu cầu ---
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[idIssuePlace]": "dom-input",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    # phoneNumber / email / fax: không có trong giấy tờ → tự nhập.

    # --- Phần 2: chủ hồ sơ = người được xác nhận ---
    "data[ownerFullname]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[ownerGender]": "dom-select",
    "data[ownerDanToc]": "dom-input",
    "data[ownerNation]": "dom-select",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerIdIssuePlace]": "dom-input",
    "data[ownerProvince]": "dom-select",
    "data[ownerDistrict]": "dom-select",
    "data[ownerAddress]": "dom-input",
    # ownerPhoneNumber / ownerEmail: đối tượng thường không có SĐT riêng → tự nhập.
}

# ---- eForm hộ tịch (iframe tokhaidientu.moj.gov.vn) — tên ô crawl từ DOM thật.
EFORM_COMP_BY_NAME = {
    # Radio đối tượng + quan hệ dựng lại khối nhân thân khi đổi → phải phát TRƯỚC Mục I.
    "doiTuongYeuCau": "x-radio",                 # "Cá nhân" | "Tổ chức"
    "nycQuanHe": "x-radio",                      # "Bản thân" | "Khác"
    # Ô ghi quan hệ ("Con đẻ") cạnh option "Khác": input.input-field-radio dùng CHUNG name nycQuanHe với ô
    # tích → không có tên riêng; fill-legacy.js tìm theo cấu trúc (LEGACY_OTHER_TEXT_DRIVERS.nycquanhekhac).
    "nycQuanHeKhac": "raw",

    # --- Mục I: người yêu cầu (cổng đổ sẵn tài khoản VNeID, ta ghi đè theo tờ khai) ---
    "HoVaTenC": "x-input",
    "SoDinhDanhC": "x-input",
    "LoaiGiayToDinhDanhC": "x-select",
    "SoGiayToTuyThanC": "x-input",
    "NgayCapDDC": "x-date",
    "NoiCapDDC": "x-input",
    "nycLoaiCuTru": "x-select",
    "nycNoiCuTru": "x-radio",                    # "Trong Nước" | "Khác"
    "nycNoiCuTru_TruongNuoc": "x-select-area",   # cổng đặt tên sai chính tả "TruongNuoc" (DOM thật)

    # --- Mục II: người được xác nhận ---
    "hoTenNguoiDuocXN": "x-input",
    "ngaySinhNguoiDuocXN": "x-date",
    "duocXNGioiTinh": "x-select",
    "danTocNguoiDuocXN": "x-select",
    "danTocKhacNguoiDuocXN": "x-select-area",    # chỉ khi dân tộc = "Khác"
    "quocTichNguoiDuocXN": "x-select",
    "duocXNDDCN": "x-input",                     # số định danh cá nhân (12 số)
    "duocXNLoaiGiayToTuyThan": "x-select",
    "duocXNSoGiayToTuyThan": "x-input",
    "duocXNNgayCapGiayToTuyThan": "x-date",
    "duocXNNoiCapGiayToTuyThan": "x-input",
    "duocXNLoaiCuTru": "x-select",
    "duocXNNoiCuTru": "x-radio",                 # "Trong nước" | "Khác"
    "duocXNNoiCuTru_TrongNuoc": "x-select-area",

    # --- Nội dung đề nghị ---
    "noiDungXacNhan": "x-input",
    "lyDoXacNhan": "x-input",
    # PhuongThucNhanKQ / CapBanSao: người dùng tự chọn.
}

EFORM_ALIASES = {
    # Phòng khi cổng sửa lỗi chính tả tên ô.
    "nycNoiCuTru_TruongNuoc": ["nycNoiCuTru_TrongNuoc"],
}
