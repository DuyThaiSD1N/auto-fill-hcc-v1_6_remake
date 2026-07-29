"""Đính kèm cho thủ tục Hưởng trợ cấp khi người có công đang hưởng trợ cấp ưu đãi từ trần.

Bước "Thành phần hồ sơ" có 2 ô cố định (2 nhánh trợ cấp: a) một lần/mai táng · b) tuất hằng tháng),
cả hai đều nhận Bản khai Mẫu 12 + trích lục khai tử. Vì không xác định được nhánh từ OCR, mặc định
đính Bản khai vào ô 1 (nhánh a — trợ cấp một lần, phổ biến); các giấy tờ còn lại (trích lục khai tử,
giấy khai sinh, CCCD, biên bản họp GĐ, danh sách) → target "new" ("Thêm giấy tờ").
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.uu_dai_ncc_tu_tran.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_BAN_KHAI = "ban_khai"
_KHAI_TU = "trich_luc_khai_tu"
_KHAI_SINH = "giay_khai_sinh"
_BIEN_BAN = "bien_ban_hop"
_DANH_SACH = "danh_sach"
_CCCD = "cccd"
_OTHER = "other"

SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": _BAN_KHAI,
        "slotIndex": 0,
        "slotName": "Trợ cấp một lần, mai táng – Bản khai theo Mẫu số 12 Phụ lục I Nghị định số 131/2021/NĐ-CP",
        "detectedType": "Bản khai Mẫu số 12",
        "documentName": "Bản khai giải quyết chế độ ưu đãi khi người có công từ trần (Mẫu số 12)",
    },
]
_SLOT_BY_KEY = {s["slotKey"]: s for s in SLOTS}

_NEW_DOCS: dict[str, dict[str, str]] = {
    _KHAI_TU: {"documentName": "Trích lục khai tử/giấy báo tử", "detectedType": "Trích lục khai tử"},
    _KHAI_SINH: {"documentName": "Giấy khai sinh/trích lục khai sinh", "detectedType": "Giấy khai sinh"},
    _BIEN_BAN: {"documentName": "Biên bản họp gia đình", "detectedType": "Biên bản họp gia đình"},
    _DANH_SACH: {"documentName": "Danh sách đề nghị trợ cấp", "detectedType": "Danh sách đề nghị"},
    _CCCD: {"documentName": "Căn cước công dân", "detectedType": "Căn cước công dân"},
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
    """Phân loại nhanh bằng rule. Nhận diện Bản khai TRƯỚC (đơn cũng nhắc khai tử/thân nhân)."""
    haystack = _fold(text)
    if not haystack:
        return ""

    # 1. Bản khai Mẫu 12.
    if ("ban khai" in haystack and ("tu tran" in haystack or "nguoi co cong" in haystack)) or "mau so 12" in haystack:
        return _BAN_KHAI

    # 2. Trích lục khai TỬ (ưu tiên trước khai sinh vì cùng chứa "khai").
    if "khai tu" in haystack or "giay chung tu" in haystack or "giay bao tu" in haystack:
        return _KHAI_TU

    # 3. Giấy khai SINH.
    if "khai sinh" in haystack:
        return _KHAI_SINH

    # 4. Biên bản họp gia đình.
    if "bien ban hop gia dinh" in haystack or ("bien ban" in haystack and "gia dinh" in haystack):
        return _BIEN_BAN

    # 5. Danh sách đề nghị.
    if "danh sach de nghi" in haystack and ("tro cap" in haystack or "mai tang" in haystack):
        return _DANH_SACH

    # 6. CCCD/giấy tùy thân.
    if _is_identity_text(haystack):
        return _CCCD

    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if "ban khai" in text or "mau so 12" in text:
        return _BAN_KHAI
    if "khai tu" in text or "chung tu" in text or "bao tu" in text:
        return _KHAI_TU
    if "khai sinh" in text:
        return _KHAI_SINH
    if "bien ban" in text:
        return _BIEN_BAN
    if "danh sach" in text:
        return _DANH_SACH
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
    """Entry point đính kèm cho uu-dai-ncc-tu-tran."""
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
