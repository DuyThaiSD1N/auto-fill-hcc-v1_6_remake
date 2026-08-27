"""Compact-agent runner cho tạm ngừng kinh doanh hộ kinh doanh."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.tam_ngung_kinh_doanh.process.fallback import apply_ocr_fallback
from app.pipelines.tam_ngung_kinh_doanh.process import mapper
from app.pipelines.tam_ngung_kinh_doanh.process.prompt import EXTRA_RULES
from app.pipelines.tam_ngung_kinh_doanh.process.schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    result = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        compact_field_fallback=apply_ocr_fallback,
    )
    pages, business_flow = mapper.build(result["fields"])
    result["pages"] = pages
    result["businessFlow"] = business_flow
    result["fields"] = pages["tam-ngung-hoat-dong"]
    result.setdefault("extracted", {})["page"] = "__suspension__"
    # Mirror riêng cho state ASP.NET: extension vẫn tìm được HKD nếu metadata lồng bị stale qua postback.
    result["extracted"]["businessSearch"] = business_flow["search"]
    return result
