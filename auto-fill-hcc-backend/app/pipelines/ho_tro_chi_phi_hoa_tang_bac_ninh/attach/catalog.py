"""Danh mục thành phần hồ sơ của eForm Bắc Ninh 1.014582."""

CATALOG: list[tuple[str, str | None, str, str]] = [
    (
        "to_khai",
        "KQ001004",
        "banChinh",
        "Đơn/Tờ khai đề nghị hỗ trợ kinh phí hỏa táng theo Mẫu số 01, có thông tin người chết và người đứng ra hỏa táng.",
    ),
    (
        "hop_dong_hoa_tang",
        "KQ001005",
        "banChinh",
        "Hợp đồng dịch vụ hỏa táng/điện táng ký với cơ sở hỏa táng.",
    ),
    ("bien_ban_uy_quyen", None, "banChinh", "Biên bản/Văn bản ủy quyền nhận hỗ trợ chi phí hỏa táng."),
    ("trich_luc_khai_tu", None, "banChinh", "Trích lục khai tử, Giấy báo tử hoặc Giấy chứng tử."),
    ("hoa_don_hoa_tang", None, "banChinh", "Hóa đơn/chứng từ thanh toán dịch vụ hỏa táng hoặc điện táng."),
    ("cccd", None, "banChinh", "Căn cước công dân/CMND/hộ chiếu của người liên quan trong hồ sơ."),
    ("khac", None, "banChinh", "Giấy tờ khác có nội dung liên quan trực tiếp đến hồ sơ hỗ trợ hỏa táng."),
]

_BY_LABEL = {label: (kq, slot, desc) for label, kq, slot, desc in CATALOG}
LABELS = [label for label, _, _, _ in CATALOG]
_DISPLAY = {
    "to_khai": "Đơn đề nghị hỗ trợ kinh phí hỏa táng (Mẫu 01)",
    "hop_dong_hoa_tang": "Hợp đồng dịch vụ hỏa táng",
    "bien_ban_uy_quyen": "Biên bản ủy quyền nhận hỗ trợ hỏa táng",
    "trich_luc_khai_tu": "Trích lục khai tử",
    "hoa_don_hoa_tang": "Hóa đơn dịch vụ hỏa táng",
    "cccd": "Căn cước công dân",
    "khac": "Giấy tờ kèm theo hồ sơ hỏa táng",
}


def is_valid(label: str) -> bool:
    return label in _BY_LABEL


def resolve(label: str) -> tuple[str, str, str]:
    kq, slot, _ = _BY_LABEL.get(label, (None, "banChinh", ""))
    if kq:
        return "existing", kq, slot
    return "supplementary", "", slot


def display_name(label: str) -> str:
    return _DISPLAY.get(label, _DISPLAY["khac"])


def llm_options() -> str:
    return "\n".join(f"- {label}: {desc}" for label, _, _, desc in CATALOG)
