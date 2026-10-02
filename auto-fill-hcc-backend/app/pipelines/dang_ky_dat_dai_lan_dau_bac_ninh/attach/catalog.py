"""Catalog thành phần hồ sơ (Đăng ký đất đai, cấp GCN lần đầu — Bắc Ninh, mã 1.115443).

LLM phân loại tài liệu → NHÃN RÚT GỌN → BE map sang componentName (mã thành phần TP-H05.xxxxxx in
đầu mỗi dòng của bảng "Tải thành phần hồ sơ") hoặc ô bổ sung. FE (fill-bacninh.js) khớp componentName
là CHUỖI CON của chữ trên dòng → dùng mã TP đầy đủ (kể cả đuôi ".S") để không dính dòng mã dài hơn.

Form sau khi đổi mã 1.013978 → 1.115443 bỏ hẳn mã KQxxxxxx, có 21 dòng (gộp cả trường hợp "diện tích
tăng thêm"). Ba nội dung xuất hiện HAI dòng (trích lục/trích đo, giấy tờ Điều 137, hồ sơ thiết kế) —
lấy dòng xuất hiện TRƯỚC trên form; dòng kia để trống.
"""

# (label, componentName = mã TP hoặc None → ô bổ sung, mô tả ngắn cho LLM)
CATALOG: list[tuple[str, str | None, str]] = [
    ("don_mau_15", "TP-H05.000018",
     "Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 15) — bản kê khai của người sử dụng đất"),
    ("don_mau_18", "TP-H05.000026", "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18)"),
    ("thong_bao_mau_16", "TP-H05.000024", "Thông báo xác nhận kết quả đăng ký đất đai (Mẫu số 16)"),
    ("danh_sach_15a", "TP-H05.000159.S",
     "Danh sách những người sử dụng chung thửa đất, sở hữu chung tài sản (Mẫu 15a, kèm theo Mẫu số 15); "
     "văn bản xác định các thành viên có chung quyền sử dụng đất của hộ gia đình"),
    ("gcn_da_cap", "TP-H05.000151.S",
     "Giấy chứng nhận quyền sử dụng đất ĐÃ CẤP (sổ đỏ/sổ hồng) của thửa đất — trường hợp diện tích tăng thêm"),
    ("trich_do_dia_chinh", "TP-H05.000167.S",
     "Trích lục/trích đo bản đồ địa chính; phiếu xác nhận kết quả đo đạc hiện trạng thửa đất; bản mô tả "
     "ranh giới, mốc giới thửa đất"),
    ("giay_to_nguon_goc", "TP-H05.000168.S",
     "Giấy tờ về quyền sử dụng đất theo Điều 137/148/149 Luật Đất đai (giấy tờ giao đất, mua bán, chuyển "
     "nhượng, tặng cho viết tay...); sơ đồ nhà ở, công trình xây dựng"),
    ("thua_ke", "TP-H05.000155.S", "Giấy tờ về việc nhận thừa kế quyền sử dụng đất (di chúc, văn bản phân chia di sản...)"),
    ("chung_tu_tai_chinh", "TP-H05.000149.S",
     "Chứng từ/tờ khai nghĩa vụ tài chính: phiếu thu, biên lai, tờ khai thuế sử dụng đất phi nông nghiệp, "
     "tờ khai tiền sử dụng đất, tờ khai lệ phí trước bạ"),
    ("mien_giam", "TP-H05.000152.S",
     "Giấy tờ chứng minh được miễn, giảm nghĩa vụ tài chính (giấy chứng nhận thương binh, người có công...)"),
    ("giao_dat_khong_tham_quyen", "TP-H05.000156.S",
     "Giấy tờ giao đất không đúng thẩm quyền; giấy tờ mua, nhận thanh lý, hóa giá, phân phối nhà ở (Điều 140)"),
    ("van_ban_cap_chung_gcn", "TP-H05.000150.S",
     "Văn bản thỏa thuận về việc cấp chung một Giấy chứng nhận (nhiều người chung quyền)"),
    ("xu_phat", "TP-H05.000157.S", "Giấy tờ/quyết định xử phạt vi phạm hành chính trong lĩnh vực đất đai; chứng từ nộp phạt"),
    ("uy_quyen", "TP-H05.000046",
     "Văn bản về việc đại diện/ủy quyền theo pháp luật dân sự (giấy ủy quyền, hợp đồng ủy quyền)"),
    ("thua_dat_lien_ke", "TP-H05.000158.S",
     "Hợp đồng/văn bản thỏa thuận/quyết định Tòa án xác lập quyền đối với thửa đất liền kề"),
    ("ho_so_thiet_ke", "TP-H05.000170.S",
     "Hồ sơ thiết kế xây dựng công trình đã thẩm định; văn bản chấp thuận nghiệm thu hoàn thành công trình"),
    ("xac_nhan_xay_dung", "TP-H05.000163.S",
     "Giấy xác nhận của cơ quan quản lý xây dựng về đủ điều kiện tồn tại nhà ở, công trình xây dựng"),
    # --- không có ô riêng → ô đính kèm BỔ SUNG ---
    ("cccd", None, "Căn cước công dân/CMND/thẻ căn cước/hộ chiếu"),
    ("gcn_ket_hon", None, "Giấy chứng nhận kết hôn/đăng ký kết hôn (chứng minh quan hệ vợ chồng)"),
    ("khac", None, "Giấy tờ khác hoặc không xác định được loại"),
]

