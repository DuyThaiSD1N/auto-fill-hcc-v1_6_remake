"""Catalog thành phần hồ sơ (giao/thuê/chuyển mục đích/gia hạn SDĐ — Bắc Ninh, TTHC 1.115438).

Cơ chế: LLM phân loại mỗi tài liệu → NHÃN RÚT GỌN (một trong LABELS). BE map nhãn rút gọn →
componentName = MÃ THÀNH PHẦN (TP-H05.*) để FE khớp đúng ô, hoặc ô đính kèm bổ sung.

Crawl 23/10/2026: cổng bỏ mã KQ0058xx, đổi sang TP-H05.*, 21 thành phần chia 3 CỤM theo mẫu đơn —
giao/thuê (Mẫu 01, id 50517–50528), chuyển mục đích (Mẫu 02, 50529–50531), gia hạn (Mẫu 04a,
50533–50538). GCN / trích lục / miễn giảm có ô RIÊNG ở từng cụm → nhãn map theo cụm (xem CUM_*),
cụm suy từ đơn trong bộ file (planner._detect_cum). Ô "Phương án tầng đất mặt (Mẫu 26)" không còn.
"""

CUM_GIAO_THUE = "giao_thue"
CUM_CHUYEN_MUC_DICH = "chuyen_muc_dich"
CUM_GIA_HAN = "gia_han"
# Người dân nộp qua trợ lý chủ yếu là chuyển mục đích → mặc định khi bộ file không có đơn.
CUM_MAC_DINH = CUM_CHUYEN_MUC_DICH

# Nhãn đơn → cụm.
DON_CUM = {
    "don_giao_thue": CUM_GIAO_THUE,
    "don_chuyen_muc_dich": CUM_CHUYEN_MUC_DICH,
    "don_gia_han": CUM_GIA_HAN,
}

# (label rút gọn, {cụm: mã TP} — thiếu cụm → ô bổ sung; None = luôn bổ sung, mô tả ngắn cho LLM)
CATALOG: list[tuple[str, dict[str, str] | None, str]] = [
    ("don_giao_thue",
     {CUM_GIAO_THUE: "TP-H05.000001", CUM_CHUYEN_MUC_DICH: "TP-H05.000001", CUM_GIA_HAN: "TP-H05.000001"},
     "Mẫu số 01 — ĐƠN ĐỀ NGHỊ GIAO ĐẤT / CHO THUÊ ĐẤT / giao đất và giao rừng / cho thuê đất và cho thuê rừng"),
    ("don_chuyen_muc_dich",
     {CUM_GIAO_THUE: "TP-H05.000002", CUM_CHUYEN_MUC_DICH: "TP-H05.000002", CUM_GIA_HAN: "TP-H05.000002"},
     "Mẫu số 02 — ĐƠN ĐỀ NGHỊ CHUYỂN MỤC ĐÍCH SỬ DỤNG ĐẤT"),
    ("don_gia_han",
     {CUM_GIAO_THUE: "TP-H05.000005", CUM_CHUYEN_MUC_DICH: "TP-H05.000005", CUM_GIA_HAN: "TP-H05.000005"},
     "Mẫu số 04a — ĐƠN ĐỀ NGHỊ GIA HẠN SỬ DỤNG ĐẤT"),
    ("gcn",
     {CUM_CHUYEN_MUC_DICH: "TP-H05.000128.S", CUM_GIA_HAN: "TP-H05.000130.S"},
     "Giấy chứng nhận QSDĐ/quyền sở hữu nhà ở/tài sản gắn liền với đất (sổ đỏ/sổ hồng) đã cấp, có số "
     "vào sổ cấp GCN, số thửa, tờ bản đồ; hoặc giấy tờ về QSDĐ theo Điều 137 Luật Đất đai"),
    ("quyet_dinh_giao_dat",
     {CUM_CHUYEN_MUC_DICH: "TP-H05.000128.S", CUM_GIA_HAN: "TP-H05.000131.S"},
     "QUYẾT ĐỊNH giao đất / cho thuê đất / cho phép chuyển mục đích sử dụng đất đã ban hành của cơ "
     "quan nhà nước (không phải đơn của người dân)"),
    ("trich_luc",
     {CUM_GIAO_THUE: "TP-H05.000118.S", CUM_CHUYEN_MUC_DICH: "TP-H05.000129.S", CUM_GIA_HAN: "TP-H05.000212"},
     "Trích lục bản đồ địa chính / trích đo bản đồ địa chính / bản đồ đo đạc chỉnh lý / PHIẾU XÁC "
     "NHẬN KẾT QUẢ ĐO ĐẠC HIỆN TRẠNG THỬA ĐẤT (có sơ đồ, tọa độ đỉnh thửa)"),
    ("mien_giam",
     {CUM_GIAO_THUE: "TP-H05.000144.S", CUM_GIA_HAN: "TP-H05.000112"},
     "Giấy tờ về miễn, giảm nghĩa vụ tài chính (tiền sử dụng đất, tiền thuê đất)"),
    ("van_ban_dau_tu",
     {CUM_GIAO_THUE: "TP-H05.000119.S", CUM_GIA_HAN: "TP-H05.000132.S"},
     "Văn bản phê duyệt dự án đầu tư / chấp thuận chủ trương đầu tư / gia hạn thời hạn hoạt động dự án"),
    ("lua_chon_nha_dau_tu", {CUM_GIAO_THUE: "TP-H05.000120.S"},
     "Văn bản phê duyệt kết quả lựa chọn nhà đầu tư (đấu thầu dự án có sử dụng đất)"),
    ("dau_gia_khong_thanh", {CUM_GIAO_THUE: "TP-H05.000121.S"},
     "Văn bản về kết quả đấu giá quyền sử dụng đất KHÔNG THÀNH"),
    ("chia_tach_sap_nhap", {CUM_GIAO_THUE: "TP-H05.000122.S"},
     "Văn bản về chia tách, sáp nhập, chuyển đổi mô hình tổ chức"),
    ("phuong_an_su_dung_dat", {CUM_GIAO_THUE: "TP-H05.000123.S"},
     "Phương án sử dụng đất đã phê duyệt của tổ chức kinh tế / đơn vị sự nghiệp công lập"),
    ("phuong_an_nong_lam", {CUM_GIAO_THUE: "TP-H05.000124.S"},
     "Phương án sử dụng đất của công ty nông, lâm nghiệp"),
    ("hien_trang_rung", {CUM_GIAO_THUE: "TP-H05.000126.S"},
     "Báo cáo điều tra, đánh giá hiện trạng rừng và bản đồ hiện trạng rừng (giao đất và giao rừng)"),
    ("thue_rung", {CUM_GIAO_THUE: "TP-H05.000127.S"},
     "Kết quả / biên bản / danh sách trúng đấu giá thuê rừng (cho thuê đất và cho thuê rừng)"),
    # --- không có ô riêng trong danh mục → ô đính kèm BỔ SUNG ---
    ("cccd", None, "Căn cước công dân/CMND/thẻ căn cước/hộ chiếu"),
    ("uy_quyen", None, "Giấy/văn bản/hợp đồng ủy quyền (có BÊN ỦY QUYỀN và BÊN ĐƯỢC ỦY QUYỀN)"),
    ("to_khai_thue", None,
     "Tờ khai thuế (thuế sử dụng đất phi nông nghiệp, lệ phí trước bạ, tiền sử dụng đất...)"),
    ("tang_dat_mat", None, "Phương án sử dụng tầng đất mặt theo Mẫu số 26"),
    ("khac", None, "Giấy tờ khác hoặc không xác định được loại"),
]

