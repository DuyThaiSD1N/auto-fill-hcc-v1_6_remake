"""Đính kèm cho thủ tục Chứng thực giao dịch liên quan đến tài sản (động sản, QSDĐ, nhà ở).

OCR + LLM phân loại tài liệu (giấy tờ sở hữu / dự thảo giao dịch / CCCD / ủy quyền) rồi route
2 hàng cố định + thêm thành phần mới. Helper đặt tên/fold dùng chung lấy từ _shared.
"""
import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_ALLOWED_LLM_TYPES = {
    "asset_ownership_proof",
    "transaction_draft",
    "identity_document",
    "authorization",
    "other",
}

_ASSET_LABEL = "Giấy tờ chứng minh quyền sở hữu quyền sử dụng tài sản"
_TRANSACTION_LABEL = "Dự thảo giao dịch"
_IDENTITY_LABEL = "Căn cước công dân"
_AUTHORIZATION_LABEL = "Văn bản ủy quyền"
_OTHER_LABEL = "Tài liệu giao dịch tài sản"

_ROW_1_COMPONENT = (
    "Bản chính hoặc bản sao có chứng thực hoặc bản sao điện tử được chứng thực "
    "từ bản chính của giấy chứng nhận quyền sở hữu, quyền sử dụng"
)
_ROW_2_COMPONENT = "Dự thảo giao dịch"

# Giao dịch/hợp đồng ủy quyền mang đi chứng thực CHÍNH LÀ giao dịch của hồ sơ (hàng 2),
# không phải văn bản ủy quyền nộp hồ sơ. LLM hay trả authorization/other cho nhóm này.
_UY_QUYEN_TRANSACTION_TITLES = ("giao dich uy quyen", "hop dong uy quyen")
_UY_QUYEN_PARTY_MARKERS = ("ben uy quyen", "ben duoc uy quyen")
_RETYPABLE_TO_TRANSACTION = ("authorization", "other")


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _canonical_type(value: str) -> str:
    doc_type = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    return doc_type if doc_type in _ALLOWED_LLM_TYPES else "other"


def _normalize_title_for_type(doc_type: str, title: str) -> str:
    text = _fold(title)
    if doc_type == "asset_ownership_proof":
        if "dang ky xe" in text:
            return "Đăng ký xe"
        if "quyen su dung dat" in text or "qsd" in text:
            return "Giấy chứng nhận quyền sử dụng đất"
        if "quyen so huu nha" in text or "nha o" in text:
            return "Giấy chứng nhận quyền sở hữu nhà ở"
    if doc_type == "identity_document" and ("can cuoc" in text or "cccd" in text):
        return "Căn cước công dân"
    return title


def _label_for_type(doc_type: str, title: str = "") -> str:
    title = _normalize_title_for_type(doc_type, str(title or "").strip())
    if doc_type == "asset_ownership_proof":
        return title or _ASSET_LABEL
    if doc_type == "transaction_draft":
        return title or _TRANSACTION_LABEL
    if doc_type == "identity_document":
        return title or _IDENTITY_LABEL
    if doc_type == "authorization":
        return title or _AUTHORIZATION_LABEL
    return title or _OTHER_LABEL


