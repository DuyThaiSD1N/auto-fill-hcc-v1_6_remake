"""Compact agent process pipeline cho "Đổi, cấp lại Giấy xác nhận khuyết tật".

Cùng luồng với khuyet_tat (OCR + LLM song song với đọc ảnh Mục III), chỉ khác schema/prompt/mapper.
Khoanh người nộp bằng mỏ neo UI dùng chung hàm của khuyet_tat vì cùng Mẫu số 01.
"""

import asyncio
import copy

from app.pipelines._shared.compact_agent import runner
from app.pipelines.doi_cap_lai_giay_xac_nhan_khuyet_tat.process import mapper
from app.pipelines.doi_cap_lai_giay_xac_nhan_khuyet_tat.process.prompt import EXTRA_RULES
from app.pipelines.doi_cap_lai_giay_xac_nhan_khuyet_tat.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)
from app.pipelines.khuyet_tat.process import dang_khuyet_tat, muc_do, vision
from app.pipelines.khuyet_tat.process.runner import (
    _counter_context,
    _owner_only_context,
    _requester_context,
)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    owner_mode = str((options or {}).get("submitterMode") or "") == "owner_as_submitter"
    levels_tasks: list = []
    types_tasks: list = []
    # Điền đợt 2 cần OCR từng tài liệu và field TRƯỚC mapper — runner chung chỉ trả chuỗi OCR đã nối.
    second_pass = bool((options or {}).get("_secondPass"))
    read: dict = {}
    requester_context = _owner_only_context if owner_mode else _requester_context

    async def build_context(documents: list[dict], opts: dict) -> str:
        read["documents"] = documents
        # Bảng dạng khuyết tật (mục III.1) đọc riêng song song lượt trích chính, như bảng mức độ.
        types_tasks.append(asyncio.create_task(dang_khuyet_tat.read_disability_types(documents)))
        return await requester_context(documents, opts) + _counter_context(opts)

    res, section_iii = await asyncio.gather(runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        context_builder=muc_do.context_with_levels(build_context, levels_tasks),
        max_tokens=2200,
    ), vision.read_section_iii(runner.flatten(files_by_role)) if vision.ENABLED else asyncio.sleep(0))
    await muc_do.apply_levels(res, levels_tasks)
    if section_iii is not None:
        for task in types_tasks:
            task.cancel()
        # Bảng tích viết tay: kết quả đọc ảnh thay hẳn phần LLM bóc từ OCR văn bản (kể cả khi rỗng —
        # đơn cấp đổi được bỏ trống Mục III).
        res["fields"] = [f for f in res["fields"] if f.get("name") not in section_iii] + [
            {"name": name, "comp": "raw", "value": value} for name, value in section_iii.items()
        ]
    else:
        if vision.ENABLED:
            # Kết quả dự phòng từ OCR văn bản hay mất cột Có/Không của bảng tích.
            res.setdefault("errors", []).append(vision.SECTION_III_WARNING)
        # Đơn cấp đổi bỏ trống Mục III → bảng không dấu → không tích gì.
        dang_khuyet_tat.apply(res, await types_tasks[0] if types_tasks else None)
    # OCR để mapper kiểm ngày sinh / ngày cấp người đại diện có trên giấy và dò lại tên phường/xã.
    enrich_options = {**(options or {}), "_ocr_text": res.get("ocr_text") or ""}
    raw_fields = copy.deepcopy(res["fields"]) if second_pass else []
    res["fields"] = mapper.enrich(res["fields"], enrich_options)
    if raw_fields and read.get("documents"):
        # Cùng eForm Mẫu số 01: thanh tra + bản vá đợt 2 của khuyet_tat (chỉ vá các khối người / địa chỉ, không đụng hai
        # ô nội dung đề nghị, lý do riêng của thủ tục này).
        from app.pipelines.khuyet_tat.thanh_tra import dot_hai

        res["_second_pass"] = lambda base_fields: dot_hai.patch(read["documents"], raw_fields, base_fields,
                                                                enrich_options)
    return res
