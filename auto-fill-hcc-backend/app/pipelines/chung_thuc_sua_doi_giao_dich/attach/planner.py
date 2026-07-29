"""Đính kèm cho thủ tục chứng thực sửa đổi, bổ sung, hủy bỏ giao dịch.

Bảng thành phần hồ sơ có 2 dòng cố định:
  STT1 - Dự thảo/văn bản sửa đổi, bổ sung, hủy bỏ giao dịch đã chứng thực và
         giấy tờ tài sản liên quan. Các file nhóm này cần gộp vào cùng PDF.
  STT2 - Giao dịch/hợp đồng cũ đã được chứng thực.

CCCD/căn cước của các bên, ủy quyền hoặc giấy tờ ngoài 2 dòng cố định sẽ thêm
thành phần hồ sơ mới.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold, normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.chung_thuc_sua_doi_giao_dich.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DOC_MODIFICATION_DRAFT = "modification_draft"
_DOC_CERTIFIED_TRANSACTION = "certified_transaction"
_DOC_ASSET = "asset_ownership_proof"
_DOC_IDENTITY = "identity_document"
_DOC_AUTHORIZATION = "authorization"
_DOC_OTHER = "other"
_ALLOWED_DOC_TYPES = {
    _DOC_MODIFICATION_DRAFT,
    _DOC_CERTIFIED_TRANSACTION,
    _DOC_ASSET,
    _DOC_IDENTITY,
    _DOC_AUTHORIZATION,
    _DOC_OTHER,
}
_ROW_1_TYPES = {_DOC_MODIFICATION_DRAFT, _DOC_ASSET}

_ROW_1_COMPONENT = (
    "Dự thảo giao dịch sửa đổi, bổ sung, hủy bỏ giao dịch đã được chứng thực. "
    "Trong trường hợp nội dung sửa đổi, bổ sung, hủy bỏ giao dịch có liên quan đến tài sản "
    "phải đăng ký quyền sở hữu, quyền sử dụng thì người yêu cầu chứng thực phải nộp bản sao "
    "giấy tờ chứng minh quyền sở hữu, quyền sử dụng hoặc giấy tờ thay thế"
)
_ROW_2_COMPONENT = "Giao dịch đã được chứng thực"

_ROW_1_LABEL = "Dự thảo sửa đổi giao dịch và giấy tờ tài sản"
_MODIFICATION_LABEL = "Dự thảo giao dịch sửa đổi bổ sung hủy bỏ"
_CERTIFIED_TRANSACTION_LABEL = "Giao dịch đã được chứng thực"
_ASSET_LABEL = "Giấy tờ chứng minh quyền sở hữu quyền sử dụng tài sản"
_IDENTITY_LABEL = "Căn cước công dân"
_AUTHORIZATION_LABEL = "Văn bản ủy quyền"
_OTHER_LABEL = "Tài liệu sửa đổi bổ sung hủy bỏ giao dịch"


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _has_any(haystack: str, needles: tuple[str, ...]) -> bool:
    return any(needle in haystack for needle in needles)


def _normalize_doc_type(value: str) -> str:
    raw = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    if raw in _ALLOWED_DOC_TYPES:
        return raw
    text = fold(raw)
    if not text or text == "other":
        return _DOC_OTHER
    if _has_any(text, ("modification", "amendment", "sua doi", "bo sung", "huy bo", "huy hop dong", "huy giao dich")):
        return _DOC_MODIFICATION_DRAFT
    if _has_any(text, ("certified", "old_transaction", "giao dich da duoc chung thuc", "hop dong da chung thuc")):
        return _DOC_CERTIFIED_TRANSACTION
    if _has_any(text, ("asset", "ownership", "quyen su dung", "quyen so huu", "tai san")):
        return _DOC_ASSET
    if _has_any(text, ("identity", "cccd", "can cuoc", "cmnd", "ho chieu")):
        return _DOC_IDENTITY
    if _has_any(text, ("authorization", "uy quyen")):
        return _DOC_AUTHORIZATION
    return _DOC_OTHER


def _is_modification_draft(haystack: str) -> bool:
    if not haystack:
        return False
    direct_markers = (
        "du thao giao dich sua doi",
        "du thao giao dich bo sung",
        "du thao giao dich huy bo",
        "du thao van ban sua doi",
        "du thao van ban bo sung",
        "du thao van ban huy bo",
        "van ban sua doi hop dong",
        "van ban bo sung hop dong",
        "van ban huy bo hop dong",
        "van ban huy hop dong",
        "van ban huy bo giao dich",
        "van ban huy giao dich",
        "thoa thuan huy bo hop dong",
        "thoa thuan huy hop dong",
        "thoa thuan huy bo giao dich",
        "thoa thuan huy giao dich",
        "sua doi hop dong",
        "bo sung hop dong",
        "huy bo hop dong",
        "huy hop dong",
        "huy bo giao dich",
        "huy giao dich",
        "cham dut hieu luc cua hop dong",
        "cham dut hieu luc hop dong",
        "phu luc hop dong",
    )
    if _has_any(haystack, direct_markers):
        return True
    return (
        "du thao" in haystack
        and _has_any(haystack, ("sua doi", "bo sung", "huy bo"))
        and _has_any(haystack, ("giao dich", "hop dong", "van ban"))
    )


def _is_certified_transaction(haystack: str) -> bool:
    if not haystack:
        return False
    if _has_any(
        haystack,
        (
            "giao dich da duoc chung thuc",
            "hop dong da duoc chung thuc",
            "hop dong da chung thuc",
            "van ban da duoc chung thuc",
        ),
    ):
        return True
    transaction_markers = (
        "hop dong tang cho",
        "hop dong chuyen nhuong",
        "hop dong mua ban",
        "hop dong the chap",
        "hop dong cho thue",
        "hop dong uy quyen",
        "van ban thoa thuan",
        "giao dich",
    )
    certification_markers = (
        "loi chung",
        "so chung thuc",
        "quyen so chung thuc",
        "chung thuc ngay",
        "nguoi thuc hien chung thuc",
        "duoc chung thuc tai",
        "duoc cong chung tai",
    )
    return _has_any(haystack, transaction_markers) and _has_any(haystack, certification_markers)


def _rule_doc_type(text: str) -> str:
    haystack = fold(text)
    if not haystack:
        return ""

    # Ưu tiên văn bản hiện tại cần chứng thực. Nó thường nhắc tới hợp đồng/giao dịch cũ
    # đã chứng thực, nên nếu xét certified_transaction trước sẽ route nhầm sang dòng 2.
    if _is_modification_draft(haystack):
        return _DOC_MODIFICATION_DRAFT

    # Hợp đồng/giao dịch cũ có thể chứa nhiều thông tin tài sản như thửa đất, QSDĐ.
    # Vì vậy nhận diện dòng 2 trước khi xét giấy tờ tài sản.
    if _is_certified_transaction(haystack):
        return _DOC_CERTIFIED_TRANSACTION

    if _has_any(
        haystack,
        (
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
        ),
    ):
        return _DOC_ASSET

    if _has_any(
        haystack,
        (
            "can cuoc cong dan",
            "the can cuoc",
            "chung minh nhan dan",
            "citizen identity card",
            "identity card",
            "so dinh danh ca nhan",
            "idvnm",
            "ho chieu",
        ),
    ):
        return _DOC_IDENTITY

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

    return ""


def _label_for_type(doc_type: str, title: str = "") -> str:
    title = str(title or "").strip()
    folded = fold(title)
    if doc_type == _DOC_MODIFICATION_DRAFT:
        if "huy bo hop dong" in folded or "huy bo giao dich" in folded:
            return title or "Văn bản hủy bỏ hợp đồng"
        if "sua doi" in folded:
            return title or "Văn bản sửa đổi giao dịch"
        if "bo sung" in folded or "phu luc" in folded:
            return title or "Văn bản bổ sung giao dịch"
        return title or _MODIFICATION_LABEL
    if doc_type == _DOC_CERTIFIED_TRANSACTION:
        return title or _CERTIFIED_TRANSACTION_LABEL
    if doc_type == _DOC_ASSET:
        if "dang ky xe" in folded:
            return "Đăng ký xe"
        if "quyen su dung dat" in folded or "so do" in folded or "so hong" in folded:
            return "Giấy chứng nhận quyền sử dụng đất"
        if "quyen so huu nha" in folded:
            return "Giấy chứng nhận quyền sở hữu nhà ở"
        return title or _ASSET_LABEL
    if doc_type == _DOC_IDENTITY:
        return title or _IDENTITY_LABEL
    if doc_type == _DOC_AUTHORIZATION:
        return title or _AUTHORIZATION_LABEL
    return title or _OTHER_LABEL


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
            "type": _normalize_doc_type(str(item.get("type") or item.get("docType") or "")),
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


def _build_new_item(files: list[dict], entry: dict, used_names: set[str]) -> dict:
    document_name = _unique_document_name(
        _label_for_type(entry["docType"], entry.get("title", "")),
        used_names,
        _OTHER_LABEL,
    )
    idx = entry["idx"]
    return {
        "fileIndex": idx,
        "sourceFileIndexes": None,
        "fileName": str(files[idx].get("name") or f"file-{idx + 1}"),
        "documentName": document_name,
        "componentName": document_name,
        "target": "new",
        "componentIndex": None,
        "needsAddComponent": True,
        "detectedType": document_name,
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
        if doc_type not in _ALLOWED_DOC_TYPES:
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
    row2_entries = [entry for entry in resolved if entry["docType"] == _DOC_CERTIFIED_TRANSACTION]
    new_entries = [entry for entry in resolved if entry["docType"] not in _ROW_1_TYPES | {_DOC_CERTIFIED_TRANSACTION}]

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
                "docType": entry["docType"],
                "documentName": _label_for_type(entry["docType"], entry.get("title", "")),
                "target": "existing",
                "componentIndex": 1,
                "mergedIntoFileIndex": row1_primary,
                "source": entry["source"],
            })

    if row2_entries:
        row2_item = _build_group_item(
            files,
            row2_entries,
            _CERTIFIED_TRANSACTION_LABEL,
            _ROW_2_COMPONENT,
            2,
            used_names,
        )
        attachments.append(row2_item)
        row2_primary = row2_item["fileIndex"]
        for entry in row2_entries:
            classified.append({
                "fileName": entry["fileName"],
                "docType": entry["docType"],
                "documentName": _CERTIFIED_TRANSACTION_LABEL,
                "target": "existing",
                "componentIndex": 2,
                "mergedIntoFileIndex": row2_primary,
                "source": entry["source"],
            })

    for entry in new_entries:
        item = _build_new_item(files, entry, used_names)
        attachments.append(item)
        classified.append({
            "fileName": entry["fileName"],
            "docType": entry["docType"],
            "documentName": item["documentName"],
            "target": "new",
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
