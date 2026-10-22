"""Compact schema for "Đăng ký kết hôn".

The LLM returns OCR-derived facts from identity documents and the marriage
declaration. UI field names, duplicate identity fields, and deterministic
values are derived in Python.
"""

def _the(side: str, ten: str) -> list[dict]:
    """Nhân thân của một bên đọc trên THẺ CCCD/CMND (hoặc giấy thay thẻ) — cặp ghim nguồn với ToKhai*_ cùng tên.
    Chung tiền tố Ben{side} với nhóm _ben: tên "Cccd" khiến model không ghi nhân thân đọc từ giấy thay thẻ vào."""
    p = f"Ben{side}"
    return [
        {"name": f"{p}_HoTen", "desc": f"Họ tên trên CCCD/CMND có giới tính {ten} (không có cả thẻ lẫn tờ khai → "
                                       "theo NGOẠI LỆ ở <giay_to>)."},
        {"name": f"{p}_SoDinhDanh",
         "desc": f"Số định danh/CCCD bên {ten.lower()}, 12 số (CMND cũ 9 số); CHỈ đọc ở MẶT TRƯỚC thẻ, dãy số sau nhãn "
                 "'Số / No.'. TUYỆT ĐỐI không đọc, ghép hoặc suy ra từ MRZ/IDVNM ở mặt sau; không đọc rõ thì bỏ."},
        {"name": f"{p}_NgaySinh", "desc": f"Ngày sinh trên thẻ bên {ten.lower()}, dd/mm/yyyy."},
        {"name": f"{p}_NgayCap",
         "desc": f"Ngày cấp thẻ bên {ten.lower()}, dd/mm/yyyy, đọc ở mặt sau có đúng số định danh của người này "
                 "(không lấy ngày hết hạn)."},
        {"name": f"{p}_NoiCap",
         "desc": f"Nơi cấp thẻ bên {ten.lower()} theo đúng loại thẻ: Căn cước mới → \"Bộ Công an\"; CCCD gắn chip có "
                 "\"CỤC TRƯỞNG CỤC CẢNH SÁT...\" → \"Cục Cảnh sát quản lý hành chính về trật tự xã hội\"."},
        {"name": f"{p}_QuocTich", "desc": f"Quốc tịch bên {ten.lower()}, CHỈ khi giấy tờ không phải của Việt Nam."},
        {"name": f"{p}_LoaiGiayTo",
         "desc": f"Loại giấy tờ tùy thân nước ngoài của bên {ten.lower()} (hộ chiếu, chứng minh thư nước ngoài); "
                 "CCCD/Căn cước Việt Nam → bỏ."},
        {"name": f"{p}_NoiCuTru_TrongNuoc",
         "desc": f"Nơi thường trú/cư trú CHỈ lấy từ CCCD/CMND của bên {ten.lower()} (đúng thẻ có số định danh của "
                 "người này), object {quocGia,tinh,xa,chiTietDuoiXa}; không có cả thẻ lẫn tờ khai → theo NGOẠI LỆ ở <giay_to>."},
    ]


def _ben(side: str, ten: str) -> list[dict]:
    """Nhóm field của MỘT BÊN không đọc từ thẻ: dân tộc trên giấy khác, số lần kết hôn (tờ khai), tình trạng hôn
    nhân và văn bản ly hôn (Tòa án)."""
    p = f"Ben{side}"
    return [
        {"name": f"{p}_DanToc",
         "desc": f"Dân tộc bên {ten.lower()} trên giấy KHÁC tờ khai và thẻ (giấy xác nhận tình trạng hôn nhân, thông "
                 "tin cư trú...), chép nguyên văn. CCCD/Căn cước không ghi dân tộc; không suy từ họ tên, địa chỉ, quê "
                 "quán; thiếu nhãn thì bỏ field."},
        {"name": f"{p}_SoLanKetHon",
         "desc": f"Số nguyên ở cột Bên {ten.lower()} của hàng \"Kết hôn lần thứ mấy\" trên tờ khai."},
        {"name": f"{p}_TinhTrangHonNhan",
         "desc": f"Mã tình trạng hôn nhân bên {ten.lower()} (1–6, chỉ trả mã số) khi có chứng cứ trực tiếp; văn bản "
                 "ly hôn của Tòa án ghi đúng người này là đương sự → \"3\"."},
        {"name": f"{p}_BanAnLyHon_So",
         "desc": f"Số bản án/quyết định ly hôn của Tòa án có bên {ten.lower()} là đương sự (khớp CHẶT họ tên hoặc số "
                 "CCCD); không có văn bản đúng người thì bỏ, không mượn văn bản của bên kia."},
        {"name": f"{p}_BanAnLyHon_Ngay", "desc": f"Ngày ban hành văn bản ly hôn của bên {ten.lower()}, dd/mm/yyyy."},
        {"name": f"{p}_BanAnLyHon_CoQuan",
         "desc": f"Tòa án ban hành văn bản ly hôn của bên {ten.lower()}, gộp đủ các dòng ở góc trên văn bản."},
        {"name": f"{p}_BanAnLyHon_DuongSu",
         "desc": f"Họ tên tất cả đương sự trong CHÍNH văn bản ly hôn đã gán cho bên {ten.lower()}, nối bằng \"; \"; "
                 "bắt buộc trả kèm khi có số văn bản."},
    ]


