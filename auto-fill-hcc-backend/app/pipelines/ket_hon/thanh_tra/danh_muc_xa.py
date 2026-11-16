"""Danh sách phường / xã HIỆN HÀNH của một tỉnh — ngữ cảnh cho thanh tra nơi cư trú khi ô xã của lượt trích không
chọn được trên cổng (tên viết tắt, thiếu dấu, bị OCR đọc lệch / cắt chữ)."""

import difflib
import re
import unicodedata
from functools import lru_cache

from app.locations.catalog import PROVINCES, WARDS_BY_SLUG
from app.pipelines._shared import area_remap

_NEAR_RATIO = 0.75
_LABEL_RE = re.compile(r"^(phuong|xa|thi tran|dac khu|p|x|tt)\.?\s+")


def _fold(text) -> str:
    text = unicodedata.normalize("NFD", str(text or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", text.replace("Đ", "D").replace("đ", "d").lower()).strip()


def _bare(text) -> str:
    return _LABEL_RE.sub("", _fold(text))


@lru_cache(maxsize=None)
def wards_of(province: str) -> tuple[str, ...]:
    """Tên phường / xã hiện hành của tỉnh (tên tỉnh viết kiểu nào danh mục nhận được thì nhận); () khi không rõ tỉnh.
    Hậu tố "- <thành phố cũ>" của tên phường không thuộc phần tên mà mapper điền."""
    name = area_remap.canonical_province(province)
    for item in PROVINCES:
        if item["name"] == name:
            wards = WARDS_BY_SLUG.get(item["slug"], {}).get("communes") or []
            return tuple(ward.split(" - ")[0].strip() for ward in wards)
    return ()


def _syllables(written: str) -> list[str]:
    """Các tiếng của tên trên giấy; chữ viết tắt dính liền tách ở chỗ đổi sang chữ hoa ("yP" → y, p; "KĐình" → k, đình)."""
    text = unicodedata.normalize("NFC", str(written or ""))
    spaced = "".join(
        f" {ch}" if at and ch.isupper() and text[at - 1].isalpha() and (
            text[at - 1].islower() or (at + 1 < len(text) and text[at + 1].islower())) else ch
        for at, ch in enumerate(text))
    return _bare(spaced).split()


def _likeness(written: str, listed: str) -> int:
    """Mức giống giữa tên trên giấy và một tên trong danh sách: 3 = trùng khi bỏ dấu, hoặc từng tiếng trên giấy là
    phần đầu của đúng tiếng đó trong tên (viết tắt); 2 = phần còn lại sau khi OCR cắt mất chữ đầu / cuối; 1 = lệch vài
    ký tự; 0 = không giống."""
    a, b = _bare(written), _bare(listed)
    if not a or not b:
        return 0
    short, full, compact = _syllables(written), b.split(), a.replace(" ", "")
    if a == b or (len(compact) >= 2 and compact == "".join(word[0] for word in full)) or (
            len(short) == len(full) >= 2 and all(whole.startswith(part) for part, whole in zip(short, full))):
        return 3
    if len(a) >= 4 and (b.endswith(a) or b.startswith(a)):
        return 2
    return 1 if difflib.SequenceMatcher(None, a, b).ratio() >= _NEAR_RATIO else 0


def only_match(written: str, province: str, answer: str) -> str:
    """Chốt chặn cho câu trả lời của model (không tự chọn tên): tên model trả phải có trong danh sách của tỉnh, giống
    tên trên giấy, và là tên DUY NHẤT của tỉnh giống ở mức cao nhất → tên đó; ngược lại ""."""
    wards = wards_of(province)
    chosen = next((ward for ward in wards if _bare(ward) == _bare(answer)), "")
    level = _likeness(written, chosen) if chosen else 0
    if not level:
        return ""
    levels = [_likeness(written, ward) for ward in wards]
    return chosen if level == max(levels) and levels.count(level) == 1 else ""


def has_like(written: str, province: str) -> bool:
    """Tỉnh có ít nhất một tên phường / xã giống tên trên giấy."""
    return any(_likeness(written, ward) for ward in wards_of(province))
