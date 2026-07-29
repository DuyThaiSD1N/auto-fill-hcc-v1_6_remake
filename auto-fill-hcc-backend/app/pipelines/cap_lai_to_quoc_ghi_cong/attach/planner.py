"""Đính kèm cho thủ tục Cấp lại Bằng Tổ quốc ghi công.

Bước "Thành phần hồ sơ" có 2 ô cố định (STT1 Đơn Mẫu 16, STT2 Bảng cũ "nếu còn") và mục
"Thêm giấy tờ"/"Giấy tờ khác" cho các giấy tờ còn lại. Planner phân loại từng file rồi:
- Đơn Mẫu 16 → fixed-slot 0; Bảng TQGC cũ → fixed-slot 1.
- CCCD, Công văn UBND, Danh sách đề nghị → target "new" (đính vào "Giấy tờ khác").
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.cap_lai_to_quoc_ghi_cong.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON_MAU16 = "don_de_nghi_mau16"
_BANG_CU = "bang_tqgc_cu"
_DANH_SACH = "danh_sach_de_nghi"
_CONG_VAN = "cong_van_ubnd"
_IDENTITY = "identity_document"
_OTHER = "other"

# 2 ô cố định trên form (đúng thứ tự hiển thị bước 3). slotName để log/khớp text; extension khớp
# theo FIXED_SLOT_KEYWORDS (FE) rồi fallback slotIndex — thủ tục này dùng fallback slotIndex.
SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": _DON_MAU16,
        "slotIndex": 0,
        "slotName": 'Đơn đề nghị theo Mẫu số 16 Phụ lục I Nghị định số 131/2021/NĐ-CP',
        "detectedType": "Đơn đề nghị cấp lại Bằng Tổ quốc ghi công (Mẫu số 16)",
        "documentName": "Đơn đề nghị cấp lại Bằng Tổ quốc ghi công (Mẫu số 16)",
    },
    {
        "slotKey": _BANG_CU,
        "slotIndex": 1,
        "slotName": 'Bảng "Tổ quốc ghi công" cũ nếu còn',
        "detectedType": 'Bằng "Tổ quốc ghi công" cũ',
        "documentName": 'Bằng "Tổ quốc ghi công" cũ',
    },
]
_SLOT_BY_KEY = {s["slotKey"]: s for s in SLOTS}

# Giấy tờ khác đính vào mục "Thêm giấy tờ" (target "new").
_NEW_DOCS: dict[str, dict[str, str]] = {
    _IDENTITY: {"documentName": "Căn cước công dân người nộp", "detectedType": "Căn cước công dân"},
    _CONG_VAN: {"documentName": "Công văn đề nghị của UBND cấp xã", "detectedType": "Công văn UBND"},
    _DANH_SACH: {
        "documentName": "Danh sách đề nghị cấp lại Bằng Tổ quốc ghi công",
        "detectedType": "Danh sách đề nghị cấp lại",
    },
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
            "identity card",
            "ho chieu",
            "passport",
        )
    )


def _rule_doc_type(text: str) -> str:
    """Phân loại nhanh bằng rule. Nhận diện Đơn Mẫu 16 TRƯỚC để tránh bị cụm 'Tổ quốc ghi công'
    kéo nhầm sang danh sách/công văn/bằng cũ."""
    haystack = _fold(text)
    if not haystack:
        return ""

    # 1. Đơn đề nghị Mẫu 16 — cụm tiêu đề + mục đặc trưng.
    if "to quoc ghi cong" in haystack and (
        "don de nghi" in haystack or "mau so 16" in haystack
    ) and (
        "thong tin nguoi de nghi" in haystack
        or "thong tin ve liet si" in haystack
        or "cap doi/cap lai" in haystack
        or "de nghi cap" in haystack
    ):
        return _DON_MAU16

    # 2. Danh sách đề nghị cấp lại (bảng nhiều cột).
    if ("danh sach" in haystack and "to quoc ghi cong" in haystack) or (
        "danh sach de nghi cap lai bang" in haystack
    ):
        return _DANH_SACH

    # 3. Công văn UBND.
    if "cv-ubnd" in haystack or ("cong van" in haystack and "ubnd" in haystack) or (
        "kinh gui" in haystack and "so noi vu" in haystack and "cap lai bang" in haystack
    ):
        return _CONG_VAN

    # 4. CCCD/giấy tùy thân.
    if _is_identity_text(haystack):
        return _IDENTITY

    # 5. Bằng Tổ quốc ghi công cũ (bản chụp tấm bằng) — bảo thủ, chủ yếu để LLM quyết.
    if "to quoc ghi cong" in haystack and "liet si" in haystack:
        return _BANG_CU

    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if "mau so 16" in text or "mau16" in text or ("don de nghi" in text and "to quoc ghi cong" in text):
        return _DON_MAU16
    if "danh sach" in text:
        return _DANH_SACH
    if "cong van" in text or "cv-ubnd" in text or "ubnd" in text:
        return _CONG_VAN
    if "can cuoc" in text or "cccd" in text or "cmnd" in text or "identity" in text or "ho chieu" in text:
        return _IDENTITY
    if "bang" in text and "cu" in text:
        return _BANG_CU
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
        # Rule thắng khi chắc chắn; nếu rule trống thì mới nghe LLM.
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
    """Entry point đính kèm cho cap-lai-to-quoc-ghi-cong."""
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
        # Chỉ hỏi LLM khi rule chưa chắc — tiết kiệm token, tránh lật rule đúng.
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
