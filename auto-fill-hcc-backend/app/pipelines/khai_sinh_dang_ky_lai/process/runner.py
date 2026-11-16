"""Compact agent process pipeline for "Đăng ký lại khai sinh"."""

import copy

from app.pipelines._shared.compact_agent import runner
from app.pipelines.khai_sinh_dang_ky_lai.process import mapper, reason
from app.pipelines.khai_sinh_dang_ky_lai.process.prompt import EXTRA_RULES
from app.pipelines.khai_sinh_dang_ky_lai.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    # Điền đợt 2 cần OCR từng tài liệu và field TRƯỚC mapper — runner chung chỉ trả chuỗi OCR đã nối.
    second_pass = bool((options or {}).get("_secondPass"))
    read: dict = {}

    def keep_documents(raw_fields, documents: list[dict]):
        read["documents"] = documents
        return raw_fields

    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        context_builder=reason.build_context,
        compact_field_fallback=keep_documents,
    )
    # Reasoning đã chốt vai trò theo người. Lọc trước mapper để không biến field
    # bị gán nhầm người thành field UI hợp lệ.
    reasoning_context = res.get("reasoning_context") or ""
    res["fields"] = reason.sanitize_extracted_fields(res["fields"], reasoning_context)
    # Truyen reasoning_context de mapper biet cha/me nao da duoc xac dinh la da chet
    enrich_options = {**(options or {}), "_reasoning_context": reasoning_context}
    raw_fields = copy.deepcopy(res["fields"]) if second_pass else []
    res["fields"] = mapper.enrich(res["fields"], enrich_options)
    if raw_fields and read.get("documents"):
        from app.pipelines.khai_sinh_dang_ky_lai.thanh_tra import dot_hai

        # Nơi gọi pipeline lấy khoá này ra khỏi kết quả rồi chạy ở nền sau khi đã trả lượt điền đầu.
        res["_second_pass"] = lambda base_fields: dot_hai.patch(read["documents"], raw_fields, base_fields,
                                                                enrich_options)

    # Rà soát bbox (Kiểu A): chỉ chạy khi router bật cờ _review (thủ tục có "review": True).
    if (options or {}).get("_review"):
        from app.review import capture
        from app.pipelines.khai_sinh_dang_ky_lai.process.schema import REVIEW_FIELDS
        try:
            cap = await capture.capture(files_by_role, res["fields"], review_names=REVIEW_FIELDS)
            if cap:
                res["_review"] = cap
        except Exception as e:  # noqa: BLE001
            res.setdefault("errors", []).append(f"review: {e}")
    return res