def _to_khai(side: str, ten: str) -> list[dict]:
    """Nhóm field cột Bên nam/Bên nữ của TỜ KHAI — nguồn dự phòng cho nhân thân, nguồn ưu tiên cho nơi cư trú."""
    p, cot = f"ToKhai{side}", f"cột BÊN {ten.upper()} của TỜ KHAI ĐĂNG KÝ KẾT HÔN"
    return [
        {"name": f"{p}_HoTen", "desc": f"Họ tên ở {cot}. CHỈ lấy từ tờ khai, không lấy CCCD."},
        {"name": f"{p}_NgaySinh", "desc": f"Ngày sinh ở {cot}, dd/mm/yyyy."},
        {"name": f"{p}_DanToc", "desc": f"Dân tộc ở {cot}, chép nguyên văn; tờ khai không ghi thì bỏ."},
        {"name": f"{p}_NoiCuTru_TrongNuoc",
         "desc": f"Nơi cư trú ở {cot}, object {{quocGia,tinh,xa,chiTietDuoiXa}}. CHỈ lấy từ tờ khai; không lấy CCCD, giấy xác "
                 "nhận tình trạng hôn nhân hay giấy khác."},
        {"name": f"{p}_SoDinhDanh", "desc": f"Số giấy tờ tùy thân ghi ở {cot}."},
        {"name": f"{p}_NgayCap", "desc": f"Ngày cấp giấy tờ tùy thân CHỈ khi ghi ở {cot}, dd/mm/yyyy."},
        {"name": f"{p}_NoiCap", "desc": f"Nơi cấp giấy tờ tùy thân CHỈ khi ghi ở {cot}, chép nguyên văn."},
    ]


FIELDS: list[dict] = [
    *_the("Nam", "Nam"),
    *_ben("Nam", "Nam"),
    *_the("Nu", "Nữ"),
    *_ben("Nu", "Nữ"),
    *_to_khai("Nam", "nam"),
    *_to_khai("Nu", "nữ"),
    {"name": "ToKhai_LoaiDangKy",
     "desc": "HIẾM KHI có: chỉ trả khi trên giấy có in chữ \"Loại đăng ký\" và một ô của mục đó được tích — trả "
             "nhãn ô được tích. Không thấy chữ \"Loại đăng ký\" thì KHÔNG trả."},
    {"name": "CopyRequest_WantsCopy",
     "desc": "\"Có\"/\"Không\" theo ô được tích ở \"Đề nghị cấp bản sao\" trên TỜ KHAI; cả hai ô trống và không có số "
             "lượng thì bỏ."},
    {"name": "CopyRequest_Quantity",
     "desc": "Số lượng bản sao dương ghi trên TỜ KHAI (\"02 bản\" → \"2\"); để chấm hoặc 0 thì bỏ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "BenNam_NgaySinh",
    "BenNam_NgayCap",
    "BenNu_NgaySinh",
    "BenNu_NgayCap",
    "BenNam_BanAnLyHon_Ngay",
    "BenNu_BanAnLyHon_Ngay",
    "ToKhaiNam_NgaySinh",
    "ToKhaiNam_NgayCap",
    "ToKhaiNu_NgaySinh",
    "ToKhaiNu_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in (
    "BenNam_TinhTrangHonNhan",
    "BenNu_TinhTrangHonNhan",
):
    COMPACT_COMP_BY_NAME[_name] = "x-select"
for _name in (
    "BenNam_NoiCuTru_TrongNuoc",
    "BenNu_NoiCuTru_TrongNuoc",
    "ToKhaiNam_NoiCuTru_TrongNuoc",
    "ToKhaiNu_NoiCuTru_TrongNuoc",
):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    # Bên nam.
    "HoTenBenNam": "x-input",
    "SoDinhDanh_BenNam": "x-input",
    "SoGiayToDinhDanh_BenNam": "x-input",
    "LoaiGiayToDinhDanh_BenNam": "x-select",
    "NgaySinhBenNam": "x-date",
    "NgayCapDD_BenNam": "x-date",
    "NoiCapDD_BenNam": "x-input",
    "DanTocBenNam": "x-select",
    # Ô ghi tay khi dropdown dân tộc chọn "Khác" (tên ngoài danh sách, vd nhóm địa phương "Cill").
    "DanTocKhacBenNam": "x-select-area",
    "QuocTichBenNam": "x-select",
    "LoaiCuTru_BenNam": "x-select",
    "NoiCuTru_BenNam": "x-radio",
    "NoiCuTru_BenNam_TrongNuoc": "x-select-area",
    "NoiCuTru_BenNam_NuocNgoai": "x-select-area",
    "SoLanKetHon_BenNam": "raw",
    "LoaiTinhTrangHonNhan_BenNam": "x-select",
    # Widget động khi chọn "Đã ly hôn": tên thật lấy từ DOM cổng dịch vụ công (name="TTHN_LyHonBenNam"),
    # chứa 3 ô con Số bản án -> Ngày cấp -> Cơ quan cấp theo thứ tự (input name="BenNam_SoBanAn"...).
    "TTHN_LyHonBenNam": "x-select-area",
    # Bên nữ.
    "HoTenBenNu": "x-input",
    "SoDinhDanh_BenNu": "x-input",
    "SoGiayToDinhDanh_BenNu": "x-input",
    "LoaiGiayToDinhDanh_BenNu": "x-select",
    "NgaySinhBenNu": "x-date",
    "NgayCapDD_BenNu": "x-date",
    "NoiCapDD_BenNu": "x-input",
    "DanTocBenNu": "x-select",
    "DanTocKhacBenNu": "x-select-area",
    "QuocTichBenNu": "x-select",
    "LoaiCuTru_BenNu": "x-select",
    "NoiCuTru_BenNu": "x-radio",
    "NoiCuTru_BenNu_TrongNuoc": "x-select-area",
    "NoiCuTru_BenNu_NuocNgoai": "x-select-area",
    "SoLanKetHon_BenNu": "raw",
    "LoaiTinhTrangHonNhan_BenNu": "x-select",
    "TTHN_LyHonBenNu": "x-select-area",  # tương tự TTHN_LyHonBenNam nhưng cho bên nữ
    "loaiDangKy": "x-radio",
    "CapBanSao": "x-radio",
    "SoLuong": "raw",
}

