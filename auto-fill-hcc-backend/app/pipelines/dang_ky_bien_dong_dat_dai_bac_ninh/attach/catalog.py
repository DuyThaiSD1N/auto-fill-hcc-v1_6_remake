"""Catalog thành phần hồ sơ "[Bắc Ninh] Đăng ký biến động QSDĐ" (1.115468).

Cơ chế: LLM phân loại mỗi tài liệu → NHÃN RÚT GỌN (một trong LABELS). BE map nhãn → componentName =
mã **TP-H05.xxxxxx** (in trong dòng tiêu đề mỗi thành phần → FE khớp substring đã fold) hoặc ô "File
đính kèm khác" (supplementary) cho tài liệu không có mục riêng.

16 thành phần hồ sơ (TP-H05.000026, 000033, 000040, 000045, 000069–000080). Cá nhân tặng cho/chuyển
nhượng thường dùng: đơn (000026) + hợp đồng (000069/000080) + GCN gốc (000040) + ủy quyền (000079);
CCCD/hộ tịch/tờ khai thuế/biên bản bàn giao → File đính kèm khác.
"""

# (label rút gọn, componentName = mã TP-H05 hoặc None nếu vào ô đính kèm khác, mô tả ngắn cho LLM)
CATALOG: list[tuple[str, str | None, str]] = [
    ("don_bien_dong", "TP-H05.000026",
     "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18) — bản kê khai của người nhận, "
     "tiêu đề 'ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI…'"),
    ("gcn", "TP-H05.000040",
     "Bản gốc Giấy chứng nhận đã cấp (sổ đỏ/sổ hồng) — có 'số vào sổ cấp GCN', số thửa, tờ bản đồ, cơ quan cấp"),
    ("vb_tang_cho", "TP-H05.000080",
     "Văn bản TẶNG CHO quyền sử dụng đất, hoặc biên bản họp đại diện thôn/tổ dân phố/UBND cấp xã về việc "
     "tặng cho quyền sử dụng đất (dùng khi giao dịch là TẶNG CHO)"),
    ("hop_dong_chuyen_quyen", "TP-H05.000069",
     "Hợp đồng hoặc văn bản về việc CHUYỂN QUYỀN sử dụng đất đối với chuyển đổi/chuyển nhượng/thừa kế/góp "
     "vốn (KHÔNG phải tặng cho) — gồm cả Lời chứng chứng thực/công chứng đi kèm"),
    ("hd_tai_san_thue", "TP-H05.000070",
     "Hợp đồng/văn bản bán, tặng cho, thừa kế, góp vốn bằng TÀI SẢN gắn liền với đất THUÊ của Nhà nước "
     "trả tiền thuê đất hằng năm"),
    ("hd_mua_ban_nha_co_thoi_han", "TP-H05.000071",
     "Hợp đồng mua bán nhà ở có thời hạn; giấy tờ về nhận tài sản thừa kế; giấy tờ nhận tài sản theo quy "
     "định pháp luật về phá sản, giải thể hoặc chấm dứt hoạt động"),
    ("vb_khai_thac_khoang_san", "TP-H05.000072",
     "Văn bản của cơ quan có thẩm quyền cho phép chuyển nhượng quyền khai thác khoáng sản"),
    ("vb_cho_thue_lai", "TP-H05.000073",
     "Văn bản về việc cho thuê, cho thuê lại quyền sử dụng đất trong DỰ ÁN xây dựng kinh doanh kết cấu hạ tầng"),
    ("vb_chap_thuan_to_chuc", "TP-H05.000074",
     "Văn bản chấp thuận của cơ quan có thẩm quyền đối với trường hợp tổ chức kinh tế nhận quyền sử dụng "
     "đất để thực hiện dự án"),
    ("phuong_an_sddnn", "TP-H05.000075",
     "Phương án sử dụng đất nông nghiệp được Chủ tịch UBND cấp xã chấp thuận (tổ chức kinh tế nhận quyền "
     "sử dụng đất nông nghiệp)"),
    ("ban_ve_tach_thua", "TP-H05.000033", "Mẫu số 22a. Bản vẽ tách thửa đất, hợp thửa đất"),
    ("manh_trich_do", "TP-H05.000045",
     "Mảnh trích đo bản đồ địa chính thửa đất (khi có nhu cầu đo đạc xác định lại kích thước/diện tích)"),
    ("vb_thoa_thuan_chung_gcn", "TP-H05.000076",
     "Văn bản thỏa thuận về việc cấp chung một Giấy chứng nhận khi có nhiều người nhận chuyển quyền"),
    ("vb_nguoi_sdd_dong_y", "TP-H05.000077",
     "Văn bản của NGƯỜI SỬ DỤNG ĐẤT đồng ý cho chủ sở hữu tài sản gắn liền với đất được chuyển nhượng/tặng "
     "cho/góp vốn tài sản (khi chủ tài sản không có quyền sử dụng đất đối với thửa đất đó)"),
    ("vb_the_chap_dong_y", "TP-H05.000078",
     "Văn bản của bên NHẬN THẾ CHẤP đồng ý cho bên thế chấp được chuyển nhượng/tặng cho/góp vốn (khi thửa "
     "đất đang thế chấp và đã đăng ký tại VPĐKĐĐ)"),
    ("van_ban_dai_dien", "TP-H05.000079",
     "Văn bản về việc đại diện theo quy định của pháp luật về dân sự (giấy ủy quyền/đại diện) khi thực "
     "hiện thủ tục thông qua người đại diện — BẮT BUỘC khi hồ sơ nộp qua người được ủy quyền"),
    # --- không có ô riêng trong 16 thành phần → ô "File đính kèm khác" (supplementary) ---
    ("cccd", None, "Căn cước công dân/CMND/thẻ căn cước/hộ chiếu của các bên"),
    ("ho_tich", None,
     "Giấy tờ hộ tịch chứng minh quan hệ (Giấy chứng nhận kết hôn, Trích lục/Giấy khai sinh) — để miễn "
     "lệ phí trước bạ/thuế TNCN hoặc làm căn cứ cấp chung 1 GCN"),
    ("to_khai_thue", None,
     "Tờ khai thuế/lệ phí: Tờ khai thuế thu nhập cá nhân (Mẫu 03/BĐS-TNCN), Tờ khai lệ phí trước bạ "
     "(Mẫu 01/LPTB), Tờ khai thuế sử dụng đất phi nông nghiệp (Mẫu 01/TK-SDDPNN)"),
    ("bien_ban_ban_giao", None,
     "Biên bản bàn giao đất và tài sản gắn liền với đất trên thực địa (giữa bên giao và bên nhận)"),
    ("khac", None, "Giấy tờ khác hoặc không xác định được loại"),
]

