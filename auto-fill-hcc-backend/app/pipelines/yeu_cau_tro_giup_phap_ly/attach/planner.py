"""Đính kèm bước "Thành phần hồ sơ" cho "Thủ tục yêu cầu trợ giúp pháp lý" (giữ nguyên file).

Bảng thành phần hồ sơ trên cổng:
  1. Giấy tờ chứng minh người thuộc diện trợ giúp pháp lý → Thông báo về TGPL / giấy chứng minh diện khác
     + CCCD của người được trợ giúp, GỘP MỘT PDF (``sourceFileIndexes``): giấy chứng minh diện đứng trước,
     CCCD theo từng người mặt trước → mặt sau. Tệp gộp đặt tên "Trợ giúp pháp lý".
  2. Đơn yêu cầu trợ giúp pháp lý (bắt buộc) → cổng tự sinh Tờ khai.pdf từ bước Kê khai, KHÔNG đính đè.
Đơn yêu cầu bản giấy, văn bản ủy quyền và giấy không rõ loại → thêm thành phần hồ sơ mới.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.compact_agent.runner import _extract_docx_text, _is_docx
from app.pipelines._shared.identity_merge import _cccd_number, _face_rank, _looks_like_cccd, _person_of
from app.pipelines.xac_nhan_thong_tin_ho_tich.attach.planner import (
    _clean_subject_name,
    _coerce_int,
    _unique_document_name,
)
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_ALLOWED_TYPES = {"proof", "identity", "paper_request", "authorization", "other"}

_ROW_PROOF = (1, "Giấy tờ chứng minh người thuộc diện trợ giúp pháp lý")
# Tên tệp gộp đính vào dòng 1 (FE đặt tên PDF theo documentName); componentName vẫn là chữ của dòng để khớp.
_ROW_PROOF_FILE_NAME = "Trợ giúp pháp lý"

_LABELS = {
    "proof": "Giấy tờ chứng minh diện trợ giúp pháp lý",
    "identity": "Căn cước công dân",
    "paper_request": "Đơn yêu cầu trợ giúp pháp lý bản giấy",
    "authorization": "Văn bản ủy quyền",
    "other": "Tài liệu trợ giúp pháp lý",
}

_REQUEST_MARKERS = ("don yeu cau tro giup phap ly",)
_NOTICE_MARKERS = ("thong bao ve tro giup phap ly", "thuoc dien tro giup phap ly", "nguoi duoc tro giup phap ly")
_PROOF_MARKERS = (
    "ho ngheo", "ho can ngheo", "khuyet tat", "nguoi co cong", "thuong binh", "liet si", "quyet dinh khoi to",
    "lenh tam giam", "lenh tam giu", "bao luc gia dinh", "mua ban nguoi", "giay khai sinh",
)
_AUTHORIZATION_MARKERS = ("van ban uy quyen", "giay uy quyen", "hop dong uy quyen")


def _rule_doc_type(text: str) -> str:
    """Dự phòng khi LLM lỗi. Đơn và Thông báo đều nhắc CCCD nên phải nhận chúng TRƯỚC thẻ."""
    folded = _fold(text)
    if not folded:
        return "other"
    head = folded[:400]
    if any(m in head for m in _REQUEST_MARKERS):
        return "paper_request"
    if any(m in folded for m in _NOTICE_MARKERS):
        return "proof"
    if any(m in folded for m in _AUTHORIZATION_MARKERS):
        return "authorization"
    if _looks_like_cccd(text):
        return "identity"
    if any(m in folded for m in _PROOF_MARKERS):
        return "proof"
    return "other"


def _canonical_type(value: Any) -> str:
    raw = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    aliases = {
        "cccd": "identity", "cmnd": "identity", "id": "identity", "passport": "identity",
        "notice": "proof", "thong_bao": "proof", "request": "paper_request", "don": "paper_request",
        "uy_quyen": "authorization",
    }
    raw = aliases.get(raw, raw)
    return raw if raw in _ALLOWED_TYPES else "other"


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


def _identity_order(indexes: list[int], ocr_text_by_index: dict[int, str]) -> list[int]:
    """CCCD theo từng người (thứ tự xuất hiện), trong một người mặt trước → mặt sau."""
    persons: list[str] = []
    for index in indexes:
        number = _cccd_number(ocr_text_by_index.get(index, ""))
        if number and number not in persons:
            persons.append(number)

    def key(index: int) -> tuple[int, int, int]:
        text = ocr_text_by_index.get(index, "")
        person = _person_of(text, persons)
        rank = persons.index(person) if person in persons else len(persons)
        return rank, _face_rank(text), index

    return sorted(indexes, key=key)


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

    proof = [i for i in range(len(raw_files)) if types[i] == "proof"]
    identity = _identity_order([i for i in range(len(raw_files)) if types[i] == "identity"], ocr_text_by_index)
    row_sources = proof + identity

    attachments: list[dict] = []
    classified: list[dict] = []
    if row_sources:
        first = row_sources[0]
        item = {
            "fileIndex": first,
            "fileName": str(raw_files[first].get("name") or f"file-{first + 1}"),
            "documentName": _ROW_PROOF_FILE_NAME,
            "componentName": _ROW_PROOF[1],
            "target": "existing",
            "componentIndex": _ROW_PROOF[0],
            "needsAddComponent": False,
            "detectedType": _LABELS[types[first]],
        }
        if len(row_sources) > 1:
            item["sourceFileIndexes"] = row_sources
        attachments.append(item)
        for index in row_sources:
            classified.append({
                "fileIndex": index, "fileName": raw_files[index].get("name"), "type": types[index],
                "documentName": _ROW_PROOF_FILE_NAME, "target": "existing", "componentIndex": _ROW_PROOF[0],
            })

    used_names = {_fold(_ROW_PROOF[1]), _fold(_ROW_PROOF_FILE_NAME)}
    for index, file in enumerate(raw_files):
        doc_type = types[index]
        if doc_type in ("proof", "identity"):
            continue
        base = (llm_by_index.get(index) or {}).get("documentName") if doc_type == "other" else ""
        document_name = _unique_document_name(base or _LABELS[doc_type], used_names, _LABELS[doc_type])
        attachments.append({
            "fileIndex": index,
            "fileName": str(file.get("name") or f"file-{index + 1}"),
            "documentName": document_name,
            "componentName": document_name,
            "target": "new",
            "componentIndex": None,
            "needsAddComponent": True,
            "detectedType": document_name,
        })
        classified.append({
            "fileIndex": index, "fileName": file.get("name"), "type": doc_type,
            "documentName": document_name, "target": "new", "componentIndex": None,
        })

    warnings: list[str] = []
    if not proof:
        warnings.append(
            "Hồ sơ chưa có giấy tờ chứng minh diện trợ giúp pháp lý (vd Thông báo về trợ giúp pháp lý) — dòng 1 "
            "chỉ có CCCD, vui lòng bổ sung."
        )
    if not identity:
        warnings.append("Hồ sơ chưa có ảnh CCCD/căn cước của người được trợ giúp pháp lý — dòng 1 chưa đủ giấy tờ.")
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
