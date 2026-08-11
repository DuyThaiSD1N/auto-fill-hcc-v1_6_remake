"""Compact agent process pipeline cho [Lâm Đồng] đính chính GCN có sai sót."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dinh_chinh_sai_sot_lam_dong.process import mapper
from app.pipelines.dinh_chinh_sai_sot_lam_dong.process.prompt import EXTRA_RULES
from app.pipelines.dinh_chinh_sai_sot_lam_dong.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    # Người nộp/đại diện được quyết định TẤT ĐỊNH bằng CÓ hay KHÔNG có Giấy ủy quyền (xem prompt) —
    # KHÔNG còn tiêm formContext (mỏ neo tài khoản) vào prompt nữa.
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        max_tokens=1200,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
