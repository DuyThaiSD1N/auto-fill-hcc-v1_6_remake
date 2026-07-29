"""Đính kèm cho thủ tục "Chứng thực di chúc".

Bảng thành phần hồ sơ:
  STT1 - Dự thảo di chúc. Nếu có CCCD/giấy tờ tùy thân liên quan, BE yêu cầu FE gộp vào cùng PDF này.
  STT2 - Giấy chứng nhận quyền sở hữu/quyền sử dụng hoặc giấy tờ thay thế đối với tài sản.
  CCCD/giấy tờ tùy thân chỉ thêm mới thành phần hồ sơ khi không có file dự thảo di chúc để gộp.

Tài liệu ngoài ba nhóm trên bị bỏ qua kèm cảnh báo để người dùng xử lý thủ công.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold, normalize_document_name
from app.pipelines.chung_thuc_di_chuc.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DOC_WILL_DRAFT = "will_draft"
_DOC_ASSET = "asset_ownership_proof"
_DOC_IDENTITY = "identity_document"
_DOC_OTHER = "other"
_ALLOWED_TYPES = {_DOC_WILL_DRAFT, _DOC_ASSET, _DOC_IDENTITY, _DOC_OTHER}

_WILL_LABEL = "Dự thảo di chúc"
_ASSET_LABEL = "Giấy tờ sở hữu tài sản"
_IDENTITY_LABEL = "Căn cước công dân"

_ROW_1_COMPONENT = "+ Dự thảo di chúc;"
_ROW_2_COMPONENT = (
    "Bản chính hoặc bản sao có chứng thực hoặc bản sao điện tử được chứng thực từ bản chính "
    "của giấy chứng nhận quyền sở hữu, quyền sử dụng hoặc giấy tờ thay thế"
)


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _normalize_type(value: str) -> str:
    raw = str(value or "").strip()
    if raw in _ALLOWED_TYPES:
        return raw
    text = fold(raw)
    if not text or text == "other":
        return _DOC_OTHER
    if "will" in text or "di chuc" in text:
        return _DOC_WILL_DRAFT
    if "asset" in text or "ownership" in text or "tai san" in text or "quyen su dung" in text:
        return _DOC_ASSET
    if "identity" in text or "cccd" in text or "can cuoc" in text or "cmnd" in text:
        return _DOC_IDENTITY
    return _DOC_OTHER


def _rule_doc_type(text: str) -> str:
    haystack = fold(text)
    if not haystack:
        return ""

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
    has_will = any(
        marker in haystack
        for marker in (
            "du thao di chuc",
            "di chuc",
            "nguoi lap di chuc",
            "nguoi thua ke",
            "di san",
            "dinh doat tai san",
            "phan tai san",
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

    # Di chúc thường mô tả sổ đỏ, đăng ký xe, tài sản tiết kiệm trong phần di sản.
    # Khi có tín hiệu di chúc, vẫn ưu tiên dòng 1 thay vì coi đó là giấy tờ tài sản.
    if has_will:
        return _DOC_WILL_DRAFT
    if has_asset:
        return _DOC_ASSET
    if has_identity:
        return _DOC_IDENTITY
    return ""


def _label_for_type(doc_type: str, title: str = "") -> str:
    title = str(title or "").strip()
    folded = fold(title)
    if doc_type == _DOC_ASSET:
        if "dang ky xe" in folded:
            return "Đăng ký xe"
        if "quyen su dung dat" in folded or "so do" in folded or "so hong" in folded:
            return "Giấy chứng nhận quyền sử dụng đất"
        if "quyen so huu nha" in folded:
            return "Giấy chứng nhận quyền sở hữu nhà ở"
        return title or _ASSET_LABEL
    if doc_type == _DOC_WILL_DRAFT:
        return title or _WILL_LABEL
    if doc_type == _DOC_IDENTITY:
        return title or _IDENTITY_LABEL
    return title or "Tài liệu chứng thực di chúc"


def _route_for_type(doc_type: str) -> tuple[str, int | None, str] | None:
    if doc_type == _DOC_WILL_DRAFT:
        return "existing", 1, _ROW_1_COMPONENT
    if doc_type == _DOC_ASSET:
        return "existing", 2, _ROW_2_COMPONENT
    if doc_type == _DOC_IDENTITY:
        return "new", None, ""
    return None


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

    docs = [
        {"index": item["index"], "text": _truncate_text(item.get("text", ""))}
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


def _build_item(
    file: dict,
    idx: int,
    doc_type: str,
    title: str,
    used_names: set[str],
    source_indexes: list[int] | None = None,
) -> dict | None:
    route = _route_for_type(doc_type)
    if not route:
        return None
    target, component_index, component_name = route
    document_name = _unique_document_name(_label_for_type(doc_type, title), used_names, _label_for_type(doc_type))
    component_name = component_name if target == "existing" else document_name
    source_indexes = list(source_indexes or [idx])
    return {
        "fileIndex": idx,
        "sourceFileIndexes": source_indexes,
        "fileName": str(file.get("name") or f"file-{idx + 1}"),
        "documentName": document_name,
        "componentName": component_name,
        "target": target,
        "componentIndex": component_index,
        "needsAddComponent": target == "new",
        "detectedType": document_name,
    }


def _safe_title_for_type(doc_type: str, title: str) -> str:
    title = str(title or "").strip()
    if doc_type == _DOC_WILL_DRAFT and "di chuc" not in fold(title):
        return ""
    return title


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, dict[str, str]] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    ocr_by_name = {item.get("name"): item for item in ocr_results}
    used_names: set[str] = set()
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    resolved: list[dict] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = str(ocr_by_name.get(file_name, {}).get("text") or "")
        rule_type = _rule_doc_type(text)
        detected = llm_types.get(idx) or {}
        llm_type = detected.get("type") or ""
        doc_type = rule_type or llm_type or _DOC_OTHER
        if doc_type not in _ALLOWED_TYPES:
            doc_type = _DOC_OTHER

        title = _safe_title_for_type(doc_type, detected.get("title", ""))
        if rule_type and llm_type and rule_type != llm_type:
            title = ""

        resolved.append({
            "idx": idx,
            "file": file,
            "fileName": file_name,
            "docType": doc_type,
            "title": title,
            "ruleType": rule_type,
            "llmType": llm_type,
        })

    will_entries = [entry for entry in resolved if entry["docType"] == _DOC_WILL_DRAFT]
    identity_indexes = [entry["idx"] for entry in resolved if entry["docType"] == _DOC_IDENTITY]
    will_merge_index = will_entries[0]["idx"] if will_entries and identity_indexes else None

    for entry in resolved:
        idx = entry["idx"]
        file = entry["file"]
        file_name = entry["fileName"]
        doc_type = entry["docType"]
        title = entry["title"]
        rule_type = entry["ruleType"]
        llm_type = entry["llmType"]

        if will_merge_index is not None and doc_type == _DOC_IDENTITY:
            classified.append({
                "fileName": file_name,
                "type": doc_type,
                "title": _IDENTITY_LABEL,
                "target": "merged",
                "componentIndex": 1,
                "mergedIntoFileIndex": will_merge_index,
                "source": "rule" if rule_type else ("llm" if llm_type else "default"),
            })
            continue

        source_indexes = [idx]
        if will_merge_index is not None and idx == will_merge_index:
            source_indexes = [idx] + [i for i in identity_indexes if i != idx]
            title = "Dự thảo di chúc kèm căn cước công dân"

        item = _build_item(file, idx, doc_type, title, used_names, source_indexes)
        if not item:
            warnings.append(f"Không xác định được giấy tờ thuộc 2 dòng hồ sơ di chúc cho file '{file_name}' — đã bỏ qua.")
            classified.append({"fileName": file_name, "type": _DOC_OTHER, "source": "unknown"})
            continue

        attachments.append(item)
        classified.append({
            "fileName": file_name,
            "type": doc_type,
            "title": item["documentName"],
            "target": item["target"],
            "componentIndex": item["componentIndex"],
            "source": "rule" if rule_type else ("llm" if llm_type else "default"),
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
