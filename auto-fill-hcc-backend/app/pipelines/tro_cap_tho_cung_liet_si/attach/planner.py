"""Đính kèm cho thủ tục Giải quyết chế độ trợ cấp thờ cúng liệt sĩ.

Bước "Thành phần hồ sơ" có 3 ô cố định + "Thêm giấy tờ":
- STT1 (fixed-slot 0): Văn bản ủy quyền.
- STT2 (fixed-slot 1): Đơn đề nghị Mẫu số 18.
- STT3 (fixed-slot 2): Bản sao chứng thực từ Bằng "Tổ quốc ghi công".
- CCCD, Trích lục khai tử → target "new" ("Thêm giấy tờ").
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.tro_cap_tho_cung_liet_si.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_UY_QUYEN = "van_ban_uy_quyen"
_DON = "don_de_nghi"
_BANG = "bang_tqgc"
_CCCD = "cccd"
_KHAI_TU = "trich_luc_khai_tu"
_OTHER = "other"

SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": _UY_QUYEN,
        "slotIndex": 0,
        "slotName": "Văn bản ủy quyền",
        "detectedType": "Văn bản ủy quyền",
        "documentName": "Văn bản ủy quyền thờ cúng liệt sĩ",
    },
    {
        "slotKey": _DON,
        "slotIndex": 1,
        "slotName": "Đơn đề nghị Mẫu số 18 Phụ lục I Nghị định số 131/2021/NĐ-CP",
        "detectedType": "Đơn đề nghị giải quyết chế độ trợ cấp thờ cúng liệt sĩ",
        "documentName": "Đơn đề nghị giải quyết chế độ trợ cấp thờ cúng liệt sĩ (Mẫu số 18)",
    },
    {
        "slotKey": _BANG,
        "slotIndex": 2,
        "slotName": 'Bản sao chứng thực từ Bằng "Tổ quốc ghi công"',
        "detectedType": 'Bằng "Tổ quốc ghi công"',
        "documentName": 'Bằng "Tổ quốc ghi công"',
    },
]
_SLOT_BY_KEY = {s["slotKey"]: s for s in SLOTS}

_NEW_DOCS: dict[str, dict[str, str]] = {
    _CCCD: {"documentName": "Căn cước công dân người nộp", "detectedType": "Căn cước công dân"},
    _KHAI_TU: {"documentName": "Trích lục khai tử thân nhân liệt sĩ", "detectedType": "Trích lục khai tử"},
}
_ALLOWED_DOC_TYPES = set(_SLOT_BY_KEY) | set(_NEW_DOCS) | {_OTHER}


def _is_identity_text(text: str) -> bool:
    haystack = _fold(text)
    return any(
        marker in haystack
        for marker in (
            "can cuoc cong dan",
            "chung minh nhan dan",
            "the can cuoc",
            "citizen identity card",
            "ho chieu",
            "passport",
        )
    )


def _rule_doc_type(text: str) -> str:
    """Phân loại nhanh bằng rule. Nhận diện Đơn TRƯỚC vì đơn cũng nhắc 'ủy quyền'/'Tổ quốc ghi công'."""
    haystack = _fold(text)
    if not haystack:
        return ""

    # 1. Đơn đề nghị trợ cấp thờ cúng (Mẫu 18).
    if ("don de nghi" in haystack and "tho cung liet si" in haystack) or "mau so 18" in haystack:
        return _DON

    # 2. Trích lục khai tử / giấy chứng tử.
    if "trich luc khai tu" in haystack or "giay chung tu" in haystack:
        return _KHAI_TU

    # 3. Văn bản ủy quyền.
    if "uy quyen" in haystack and ("tho cung" in haystack or "bien ban hop" in haystack or "gia dinh" in haystack):
        return _UY_QUYEN

    # 4. Bằng Tổ quốc ghi công.
    if "to quoc ghi cong" in haystack and ("bang so" in haystack or "quyet dinh so" in haystack):
        return _BANG

    # 5. CCCD/giấy tùy thân.
    if _is_identity_text(haystack):
        return _CCCD

    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if "don" in text and "tho cung" in text:
        return _DON
    if "khai tu" in text or "chung tu" in text:
        return _KHAI_TU
    if "uy quyen" in text:
        return _UY_QUYEN
    if "bang" in text and ("to quoc" in text or "ghi cong" in text):
        return _BANG
    if any(k in text for k in ("can cuoc", "cccd", "cmnd", "ho chieu", "identity")):
        return _CCCD
    return value if value in _ALLOWED_DOC_TYPES else _OTHER


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


def _build_new_item(file: dict, file_index: int, doc_type: str) -> dict:
    cfg = _NEW_DOCS[doc_type]
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    return {
        "fileIndex": file_index,
        "fileName": file_name,
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

        if doc_type in _SLOT_BY_KEY:
            items.append(_build_fixed_item(file, idx, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "source": "rule" if rule_type else "llm"})
            continue
        if doc_type in _NEW_DOCS:
            items.append(_build_new_item(file, idx, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "source": "rule" if rule_type else "llm"})
            continue

        warnings.append(f"Không xác định được loại giấy tờ cho file '{file_name}' — bỏ qua, vui lòng đính kèm thủ công.")
        classified.append({"fileName": file_name, "docType": _OTHER, "source": "unknown"})

    return items, warnings, classified


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    """Entry point đính kèm cho tro-cap-tho-cung-liet-si."""
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
