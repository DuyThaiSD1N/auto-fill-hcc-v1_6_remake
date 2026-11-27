"""Facts nguồn cho thủ tục tách thửa hoặc hợp thửa đất (1.012784) — cổng iGate Ninh Bình.

Form.io Bước 1 (file mapping "Tách thửa - Phi địa giới", DOM cổng Ninh Bình) có ba khối, KHÔNG có khối chủ hồ sơ riêng:
- Thông tin người nộp (fieldSet1): fullname/birthday/phoneNumber/email/identityNumber/identityDate/identityAgency/
  province/village/address + organization/taxCode/province1/village1/address1 (chỉ khi tổ chức đứng tên).
- Địa chỉ thửa đất (panel2): TuCachNguoiNopHoSo/SoThuaDat/SoToBanDo/diaChiThuaDat/province2 (KHOÁ "Tỉnh Ninh Bình")/
  village2 (chỉ 98 xã/phường Ninh Bình).
- Thông tin người nhận kết quả (ttt1): hoTen/soCCCD/diaChi/hinhThucNopHs.
Hai vai: CHỦ HỒ SƠ = người sử dụng đất đứng Đơn đề nghị tách thửa, hợp thửa (Mẫu số 01/ĐK); NGƯỜI NỘP = bên được ủy quyền
nếu có văn bản ủy quyền, không có thì chính chủ hồ sơ.
"""

