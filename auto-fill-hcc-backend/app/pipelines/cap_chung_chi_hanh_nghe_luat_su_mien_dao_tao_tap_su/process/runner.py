"""Compact agent process pipeline for "Cấp Chứng chỉ hành nghề luật sư (miễn đào tạo, miễn tập sự)"."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_chung_chi_hanh_nghe_luat_su_mien_dao_tao_tap_su.process import mapper
from app.pipelines.cap_chung_chi_hanh_nghe_luat_su_mien_dao_tao_tap_su.process.prompt import EXTRA_RULES
from app.pipelines.cap_chung_chi_hanh_nghe_luat_su_mien_dao_tao_tap_su.process.schema import (
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
        options=options,
    )
    res["fields"], warnings = mapper.enrich(res["fields"], options)
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
