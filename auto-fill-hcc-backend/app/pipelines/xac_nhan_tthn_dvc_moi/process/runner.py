"""Pipeline cấp Giấy XNTTHN (Cổng DVC quốc gia mới): phân vai + chuẩn hoá mục đích → trích → mapper."""

from app.pipelines._shared.compact_agent import runner

from . import mapper, reason
from .prompt import EXTRA_RULES
from .schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    result = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        context_builder=reason.build_context,
    )
    enrich_options = {**(options or {}), "_reasoning_context": result.get("reasoning_context") or "",
                      "_ocr_text": result.get("ocr_text") or ""}
    result["fields"], warnings = mapper.enrich(result["fields"], enrich_options)
    if warnings:
        result.setdefault("errors", []).extend(warnings)
    return result
