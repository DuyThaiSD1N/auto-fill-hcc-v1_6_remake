"""Đính kèm bước "Thành phần hồ sơ" cho thủ tục mai táng phí dân công hỏa tuyến (cổng MOHA).

Form Angular Reactive CHỈ có 2 ô CỐ ĐỊNH (KHÔNG có nút "Thêm giấy tờ" — engine attach MOHA fixed-slot):
  slot 0  "Bản trích sao quyết định của đối tượng từ trần đã được hưởng chế độ trợ cấp một lần; ..."
  slot 1  "Giấy chứng tử"

QUY TẮC ĐÍNH (theo cổng thật): CHỈ Trích lục khai tử/Giấy chứng tử → slot 1 (dòng 2). MỌI file còn lại
(Bản khai Mẫu 02-MTP, Biên bản 80A, CCCD, Quyết định trợ cấp, kể cả PDF gộp & giấy tờ chưa rõ loại) →
slot 0 (dòng 1). Ô upload nhận NHIỀU file nên gom được cả bộ vào dòng 1.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.mai_tang_dan_cong.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_QD_TRO_CAP = "qd_tro_cap"
_GIAY_CHUNG_TU = "giay_chung_tu"
_BAN_KHAI_02MTP = "ban_khai_02mtp"
_BIEN_BAN_80A = "bien_ban_80a"
_CCCD = "cccd"
_OTHER = "other"

_SLOT_QD = {
    "slotIndex": 0,
    "slotName": "Bản trích sao quyết định của đối tượng từ trần đã được hưởng chế độ trợ cấp một lần",
}
_SLOT_CHUNG_TU = {"slotIndex": 1, "slotName": "Giấy chứng tử"}
SLOTS = [_SLOT_QD, _SLOT_CHUNG_TU]

# Tên hiển thị cho file đính (theo loại phát hiện được). File loại khác/không rõ giữ tên gốc.
_DOC_NAME = {
    _QD_TRO_CAP: "Bản trích sao Quyết định trợ cấp một lần của đối tượng từ trần",
    _GIAY_CHUNG_TU: "Trích lục khai tử (thay Giấy chứng tử)",
    _BAN_KHAI_02MTP: "Bản khai của thân nhân (Mẫu 02-MTP)",
    _BIEN_BAN_80A: "Biên bản họp đồng thuận (Mẫu số 80A)",
    _CCCD: "Căn cước công dân người khai",
}
_ALLOWED_DOC_TYPES = {_QD_TRO_CAP, _GIAY_CHUNG_TU, _BAN_KHAI_02MTP, _BIEN_BAN_80A, _CCCD, _OTHER}


def _is_identity_text(text: str) -> bool:
    h = _fold(text)
    return any(
        m in h
        for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "citizen identity", "ho chieu", "passport")
    )


def _rule_doc_type(text: str) -> str:
    """Rule dự phòng; ưu tiên nhận Bản khai 02-MTP cho file gộp (để đặt tên đúng)."""
    h = _fold(text)
    if not h:
        return ""
    if "ban khai" in h and ("mai tang phi" in h or "02-mtp" in h or "02 mtp" in h or "phan khai ve than nhan" in h):
        return _BAN_KHAI_02MTP
    if "bien ban" in h and ("dong thuan" in h or "cung hang thua ke" in h or "80a" in h):
        return _BIEN_BAN_80A
    if "trich luc khai tu" in h or "giay chung tu" in h or "giay bao tu" in h:
        return _GIAY_CHUNG_TU
    if ("quyet dinh" in h or "qd-btl" in h or "trich sao" in h) and ("tro cap mot lan" in h or "mot lan" in h or "qd-btl" in h):
        return _QD_TRO_CAP
    if _is_identity_text(h):
        return _CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if "02-mtp" in text or "02 mtp" in text or ("ban khai" in text and "mai tang" in text) or "than nhan" in text:
        return _BAN_KHAI_02MTP
    if "80a" in text or "dong thuan" in text or "bien ban" in text:
        return _BIEN_BAN_80A
    if "khai tu" in text or "chung tu" in text or "bao tu" in text:
        return _GIAY_CHUNG_TU
    if "tro cap" in text or "qd-btl" in text or "trich sao" in text or "quyet dinh" in text:
        return _QD_TRO_CAP
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


def _build_item(file: dict, file_index: int, doc_type: str) -> dict:
    # CHỈ Giấy chứng tử/Trích lục khai tử vào slot 1; MỌI loại khác (kể cả 'other') vào slot 0.
    slot = _SLOT_CHUNG_TU if doc_type == _GIAY_CHUNG_TU else _SLOT_QD
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    document_name = _DOC_NAME.get(doc_type) or file_name
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": slot["slotName"],
        "target": "fixed-slot",
        "needsAddComponent": False,
        "detectedType": doc_type,
        "slotKey": "giay_chung_tu" if doc_type == _GIAY_CHUNG_TU else "hs_dinh_kem",
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
        llm_type = llm_types.get(idx, "")
        valid_llm = llm_type if llm_type in _ALLOWED_DOC_TYPES else ""

        # LLM-PRIMARY: luôn ưu tiên phán đoán của LLM. Rule keyword CHỈ dùng dự phòng khi LLM lỗi (502)/
        # trả rỗng/không hợp lệ. Prompt đã dặn: file gộp có Bản khai → ban_khai (không nhầm giấy chứng tử);
        # chỉ Trích lục khai tử ĐỘC LẬP mới là giay_chung_tu → slot 1. Các loại khác đều về slot 0.
        if valid_llm and valid_llm != _OTHER:
            doc_type, source = valid_llm, "llm"
        else:
            rule_type = _rule_doc_type(text)
            doc_type, source = (rule_type, "rule") if rule_type else (_OTHER, "unknown")

        items.append(_build_item(file, idx, doc_type))
        classified.append({
            "fileName": file_name,
            "docType": doc_type,
            "source": source,
            "slotIndex": items[-1]["slotIndex"],
        })

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
