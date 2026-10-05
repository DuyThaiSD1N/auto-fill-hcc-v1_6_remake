"""Schema trích xuất cho "Đăng ký khai sinh" trên Cổng DVC quốc gia mới (SurveyJS).

Khối THÔNG TIN NGƯỜI NỘP do cổng đổ từ tài khoản định danh → không trích. LLM trả dữ kiện của NGƯỜI ĐƯỢC
KHAI SINH, MẸ, CHA (đúng người đã chốt ở bước phân vai) và dòng quan hệ của người yêu cầu trên tờ khai.
"""


def _person(prefix: str, label: str) -> list[dict]:
    return [
        {"name": f"{prefix}_HoTen", "desc": f"Họ, chữ đệm, tên của {label}."},
        {"name": f"{prefix}_SoDinhDanh",
         "desc": f"Số định danh cá nhân (đúng 12 chữ số) của {label}. Số 9 chữ số là CMND → không trả ở đây."},
        {"name": f"{prefix}_NgaySinh",
         "desc": f"Ngày sinh của {label}, dd/mm/yyyy — chỉ khi đủ ngày-tháng-năm; chỉ có năm thì bỏ."},
        {"name": f"{prefix}_QuocTich", "desc": f"Quốc tịch của {label} nếu giấy tờ ghi."},
        {"name": f"{prefix}_DanToc", "desc": f"Dân tộc của {label} nếu giấy tờ ghi."},
        {"name": f"{prefix}_LoaiGiayTo",
         "desc": f"Loại giấy tờ tùy thân CỦA CHÍNH {label}: Căn cước, Căn cước công dân, CMND, Hộ chiếu..."},
        {"name": f"{prefix}_SoGiayTo", "desc": f"Số giấy tờ tùy thân CỦA CHÍNH {label} (số hộ chiếu, CMND, CCCD)."},
        {"name": f"{prefix}_NgayCap", "desc": f"Ngày cấp giấy tờ tùy thân của {label}, dd/mm/yyyy."},
        {"name": f"{prefix}_NoiCap",
         "desc": f"Cơ quan cấp giấy tờ tùy thân của {label}, CHÉP ĐÚNG chữ trên giấy. Không ghi → bỏ."},
        {"name": f"{prefix}_NoiCuTru",
         "desc": f"Nơi cư trú của {label}, object {{quocGia,tinh,xa,diaChi[,huyen]}}. BẮT BUỘC trả khi khối của "
                 f"người đó trên tờ khai có dòng 'Nơi cư trú' — kể cả trùng địa chỉ người kia, kể cả người nước "
                 f"ngoài đang cư trú ở Việt Nam. Đã chết → bỏ."},
        {"name": f"{prefix}_DaChet",
         "desc": f'true khi giấy tờ cho thấy {label} đã chết (nơi cư trú ghi "chết", có trích lục khai tử).'},
    ]


