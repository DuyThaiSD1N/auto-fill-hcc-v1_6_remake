"""Compact agent pipeline cho "Cấp đổi thẻ căn cước" (Cổng DVC Bộ Công an)."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_doi_the_can_cuoc.process import mapper
from app.pipelines.cap_doi_the_can_cuoc.process.prompt import EXTRA_RULES
from app.pipelines.cap_doi_the_can_cuoc.process.schema import (
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
        compact_field_fallback=mapper.email_ocr_fallback,
        options=options,
    )
    res["fields"] = mapper.enrich(res["fields"], options)
    return res
