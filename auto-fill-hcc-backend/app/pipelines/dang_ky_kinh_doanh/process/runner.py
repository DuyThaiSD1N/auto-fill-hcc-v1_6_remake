"""Compact agent pipeline for household business registration."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_kinh_doanh.process import mapper
from app.pipelines.dang_ky_kinh_doanh.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_kinh_doanh.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    DEFAULT_PAGE,
    FIELDS,
)


_ALL_PAGES = {"__all__", "all", "tat-ca"}


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
    )
    opts = options or {}
    page = opts.get("page") or opts.get("businessPage") or DEFAULT_PAGE
    compact = res["fields"]  # facts thô từ LLM — dùng để map cho từng trang

    # Chế độ FILL TẤT CẢ 8 trang trong 1 lần (extension tự lặp fill→lưu→sang trang).
    if opts.get("allPages") or str(page).lower() in _ALL_PAGES:
        res["pages"] = mapper.enrich_all(compact)
        res["fields"] = res["pages"].get(DEFAULT_PAGE, [])
        res.setdefault("extracted", {})["page"] = "__all__"
        return res

    res["fields"] = mapper.enrich(compact, page=page)
    res.setdefault("extracted", {})["page"] = page
    return res
