"""Phân loại theo nguyên file cho thủ tục đăng ký kết hôn.

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
from app.pipelines.ket_hon.attach.dinh_kem_khong_tach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_ALLOWED_DOC_TYPES = {"identity", "marriage_declaration", "commitment", "other"}

_IDENTITY_LABEL = "Giấy tờ tùy thân"
_DECLARATION_LABEL = "Tờ khai đăng ký kết hôn"
_COMMITMENT_LABEL = "Bản cam đoan"
# Chỉ dùng khi cả LLM lẫn OCR đều không cho tên cụ thể. Không được lấy tên thủ tục làm fallback
# vì file tải nhầm hoặc hồ sơ tham chiếu vẫn phải mang tên phản ánh chính nội dung của nó.
_OTHER_LABEL = "Tài liệu đính kèm"

_ID_SLOT_INDEX = 2
_ID_SLOT_COMPONENT = (
    "Hộ chiếu/Chứng minh nhân dân/Thẻ căn cước công dân/Thẻ căn cước/Căn cước điện tử"
)
_IDENTITY_NUMBER_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")


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
        "paper_declaration": "marriage_declaration",
        "declaration": "marriage_declaration",
        "cam_doan": "commitment",
    }
    raw = aliases.get(raw, raw)
    return raw if raw in _ALLOWED_DOC_TYPES else "other"


def _rule_doc_type(text: str) -> str:
    """Fallback khi LLM lỗi; chỉ nhận loại có tiêu đề/dấu hiệu đủ chắc chắn."""
    folded = _fold(text)
    if "to khai dang ky ket hon" in folded:
        return "marriage_declaration"
    if "ban cam doan" in folded or "giay cam doan" in folded:
        return "commitment"
    identity_front_markers = (
        "can cuoc cong dan", "citizen identity card", "identity card", "chung minh nhan dan",
        "passport", "ho chieu",
    )
    has_front = any(marker in folded for marker in identity_front_markers)
    has_back = "idvnm" in folded or (
        "dac diem nhan dang" in folded and bool(_IDENTITY_NUMBER_RE.search(text or ""))
    )
    return "identity" if has_front or has_back else "other"


def _fallback_document_name(text: str) -> str:
    folded = _fold(text)
    known_titles = (
        ("giay xac nhan tinh trang hon nhan", "Giấy xác nhận tình trạng hôn nhân"),
        ("quyet dinh ly hon", "Quyết định ly hôn"),
        ("ban an ly hon", "Bản án ly hôn"),
        ("trich luc khai tu", "Trích lục khai tử"),
        ("giay bao tu", "Giấy báo tử"),
        ("giay uy quyen", "Giấy ủy quyền"),
        ("van ban uy quyen", "Văn bản ủy quyền"),
    )
    for marker, title in known_titles:
        if marker in folded:
            return title
    return ""


def _clean_subject_name(value: Any) -> str:
    subject = re.sub(r"\s+", " ", str(value or "")).strip(" :-")
    if _fold(subject) in {"", "ho ten", "ho va ten", "full name", "khong ro"}:
        return ""
    return subject[:40].strip()


def _identity_document_name(text: str, subject_name: str = "") -> str:
    folded = _fold(text)
    has_passport = "passport" in folded or "ho chieu" in folded
    has_cccd = "can cuoc" in folded or "citizen identity" in folded or "idvnm" in folded
    has_cmnd = "chung minh nhan dan" in folded or "cmnd" in folded
    if has_cccd and not has_passport and not has_cmnd:
        # Một file nguyên bản có nhiều số định danh là danh sách CCCD của nhiều người: chế độ
        # không tách phải giữ chung đúng tên tổng quát, dù LLM có trả tên của một người trong file.
        identity_numbers = set(_IDENTITY_NUMBER_RE.findall(str(text or "")))
        subject = _clean_subject_name(subject_name)
        if subject and len(identity_numbers) <= 1:
            return normalize_document_name(f"CCCD {subject}", "Căn cước công dân")
        return "Căn cước công dân"
    if has_passport and not has_cccd and not has_cmnd:
        return "Hộ chiếu"
    if has_cmnd and not has_cccd and not has_passport:
        return "Chứng minh nhân dân"
    return _IDENTITY_LABEL


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


def _identity_slot(options: dict | None) -> tuple[int, str]:
    components = (((options or {}).get("attachmentContext") or {}).get("components") or [])
    candidates: list[tuple[int, int, str]] = []
    for component in components:
        if not isinstance(component, dict):
            continue
        name = str(component.get("componentName") or "").strip()
        folded = _fold(name)
        score = 0
        if "ho chieu" in folded:
            score += 3
        if "can cuoc" in folded:
            score += 3
        if "chung minh nhan dan" in folded or "cmnd" in folded:
            score += 2
        if "giay to tuy than" in folded:
            score += 2
        index = _coerce_int(component.get("index"))
        if score and index and index > 0:
            candidates.append((score, index, name))
    if candidates:
        _, index, name = max(candidates, key=lambda item: (item[0], -item[1]))
        return index, name
    return _ID_SLOT_INDEX, _ID_SLOT_COMPONENT


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
    """Mỗi file chỉ nhận kết quả LLM đầu tiên; thiếu file sẽ fallback theo OCR, không mất file."""
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
        }
    return result


async def plan_ket_hon_attachments_without_split(
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
    identity_subject_by_index: dict[int, str] = {}
    used_names: set[str] = set()
    identity_position = 0
    slot = _identity_slot(options)

    for file_index, file in enumerate(raw_files):
        ocr_text = documents[file_index]["ocrText"]
        llm_item = classified_by_index.get(file_index) or {}
        doc_type = llm_item.get("type") or _rule_doc_type(ocr_text)
        if file_index not in classified_by_index:
            doc_type = _rule_doc_type(ocr_text)

        if doc_type == "identity":
            document_name = _unique_document_name(
                _identity_document_name(ocr_text, llm_item.get("subjectName") or ""),
                used_names,
                _IDENTITY_LABEL,
            )
            identity_indexes.add(file_index)
            identity_subject_by_index[file_index] = llm_item.get("subjectName") or ""
            if identity_position == 0:
                target, component_index, component_name, needs_add = "existing", slot[0], slot[1], False
            else:
                target, component_index, component_name, needs_add = "new", None, document_name, True
            identity_position += 1
        elif doc_type == "marriage_declaration":
            document_name = _unique_document_name(_DECLARATION_LABEL, used_names, _DECLARATION_LABEL)
            target, component_index, component_name, needs_add = "new", None, document_name, True
        elif doc_type == "commitment":
            document_name = _unique_document_name(_COMMITMENT_LABEL, used_names, _COMMITMENT_LABEL)
            target, component_index, component_name, needs_add = "new", None, document_name, True
        else:
            proposed = llm_item.get("documentName") or _fallback_document_name(ocr_text)
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
            "type": doc_type,
            "documentName": document_name,
            "target": target,
            "componentIndex": component_index,
        })

    ocr_text_by_index = {item["fileIndex"]: item["ocrText"] for item in documents}
    attachments = merge_identity_attachments(attachments, ocr_text_by_index, identity_indexes)
    # Tên được đánh lại SAU KHI gộp: lấy tên đọc được ở bất kỳ mặt nào của cùng người. Component
    # có sẵn vẫn giữ nguyên tên DOM; chỉ documentName/component mới dùng "CCCD HỌ TÊN".
    used_identity_names: set[str] = set()
    final_identity_name_by_file: dict[int, str] = {}
    for item in attachments:
        source_indexes = item.get("sourceFileIndexes") or [item.get("fileIndex")]
        if not any(index in identity_indexes for index in source_indexes):
            continue
        combined_text = "\n".join(ocr_text_by_index.get(index, "") for index in source_indexes)
        subjects = []
        for index in source_indexes:
            subject = _clean_subject_name(identity_subject_by_index.get(index, ""))
            if subject and _fold(subject) not in {_fold(value) for value in subjects}:
                subjects.append(subject)
        subject_name = subjects[0] if len(subjects) == 1 else ""
        base_name = _identity_document_name(combined_text, subject_name)
        document_name = _unique_document_name(base_name, used_identity_names, _IDENTITY_LABEL)
        item["documentName"] = document_name
        item["detectedType"] = document_name
        if item.get("target") == "new":
            item["componentName"] = document_name
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


plan = plan_ket_hon_attachments_without_split

__all__ = ["plan", "plan_ket_hon_attachments_without_split"]
