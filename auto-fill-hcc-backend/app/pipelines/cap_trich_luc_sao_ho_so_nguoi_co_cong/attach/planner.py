"""Đính kèm cho thủ tục 1.010828 — cấp trích lục hoặc sao hồ sơ người có công với cách mạng.

Bước "Thành phần hồ sơ" chỉ có MỘT dòng: "Đơn đề nghị hoặc văn bản đề nghị cấp trích lục hoặc sao một số giấy tờ
trong hồ sơ hoặc toàn bộ hồ sơ người có công" (1 Bản chính). Theo ánh xạ đính kèm: tích dòng 1 rồi chọn CÙNG LÚC
mọi tệp ở "Chọn tệp tin" — Đơn đề nghị + CCCD (không có dòng riêng) đính CHUNG dòng 1, giữ nguyên từng tệp, không
tách trang. Tệp chưa rõ loại cũng đính dòng 1 kèm cảnh báo — không bỏ sót tệp nào.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.cap_trich_luc_sao_ho_so_nguoi_co_cong.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON = "don_de_nghi"
_IDENTITY = "identity_document"
_OTHER = "other"

SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": _DON,
        "slotIndex": 0,
        "slotName": (
            "Đơn đề nghị hoặc văn bản đề nghị cấp trích lục hoặc sao một số giấy tờ trong hồ sơ hoặc toàn bộ hồ sơ "
            "người có công"
        ),
        "slotKeywords": ["cap trich luc hoac sao", "toan bo ho so nguoi co cong"],
        "detectedType": "Đơn đề nghị cấp trích lục hoặc sao hồ sơ người có công",
        "documentName": "Đơn đề nghị cấp trích lục hoặc sao hồ sơ người có công",
    },
]
_SLOT_BY_KEY = {s["slotKey"]: s for s in SLOTS}

# Giấy không có dòng riêng → vẫn vào dòng Đơn, chỉ đổi tên hiển thị.
_EXTRA_DOCS: dict[str, dict[str, str]] = {
    _IDENTITY: {"documentName": "Căn cước công dân", "detectedType": "Căn cước công dân"},
    _OTHER: {"documentName": "Giấy tờ kèm theo", "detectedType": "Giấy tờ khác"},
}
_ALLOWED_DOC_TYPES = set(_SLOT_BY_KEY) | set(_EXTRA_DOCS)
# Đơn trước, CCCD sau: cổng hiển thị tệp theo thứ tự chọn.
_ORDER = {_DON: 0, _IDENTITY: 1, _OTHER: 2}


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
            "idvnm",
            "ho chieu",
            "passport",
        )
    )


def _rule_doc_type(text: str) -> str:
    """Nhận Đơn TRƯỚC: thân đơn có dòng "CCCD/CMND số" nhưng không có nhãn của thẻ."""
    haystack = _fold(text)
    if not haystack:
        return ""
    if ("don de nghi" in haystack or "van ban de nghi" in haystack) and (
        "nguoi lam don" in haystack
        or "trich luc" in haystack
        or "di chuyen ho so" in haystack
        or "nguoi co cong" in haystack
    ):
        return _DON
    if _is_identity_text(haystack):
        return _IDENTITY
    return ""


def _is_don_di_chuyen(text: str) -> bool:
    haystack = _fold(text)
    return "di chuyen ho so" in haystack and "trich luc" not in haystack and "sao ho so" not in haystack


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == _OTHER:
        return _OTHER
    if value in _ALLOWED_DOC_TYPES:
        return value
    if "don" in text or "de nghi" in text:
        return _DON
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


def _build_item(file: dict, file_index: int, doc_type: str) -> dict:
    slot = _SLOT_BY_KEY[_DON]
    cfg = _EXTRA_DOCS.get(doc_type) or slot
    return {
        "fileIndex": file_index,
        "fileName": str(file.get("name") or f"file-{file_index + 1}"),
        "documentName": cfg["documentName"],
        "componentName": slot["slotName"],
        "target": "fixed-slot",
        "needsAddComponent": False,
        "detectedType": cfg["detectedType"],
        "slotKey": slot["slotKey"],
        "slotIndex": slot["slotIndex"],
        "slotName": slot["slotName"],
        "slotKeywords": slot["slotKeywords"],
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
    di_chuyen = False

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = str(by_name.get(file_name, {}).get("text") or "")
        rule_type = _rule_doc_type(text)
        llm_type = llm_types.get(idx, "")
        doc_type = rule_type or (llm_type if llm_type in _ALLOWED_DOC_TYPES else _OTHER)
        source = "rule" if rule_type else ("llm" if llm_type else "unknown")

        items.append(_build_item(file, idx, doc_type))
        if doc_type == _DON and _is_don_di_chuyen(text):
            di_chuyen = True
        if doc_type == _OTHER:
            warnings.append(
                f"Không nhận ra loại giấy tờ của file '{file_name}' — đã đính chung dòng Đơn đề nghị, vui lòng kiểm "
                "tra lại."
            )
        classified.append({"fileName": file_name, "docType": doc_type, "source": source})

    items.sort(key=lambda item: (_ORDER[classified[item["fileIndex"]]["docType"]], item["fileIndex"]))
    if not any(c["docType"] == _DON for c in classified):
        warnings.append("Chưa có Đơn đề nghị cấp trích lục hoặc sao hồ sơ — dòng thành phần hồ sơ bắt buộc thiếu đơn.")
    if di_chuyen:
        warnings.append(
            "Dòng 1 yêu cầu đơn cấp trích lục hoặc sao hồ sơ, còn đơn trong hồ sơ là đơn đề nghị di chuyển hồ sơ — cần "
            "xác nhận đúng thủ tục trước khi nộp."
        )
    return items, warnings, classified


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    """Entry point đính kèm cho cap-trich-luc-sao-ho-so-nguoi-co-cong."""
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
