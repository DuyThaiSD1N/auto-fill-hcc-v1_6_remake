"""Compact agent pipeline cho thủ tục 1.115682 (Lào Cai) — sử dụng đất kết hợp đa mục đích (cấp xã)."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_cap_xa.process import mapper
from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_cap_xa.process.prompt import EXTRA_RULES
from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_cap_xa.process.schema import (
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
    # options mang formContext (họ tên + số căn cước cổng đã prefill từ tài khoản định danh) — mapper
    # cần nó để biết AI đang đi nộp. Ở thủ tục này cán bộ nộp thay là ca thường gặp nên thiếu mốc
    # thì cả khối "Thông tin người nộp" bị bỏ trống có chủ ý, không phải lỗi im lặng.
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
