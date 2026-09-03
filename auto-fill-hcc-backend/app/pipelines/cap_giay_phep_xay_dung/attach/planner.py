"""Đính kèm bước thành phần hồ sơ cho thủ tục cấp giấy phép xây dựng mới.

Hồ sơ mẫu hiện tại là nhà ở riêng lẻ của cá nhân. Tập trung 3 nhóm chính:
  STT1  - Đơn đề nghị cấp giấy phép xây dựng, CCCD chủ hộ/người nộp, bản cam kết.
          Các file nhóm này cùng bơm vào hàng upload có sẵn của STT1.
  STT11 - Giấy tờ hợp pháp về đất đai: sổ đỏ/GCN quyền sử dụng đất.
  STT27 - Hồ sơ thiết kế xây dựng: bản vẽ, kê khai kinh nghiệm thiết kế,
          chứng chỉ năng lực tổ chức, chứng chỉ hành nghề cá nhân thiết kế.

Các dòng dự án/tôn giáo/sửa chữa/thẩm định khác tạm bỏ qua nếu không có giấy tờ
đặc thù nhận diện rõ.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold, normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.cap_giay_phep_xay_dung.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DOC_APPLICATION = "building_permit_application"
_DOC_IDENTITY = "identity_document"
_DOC_SAFETY_COMMITMENT = "safety_commitment"
_DOC_LAND = "land_legal_document"
_DOC_DRAWINGS = "construction_design_drawings"
_DOC_EXPERIENCE = "design_experience_declaration"
_DOC_CAPACITY = "construction_capacity_certificate"
_DOC_ARCHITECT_CERT = "architect_practice_certificate"
_DOC_PROJECT_APPROVAL = "project_approval"
_DOC_REPAIR_APPLICATION = "repair_application"
_DOC_OLD_PERMIT = "old_construction_permit"
_DOC_OTHER = "other"
_DOC_SKIP = "skip"

_ALLOWED_DOC_TYPES = {
    _DOC_APPLICATION,
    _DOC_IDENTITY,
    _DOC_SAFETY_COMMITMENT,
    _DOC_LAND,
    _DOC_DRAWINGS,
    _DOC_EXPERIENCE,
    _DOC_CAPACITY,
    _DOC_ARCHITECT_CERT,
    _DOC_PROJECT_APPROVAL,
    _DOC_REPAIR_APPLICATION,
    _DOC_OLD_PERMIT,
    _DOC_OTHER,
    _DOC_SKIP,
}

_ROW_1_TYPES = {_DOC_APPLICATION, _DOC_IDENTITY, _DOC_SAFETY_COMMITMENT}
_ROW_11_TYPES = {_DOC_LAND}
_ROW_27_TYPES = {_DOC_DRAWINGS, _DOC_EXPERIENCE, _DOC_CAPACITY, _DOC_ARCHITECT_CERT}

_ROW_1_COMPONENT = "- Đơn đề nghị cấp giấy phép xây dựng theo Mẫu số 1 Phụ lục số II Nghị định số 175/2024/NĐ-CP"
_ROW_11_COMPONENT = "- Một trong những giấy tờ hợp pháp về đất đai chứng minh sự phù hợp mục đích sử dụng đất và sở hữu công trình"
_ROW_27_COMPONENT = "- Hồ sơ thiết kế xây dựng: Đối với nhà ở riêng lẻ của hộ gia đình, cá nhân: 02 bộ bản vẽ thiết kế xây dựng kèm theo"

_ROW_1_LABEL = "Đơn đề nghị cấp GPXD và giấy tờ kèm theo"
_ROW_11_LABEL = "Giấy tờ hợp pháp về đất đai"
_ROW_27_LABEL = "Hồ sơ thiết kế xây dựng"

_SLOT_APPLICATION = "gpxd_application"
_SLOT_LAND = "gpxd_land_document"
_SLOT_DESIGN = "gpxd_design_dossier"

SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": _SLOT_APPLICATION,
        "slotIndex": 0,
        "componentIndex": 1,
        "slotName": _ROW_1_COMPONENT,
        "documentName": _ROW_1_LABEL,
        "detectedType": _ROW_1_LABEL,
    },
    {
        "slotKey": _SLOT_LAND,
        "slotIndex": 10,
        "componentIndex": 11,
        "slotName": _ROW_11_COMPONENT,
        "documentName": _ROW_11_LABEL,
        "detectedType": _ROW_11_LABEL,
    },
    {
        "slotKey": _SLOT_DESIGN,
        "slotIndex": 26,
        "componentIndex": 27,
        "slotName": _ROW_27_COMPONENT,
        "documentName": _ROW_27_LABEL,
        "detectedType": _ROW_27_LABEL,
    },
]
_SLOT_BY_KEY = {item["slotKey"]: item for item in SLOTS}

_LABELS = {
    _DOC_APPLICATION: "Đơn đề nghị cấp giấy phép xây dựng",
    _DOC_IDENTITY: "Căn cước công dân",
    _DOC_SAFETY_COMMITMENT: "Bản cam kết xây nhà",
    _DOC_LAND: "Giấy chứng nhận quyền sử dụng đất",
    _DOC_DRAWINGS: "Bản vẽ xin cấp phép xây dựng",
    _DOC_EXPERIENCE: "Bản kê khai kinh nghiệm thiết kế",
    _DOC_CAPACITY: "Chứng chỉ năng lực hoạt động xây dựng",
    _DOC_ARCHITECT_CERT: "Chứng chỉ hành nghề kiến trúc",
    _DOC_PROJECT_APPROVAL: "Văn bản phê duyệt thẩm định dự án",
    _DOC_REPAIR_APPLICATION: "Đơn đề nghị cấp giấy phép sửa chữa cải tạo",
    _DOC_OLD_PERMIT: "Giấy phép xây dựng cũ",
    _DOC_OTHER: "Tài liệu cấp giấy phép xây dựng",
    _DOC_SKIP: "Bỏ qua",
}

_GROUP_PRIORITY = {
    _DOC_APPLICATION: 10,
    _DOC_IDENTITY: 20,
    _DOC_SAFETY_COMMITMENT: 30,
    _DOC_LAND: 10,
    _DOC_DRAWINGS: 10,
    _DOC_EXPERIENCE: 20,
    _DOC_CAPACITY: 30,
    _DOC_ARCHITECT_CERT: 40,
}


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _has_any(haystack: str, needles: tuple[str, ...]) -> bool:
    return any(needle in haystack for needle in needles)


def _normalize_doc_type(value: str) -> str:
    raw = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    if raw in _ALLOWED_DOC_TYPES:
        return raw
    text = fold(raw)
    if not text or text == "other":
        return _DOC_OTHER
    if _has_any(text, ("building_permit", "cap_giay_phep_xay_dung", "don_de_nghi", "don de nghi")):
        return _DOC_APPLICATION
    if _has_any(text, ("identity", "cccd", "can cuoc", "cmnd", "ho chieu")):
        return _DOC_IDENTITY
    if _has_any(text, ("safety", "commitment", "cam ket", "lien ke")):
        return _DOC_SAFETY_COMMITMENT
    if _has_any(text, ("land", "so do", "qsd", "quyen su dung dat", "dat dai")):
        return _DOC_LAND
    if _has_any(text, ("drawing", "design_drawing", "ban ve", "ho so thiet ke")):
        return _DOC_DRAWINGS
    if _has_any(text, ("experience", "kinh nghiem thiet ke", "ke khai")):
        return _DOC_EXPERIENCE
    if _has_any(text, ("capacity", "chung chi nang luc")):
        return _DOC_CAPACITY
    if _has_any(text, ("practice", "architect", "hanh nghe", "kien truc")):
        return _DOC_ARCHITECT_CERT
    if _has_any(text, ("project", "approval", "phe duyet", "tham dinh")):
        return _DOC_PROJECT_APPROVAL
    if _has_any(text, ("repair", "sua chua", "cai tao")):
        return _DOC_REPAIR_APPLICATION
    if _has_any(text, ("old permit", "giay phep xay dung cu")):
        return _DOC_OLD_PERMIT
    if _has_any(text, ("skip", "irrelevant", "khong ap dung")):
        return _DOC_SKIP
    return _DOC_OTHER


def _label_for_type(doc_type: str, title: str = "") -> str:
    title = normalize_document_name(title, "") if title else ""
    if title and doc_type not in {_DOC_IDENTITY, _DOC_LAND}:
        return title
    return _LABELS.get(doc_type, _LABELS[_DOC_OTHER])


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    if not documents:
        return {}

    docs = [{"index": item["index"], "text": _truncate_text(item.get("text", ""))} for item in documents]
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(docs)},
    ]
    raw = await client.chat(messages, max_tokens=900, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    parsed_docs = parsed.get("documents", []) or []

    def _coerce(item: dict) -> dict[str, str]:
        return {
            "type": _normalize_doc_type(str(item.get("type") or item.get("docType") or "")),
            "title": str(item.get("title") or item.get("documentName") or "").strip(),
        }

    out: dict[int, dict[str, str]] = {}
    if len(parsed_docs) == len(documents):
        for pos, item in enumerate(parsed_docs):
            out[documents[pos]["index"]] = _coerce(item)
        return out

    raw_items: list[tuple[int, dict]] = []
    for item in parsed_docs:
        try:
            raw_items.append((int(item.get("index")), item))
        except Exception:  # noqa: BLE001
            continue
    offset = 0 if any(idx == 0 for idx, _ in raw_items) else 1
    valid = {doc["index"] for doc in documents}
    for raw_idx, item in raw_items:
        idx = raw_idx - offset
        if idx in valid:
            out[idx] = _coerce(item)
    return out


def _ordered_entries(entries: list[dict]) -> list[dict]:
    return sorted(entries, key=lambda item: (_GROUP_PRIORITY.get(item["docType"], 99), item["idx"]))


def _slot_key_for_type(doc_type: str) -> str:
    if doc_type in _ROW_1_TYPES:
        return _SLOT_APPLICATION
    if doc_type in _ROW_11_TYPES:
        return _SLOT_LAND
    if doc_type in _ROW_27_TYPES:
        return _SLOT_DESIGN
    return ""


def _build_fixed_item(files: list[dict], entry: dict) -> dict:
    slot = _SLOT_BY_KEY[_slot_key_for_type(entry["docType"])]
    idx = entry["idx"]
    document_name = _label_for_type(entry["docType"], entry.get("title", ""))
    return {
        "fileIndex": idx,
        "fileName": str(files[idx].get("name") or f"file-{idx + 1}"),
        "documentName": document_name,
        "componentName": slot["slotName"],
        "target": "fixed-slot",
        "componentIndex": slot["componentIndex"],
        "needsAddComponent": False,
        "detectedType": document_name,
        "slotKey": slot["slotKey"],
        "slotIndex": slot["slotIndex"],
        "slotName": slot["slotName"],
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, dict[str, str]] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    resolved: list[dict] = []
    warnings: list[str] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        # Phân loại HOÀN TOÀN bằng LLM (prompt.py). KHÔNG dùng keyword đoán loại từ OCR: keyword dễ
        # trùng lẫn (vd "Sơ đồ thửa đất" là MỘT MỤC trong SỔ ĐỎ nhưng trùng cụm bản vẽ) và đè SAI kết
        # quả LLM. LLM đọc toàn văn + ngữ cảnh nên phân loại đúng hơn; quy tắc nghiệp vụ đặt ở prompt.
        detected = llm_types.get(idx) or {}
        llm_type = detected.get("type") or ""
        doc_type = llm_type if llm_type in _ALLOWED_DOC_TYPES else _DOC_OTHER
        resolved.append({
            "idx": idx,
            "fileName": file_name,
            "docType": doc_type,
            "title": detected.get("title", ""),
            "source": "llm" if llm_type else "default",
        })

    row1_entries = [entry for entry in resolved if entry["docType"] in _ROW_1_TYPES]
    row11_entries = [entry for entry in resolved if entry["docType"] in _ROW_11_TYPES]
    row27_entries = [entry for entry in resolved if entry["docType"] in _ROW_27_TYPES]
    skipped_entries = [
        entry
        for entry in resolved
        if entry["docType"] not in _ROW_1_TYPES | _ROW_11_TYPES | _ROW_27_TYPES
    ]

    attachments: list[dict] = []
    classified: list[dict] = []

    for entries, slot_key in (
        (row1_entries, _SLOT_APPLICATION),
        (row11_entries, _SLOT_LAND),
        (row27_entries, _SLOT_DESIGN),
    ):
        slot = _SLOT_BY_KEY[slot_key]
        for entry in _ordered_entries(entries):
            item = _build_fixed_item(files, entry)
            attachments.append(item)
            classified.append({
                "fileName": entry["fileName"],
                "docType": entry["docType"],
                "documentName": item["documentName"],
                "target": "fixed-slot",
                "componentIndex": slot["componentIndex"],
                "slotKey": slot["slotKey"],
                "slotIndex": slot["slotIndex"],
                "source": entry["source"],
            })

    for entry in skipped_entries:
        if entry["docType"] in {_DOC_OTHER, _DOC_SKIP}:
            warnings.append(f"Không xác định được dòng thành phần hồ sơ GPXD cho file '{entry['fileName']}' — đã bỏ qua.")
        else:
            warnings.append(f"File '{entry['fileName']}' thuộc nhóm '{entry['docType']}' chưa áp dụng cho hồ sơ nhà ở riêng lẻ — đã bỏ qua.")
        classified.append({
            "fileName": entry["fileName"],
            "docType": entry["docType"],
            "documentName": _label_for_type(entry["docType"], entry.get("title", "")),
            "target": "skip",
            "componentIndex": None,
            "source": entry["source"],
        })

    return attachments, warnings, classified


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [file for file in raw_files if file.get("type") in _OCR_TYPES]

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    ocr_by_name = {item.get("name"): item for item in ocr_results}
    llm_docs = [
        {
            "index": idx,
            "text": str(ocr_by_name.get(file.get("name"), {}).get("text") or ""),
        }
        for idx, file in enumerate(raw_files)
    ]

    t1 = time.monotonic()
    llm_types: dict[int, dict[str, str]] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types)
    errors.extend(warnings)
    skipped_ocr = [file["name"] for file in raw_files if file.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [file["name"] for file in raw_files],
            "ocrDocuments": [item.get("name") for item in ocr_results if item.get("text")],
            "llmDocuments": [file["name"] for file in raw_files],
            "sessionId": (session or {}).get("request_id"),
            "classified": classified,
            "skippedOcr": skipped_ocr,
            "slots": SLOTS,
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "ocr_text": join_ocr_documents(ocr_results),
        "llm_output": {str(idx): val for idx, val in llm_types.items()},
        "errors": errors,
    }
