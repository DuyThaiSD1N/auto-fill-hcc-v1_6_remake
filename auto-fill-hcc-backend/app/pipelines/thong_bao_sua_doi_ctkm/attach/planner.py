"""Đính kèm bước "Thành phần hồ sơ" cho "Thông báo sửa đổi, bổ sung nội dung chương trình khuyến mại"
(cổng Bộ Công Thương — bảng Angular, engine FE `attp-row`).

Cổng chỉ có MỘT dòng thành phần: Thông báo theo Mẫu 06 (Bản chính). Mọi tệp tải lên — kể cả CCCD của
người nộp — đều đính vào dòng đó (định tuyến tất định, không tệp nào rơi).
OCR + LLM (prompt.py) chỉ để đặt tên tài liệu theo loại giấy: engine attp-row đặt tên tệp tải lên theo
`documentName`. LLM không trả loại được → giữ TÊN TỆP GỐC.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.thong_bao_sua_doi_ctkm.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_ROW = {
    # Đoạn nguyên văn đặc trưng của dòng (FE khớp substring đã fold dấu vào cột tên giấy tờ).
    "componentName": "Thông báo sửa đổi, bổ sung nội dung chương trình",
    "loaiBan": "Bản chính",
}

_OTHER = "other"
# Tên tài liệu theo loại (≤50 ký tự, không ngoặc, không dấu chấm). Cài đặt tài khoản tắt "đổi tên tệp"
# thì FE tự giữ tên gốc.
_LABELS = {
    "thong_bao_sua_doi": "Thông báo sửa đổi, bổ sung chương trình khuyến mại",
    "cccd": "Căn cước công dân",
}
_ALLOWED_DOC_TYPES = set(_LABELS) | {_OTHER}


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def _clean_title(value: str) -> str:
    text = re.sub(r"[()\[\]{}.]+", " ", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:50].strip()


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    if not documents:
        return {}
    docs = [{"index": item["index"], "text": _truncate_text(item.get("text", ""))} for item in documents]
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(docs)},
    ]
    raw = await client.chat(
        messages, max_tokens=max(500, 120 * len(docs)), enable_thinking=settings.agent_reasoning,
    )
    parsed = client.extract_json_block(raw)
    valid = {item["index"] for item in documents}
    out: dict[int, dict[str, str]] = {}
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        if idx not in valid:
            continue
        doc_type = str(item.get("docType") or item.get("type") or "").strip().lower()
        out[idx] = {
            "docType": doc_type if doc_type in _ALLOWED_DOC_TYPES else _OTHER,
            "title": _clean_title(item.get("title") or ""),
        }
    return out


def build_plan_items(files: list[dict], llm_types: dict[int, dict[str, str]] | None = None) -> list[dict]:
    llm_types = llm_types or {}
    items: list[dict] = []
    # Mọi tệp vào cùng MỘT dòng: hai tệp cùng loại (vd hai mặt CCCD) phải khác tên để cán bộ phân biệt.
    name_counts: dict[str, int] = {}
    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        detected = llm_types.get(index) or {}
        doc_type = detected.get("docType") or _OTHER
        document_name = _LABELS.get(doc_type) or detected.get("title") or ""
        if document_name:
            name_counts[document_name] = name_counts.get(document_name, 0) + 1
            if name_counts[document_name] > 1:
                document_name = f"{document_name} {name_counts[document_name]}"
        else:
            document_name = file_name
        items.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": document_name,
            "componentName": _ROW["componentName"],
            "loaiBan": _ROW["loaiBan"],
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": doc_type if index in llm_types else "thong_bao_sua_doi_ctkm",
        })
    return items


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_indexes = [idx for idx, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]
    ocr_files = [raw_files[idx] for idx in ocr_indexes]

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    # ocr_per_file trả đúng thứ tự tệp đưa vào → ghép theo vị trí, không theo tên (hai ảnh có thể trùng tên).
    llm_docs: list[dict[str, Any]] = []
    for idx, result in zip(ocr_indexes, ocr_results):
        text = str(result.get("text") or "")
        if text.strip():
            llm_docs.append({"index": idx, "text": text})

    t1 = time.monotonic()
    llm_types: dict[int, dict[str, str]] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments = build_plan_items(raw_files, llm_types)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "classified": [
                {
                    "fileName": item["fileName"],
                    "docType": item["detectedType"],
                    "documentName": item["documentName"],
                    "source": "llm" if item["fileIndex"] in llm_types else "single-row",
                }
                for item in attachments
            ],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "ocr_text": join_ocr_documents(ocr_results),
        "llm_output": {str(idx): val for idx, val in llm_types.items()},
        "errors": errors,
    }
