"""Compact role-fact schema for "Đăng ký lại khai sinh".

The LLM returns one stable intermediate contract for every document mix. It
extracts role facts; Python maps those facts to legacy UI fields and defaults.
"""

FIELDS: list[dict] = [
    # Người yêu cầu — CHỈ trích khi tờ khai/đơn ghi rõ thông tin người yêu cầu KHÁC với cha/mẹ,
    # hoặc khi tờ khai có dòng "Người yêu cầu" / "Họ tên người yêu cầu" với nội dung đầy đủ.
    # Nếu người yêu cầu chính là cha hoặc mẹ thì KHÔNG trả Requester_* (đã có Father_*/Mother_*).
    {"name": "Requester_FullName", "desc": "Họ tên người yêu cầu đăng ký lại khai sinh (từ tờ khai/đơn), chỉ trả khi tờ khai ghi rõ và khác với cha/mẹ."},
    {"name": "Requester_IdNumber", "desc": "Số định danh/CCCD/CMND của người yêu cầu (từ tờ khai/CCCD), chỉ trả khi có."},
    {"name": "Requester_IdIssueDate", "desc": "Ngày cấp giấy tờ định danh người yêu cầu, dd/mm/yyyy."},
    {"name": "Requester_IdIssuePlace", "desc": "Nơi cấp giấy tờ định danh người yêu cầu."},
    {"name": "Requester_ResidenceDomestic", "desc": "Nơi cư trú người yêu cầu, object {quocGia,tinh,xa,diaChi}."},
    {"name": "Requester_Relationship", "desc": "Quan hệ người yêu cầu với người được đăng ký lại khai sinh (vd 'Con', 'Anh', 'Em', 'Chị'...)."},

    # Người được đăng ký lại khai sinh.
    {"name": "Subject_FullName", "desc": "Họ tên đầy đủ của người được đăng ký lại khai sinh."},
    {"name": "Subject_BirthDate",
     "desc": "Ngày sinh người được đăng ký lại khai sinh, dd/mm/yyyy. Lấy từ giấy khai sinh cũ; nếu con có "
             "CCCD riêng thì lấy từ CCCD CỦA CON (KHÔNG lấy ngày sinh của cha/mẹ). Phải lấy đủ ngày/tháng/năm "
             "nếu phần số hoặc phần ghi bằng chữ có đủ; chỉ trả yyyy khi thật sự chỉ xác định được năm."},
    {"name": "Subject_Gender", "desc": 'Giới tính người được đăng ký lại khai sinh: "Nam" hoặc "Nữ".'},
    {"name": "Subject_Ethnicity", "desc": "Dân tộc người được đăng ký lại khai sinh."},
    {"name": "Subject_Nationality", "desc": "Quốc tịch người được đăng ký lại khai sinh nếu giấy tờ ghi rõ."},
    {"name": "Subject_BirthPlaceDomestic",
     "desc": "Nơi sinh trong nước của người được đăng ký lại khai sinh, object {quocGia,tinh,xa,diaChi}. "
             "Ưu tiên NƠI SINH ghi trên giấy khai sinh cũ/trích lục; nếu KHÔNG có nơi sinh thì lấy theo "
             "NƠI THƯỜNG TRÚ trên CCCD của chính người đó. KHÔNG dùng quê quán làm nơi sinh."},
    {"name": "Subject_HometownDomestic",
     "desc": "Quê quán trong nước của người được đăng ký lại khai sinh, object {quocGia,tinh,xa,diaChi}. "
             "Lấy từ QUÊ QUÁN trên giấy tờ (CCCD/giấy khai sinh); KHÔNG dùng nơi sinh/nơi cư trú làm quê quán."},

    # Cha của người được đăng ký lại khai sinh.
    {"name": "Father_FullName", "desc": "Họ tên cha của người được đăng ký lại khai sinh. Ưu tiên lấy từ CCCD của cha; nếu cha đã mất và không có CCCD thì lấy từ TRÍCH LỤC KHAI TỬ (dòng 'Họ tên người chết')."},
    {"name": "Father_IdNumber",
     "desc": "Số định danh/CCCD/CMND của cha, ƯU TIÊN lấy từ CCCD/CMND CỦA CHÍNH CHA. "
             "KHÔNG lấy số định danh của con trên giấy khai sinh làm số của cha."},
    {"name": "Father_Gender",
     "desc": 'Giới tính GHI TRÊN giấy tờ đã dùng để điền Father_* ("Nam" hoặc "Nữ"). BẮT BUỘC trả khi có '
             'trả bất kỳ field Father_* nào lấy từ CCCD/CMND. Thẻ ghi "Nữ" nghĩa là thẻ đó KHÔNG phải của cha.'},
    {"name": "Father_IdIssueDate", "desc": "Ngày cấp giấy tờ định danh của cha, dd/mm/yyyy — LẤY TỪ CCCD của cha nếu có."},
    {"name": "Father_IdIssuePlace", "desc": "Nơi cấp giấy tờ định danh của cha — lấy từ mặt sau CCCD; RIÊNG Giấy CMND (~9 số) lấy 'Công an tỉnh/thành phố ...' ghi cùng dòng số CMND (KHÔNG suy 'Cục Cảnh sát...'/'Bộ Công an')."},
    {"name": "Father_BirthDateOrYear",
     "desc": "Ngày sinh cha. Nếu cha có CCCD thì lấy NGÀY đầy đủ dd/mm/yyyy từ CCCD; "
             "chỉ trả năm (yyyy) khi cha KHÔNG có CCCD và tài liệu chỉ ghi năm. "
             "Nếu cha đã mất, lấy năm sinh từ TRÍCH LỤC KHAI TỬ của cha (dòng 'Ngày, tháng, năm sinh')."},
    {"name": "Father_Ethnicity",
     "desc": "Dân tộc cha nếu tài liệu ghi rõ; nếu cha đã mất thì lấy từ dòng 'Dân tộc' trên TRÍCH LỤC KHAI TỬ của cha."},
    {"name": "Father_Nationality",
     "desc": "Quốc tịch cha nếu tài liệu ghi rõ; nếu cha đã mất thì lấy từ dòng 'Quốc tịch' trên TRÍCH LỤC KHAI TỬ của cha."},
    {"name": "Father_ResidenceDomestic",
     "desc": 'Nơi cư trú trong nước của cha, object {quocGia,tinh,xa,diaChi}. Ưu tiên "Nơi thường trú" '
             'trên CCCD của cha nếu có (KHÔNG lấy nơi cư trú trên giấy khai sinh). '
             'Nếu tài liệu ghi cha đã chết/mất hoặc OCR nhiễu như "Da Chet", "D.d. Chat", "L.D.d. Chat" thì '
             'trả {"quocGia":"","tinh":"","xa":"","diaChi":"Đã chết"}.'},
    {"name": "Father_HometownFromDeathCert",
     "desc": 'Nơi cư trú/thường trú cuối cùng của cha lấy từ TRÍCH LỤC KHAI TỬ hoặc GIẤY CHỨNG TỬ khi cha đã mất '
             'và không có CCCD trong hồ sơ, object {quocGia,tinh,xa,diaChi}. '
             'Ưu tiên dòng "Nơi thường trú" hoặc "Nơi cư trú" trên trích lục khai tử; '
             'nếu không có nơi cư trú thì lấy dòng "Quê quán". '
             'Chỉ trả khi cha đã mất VÀ có trích lục khai tử trong hồ sơ.'},

    # Mẹ của người được đăng ký lại khai sinh.
    {"name": "Mother_FullName", "desc": "Họ tên mẹ của người được đăng ký lại khai sinh. Ưu tiên lấy từ CCCD của mẹ; nếu mẹ đã mất và không có CCCD thì lấy từ TRÍCH LỤC KHAI TỬ (dòng 'Họ tên người chết')."},
    {"name": "Mother_IdNumber",
     "desc": "Số định danh/CCCD/CMND của mẹ, ƯU TIÊN lấy từ CCCD/CMND CỦA CHÍNH MẸ THAY VÌ TỪ GIẤY KHAI SINH CỦA CON. "
             "KHÔNG lấy số định danh của con trên giấy khai sinh làm số của mẹ."},
    {"name": "Mother_Gender",
     "desc": 'Giới tính GHI TRÊN giấy tờ đã dùng để điền Mother_* ("Nam" hoặc "Nữ"). BẮT BUỘC trả khi có '
             'trả bất kỳ field Mother_* nào lấy từ CCCD/CMND. Thẻ ghi "Nam" nghĩa là thẻ đó KHÔNG phải của mẹ.'},
    {"name": "Mother_IdIssueDate", "desc": "Ngày cấp giấy tờ định danh của mẹ, dd/mm/yyyy — LẤY TỪ CCCD của mẹ nếu có."},
    {"name": "Mother_IdIssuePlace", "desc": "Nơi cấp giấy tờ định danh của mẹ — lấy từ mặt sau CCCD; RIÊNG Giấy CMND (~9 số) lấy 'Công an tỉnh/thành phố ...' ghi cùng dòng số CMND (KHÔNG suy 'Cục Cảnh sát...'/'Bộ Công an')."},
    {"name": "Mother_BirthDateOrYear",
     "desc": "Ngày sinh mẹ. Nếu mẹ có CCCD thì lấy NGÀY đầy đủ dd/mm/yyyy từ CCCD; "
             "chỉ trả năm (yyyy) khi mẹ KHÔNG có CCCD và tài liệu chỉ ghi năm. "
             "Nếu mẹ đã mất, lấy năm sinh từ TRÍCH LỤC KHAI TỬ của mẹ (dòng 'Ngày, tháng, năm sinh')."},
    {"name": "Mother_Ethnicity",
     "desc": "Dân tộc mẹ nếu tài liệu ghi rõ; nếu mẹ đã mất thì lấy từ dòng 'Dân tộc' trên TRÍCH LỤC KHAI TỬ của mẹ."},
    {"name": "Mother_Nationality",
     "desc": "Quốc tịch mẹ nếu tài liệu ghi rõ; nếu mẹ đã mất thì lấy từ dòng 'Quốc tịch' trên TRÍCH LỤC KHAI TỬ của mẹ."},
    {"name": "Mother_ResidenceDomestic",
     "desc": 'Nơi cư trú trong nước của mẹ, object {quocGia,tinh,xa,diaChi}. Ưu tiên "Nơi thường trú" '
             'trên CCCD của mẹ nếu có (KHÔNG lấy nơi cư trú trên giấy khai sinh). '
             'Nếu tài liệu ghi mẹ đã chết/mất hoặc OCR nhiễu như "Da Chet", "D.d. Chat", "L.D.d. Chat" thì '
             'trả {"quocGia":"","tinh":"","xa":"","diaChi":"Đã chết"}.'},
    {"name": "Mother_HometownFromDeathCert",
     "desc": 'Nơi cư trú/thường trú cuối cùng của mẹ lấy từ TRÍCH LỤC KHAI TỬ hoặc GIẤY CHỨNG TỬ khi mẹ đã mất '
             'và không có CCCD trong hồ sơ, object {quocGia,tinh,xa,diaChi}. '
             'Ưu tiên dòng "Nơi thường trú" hoặc "Nơi cư trú" trên trích lục khai tử; '
             'nếu không có nơi cư trú thì lấy dòng "Quê quán". '
             'Chỉ trả khi mẹ đã mất VÀ có trích lục khai tử trong hồ sơ.'},

    # Thông tin đăng ký khai sinh trước đây.
    # PreviousRegistration_* CHỈ từ tài liệu GHI NHẬN VIỆC KHAI SINH của Subject (giấy khai sinh cũ /
    # bản sao / trích lục khai sinh / tờ khai đăng ký lại). KHÔNG lấy từ GIẤY CHỨNG NHẬN KẾT HÔN (dù có
    # "Số:"/"Quyển số:" ở đầu — đó là số đăng ký kết hôn), trích lục khai tử (đuôi "TLKT") hay CCCD.
    # Không có giấy khai sinh cũ/tờ khai đăng ký lại → BỎ TRỐNG toàn bộ.
    {"name": "PreviousRegistration_AgencyProvince",
     "desc": "Tỉnh/thành phố của cơ quan ĐĂNG KÝ KHAI SINH trước đây, CHỈ từ giấy khai sinh cũ/trích lục "
             "khai sinh/tờ khai đăng ký lại. KHÔNG lấy tỉnh trên giấy kết hôn/khai tử/CCCD. Ví dụ Lai Châu."},
    {"name": "PreviousRegistration_Number",
     "desc": 'Số ĐĂNG KÝ KHAI SINH trước đây — CHỈ từ GIẤY KHAI SINH CŨ/TRÍCH LỤC KHAI SINH/TỜ KHAI đăng ký lại '
             'Không có giấy khai sinh cũ/tờ khai đăng ký lại thì bỏ trống. KHÔNG lấy số thứ tự mục "(7)", "(10)".'},
    {"name": "PreviousRegistration_BookNumber",
     "desc": "Quyển số đăng ký khai sinh trước đây — CHỈ trả khi giấy khai sinh cũ/trích lục/tờ khai đăng ký lại "
             "ghi rõ nhãn 'Quyển số'. Không tự tính hoặc suy ra từ số đăng ký/ngày đăng ký."},
    {"name": "PreviousRegistration_Date",
     "desc": "Ngày ĐĂNG KÝ KHAI SINH trước đây, dd/mm/yyyy — CHỈ từ giấy khai sinh cũ/trích lục/tờ khai. "
             "Không có giấy khai sinh cũ/tờ khai đăng ký lại thì bỏ trống."},

    # Đề nghị cấp bản sao — chỉ từ lựa chọn/số lượng ghi thật trên tờ khai, không mặc định.
    {"name": "CopyRequest_SourceDocumentTitle",
     "desc": "Tiêu đề NGUYÊN VĂN của tài liệu chứa yêu cầu cấp bản sao. CHỈ trả cùng CopyRequest_* khi tiêu đề "
             "tài liệu là TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH; không trả cho TỜ KHAI CẤP BẢN SAO TRÍCH LỤC HỘ TỊCH "
             "hoặc mẫu yêu cầu cấp trích lục khác."},
    {"name": "CopyRequest_WantsCopy",
     "desc": '"Có" nếu TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH tích/chọn đề nghị cấp bản sao; "Không" nếu chính tờ khai '
             "đó tích/chọn không cấp bản sao. Không lấy từ tờ khai cấp bản sao trích lục; không thấy lựa chọn "
             "rõ thì bỏ field."},
    {"name": "CopyRequest_Quantity",
     "desc": "Số lượng bản sao đề nghị cấp, chỉ trả số nguyên dương khi TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH ghi rõ. "
             "Không lấy số lượng trên tờ khai cấp bản sao trích lục; không tự mặc định là 1."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Requester_IdIssueDate",
    "Subject_BirthDate",
    "Father_IdIssueDate",
    "Mother_IdIssueDate",
    "PreviousRegistration_Date",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in (
    "Requester_ResidenceDomestic",
    "Subject_BirthPlaceDomestic",
    "Subject_HometownDomestic",
    "Father_ResidenceDomestic",
    "Father_HometownFromDeathCert",
    "Mother_ResidenceDomestic",
    "Mother_HometownFromDeathCert",
):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"


# Field ĐÁNG rà soát bbox (name → nhãn). Đọc từ giấy khai sinh cũ/trích lục + CCCD cha/mẹ. Tên
# gộp (HoTenKS/HoTenChaKS/HoTenMeKS). Địa chỉ x-select-area tách tỉnh/xã/địa chỉ ở service.
# BỎ QUA: quốc tịch, loại cư trú, radio nơi sinh/quê quán và mục cấp bản sao.
REVIEW_FIELDS = {
    # Con (người được đăng ký lại khai sinh)
    "HoTenKS": "Họ tên con",
    "NgaySinhChon": "Ngày sinh con",
    "GioiTinhKS": "Giới tính con",
    "DanTocKS": "Dân tộc con",
    "nksNoiSinh_TrongNuoc": "Nơi sinh con",
    "nksQueQuan_TrongNuoc": "Quê quán con",
    # Mẹ
    "HoTenMeKS": "Họ tên mẹ",
    "SoDinhDanhMe": "Số định danh mẹ",
    "LoaiGiayToDinhDanhMe": "Loại giấy tờ mẹ",
    "NgayCapDDMe": "Ngày cấp CCCD mẹ",
    "NoiCapDDMe": "Nơi cấp CCCD mẹ",
    "NamSinhMeKS": "Ngày sinh mẹ",
    "DanTocMeKS": "Dân tộc mẹ",
    "MeNoiCuTru_TrongNuoc": "Nơi cư trú mẹ",
    # Cha
    "HoTenChaKS": "Họ tên cha",
    "SoDinhDanhCha": "Số định danh cha",
    "LoaiGiayToDinhDanhCha": "Loại giấy tờ cha",
    "NgayCapDDCha": "Ngày cấp CCCD cha",
    "NoiCapDDCha": "Nơi cấp CCCD cha",
    "NamSinhChaKS": "Ngày sinh cha",
    "DanTocChaKS": "Dân tộc cha",
    "ChaNoiCuTru_TrongNuoc": "Nơi cư trú cha",
    # Đăng ký trước đây (giấy khai sinh cũ)
    "soDKTruocDay": "Số đăng ký trước đây",
    "ngayDKTruocDay": "Ngày đăng ký trước đây",
}
