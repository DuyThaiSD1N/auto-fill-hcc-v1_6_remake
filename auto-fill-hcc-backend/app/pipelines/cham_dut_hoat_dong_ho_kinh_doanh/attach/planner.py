"""Phân loại tài liệu vào đúng danh mục đính kèm của hồ sơ chấm dứt HKD."""

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

_TYPE_CONFIG = {
    "family_minutes": ("DISSOLUTION_FAMILY_MINUTES", "Bản sao biên bản họp thành viên hộ gia đình"),
    "tax_termination_notice": ("TAX_TERMINATION_NOTICE", "Thông báo về việc chấm dứt hiệu lực mã số thuế của Cơ quan thuế"),
    "dissolution_notice": ("DISSOLUTION_NOTICE", "Thông báo về việc chấm dứt hoạt động hộ kinh doanh"),
    "registration_certificate": ("BUSINESS_REG_CERT_ORIGINAL", "Bản gốc Giấy chứng nhận đăng ký hộ kinh doanh"),
    "other": ("OTHERS", "Khác"),
}

_MARKERS = (
    ("family_minutes", ("bien ban hop thanh vien ho gia dinh",)),
    # File scan gộp thường đặt Mẫu số 1 ở trang đầu rồi mới tới GCN/Thông báo thuế: ưu tiên
    # thành phần chính để không đẩy cả bộ hồ sơ vào loại thuế chỉ vì marker ở trang sau.
    ("dissolution_notice", ("thong bao ve viec cham dut hoat dong ho kinh doanh",)),
    ("tax_termination_notice", (
        "cham dut hieu luc ma so thue", "hoan thanh nghia vu nop thue de nop ho so giai the",
        "hoan thanh nghia vu thue de giai the",
    )),
    ("registration_certificate", ("giay chung nhan dang ky ho kinh doanh",)),
)


def _detect_type(text: str) -> str | None:
    folded = _fold(text or "")
    for doc_type, markers in _MARKERS:
        if any(marker in folded for marker in markers):
            return doc_type
    return None


def _truncate(text: str, limit: int = 3500) -> str:
    value = re.sub(r"\s+", " ", text or "").strip()
    return value if len(value) <= limit else value[:limit] + "..."


async def _classify(documents: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    if not documents:
        return {}
    raw = await client.chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ], max_tokens=700, enable_thinking=settings.agent_reasoning)
    items = client.extract_json_block(raw).get("documents", []) or []
    allowed = set(_TYPE_CONFIG)
    out: dict[int, dict[str, str]] = {}
    if len(items) == len(documents):
        for position, item in enumerate(items):
            doc_type = str(item.get("type") or "other").lower()
            out[documents[position]["index"]] = {
                "type": doc_type if doc_type in allowed else "other",
                "documentName": str(item.get("documentName") or "").strip(),
            }
    return out


def _unique_name(value: str, used: set[str], fallback: str) -> str:
    base = normalize_document_name(value, fallback)
    folded = _fold(base)
    if folded not in used:
        used.add(folded)
        return base
    number = 2
    while True:
        candidate = f"{base[:43].strip()} {number}"[:50]
        folded = _fold(candidate)
        if folded not in used:
            used.add(folded)
            return candidate
        number += 1


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    ocr_files = [item for item in raw_files if item.get("type") in _OCR_TYPES]
    errors: list[str] = []

    from app.services import ocr

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for result in ocr_results:
        if result.get("error"):
            errors.append(f"OCR {result.get('name')}: {result['error']}")
    ocr_by_name = {result.get("name"): result for result in ocr_results}
    docs = [{
        "index": index,
        "text": _truncate(str(ocr_by_name.get(item.get("name"), {}).get("text") or "")),
    } for index, item in enumerate(raw_files)]

    llm_started = time.monotonic()
    classified: dict[int, dict[str, str]] = {}
    try:
        # LLM xử lý toàn bộ để đặt tên riêng và là fallback bắt buộc cho tài liệu rule chưa rõ.
        classified = await _classify(docs) if any(item["text"] for item in docs) else {}
    except Exception as exc:  # noqa: BLE001
        errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - llm_started) * 1000)

    attachments = []
    summary = []
    used_names: set[str] = set()
    for index, item in enumerate(raw_files):
        text = str(ocr_by_name.get(item.get("name"), {}).get("text") or "")
        llm = classified.get(index) or {}
        doc_type = _detect_type(text) or str(llm.get("type") or "other")
        if doc_type not in _TYPE_CONFIG:
            doc_type = "other"
        category, component = _TYPE_CONFIG[doc_type]
        document_name = _unique_name(str(llm.get("documentName") or ""), used_names, component)
        attachments.append({
            "fileIndex": index,
            "fileName": item.get("name") or f"file-{index + 1}",
            "documentName": document_name,
            "componentName": component,
            "target": "new",
            "needsAddComponent": False,
            "detectedType": component,
            "category": category,
        })
        summary.append({
            "fileName": item.get("name"), "type": doc_type,
            "category": category, "documentName": document_name,
        })

    return {
        "attachments": attachments,
        "extracted": {"classified": summary, "sessionId": (session or {}).get("request_id")},
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
