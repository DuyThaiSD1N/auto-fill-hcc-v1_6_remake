"""Đính kèm cho thủ tục chứng thực văn bản phân chia di sản.

Form có 2 dòng cố định:
  STT1 - Giấy tờ sở hữu/quyền sử dụng tài sản. Theo mẫu nghiệp vụ, gộp thêm giấy chứng tử,
         phiếu đo đạc và CCCD người hưởng di sản vào cùng PDF dòng này.
  STT2 - Dự thảo/văn bản thỏa thuận phân chia di sản thừa kế.

Không thêm thành phần hồ sơ mới.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold, normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.chung_thuc_phan_chia_di_san.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DOC_DIVISION_DRAFT = "division_draft"
_DOC_ASSET = "asset_ownership_proof"
_DOC_DEATH = "death_proof"
_DOC_SURVEY = "survey_adjustment"
_DOC_IDENTITY = "identity_document"
_DOC_OTHER = "other"
_ALLOWED_TYPES = {
    _DOC_DIVISION_DRAFT,
    _DOC_ASSET,
    _DOC_DEATH,
    _DOC_SURVEY,
    _DOC_IDENTITY,
    _DOC_OTHER,
}
_ROW_1_TYPES = {
    _DOC_ASSET,
    _DOC_DEATH,
    _DOC_SURVEY,
    _DOC_IDENTITY,
}

_ROW_1_COMPONENT = (
    "Bản chính hoặc bản sao có chứng thực hoặc bản sao điện tử được chứng thực "
    "từ bản chính của giấy chứng nhận quyền sở hữu, quyền sử dụng"
)
_ROW_2_COMPONENT = "Dự thảo văn bản phân chia di sản"

_ROW_1_LABEL = "Giấy tờ kèm theo hồ sơ phân chia di sản"
_DRAFT_LABEL = "Dự thảo văn bản phân chia di sản"
_ASSET_LABEL = "Giấy chứng nhận quyền sử dụng đất"
_DEATH_LABEL = "Giấy chứng tử hoặc trích lục khai tử"
_SURVEY_LABEL = "Phiếu đo đạc chỉnh lý thửa đất"
_IDENTITY_LABEL = "Căn cước công dân"


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _normalize_type(value: str) -> str:
    raw = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    if raw in _ALLOWED_TYPES:
        return raw
    text = fold(raw)
    if not text or text == "other":
        return _DOC_OTHER
    if "draft" in text or "du thao" in text or "phan chia di san" in text:
        return _DOC_DIVISION_DRAFT
    if "asset" in text or "ownership" in text or "quyen su dung" in text or "tai san" in text:
        return _DOC_ASSET
    if "death" in text or "khai tu" in text or "chung tu" in text:
        return _DOC_DEATH
    if "inheritance" in text or "thua ke" in text or "thoa thuan" in text:
        return _DOC_DIVISION_DRAFT
    if "survey" in text or "do dac" in text or "chinh ly" in text or "dia chinh" in text:
        return _DOC_SURVEY
    if "identity" in text or "cccd" in text or "can cuoc" in text or "cmnd" in text:
        return _DOC_IDENTITY
    return _DOC_OTHER


def _rule_doc_type(text: str) -> str:
    haystack = fold(text)
    if not haystack:
        return ""

    has_division_draft = any(
        marker in haystack
        for marker in (
            "du thao van ban phan chia di san",
            "du thao van ban thoa thuan phan chia di san",
            "du thao phan chia di san",
            "van ban thoa thuan phan chia di san thua ke",
            "thoa thuan phan chia di san thua ke",
            "van ban thoa thuan phan chia di san",
        )
    ) or (
        "du thao" in haystack and "phan chia di san" in haystack
    ) or (
        "van ban phan chia di san" in haystack
    )
    has_survey = any(
        marker in haystack
        for marker in (
            "phieu do dac",
            "chinh ly thua dat",
            "trich do",
            "ban trich do",
            "dia chinh",
        )
    )
    has_death = any(
        marker in haystack
        for marker in (
            "giay chung tu",
            "trich luc khai tu",
            "khai tu",
            "ngay chet",
            "ngay mat",
            "da chet",
        )
    )
    has_asset = any(
        marker in haystack
        for marker in (
            "giay chung nhan quyen su dung dat",
            "quyen so huu nha",
            "quyen so huu tai san",
            "giay chung nhan dang ky xe",
            "dang ky xe",
            "so do",
            "so hong",
            "thua dat",
            "to ban do",
            "nguoi su dung dat",
            "chu so huu tai san",
        )
    )
    has_identity = any(
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
    )

    if has_division_draft:
        return _DOC_DIVISION_DRAFT
    if has_survey:
        return _DOC_SURVEY
    if has_death:
        return _DOC_DEATH
    if has_asset:
        return _DOC_ASSET
    if has_identity:
        return _DOC_IDENTITY
    return ""


def _label_for_type(doc_type: str, title: str = "") -> str:
    title = str(title or "").strip()
    folded = fold(title)
    if doc_type == _DOC_DIVISION_DRAFT:
        return title or _DRAFT_LABEL
    if doc_type == _DOC_ASSET:
        if "dang ky xe" in folded:
            return "Đăng ký xe"
        if "quyen su dung dat" in folded or "so do" in folded or "so hong" in folded:
            return "Giấy chứng nhận quyền sử dụng đất"
        if "quyen so huu nha" in folded:
            return "Giấy chứng nhận quyền sở hữu nhà ở"
        return title or _ASSET_LABEL
    if doc_type == _DOC_DEATH:
        return title or _DEATH_LABEL
    if doc_type == _DOC_SURVEY:
        return title or _SURVEY_LABEL
    if doc_type == _DOC_IDENTITY:
        return title or _IDENTITY_LABEL
    return title or "Tài liệu phân chia di sản"


def _unique_document_name(base: str, used: set[str], fallback: str) -> str:
    normalized = normalize_document_name(base, fallback)
    key = fold(normalized)
    if key and key not in used:
        used.add(key)
        return normalized
    stem = normalized[:45].strip() or fallback[:45].strip()
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
            "type": _normalize_type(str(item.get("type") or item.get("docType") or "")),
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


def _build_group_item(
    files: list[dict],
    entries: list[dict],
    document_name: str,
    component_name: str,
    component_index: int,
    used_names: set[str],
) -> dict:
    source_indexes = [entry["idx"] for entry in sorted(entries, key=lambda item: item["idx"])]
    primary = source_indexes[0]
    normalized_name = _unique_document_name(document_name, used_names, document_name)
    return {
        "fileIndex": primary,
        "sourceFileIndexes": source_indexes,
        "fileName": str(files[primary].get("name") or f"file-{primary + 1}"),
        "documentName": normalized_name,
        "componentName": component_name,
        "target": "existing",
        "componentIndex": component_index,
        "needsAddComponent": False,
        "detectedType": normalized_name,
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, dict[str, str]] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    by_name = {item.get("name"): item for item in ocr_results}
    resolved: list[dict] = []
    warnings: list[str] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = str(by_name.get(file_name, {}).get("text") or "")
        rule_type = _rule_doc_type(text)
        detected = llm_types.get(idx) or {}
        llm_type = detected.get("type") or ""
        doc_type = rule_type or llm_type or _DOC_OTHER
        if doc_type not in _ALLOWED_TYPES:
            doc_type = _DOC_OTHER
        title = "" if rule_type and llm_type and rule_type != llm_type else detected.get("title", "")
        resolved.append({
            "idx": idx,
            "fileName": file_name,
            "docType": doc_type,
            "title": title,
            "source": "rule" if rule_type else ("llm" if llm_type else "default"),
        })

    row1_entries = [entry for entry in resolved if entry["docType"] in _ROW_1_TYPES]
    draft_entries = [entry for entry in resolved if entry["docType"] == _DOC_DIVISION_DRAFT]
    skipped_entries = [entry for entry in resolved if entry["docType"] == _DOC_OTHER]

    used_names: set[str] = set()
    attachments: list[dict] = []
    classified: list[dict] = []

    if row1_entries:
        row1_name = _ROW_1_LABEL if len(row1_entries) > 1 else _label_for_type(
            row1_entries[0]["docType"], row1_entries[0].get("title", "")
        )
        row1_item = _build_group_item(files, row1_entries, row1_name, _ROW_1_COMPONENT, 1, used_names)
        attachments.append(row1_item)
        row1_primary = row1_item["fileIndex"]
        for entry in row1_entries:
            classified.append({
                "fileName": entry["fileName"],
                "type": entry["docType"],
                "title": _label_for_type(entry["docType"], entry.get("title", "")),
                "target": "existing",
                "componentIndex": 1,
                "mergedIntoFileIndex": row1_primary,
                "source": entry["source"],
            })

    if draft_entries:
        draft_item = _build_group_item(files, draft_entries, _DRAFT_LABEL, _ROW_2_COMPONENT, 2, used_names)
        attachments.append(draft_item)
        draft_primary = draft_item["fileIndex"]
        for entry in draft_entries:
            classified.append({
                "fileName": entry["fileName"],
                "type": entry["docType"],
                "title": _DRAFT_LABEL,
                "target": "existing",
                "componentIndex": 2,
                "mergedIntoFileIndex": draft_primary,
                "source": entry["source"],
            })

    for entry in skipped_entries:
        warnings.append(
            f"Không xác định được giấy tờ thuộc 2 dòng hồ sơ phân chia di sản cho file '{entry['fileName']}' — đã bỏ qua."
        )
        classified.append({
            "fileName": entry["fileName"],
            "type": _DOC_OTHER,
            "title": "",
            "target": "skipped",
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
