"""Đính kèm cho "[Bắc Ninh] Cấp đổi Giấy chứng nhận QSDĐ".

E-form Bắc Ninh (Liferay) có 2 nhóm thành phần hồ sơ cho thủ tục này, mỗi nhóm gồm 2 dòng con
Bản chính / Bản sao. FE khớp NHÓM theo `componentName` (substring nhãn đã fold dấu), tick checkbox
nhóm rồi gán file vào ô Bản chính.

Gom file theo chú giải hồ sơ mẫu:
- Đơn Mẫu 18 + CCCD người yêu cầu → nhóm "Đơn đăng ký biến động đất đai... Mẫu số 18".
- Bản gốc GCN → nhóm "Bản gốc Giấy chứng nhận đã cấp".

Route TẤT ĐỊNH theo nội dung OCR; LLM chỉ dùng để đặt documentName hiển thị. File không rõ → gộp vào
nhóm Đơn Mẫu 18 (nhóm chính của thủ tục này — cấp đổi không có nhóm "chứng minh sai sót").
"""
import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_ALLOWED_LLM_TYPES = {"identity", "application", "land_certificate", "authorization"}
_CONFIDENT_LLM_TYPES = {"identity", "application", "land_certificate", "authorization"}

# Nhãn nhận dạng NHÓM thành phần hồ sơ (FE khớp theo substring đã fold dấu).
_COMP_APPLICATION = "Đơn đăng ký biến động đất đai"
_COMP_LAND_CERT = "Bản gốc Giấy chứng nhận đã cấp"

# type → (componentName, nhãn hiển thị mặc định). Cấp đổi CHỈ có 2 nhóm; ủy quyền/không rõ → gộp Đơn.
_ROUTE = {
    "application": (_COMP_APPLICATION, "Đơn đăng ký biến động Mẫu số 18"),
    "identity": (_COMP_APPLICATION, "Căn cước công dân"),
    "land_certificate": (_COMP_LAND_CERT, "Bản gốc Giấy chứng nhận QSDĐ"),
    "authorization": (_COMP_APPLICATION, "Văn bản ủy quyền"),
    "other": (_COMP_APPLICATION, "Giấy tờ kèm theo đơn"),
}


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def _canonical_type(value: str) -> str:
    doc_type = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    return doc_type if doc_type in _ALLOWED_LLM_TYPES else "other"


def _looks_like_identity(haystack: str) -> bool:
    if any(k in haystack for k in (
        "can cuoc cong dan", "the can cuoc", "cccd", "chung minh nhan dan", "ho chieu", "passport",
    )):
        return True
    if "so dinh danh ca nhan" not in haystack:
        return False
    markers = ("co gia tri den", "date of expiry", "noi thuong tru", "place of residence",
               "que quan", "place of origin", "dac diem nhan dang")
    return sum(1 for m in markers if m in haystack) >= 2


def _detect_route_type(ocr_text: str) -> str | None:
    """Route TẤT ĐỊNH theo nội dung OCR. None = không rõ (để LLM/mặc định quyết)."""
    haystack = _fold(ocr_text or "")
    if not haystack.strip():
        return None
    # Đơn Mẫu 18 (ưu tiên trước identity: đơn cũng ghi số định danh người khai).
    if "mau so 18" in haystack or "dang ky bien dong" in haystack:
        return "application"
    if "giay uy quyen" in haystack or "van ban uy quyen" in haystack or "hop dong uy quyen" in haystack:
        return "authorization"
    if ("quyen su dung dat" in haystack or "quyen so huu" in haystack) and "giay chung nhan" in haystack:
        return "land_certificate"
    if _looks_like_identity(haystack):
        return "identity"
    return None


def _detect_route_by_filename(name: str) -> str | None:
    """Fallback CUỐI khi OCR rỗng: đoán theo TÊN FILE. Nội dung OCR vẫn ưu tiên trước."""
    h = _fold(name or "")
    if not h.strip():
        return None
    if "uy quyen" in h:
        return "authorization"
    if "mau so 18" in h or ("don" in h and ("bien dong" in h or "dang ky" in h or "dki" in h or "dkbd" in h)):
        return "application"
    if "can cuoc" in h or "cccd" in h or "cmnd" in h or "cmt" in h or "the cc" in h:
        return "identity"
    if any(k in h for k in ("so dat", "so do", "so hong", "gcn", "qsdd", "quyen su dung dat", "giay chung nhan")):
        return "land_certificate"
    return None


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
    component_name, _ = _ROUTE.get(doc_type, _ROUTE["other"])
    return {
        "fileIndex": idx,
        "fileName": str(file.get("name") or f"file-{idx + 1}"),
        "documentName": document_name,
        "componentName": component_name,
        "target": "existing",
        "slotKey": "banChinh",  # gán vào ô Bản chính (không ký số) của nhóm
        "needsAddComponent": False,
        "detectedType": document_name,
    }


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
        ocr_text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        doc_type = _detect_route_type(ocr_text)
        route_src = "ocr" if doc_type else None
        if doc_type is None:
            llm_type = detected.get("type") or ""
            if llm_type in _CONFIDENT_LLM_TYPES:
                doc_type = llm_type
                route_src = "llm"
        if doc_type is None:
            doc_type = _detect_route_by_filename(file.get("name"))
            if doc_type:
                route_src = "filename"
        if doc_type is None:
            doc_type = "other"
            route_src = "default"

        _, fallback_label = _ROUTE.get(doc_type, _ROUTE["other"])
        if route_src in ("ocr", "llm"):
            base_name = detected.get("documentName") or fallback_label
        else:
            base_name = fallback_label
        document_name = _unique_document_name(base_name, used_names, fallback_label)

        item = _build_item(file, idx, doc_type, document_name)
        attachments.append(item)
        classified.append({
            "fileName": file.get("name"),
            "type": doc_type,
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
        "errors": errors,
    }
