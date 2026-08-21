"""Lập kế hoạch đính kèm vào đúng 16 dòng hồ sơ trên cổng DVC Ninh Bình."""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_LOAI_BAN = "Bản chính"

# Các dòng có tên gần giống nhau thuộc những nhánh nghiệp vụ khác nhau; không được nhân cùng một file
# sang nhiều nhánh chỉ vì docType giống nhau.
_GCN_CHUYEN_MUC_DICH_ROUTE = {"index": 4, "name": "Một trong các giấy chứng nhận quy định tại khoản 21 Điều 3"}
_GCN_GIA_HAN_ROUTE = {"index": 14, "name": "Một trong các giấy tờ sau"}

_ROUTES: dict[str, list[dict[str, Any]]] = {
    "ket_qua_lua_chon_nha_dau_tu": [{"index": 1, "name": "Bản sao văn bản phê duyệt kết quả lựa chọn nhà đầu tư"}],
    "don_mau_01": [{"index": 2, "name": "Đơn theo Mẫu số 01"}],
    "van_ban_phe_duyet_dau_tu": [{"index": 3, "name": "Bản sao văn bản phê duyệt dự án đầu tư"}],
    "gcn": [_GCN_CHUYEN_MUC_DICH_ROUTE],
    "phuong_an_tang_dat_mat": [
        {"index": 5, "name": "Phương án sử dụng tầng đất mặt theo Mẫu số 26"},
        {"index": 6, "name": "Phương án sử dụng tầng đất mặt theo Mẫu số 26"},
    ],
    "du_an_giao_rung": [{"index": 7, "name": "Dự án đầu tư đối với khu rừng đề nghị giao"}],
    "dau_gia_thue_rung": [{"index": 8, "name": "Kết quả đấu giá thuê rừng"}],
    "giay_to_dau_tu_tong_hop": [
        {"index": 9, "name": "Một trong các loại giấy tờ sau"},
        {"index": 12, "name": "Một trong các loại giấy tờ sau"},
    ],
    "phuong_an_cong_ty_nong_lam": [{"index": 10, "name": "Phương án sử dụng đất của công ty nông, lâm nghiệp tại địa phương"}],
    "phuong_an_dat_thu_hoi": [{"index": 11, "name": "Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối với diện tích đất thu hồi"}],
    "phuong_an_to_chuc_kinh_te": [{"index": 13, "name": "Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối với tổ chức kinh tế"}],
    "don_mau_04": [{"index": 15, "name": "Đơn theo Mẫu số 04"}],
    "uy_quyen": [{"index": 16, "name": "phải có văn bản về việc ủy quyền"}],
}
_SKIP = {"cccd"}
_ALLOWED = set(_ROUTES) | _SKIP | {"other"}

_DISPLAY = {
    "gcn": "Giấy chứng nhận quyền sử dụng đất",
    "don_mau_01": "Đơn theo Mẫu số 01",
    "don_mau_04": "Đơn theo Mẫu số 04",
    "uy_quyen": "Văn bản ủy quyền",
    "cccd": "Căn cước công dân",
}


def _normalize_doc_type(value: Any) -> str:
    folded = _fold(str(value or ""))
    for doc_type in _ALLOWED:
        if folded == _fold(doc_type):
            return doc_type
    return "other"


def _rule_doc_type(text: str) -> str:
    """Fallback chỉ dùng dấu hiệu tài liệu có độ tin cậy cao."""
    folded = _fold(text or "")
    if not folded:
        return ""
    if "don xin gia han su dung dat" in folded or ("mau so 04" in folded and "su dung dat" in folded):
        return "don_mau_04"
    if (
        "don theo mau so 01" in folded
        or ("mau so 01" in folded and "giao dat" in folded)
        or "don de nghi cho phep chuyen muc dich su dung dat" in folded
    ):
        return "don_mau_01"
    if "ben duoc uy quyen" in folded or "giay uy quyen" in folded or "hop dong uy quyen" in folded:
        return "uy_quyen"
    if "mau so 26" in folded and "tang dat mat" in folded:
        return "phuong_an_tang_dat_mat"
    if "giay chung nhan quyen su dung dat" in folded and ("thua dat" in folded or "so vao so" in folded):
        return "gcn"
    if "can cuoc cong dan" in folded or "citizen identity card" in folded:
        return "cccd"
    return ""


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
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


def _routes_for_doc_type(doc_type: str, dossier_types: set[str]) -> tuple[list[dict[str, Any]], str]:
    if doc_type != "gcn":
        return _ROUTES[doc_type], ""

    has_mau_01 = "don_mau_01" in dossier_types
    has_mau_04 = "don_mau_04" in dossier_types
    if has_mau_01 and not has_mau_04:
        return [_GCN_CHUYEN_MUC_DICH_ROUTE], ""
    if has_mau_04 and not has_mau_01:
        return [_GCN_GIA_HAN_ROUTE], ""
    if has_mau_01 and has_mau_04:
        return [], "hồ sơ đồng thời có Đơn Mẫu số 01 và Đơn Mẫu số 04"
    return [], "không xác định được nhánh từ Đơn Mẫu số 01 hoặc Đơn Mẫu số 04"


def _build_items(file: dict, file_index: int, doc_type: str, routes: list[dict[str, Any]]) -> list[dict]:
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    document_name = _DISPLAY.get(doc_type) or routes[0]["name"]
    return [
        {
            "fileIndex": file_index,
            "fileName": file_name,
            "documentName": document_name,
            "componentName": route["name"],
            "componentIndex": route["index"],
            "loaiBan": _LOAI_BAN,
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": doc_type,
        }
        for route in routes
    ]


def build_plan_items(files: list[dict], ocr_results: list[dict], llm_types: dict[int, str] | None = None):
    llm_types = llm_types or {}
    ocr_by_name = {item.get("name"): item for item in ocr_results}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    resolved: list[tuple[int, dict, str, str, str]] = []
    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        text = str(ocr_by_name.get(file_name, {}).get("text") or "")
        llm_type = llm_types.get(index, "")
        rule_type = _rule_doc_type(text)
        if llm_type in _ROUTES or llm_type in _SKIP:
            doc_type, source = llm_type, "llm"
        elif rule_type:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = "other", "unknown"

        resolved.append((index, file, file_name, doc_type, source))

    dossier_types = {doc_type for _, _, _, doc_type, _ in resolved}
    for index, file, file_name, doc_type, source in resolved:

        if doc_type in _ROUTES:
            routes, route_error = _routes_for_doc_type(doc_type, dossier_types)
            if route_error:
                warnings.append(
                    f"Không tự đính kèm '{file_name}': {route_error} — vui lòng chọn đúng thành phần thủ công."
                )
                classified.append({"fileName": file_name, "docType": doc_type, "source": source,
                                   "skipped": True, "reason": "unresolved_branch"})
                continue
            items = _build_items(file, index, doc_type, routes)
            attachments.extend(items)
            classified.append({"fileName": file_name, "docType": doc_type, "source": source,
                               "componentIndexes": [item["componentIndex"] for item in items]})
        elif doc_type in _SKIP:
            classified.append({"fileName": file_name, "docType": doc_type, "source": source, "skipped": True})
        else:
            warnings.append(f"Không xác định được loại giấy tờ cho file '{file_name}' — vui lòng đính kèm thủ công.")
            classified.append({"fileName": file_name, "docType": "other", "source": source, "skipped": True})
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
