"""Lập kế hoạch đính kèm "Cấp, cấp lại, chuyển đổi GCNKNCM, CCCM" (cổng Bộ Xây dựng dvc.moc — attp-row).

Bảng 4 dòng (mat-checkbox + rdo_File Bản chính/Bản sao + input file) → engine FE `attp-row`. componentName =
đoạn text đặc trưng của dòng (FE khớp substring đã fold dấu).
⚠ Dòng GCNKNCM/CCCM có NHÃN dạng dấu chấm trong DOM (không có text đặc trưng) → componentName best-effort
+ componentIndex; CẦN VERIFY trên trang thật. CCCD chỉ là nguồn điền → bỏ qua.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.cap_gcnkncm_cccm.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON = "don_de_nghi"
_GCNKNCM = "gcnkncm"
_SUC_KHOE = "giay_kham_suc_khoe"
_ANH = "anh_the"
_CCCD = "cccd"
_OTHER = "other"

# componentIndex 1-based theo thứ tự DOM THẬT (xác nhận trên trang live 2026-09-04):
# ① Sức khỏe · ② GCNKNCM (thuyền trưởng/máy trưởng/CCCM) · ③ Ảnh 2x3 · ④ Đơn đề nghị.
_ROWS: dict[str, dict[str, Any]] = {
    _SUC_KHOE: {
        "componentName": "Giấy chứng nhận sức khỏe do cơ sở y tế",
        "componentIndex": 1,
        "loaiBan": "Bản chính",
        "documentName": "Giấy chứng nhận sức khỏe",
    },
    _GCNKNCM: {
        # Dòng dài "Xuất trình… giấy tờ chứng nhận về thuyền trưởng hoặc máy trưởng hoặc chứng chỉ chuyên môn…"
        "componentName": "thuyền trưởng hoặc máy trưởng",
        "componentIndex": 2,
        "loaiBan": "Bản chính",
        "documentName": "Giấy chứng nhận khả năng chuyên môn/Chứng chỉ chuyên môn",
    },
    _ANH: {
        "componentName": "02 (hai) ảnh màu",
        "componentIndex": 3,
        "loaiBan": "Bản chính",
        "documentName": "02 ảnh màu 2x3",
    },
    _DON: {
        "componentName": "Đơn đề nghị theo quy định",
        "componentIndex": 4,
        "loaiBan": "Bản chính",
        "documentName": "Đơn đề nghị cấp/cấp lại/chuyển đổi GCNKNCM, CCCM",
    },
}
_SKIP_DOCS = {_CCCD}
_ALLOWED = set(_ROWS) | _SKIP_DOCS | {_OTHER}


def _normalize(value: str) -> str:
    f = _fold(value)
    if "suc khoe" in f:
        return _SUC_KHOE
    if "don" in f and "de nghi" in f:
        return _DON
    if "kha nang chuyen mon" in f or "gcnkncm" in f or "chung chi chuyen mon" in f:
        return _GCNKNCM
    if any(m in f for m in ("cccd", "can cuoc", "cmnd", "ho chieu")):
        return _CCCD
    if "anh" in f and ("the" in f or "2x3" in f or "3x4" in f):
        return _ANH
    return value if value in _ALLOWED else _OTHER


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=400, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    out: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            out[int(item.get("index"))] = _normalize(str(item.get("docType") or item.get("type") or ""))
        except Exception:  # noqa: BLE001
            continue
    return out


def _build_row_item(file: dict, file_index: int, doc_type: str) -> dict:
    row = _ROWS[doc_type]
    return {
        "fileIndex": file_index,
        "fileName": str(file.get("name") or f"file-{file_index + 1}"),
        "documentName": row["documentName"],
        "componentName": row["componentName"],
        "componentIndex": row["componentIndex"],
        "loaiBan": row["loaiBan"],
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": doc_type,
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    _ = ocr_results
    llm_types = llm_types or {}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        # LLM-PRIMARY: hoàn toàn tin LLM phân loại (KHÔNG dùng rule keyword). Thiếu → other.
        llm_type = llm_types.get(index, "")
        doc_type = llm_type if llm_type in _ALLOWED else _OTHER
        source = "llm" if doc_type != _OTHER else "unknown"

        if doc_type in _ROWS:
            attachments.append(_build_row_item(file, index, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "source": source})
        elif doc_type in _SKIP_DOCS:
            classified.append({"fileName": file_name, "docType": doc_type, "source": source, "skipped": True})
        else:
            warnings.append(f"Không xác định được loại giấy tờ cho file '{file_name}' — vui lòng đính kèm thủ công.")
            classified.append({"fileName": file_name, "docType": _OTHER, "source": source, "skipped": True})

    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]
    errors: list[str] = []

    from app.services import ocr

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    llm_docs = [
        {"index": index, "text": str(by_name.get(f.get("name"), {}).get("text") or "")}
        for index, f in enumerate(raw_files)
        if str(by_name.get(f.get("name"), {}).get("text") or "").strip()
    ]
    started = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [item.get("name") for item in ocr_results if item.get("text")],
            "llmDocuments": [raw_files[d["index"]]["name"] for d in llm_docs],
            "classified": classified,
            "rows": [{"docType": dt, **row} for dt, row in _ROWS.items()],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