_BY_LABEL = {label: (code, desc) for label, code, desc in CATALOG}
LABELS = [label for label, _, _ in CATALOG]

_DISPLAY = {
    "don_mau_15": "Đơn đăng ký đất đai (Mẫu 15)",
    "don_mau_18": "Đơn đăng ký biến động (Mẫu 18)",
    "thong_bao_mau_16": "Thông báo xác nhận kết quả đăng ký (Mẫu 16)",
    "danh_sach_15a": "Danh sách người sử dụng chung (Mẫu 15a)",
    "gcn_da_cap": "Giấy chứng nhận đã cấp",
    "trich_do_dia_chinh": "Trích đo, đo đạc thửa đất",
    "giay_to_nguon_goc": "Giấy tờ nguồn gốc sử dụng đất",
    "thua_ke": "Giấy tờ thừa kế",
    "chung_tu_tai_chinh": "Tờ khai, chứng từ nghĩa vụ tài chính",
    "mien_giam": "Giấy tờ miễn giảm nghĩa vụ tài chính",
    "giao_dat_khong_tham_quyen": "Giấy tờ giao đất không đúng thẩm quyền",
    "van_ban_cap_chung_gcn": "Văn bản cấp chung Giấy chứng nhận",
    "xu_phat": "Giấy tờ xử phạt đất đai",
    "uy_quyen": "Giấy ủy quyền",
    "thua_dat_lien_ke": "Giấy tờ quyền thửa đất liền kề",
    "ho_so_thiet_ke": "Hồ sơ thiết kế xây dựng",
    "xac_nhan_xay_dung": "Giấy xác nhận xây dựng",
    "cccd": "Căn cước công dân",
    "gcn_ket_hon": "Giấy chứng nhận kết hôn",
    "khac": "Tài liệu kèm theo",
}


def is_valid(label: str) -> bool:
    return label in _BY_LABEL


def resolve(label: str) -> tuple[str, str]:
    code, _ = _BY_LABEL.get(label, (None, ""))
    return ("existing", code) if code else ("supplementary", "")


def display_name(label: str) -> str:
    return _DISPLAY.get(label, "Tài liệu kèm theo")


def llm_options() -> str:
    return "\n".join(f"- {label}: {desc}" for label, _, desc in CATALOG)
