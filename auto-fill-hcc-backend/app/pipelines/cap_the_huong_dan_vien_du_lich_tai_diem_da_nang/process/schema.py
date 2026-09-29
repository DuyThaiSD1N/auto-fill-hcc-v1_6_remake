"""Compact schema cho "Thủ tục cấp thẻ hướng dẫn viên du lịch tại điểm" (mã 1.001440, QT-115) — Đà Nẵng.

Cổng Bộ VHTTDL `dichvucong.bvhttdl.gov.vn`, nộp về Sở VHTTDL TP Đà Nẵng — CÙNG giao diện với thẻ HDV nội
địa (1.004623): Angular Material bọc trong `liz-*`, DOM không có formcontrolname, ô trong eform chỉ có id
tự sinh; form và bảng thành phần hồ sơ NẰM CHUNG trang. LLM chỉ trả FACT nguồn; `mapper.enrich` suy tất
định ra ô UI theo (section = `.group-header`, name = `<mat-label>`) cho engine `fill-liz.js`.

Hồ sơ chỉ có MỘT người: người đề nghị cấp thẻ (Đơn Mẫu số 06 — Phụ lục I.9 Nghị quyết 66.18/2026/NQ-CP;
hồ sơ cũ có thể còn dùng Mẫu số 04). Phần II "Thông tin người nộp hồ sơ" là của tài khoản đăng nhập — chỉ
điền khi số CCCD tài khoản TRÙNG số CCCD của người đề nghị (xem mapper); Phần III "Thông tin ủy quyền"
không điền. Phần IV là nội dung đơn: giới tính, trình độ, ngoại ngữ, email, TÊN ĐIỂM DU LỊCH — ô cốt lõi
riêng của thẻ tại điểm.

⚑ Bản DOM dùng lập mapping bị Google Dịch ("Thành phần hồ sơ" → "Thành phần tin nhắn", header Phần IV →
"Người hướng dẫn thẻ cấp độ tại điểm"). Nhãn dưới đây là nhãn khôi phục, dùng lại đúng bộ nhãn đã chạy
thật trên trang thẻ nội địa cùng cổng. Section là CỤM NGẮN vì engine khớp section theo quan hệ chứa nhau.
"""

