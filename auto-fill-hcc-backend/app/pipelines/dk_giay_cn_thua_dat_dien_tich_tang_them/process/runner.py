"""Compact agent pipeline cho thủ tục 1.115694 (Lào Cai) — thửa đất có diện tích tăng thêm."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dk_giay_cn_thua_dat_dien_tich_tang_them.process import mapper
from app.pipelines.dk_giay_cn_thua_dat_dien_tich_tang_them.process.prompt import EXTRA_RULES
from app.pipelines.dk_giay_cn_thua_dat_dien_tich_tang_them.process.schema import (
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
    # cần nó để biết AI đang đi nộp, tách khỏi chủ hồ sơ khi hồ sơ nộp qua người được ủy quyền.
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
