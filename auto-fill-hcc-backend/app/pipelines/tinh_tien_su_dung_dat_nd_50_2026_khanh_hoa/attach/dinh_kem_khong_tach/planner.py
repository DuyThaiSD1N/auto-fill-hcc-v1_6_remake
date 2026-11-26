"""Đính kèm KHÔNG TÁCH cho bảng thành phần hồ sơ của 1.115148 trên cổng Khánh Hòa — cài đặt tách tắt.

Bảng (ảnh bước "Thành phần hồ sơ" + file mapping Phần VI, 24/11/2026) chỉ có MỘT dòng: checkbox + "Chọn tệp tin" "Văn bản
đề nghị tính hoặc tính lại tiền sử dụng đất", loại bản ghi cứng "1 Bản chính" — TRÙNG bảng bản Lâm Đồng nên dùng lại bảng
dòng, phân loại và dựng mục đính kèm của bản đó (engine FE `attp-row`, không gửi loaiBan, componentIndex đếm từ 1). Mọi
tệp (Đơn, CCCD, Giấy chứng nhận, thông báo / chứng từ nộp tiền, giấy ủy quyền, giấy lạ) đính vào dòng duy nhất, mỗi tệp
một lần; thiếu Văn bản đề nghị thì cảnh báo. Có attachmentContext thì dò dòng THẬT trên trang. Chỉ prompt LLM là riêng
(ghi cổng Khánh Hòa).
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared.documents import representative_excerpt
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.attach.planner import _LLM_TEXT_MAX_CHARS, _ocr_for_classify
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_lam_dong.attach.dinh_kem_khong_tach.planner import (  # noqa: F401
    _NAMES,
    _OTHER,
    ROW_NAME,
    _doc_types,
    attachment,
    build_plan_items,
    document_name,
    missing_request_warning,
    normalize_doc_type,
    portal_rows,
    primary,
    resolve_row,
)
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, list[str]]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=600, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    result: dict[int, list[str]] = {}
    for item in parsed.get("documents", []) or []:
        try:
            result[int(item.get("index"))] = _doc_types(item.get("docTypes", item.get("docType")))
        except (TypeError, ValueError, AttributeError):
            continue
    return result


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    rows = portal_rows(options)
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    ocr_files = [item for item in raw_files if item.get("type") in _OCR_TYPES]
    errors: list[str] = []

    started = time.monotonic()
    ocr_results = await _ocr_for_classify(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    llm_documents = [
        {"index": index, "text": representative_excerpt(str(by_name[file.get("name")].get("text")),
                                                        _LLM_TEXT_MAX_CHARS)}
        for index, file in enumerate(raw_files)
        if str(by_name.get(file.get("name"), {}).get("text") or "").strip()
    ]
    started = time.monotonic()
    llm_types: dict[int, list[str]] = {}
    if llm_documents:
        try:
            llm_types = await _classify_with_llm(llm_documents)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types, rows)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [item["name"] for item in raw_files],
            "ocrDocuments": [item.get("name") for item in ocr_results if item.get("text")],
            "llmDocuments": [raw_files[item["index"]]["name"] for item in llm_documents],
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
