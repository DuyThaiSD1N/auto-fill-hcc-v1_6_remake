"""Compact agent process pipeline for khai sinh liên thông."""

import copy

from app.pipelines._shared.compact_agent import runner
from app.pipelines.khai_sinh_lien_thong.process import mapper
from app.pipelines.khai_sinh_lien_thong.process.prompt import EXTRA_RULES
from app.pipelines.khai_sinh_lien_thong.process.schema import (
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
        context_builder=keep_documents if second_pass else None,
    )
    raw_fields = copy.deepcopy(res["fields"]) if second_pass else []
    res["fields"] = mapper.enrich(res["fields"], options, ocr_text=res.get("ocr_text") or "")
    if raw_fields and read.get("documents"):
        from ..thanh_tra import dot_hai

        # Nơi gọi pipeline lấy khoá này ra khỏi kết quả rồi chạy ở nền sau khi đã trả lượt điền đầu.
        res["_second_pass"] = lambda base_fields: dot_hai.patch(read["documents"], raw_fields, base_fields,
                                                                dict(options or {}))

    # Rà soát bbox (Kiểu A): chỉ chạy khi router bật cờ _review (thủ tục có "review": True).
    if (options or {}).get("_review"):
        from app.review import capture
        from app.pipelines.khai_sinh_lien_thong.process.schema import (
            REVIEW_FIELDS,
            REVIEW_NAME_GROUPS,
        )
        try:
            cap = await capture.capture(
                files_by_role, res["fields"],
                review_names=REVIEW_FIELDS, name_groups=REVIEW_NAME_GROUPS,
            )
            if cap:
                res["_review"] = cap
        except Exception as e:  # noqa: BLE001
            res.setdefault("errors", []).append(f"review: {e}")
    return res
