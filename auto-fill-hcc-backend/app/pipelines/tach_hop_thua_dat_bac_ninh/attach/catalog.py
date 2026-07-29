"""Catalog thành phần hồ sơ "[Bắc Ninh] Tách thửa đất/hợp thửa đất".

Cơ chế: LLM phân loại mỗi tài liệu → NHÃN RÚT GỌN → BE map sang componentName CHI TIẾT (mã KQ, in
trong dòng tiêu đề mỗi thành phần) hoặc ô đính kèm BỔ SUNG → FE khớp đúng ô để upload.

Form có 4 thành phần: (1) Đơn Mẫu 21, (3) GCN đã cấp, (4) Văn bản cơ quan thẩm quyền, (5) Bản vẽ Mẫu 22.
"""

# (label rút gọn, componentName = mã KQ hoặc None nếu vào ô bổ sung, mô tả ngắn cho LLM)
CATALOG: list[tuple[str, str | None, str]] = [
    ("don_tach_thua", "KQ006017",
     "Đơn đề nghị tách thửa đất, hợp thửa đất theo Mẫu số 21 — bản kê khai của người sử dụng đất, có "
     "tiêu đề 'ĐƠN ĐỀ NGHỊ TÁCH THỬA ĐẤT, HỢP THỬA ĐẤT'"),
    ("gcn", "KQ004751",
     "Giấy chứng nhận đã cấp (sổ đỏ/sổ hồng) — có 'số vào sổ cấp GCN', số thửa, tờ bản đồ, cơ quan cấp"),
    ("van_ban_co_quan", "KQ004752",
     "Các văn bản của cơ quan có thẩm quyền thể hiện nội dung tách thửa/hợp thửa (quyết định/thông báo…)"),
    ("ban_ve_tach_thua", "KQ006018",
     "Bản vẽ tách thửa đất, hợp thửa đất lập theo Mẫu số 22 (bản vẽ kỹ thuật thửa đất, sơ đồ phân chia)"),
    # --- không có ô riêng → ô đính kèm BỔ SUNG ---
    ("cccd", None, "Căn cước công dân/CMND/thẻ căn cước/hộ chiếu của chủ đất"),
    ("khac", None, "Giấy tờ khác hoặc không xác định được loại"),
]

_BY_LABEL = {label: (kq, desc) for label, kq, desc in CATALOG}
LABELS = [label for label, _, _ in CATALOG]

_DISPLAY = {
    "don_tach_thua": "Đơn đề nghị tách/hợp thửa (Mẫu 21)",
    "gcn": "Giấy chứng nhận đã cấp",
    "van_ban_co_quan": "Văn bản cơ quan có thẩm quyền",
    "ban_ve_tach_thua": "Bản vẽ tách/hợp thửa (Mẫu 22)",
    "cccd": "Căn cước công dân",
    "khac": "Tài liệu kèm theo",
}


def is_valid(label: str) -> bool:
    return label in _BY_LABEL


def resolve(label: str) -> tuple[str, str]:
    kq, _ = _BY_LABEL.get(label, (None, ""))
    if kq:
        return ("existing", kq)
    return ("supplementary", "")


def display_name(label: str) -> str:
    return _DISPLAY.get(label, "Tài liệu kèm theo")


def llm_options() -> str:
    return "\n".join(f"- {label}: {desc}" for label, _, desc in CATALOG)
