"""Đính kèm bước "Thành phần hồ sơ" cho thủ tục "Sửa đổi, bổ sung thông tin cá nhân trong hồ sơ
người có công" (cổng MOHA).

2 thành phần cố định (nút "Chọn tệp" — engine attach MOHA fixed-slot):
  slot 0  Bản sao có chứng thực CCCD/CMND của người có công hoặc thân nhân   ← cccd
  slot 1  Đơn đề nghị theo Mẫu số 26 Phụ lục I Nghị định số 131/2021/NĐ-CP   ← don_mau_26

Giấy tờ nguồn khác (Bản khai thân nhân, Giấy khai sinh, Trích lục khai tử, Bằng Tổ quốc ghi công,
Công văn/Tờ trình Sở Nội vụ...) KHÔNG có ô cố định riêng (chỉ đính kèm bổ sung qua FormArray text,
extension không tải file vào đó) → BỎ QUA (skipped), KHÔNG route "new" (form không có nút "Thêm thành
phần hồ sơ"). Route TẤT ĐỊNH theo rule OCR; LLM dự phòng khi rule không chắc.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.sua_doi_thong_tin_ho_so_nguoi_co_cong.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_CCCD = "cccd"
_DON = "don_mau_26"
_BAN_KHAI = "ban_khai"
_KHAI_SINH = "giay_khai_sinh"
_KHAI_TU = "trich_luc_khai_tu"
_TQGC = "to_quoc_ghi_cong"
_CONG_VAN = "cong_van_so"
_OTHER = "other"

SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": _CCCD,
        "slotIndex": 0,
        "slotName": "Bản sao có chứng thực căn cước công dân, chứng minh nhân dân của người có công hoặc thân nhân",
        "detectedType": "CCCD/CMND",
        "documentName": "Bản sao chứng thực CCCD/CMND",
    },
    {
        "slotKey": _DON,
        "slotIndex": 1,
        "slotName": "Đơn đề nghị theo Mẫu số 26 Phụ lục I Nghị định số 131/2021/NĐ-CP",
        "detectedType": "Đơn đề nghị Mẫu số 26",
        "documentName": "Đơn đề nghị sửa đổi, bổ sung thông tin (Mẫu số 26)",
    },
]
_SLOT_BY_KEY = {s["slotKey"]: s for s in SLOTS}

# Giấy tờ nguồn KHÁC (Bản khai / khai sinh / trích lục khai tử / TQGC / công văn) không có ô cố định
# → BỎ QUA, không route "new" (form MOHA này không có nút "Thêm thành phần hồ sơ").
_SKIP_DOCS = {_BAN_KHAI, _KHAI_SINH, _KHAI_TU, _TQGC, _CONG_VAN}
_ALLOWED_DOC_TYPES = set(_SLOT_BY_KEY) | _SKIP_DOCS | {_OTHER}


def _is_identity_text(text: str) -> bool:
    haystack = _fold(text)
    return any(
        m in haystack
        for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "citizen identity", "ho chieu", "passport")
    )


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR. Nhận Đơn Mẫu 26 và các giấy tờ đặc trưng TRƯỚC, CCCD sau cùng."""
    h = _fold(text)
    if not h:
        return ""
    # Đơn đề nghị Mẫu số 26 — tiêu đề "ĐƠN ĐỀ NGHỊ" + "sửa đổi, bổ sung thông tin" hoặc "mẫu số 26".
    if "mau so 26" in h or ("don de nghi" in h and "sua doi" in h and "bo sung" in h):
        return _DON
    # Trích lục khai tử / giấy báo tử của liệt sĩ.
    if "trich luc khai tu" in h or "giay bao tu" in h or ("khai tu" in h and "trich luc" in h):
        return _KHAI_TU
    # Bằng Tổ quốc ghi công.
    if "to quoc ghi cong" in h or "bang to quoc" in h:
        return _TQGC
    # Giấy khai sinh (tránh nhầm trích lục khai tử ở trên).
    if "giay khai sinh" in h or "trich luc khai sinh" in h or "ban sao khai sinh" in h:
        return _KHAI_SINH
    # Công văn / Tờ trình của Sở Nội vụ.
    if "cong van" in h or "to trinh" in h:
        return _CONG_VAN
    # Bản khai thân nhân / tình hình thân nhân liệt sĩ.
    if "ban khai" in h and ("than nhan" in h or "tinh hinh than nhan" in h or "mau so 05" in h):
        return _BAN_KHAI
    # CCCD/CMND (nhận sau cùng vì đơn/bản khai cũng nhắc số CCCD).
    if _is_identity_text(h):
        return _CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if "mau so 26" in text or ("don" in text and "sua doi" in text):
        return _DON
    if "khai tu" in text or "bao tu" in text:
        return _KHAI_TU
    if "to quoc ghi cong" in text:
        return _TQGC
    if "khai sinh" in text:
        return _KHAI_SINH
    if "cong van" in text or "to trinh" in text:
        return _CONG_VAN
    if "ban khai" in text:
        return _BAN_KHAI
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
        if doc_type in _SKIP_DOCS:
            # Giấy tờ nguồn (bản khai/khai sinh/khai tử/TQGC/công văn) — không có ô cố định → bỏ qua.
            classified.append({"fileName": file_name, "docType": doc_type, "source": "rule" if rule_type else "llm", "skipped": True})
            continue

        warnings.append(f"Không xác định được loại giấy tờ cho file '{file_name}' — vui lòng đính kèm thủ công.")
        classified.append({"fileName": file_name, "docType": _OTHER, "source": "unknown"})

    return items, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
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
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
