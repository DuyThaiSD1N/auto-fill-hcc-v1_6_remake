"""Catalog thành phần hồ sơ 1.115667 (Lào Cai) — bảng "Thành phần hồ sơ" bước 3.

Bảng có 2 NHÁNH, mỗi nhánh 1 dòng tiêu đề (có checkbox) + 8 dòng giấy tờ:
  a) Chủ đầu tư dự án nộp hồ sơ đăng ký, cấp GCN cho người nhận chuyển nhượng.
  b) Người nhận chuyển nhượng trực tiếp thực hiện.
Hai nhánh có CÙNG loại giấy tờ, tên dòng gần như trùng (vd "Đơn đăng ký biến động… Mẫu số 24" ở cả a-1 và
b-1), chỉ khác thứ tự. Vì vậy FE phải khoanh vùng dòng theo tiêu đề nhánh (sectionHeader) rồi mới khớp
từ khóa (slotKeywords); khớp text toàn bảng sẽ luôn rơi vào nhánh a) ở trên.

Từ khóa đã fold (bỏ dấu, thường), chọn sao cho trong CÙNG một nhánh chỉ khớp đúng một dòng.
"""

BRANCH_A = "a"
BRANCH_B = "b"

SECTION_HEADERS = {
    BRANCH_A: "a) doi voi truong hop chu dau tu du an nop ho so",
    BRANCH_B: "b) doi voi truong hop nguoi nhan chuyen nhuong",
}

# label → (vị trí dòng nhánh a, vị trí dòng nhánh b, từ khóa dòng, tên hiển thị mặc định, mô tả cho LLM)
CATALOG: list[tuple[str, int, int, list[str], str, str]] = [
    ("don_dang_ky", 1, 1, ["don dang ky bien dong dat dai"],
     "Đơn đăng ký biến động đất đai (Mẫu số 24)",
     "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 24, QĐ 47/2026/QĐ-UBND hoặc mẫu "
     "đơn đăng ký biến động khác) — tiêu đề 'ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI…'"),
    ("hop_dong", 4, 2, ["hop dong chuyen nhuong quyen su dung dat"],
     "Hợp đồng chuyển nhượng QSDĐ",
     "Hợp đồng chuyển nhượng/mua bán quyền sử dụng đất, quyền sở hữu nhà ở, công trình xây dựng trong dự "
     "án (kể cả Lời chứng của công chứng viên đi kèm trong cùng file)"),
    ("ban_giao", 5, 3, ["bien ban ban giao nha"],
     "Biên bản bàn giao nhà, đất",
     "Biên bản bàn giao nhà, đất, công trình xây dựng; hoặc BIÊN BẢN KIỂM TRA HIỆN TRẠNG CĂN/lô có kết "
     "luận đủ điều kiện giao, nhận nhà giữa chủ đầu tư và bên mua"),
    ("nghiem_thu", 2, 4, ["da duoc nghiem thu dua vao khai thac"],
     "Biên bản nghiệm thu đưa vào sử dụng",
     "Văn bản/Biên bản NGHIỆM THU hoàn thành công trình, hạng mục công trình đưa vào khai thác, sử dụng"),
    ("du_dieu_kien", 3, 5, ["du dieu kien duoc chuyen nhuong cho ca nhan tu xay dung"],
     "Văn bản đủ điều kiện chuyển nhượng",
     "Văn bản của cơ quan có thẩm quyền về việc ĐỦ ĐIỀU KIỆN được chuyển nhượng quyền sử dụng đất cho cá "
     "nhân tự xây dựng nhà ở (đất đã có hạ tầng kỹ thuật)"),
    ("gcn_chu_dau_tu", 6, 6, ["giay chung nhan da cap cho chu dau tu"],
     "Giấy chứng nhận đã cấp cho chủ đầu tư",
     "GIẤY CHỨNG NHẬN quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất đã cấp cho CHỦ ĐẦU TƯ dự "
     "án (người sử dụng đất là công ty/chủ đầu tư; có số vào sổ, số thửa, tờ bản đồ)"),
    ("chung_tu_tai_chinh", 7, 7, ["chung tu chung minh viec hoan thanh nghia vu tai chinh"],
     "Chứng từ hoàn thành nghĩa vụ tài chính",
     "Chứng từ, biên lai, giấy nộp tiền chứng minh đã hoàn thành NGHĨA VỤ TÀI CHÍNH (tiền sử dụng đất, "
     "thuế, lệ phí) khi dự án được điều chỉnh quy hoạch"),
    ("so_do", 8, 8, ["so do tai san gan lien voi dat"],
     "Sơ đồ tài sản gắn liền với đất",
     "Sơ đồ nhà/tài sản gắn liền với đất, sơ đồ thửa đất vẽ RIÊNG thành một tài liệu"),
]

# Không có dòng riêng trong bảng → bỏ qua, báo người dùng.
UNSLOTTED: list[tuple[str, str, str]] = [
    ("cccd", "Căn cước công dân", "CCCD/CMND/thẻ căn cước/hộ chiếu của bất kỳ ai"),
    ("khac", "Tài liệu khác", "Giấy tờ khác hoặc không xác định được loại"),
]

_ROW = {label: (row_a, row_b, keywords, display) for label, row_a, row_b, keywords, display, _ in CATALOG}
_DISPLAY = {**{label: v[3] for label, v in _ROW.items()}, **{label: name for label, name, _ in UNSLOTTED}}
LABELS = [label for label, *_ in CATALOG] + [label for label, _, _ in UNSLOTTED]


def is_valid(label: str) -> bool:
    return label in _DISPLAY


def has_slot(label: str) -> bool:
    return label in _ROW


def slot(branch: str, label: str) -> dict | None:
    """Nhãn → ô đính kèm của nhánh. slotName in kèm mã dòng (vd "b-2") để thông báo cho người dùng dễ đọc."""
    row = _ROW.get(label)
    if not row or branch not in SECTION_HEADERS:
        return None
    row_a, row_b, keywords, display = row
    position = row_a if branch == BRANCH_A else row_b
    return {
        "slotKey": f"lc_115667_{branch}_{label}",
        # Thứ tự trong bảng: tiêu đề a) = 0, a-1..a-8 = 1..8, tiêu đề b) = 9, b-1..b-8 = 10..17.
        "slotIndex": position if branch == BRANCH_A else 9 + position,
        "slotName": f"{branch}-{position}. {display}",
        "sectionHeader": SECTION_HEADERS[branch],
        "slotKeywords": list(keywords),
    }


def display_name(label: str) -> str:
    return _DISPLAY.get(label, "Tài liệu kèm theo")


def llm_options() -> str:
    lines = [f"- {label}: {desc}" for label, *_, desc in CATALOG]
    lines += [f"- {label}: {desc}" for label, _, desc in UNSLOTTED]
    return "\n".join(lines)
