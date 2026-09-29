"""Compact schema cho "Thủ tục cấp lại thẻ hướng dẫn viên du lịch" (mã 1.004614, QT-122) — Đà Nẵng.

Cổng Bộ VHTTDL `dichvucong.bvhttdl.gov.vn`, nộp về Sở VHTTDL TP Đà Nẵng — CÙNG giao diện với cấp đổi
(1.001432), thẻ nội địa (1.004623) và thẻ tại điểm (1.001440): Angular Material bọc trong `liz-*`, DOM
không có formcontrolname, ô trong eform chỉ có id tự sinh; form và bảng thành phần hồ sơ NẰM CHUNG trang.
LLM chỉ trả FACT nguồn; `mapper.enrich` suy tất định ra ô UI theo (section = `.group-header`, name =
`<mat-label>`) cho engine `fill-liz.js`.

Hồ sơ chỉ có MỘT người: người đề nghị cấp lại thẻ. Nguồn chính là Đơn đề nghị cấp lại (Mẫu số 05 Phụ lục
II Thông tư 04/2024/TT-BVHTTDL); thẻ cũ thường đã MẤT nên số thẻ / nơi cấp / ngày cấp / loại thẻ đã được
cấp chủ yếu đọc ở mục "Đã được cấp thẻ" của Đơn. Nhân thân theo thứ tự CCCD → Đơn → chứng chỉ nghiệp vụ →
văn bằng. Phần "Thông tin người nộp hồ sơ" là của tài khoản đăng nhập — chỉ điền khi số CCCD tài khoản TRÙNG
số CCCD của người đề nghị (xem mapper); khối "Thông tin ủy quyền" không điền. Khối "Thông tin cấp lại thẻ
hướng dẫn viên du lịch" là nội dung Mẫu 05: giới tính, email, loại thẻ đã được cấp, số thẻ, ngày cấp, nơi
cấp, lý do cấp lại.

⚑ Bản DOM dùng lập mapping bị Google Dịch (header → "Thẻ hướng dẫn cấp lại theo lịch trình", "Số thẻ" →
"Số", "Ngày cấp" → "Ngày tháng", "Nơi cấp" → "mà", ô loại thẻ → "Họ địa chỉ"/"Quốc tế"/"Tại"). Nhãn dưới
đây là nhãn khôi phục theo Mẫu 05, kèm `aliases` là các cách cổng có thể in (engine thử `name` trước rồi
tới từng alias, vẫn trong đúng section). Section là CỤM NGẮN vì engine khớp section theo quan hệ chứa nhau.
"""

