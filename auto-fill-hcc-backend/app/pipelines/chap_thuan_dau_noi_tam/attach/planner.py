"""Đính kèm "Thành phần hồ sơ" cho "Chấp thuận vị trí đấu nối tạm vào đường bộ đang khai thác" (cổng DVC
Bộ Xây dựng — Angular Reactive Form, engine FE `attp-row`).

Bảng thành phần hồ sơ 3 dòng (dùng chung rdo_File): (1) HĐ thi công / VB chấp thuận chủ trương đầu tư;
(2) Văn bản đề nghị (Đơn Mẫu Mucb); (3) Hồ sơ thiết kế bản vẽ thi công nút giao. FE khớp dòng bằng
componentName (substring fold).

Theo yêu cầu: Công văn/Nghị quyết/hồ sơ pháp lý → gom dòng (1); Đơn → dòng (2); bản vẽ → dòng (3). CCCD chỉ
dùng để trích thông tin, KHÔNG đính. Phân loại **LLM-primary**; rule keyword + heuristic ảnh chỉ DỰ PHÒNG.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.compact_agent.runner import _extract_docx_text, _is_docx
from app.pipelines.chap_thuan_dau_noi_tam.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON = "don_de_nghi"
_BANVE = "ho_so_ban_ve"
_HD = "hd_chu_truong"
_CCCD = "cccd"
_OTHER = "other"

_HD_COMPONENT = "hợp đồng thi công xây dựng dự án đối với trường hợp nhà thầu đề nghị đấu nối tạm"
_DON_COMPONENT = "Văn bản đề nghị theo quy định"
_BANVE_COMPONENT = "Hồ sơ thiết kế bản vẽ thi công nút giao đấu nối tạm"

_ROWS: dict[str, dict[str, str]] = {
    _HD: {
        "componentName": _HD_COMPONENT,
        "loaiBan": "Bản chính",
        "documentName": "Hợp đồng thi công / Văn bản chấp thuận chủ trương đầu tư (kèm căn cứ pháp lý)",
    },
    _DON: {
        "componentName": _DON_COMPONENT,
        "loaiBan": "Bản chính",
        "documentName": "Văn bản đề nghị chấp thuận vị trí đấu nối tạm (Mẫu Mucb)",
    },
    _BANVE: {
        "componentName": _BANVE_COMPONENT,
        "loaiBan": "Bản chính",
        "documentName": "Hồ sơ thiết kế bản vẽ thi công nút giao đấu nối tạm, phương án tổ chức giao thông",
    },
}
# CCCD chỉ trích xuất, không đính → bỏ qua.
_SKIP_DOCS: set[str] = {_CCCD}
_ALLOWED_DOC_TYPES = set(_ROWS) | _SKIP_DOCS | {_OTHER}


def _is_identity_text(text: str) -> bool:
    h = _fold(text)
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport"))


def _is_photo_like(text: str) -> bool:
    """Bản vẽ scan/ảnh: OCR rỗng/chỉ nhãn ảnh/rác. Đếm chữ cái < 20 → coi là ảnh (→ bản vẽ)."""
    letters = sum(1 for c in _fold(text) if c.isalpha())
    return letters < 20


def _rule_doc_type(text: str) -> str:
    h = _fold(text)
    if not h:
        return ""
    if _is_identity_text(h):
        return _CCCD
    if "de nghi chap thuan" in h and "dau noi" in h:
        return _DON
    if ("ban ve" in h or "thiet ke" in h or "bien phap thi cong" in h or "to chuc giao thong" in h) and "nut giao" in h:
        return _BANVE
    if "hop dong thi cong" in h or "chu truong dau tu" in h or "phe duyet du an" in h or "nghi quyet" in h:
        return _HD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if text in _ALLOWED_DOC_TYPES:
        return text
    if "ban ve" in text or "thiet ke" in text or "ban_ve" in text:
        return _BANVE
    if "cccd" in text or "can cuoc" in text or "cmnd" in text or "ho chieu" in text:
        return _CCCD
    if "hop dong" in text or "chu truong" in text or "phe duyet" in text or "cong van" in text:
        return _HD
    if "don" in text or "de nghi" in text or "mucb" in text:
        return _DON
    return _OTHER


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
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        out[idx] = _normalize_doc_type(str(item.get("docType") or item.get("type") or ""))
    return out


def _build_row_item(file: dict, file_index: int, doc_type: str) -> dict:
    row = _ROWS[doc_type]
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": row["documentName"],
        "componentName": row["componentName"],
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
    llm_types = llm_types or {}
    by_name = {item.get("name"): item for item in ocr_results}
    items: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = str(by_name.get(file_name, {}).get("text") or "")
        llm_type = llm_types.get(idx, "")
        rule_type = _rule_doc_type(text)
        if llm_type in _ROWS or llm_type in _SKIP_DOCS:
            doc_type, source = llm_type, "llm"
        elif rule_type:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = _OTHER, "unknown"

        if doc_type in _ROWS:
            items.append(_build_row_item(file, idx, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "source": source})
            continue
        if doc_type in _SKIP_DOCS:
            classified.append({"fileName": file_name, "docType": doc_type, "source": source, "skipped": True})
            continue

        # DỰ PHÒNG: file ẢNH/bản vẽ scan (OCR rỗng/rác) → dòng "Hồ sơ thiết kế bản vẽ". KHÔNG cho docx.
        if not _is_docx(file) and _is_photo_like(text):
            items.append(_build_row_item(file, idx, _BANVE))
            classified.append({"fileName": file_name, "docType": _BANVE, "source": "photo-fallback"})
            continue

        # Mặc định an toàn: gom file chưa rõ (công văn/pháp lý) vào dòng (1) HĐ/chủ trương.
        items.append(_build_row_item(file, idx, _HD))
        classified.append({"fileName": file_name, "docType": _HD, "source": f"{source}-default"})
        warnings.append(f"Không phân loại chắc chắn '{file_name}' — tạm đính dòng 'HĐ/chủ trương', vui lòng kiểm tra.")

    return items, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    _ = session
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    from app.services import ocr

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_results.extend(_extract_docx_text(f) for f in raw_files if _is_docx(f))
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    ocr_by_name = {item.get("name"): item for item in ocr_results}
    llm_docs: list[dict[str, Any]] = []
    for idx, file in enumerate(raw_files):
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        if text.strip():
            llm_docs.append({"index": idx, "text": text})

    t1 = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types)
    errors.extend(warnings)
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES and not _is_docx(f)]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "classified": classified,
            "skippedOcr": skipped_ocr,
            "rows": [{"docType": k, **v} for k, v in _ROWS.items()],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
