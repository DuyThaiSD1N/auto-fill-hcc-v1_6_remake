"""Compact schema for "Xác nhận tình trạng hôn nhân".

The requester is always the subject ("Bản thân"). The LLM returns source facts
from the declaration/identity documents; UI defaults and duplicate
requester/subject fields are derived in Python.
"""

FIELDS: list[dict] = [
    # --- NGƯỜI ĐƯỢC CẤP giấy XNTTHN: thông tin IN trên giấy tờ của chính người đó ---
    # Nguồn phổ biến là thẻ CCCD/CMND/căn cước; field nào thẻ không in (thường là dân tộc) thì lấy giấy in
    # khác đứng tên họ — chọn nguồn theo TỪNG field, không theo cả nhóm. KHÔNG lấy từ tờ khai (đã có
    # ToKhai_*): mapper cần hai nguồn riêng để bản in thắng chữ viết tay khi cùng số định danh. Hồ sơ
    # ủy quyền: người được cấp là NGƯỜI ỦY QUYỀN.
    {"name": "NguoiDuocCap_HoTen",
     "desc": 'Họ tên NGƯỜI ĐƯỢC CẤP giấy XNTTHN in trên giấy tờ của chính họ — thường là thẻ CCCD/CMND/'
             'căn cước; không có thẻ thì giấy in khác đứng tên họ (giấy XNTTHN đã cấp trước đây, xác nhận '
             'thông tin cư trú). KHÔNG lấy từ tờ khai. Hồ sơ ủy quyền: đây là NGƯỜI ỦY QUYỀN (người cần '
             'giấy); thẻ của người đi nộp thuộc NguoiYeuCau_*.'},
    {"name": "NguoiDuocCap_SoDinhDanh",
     "desc": "Số định danh/CCCD/CMND của người được cấp, cùng nguồn với NguoiDuocCap_HoTen; trên thẻ có thể "
             "đọc từ dòng MRZ mặt sau."},
    {"name": "NguoiDuocCap_NgaySinh",
     "desc": "Ngày sinh của người được cấp, cùng nguồn với NguoiDuocCap_HoTen, dd/mm/yyyy."},
    {"name": "NguoiDuocCap_GioiTinh",
     "desc": 'Giới tính của người được cấp, cùng nguồn với NguoiDuocCap_HoTen: "Nam" hoặc "Nữ".'},
    {"name": "NguoiDuocCap_DanToc",
     "desc": "Dân tộc IN trên thẻ CCCD/CMND của người được cấp (CMND cũ có in; thẻ mẫu mới thường không in "
             "thì bỏ trống). Dân tộc ghi trên giấy tờ khác thuộc GiayToKhac_DanToc."},
    {"name": "GiayToKhac_DanToc",
     "desc": "Dân tộc của NGƯỜI ĐƯỢC CẤP ghi trên giấy tờ KHÁC tờ khai và thẻ: khối \"XÁC NHẬN\" của giấy XNTTHN đã "
             "cấp trước đây, xác nhận thông tin cư trú, giấy chứng nhận kết hôn (đúng cột của người được cấp), "
             "giấy khai sinh của CHÍNH người được cấp. BẮT BUỘC trả khi một giấy như vậy có ghi, KỂ CẢ khi hồ sơ "
             "có thẻ hoặc tờ khai. KHÔNG lấy dân tộc của người đã mất, của con, cha mẹ, hay của vợ/chồng. Chép "
             "nguyên chữ, giữ cả dấu nháy (\"K'Ho\")."},
    {"name": "NguoiDuocCap_QuocTich",
     "desc": "Quốc tịch của người được cấp nếu giấy ghi rõ."},
    {"name": "NguoiDuocCap_NgayCap",
     "desc": 'Ngày cấp thẻ CCCD/CMND của người được cấp — mặt sau thẻ, dòng "Ngày, tháng, năm / Date, '
             'month, year", dd/mm/yyyy. Không có thẻ thì ngày cấp giấy tờ tùy thân ghi trên giấy in khác '
             'đứng tên họ. KHÔNG lấy từ tờ khai.'},
    {"name": "NguoiDuocCap_NoiCap",
     "desc": 'Nơi cấp thẻ của người được cấp (mặt sau thẻ). Thấy "CỤC TRƯỞNG CỤC CẢNH SÁT..." thì trả '
             '"Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mẫu mới ghi "BỘ CÔNG AN" '
             'thì trả "Bộ Công an".'},
    {"name": "NguoiDuocCap_NoiCuTru",
     "desc": 'Nơi thường trú/cư trú của người được cấp in trên thẻ (không có thẻ thì giấy in khác đứng tên '
             'họ), object {quocGia,tinh,xa,diaChi}. KHÔNG lấy từ tờ khai; KHÔNG lấy "nơi thường trú cuối '
             'cùng" trên giấy khai tử (đó là của người đã mất).'},
    # --- NGƯỜI YÊU CẦU / NGƯỜI ĐI NỘP KHÁC người được cấp: thông tin IN trên thẻ của người đó ---
    # Người được ủy quyền đi nộp, hoặc người thân khai hộ có kèm thẻ. Chỉ một người thì nhóm này trống.
    {"name": "NguoiYeuCau_HoTen",
     "desc": 'Họ tên in trên thẻ CCCD/CMND/căn cước của NGƯỜI ĐI NỘP / NGƯỜI YÊU CẦU, CHỈ trả khi người này '
             'KHÁC người được cấp: người được ủy quyền (phần "Người được ủy quyền" của giấy ủy quyền) hoặc '
             'người thân khai hộ (khối đầu tờ khai ghi tên người khác). Hồ sơ chỉ có một người thì để trống.'},
    {"name": "NguoiYeuCau_SoDinhDanh",
     "desc": "Số định danh in trên thẻ của người đi nộp (NguoiYeuCau_HoTen); có thể đọc từ MRZ mặt sau."},
    {"name": "NguoiYeuCau_NgaySinh",
     "desc": "Ngày sinh in trên thẻ của người đi nộp, dd/mm/yyyy."},
    {"name": "NguoiYeuCau_NgayCap",
     "desc": "Ngày cấp thẻ của người đi nộp (mặt sau thẻ), dd/mm/yyyy."},
    {"name": "NguoiYeuCau_NoiCap",
     "desc": 'Nơi cấp thẻ của người đi nộp; chuẩn hóa như NguoiDuocCap_NoiCap.'},
    {"name": "NguoiYeuCau_NoiCuTru",
     "desc": "Nơi thường trú in trên thẻ của người đi nộp, object {quocGia,tinh,xa,diaChi}."},
    # --- Fields từ TỜ KHAI (thông tin NGƯỜI YÊU CẦU - Section I, ghi ở ĐẦU tờ khai) ---
    # Tờ khai luôn có HAI khối riêng: "Họ, chữ đệm, tên người yêu cầu" (đầu tờ khai) và "Đề nghị cấp
    # Giấy xác nhận... cho người có tên dưới đây" (Section II, → ToKhai_*). Hai khối này CÓ THỂ khác
    # người (thân nhân đứng nộp hộ mà không kèm giấy ủy quyền chính thức) — PHẢI tách riêng, không
    # gộp vào ToKhai_* của Section II.
    {"name": "ToKhaiYeuCau_HoTen",
     "desc": 'Họ tên NGƯỜI YÊU CẦU, lấy từ dòng "Họ, chữ đệm, tên người yêu cầu:" ở ĐẦU tờ khai. '
             'Đây là người ĐI NỘP đơn, CÓ THỂ KHÁC người được cấp giấy ở Section II — không tự suy '
             'đoán trùng nhau, lấy đúng tên ghi ở dòng này. Chỉ lấy từ TỜ KHAI: người được khai sinh, cha, '
             'mẹ trên giấy khai sinh và người đã mất trên giấy khai tử KHÔNG phải người yêu cầu.'},
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
     "desc": 'Họ tên từ TỜ KHAI cấp giấy XNTTHN, lấy từ dòng "Họ, chữ đệm, tên:" trong phần "Đề nghị cấp Giấy xác nhận tình trạng hôn nhân cho người có tên dưới đây" (người được cấp). Chỉ lấy từ TỜ KHAI: người được khai sinh, cha, mẹ trên giấy khai sinh và người đã mất trên giấy khai tử KHÔNG phải người được cấp.'},
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
    {"name": "ToKhai_LaBanThan",
     "desc": 'Trả true CHỈ khi TỜ KHAI ghi quan hệ "Tự khai"/"Bản thân" và họ tên người yêu cầu '
             'trùng họ tên người được cấp giấy. Không suy luận từ một CCCD đơn lẻ.'},
    {"name": "TinhTrangHonNhanC1",
     "desc": 'Tình trạng hôn nhân'},
    {"name": "DivorceDecision_Number",
     "desc": "Số bản án/quyết định ly hôn: lấy từ bản án/quyết định ly hôn thật; hồ sơ không có văn bản đó thì "
             "lấy từ dòng tình trạng hôn nhân trên TỜ KHAI / giấy XNTTHN cũ."},
    {"name": "DivorceDecision_Date",
     "desc": "Ngày cấp/ban hành bản án/quyết định ly hôn, dd/mm/yyyy; nguồn như DivorceDecision_Number."},
    {"name": "DivorceDecision_Agency",
     "desc": "Cơ quan ban hành/cấp bản án/quyết định ly hôn; nguồn như DivorceDecision_Number."},
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
             'nằm ở cả hai field. Không có khoảng thời gian thì bỏ trống. CHỈ lấy từ TỜ KHAI: hồ sơ không '
             'có tờ khai thì bỏ trống; ngày chết của vợ/chồng hay ngày cấp giấy khác KHÔNG phải mốc này.'},
    {"name": "Period_DenNgay",
     "desc": 'Ngày KẾT THÚC của khoảng thời gian nói trên, dd/mm/yyyy. Lấy sau chữ "đến ngày ... '
             'tháng ... năm ..." trên cùng dòng, kể cả khi viết gọn "đến 14/9/2016" hay "tới '
             '14-9-2016" (chữ "ngày" có thể vắng). Không có thì bỏ trống, không tự đặt.'},
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
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("NguoiDuocCap_NgaySinh", "NguoiDuocCap_NgayCap", "NguoiYeuCau_NgaySinh", "NguoiYeuCau_NgayCap",
              "PoA_SubjectDoB", "PoA_SubjectIdDate", "ToKhai_NgaySinh", "ToKhai_NgayCapGiayTo",
              "ToKhaiYeuCau_NgaySinh", "ToKhaiYeuCau_NgayCapGiayTo"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
COMPACT_COMP_BY_NAME["DivorceDecision_Date"] = "x-date"
COMPACT_COMP_BY_NAME["DeathCert_Date"] = "x-date"
COMPACT_COMP_BY_NAME["Marriage_Date"] = "x-date"
COMPACT_COMP_BY_NAME["Period_TuNgay"] = "x-date"
COMPACT_COMP_BY_NAME["Period_DenNgay"] = "x-date"
COMPACT_COMP_BY_NAME["ToKhai_NoiCuTru"] = "x-select-area"
COMPACT_COMP_BY_NAME["ToKhaiYeuCau_NoiCuTru"] = "x-select-area"
COMPACT_COMP_BY_NAME["NguoiDuocCap_NoiCuTru"] = "x-select-area"
COMPACT_COMP_BY_NAME["NguoiYeuCau_NoiCuTru"] = "x-select-area"
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