_BY_LABEL = {label: (codes, desc) for label, codes, desc in CATALOG}
LABELS = [label for label, _, _ in CATALOG]

# Nhãn hiển thị mặc định (documentName) khi không có tên cụ thể.
_DISPLAY = {
    "don_giao_thue": "Đơn đề nghị giao đất, cho thuê đất",
    "don_chuyen_muc_dich": "Đơn đề nghị chuyển mục đích sử dụng đất",
    "don_gia_han": "Đơn đề nghị gia hạn sử dụng đất",
    "gcn": "Giấy chứng nhận QSDĐ",
    "quyet_dinh_giao_dat": "Quyết định giao đất, cho thuê đất",
    "trich_luc": "Trích đo bản đồ địa chính",
    "mien_giam": "Giấy tờ miễn, giảm nghĩa vụ tài chính",
    "van_ban_dau_tu": "Văn bản phê duyệt dự án đầu tư",
    "lua_chon_nha_dau_tu": "Kết quả lựa chọn nhà đầu tư",
    "dau_gia_khong_thanh": "Kết quả đấu giá không thành",
    "chia_tach_sap_nhap": "Văn bản chia tách, sáp nhập",
    "phuong_an_su_dung_dat": "Phương án sử dụng đất",
    "phuong_an_nong_lam": "Phương án sử dụng đất nông, lâm nghiệp",
    "hien_trang_rung": "Báo cáo hiện trạng rừng",
    "thue_rung": "Kết quả đấu giá thuê rừng",
    "cccd": "Căn cước công dân",
    "uy_quyen": "Văn bản ủy quyền",
    "to_khai_thue": "Tờ khai thuế",
    "tang_dat_mat": "Phương án tầng đất mặt (Mẫu 26)",
    "khac": "Tài liệu kèm theo",
}


def is_valid(label: str) -> bool:
    return label in _BY_LABEL


def resolve(label: str, cum: str = CUM_MAC_DINH) -> tuple[str, str]:
    """(Nhãn rút gọn, cụm) → (target, componentName). componentName = mã TP khi có ô riêng, "" nếu bổ sung."""
    codes, _ = _BY_LABEL.get(label, (None, ""))
    code = (codes or {}).get(cum)
    if code:
        return ("existing", code)
    return ("supplementary", "")


def display_name(label: str) -> str:
    return _DISPLAY.get(label, "Tài liệu kèm theo")


def llm_options() -> str:
    """Chuỗi liệt kê nhãn + mô tả để nhúng vào prompt phân loại."""
    return "\n".join(f"- {label}: {desc}" for label, _, desc in CATALOG)
