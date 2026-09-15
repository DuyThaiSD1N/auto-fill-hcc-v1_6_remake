"""Đính kèm cho "[Bắc Ninh] Cấp đổi Giấy chứng nhận QSDĐ".

E-form Bắc Ninh (Liferay) có 2 nhóm thành phần hồ sơ cho thủ tục này, mỗi nhóm gồm 2 dòng con
Bản chính / Bản sao. FE khớp NHÓM theo `componentName` (substring nhãn đã fold dấu), tick checkbox
nhóm rồi gán file vào ô Bản chính.

Khớp thành phần hồ sơ theo MÃ TP-H05 (in trong dòng tiêu đề mỗi thành phần → FE khớp substring đã
fold, BỀN hơn khớp nhãn tiếng Việt hay đổi; vd form ghi "Giấy chứng nhận đã cấp, trừ trường hợp…"
KHÔNG có chữ "Bản gốc" nên khớp theo nhãn cũ sẽ TRƯỢT):
- Đơn đăng ký biến động (Mẫu 18) → TP-H05.000026.
- Bản gốc GCN đã cấp → TP-H05.000040.
- CCCD / văn bản ủy quyền / giấy tờ khác: form cấp đổi (1.012783) KHÔNG có ô riêng → ô "File đính kèm
  khác" (target "supplementary"). Tránh dồn nhiều file vào 1 ô Bản chính (chỉ nhận 1 file → mất file).

Phân loại LLM-FIRST (LLM đọc OCR → type; KHÔNG dùng rule keyword — giòn, dễ nhận nhầm). Type không rõ
→ "other" → "File đính kèm khác" ⇒ ĐÍNH ĐỦ, không rớt file nào. Mọi file luôn sinh 1 attachment item.
"""
import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_ALLOWED_LLM_TYPES = {"identity", "application", "land_certificate", "authorization"}

# componentName = MÃ TP-H05 (FE khớp substring đã fold: "tp h05.000040" nằm trong dòng tiêu đề thành phần).
_COMP_APPLICATION = "TP-H05.000026"   # Đơn đăng ký biến động đất đai (Mẫu số 18)
_COMP_LAND_CERT = "TP-H05.000040"     # Bản gốc Giấy chứng nhận đã cấp

# type → (target, componentName, nhãn hiển thị mặc định).
# Form cấp đổi chỉ có ô riêng cho Đơn (000026) + GCN (000040); CCCD/ủy quyền/khác → "File đính kèm khác".
_ROUTE = {
    "application": ("existing", _COMP_APPLICATION, "Đơn đăng ký biến động Mẫu số 18"),
    "land_certificate": ("existing", _COMP_LAND_CERT, "Bản gốc Giấy chứng nhận QSDĐ"),
    "identity": ("supplementary", "", "Căn cước công dân"),
    "authorization": ("supplementary", "", "Văn bản ủy quyền"),
    "other": ("supplementary", "", "Giấy tờ kèm theo đơn"),
}


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def _canonical_type(value: str) -> str:
    doc_type = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    return doc_type if doc_type in _ALLOWED_LLM_TYPES else "other"


def _unique_document_name(base: str, used: set[str], fallback: str) -> str:
    normalized = normalize_document_name(base, fallback)
    key = _fold(normalized)
    if key and key not in used:
        used.add(key)
        return normalized
    stem = normalized[:45].strip() or fallback[:45].strip() or "Tài liệu"
    n = 2
    while True:
        candidate = f"{stem} {n}"[:50].strip()
        key = _fold(candidate)
        if key not in used:
            used.add(key)
            return candidate
        n += 1


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    if not documents:
        return {}
    docs = [{"index": item["index"], "text": _truncate_text(item.get("text", ""))} for item in documents]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(docs)},
    ]
    raw = await client.chat(messages, max_tokens=700, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    parsed_docs = parsed.get("documents", []) or []

    def _coerce(item: dict) -> dict[str, str]:
        return {
            "type": _canonical_type(str(item.get("type") or "")),
            "documentName": str(item.get("documentName") or "").strip(),
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
    offset = 0 if any(r == 0 for r, _ in raw_items) else 1
    valid = {d["index"] for d in documents}
    for r, item in raw_items:
        idx = r - offset
        if idx in valid:
            out[idx] = _coerce(item)
    return out


def _build_item(file: dict, idx: int, doc_type: str, document_name: str) -> dict:
    target, component_name, _ = _ROUTE.get(doc_type, _ROUTE["other"])
    item = {
        "fileIndex": idx,
        "fileName": str(file.get("name") or f"file-{idx + 1}"),
        "documentName": document_name,
        "componentName": component_name,
        "target": target,
        "needsAddComponent": False,
        "detectedType": document_name,
    }
    if target == "existing":
        item["slotKey"] = "banChinh"  # gán vào ô Bản chính (không ký số) của nhóm
    return item


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    from app.services import ocr

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for r in ocr_results:
        if r.get("error"):
            errors.append(f"OCR {r.get('name')}: {r['error']}")

    ocr_by_name = {r.get("name"): r for r in ocr_results}
    llm_docs = [
        {"index": idx, "text": str(ocr_by_name.get(file.get("name"), {}).get("text") or "")}
        for idx, file in enumerate(raw_files)
    ]

    t1 = time.monotonic()
    llm_types: dict[int, dict[str, str]] = {}
    if any(d["text"].strip() for d in llm_docs):
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as e:  # noqa: BLE001
            errors.append(f"attachment_agent: {e}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments: list[dict] = []
    classified: list[dict] = []
    used_names: set[str] = set()
    for idx, file in enumerate(raw_files):
        detected = llm_types.get(idx) or {"type": "", "documentName": ""}
        # LLM-FIRST: type do LLM quyết. Không hợp lệ/không rõ → "other" → "File đính kèm khác"
        # (ĐÍNH ĐỦ, KHÔNG rớt file). KHÔNG dùng rule keyword để phân loại.
        llm_type = detected.get("type") or ""
        if llm_type in _ALLOWED_LLM_TYPES:
            doc_type = llm_type
            route_src = "llm"
        else:
            doc_type = "other"
            route_src = "default"

        _, _, fallback_label = _ROUTE.get(doc_type, _ROUTE["other"])
        base_name = (detected.get("documentName") if route_src == "llm" else "") or fallback_label
        document_name = _unique_document_name(base_name, used_names, fallback_label)

        item = _build_item(file, idx, doc_type, document_name)
        attachments.append(item)
        classified.append({
            "fileName": file.get("name"),
            "type": doc_type,
            "routeSrc": route_src,
            "documentName": document_name,
            "componentName": item["componentName"],
        })

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [f["name"] for f in raw_files],
            "sessionId": (session or {}).get("request_id"),
            "classified": classified,
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "ocr_text": join_ocr_documents(ocr_results),
        "errors": errors,
    }
