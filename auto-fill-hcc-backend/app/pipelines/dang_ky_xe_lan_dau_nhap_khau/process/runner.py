"""Compact agent pipeline cho thủ tục 1.013066 (Cổng DVC Bộ Công an)."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_xe_lan_dau_nhap_khau.process import mapper
from app.pipelines.dang_ky_xe_lan_dau_nhap_khau.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_xe_lan_dau_nhap_khau.process.schema import (
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
    raw_fields = res["fields"]
    res["fields"], warnings = mapper.enrich(raw_fields, options)
    # Chủ xe trên giấy là người khác chủ tài khoản VNeID → không điền; `blocked` để Auto Fill / trợ lý hiện câu báo dễ
    # hiểu thay cho thông báo chung "không đọc được giấy tờ".
    blocked = mapper.account_block(mapper._by_name(raw_fields), options) if mapper.has_account_anchor(options) else None
    if blocked:
        res["blocked"] = blocked
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
