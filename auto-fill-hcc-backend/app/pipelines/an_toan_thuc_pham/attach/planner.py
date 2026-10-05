"""Đính kèm cho thủ tục cấp Giấy chứng nhận cơ sở đủ điều kiện ATTP.

Trang thành phần hồ sơ của thủ tục này gom toàn bộ giấy tờ vào một dòng
"A. Thành phần hồ sơ..." nên mọi file vẫn vào cùng một slot. Mỗi file được upload
lặp lại vào cùng slot vì cổng có thể chỉ nhận một file cho mỗi lần bấm
"Chọn tệp tin".

OCR + LLM (prompt.py) chỉ để đặt tên tài liệu theo loại giấy — extension đặt tên tệp tải lên
theo documentName. LLM không trả loại được thì giữ tên file gốc như trước, không bỏ file nào.
"""

import re
import time
from pathlib import Path
from typing import Any

from app.config import settings
from app.pipelines._shared import fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.an_toan_thuc_pham.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_SLOT_KEY = "attp_dossier"
_SLOT_INDEX = 0
_SLOT_NAME = (
    "A. Thành phần hồ sơ: Đơn đề nghị cấp Giấy chứng nhận; Giấy chứng nhận đăng ký kinh doanh/"
    "doanh nghiệp; bản thuyết minh cơ sở vật chất, trang thiết bị; giấy xác nhận đủ sức khỏe; "
    "danh sách người sản xuất/kinh doanh đã tập huấn kiến thức an toàn thực phẩm"
)

_OTHER = "other"
# Tên tài liệu theo loại giấy (≤50 ký tự, không ngoặc, không dấu chấm — ràng buộc ô tên của cổng).
_LABELS = {
    "don_de_nghi": "Đơn đề nghị cấp Giấy chứng nhận ATTP",
    "gcn_dkkd": "Giấy chứng nhận đăng ký kinh doanh",
    "thuyet_minh": "Bản thuyết minh cơ sở vật chất trang thiết bị",
    "suc_khoe": "Giấy xác nhận đủ sức khỏe",
    "tap_huan": "Danh sách người đã tập huấn kiến thức ATTP",
}
_ALLOWED_DOC_TYPES = set(_LABELS) | {_OTHER}


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def _clean_title(value: str) -> str:
    text = re.sub(r"[()\[\]{}.]+", " ", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:50].strip()


def _document_name(file_name: str) -> str:
    stem = Path(file_name or "").stem.strip()
    return stem[:80] or "Tài liệu hồ sơ an toàn thực phẩm"


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


def _build_item(file: dict, index: int, document_name: str, detected_type: str) -> dict:
    file_name = str(file.get("name") or f"file-{index + 1}")
    return {
        "fileIndex": index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": _SLOT_NAME,
        "target": "fixed-slot",
        "componentIndex": 1,
        "needsAddComponent": False,
        "detectedType": detected_type,
        "slotKey": _SLOT_KEY,
        "slotIndex": _SLOT_INDEX,
        "slotName": _SLOT_NAME,
        "repeatUpload": True,
    }


def build_plan_items(
    files: list[dict], llm_types: dict[int, dict[str, str]] | None = None,
) -> tuple[list[dict], list[dict]]:
    llm_types = llm_types or {}
    attachments: list[dict] = []
    classified: list[dict] = []
    # Cùng một dòng nhận nhiều tệp: hai tệp cùng loại giấy phải khác tên để cán bộ phân biệt trên cổng.
    seen: dict[str, int] = {}
    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        detected = llm_types.get(idx) or {}
        doc_type = detected.get("docType") or _OTHER
        name = _LABELS.get(doc_type) or detected.get("title") or ""
        source = "llm" if name else "fileName"
        if not name:
            name = _document_name(file_name)
        else:
            key = fold(name)
            seen[key] = seen.get(key, 0) + 1
            if seen[key] > 1:
                name = f"{name} {seen[key]}"
        detected_type = _LABELS.get(doc_type, "Tài liệu thành phần hồ sơ an toàn thực phẩm")
        item = _build_item(file, idx, name, detected_type)
        attachments.append(item)
        classified.append({
            "fileName": file_name,
            "docType": doc_type,
            "slotKey": item["slotKey"],
            "slotIndex": item["slotIndex"],
            "documentName": name,
            "source": source,
        })
    return attachments, classified


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    _ = options or {}
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

    attachments, classified = build_plan_items(raw_files, llm_types)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "sessionId": (session or {}).get("request_id"),
            "classified": classified,
            "skippedOcr": [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES],
            "slots": [
                {
                    "slotKey": _SLOT_KEY,
                    "slotIndex": _SLOT_INDEX,
                    "slotName": _SLOT_NAME,
                }
            ],
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
