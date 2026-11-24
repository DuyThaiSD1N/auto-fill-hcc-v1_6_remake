"""Bổ sung ô còn trống trên form SurveyJS cấp bản sao trích lục hộ tịch (dichvucong.gov.vn/nop-ho-so).

Ô bắt buộc lấy theo chính cổng (isRequired / dấu "*" ở nhãn). Khối người nộp cổng khóa theo tài khoản nên không hỏi;
Quan hệ = "Bản thân" thì cổng tự chép khối người được cấp. Chọn nơi cư trú "Trong nước" xong thì ô Quốc gia / Tỉnh /
Xã / Địa chỉ hiện ra và được hỏi tiếp ở lượt sau.
"""

PROCEDURE_KEYS = ("trich-luc-ks",)

REQUIRED = ()

# Chỉ bổ sung ô bắt buộc: ô không bắt buộc còn trống vẫn tô cam nhưng không đếm, không hỏi; hết ô bắt buộc là xong.
REQUIRED_ONLY = True

# Kính gửi / Tại (engine dựng theo cơ quan đã chọn hoặc tài khoản quầy) và Ngày / Tháng / Năm lập tờ khai (cổng tự điền).
NO_ASK = ("citizenField27", "citizenField37", "citizenField50", "citizenField52", "citizenField53")

# Ngày sinh người được cấp là Ô CHỮ (nhãn "dd/mm/yyyy"), không phải ô lịch: hỏi như ô ngày, nhận cả tháng-năm hoặc
# chỉ năm, ghi vào cổng dạng chữ.
TEXT_DATES = ("citizenNDK_NgaySinh",)

# Cùng ba ô tra cứu CSDL dân cư như khai tử: điền xong chờ cổng tra rồi mới tìm ô trống kế tiếp, kẻo hỏi đúng
# giới tính / dân tộc cổng sắp tự đổ.
LOOKUP = ("citizenNDK_HoVaTen", "citizenNDK_SoDinhDanh", "citizenNDK_NgaySinh")

# Chế độ tiếng Mông (Lai Châu): vòng hỏi đọc nhãn ô bằng tiếng Mông theo tên ô — nhãn trên tờ khai là tiếng Việt. Ô
# không có trong bảng thì lời đọc Mông gọi chung "ô này". BẢN NHÁP chờ người soát; chữ đã có trong script_mong: "npe"
# (tên), "daim npav" (thẻ), "hnub yug" (ngày sinh), "xeev" (tỉnh), "zos" (xã), "cuv npe" (đăng ký), "daim ntawv theej"
# (bản sao), "qhov chaw nyob" (chỗ ở), "txiv" (cha), "niam" (mẹ); TỪ MỚI: "xeem" (họ), "haiv neeg" (dân tộc), "teb chaws" (quốc gia), "ntxaws"
# (chi tiết), "txheeb ze" (quan hệ), "tus lej" (số), "hom" (loại), "pes tsawg" (bao nhiêu).
HMONG = True
_PERSON = "tus neeg tau daim ntawv"
_ADDRESS = "chaw nyob"
_RECORD = "daim ntawv xav theej"
HMONG_LABELS = {
    "citizenQuanhe": ("kev txheeb ze nrog tus neeg tau daim ntawv", ""),
    "citizenField8": ("kev txheeb ze lwm yam", ""),
    "citizenNDK_HoVaTen": ("npe thiab xeem", _PERSON),
    "citizenNDK_SoDinhDanh": ("tus lej cim tus kheej", _PERSON),
    "citizenNDK_NgaySinh": ("hnub yug", _PERSON),
    "citizenField13": ("txiv neej los poj niam", _PERSON),
    "citizenField32": ("haiv neeg", _PERSON),
    "citizenNDK_LoaiGiayToTuyThan": ("hom daim npav", _PERSON),
    "citizenNDK_SoGiayToTuyThan": ("tus lej daim npav", _PERSON),
    "citizenNDK_NoiCap": ("qhov chaw muab daim npav", _PERSON),
    "citizenNDK_NgayCap": ("hnub muab daim npav", _PERSON),
    "citizenNDK_LoaiCuTru": ("hom chaw nyob", _PERSON),
    "citizenNDK_Noicutru": ("nyob hauv teb chaws los txawv teb chaws", _PERSON),
    "citizenField21": ("teb chaws", _ADDRESS),
    "citizenNDK_TinhThanh": ("xeev", _ADDRESS),
    "citizenNDK_PhuongXa": ("zos", _ADDRESS),
    "citizenField38": ("chaw nyob ntxaws", _ADDRESS),
    "citizenLoaiViecYeuCau": ("hom ntawv xav theej", _RECORD),
    "citizenHoSo_CoQuanDangKy": ("qhov chaw tau cuv npe", _RECORD),
    "citizenHotenCha": ("npe txiv", _PERSON),
    "citizenHotenMe": ("npe niam", _PERSON),
    "citizenHotenVohoacChong": ("npe tus poj niam los tus txiv", _PERSON),
    "citizenNgaysinhVohoacChong": ("hnub yug tus poj niam los tus txiv", _PERSON),
    "citizenTenGiayToHoTich": ("lub npe daim ntawv", _RECORD),
    "citizencauhoi3": ("tus lej cuv npe", _RECORD),
    "citizencauhoi4": ("tus lej phau ntawv", _RECORD),
    "citizencauhoi5": ("hnub cuv npe", _RECORD),
    "citizenSoLuongBanSao": ("pes tsawg daim ntawv theej", _RECORD),
}
