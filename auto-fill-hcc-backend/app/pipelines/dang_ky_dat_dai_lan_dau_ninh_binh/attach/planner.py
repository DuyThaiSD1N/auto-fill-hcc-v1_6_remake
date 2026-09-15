"""Lập kế hoạch đính kèm vào đúng dòng hồ sơ trên cổng DVC Ninh Bình.

Thủ tục "Đăng ký đất đai, cấp Giấy chứng nhận lần đầu": bảng đính kèm có sẵn 20 dòng, mỗi dòng ứng
với một loại giấy tờ. componentIndex là vị trí DOM 0-based của dòng (STT − 1); componentName là đoạn
text đặc trưng trong cột "Tên giấy tờ" của dòng đó (khớp substring sau khi fold dấu ở FE).

Phân loại LLM-FIRST tuyệt đối: doc_type CHỈ lấy từ LLM. Không có nhánh rule keyword nào (giòn, dễ sai).
Không rõ/không hợp lệ -> "other" -> cảnh báo, KHÔNG ép vào dòng gần giống. Mỗi file chỉ sinh một plan
item để không nhân bản một tài liệu sang nhiều dòng.

Các nhóm dòng có tên gần giống (thừa kế 4/5/16, thỏa thuận cấp chung 12/18, Điều 137 10/17) chỉ route
về dòng CHÍNH; componentIndex giúp FE chọn đúng dòng khi text trùng nhau.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON_DANG_KY = "don_dang_ky"
_IDENTITY = "identity"
_CHUNG_TU_TAI_CHINH = "chung_tu_tai_chinh"
_THUA_KE_QSDD = "thua_ke_qsdd"
_MANH_TRICH_DO = "manh_trich_do"
_THOA_THUAN_CAP_CHUNG = "thoa_thuan_cap_chung"
_GIAY_TO_DIEU_137 = "giay_to_dieu_137"
_VAN_BAN_DAI_DIEN = "van_ban_dai_dien"
_OTHER = "other"

# componentName lấy VERBATIM từ cột "Tên giấy tờ" của html đính kèm.html (đã đối chiếu 20 dòng).
_ROUTES: dict[str, dict[str, Any]] = {
    _DON_DANG_KY: {
        "index": 19,
        "name": "Đơn đăng ký đất đai, tài sản gắn liền với đất",
        "documentName": "Đơn đăng ký đất đai (Mẫu số 15)",
    },
    # Form KHÔNG có dòng CCCD riêng -> CCCD đi chung dòng Đơn đăng ký.
    _IDENTITY: {
        "index": 19,
        "name": "Đơn đăng ký đất đai, tài sản gắn liền với đất",
        "documentName": "Căn cước công dân",
    },
    _CHUNG_TU_TAI_CHINH: {
        "index": 0,
        "name": "Chứng từ thực hiện nghĩa vụ tài chính",
        "documentName": "Chứng từ nghĩa vụ tài chính",
    },
    _THUA_KE_QSDD: {
        "index": 5,
        "name": "nhận thừa kế quyền sử dụng đất chưa được cấp Giấy chứng nhận",
        "documentName": "Giấy tờ nhận thừa kế QSDĐ",
    },
    _MANH_TRICH_DO: {
        "index": 9,
        "name": "Mảnh trích đo bản đồ địa chính thửa đất",
        "documentName": "Mảnh trích đo bản đồ địa chính",
    },
    _THOA_THUAN_CAP_CHUNG: {
        "index": 12,
        "name": "Văn bản thỏa thuận về việc cấp chung một Giấy chứng nhận",
        "documentName": "Văn bản thỏa thuận cấp chung một GCN / Danh sách Mẫu 15",
    },
    _GIAY_TO_DIEU_137: {
        "index": 10,
        "name": "Một trong các loại giấy tờ quy định tại Điều 137, khoản 1, khoản 5 Điều 148",
        "documentName": "Giấy tờ theo Điều 137",
    },
    _VAN_BAN_DAI_DIEN: {
        "index": 13,
        "name": "Văn bản về việc đại diện theo quy định của pháp luật về dân sự",
        "documentName": "Văn bản đại diện/ủy quyền",
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

        warnings.append(f"Không xác định được loại giấy tờ cho file '{file_name}' — vui lòng đính kèm thủ công.")
        source = "llm" if llm_type == _OTHER else "unknown"
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
