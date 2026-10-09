"""Compact agent process pipeline cho "Đổi, cấp lại Giấy xác nhận khuyết tật".

Cùng luồng với khuyet_tat (OCR + LLM song song với đọc ảnh Mục III), chỉ khác schema/prompt/mapper.
Khoanh người nộp bằng mỏ neo UI dùng chung hàm của khuyet_tat vì cùng Mẫu số 01.
"""

import asyncio

from app.pipelines._shared.compact_agent import runner
from app.pipelines.doi_cap_lai_giay_xac_nhan_khuyet_tat.process import mapper
from app.pipelines.doi_cap_lai_giay_xac_nhan_khuyet_tat.process.prompt import EXTRA_RULES
from app.pipelines.doi_cap_lai_giay_xac_nhan_khuyet_tat.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)
from app.pipelines.khuyet_tat.process import vision
from app.pipelines.khuyet_tat.process.runner import (
    _owner_only_context,
    _requester_context,
)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    owner_mode = str((options or {}).get("submitterMode") or "") == "owner_as_submitter"
    res, section_iii = await asyncio.gather(runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        context_builder=_owner_only_context if owner_mode else _requester_context,
        max_tokens=2200,
    ), vision.read_section_iii(runner.flatten(files_by_role)))
    if section_iii is not None:
        # Bảng tích viết tay: kết quả đọc ảnh thay hẳn phần LLM bóc từ OCR văn bản (kể cả khi rỗng —
        # đơn cấp đổi được bỏ trống Mục III).
        res["fields"] = [f for f in res["fields"] if f.get("name") not in section_iii] + [
            {"name": name, "comp": "raw", "value": value} for name, value in section_iii.items()
        ]
    res["fields"] = mapper.enrich(res["fields"], options)
    return res
