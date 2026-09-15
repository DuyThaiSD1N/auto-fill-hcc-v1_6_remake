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
    # --- Fields từ TỜ KHAI (thông tin NGƯỜI YÊU CẦU - Section I, ghi ở ĐẦU tờ khai) ---
    # Tờ khai luôn có HAI khối riêng: "Họ, chữ đệm, tên người yêu cầu" (đầu tờ khai) và "Đề nghị cấp
    # Giấy xác nhận... cho người có tên dưới đây" (Section II, → ToKhai_*). Hai khối này CÓ THỂ khác
    # người (thân nhân đứng nộp hộ mà không kèm giấy ủy quyền chính thức) — PHẢI tách riêng, không
    # gộp vào ToKhai_* của Section II.
    {"name": "ToKhaiYeuCau_HoTen",
     "desc": 'Họ tên NGƯỜI YÊU CẦU, lấy từ dòng "Họ, chữ đệm, tên người yêu cầu:" ở ĐẦU tờ khai. '
             'Đây là người ĐI NỘP đơn, CÓ THỂ KHÁC người được cấp giấy ở Section II — không tự suy '
             'đoán trùng nhau, lấy đúng tên ghi ở dòng này.'},
    {"name": "ToKhaiYeuCau_NgaySinh",
     "desc": 'Ngày sinh NGƯỜI YÊU CẦU, lấy từ dòng "Ngày, tháng, năm sinh:" NGAY DƯỚI "Họ, chữ đệm, '
             'tên người yêu cầu" ở ĐẦU tờ khai, dd/mm/yyyy. KHÔNG lấy ngày sinh ở Section II (người '
             'được cấp) — hai khối có thể là hai người khác nhau.'},
    {"name": "ToKhaiYeuCau_SoDinhDanh",
     "desc": 'Số CCCD/CMND của NGƯỜI YÊU CẦU, lấy từ dòng "Giấy tờ tùy thân:" NGAY SAU tên người yêu '
             'cầu ở đầu tờ khai — KHÔNG lấy ở phần "người được cấp" phía dưới.'},
    {"name": "ToKhaiYeuCau_NgayCapGiayTo",
     "desc": 'Ngày cấp giấy tờ tùy thân của NGƯỜI YÊU CẦU (khối đầu tờ khai), dd/mm/yyyy.'},
    {"name": "ToKhaiYeuCau_NoiCapGiayTo",
     "desc": 'Nơi cấp giấy tờ tùy thân của NGƯỜI YÊU CẦU (khối đầu tờ khai).'},
    {"name": "ToKhaiYeuCau_NoiCuTru",
     "desc": 'Nơi cư trú của NGƯỜI YÊU CẦU ghi ở khối đầu tờ khai, object {quocGia,tinh,xa,diaChi}.'},
    {"name": "ToKhaiYeuCau_QuanHe",
     "desc": 'Quan hệ giữa NGƯỜI YÊU CẦU và người được cấp giấy, lấy NGUYÊN VĂN dòng "Quan hệ với '
             'người được cấp Giấy xác nhận tình trạng hôn nhân:" (hoặc biến thể gần đúng). Ví dụ: '
             '"Bản thân", "Tự khai", "là con đẻ", "là bố đẻ", "là mẹ đẻ", "là vợ", "là chồng", '
             '"là cháu". Giữ nguyên chữ trên tờ khai, KHÔNG tự diễn giải hay quy đổi.'},
    # --- Fields từ TỜ KHAI (thông tin người được xác nhận - Section II) ---
    {"name": "ToKhai_HoTen",
     "desc": 'Họ tên từ TỜ KHAI cấp giấy XNTTHN, lấy từ dòng "Họ, chữ đệm, tên:" trong phần "Đề nghị cấp Giấy xác nhận tình trạng hôn nhân cho người có tên dưới đây" (người được cấp).'},
    {"name": "ToKhai_NgaySinh",
     "desc": 'Ngày sinh từ TỜ KHAI, lấy từ dòng "Ngày, tháng, năm sinh:" trong phần người được cấp, dd/mm/yyyy.'},
    {"name": "ToKhai_GioiTinh",
     "desc": 'Giới tính từ TỜ KHAI, lấy từ dòng "Giới tính:" trong phần người được cấp: "Nam" hoặc "Nữ".'},
    {"name": "ToKhai_DanToc",
     "desc": 'Dân tộc từ TỜ KHAI, lấy từ dòng "Dân tộc:" trong phần người được cấp. Ưu tiên cao nhất cho thông tin người được cấp.'},
    {"name": "ToKhai_QuocTich",
     "desc": 'Quốc tịch từ TỜ KHAI, lấy từ dòng "Quốc tịch:" trong phần người được cấp.'},
    {"name": "ToKhai_SoDinhDanh",
     "desc": 'Số CCCD/CMND từ TỜ KHAI, lấy từ dòng "Giấy tờ tùy thân: ... số" trong phần người được cấp.'},
    {"name": "ToKhai_NgayCapGiayTo",
     "desc": 'Ngày cấp giấy tờ từ TỜ KHAI, lấy từ dòng "Cấp ngày..." trong phần người được cấp, dd/mm/yyyy.'},
    {"name": "ToKhai_NoiCapGiayTo",
     "desc": 'Nơi cấp giấy tờ từ TỜ KHAI, lấy từ dòng "tại ..." sau "Cấp ngày" trong phần người được cấp.'},
    {"name": "ToKhai_NoiCuTru",
     "desc": 'Nơi cư trú hiện tại trên TỜ KHAI cấp giấy XNTTHN, object {quocGia,tinh,xa,diaChi}. '
             'Lấy đúng dòng "Nơi cư trú" của người yêu cầu/người được cấp; bắt buộc trả khi tờ khai có.'},
    # --- Fields từ GIẤY KHAI SINH / TRÍCH LỤC KHAI SINH của chính người xin giấy ---
    # Hồ sơ hay kèm GKS để chứng minh nhân thân (dân tộc, ngày sinh) khi thẻ căn cước mẫu mới không
    # in dân tộc. GKS KHÔNG có "người yêu cầu": ngoài người được khai sinh nó chỉ còn cha, mẹ, người
    # đi khai sinh và cán bộ ký. Không có field riêng cho cha/mẹ thì agent đẩy tên họ sang
    # ToKhaiYeuCau_*/ToKhai_*, kéo mục I hoặc mục II của form thành tên cha/mẹ.
    {"name": "Gks_HoTen",
     "desc": 'Họ tên NGƯỜI ĐƯỢC KHAI SINH trên GIẤY KHAI SINH/TRÍCH LỤC KHAI SINH (dòng "Họ, chữ '
             'đệm, tên:" ở khối "Người được khai sinh"). KHÔNG lấy tên cha/mẹ/người đi khai sinh.'},
    {"name": "Gks_NgaySinh",
     "desc": "Ngày sinh của người được khai sinh trên giấy khai sinh, dd/mm/yyyy."},
    {"name": "Gks_GioiTinh",
     "desc": 'Giới tính của người được khai sinh trên giấy khai sinh: "Nam" hoặc "Nữ".'},
    {"name": "Gks_DanToc",
     "desc": "Dân tộc của người được khai sinh trên giấy khai sinh. Nguồn quý vì thẻ căn cước mẫu "
             "mới không in dân tộc."},
    {"name": "Gks_QuocTich",
     "desc": "Quốc tịch của người được khai sinh trên giấy khai sinh."},
    {"name": "Gks_ChaHoTen",
     "desc": 'Họ tên NGƯỜI CHA ghi trên giấy khai sinh (khối "Người cha"). BẮT BUỘC trả khi giấy có '
             '— Python mapper dùng để loại tên cha ra khỏi mục người yêu cầu/người được cấp. '
             'TUYỆT ĐỐI KHÔNG đẩy tên này sang ToKhaiYeuCau_* hay ToKhai_*.'},
    {"name": "Gks_MeHoTen",
     "desc": 'Họ tên NGƯỜI MẸ ghi trên giấy khai sinh (khối "Người mẹ"). BẮT BUỘC trả khi giấy có. '
             'TUYỆT ĐỐI KHÔNG đẩy tên này sang ToKhaiYeuCau_* hay ToKhai_*.'},
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
     "desc": 'Họ tên vợ/chồng hiện tại. Ưu tiên Giấy chứng nhận/đăng ký kết hôn; nếu không có thì lấy '
             'từ dòng "hiện tại đang có chồng/vợ là..." trên TỜ KHAI.'},
    {"name": "Marriage_Number",
     "desc": "Số Giấy chứng nhận/đăng ký kết hôn, lấy từ giấy kết hôn hoặc dòng tình trạng hôn nhân trên "
             "TỜ KHAI nếu ghi rõ. Không lấy số CCCD/CMND của vợ/chồng."},
    {"name": "Marriage_Date",
     "desc": "Ngày đăng ký/cấp Giấy chứng nhận kết hôn, dd/mm/yyyy; lấy từ giấy kết hôn hoặc TỜ KHAI "
             "nếu ghi rõ. Không lấy ngày sinh/ngày cấp CCCD của vợ/chồng."},
    {"name": "Marriage_Agency",
     "desc": "Cơ quan đăng ký/cấp Giấy chứng nhận kết hôn, lấy từ giấy kết hôn hoặc TỜ KHAI nếu ghi rõ. "
             "Không lấy cơ quan cấp CCCD của vợ/chồng."},
    # Tờ khai cho phép xin xác nhận CHƯA ĐĂNG KÝ KẾT HÔN TRONG MỘT KHOẢNG THỜI GIAN đã qua (vd để
    # bổ sung hồ sơ mua bán đất diễn ra trước khi kết hôn), kể cả khi HIỆN TẠI người đó đã có vợ/chồng.
    # Không có hai field này thì cả khoảng thời gian bị mất trắng khỏi output.
    {"name": "Period_TuNgay",
     "desc": 'Ngày BẮT ĐẦU của khoảng thời gian mong muốn xác nhận chưa đăng ký kết hôn với ai, '
             'dd/mm/yyyy. Lấy ở dòng "Tình trạng hôn nhân" của TỜ KHAI, sau chữ "Từ ngày ... tháng '
             '... năm ..." HOẶC dạng viết gọn "Từ ngày 27/4/2016", "Từ 27-4-2016". BẮT BUỘC trả kể '
             'cả khi ngày này TRÙNG ngày bản án ly hôn (DivorceDecision_Date) — một ngày được phép '
             'nằm ở cả hai field. Không có khoảng thời gian thì bỏ trống.'},
    {"name": "Period_DenNgay",
     "desc": 'Ngày KẾT THÚC của khoảng thời gian nói trên, dd/mm/yyyy. Lấy sau chữ "đến ngày ... '
             'tháng ... năm ..." trên cùng dòng, kể cả khi viết gọn "đến 14/9/2016" hay "tới '
             '14-9-2016" (chữ "ngày" có thể vắng). Không có thì bỏ trống.'},
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
    {"name": "PoA_SubjectDanToc",
     "desc": 'Dân tộc của người ủy quyền nếu giấy ủy quyền ghi ("Dân tộc: Kinh").'},
    # --- THẺ CCCD/CMND CỦA NGƯỜI ỦY QUYỀN (nếu hồ sơ kèm) — bản IN, ưu tiên hơn giấy ủy quyền/tờ khai ---
    {"name": "PoA_SubjectCccdHoTen",
     "desc": "Họ tên IN trên THẺ CCCD/CMND CỦA NGƯỜI ỦY QUYỀN (thẻ có số trùng/gần trùng PoA_SubjectIdNumber). "
             "KHÔNG lấy thẻ của người đi nộp (thẻ đó thuộc Cccd_*)."},
    {"name": "PoA_SubjectCccdSoDinhDanh",
     "desc": "Số định danh IN trên thẻ CCCD/CMND của người ủy quyền; có thể đọc từ MRZ mặt sau."},
    {"name": "PoA_SubjectCccdNgaySinh",
     "desc": "Ngày sinh IN trên thẻ CCCD/CMND của người ủy quyền, dd/mm/yyyy."},
    {"name": "PoA_SubjectCccdGioiTinh",
     "desc": 'Giới tính IN trên thẻ CCCD/CMND của người ủy quyền: "Nam" hoặc "Nữ".'},
    {"name": "PoA_SubjectCccdNgayCap",
     "desc": "Ngày cấp trên thẻ CCCD/CMND của người ủy quyền (mặt sau), dd/mm/yyyy."},
    {"name": "PoA_SubjectCccdNoiCap",
     "desc": 'Nơi cấp thẻ CCCD/CMND của người ủy quyền (mặt sau). "CỤC TRƯỞNG CỤC CẢNH SÁT..." → '
             '"Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},
    {"name": "PoA_SubjectCccdNoiCuTru",
     "desc": 'Nơi thường trú IN trên THẺ CCCD/CMND CỦA NGƯỜI ỦY QUYỀN (thẻ có số trùng PoA_SubjectIdNumber) '
             'nếu hồ sơ có kèm thẻ đó, object {quocGia,tinh,xa,diaChi}. KHÔNG lấy từ giấy ủy quyền, '
             'KHÔNG lấy thẻ của người đi nộp (thẻ đó thuộc Cccd_*).'},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Cccd_NgaySinh", "Cccd_NgayCap", "PoA_SubjectDoB", "PoA_SubjectIdDate",
              "PoA_SubjectCccdNgaySinh", "PoA_SubjectCccdNgayCap", "ToKhai_NgaySinh", "ToKhai_NgayCapGiayTo", "ToKhaiYeuCau_NgaySinh", "ToKhaiYeuCau_NgayCapGiayTo", "Gks_NgaySinh"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
COMPACT_COMP_BY_NAME["DivorceDecision_Date"] = "x-date"
COMPACT_COMP_BY_NAME["DeathCert_Date"] = "x-date"
COMPACT_COMP_BY_NAME["Marriage_Date"] = "x-date"
COMPACT_COMP_BY_NAME["Period_TuNgay"] = "x-date"
COMPACT_COMP_BY_NAME["Period_DenNgay"] = "x-date"
COMPACT_COMP_BY_NAME["ToKhai_NoiCuTru"] = "x-select-area"
COMPACT_COMP_BY_NAME["ToKhaiYeuCau_NoiCuTru"] = "x-select-area"
COMPACT_COMP_BY_NAME["Cccd_NoiCuTru"] = "x-select-area"
COMPACT_COMP_BY_NAME["PoA_SubjectAddress"] = "x-select-area"
COMPACT_COMP_BY_NAME["PoA_SubjectCccdNoiCuTru"] = "x-select-area"
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
    "nycNoiCuTru_NuocNgoai": "x-select-area",
    "quanhevoinguoiduocxacminh": "x-radio",
    # Ô nhập free-text cạnh option "Khác" của mục quan hệ (chỉ render sau khi tick "Khác").
    "quanhekhac": "raw",
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
    "nxnNoiCuTru_NuocNgoai": "x-select-area",
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
    # (17) "Số lượng bản sao" — ô BẮT BUỘC của cổng nhưng tờ khai giấy không có mục này, nên Python
    # điền mặc định 1 (viền vàng để cán bộ rà lại). Tên DOM giống thủ tục Trích lục cùng họ eForm.
    "SoLuong": "raw",
}

UI_ALIASES = {
    # Tên ô "quan hệ khác" đổi theo phiên bản eForm; extension còn có fallback theo cấu trúc
    # (ô nhập nằm trong/kề option "Khác" đang tick) nếu không tên nào khớp.
    "quanhekhac": [
        "nhapquanhekhac",
        "quanhevoinguoiduocxacminhkhac",
        "quanhevoinguoiduocxacminh_khac",
        "quanhe_khac",
        "nhapquanhe",
    ],
    "SoGiayToTuyThanC": ["TenGiayToC", "SoGiayToDinhDanhC"],
    "SoGiayToTuyThanC1": ["SoGiayToDinhDanhC1", "TenGiayToC1"],
    "nxnLoaiTinhTrangHonNhan=3": ["nxnLoaiTinhTrangHonNhan=2"],
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
