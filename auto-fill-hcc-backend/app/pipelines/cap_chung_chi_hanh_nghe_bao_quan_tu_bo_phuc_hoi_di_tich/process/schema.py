"""Compact schema cho "Thủ tục cấp Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích" (1.001822, QT-09).

Cổng Bộ VHTTDL `dichvucong.bvhttdl.gov.vn` (nộp về Sở VHTTDL tỉnh) — Angular Material bọc trong `liz-*`, DOM
không có formcontrolname. Form và bảng thành phần hồ sơ NẰM CHUNG trang `/nop-ho-so`. LLM chỉ trả FACT nguồn;
`mapper.enrich` suy tất định ra ô UI theo (section = `.group-header`, name = `<mat-label>`) cho engine
`fill-liz.js`.

Hồ sơ chỉ có MỘT người: người đề nghị cấp chứng chỉ (Đơn Mẫu số 51, NĐ 308/2025/NĐ-CP). Trang có:
  - "Thông tin người nộp hồ sơ" — của tài khoản đăng nhập (Tên, CMND cổng khoá theo tài khoản);
  - "Thông tin người ủy quyền" — khối ẩn, hiện khi tích ô cùng tên (nộp thay: người ủy quyền = chủ hồ sơ);
  - Đơn Mẫu 51 — nội dung chính của thủ tục;
  - HAI biểu mẫu của thủ tục khác vẫn hiện trên trang (đơn giám định cổ vật, đơn cấp lại GCN/CCHN) với nhãn
    TRÙNG Mẫu 51 ("Họ và tên (viết bằng chữ in hoa)", "Số định danh…", "Ngày tháng năm sinh", "Địa chỉ liên
    hệ") — KHÔNG điền, nên section của Mẫu 51 là bắt buộc;
  - "Thông tin biên lai" — nhập một ô thì phải đủ 5 ô, hồ sơ không có SĐT/email → không điền.

⚑ CHƯA CÓ DOM GỐC: nhãn lấy theo bản mapping QT-09 (cột formcontrolname chỉ có id tự sinh). Tiêu đề khối
Mẫu 51 chưa đối chiếu được nên dùng CỤM NGẮN "chứng chỉ hành nghề bảo quản" (engine khớp section theo quan hệ
chứa nhau). Khối đơn cấp lại đứng SAU Mẫu 51 trên trang nên kể cả khi tiêu đề của nó cũng chứa cụm này, engine
vẫn gặp ô của Mẫu 51 trước.
"""

