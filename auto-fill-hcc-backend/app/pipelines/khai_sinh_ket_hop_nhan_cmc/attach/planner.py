"""Rule-first, LLM-fallback attachment routing for the combined procedure."""

import re
import time
from pathlib import Path
from typing import Any

from app.config import settings
from app.pipelines._shared import fold, normalize_document_name
from app.pipelines.khai_sinh_ket_hop_nhan_cmc.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_BIRTH_ROW = "+ Giấy chứng sinh; trường hợp không có giấy chứng sinh thì nộp văn bản của người làm chứng xác nhận về việc sinh"
_RELATIONSHIP_ROW = "+ Văn bản của cơ quan y tế, cơ quan giám định hoặc cơ quan khác có thẩm quyền xác nhận quan hệ cha con, quan hệ mẹ con."
_WITNESS_ROW = "+ Trường hợp không có văn bản nêu trên thì các bên nhận cha, mẹ, con lập văn bản cam đoan về mối quan hệ cha, mẹ, con, có ít nhất hai người làm chứng về mối quan hệ cha, mẹ, con."

_ALLOWED_LLM_TYPES = {
    "relationship_proof",
    "birth_proof",
    "birth_declaration",
    "recognition_declaration",
    "identity",
    "marital_status_evidence",
    "witness_commitment",
    "authorization",
    "other",
}
_GENERIC_NAMES = {
    "tai lieu bo sung",
    "tai lieu khac",
    "ho so bo sung",
    "giay to bo sung",
    "tai lieu dinh kem",
    "khong xac dinh",
}


def _has(text: str, *markers: str) -> bool:
    return any(marker in text for marker in markers)


def _doc_type(text: str) -> str:
    value = fold(text)
    if _has(value, "ket qua xet nghiem adn", "xet nghiem dna", "giam dinh gen", "quan he huyet thong", "novamed"):
        return "relationship_proof"
    if _has(value, "giay chung sinh", "ma so gcs", "da sinh con vao luc"):
        return "birth_proof"
    if _has(value, "to khai dang ky nhan cha", "to khai dang ki nhan cha"):
        return "recognition_declaration"
    if _has(value, "to khai dang ky khai sinh", "to khai dang ki khai sinh"):
        return "birth_declaration"
    if _has(value, "can cuoc cong dan", "the can cuoc", "citizen identity", "idvnm", "chung minh nhan dan"):
        return "identity"
    if _has(value, "giay chung tu", "trich luc khai tu"):
        return "marital_status_evidence"
    if _has(value, "quyet dinh ly hon", "ban an ly hon", "cong nhan thuan tinh ly hon"):
        return "marital_status_evidence"
    return "other"


def _label(doc_type: str, text: str) -> str:
    value = fold(text)
    if doc_type == "relationship_proof":
        return "Kết quả xét nghiệm ADN"
    if doc_type == "birth_proof":
        return "Giấy chứng sinh"
    if doc_type == "identity":
        return "Căn cước công dân"
    if doc_type == "marital_status_evidence":
        return "Quyết định ly hôn" if "ly hon" in value else "Giấy chứng tử"
    if doc_type == "birth_declaration":
        return "Tờ khai đăng ký khai sinh bản giấy"
    if doc_type == "recognition_declaration":
        return "Tờ khai đăng ký nhận cha, mẹ, con bản giấy"
    if doc_type == "witness_commitment":
        return "Văn bản cam đoan quan hệ cha, mẹ, con"
    if doc_type == "authorization":
        return "Văn bản ủy quyền"
    return ""


def _truncate_text(text: str, limit: int = 4000) -> str:
    value = re.sub(r"\s+", " ", text or "").strip()
    return value if len(value) <= limit else value[:limit] + "..."


def _normalize_llm_type(value: Any) -> str:
    raw = str(value or "").strip()
    if raw in _ALLOWED_LLM_TYPES:
        return raw
    value_folded = fold(raw)
    if _has(value_folded, "adn", "dna", "huyet thong", "relationship"):
        return "relationship_proof"
    if _has(value_folded, "chung sinh", "birth proof"):
        return "birth_proof"
    if _has(value_folded, "to khai khai sinh", "birth declaration"):
        return "birth_declaration"
    if _has(value_folded, "to khai nhan cha", "recognition declaration"):
        return "recognition_declaration"
    if _has(value_folded, "can cuoc", "cccd", "cmnd", "ho chieu", "identity"):
        return "identity"
    if _has(value_folded, "chung tu", "khai tu", "ly hon", "marital"):
        return "marital_status_evidence"
    if _has(value_folded, "cam doan", "lam chung", "witness"):
        return "witness_commitment"
    if _has(value_folded, "uy quyen", "authorization"):
        return "authorization"
    return "other"


def _specific_llm_name(value: Any) -> str:
    name = re.sub(r"\s+", " ", str(value or "")).strip(" ;,.")
    folded = fold(name)
    is_generic = any(folded == item or folded.startswith(item + " ") for item in _GENERIC_NAMES)
    return "" if not name or is_generic else name


