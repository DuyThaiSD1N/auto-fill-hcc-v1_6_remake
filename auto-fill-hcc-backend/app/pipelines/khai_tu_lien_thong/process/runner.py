"""Compact agent process pipeline for liên thông khai tử."""

import copy

from app.pipelines.khai_tu.process.runner import extract
from app.pipelines.khai_tu_lien_thong.process import mapper


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    # Điền đợt 2 cần OCR từng tài liệu và field TRƯỚC mapper.
    second_pass = bool((options or {}).get("_secondPass"))
    documents: list[dict] = []
    res = await extract(files_by_role, options, documents_out=documents if second_pass else None)
    raw_fields = copy.deepcopy(res["fields"]) if second_pass else []
    reasoning_context = res.get("reasoning_context") or ""
    res["fields"] = mapper.enrich(
        res["fields"],
        options,
        reasoning_context=reasoning_context,
        ocr_text=res.get("ocr_text") or "",
    )
    if raw_fields and documents:
        from ..thanh_tra import dot_hai

        # Nơi gọi pipeline lấy khoá này ra khỏi kết quả rồi chạy ở nền sau khi đã trả lượt điền đầu.
        res["_second_pass"] = lambda base_fields: dot_hai.patch(documents, reasoning_context, raw_fields, base_fields,
                                                                dict(options or {}))
    return res
