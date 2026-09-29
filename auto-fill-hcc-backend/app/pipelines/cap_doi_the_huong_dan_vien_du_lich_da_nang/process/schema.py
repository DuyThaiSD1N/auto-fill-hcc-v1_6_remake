"""Compact schema cho "Thủ tục cấp đổi thẻ hướng dẫn viên du lịch quốc tế, thẻ hướng dẫn viên du lịch nội
địa" (mã 1.001432, QT-113) — Đà Nẵng.

Cổng Bộ VHTTDL `dichvucong.bvhttdl.gov.vn`, nộp về Sở VHTTDL TP Đà Nẵng — CÙNG giao diện với thẻ HDV nội
địa (1.004623) và thẻ tại điểm (1.001440): Angular Material bọc trong `liz-*`, DOM không có
formcontrolname, ô trong eform chỉ có id tự sinh; form và bảng thành phần hồ sơ NẰM CHUNG trang. LLM chỉ
trả FACT nguồn; `mapper.enrich` suy tất định ra ô UI theo (section = `.group-header`, name = `<mat-label>`)
cho engine `fill-liz.js`.

Hồ sơ chỉ có MỘT người: người đề nghị cấp đổi thẻ. Nguồn chính là Đơn đề nghị cấp đổi (Mẫu số 05 Phụ lục
II Thông tư 04/2024/TT-BVHTTDL) và thẻ HDV đã được cấp. Phần II "Thông tin người nộp hồ sơ" là của tài
khoản đăng nhập — chỉ điền khi số CCCD tài khoản TRÙNG số CCCD của người đề nghị (xem mapper); Phần III
"Thông tin ủy quyền" không điền. Phần IV "thẻ hướng dẫn viên đã được cấp" là nội dung Mẫu 05: giới tính,
email, số thẻ, ngày cấp, nơi cấp, loại thẻ đã được cấp, lý do cấp đổi.

⚑ Bản DOM dùng lập mapping bị Google Dịch (header Phần IV → "Thay đổi thẻ hướng dẫn theo lịch", "Số thẻ"
→ "Số", "Nơi cấp" → "mà"…). Nhãn dưới đây là nhãn khôi phục theo Mẫu 05, kèm `aliases` là các cách cổng
có thể in (engine thử `name` trước rồi tới từng alias, vẫn trong đúng section). Section là CỤM NGẮN vì
engine khớp section theo quan hệ chứa nhau.
"""

