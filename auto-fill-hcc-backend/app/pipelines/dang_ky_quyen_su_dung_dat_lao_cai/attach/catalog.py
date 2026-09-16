"""Catalog thành phần hồ sơ 1.115668 (Lào Cai) — bảng "Thành phần hồ sơ" bước 3.

Bảng có 2 NHÁNH, mỗi nhánh mở bằng 1 dòng tiêu đề có checkbox:
  a) Chuyển đổi, chuyển nhượng, thừa kế, tặng cho, góp vốn…            → 12 dòng giấy tờ.
  b) Người sử dụng đất tặng cho QSDĐ cho Nhà nước/cộng đồng dân cư…   → 2 dòng biên bản (kèm GCN gốc).
Bên dưới còn khối "Thành phần hồ sơ khác nếu có" (danh sách Giấy tờ khác: tên tự nhập + tệp).

FE khoanh vùng dòng theo tiêu đề nhánh (sectionHeader) rồi khớp từ khóa đã fold (slotKeywords); từ khóa chọn
sao cho trong CÙNG nhánh chỉ khớp đúng một dòng. slotKey theo DÒNG (không theo nhãn) để nhiều tệp cùng dòng được
FE gom vào một lần chọn tệp. Giấy tờ không có dòng riêng → "Giấy tờ khác".
"""

BRANCH_A = "a"
BRANCH_B = "b"

SECTION_HEADERS = {
    BRANCH_A: "a) doi voi truong hop chuyen doi",
    BRANCH_B: "b) doi voi truong hop nguoi su dung dat tang cho",
}

# (nhánh, vị trí) → (từ khóa dòng đã fold, tên dòng rút gọn)
ROWS: dict[tuple[str, int], tuple[list[str], str]] = {
    (BRANCH_A, 1): (["don dang ky bien dong dat dai"], "Đơn đăng ký biến động đất đai (Mẫu số 24)"),
    (BRANCH_A, 2): (["giay chung nhan da cap"], "Giấy chứng nhận đã cấp"),
    (BRANCH_A, 3): (["van ban ve viec chuyen quyen su dung dat"], "Hợp đồng/văn bản chuyển quyền sử dụng đất"),
    (BRANCH_A, 4): (["ban hoac tang cho hoac de thua ke hoac gop von bang tai san"],
                    "Hợp đồng về tài sản trên đất thuê trả tiền hằng năm"),
    (BRANCH_A, 5): (["chuyen nhuong quyen khai thac khoang san"], "Văn bản chuyển nhượng quyền khai thác khoáng sản"),
    (BRANCH_A, 6): (["cho thue lai quyen su dung dat"], "Văn bản cho thuê, cho thuê lại QSDĐ trong dự án"),
    (BRANCH_A, 7): (["ban ve tach thua dat"], "Bản vẽ tách thửa, hợp thửa (Mẫu số 28)"),
    (BRANCH_A, 8): (["manh trich do ban do dia chinh"], "Mảnh trích đo bản đồ địa chính"),
    (BRANCH_A, 9): (["cap chung mot giay chung nhan"], "Văn bản thỏa thuận cấp chung một GCN"),
    (BRANCH_A, 10): (["van ban cua nguoi su dung dat dong y"], "Văn bản người sử dụng đất đồng ý"),
    (BRANCH_A, 11): (["ben nhan the chap"], "Văn bản bên nhận thế chấp đồng ý"),
    (BRANCH_A, 12): (["van ban ve viec dai dien"], "Văn bản về việc đại diện"),
    (BRANCH_B, 1): (["bien ban hop giua dai dien thon"], "Văn bản/biên bản họp thôn về tặng cho QSDĐ"),
    (BRANCH_B, 2): (["uy ban nhan dan cap xa voi nguoi su dung dat"], "Biên bản UBND cấp xã về tặng cho QSDĐ"),
}

