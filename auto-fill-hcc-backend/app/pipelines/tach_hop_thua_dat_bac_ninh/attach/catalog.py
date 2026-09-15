"""Catalog thành phần hồ sơ "[Bắc Ninh] Tách thửa đất/hợp thửa đất".

Cơ chế: LLM phân loại mỗi tài liệu → NHÃN RÚT GỌN → BE map sang componentName (mã thành phần in
trong dòng tiêu đề mỗi hàng trên cổng) hoặc ô đính kèm BỔ SUNG → FE khớp đúng hàng để upload.

Form có 4 thành phần trên cổng Bắc Ninh (khớp theo MÃ TP-H05.0000xx hiện trong dòng tiêu đề, KHÔNG
phải mã KQ kết quả — cổng đính kèm hiển thị mã TP-H05):
  TP-H05.000032 Mẫu số 22.  Đơn đề nghị tách thửa đất, hợp thửa đất
  TP-H05.000033 Mẫu số 22a. Bản vẽ tách thửa đất, hợp thửa đất
  TP-H05.000040 Giấy chứng nhận đã cấp
  TP-H05.000047 Các văn bản của cơ quan có thẩm quyền thể hiện nội dung tách/hợp thửa (nếu có)
"""

# (label rút gọn, componentName = MÃ TP-H05 (khớp text hàng) hoặc None nếu vào ô bổ sung, mô tả cho LLM)
CATALOG: list[tuple[str, str | None, str]] = [
    ("don_tach_thua", "TP-H05.000032",
     "Đơn đề nghị tách thửa đất, hợp thửa đất (Mẫu số 22) — bản kê khai của người sử dụng đất, có "
     "tiêu đề 'ĐƠN ĐỀ NGHỊ TÁCH THỬA ĐẤT, HỢP THỬA ĐẤT'"),
    ("gcn", "TP-H05.000040",
     "Giấy chứng nhận đã cấp (sổ đỏ/sổ hồng) — có 'số vào sổ cấp GCN', số thửa, tờ bản đồ, cơ quan cấp"),
    ("van_ban_co_quan", "TP-H05.000047",
     "Các văn bản của cơ quan có thẩm quyền thể hiện nội dung tách thửa/hợp thửa (quyết định/thông báo…)"),
    ("ban_ve_tach_thua", "TP-H05.000033",
     "Bản vẽ tách thửa đất, hợp thửa đất (Mẫu số 22a) — bản vẽ kỹ thuật thửa đất, sơ đồ phân chia"),
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
