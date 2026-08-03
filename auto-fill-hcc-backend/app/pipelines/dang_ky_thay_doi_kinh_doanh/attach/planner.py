"""Attachment plan cho thay đổi nội dung đăng ký HKD.

Thông báo và GCN đi cùng thành phần chính theo bảng ánh xạ nghiệp vụ. CCCD vào
giấy tờ pháp lý cá nhân; các trường hợp điều kiện giữ đúng tên thành phần trên cổng.
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

_TYPE_CONFIG = {
    "change_notice": ("BUSCHANGEFRM", "Thông báo thay đổi nội dung đăng ký hộ kinh doanh"),
    # Bảng ánh xạ nghiệp vụ gộp GCN hiện tại cùng thành phần chính của Thông báo thay đổi.
    "registration_certificate": ("BUSCHANGEFRM", "Thông báo thay đổi nội dung đăng ký hộ kinh doanh"),
    "personal_legal": ("CPID", "Bản sao giấy tờ pháp lý của cá nhân"),
    "transfer_proof": ("TRANSFER", "Hợp đồng mua bán hoặc các giấy tờ chứng minh hoàn tất việc mua bán; hợp đồng tặng cho; bản sao văn bản xác nhận quyền thừa kế hợp pháp"),
    "family_minutes": ("FAMILYMINUTES", "Bản sao biên bản họp thành viên hộ gia đình"),
    "family_authorization": ("FAMILYAUTH", "Bản sao văn bản ủy quyền của thành viên hộ gia đình cho một thành viên làm chủ hộ kinh doanh"),
    "other": ("OTHERS", "Khác"),
}

_MARKERS = (
    ("change_notice", ("thong bao thay doi noi dung dang ky ho kinh doanh", "dang ky thay doi noi dung dang ky ho kinh doanh")),
    ("registration_certificate", ("giay chung nhan dang ky ho kinh doanh",)),
    ("personal_legal", ("can cuoc cong dan", "the can cuoc", "chung minh nhan dan", "ho chieu", "passport")),
    ("transfer_proof", ("hop dong mua ban ho kinh doanh", "hop dong tang cho ho kinh doanh", "quyen thua ke hop phap")),
    ("family_minutes", ("bien ban hop thanh vien ho gia dinh",)),
    ("family_authorization", ("uy quyen cua thanh vien ho gia dinh", "uy quyen lam chu ho kinh doanh")),
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
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=700, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    items = parsed.get("documents", []) or []
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

    docs = [
        {"index": index, "text": _truncate(str(ocr_by_name.get(item.get("name"), {}).get("text") or ""))}
        for index, item in enumerate(raw_files)
    ]
    llm_started = time.monotonic()
    classified: dict[int, dict[str, str]] = {}
    try:
        # LLM luôn xử lý toàn bộ để đặt tên cụ thể và làm fallback cho mọi tài liệu rule không rõ.
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
        summary.append({"fileName": item.get("name"), "type": doc_type, "category": category, "documentName": document_name})

    return {
        "attachments": attachments,
        "extracted": {"classified": summary, "sessionId": (session or {}).get("request_id")},
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