FIELDS: list[dict] = [
    # ---- NGƯỜI ĐỀ NGHỊ (CCCD → Đơn → thẻ HDV cũ → chứng chỉ/văn bằng nếu có) ----
    {
        "name": "NguoiDeNghi_HoTen",
        "desc": "Họ và tên người đề nghị cấp đổi thẻ — CCCD 'Họ và tên'; dòng 'Họ và tên (chữ in hoa)' của "
                "Đơn; họ tên in trên thẻ HDV cũ. Viết có dấu, KHÔNG lấy bản tiếng Anh không dấu.",
    },
    {
        "name": "NguoiDeNghi_NgaySinh",
        "desc": "Ngày sinh người đề nghị, dd/mm/yyyy. Nguồn: CCCD → Đơn → thẻ HDV cũ/chứng chỉ ('Sinh ngày'). "
                "Chỉ trả khi đọc được ĐỦ ngày-tháng-năm.",
    },
    {
        "name": "NguoiDeNghi_GioiTinh",
        "desc": "Giới tính ở CCCD hoặc Đơn ('Giới tính: Nam'): 'Nam' hoặc 'Nữ'. Chỉ trả khi ghi/đánh dấu rõ; "
                "chữ 'Ông/Bà' in sẵn KHÔNG phải giá trị.",
    },
    {
        "name": "NguoiDeNghi_SoDinhDanh",
        "desc": "Số định danh cá nhân/CMND của người đề nghị (CCCD, dòng 'Số định danh cá nhân/Chứng minh nhân "
                "dân' của Đơn). Chỉ chữ số, chép ĐỦ các chữ số đọc được; số bị che/mờ thì chép phần đọc được, "
                "KHÔNG bù. KHÔNG lấy số thẻ HDV hay số hiệu chứng chỉ.",
    },
    {"name": "NguoiDeNghi_NgayCap", "desc": "Ngày cấp CCCD/số định danh (mặt sau CCCD, hoặc dòng 'Ngày cấp' cạnh số CCCD trên chứng chỉ), dd/mm/yyyy. KHÔNG lấy ngày cấp thẻ HDV."},
    {"name": "NguoiDeNghi_NoiCap", "desc": "Nơi cấp CCCD (cơ quan cấp in trên CCCD, hoặc dòng 'Nơi cấp' cạnh số CCCD trên chứng chỉ), nguyên văn. KHÔNG lấy nơi cấp thẻ HDV."},
    {"name": "NguoiDeNghi_DienThoai", "desc": "Điện thoại ở Đơn, chỉ chữ số, chép đủ các chữ số đọc được."},
    {"name": "NguoiDeNghi_Email", "desc": "Email ở Đơn, nguyên văn. Phần tên hộp thư bị che thì bỏ field."},
    {
        "name": "NguoiDeNghi_DiaChi",
        "desc": "Nơi thường trú trên CCCD; không có CCCD thì 'Địa chỉ liên lạc' ở Đơn. Object {tinh,xa,diaChi}. "
                "KHÔNG lấy nơi lập đơn ('Thành phố Đà Nẵng, ngày…'), nơi chứng thực hay địa chỉ trường học.",
    },

    # ---- THẺ HDV ĐÃ ĐƯỢC CẤP (thẻ cũ → mục 'Đã được cấp thẻ hướng dẫn viên du lịch' của Đơn Mẫu 05) ----
    {
        "name": "TheCu_SoThe",
        "desc": "Số thẻ hướng dẫn viên du lịch ĐÃ ĐƯỢC CẤP — dòng 'Số/No.' in trên thẻ HDV cũ (thường 9 chữ "
                "số); không có ảnh thẻ thì dòng '+ Số thẻ' trong mục 'Đã được cấp thẻ hướng dẫn viên du lịch' "
                "của Đơn Mẫu 05. KHÔNG lấy 'Số hiệu chứng chỉ', 'Số vào sổ', số CCCD. Chép nguyên văn.",
    },
    {
        "name": "TheCu_NgayCap",
        "desc": "Ngày cấp thẻ HDV đã được cấp, dd/mm/yyyy — dòng '- Ngày cấp' trong mục 'Đã được cấp thẻ' của "
                "Đơn Mẫu 05, hoặc ngày cấp in trên thẻ cũ. KHÔNG lấy ngày HẾT HẠN của thẻ, ngày cấp CCCD, ngày "
                "cấp chứng chỉ hay ngày lập đơn.",
    },
    {
        "name": "TheCu_NoiCap",
        "desc": "Nơi cấp thẻ HDV đã được cấp — dòng '- Nơi cấp' trong mục 'Đã được cấp thẻ' của Đơn Mẫu 05, "
                "hoặc cơ quan cấp in trên thẻ cũ (vd 'Sở Du lịch thành phố Đà Nẵng', 'Tổng cục Du lịch'). "
                "Chép nguyên văn. KHÔNG lấy nơi cấp CCCD.",
    },
    {
        "name": "TheCu_Loai",
        "desc": "Loại thẻ HDV ĐÃ ĐƯỢC CẤP: 'nội địa', 'quốc tế' hoặc 'tại điểm' — ô được đánh dấu ở dòng '+ "
                "Loại: □ Nội địa □ Quốc tế □ Tại điểm' của Đơn Mẫu 05, hoặc chữ in trên thẻ cũ ('HƯỚNG DẪN "
                "VIÊN DU LỊCH NỘI ĐỊA', 'INTERNATIONAL TOUR GUIDE', 'DOMESTIC TOUR GUIDE'…). Ô '□' rỗng là "
                "KHÔNG chọn; không thấy ô nào được đánh dấu thì bỏ field. KHÔNG suy từ tên chứng chỉ nghiệp vụ.",
    },
    {
        "name": "Don_LyDo",
        "desc": "Dòng 'Lý do đề nghị cấp đổi/cấp lại thẻ' của Đơn Mẫu 05, chép nguyên văn phần người đề nghị "
                "ghi (vd 'Thẻ hết hạn sử dụng'). Dòng chấm để trống thì bỏ field.",
    },
    {
        "name": "Don_LoaiDeNghi",
        "desc": "Đơn đề nghị gì, đọc ở TIÊU ĐỀ và câu đề nghị cuối đơn: 'cấp đổi' (Mẫu 05, cấp đổi thẻ), "
                "'cấp lại' (Mẫu 05 nhưng ghi rõ cấp lại, bị mất/hư hỏng) hoặc 'cấp mới' (đơn 'Cấp thẻ hướng dẫn "
                "viên du lịch nội địa/quốc tế/tại điểm' — Mẫu 04/06, không có chữ đổi/lại). Tiêu đề in sẵn "
                "'cấp đổi/cấp lại' mà không gạch bỏ bên nào → 'cấp đổi'.",
    },
    {
        "name": "Don_LoaiTheDeNghi",
        "desc": "Chỉ với đơn CẤP MỚI (Mẫu 04/06): loại thẻ ghi ở tiêu đề 'Cấp thẻ hướng dẫn viên du lịch …' — "
                "'nội địa', 'quốc tế' hoặc 'tại điểm'. Đơn cấp đổi/cấp lại thì bỏ field.",
    },
    {"name": "Don_CoQuanNhan", "desc": "Cơ quan ở dòng 'Kính gửi' của Đơn (vd 'Sở Văn hóa, Thể thao và Du lịch thành phố Đà Nẵng')."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _n in ("NguoiDeNghi_NgaySinh", "NguoiDeNghi_NgayCap", "TheCu_NgayCap"):
    COMPACT_COMP_BY_NAME[_n] = "x-date"
COMPACT_COMP_BY_NAME["NguoiDeNghi_DiaChi"] = "x-select-area"

# ---- UI fields cho engine fill-liz.js — khớp (section, mat-label) ----
# Section là CỤM NGẮN: engine chấp nhận header chứa cụm này (hoặc ngược lại).
S_NOP = "Thông tin người nộp hồ sơ"
S_THE = "thẻ hướng dẫn"

LABEL_LOAI_THE = "Đã được cấp thẻ hướng dẫn viên du lịch loại"
LABEL_LY_DO = "Lý do đề nghị cấp đổi/cấp lại thẻ"
# Nhãn từng ô trong nhóm checkbox "loại thẻ" (DOM dịch sai "Họ địa chỉ"/"Quốc tế"/"Tại" — nhãn gốc theo Mẫu 05).
LOAI_THE_OPTIONS = {"nội địa": "Nội địa", "quốc tế": "Quốc tế", "tại điểm": "Tại điểm"}

# comp: liz-input (text/textarea) | liz-date (datepicker dd/mm/yyyy) | liz-select (mat-select overlay) |
# liz-checkbox (ô tích; kèm `option` khi là nhóm nhiều ô).
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

    (S_THE, LABEL_LOAI_THE, "liz-checkbox", ("Đã được cấp thẻ hướng dẫn viên du lịch",)),
    (S_THE, "Giới tính", "liz-select", ()),
    (S_THE, "Email", "liz-input", ("E-mail",)),
    (S_THE, "Số thẻ", "liz-input", ("Số thẻ hướng dẫn viên du lịch", "Số thẻ HDV", "Số")),
    (S_THE, "Ngày cấp", "liz-date",
     ("Ngày cấp thẻ", "Ngày cấp thẻ HDV", "Ngày tháng năm cấp", "Ngày tháng cấp", "Ngày tháng")),
    (S_THE, "Nơi cấp", "liz-input", ("Nơi cấp thẻ", "Nơi cấp thẻ HDV", "Cơ quan cấp", "Cơ quan cấp thẻ", "Cấp tại")),
    (S_THE, LABEL_LY_DO, "liz-input",
     ("Lý do đề nghị cấp đổi, cấp lại thẻ", "Lý do đề nghị cấp đổi thẻ", "Lý do")),
]

COMP_BY_UI = {(s, l): c for s, l, c, _a in UI_FIELDS}
ALIASES_BY_UI = {(s, l): list(a) for s, l, _c, a in UI_FIELDS}

# Ô ngày cấp / nơi cấp thẻ cũ: nhãn trên cổng chưa xác nhận được (DOM mapping bị dịch thành "Ngày tháng",
# "mà") → engine rơi về vị trí: ô ngày / ô chữ ĐẦU TIÊN ngay sau ô Số thẻ, cùng section (thứ tự DOM
# mat-input-57 Số thẻ → 58 ngày → 59 nơi cấp).
_SO_THE_LABELS = ["Số thẻ", *ALIASES_BY_UI[(S_THE, "Số thẻ")]]
AFTER_BY_UI = {(S_THE, "Ngày cấp"): _SO_THE_LABELS, (S_THE, "Nơi cấp"): _SO_THE_LABELS}
