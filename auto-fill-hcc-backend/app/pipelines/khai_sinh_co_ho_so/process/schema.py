"""Compact role-fact schema cho "Đăng ký khai sinh cho người đã có hồ sơ, giấy tờ cá nhân" (1.004772).

Cùng họ biểu mẫu với đăng ký lại khai sinh (eForm "Tờ khai đăng ký khai sinh" của Bộ Tư pháp), nhưng
người được khai sinh CHƯA TỪNG được đăng ký khai sinh → KHÔNG có khối "đăng ký khai sinh trước đây".
Nguồn dữ liệu thay thế là HỒ SƠ, GIẤY TỜ CÁ NHÂN đã có: CCCD/CMND, thẻ BHYT, giấy tờ cư trú, học bạ,
bằng tốt nghiệp, chứng chỉ, giấy chứng nhận kết hôn, trích lục khai tử của cha/mẹ, giấy đề nghị xác
nhận của cơ quan quản lý.

LLM chỉ trả role-fact; Python (mapper.py) mới map sang field UI legacy + giá trị mặc định.
"""

FIELDS: list[dict] = [
    # Người yêu cầu — ƯU TIÊN TỜ KHAI. Trích khi TỜ KHAI ĐĂNG KÝ KHAI SINH có dòng
    # "Họ, chữ đệm, tên người yêu cầu" / "Người yêu cầu", KỂ CẢ khi người đó chính là con/cha/mẹ:
    # mapper cần biết để tick đúng ô "(5) Quan hệ với người được khai sinh" trước khi điền.
    # Không có tờ khai → BỎ TRỐNG toàn bộ Requester_* (mapper tự fallback sang CCCD của chính chủ).
    {"name": "Requester_SourceDocumentTitle",
     "desc": "Tiêu đề NGUYÊN VĂN của tài liệu đã dùng để điền Requester_*. CHỈ trả cùng Requester_* khi "
             "tiêu đề đó là TỜ KHAI ĐĂNG KÝ KHAI SINH; không trả cho CCCD, học bạ, bằng tốt nghiệp, "
             "giấy đề nghị xác nhận hay tờ khai cấp bản sao trích lục."},
    {"name": "Requester_RelationToSubject",
     "desc": 'Quan hệ của người yêu cầu với NGƯỜI ĐƯỢC ĐĂNG KÝ KHAI SINH, đọc từ dòng "Quan hệ với '
             'người được khai sinh" trên TỜ KHAI. BẮT BUỘC quy về ĐÚNG MỘT trong bốn giá trị: '
             '"Bản thân" (người yêu cầu tự đi làm cho chính mình — tờ khai ghi "Bản thân"/"Tự khai"/'
             '"Chính mình" hoặc họ tên người yêu cầu trùng người được khai sinh) | "Cha" | "Mẹ" | '
             '"Khác" (ông, bà, anh, chị, em, con, cháu, người được ủy quyền...). Không có tờ khai thì bỏ field.'},
    {"name": "Requester_FullName", "desc": "Họ tên người yêu cầu ghi trên TỜ KHAI đăng ký khai sinh (dòng 'Họ, chữ đệm, tên người yêu cầu')."},
    {"name": "Requester_IdNumber", "desc": "Số định danh/CCCD/CMND của người yêu cầu (từ tờ khai/CCCD của chính người yêu cầu), chỉ trả khi có."},
    {"name": "Requester_IdIssueDate", "desc": "Ngày cấp giấy tờ định danh người yêu cầu, dd/mm/yyyy."},
    {"name": "Requester_IdIssuePlace", "desc": "Nơi cấp giấy tờ định danh người yêu cầu."},
    {"name": "Requester_ResidenceDomestic", "desc": "Nơi cư trú người yêu cầu, object {quocGia,tinh,xa,diaChi}."},
    {"name": "Requester_Relationship",
     "desc": "Chữ NGUYÊN VĂN ghi ở dòng quan hệ trên tờ khai khi không quy được về 4 giá trị chuẩn "
             "(vd 'Con', 'Anh', 'Em', 'Chị', 'Cháu nội'...). Dùng kèm Requester_RelationToSubject=\"Khác\"."},

    # Người được đăng ký khai sinh — thường là NGƯỜI LỚN đã có CCCD/học bạ/bằng cấp.
    {"name": "Subject_FullName", "desc": "Họ tên đầy đủ của người được đăng ký khai sinh."},
    {"name": "Subject_BirthDate",
     "desc": "Ngày sinh người được đăng ký khai sinh, dd/mm/yyyy. Lấy từ CCCD/CMND CỦA CHÍNH NGƯỜI ĐÓ, "
             "hoặc từ tờ khai/học bạ/bằng tốt nghiệp/thẻ BHYT của chính người đó (KHÔNG lấy ngày sinh của "
             "cha/mẹ). Phải lấy đủ ngày/tháng/năm nếu phần số hoặc phần ghi bằng chữ có đủ; chỉ trả yyyy "
             "khi thật sự chỉ xác định được năm."},
    {"name": "Subject_BirthDateInWords",
     "desc": "Ngày sinh GHI BẰNG CHỮ của người được đăng ký khai sinh, chép NGUYÊN VĂN phần trong ngoặc "
             "sau ngày sinh trên TỜ KHAI (vd 'Mùng chín tháng mười một năm một nghìn chín trăm bảy mươi ba'). "
             "Chỉ trả khi tờ khai thật sự có ghi; KHÔNG tự chuyển số sang chữ."},
    {"name": "Subject_Gender", "desc": 'Giới tính người được đăng ký khai sinh: "Nam" hoặc "Nữ".'},
    {"name": "Subject_Ethnicity", "desc": "Dân tộc người được đăng ký khai sinh."},
    {"name": "Subject_Nationality", "desc": "Quốc tịch người được đăng ký khai sinh nếu giấy tờ ghi rõ."},
    {"name": "Subject_BirthPlaceDomestic",
     "desc": "Nơi sinh trong nước của người được đăng ký khai sinh, object {quocGia,tinh,xa,diaChi}. "
             "Ưu tiên NƠI SINH ghi trên TỜ KHAI; nếu tờ khai không ghi thì lấy nơi sinh trên hồ sơ, giấy tờ "
             "cá nhân (học bạ, hồ sơ học tập, giấy đề nghị xác nhận); vẫn không có thì lấy theo NƠI THƯỜNG TRÚ "
             "trên CCCD của chính người đó. KHÔNG dùng quê quán làm nơi sinh."},
    {"name": "Subject_HometownDomestic",
     "desc": "Quê quán trong nước của người được đăng ký khai sinh, object {quocGia,tinh,xa,diaChi}. "
             "Lấy từ QUÊ QUÁN trên tờ khai/CCCD/hồ sơ cá nhân; KHÔNG dùng nơi sinh/nơi cư trú làm quê quán."},
    # Nhân thân trên CCCD/CMND CỦA CHÍNH người được khai sinh — nguồn fallback để điền khối
    # "Thông tin người yêu cầu" khi hồ sơ KHÔNG có tờ khai (chính chủ tự đi đăng ký cho mình).
    {"name": "Subject_IdNumber",
     "desc": "Số định danh/CCCD/CMND CỦA CHÍNH người được đăng ký khai sinh. CHỈ trả khi hồ sơ có "
             "CCCD/CMND của chính người đó; KHÔNG lấy số của cha/mẹ, KHÔNG lấy số trên thẻ BHYT của người khác."},
    {"name": "Subject_IdIssueDate", "desc": "Ngày cấp CCCD/CMND của chính người được đăng ký khai sinh, dd/mm/yyyy."},
    {"name": "Subject_IdIssuePlace",
     "desc": "Nơi cấp CCCD/CMND của chính người được đăng ký khai sinh — lấy từ mặt sau CCCD; RIÊNG "
             "Giấy CMND (~9 số) lấy 'Công an tỉnh/thành phố ...' ghi cùng dòng số CMND."},
    {"name": "Subject_ResidenceDomestic",
     "desc": 'Nơi cư trú/thường trú của chính người được đăng ký khai sinh, object {quocGia,tinh,xa,diaChi}. '
             'Ưu tiên "Nơi thường trú" trên CCCD CỦA CHÍNH NGƯỜI ĐÓ; KHÔNG lấy nơi cư trú của cha/mẹ.'},

    # Cha của người được đăng ký khai sinh — rất hay ĐÃ MẤT và không có CCCD.
    {"name": "Father_FullName", "desc": "Họ tên cha của người được đăng ký khai sinh. Ưu tiên lấy từ CCCD của cha; nếu cha đã mất và không có CCCD thì lấy từ TỜ KHAI, GIẤY ĐỀ NGHỊ XÁC NHẬN hoặc TRÍCH LỤC KHAI TỬ (dòng 'Họ tên người chết')."},
    {"name": "Father_IdNumber",
     "desc": "Số định danh/CCCD/CMND của cha, ƯU TIÊN lấy từ CCCD/CMND CỦA CHÍNH CHA. "
             "KHÔNG lấy số định danh của người được khai sinh (trên CCCD/BHYT/học bạ) làm số của cha."},
    {"name": "Father_Gender",
     "desc": 'Giới tính GHI TRÊN giấy tờ đã dùng để điền Father_* ("Nam" hoặc "Nữ"). BẮT BUỘC trả khi có '
             'trả bất kỳ field Father_* nào lấy từ CCCD/CMND. Thẻ ghi "Nữ" nghĩa là thẻ đó KHÔNG phải của cha.'},
    {"name": "Father_IdIssueDate", "desc": "Ngày cấp giấy tờ định danh của cha, dd/mm/yyyy — LẤY TỪ CCCD của cha nếu có."},
    {"name": "Father_IdIssuePlace", "desc": "Nơi cấp giấy tờ định danh của cha — lấy từ mặt sau CCCD; RIÊNG Giấy CMND (~9 số) lấy 'Công an tỉnh/thành phố ...' ghi cùng dòng số CMND (KHÔNG suy 'Cục Cảnh sát...'/'Bộ Công an')."},
    {"name": "Father_BirthDateOrYear",
     "desc": "Ngày sinh cha. Nếu cha có CCCD thì lấy NGÀY đầy đủ dd/mm/yyyy từ CCCD; "
             "chỉ trả năm (yyyy) khi cha KHÔNG có CCCD và tài liệu chỉ ghi năm (tờ khai thủ tục này "
             "thường chỉ ghi NĂM SINH của cha/mẹ). Nếu cha đã mất, lấy năm sinh từ TRÍCH LỤC KHAI TỬ "
             "của cha (dòng 'Ngày, tháng, năm sinh')."},
    {"name": "Father_Ethnicity",
     "desc": "Dân tộc cha nếu tài liệu ghi rõ (tờ khai, giấy đề nghị xác nhận); nếu cha đã mất thì lấy từ "
             "dòng 'Dân tộc' trên TRÍCH LỤC KHAI TỬ của cha."},
    {"name": "Father_Nationality",
     "desc": "Quốc tịch cha nếu tài liệu ghi rõ; nếu cha đã mất thì lấy từ dòng 'Quốc tịch' trên TRÍCH LỤC KHAI TỬ của cha."},
    {"name": "Father_ResidenceDomestic",
     "desc": 'Nơi cư trú trong nước của cha, object {quocGia,tinh,xa,diaChi}. Ưu tiên "Nơi thường trú" '
             'trên CCCD của cha nếu có; không có CCCD thì lấy nơi cư trú ghi trên TỜ KHAI/GIẤY ĐỀ NGHỊ XÁC NHẬN. '
             'Nếu tài liệu ghi cha đã chết/mất hoặc OCR nhiễu như "Da Chet", "D.d. Chat", "L.D.d. Chat" thì '
             'trả {"quocGia":"","tinh":"","xa":"","diaChi":"Đã chết"}.'},
    {"name": "Father_HometownFromDeathCert",
     "desc": 'Nơi cư trú/thường trú cuối cùng của cha lấy từ TRÍCH LỤC KHAI TỬ hoặc GIẤY CHỨNG TỬ khi cha đã mất '
             'và không có CCCD trong hồ sơ, object {quocGia,tinh,xa,diaChi}. '
             'Ưu tiên dòng "Nơi thường trú" hoặc "Nơi cư trú" trên trích lục khai tử; '
             'nếu không có nơi cư trú thì lấy dòng "Quê quán". '
             'Chỉ trả khi cha đã mất VÀ có trích lục khai tử trong hồ sơ.'},

    # Mẹ của người được đăng ký khai sinh.
    {"name": "Mother_FullName", "desc": "Họ tên mẹ của người được đăng ký khai sinh. Ưu tiên lấy từ CCCD của mẹ; nếu mẹ đã mất và không có CCCD thì lấy từ TỜ KHAI, GIẤY CHỨNG NHẬN KẾT HÔN hoặc TRÍCH LỤC KHAI TỬ (dòng 'Họ tên người chết')."},
    {"name": "Mother_IdNumber",
     "desc": "Số định danh/CCCD/CMND của mẹ, ƯU TIÊN lấy từ CCCD/CMND CỦA CHÍNH MẸ. "
             "KHÔNG lấy số định danh của người được khai sinh làm số của mẹ."},
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
     "desc": "Dân tộc mẹ nếu tài liệu ghi rõ (tờ khai, giấy đề nghị xác nhận); nếu mẹ đã mất thì lấy từ "
             "dòng 'Dân tộc' trên TRÍCH LỤC KHAI TỬ của mẹ."},
    {"name": "Mother_Nationality",
     "desc": "Quốc tịch mẹ nếu tài liệu ghi rõ; nếu mẹ đã mất thì lấy từ dòng 'Quốc tịch' trên TRÍCH LỤC KHAI TỬ của mẹ."},
    {"name": "Mother_ResidenceDomestic",
     "desc": 'Nơi cư trú trong nước của mẹ, object {quocGia,tinh,xa,diaChi}. Ưu tiên "Nơi thường trú" '
             'trên CCCD của mẹ nếu có; không có CCCD thì lấy nơi cư trú ghi trên TỜ KHAI. '
             'Nếu tài liệu ghi mẹ đã chết/mất hoặc OCR nhiễu như "Da Chet", "D.d. Chat", "L.D.d. Chat" thì '
             'trả {"quocGia":"","tinh":"","xa":"","diaChi":"Đã chết"}.'},
    {"name": "Mother_HometownFromDeathCert",
     "desc": 'Nơi cư trú/thường trú cuối cùng của mẹ lấy từ TRÍCH LỤC KHAI TỬ hoặc GIẤY CHỨNG TỬ khi mẹ đã mất '
             'và không có CCCD trong hồ sơ, object {quocGia,tinh,xa,diaChi}. '
             'Ưu tiên dòng "Nơi thường trú" hoặc "Nơi cư trú" trên trích lục khai tử; '
             'nếu không có nơi cư trú thì lấy dòng "Quê quán". '
             'Chỉ trả khi mẹ đã mất VÀ có trích lục khai tử trong hồ sơ.'},

    # Đề nghị cấp bản sao — chỉ từ lựa chọn/số lượng ghi thật trên tờ khai, không mặc định.
    {"name": "CopyRequest_SourceDocumentTitle",
     "desc": "Tiêu đề NGUYÊN VĂN của tài liệu chứa yêu cầu cấp bản sao. CHỈ trả cùng CopyRequest_* khi tiêu đề "
             "tài liệu là TỜ KHAI ĐĂNG KÝ KHAI SINH; không trả cho TỜ KHAI CẤP BẢN SAO TRÍCH LỤC HỘ TỊCH "
             "hoặc mẫu yêu cầu cấp trích lục khác."},
    {"name": "CopyRequest_WantsCopy",
     "desc": '"Có" nếu TỜ KHAI ĐĂNG KÝ KHAI SINH tích/chọn đề nghị cấp bản sao; "Không" nếu chính tờ khai '
             "đó tích/chọn không cấp bản sao. Không lấy từ tờ khai cấp bản sao trích lục; không thấy lựa chọn "
             "rõ thì bỏ field."},
    {"name": "CopyRequest_Quantity",
     "desc": "Số lượng bản sao đề nghị cấp, chỉ trả số nguyên dương khi TỜ KHAI ĐĂNG KÝ KHAI SINH ghi rõ. "
             "Không lấy số lượng trên tờ khai cấp bản sao trích lục; không tự mặc định là 1."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Requester_IdIssueDate",
    "Subject_BirthDate",
    "Subject_IdIssueDate",
    "Father_IdIssueDate",
    "Mother_IdIssueDate",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in (
    "Requester_ResidenceDomestic",
    "Subject_BirthPlaceDomestic",
    "Subject_ResidenceDomestic",
    "Subject_HometownDomestic",
    "Father_ResidenceDomestic",
    "Father_HometownFromDeathCert",
    "Mother_ResidenceDomestic",
    "Mother_HometownFromDeathCert",
):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"


# Field ĐÁNG rà soát bbox (name → nhãn). Đọc từ hồ sơ/giấy tờ cá nhân + CCCD cha/mẹ. Tên gộp
# (HoTenKS/HoTenChaKS/HoTenMeKS). Địa chỉ x-select-area tách tỉnh/xã/địa chỉ ở service.
# BỎ QUA: quốc tịch, loại cư trú, radio nơi sinh/quê quán và mục cấp bản sao.
REVIEW_FIELDS = {
    # Người được đăng ký khai sinh
    "HoTenKS": "Họ tên người được khai sinh",
    "NgaySinhChon": "Ngày sinh",
    "GioiTinhKS": "Giới tính",
    "DanTocKS": "Dân tộc",
    "nksNoiSinh_TrongNuoc": "Nơi sinh",
    "nksQueQuan_TrongNuoc": "Quê quán",
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
}
