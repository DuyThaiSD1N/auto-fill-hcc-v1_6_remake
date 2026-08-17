"""Đính kèm bước 3 cho thủ tục "Đăng ký lại khai tử".

Bảng thành phần hồ sơ:
  STT1 - Mẫu hộ tịch điện tử tương tác đăng ký lại khai tử: eForm tự có, không xử lý.
  STT2 - Bản sao Giấy chứng tử trước đây hoặc giấy tờ liên quan chứng minh sự kiện chết.
  STT3 - Văn bản ủy quyền nếu có.

Tờ khai bản giấy, CCCD/giấy tờ tùy thân và mọi giấy tờ khác -> thêm thành phần hồ sơ mới.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold, normalize_document_name
from app.pipelines._shared.identity_merge import merge_identity_attachments
from app.pipelines.khai_tu_dang_ky_lai.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DOC_DEATH_PROOF = "death_proof"
_DOC_AUTHORIZATION = "authorization"
_DOC_PAPER_DECLARATION = "paper_declaration"
_DOC_IDENTITY = "identity"
_DOC_OTHER = "other"
_ALLOWED_DOC_TYPES = {
    _DOC_DEATH_PROOF,
    _DOC_AUTHORIZATION,
    _DOC_PAPER_DECLARATION,
    _DOC_IDENTITY,
    _DOC_OTHER,
}

_DEATH_PROOF_LABEL = "Giấy tờ chứng minh sự kiện chết"
_AUTHORIZATION_LABEL = "Văn bản ủy quyền"
_PAPER_DECLARATION_LABEL = "Tờ khai bản giấy"
_IDENTITY_LABEL = "Căn cước công dân"
_OTHER_LABEL = "Giấy tờ khác"

_ROW_2_COMPONENT = (
    "- Bản sao Giấy chứng tử trước đây được cấp hợp lệ. Nếu không có bản sao Giấy chứng tử "
    "trước đây được cấp hợp lệ thì nộp bản sao hồ sơ, giấy tờ liên quan có nội dung chứng minh "
    "sự kiện chết."
)

_ROW_3_COMPONENT = (
    "- Văn bản ủy quyền theo quy định của pháp luật trong trường hợp ủy quyền thực hiện việc "
    "đăng ký lại khai tử."
)
def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _normalize_doc_type(value: str) -> str:
    raw = str(value or "").strip()
    if raw in _ALLOWED_DOC_TYPES:
        return raw
    text = fold(raw)
    if not text or text == "other":
        return _DOC_OTHER
    if "authorization" in text or "uy quyen" in text:
        return _DOC_AUTHORIZATION
    if "paper" in text or "declaration" in text or "to khai" in text:
        return _DOC_PAPER_DECLARATION
    if "identity" in text or "cccd" in text or "can cuoc" in text or "cmnd" in text:
        return _DOC_IDENTITY
    if "death" in text or "khai tu" in text or "chung tu" in text or "lang mo" in text or "bia mo" in text:
        return _DOC_DEATH_PROOF
    return _DOC_OTHER


def _rule_doc_type(text: str) -> str:
    haystack = fold(text)
    if not haystack:
        return ""

    is_paper_declaration = (
        "to khai dang ky lai khai tu" in haystack
        or "to khai dang ky khai tu" in haystack
    )
    has_tombstone_or_death_info = any(
        marker in haystack
        for marker in (
            "lang mo",
            "bia mo",
            "ta the",
            "tu tran",
            "da mat",
            "mat ngay",
            "ngay mat",
            "nam mat",
            "chung minh su kien chet",
            "thong tin bia mo",
        )
    ) or bool(re.search(r"\bsinh nam\b.*\b(ta the|mat|chet)\b", haystack))
    has_death_certificate = any(
        marker in haystack
        for marker in (
            "giay chung tu",
            "trich luc khai tu",
            "giay bao tu",
            "ban sao khai tu",
        )
    )

    # Tờ khai có nhãn trống "Giấy chứng tử/Trích lục khai tử số..." nên không coi riêng
    # chữ "Giấy chứng tử/Trích lục khai tử" trong tờ khai là giấy tờ chứng minh chết.
    if is_paper_declaration and not has_tombstone_or_death_info:
        return _DOC_PAPER_DECLARATION

    # File gộp có cả tờ khai và giấy tờ chứng minh chết rõ ràng thì ưu tiên STT2.
    if has_tombstone_or_death_info or has_death_certificate:
        return _DOC_DEATH_PROOF
    if is_paper_declaration:
        return _DOC_PAPER_DECLARATION

    if any(marker in haystack for marker in ("van ban uy quyen", "giay uy quyen", "ben uy quyen", "ben duoc uy quyen")):
        return _DOC_AUTHORIZATION

    if any(
        marker in haystack
        for marker in (
            "can cuoc cong dan",
            "the can cuoc",
            "chung minh nhan dan",
            "citizen identity card",
            "identity card",
            "so dinh danh ca nhan",
            "idvnm",
            "ho chieu",
        )
    ):
        return _DOC_IDENTITY

    return ""


def _route_for_type(doc_type: str) -> tuple[str, int | None, str]:
    if doc_type == _DOC_DEATH_PROOF:
        return "existing", 2, _ROW_2_COMPONENT
    if doc_type == _DOC_AUTHORIZATION:
        return "existing", 3, _ROW_3_COMPONENT
    return "new", None, ""


def _label_for_type(doc_type: str) -> str:
    return {
        _DOC_DEATH_PROOF: _DEATH_PROOF_LABEL,
        _DOC_AUTHORIZATION: _AUTHORIZATION_LABEL,
        _DOC_PAPER_DECLARATION: _PAPER_DECLARATION_LABEL,
        _DOC_IDENTITY: _IDENTITY_LABEL,
    }.get(doc_type, _OTHER_LABEL)


def _unique_document_name(base: str, used: set[str], fallback: str) -> str:
    normalized = normalize_document_name(base, fallback)
    key = fold(normalized)
    if key and key not in used:
        used.add(key)
        return normalized
    stem = normalized[:45].strip() or fallback[:45].strip() or _OTHER_LABEL
    n = 2
    while True:
        candidate = f"{stem} {n}"[:50].strip()
        key = fold(candidate)
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
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(docs)},
    ]
    raw = await client.chat(messages, max_tokens=700, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    parsed_docs = parsed.get("documents", []) or []

    def _coerce(item: dict) -> dict[str, str]:
        return {
            "type": _normalize_doc_type(str(item.get("docType") or item.get("type") or "")),
            "documentName": str(item.get("documentName") or item.get("title") or "").strip(),
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


def _resolve_document_name(file: dict, doc_type: str, detected: dict, used: set[str]) -> str:
    # Type ĐÃ BIẾT → dùng NHÃN CHUẨN theo type, KHÔNG lấy documentName tự do của LLM: tránh tờ khai bị
    # LLM đặt nhầm "Trích lục khai tử" (do đọc trúng dòng "Giấy chứng tử/Trích lục khai tử số..." trong
    # tờ khai). Mọi tài liệu ngoài 3 nhóm chính dùng đúng component "Giấy tờ khác".
    fallback = _label_for_type(doc_type)
    base = fallback
    return _unique_document_name(base, used, fallback)


def _build_item(file: dict, idx: int, doc_type: str, document_name: str) -> dict:
    target, component_index, existing_component = _route_for_type(doc_type)
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


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, dict[str, str]] | None = None,
) -> tuple[list[dict], list[dict]]:
    llm_types = llm_types or {}
    by_name = {item.get("name"): item for item in ocr_results}
    used_names: set[str] = set()
    attachments: list[dict] = []
    classified: list[dict] = []
    ocr_text_by_index: dict[int, str] = {}
    identity_indexes: set[int] = set()

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = str(by_name.get(file_name, {}).get("text") or "")
        ocr_text_by_index[idx] = text
        rule_type = _rule_doc_type(text)
        detected = llm_types.get(idx) or {}
        llm_type = detected.get("type") or ""
        # ƯU TIÊN LLM cho phân loại chung; rule là LƯỚI ĐỠ khi LLM rỗng/không hợp lệ.
        doc_type = llm_type or rule_type or _DOC_OTHER
        # CHỐT CHẶN tất định: tờ khai (paper_declaration) và CCCD (identity) rule bắt RẤT CHẮC và TUYỆT
        # ĐỐI không được vào STT2 (chúng là thành phần hồ sơ MỚI). Ép theo rule, đè LLM — vì LLM hay gán
        # nhầm tờ khai thành death_proof (tờ khai có dòng "Đã chết..." + tham chiếu "Trích lục khai tử số"),
        # khiến tờ khai và trích lục thật đụng cùng ô STT2 → FE bỏ qua 1 file.
        # Bằng chứng chết rõ ràng cũng phải đè LLM khi file gộp có CCCD + lăng mộ/giấy chứng tử;
        # nếu không, LLM dễ chọn identity và làm mất đường vào STT2.
        rule_override = rule_type in (_DOC_PAPER_DECLARATION, _DOC_IDENTITY, _DOC_DEATH_PROOF, _DOC_AUTHORIZATION)
        if rule_override:
            doc_type = rule_type
        if doc_type not in _ALLOWED_DOC_TYPES:
            doc_type = _DOC_OTHER
        if doc_type == _DOC_IDENTITY:
            identity_indexes.add(idx)
        document_name = _resolve_document_name(file, doc_type, detected, used_names)
        item = _build_item(file, idx, doc_type, document_name)
        attachments.append(item)
        classified.append({
            "fileName": file_name,
            "docType": doc_type,
            "documentName": document_name,
            "target": item["target"],
            "componentIndex": item["componentIndex"],
            "source": "rule" if rule_override else ("llm" if llm_type else ("rule" if rule_type else "default")),
        })

    # Gộp CCCD 2 mặt CÙNG người thành 1 PDF (mặt trước→sau) vào ô giấy tùy thân.
    attachments = merge_identity_attachments(attachments, ocr_text_by_index, identity_indexes)

    return attachments, classified


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

    attachments, classified = build_plan_items(raw_files, ocr_results, llm_types)
    skipped_ocr = [file["name"] for file in raw_files if file.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [file["name"] for file in raw_files],
            "ocrDocuments": [item.get("name") for item in ocr_results if item.get("text")],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "sessionId": (session or {}).get("request_id"),
            "classified": classified,
            "skippedOcr": skipped_ocr,
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "errors": errors,
    }
