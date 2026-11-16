"""Compact schema cho "Đăng ký lại kết hôn".

LLM chỉ trả sự thật OCR, mỗi nhóm field gắn với MỘT loại giấy: thẻ của từng bên (BenNam_* / BenNu_*), khối vợ / chồng
trên tờ khai (ToKhaiNam_* / ToKhaiNu_*), lần đăng ký kết hôn trước đây (KetHonCu_*). Mapper quyết định ưu tiên nguồn
và dựng field UI.
"""


def _the(side: str, ten: str) -> list[dict]:
    """Nhân thân của một bên đọc trên THẺ CCCD/CMND (hoặc giấy thay thẻ) — cặp ghim nguồn với ToKhai*_ cùng tên.
    Tiền tố Ben{side} chung với dân tộc trên giấy khác: tên "Cccd" khiến model không ghi nhân thân đọc từ giấy thay thẻ."""
    p, ben = f"Ben{side}", f"bên {ten.lower()}"
    return [
        {"name": f"{p}_HoTen", "desc": f"Họ tên trên CCCD/CMND có giới tính {ten} (không có cả thẻ lẫn tờ khai → theo "
                                       "NGOẠI LỆ ở <giay_to>)."},
        {"name": f"{p}_SoDinhDanh",
         "desc": f"Số định danh/CCCD {ben}, 12 số (CMND cũ 9 số); CHỈ đọc ở MẶT TRƯỚC thẻ, dãy số sau nhãn 'Số / No.'. "
                 "TUYỆT ĐỐI không đọc, ghép hoặc suy ra từ MRZ/IDVNM ở mặt sau; không đọc rõ thì bỏ."},
        {"name": f"{p}_NgaySinh", "desc": f"Ngày sinh trên thẻ {ben}, dd/mm/yyyy."},
        {"name": f"{p}_NgayCap",
         "desc": f"Ngày cấp thẻ {ben}, dd/mm/yyyy, đọc ở mặt sau có đúng số định danh của người này (không lấy ngày "
                 "hết hạn)."},
        {"name": f"{p}_NoiCap",
         "desc": f"Nơi cấp thẻ {ben} theo đúng loại thẻ: Căn cước mới → \"Bộ Công an\"; CCCD gắn chip có \"CỤC TRƯỞNG "
                 "CỤC CẢNH SÁT...\" → \"Cục Cảnh sát quản lý hành chính về trật tự xã hội\"."},
        {"name": f"{p}_QuocTich", "desc": f"Quốc tịch {ben}, CHỈ khi giấy tờ không phải của Việt Nam."},
        {"name": f"{p}_NoiCuTru_TrongNuoc",
         "desc": f"Nơi thường trú/cư trú CHỈ lấy từ CCCD/CMND của {ben} (đúng thẻ có số định danh của người này), "
                 "object {quocGia,tinh,xa,chiTietDuoiXa}; không có cả thẻ lẫn tờ khai → theo NGOẠI LỆ ở <giay_to>."},
        {"name": f"{p}_DanToc",
         "desc": f"Dân tộc {ben} trên giấy KHÁC tờ khai và thẻ (giấy chứng nhận kết hôn cũ, khối cha/mẹ trên giấy "
                 "khai sinh của con, bản cam đoan, xác nhận / phiếu thông tin cư trú...), chép nguyên văn. Không suy từ "
                 "họ tên, địa chỉ, quê quán; thiếu nhãn thì bỏ field."},
    ]


def _to_khai(side: str, ten: str, khoi: str) -> list[dict]:
    """Khối vợ / chồng của TỜ KHAI — nguồn dự phòng cho nhân thân, nguồn ưu tiên cho nơi cư trú."""
    p, o = f"ToKhai{side}", f"khối \"Họ, chữ đệm, tên của {khoi}\" (bên {ten}) trên TỜ KHAI ĐĂNG KÝ LẠI KẾT HÔN"
    return [
        {"name": f"{p}_HoTen", "desc": f"Họ tên ở {o}. CHỈ lấy từ tờ khai, không lấy CCCD."},
        {"name": f"{p}_NgaySinh", "desc": f"Ngày sinh ở {o}, dd/mm/yyyy."},
        {"name": f"{p}_DanToc", "desc": f"Dân tộc ở {o}, chép nguyên văn (bỏ số chú thích in sẵn); tờ khai không ghi thì bỏ."},
        {"name": f"{p}_NoiCuTru_TrongNuoc",
         "desc": f"Nơi cư trú ở {o}, object {{quocGia,tinh,xa,chiTietDuoiXa}}; hồ sơ không có tờ khai hoặc tờ khai bỏ "
                 f"trống dòng này → nơi cư trú của đúng người đó tự khai trên BẢN CAM ĐOAN. Không lấy CCCD, giấy chứng "
                 "nhận kết hôn cũ hay giấy khác."},
        {"name": f"{p}_SoDinhDanh", "desc": f"Số giấy tờ tùy thân ghi ở dòng \"Giấy tờ tùy thân\" của {o}."},
        {"name": f"{p}_NgayCap", "desc": f"Ngày cấp giấy tờ tùy thân CHỈ khi ghi ở dòng \"Giấy tờ tùy thân\" của {o}, "
                                         "dd/mm/yyyy."},
        {"name": f"{p}_NoiCap",
         "desc": f"Nơi cấp giấy tờ tùy thân CHỈ khi ghi ở dòng \"Giấy tờ tùy thân\" của {o}, chép nguyên văn; cụm in sẵn "
                 "liệt kê nhiều cơ quan ngăn bằng \"/\" mà không đánh dấu cơ quan nào thì bỏ."},
    ]


