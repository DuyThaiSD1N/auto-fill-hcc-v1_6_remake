"""Compact-agent runner cho thay đổi nội dung đăng ký HKD."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_thay_doi_kinh_doanh.process import mapper
from app.pipelines.dang_ky_thay_doi_kinh_doanh.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_thay_doi_kinh_doanh.process.schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    result = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
    )
    compact = result["fields"]
    pages, business_flow = mapper.build(compact)
    result["pages"] = pages
    result["businessFlow"] = business_flow
    first_page = business_flow["pageOrder"][0] if business_flow["pageOrder"] else "nguoi-nop-ho-so"
    result["fields"] = pages.get(first_page, [])
    result.setdefault("extracted", {})["page"] = "__change__"
    return result
