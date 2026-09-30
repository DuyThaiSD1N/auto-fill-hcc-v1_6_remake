"""Đính kèm cho thủ tục bầu/công nhận tổ trưởng tổ hòa giải (cấp xã) — mã TTHC 2.000950.

Thủ tục chỉ có bước đính kèm. Bảng thành phần hồ sơ trên cổng:
  STT1 - Biên bản kiểm phiếu hoặc biên bản về kết quả biểu quyết về việc bầu tổ trưởng tổ hòa giải.
         Nhận Mẫu 04 (chính) và Mẫu 01 (biên bản bầu hòa giải viên — bổ trợ).
  STT2 - Văn bản đề nghị công nhận tổ trưởng tổ hòa giải.
         Nhận Mẫu 07 (chính), Mẫu 06 (danh sách đề nghị công nhận hòa giải viên) và Mẫu 10
         (tổng hợp danh sách hòa giải viên cơ sở) — bổ trợ.

Người dân hay scan nhiều mẫu vào chung một PDF, nên phân loại theo cả file. Nhiều file cùng một dòng
thì gộp vào một PDF (`sourceFileIndexes`, file chứa mẫu chính đứng đầu). Một file gộp cả biên bản lẫn
giấy đề nghị thì đính dòng 2; nếu không có file biên bản riêng thì đính thêm chính file đó vào dòng 1.
Không bấm "Thêm thành phần hồ sơ": tài liệu ngoài hai nhóm trên bị bỏ qua kèm cảnh báo.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold, normalize_document_name
from app.pipelines.bau_to_truong_to_hoa_giai.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DOC_MINUTES = "election_minutes"
_DOC_PROPOSAL = "proposal"
_DOC_COMBINED = "combined"
_DOC_OTHER = "other"
_ALLOWED_TYPES = {_DOC_MINUTES, _DOC_PROPOSAL, _DOC_COMBINED, _DOC_OTHER}

_MINUTES_LABEL = "Biên bản bầu tổ trưởng tổ hòa giải"
_PROPOSAL_LABEL = "Văn bản đề nghị công nhận tổ trưởng tổ hòa giải"

_ROW_1_COMPONENT = (
    "Biên bản kiểm phiếu hoặc biên bản về kết quả biểu quyết về việc bầu tổ trưởng tổ hòa giải."
)
_ROW_2_COMPONENT = "Văn bản đề nghị công nhận tổ trưởng tổ hòa giải."

# Tiêu đề biên bản Mẫu 01/04. Giấy đề nghị Mẫu 07 có câu "Căn cứ kết quả bầu tổ trưởng tổ hòa giải
# (có biên bản gửi kèm)" — không chứa các cụm dưới đây nên không bị nhận nhầm thành biên bản.
_MINUTES_MARKERS = (
    "bien ban ve ket qua bieu quyet",
    "bien ban kiem phieu",
    "ket qua bieu quyet bau to truong",
    "ket qua bieu quyet bau hoa giai vien",
    "to bau hoa giai vien",
)
# Tiêu đề Mẫu 06/07/10.
_PROPOSAL_MARKERS = (
    "giay de nghi",
    "van ban de nghi",
    "de nghi cong nhan to truong",
    "de nghi cong nhan hoa giai vien",
    "quyet dinh cong nhan to truong",
    "quyet dinh cong nhan hoa giai vien",
    "tong hop danh sach",
)
# Mẫu chính của từng dòng (Mẫu 04 / Mẫu 07) — dùng để xếp file lên đầu khi gộp.
_MINUTES_MAIN_MARKERS = ("bau to truong to hoa giai", "bieu quyet bau to truong")
_PROPOSAL_MAIN_MARKERS = ("cong nhan to truong to hoa giai",)


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
    if "combined" in text:
        return _DOC_COMBINED
    if "minutes" in text or "bien ban" in text:
        return _DOC_MINUTES
    if "proposal" in text or "de nghi" in text or "danh sach" in text:
        return _DOC_PROPOSAL
    return _DOC_OTHER


def _rule_doc_type(text: str) -> str:
    haystack = fold(text)
    if not haystack:
        return ""
    has_minutes = any(marker in haystack for marker in _MINUTES_MARKERS)
    has_proposal = any(marker in haystack for marker in _PROPOSAL_MARKERS)
    if has_minutes and has_proposal:
        return _DOC_COMBINED
    if has_minutes:
        return _DOC_MINUTES
    if has_proposal:
        return _DOC_PROPOSAL
    return ""


def _has_main_form(text: str, row: int) -> bool:
    haystack = fold(text)
    markers = _MINUTES_MAIN_MARKERS if row == 1 else _PROPOSAL_MAIN_MARKERS
    return any(marker in haystack for marker in markers)


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


def _order_main_first(entries: list[dict], row: int) -> list[dict]:
    main = [entry for entry in entries if _has_main_form(entry["text"], row)]
    rest = [entry for entry in entries if entry not in main]
    return main + rest


def _build_row_item(entries: list[dict], row: int, used_names: set[str]) -> dict:
    ordered = _order_main_first(entries, row)
    primary = ordered[0]
    label = _MINUTES_LABEL if row == 1 else _PROPOSAL_LABEL
    component_name = _ROW_1_COMPONENT if row == 1 else _ROW_2_COMPONENT
    document_name = _unique_document_name(label, used_names, label)
    return {
        "fileIndex": primary["idx"],
        "sourceFileIndexes": [entry["idx"] for entry in ordered],
        "fileName": primary["fileName"],
        "documentName": document_name,
        "componentName": component_name,
        "target": "existing",
        "componentIndex": row,
        "needsAddComponent": False,
        "detectedType": document_name,
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, dict[str, str]] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    ocr_by_name = {item.get("name"): item for item in ocr_results}
    used_names: set[str] = set()
    warnings: list[str] = []
    resolved: list[dict] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = str(ocr_by_name.get(file_name, {}).get("text") or "")
        rule_type = _rule_doc_type(text)
        llm_type = (llm_types.get(idx) or {}).get("type") or ""
        doc_type = rule_type or llm_type or _DOC_OTHER
        if doc_type not in _ALLOWED_TYPES:
            doc_type = _DOC_OTHER
        resolved.append({
            "idx": idx,
            "fileName": file_name,
            "text": text,
            "docType": doc_type,
            "source": "rule" if rule_type else ("llm" if llm_type else "default"),
        })

    minutes = [entry for entry in resolved if entry["docType"] == _DOC_MINUTES]
    proposals = [entry for entry in resolved if entry["docType"] == _DOC_PROPOSAL]
    combined = [entry for entry in resolved if entry["docType"] == _DOC_COMBINED]

    # File gộp cả hai nhóm: luôn thuộc dòng 2; chỉ đính thêm vào dòng 1 khi không có biên bản riêng.
    row_1 = minutes or list(combined)
    row_2 = proposals + combined

    attachments: list[dict] = []
    if row_1:
        attachments.append(_build_row_item(row_1, 1, used_names))
    else:
        warnings.append("Không tìm thấy biên bản bầu tổ trưởng tổ hòa giải (Mẫu 04) — dòng 1 để trống.")
    if row_2:
        attachments.append(_build_row_item(row_2, 2, used_names))
    else:
        warnings.append("Không tìm thấy văn bản đề nghị công nhận tổ trưởng tổ hòa giải (Mẫu 07) — dòng 2 để trống.")

    row_1_indexes = {entry["idx"] for entry in row_1}
    row_2_indexes = {entry["idx"] for entry in row_2}
    classified: list[dict] = []
    for entry in resolved:
        rows = [row for row, indexes in ((1, row_1_indexes), (2, row_2_indexes)) if entry["idx"] in indexes]
        if not rows:
            warnings.append(
                f"Không xác định được giấy tờ thuộc 2 dòng hồ sơ tổ hòa giải cho file '{entry['fileName']}' — đã bỏ qua."
            )
            classified.append({"fileName": entry["fileName"], "type": _DOC_OTHER, "source": "unknown"})
            continue
        classified.append({
            "fileName": entry["fileName"],
            "type": entry["docType"],
            "target": "existing",
            "componentIndex": rows[0],
            "componentIndexes": rows,
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
    # Chỉ hỏi LLM những file rule không nhận ra — hồ sơ đúng mẫu thì không tốn lượt gọi.
    llm_docs = [
        {
            "index": idx,
            "text": str(ocr_by_name.get(file.get("name"), {}).get("text") or ""),
        }
        for idx, file in enumerate(raw_files)
        if not _rule_doc_type(str(ocr_by_name.get(file.get("name"), {}).get("text") or ""))
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
