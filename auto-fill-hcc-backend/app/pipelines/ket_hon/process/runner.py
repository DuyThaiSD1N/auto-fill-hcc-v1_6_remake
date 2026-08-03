"""Compact agent process pipeline for "Đăng ký kết hôn"."""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.ket_hon.process import mapper
from app.pipelines.ket_hon.process.prompt import EXTRA_RULES
from app.pipelines.ket_hon.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


_ETHNICITY_FIELDS = {"CccdNam_DanToc", "CccdNu_DanToc"}


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _compact_field_fallback(raw_fields, documents: list[dict]):
    """Loại dân tộc LLM suy từ họ/địa bàn khi OCR không hề có nhãn nguồn.

    Đây là chốt chứng cứ cục bộ cho đăng ký kết hôn: nếu hồ sơ có nhãn ``Dân tộc``
    thì giữ output để prompt phân vai; nếu không có nhãn thì cả hai CCCD đều không
    thể là nguồn dân tộc và hai field phải bị loại.
    """
    ocr_text = "\n".join(str(document.get("text") or "") for document in documents)
    if "dan toc" in _fold(ocr_text):
        return raw_fields

    if isinstance(raw_fields, dict):
        return {name: value for name, value in raw_fields.items() if name not in _ETHNICITY_FIELDS}
    if isinstance(raw_fields, list):
        return [
            field for field in raw_fields
            if not isinstance(field, dict) or field.get("name") not in _ETHNICITY_FIELDS
        ]
    return raw_fields


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        compact_field_fallback=_compact_field_fallback,
    )
    res["fields"] = mapper.enrich(res["fields"])

    # Rà soát bbox (Kiểu A): chỉ chạy khi router bật cờ _review (thủ tục có "review": True).
    # Đặt sau enrich để khớp trên FIELDS CUỐI (key theo DOM name mà FE điền). Lỗi → bỏ qua,
    # không chặn autofill.
    if (options or {}).get("_review"):
        from app.review import capture
        from app.pipelines.ket_hon.process.schema import REVIEW_FIELDS
        try:
            cap = await capture.capture(files_by_role, res["fields"], review_names=REVIEW_FIELDS)
            if cap:
                res["_review"] = cap
        except Exception as e:  # noqa: BLE001
            res.setdefault("errors", []).append(f"review: {e}")
    return res
