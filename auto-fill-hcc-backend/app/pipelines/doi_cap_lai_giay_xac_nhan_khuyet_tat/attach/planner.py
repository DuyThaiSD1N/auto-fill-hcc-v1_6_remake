"""Đính kèm cho thủ tục "Đổi, cấp lại Giấy xác nhận khuyết tật".

Bảng Thành phần hồ sơ trên cổng Bộ Y tế chỉ có ĐÚNG MỘT dòng (Đơn đề nghị cấp đổi, cấp lại theo
Mẫu số 01) và không có nút thêm thành phần → MỌI FILE đều đính vào dòng 1 (fixed-slot, slotIndex 0),
không bỏ sót file nào. LLM chỉ dùng để đặt tên hiển thị và cảnh báo file không phải Đơn đề nghị.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines.doi_cap_lai_giay_xac_nhan_khuyet_tat.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# slotName VERBATIM theo bảng của cổng; FE tìm ô bằng slotIndex nên chủ yếu để hiển thị/đối chiếu.
SLOT = {
    "slotKey": "don_de_nghi",
    "slotIndex": 0,
    "slotName": (
        "Đơn đề nghị cấp đổi, cấp lại Giấy xác nhận khuyết tật theo Mẫu số 01 ban hành kèm theo "
        "Thông tư số 01/2019/TT-BLĐTBXH (được sửa đổi, bổ sung tại Thông tư số 08/2023/TT-BLĐTBXH)"
    ),
    "detectedType": "Đơn đề nghị cấp đổi, cấp lại Giấy xác nhận khuyết tật",
}
SLOTS: list[dict] = [SLOT]

_LABELS = {
    "don_de_nghi": "Đơn đề nghị cấp đổi, cấp lại Giấy xác nhận khuyết tật",
    "giay_xac_nhan_khuyet_tat": "Giấy xác nhận khuyết tật cũ",
    "cccd": "Căn cước công dân",
}


def _normalize_type(value: str) -> str:
    raw = str(value or "").strip()
    return raw if raw in _LABELS else ""


async def _classify_documents_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=400, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    out: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        out[idx] = _normalize_type(str(item.get("type") or item.get("docType") or ""))
    return out


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str]]:
    """MỌI FILE đều đính vào dòng 1; loại LLM nhận ra chỉ đổi tên hiển thị và sinh cảnh báo."""
    llm_types = llm_types or {}
    items: list[dict] = []
    warnings: list[str] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        doc_type = llm_types.get(idx, "")
        label = _LABELS.get(doc_type) or f"Tài liệu khác - {file_name}"
        items.append({
            "fileIndex": idx,
            "fileName": file_name,
            "documentName": label,
            "componentName": SLOT["slotName"],
            "target": "fixed-slot",
            "needsAddComponent": False,
            "detectedType": label,
            "slotKey": SLOT["slotKey"],
            "slotIndex": SLOT["slotIndex"],
            "slotName": SLOT["slotName"],
        })
        if doc_type != SLOT["slotKey"]:
            reason = (
                f"được nhận là '{_LABELS[doc_type]}'" if doc_type in _LABELS
                else "chưa nhận diện chắc loại giấy tờ"
            )
            warnings.append(
                f"File '{file_name}' {reason}, không phải Đơn đề nghị Mẫu số 01 — vẫn đính vào dòng duy "
                "nhất của thủ tục; cán bộ kiểm tra lại."
            )

    return items, warnings


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    """Entry point đính kèm cho doi-cap-lai-giay-xac-nhan-khuyet-tat."""
    _ = options or {}
    _ = session
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    from app.services import ocr

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    ocr_by_name = {item.get("name"): item for item in ocr_results}
    llm_docs: list[dict[str, Any]] = []
    for idx, file in enumerate(raw_files):
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        if text.strip():
            llm_docs.append({"index": idx, "fileName": file.get("name"), "text": text})

    t1 = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_docs:
        try:
            llm_types = await _classify_documents_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings = build_plan_items(raw_files, llm_types)
    errors.extend(warnings)
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [doc["fileName"] for doc in llm_docs],
            "skippedOcr": skipped_ocr,
            "slots": [s["slotName"] for s in SLOTS],
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "errors": errors,
    }
