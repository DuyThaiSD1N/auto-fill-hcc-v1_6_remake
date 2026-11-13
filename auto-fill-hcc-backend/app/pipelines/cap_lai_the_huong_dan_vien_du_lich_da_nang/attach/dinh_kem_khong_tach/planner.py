"""Đính kèm [Đà Nẵng · Bộ VHTTDL] cấp lại thẻ hướng dẫn viên du lịch (1.004614) — chế độ KHÔNG tách giấy tờ.

Cài đặt "Tách giấy tờ" tắt (hoặc client cũ): OCR từng tệp như chế độ tách, ảnh chân dung (gần như không có chữ) nhận
tất định, các tệp còn lại phân loại trong MỘT lượt LLM (docType + alsoTypes, cùng prompt với chế độ tách). MỖI TỆP đính
NGUYÊN, MỘT lần (không `sourceSegments`), vào dòng của giấy chính: chọn dòng, tên tài liệu, gợi ý ô "Mô tả" và cảnh báo
thiếu Đơn / ảnh đều qua `build_plan_items` của chế độ tách ở nhánh phân loại nguyên tệp (_ROW_PRIORITY: Đơn cấp lại
trước, giấy tờ thay đổi, đơn sai mẫu, giấy đính chung dòng 1, ảnh cuối) nên hai chế độ đặt cùng dòng. Tệp gộp nhiều giấy
thuộc dòng khác nhau → thêm cảnh báo (bật "Tách giấy tờ" để tách trang).

OCR lỗi / LLM lỗi → tệp về dòng 1 (bản sao giấy tờ — ô duy nhất nhận giấy tờ kèm theo), giữ tên gốc. Không bỏ tệp nào.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines.cap_the_huong_dan_vien_du_lich_noi_dia.attach.planner import _looks_like_photo
from app.process.schemas import FileItem
from app.services.llm import client

from ..dinh_kem_tach.planner import (
    _OCR_TYPES,
    _ROUTES,
    _SLOT_SHORT,
    _T_ANH,
    _normalize_also,
    _normalize_doc_type,
    _split_pages,
    build_plan_items,
)
from .prompt import SYSTEM_PROMPT, build_user_prompt

# Hạn mức chữ mỗi tệp gửi LLM (cả hồ sơ một lượt); tệp nhiều trang lấy phần đầu từng trang.
_LLM_FILE_CHARS = 8000


def _excerpt(text: str, pages: list[str] | None) -> str:
    if pages and len(pages) > 1:
        per_page = max(300, min(2000, _LLM_FILE_CHARS // len(pages)))
        return "\n".join(f"[Trang {n}] {page[:per_page]}" for n, page in enumerate(pages, start=1))
    return (pages[0] if pages else text)[:_LLM_FILE_CHARS]


async def _classify_all(documents: list[dict[str, Any]]) -> dict[int, tuple[str, list[str]]]:
    """MỘT lượt LLM cho cả hồ sơ → {fileIndex: (docType, alsoTypes)}."""
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=max(300, 80 * len(documents) + 200),
                            enable_thinking=settings.agent_reasoning)
    answered = [d for d in client.extract_json_block(raw).get("documents", []) or [] if isinstance(d, dict)]
    sent = [d["index"] for d in documents]
    result: dict[int, tuple[str, list[str]]] = {}
    for position, item in enumerate(answered):
        try:
            index = int(item.get("index"))
        except (TypeError, ValueError):
            # Thiếu index mà trả đủ số phần tử → theo thứ tự (prompt yêu cầu cùng thứ tự đầu vào).
            index = sent[position] if len(answered) == len(sent) else -1
        if index in sent and index not in result:
            doc_type = _normalize_doc_type(item.get("docType") or item.get("type"))
            result[index] = (doc_type, _normalize_also(item.get("alsoTypes"), doc_type))
    return result


def _gop_warnings(attachments: list[dict], llm_types: dict[int, tuple[str, list[str]]],
                  files: list[dict]) -> list[str]:
    warnings: list[str] = []
    for item in attachments:
        doc_type, also = llm_types.get(item["fileIndex"], ("", []))
        other_slots = sorted({_ROUTES[t] for t in (doc_type, *also) if t in _ROUTES} - {item["slotIndex"]})
        if other_slots:
            name = files[item["fileIndex"]].get("name")
            warnings.append(
                f"'{name}' gộp nhiều giấy tờ — đính nguyên tệp một lần vào dòng {item['slotIndex'] + 1} "
                f"({_SLOT_SHORT[item['slotIndex']]}), không tách sang dòng "
                f"{', '.join(str(s + 1) for s in other_slots)}. Bật cài đặt \"Tách giấy tờ\" nếu cần đính từng giấy "
                "đúng dòng."
            )
    return warnings


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    from app.services import ocr

    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]
    errors: list[str] = []

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file([f for _, f in pairs]) if pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    ocr_by_index = {index: result for (index, _), result in zip(pairs, ocr_results)}
    for index, result in ocr_by_index.items():
        if result.get("error"):
            errors.append(f"OCR {raw_files[index].get('name')}: {result['error']}")

    llm_types: dict[int, tuple[str, list[str]]] = {}
    documents: list[dict[str, Any]] = []
    for index, file in enumerate(raw_files):
        entry = ocr_by_index.get(index, {})
        text = str(entry.get("text") or "")
        pages = _split_pages(text) if not entry.get("error") else None
        multi_page = bool(pages and len(pages) > 1)
        body = pages[0] if pages else text
        # Ảnh chân dung không có chữ → nhận tất định (như chế độ tách). Tệp OCR lỗi thì KHÔNG coi là ảnh.
        if not multi_page and not entry.get("error") and file.get("type") in _OCR_TYPES \
                and _looks_like_photo(file, body):
            llm_types[index] = (_T_ANH, [])
        elif text.strip():
            documents.append({"index": index, "text": _excerpt(text, pages)})

    started = time.monotonic()
    if documents:
        try:
            llm_types.update(await _classify_all(documents))
        except Exception as exc:  # noqa: BLE001 — LLM lỗi → tệp về dòng 1, giữ tên gốc
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, llm_types)
    errors.extend(warnings)
    errors.extend(_gop_warnings(attachments, llm_types, raw_files))
    return {
        "attachments": attachments,
        "extracted": {
            "attachmentMode": "preserve_files",
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [raw_files[i]["name"] for i, r in ocr_by_index.items() if r.get("text")],
            "llmDocuments": [raw_files[d["index"]]["name"] for d in documents],
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
