"""Compact agent pipeline cho thủ tục 1.115668 (Lào Cai)."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.process import mapper
from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.process.schema import (
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
    # options mang formContext (VNeID người đăng nhập) — mapper cần nó để nhận ra CCCD của NGƯỜI NỘP.
    res["fields"] = mapper.enrich(res["fields"], options)
    return res
