"""Compact schema for "Đăng ký khai tử".

The LLM returns only source facts from the paper/electronic declaration,
identity documents, and documents proving the death event. UI defaults,
duplicate identity fields, and form-specific component names are derived in
Python.
"""

FIELDS: list[dict] = [
    # CCCD/CMND CỦA NGƯỜI YÊU CẦU. Khi có nhiều thẻ, LLM định tuyến theo
    # requester_context; Python tiếp tục kiểm tra mỏ neo trước khi điền UI.
    {"name": "Cccd_HoTen",
     "desc": "Họ tên trên CCCD/CMND của NGƯỜI YÊU CẦU. Khi có 2 CCCD và đúng 1 CCCD "
             "khớp tên/số định danh trong requester_context, chỉ lấy CCCD khớp vào Cccd_*; "
             "CCCD còn lại là của người được đăng ký khai tử và phải đưa vào NguoiMat_*."},
    {"name": "Cccd_SoDinhDanh",
     "desc": "Số CCCD 12 chữ số hoặc CMND 9 chữ số của NGƯỜI YÊU CẦU; có thể đọc từ MRZ mặt sau."},
    {"name": "Cccd_NgaySinh",
     "desc": "Ngày sinh trên CCCD/CMND của NGƯỜI YÊU CẦU, dd/mm/yyyy; nếu chỉ có năm thì trả yyyy."},
    {"name": "Cccd_GioiTinh",
     "desc": 'Giới tính trên CCCD/CMND của NGƯỜI YÊU CẦU: "Nam" hoặc "Nữ".'},
    {"name": "Cccd_DanToc",
     "desc": "Dân tộc của NGƯỜI YÊU CẦU chỉ khi chính giấy tờ tùy thân có in nhãn dân tộc; "
             "CCCD/Căn cước thông thường không có dân tộc thì bỏ field, không suy."},
    {"name": "Cccd_QuocTich",
     "desc": "Quốc tịch trên CCCD/CMND của NGƯỜI YÊU CẦU nếu giấy có ghi."},
    {"name": "Cccd_NgayCap",
     "desc": "Ngày cấp CCCD/CMND của NGƯỜI YÊU CẦU, dd/mm/yyyy."},
    {"name": "Cccd_NoiCap",
     "desc": "Cơ quan cấp CCCD/CMND của NGƯỜI YÊU CẦU, lấy đúng nội dung cạnh ngày cấp: "
             "giữ Công an tỉnh/thành phố với CMND; chỉ trả Cục Cảnh sát hoặc Bộ Công an "
             "khi chính nguồn ghi như vậy; chỉ trả tên cơ quan, bỏ chức danh như CỤC TRƯỞNG."},
    {"name": "Cccd_NoiCuTru",
     "desc": "Địa chỉ thường trú/cư trú trên CCCD/CMND của NGƯỜI YÊU CẦU, object "
             "{quocGia,tinh,xa,diaChi}; xa bắt buộc khi giấy có."},
    {"name": "ToKhai_QuanHeNguoiYeuCau",
     "desc": 'Quan hệ của người yêu cầu với người đã chết, chỉ lấy từ nhãn "Quan hệ với người đã chết" '
             "có giá trị thật; không lấy quan hệ của người khác được nhắc trong công văn."},
    {"name": "ToKhai_LoaiDangKy",
     "desc": 'Loại đăng ký chỉ lấy khi Tờ khai đăng ký khai tử/mẫu hộ tịch điện tử ghi rõ tại nhãn '
             '"Loại đăng ký". Chỉ trả một trong: "Đăng ký đúng hạn", "Đăng ký quá hạn", '
             '"Đăng ký khai tử cho người chết đã lâu". Nếu tài liệu không ghi thì bỏ field; Python '
             'sẽ mặc định "Đăng ký đúng hạn".'},

    # Danh tính người mất và sự kiện chết. Metadata giấy báo tử vẫn giữ tiền tố Gbt_*.
    {"name": "NguoiMat_HoTen",
     "desc": "Họ tên người được đăng ký khai tử. Ưu tiên giấy tờ tùy thân của người chết nếu xác định "
             "đúng vai; tiếp theo giấy báo tử/giấy tờ thay thế; tiếp theo tờ khai đăng ký khai tử. "
             "Nếu thiếu các nguồn trên, lấy người trong câu công văn hành chính ghi rõ "
             '"đăng ký khai tử ... cho ông/bà <họ tên>".'},
    {"name": "NguoiMat_NgaySinh",
     "desc": "Ngày sinh người được đăng ký khai tử, dd/mm/yyyy; nếu chỉ có năm thì trả yyyy. "
             "Ưu tiên giấy tờ tùy thân xác định đúng người chết, rồi nguồn khai tử ghi rõ. "
             "Công văn về người chết lâu năm ghi rõ sinh năm yyyy thì được trả yyyy."},
    {"name": "NguoiMat_GioiTinh",
     "desc": 'Giới tính người được đăng ký khai tử: "Nam" hoặc "Nữ"; ưu tiên giấy tờ tùy thân '
             'xác định đúng người chết, rồi nguồn khai tử có nhãn giới tính rõ; không suy từ "ông/bà".'},
    {"name": "NguoiMat_DanToc",
     "desc": 'Dân tộc người mất(Kinh, Mông, ...). Thứ tự nguồn bắt buộc: (1) nhãn "Dân tộc" trong KHỐI NGƯỜI CHẾT '
             "trên Tờ khai đăng ký khai tử; (2) Giấy báo tử/giấy chứng tử; (3) giấy tờ khác có ghi rõ; "},
    {"name": "NguoiMat_QuocTich",
     "desc": "Quốc tịch người được đăng ký khai tử; ưu tiên giấy tờ tùy thân xác định đúng người chết, "
             "rồi giấy báo tử/giấy tờ thay thế, rồi tờ khai."},
    {"name": "NguoiMat_SoDinhDanh",
     "desc": "Số CCCD (12 chữ số) hoặc CMND (9 chữ số) được nguồn gán trực tiếp cho người tử vong; "
             "có thể lấy từ CCCD còn lại khi CCCD kia khớp requester_context. Không lấy số của người "
             "yêu cầu/người khác trong công văn."},
    {"name": "NguoiMat_NgayCapGiayTo",
     "desc": "Ngày cấp giấy tờ tùy thân người tử vong, dd/mm/yyyy. Khi đã xác định đúng CCCD/CMND "
             "của người chết và OCR mặt sau có nhãn Ngày, tháng, năm/Date, month, year thì BẮT BUỘC "
             "trả ngày đó; không lấy ngày cấp của người yêu cầu/người khác."},
    {"name": "NguoiMat_NoiCapGiayTo",
     "desc": "Nơi cấp giấy tờ tùy thân người tử vong. Khi đã xác định đúng CCCD/CMND của người chết và "
             "OCR có cơ quan cấp thì BẮT BUỘC trả tên cơ quan đó; bỏ chức danh như CỤC TRƯỞNG và không "
             "lấy cơ quan cấp giấy tờ của người yêu cầu/người khác."},
    {"name": "NguoiMat_NoiCuTruCuoiCung",
     "desc": 'NƠI CƯ TRÚ CUỐI CÙNG của người chết, object {quocGia,tinh,xa,diaChi}. Thứ tự nguồn: '
             '(1) mục "Nơi cư trú cuối cùng" trong Tờ khai đăng ký khai tử; '
             '(2) mục "Nơi cư trú trước khi chết/cuối cùng" trong giấy báo tử/giấy tờ thay thế; '
             "(3) với người chết lâu năm, địa chỉ gần thời điểm chết nhất mà văn bản có thẩm quyền xác "
             "nhận trực tiếp thuộc người chết; (4) nơi thường trú trên CCCD/CMND người chết. Không dùng "
             "địa chỉ người yêu cầu, vợ/chồng hoặc chủ hộ khác."},
    {"name": "NguoiMat_NgayMat",
     "desc": 'Ngày tử vong, dd/mm/yyyy; lấy từ "Tử vong lúc"/"Đã chết vào lúc", không lấy giờ vào viện. '
             'Nếu công văn người chết lâu năm chỉ ghi rõ "chết năm yyyy" thì trả yyyy.'},
    {"name": "NguoiMat_GioMat", "desc": 'Giờ tử vong dạng "HH:mm"; ví dụ "06 giờ 38 phút" hoặc "giờ 6, phút 38" -> "06:38".'},
    {"name": "NguoiMat_NguyenNhanMat", "desc": "Nguyên nhân tử vong."},
    {"name": "NguoiMat_NoiChet",
     "desc": 'Nơi chết/nơi tử vong từ nhãn rõ ràng, object {quocGia,tinh,xa,diaChi}. Ưu tiên '
             "giấy báo tử/giấy tờ thay thế, rồi chứng cứ có thẩm quyền về nơi chết/nơi phát hiện thi thể, "
             "rồi tờ khai. Không dùng cơ quan cấp giấy báo tử làm nơi chết."},
    {"name": "Gbt_So",
     "desc": 'Số giấy báo tử/giấy tờ thay thế: CHỈ lấy từ chính GIẤY BÁO TỬ hoặc giá trị được ghi rõ '
             'sau nhãn "Số Giấy báo tử/Giấy tờ thay thế Giấy báo tử" trên TỜ KHAI ĐĂNG KÝ KHAI TỬ. '
             "Số Trích lục khai tử/TLKT/TLKT-BS tuyệt đối không phải Gbt_So."},
    {"name": "Gbt_CoQuanCap",
     "desc": "Cơ sở/cơ quan cấp giấy báo tử hoặc giấy tờ thay thế: CHỈ lấy từ chính GIẤY BÁO TỬ hoặc "
             "cơ quan được dẫn chiếu rõ tại đúng mục Giấy báo tử trên TỜ KHAI ĐĂNG KÝ KHAI TỬ. "
             "Không lấy cơ quan ban hành/ký Trích lục khai tử và không suy từ nơi chết."},
    {"name": "Gbt_NgayCap",
     "desc": "Ngày lập/cấp giấy báo tử hoặc giấy tờ thay thế, dd/mm/yyyy: CHỈ lấy từ chính GIẤY BÁO TỬ "
             "hoặc ngày cấp được dẫn chiếu rõ tại đúng mục Giấy báo tử trên TỜ KHAI ĐĂNG KÝ KHAI TỬ. "
             "Không lấy ngày lập/cấp/đăng ký của Trích lục khai tử và không nhầm ngày chết."},

    # Yêu cầu cấp bản sao trên chính tờ khai đăng ký khai tử, không đặt mặc định.
    {"name": "CopyRequest_WantsCopy",
     "desc": '"Có" chỉ khi TỜ KHAI ĐĂNG KÝ KHAI TỬ có dấu chọn thật tại Có; "Không" chỉ khi có '
             "dấu chọn thật tại Không. Các ký hiệu ô trống ☐/□ và riêng chữ in sẵn "
             '"Có, Không" KHÔNG phải dấu chọn. Nếu số lượng bản sao dương thì trả "Có". '
             "Cả hai ô trống/không rõ và số lượng trống thì BẮT BUỘC bỏ field."},
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
    "NguoiMat_NgaySinh",
    "NguoiMat_NgayCapGiayTo",
    "NguoiMat_NgayMat",
    "Gbt_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Cccd_NoiCuTru", "NguoiMat_NoiCuTruCuoiCung", "NguoiMat_NoiChet"):
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
