"""Đính kèm cho thủ tục 1.010814 — cấp bổ sung/cấp lại giấy chứng nhận người có công, thân nhân liệt sĩ.

Bước "Thành phần hồ sơ" chỉ có MỘT dòng cố định: "Đơn đề nghị theo Mẫu số 25 Phụ lục I Nghị định số
131/2021/NĐ-CP" (1 Bản chính). Giấy tờ còn lại đi nút "+ Thêm giấy tờ" (target "new"):
- Đơn M25 → fixed-slot 0.
- Giấy chứng nhận đã cấp (bản cũ bị mất/hư hỏng), CCCD → dòng mới đặt tên theo loại giấy.
- Tệp không nhận ra loại vẫn thêm dòng "Giấy tờ kèm theo" kèm cảnh báo — không bỏ sót tệp nào.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.cap_bo_sung_cap_lai_giay_chung_nhan_nguoi_co_cong.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON_MAU25 = "don_de_nghi_mau25"
_GCN_CU = "giay_chung_nhan_cu"
_IDENTITY = "identity_document"
_OTHER = "other"

SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": _DON_MAU25,
        "slotIndex": 0,
        "slotName": "Đơn đề nghị theo Mẫu số 25 Phụ lục I Nghị định số 131/2021/NĐ-CP",
        "detectedType": "Đơn đề nghị cấp bổ sung/cấp lại giấy chứng nhận (Mẫu số 25)",
        "documentName": "Đơn đề nghị cấp bổ sung/cấp lại giấy chứng nhận (Mẫu số 25)",
    },
]
_SLOT_BY_KEY = {s["slotKey"]: s for s in SLOTS}

_NEW_DOCS: dict[str, dict[str, str]] = {
    _GCN_CU: {"documentName": "Giấy chứng nhận đã cấp", "detectedType": "Giấy chứng nhận đã cấp"},
    _IDENTITY: {"documentName": "Căn cước công dân", "detectedType": "Căn cước công dân"},
    _OTHER: {"documentName": "Giấy tờ kèm theo", "detectedType": "Giấy tờ khác"},
}
_ALLOWED_DOC_TYPES = set(_SLOT_BY_KEY) | set(_NEW_DOCS)

_GCN_SUBJECTS = ("than nhan liet si", "thuong binh", "benh binh", "nguoi co cong", "chat doc hoa hoc")


def _is_identity_text(haystack: str) -> bool:
    return any(
        marker in haystack
        for marker in (
            "can cuoc cong dan",
            "chung minh nhan dan",
            "the can cuoc",
            "citizen identity card",
            "identity card",
            "so dinh danh ca nhan",
            "ho chieu",
            "passport",
        )
    )


def _rule_doc_type(text: str) -> str:
    """Nhận Đơn M25 TRƯỚC: thân đơn cũng có cụm "giấy chứng nhận thân nhân liệt sĩ"."""
    haystack = _fold(text)
    if not haystack:
        return ""
    if "don de nghi" in haystack and (
        "mau so 25" in haystack
        or "cap bo sung hoac cap lai giay chung nhan" in haystack
        or ("cap bo sung/cap lai" in haystack and "nguoi lam don" in haystack)
    ):
        return _DON_MAU25
    if "giay chung nhan" in haystack and any(s in haystack for s in _GCN_SUBJECTS) and "nguoi lam don" not in haystack:
        return _GCN_CU
    if _is_identity_text(haystack):
        return _IDENTITY
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == _OTHER:
        return _OTHER
    if value in _ALLOWED_DOC_TYPES:
        return value
    if "mau25" in text or "mau so 25" in text or "don de nghi" in text:
        return _DON_MAU25
    if "giay chung nhan" in text or "gcn" in text:
        return _GCN_CU
    if any(m in text for m in ("can cuoc", "cccd", "cmnd", "identity", "ho chieu")):
        return _IDENTITY
    return _OTHER


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


def _build_fixed_item(file: dict, file_index: int, slot_key: str) -> dict:
    slot = _SLOT_BY_KEY[slot_key]
    return {
        "fileIndex": file_index,
        "fileName": str(file.get("name") or f"file-{file_index + 1}"),
        "documentName": slot["documentName"],
        "componentName": slot["slotName"],
        "target": "fixed-slot",
        "needsAddComponent": False,
        "detectedType": slot["detectedType"],
        "slotKey": slot["slotKey"],
        "slotIndex": slot["slotIndex"],
        "slotName": slot["slotName"],
    }


def _build_new_item(file: dict, file_index: int, doc_type: str) -> dict:
    cfg = _NEW_DOCS[doc_type]
    return {
        "fileIndex": file_index,
        "fileName": str(file.get("name") or f"file-{file_index + 1}"),
        "documentName": cfg["documentName"],
        "componentName": cfg["documentName"],
        "target": "new",
        "componentIndex": None,
        "needsAddComponent": True,
        "detectedType": cfg["detectedType"],
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
        doc_type = rule_type or (llm_type if llm_type in _ALLOWED_DOC_TYPES else _OTHER)
        source = "rule" if rule_type else ("llm" if llm_type else "unknown")

        if doc_type in _SLOT_BY_KEY:
            items.append(_build_fixed_item(file, idx, doc_type))
        else:
            items.append(_build_new_item(file, idx, doc_type))
            if doc_type == _OTHER:
                warnings.append(
                    f"Không nhận ra loại giấy tờ của file '{file_name}' — đã thêm dòng 'Giấy tờ kèm theo', "
                    "vui lòng sửa tên giấy tờ cho đúng."
                )
        classified.append({"fileName": file_name, "docType": doc_type, "source": source})

    if not any(item.get("slotKey") == _DON_MAU25 for item in items):
        warnings.append("Chưa có Đơn đề nghị Mẫu số 25 — dòng thành phần hồ sơ bắt buộc đang trống.")
    return items, warnings, classified


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    """Entry point đính kèm cho cap-bo-sung-cap-lai-giay-chung-nhan-nguoi-co-cong."""
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
        if text.strip() and not _rule_doc_type(text):
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

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "classified": classified,
            "skippedOcr": [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES],
            "slots": SLOTS,
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "errors": errors,
    }
