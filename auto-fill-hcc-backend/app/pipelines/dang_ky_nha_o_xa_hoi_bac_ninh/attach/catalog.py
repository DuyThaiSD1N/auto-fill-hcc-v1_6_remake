"""Danh mục thành phần hồ sơ của eForm Bắc Ninh 2836 (đăng ký nhà ở xã hội).

Chỉ có MỘT thành phần bắt buộc: G17-KQ005445 "Giấy tờ chứng minh điều kiện về nhà ở...". Trong đó:
- Bản chính: Giấy xác nhận về điều kiện nhà ở (Mẫu 02) đã ký.
- Bản sao: bản sao chứng thực CCCD (2 vợ chồng) + Giấy chứng nhận kết hôn.
Giấy tờ chứng minh đối tượng (mục 8) không có dòng riêng → ô đính kèm bổ sung (supplementary).
"""

# (label, mã KQ hoặc None, slot, mô tả cho LLM)
CATALOG: list[tuple[str, str | None, str, str]] = [
    (
        "giay_xac_nhan_nha_o",
        "KQ005445",
        "banChinh",
        "Giấy xác nhận về điều kiện nhà ở theo Mẫu số 02 (đơn đã kê khai, ký) — bản chính.",
    ),
    (
        "cccd",
        "KQ005445",
        "banSao",
        "Bản sao chứng thực Căn cước công dân/CMND/hộ chiếu của người kê khai và vợ/chồng.",
    ),
    (
        "giay_ket_hon",
        "KQ005445",
        "banSao",
        "Bản sao Giấy chứng nhận kết hôn của hai vợ chồng.",
    ),
    (
        "khac",
        None,
        "banChinh",
        "Giấy tờ chứng minh đối tượng (mục 8) hoặc giấy tờ khác liên quan trực tiếp đến hồ sơ nhà ở xã hội.",
    ),
]

_BY_LABEL = {label: (kq, slot, desc) for label, kq, slot, desc in CATALOG}
LABELS = [label for label, _, _, _ in CATALOG]
_DISPLAY = {
    "giay_xac_nhan_nha_o": "Giấy xác nhận về điều kiện nhà ở (Mẫu 02)",
    "cccd": "Căn cước công dân",
    "giay_ket_hon": "Giấy chứng nhận kết hôn",
    "khac": "Giấy tờ kèm theo hồ sơ nhà ở xã hội",
}


def is_valid(label: str) -> bool:
    return label in _BY_LABEL


def resolve(label: str) -> tuple[str, str, str]:
    kq, slot, _ = _BY_LABEL.get(label, (None, "banChinh", ""))
    if kq:
        return "existing", kq, slot
    return "supplementary", "", slot


def slot_of(label: str) -> str:
    return _BY_LABEL.get(label, (None, "banChinh", ""))[1]


def display_name(label: str) -> str:
    return _DISPLAY.get(label, _DISPLAY["khac"])


def llm_options() -> str:
    return "\n".join(f"- {label}: {desc}" for label, _, _, desc in CATALOG)
