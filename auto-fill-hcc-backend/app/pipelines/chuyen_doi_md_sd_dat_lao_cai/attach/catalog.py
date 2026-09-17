"""Catalog thành phần hồ sơ 1.115651 (Lào Cai) — bảng "Thành phần hồ sơ" bước 3.

Bảng chia 4 NHÓM, mỗi nhóm mở bằng 1 dòng tiêu đề có checkbox; nhóm chọn theo MẪU ĐƠN:
  (1) Chuyển mục đích sử dụng đất            — Đơn Mẫu số 02 → 2 dòng.
  (2) Chuyển hình thức sử dụng đất           — Đơn Mẫu số 03 → 3 dòng.
  (3) Gia hạn sử dụng đất khi hết thời hạn   — Đơn Mẫu số 17 → 4 dòng (2 dòng GCN trùng nhau).
  (4) Điều chỉnh thời hạn sử dụng đất dự án  — Đơn Mẫu số 18 → 4 dòng.
Bên dưới còn khối "Thông tin khác" với danh sách "Giấy tờ khác" (tên tự nhập + tệp).

FE khoanh vùng dòng theo tiêu đề nhóm (sectionHeader) rồi khớp từ khóa đã fold (slotKeywords); từ khóa chọn sao
cho trong CÙNG nhóm chỉ khớp đúng một dòng (dòng "giấy chứng nhận" lặp lại ở cả 4 nhóm). slotKey theo DÒNG để nhiều
tệp cùng dòng được FE gom vào một lần chọn tệp. Giấy tờ không có dòng trong nhóm → "Giấy tờ khác".
"""

GROUP_1 = "1"
GROUP_2 = "2"
GROUP_3 = "3"
GROUP_4 = "4"

SECTION_HEADERS = {
    GROUP_1: "(1) ho so de nghi chuyen muc dich su dung dat",
    GROUP_2: "(2) ho so de nghi chuyen hinh thuc su dung dat",
    GROUP_3: "(3) ho so de nghi gia han su dung dat",
    GROUP_4: "(4) ho so de nghi dieu chinh thoi han su dung dat",
}

# (nhóm, vị trí) → (từ khóa dòng đã fold, tên dòng rút gọn)
ROWS: dict[tuple[str, int], tuple[list[str], str]] = {
    (GROUP_1, 1): (["don theo mau so 02"], "Đơn Mẫu số 02"),
    (GROUP_1, 2): (["khoan 21 dieu 3"], "Giấy chứng nhận / giấy tờ Điều 137 / quyết định giao đất"),
    (GROUP_2, 1): (["don theo mau so 03"], "Đơn Mẫu số 03"),
    (GROUP_2, 2): (["khoan 21 dieu 3"], "Giấy chứng nhận / giấy tờ Điều 137"),
    (GROUP_2, 3): (["quyet dinh cho thue dat"], "Quyết định giao đất, cho thuê đất, cho phép chuyển mục đích"),
    (GROUP_3, 1): (["don theo mau so 17"], "Đơn Mẫu số 17"),
    # Cổng lặp 2 dòng "Một trong các giấy chứng nhận…" y hệt ở nhóm (3) → FE lấy dòng khớp ĐẦU TIÊN (vị trí 2).
    (GROUP_3, 2): (["khoan 21 dieu 3"], "Giấy chứng nhận"),
    (GROUP_3, 4): (["cho phep gia han thoi han hoat dong"], "Văn bản gia hạn/thời hạn hoạt động dự án"),
    (GROUP_4, 1): (["don theo mau so 18"], "Đơn Mẫu số 18"),
    (GROUP_4, 2): (["thay doi thoi han hoat dong"], "Văn bản cho phép thay đổi thời hạn hoạt động dự án"),
    (GROUP_4, 3): (["mot trong cac giay chung nhan"], "Giấy chứng nhận"),
    (GROUP_4, 4): (["quyet dinh giao dat"], "Quyết định giao đất, cho thuê đất, cho phép chuyển mục đích"),
}

# Đơn → nhóm hồ sơ.
FORM_GROUP = {"don_mau_02": GROUP_1, "don_mau_03": GROUP_2, "don_mau_17": GROUP_3, "don_mau_18": GROUP_4}

# label → {nhóm: vị trí dòng}; nhóm không có dòng cho nhãn → "Giấy tờ khác".
ROUTES: dict[str, dict[str, int]] = {
    "don_mau_02": {GROUP_1: 1},
    "don_mau_03": {GROUP_2: 1},
    "don_mau_17": {GROUP_3: 1},
    "don_mau_18": {GROUP_4: 1},
    "gcn": {GROUP_1: 2, GROUP_2: 2, GROUP_3: 2, GROUP_4: 3},
    # Dòng giấy chứng nhận nhóm (1) ghi cả "quyết định giao đất… và tài liệu đáp ứng tiêu chí chuyển mục đích".
    "quyet_dinh_giao_dat": {GROUP_1: 2, GROUP_2: 3, GROUP_4: 4},
    "tai_lieu_dieu_kien": {GROUP_1: 2},
    "vb_thoi_han_du_an": {GROUP_3: 4},
    "vb_thay_doi_thoi_han_du_an": {GROUP_4: 2},
}

