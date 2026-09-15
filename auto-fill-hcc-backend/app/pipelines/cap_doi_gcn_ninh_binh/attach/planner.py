"""Lập kế hoạch đính kèm vào đúng dòng hồ sơ trên cổng DVC Ninh Bình (cấp đổi Giấy chứng nhận).

Thủ tục "Cấp đổi Giấy chứng nhận": bảng đính kèm CHỈ có 2 dòng. componentIndex là vị trí DOM 0-based
của dòng (STT − 1); componentName là đoạn text đặc trưng trong cột "Tên giấy tờ" của dòng đó (khớp
substring sau khi fold dấu ở FE).

Bố cục 2 dòng:
- STT1 (index 0): Mảnh trích đo bản đồ địa chính thửa đất -> chỉ nhận mảnh trích đo/phiếu đo đạc.
- STT2 (index 1): Đơn đăng ký biến động Mẫu số 11/ĐK -> gom CHUNG cả Đơn Mẫu 11, Giấy chứng nhận đã
  cấp, văn bản ủy quyền và CCCD (form không có dòng riêng cho GCN/ủy quyền/CCCD). Bốn docType
  don_bien_dong/land_certificate/authorization/identity cùng componentName+componentIndex=1 nên engine
  attp-row tự gom vào cùng một ô upload multiple của dòng 2 — đúng ý đồ. Mỗi file vẫn sinh một plan
  item riêng, documentName khác nhau để cán bộ đối chiếu.

Phân loại LLM-FIRST tuyệt đối: doc_type CHỈ lấy từ LLM. Không có nhánh rule keyword nào (giòn, dễ sai).
Không rõ/không hợp lệ -> "other" -> cảnh báo, KHÔNG ép vào dòng gần giống.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_MANH_TRICH_DO = "manh_trich_do"
_DON_BIEN_DONG = "don_bien_dong"
_LAND_CERTIFICATE = "land_certificate"
_AUTHORIZATION = "authorization"
_IDENTITY = "identity"
_OTHER = "other"

# componentName lấy VERBATIM từ cột "Tên giấy tờ" của html đính kèm.html (đã đối chiếu 2 dòng).
_DON_BIEN_DONG_NAME = "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 11"
_ROUTES: dict[str, dict[str, Any]] = {
    _MANH_TRICH_DO: {
        "index": 0,
        "name": "Mảnh trích đo bản đồ địa chính thửa đất",
        "documentName": "Mảnh trích đo / phiếu đo đạc",
    },
    _DON_BIEN_DONG: {
        "index": 1,
        "name": _DON_BIEN_DONG_NAME,
        "documentName": "Đơn đăng ký biến động (Mẫu số 11/ĐK)",
    },
    # Form KHÔNG có dòng riêng cho Giấy chứng nhận đã cấp -> đi chung dòng Đơn Mẫu 11.
    _LAND_CERTIFICATE: {
        "index": 1,
        "name": _DON_BIEN_DONG_NAME,
        "documentName": "Giấy chứng nhận đã cấp",
    },
    # Form KHÔNG có dòng riêng cho văn bản ủy quyền -> đi chung dòng Đơn Mẫu 11.
    _AUTHORIZATION: {
        "index": 1,
        "name": _DON_BIEN_DONG_NAME,
        "documentName": "Văn bản ủy quyền",
    },
    # Form KHÔNG có dòng CCCD riêng -> CCCD đi chung dòng Đơn Mẫu 11.
    _IDENTITY: {
        "index": 1,
        "name": _DON_BIEN_DONG_NAME,
        "documentName": "Căn cước công dân",
    },
}
_ALLOWED = set(_ROUTES) | {_OTHER}


def _normalize_doc_type(value: Any) -> str:
    folded = _fold(str(value or ""))
    for doc_type in _ALLOWED:
        if folded == _fold(doc_type):
            return doc_type
    return _OTHER


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=700, enable_thinking=settings.agent_reasoning)
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
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": doc_type,
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict] | None = None,
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    del ocr_results  # LLM-first: không dùng OCR text để suy luận rule ở đây.
    llm_types = llm_types or {}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        llm_type = llm_types.get(index, "")
        # doc_type CHỈ lấy từ LLM; không có rule fallback.
        doc_type = llm_type if llm_type in _ROUTES else _OTHER

        if doc_type in _ROUTES:
            item = _build_item(file, index, doc_type)
            attachments.append(item)
            classified.append(
                {
                    "fileName": file_name,
                    "docType": doc_type,
                    "source": "llm",
                    "componentIndex": item["componentIndex"],
                }
            )
            continue

        # Form KHÔNG có dòng "Giấy tờ khác" → KHÔNG bỏ file (sẽ rớt), mà đính CHUNG vào dòng ĐƠN đăng ký
        # biến động (Mẫu 11/ĐK, index 1) — nơi đã gom Đơn/GCN/ủy quyền/CCCD. Giữ TÊN FILE GỐC làm
        # documentName để cán bộ nhận ra và soát lại (yêu cầu user 2026-09-09).
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": file_name,
            "componentName": _DON_BIEN_DONG_NAME,
            "componentIndex": 1,
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": _OTHER,
        })
        warnings.append(
            f"Chưa nhận diện chắc loại giấy tờ cho '{file_name}' — tạm đính vào dòng Đơn đăng ký "
            f"biến động (Mẫu 11/ĐK); cán bộ kiểm tra lại."
        )
        source = "llm" if llm_type == _OTHER else "unknown"
        classified.append({"fileName": file_name, "docType": _OTHER, "source": source, "routedTo": 1})

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