FIELDS: list[dict] = [
    *_the("Nam", "Nam"),
    *_the("Nu", "Nữ"),
    *_to_khai("Nam", "nam", "chồng"),
    *_to_khai("Nu", "nữ", "vợ"),
    # Lần đăng ký kết hôn TRƯỚC ĐÂY — xem <ket_hon_cu> trong EXTRA_RULES.
    {"name": "KetHonCu_So",
     "desc": "Số Giấy chứng nhận kết hôn / số đăng ký kết hôn trước đây, chỉ khi có giá trị thật ghi ngay sau nhãn. "
             "Số chú thích in sẵn trong ngoặc như \"(5)\" là ô TRỐNG → bỏ."},
    {"name": "KetHonCu_QuyenSo",
     "desc": "Quyển số đăng ký kết hôn trước đây, chỉ khi có giá trị thật ngay sau nhãn \"Quyển số\" của lần đăng ký "
             "đó. Số chú thích in sẵn trong ngoặc như \"(5)\" là ô TRỐNG → bỏ."},
    {"name": "KetHonCu_NgayDangKy",
     "desc": "Ngày đăng ký kết hôn trước đây, dd/mm/yyyy; chỉ ghi năm hoặc tháng/năm thì bỏ."},
    {"name": "KetHonCu_TinhDangKy", "desc": "Tỉnh/thành phố của cơ quan đăng ký kết hôn trước đây, chép như giấy ghi."},
    {"name": "KetHonCu_XaDangKy",
     "desc": "Tên PHƯỜNG/XÃ/THỊ TRẤN của cơ quan đăng ký kết hôn trước đây, giữ tiền tố đơn vị, bỏ \"UBND\" và phần "
             "huyện / tỉnh ghi sau; chính cơ quan là UBND cấp huyện thì bỏ field."},
    {"name": "CopyRequest_WantsCopy",
     "desc": "\"Có\"/\"Không\" theo ô được tích ở dòng \"Đề nghị cấp bản sao\" trên TỜ KHAI ĐĂNG KÝ LẠI KẾT HÔN; cả "
             "hai ô trống và không có số lượng thì bỏ."},
    {"name": "CopyRequest_Quantity",
     "desc": "Số lượng bản sao dương ghi ở dòng \"Số lượng: ... bản\" trên TỜ KHAI (\"02 bản\" → \"2\"); để chấm, "
             "chỉ có số chú thích in sẵn như \"(6)\", \"(7)\" hoặc 0 thì bỏ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("BenNam_NgaySinh", "BenNam_NgayCap", "BenNu_NgaySinh", "BenNu_NgayCap", "KetHonCu_NgayDangKy",
              "ToKhaiNam_NgaySinh", "ToKhaiNam_NgayCap", "ToKhaiNu_NgaySinh", "ToKhaiNu_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("BenNam_NoiCuTru_TrongNuoc", "BenNu_NoiCuTru_TrongNuoc",
              "ToKhaiNam_NoiCuTru_TrongNuoc", "ToKhaiNu_NoiCuTru_TrongNuoc"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    # Bên nam (chồng).
    "HoTenBenNam": "x-input",
    "SoDinhDanh_BenNam": "x-input",
    "SoGiayToDinhDanh_BenNam": "x-input",
    "LoaiGiayToDinhDanh_BenNam": "x-select",
    "NgaySinhBenNam": "x-date",
    "NgayCapDD_BenNam": "x-date",
    "NoiCapDD_BenNam": "x-input",
    "DanTocBenNam": "x-select",
    "QuocTichBenNam": "x-select",
    "LoaiCuTru_BenNam": "x-select",
    "NoiCuTru_BenNam": "x-radio",
    "NoiCuTru_BenNam_TrongNuoc": "x-select-area",
    "SoLanKetHon_BenNam": "x-input-number",
    "LoaiTinhTrangHonNhan_BenNam": "x-select",
    # Bên nữ (vợ).
    "HoTenBenNu": "x-input",
    "SoDinhDanh_BenNu": "x-input",
    "SoGiayToDinhDanh_BenNu": "x-input",
    "LoaiGiayToDinhDanh_BenNu": "x-select",
    "NgaySinhBenNu": "x-date",
    "NgayCapDD_BenNu": "x-date",
    "NoiCapDD_BenNu": "x-input",
    "DanTocBenNu": "x-select",
    "QuocTichBenNu": "x-select",
    "LoaiCuTru_BenNu": "x-select",
    "NoiCuTru_BenNu": "x-radio",
    "NoiCuTru_BenNu_TrongNuoc": "x-select-area",
    "SoLanKetHon_BenNu": "x-input-number",
    "LoaiTinhTrangHonNhan_BenNu": "x-select",
    # Hồ sơ gốc (đăng ký lại).
    "loaiDangKy": "x-radio",
    "soDangKyTruocDay": "x-input",
    "quyenDangKyTruocDay": "x-input",
    "ngayDangKyTruocDay": "x-date",
    "noiDangKyTruocDay_filter": "x-select",  # dropdown tỉnh/thành (lọc trước)
    "noiDangKyTruocDay": "x-select",          # dropdown đơn vị (load theo filter)
    # Khác.
    "CapBanSao": "x-radio",
    # SoLuong: ô số lượng bản sao (input trần, hiện khi chọn "Có").
    "SoLuong": "raw",
}
