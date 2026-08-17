"""Compact schema for "Xác nhận tình trạng hôn nhân".

The requester is always the subject ("Bản thân"). The LLM returns source facts
from the declaration/identity documents; UI defaults and duplicate
requester/subject fields are derived in Python.
"""

FIELDS: list[dict] = [
    {"name": "Cccd_HoTen", "desc": "Họ tên trên CCCD/CMND của cá nhân yêu cầu xác nhận."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh/CCCD/CMND; có thể đọc từ MRZ mặt sau."},
    {"name": "Cccd_NgaySinh", "desc": "Ngày sinh trên CCCD/CMND, dd/mm/yyyy."},
    {"name": "Cccd_GioiTinh", "desc": 'Giới tính trên CCCD/CMND: "Nam" hoặc "Nữ".'},
    {"name": "Cccd_DanToc", "desc": "Dân tộc của người yêu cầu. Ưu tiên đọc ở TỜ KHAI (dòng 'Dân tộc: ...'), sau đó tới CCCD/CMND. Thẻ CCCD mẫu mới thường không in dân tộc → PHẢI lấy từ tờ khai; BẮT BUỘC điền nếu giấy nào ghi."},
    {"name": "Cccd_QuocTich", "desc": "Quốc tịch trên CCCD/CMND nếu OCR ghi rõ hoặc khác Việt Nam."},
    {"name": "Cccd_NgayCap", "desc": "Ngày cấp CCCD/CMND, Thường ở mặt sau của CCCD, Ngày, tháng, năm / Date, month, year (mặt sau), hoặc ở tờ khai, dạng dd/mm/yyyy"},
    {"name": "Cccd_NoiCap",
     "desc": 'Nơi cấp CCCD/CMND từ mặt sau. Nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT..." '
             'thì trả "Cục Cảnh sát quản lý hành chính về trật tự xã hội", nếu là Bộ công an... thì trả "Bộ Công An".'},
    {"name": "ToKhai_NoiCuTru",
     "desc": 'Nơi cư trú hiện tại trên TỜ KHAI cấp giấy XNTTHN, object {quocGia,tinh,xa,diaChi}. '
             'Lấy đúng dòng "Nơi cư trú" của người yêu cầu/người được cấp; bắt buộc trả khi tờ khai có.'},
    {"name": "Cccd_NoiCuTru",
     "desc": 'Nơi thường trú/cư trú trên CCCD/CMND, object {quocGia,tinh,xa,diaChi}. Chỉ lấy từ thẻ '
             'CCCD/CMND; đây là nguồn dự phòng khi tờ khai không có nơi cư trú.'},
    {"name": "ToKhai_LaBanThan",
     "desc": 'Trả true CHỈ khi TỜ KHAI ghi quan hệ "Tự khai"/"Bản thân" và họ tên người yêu cầu '
             'trùng họ tên người được cấp giấy. Không suy luận từ một CCCD đơn lẻ.'},
    {"name": "TinhTrangHonNhanC1",
     "desc": 'Tình trạng hôn nhân'},
    {"name": "DivorceDecision_Number",
     "desc": "Số bản án/quyết định ly hôn, chỉ lấy từ tài liệu quyết định/bản án ly hôn thật."},
    {"name": "DivorceDecision_Date",
     "desc": "Ngày cấp/ban hành bản án/quyết định ly hôn, dd/mm/yyyy."},
    {"name": "DivorceDecision_Agency",
     "desc": "Cơ quan ban hành/cấp bản án/quyết định ly hôn."},
    {"name": "DeathCert_Number",
     "desc": "Số giấy chứng tử/trích lục khai tử/giấy báo tử của vợ/chồng đã chết, chỉ lấy từ giấy tờ khai tử thật."},
    {"name": "DeathCert_Date",
     "desc": "Ngày cấp giấy chứng tử/trích lục khai tử/giấy báo tử, dd/mm/yyyy."},
    {"name": "DeathCert_Agency",
     "desc": "Cơ quan cấp giấy chứng tử/trích lục khai tử/giấy báo tử (vd UBND phường...)."},
    {"name": "Marriage_SpouseName",
     "desc": 'Họ tên vợ/chồng hiện tại (người còn lại, KHÔNG phải người yêu cầu — đối chiếu CCCD: lấy '
             'tên người KHÁC với người yêu cầu). Ưu tiên Giấy chứng nhận/đăng ký kết hôn; nếu không có '
             'thì lấy từ dòng "hiện tại đang có chồng/vợ là..." trên TỜ KHAI.'},
    {"name": "Marriage_Number",
     "desc": "Số Giấy chứng nhận/đăng ký kết hôn, lấy từ giấy kết hôn hoặc dòng tình trạng hôn nhân trên "
             "TỜ KHAI nếu ghi rõ. Không lấy số CCCD/CMND của vợ/chồng."},
    {"name": "Marriage_Date",
     "desc": "Ngày đăng ký/cấp Giấy chứng nhận kết hôn, dd/mm/yyyy; lấy từ giấy kết hôn hoặc TỜ KHAI "
             "nếu ghi rõ. Không lấy ngày sinh/ngày cấp CCCD của vợ/chồng."},
    {"name": "Marriage_Agency",
     "desc": "Cơ quan đăng ký/cấp Giấy chứng nhận kết hôn, lấy từ giấy kết hôn hoặc TỜ KHAI nếu ghi rõ. "
             "Không lấy cơ quan cấp CCCD của vợ/chồng."},
    {"name": "Purpose",
     "desc": 'Mục đích sử dụng giấy XNTTHN.'},
    # --- Fields từ GIẤY ỦY QUYỀN (khi người yêu cầu nhờ người khác nộp thay) ---
    # Người ủy quyền (Section I của giấy ủy quyền) = người cần giấy XNTTHN → Mục II form.
    # Người được ủy quyền (Section II của giấy ủy quyền) = người đi nộp hồ sơ → Mục I form (thường có CCCD kèm).
    {"name": "PoA_SubjectName",
     "desc": "Họ tên người ủy quyền (ở Section I của GIẤY ỦY QUYỀN, tức người CẦN giấy XNTTHN). Chỉ lấy khi có giấy ủy quyền thật sự."},
    {"name": "PoA_SubjectDoB",
     "desc": "Ngày sinh của người ủy quyền (Section I giấy ủy quyền), dd/mm/yyyy."},
    {"name": "PoA_SubjectGender",
     "desc": 'Giới tính của người ủy quyền nếu ghị trong giấy ủy quyền hoặc CCCD của họ: "Nam" hoặc "Nữ".'},
    {"name": "PoA_SubjectIdNumber",
     "desc": "Số CCCD/CMND của người ủy quyền (Section I giấy ủy quyền)."},
    {"name": "PoA_SubjectIdDate",
     "desc": "Ngày cấp CCCD/CMND của người ủy quyền, dd/mm/yyyy."},
    {"name": "PoA_SubjectIssuer",
     "desc": "Nơi cấp CCCD/CMND của người ủy quyền (Section I giấy ủy quyền)."},
    {"name": "PoA_SubjectAddress",
     "desc": "Nơi cư trú của người ủy quyền (Section I giấy ủy quyền), object {tinh, xa, diaChi}."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Cccd_NgaySinh", "Cccd_NgayCap", "PoA_SubjectDoB", "PoA_SubjectIdDate"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
COMPACT_COMP_BY_NAME["DivorceDecision_Date"] = "x-date"
COMPACT_COMP_BY_NAME["DeathCert_Date"] = "x-date"
COMPACT_COMP_BY_NAME["Marriage_Date"] = "x-date"
COMPACT_COMP_BY_NAME["ToKhai_NoiCuTru"] = "x-select-area"
COMPACT_COMP_BY_NAME["Cccd_NoiCuTru"] = "x-select-area"
COMPACT_COMP_BY_NAME["PoA_SubjectAddress"] = "x-select-area"
COMPACT_COMP_BY_NAME["TinhTrangHonNhanC1"] = "x-select"

UI_COMP_BY_NAME = {
    # Section I: người yêu cầu cấp giấy.
    "HoVaTenC": "x-input",
    "NgaySinhC": "x-date",        # ngày sinh người yêu cầu (đang có trong form nhưng thiếu trong schema cũ)
    "SoDinhDanhC": "x-input",
    "SoGiayToTuyThanC": "raw",  # ô "Số:" cạnh dropdown Giấy tờ tùy thân (mục I) — form đặt name TenGiayToC
    "LoaiGiayToDinhDanhC": "x-select",
    "NgayCapDDC": "x-date",
    "NoiCapDDC": "x-input",
    "nycLoaiCuTru": "x-select",
    "nycNoiCuTru": "x-radio",
    "nycNoiCuTru_TrongNuoc": "x-select-area",
    # eForm trên cổng React mới (dichvucong.gov.vn) có thêm các ô này.
    "NgaySinhC": "x-date",
    "SoLuong": "x-input",
    "loaiDangKy": "x-radio",
    "quanhevoinguoiduocxacminh": "x-radio",
    # Section II: người được xác nhận tình trạng hôn nhân.
    "HoVaTenC1": "x-input",
    "NgaySinhC1": "x-date",
    "GioiTinhC1": "x-select",
    "DanTocC1": "x-select",
    "QuocTichC1": "x-select",
    "SoDinhDanhC1": "x-input",
    "SoGiayToTuyThanC1": "raw",
    "LoaiGiayToDinhDanhC1": "x-select",
    "NgayCapDDC1": "x-date",
    "NoiCapDDC1": "x-input",
    "nxnLoaiCuTru": "x-select",
    "nxnNoiCuTru": "x-radio",
    "nxnNoiCuTru_TrongNuoc": "x-select-area",
    "TinhTrangHonNhanC1": "x-select",
    "nxnLoaiTinhTrangHonNhan=2": "x-select-area",  # đang có vợ/chồng (có tên vợ/chồng + GCN kết hôn)
    # Input con của vùng động =2. Backend phát raw sau x-select-area để extension chỉ cần điền theo DOM name.
    "soGiayTo": "raw",
    "ngayCapGiayTo-day": "raw",
    "ngayCapGiayTo-month": "raw",
    "ngayCapGiayTo-year": "raw",
    "ngayCapGiayTo-name-date-input": "raw",
    "coQuanCapGiayTo": "raw",
    "nxnLoaiTinhTrangHonNhan=3": "x-select-area",  # đã ly hôn
    "nxnLoaiTinhTrangHonNhan=4": "x-select-area",  # góa (vợ/chồng đã chết)
    "nxnLoaiTinhTrangHonNhan=5": "x-select-area",  # option 5 (form có nhưng schema cũ thiếu)
    "nxnLoaiTinhTrangHonNhan=6": "x-select-area",  # option 6 (form có nhưng schema cũ thiếu)
    # Defaults.
    "mucdich": "x-select",
    "mucdichkhac": "x-select-area",    # x-select-area ào mục đích khác (khận với form thực)
    "nhapmucdichkhac": "raw",          # ô nhập mục đích free-text (input trần)
    "TraKQ": "x-radio",
}

UI_ALIASES = {
    "SoGiayToTuyThanC": ["TenGiayToC", "SoGiayToDinhDanhC"],
    "SoGiayToTuyThanC1": ["SoGiayToDinhDanhC1"],
    "nxnLoaiTinhTrangHonNhan=3": ["nxnLoaiTinhTrangHonNhan=2"],
    # eForm cổng mới đặt tên ô "mục đích khác" là mucdichkhac (bản cũ: nhapmucdichkhac).
    "nhapmucdichkhac": ["mucdichkhac"],
    # Một số bản form viết hoa chữ đầu.
    "loaiDangKy": ["LoaiDangKy"],
}

# Field ĐÁNG rà soát bbox (name → nhãn). Rà theo Section II (người được xác minh) — chứa TRỌN
# dữ liệu đọc từ CCCD, tránh trùng với Section I (người yêu cầu, thường cùng người). x-select-area
# (nơi cư trú) sẽ được tách tỉnh/xã/địa chỉ ở service. BỎ QUA: quốc tịch, loại cư trú, radio, mục đích.
REVIEW_FIELDS = {
    "HoVaTenC1": "Họ tên",
    "SoDinhDanhC1": "Số định danh",
    "LoaiGiayToDinhDanhC1": "Loại giấy tờ",
    "SoGiayToTuyThanC1": "Số giấy tờ",
    "NgaySinhC1": "Ngày sinh",
    "GioiTinhC1": "Giới tính",
    "DanTocC1": "Dân tộc",
    "NgayCapDDC1": "Ngày cấp CCCD",
    "NoiCapDDC1": "Nơi cấp CCCD",
    "nxnNoiCuTru_TrongNuoc": "Nơi cư trú",
}
