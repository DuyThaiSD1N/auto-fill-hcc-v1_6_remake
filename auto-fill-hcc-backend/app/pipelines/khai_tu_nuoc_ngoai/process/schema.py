"""Schema cho "Đăng ký khai tử có yếu tố nước ngoài" (1.001766).

Cổng thật: DVCQG chọn cơ quan xong chuyển sang cổng Bộ Tư pháp (dichvucongnganhtuphap.moj.gov.vn/nop-ho-so?
maThuTuc=1.001766), bước "Kê khai thông tin" là eForm "MẪU HỘ TỊCH ĐIỆN TỬ TƯƠNG TÁC ĐĂNG KÝ KHAI TỬ" — cùng mẫu khai tử
2053 (monitor-fe/src/simulations/mau-eform/2053.json), tên ô theo file Mapping_1.001766 của BA.

LLM chỉ trả dữ kiện theo vai (người yêu cầu / người chết / giấy báo tử); ô UI, mã radio, nhánh trong nước / nước ngoài
do mapper tính.
"""

FIELDS: list[dict] = [
    # Người yêu cầu (mục I) — theo tờ khai + CCCD / hộ chiếu của chính người đó.
    {"name": "Requester_FullName", "desc": "Họ tên người yêu cầu đăng ký khai tử."},
    {"name": "Requester_BirthDate", "desc": "Ngày sinh người yêu cầu, dd/mm/yyyy (theo CCCD nếu tờ khai bỏ trống)."},
    {"name": "Requester_IdType", "desc": 'Loại giấy tờ tùy thân người yêu cầu ghi trên giấy: "Căn cước công dân", '
                                        '"Thẻ căn cước", "Chứng minh nhân dân", "Hộ chiếu"...'},
    {"name": "Requester_IdNumber", "desc": "Số CCCD / số định danh / số hộ chiếu của người yêu cầu."},
    {"name": "Requester_IdIssueDate", "desc": "Ngày cấp giấy tờ tùy thân người yêu cầu, dd/mm/yyyy."},
    {"name": "Requester_IdIssuePlace", "desc": "Cơ quan cấp giấy tờ tùy thân người yêu cầu."},
    {"name": "Requester_Residence", "desc": "Nơi cư trú người yêu cầu, object {quocGia,tinh,xa,chiTietDuoiXa}."},
    {"name": "Requester_Relationship", "desc": 'Quan hệ của người yêu cầu với người đã chết, chép nguyên văn '
                                              '(vd "Con", "Vợ", "Người được ủy quyền").'},

    # Người được khai tử (mục II) — người nước ngoài: theo hộ chiếu + tờ khai + giấy báo tử.
    {"name": "Deceased_FullName", "desc": "Họ tên người đã chết."},
    {"name": "Deceased_BirthDate", "desc": "Ngày sinh người đã chết, dd/mm/yyyy; chỉ có năm thì yyyy."},
    {"name": "Deceased_Gender", "desc": 'Giới tính người đã chết: "Nam" hoặc "Nữ".'},
    {"name": "Deceased_Ethnicity", "desc": 'Dân tộc người đã chết chép đúng chữ trên giấy (vd "Hán").'},
    {"name": "Deceased_Nationality", "desc": "Quốc tịch người đã chết bằng tiếng Việt (vd \"Trung Quốc\")."},
    {"name": "Deceased_IdType", "desc": 'Loại giấy tờ tùy thân người đã chết: "Hộ chiếu", "Căn cước công dân", '
                                       '"Thẻ cư trú"...'},
    {"name": "Deceased_IdNumber", "desc": "Số hộ chiếu / số giấy tờ tùy thân người đã chết."},
    {"name": "Deceased_IdIssueDate", "desc": "Ngày cấp giấy tờ tùy thân người đã chết, dd/mm/yyyy."},
    {"name": "Deceased_IdIssuePlace", "desc": "Cơ quan cấp giấy tờ tùy thân người đã chết, theo tờ khai tiếng Việt."},
    {"name": "Deceased_ResidenceType", "desc": 'Nhãn loại cư trú nếu giấy ghi rõ: "Thường trú" / "Tạm trú".'},
    {"name": "Deceased_Residence", "desc": "Nơi cư trú cuối cùng của người đã chết, object "
                                          "{quocGia,tinh,xa,chiTietDuoiXa}; địa chỉ nước ngoài ghi đúng quocGia."},
    {"name": "Deceased_DeathDate", "desc": 'Ngày chết dd/mm/yyyy, lấy từ "Đã chết vào lúc" / "Đã tử vong vào lúc".'},
    {"name": "Deceased_DeathTime", "desc": 'Giờ chết dạng "HH:mm"; ví dụ "09 giờ 40 phút" -> "09:40".'},
    {"name": "Deceased_DeathPlace", "desc": "Nơi chết, object {quocGia,tinh,xa,chiTietDuoiXa}."},
    {"name": "Deceased_DeathCause", "desc": "Nguyên nhân chết; tờ khai để trống thì bỏ."},

    # Nhân thân CHÉP NGUYÊN VĂN từ TỜ KHAI để Python đối chiếu với CCCD (khuôn đăng ký lại khai tử).
    {"name": "ToKhai_NguoiYeuCau_HoTen", "desc": "Họ tên người yêu cầu CHÉP NGUYÊN VĂN từ tờ khai; không lấy từ CCCD."},
    {"name": "ToKhai_NguoiYeuCau_SoDinhDanh", "desc": "Số giấy tờ tùy thân người yêu cầu CHÉP NGUYÊN VĂN từ tờ khai."},
    {"name": "ToKhai_NguoiChet_HoTen", "desc": "Họ tên người đã chết CHÉP NGUYÊN VĂN từ tờ khai."},
    {"name": "ToKhai_NguoiChet_SoDinhDanh", "desc": "Số giấy tờ tùy thân người đã chết CHÉP NGUYÊN VĂN từ tờ khai."},
    {"name": "ToKhai_NguoiChet_NgaySinh", "desc": "Ngày sinh người đã chết CHÉP từ tờ khai, dd/mm/yyyy (chỉ năm thì yyyy)."},

    # Loại đăng ký: chỉ khi giấy ghi rõ; không có thì Python tính theo hạn 15 ngày kể từ ngày chết.
    {"name": "Registration_Type", "desc": 'Chỉ khi tờ khai ghi/tích rõ: "Đăng ký đúng hạn", "Đăng ký quá hạn" hoặc '
                                         '"Đăng ký khai tử cho người chết đã lâu".'},

    # Giấy báo tử / giấy tờ thay thế.
    {"name": "DeathNotice_Type", "desc": "Loại giấy báo tử / giấy tờ thay thế nếu giấy ghi rõ."},
    {"name": "DeathNotice_Number", "desc": "Số giấy báo tử / giấy tờ thay thế; chỉ trả nếu có giá trị thật."},
    {"name": "DeathNotice_IssueDate", "desc": "Ngày cấp giấy báo tử / giấy tờ thay thế, dd/mm/yyyy."},
    {"name": "DeathNotice_IssueAgency", "desc": "Cơ quan / cơ sở khám bệnh, chữa bệnh cấp giấy báo tử."},

    # Đề nghị cấp bản sao.
    {"name": "CopyRequest_WantsCopy", "desc": '"Có" nếu tờ khai tích đề nghị cấp bản sao, "Không" nếu tích không.'},
    {"name": "CopyRequest_Quantity", "desc": "Số lượng bản sao, chỉ trả số nếu tờ khai ghi rõ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Requester_BirthDate", "Requester_IdIssueDate", "Deceased_IdIssueDate", "Deceased_DeathDate",
              "DeathNotice_IssueDate"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Requester_Residence", "Deceased_Residence", "Deceased_DeathPlace"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Thứ tự dict = thứ tự phát ra trên form: ô tích / ô chọn đứng trước khối nó mở ra.
UI_COMP_BY_NAME = {
    # I. Người yêu cầu — cổng đổ sẵn theo tài khoản; nộp thay thì ghi đè theo người yêu cầu trên hồ sơ.
    "HoVaTenC": "x-input",
    "NgaySinhC": "x-date",
    "SoDinhDanhC": "x-input",
    "LoaiGiayToDinhDanhC": "x-select",
    "nycTenGiayTo": "x-select-area",
    "SoGiayToDinhDanhC": "x-input",
    "NgayCapDDC": "x-date",
    "NoiCapDDC": "x-input",
    "nycLoaiCuTru": "x-select",
    "nycNoiCuTru": "x-radio",
    "nycNoiCuTru_TrongNuoc": "x-select-area",
    "nycNoiCuTru_NuocNgoai": "x-select-area",
    "QuanHe": "x-input",
    # II. Người được khai tử.
    "loaiDangKy": "x-radio",
    "HoTen": "x-input",
    "NgaySinh": "x-input",
    "GioiTinh": "x-select",
    "nktDanToc": "x-select",
    "nktDanTocKhac": "x-select-area",
    "nktQuocTich": "x-select",
    "SoDinhDanh": "x-input",
    "LoaiGiayToDinhDanh": "x-select",
    "nktTenGiayTo": "x-select-area",
    "SoGiayToDinhDanh": "x-input",
    "NgayCapDD": "x-date",
    "NoiCapDD": "x-input",
    "nktLoaiCuTru": "x-select",
    "nktNoiCuTru": "x-radio",
    "nktNoiCuTru_TrongNuoc": "x-select-area",
    "nktNoiCuTru_NuocNgoai": "x-select-area",
    "NgayMat": "x-date-text",
    "GioMat": "x-input",
    "PhutMat": "x-input",
    "nktNoiChet": "x-radio",
    "nktNoiChet_TrongNuoc": "x-select-area",
    "nktNoiChet_NuocNgoai": "x-select-area",
    "NguyenNhanMat": "x-input",
    # Giấy báo tử / giấy tờ thay thế.
    "gbtLoai": "x-select-default",
    "gbtSo": "x-input",
    "gbtNgay": "x-date",
    "gbtCoQuanCap": "x-input",
    # Đề nghị cấp bản sao: radio Có/Không (mẫu 2053) + ô số lượng là input trần trong khối "ThongTin". Mapping BA chụp
    # được ô SoLuong không thấy radio → "raw" tìm input theo name, có hay không có khối bọc đều điền được.
    "CapBanSao": "x-radio",
    "SoLuong": "raw",
}
