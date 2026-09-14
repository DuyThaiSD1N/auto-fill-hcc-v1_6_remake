"""Đính kèm bước "Thành phần hồ sơ" cho thủ tục "Xác nhận thông tin hộ tịch" (giữ nguyên file).

Bảng thành phần hồ sơ trên cổng:
  1. Mẫu điện tử tương tác đề nghị xác nhận thông tin hộ tịch → cổng tự sinh Tờ khai.pdf, KHÔNG đính.
  2. Giấy tờ, tài liệu có liên quan đến nội dung đề nghị xác nhận → giấy khai sinh (ưu tiên) / giấy hộ
     tịch; CCCD/CMND và giấy liên quan khác không còn chỗ ở dòng 2 thì thêm thành phần mới.
  3. Văn bản ủy quyền (được chứng thực)                          → văn bản ủy quyền (con/cha/mẹ… nộp thay
     thì miễn, hồ sơ thường không có).
Tờ khai bản giấy (có chữ ký) → thêm thành phần mới như trích lục.
Hai mặt CCCD cùng người được gộp bằng ``sourceFileIndexes``.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.pipelines._shared.compact_agent.runner import _extract_docx_text, _is_docx
from app.pipelines._shared.identity_merge import merge_identity_attachments
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_ALLOWED_TYPES = {"paper_declaration", "civil_status", "identity", "authorization", "related", "other"}

_ROW_RELATED = (2, "Giấy tờ, tài liệu có liên quan đến nội dung đề nghị xác nhận thông tin hộ tịch")
_ROW_AUTHORIZATION = (3, "Văn bản ủy quyền")

# Thứ tự giành dòng 2: giấy hộ tịch trước (mapping: "đính kèm bản chụp Giấy khai sinh"), rồi CCCD, rồi
# giấy liên quan khác.
_ROW_PRIORITY = {"civil_status": 0, "identity": 1, "related": 2}

_LABELS = {
    "paper_declaration": "Tờ khai bản giấy",
    "civil_status": "Giấy khai sinh",
    "identity": "Căn cước công dân",
    "authorization": "Văn bản ủy quyền",
    "related": "Giấy tờ liên quan",
    "other": "Tài liệu xác nhận thông tin hộ tịch",
}

_DECLARATION_MARKERS = ("to khai de nghi xac nhan thong tin ho tich", "xac nhan thong tin ho tich")
_CIVIL_STATUS_MARKERS = (
    "giay khai sinh", "trich luc khai sinh", "giay chung nhan ket hon", "trich luc ket hon",
    "trich luc khai tu", "giay chung tu",
)
_IDENTITY_MARKERS = ("can cuoc cong dan", "citizen identity", "chung minh nhan dan", "ho chieu", "passport", "idvnm")
_AUTHORIZATION_MARKERS = ("van ban uy quyen", "giay uy quyen", "hop dong uy quyen")
_CCCD_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")


def _rule_doc_type(text: str) -> str:
    """Dự phòng khi LLM lỗi. Tờ khai kể tên giấy khai sinh/CCCD nên phải nhận tờ khai TRƯỚC."""
    folded = _fold(text)
    if not folded:
        return "other"
    if "to khai" in folded[:400] and any(m in folded for m in _DECLARATION_MARKERS):
        return "paper_declaration"
    if any(m in folded for m in _AUTHORIZATION_MARKERS):
        return "authorization"
    if any(m in folded for m in _CIVIL_STATUS_MARKERS):
        return "civil_status"
    if any(m in folded for m in _IDENTITY_MARKERS):
        return "identity"
    return "other"


def _canonical_type(value: Any) -> str:
    raw = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    aliases = {
        "cccd": "identity", "cmnd": "identity", "id": "identity", "passport": "identity",
        "declaration": "paper_declaration", "birth": "civil_status", "giay_khai_sinh": "civil_status",
        "civil_status_birth": "civil_status", "civil_status_marriage": "civil_status",
        "civil_status_death": "civil_status", "uy_quyen": "authorization",
    }
    raw = aliases.get(raw, raw)
    return raw if raw in _ALLOWED_TYPES else "other"


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _clean_subject_name(value: Any) -> str:
    subject = re.sub(r"\s+", " ", str(value or "")).strip(" :-")
    if _fold(subject) in {"", "ho ten", "ho va ten", "full name", "khong ro"}:
        return ""
    return subject[:40].strip()


def _identity_document_name(text: str, subject_name: str = "") -> str:
    folded = _fold(text)
    if "chung minh nhan dan" in folded and "can cuoc" not in folded:
        return "Chứng minh nhân dân"
    if ("passport" in folded or "ho chieu" in folded) and "can cuoc" not in folded:
        return "Hộ chiếu"
    subject = _clean_subject_name(subject_name)
    if subject and len(set(_CCCD_RE.findall(str(text or "")))) <= 1:
        return normalize_document_name(f"CCCD {subject}", _LABELS["identity"])
    return _LABELS["identity"]


def _unique_document_name(base: str, used: set[str], fallback: str) -> str:
    normalized = normalize_document_name(base, fallback)
    if _fold(normalized) not in used:
        used.add(_fold(normalized))
        return normalized
    stem = normalized[:45].strip() or fallback[:45].strip()
    suffix = 2
    while _fold(f"{stem} {suffix}") in used:
        suffix += 1
    candidate = f"{stem} {suffix}"[:50].strip()
    used.add(_fold(candidate))
    return candidate


async def _classify_with_llm(documents: list[dict[str, Any]]) -> list[dict]:
    if not documents:
        return []
    raw = await client.chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(documents)},
        ],
        max_tokens=max(600, min(2400, len(documents) * 160)),
        enable_thinking=settings.agent_reasoning,
    )
    parsed = client.extract_json_block(raw)
    return parsed.get("documents", []) if isinstance(parsed, dict) else []


def _validated_classifications(raw_items: list[dict], file_count: int) -> dict[int, dict]:
    result: dict[int, dict] = {}
    for raw in raw_items or []:
        if not isinstance(raw, dict):
            continue
        file_index = _coerce_int(raw.get("fileIndex", raw.get("index")))
        if file_index is None or not 0 <= file_index < file_count or file_index in result:
            continue
        result[file_index] = {
            "type": _canonical_type(raw.get("type")),
            "documentName": str(raw.get("documentName") or "").strip(),
            "subjectName": _clean_subject_name(raw.get("subjectName")),
        }
    return result


def build_plan_items(
    raw_files: list[dict],
    ocr_text_by_index: dict[int, str],
    llm_by_index: dict[int, dict],
) -> tuple[list[dict], list[dict], list[str]]:
    """Dựng kế hoạch đính kèm từ loại giấy đã phân (tách khỏi I/O để test)."""
    types: dict[int, str] = {}
    for index in range(len(raw_files)):
        llm_item = llm_by_index.get(index)
        types[index] = llm_item["type"] if llm_item else _rule_doc_type(ocr_text_by_index.get(index, ""))

    # Chốt dòng CÓ SẴN trước theo độ ưu tiên, không theo thứ tự upload.
    slot_owner: dict[int, int] = {}
    related = [i for i, t in types.items() if t in _ROW_PRIORITY]
    if related:
        slot_owner[_ROW_RELATED[0]] = min(related, key=lambda i: (_ROW_PRIORITY[types[i]], i))
    authorization = [i for i, t in types.items() if t == "authorization"]
    if authorization:
        slot_owner[_ROW_AUTHORIZATION[0]] = authorization[0]
    row_by_file = {file_index: row for row, file_index in slot_owner.items()}

    attachments: list[dict] = []
    classified: list[dict] = []
    used_names: set[str] = set()
    identity_indexes: set[int] = set()
    subject_by_index: dict[int, str] = {}
    for index, file in enumerate(raw_files):
        doc_type = types[index]
        llm_item = llm_by_index.get(index) or {}
        text = ocr_text_by_index.get(index, "")
        if doc_type == "identity":
            identity_indexes.add(index)
            subject_by_index[index] = llm_item.get("subjectName") or ""
            base = _identity_document_name(text, subject_by_index[index])
        elif doc_type in ("civil_status", "related", "other"):
            base = llm_item.get("documentName") or _LABELS[doc_type]
        else:
            base = _LABELS[doc_type]
        document_name = _unique_document_name(base, used_names, _LABELS[doc_type])

        row = row_by_file.get(index)
        if row == _ROW_RELATED[0]:
            target, component_index, component_name = "existing", *_ROW_RELATED
        elif row == _ROW_AUTHORIZATION[0]:
            target, component_index, component_name = "existing", *_ROW_AUTHORIZATION
        else:
            target, component_index, component_name = "new", None, document_name
        attachments.append({
            "fileIndex": index,
            "fileName": str(file.get("name") or f"file-{index + 1}"),
            "documentName": document_name,
            "componentName": component_name,
            "target": target,
            "componentIndex": component_index,
            "needsAddComponent": target == "new",
            "detectedType": document_name,
        })
        classified.append({
            "fileIndex": index, "fileName": file.get("name"), "type": doc_type,
            "documentName": document_name, "target": target, "componentIndex": component_index,
        })

    attachments = merge_identity_attachments(attachments, ocr_text_by_index, identity_indexes)

    warnings: list[str] = []
    if not any(t == "civil_status" for t in types.values()):
        warnings.append(
            "Hồ sơ chưa có Giấy khai sinh / giấy tờ hộ tịch của người được xác nhận (dòng 2) — vui lòng đính tay "
            "nếu có."
        )
    return attachments, classified, warnings


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file([f for _, f in ocr_pairs]) if ocr_pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    ocr_by_index = {i: result for (i, _), result in zip(ocr_pairs, ocr_results)}
    for i, result in ocr_by_index.items():
        if result.get("error"):
            errors.append(f"OCR fileIndex={i} {raw_files[i].get('name')}: {result['error']}")
    ocr_text_by_index = {i: str((ocr_by_index.get(i) or {}).get("text") or "") for i in range(len(raw_files))}
    # Giấy khai sinh hay được gửi nguyên file .docx: đọc text trực tiếp để phân loại, không qua OCR.
    for i, f in enumerate(raw_files):
        if _is_docx(f) and not ocr_text_by_index[i]:
            ocr_text_by_index[i] = str(_extract_docx_text(f).get("text") or "")

    started = time.monotonic()
    raw_classifications: list[dict] = []
    documents = [{"fileIndex": i, "ocrText": ocr_text_by_index[i]} for i in range(len(raw_files))]
    if documents:
        try:
            raw_classifications = await _classify_with_llm(documents)
        except Exception as exc:  # noqa: BLE001 - rule dự phòng vẫn giữ đủ file
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, classified, warnings = build_plan_items(
        raw_files, ocr_text_by_index, _validated_classifications(raw_classifications, len(raw_files)),
    )
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [raw_files[i].get("name") for i, r in ocr_by_index.items() if r.get("text")],
            "sessionId": (session or {}).get("request_id"),
            "attachmentMode": "preserve_files",
            "classified": classified,
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
