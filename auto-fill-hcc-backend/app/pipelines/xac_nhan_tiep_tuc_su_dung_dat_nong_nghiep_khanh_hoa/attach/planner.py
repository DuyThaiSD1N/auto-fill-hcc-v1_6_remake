"""Lập kế hoạch đính kèm cho 2 dòng thành phần hồ sơ trên cổng iGate Khánh Hòa (1.013947) + nút "Thêm giấy tờ".

Bảng 2 dòng (mat-checkbox + radio Bản chính/Bản sao + "Chọn tệp tin", engine FE `attp-row`), thứ tự DOM theo ảnh ánh xạ
hồ sơ (quy trình 1.013947-1.1):

  STT1 : Văn bản đề nghị xác nhận lại thời hạn sử dụng đất theo Mẫu số 09   -> don_de_nghi
  STT2 : (2) Giấy chứng nhận đã cấp.,                                       -> gcn + manh_trich_do (ĐÍNH CHUNG)
  "+ Thêm giấy tờ": Đơn đăng ký biến động Mẫu 18, văn bản ủy quyền, CCCD, giấy chưa nhận diện -> add-document-dialog,
                    không tạo được dòng thì đính chung dòng 1.

Ánh xạ hồ sơ: form không có dòng riêng cho Phiếu đo đạc chỉnh lý; phiếu đo cho chính thửa đất của Giấy chứng nhận nên đính
CÙNG dòng 2 — hai item cùng componentName để FE gom vào một lần "Chọn tệp tin". componentIndex = STT. MỖI FILE ĐÍNH NGUYÊN
KHỐI, KHÔNG TÁCH TRANG. KHÔNG set Bản chính/Bản sao ở dòng có sẵn: giữ loại bản mặc định của cổng.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.attach.planner import (
    _LLM_TEXT_MAX_CHARS,
    _ocr_for_classify,
    plan_theo_cai_dat_tach,
)
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON = "don_de_nghi"
_GCN = "gcn"
_MANH_TRICH_DO = "manh_trich_do"
_DON_BIEN_DONG = "don_bien_dong"
_AUTHORIZATION = "authorization"
_IDENTITY = "identity"
_OTHER = "other"

_DON_ROW = 1
_DON_NAME = "Văn bản đề nghị xác nhận lại thời hạn sử dụng đất"
_GCN_NAME = "Giấy chứng nhận đã cấp"

_ROUTES: dict[str, dict[str, Any]] = {
    _DON: {"row": _DON_ROW, "name": _DON_NAME,
           "documentName": "Đơn xin xác nhận lại thời hạn sử dụng đất nông nghiệp"},
    _GCN: {"row": 2, "name": _GCN_NAME, "documentName": "Giấy chứng nhận đã cấp"},
    # Không có dòng riêng: đính chung dòng Giấy chứng nhận (cùng componentName -> FE gom một lần chọn tệp).
    _MANH_TRICH_DO: {"row": 2, "name": _GCN_NAME, "documentName": "Phiếu đo đạc chỉnh lý thửa đất"},
}

# Giấy không có dòng trong bảng -> tạo dòng qua modal "Thêm giấy tờ". FE thử lần lượt formOptionHints (cụ thể -> chung)
# rồi componentName; không tạo được dòng thì đính chung dòng 1 (fallbackComponentName).
_ADD_DOCUMENTS: dict[str, dict[str, Any]] = {
    _DON_BIEN_DONG: {
        "componentName": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất",
        "formOptionHints": ["Đơn đăng ký biến động", "Giấy tờ khác"],
        "documentName": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18)",
        "loaiBan": "Bản chính",
    },
    _AUTHORIZATION: {
        "componentName": "Văn bản ủy quyền",
        "formOptionHints": ["Văn bản ủy quyền", "Giấy ủy quyền", "Hợp đồng ủy quyền", "Giấy tờ khác"],
        "documentName": "Văn bản ủy quyền/đại diện",
        "loaiBan": "Bản chính",
    },
    _IDENTITY: {
        "componentName": "Căn cước công dân",
        "formOptionHints": ["Căn cước công dân", "Căn cước", "Giấy tờ tùy thân", "Giấy tờ khác"],
        "documentName": "Căn cước công dân (bản sao)",
        "loaiBan": "Bản sao",
    },
}
_OTHER_DOCUMENT = {"formOptionHints": ["Giấy tờ khác"], "loaiBan": "Bản sao"}

# File gộp nhiều giấy: chỗ của giấy ĐỨNG TRƯỚC nhận nguyên file.
_PRIORITY: tuple[str, ...] = (_DON, _GCN, _MANH_TRICH_DO, _DON_BIEN_DONG, _AUTHORIZATION, _IDENTITY)
_ALLOWED = set(_ROUTES) | set(_ADD_DOCUMENTS) | {_OTHER}

_REQUIRED_DOCS: tuple[tuple[str, str], ...] = (
    (_DON, "Hồ sơ chưa có Đơn xin xác nhận lại thời hạn sử dụng đất nông nghiệp (dòng 1) — cán bộ bổ sung."),
    (_GCN, "Hồ sơ chưa có Giấy chứng nhận đã cấp (dòng 2) — cán bộ bổ sung."),
)


def _normalize_doc_type(value: Any) -> str:
    folded = _fold(str(value or ""))
    for doc_type in _ALLOWED:
        if folded == _fold(doc_type):
            return doc_type
    return _OTHER


def _doc_types(item: dict) -> list[str]:
    raw = item.get("docTypes")
    if raw is None:
        raw = item.get("docType") or item.get("type")
    if not isinstance(raw, list):
        raw = [raw]
    out: list[str] = []
    for value in raw:
        doc_type = _normalize_doc_type(value)
        if doc_type not in out:
            out.append(doc_type)
    return out


def _primary(doc_types: list[str]) -> str:
    for doc_type in _PRIORITY:
        if doc_type in doc_types:
            return doc_type
    return _OTHER


def _place_key(doc_type: str) -> tuple[str, Any]:
    if doc_type in _ADD_DOCUMENTS:
        return ("add", doc_type)
    return ("row", _ROUTES[doc_type]["row"])


def _place(doc_type: str) -> str:
    """Chỗ đính của một loại giấy, để báo cán bộ khi giấy đó nằm chung file với giấy chính."""
    if doc_type in _ADD_DOCUMENTS:
        return f"{_ADD_DOCUMENTS[doc_type]['documentName']} (nút Thêm giấy tờ)"
    route = _ROUTES[doc_type]
    return f"{route['documentName']} (dòng {route['row']})"


def _add_document(index: int, file_name: str, group: dict, document_name: str, doc_type: str) -> dict:
    return {
        "fileIndex": index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": group.get("componentName") or document_name,
        "formOptionHints": list(group["formOptionHints"]),
        "loaiBan": group["loaiBan"],
        "quantity": 1,
        "target": "add-document-dialog",
        "needsAddComponent": True,
        "fallbackComponentName": _DON_NAME,
        "detectedType": doc_type,
    }


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, list[str]]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=600, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    result: dict[int, list[str]] = {}
    for item in parsed.get("documents", []) or []:
        try:
            result[int(item.get("index"))] = _doc_types(item)
        except (TypeError, ValueError, AttributeError):
            continue
    return result


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict] | None = None,
    llm_types: dict[int, list[str] | str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    del ocr_results  # LLM-first: không suy luận rule từ OCR text ở đây.
    llm_types = llm_types or {}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    present: set[str] = set()

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        raw_types = llm_types.get(index)
        doc_types = _doc_types({"docTypes": raw_types}) if raw_types else []
        doc_type = _primary(doc_types)
        present.update(doc_types)

        if doc_type in _ADD_DOCUMENTS:
            group = _ADD_DOCUMENTS[doc_type]
            attachments.append(_add_document(index, file_name, group, group["documentName"], doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "docTypes": doc_types, "source": "llm",
                               "addDocument": True})
        elif doc_type in _ROUTES:
            route = _ROUTES[doc_type]
            attachments.append({
                "fileIndex": index,
                "fileName": file_name,
                "documentName": route["documentName"],
                "componentName": route["name"],
                "componentIndex": route["row"],
                "target": "attp-row",
                "needsAddComponent": False,
                "detectedType": doc_type,
            })
            classified.append({"fileName": file_name, "docType": doc_type, "docTypes": doc_types, "source": "llm",
                               "componentIndex": route["row"]})
        else:
            # Không nhận diện được: không bỏ file mà thêm dòng "Giấy tờ khác" mang TÊN FILE GỐC để cán bộ soát.
            attachments.append(_add_document(index, file_name, _OTHER_DOCUMENT, file_name, _OTHER))
            warnings.append(f"Chưa nhận diện chắc loại giấy tờ cho '{file_name}' — tạm thêm qua nút 'Thêm giấy tờ'; cán "
                            "bộ kiểm tra lại.")
            classified.append({"fileName": file_name, "docType": _OTHER, "docTypes": doc_types,
                               "source": "llm" if raw_types else "unknown", "addDocument": True})
            continue

        # Giấy có chỗ RIÊNG nhưng nằm chung file với giấy chính: đính nguyên file một lần, báo cán bộ không đính lại.
        place = _place_key(doc_type)
        bundled = []
        for other in doc_types:
            if other == doc_type or other not in _PRIORITY or other == _IDENTITY:
                continue  # giấy nhân thân đi kèm file nào cũng được
            if _place_key(other) != place and _place(other) not in bundled:
                bundled.append(_place(other))
        if bundled:
            warnings.append(f"'{file_name}' gộp nhiều giấy tờ — đính nguyên file một lần, không tải lại sang: "
                            f"{'; '.join(bundled)}.")

    if files:
        warnings.extend(message for doc_type, message in _REQUIRED_DOCS if doc_type not in present)
    return attachments, warnings, classified


async def _plan_theo_tep(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    ocr_files = [item for item in raw_files if item.get("type") in _OCR_TYPES]
    errors: list[str] = []

    started = time.monotonic()
    ocr_results = await _ocr_for_classify(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    llm_documents = [
        {"index": index, "text": str(by_name.get(file.get("name"), {}).get("text") or "")[:_LLM_TEXT_MAX_CHARS]}
        for index, file in enumerate(raw_files)
        if str(by_name.get(file.get("name"), {}).get("text") or "").strip()
    ]
    started = time.monotonic()
    llm_types: dict[int, list[str]] = {}
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


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    """Bật "Có tách hồ sơ khi đính kèm" → PDF gộp cắt từng giấy rồi mới xếp dòng (plan_theo_cai_dat_tach)."""
    return await plan_theo_cai_dat_tach(_plan_theo_tep, files, options, session)