FIELDS: list[dict] = [
    # ---- NGƯỜI ĐỀ NGHỊ CẤP THẺ (CCCD → Đơn → Chứng chỉ nghiệp vụ → Văn bằng) ----
    {
        "name": "NguoiDeNghi_HoTen",
        "desc": "Họ và tên người đề nghị cấp thẻ — CCCD 'Họ và tên'; dòng 'Họ và tên (chữ in hoa)' của Đơn; "
                "'Cấp cho Ông/Bà' trên chứng chỉ; 'Cho' trên văn bằng. Viết có dấu, KHÔNG lấy bản tiếng Anh "
                "không dấu ('Upon').",
    },
    {
        "name": "NguoiDeNghi_NgaySinh",
        "desc": "Ngày sinh người đề nghị, dd/mm/yyyy. Nguồn: CCCD → Đơn → chứng chỉ ('Sinh ngày') → văn bằng "
                "(bản tiếng Anh ghi dạng '12 July 2004'). Chỉ trả khi đọc được ĐỦ ngày-tháng-năm.",
    },
    {
        "name": "NguoiDeNghi_GioiTinh",
        "desc": "Giới tính ở CCCD hoặc Đơn ('Giới tính: Nam'): 'Nam' hoặc 'Nữ'. Chỉ trả khi ghi/đánh dấu rõ; "
                "chữ 'Ông/Bà' in sẵn trên chứng chỉ KHÔNG phải giá trị.",
    },
    {
        "name": "NguoiDeNghi_SoDinhDanh",
        "desc": "Số định danh cá nhân/CMND của người đề nghị (CCCD, Đơn, dòng 'Thẻ CCCD/Hộ chiếu số' trên chứng "
                "chỉ). Chỉ chữ số, chép ĐỦ các chữ số đọc được; số bị che/mờ thì chép phần đọc được, KHÔNG bù.",
    },
    {"name": "NguoiDeNghi_NgayCap", "desc": "Ngày cấp CCCD/số định danh (mặt sau CCCD, hoặc dòng 'Ngày cấp' trên chứng chỉ nghiệp vụ), dd/mm/yyyy."},
    {"name": "NguoiDeNghi_NoiCap", "desc": "Nơi cấp CCCD (cơ quan cấp in trên CCCD, hoặc dòng 'Nơi cấp' trên chứng chỉ nghiệp vụ), nguyên văn."},
    {"name": "NguoiDeNghi_DienThoai", "desc": "Điện thoại ở Đơn, chỉ chữ số, chép đủ các chữ số đọc được."},
    {"name": "NguoiDeNghi_Email", "desc": "Email ở Đơn, nguyên văn. Phần tên hộp thư bị che thì bỏ field."},
    {
        "name": "NguoiDeNghi_DiaChi",
        "desc": "Nơi thường trú trên CCCD; không có CCCD thì 'Địa chỉ liên lạc' ở Đơn. Object {tinh,xa,diaChi}. "
                "KHÔNG lấy nơi lập đơn ('Thành phố Đà Nẵng, ngày…'), nơi chứng thực hay địa chỉ trường học.",
    },
    {
        "name": "NguoiDeNghi_TrinhDoChuyenMon",
        "desc": "Dòng 'Trình độ chuyên môn nghiệp vụ' ở Đơn, chép nguyên văn (vd 'Cử nhân', 'Cao đẳng').",
    },
    {
        "name": "NguoiDeNghi_TrinhDoNgoaiNgu",
        "desc": "Dòng 'Trình độ ngoại ngữ' ở Đơn (chỉ áp dụng thẻ quốc tế). Dòng chấm/để trống thì bỏ field.",
    },
    {
        "name": "NguoiDeNghi_TenDiemDuLich",
        "desc": "Tên điểm du lịch người đề nghị sẽ hướng dẫn — dòng tên điểm của Đơn, hoặc phần ngay sau 'tại "
                "điểm' trong tiêu đề/câu đề nghị ('…cấp thẻ hướng dẫn viên du lịch tại điểm <TÊN ĐIỂM> cho "
                "tôi'). Chỉ chép <TÊN ĐIỂM> (vd 'Khu du lịch Bà Nà Hills'). Dòng 'Hướng dẫn ghi' in sẵn cuối "
                "đơn KHÔNG phải giá trị — đơn không ghi tên điểm cụ thể thì bỏ field.",
    },
    {
        "name": "Don_LoaiThe",
        "desc": "Loại thẻ ghi ở TIÊU ĐỀ Đơn 'Cấp thẻ hướng dẫn viên du lịch …': 'tại điểm', 'nội địa' hoặc "
                "'quốc tế'. Không đọc ở dòng 'Hướng dẫn ghi'.",
    },
    {"name": "Don_CoQuanNhan", "desc": "Cơ quan ở dòng 'Kính gửi' của Đơn (vd 'Sở Văn hóa, Thể thao và Du lịch thành phố Đà Nẵng')."},

    # ---- CHỨNG CHỈ / VĂN BẰNG (không có ô riêng — chỉ bổ sung trình độ và đối chiếu loại thẻ) ----
    {
        "name": "ChungChi_Ten",
        "desc": "Tên chứng chỉ/giấy chứng nhận nghiệp vụ hướng dẫn du lịch trong hồ sơ, nguyên văn (vd 'Chứng "
                "chỉ nghiệp vụ hướng dẫn du lịch nội địa'). Không có thì bỏ field.",
    },
    {
        "name": "VanBang_TrinhDo",
        "desc": "Trình độ của văn bằng tốt nghiệp: 'Trung cấp', 'Cao đẳng', 'Đại học', 'Thạc sĩ' hoặc 'Tiến "
                "sĩ' (Bằng cử nhân/kỹ sư → 'Đại học'). Không có văn bằng thì bỏ field.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _n in ("NguoiDeNghi_NgaySinh", "NguoiDeNghi_NgayCap"):
    COMPACT_COMP_BY_NAME[_n] = "x-date"
COMPACT_COMP_BY_NAME["NguoiDeNghi_DiaChi"] = "x-select-area"

# ---- UI fields cho engine fill-liz.js — khớp (section, mat-label) ----
# Section là CỤM NGẮN: engine chấp nhận header chứa cụm này (hoặc ngược lại).
S_NOP = "Thông tin người nộp hồ sơ"
S_THE = "thẻ hướng dẫn"

# comp: liz-input (text/textarea) | liz-date (datepicker dd/mm/yyyy) | liz-select (mat-select overlay).
# Cố ý BỎ: Phần I (cơ quan, lĩnh vực, thủ tục — cổng chọn sẵn/disabled; dịch vụ công, CCCD tư vấn, VNPost,
# ghi chú — để trống); ô disabled của Phần II (Tên người nộp, CMND/Hộ chiếu/MST — cổng tự điền từ tài
# khoản); Phần III ủy quyền (ẩn); Phần V lệ phí (cổng tự tính); Phần VII cam kết (người nộp tự tích).
UI_FIELDS: list[tuple[str, str, str, tuple[str, ...]]] = [
    (S_NOP, "Ngày sinh", "liz-date", ()),
    (S_NOP, "Ngày cấp", "liz-date", ()),
    (S_NOP, "Nơi cấp", "liz-input", ()),
    (S_NOP, "Số điện thoại", "liz-input", ("Điện thoại",)),
    (S_NOP, "Email", "liz-input", ("E-mail",)),
    (S_NOP, "Địa chỉ hành chính", "liz-select", ()),
    (S_NOP, "Địa chỉ chi tiết", "liz-input", ("Địa chỉ",)),

    (S_THE, "Giới tính", "liz-select", ()),
    (S_THE, "Trình độ chuyên môn nghiệp vụ", "liz-input",
     ("Trình độ chuyên môn, nghiệp vụ", "Trình độ chuyên môn")),
    (S_THE, "Trình độ ngoại ngữ (đối với người đề nghị cấp thẻ HDV du lịch quốc tế)", "liz-input",
     ("Trình độ ngoại ngữ",)),
    (S_THE, "Email", "liz-input", ("E-mail",)),
    (S_THE, "Tên điểm du lịch đối với trường hợp cấp thẻ hướng dẫn viên du lịch tại điểm", "liz-input",
     ("Tên điểm du lịch",)),
]

COMP_BY_UI = {(s, l): c for s, l, c, _a in UI_FIELDS}
ALIASES_BY_UI = {(s, l): list(a) for s, l, _c, a in UI_FIELDS}
