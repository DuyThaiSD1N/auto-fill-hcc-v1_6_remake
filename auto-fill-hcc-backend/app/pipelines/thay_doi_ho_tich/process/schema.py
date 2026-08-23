"""Compact schema cho "Thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc".

LLM chỉ trích SỰ KIỆN/DANH TÍNH nguồn từ giấy tờ hộ tịch (giấy khai sinh / trích lục
kết hôn / trích lục khai tử) và mọi CCCD đính kèm. CCCD người yêu cầu dùng để đối chiếu;
CCCD của chủ thể dùng để chuẩn hóa và bổ sung danh tính. Python suy ra field UI mục II + III
và default mục I.

Mục I (người yêu cầu) cổng tự điền từ VNeID — KHÔNG trích; chỉ đặt 3 default cư trú (viền vàng).
"""

# Sub-field danh tính dùng chung cho các nhóm người (ChuThe / Chong / Vo).
_PERSON_SUB = {
    "HoTen": "Họ và tên đầy đủ. Nếu có CCCD khớp người này thì BẮT BUỘC ưu tiên tên chuẩn trên CCCD, không giữ dấu gạch nối giữa các thành phần tên từ giấy hộ tịch cũ.",
    "NgaySinh": "Ngày sinh dd/mm/yyyy; nếu chỉ có năm thì trả yyyy. Ưu tiên CCCD khớp người này.",
    "GioiTinh": 'Giới tính: "Nam" hoặc "Nữ". Ưu tiên CCCD khớp người này.',
    "DanToc": "Chỉ trả dân tộc khi OCR ghi rõ cho đúng người này; không suy từ CCCD, họ tên, quê quán hay địa bàn.",
    "QuocTich": "Quốc tịch nếu giấy tờ có ghi. CCCD khớp người này đã được upload thì BẮT BUỘC trả quốc tịch trên CCCD.",
    "SoDinhDanh": "Số định danh cá nhân/CCCD nếu có. CCCD khớp người này đã được upload thì BẮT BUỘC trả.",
    "SoGiayTo": "Số giấy tờ tùy thân nếu khác số định danh.",
    "NgayCapGiayTo": "Ngày cấp giấy tờ tùy thân, dd/mm/yyyy. CCCD khớp người này đã được upload thì BẮT BUỘC trả.",
    "NoiCapGiayTo": "Nơi cấp/cơ quan cấp giấy tờ tùy thân. CCCD khớp người này đã được upload thì BẮT BUỘC trả.",
    "NoiCuTru": "Nơi cư trú, object {quocGia,tinh,xa,diaChi}. Nếu CCCD khớp người này đã được upload thì BẮT BUỘC lấy nơi thường trú trên CCCD, KHÔNG lấy địa chỉ cũ trên giấy hộ tịch.",
}


def _person_fields(prefix: str, who: str) -> list[dict]:
    fields = []
    for sub, desc in _PERSON_SUB.items():
        if prefix == "ChuThe" and sub == "NoiCuTru":
            desc = (
                "Nơi cư trú, object {quocGia,tinh,xa,diaChi}. Thứ tự ưu tiên: "
                "khối người được thay đổi trên TỜ KHAI cải chính > CCCD khớp chủ thể "
                "> giấy tờ hộ tịch gốc."
            )
        fields.append({"name": f"{prefix}_{sub}", "desc": f"{who}: {desc}"})
    return fields


