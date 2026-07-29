"""Đính kèm cho thủ tục Bổ sung tình hình thân nhân trong hồ sơ liệt sĩ.

Bước "Thành phần hồ sơ" có 2 ô cố định + "Thêm giấy tờ":
- STT1 (fixed-slot 0): bản sao chứng thực giấy tờ CHỨNG MINH QUAN HỆ với liệt sĩ
  (CCCD/CMND, giấy khai sinh, trích lục khai sinh, đăng ký kết hôn, lý lịch).
- STT2 (fixed-slot 1): Đơn đề nghị sửa đổi, bổ sung (Mẫu 06/26).
- Hồ sơ liệt sĩ, Bằng TQGC, Công văn UBND → target "new" (đính vào "Giấy tờ khác").
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.bo_sung_than_nhan_liet_si.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_CHUNG_MINH_QH = "giay_to_chung_minh_quan_he"
_DON = "don_sua_doi_bo_sung"
_HO_SO_LS = "ho_so_liet_si"
_BANG = "bang_tqgc"
_CONG_VAN = "cong_van_ubnd"
_OTHER = "other"

# 2 ô cố định (đúng thứ tự hiển thị bước 3). FE khớp theo FIXED_SLOT_KEYWORDS (không có key này)
# rồi fallback slotIndex — thủ tục này dùng fallback slotIndex.
SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": _CHUNG_MINH_QH,
        "slotIndex": 0,
        "slotName": "Bản sao được chứng thực từ một trong các giấy tờ chứng minh mối quan hệ với liệt sĩ",
        "detectedType": "Giấy tờ chứng minh quan hệ với liệt sĩ",
        "documentName": "Giấy tờ chứng minh quan hệ với liệt sĩ",
    },
    {
        "slotKey": _DON,
        "slotIndex": 1,
        "slotName": "Đơn đề nghị theo Mẫu số 06 Phụ lục I Nghị định số 131/2021/NĐ-CP",
        "detectedType": "Đơn đề nghị sửa đổi, bổ sung thông tin trong hồ sơ liệt sĩ",
        "documentName": "Đơn đề nghị sửa đổi, bổ sung thông tin trong hồ sơ liệt sĩ",
    },
]
_SLOT_BY_KEY = {s["slotKey"]: s for s in SLOTS}

_NEW_DOCS: dict[str, dict[str, str]] = {
    _HO_SO_LS: {"documentName": "Hồ sơ liệt sĩ", "detectedType": "Hồ sơ liệt sĩ"},
    _BANG: {"documentName": 'Bằng "Tổ quốc ghi công"', "detectedType": 'Bằng "Tổ quốc ghi công"'},
    _CONG_VAN: {"documentName": "Công văn đề nghị của UBND cấp xã", "detectedType": "Công văn UBND"},
}
_ALLOWED_DOC_TYPES = set(_SLOT_BY_KEY) | set(_NEW_DOCS) | {_OTHER}


def _is_identity_or_relation_text(text: str) -> bool:
    haystack = _fold(text)
    return any(
        marker in haystack
        for marker in (
            "can cuoc cong dan",
            "chung minh nhan dan",
            "the can cuoc",
            "citizen identity card",
            "giay khai sinh",
            "trich luc khai sinh",
            "dang ky ket hon",
            "ly lich can bo",
            "ly lich dang vien",
            "ly lich quan nhan",
        )
    )


def _rule_doc_type(text: str) -> str:
    """Phân loại nhanh bằng rule. Nhận diện Đơn TRƯỚC vì đơn cũng nhắc 'hồ sơ liệt sĩ'."""
    haystack = _fold(text)
    if not haystack:
        return ""

    # 1. Đơn đề nghị sửa đổi, bổ sung (Mẫu 26/06).
    if "sua doi bo sung thong tin trong ho so liet si" in haystack or (
        "don de nghi" in haystack
        and "sua doi" in haystack
        and ("ho so liet si" in haystack or "mau so 26" in haystack or "mau so 06" in haystack)
    ) or "thuoc dien nguoi co cong" in haystack:
        return _DON

    # 2. Công văn UBND.
    if "cv-ubnd" in haystack or ("cong van" in haystack and "ubnd" in haystack) or (
        "kinh gui" in haystack and "so noi vu" in haystack and "sua doi" in haystack
    ):
        return _CONG_VAN

    # 3. Bằng Tổ quốc ghi công (tấm bằng).
    if "to quoc ghi cong" in haystack and ("bang so" in haystack or "quyet dinh so" in haystack):
        return _BANG

    # 4. Giấy tờ chứng minh quan hệ (CCCD/GKS/trích lục/kết hôn/lý lịch).
    if _is_identity_or_relation_text(haystack):
        return _CHUNG_MINH_QH

    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if "don" in text and "sua doi" in text:
        return _DON
    if "cong van" in text or "cv-ubnd" in text or "ubnd" in text:
        return _CONG_VAN
    if "bang" in text and ("to quoc" in text or "ghi cong" in text):
        return _BANG
    if "ho so liet si" in text:
        return _HO_SO_LS
    if any(k in text for k in ("can cuoc", "cccd", "cmnd", "khai sinh", "ket hon", "ly lich", "chung minh quan he")):
        return _CHUNG_MINH_QH
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
    """Entry point đính kèm cho bo-sung-than-nhan-liet-si."""
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
