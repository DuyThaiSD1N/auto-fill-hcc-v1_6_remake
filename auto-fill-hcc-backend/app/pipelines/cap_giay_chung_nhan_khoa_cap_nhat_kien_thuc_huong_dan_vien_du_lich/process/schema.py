"""Compact schema cho "Thủ tục cấp Giấy chứng nhận khóa cập nhật kiến thức cho hướng dẫn viên du lịch nội địa và
hướng dẫn viên du lịch quốc tế" (1.004605, QT-123).

Cổng Bộ VHTTDL `dichvucong.bvhttdl.gov.vn` (nộp về Sở VHTTDL tỉnh) — Angular Material bọc trong `liz-*`, DOM không
có formcontrolname, ô trong x-decoder chỉ có id tự sinh. Form và bảng thành phần hồ sơ NẰM CHUNG trang `/nop-ho-so`.
LLM chỉ trả FACT nguồn; `mapper.enrich` suy tất định ra ô UI theo (section = `.group-header`, name = `<mat-label>`)
cho engine `fill-liz.js`.

Hồ sơ chỉ có MỘT người: hướng dẫn viên đăng ký tham dự khóa (Mẫu số 06 Phụ lục II Thông tư 04/2024/TT-BVHTTDL).
Trang có:
  - "Thông tin người nộp hồ sơ" — của tài khoản đăng nhập (Tên, CMND cổng khoá theo tài khoản) → điền khi tài khoản
    CHÍNH LÀ người đăng ký (trùng số CCCD; đơn chưa có số thật thì trùng họ tên);
  - "Thông tin người ủy quyền" — khối ẩn, hiện khi tích ô cùng tên. Tài khoản KHÁC người đăng ký (nộp thay) → tích ô
    rồi điền người đăng ký vào đây, như CCHN di tích 1.001822;
  - "THÔNG TIN ĐƠN ĐỀ NGHỊ" — nội dung Mẫu 06: giới tính, thẻ HDV đã được cấp, công văn/thông báo mở khóa, ngày
    bắt đầu – kết thúc khóa;
  - "Thông tin biên lai" — nhập một ô thì phải đủ 5 ô → không điền.

⚑ Bản DOM lập mapping bị Google Dịch; nhãn khối đơn đã đối chiếu ảnh chụp cổng thật (06/11/2026): "Loại thẻ",
"Giới tính người đề nghị", "Số thẻ:", "Nơi cấp:", "Ngày cấp:", "Căn cứ Thông báo số", "Ngày thông báo", "Ngày bắt đầu",
"Ngày kết thúc" (engine bỏ dấu ':' cuối nhãn). Nơi cấp / Ngày cấp thẻ nhãn trùng hai khối trên nên vẫn khai thêm
`after` = ô Số thẻ: engine lấy ô chữ / ô ngày ĐẦU TIÊN sau ô Số thẻ, cùng section.
"""