# label → (dòng, tên hiển thị mặc định của tài liệu, mô tả cho LLM)
CATALOG: list[tuple[str, tuple[str, int], str, str]] = [
    ("don_dang_ky", (BRANCH_A, 1), "Đơn đăng ký biến động đất đai",
     "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 24 hoặc mẫu đơn biến động khác)"),
    ("gcn", (BRANCH_A, 2), "Giấy chứng nhận quyền sử dụng đất",
     "GIẤY CHỨNG NHẬN quyền sử dụng đất/quyền sở hữu nhà ở và tài sản gắn liền với đất (sổ đỏ/sổ hồng) có số "
     "seri, số vào sổ, thửa đất, tờ bản đồ — KHÔNG phải GCN đăng ký doanh nghiệp"),
    ("hop_dong_chuyen_quyen", (BRANCH_A, 3), "Hợp đồng chuyển quyền sử dụng đất",
     "Hợp đồng/văn bản chuyển đổi, chuyển nhượng, mua bán (kể cả hợp đồng mua bán tài sản đấu giá là quyền sử "
     "dụng đất), thừa kế, tặng cho, góp vốn bằng quyền sử dụng đất, tài sản gắn liền với đất (kèm lời chứng)"),
    ("hd_tai_san_dat_thue", (BRANCH_A, 4), "Hợp đồng về tài sản trên đất thuê",
     "Hợp đồng/văn bản bán, tặng cho, thừa kế, góp vốn bằng TÀI SẢN gắn liền với đất THUÊ của Nhà nước trả tiền "
     "thuê hằng năm"),
    ("vb_khoang_san", (BRANCH_A, 5), "Văn bản cho phép chuyển nhượng quyền khai thác khoáng sản",
     "Văn bản của cơ quan có thẩm quyền cho phép chuyển nhượng quyền khai thác khoáng sản"),
    ("vb_cho_thue_lai", (BRANCH_A, 6), "Văn bản cho thuê lại quyền sử dụng đất",
     "Hợp đồng/văn bản cho thuê, cho thuê lại quyền sử dụng đất trong dự án xây dựng kinh doanh kết cấu hạ tầng"),
    ("ban_ve_tach_hop_thua", (BRANCH_A, 7), "Bản vẽ tách thửa, hợp thửa",
     "Bản vẽ tách thửa đất, hợp thửa đất (Mẫu số 28)"),
    ("manh_trich_do", (BRANCH_A, 8), "Mảnh trích đo bản đồ địa chính",
     "Mảnh trích đo bản đồ địa chính thửa đất / phiếu đo đạc xác định lại kích thước, diện tích"),
    ("vb_cap_chung_gcn", (BRANCH_A, 9), "Văn bản thỏa thuận cấp chung GCN",
     "Văn bản thỏa thuận cấp chung một Giấy chứng nhận khi có nhiều người cùng nhận chuyển quyền"),
    ("vb_nguoi_sdd_dong_y", (BRANCH_A, 10), "Văn bản người sử dụng đất đồng ý",
     "Văn bản của NGƯỜI SỬ DỤNG ĐẤT đồng ý cho chủ sở hữu tài sản gắn liền với đất được chuyển nhượng/tặng "
     "cho/góp vốn tài sản"),
    ("vb_the_chap_dong_y", (BRANCH_A, 11), "Văn bản bên nhận thế chấp đồng ý",
     "Văn bản của BÊN NHẬN THẾ CHẤP (ngân hàng) đồng ý cho bên thế chấp được chuyển nhượng/tặng cho/góp vốn"),
    ("vb_dai_dien", (BRANCH_A, 12), "Giấy ủy quyền",
     "Giấy ủy quyền/hợp đồng ủy quyền/văn bản đại diện theo pháp luật dân sự khi làm thủ tục qua người đại diện"),
    ("gcn_dkdn", (BRANCH_A, 12), "Giấy chứng nhận đăng ký doanh nghiệp",
     "GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP (mã số doanh nghiệp, người đại diện theo pháp luật) của bất kỳ bên "
     "nào — chứng minh tư cách người đại diện"),
    ("bb_tang_cho_thon", (BRANCH_B, 1), "Biên bản họp thôn về tặng cho QSDĐ",
     "Văn bản của người sử dụng đất hoặc BIÊN BẢN HỌP giữa đại diện thôn, làng, bản, tổ dân phố với người sử "
     "dụng đất về việc TẶNG CHO quyền sử dụng đất cho Nhà nước/cộng đồng"),
    ("bb_tang_cho_ubnd", (BRANCH_B, 2), "Biên bản UBND cấp xã về tặng cho QSDĐ",
     "BIÊN BẢN giữa ỦY BAN NHÂN DÂN cấp xã với người sử dụng đất về việc TẶNG CHO quyền sử dụng đất"),
]

# Không có dòng riêng → "Giấy tờ khác" (tên = documentName).
OTHER: list[tuple[str, str, str]] = [
    ("hoa_don", "Hóa đơn thanh toán", "Hóa đơn giá trị gia tăng/hóa đơn thanh toán, biên lai, ủy nhiệm chi"),
    ("to_khai_thue", "Tờ khai thuế, lệ phí", "Tờ khai thuế thu nhập cá nhân, lệ phí trước bạ, thuế sử dụng đất"),
    ("khac", "Tài liệu kèm theo", "Giấy tờ khác (biên bản đấu giá, giấy tờ hộ tịch…) hoặc không xác định"),
]
# CCCD không phải thành phần hồ sơ của thủ tục → không đính kèm.
SKIPPED: list[tuple[str, str, str]] = [
    ("cccd", "Căn cước công dân", "CCCD/CMND/thẻ căn cước/hộ chiếu của bất kỳ ai"),
]

_ROW_OF = {label: row for label, row, _, _ in CATALOG}
_DISPLAY = {
    **{label: name for label, _, name, _ in CATALOG},
    **{label: name for label, name, _ in OTHER + SKIPPED},
}
OTHER_LABELS = {label for label, _, _ in OTHER}
SKIPPED_LABELS = {label for label, _, _ in SKIPPED}


def is_valid(label: str) -> bool:
    return label in _DISPLAY


def row_of(label: str) -> tuple[str, int] | None:
    return _ROW_OF.get(label)


def slot(row: tuple[str, int]) -> dict:
    branch, position = row
    keywords, name = ROWS[row]
    return {
        "slotKey": f"lc_115668_{branch}_{position}",
        "slotName": f"{branch}-{position}. {name}",
        "sectionHeader": SECTION_HEADERS[branch],
        "slotKeywords": list(keywords),
    }


def display_name(label: str) -> str:
    return _DISPLAY.get(label, "Tài liệu kèm theo")


def llm_options() -> str:
    lines = [f"- {label}: {desc}" for label, _, _, desc in CATALOG]
    lines += [f"- {label}: {desc}" for label, _, desc in OTHER + SKIPPED]
    return "\n".join(lines)