FIELDS: list[dict] = [
    {
        "name": "ChuHoSo_LoaiChuThe",
        "desc": '"Tổ chức" nếu người sử dụng đất đề nghị tách/hợp thửa là công ty/doanh nghiệp/HTX/cơ quan; "Cá nhân" nếu '
        "là một người (kể cả đại diện hộ gia đình).",
    },
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Tên CHỦ HỒ SƠ = người sử dụng đất ĐỀ NGHỊ tách/hợp thửa: mục 'I.1. Người sử dụng đất – a) Tên' của Đơn đề "
        "nghị tách thửa đất, hợp thửa đất (Mẫu số 01/ĐK) -> người đứng tên Giấy chứng nhận đã cấp -> 'Tên người sử dụng "
        "đất' trên Bản vẽ tách thửa. Bỏ danh xưng Ông/Bà. Có ủy quyền thì đây là BÊN ỦY QUYỀN. KHÔNG lấy người nhận các "
        "thửa mới sau tách (mục 'Thửa thứ 1/2…'), KHÔNG lấy đơn vị đo đạc lập bản vẽ.",
    },
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh đầy đủ của CHỦ HỒ SƠ, dd/mm/yyyy — CCCD đúng người. Chỉ có năm sinh "
     "thì bỏ field, không suy từ số định danh."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/CMND/định danh của CHỦ HỒ SƠ (Đơn mục a) 'CCCD: …', Giấy chứng nhận, "
     "Bản vẽ, thẻ CCCD), chỉ chữ số."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD của CHỦ HỒ SƠ, dd/mm/yyyy — chỉ lấy trên thẻ CCCD đúng người."},
    {"name": "ChuHoSo_NoiCap", "desc": "Nơi cấp CCCD của CHỦ HỒ SƠ, cùng giấy với số và ngày cấp. Viết tắt 'CCS QLHC về "
     "TTXH' -> 'Cục Cảnh sát quản lý hành chính về trật tự xã hội'; thẻ căn cước mới -> 'Bộ Công an'."},
    {
        "name": "ChuHoSo_DiaChi",
        "desc": "Nơi THƯỜNG TRÚ của CHỦ HỒ SƠ, object {quocGia,tinh,xa,chiTietDuoiXa}. Ưu tiên: CCCD 'Nơi thường trú' "
        "-> Đơn mục 'c) Địa chỉ' -> địa chỉ người sử dụng đất trên Bản vẽ. chiTietDuoiXa = số nhà/thôn/tổ; giấy chỉ ghi "
        "tới phường thì để trống. KHÔNG lấy địa chỉ thửa đất.",
    },
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại của CHỦ HỒ SƠ ở Đơn mục 'd) Điện thoại liên hệ', chỉ chữ số. "
     "Ô bỏ trống (chỉ có dấu chấm) thì bỏ field."},
    {"name": "ChuHoSo_Email", "desc": "Hộp thư điện tử của CHỦ HỒ SƠ ở Đơn mục d) nếu có."},
    {"name": "ChuHoSo_MaSoThue", "desc": "Mã số doanh nghiệp/mã số thuế khi CHỦ HỒ SƠ là TỔ CHỨC (Đơn mục 'b) Giấy tờ "
     "pháp nhân số', Giấy chứng nhận đăng ký doanh nghiệp). Chỉ chữ số. KHÔNG lấy số Giấy phép đo đạc."},
    {
        "name": "NguoiNop_HoTen",
        "desc": "Họ tên NGƯỜI NỘP. Có văn bản/hợp đồng ủy quyền thì lấy BÊN ĐƯỢC ỦY QUYỀN; không có thì người nộp chính là "
        "CHỦ HỒ SƠ (chép đúng ChuHoSo_HoTen).",
    },
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh đầy đủ của NGƯỜI NỘP, dd/mm/yyyy (CCCD / văn bản ủy quyền). Chỉ có "
     "năm thì bỏ field."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền phải lấy của BÊN ĐƯỢC "
     "ỦY QUYỀN."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD của NGƯỜI NỘP, dd/mm/yyyy, đi cùng đúng số giấy tờ."},
    {"name": "NguoiNop_NoiCap", "desc": "Nơi cấp CCCD của NGƯỜI NỘP, đi cùng đúng số và ngày cấp, ghi đầy đủ không viết "
     "tắt."},
    {
        "name": "NguoiNop_DiaChi",
        "desc": "Nơi thường trú của NGƯỜI NỘP, object {quocGia,tinh,xa,chiTietDuoiXa}. Có ủy quyền thì lấy của BÊN ĐƯỢC ỦY "
        "QUYỀN (CCCD/văn bản ủy quyền); tự nộp thì chép nguyên ChuHoSo_DiaChi. KHÔNG lấy địa chỉ thửa đất.",
    },
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại NGƯỜI NỘP, chỉ chữ số. Không lấy số của chủ hồ sơ khi hai người "
     "khác nhau."},
    {"name": "NguoiNop_Email", "desc": "Email của NGƯỜI NỘP nếu có."},
    {
        "name": "ThuaDat_SoThua",
        "desc": "Số thửa đất GỐC đề nghị tách (hoặc thửa thứ nhất khi hợp): Giấy chứng nhận 'a. Thửa đất số' -> Đơn mục "
        "'2. a) Tách thửa đất số' -> Bản vẽ 'Thửa số'. Chỉ lấy số. KHÔNG lấy số thửa mới sau tách (16-1, 16-2…).",
    },
    {"name": "ThuaDat_SoTo", "desc": "Số tờ bản đồ của thửa đất gốc: Giấy chứng nhận 'tờ bản đồ số' -> Đơn -> Bản vẽ. "
     "Chỉ lấy số."},
    {
        "name": "ThuaDat_DiaChi",
        "desc": "ĐỊA CHỈ THỬA ĐẤT gốc, object {quocGia,tinh,xa,chiTietDuoiXa}: Giấy chứng nhận 'e. Địa chỉ' -> Đơn 'địa chỉ "
        "thửa đất' -> Bản vẽ. Cụm huyện/thành phố cũ BỎ. KHÔNG lấy nơi thường trú của người.",
    },
    {
        "name": "ThuaDat_DiaChiDayDu",
        "desc": "Chép NGUYÊN VĂN địa chỉ thửa đất gốc trên Giấy chứng nhận (mục 'Địa chỉ' của thông tin thửa đất), thiếu thì "
        "lấy ở Đơn mục 2.a) 'địa chỉ thửa đất'.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ChuHoSo_DiaChi", "NguoiNop_DiaChi", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô Form.io trên cổng (cột "formcontrolname / field-key" của file mapping). data[province2] bị khoá "Tỉnh Ninh Bình" và
# data[hinhThucNopHs] cổng chọn sẵn "Trực tuyến" nên không khai.
UI_COMP_BY_NAME = {
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[phoneNumber]": "dom-input",
    "data[email]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[province]": "dom-select",
    "data[village]": "dom-select",
    "data[address]": "dom-input",
    "data[organization]": "dom-input",
    "data[taxCode]": "dom-input",
    "data[province1]": "dom-select",
    "data[village1]": "dom-select",
    "data[address1]": "dom-input",
    "data[TuCachNguoiNopHoSo]": "dom-input",
    "data[SoThuaDat]": "dom-input",
    "data[SoToBanDo]": "dom-input",
    "data[diaChiThuaDat]": "dom-input",
    "data[village2]": "dom-select",
    "data[hoTen]": "dom-input",
    "data[soCCCD]": "dom-input",
    "data[diaChi]": "dom-input",
}
