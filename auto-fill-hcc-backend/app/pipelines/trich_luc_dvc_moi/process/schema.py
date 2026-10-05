"""Schema trích xuất cho "Cấp bản sao Trích lục hộ tịch" trên Cổng DVC quốc gia mới (SurveyJS).

Khối THÔNG TIN NGƯỜI NỘP do cổng đổ từ tài khoản định danh và khóa readonly → không trích.
LLM chỉ trả dữ kiện của NGƯỜI ĐƯỢC CẤP (đúng người đã chốt ở bước phân vai) và GIẤY TỜ HỘ TỊCH
đã đăng ký; quan hệ người nộp ↔ người được cấp lấy từ bước phân vai, mapper kiểm lại bằng số định danh.
"""

FIELDS: list[dict] = [
    {"name": "NguoiDuocCap_HoTen",
     "desc": "Họ, chữ đệm, tên của NGƯỜI ĐƯỢC CẤP bản sao — đúng người ở khối <nguoi_duoc_cap> đã phân vai."},
    {"name": "NguoiDuocCap_SoDinhDanh",
     "desc": "Số định danh cá nhân (đúng 12 chữ số) của người được cấp. Số 9 chữ số là CMND → không trả "
             "ở đây. Dòng 'Số: <mã>/<năm>' đầu giấy hộ tịch là số đăng ký, không phải số định danh."},
    {"name": "NguoiDuocCap_NgaySinh", "desc": "Ngày sinh người được cấp, dd/mm/yyyy."},
    {"name": "NguoiDuocCap_GioiTinh", "desc": 'Giới tính người được cấp: "Nam" hoặc "Nữ".'},
    {"name": "NguoiDuocCap_DanToc", "desc": "Dân tộc người được cấp, giữ nguyên tên ghi trên giấy."},
    {"name": "NguoiDuocCap_QuocTich", "desc": "Quốc tịch người được cấp nếu giấy tờ có ghi."},
    {"name": "NguoiDuocCap_LoaiGiayTo",
     "desc": "Loại giấy tờ tùy thân CỦA CHÍNH người được cấp: Căn cước, Căn cước công dân, CMND hoặc Hộ chiếu."},
    {"name": "NguoiDuocCap_SoGiayTo", "desc": "Số giấy tờ tùy thân CỦA CHÍNH người được cấp."},
    {"name": "NguoiDuocCap_NgayCap", "desc": "Ngày cấp giấy tờ tùy thân của người được cấp, dd/mm/yyyy."},
    {"name": "NguoiDuocCap_NoiCap",
     "desc": "Cơ quan cấp giấy tờ tùy thân của người được cấp, CHÉP ĐÚNG chữ ghi trên giấy (kể cả viết tắt như "
             "'CA <tỉnh>'). Giấy không ghi cơ quan cấp → bỏ field, không tự điền cơ quan nào."},
    {"name": "NguoiDuocCap_NoiCuTru",
     "desc": "Nơi cư trú của người được cấp, object {quocGia,tinh,xa,diaChi[,huyen]}."},

    {"name": "GiayTo_LoaiSuKien",
     "desc": 'Loại trích lục CẦN CẤP BẢN SAO, một mã: "birth" (khai sinh), "marriage" (kết hôn / ghi chú kết hôn), '
             '"death" (khai tử), "guardianship" (đăng ký giám hộ), "guardianship_end" (chấm dứt giám hộ), '
             '"parent_child" (nhận cha, mẹ, con), "adoption" (nuôi con nuôi), "civil_change" (thay đổi, cải chính, '
             'bổ sung thông tin hộ tịch, xác định lại dân tộc), "divorce" (ghi chú ly hôn), '
             '"supervision" (giám sát giám hộ), "supervision_end" (chấm dứt giám sát giám hộ).'},
    {"name": "GiayTo_TenGiayTo",
     "desc": "Tên giấy tờ hộ tịch đã đăng ký cần cấp bản sao (vd Giấy khai sinh, Giấy chứng nhận kết hôn, "
             "Trích lục khai tử). Không lấy tên tờ khai/giấy ủy quyền."},
    {"name": "GiayTo_CoQuanDangKy", "desc": "Cơ quan đã đăng ký sự kiện hộ tịch trước đây."},
    {"name": "GiayTo_So", "desc": "Số đăng ký của sự kiện hộ tịch (dòng 'Số:' / 'Số đăng ký')."},
    {"name": "GiayTo_QuyenSo",
     "desc": "Quyển số đăng ký, CHỈ khi nhãn 'Quyển số' có giá trị thật ngay sau nhãn."},
    {"name": "GiayTo_NgayDangKy", "desc": "Ngày đăng ký sự kiện hộ tịch, dd/mm/yyyy."},
    {"name": "SoLuongBanSao",
     "desc": "Số lượng bản sao yêu cầu, chỉ khi tờ khai/giấy ủy quyền ghi rõ; số nguyên dương."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("NguoiDuocCap_NgaySinh", "NguoiDuocCap_NgayCap", "GiayTo_NgayDangKy"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
COMPACT_COMP_BY_NAME["NguoiDuocCap_NoiCuTru"] = "x-select-area"

# Ô SurveyJS: name = phần trước "__<số>" của data-name (hậu tố đổi theo phiên bản biểu mẫu nên
# extension khớp theo tiền tố). comp chọn cách ghi giá trị trên model survey.
UI_COMP_BY_NAME = {
    "citizenQuanhe": "sjs-dropdown",           # Quan hệ với người được cấp
    "citizenField8": "sjs-text",               # Quan hệ khác
    # THÔNG TIN NGƯỜI ĐƯỢC CẤP GIẤY TỜ HỘ TỊCH
    "citizenNDK_SoDinhDanh": "sjs-text",
    "citizenNDK_HoVaTen": "sjs-text",
    "citizenNDK_NgaySinh": "sjs-text",         # ô text dd/mm/yyyy, không phải date
    "citizenNDK_LoaiGiayToTuyThan": "sjs-dropdown",
    "citizenNDK_SoGiayToTuyThan": "sjs-text",
    "citizenNDK_NoiCap": "sjs-text",
    "citizenNDK_NgayCap": "sjs-date",
    "citizenField13": "sjs-dropdown",          # Giới tính
    "citizenNDK_LoaiCuTru": "sjs-dropdown",
    "citizenField32": "sjs-dropdown",          # Dân tộc
    "citizenNDK_Noicutru": "sjs-radio",        # 1 = Trong nước; 4 ô dưới chỉ hiện sau khi chọn
    "citizenField21": "sjs-dropdown",          # Quốc gia nơi cư trú
    "citizenNDK_TinhThanh": "sjs-dropdown",
    "citizenNDK_PhuongXa": "sjs-dropdown",     # danh mục tải theo tỉnh → phát sau tỉnh
    "citizenField38": "sjs-text",              # Nơi cư trú địa chỉ chi tiết
    # THÔNG TIN VỀ GIẤY TỜ HỘ TỊCH ĐÃ ĐĂNG KÝ
    "citizenLoaiViecYeuCau": "sjs-dropdown",
    "citizenHoSo_CoQuanDangKy": "sjs-text",
    "citizenTenGiayToHoTich": "sjs-text",
    "citizencauhoi3": "sjs-text",              # Số đăng ký
    "citizencauhoi4": "sjs-text",              # Quyển số
    "citizencauhoi5": "sjs-date",              # Ngày tháng năm đăng ký
    "citizenSoLuongBanSao": "sjs-text",
}
