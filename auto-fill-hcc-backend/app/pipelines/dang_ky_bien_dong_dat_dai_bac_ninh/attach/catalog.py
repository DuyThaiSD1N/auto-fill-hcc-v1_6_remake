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

# 1.115470 — biến động theo thỏa thuận hộ gia đình/vợ chồng, công trình ngầm, tài sản công, giải quyết
# tranh chấp/bản án, xử lý tài sản thế chấp. Cùng đơn Mẫu 18 nhưng 18 thành phần KHÁC 1.115468 (crawl
# 20/10/2026): ủy quyền là 000046 (không phải 000079), không có 000069/000080 → dùng catalog riêng, đính
# nhầm mã của 1.115468 là FE báo "Không khớp thành phần".
CATALOG_THOA_THUAN: list[tuple[str, str | None, str]] = [
    ("don_bien_dong", "TP-H05.000026",
     "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18) — tiêu đề 'ĐƠN ĐĂNG KÝ BIẾN ĐỘNG "
     "ĐẤT ĐAI…'"),
    ("gcn", "TP-H05.000040",
     "Bản gốc Giấy chứng nhận đã cấp (sổ đỏ/sổ hồng) — có 'số vào sổ cấp GCN', số thửa, tờ bản đồ, cơ quan cấp"),
    ("vb_thoa_thuan", "TP-H05.000085",
     "VĂN BẢN THỎA THUẬN của các thành viên hộ gia đình, của vợ và chồng, hoặc của những người cùng đứng tên "
     "về việc thay đổi quyền sử dụng đất/quyền sở hữu tài sản (vd thỏa thuận về diện tích, phân chia, đứng tên)"),
    ("giay_to_hon_nhan", "TP-H05.000086",
     "Giấy chứng nhận kết hôn, quyết định/bản án ly hôn, giấy xác nhận tình trạng hôn nhân"),
    ("vb_cong_trinh_ngam", "TP-H05.000087",
     "Văn bản của cơ quan có thẩm quyền cho phép thay đổi quyền sử dụng đất xây dựng công trình trên mặt đất "
     "phục vụ vận hành, khai thác công trình ngầm / quyền sở hữu công trình ngầm"),
    ("vb_cho_phep_tai_san_cong", "TP-H05.000088",
     "Quyết định/văn bản của cơ quan có thẩm quyền cho phép bán tài sản, ĐIỀU CHUYỂN, chuyển nhượng quyền "
     "sử dụng đất là tài sản công"),
    ("hd_mua_ban_tai_san_cong", "TP-H05.000089",
     "Hợp đồng mua bán tài sản công là quyền sử dụng đất, tài sản gắn liền với đất"),
    ("bien_ban_hoa_giai", "TP-H05.000090",
     "Biên bản hòa giải thành hoặc văn bản công nhận kết quả hòa giải thành"),
    ("qd_giai_quyet_tranh_chap", "TP-H05.000091",
     "Quyết định của cơ quan hành chính có thẩm quyền giải quyết tranh chấp, khiếu nại, tố cáo về đất đai"),
    ("ban_an_toa_an", "TP-H05.000092",
     "Bản án/quyết định của Tòa án nhân dân, quyết định thi hành án của cơ quan thi hành án"),
    ("phan_quyet_trong_tai", "TP-H05.000093",
     "Quyết định hoặc phán quyết của Trọng tài thương mại Việt Nam"),
    ("hd_chuyen_nhuong", "TP-H05.000094",
     "Hợp đồng chuyển nhượng quyền sử dụng đất, tài sản gắn liền với đất giữa người sử dụng đất với người "
     "nhận chuyển nhượng"),
    ("hd_chuyen_nhuong_tai_san_the_chap", "TP-H05.000095",
     "Hợp đồng chuyển nhượng/chuyển giao QSDĐ do bên có quyền BÁN TÀI SẢN THẾ CHẤP ký với người nhận"),
    ("hd_mua_ban_dau_gia", "TP-H05.000096",
     "Hợp đồng mua bán tài sản ĐẤU GIÁ quyền sử dụng đất hoặc văn bản xác nhận kết quả thi hành án dân sự"),
    ("hd_the_chap", "TP-H05.000097",
     "Hợp đồng thế chấp QSDĐ hoặc văn bản thỏa thuận bên nhận thế chấp được nhận chính tài sản bảo đảm"),
    ("ban_ve_tach_thua", "TP-H05.000033", "Mẫu số 22a. Bản vẽ tách thửa đất, hợp thửa đất"),
    ("manh_trich_do", "TP-H05.000045",
     "Mảnh trích đo bản đồ địa chính thửa đất (khi có nhu cầu đo đạc xác định lại kích thước/diện tích)"),
    ("van_ban_dai_dien", "TP-H05.000046",
     "Văn bản về việc đại diện theo quy định của pháp luật về dân sự (giấy ủy quyền/đại diện) khi thực "
     "hiện thủ tục thông qua người đại diện"),
    # --- không có ô riêng → ô "File đính kèm khác" (supplementary) ---
    ("cccd", None, "Căn cước công dân/CMND/thẻ căn cước/hộ chiếu của các bên"),
    ("ho_tich", None, "Giấy khai sinh/trích lục khai sinh và giấy tờ hộ tịch khác (không phải kết hôn/ly hôn)"),
    ("to_khai_thue", None,
     "Tờ khai thuế/lệ phí: Tờ khai thuế thu nhập cá nhân (Mẫu 03/BĐS-TNCN), Tờ khai lệ phí trước bạ "
     "(Mẫu 01/LPTB), Tờ khai thuế sử dụng đất phi nông nghiệp (Mẫu 01/TK-SDDPNN)"),
    ("khac", None, "Giấy tờ khác hoặc không xác định được loại"),
]