FIELDS: list[dict] = [
    # ---- NGƯỜI ĐỀ NGHỊ (CCCD → Đơn → chứng chỉ nghiệp vụ → văn bằng → thẻ HDV cũ) ----
    {
        "name": "NguoiDeNghi_HoTen",
        "desc": "Họ và tên người đề nghị cấp lại thẻ — CCCD 'Họ và tên'; dòng 'Họ và tên (chữ in hoa)' của Đơn; "
                "'Cấp cho Ông/Bà' của chứng chỉ; 'Cho: Ông/Bà …' của văn bằng. Viết có dấu, KHÔNG lấy bản tiếng "
                "Anh không dấu ('Mr. LE VAN …').",
    },
    {
        "name": "NguoiDeNghi_NgaySinh",
        "desc": "Ngày sinh người đề nghị, dd/mm/yyyy. Nguồn: CCCD → Đơn → chứng chỉ ('Sinh ngày') → văn bằng. "
                "Chỉ trả khi đọc được ĐỦ ngày-tháng-năm.",
    },
    {
        "name": "NguoiDeNghi_GioiTinh",
        "desc": "Giới tính ở CCCD hoặc Đơn ('Giới tính: Nam'): 'Nam' hoặc 'Nữ'. Không có hai nguồn đó thì danh "
                "xưng ĐÃ ĐIỀN trên văn bằng ('Ông'/'Mr.' → Nam, 'Bà'/'Ms.' → Nữ). Chữ 'Ông/Bà' in sẵn trên "
                "chứng chỉ KHÔNG phải giá trị.",
    },
    {
        "name": "NguoiDeNghi_SoDinhDanh",
        "desc": "Số định danh cá nhân/CMND của người đề nghị (CCCD; dòng 'Số định danh cá nhân/Chứng minh nhân "
                "dân' của Đơn; dòng 'Giấy CMND / Thẻ CCCD / Hộ chiếu số' của chứng chỉ). Chỉ chữ số, chép ĐỦ "
                "các chữ số đọc được; số bị che/mờ thì chép phần đọc được, KHÔNG bù. KHÔNG lấy số thẻ HDV, số "
                "hiệu chứng chỉ, số hiệu văn bằng.",
    },
    {
        "name": "NguoiDeNghi_NgayCap",
        "desc": "Ngày cấp CCCD/số định danh (mặt sau CCCD, hoặc dòng 'Ngày cấp' cạnh số CCCD trên chứng chỉ), "
                "dd/mm/yyyy. KHÔNG lấy ngày cấp thẻ HDV, ngày cấp chứng chỉ hay ngày ký văn bằng.",
    },
    {
        "name": "NguoiDeNghi_NoiCap",
        "desc": "Nơi cấp CCCD (cơ quan cấp in trên CCCD, hoặc dòng 'Nơi cấp' cạnh số CCCD trên chứng chỉ), nguyên "
                "văn. KHÔNG lấy nơi cấp thẻ HDV.",
    },
    {"name": "NguoiDeNghi_DienThoai", "desc": "Điện thoại ở Đơn, chỉ chữ số, chép đủ các chữ số đọc được."},
    {"name": "NguoiDeNghi_Email", "desc": "Email ở Đơn, nguyên văn. Phần tên hộp thư bị che thì bỏ field."},
    {
        "name": "NguoiDeNghi_DiaChi",
        "desc": "Nơi thường trú trên CCCD; không có CCCD thì 'Địa chỉ liên lạc' ở Đơn. Object {tinh,xa,diaChi}. "
                "KHÔNG lấy nơi lập đơn ('Thành phố Đà Nẵng, ngày…'), nơi chứng thực hay địa chỉ trường học.",
    },

    # ---- THẺ HDV ĐÃ ĐƯỢC CẤP (mục 'Đã được cấp thẻ hướng dẫn viên du lịch' của Đơn Mẫu 05 → thẻ cũ) ----
    {
        "name": "TheCu_SoThe",
        "desc": "Số thẻ hướng dẫn viên du lịch ĐÃ ĐƯỢC CẤP — dòng '+ Số thẻ' trong mục 'Đã được cấp thẻ hướng dẫn "
                "viên du lịch' của Đơn Mẫu 05; hoặc dòng 'Số/No.' in trên thẻ HDV cũ (nếu có ảnh thẻ, thường 9 "
                "chữ số). KHÔNG lấy 'Số hiệu chứng chỉ', 'Số vào sổ', số hiệu văn bằng, số CCCD. Chép nguyên văn.",
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
                "KHÔNG chọn; không thấy ô nào được đánh dấu thì bỏ field. KHÔNG suy từ tên chứng chỉ nghiệp vụ "
                "hay tiêu đề đơn cấp mới.",
    },
    {
        "name": "Don_LyDo",
        "desc": "Dòng 'Lý do đề nghị cấp đổi/cấp lại thẻ' của Đơn Mẫu 05, chép nguyên văn phần người đề nghị "
                "ghi (vd 'Thẻ bị mất', 'Thẻ bị hư hỏng', 'Thay đổi thông tin trên thẻ'). Dòng chấm để trống thì "
                "bỏ field.",
    },
    {
        "name": "Don_LoaiDeNghi",
        "desc": "Đơn đề nghị gì, đọc ở TIÊU ĐỀ và câu đề nghị cuối đơn: 'cấp lại' (Mẫu 05 ghi cấp lại, thẻ bị "
                "mất/hư hỏng/thay đổi thông tin), 'cấp đổi' (Mẫu 05 đã GẠCH chữ 'cấp lại', chỉ còn cấp đổi) "
                "hoặc 'cấp mới' (đơn 'Cấp thẻ hướng dẫn viên du lịch nội địa/quốc tế/tại điểm' — Mẫu 04/06, "
                "không có chữ đổi/lại). Tiêu đề in sẵn 'cấp đổi/cấp lại' mà không gạch bỏ bên nào → 'cấp lại'.",
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
# Section là CỤM NGẮN: engine chấp nhận header chứa cụm này (hoặc ngược lại). Header khối cấp lại (khôi
# phục từ bản dịch "Thẻ hướng dẫn cấp lại theo lịch trình") chứa "thẻ hướng dẫn".
S_NOP = "Thông tin người nộp hồ sơ"
S_THE = "thẻ hướng dẫn"

LABEL_LOAI_THE = "Đã được cấp thẻ hướng dẫn viên du lịch loại"
LABEL_LY_DO = "Lý do đề nghị cấp đổi/cấp lại thẻ"
# Nhãn từng ô trong nhóm checkbox "loại thẻ" (DOM dịch sai "Họ địa chỉ"/"Quốc tế"/"Tại" — nhãn gốc theo Mẫu 05).
LOAI_THE_OPTIONS = {"nội địa": "Nội địa", "quốc tế": "Quốc tế", "tại điểm": "Tại điểm"}

# comp: liz-input (text/textarea) | liz-date (datepicker dd/mm/yyyy) | liz-select (mat-select overlay) |
# liz-checkbox (ô tích; kèm `option` khi là nhóm nhiều ô).
# Cố ý BỎ: Phần 0 (cơ quan, lĩnh vực, thủ tục — cổng chọn sẵn/disabled; dịch vụ công, CCCD tư vấn, VNPost,
# ghi chú — để trống); ô disabled của khối người nộp (Tên người nộp, CMND/Hộ chiếu/MST — cổng tự điền từ tài
# khoản); khối ủy quyền (ẩn tới khi tick); Phần IV lệ phí (cổng tự tính); Phần VI cam kết (người nộp tự tích).
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
     ("Lý do đề nghị cấp lại thẻ", "Lý do đề nghị cấp đổi, cấp lại thẻ", "Lý do đề nghị cấp lại", "Lý do")),
]

COMP_BY_UI = {(s, l): c for s, l, c, _a in UI_FIELDS}
ALIASES_BY_UI = {(s, l): list(a) for s, l, _c, a in UI_FIELDS}

# Ô ngày cấp / nơi cấp thẻ cũ: nhãn trên cổng chưa xác nhận được (DOM mapping bị dịch thành "Ngày tháng",
# "mà") → engine rơi về vị trí: ô ngày / ô chữ ĐẦU TIÊN ngay sau ô Số thẻ, cùng section (thứ tự DOM
# mat-input-56 Số → 57 ngày → 58 nơi cấp).
_SO_THE_LABELS = ["Số thẻ", *ALIASES_BY_UI[(S_THE, "Số thẻ")]]
AFTER_BY_UI = {(S_THE, "Ngày cấp"): _SO_THE_LABELS, (S_THE, "Nơi cấp"): _SO_THE_LABELS}