FIELDS: list[dict] = [
    # ---- NGƯỜI ĐĂNG KÝ (Đơn Mẫu 06; đối chiếu CCCD, thẻ HDV nếu có) ----
    {
        "name": "NguoiDeNghi_HoTen",
        "desc": "Họ và tên người đăng ký — dòng '- Họ và tên (chữ in hoa)' của Đơn; đối chiếu CCCD, chữ ký 'NGƯỜI ĐỀ "
                "NGHỊ' cuối đơn. Viết có dấu.",
    },
    {
        "name": "NguoiDeNghi_SoDinhDanh",
        "desc": "Số định danh cá nhân/CMND của người đăng ký (dòng 'Số định danh cá nhân/ Chứng minh nhân dân' của "
                "Đơn, hoặc CCCD). Chỉ chữ số, chép ĐỦ các chữ số đọc được, KHÔNG bù. KHÔNG lấy số thẻ HDV.",
    },
    {
        "name": "NguoiDeNghi_NgaySinh",
        "desc": "Ngày sinh người đăng ký, dd/mm/yyyy (Đơn: 'Ngày tháng năm sinh'; CCCD). Chỉ trả khi ĐỦ ngày-tháng-năm.",
    },
    {
        "name": "NguoiDeNghi_GioiTinh",
        "desc": "Giới tính ở Đơn ('Giới tính: ☒ Nam ☐ Nữ') hoặc CCCD: 'Nam' hoặc 'Nữ'. Chỉ trả khi ô được đánh dấu "
                "rõ hoặc CCCD ghi rõ; ô '☐' rỗng là KHÔNG chọn.",
    },
    {
        "name": "NguoiDeNghi_NgayCap",
        "desc": "Ngày cấp CCCD — CHỈ lấy trên thẻ CCCD (mặt sau), dd/mm/yyyy. Đơn Mẫu 06 không có ngày cấp CCCD: "
                "'Ngày cấp' trong dòng thẻ hướng dẫn viên KHÔNG phải ngày cấp CCCD.",
    },
    {
        "name": "NguoiDeNghi_NoiCap",
        "desc": "Nơi cấp CCCD — CHỈ lấy cơ quan cấp in trên thẻ CCCD ('Cục Cảnh sát quản lý hành chính về trật tự xã "
                "hội' / 'Bộ Công an'). 'Nơi cấp' trong dòng thẻ hướng dẫn viên KHÔNG phải nơi cấp CCCD.",
    },
    {
        "name": "NguoiDeNghi_DiaChi",
        "desc": "Dòng 'Địa chỉ liên lạc' của Đơn; đơn để trống thì nơi thường trú/nơi cư trú trên CCCD. Object "
                "{tinh,xa,chiTietDuoiXa}. KHÔNG lấy nơi lập đơn ('Nha Trang, ngày…') hay địa chỉ của Sở.",
    },
    {"name": "NguoiDeNghi_DienThoai", "desc": "Dòng 'Điện thoại' của Đơn, chỉ chữ số, chép đủ các chữ số đọc được."},
    {
        "name": "NguoiDeNghi_Email",
        "desc": "Email ĐẦU TIÊN của Đơn — ô 'Email' cùng dòng 'Điện thoại'. Nguyên văn, bỏ chữ 'Email:' lặp lại nếu "
                "OCR dính vào.",
    },
    {
        "name": "NguoiDeNghi_EmailKhac",
        "desc": "Chỉ khi Đơn ghi HAI địa chỉ email KHÁC nhau: email còn lại (không phải email đã trả ở "
                "NguoiDeNghi_Email). Đơn chỉ có một email thì bỏ field.",
    },

    # ---- THẺ HƯỚNG DẪN VIÊN ĐÃ ĐƯỢC CẤP (mục '- Đã được cấp thẻ hướng dẫn viên du lịch' của Đơn; thẻ HDV nếu có) ----
    {
        "name": "The_Loai",
        "desc": "Loại thẻ đã được cấp — ô được đánh dấu ở dòng '+ Loại: ☐ Nội địa ☐ Quốc tế ☐ Tại điểm': 'nội địa', "
                "'quốc tế' hoặc 'tại điểm'; hoặc chữ in trên thẻ HDV. Không thấy ô nào được đánh dấu thì bỏ field.",
    },
    {
        "name": "The_So",
        "desc": "Số thẻ hướng dẫn viên — dòng '+ Số thẻ' của Đơn, hoặc số in trên thẻ HDV. Chép NGUYÊN VĂN từng ký tự; "
                "phần bị xuống dòng thì nối lại bằng MỘT dấu cách, KHÔNG tự thêm gạch nối. KHÔNG lấy số CCCD, số "
                "công văn.",
    },
    {
        "name": "The_NoiCap",
        "desc": "Nơi cấp thẻ HDV — '- Nơi cấp' NGAY SAU Số thẻ, cùng dòng (vd 'Sở VHTTDL Khánh Hòa'). Nguyên văn.",
    },
    {
        "name": "The_NgayCap",
        "desc": "Ngày cấp thẻ HDV — '- Ngày cấp' NGAY SAU Nơi cấp ở trên, cùng dòng Số thẻ, dd/mm/yyyy.",
    },
    {
        "name": "The_NoiCapKhac",
        "desc": "Chỉ khi dòng thẻ HDV ghi HAI bộ 'Nơi cấp … Ngày cấp …': Nơi cấp của bộ THỨ HAI, nguyên văn. Chỉ có "
                "một bộ thì bỏ field.",
    },
    {
        "name": "The_NgayCapKhac",
        "desc": "Chỉ khi dòng thẻ HDV ghi HAI bộ 'Nơi cấp … Ngày cấp …': Ngày cấp của bộ THỨ HAI, dd/mm/yyyy.",
    },

    # ---- KHÓA CẬP NHẬT KIẾN THỨC (câu 'Căn cứ Công văn số … ngày … của …, tôi đăng ký … từ ngày … đến ngày …') ----
    {
        "name": "CongVan_So",
        "desc": "Số công văn/thông báo mở khóa — phần sau 'Căn cứ Công văn số' (hoặc 'Thông báo số'), tới trước chữ "
                "'ngày' (vd '1234/SVHTTDL-QLDL'). Chép NGUYÊN VĂN từng ký tự của ký hiệu: KHÔNG thêm dấu tiếng Việt "
                "(OCR ghi 'QLDL' thì giữ 'QLDL', không đổi thành 'QLĐL'); chỉ bỏ dấu cách thừa quanh '/' và '-'.",
    },
    {"name": "CongVan_Ngay", "desc": "Ngày của công văn/thông báo đó (chữ 'ngày' ngay sau số công văn), dd/mm/yyyy."},
    {"name": "CongVan_CoQuan", "desc": "Cơ quan ban hành công văn — phần sau 'của' (vd 'Sở Văn hóa, Thể thao và Du lịch …')."},
    {"name": "Khoa_TuNgay", "desc": "Ngày bắt đầu khóa học — '… từ ngày dd/mm/yyyy', dd/mm/yyyy."},
    {"name": "Khoa_DenNgay", "desc": "Ngày kết thúc khóa học — '… đến ngày dd/mm/yyyy', dd/mm/yyyy."},
    {"name": "Don_CoQuanNhan", "desc": "Cơ quan ở dòng 'Kính gửi' của Đơn (vd 'Sở Văn hóa, Thể thao và Du lịch tỉnh …')."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _n in ("NguoiDeNghi_NgaySinh", "NguoiDeNghi_NgayCap", "The_NgayCap", "The_NgayCapKhac", "CongVan_Ngay",
           "Khoa_TuNgay", "Khoa_DenNgay"):
    COMPACT_COMP_BY_NAME[_n] = "x-date"
COMPACT_COMP_BY_NAME["NguoiDeNghi_DiaChi"] = "x-select-area"

# ---- UI fields cho engine fill-liz.js — khớp (section, mat-label) ----
# Section là CỤM NGẮN: engine chấp nhận header chứa cụm này (hoặc ngược lại).
S_NOP = "Thông tin người nộp hồ sơ"
S_UQ = "Thông tin người ủy quyền"
S_DON = "đơn đề nghị"

# Nhãn ô tích bật khối ủy quyền (liz-checkbox, trùng chữ với group-header của khối).
UY_QUYEN_CHECKBOX = "Thông tin người ủy quyền"

LABEL_LOAI_THE = "Loại thẻ"
LABEL_GIOI_TINH = "Giới tính người đề nghị"
LABEL_SO_THE = "Số thẻ"
LABEL_NOI_CAP_THE = "Nơi cấp"
LABEL_NGAY_CAP_THE = "Ngày cấp"
LABEL_THONG_BAO_SO = "Căn cứ Thông báo số"
LABEL_NGAY_THONG_BAO = "Ngày thông báo"
LABEL_NGAY_BAT_DAU = "Ngày bắt đầu"
LABEL_NGAY_KET_THUC = "Ngày kết thúc"

# comp: liz-input (text/textarea) | liz-date (datepicker dd/mm/yyyy) | liz-select (mat-select overlay).
# Cố ý BỎ: Phần I (cơ quan/lĩnh vực/thủ tục cổng khoá theo link, dịch vụ công chọn sẵn theo MaDVC, CCCD tư vấn,
# VNPost, ghi chú); ô disabled của khối người nộp (Tên, CMND — cổng tự điền từ tài khoản); biên lai; ô cam kết (người
# nộp tự tích). Nhãn hai khối người nộp / ủy quyền đã đối chiếu ảnh chụp cổng thật (06/11/2026).
UI_FIELDS: list[tuple[str, str, str, tuple[str, ...]]] = [
    (S_NOP, "Ngày sinh", "liz-date", ()),
    (S_NOP, "Ngày cấp", "liz-date", ()),
    (S_NOP, "Nơi cấp", "liz-input", ()),
    (S_NOP, "Số điện thoại", "liz-input", ("Điện thoại",)),
    (S_NOP, "Email", "liz-input", ("E-mail",)),
    (S_NOP, "Địa chỉ hành chính", "liz-select", ()),
    (S_NOP, "Địa chỉ chi tiết", "liz-input", ()),

    (S_UQ, "Tên người / Tên đơn vị ủy quyền", "liz-input", ()),
    (S_UQ, "Ngày sinh", "liz-date", ()),
    (S_UQ, "CMND/Hộ chiếu/MST Doanh nghiệp", "liz-input", ()),
    (S_UQ, "Ngày cấp", "liz-date", ()),
    (S_UQ, "Nơi cấp", "liz-input", ()),
    (S_UQ, "Số điện thoại", "liz-input", ()),
    (S_UQ, "Email", "liz-input", ("E-mail",)),
    (S_UQ, "Địa chỉ hành chính", "liz-select", ()),
    (S_UQ, "Địa chỉ chi tiết", "liz-input", ()),

    (S_DON, LABEL_LOAI_THE, "liz-select",
     ("Loại", "Loại thẻ hướng dẫn viên du lịch", "Loại thẻ hướng dẫn viên", "Loại thẻ đã được cấp")),
    (S_DON, LABEL_GIOI_TINH, "liz-select", ("Giới tính",)),
    (S_DON, LABEL_SO_THE, "liz-input", ("Số", "Số thẻ hướng dẫn viên du lịch", "Số thẻ HDV")),
    (S_DON, LABEL_NOI_CAP_THE, "liz-input", ("Nơi cấp thẻ", "Cơ quan cấp", "Cơ quan cấp thẻ")),
    (S_DON, LABEL_NGAY_CAP_THE, "liz-date", ("Ngày cấp thẻ", "Ngày")),
    (S_DON, LABEL_THONG_BAO_SO, "liz-input", ("Căn cứ Công văn số", "Thông báo số", "Số thông báo")),
    (S_DON, LABEL_NGAY_THONG_BAO, "liz-date", ("Ngày công văn", "Ngày ban hành thông báo")),
    (S_DON, LABEL_NGAY_BAT_DAU, "liz-date", ("Từ ngày", "Ngày đầu")),
    (S_DON, LABEL_NGAY_KET_THUC, "liz-date", ("Đến ngày", "Ngày cuối")),
]

COMP_BY_UI = {(s, l): c for s, l, c, _a in UI_FIELDS}
ALIASES_BY_UI = {(s, l): list(a) for s, l, _c, a in UI_FIELDS}

# Nơi cấp / Ngày cấp thẻ: nhãn trùng khối người nộp và chưa xác nhận được trên DOM gốc → engine rơi về vị trí: ô chữ /
# ô ngày ĐẦU TIÊN ngay sau ô Số thẻ, cùng section (DOM: Số → Nơi cấp → Ngày cấp).
_SO_THE_LABELS = [LABEL_SO_THE, *ALIASES_BY_UI[(S_DON, LABEL_SO_THE)]]
AFTER_BY_UI = {(S_DON, LABEL_NOI_CAP_THE): _SO_THE_LABELS, (S_DON, LABEL_NGAY_CAP_THE): _SO_THE_LABELS}
