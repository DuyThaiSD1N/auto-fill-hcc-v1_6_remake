"""Đính kèm bước 3 cho thủ tục "Đăng ký nhận cha, mẹ, con".

Bảng thành phần hồ sơ:
  STT1 - Mẫu hộ tịch điện tử tương tác đăng ký nhận cha, mẹ, con: eForm tự có.
  STT2 - Văn bản của cơ quan y tế/cơ quan giám định/cơ quan có thẩm quyền xác nhận quan hệ cha con, mẹ con.
  STT3 - Nếu không có STT2: văn bản cam đoan của các bên và ít nhất hai người làm chứng.

Tờ khai bản giấy, CCCD/căn cước, giấy khai sinh/giấy chứng sinh và giấy tờ loại khác
-> thêm thành phần hồ sơ mới.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold, normalize_document_name
from app.pipelines._shared.identity_merge import merge_identity_attachments
from app.pipelines.nhan_cha_me_con.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DOC_RELATIONSHIP_PROOF = "relationship_proof"
_DOC_WITNESS_COMMITMENT = "witness_commitment"
_DOC_PAPER_DECLARATION = "paper_declaration"
_DOC_IDENTITY = "identity"
_DOC_BIRTH_DOCUMENT = "birth_document"
_DOC_AUTHORIZATION = "authorization"
_DOC_OTHER = "other"
_DOC_SKIP = "skip"

_ALLOWED_DOC_TYPES = {
    _DOC_RELATIONSHIP_PROOF,
    _DOC_WITNESS_COMMITMENT,
    _DOC_PAPER_DECLARATION,
    _DOC_IDENTITY,
    _DOC_BIRTH_DOCUMENT,
    _DOC_AUTHORIZATION,
    _DOC_OTHER,
    _DOC_SKIP,
}

_RELATIONSHIP_PROOF_LABEL = "Kết quả xét nghiệm ADN"
_WITNESS_COMMITMENT_LABEL = "Văn bản cam đoan quan hệ cha, mẹ, con"
_PAPER_DECLARATION_LABEL = "Tờ khai đăng ký nhận cha, mẹ, con bản giấy"
_IDENTITY_LABEL = "Căn cước công dân"
_BIRTH_DOCUMENT_LABEL = "Giấy khai sinh/Giấy chứng sinh"
_AUTHORIZATION_LABEL = "Văn bản ủy quyền"
_OTHER_LABEL = "Tài liệu đăng ký nhận cha, mẹ, con"
_SKIP_LABEL = "Bỏ qua"

_ROW_2_COMPONENT = "+ Văn bản của cơ quan y tế, cơ quan giám định hoặc cơ quan khác có thẩm quyền xác nhận quan hệ cha con, quan hệ mẹ con."
_ROW_3_COMPONENT = "+ Trường hợp không có văn bản nêu trên thì phải có văn bản cam đoan của các bên nhận cha, mẹ, con về mối quan hệ cha, mẹ, con và có ít nhất hai người làm chứng về mối quan hệ cha, mẹ, con."


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _has_any(haystack: str, needles: tuple[str, ...]) -> bool:
    return any(needle in haystack for needle in needles)


def _normalize_doc_type(value: str) -> str:
    raw = str(value or "").strip()
    if raw in _ALLOWED_DOC_TYPES:
        return raw
    text = fold(raw)
    if not text or text == "other":
        return _DOC_OTHER
    if _has_any(text, ("relationship", "adn", "dna", "huyet thong", "giam dinh")):
        return _DOC_RELATIONSHIP_PROOF
    if _has_any(text, ("witness", "commitment", "cam doan", "lam chung")):
        return _DOC_WITNESS_COMMITMENT
    if _has_any(text, ("paper", "declaration", "to khai")):
        return _DOC_PAPER_DECLARATION
    if _has_any(text, ("birth", "khai sinh", "chung sinh", "gcs")):
        return _DOC_BIRTH_DOCUMENT
    if _has_any(text, ("identity", "cccd", "can cuoc", "cmnd", "ho chieu")):
        return _DOC_IDENTITY
    if _has_any(text, ("authorization", "uy quyen")):
        return _DOC_AUTHORIZATION
    if _has_any(text, ("skip", "irrelevant", "khong lien quan", "bo qua")):
        return _DOC_SKIP
    return _DOC_OTHER


def _is_relationship_proof(haystack: str) -> bool:
    if not haystack:
        return False
    if _has_any(
        haystack,
        (
            "ket qua xet nghiem adn",
            "xet nghiem adn",
            "xet nghiem dna",
            "giam dinh adn",
            "giam dinh dna",
            "giam dinh gen",
            "genemapper",
            "verifiler",
            "locus mau",
            "ky hieu mau",
            "novamed",
        ),
    ):
        return True
    relation_markers = (
        "quan he huyet thong",
        "quan he bo con",
        "quan he cha con",
        "quan he me con",
        "bo - con",
        "cha - con",
        "me - con",
        "do tin cay",
    )
    return _has_any(haystack, relation_markers) and _has_any(haystack, ("ket luan", "xac nhan", "co quan y te", "co quan giam dinh"))


def _rule_doc_type(text: str) -> str:
    haystack = fold(text)
    if not haystack:
        return ""

    # File gộp có kết quả ADN/y tế phải đi STT2, dù cùng file có CCCD/GCS.
    if _is_relationship_proof(haystack):
        return _DOC_RELATIONSHIP_PROOF

    if _has_any(
        haystack,
        (
            "van ban uy quyen",
            "giay uy quyen",
            "ben uy quyen",
            "ben duoc uy quyen",
        ),
    ):
        return _DOC_AUTHORIZATION

    # Tờ khai mẫu luôn có câu "Tôi cam đoan..." ở cuối. Phải nhận là tờ khai
    # trước khi xét văn bản cam đoan riêng, nếu không sẽ bị skip khi đã có ADN.
    if "to khai dang ky nhan cha" in haystack and " me" in haystack and " con" in haystack:
        return _DOC_PAPER_DECLARATION

    if _has_any(
        haystack,
        (
            "van ban cam doan",
            "ban cam doan",
            "cam doan cua cac ben",
            "nguoi lam chung",
            "lam chung ve moi quan he",
            "cam doan viec nhan cha con",
            "cam doan viec nhan me con",
        ),
    ):
        return _DOC_WITNESS_COMMITMENT

    if _has_any(
        haystack,
        (
            "giay chung sinh",
            "ma so gcs",
            "da sinh con vao luc",
            "du dinh dat ten con",
            "dai dien co so kcb",
            "benh vien",
        ),
    ):
        return _DOC_BIRTH_DOCUMENT

    if (
        "giay khai sinh" in haystack
        or "noi dang ky khai sinh" in haystack
        or ("nguoi me" in haystack and "nguoi cha" in haystack and "ho chu dem ten" in haystack)
    ):
        return _DOC_BIRTH_DOCUMENT

    if _has_any(
        haystack,
        (
            "can cuoc cong dan",
            "the can cuoc",
            "citizen identity card",
            "identity card",
            "so / no",
            "so dinh danh ca nhan",
            "idvnm",
            "chung minh nhan dan",
            "cmnd",
            "ho chieu",
        ),
    ):
        return _DOC_IDENTITY

    return ""


def _rule_document_name(doc_type: str, text: str) -> str:
    haystack = fold(text)
    if doc_type == _DOC_RELATIONSHIP_PROOF:
        if _has_any(haystack, ("adn", "dna", "genemapper", "verifiler", "locus mau")):
            return _RELATIONSHIP_PROOF_LABEL
        return "Văn bản xác nhận quan hệ cha, mẹ, con"
    if doc_type == _DOC_WITNESS_COMMITMENT:
        return _WITNESS_COMMITMENT_LABEL
    if doc_type == _DOC_PAPER_DECLARATION:
        return _PAPER_DECLARATION_LABEL
    if doc_type == _DOC_IDENTITY:
        return _IDENTITY_LABEL
    if doc_type == _DOC_BIRTH_DOCUMENT:
        if "giay chung sinh" in haystack or "ma so gcs" in haystack:
            return "Giấy chứng sinh"
        if "giay khai sinh" in haystack:
            return "Giấy khai sinh"
        return _BIRTH_DOCUMENT_LABEL
    if doc_type == _DOC_AUTHORIZATION:
        return _AUTHORIZATION_LABEL
    if doc_type == _DOC_SKIP:
        return _SKIP_LABEL
    return ""


def _route_for_type(doc_type: str) -> tuple[str, int | None, str]:
    if doc_type == _DOC_RELATIONSHIP_PROOF:
        return "existing", 2, _ROW_2_COMPONENT
    if doc_type == _DOC_WITNESS_COMMITMENT:
        return "existing", 3, _ROW_3_COMPONENT
    return "new", None, ""


def _label_for_type(doc_type: str) -> str:
    return {
        _DOC_RELATIONSHIP_PROOF: _RELATIONSHIP_PROOF_LABEL,
        _DOC_WITNESS_COMMITMENT: _WITNESS_COMMITMENT_LABEL,
        _DOC_PAPER_DECLARATION: _PAPER_DECLARATION_LABEL,
        _DOC_IDENTITY: _IDENTITY_LABEL,
        _DOC_BIRTH_DOCUMENT: _BIRTH_DOCUMENT_LABEL,
        _DOC_AUTHORIZATION: _AUTHORIZATION_LABEL,
        _DOC_SKIP: _SKIP_LABEL,
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
    raw = await client.chat(messages, max_tokens=900, enable_thinking=settings.agent_reasoning)
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
    fallback = _label_for_type(doc_type)
    base = detected.get("documentName") or fallback or file.get("name") or ""
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
) -> tuple[list[dict], list[dict], dict[int, str], set[int]]:
    llm_types = llm_types or {}
    by_name = {item.get("name"): item for item in ocr_results}
    used_names: set[str] = set()
    resolved: list[dict] = []
    # Thu thập cho helper gộp CCCD 2 mặt cùng người (khóa theo số định danh).
    ocr_text_by_index: dict[int, str] = {}
    identity_indexes: set[int] = set()

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = str(by_name.get(file_name, {}).get("text") or "")
        ocr_text_by_index[idx] = text
        rule_type = _rule_doc_type(text)
        detected = llm_types.get(idx) or {}
        llm_type = detected.get("type") or ""
        doc_type = rule_type or llm_type or _DOC_OTHER
        if doc_type not in _ALLOWED_DOC_TYPES:
            doc_type = _DOC_OTHER
        if doc_type == _DOC_IDENTITY:
            identity_indexes.add(idx)
        rule_name = _rule_document_name(doc_type, text) if rule_type else ""
        name_source = {"documentName": rule_name} if rule_name else detected
        resolved.append({
            "idx": idx,
            "fileName": file_name,
            "file": file,
            "docType": doc_type,
            "nameSource": name_source,
            "source": "rule" if rule_type else ("llm" if llm_type else "default"),
        })

    has_relationship_proof = any(entry["docType"] == _DOC_RELATIONSHIP_PROOF for entry in resolved)
    attachments: list[dict] = []
    classified: list[dict] = []

    for entry in sorted(resolved, key=lambda item: item["idx"]):
        idx = entry["idx"]
        file = entry["file"]
        doc_type = entry["docType"]

        if doc_type == _DOC_WITNESS_COMMITMENT and has_relationship_proof:
            classified.append({
                "fileName": entry["fileName"],
                "docType": doc_type,
                "documentName": _WITNESS_COMMITMENT_LABEL,
                "target": "skip",
                "componentIndex": None,
                "source": entry["source"],
                "reason": "relationship_proof_present",
            })
            continue

        if doc_type == _DOC_SKIP:
            classified.append({
                "fileName": entry["fileName"],
                "docType": doc_type,
                "documentName": _SKIP_LABEL,
                "target": "skip",
                "componentIndex": None,
                "source": entry["source"],
            })
            continue

        document_name = _resolve_document_name(file, doc_type, entry["nameSource"], used_names)
        item = _build_item(file, idx, doc_type, document_name)
        attachments.append(item)
        classified.append({
            "fileName": entry["fileName"],
            "docType": doc_type,
            "documentName": document_name,
            "target": item["target"],
            "componentIndex": item["componentIndex"],
            "source": entry["source"],
        })

    return attachments, classified, ocr_text_by_index, identity_indexes


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

    attachments, classified, ocr_text_by_index, identity_indexes = build_plan_items(
        raw_files, ocr_results, llm_types
    )
    # Gộp CCCD 2 mặt CÙNG người thành 1 PDF (mặt trước→sau); nhiều người → khóa số định danh nên an toàn.
    attachments = merge_identity_attachments(attachments, ocr_text_by_index, identity_indexes)
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
