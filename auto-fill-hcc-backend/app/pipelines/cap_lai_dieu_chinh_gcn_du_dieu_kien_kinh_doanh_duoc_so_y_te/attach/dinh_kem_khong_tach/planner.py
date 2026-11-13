"""Đính kèm KHÔNG TÁCH cho "Cấp lại, điều chỉnh GCN đủ điều kiện kinh doanh dược (Sở Y tế)" — cài đặt tách tắt.

OCR từng tệp (cùng cách gọi của chế độ tách) → MỘT lượt LLM liệt kê mọi loại giấy trong từng tệp → MỖI TỆP đính
NGUYÊN, đúng MỘT lần (không `sourceSegments`), vào dòng của giấy chính trong tệp theo _PRIORITY:
  Đơn cấp lại / Đơn điều chỉnh  → dòng 1 / dòng 3
  GCN đủ ĐKKD dược, CCHN dược, giấy tờ pháp lý, thuyết minh an ninh → dòng riêng 2 / 4 / 5 / 6
  CCCD, giấy chưa rõ loại        → dòng Đơn (dòng 3 nếu hồ sơ chỉ có Đơn điều chỉnh, còn lại dòng 1) + cảnh báo
Bảng dòng, loại bản, cách đặt tên và luật dòng Đơn dự phòng dùng CHUNG với chế độ tách (dinh_kem_tach/planner.py
`build_plan_items`, mỗi tệp đưa vào như một đoạn phủ trọn tệp) để hai chế độ đặt cùng chỗ. LLM không trả lời / OCR rỗng
→ rule OCR của chế độ tách; vẫn không rõ thì về dòng Đơn, giữ tên gốc. Không bao giờ bỏ tệp.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared.documents import join_ocr_documents, representative_excerpt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from ..dinh_kem_tach.planner import (
    _CCCD,
    _CCHN,
    _DON_CAP_LAI,
    _DON_DIEU_CHINH,
    _GCN_DKKD,
    _OCR_TYPES,
    _OTHER,
    _PHAP_LY,
    _ROWS,
    _THUYET_MINH,
    _normalize_type,
    _pdf_page_count,
    build_plan_items,
)
from .prompt import SYSTEM_PROMPT, build_user_prompt

_LLM_TEXT_MAX_CHARS = 6000

# Tệp gộp nhiều giấy: giấy ĐỨNG TRƯỚC nhận nguyên tệp. Đơn trước, giấy có dòng riêng sau, CCCD / giấy lạ (đi chung
# dòng Đơn) cuối.
_PRIORITY: tuple[str, ...] = (
    _DON_CAP_LAI, _DON_DIEU_CHINH, _GCN_DKKD, _CCHN, _PHAP_LY, _THUYET_MINH, _CCCD, _OTHER,
)


def doc_types(raw: Any) -> list[str]:
    """docTypes LLM trả (chuỗi hoặc danh sách) → danh sách loại hợp lệ, không trùng, giữ thứ tự."""
    if not isinstance(raw, list):
        raw = [raw]
    out: list[str] = []
    for value in raw:
        doc_type = _normalize_type(str(value or ""))
        if doc_type not in out:
            out.append(doc_type)
    return out


def primary(types: list[str]) -> str:
    return next((doc_type for doc_type in _PRIORITY if doc_type in types), _OTHER)


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, list[str]]:
    if not documents:
        return {}
    raw = await client.chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(documents)},
        ],
        max_tokens=max(600, min(2000, len(documents) * 120)),
        enable_thinking=settings.agent_reasoning,
    )
    parsed = client.extract_json_block(raw)
    result: dict[int, list[str]] = {}
    for item in parsed.get("documents", []) or []:
        try:
            result[int(item.get("index"))] = doc_types(item.get("docTypes", item.get("docType", item.get("type"))))
        except (TypeError, ValueError, AttributeError):
            continue
    return result


def build_whole_file_items(
    raw_files: list[dict],
    llm_types: dict[int, list[str]],
    page_counts: dict[int, int],
    full_text_by_file: dict[int, str],
) -> tuple[list[dict], list[dict], list[str]]:
    """Mỗi tệp = một đoạn phủ trọn tệp, loại = giấy chính → bảng dòng của chế độ tách. Thuần tất định."""
    segments: list[dict] = []
    merged: dict[int, set[int]] = {}
    for index, file in enumerate(raw_files):
        types = llm_types.get(index) or []
        rows = {_ROWS[t]["componentIndex"] for t in types if t in _ROWS}
        # Tệp gộp nhiều giấy có dòng riêng giữ TÊN GỐC để cán bộ nhận ra; tệp một giấy mang tên dòng.
        name = str(file.get("name") or f"file-{index + 1}") if len(rows) > 1 else ""
        if len(rows) > 1:
            merged[index] = rows
        segments.append({"fileIndex": index, "pageFrom": 1, "pageTo": page_counts.get(index, 1),
                         "type": primary(types), "documentName": name})
    file_meta = {
        i: {"pageCount": page_counts.get(i, 1), "pageBoundariesAvailable": False} for i in range(len(raw_files))
    }
    attachments, classified, warnings = build_plan_items(raw_files, segments, file_meta, {}, full_text_by_file)

    for entry in classified:
        entry["docTypes"] = llm_types.get(entry["fileIndex"]) or []
        entry["source"] = "llm" if entry["fileIndex"] in llm_types else "rule"
    for item in attachments:
        others = sorted(merged.get(item["fileIndex"], set()) - {item["componentIndex"]})
        if others:
            warnings.append(
                f"'{item['fileName']}' gộp nhiều giấy tờ — đính nguyên tệp một lần vào dòng {item['componentIndex']} "
                f"({item['componentName']}), không tách sang dòng {', '.join(map(str, others))}; cán bộ kiểm tra lại."
            )
    return attachments, classified, warnings


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file([f for _, f in ocr_pairs]) if ocr_pairs else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    ocr_by_index = {ri: res for (ri, _), res in zip(ocr_pairs, ocr_results)}
    for ri, res in ocr_by_index.items():
        if res.get("error"):
            errors.append(f"OCR fileIndex={ri} {raw_files[ri].get('name')}: {res['error']}")

    full_text_by_file = {i: str((ocr_by_index.get(i) or {}).get("text") or "") for i in range(len(raw_files))}
    page_counts = {i: _pdf_page_count(f) for i, f in enumerate(raw_files)}
    llm_docs = [
        {"index": i, "text": representative_excerpt(text, _LLM_TEXT_MAX_CHARS)}
        for i, text in full_text_by_file.items() if text.strip()
    ]

    t1 = time.monotonic()
    llm_types: dict[int, list[str]] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as e:  # noqa: BLE001 — LLM lỗi → rule OCR, không rõ thì về dòng Đơn, giữ tên gốc
            errors.append(f"attachment_agent: {e}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, classified, warnings = build_whole_file_items(raw_files, llm_types, page_counts, full_text_by_file)
    errors.extend(warnings)

    indexed_ocr = [
        {**res, "name": f"fileIndex={i} · {raw_files[i].get('name')}"} for i, res in sorted(ocr_by_index.items())
    ]
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [raw_files[i]["name"] for i, r in ocr_by_index.items() if r.get("text")],
            "llmDocuments": [raw_files[d["index"]]["name"] for d in llm_docs],
            "sessionId": (session or {}).get("request_id"),
            "attachmentMode": "whole_files",
            "classified": classified,
            "rows": [{"docType": k, **v} for k, v in _ROWS.items()],
        },
        "ocr_text": join_ocr_documents(indexed_ocr),
        "llm_output": {"documents": [{"index": i, "docTypes": t} for i, t in sorted(llm_types.items())]},
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
