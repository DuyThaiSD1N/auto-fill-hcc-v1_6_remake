"""Compact agent process pipeline "Cấp, cấp lại Giấy phép liên vận giữa Việt Nam, Lào và Campuchia" (1.002877).

OCR + LLM chạy song song với lượt Qwen đọc ảnh Giấy đề nghị (vision.py); kết quả ảnh ghép vào như bản Việt – Lào
(`_apply_vision`: bảng xe, phường/xã, SĐT, mục đích) rồi mapper suy ra ô Form.io.
"""

import asyncio

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_giay_phep_lien_van_viet_lao.process.runner import _apply_vision
from app.pipelines.cap_giay_phep_lien_van_viet_lao_campuchia.process import mapper, vision
from app.pipelines.cap_giay_phep_lien_van_viet_lao_campuchia.process.prompt import EXTRA_RULES
from app.pipelines.cap_giay_phep_lien_van_viet_lao_campuchia.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res, parsed = await asyncio.gather(runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
    ), vision.read_application(runner.flatten(files_by_role)))
    vision_warnings = _apply_vision(res["fields"], parsed) if parsed else []
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if vision_warnings or warnings:
        res.setdefault("errors", []).extend(vision_warnings + warnings)
    return res