MA_CHUYEN_QUYEN = "1.115468"
MA_THOA_THUAN = "1.115470"
CATALOGS: dict[str, list[tuple[str, str | None, str]]] = {
    MA_CHUYEN_QUYEN: CATALOG,
    MA_THOA_THUAN: CATALOG_THOA_THUAN,
}


def _rows(ma: str) -> list[tuple[str, str | None, str]]:
    return CATALOGS.get(ma, CATALOG)


def _by_label(ma: str) -> dict[str, tuple[str | None, str]]:
    return {label: (code, desc) for label, code, desc in _rows(ma)}


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
    # 1.115470
    "vb_thoa_thuan": "Văn bản thỏa thuận thay đổi QSDĐ",
    "giay_to_hon_nhan": "Giấy tờ về tình trạng hôn nhân",
    "vb_cong_trinh_ngam": "Văn bản cho phép thay đổi QSDĐ công trình ngầm",
    "vb_cho_phep_tai_san_cong": "Văn bản cho phép bán/điều chuyển tài sản công",
    "hd_mua_ban_tai_san_cong": "Hợp đồng mua bán tài sản công",
    "bien_ban_hoa_giai": "Biên bản hòa giải thành",
    "qd_giai_quyet_tranh_chap": "Quyết định giải quyết tranh chấp đất đai",
    "ban_an_toa_an": "Bản án/quyết định của Tòa án",
    "phan_quyet_trong_tai": "Phán quyết Trọng tài thương mại",
    "hd_chuyen_nhuong": "Hợp đồng chuyển nhượng QSDĐ",
    "hd_chuyen_nhuong_tai_san_the_chap": "Hợp đồng chuyển nhượng tài sản thế chấp",
    "hd_mua_ban_dau_gia": "Hợp đồng mua bán tài sản đấu giá",
    "hd_the_chap": "Hợp đồng thế chấp QSDĐ",
}


def is_valid(label: str, ma: str = MA_CHUYEN_QUYEN) -> bool:
    return label in _by_label(ma)


def resolve(label: str, ma: str = MA_CHUYEN_QUYEN) -> tuple[str, str]:
    """Nhãn rút gọn → (target, componentName). componentName = mã TP-H05 khi có ô riêng, "" nếu đính kèm khác."""
    code, _ = _by_label(ma).get(label, (None, ""))
    if code:
        return ("existing", code)
    return ("supplementary", "")


def display_name(label: str) -> str:
    return _DISPLAY.get(label, "Tài liệu kèm theo")


def llm_options(ma: str = MA_CHUYEN_QUYEN) -> str:
    """Chuỗi liệt kê nhãn + mô tả để nhúng vào prompt phân loại."""
    return "\n".join(f"- {label}: {desc}" for label, _, desc in _rows(ma))
