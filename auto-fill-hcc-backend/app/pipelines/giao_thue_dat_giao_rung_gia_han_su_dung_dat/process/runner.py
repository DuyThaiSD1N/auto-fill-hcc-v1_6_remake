"""Compact agent process pipeline cho [Lâm Đồng] giao đất, cho thuê đất, chuyển mục đích sử dụng đất, giao rừng, gia
hạn sử dụng đất (1.116366)."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.giao_thue_dat_giao_rung_gia_han_su_dung_dat.process import mapper
from app.pipelines.giao_thue_dat_giao_rung_gia_han_su_dung_dat.process.prompt import EXTRA_RULES
from app.pipelines.giao_thue_dat_giao_rung_gia_han_su_dung_dat.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    # Người nộp/chủ hồ sơ quyết định TẤT ĐỊNH theo CÓ hay KHÔNG có Giấy ủy quyền (xem prompt) — không tiêm formContext
    # (mỏ neo tài khoản) vào prompt, giống các thủ tục Lâm Đồng khác.
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
