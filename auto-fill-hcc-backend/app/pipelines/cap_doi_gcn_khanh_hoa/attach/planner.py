"""Lập kế hoạch đính kèm cho 4 dòng thành phần hồ sơ trên cổng iGate Khánh Hòa (1.012783) + nút "Thêm giấy tờ".

Bảng 4 dòng (mat-checkbox + radio Bản chính/Bản sao + "Chọn tệp tin", engine FE `attp-row`), đúng thứ tự DOM của cả hai
quy trình 1.012783-1.1 và 1.012783-1.2:

  STT1 : "(2) Bản gốc Giấy chứng nhận đã cấp."              tick sẵn, 1 Bản chính -> gcn
  STT2 : "Giấy chứng nhận quyền sử dụng đất; Giấy chứng …"   0 Bản chính, CÙNG LOẠI dòng 1 -> KHÔNG đính (ánh xạ hồ sơ)
  STT3 : "(3) Mảnh trích đo bản đồ địa chính thửa đất …"     tick sẵn, 1 Bản sao -> manh_trich_do
  STT4 : "(1) Đơn đăng ký biến động đất đai … Mẫu số 18"     tick sẵn, 1 Bản chính -> don_bien_dong (+ CCCD, tờ khai)
  "+ Thêm giấy tờ": giấy/hợp đồng ủy quyền                    -> authorization (modal, dự phòng dòng 4)

componentIndex = STT (FE thử rows[componentIndex - 1] trước rồi mới dò tên). MỖI FILE ĐÍNH NGUYÊN KHỐI, KHÔNG TÁCH TRANG
(ánh xạ hồ sơ: file GCN 4 trang gồm bìa, thửa đất và trang bổ sung đính nguyên vào dòng 1). LLM liệt kê mọi loại giấy
trong file, planner chọn dòng theo _PRIORITY rồi cảnh báo giấy có chỗ riêng mà nằm chung file. Dòng 1/3/4 cổng tick sẵn:
thiếu file của dòng nào thì nhắc cán bộ bổ sung hoặc bỏ tick. KHÔNG set Bản chính/Bản sao: số bản mặc định của cổng đã
đúng ánh xạ, cán bộ tự sửa nếu cần.
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

_DON = "don_bien_dong"
_GCN = "gcn"
_MANH_TRICH_DO = "manh_trich_do"
_AUTHORIZATION = "authorization"
_TO_KHAI_THUE = "to_khai_thue"
_IDENTITY = "identity"
_OTHER = "other"

_GCN_ROW = 1
_MANH_TRICH_DO_ROW = 3
_DON_ROW = 4
_DON_NAME = "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất"

_ROUTES: dict[str, dict[str, Any]] = {
    _GCN: {
        "row": _GCN_ROW,
        "name": "Bản gốc Giấy chứng nhận đã cấp",
        "documentName": "Bản gốc Giấy chứng nhận đã cấp",
    },
    _MANH_TRICH_DO: {
        "row": _MANH_TRICH_DO_ROW,
        "name": "Mảnh trích đo bản đồ địa chính thửa đất",
        "documentName": "Mảnh trích đo bản đồ địa chính thửa đất",
    },
    _DON: {
        "row": _DON_ROW,
        "name": _DON_NAME,
        "documentName": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất",
    },
    # Không có dòng riêng -> đính chung dòng Đơn, documentName để cán bộ phân biệt.
    _TO_KHAI_THUE: {"row": _DON_ROW, "name": _DON_NAME, "documentName": "Tờ khai thuế/lệ phí trước bạ"},
    _IDENTITY: {"row": _DON_ROW, "name": _DON_NAME, "documentName": "Giấy tờ nhân thân (CCCD/căn cước)"},
}

# Giấy ủy quyền không có dòng trong bảng -> tạo dòng qua modal "Thêm giấy tờ". FE thử lần lượt formOptionHints rồi
# componentName; không tạo được dòng thì đính chung dòng Đơn (fallbackComponentName).
_ADD_DOCUMENT = {
    "componentName": "Giấy ủy quyền",
    "formOptionHints": ["Giấy ủy quyền", "Văn bản ủy quyền", "Hợp đồng ủy quyền", "ủy quyền", "Giấy tờ khác"],
    "documentName": "Văn bản ủy quyền người nộp",
}

# File gộp nhiều giấy: chỗ của giấy ĐỨNG TRƯỚC nhận nguyên file.
_PRIORITY: tuple[str, ...] = (_DON, _GCN, _MANH_TRICH_DO, _AUTHORIZATION, _TO_KHAI_THUE, _IDENTITY)
_ALLOWED = set(_ROUTES) | {_AUTHORIZATION, _OTHER}

# Dòng cổng tick sẵn -> lời nhắc khi hồ sơ không có giấy nào cho dòng đó.
_TICKED_ROWS: tuple[tuple[str, str], ...] = (
    (_GCN, "Hồ sơ chưa có Bản gốc Giấy chứng nhận đã cấp (dòng 1) — giấy bắt buộc của thủ tục cấp đổi, cán bộ bổ sung."),
    (_MANH_TRICH_DO, "Dòng 3 (Mảnh trích đo bản đồ địa chính) cổng tick sẵn nhưng hồ sơ không có file — cán bộ bổ sung, "
                     "hoặc bỏ tick nếu không thuộc trường hợp đo đạc lại thửa đất."),
    (_DON, "Hồ sơ chưa có Đơn đăng ký biến động đất đai (dòng 4) — cán bộ bổ sung."),
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


def _place(doc_type: str) -> str:
    """Chỗ đính của một loại giấy, để báo cán bộ khi giấy đó nằm chung file với giấy chính."""
    if doc_type == _AUTHORIZATION:
        return f"{_ADD_DOCUMENT['documentName']} (nút Thêm giấy tờ)"
    route = _ROUTES[doc_type]
    return f"{route['documentName']} (dòng {route['row']})"


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

        if doc_type == _AUTHORIZATION:
            attachments.append({
                "fileIndex": index,
                "fileName": file_name,
                "documentName": _ADD_DOCUMENT["documentName"],
                "componentName": _ADD_DOCUMENT["componentName"],
                "formOptionHints": list(_ADD_DOCUMENT["formOptionHints"]),
                "loaiBan": "Bản chính",
                "quantity": 1,
                "target": "add-document-dialog",
                "needsAddComponent": True,
                "fallbackComponentName": _DON_NAME,
                "detectedType": doc_type,
            })
            classified.append({"fileName": file_name, "docType": doc_type, "docTypes": doc_types, "source": "llm",
                               "addDocument": True})
            place_row = None
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
            place_row = route["row"]
        else:
            # Không nhận diện được: không bỏ file mà đính chung dòng Đơn, giữ TÊN FILE GỐC để cán bộ soát.
            attachments.append({
                "fileIndex": index,
                "fileName": file_name,
                "documentName": file_name,
                "componentName": _DON_NAME,
                "componentIndex": _DON_ROW,
                "target": "attp-row",
                "needsAddComponent": False,
                "detectedType": _OTHER,
            })
            warnings.append(
                f"Chưa nhận diện chắc loại giấy tờ cho '{file_name}' — tạm đính vào dòng {_DON_ROW} (Đơn đăng ký biến "
                "động); cán bộ kiểm tra lại."
            )
            classified.append({"fileName": file_name, "docType": _OTHER, "docTypes": doc_types,
                               "source": "llm" if raw_types else "unknown", "routedTo": _DON_ROW})
            continue

        # Giấy có chỗ RIÊNG nhưng nằm chung file với giấy chính: đính nguyên file một lần, báo cán bộ không đính lại.
        bundled = []
        for other in doc_types:
            if other == doc_type or other not in _PRIORITY:
                continue
            other_row = None if other == _AUTHORIZATION else _ROUTES[other]["row"]
            if other_row == _DON_ROW and other != _DON:
                continue  # giấy không có dòng riêng, vốn đã đính chung dòng Đơn
            if other_row != place_row and _place(other) not in bundled:
                bundled.append(_place(other))
        if bundled:
            warnings.append(f"'{file_name}' gộp nhiều giấy tờ — đính nguyên file một lần, không tách sang: "
                            f"{'; '.join(bundled)}.")

    if files:
        warnings.extend(message for doc_type, message in _TICKED_ROWS if doc_type not in present)
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
