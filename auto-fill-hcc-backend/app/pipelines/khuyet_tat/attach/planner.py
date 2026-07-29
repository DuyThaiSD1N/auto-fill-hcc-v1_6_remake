"""Đính kèm cho thủ tục xác định mức độ khuyết tật.

Form bước Thành phần hồ sơ có các ô upload cố định. Pipeline này OCR + LLM để
phân loại file vào đúng slot rồi trả target="fixed-slot" cho extension.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold
from app.pipelines.khuyet_tat.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DOC_RELATED = "disability_related_docs"
_DOC_MEDICAL_CONCLUSION = "medical_assessment_conclusion"
_DOC_APPLICATION = "disability_application_form"
_DOC_OTHER = "other"

SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": _DOC_RELATED,
        "slotIndex": 0,
        "slotName": "Bản sao các giấy tờ liên quan đến khuyết tật",
        "detectedType": "Giấy tờ liên quan đến khuyết tật",
        "documentName": "Giấy tờ liên quan đến khuyết tật",
    },
    {
        "slotKey": _DOC_MEDICAL_CONCLUSION,
        "slotIndex": 1,
        "slotName": "Bản sao kết luận của Hội đồng Giám định y khoa",
        "detectedType": "Kết luận của cơ sở y tế về tình trạng bệnh",
        "documentName": "Kết luận của cơ sở y tế về tình trạng bệnh",
    },
    {
        "slotKey": _DOC_APPLICATION,
        "slotIndex": 3,
        "slotName": "Đơn đề nghị theo Mẫu số 01",
        "detectedType": "Đơn đề nghị xác định mức độ khuyết tật",
        "documentName": "Đơn đề nghị xác định mức độ khuyết tật",
    },
]

_SLOT_BY_KEY = {item["slotKey"]: item for item in SLOTS}
_ALLOWED_DOC_TYPES = set(_SLOT_BY_KEY) | {_DOC_OTHER}


def _is_identity_text(text: str) -> bool:
    haystack = fold(text)
    return any(
        marker in haystack
        for marker in (
            "can cuoc cong dan",
            "chung minh nhan dan",
            "the can cuoc",
            "citizen identity card",
            "identity card",
            "ho chieu",
        )
    )


def _rule_doc_type(text: str) -> str:
    haystack = fold(text)
    if not haystack:
        return ""

    if (
        "don de nghi" in haystack
        and (
            "xac dinh muc do khuyet tat" in haystack
            or "xac dinh lai muc do khuyet tat" in haystack
            or "cap giay xac nhan khuyet tat" in haystack
            or "mau so 01" in haystack
            or "thong tu so 01 2019" in haystack
            or "thong tu so 08 2023" in haystack
        )
    ):
        return _DOC_APPLICATION

    if (
        "hoi dong giam dinh y khoa" in haystack
        or "ket luan giam dinh y khoa" in haystack
        or ("ket luan" in haystack and "kha nang tu phuc vu" in haystack)
        or ("ket luan" in haystack and "suy giam kha nang lao dong" in haystack)
        or ("ket luan" in haystack and "tinh trang benh" in haystack)
        or ("ket luan" in haystack and "muc do khuyet tat" in haystack)
    ):
        return _DOC_MEDICAL_CONCLUSION

    if any(
        marker in haystack
        for marker in (
            "benh an",
            "tom tat benh an",
            "giay ra vien",
            "phieu kham",
            "giay kham",
            "kham benh",
            "dieu tri",
            "phau thuat",
            "chan doan",
            "benh vien",
            "trung tam y te",
            "co so y te",
        )
    ):
        return _DOC_RELATED

    return ""


def _normalize_doc_type(value: str) -> str:
    raw = str(value or "").strip()
    if raw in _ALLOWED_DOC_TYPES:
        return raw
    text = fold(raw)
    if not text or text == "other":
        return _DOC_OTHER
    if "application" in text or "don de nghi" in text or "mau so 01" in text:
        return _DOC_APPLICATION
    if "medical" in text or "giam dinh" in text or "ket luan" in text:
        return _DOC_MEDICAL_CONCLUSION
    if "related" in text or "benh an" in text or "giay kham" in text:
        return _DOC_RELATED
    return _DOC_OTHER


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}

    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=500, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    out: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        out[idx] = _normalize_doc_type(str(item.get("docType") or item.get("type") or ""))
    return out


def _build_item(file: dict, file_index: int, slot_key: str) -> dict:
    slot = _SLOT_BY_KEY[slot_key]
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": slot["documentName"],
        "componentName": slot["slotName"],
        "target": "fixed-slot",
        "needsAddComponent": False,
        "detectedType": slot["detectedType"],
        "slotKey": slot["slotKey"],
        "slotIndex": slot["slotIndex"],
        "slotName": slot["slotName"],
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    by_name = {item.get("name"): item for item in ocr_results}
    items: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = str(by_name.get(file_name, {}).get("text") or "")
        rule_type = _rule_doc_type(text)
        llm_type = llm_types.get(idx, "")
        doc_type = llm_type if llm_type in _SLOT_BY_KEY else rule_type

        if not doc_type and _is_identity_text(text):
            warnings.append(f"File '{file_name}' là giấy tờ tùy thân — không đính kèm ở bước này, đã bỏ qua.")
            classified.append({"fileName": file_name, "docType": _DOC_OTHER, "source": "identity-skip"})
            continue
        if not doc_type:
            warnings.append(f"Không xác định được loại giấy tờ cho file '{file_name}' — bỏ qua, vui lòng đính kèm thủ công.")
            classified.append({"fileName": file_name, "docType": _DOC_OTHER, "source": "unknown"})
            continue

        items.append(_build_item(file, idx, doc_type))
        classified.append({
            "fileName": file_name,
            "docType": doc_type,
            "source": "llm" if llm_type in _SLOT_BY_KEY else "rule",
            "slotIndex": _SLOT_BY_KEY[doc_type]["slotIndex"],
        })

    return items, warnings, classified


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
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
            llm_docs.append({"index": idx, "text": text})

    t1 = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types)
    errors.extend(warnings)
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "classified": classified,
            "skippedOcr": skipped_ocr,
            "slots": SLOTS,
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "errors": errors,
    }
