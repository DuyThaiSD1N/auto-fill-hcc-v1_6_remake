"""Compact schema for "Đăng ký khai tử".

The LLM returns only source facts from CCCD/CMND and death-registration source
documents (Giấy báo tử or paper declaration). UI defaults, duplicate identity
fields, and form-specific component names are derived in Python.
"""

FIELDS: list[dict] = [
    # CCCD/CMND ĐẦU VÀO — có thể là của người yêu cầu HOẶC của người đã mất.
    # Trích đầy đủ danh tính người trên thẻ; Python tự quyết người yêu cầu vs người mất.
    {"name": "Cccd_HoTen", "desc": "Họ tên người trên CCCD/CMND đầu vào."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh/CCCD (12 chữ số) hoặc CMND (9 chữ số) đầu vào; có thể đọc từ MRZ mặt sau."},
    {"name": "Cccd_NgaySinh", "desc": "Ngày sinh trên CCCD/CMND đầu vào, dd/mm/yyyy; nếu chỉ có năm thì trả yyyy."},
    {"name": "Cccd_GioiTinh", "desc": 'Giới tính trên CCCD/CMND đầu vào: "Nam" hoặc "Nữ".'},
    {"name": "Cccd_DanToc", "desc": "Dân tộc trên CCCD/CMND đầu vào nếu thẻ có ghi."},
    {"name": "Cccd_QuocTich", "desc": "Quốc tịch trên CCCD/CMND đầu vào nếu thẻ có ghi."},
    {"name": "Cccd_NgayCap", "desc": "Ngày cấp CCCD/CMND đầu vào, dd/mm/yyyy."},
    {"name": "Cccd_NoiCap",
     "desc": 'Nơi cấp CCCD/CMND đầu vào từ mặt sau. Gần ngày cấp thường có '
             '"CỤC TRƯỞNG CỤC CẢNH SÁT..."; trả '
             '"Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},
    {"name": "Cccd_NoiCuTru", "desc": "Địa chỉ cư trú/thường trú trên CCCD/CMND đầu vào, object {quocGia,tinh,xa,diaChi}; xa (phường/xã) BẮT BUỘC khi giấy có."},
    {"name": "ToKhai_QuanHeNguoiYeuCau",
     "desc": "Quan hệ của người yêu cầu với người đã chết, chỉ lấy nếu tờ khai giấy ghi rõ."},

    # Death facts from Giấy báo tử or paper declaration.
    {"name": "Gbt_HoTenNguoiMat", "desc": "Họ tên người tử vong trên giấy báo tử hoặc tờ khai đăng ký khai tử."},
    {"name": "Gbt_NgaySinhNguoiMat", "desc": "Ngày sinh người tử vong, dd/mm/yyyy; nếu chỉ có năm thì trả yyyy."},
    {"name": "Gbt_GioiTinhNguoiMat", "desc": 'Giới tính người tử vong: "Nam" hoặc "Nữ".'},
    {"name": "Gbt_DanTocNguoiMat", "desc": "Dân tộc người tử vong."},
    {"name": "Gbt_QuocTichNguoiMat", "desc": "Quốc tịch người tử vong nếu giấy báo tử/tờ khai ghi rõ hoặc khác Việt Nam."},
    {"name": "Gbt_SoDinhDanhNguoiMat", "desc": "Số CCCD (12 chữ số) hoặc CMND (9 chữ số) của người tử vong nếu giấy báo tử/tờ khai ghi."},
    {"name": "Gbt_NgayCapDDNguoiMat",
     "desc": "Ngày cấp giấy tờ tùy thân người tử vong, dd/mm/yyyy. BẮT BUỘC trích nếu nguồn là CCCD "
             'của người mất: nằm sau "Ngày, tháng, năm / Date, month, year" ở mặt sau.'},
    {"name": "Gbt_NoiCapDDNguoiMat",
     "desc": "Nơi cấp giấy tờ tùy thân người tử vong. BẮT BUỘC trích nếu nguồn là CCCD của người mất: "
             'gần ngày cấp mặt sau thường có "CỤC TRƯỞNG CỤC CẢNH SÁT..." → trả '
             '"Cục Cảnh sát quản lý hành chính về trật tự xã hội"; nếu thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" '
             '→ trả "Bộ Công an".'},
    {"name": "Gbt_NoiCuTruNguoiMat", "desc": "Nơi thường trú/tạm trú người tử vong, object {quocGia,tinh,xa,diaChi}; xa (phường/xã) BẮT BUỘC khi giấy có."},
    {"name": "Gbt_NgayMat", "desc": 'Ngày tử vong, dd/mm/yyyy; lấy từ "Tử vong lúc"/"Đã chết vào lúc", không lấy giờ vào viện.'},
    {"name": "Gbt_GioMat", "desc": 'Giờ tử vong dạng "HH:mm"; ví dụ "06 giờ 38 phút" hoặc "giờ 6, phút 38" -> "06:38".'},
    {"name": "Gbt_NguyenNhanMat", "desc": "Nguyên nhân tử vong."},
    {"name": "Gbt_NoiChet", "desc": "Nơi chết/nơi tử vong, object {quocGia,tinh,xa,diaChi}; xa (phường/xã) BẮT BUỘC khi giấy có; nếu không có mục riêng thì lấy cơ sở báo tử."},
    {"name": "Gbt_So", "desc": 'Số giấy báo tử/giấy tờ thay thế sau nhãn "Số"; chỉ trả nếu có giá trị thật.'},
    {"name": "Gbt_CoQuanCap", "desc": "Cơ sở/cơ quan cấp giấy báo tử hoặc giấy tờ thay thế; chỉ trả nếu có giá trị thật."},
    {"name": "Gbt_NgayCap", "desc": "Ngày lập/cấp giấy báo tử hoặc giấy tờ thay thế, dd/mm/yyyy; chỉ trả nếu có giá trị thật."},

    # Yêu cầu cấp bản sao trên chính tờ khai đăng ký khai tử, không đặt mặc định.
    {"name": "CopyRequest_WantsCopy",
     "desc": '"Có" nếu TỜ KHAI ĐĂNG KÝ KHAI TỬ tích/chọn Có ở mục đề nghị cấp bản sao; '
             '"Không" nếu tích/chọn Không. Nếu tờ khai ghi số lượng bản sao dương thì trả "Có" '
             "kể cả dấu tick không rõ. Không có dấu chọn và không có số lượng thì bỏ field."},
    {"name": "CopyRequest_Quantity",
     "desc": "Số lượng bản sao ghi thật trên TỜ KHAI ĐĂNG KÝ KHAI TỬ, trả số nguyên dương "
             "(ví dụ 03 bản -> 3). Field này chỉ là bằng chứng suy ra yêu cầu cấp bản sao; "
             "không tự mặc định số lượng."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Cccd_NgaySinh",
    "Cccd_NgayCap",
    "Gbt_NgaySinhNguoiMat",
    "Gbt_NgayCapDDNguoiMat",
    "Gbt_NgayMat",
    "Gbt_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Cccd_NoiCuTru", "Gbt_NoiCuTruNguoiMat", "Gbt_NoiChet"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    # Người yêu cầu.
    "HoVaTenC": "x-input",
    "SoDinhDanhC": "x-input",
    "SoGiayToDinhDanhC": "x-input",
    "LoaiGiayToDinhDanhC": "x-select",
    "NgayCapDDC": "x-date",
    "NoiCapDDC": "x-input",
    "nycLoaiCuTru": "x-select",
    "nycNoiCuTru": "x-radio",
    "nycNoiCuTru_TrongNuoc": "x-select-area",
    "QuanHe": "x-input",
    # Người được khai tử.
    "HoTen": "x-input",
    # Ô ngày sinh người mất là input trần chỉ điền NĂM (placeholder "Điền năm") → comp "raw".
    "NgaySinh": "raw",
    "GioiTinh": "x-select",
    "nktDanToc": "x-select",
    "nktQuocTich": "x-select",
    "SoDinhDanh": "x-input",
    "SoGiayToDinhDanh": "x-input",
    "LoaiGiayToDinhDanh": "x-select",
    "NgayCapDD": "x-date",
    "NoiCapDD": "x-input",
    "nktLoaiCuTru": "x-select",
    "nktNoiCuTru": "x-radio",
    "nktNoiCuTru_TrongNuoc": "x-select-area",
    "NgayMat": "x-date-text",
    "GioMat": "x-input",
    "PhutMat": "x-input",
    "NguyenNhanMat": "x-input",
    "nktNoiChet": "x-radio",
    "nktNoiChet_TrongNuoc": "x-select-area",
    # Giấy báo tử.
    "gbtLoai": "x-select-default",
    "gbtSo": "x-input",
    "gbtCoQuanCap": "x-input",
    "gbtNgay": "x-date",
    # Default đăng ký.
    "loaiDangKy": "x-radio",
    # Bản sao.
    "CapBanSao": "x-radio",
    "SoLuong": "raw",
}


# Field ĐÁNG rà soát bbox (name → nhãn). Đọc từ CCCD người mất/người yêu cầu + giấy báo tử + tờ khai.
# Địa chỉ x-select-area tách tỉnh/xã/địa chỉ ở service. BỎ QUA: quốc tịch, loại cư trú, radio, quan hệ,
# giờ/phút mất (quá ngắn), các mục mặc định.
REVIEW_FIELDS = {
    # Người mất
    "HoTen": "Họ tên người mất",
    "NgaySinh": "Ngày sinh người mất",
    "GioiTinh": "Giới tính người mất",
    "nktDanToc": "Dân tộc người mất",
    "SoDinhDanh": "Số định danh người mất",
    "LoaiGiayToDinhDanh": "Loại giấy tờ người mất",
    "NgayCapDD": "Ngày cấp CCCD người mất",
    "NoiCapDD": "Nơi cấp CCCD người mất",
    "nktNoiCuTru_TrongNuoc": "Nơi cư trú người mất",
    "NgayMat": "Ngày mất",
    "NguyenNhanMat": "Nguyên nhân mất",
    "nktNoiChet_TrongNuoc": "Nơi chết",
    # Giấy báo tử
    "gbtSo": "Số giấy báo tử",
    "gbtCoQuanCap": "Cơ quan cấp giấy báo tử",
    "gbtNgay": "Ngày cấp giấy báo tử",
    # Người yêu cầu
    "HoVaTenC": "Họ tên người yêu cầu",
    "SoDinhDanhC": "Số định danh người yêu cầu",
    "LoaiGiayToDinhDanhC": "Loại giấy tờ người yêu cầu",
    "NgayCapDDC": "Ngày cấp CCCD người yêu cầu",
    "NoiCapDDC": "Nơi cấp CCCD người yêu cầu",
    "nycNoiCuTru_TrongNuoc": "Nơi cư trú người yêu cầu",
}
