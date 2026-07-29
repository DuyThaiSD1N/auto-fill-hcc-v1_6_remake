"""Catalog thành phần hồ sơ "[Bắc Ninh] Đăng ký biến động QSDĐ (chuyển nhượng/thừa kế/tặng cho…)".

Cơ chế: LLM phân loại mỗi tài liệu → NHÃN RÚT GỌN (một trong LABELS). BE map nhãn rút gọn →
componentName CHI TIẾT (mã KQ để FE khớp đúng ô — mã KQ có in trong dòng tiêu đề mỗi thành phần)
hoặc ô đính kèm bổ sung. FE chỉ cần tìm đúng mã KQ để upload.

Form có 13 thành phần (TPHS 1–13); cá nhân chuyển nhượng thường chỉ dùng 3 thành phần đầu
(don_bien_dong / gcn / hop_dong_chuyen_quyen) + CCCD (bổ sung).
"""

# (label rút gọn, componentName = mã KQ hoặc None nếu vào ô bổ sung, mô tả ngắn cho LLM)
CATALOG: list[tuple[str, str | None, str]] = [
    ("don_bien_dong", "KQ005897",
     "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18/Mẫu 16-ĐK) — bản kê khai của "
     "người nhận, có tiêu đề 'ĐƠN ĐĂNG KÝ BIẾN ĐỘNG…'"),
    ("gcn", "KQ0777",
     "Bản gốc Giấy chứng nhận đã cấp (sổ đỏ/sổ hồng) — có 'số vào sổ cấp GCN', số thửa, tờ bản đồ, cơ quan cấp"),
    ("hop_dong_chuyen_quyen", "KQ005898",
     "Hợp đồng hoặc văn bản về việc CHUYỂN QUYỀN (chuyển nhượng/tặng cho/thừa kế/góp vốn) quyền sử dụng "
     "đất, tài sản gắn liền với đất — gồm cả Lời chứng chứng thực/công chứng đi kèm hợp đồng"),
    ("van_ban_dai_dien", "KQ004869",
     "Văn bản về việc đại diện theo pháp luật về dân sự (giám hộ/đại diện), CHỈ khi nêu rõ đại diện/ủy quyền"),
    ("ban_ve_tach_thua", "KQ005901", "Bản vẽ tách thửa, hợp thửa theo Mẫu số 22"),
    ("manh_trich_do", "KQ005902", "Mảnh trích đo bản đồ địa chính thửa đất"),
    ("vb_the_chap_dong_y", "KQ005905",
     "Văn bản của bên NHẬN THẾ CHẤP đồng ý cho chuyển nhượng, tặng cho (khi đất đang thế chấp)"),
    ("vb_nguoi_sdd_dong_y", "KQ005904",
     "Văn bản của NGƯỜI SỬ DỤNG ĐẤT đồng ý cho chủ sở hữu tài sản gắn liền với đất chuyển nhượng/tặng cho/góp vốn"),
    ("vb_thoa_thuan_chung_gcn", "KQ005903",
     "Văn bản thỏa thuận cấp chung một Giấy chứng nhận khi có nhiều người nhận chuyển quyền"),
    ("vb_tang_cho", "KQ005906",
     "Văn bản tặng cho quyền sử dụng đất hoặc biên bản họp đại diện thôn/tổ dân phố (trường hợp tặng cho)"),
    ("bien_ban_hop_xa_tang_cho", "KQ005907",
     "Biên bản họp giữa UBND cấp xã với người sử dụng đất về việc tặng cho quyền sử dụng đất"),
    ("hd_tai_san_thue", "KQ005899",
     "Hợp đồng/văn bản bán, tặng cho, thừa kế, góp vốn bằng TÀI SẢN gắn liền với đất THUÊ của Nhà nước "
     "trả tiền hằng năm"),
    ("vb_cho_thue_lai", "KQ005900",
     "Văn bản về việc cho thuê, cho thuê lại quyền sử dụng đất trong DỰ ÁN xây dựng kinh doanh kết cấu hạ tầng"),
    # --- không có ô riêng trong danh mục → ô đính kèm BỔ SUNG ---
    ("cccd", None, "Căn cước công dân/CMND/thẻ căn cước/hộ chiếu của các bên"),
    ("khac", None, "Giấy tờ khác hoặc không xác định được loại"),
]

_BY_LABEL = {label: (kq, desc) for label, kq, desc in CATALOG}
LABELS = [label for label, _, _ in CATALOG]

# Nhãn hiển thị mặc định (documentName) khi không có tên cụ thể.
_DISPLAY = {
    "don_bien_dong": "Đơn đăng ký biến động đất đai",
    "gcn": "Giấy chứng nhận QSDĐ (bản gốc)",
    "hop_dong_chuyen_quyen": "Hợp đồng chuyển quyền sử dụng đất",
    "van_ban_dai_dien": "Văn bản đại diện theo pháp luật",
    "ban_ve_tach_thua": "Bản vẽ tách/hợp thửa (Mẫu 22)",
    "manh_trich_do": "Mảnh trích đo địa chính",
    "vb_the_chap_dong_y": "Văn bản bên nhận thế chấp đồng ý",
    "vb_nguoi_sdd_dong_y": "Văn bản người SDĐ đồng ý",
    "vb_thoa_thuan_chung_gcn": "Văn bản thỏa thuận cấp chung 1 GCN",
    "vb_tang_cho": "Văn bản tặng cho QSDĐ",
    "bien_ban_hop_xa_tang_cho": "Biên bản họp UBND xã (tặng cho)",
    "hd_tai_san_thue": "Hợp đồng tài sản trên đất thuê",
    "vb_cho_thue_lai": "Văn bản cho thuê lại QSDĐ",
    "cccd": "Căn cước công dân",
    "khac": "Tài liệu kèm theo",
}


def is_valid(label: str) -> bool:
    return label in _BY_LABEL


def resolve(label: str) -> tuple[str, str]:
    """Nhãn rút gọn → (target, componentName). componentName = mã KQ khi có ô riêng, "" nếu bổ sung."""
    kq, _ = _BY_LABEL.get(label, (None, ""))
    if kq:
        return ("existing", kq)
    return ("supplementary", "")


def display_name(label: str) -> str:
    return _DISPLAY.get(label, "Tài liệu kèm theo")


def llm_options() -> str:
    """Chuỗi liệt kê nhãn + mô tả để nhúng vào prompt phân loại."""
    return "\n".join(f"- {label}: {desc}" for label, _, desc in CATALOG)
