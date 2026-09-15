"""Đính kèm cho thủ tục chứng thực văn bản phân chia di sản.

Form có 2 dòng cố định + cho phép THÊM thành phần hồ sơ mới (như chứng thực bản sao/chữ ký):
  STT1 - Giấy tờ sở hữu/quyền sử dụng tài sản và giấy tờ bổ trợ (chứng tử, đo đạc, CCCD, ủy quyền).
  STT2 - Dự thảo/văn bản thỏa thuận phân chia di sản thừa kế.

Hai chế độ theo cài đặt ``options.splitDocuments`` (toggle global trong Cài đặt extension, chỉ tác động
thủ tục này — mặc định TẮT):
  - GỘP (mặc định, như cũ): mọi giấy tờ ngoài dự thảo GỘP CHUNG 1 PDF vào dòng 1; dự thảo vào dòng 2.
  - KHÔNG GỘP: mỗi giấy tờ đính riêng 1 dòng — giấy bổ trợ ĐẦU TIÊN vào dòng 1, các giấy sau mỗi cái
    THÊM 1 thành phần hồ sơ mới; dự thảo LUÔN ở dòng 2 cố định.

Phân loại tài liệu LLM-FIRST (không dùng rule keyword để quyết định type — chất lượng đặt ở prompt).
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
_DOC_AUTH = "authorization"
_DOC_OTHER = "other"
_ALLOWED_TYPES = {
    _DOC_DIVISION_DRAFT,
    _DOC_ASSET,
    _DOC_DEATH,
    _DOC_SURVEY,
    _DOC_IDENTITY,
    _DOC_AUTH,
    _DOC_OTHER,
}

_ROW_1_COMPONENT = (
    "Bản chính hoặc bản sao có chứng thực hoặc bản sao điện tử được chứng thực "
    "từ bản chính của giấy chứng nhận quyền sở hữu, quyền sử dụng"
)
_ROW_2_COMPONENT = "Dự thảo văn bản phân chia di sản"

_ROW_1_LABEL = "Giấy tờ kèm theo hồ sơ phân chia di sản"
_DRAFT_LABEL = "Dự thảo văn bản phân chia di sản"
_ASSET_LABEL = "Giấy chứng nhận quyền sử dụng đất"
_DEATH_LABEL = "Giấy chứng tử hoặc trích lục khai tử"
_SURVEY_LABEL = "Phiếu đo đạc chỉnh lý thửa đất"
_IDENTITY_LABEL = "Căn cước công dân"
_AUTH_LABEL = "Văn bản ủy quyền"
_OTHER_LABEL = "Tài liệu phân chia di sản"


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
    # Ủy quyền phải xét TRƯỚC asset: giấy ủy quyền hay nhắc số GCN QSDĐ trong nội dung.
    if "author" in text or "uy quyen" in text:
        return _DOC_AUTH
    if "draft" in text or "du thao" in text or "phan chia di san" in text:
        return _DOC_DIVISION_DRAFT
    if "inheritance" in text or "thua ke" in text or "thoa thuan" in text:
        return _DOC_DIVISION_DRAFT
    if "asset" in text or "ownership" in text or "quyen su dung" in text or "tai san" in text:
        return _DOC_ASSET
    if "death" in text or "khai tu" in text or "chung tu" in text:
        return _DOC_DEATH
    if "survey" in text or "do dac" in text or "chinh ly" in text or "dia chinh" in text:
        return _DOC_SURVEY
    if "identity" in text or "cccd" in text or "can cuoc" in text or "cmnd" in text:
        return _DOC_IDENTITY
    return _DOC_OTHER


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
    if doc_type == _DOC_AUTH:
        return title or _AUTH_LABEL
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
            "type": _normalize_type(str(item.get("type") or item.get("docType") or "")),
            "title": str(item.get("title") or item.get("documentName") or "").strip(),
        }

    out: dict[int, dict[str, str]] = {}
    # Bền vững nhất: LLM trả đúng số lượng → map THEO THỨ TỰ (bỏ field "index" hay lệch 0/1-based).
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
    """Gộp nhiều file vào 1 thành phần hồ sơ (mode GỘP)."""
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


def _build_single_item(
    files: list[dict],
    entry: dict,
    document_name: str,
    component_name: str | None,
    target: str,
    component_index: int | None,
    used_names: set[str],
) -> dict:
    """Đính 1 file vào 1 dòng riêng (mode KHÔNG GỘP): existing = ô sẵn, new = thêm thành phần."""
    idx = entry["idx"]
    normalized_name = _unique_document_name(document_name, used_names, document_name)
    return {
        "fileIndex": idx,
        "sourceFileIndexes": [idx],
        "fileName": str(files[idx].get("name") or f"file-{idx + 1}"),
        "documentName": normalized_name,
        # Thành phần mới: FE tạo dòng mới theo componentName = tên tài liệu (khớp nhãn đã fold dấu).
        "componentName": component_name if target == "existing" else normalized_name,
        "target": target,
        "componentIndex": component_index,
        "needsAddComponent": target == "new",
        "detectedType": normalized_name,
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, dict[str, str]] | None = None,
    split: bool = False,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    resolved: list[dict] = []
    warnings: list[str] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        detected = llm_types.get(idx) or {}
        # LLM-FIRST: type lấy thẳng từ LLM; không có/không hợp lệ → other (không suy luận bằng rule).
        doc_type = _normalize_type(detected.get("type") or "")
        resolved.append({
            "idx": idx,
            "fileName": file_name,
            "docType": doc_type,
            "title": str(detected.get("title") or "").strip(),
            "source": "llm" if detected.get("type") else "default",
        })

    if split:
        return _build_split_plan(files, resolved, warnings)
    return _build_merge_plan(files, resolved, warnings)


def _build_merge_plan(
    files: list[dict], resolved: list[dict], warnings: list[str],
) -> tuple[list[dict], list[str], list[dict]]:
    """GỘP (như cũ): mọi giấy tờ ngoài dự thảo gộp chung dòng 1; dự thảo gộp dòng 2."""
    draft_entries = [e for e in resolved if e["docType"] == _DOC_DIVISION_DRAFT]
    rest_entries = [e for e in resolved if e["docType"] != _DOC_DIVISION_DRAFT]

    used_names: set[str] = set()
    attachments: list[dict] = []
    classified: list[dict] = []

    if rest_entries:
        row1_name = _ROW_1_LABEL if len(rest_entries) > 1 else _label_for_type(
            rest_entries[0]["docType"], rest_entries[0]["title"]
        )
        row1_item = _build_group_item(files, rest_entries, row1_name, _ROW_1_COMPONENT, 1, used_names)
        attachments.append(row1_item)
        for entry in rest_entries:
            classified.append({
                "fileName": entry["fileName"],
                "type": entry["docType"],
                "title": _label_for_type(entry["docType"], entry["title"]),
                "target": "existing",
                "componentIndex": 1,
                "mergedIntoFileIndex": row1_item["fileIndex"],
                "source": entry["source"],
            })

    if draft_entries:
        draft_item = _build_group_item(files, draft_entries, _DRAFT_LABEL, _ROW_2_COMPONENT, 2, used_names)
        attachments.append(draft_item)
        for entry in draft_entries:
            classified.append({
                "fileName": entry["fileName"],
                "type": entry["docType"],
                "title": _DRAFT_LABEL,
                "target": "existing",
                "componentIndex": 2,
                "mergedIntoFileIndex": draft_item["fileIndex"],
                "source": entry["source"],
            })

    return attachments, warnings, classified


def _build_split_plan(
    files: list[dict], resolved: list[dict], warnings: list[str],
) -> tuple[list[dict], list[str], list[dict]]:
    """KHÔNG GỘP: mỗi giấy tờ 1 dòng. Dự thảo → dòng 2 cố định; giấy bổ trợ đầu tiên → dòng 1,
    còn lại mỗi cái thêm 1 thành phần hồ sơ mới. Giữ nguyên thứ tự file người dùng tải lên."""
    used_names: set[str] = set()
    attachments: list[dict] = []
    classified: list[dict] = []
    row1_used = False
    row2_used = False

    for entry in resolved:
        is_draft = entry["docType"] == _DOC_DIVISION_DRAFT
        if is_draft and not row2_used:
            # Dự thảo phân chia di sản → ô cố định dòng 2.
            row2_used = True
            item = _build_single_item(
                files, entry, _DRAFT_LABEL, _ROW_2_COMPONENT, "existing", 2, used_names
            )
        elif not is_draft and not row1_used:
            # Giấy bổ trợ ĐẦU TIÊN → ô cố định dòng 1.
            row1_used = True
            label = _label_for_type(entry["docType"], entry["title"])
            item = _build_single_item(
                files, entry, label, _ROW_1_COMPONENT, "existing", 1, used_names
            )
        else:
            # Mọi giấy tờ còn lại (kể cả dự thảo thứ 2 hiếm gặp) → thêm thành phần hồ sơ mới.
            label = _label_for_type(entry["docType"], entry["title"])
            item = _build_single_item(files, entry, label, None, "new", None, used_names)

        attachments.append(item)
        classified.append({
            "fileName": entry["fileName"],
            "type": entry["docType"],
            "title": item["documentName"],
            "target": item["target"],
            "componentIndex": item["componentIndex"],
            "mergedIntoFileIndex": entry["idx"],
            "source": entry["source"],
        })

    return attachments, warnings, classified


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    options = options or {}
    # Toggle Cài đặt extension (chỉ tác động thủ tục này): True = KHÔNG GỘP (mỗi giấy tờ 1 dòng).
    # Thiếu/không phải bool True (extension cũ) → GỘP như cũ ⇒ tương thích ngược.
    split = options.get("splitDocuments") is True
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

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types, split=split)
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
            "splitDocuments": split,
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
