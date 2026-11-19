"""Compact agent process pipeline cho "Cấp bản sao văn bằng, chứng chỉ từ sổ gốc" (cổng DVC Bộ GD&ĐT).

Chỉ trích nhân thân chủ văn bằng + nội dung kê khai; người nộp lấy từ tài khoản (formContext), bật "Lấy người nộp theo tờ khai" thì theo chủ văn bằng. Xem mapper."""

import copy

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_ban_sao_van_bang_so_goc.process import mapper
from app.pipelines.cap_ban_sao_van_bang_so_goc.process.prompt import EXTRA_RULES
from app.pipelines.cap_ban_sao_van_bang_so_goc.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    # Điền đợt 2 cần OCR từng tài liệu và field TRƯỚC mapper — runner chung chỉ trả chuỗi OCR đã nối.
    second_pass = bool((options or {}).get("_secondPass"))
    read: dict = {}

    async def keep_documents(documents: list[dict], opts: dict) -> str:
        read["documents"] = documents
        return ""

    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        context_builder=keep_documents if second_pass else None,
    )
    raw_fields = copy.deepcopy(res["fields"]) if second_pass else []
    ocr_text = res.get("ocr_text", "")
    mapped_fields, warnings = mapper.enrich(res["fields"], options, ocr_text=ocr_text)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    if raw_fields and read.get("documents"):
        from app.pipelines.cap_ban_sao_van_bang_so_goc.thanh_tra import dot_hai

        # Nơi gọi pipeline lấy khoá này ra khỏi kết quả rồi chạy ở nền sau khi đã trả lượt điền đầu.
        res["_second_pass"] = lambda base_fields: dot_hai.patch(read["documents"], raw_fields, base_fields,
                                                                options, ocr_text)
    return res