def _filename_fallback(name: str, index: int) -> str:
    stem = Path(name or "").stem.strip() or f"File {index + 1}"
    return normalize_document_name(name, stem)


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    if not documents:
        return {}
    payload = [
        {
            "index": item["index"],
            "fileName": item.get("fileName", ""),
            "text": _truncate_text(str(item.get("text") or "")),
        }
        for item in documents
    ]
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(payload)},
    ]
    raw = await client.chat(messages, max_tokens=900, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    parsed_docs = parsed.get("documents", []) or []
    valid_indexes = {item["index"] for item in documents}
    result: dict[int, dict[str, str]] = {}
    for position, item in enumerate(parsed_docs):
        try:
            index = int(item.get("index"))
        except (TypeError, ValueError):
            index = documents[position]["index"] if position < len(documents) else -1
        if index not in valid_indexes:
            continue
        result[index] = {
            "type": _normalize_llm_type(item.get("docType") or item.get("type")),
            "documentName": _specific_llm_name(item.get("documentName") or item.get("title")),
        }
    return result


def build_plan_items(
    files: list[dict[str, Any]],
    ocr_results: list[dict],
    llm_types: dict[int, dict[str, str]] | None = None,
) -> tuple[list[dict], list[dict]]:
    llm_types = llm_types or {}
    by_name = {item.get("name"): item for item in ocr_results}
    attachments: list[dict] = []
    classified: list[dict] = []
    used_new: set[str] = set()

    for index, file in enumerate(files):
        name = str(file.get("name") or f"file-{index + 1}")
        text = str(by_name.get(name, {}).get("text") or "")
        classification_text = f"{name}\n{text}"
        rule_type = _doc_type(classification_text)
        llm_result = llm_types.get(index) or {}
        llm_type = _normalize_llm_type(llm_result.get("type")) if llm_result else ""
        doc_type = rule_type if rule_type != "other" else (llm_type or "other")
        label = _label(doc_type, classification_text)
        if rule_type == "other":
            label = _specific_llm_name(llm_result.get("documentName")) or label
        if not label:
            # LLM lỗi/không trả tên: giữ tên file, tuyệt đối không sinh nhãn tài liệu chung.
            label = _filename_fallback(name, index)

        if doc_type == "birth_proof":
            target, component_index, component_name = "existing", 3, _BIRTH_ROW
        elif doc_type == "relationship_proof":
            # File gộp ADN + CCCD vẫn đi STT4; không nhân bản cùng file sang thành phần khác.
            target, component_index, component_name = "existing", 4, _RELATIONSHIP_ROW
        elif doc_type == "witness_commitment":
            target, component_index, component_name = "existing", 5, _WITNESS_ROW
        else:
            target, component_index = "new", None
            component_name = normalize_document_name(label, _filename_fallback(name, index))
            base = component_name
            suffix = 2
            while fold(component_name) in used_new:
                component_name = f"{base} {suffix}"[:50]
                suffix += 1
            used_new.add(fold(component_name))

        item = {
            "fileIndex": index,
            "fileName": name,
            "documentName": label,
            "componentName": component_name,
            "target": target,
            "componentIndex": component_index,
            "needsAddComponent": target == "new",
            "detectedType": label,
        }
        attachments.append(item)
        classified.append({
            "fileName": name,
            "docType": doc_type,
            "documentName": label,
            "target": target,
            "componentIndex": component_index,
            "source": "rule" if rule_type != "other" else ("llm" if llm_result else "filename_fallback"),
        })
    return attachments, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    ocr_files = [item for item in raw_files if item.get("type") in _OCR_TYPES]
    errors: list[str] = []

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    fallback_docs = []
    for index, file in enumerate(raw_files):
        name = str(file.get("name") or f"file-{index + 1}")
        text = str(by_name.get(name, {}).get("text") or "")
        if _doc_type(f"{name}\n{text}") == "other":
            fallback_docs.append({"index": index, "fileName": name, "text": text})

    llm_started = time.monotonic()
    llm_types: dict[int, dict[str, str]] = {}
    if fallback_docs:
        try:
            llm_types = await _classify_with_llm(fallback_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
        for item in fallback_docs:
            detected = llm_types.get(item["index"]) or {}
            if not detected or (
                _normalize_llm_type(detected.get("type")) == "other"
                and not _specific_llm_name(detected.get("documentName"))
            ):
                errors.append(f"attachment_agent: chưa đặt được tên cụ thể cho {item['fileName']}")
    llm_ms = int((time.monotonic() - llm_started) * 1000)

    attachments, classified = build_plan_items(raw_files, ocr_results, llm_types)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [item["name"] for item in raw_files],
            "ocrDocuments": [item.get("name") for item in ocr_results if item.get("text")],
            "llmDocuments": [raw_files[item["index"]]["name"] for item in fallback_docs],
            "sessionId": (session or {}).get("request_id"),
            "classified": classified,
            "skippedOcr": [item["name"] for item in raw_files if item.get("type") not in _OCR_TYPES],
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "errors": errors,
    }
