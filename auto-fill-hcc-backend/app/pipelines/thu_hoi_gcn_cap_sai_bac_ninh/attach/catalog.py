"""Catalog thành phần hồ sơ (Thu hồi GCN cấp sai — Bắc Ninh).

2 thành phần chính; CCCD/khác → ô đính kèm bổ sung.
"""

CATALOG: list[tuple[str, str | None, str]] = [
    ("van_ban_kien_nghi", "KQ004767",
     "Văn bản kiến nghị việc cấp Giấy chứng nhận không đúng quy định (thường là Biên bản họp gia đình)"),
    ("gcn", "KQ004768", "Giấy chứng nhận QSDĐ đã cấp (sổ đỏ/hồng) — bản gốc đang xin thu hồi"),
    ("cccd", None, "Căn cước công dân/CMND/thẻ căn cước/hộ chiếu"),
    ("khac", None, "Giấy tờ khác hoặc không xác định được loại"),
]

_BY_LABEL = {label: (kq, desc) for label, kq, desc in CATALOG}
LABELS = [label for label, _, _ in CATALOG]

_DISPLAY = {
    "van_ban_kien_nghi": "Văn bản kiến nghị (Biên bản họp GĐ)",
    "gcn": "Giấy chứng nhận QSDĐ (bản gốc)",
    "cccd": "Căn cước công dân",
    "khac": "Tài liệu kèm theo",
}


def is_valid(label: str) -> bool:
    return label in _BY_LABEL


def resolve(label: str) -> tuple[str, str]:
    kq, _ = _BY_LABEL.get(label, (None, ""))
    return ("existing", kq) if kq else ("supplementary", "")


def display_name(label: str) -> str:
    return _DISPLAY.get(label, "Tài liệu kèm theo")


def llm_options() -> str:
    return "\n".join(f"- {label}: {desc}" for label, _, desc in CATALOG)
