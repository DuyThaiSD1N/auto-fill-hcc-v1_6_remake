"""Lập kế hoạch đính kèm vào đúng 4 dòng hồ sơ trên cổng DVC Ninh Bình.

Thứ tự dòng lấy từ HTML thật của thủ tục, không lấy từ ảnh minh họa:
  0. Đơn đăng ký biến động Mẫu số 18 (CCCD người nộp đi chung dòng này)
  1. Văn bản ủy quyền
  2. Giấy tờ chứng minh sai sót
  3. Bản gốc Giấy chứng nhận đã cấp

Mỗi file chỉ sinh một plan item để không nhân bản một tài liệu sang nhiều dòng.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_LOAI_BAN = "Bản chính"

_APPLICATION = "application"
_AUTHORIZATION = "authorization"
_ERROR_PROOF = "error_proof"
_LAND_CERTIFICATE = "land_certificate"
_IDENTITY = "identity"
_OTHER = "other"

_ROUTES: dict[str, dict[str, Any]] = {
    _APPLICATION: {
        "index": 0,
        "name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18",
        "documentName": "Đơn đăng ký biến động Mẫu số 18",
    },
    # Tài liệu định danh là giấy tờ kèm theo người viết đơn; form không có dòng CCCD riêng.
    _IDENTITY: {
        "index": 0,
        "name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18",
        "documentName": "Căn cước công dân",
    },
    _AUTHORIZATION: {
        "index": 1,
        "name": "Văn bản về việc ủy quyền theo quy định của pháp luật về dân sự",
        "documentName": "Văn bản ủy quyền",
    },
    _ERROR_PROOF: {
        "index": 2,
        "name": "Giấy tờ chứng minh sai sót thông tin của người được cấp Giấy chứng nhận",
        "documentName": "Giấy tờ chứng minh sai sót",
    },
    _LAND_CERTIFICATE: {
        "index": 3,
        "name": "Bản gốc Giấy chứng nhận đã cấp",
        "documentName": "Giấy chứng nhận quyền sử dụng đất",
    },
}
_ALLOWED = set(_ROUTES) | {_OTHER}


def _normalize_doc_type(value: Any) -> str:
    folded = _fold(str(value or ""))
    for doc_type in _ALLOWED:
        if folded == _fold(doc_type):
            return doc_type
    return _OTHER


def _is_identity_text(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "can cuoc cong dan",
            "citizen identity card",
            "chung minh nhan dan",
            "the can cuoc",
            "ho chieu",
            "passport",
        )
    )


def _rule_doc_type(text: str) -> str:
    """Fallback theo dấu hiệu chắc chắn; LLM vẫn là nguồn phân loại đầu tiên."""
    folded = _fold(text or "")
    if not folded:
        return ""
    if "mau so 18" in folded or "don dang ky bien dong dat dai" in folded:
        return _APPLICATION
    if any(marker in folded for marker in ("giay uy quyen", "van ban uy quyen", "hop dong uy quyen")):
        return _AUTHORIZATION
    if "giay chung nhan" in folded and any(
        marker in folded for marker in ("quyen su dung dat", "thua dat", "to ban do", "so vao so")
    ):
        return _LAND_CERTIFICATE
    if _is_identity_text(folded):
        return _IDENTITY
    if any(
        marker in folded
        for marker in (
            "giay khai sinh",
            "trich luc khai sinh",
            "giay xac nhan",
            "hop dong chuyen nhuong quyen su dung dat",
            "ho so dia chinh",
            "trich luc ban do",
            "chung minh sai sot",
        )
    ):
        return _ERROR_PROOF
    return ""


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=600, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    result: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            result[int(item.get("index"))] = _normalize_doc_type(item.get("docType") or item.get("type"))
        except (TypeError, ValueError):
            continue
    return result


def _build_item(file: dict, file_index: int, doc_type: str) -> dict:
    route = _ROUTES[doc_type]
    return {
        "fileIndex": file_index,
        "fileName": str(file.get("name") or f"file-{file_index + 1}"),
        "documentName": route["documentName"],
        "componentName": route["name"],
        "componentIndex": route["index"],
        "loaiBan": _LOAI_BAN,
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
    ocr_by_name = {item.get("name"): item for item in ocr_results}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        text = str(ocr_by_name.get(file_name, {}).get("text") or "")
        llm_type = llm_types.get(index, "")
        rule_type = _rule_doc_type(text)

        if llm_type in _ROUTES:
            doc_type, source = llm_type, "llm"
        elif rule_type:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = _OTHER, "llm" if llm_type == _OTHER else "unknown"

        if doc_type in _ROUTES:
            item = _build_item(file, index, doc_type)
            attachments.append(item)
            classified.append(
                {
                    "fileName": file_name,
                    "docType": doc_type,
                    "source": source,
                    "componentIndex": item["componentIndex"],
                }
            )
            continue

        warnings.append(f"Không xác định được loại giấy tờ cho file '{file_name}' — vui lòng đính kèm thủ công.")
        classified.append({"fileName": file_name, "docType": _OTHER, "source": source, "skipped": True})

    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    ocr_files = [item for item in raw_files if item.get("type") in _OCR_TYPES]
    errors: list[str] = []

    from app.services import ocr

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    llm_documents = [
        {"index": index, "text": str(by_name.get(file.get("name"), {}).get("text") or "")}
        for index, file in enumerate(raw_files)
        if str(by_name.get(file.get("name"), {}).get("text") or "").strip()
    ]
    started = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_documents:
        try:
            llm_types = await _classify_with_llm(llm_documents)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [item["name"] for item in raw_files],
            "ocrDocuments": [item.get("name") for item in ocr_results if item.get("text")],
            "llmDocuments": [raw_files[item["index"]]["name"] for item in llm_documents],
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
