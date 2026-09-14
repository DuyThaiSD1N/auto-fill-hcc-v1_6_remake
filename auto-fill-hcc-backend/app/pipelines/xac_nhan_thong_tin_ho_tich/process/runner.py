"""Compact agent pipeline cho "Xác nhận thông tin hộ tịch"."""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.xac_nhan_thong_tin_ho_tich.process import mapper
from app.pipelines.xac_nhan_thong_tin_ho_tich.process.prompt import EXTRA_RULES
from app.pipelines.xac_nhan_thong_tin_ho_tich.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

# Nhóm field đọc từ THẺ của một người → (prefix, mỏ neo họ tên, mỏ neo số).
_CARD_GROUPS = (
    ("Nyc_", "Nyc_HoTen", "Nyc_SoDinhDanh"),
    ("ChuThe_", "ChuThe_HoTen", "ChuThe_SoDinhDanh"),
)


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _requester_hint(options: dict) -> str:
    """Mỏ neo tài khoản đăng nhập (nếu cổng có đổ) để LLM chọn đúng CCCD người yêu cầu."""
    ctx = (options or {}).get("formContext") or {}
    name = str(ctx.get("applicantFullname") or "").strip()
    idnum = str(ctx.get("applicantIdentityNumber") or "").strip()
    if not name and not idnum:
        return ""
    return (
        "\n\n<requester_context>\n"
        f'Tài khoản đang đăng nhập cổng: họ tên="{name}", số định danh="{idnum}".\n'
        "CHỈ là MỎ NEO để chọn thẻ nào là của người yêu cầu. TUYỆT ĐỐI không dùng tên/số này làm GIÁ TRỊ\n"
        "field. Người yêu cầu ghi trên tờ khai khác tài khoản này thì theo TỜ KHAI.\n"
        "</requester_context>"
    )


def _drop_unbacked_cards(raw_fields, documents: list[dict]):
    """Bỏ nhóm thẻ mà cả họ tên lẫn số đều không có trong OCR — LLM chép mỏ neo thay vì đọc giấy."""
    if not isinstance(raw_fields, (dict, list)):
        return raw_fields

    def value_of(name):
        if isinstance(raw_fields, dict):
            return raw_fields.get(name)
        for field in raw_fields:
            if isinstance(field, dict) and field.get("name") == name:
                return field.get("value")
        return None

    ocr_text = "\n".join(str(document.get("text") or "") for document in documents)
    ocr_folded = _fold(ocr_text)
    ocr_digits = _digits(ocr_text)

    dropped: set[str] = set()
    for prefix, name_field, id_field in _CARD_GROUPS:
        name = _fold(value_of(name_field))
        idnum = _digits(value_of(id_field))
        if not name and not idnum:
            continue
        if (idnum and idnum in ocr_digits) or (name and name in ocr_folded):
            continue
        dropped.add(prefix)
    if not dropped:
        return raw_fields

    def is_dropped(name) -> bool:
        return any(str(name or "").startswith(prefix) for prefix in dropped)

    if isinstance(raw_fields, dict):
        return {name: value for name, value in raw_fields.items() if not is_dropped(name)}
    return [f for f in raw_fields if not isinstance(f, dict) or not is_dropped(f.get("name"))]


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES + _requester_hint(options),
        compact_field_fallback=_drop_unbacked_cards,
        options=options,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
