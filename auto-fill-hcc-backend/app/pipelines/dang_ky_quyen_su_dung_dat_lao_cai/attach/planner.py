"""Đính kèm cho [Lào Cai] Đăng ký biến động quyền sử dụng đất (1.115668).

LLM đọc OCR từng file → nhãn rút gọn (catalog.py). BE đổi nhãn thành:
  - ô fixed-slot của đúng dòng + đúng nhánh (FE khoanh vùng theo tiêu đề nhánh, tích checkbox dòng rồi bơm tệp);
  - hoặc một dòng "Giấy tờ khác" (target=new, tên = documentName) cho hóa đơn, tờ khai thuế, tài liệu khác.
CCCD không phải thành phần hồ sơ → bỏ qua kèm cảnh báo.

Nhánh: mặc định a) (chuyển nhượng, thừa kế, tặng cho…). Chỉ khi có biên bản tặng cho QSDĐ cho Nhà nước/cộng đồng
mới sang nhánh b); khi đó GCN gốc đi cùng dòng biên bản (tên dòng b ghi "…và bản gốc Giấy chứng nhận đã cấp"),
các giấy tờ thuộc dòng nhánh a) chuyển xuống "Giấy tờ khác".
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold, normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from . import catalog
from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
# Cổng Lào Cai: "Dung lượng tối đa là 6 Mb".
_MAX_FILE_BYTES = 6 * 1024 * 1024


def _truncate_text(text: str, limit: int = 3500) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def _data_url_size(data_url: str) -> int:
    payload = re.sub(r"\s+", "", str(data_url or "").partition(",")[2])
    if not payload:
        return 0
    padding = len(payload) - len(payload.rstrip("="))
    return max(0, (len(payload) * 3) // 4 - padding)


def _unique_document_name(base: str, used: set[str], fallback: str) -> str:
    value = normalize_document_name(base, fallback)
    key = fold(value)
    if key and key not in used:
        used.add(key)
        return value
    stem = value[:52].strip() or fallback[:52].strip()
    suffix = 2
    while True:
        candidate = f"{stem} {suffix}"[:60].strip()
        if fold(candidate) not in used:
            used.add(fold(candidate))
            return candidate
        suffix += 1


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    if not documents:
        return {}
    docs = [{"index": item["index"], "text": _truncate_text(item.get("text", ""))} for item in documents]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(docs)},
    ]
    raw = await client.chat(messages, max_tokens=900, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw) or {}
    parsed_docs = parsed.get("documents", []) or []

    def _coerce(item: dict) -> dict[str, str]:
        label = str(item.get("label") or "").strip()
        return {
            "label": label if catalog.is_valid(label) else "",
            "documentName": str(item.get("documentName") or "").strip(),
        }

    out: dict[int, dict[str, str]] = {}
    # LLM trả đúng số lượng → map theo THỨ TỰ (tránh lệch 0/1-based index).
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
    valid = {d["index"] for d in documents}
    for raw_idx, item in raw_items:
        idx = raw_idx - offset
        if idx in valid:
            out[idx] = _coerce(item)
    return out


def _fixed_item(entry: dict, row: tuple[str, int]) -> dict:
    slot = catalog.slot(row)
    return {
        "fileIndex": entry["idx"],
        "fileName": entry["fileName"],
        "documentName": entry["documentName"],
        "componentName": slot["slotName"],
        "target": "fixed-slot",
        "needsAddComponent": False,
        "detectedType": entry["label"],
        "slotKey": slot["slotKey"],
        "slotName": slot["slotName"],
        "sectionHeader": slot["sectionHeader"],
        "slotKeywords": slot["slotKeywords"],
        "tickRow": True,
    }


def _other_item(entry: dict) -> dict:
    # FE: target=new trên cổng có danh sách "Giấy tờ khác" → thêm dòng, gõ tên rồi chọn tệp.
    return {
        "fileIndex": entry["idx"],
        "fileName": entry["fileName"],
        "documentName": entry["documentName"],
        "componentName": entry["documentName"],
        "target": "new",
        "needsAddComponent": True,
        "detectedType": entry["label"],
        # Cổng iGate VNPT: bấm option "Chọn tệp tin" mở hộp thoại file của hệ điều hành → FE chỉ gán thẳng.
        "noChooserClick": True,
    }


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, dict[str, str]] | None = None,
) -> tuple[list[dict], list[str], list[dict], str]:
    llm_types = llm_types or {}
    entries: list[dict] = []
    used_names: set[str] = set()
    for position, file in enumerate(files):
        idx = int(file.get("_index", position))
        detected = llm_types.get(idx) or {}
        label = detected.get("label") or "khac"
        fallback = catalog.display_name(label)
        entries.append({
            "idx": idx,
            "fileName": str(file.get("name") or f"file-{idx + 1}"),
            "label": label,
            "documentName": _unique_document_name(detected.get("documentName") or fallback, used_names, fallback),
        })

    b_rows = sorted(
        row for row in (catalog.row_of(e["label"]) for e in entries) if row and row[0] == catalog.BRANCH_B
    )
    branch = catalog.BRANCH_B if b_rows else catalog.BRANCH_A

    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    for entry in entries:
        base = {"fileName": entry["fileName"], "label": entry["label"], "documentName": entry["documentName"]}
        label = entry["label"]
        if label in catalog.SKIPPED_LABELS:
            warnings.append(
                f"File '{entry['fileName']}' ({entry['documentName']}) không phải thành phần hồ sơ — đã bỏ qua."
            )
            classified.append({**base, "target": "skip", "reason": "not_a_component"})
            continue

        row = catalog.row_of(label)
        if branch == catalog.BRANCH_B and label == "gcn":
            row = b_rows[0]
        if row and row[0] == branch:
            item = _fixed_item(entry, row)
            attachments.append(item)
            classified.append({**base, "target": "fixed-slot", "slotKey": item["slotKey"]})
        else:
            attachments.append(_other_item(entry))
            classified.append({**base, "target": "new"})

    return attachments, warnings, classified, branch


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [
        {"name": file.name, "type": file.type, "dataUrl": file.dataUrl, "_index": idx}
        for idx, file in enumerate(files)
    ]
    valid_files: list[dict] = []
    for file in raw_files:
        size = _data_url_size(file.get("dataUrl", ""))
        if size > _MAX_FILE_BYTES:
            errors.append(f"File '{file['name']}' vượt quá 6 MB ({size / 1024 / 1024:.2f} MB) — đã bỏ qua.")
        else:
            valid_files.append(file)

    ocr_files = [file for file in valid_files if file.get("type") in _OCR_TYPES]
    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for result in ocr_results:
        if result.get("error"):
            errors.append(f"OCR {result.get('name')}: {result['error']}")

    ocr_by_name = {result.get("name"): result for result in ocr_results}
    llm_docs = [
        {"index": file["_index"], "text": str(ocr_by_name.get(file.get("name"), {}).get("text") or "")}
        for file in valid_files
    ]

    t1 = time.monotonic()
    llm_types: dict[int, dict[str, str]] = {}
    if any(doc["text"].strip() for doc in llm_docs):
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified, branch = build_plan_items(valid_files, llm_types)
    errors.extend(warnings)

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [file["name"] for file in raw_files],
            "ocrDocuments": [result.get("name") for result in ocr_results if result.get("text")],
            "llmDocuments": [file["name"] for file in valid_files],
            "sessionId": (session or {}).get("request_id"),
            "branch": branch,
            "classified": classified,
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "ocr_text": join_ocr_documents(ocr_results),
        "llm_output": {str(idx): value for idx, value in llm_types.items()},
        "errors": errors,
    }
