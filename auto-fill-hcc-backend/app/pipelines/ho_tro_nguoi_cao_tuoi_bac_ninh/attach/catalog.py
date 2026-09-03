"""Catalog thành phần hồ sơ (attach-only) "[Bắc Ninh] Hỗ trợ Người cao tuổi…" (1.014589).

Cổng Liferay Bắc Ninh — FE khớp thành phần theo mã KQ (in trong dòng tiêu đề thành phần). Thủ tục này
CHỈ có 1 thành phần bắt buộc: Tờ khai đề nghị hưởng trợ cấp xã hội (Mẫu 01) → KQ001012 (01 bản chính).
Giấy tờ khác (CCCD, Kết quả tra cứu dân cư…) → ô đính kèm BỔ SUNG.
"""

# (label rút gọn, mã KQ | None nếu ô bổ sung, slotKey, mô tả cho LLM)
CATALOG: list[tuple[str, str | None, str, str]] = [
    ("to_khai", "KQ001012", "banChinh",
     "Tờ khai đề nghị hưởng trợ cấp xã hội — Mẫu số 01 (NQ 103/2025/NQ-HĐND). Có tiêu đề 'TỜ KHAI…' / 'ĐỀ "
     "NGHỊ HƯỞNG TRỢ CẤP XÃ HỘI', kê khai người cao tuổi, có xác nhận UBND xã. GỒM cả trường hợp scan chung "
     "hồ sơ (tờ khai + CCCD) — nếu có tờ khai thì xếp vào đây."),
    # --- không có ô riêng → ô đính kèm BỔ SUNG ---
    ("cccd", None, "banChinh", "Căn cước công dân/CMND/thẻ căn cước/hộ chiếu của người cao tuổi."),
    ("kq_dan_cu", None, "banChinh",
     "Kết quả kiểm tra/tra cứu thông tin công dân trong CSDLQG về dân cư."),
    ("khac", None, "banChinh", "Giấy tờ khác hoặc không xác định được loại."),
]

_BY_LABEL = {label: (kq, slot, desc) for label, kq, slot, desc in CATALOG}
LABELS = [label for label, _, _, _ in CATALOG]

_DISPLAY = {
    "to_khai": "Tờ khai đề nghị hưởng trợ cấp xã hội (Mẫu 01)",
    "cccd": "Căn cước công dân",
    "kq_dan_cu": "Kết quả tra cứu thông tin dân cư",
    "khac": "Tài liệu kèm theo",
}


def is_valid(label: str) -> bool:
    return label in _BY_LABEL


def resolve(label: str) -> tuple[str, str, str]:
    """Nhãn rút gọn → (target, componentName, slotKey)."""
    kq, slot, _ = _BY_LABEL.get(label, (None, "banChinh", ""))
    if kq:
        return ("existing", kq, slot)
    return ("supplementary", "", slot)


def display_name(label: str) -> str:
    return _DISPLAY.get(label, "Tài liệu kèm theo")


def llm_options() -> str:
    return "\n".join(f"- {label}: {desc}" for label, _, _, desc in CATALOG)
