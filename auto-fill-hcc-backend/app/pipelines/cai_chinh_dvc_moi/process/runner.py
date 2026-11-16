"""Pipeline thay đổi, cải chính hộ tịch (Cổng DVC quốc gia mới): phân vai → trích → mapper."""

import copy

from app.pipelines._shared.compact_agent import runner

from . import mapper, reason
from .prompt import EXTRA_RULES
from .schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    # Điền đợt 2 cần OCR từng tài liệu và field TRƯỚC mapper — runner chung chỉ trả chuỗi OCR đã nối.
    second_pass = bool((options or {}).get("_secondPass"))
    read: dict = {}

    async def build_context(documents: list[dict], opts: dict) -> str:
        read["documents"] = documents
        return await reason.build_context(documents, opts)

    result = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        context_builder=build_context,
    )
    raw_fields = copy.deepcopy(result["fields"]) if second_pass else []
    enrich_options = {**(options or {}), "_reasoning_context": result.get("reasoning_context") or ""}
    result["fields"], warnings = mapper.enrich(result["fields"], enrich_options)
    if warnings:
        result.setdefault("errors", []).extend(warnings)
    if raw_fields and read.get("documents"):
        from ..thanh_tra import dot_hai

        # Nơi gọi pipeline lấy khoá này ra khỏi kết quả rồi chạy ở nền sau khi đã trả lượt điền đầu.
        result["_second_pass"] = lambda base_fields: dot_hai.patch(
            read["documents"], enrich_options["_reasoning_context"], raw_fields, base_fields, enrich_options)
    return result