# Tên DOM ô "dân tộc khác" chưa đối chiếu được trên cổng → gửi kèm các biến thể đặt tên của eForm;
# extension còn tìm theo ô dropdown gốc (otherOf) nếu không tên nào khớp.
UI_ALIASES = {
    "DanTocKhacBenNam": ["DanTocBenNamKhac", "DanTocKhac_BenNam", "DanTocBenNam_Khac"],
    "DanTocKhacBenNu": ["DanTocBenNuKhac", "DanTocKhac_BenNu", "DanTocBenNu_Khac"],
}

# Field ĐÁNG rà soát bbox (name → nhãn hiển thị). CHỈ các ô đọc TỪ GIẤY TỜ, có thể khoanh
# vùng trên ảnh: họ tên, số định danh, ngày sinh/cấp, và NƠI CƯ TRÚ (x-select-area → tách
# tỉnh/xã/địa chỉ ở service). BỎ QUA: loại giấy tờ, quốc tịch, loại cư trú, radio "nơi cư trú"=1,
# số lần kết hôn, tình trạng hôn nhân (giá trị suy diễn/hằng số, không nằm trên giấy tờ).
REVIEW_FIELDS = {
    # Bên nam
    "HoTenBenNam": "Họ tên chồng",
    "SoDinhDanh_BenNam": "Số định danh chồng",
    "LoaiGiayToDinhDanh_BenNam": "Loại giấy tờ chồng",
    "SoGiayToDinhDanh_BenNam": "Số giấy tờ chồng",
    "NgaySinhBenNam": "Ngày sinh chồng",
    "DanTocBenNam": "Dân tộc chồng",
    "NgayCapDD_BenNam": "Ngày cấp CCCD chồng",
    "NoiCapDD_BenNam": "Nơi cấp CCCD chồng",
    "NoiCuTru_BenNam_TrongNuoc": "Nơi cư trú chồng",
    "SoLanKetHon_BenNam": "Số lần kết hôn chồng",
    # Bên nữ
    "HoTenBenNu": "Họ tên vợ",
    "SoDinhDanh_BenNu": "Số định danh vợ",
    "LoaiGiayToDinhDanh_BenNu": "Loại giấy tờ vợ",
    "SoGiayToDinhDanh_BenNu": "Số giấy tờ vợ",
    "NgaySinhBenNu": "Ngày sinh vợ",
    "DanTocBenNu": "Dân tộc vợ",
    "NgayCapDD_BenNu": "Ngày cấp CCCD vợ",
    "NoiCapDD_BenNu": "Nơi cấp CCCD vợ",
    "NoiCuTru_BenNu_TrongNuoc": "Nơi cư trú vợ",
    "SoLanKetHon_BenNu": "Số lần kết hôn vợ",
}
