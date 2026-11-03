"""Compact agent pipeline cho thủ tục 2.002862 (Lai Châu)."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.ho_tro_mai_tang_dan_toc_thieu_so_lai_chau.process import mapper
from app.pipelines.ho_tro_mai_tang_dan_toc_thieu_so_lai_chau.process.prompt import EXTRA_RULES
from app.pipelines.ho_tro_mai_tang_dan_toc_thieu_so_lai_chau.process.schema import (
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
    res["fields"] = mapper.enrich(res["fields"])
    return res
