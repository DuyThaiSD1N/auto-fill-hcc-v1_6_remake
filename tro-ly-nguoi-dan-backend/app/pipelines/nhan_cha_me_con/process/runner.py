"""Compact agent process pipeline for "Đăng ký nhận cha, mẹ, con"."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.nhan_cha_me_con.process import mapper
from app.pipelines.nhan_cha_me_con.process.prompt import EXTRA_RULES
from app.pipelines.nhan_cha_me_con.process.schema import (
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
    res["fields"] = mapper.enrich(res["fields"], options)
    return res

