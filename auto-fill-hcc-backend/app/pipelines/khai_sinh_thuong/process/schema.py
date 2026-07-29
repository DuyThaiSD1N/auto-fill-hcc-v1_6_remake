"""Compact schema for regular "Đăng ký khai sinh" legacy e-form.

The LLM returns only OCR-derived facts. UI defaults, duplicate fields and
legacy x-* field names are derived in Python.
"""

FIELDS: list[dict] = [
    # Child facts from GIAY CHUNG SINH.
    {"name": "Gcs_HoTenCon", "desc": 'Tên con từ mục "Dự định đặt tên con là" trên giấy chứng sinh.'},
    {"name": "Gcs_NgaySinhCon", "desc": "Ngày sinh con trên giấy chứng sinh, dd/mm/yyyy."},
    {"name": "Gcs_GioiTinhCon", "desc": 'Giới tính con: "Nam" hoặc "Nữ".'},
    {"name": "Gcs_DanTocCon", "desc": "Dân tộc con trên giấy chứng sinh."},
    {"name": "Gcs_NoiSinh", "desc": "Nơi sinh con trên giấy chứng sinh, object {quocGia,tinh,xa,diaChi}; diaChi là cơ sở y tế."},

    # Father facts from CCCD/CMND Nam.
    {"name": "CccdNam_HoTen", "desc": "Họ tên trên CCCD/CMND giới tính Nam. Không lấy từ giấy chứng sinh."},
    {"name": "CccdNam_SoDinhDanh", "desc": "Số định danh/CCCD trên CCCD Nam, 12 số; có thể đọc từ MRZ mặt sau."},
    {"name": "CccdNam_NgayCap", "desc": "Ngày cấp CCCD Nam, dd/mm/yyyy. Bắt buộc cố đọc từ mặt sau CCCD."},
    {
        "name": "CccdNam_NoiCap",
        "desc": (
            "Nơi cấp CCCD Nam từ mặt sau. Nếu OCR thấy CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ "
            'HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI thì trả "Cục Cảnh sát quản lý hành chính về trật tự xã hội".'
        ),
    },
    {"name": "CccdNam_NgaySinh", "desc": "Ngày sinh trên CCCD Nam, dd/mm/yyyy."},
    {"name": "CccdNam_DanToc", "desc": "Dân tộc trên giấy tờ Nam chỉ khi chính giấy tờ Nam ghi rõ; CCCD gắn chip thường không có."},
    {"name": "CccdNam_QuocTich", "desc": "Quốc tịch trên CCCD Nam chỉ trả nếu giấy tờ ghi rõ hoặc khác Việt Nam."},
    {"name": "CccdNam_QueQuan", "desc": "Quê quán/nguyên quán trên CCCD Nam, object {quocGia,tinh,xa,diaChi} nếu có."},
    {"name": "CccdNam_NoiCuTru_TrongNuoc", "desc": "Địa chỉ cư trú/thường trú trên CCCD Nam, object {quocGia,tinh,xa,diaChi}."},

    # Mother facts from CCCD/CMND Nu.
    {"name": "CccdNu_HoTen", "desc": "Họ tên trên CCCD/CMND giới tính Nữ. Không lấy từ giấy chứng sinh."},
    {"name": "CccdNu_SoDinhDanh", "desc": "Số định danh/CCCD trên CCCD Nữ, 12 số; có thể đọc từ MRZ mặt sau."},
    {"name": "CccdNu_NgayCap", "desc": "Ngày cấp CCCD Nữ, dd/mm/yyyy. Bắt buộc cố đọc từ mặt sau CCCD."},
    {
        "name": "CccdNu_NoiCap",
        "desc": (
            "Nơi cấp CCCD Nữ từ mặt sau. Nếu OCR thấy CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ "
            'HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI thì trả "Cục Cảnh sát quản lý hành chính về trật tự xã hội".'
        ),
    },
    {"name": "CccdNu_NgaySinh", "desc": "Ngày sinh trên CCCD Nữ, dd/mm/yyyy."},
    {"name": "CccdNu_DanToc", "desc": "Dân tộc trên giấy tờ Nữ chỉ khi chính giấy tờ Nữ ghi rõ; CCCD gắn chip thường không có."},
    {"name": "CccdNu_QuocTich", "desc": "Quốc tịch trên CCCD Nữ chỉ trả nếu giấy tờ ghi rõ hoặc khác Việt Nam."},
    {"name": "CccdNu_NoiCuTru_TrongNuoc", "desc": "Địa chỉ cư trú/thường trú trên CCCD Nữ, object {quocGia,tinh,xa,diaChi}."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Gcs_NgaySinhCon",
    "CccdNam_NgayCap",
    "CccdNam_NgaySinh",
    "CccdNu_NgayCap",
    "CccdNu_NgaySinh",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in (
    "Gcs_NoiSinh",
    "CccdNam_QueQuan",
    "CccdNam_NoiCuTru_TrongNuoc",
    "CccdNu_NoiCuTru_TrongNuoc",
):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

