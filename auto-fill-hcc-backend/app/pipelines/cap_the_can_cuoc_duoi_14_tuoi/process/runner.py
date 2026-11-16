"""Compact agent pipeline cho "Cấp thẻ căn cước cho người dưới 14 tuổi" (Cổng DVC Bộ Công an)."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_doi_the_can_cuoc.process.mapper import email_ocr_fallback
from app.pipelines.cap_the_can_cuoc_duoi_14_tuoi.process import mapper
from app.pipelines.cap_the_can_cuoc_duoi_14_tuoi.process.prompt import EXTRA_RULES
from app.pipelines.cap_the_can_cuoc_duoi_14_tuoi.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        # LLM chép lệch email đều đặn dù OCR đọc đúng (xem cấp đổi căn cước) → lấy email gần nhất trong chữ OCR.
        compact_field_fallback=email_ocr_fallback,
        options=options,
    )
    res["fields"] = mapper.enrich(res["fields"], options)
    return res
