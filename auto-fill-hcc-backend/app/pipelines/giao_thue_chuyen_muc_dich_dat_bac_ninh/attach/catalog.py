"""Catalog thành phần hồ sơ (giao/thuê/chuyển mục đích/gia hạn SDĐ — Bắc Ninh).

Cơ chế: LLM phân loại mỗi tài liệu → NHÃN RÚT GỌN (một trong LABELS). BE map nhãn rút gọn →
componentName CHI TIẾT (mã KQ để FE khớp đúng ô) hoặc ô đính kèm bổ sung. FE chỉ cần tìm đúng
tên (mã KQ) để upload.

Danh mục form có 15 thành phần, phần lớn là biến thể pháp lý cho tổ chức/dự án/rừng. Ở đây gom
về các nhãn PHÂN BIỆT ĐƯỢC + đại diện cho từng cụm (giảm nhầm lẫn cho LLM); cá nhân chủ yếu dùng
gcn / cccd / uy_quyen / don_de_nghi.
"""

# (label rút gọn, componentName = mã KQ hoặc None nếu vào ô bổ sung, mô tả ngắn cho LLM)
CATALOG: list[tuple[str, str | None, str]] = [
    ("gcn", "KQ005881",
     "Giấy chứng nhận QSDĐ/quyền sở hữu nhà ở/tài sản gắn liền với đất (sổ đỏ/sổ hồng) đã cấp; "
     "hoặc quyết định giao đất/cho thuê đất/cho phép chuyển mục đích của cơ quan nhà nước"),
    ("don_mau_01", "KQ005868", "Đơn theo Mẫu số 01"),
    ("don_mau_04", "KQ005880", "Đơn theo Mẫu số 04"),
    ("tang_dat_mat", "KQ005866",
     "Phương án sử dụng tầng đất mặt theo Mẫu số 26 (chuyển mục đích đất chuyên trồng lúa)"),
    ("du_an_giao_rung", "KQ005870",
     "Dự án đầu tư đối với khu rừng đề nghị giao; báo cáo/bản đồ hiện trạng rừng"),
    ("dau_gia_thue_rung", "KQ005869",
     "Kết quả/biên bản/danh sách đấu giá cho thuê rừng"),
    ("phuong_an_su_dung_dat", "KQ005875",
     "Phương án sử dụng đất đã được phê duyệt (tổ chức kinh tế/đơn vị sự nghiệp/công ty nông-lâm/đất thu hồi)"),
    ("van_ban_dau_tu", "KQ005873",
     "Văn bản phê duyệt dự án đầu tư/chấp thuận chủ trương đầu tư/kết quả lựa chọn nhà đầu tư (PPP)"),
    ("gcn_dieu137", "KQ005874",
     "Giấy chứng nhận/giấy tờ theo Điều 137 Luật Đất đai (CHỈ khi tài liệu nêu rõ Điều 137)"),
    # --- không có ô riêng trong danh mục → ô đính kèm BỔ SUNG ---
    ("cccd", None, "Căn cước công dân/CMND/thẻ căn cước/hộ chiếu"),
    ("uy_quyen", None, "Văn bản/giấy/hợp đồng ủy quyền"),
    ("don_de_nghi", None,
     "Đơn đề nghị giao/thuê/chuyển mục đích/gia hạn sử dụng đất (Mẫu 02) — bản kê khai của người dân"),
    ("khac", None, "Giấy tờ khác hoặc không xác định được loại"),
]

_BY_LABEL = {label: (kq, desc) for label, kq, desc in CATALOG}
LABELS = [label for label, _, _ in CATALOG]

# Nhãn hiển thị mặc định (documentName) khi không có tên cụ thể.
_DISPLAY = {
    "gcn": "Giấy chứng nhận QSDĐ",
    "don_mau_01": "Đơn theo Mẫu số 01",
    "don_mau_04": "Đơn theo Mẫu số 04",
    "tang_dat_mat": "Phương án tầng đất mặt (Mẫu 26)",
    "du_an_giao_rung": "Dự án đầu tư giao rừng",
    "dau_gia_thue_rung": "Kết quả đấu giá thuê rừng",
    "phuong_an_su_dung_dat": "Phương án sử dụng đất",
    "van_ban_dau_tu": "Văn bản phê duyệt đầu tư",
    "gcn_dieu137": "Giấy tờ theo Điều 137",
    "cccd": "Căn cước công dân",
    "uy_quyen": "Văn bản ủy quyền",
    "don_de_nghi": "Đơn đề nghị",
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