def _unique_document_name(base: str, used: set[str], fallback: str) -> str:
    normalized = normalize_document_name(base, fallback)
    key = _fold(normalized)
    if key and key not in used:
        used.add(key)
        return normalized

    stem = normalized[:45].strip() or fallback[:45].strip() or _OTHER_LABEL
    n = 2
    while True:
        candidate = f"{stem} {n}"[:50].strip()
        key = _fold(candidate)
        if key not in used:
            used.add(key)
            return candidate
        n += 1


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    if not documents:
        return {}

    docs = [
        {
            "index": item["index"],
            "text": _truncate_text(item.get("text", "")),
        }
        for item in documents
    ]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(docs)},
    ]
    raw = await client.chat(messages, max_tokens=800, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    parsed_docs = parsed.get("documents", []) or []

    def _coerce(item: dict) -> dict[str, str]:
        return {
            "type": _canonical_type(str(item.get("type") or "")),
            "title": str(item.get("title") or "").strip(),
        }

    out: dict[int, dict[str, str]] = {}

    # Bền vững nhất: LLM trả đúng số lượng → map THEO THỨ TỰ, bỏ qua field "index"
    # (LLM hay đánh lệch 0-based/1-based khiến gán nhầm phân loại sang file khác).
    if len(parsed_docs) == len(documents):
        for pos, item in enumerate(parsed_docs):
            out[documents[pos]["index"]] = _coerce(item)
        return out

    # Số lượng lệch (LLM gộp/bỏ sót) → map theo index, tự dò 0-based hay 1-based.
    raw_items: list[tuple[int, dict]] = []
    for item in parsed_docs:
        try:
            raw_items.append((int(item.get("index")), item))
        except Exception:  # noqa: BLE001
            continue
    offset = 0 if any(r == 0 for r, _ in raw_items) else 1  # không có index 0 → coi là 1-based
    valid = {d["index"] for d in documents}
    for r, item in raw_items:
        idx = r - offset
        if idx in valid:
            out[idx] = _coerce(item)
    return out


def _is_uy_quyen_transaction(text: str) -> bool:
    """OCR cho thấy tài liệu là giao dịch ủy quyền (có hai bên ký kết), không phải giấy ủy quyền nộp hồ sơ."""
    folded = _fold(text)
    if not folded:
        return False
    if all(marker in folded for marker in _UY_QUYEN_PARTY_MARKERS):
        return True
    return any(title in folded for title in _UY_QUYEN_TRANSACTION_TITLES)


def _uy_quyen_transaction_title(text: str) -> str:
    return "Hợp đồng ủy quyền" if "hop dong uy quyen" in _fold(text) else "Giao dịch ủy quyền"


def _retype_uy_quyen_transaction(
    detected_types: dict[int, dict[str, str]],
    texts: dict[int, str],
) -> None:
    """Đưa giao dịch ủy quyền về transaction_draft khi chưa có tài liệu nào là dự thảo giao dịch."""
    if any(d.get("type") == "transaction_draft" for d in detected_types.values()):
        return
    for idx, detected in detected_types.items():
        if detected.get("type") not in _RETYPABLE_TO_TRANSACTION:
            continue
        text = texts.get(idx, "")
        if not _is_uy_quyen_transaction(text):
            continue
        detected["type"] = "transaction_draft"
        detected["title"] = _uy_quyen_transaction_title(text)
        return


def _route_for_type(doc_type: str, asset_seen: int, transaction_seen: int) -> tuple[str, int | None, str]:
    if doc_type == "asset_ownership_proof" and asset_seen == 0:
        return "existing", 1, _ROW_1_COMPONENT
    if doc_type == "transaction_draft" and transaction_seen == 0:
        return "existing", 2, _ROW_2_COMPONENT
    return "new", None, ""


def _build_item(
    file: dict,
    idx: int,
    doc_type: str,
    title: str,
    asset_seen: int,
    transaction_seen: int,
    used_names: set[str],
) -> dict:
    target, component_index, existing_component = _route_for_type(doc_type, asset_seen, transaction_seen)
    fallback = _label_for_type(doc_type)
    document_name = _unique_document_name(_label_for_type(doc_type, title), used_names, fallback)
    component_name = existing_component if target == "existing" else document_name
    return {
        "fileIndex": idx,
        "fileName": str(file.get("name") or f"file-{idx + 1}"),
        "documentName": document_name,
        "componentName": component_name,
        "target": target,
        "componentIndex": component_index,
        "needsAddComponent": target == "new",
        "detectedType": document_name,
    }


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    """Entry point đính kèm (gọi qua registry.get_attach_pipeline)."""
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    from app.services import ocr


    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for r in ocr_results:
        if r.get("error"):
            errors.append(f"OCR {r.get('name')}: {r['error']}")

    ocr_by_name = {r.get("name"): r for r in ocr_results}
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
        except Exception as e:  # noqa: BLE001
            errors.append(f"attachment_agent: {e}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    detected_types: dict[int, dict[str, str]] = {
        idx: dict(llm_types.get(idx) or {"type": "other", "title": ""}) for idx in range(len(raw_files))
    }
    _retype_uy_quyen_transaction(detected_types, {d["index"]: d["text"] for d in llm_docs})

    asset_seen = 0
    transaction_seen = 0
    used_names: set[str] = set()
    attachments: list[dict] = []
    classified: list[dict] = []
    for idx, file in enumerate(raw_files):
        detected = detected_types[idx]
        doc_type = detected["type"]
        item = _build_item(
            file,
            idx,
            doc_type,
            detected.get("title", ""),
            asset_seen,
            transaction_seen,
            used_names,
        )
        attachments.append(item)
        if doc_type == "asset_ownership_proof":
            asset_seen += 1
        if doc_type == "transaction_draft":
            transaction_seen += 1
        classified.append({
            "fileName": file.get("name"),
            "type": doc_type,
            "title": detected.get("title", ""),
            "target": item["target"],
            "componentIndex": item["componentIndex"],
        })

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [f["name"] for f in raw_files],
            "sessionId": (session or {}).get("request_id"),
            "classified": classified,
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        # Cho trace (AttachmentPlanResp tự lược 2 field này khỏi HTTP response).
        "ocr_text": join_ocr_documents(ocr_results),
        "llm_output": {str(idx): val for idx, val in llm_types.items()},
        "errors": errors,
    }


# Bí danh tương thích tên cũ (router/shim/test gọi plan_chung_thuc_giao_dich_tai_san_attachments).
plan_chung_thuc_giao_dich_tai_san_attachments = plan
