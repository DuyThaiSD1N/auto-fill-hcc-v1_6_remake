"""Compact agent pipeline cho thủ tục 1.115677 (Lào Cai) — xác nhận tiếp tục sử dụng đất nông nghiệp."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep.process import mapper
from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep.process.prompt import EXTRA_RULES
from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep.process.schema import (
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
    # options mang formContext (họ tên + số căn cước cổng đã điền sẵn từ tài khoản định danh) — mapper
    # cần nó để biết AI đang đi nộp: Mẫu 39 rất hay do VỢ/CHỒNG ký nộp thay cho người đứng tên đầu.
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