FIELDS: list[dict] = [
    {
        "name": "DanhSachCccd",
        "desc": (
            "BẮT BUỘC trả một phần tử cho MỖI CCCD/CMND đã upload; không bỏ qua thẻ nào. "
            "Giá trị là array object [{HoTen,SoDinhDanh,NgaySinh,GioiTinh,QuocTich,"
            "NgayCap,NoiCap,NoiCuTru}]. Mỗi object chỉ chứa dữ liệu của đúng một thẻ; "
            "NoiCuTru={quocGia,tinh,xa,diaChi} lấy nơi thường trú trên thẻ."
        ),
    },
    
    # ==================================================================================
    # NGƯỜI YÊU CẦU — dữ kiện GHI TRÊN TỜ KHAI ĐĂNG KÝ
    # ==================================================================================
    # Ưu tiên lấy thông tin người yêu cầu từ TỜ KHAI thay vì từ CCCD hoặc VNeID.
    # Khi tờ khai có ghi thông tin này thì BẮT BUỘC trả, kể cả khi có CCCD của người đó.
    
    {"name": "NguoiYeuCau_HoTen",
     "desc": "Họ tên người yêu cầu ĐÚNG NHƯ TỜ KHAI ghi tại nhãn 'Họ, chữ đệm, tên người yêu cầu' "
             "hoặc 'Người đi khai'. Có tờ khai ghi giá trị này thì BẮT BUỘC trả, kể cả khi hồ sơ "
             "cũng có ảnh CCCD của chính người đó."},

    {"name": "NguoiYeuCau_NgaySinh",
     "desc": "Ngày sinh người yêu cầu ĐÚNG NHƯ TỜ KHAI ghi, dd/mm/yyyy; nếu chỉ có năm thì trả yyyy. "
             "Có tờ khai ghi giá trị này thì BẮT BUỘC trả."},

    {"name": "NguoiYeuCau_SoDinhDanh",
     "desc": "Số CCCD/CMND của người yêu cầu ĐÚNG NHƯ TỜ KHAI ghi tại nhãn 'Giấy tờ tùy thân' "
             "(dạng 'CCCD số ...'/'CMND số ...'). Có tờ khai ghi giá trị này thì BẮT BUỘC trả, "
             "kể cả khi số đó trùng với số trên ảnh CCCD."},

    {"name": "NguoiYeuCau_LoaiGiayTo",
     "desc": "Loại giấy tờ tùy thân người yêu cầu ĐÚNG NHƯ TỜ KHAI gọi tên tại nhãn 'Giấy tờ tùy thân', "
             "ví dụ tờ khai ghi 'CCCD số ...' thì trả 'Thẻ căn cước công dân', ghi 'CMND số ...' thì trả "
             "'Chứng minh nhân dân', ghi 'Căn cước số ...' thì trả 'Thẻ Căn cước', ghi hộ chiếu thì trả "
             "'Hộ chiếu'. Tờ khai không gọi tên loại giấy tờ thì bỏ field, không suy từ độ dài số."},

    {"name": "NguoiYeuCau_NgayCap",
     "desc": "Ngày cấp giấy tờ tùy thân của người yêu cầu ĐÚNG NHƯ TỜ KHAI ghi (thường nằm trong "
             "cụm 'Nơi cấp: ... cấp ngày dd/mm/yyyy' của khối người yêu cầu), dd/mm/yyyy."},

    {"name": "NguoiYeuCau_NoiCap",
     "desc": "Cơ quan cấp giấy tờ tùy thân của người yêu cầu ĐÚNG NHƯ TỜ KHAI ghi tại nhãn 'Nơi cấp' "
             "của khối người yêu cầu; chỉ trả tên cơ quan, bỏ chức danh như CỤC TRƯỞNG và bỏ phần "
             "'cấp ngày ...' đi kèm."},

    {"name": "NguoiYeuCau_NoiCuTru",
     "desc": "Nơi cư trú người yêu cầu ĐÚNG NHƯ TỜ KHAI ghi tại nhãn 'Nơi cư trú' hoặc 'Nơi thường trú', "
             "object {quocGia,tinh,xa,diaChi}. Giữ đúng địa danh của tờ khai, không thay bằng địa chỉ "
             "trên CCCD dù CCCD viết rõ hơn."},

    {"name": "NguoiYeuCau_QuanHe",
     "desc": "Quan hệ giữa NGƯỜI YÊU CẦU và NGƯỜI CÓ NỘI DUNG thay đổi/cải chính/bổ sung/xác định lại "
             "dân tộc, đọc Ô TÍCH ở dòng 'Quan hệ với người được thay đổi, cải chính, bổ sung thông tin "
             "hộ tịch, xác định lại dân tộc: Bản thân / Khác' trên TỜ KHAI. Trả ĐÚNG 'Bản thân' nếu ô "
             "Bản thân được tích, 'Khác' nếu ô Khác được tích. Không có tờ khai, hoặc có nhưng không xác "
             "định được ô nào được tích, thì BỎ field — không suy đoán."},

    # Các field CCCD người yêu cầu (dùng khi không có tờ khai hoặc làm dự phòng)
    {"name": "Cccd_HoTen", "desc": "Họ tên trên CCCD/CMND của NGƯỜI YÊU CẦU, lấy đúng tài liệu được identity_document_context xác định; không lấy CCCD người khác."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh/CCCD của NGƯỜI YÊU CẦU trên đúng tài liệu được identity_document_context xác định; có thể đọc từ MRZ."},
    {"name": "Cccd_NgayCap", "desc": "Ngày cấp trên đúng CCCD/CMND của NGƯỜI YÊU CẦU — dòng 'Ngày, tháng, năm / Date, month, year' MẶT SAU (có thể dính liền nhãn 'year'), dd/mm/yyyy."},
    {"name": "Cccd_NoiCap", "desc": "Nơi cấp trên đúng CCCD/CMND của NGƯỜI YÊU CẦU. 'CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI' → 'Cục Cảnh sát quản lý hành chính về trật tự xã hội'; 'BỘ CÔNG AN' → 'Bộ Công an'."},

    # Loại sự kiện hộ tịch của giấy tờ chính.
    {"name": "LoaiSuKien", "desc": 'Loại sự kiện của GIẤY TỜ HỘ TỊCH chính, không phải CCCD: "birth", "marriage" hoặc "death". Giấy cũ có chữ "hôn thú"/"tạm thay hôn thú" là "marriage".'},
    {"name": "TenGiayTo", "desc": "Tên giấy tờ hộ tịch đúng theo OCR (gồm cả tên lịch sử như Giấy chứng nhận tạm thay hôn thú); không lấy tên CCCD."},

    # Metadata hồ sơ gốc (mục 14).
    {"name": "HoSo_So", "desc": "Số đăng ký/số trích lục của giấy tờ hộ tịch."},
    {"name": "HoSo_QuyenSo", "desc": "Quyển số đăng ký hộ tịch nếu giấy tờ có ghi."},
    {"name": "HoSo_NgayDangKy", "desc": "Ngày đăng ký sự kiện hộ tịch, dd/mm/yyyy."},
    {"name": "HoSo_NoiDangKy", "desc": "Nơi đăng ký hồ sơ gốc (cơ quan đã đăng ký sự kiện hộ tịch)."},

    # Nội dung đề nghị (chỉ có trên TỜ KHAI cải chính/thay đổi hộ tịch).
    {"name": "NoiDungThayDoi", "desc": "Nội dung đề nghị thay đổi/cải chính/bổ sung (mục 'Nội dung: ...' trên tờ khai). Vd 'Cải chính tên từ X sang Y'."},
    {"name": "LyDo", "desc": "Lý do đề nghị thay đổi/cải chính (mục 'Lý do: ...' trên tờ khai)."},
    {"name": "ViecDangKy", "desc": "Loại việc đăng ký ở dòng 'Đề nghị cơ quan đăng ký việc <X>' trên tờ khai. Trả ĐÚNG một trong 5 giá trị: 'Cải chính' | 'Thay đổi' | 'Bổ sung hộ tịch' | 'Xác định lại dân tộc' | '' (rỗng nếu không rõ). KHÔNG lấy từ tiêu đề tờ khai (tiêu đề liệt kê cả 4)."},

    # Chủ thể (khai sinh = con; khai tử = người đã mất).
    *_person_fields("ChuThe", "Người được khai sinh (con) hoặc người đã mất, là chủ thể của giấy tờ"),
    # Hai bên trong trích lục kết hôn.
    *_person_fields("Chong", "Người chồng/bên nam trong giấy/trích lục kết hôn"),
    *_person_fields("Vo", "Người vợ/bên nữ trong giấy/trích lục kết hôn"),
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "NguoiYeuCau_NgaySinh",
    "NguoiYeuCau_NgayCap",
    "Cccd_NgayCap",
    "HoSo_NgayDangKy",
    "ChuThe_NgaySinh", "ChuThe_NgayCapGiayTo",
    "Chong_NgaySinh", "Chong_NgayCapGiayTo",
    "Vo_NgaySinh", "Vo_NgayCapGiayTo",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("NguoiYeuCau_NoiCuTru", "ChuThe_NoiCuTru", "Chong_NoiCuTru", "Vo_NoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Field UI thật trên form (tên = thuộc tính name của web-component x-* đã render).
UI_COMP_BY_NAME = {
    # Metadata để extension tự điền
    "__requesterInfo": "raw",  # Thông tin người yêu cầu từ tờ khai/CCCD để extension tự điền
    # Mục I — người yêu cầu.
    "HoVaTenC": "x-input",  # (1) Họ, chữ đệm, tên người yêu cầu
    "SoDinhDanhC": "x-input",  # (2) Số định danh cá nhân
    "LoaiGiayToTuyThanC": "x-select",  # (3) Giấy tờ tùy thân dropdown
    "SoGiayToTuyThanC": "x-input",  # (3) Số giấy tờ (có thể khác số định danh)
    "nycLoaiCuTru": "x-select",
    "nycNoiCuTru": "x-radio",
    "nycNoiCuTru_TrongNuoc": "x-select-area",
    # (5) Quan hệ với người được thay đổi/cải chính/bổ sung/xác định lại dân tộc: "Bản thân" | "Khác".
    "nycQuanHe": "x-radio",
    # Mục II — người có nội dung thay đổi.
    "ntdHoTen": "x-input",
    "ntdNgaySinh": "x-date-text",
    "ntdGioiTinh": "x-select",
    "ntdDanToc": "x-select",
    "ntdQuocTich": "x-select",
    "ntdSoDDCN": "x-input",
    "ntdLoaiGiayToTuyThan": "x-select",
    "ntdSoGiayToTuyThan": "x-input",
    "ntdNgayCapGiayToTuyThan": "x-date",
    "ntdNoiCapGiayToTuyThan": "x-input",
    "ntdLoaiCuTru": "x-select",
    "ntdNoiCuTru": "x-radio",
    "ntdNoiCuTru_TrongNuoc": "x-select-area",
    # Mục III — nội dung đề nghị.
    "viecDangKy": "x-select-default",  # Việc đăng ký: Thay đổi/Cải chính/Bổ sung hộ tịch/Xác định lại dân tộc
    "nghiepVuDK": "x-select-default",
    "soDangKyHSGoc": "x-input",
    "quyenDangKyHSGoc": "x-input",
    "ngayDangKyHSGoc": "x-date",
    "noiDangKyHSGoc": "x-input",
    # noiDungDK/lyDoDK là <input> TRẦN theo name (không bọc x-input) → comp "raw".
    "noiDungDK": "raw",
    "lyDoDK": "raw",
    "CapBanSao": "x-radio",
    # SoLuong: ô số lượng bản sao (input trần, hiện khi chọn "Có"). Tên xác nhận từ DOM thật.
    "SoLuong": "raw",
    "TraKQ": "x-radio",
}


# Field ĐÁNG rà soát bbox (name → nhãn). Đọc từ CCCD/giấy tờ của người được thay đổi + hồ sơ hộ tịch
# gốc + tờ khai. Người YÊU CẦU do cổng tự điền (VNeID) → không rà. Địa chỉ x-select-area tách
# tỉnh/xã/địa chỉ ở service. BỎ QUA: quốc tịch, loại cư trú, radio, việc/nghiệp vụ ĐK, mục mặc định.
REVIEW_FIELDS = {
    # Người được thay đổi/cải chính
    "ntdHoTen": "Họ tên người được thay đổi",
    "ntdNgaySinh": "Ngày sinh",
    "ntdGioiTinh": "Giới tính",
    "ntdDanToc": "Dân tộc",
    "ntdSoDDCN": "Số định danh",
    "ntdLoaiGiayToTuyThan": "Loại giấy tờ",
    "ntdSoGiayToTuyThan": "Số giấy tờ",
    "ntdNgayCapGiayToTuyThan": "Ngày cấp CCCD",
    "ntdNoiCapGiayToTuyThan": "Nơi cấp CCCD",
    "ntdNoiCuTru_TrongNuoc": "Nơi cư trú",
    # Hồ sơ hộ tịch gốc
    "soDangKyHSGoc": "Số đăng ký hồ sơ gốc",
    "quyenDangKyHSGoc": "Quyển số hồ sơ gốc",
    "ngayDangKyHSGoc": "Ngày đăng ký gốc",
    "noiDangKyHSGoc": "Nơi đăng ký gốc",
    # Nội dung thay đổi
    "noiDungDK": "Nội dung thay đổi/cải chính",
    "lyDoDK": "Lý do",
}
