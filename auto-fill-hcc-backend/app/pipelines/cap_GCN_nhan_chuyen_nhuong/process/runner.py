"""Compact agent pipeline cho thủ tục 1.115667 (Lào Cai)."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_GCN_nhan_chuyen_nhuong.process import mapper
from app.pipelines.cap_GCN_nhan_chuyen_nhuong.process.prompt import EXTRA_RULES
from app.pipelines.cap_GCN_nhan_chuyen_nhuong.process.schema import (
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
    # options mang formContext (VNeID người đăng nhập) — mapper cần nó để nhận ra CCCD của NGƯỜI NỘP
    # giữa nhiều thẻ trong hồ sơ.
    res["fields"] = mapper.enrich(res["fields"], options)
    return res