# (label, tên hiển thị mặc định, mô tả cho LLM)
LABELS: list[tuple[str, str, str]] = [
    ("don_mau_02", "Đơn đề nghị chuyển mục đích sử dụng đất",
     "ĐƠN đề nghị/xin CHUYỂN MỤC ĐÍCH sử dụng đất (Mẫu số 02)"),
    ("don_mau_03", "Đơn đề nghị chuyển hình thức sử dụng đất",
     "ĐƠN đề nghị CHUYỂN HÌNH THỨC sử dụng đất, vd từ thuê đất trả tiền hằng năm sang trả một lần (Mẫu số 03)"),
    ("don_mau_17", "Đơn đề nghị gia hạn sử dụng đất", "ĐƠN đề nghị GIA HẠN sử dụng đất (Mẫu số 17)"),
    ("don_mau_18", "Đơn đề nghị điều chỉnh thời hạn sử dụng đất",
     "ĐƠN đề nghị ĐIỀU CHỈNH THỜI HẠN sử dụng đất của dự án đầu tư (Mẫu số 18)"),
    ("gcn", "Giấy chứng nhận quyền sử dụng đất",
     "GIẤY CHỨNG NHẬN quyền sử dụng đất/quyền sở hữu nhà ở, tài sản gắn liền với đất, hoặc giấy tờ về quyền sử dụng "
     "đất theo Điều 137 Luật Đất đai — KHÔNG phải GCN đăng ký doanh nghiệp"),
    ("quyet_dinh_giao_dat", "Quyết định giao đất, cho thuê đất",
     "QUYẾT ĐỊNH giao đất, cho thuê đất, cho phép chuyển mục đích sử dụng đất của cơ quan nhà nước"),
    ("tai_lieu_dieu_kien", "Tài liệu đáp ứng điều kiện chuyển mục đích",
     "Tài liệu chứng minh đáp ứng tiêu chí, điều kiện chuyển mục đích đất trồng lúa, đất rừng (khoản 1 Điều 46 NĐ 102)"),
    ("vb_thoi_han_du_an", "Văn bản về thời hạn hoạt động dự án",
     "Văn bản cho phép GIA HẠN thời gian hoạt động của dự án đầu tư hoặc thể hiện thời hạn hoạt động dự án (quyết định "
     "chủ trương đầu tư, giấy chứng nhận đăng ký đầu tư)"),
    ("vb_thay_doi_thoi_han_du_an", "Văn bản cho phép thay đổi thời hạn dự án",
     "Văn bản của cơ quan có thẩm quyền cho phép THAY ĐỔI (điều chỉnh) thời hạn hoạt động của dự án đầu tư"),
    ("ban_do", "Mảnh đo đạc chỉnh lý bản đồ địa chính",
     "Mảnh đo đạc chỉnh lý/trích đo bản đồ địa chính, sơ đồ khu đất, bản đồ kèm quyết định"),
    ("gcn_dkdn", "Giấy chứng nhận đăng ký doanh nghiệp", "GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP"),
    ("vb_uy_quyen", "Giấy ủy quyền", "Giấy ủy quyền/văn bản cử người đi nộp hồ sơ"),
    ("cccd", "Căn cước công dân", "CCCD/CMND/thẻ căn cước/hộ chiếu của bất kỳ ai"),
    ("khac", "Tài liệu kèm theo", "Giấy tờ khác hoặc không xác định được loại"),
]

# CCCD không phải thành phần hồ sơ của thủ tục → không đính kèm.
SKIPPED_LABELS = {"cccd"}

_DISPLAY = {label: name for label, name, _ in LABELS}


def is_valid(label: str) -> bool:
    return label in _DISPLAY


def row_for(label: str, group: str) -> tuple[str, int] | None:
    position = ROUTES.get(label, {}).get(group)
    return (group, position) if position else None


def slot(row: tuple[str, int]) -> dict:
    group, position = row
    keywords, name = ROWS[row]
    return {
        "slotKey": f"lc_115651_{group}_{position}",
        "slotName": f"({group})-{position}. {name}",
        "sectionHeader": SECTION_HEADERS[group],
        "slotKeywords": list(keywords),
    }


def display_name(label: str) -> str:
    return _DISPLAY.get(label, "Tài liệu kèm theo")


def llm_options() -> str:
    return "\n".join(f"- {label}: {desc}" for label, _, desc in LABELS)
