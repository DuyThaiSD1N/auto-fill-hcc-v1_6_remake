"""Helper dùng chung cho các pipeline: chuẩn hóa tên tài liệu, fold dấu tiếng Việt.

Đặt ở _shared vì nhiều thủ tục (chung_thuc_ban_sao, chung_thuc_giao_dich_tai_san...) cùng dùng.
"""
import re
import unicodedata
from pathlib import Path

GENERIC_DOCUMENT_TYPE = "Tài liệu chứng thực"

_GENERIC_FILE_RE = re.compile(
    r"^(\d+|img|image|photo|scan|screenshot|zalo|z\d+|file|document|tai lieu|tài liệu)[\s_\-0-9:]*$",
    re.I,
)


def fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def normalize_document_name(raw: str, fallback: str = "Tài liệu chứng thực") -> str:
    """Chuẩn hóa tên đưa vào ô `Tên tài liệu` của ví giấy tờ.

    Form chỉ nhận chữ, số, khoảng trắng, gạch dưới và gạch ngang. Một số tên file
    người dùng upload là Unicode decomposed (vd: Giấy) nên phải normalize về NFC
    trước khi fill, nếu không UI báo "Tên tài liệu không hợp lệ".
    """
    stem = Path(raw or "").stem or raw or ""
    source = stem.strip()
    if not source or _GENERIC_FILE_RE.match(fold(source)):
        source = fallback

    source = unicodedata.normalize("NFC", source)
    chars: list[str] = []
    for ch in source:
        if unicodedata.category(ch) == "Mn":
            continue
        if ch.isalnum() or ch in {" ", "_", "-"}:
            chars.append(ch)
        else:
            chars.append(" ")

    text = re.sub(r"\s+", " ", "".join(chars)).strip()
    if not text:
        text = fallback
    return text[:50].strip() or "Tài liệu chứng thực"
