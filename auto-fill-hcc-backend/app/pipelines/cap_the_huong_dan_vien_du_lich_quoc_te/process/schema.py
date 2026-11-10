"""Compact schema cho "Thủ tục cấp thẻ hướng dẫn viên du lịch quốc tế" (mã 1.004628, QT-120).

Cổng Bộ VHTTDL `dichvucong.bvhttdl.gov.vn` (nộp về Sở VHTTDL tỉnh) — Angular Material bọc trong `liz-*`, DOM không có
formcontrolname, ô chỉ có id tự sinh. Form và bảng thành phần hồ sơ NẰM CHUNG trang. LLM chỉ trả FACT nguồn;
`mapper.enrich` suy tất định ra ô UI theo (section = `.group-header`, name = `<mat-label>`) cho engine `fill-liz.js`.

Hồ sơ chỉ có MỘT người: người đề nghị cấp thẻ (Đơn Mẫu 04). Khối người nộp / người ủy quyền chọn theo mốc tài khoản
(xem mapper, cùng cách với 1.004605). Phần IV là nội dung Đơn Mẫu 04 (giới tính, trình độ chuyên môn, trình độ ngoại
ngữ); thẻ quốc tế KHÔNG có ô Email riêng ở Phần IV như bản nội địa.

⚑ Mapping lập từ DOM bị Google Dịch: nhãn dưới đây là nhãn khôi phục (giống trang thẻ nội địa 1.004623 cùng cổng), mỗi
ô kèm `aliases`. Ô chọn "Trong" (mat-select đầu Phần IV) chưa rõ nhãn gốc → KHÔNG khai, chờ xác nhận trên cổng.
"""

