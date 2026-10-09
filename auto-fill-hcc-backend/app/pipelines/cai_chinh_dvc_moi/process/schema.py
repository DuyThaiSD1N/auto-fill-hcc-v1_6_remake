"""Schema trích xuất cho "Thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc" trên Cổng DVC
quốc gia mới (SurveyJS).

Khối THÔNG TIN NGƯỜI NỘP do cổng đổ từ tài khoản định danh → không trích. LLM trả dữ kiện của NGƯỜI CÓ NỘI
DUNG THAY ĐỔI (đúng người đã chốt ở bước phân vai), giấy tờ hộ tịch đã đăng ký và nội dung đề nghị.
"""

FIELDS: list[dict] = [
    {"name": "NguoiThayDoi_HoTen",
     "desc": "Họ, chữ đệm, tên ĐANG CÓ trong sổ hộ tịch của người có nội dung thay đổi — không lấy tên MỚI "
             "nêu ở phần nội dung đề nghị."},
    {"name": "NguoiThayDoi_SoDinhDanh",
     "desc": "Số định danh cá nhân (đúng 12 chữ số) của người có nội dung thay đổi. Số 9 chữ số là CMND → "
             "không trả ở đây."},
    {"name": "NguoiThayDoi_NgaySinh", "desc": "Ngày sinh người có nội dung thay đổi, dd/mm/yyyy."},
    {"name": "NguoiThayDoi_GioiTinh", "desc": 'Giới tính: "Nam" hoặc "Nữ".'},
    {"name": "NguoiThayDoi_DanToc",
     "desc": "Dân tộc ĐANG ghi trong hộ tịch (không lấy dân tộc mới đề nghị xác định lại)."},
    {"name": "NguoiThayDoi_QuocTich",
     "desc": "Quốc tịch ĐANG ghi trong hộ tịch / tờ khai (không lấy quốc tịch mới đề nghị thay đổi)."},
    {"name": "NguoiThayDoi_LoaiGiayTo",
     "desc": "Loại giấy tờ tùy thân CỦA CHÍNH người có nội dung thay đổi: Căn cước, Căn cước công dân, CMND, Hộ chiếu."},
    {"name": "NguoiThayDoi_SoGiayTo", "desc": "Số giấy tờ tùy thân CỦA CHÍNH người có nội dung thay đổi."},
    {"name": "NguoiThayDoi_NgayCap", "desc": "Ngày cấp giấy tờ tùy thân, dd/mm/yyyy."},
    {"name": "NguoiThayDoi_NoiCap",
     "desc": "Cơ quan cấp giấy tờ tùy thân, CHÉP ĐÚNG chữ ghi trên giấy (kể cả viết tắt). Giấy không ghi → bỏ."},
    {"name": "NguoiThayDoi_NoiCuTru",
     "desc": "Nơi cư trú của người có nội dung thay đổi, object {quocGia,tinh,xa,diaChi[,huyen]}."},

    {"name": "ViecDangKy",
     "desc": 'Loại việc đăng ký: "Cải chính", "Thay đổi", "Bổ sung" hoặc "Xác định lại dân tộc".'},
    {"name": "HoSo_LoaiGiayTo",
     "desc": 'Loại giấy tờ hộ tịch ĐÃ ĐĂNG KÝ cần sửa: "khai sinh", "khai tử", "kết hôn", "giám hộ", '
             '"giám sát giám hộ" hoặc "nhận cha mẹ con".'},
    {"name": "HoSo_So", "desc": "Số đăng ký của giấy tờ hộ tịch đã đăng ký."},
    {"name": "HoSo_QuyenSo", "desc": "Quyển số đăng ký, CHỈ khi nhãn 'Quyển số' có giá trị thật."},
    {"name": "HoSo_NgayDangKy", "desc": "Ngày đăng ký giấy tờ hộ tịch, dd/mm/yyyy."},
    {"name": "HoSo_NoiDangKy", "desc": "Cơ quan / nơi đã đăng ký giấy tờ hộ tịch."},
    {"name": "NoiDung",
     "desc": "Nội dung đề nghị thay đổi / cải chính / bổ sung / xác định lại dân tộc theo dòng 'Nội dung' của "
             "tờ khai (gồm thông tin cũ và mới), CHỈ các thay đổi — không kèm lý do; viết thành câu có nghĩa. Không "
             "có tờ khai mà có bản cam đoan → theo bản cam đoan, đúng chiều từ giá trị đang ghi trên giấy hộ tịch "
             "cần sửa thành giá trị theo giấy tờ khác."},
    {"name": "LyDo",
     "desc": "Lý do đề nghị theo dòng 'Lý do' của tờ khai (kể cả khi OCR nối nó vào cuối phần nội dung); "
             "viết thành câu ngắn có nghĩa. Không có tờ khai mà có bản cam đoan → câu ngắn tóm căn cứ trong bản cam "
             "đoan."},
    {"name": "SoLuongBanSao",
     "desc": "Số bản sao trích lục đề nghị cấp: số nguyên; tờ khai đánh dấu KHÔNG đề nghị cấp bản sao → 0. "
             "Tờ khai không ghi → bỏ field."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("NguoiThayDoi_NgaySinh", "NguoiThayDoi_NgayCap", "HoSo_NgayDangKy"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
COMPACT_COMP_BY_NAME["NguoiThayDoi_NoiCuTru"] = "x-select-area"

# Ô SurveyJS: name = phần trước "__<số>" của data-name (extension khớp theo tiền tố).
UI_COMP_BY_NAME = {
    "citizenNycNoicutru": "sjs-radio",                 # Nơi cư trú người nộp: cổng hay để trống
    "citizenQuanhevsngcaichinhhotich1": "sjs-radio",   # Bản thân / Khác
    "citizenMqhkhac": "sjs-text",                      # Quan hệ cụ thể, chỉ hiện khi chọn "Khác"
    # THÔNG TIN VỀ NGƯỜI CÓ NỘI DUNG THAY ĐỔI
    "citizenNDKHoTen": "sjs-text",
    "citizenNDKSodinhdanh": "sjs-text",
    # Cổng đã đổi ô ngày sinh từ "citizenNDKNgaysinh" (ô ngày) sang ô chữ dd/mm/yyyy dùng chung với trích lục.
    "citizenNDK_NgaySinh": "sjs-text",
    "citizenNDKLoaiGiaytotuythan": "sjs-dropdown",
    "citizenNDKSogiaytotuythan": "sjs-text",
    "citizenNDKNgaycapgiaytotuythan": "sjs-date",
    "citizenNDKCoquancap": "sjs-text",
    "citizenNDKLoaicutru": "sjs-dropdown",
    "citizenNDKGioitinh": "sjs-dropdown",
    "citizenNDKQuocTich": "sjs-dropdown",
    "citizenNDKDantoc": "sjs-dropdown",
    "citizenNDKNoiCuTru": "sjs-radio",                 # Trong Nước / Khác
    # Ô quốc gia/tỉnh/xã/chi tiết chỉ hiện sau khi chọn "Trong Nước", tên ô không cố định → extension dò
    # theo nhãn trong cùng khối với radio (khóa "radio").
    "citizenNDKNoiCuTru_TrongNuoc": "sjs-area",
    # Nội dung đề nghị
    "citizenViecDangKy": "sjs-dropdown",
    "citizenLoainghiepvu": "sjs-dropdown",             # Tên giấy tờ hộ tịch đã đăng ký
    "citizenTTSodangkyhosogoc": "sjs-text",
    "citizenTTQuyensodangkyhosogoc": "sjs-text",
    "citizenTTngayDangKyHSGoc": "sjs-date",
    "citizenTTNoidangkyhosogoc": "sjs-text",
    "citizenTTNoidungdk": "sjs-text",
    "citizenLydothaydoi": "sjs-text",
    "citizenSoluongbansao": "sjs-text",
}
