"""Đính kèm bước "Thành phần hồ sơ" cho thủ tục giải quyết chế độ người HĐKC GPDT (cổng MOHA).

3 thành phần cố định (Angular Reactive Form, nút "Chọn tệp" — engine attach MOHA fixed-slot):
  slot 0  Bản khai theo Mẫu số 11 (bản chính)            ← ban_khai
  slot 1  Giấy báo tử / trích lục khai tử                ← giay_bao_tu (chỉ khi đối tượng đã chết)
  slot 2  Bản sao Huân/Huy chương Kháng chiến, Chiến thắng ← huy_chuong

Giấy tờ nguồn khác (CCCD, Sổ BHXH...) không có ô riêng → target "new" (Thêm giấy tờ). Mọi file có OCR
đều được LLM phân loại trước; rule OCR chỉ dự phòng. Riêng file gộp nhiều giấy phải ưu tiên Bản khai.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.giai_quyet_che_do_khang_chien.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_BAN_KHAI = "ban_khai"
_BAO_TU = "giay_bao_tu"
_HUY_CHUONG = "huy_chuong"
_CCCD = "cccd"
_BHXH = "so_bhxh"
_OTHER = "other"

SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": _BAN_KHAI,
        "slotIndex": 0,
        "slotName": "Bản khai theo Mẫu số 11 Phụ lục I Nghị định số 131/2021/NĐ-CP",
        "detectedType": "Bản khai Mẫu số 11",
        "documentName": "Bản khai của người hoạt động kháng chiến (Mẫu số 11)",
    },
    {
        "slotKey": _BAO_TU,
        "slotIndex": 1,
        "slotName": "Giấy báo tử hoặc trích lục khai tử",
        "detectedType": "Giấy báo tử/trích lục khai tử",
        "documentName": "Giấy báo tử hoặc trích lục khai tử",
    },
    {
        "slotKey": _HUY_CHUONG,
        "slotIndex": 2,
        "slotName": "Bản sao chứng thực Huân chương, Huy chương Kháng chiến, Chiến thắng hoặc quyết định tặng thưởng",
        "detectedType": "Huân/Huy chương Kháng chiến",
        "documentName": "Bản sao Huân/Huy chương Kháng chiến, Chiến thắng",
    },
]
_SLOT_BY_KEY = {s["slotKey"]: s for s in SLOTS}

# CCCD/Sổ BHXH là GIẤY TỜ NGUỒN (để điền form), KHÔNG thuộc 3 thành phần hồ sơ bắt buộc
# (Bản khai / Giấy báo tử / Huân-Huy chương). Form MOHA này KHÔNG có nút "Thêm thành phần hồ sơ"
# → KHÔNG route sang target "new" (sẽ lỗi "không tìm thấy nút"). Chỉ bỏ qua, không đính kèm.
_SKIP_DOCS = {_CCCD, _BHXH}
_NEW_DOCS: dict[str, dict[str, str]] = {}
_ALLOWED_DOC_TYPES = set(_SLOT_BY_KEY) | _SKIP_DOCS | {_OTHER}


def _is_identity_text(text: str) -> bool:
    haystack = _fold(text)
    return any(
        m in haystack
        for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "citizen identity", "ho chieu", "passport")
    )


def _rule_doc_type(text: str) -> str:
    """Rule dự phòng; Bản khai Mẫu 11/12 luôn thắng tài liệu khác trong cùng file."""
    h = _fold(text)
    if not h:
        return ""
    # Mẫu 12 có thể gộp cả trích lục khai tử và CCCD phía sau. Chỉ nhận Mẫu 11/12
    # khi đồng thời có tiêu đề BẢN KHAI để tránh bắt nhầm biểu mẫu số 12 của thủ tục khác.
    is_declaration = "ban khai" in h and any(
        marker in h
        for marker in (
            "mau so 11",
            "mau so 12",
            "hoat dong khang chien",
            "khang chien giai phong",
            "nguoi co cong tu tran",
        )
    )
    if is_declaration:
        return _BAN_KHAI
    # Giấy báo tử / khai tử.
    if "khai tu" in h or "giay bao tu" in h or "giay chung tu" in h:
        return _BAO_TU
    # Huân/Huy chương / quyết định khen thưởng.
    if any(k in h for k in ("huy chuong khang chien", "huan chuong khang chien", "huy chuong chien thang",
                            "huan chuong", "huy chuong", "khen thuong")):
        return _HUY_CHUONG
    # Sổ BHXH.
    if "bao hiem xa hoi" in h or "so bhxh" in h or "qua trinh dong bhxh" in h:
        return _BHXH
    if _is_identity_text(h):
        return _CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if "ban khai" in text or "mau so 11" in text or "mau so 12" in text:
        return _BAN_KHAI
    if "bao tu" in text or "khai tu" in text or "chung tu" in text:
        return _BAO_TU
    if "huy chuong" in text or "huan chuong" in text or "khen thuong" in text:
        return _HUY_CHUONG
    if "bhxh" in text or "bao hiem" in text:
        return _BHXH
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
        valid_llm_type = llm_type if llm_type in _ALLOWED_DOC_TYPES else ""

        # LLM là nguồn phân loại đầu tiên. Ngoại lệ nghiệp vụ duy nhất: nếu một
        # file gộp có Bản khai Mẫu 11/12 thì Bản khai luôn là loại đại diện.
        if rule_type == _BAN_KHAI:
            doc_type = _BAN_KHAI
            source = "llm" if valid_llm_type == _BAN_KHAI else "rule-priority"
        elif valid_llm_type and valid_llm_type != _OTHER:
            doc_type = valid_llm_type
            source = "llm"
        elif rule_type:
            doc_type = rule_type
            source = "rule"
        else:
            doc_type = _OTHER
            source = "llm" if valid_llm_type == _OTHER else "unknown"

        if doc_type in _SLOT_BY_KEY:
            items.append(_build_fixed_item(file, idx, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "source": source})
            continue
        if doc_type in _SKIP_DOCS:
            # Giấy tờ nguồn (CCCD/BHXH) — chỉ dùng để điền form, KHÔNG thuộc thành phần hồ sơ → bỏ qua.
            classified.append({"fileName": file_name, "docType": doc_type, "source": source, "skipped": True})
            continue

        warnings.append(f"Không xác định được loại giấy tờ cho file '{file_name}' — vui lòng đính kèm thủ công.")
        classified.append({"fileName": file_name, "docType": _OTHER, "source": source})

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
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