FIELDS: list[dict] = [
    # ---- NGƯỜI ĐỀ NGHỊ CẤP THẺ (Đơn Mẫu 04; đối chiếu văn bằng, chứng chỉ, CCCD nếu có) ----
    {
        "name": "NguoiDeNghi_HoTen",
        "desc": "Họ và tên người đề nghị cấp thẻ — dòng 'Họ và tên (chữ in hoa)' Đơn Mẫu 04; đối chiếu tên trên văn "
                "bằng/chứng chỉ. Viết có dấu như bản tiếng Việt, KHÔNG lấy bản tiếng Anh không dấu.",
    },
    {
        "name": "NguoiDeNghi_NgaySinh",
        "desc": "Ngày sinh người đề nghị, dd/mm/yyyy. Nguồn: Đơn 04 → CCCD → chứng chỉ/văn bằng. Chỉ trả khi đọc được "
                "ĐỦ ngày-tháng-năm.",
    },
    {
        "name": "NguoiDeNghi_GioiTinh",
        "desc": "Giới tính ở Đơn 04 ('Giới tính: ☒ Nam □ Nữ') hoặc CCCD: 'Nam' hoặc 'Nữ'. Chỉ trả khi ô được đánh dấu "
                "rõ hoặc CCCD ghi rõ.",
    },
    {
        "name": "NguoiDeNghi_SoDinhDanh",
        "desc": "Số định danh cá nhân/CMND của người đề nghị (Đơn 04, CCCD). Chỉ chữ số, chép ĐỦ các chữ số đọc được; "
                "số bị che/mờ một phần thì chép phần đọc được, KHÔNG bù.",
    },
    {"name": "NguoiDeNghi_NgayCap", "desc": "Ngày cấp CCCD (mặt sau CCCD), dd/mm/yyyy. Đơn 04 không có mục này."},
    {"name": "NguoiDeNghi_NoiCap", "desc": "Nơi cấp CCCD (cơ quan cấp in trên CCCD: 'Bộ Công an' / 'Cục Cảnh sát quản lý hành chính về trật tự xã hội')."},
    {"name": "NguoiDeNghi_DienThoai", "desc": "Điện thoại ở Đơn 04, chỉ chữ số, chép đủ các chữ số đọc được."},
    {"name": "NguoiDeNghi_Email", "desc": "Email ở Đơn 04, nguyên văn. Phần tên hộp thư bị che thì bỏ field."},
    {
        "name": "NguoiDeNghi_DiaChi",
        "desc": "Địa chỉ liên lạc ở Đơn 04; đơn để trống thì lấy nơi cư trú/nơi thường trú trên CCCD. Object "
                "{tinh,xa,chiTietDuoiXa}. KHÔNG lấy nơi lập đơn ('Hà Nội, ngày…'), nơi chứng thực, địa chỉ trường "
                "học hay trung tâm khảo thí thay cho địa chỉ liên lạc.",
    },
    {
        "name": "NguoiDeNghi_TrinhDoChuyenMon",
        "desc": "Dòng 'Trình độ chuyên môn nghiệp vụ' ở Đơn 04, chép nguyên văn (vd 'Cử nhân Quản trị dịch vụ du lịch "
                "và lữ hành', 'Đại học').",
    },
    {
        "name": "NguoiDeNghi_TrinhDoNgoaiNgu",
        "desc": "Phần ghi sau 'Trình độ ngoại ngữ (đối với người đề nghị cấp thẻ HDV du lịch quốc tế):' ở Đơn 04 — "
                "có thể xuống dòng; chép nguyên văn cả câu (vd 'Tiếng Anh – Chứng chỉ IELTS Academic 7.0 (tương "
                "đương bậc 5 …)'). Dòng chấm/để trống thì bỏ field.",
    },
    {
        "name": "Don_LoaiThe",
        "desc": "Loại thẻ ghi ở tiêu đề Đơn 04 'Cấp thẻ hướng dẫn viên du lịch …': 'quốc tế', 'nội địa' hoặc 'tại "
                "điểm'.",
    },
    {"name": "Don_CoQuanNhan", "desc": "Cơ quan ở dòng 'Kính gửi' của Đơn 04 (vd 'Sở Văn hóa, Thể thao và Du lịch tỉnh …')."},

    # ---- NGOẠI NGỮ: chứng chỉ ngoại ngữ / văn bằng ngoại ngữ (đối chiếu + bù ô trình độ ngoại ngữ) ----
    {
        "name": "NgoaiNgu_ChungChi",
        "desc": "Chứng chỉ/văn bằng chứng minh ngoại ngữ: ngôn ngữ + tên chứng chỉ + điểm/bậc (vd 'Tiếng Anh – IELTS "
                "Academic 7.0', 'Tiếng Trung – HSK 5', 'Cử nhân Ngôn ngữ Anh'). Lấy từ CHÍNH tờ chứng chỉ/văn bằng, "
                "KHÔNG chép dòng trong Đơn. Không có giấy tờ này thì bỏ field.",
    },
    {
        "name": "NgoaiNgu_NgayHetHan",
        "desc": "Ngày hết hạn ghi trên chứng chỉ ngoại ngữ ('Có giá trị đến', 'Valid until', 'Expiry date'), "
                "dd/mm/yyyy. Chứng chỉ không in ngày hết hạn thì bỏ field, KHÔNG tự cộng 2 năm.",
    },

    # ---- NGHIỆP VỤ: văn bằng + chứng chỉ nghiệp vụ (chỉ để đối chiếu điều kiện) ----
    {
        "name": "VanBang_TrinhDo",
        "desc": "Trình độ của văn bằng tốt nghiệp: 'Cao đẳng', 'Đại học', 'Thạc sĩ' hoặc 'Tiến sĩ' (Bằng cử nhân/kỹ sư "
                "→ 'Đại học'). Không có văn bằng thì bỏ field.",
    },
    {
        "name": "VanBang_ChuyenNganh",
        "desc": "Ngành/chuyên ngành ghi trên văn bằng tốt nghiệp (vd 'Hướng dẫn du lịch', 'Quản trị dịch vụ du lịch và "
                "lữ hành', 'Ngôn ngữ Anh'), chép nguyên văn phần tiếng Việt.",
    },
    {
        "name": "ChungChi_Ten",
        "desc": "Tên chứng chỉ NGHIỆP VỤ hướng dẫn du lịch (vd 'Chứng chỉ nghiệp vụ hướng dẫn du lịch quốc tế'), "
                "nguyên văn. Chứng chỉ ngoại ngữ KHÔNG tính. Hồ sơ không có chứng chỉ nghiệp vụ thì bỏ field.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _n in ("NguoiDeNghi_NgaySinh", "NguoiDeNghi_NgayCap", "NgoaiNgu_NgayHetHan"):
    COMPACT_COMP_BY_NAME[_n] = "x-date"
COMPACT_COMP_BY_NAME["NguoiDeNghi_DiaChi"] = "x-select-area"

# ---- UI fields cho engine fill-liz.js — khớp (section, mat-label) ----
# Section là CỤM NGẮN: engine chấp nhận header chứa cụm này (hoặc ngược lại).
S_NOP = "Thông tin người nộp hồ sơ"
S_UQ = "Thông tin người ủy quyền"
S_THE = "thẻ hướng dẫn"

# Nhãn ô tích bật khối ủy quyền (liz-checkbox, trùng chữ với group-header của khối) — như 1.004605 cùng cổng.
UY_QUYEN_CHECKBOX = "Thông tin người ủy quyền"

LABEL_GIOI_TINH = "Giới tính"
LABEL_CHUYEN_MON = "Trình độ chuyên môn nghiệp vụ"
LABEL_NGOAI_NGU = "Trình độ ngoại ngữ (đối với người đề nghị cấp thẻ HDV du lịch quốc tế)"

# comp: liz-input (text/textarea) | liz-date (datepicker dd/mm/yyyy) | liz-select (mat-select overlay).
# Cố ý BỎ các ô cổng render `disabled` ở Phần II (Tên người nộp, CMND/Hộ chiếu/MST) — cổng tự điền từ tài khoản định
# danh. Phần I (cơ quan, lĩnh vực, thủ tục, dịch vụ công) cổng chọn sẵn; biên lai + tên điểm du lịch không điền.
UI_FIELDS: list[tuple[str, str, str, tuple[str, ...]]] = [
    (S_NOP, "Ngày sinh", "liz-date", ()),
    (S_NOP, "Ngày cấp", "liz-date", ()),
    (S_NOP, "Nơi cấp", "liz-input", ()),
    (S_NOP, "Số điện thoại", "liz-input", ("Điện thoại",)),
    (S_NOP, "Email", "liz-input", ("E-mail",)),
    (S_NOP, "Địa chỉ hành chính", "liz-select", ()),
    (S_NOP, "Địa chỉ chi tiết", "liz-input", ()),

    (S_UQ, "Tên người / Tên đơn vị ủy quyền", "liz-input", ("Tên người / Đơn vị ủy quyền",)),
    (S_UQ, "Ngày sinh", "liz-date", ()),
    (S_UQ, "CMND/Hộ chiếu/MST Doanh nghiệp", "liz-input", ()),
    (S_UQ, "Ngày cấp", "liz-date", ()),
    (S_UQ, "Nơi cấp", "liz-input", ()),
    (S_UQ, "Số điện thoại", "liz-input", ()),
    (S_UQ, "Email", "liz-input", ("E-mail",)),
    (S_UQ, "Địa chỉ hành chính", "liz-select", ()),
    (S_UQ, "Địa chỉ chi tiết", "liz-input", ()),

    (S_THE, LABEL_GIOI_TINH, "liz-select", ()),
    (S_THE, LABEL_CHUYEN_MON, "liz-input", ("Trình độ chuyên môn, nghiệp vụ", "Trình độ chuyên môn")),
    (S_THE, LABEL_NGOAI_NGU, "liz-input", ("Trình độ ngoại ngữ",)),
]

COMP_BY_UI = {(s, l): c for s, l, c, _a in UI_FIELDS}
ALIASES_BY_UI = {(s, l): list(a) for s, l, _c, a in UI_FIELDS}