FIELDS: list[dict] = [
    # ---- NGƯỜI ĐỀ NGHỊ (Đơn Mẫu 51; đối chiếu CCCD, CCHN kiến trúc/xây dựng, văn bằng, chứng chỉ bồi dưỡng) ----
    {
        "name": "NguoiDeNghi_HoTen",
        "desc": "Họ và tên người đề nghị cấp chứng chỉ — dòng '1. Họ và tên (viết bằng chữ in hoa)' của Đơn Mẫu "
                "51; đối chiếu 'Họ và tên' trên CCCD/CCHN, 'cho' trên bằng tốt nghiệp, 'Cho Ông/Bà' trên chứng chỉ "
                "bồi dưỡng. Viết có dấu.",
    },
    {
        "name": "NguoiDeNghi_NgaySinh",
        "desc": "Ngày sinh người đề nghị, dd/mm/yyyy (Đơn: 'Ngày, tháng, năm sinh'; CCHN: 'Ngày tháng năm sinh'; "
                "bằng: 'sinh ngày'). Chỉ trả khi đọc được ĐỦ ngày-tháng-năm.",
    },
    {
        "name": "NguoiDeNghi_SoDinhDanh",
        "desc": "Số định danh cá nhân/CCCD của người đề nghị (CCCD hoặc dòng 'Số định danh cá nhân/Chứng minh nhân "
                "dân' của Đơn). Chỉ chữ số. Số CMND cũ 9 số in trên CCHN chỉ dùng khi không có số nào khác.",
    },
    {
        "name": "NguoiDeNghi_NgayCap",
        "desc": "Ngày cấp CÙNG giấy tờ với số định danh đã chọn (Đơn: '… cấp ngày dd/mm/yyyy do … cấp'; CCCD: ngày "
                "cấp), dd/mm/yyyy.",
    },
    {
        "name": "NguoiDeNghi_NoiCap",
        "desc": "Nơi cấp CÙNG giấy tờ với số định danh đã chọn — Đơn: phần giữa 'do' và 'cấp' (vd 'Cục Cảnh sát quản "
                "lý hành chính về trật tự xã hội'); CCHN: dòng 'Nơi cấp'.",
    },
    {
        "name": "NguoiDeNghi_DiaChiLienHe",
        "desc": "Dòng 'Địa chỉ liên hệ' của Đơn Mẫu 51, chép NGUYÊN VĂN cả dòng, giữ cả phần '(Nay là: …)' nếu có.",
    },
    {
        "name": "NguoiDeNghi_DiaChiHienNay",
        "desc": "Địa chỉ HIỆN HÀNH của người đề nghị: nơi thường trú trên CCCD; không có CCCD thì phần sau 'Nay là' "
                "trong địa chỉ liên hệ của Đơn (không có 'Nay là' thì chính địa chỉ liên hệ). Object "
                "{tinh,xa,chiTietDuoiXa}.",
    },
    {"name": "NguoiDeNghi_DienThoai", "desc": "Số điện thoại của người đề nghị nếu giấy tờ có ghi, chỉ chữ số."},
    {"name": "NguoiDeNghi_Email", "desc": "Email của người đề nghị nếu giấy tờ có ghi, nguyên văn."},
    {
        "name": "NguoiDeNghi_TrinhDoChuyenMon",
        "desc": "Mục '2. Trình độ chuyên môn' của Đơn Mẫu 51, chép NGUYÊN VĂN phần sau dấu hai chấm (vd 'Trường Đại "
                "học Xây dựng – ngành: Kiến trúc').",
    },
    {
        "name": "NguoiDeNghi_KinhNghiem",
        "desc": "Mục '3. Kinh nghiệm chuyên môn về bảo quản, tu bổ, phục hồi di tích…' của Đơn Mẫu 51: MẢNG, mỗi "
                "phần tử NGUYÊN VĂN một mục a., b., c.… (công trình, thời gian thực hiện, công việc).",
    },
    {
        "name": "Don_HoatDongDeNghi",
        "desc": "Các hoạt động đề nghị cấp chứng chỉ, liệt kê sau câu '…cho các hoạt động sau:' của Đơn Mẫu 51: "
                "MẢNG, mỗi phần tử một hoạt động (vd 'Lập quy hoạch bảo quản, tu bổ, phục hồi di tích.').",
    },
    {"name": "Don_CoQuanNhan", "desc": "Cơ quan ở dòng 'Kính gửi' của Đơn Mẫu 51 (vd 'Giám đốc Sở Văn hóa, Thể thao và Du lịch tỉnh …')."},

    # ---- VĂN BẰNG + CHỨNG CHỈ (bù trình độ chuyên môn khi đơn để trống; đối chiếu thời hạn) ----
    {
        "name": "VanBang_CoSoDaoTao",
        "desc": "Trường cấp bằng tốt nghiệp đại học (dòng 'Hiệu trưởng trường … cấp'), hoặc 'Cơ sở đào tạo' trên CCHN.",
    },
    {"name": "VanBang_Nganh", "desc": "Ngành ghi trên bằng tốt nghiệp đại học (vd 'Kiến trúc', 'Xây dựng dân dụng')."},
    {
        "name": "ChungChi_ThoiHan",
        "desc": "Thời hạn các chứng chỉ hành nghề kiến trúc / hoạt động xây dựng: MẢNG object {ten, so, denNgay} — "
                "ten = tên chứng chỉ, so = 'Số: …' in trên chứng chỉ, denNgay = ngày cuối cột 'Thời hạn' ('Từ … "
                "đến dd/mm/yyyy'), dd/mm/yyyy. Không có cột thời hạn thì bỏ field.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _n in ("NguoiDeNghi_NgaySinh", "NguoiDeNghi_NgayCap"):
    COMPACT_COMP_BY_NAME[_n] = "x-date"
COMPACT_COMP_BY_NAME["NguoiDeNghi_DiaChiHienNay"] = "x-select-area"

# ---- UI fields cho engine fill-liz.js — khớp (section, mat-label) ----
S_NOP = "Thông tin người nộp hồ sơ"
S_UQ = "Thông tin người ủy quyền"
S_DON = "chứng chỉ hành nghề bảo quản"

# Nhãn ô tích bật khối ủy quyền (liz-checkbox, trùng chữ với group-header của khối).
UY_QUYEN_CHECKBOX = "Thông tin người ủy quyền"

LABEL_HO_TEN = "Họ và tên (viết bằng chữ in hoa)"
LABEL_SO_DINH_DANH = "Số định danh cá nhân/Chứng minh nhân dân"
LABEL_NGAY_SINH = "Ngày tháng năm sinh"
LABEL_DIA_CHI_LIEN_HE = "Địa chỉ liên hệ"
LABEL_TRINH_DO = "Trình độ chuyên môn (ghi rõ chuyên ngành đào tạo được ghi trong văn bằng, chứng chỉ đã được cấp)"
LABEL_KINH_NGHIEM = (
    "Kinh nghiệm chuyên môn về bảo quản, tu bổ, phục hồi di tích liên quan đến hoạt động đề nghị cấp Chứng chỉ "
    "hành nghề (ghi theo bản khai kinh nghiệm chuyên môn đã được tổ chức nơi đã làm việc hoặc đang làm việc xác nhận)"
)
LABEL_HOAT_DONG = "Cấp Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích cho các hoạt động sau"

# comp: liz-input (text/textarea) | liz-date (datepicker dd/mm/yyyy) | liz-select (mat-select overlay).
# Cố ý BỎ "Tên người nộp" và "CMND/Hộ chiếu/MST" của khối người nộp — cổng khoá theo tài khoản định danh.
UI_FIELDS: list[tuple[str, str, str, tuple[str, ...]]] = [
    (S_NOP, "Ngày sinh", "liz-date", ()),
    (S_NOP, "Ngày cấp", "liz-date", ()),
    (S_NOP, "Nơi cấp", "liz-input", ()),
    (S_NOP, "Số điện thoại", "liz-input", ()),
    (S_NOP, "Email", "liz-input", ()),
    (S_NOP, "Địa chỉ hành chính", "liz-select", ()),
    (S_NOP, "Địa chỉ chi tiết", "liz-input", ()),

    (S_UQ, "Tên người / Tên đơn vị ủy quyền", "liz-input", ()),
    (S_UQ, "Ngày sinh", "liz-date", ()),
    (S_UQ, "CMND/Hộ chiếu/MST Doanh nghiệp", "liz-input", ()),
    (S_UQ, "Ngày cấp", "liz-date", ()),
    (S_UQ, "Nơi cấp", "liz-input", ()),
    (S_UQ, "Số điện thoại", "liz-input", ()),
    (S_UQ, "Email", "liz-input", ()),
    (S_UQ, "Địa chỉ hành chính", "liz-select", ()),
    (S_UQ, "Địa chỉ chi tiết", "liz-input", ()),

    (S_DON, LABEL_HO_TEN, "liz-input", ("Họ và tên",)),
    (S_DON, LABEL_SO_DINH_DANH, "liz-input", ("Số định danh cá nhân",)),
    (S_DON, LABEL_NGAY_SINH, "liz-date", ("Ngày, tháng, năm sinh",)),
    (S_DON, LABEL_DIA_CHI_LIEN_HE, "liz-input", ()),
    (S_DON, LABEL_TRINH_DO, "liz-input", ("Trình độ chuyên môn",)),
    (S_DON, LABEL_KINH_NGHIEM, "liz-input", ("Kinh nghiệm chuyên môn về bảo quản, tu bổ, phục hồi di tích",)),
    (S_DON, LABEL_HOAT_DONG, "liz-input", ()),
]

COMP_BY_UI = {(s, l): c for s, l, c, _a in UI_FIELDS}
ALIASES_BY_UI = {(s, l): list(a) for s, l, _c, a in UI_FIELDS}