_BY_LABEL = {label: (code, desc) for label, code, desc in CATALOG}
LABELS = [label for label, _, _ in CATALOG]

# Nhãn hiển thị mặc định (documentName) khi không có tên cụ thể.
_DISPLAY = {
    "don_bien_dong": "Đơn đăng ký biến động đất đai (Mẫu 18)",
    "gcn": "Giấy chứng nhận QSDĐ (bản gốc)",
    "vb_tang_cho": "Văn bản tặng cho QSDĐ",
    "hop_dong_chuyen_quyen": "Hợp đồng chuyển quyền sử dụng đất",
    "hd_tai_san_thue": "Hợp đồng tài sản trên đất thuê",
    "hd_mua_ban_nha_co_thoi_han": "Hợp đồng mua bán nhà ở có thời hạn",
    "vb_khai_thac_khoang_san": "Văn bản cho phép chuyển nhượng quyền khai thác khoáng sản",
    "vb_cho_thue_lai": "Văn bản cho thuê/cho thuê lại QSDĐ",
    "vb_chap_thuan_to_chuc": "Văn bản chấp thuận cơ quan có thẩm quyền",
    "phuong_an_sddnn": "Phương án sử dụng đất nông nghiệp",
    "ban_ve_tach_thua": "Bản vẽ tách/hợp thửa (Mẫu 22a)",
    "manh_trich_do": "Mảnh trích đo địa chính",
    "vb_thoa_thuan_chung_gcn": "Văn bản thỏa thuận cấp chung 1 GCN",
    "vb_nguoi_sdd_dong_y": "Văn bản người SDĐ đồng ý",
    "vb_the_chap_dong_y": "Văn bản bên nhận thế chấp đồng ý",
    "van_ban_dai_dien": "Văn bản đại diện theo pháp luật (ủy quyền)",
    "cccd": "Căn cước công dân",
    "ho_tich": "Giấy tờ hộ tịch",
    "to_khai_thue": "Tờ khai thuế",
    "bien_ban_ban_giao": "Biên bản bàn giao đất",
    "khac": "Tài liệu kèm theo",
}


def is_valid(label: str) -> bool:
    return label in _BY_LABEL


def resolve(label: str) -> tuple[str, str]:
    """Nhãn rút gọn → (target, componentName). componentName = mã TP-H05 khi có ô riêng, "" nếu đính kèm khác."""
    code, _ = _BY_LABEL.get(label, (None, ""))
    if code:
        return ("existing", code)
    return ("supplementary", "")


def display_name(label: str) -> str:
    return _DISPLAY.get(label, "Tài liệu kèm theo")


def llm_options() -> str:
    """Chuỗi liệt kê nhãn + mô tả để nhúng vào prompt phân loại."""
    return "\n".join(f"- {label}: {desc}" for label, _, desc in CATALOG)
