"""Compact-agent process pipeline cho thủ tục đính chính GCN đã cấp lần đầu có sai sót Khánh Hòa (1.012796).

Bù tất định dùng chung với đính chính GCN đã cấp Khánh Hòa (1.012790, `apply_fallback`): số thửa/số tờ khi mọi chỗ in
cùng một số, phường/xã nơi thường trú theo dòng "c) Địa chỉ" của Đơn (Mẫu 18 cùng bố cục mục 1), tên người in ở mục I của
Giấy chứng nhận mẫu mới. GCN mẫu cũ ("I- Tên người sử dụng đất") không khớp mục I mẫu mới nên để LLM đọc.
"""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dinh_chinh_gcn_da_cap_khanh_hoa.process.runner import apply_fallback

from . import mapper
from .prompt import EXTRA_RULES
from .schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    result = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        compact_field_fallback=apply_fallback,
    )
    result["fields"], warnings = mapper.enrich(result["fields"], options)
    if warnings:
        result.setdefault("errors", []).extend(warnings)
    return result
