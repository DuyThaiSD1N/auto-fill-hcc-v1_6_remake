"""Compact schema cho "Thủ tục tổ chức biểu diễn nghệ thuật" (1.009397, NĐ 144/2020/NĐ-CP).

Cổng Bộ VHTTDL `dichvucong.bvhttdl.gov.vn` (nộp về Sở VHTTDL tỉnh) — Angular Material bọc trong `liz-*`, DOM
không có formcontrolname. Form và bảng thành phần hồ sơ NẰM CHUNG trang `/nop-ho-so`. LLM chỉ trả FACT nguồn;
`mapper.enrich` suy tất định ra ô UI theo (section = `.group-header`, name = `<mat-label>`) cho engine
`fill-liz.js`.

Hồ sơ của MỘT tổ chức đề nghị (công ty, đơn vị nghệ thuật): Văn bản đề nghị Mẫu số 02 + Kịch bản/danh mục tác
phẩm; có thể kèm Giấy chứng nhận đăng ký doanh nghiệp. Trang có:
  - "Thông tin người nộp hồ sơ" — cổng đổ sẵn từ tài khoản định danh, KHÔNG điền;
  - "Thông tin người ủy quyền" — khối ẩn, hiện khi tích ô cùng tên: tổ chức đề nghị (cá nhân đi nộp thay);
  - khối đề nghị tổ chức biểu diễn — nội dung chính của Văn bản đề nghị;
  - "Thông tin biên lai" — nhập một ô thì phải đủ 5 ô, hồ sơ không có SĐT/email → không điền.

⚑ CHƯA CÓ DOM GỐC: nhãn lấy theo bản mapping (cột formcontrolname chỉ có id tự sinh). Tiêu đề khối đề nghị chưa
đối chiếu được nên dùng CỤM NGẮN "tổ chức biểu diễn nghệ thuật" (engine khớp section theo quan hệ chứa nhau).
"""

_VB = "Văn bản đề nghị tổ chức biểu diễn nghệ thuật (Mẫu số 02)"
_KB = "Kịch bản / nội dung chi tiết chương trình"
_GCN = "Giấy chứng nhận đăng ký doanh nghiệp/kinh doanh"

