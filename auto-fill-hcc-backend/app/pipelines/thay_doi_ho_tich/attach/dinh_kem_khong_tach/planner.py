"""Phân loại theo nguyên file cho thủ tục thay đổi, cải chính hộ tịch.

Nhánh này cố ý không sinh ``sourceSegments``: một PDF hỗn hợp vẫn là một tài liệu đính kèm.
Ngoại lệ duy nhất là các file rời chứa hai mặt CCCD cùng người được gộp bằng ``sourceFileIndexes``.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines._shared.identity_merge import merge_identity_attachments
from app.pipelines.thay_doi_ho_tich.attach.dinh_kem_khong_tach.prompt import (
    SYSTEM_PROMPT,
    build_user_prompt,
)
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_ALLOWED_DOC_TYPES = {
    "identity", "paper_declaration", "supporting_evidence", "authorization", "other",
}

_IDENTITY_LABEL = "Giấy tờ tùy thân"
_DECLARATION_LABEL = "Tờ khai cải chính hộ tịch bản giấy"
_EVIDENCE_LABEL = "Giấy tờ làm căn cứ cải chính hộ tịch"
_AUTHORIZATION_LABEL = "Văn bản ủy quyền"
_OTHER_LABEL = "Tài liệu đính kèm"

_FALLBACK_SLOTS = {
    "supporting_evidence": (
        2,
        "Giấy tờ liên quan đến việc thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc",
    ),
    "authorization": (3, "Văn bản ủy quyền"),
}


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _canonical_type(value: Any) -> str:
    raw = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    aliases = {
        "id": "identity",
        "cccd": "identity",
        "cmnd": "identity",
        "passport": "identity",
        "declaration": "paper_declaration",
        "paper_form": "paper_declaration",
        "ho_tich_doc": "supporting_evidence",
        "civil_status": "supporting_evidence",
        "birth": "supporting_evidence",
        "marriage": "supporting_evidence",
        "death": "supporting_evidence",
        "uy_quyen": "authorization",
        "power_of_attorney": "authorization",
    }
    raw = aliases.get(raw, raw)
    return raw if raw in _ALLOWED_DOC_TYPES else "other"


def _clean_subject_name(value: Any) -> str:
    subject = re.sub(r"\s+", " ", str(value or "")).strip(" :-")
    if _fold(subject) in {"", "ho ten", "ho va ten", "full name", "khong ro"}:
        return ""
    return subject[:40].strip()


def _identity_document_name(
    document_name: Any,
    subject_name: Any = "",
    identity_type: Any = "",
) -> str:
    """Chuẩn hóa tên từ kết quả LLM, không tự phân loại lại bằng OCR."""
    proposed = str(document_name or "").strip()
    folded_type = _fold(str(identity_type or proposed))
    if "chung minh nhan dan" in folded_type or "cmnd" in folded_type:
        label, fallback = "CMND", "Chứng minh nhân dân"
    elif "ho chieu" in folded_type or "passport" in folded_type:
        label = fallback = "Hộ chiếu"
    elif "can cuoc" in folded_type or "cccd" in folded_type or "identity card" in folded_type:
        label, fallback = "CCCD", "Căn cước công dân"
    else:
        label = fallback = _IDENTITY_LABEL
    subject = _clean_subject_name(subject_name)
    if subject:
        return normalize_document_name(f"{label} {subject}", fallback)
    return normalize_document_name(proposed, fallback)


def _unique_document_name(base: str, used: set[str], fallback: str) -> str:
    normalized = normalize_document_name(base, fallback)
    key = _fold(normalized)
    if key and key not in used:
        used.add(key)
        return normalized
    stem = normalized[:45].strip() or fallback[:45].strip()
    suffix = 2
    while True:
        candidate = f"{stem} {suffix}"[:50].strip()
        key = _fold(candidate)
        if key not in used:
            used.add(key)
            return candidate
        suffix += 1


def _slot_score(doc_type: str, component_name: str) -> int:
    folded = _fold(component_name)
    if doc_type == "supporting_evidence":
        markers = ("giay to lien quan", "thay doi", "cai chinh")
        return 12 if all(marker in folded for marker in markers) else 0
    if doc_type == "authorization":
        return 12 if "van ban uy quyen" in folded else (8 if "giay uy quyen" in folded else 0)
    return 0


def _slot(
    options: dict | None,
    doc_type: str,
    claimed_component_indexes: set[int],
) -> tuple[int, str] | None:
    fallback = _FALLBACK_SLOTS.get(doc_type)
    if not fallback:
        return None
    components = (((options or {}).get("attachmentContext") or {}).get("components") or [])
    candidates: list[tuple[int, int]] = []
    for component in components:
        if not isinstance(component, dict):
            continue
        name = str(component.get("componentName") or "").strip()
        score = _slot_score(doc_type, name)
        index = _coerce_int(component.get("index"))
        if score and index and index > 0:
            candidates.append((score, index))
    if candidates:
        for _, index in sorted(candidates, key=lambda item: (-item[0], item[1])):
            if index in claimed_component_indexes:
                continue
            claimed_component_indexes.add(index)
            # Không phản chiếu nguyên chuỗi DOM có thể chứa phần "Tên Hồ Sơ" lặp lại.
            return index, fallback[1]
        return None
    if components:
        return None
    index, name = fallback
    if index in claimed_component_indexes:
        return None
    claimed_component_indexes.add(index)
    return index, name


async def _classify_with_llm(documents: list[dict[str, Any]]) -> list[dict]:
    if not documents:
        return []
    raw = await client.chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(documents)},
        ],
        max_tokens=max(900, min(2800, len(documents) * 180)),
        enable_thinking=settings.agent_reasoning,
    )
    parsed = client.extract_json_block(raw)
    return parsed.get("documents", []) if isinstance(parsed, dict) else []


def _validated_classifications(raw_items: list[dict], file_count: int) -> dict[int, dict]:
    """Mỗi file chỉ nhận kết quả LLM đầu tiên; thiếu kết quả vẫn giữ file dưới loại ``other``."""
    result: dict[int, dict] = {}
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        file_index = _coerce_int(raw.get("fileIndex", raw.get("index")))
        if file_index is None or not 0 <= file_index < file_count or file_index in result:
            continue
        result[file_index] = {
            "type": _canonical_type(raw.get("type")),
            "documentName": str(raw.get("documentName") or raw.get("title") or "").strip(),
            "subjectName": _clean_subject_name(raw.get("subjectName")),
            "identityType": str(raw.get("identityType") or "").strip(),
            "titleText": str(raw.get("titleText") or "").strip(),
        }
    return result


async def plan_thay_doi_ho_tich_attachments_without_split(
    files: list[FileItem], options: dict | None = None, session: dict | None = None,
) -> dict:
    errors: list[str] = []
    raw_files = [{"name": file.name, "type": file.type, "dataUrl": file.dataUrl} for file in files]
    ocr_pairs = [(index, file) for index, file in enumerate(raw_files) if file.get("type") in _OCR_TYPES]

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file([file for _, file in ocr_pairs]) if ocr_pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    ocr_by_index = {raw_index: result for (raw_index, _), result in zip(ocr_pairs, ocr_results)}
    for file_index, result in ocr_by_index.items():
        if result.get("error"):
            errors.append(f"OCR fileIndex={file_index} {raw_files[file_index].get('name')}: {result['error']}")

    documents = [
        {
            "fileIndex": file_index,
            "ocrText": str((ocr_by_index.get(file_index) or {}).get("text") or ""),
        }
        for file_index in range(len(raw_files))
    ]
    started = time.monotonic()
    raw_classifications: list[dict] = []
    if documents:
        try:
            raw_classifications = await _classify_with_llm(documents)
        except Exception as exc:  # noqa: BLE001 - fallback giữ nguyên mọi file
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)
    classified_by_index = _validated_classifications(raw_classifications, len(raw_files))

    attachments: list[dict] = []
    classified: list[dict] = []
    identity_indexes: set[int] = set()
    used_names: set[str] = set()
    claimed_component_indexes: set[int] = set()

    for file_index, file in enumerate(raw_files):
        llm_item = classified_by_index.get(file_index) or {}
        doc_type = llm_item.get("type") or "other"

        if doc_type == "identity":
            document_name = _unique_document_name(
                _identity_document_name(
                    llm_item.get("documentName"),
                    llm_item.get("subjectName"),
                    llm_item.get("identityType"),
                ),
                used_names,
                _IDENTITY_LABEL,
            )
            identity_indexes.add(file_index)
            target, component_index, component_name, needs_add = "new", None, document_name, True
        elif doc_type == "paper_declaration":
            document_name = _unique_document_name(_DECLARATION_LABEL, used_names, _DECLARATION_LABEL)
            target, component_index, component_name, needs_add = "new", None, document_name, True
        elif doc_type in {"supporting_evidence", "authorization"}:
            fallback = _EVIDENCE_LABEL if doc_type == "supporting_evidence" else _AUTHORIZATION_LABEL
            proposed = llm_item.get("documentName")
            document_name = _unique_document_name(proposed, used_names, fallback)
            slot = _slot(options, doc_type, claimed_component_indexes)
            if slot:
                target, component_index = "existing", slot[0]
                component_name, needs_add = slot[1], False
            else:
                target, component_index = "new", None
                component_name, needs_add = document_name, True
        else:
            proposed = llm_item.get("documentName")
            document_name = _unique_document_name(proposed, used_names, _OTHER_LABEL)
            target, component_index, component_name, needs_add = "new", None, document_name, True

        attachments.append({
            "fileIndex": file_index,
            "fileName": str(file.get("name") or f"file-{file_index + 1}"),
            "documentName": document_name,
            "componentName": component_name,
            "target": target,
            "componentIndex": component_index,
            "needsAddComponent": needs_add,
            "detectedType": document_name,
        })
        classified.append({
            "fileIndex": file_index,
            "fileName": file.get("name"),
            "titleText": llm_item.get("titleText") or "",
            "type": doc_type,
            "identityType": llm_item.get("identityType") or "",
            "documentName": document_name,
            "target": target,
            "componentIndex": component_index,
        })

    ocr_text_by_index = {item["fileIndex"]: item["ocrText"] for item in documents}
    attachments = merge_identity_attachments(attachments, ocr_text_by_index, identity_indexes)
    # Sau khi gộp hai mặt cùng người, chỉ phản chiếu tên mà LLM đã trả cho nhóm đó.
    final_identity_name_by_file: dict[int, str] = {}
    for item in attachments:
        source_indexes = item.get("sourceFileIndexes") or [item.get("fileIndex")]
        if not any(index in identity_indexes for index in source_indexes):
            continue
        document_name = str(item.get("documentName") or _IDENTITY_LABEL)
        for index in source_indexes:
            if isinstance(index, int):
                final_identity_name_by_file[index] = document_name
    for item in classified:
        if item["fileIndex"] in final_identity_name_by_file:
            item["documentName"] = final_identity_name_by_file[item["fileIndex"]]

    indexed_ocr_results = []
    for file_index, file in enumerate(raw_files):
        result = ocr_by_index.get(file_index)
        if result:
            indexed_ocr_results.append({
                **result,
                "name": f"fileIndex={file_index} · {file.get('name') or f'file-{file_index + 1}'}",
            })

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [file["name"] for file in raw_files],
            "ocrDocuments": [
                raw_files[index].get("name") for index, result in ocr_by_index.items() if result.get("text")
            ],
            "llmDocuments": [file.get("name") for file in raw_files],
            "sessionId": (session or {}).get("request_id"),
            "attachmentMode": "preserve_files",
            "classified": classified,
        },
        "ocr_text": join_ocr_documents(indexed_ocr_results),
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "errors": errors,
    }


plan = plan_thay_doi_ho_tich_attachments_without_split

__all__ = ["plan", "plan_thay_doi_ho_tich_attachments_without_split"]