FIELDS: list[dict] = [
    {"name": "Con_HoTen", "desc": "Họ, chữ đệm, tên của NGƯỜI ĐƯỢC KHAI SINH."},
    {"name": "Con_NgaySinh", "desc": "Ngày sinh của người được khai sinh, dd/mm/yyyy."},
    {"name": "Con_GioiTinh", "desc": 'Giới tính người được khai sinh: "Nam" hoặc "Nữ".'},
    {"name": "Con_DanToc", "desc": "Dân tộc người được khai sinh nếu giấy tờ ghi."},
    {"name": "Con_QuocTich", "desc": "Quốc tịch người được khai sinh nếu giấy tờ ghi."},
    {"name": "Con_NoiSinh",
     "desc": "Nơi sinh, object {quocGia,tinh,xa,diaChi[,huyen]}; sinh tại cơ sở y tế thì diaChi = tên cơ sở y tế "
             "nối phần địa chỉ chi tiết của cơ sở."},
    {"name": "Con_QueQuan", "desc": "Quê quán người được khai sinh, object {quocGia,tinh,xa,diaChi[,huyen]}."},
    *_person("Me", "MẸ của người được khai sinh"),
    *_person("Cha", "CHA của người được khai sinh"),
    {"name": "NguoiYeuCau_HoTen", "desc": "Họ tên người yêu cầu ghi ở phần đầu tờ khai đăng ký khai sinh."},
    {"name": "NguoiYeuCau_SoDinhDanh", "desc": "Số giấy tờ tùy thân của người yêu cầu trên tờ khai."},
    {"name": "NguoiYeuCau_QuanHe",
     "desc": "Dòng 'Quan hệ với người được khai sinh' trên tờ khai, chép đúng chữ (vd 'Mẹ', 'Bà nội', 'Chính tôi')."},
    {"name": "SoLuongBanSao",
     "desc": "Số bản sao trích lục đề nghị cấp: số nguyên; tờ khai đánh dấu KHÔNG đề nghị → 0; không ghi → bỏ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Con_NgaySinh", "Me_NgaySinh", "Me_NgayCap", "Cha_NgaySinh", "Cha_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Con_NoiSinh", "Con_QueQuan", "Me_NoiCuTru", "Cha_NoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô SurveyJS: name = phần trước hậu tố "__<số>" của data-name (extension khớp theo tiền tố). Ngày cấp của mẹ/cha
# có "__" ở giữa tên ("citizenNgaythangnamcap__me") — vẫn là tiền tố nên không lẫn hai người.
UI_COMP_BY_NAME = {
    "citizenQuanhevoinguoiduockhaisinh": "sjs-radio",   # Khác / Cha / Mẹ
    "citizenField62": "sjs-text",                       # Quan hệ khác
    # Người được đăng ký khai sinh
    "citizenHoVaTen_NgdcKS": "sjs-text",
    "citizenNgaythangnamsinh_NgdcKS": "sjs-date",
    "citizenGioitinh_NgdcKS": "sjs-dropdown",
    "citizenQuoctich_NgdcKS": "sjs-dropdown",
    "citizenDanToc_NgdcKS": "sjs-dropdown",
    "citizenLoaiDangKy": "sjs-dropdown",
    "citizenLoaikhaisinh_NgdcKS": "sjs-dropdown",
    "citizenNoisinhnks": "sjs-radio",
    "citizenNoisinhnks_TrongNuoc": "sjs-area",
    "citizenQuequannks": "sjs-radio",
    "citizenQuequannks_TrongNuoc": "sjs-area",
    # Mẹ
    "citizenNDK_HoVaTen": "sjs-text",
    "citizenNDK_SoDinhDanh": "sjs-text",
    "citizenNDK_NgaySinh": "sjs-date",
    "citizenQuoctich_me": "sjs-dropdown",
    "citizenDanToc_me": "sjs-dropdown",
    "citizenLoaiGiaytotuythan_me": "sjs-dropdown",
    "citizenSoGiayToTuyThan_me": "sjs-text",
    "citizenNgaythangnamcap__me": "sjs-date",
    "citizenCoquancap_me": "sjs-text",
    "citizenMeLoaicutru": "sjs-dropdown",
    "citizenMeNoicutru": "sjs-radio",
    "citizenMeNoicutru_TrongNuoc": "sjs-area",
    # Cha
    "citizenNDK_HoVaTenCha": "sjs-text",
    "citizenNDK_SoDinhDanhCha": "sjs-text",
    "citizenNDK_NgaySinhCha": "sjs-date",
    "citizenQuoctich_cha": "sjs-dropdown",
    "citizenDanToc_cha": "sjs-dropdown",
    "citizenField24": "sjs-dropdown",                   # Loại giấy tờ tùy thân của cha
    "citizenSoGiayToTuyThan_cha": "sjs-text",
    "citizenNgaythangnamcap__cha": "sjs-date",
    "citizenCoquancap_cha": "sjs-text",
    "citizenChaLoaicutru": "sjs-dropdown",
    "citizenChaNoicutru": "sjs-radio",
    "citizenChaNoicutru_TrongNuoc": "sjs-area",
    "citizenSoluongbansao": "sjs-text",
}