FIELDS: list[dict] = [
    # ---- TỔ CHỨC ĐỀ NGHỊ (bên ủy quyền) ----
    {
        "name": "DonVi_Ten",
        "desc": f"Tên tổ chức đề nghị: 'Tên công ty viết bằng tiếng Việt' trên {_GCN}; không có GCN thì dòng tên "
                f"cơ quan/tổ chức ở góc trái trên {_VB} (GHÉP các dòng của tên), hoặc tên in trên con dấu. Chép "
                "nguyên văn.",
    },
    {
        "name": "DonVi_MaSo",
        "desc": f"Mã số doanh nghiệp trên {_GCN}. Chép đúng chữ số đọc được, KHÔNG bù số bị che/thiếu.",
    },
    {
        "name": "DonVi_MaSoConDau",
        "desc": "Mã số in trên CON DẤU tròn của tổ chức (cụm 'M.S.D.N: …' / 'MST: …' chạy vòng quanh dấu) đóng "
                f"trên {_VB} hoặc {_KB}. Chỉ chữ số đọc được, KHÔNG bù.",
    },
    {"name": "DonVi_NgayCap", "desc": f"Ngày 'Đăng ký lần đầu' trên {_GCN}, dd/mm/yyyy."},
    {
        "name": "DonVi_NoiCap",
        "desc": f"Cơ quan cấp {_GCN} — tiêu đề góc trái thường in HAI dòng (cơ quan cấp trên, rồi phòng): GHÉP "
                "thành 'Phòng Đăng ký kinh doanh - Sở … tỉnh …'.",
    },
    {
        "name": "DonVi_DienThoai",
        "desc": f"Điện thoại của tổ chức ({_GCN} hoặc dòng 'Điện thoại' của {_VB}). Chỉ chữ số; KHÔNG lấy số của "
                "người chịu trách nhiệm.",
    },
    {"name": "DonVi_Email", "desc": f"Email của tổ chức ({_GCN} hoặc {_VB}), nếu có."},
    {
        "name": "DonVi_TruSo",
        "desc": f"Địa chỉ trụ sở chính trên {_GCN}, object {{tinh,xa,chiTietDuoiXa}}: chiTietDuoiXa = số nhà/"
                "đường/thôn (KHÔNG kèm xã/tỉnh). KHÔNG lấy địa điểm biểu diễn, KHÔNG lấy địa danh trên con dấu.",
    },

    # ---- VĂN BẢN ĐỀ NGHỊ (Mẫu số 02) ----
    {"name": "DeNghi_KinhGui", "desc": f"Cơ quan ở dòng 'Kính gửi' của {_VB} (vd 'Sở Văn hóa, Thể thao và Du lịch …')."},
    {
        "name": "DeNghi_TenChuongTrinh",
        "desc": f"Mục '1. Tên chương trình biểu diễn nghệ thuật' của {_VB}: chép NGUYÊN VĂN phần sau dấu hai chấm, "
                "kèm dòng '(Thời lượng: …)' ngay dưới nếu có.",
    },
    {
        "name": "DeNghi_ThoiGian",
        "desc": f"Mục '2. Thời gian tổ chức' của {_VB}, chép NGUYÊN VĂN phần sau dấu hai chấm (giữ cả giờ và mọi ngày, "
                "vd 'Từ 19h30 – 21h00 ngày 05, 06 tháng 12 năm 2026').",
    },
    {"name": "DeNghi_DiaDiem", "desc": f"Mục '3. Địa điểm tổ chức' của {_VB}, chép NGUYÊN VĂN."},
    {
        "name": "DeNghi_DuyetThoiGian",
        "desc": f"Mục '4. Dự kiến thời gian, địa điểm tổ chức duyệt chương trình' của {_VB}: CHỈ phần THỜI GIAN "
                "(trước chữ 'tại'), chép nguyên văn (vd 'Lúc 14h00 ngày 05/12/2026').",
    },
    {
        "name": "DeNghi_DuyetDiaDiem",
        "desc": f"Mục 4 của {_VB}: CHỈ phần ĐỊA ĐIỂM duyệt chương trình (sau chữ 'tại'), chép nguyên văn.",
    },
    {
        "name": "DeNghi_NguoiChiuTrachNhiem",
        "desc": f"Mục '5. Người chịu trách nhiệm chính nội dung' của {_VB}, chép NGUYÊN VĂN phần sau dấu hai chấm "
                "(kể cả chức vụ).",
    },
    {
        "name": "DeNghi_LienKet",
        "desc": f"Dòng 'Cơ quan, tổ chức, cá nhân liên kết' trong mục 6 của {_VB}, chép nguyên văn (kể cả '(Không có)').",
    },
    {
        "name": "DeNghi_TonVinh",
        "desc": f"Dòng 'Việc tôn vinh, vinh danh danh hiệu của cá nhân, tổ chức' trong mục 6 của {_VB}, chép nguyên "
                "văn (kể cả '(Không có)').",
    },
    {
        "name": "DeNghi_TaiLieuKemTheo",
        "desc": f"Dòng 'Tài liệu kèm theo' trong mục 6 của {_VB}: MẢNG, phần tử đầu là phần sau dấu hai chấm, các "
                "phần tử sau là từng dòng gạch đầu dòng nêu GIẤY TỜ ngay dưới (vd giấy tiếp nhận/chấp thuận địa điểm) "
                "cho tới trước câu 'Chúng tôi cam kết…'. Chép nguyên văn.",
    },

    # ---- KỊCH BẢN (bù khi văn bản đề nghị thiếu; đối chiếu lệch) ----
    {"name": "KichBan_TenChuongTrinh", "desc": f"Tên chương trình/sự kiện ở tiêu đề {_KB}, chép nguyên văn."},
    {"name": "KichBan_ThoiGian", "desc": f"Dòng 'Thời gian' ở đầu {_KB}, chép nguyên văn."},
    {"name": "KichBan_DiaDiem", "desc": f"Dòng 'Địa điểm' ở đầu {_KB}, chép nguyên văn."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["DonVi_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["DonVi_TruSo"] = "x-select-area"

# ---- UI fields cho engine fill-liz.js — khớp (section, mat-label) ----
S_UQ = "Thông tin người ủy quyền"
S_DN = "tổ chức biểu diễn nghệ thuật"

# Nhãn ô tích bật khối ủy quyền (liz-checkbox, trùng chữ với group-header của khối).
UY_QUYEN_CHECKBOX = "Thông tin người ủy quyền"

LABEL_TEN_CT = "Tên chương trình biểu diễn nghệ thuật (tên nước ngoài nếu có)"
LABEL_DIA_DIEM = "Địa điểm tổ chức"
LABEL_DUYET_THOI_GIAN = "Dự kiến thời gian tổ chức duyệt chương trình"
LABEL_DUYET_DIA_DIEM = "Dự kiến địa điểm tổ chức duyệt chương trình"
LABEL_NGUOI_CHIU_TN = "Người chịu trách nhiệm chính nội dung"
LABEL_THOI_GIAN = "Thời gian tổ chức"
LABEL_LIEN_KET = "Cơ quan, tổ chức, cá nhân liên kết (nếu có)"
LABEL_TON_VINH = "Việc tôn vinh, vinh danh danh hiệu của cá nhân, tổ chức (nếu có)"
LABEL_TAI_LIEU = "Tài liệu kèm theo"

# comp: liz-input (text/textarea) | liz-date (datepicker dd/mm/yyyy) | liz-select (mat-select overlay).
# Bỏ "Ngày sinh" của khối ủy quyền: bên ủy quyền là tổ chức.
UI_FIELDS: list[tuple[str, str, str, tuple[str, ...]]] = [
    (S_UQ, "Tên người / Tên đơn vị ủy quyền", "liz-input", ()),
    (S_UQ, "CMND/Hộ chiếu/MST Doanh nghiệp", "liz-input", ()),
    (S_UQ, "Ngày cấp", "liz-date", ()),
    (S_UQ, "Nơi cấp", "liz-input", ()),
    (S_UQ, "Số điện thoại", "liz-input", ()),
    (S_UQ, "Email", "liz-input", ()),
    (S_UQ, "Địa chỉ hành chính", "liz-select", ()),
    (S_UQ, "Địa chỉ chi tiết", "liz-input", ()),

    (S_DN, LABEL_TEN_CT, "liz-input", ("Tên chương trình biểu diễn nghệ thuật",)),
    (S_DN, LABEL_DIA_DIEM, "liz-input", ()),
    (S_DN, LABEL_DUYET_THOI_GIAN, "liz-date", ()),
    (S_DN, LABEL_DUYET_DIA_DIEM, "liz-input", ()),
    (S_DN, LABEL_NGUOI_CHIU_TN, "liz-input", ()),
    (S_DN, LABEL_THOI_GIAN, "liz-date", ()),
    (S_DN, LABEL_LIEN_KET, "liz-input", ("Cơ quan, tổ chức, cá nhân liên kết",)),
    (S_DN, LABEL_TON_VINH, "liz-input", ("Việc tôn vinh, vinh danh danh hiệu của cá nhân, tổ chức",)),
    (S_DN, LABEL_TAI_LIEU, "liz-input", ()),
]

COMP_BY_UI = {(s, l): c for s, l, c, _a in UI_FIELDS}
ALIASES_BY_UI = {(s, l): list(a) for s, l, _c, a in UI_FIELDS}
