"""Lập kế hoạch đính kèm cho 3 dòng thành phần hồ sơ trên cổng iGate Khánh Hòa (1.012790-1.1) + nút "Thêm giấy tờ".

Bảng 3 dòng (mat-checkbox + "Chọn tệp tin", engine FE `attp-row`), đúng thứ tự DOM theo ảnh ánh xạ hồ sơ:

  STT1 : "+ Bản gốc Giấy chứng nhận đã cấp;"                     chưa tick, 1 Bản chính -> gcn
  STT2 : "+ Giấy tờ chứng minh sai sót thông tin …"              chưa tick, 1 Bản sao   -> CÙNG TỆP gcn (trang IV ghi
                                                                  sai sót) + CCCD, giấy xác nhận cư trú, giấy chứng minh
  STT3 : "- Văn bản về việc ủy quyền …"                           TICK SẴN, 1 Bản sao   -> authorization; không có thì
                                                                  gửi untickRows để FE bỏ tick
  "+ Thêm giấy tờ": Đơn đăng ký biến động (Mẫu số 27)             -> add-document-dialog, không tạo được dòng thì đính
                                                                  chung dòng 2

componentIndex = STT (FE thử rows[componentIndex - 1] trước rồi mới dò tên). MỖI FILE ĐÍNH NGUYÊN KHỐI, KHÔNG TÁCH TRANG.
File Giấy chứng nhận đính HAI LẦN: dòng 1 và dòng 2 (ảnh ánh xạ: "đính kèm chung với dòng 1 – cùng 1 tệp, không tách").
LLM liệt kê mọi loại giấy trong file, planner chọn chỗ theo _PRIORITY rồi cảnh báo giấy có chỗ riêng mà nằm chung file.
KHÔNG set Bản chính/Bản sao: số bản mặc định của cổng đã đúng ánh xạ.
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
_IDENTITY = "identity"
_CU_TRU = "cu_tru"
_BANG_CHUNG = "bang_chung"
_AUTHORIZATION = "authorization"
_OTHER = "other"

_GCN_ROW = 1
_SAI_SOT_ROW = 2
_UY_QUYEN_ROW = 3
_GCN_NAME = "Bản gốc Giấy chứng nhận đã cấp"
_SAI_SOT_NAME = "Giấy tờ chứng minh sai sót thông tin"
_UY_QUYEN_NAME = "Văn bản về việc ủy quyền"

_ROUTES: dict[str, dict[str, Any]] = {
    _GCN: {"row": _GCN_ROW, "name": _GCN_NAME, "documentName": "Bản gốc Giấy chứng nhận đã cấp"},
    _IDENTITY: {"row": _SAI_SOT_ROW, "name": _SAI_SOT_NAME, "documentName": "Căn cước công dân"},
    _CU_TRU: {"row": _SAI_SOT_ROW, "name": _SAI_SOT_NAME, "documentName": "Giấy xác nhận thông tin về cư trú"},
    _BANG_CHUNG: {"row": _SAI_SOT_ROW, "name": _SAI_SOT_NAME, "documentName": "Giấy tờ chứng minh sai sót thông tin"},
    _AUTHORIZATION: {"row": _UY_QUYEN_ROW, "name": _UY_QUYEN_NAME, "documentName": "Văn bản ủy quyền"},
}
# Bản thứ hai của file Giấy chứng nhận ở dòng 2: trang IV "Những thay đổi…" ghi rõ nội dung sai sót.
_GCN_COPY = {"row": _SAI_SOT_ROW, "name": _SAI_SOT_NAME,
             "documentName": "Giấy chứng nhận đã cấp (thể hiện thông tin sai sót)"}

# Đơn không có dòng trong bảng -> tạo dòng qua modal "Thêm giấy tờ". FE thử lần lượt formOptionHints rồi componentName;
# không tạo được dòng thì đính chung dòng 2 (fallbackComponentName).
_ADD_DOCUMENT = {
    "componentName": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất",
    "formOptionHints": ["Đơn đăng ký biến động đất đai", "Đơn đăng ký biến động", "Đơn đề nghị đính chính",
                        "Giấy tờ khác"],
    "documentName": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 27)",
}

# File gộp nhiều giấy: chỗ của giấy ĐỨNG TRƯỚC nhận nguyên file.
_PRIORITY: tuple[str, ...] = (_GCN, _DON, _AUTHORIZATION, _CU_TRU, _IDENTITY, _BANG_CHUNG)
_ALLOWED = set(_PRIORITY) | {_OTHER}

_MISSING: tuple[tuple[str, str], ...] = (
    (_GCN, "Hồ sơ chưa có Bản gốc Giấy chứng nhận đã cấp (dòng 1) — giấy bắt buộc của thủ tục đính chính, cán bộ bổ "
           "sung."),
    (_DON, "Hồ sơ chưa có Đơn đăng ký biến động đất đai (Mẫu số 27) ghi nội dung đính chính — cán bộ bổ sung qua nút "
           "Thêm giấy tờ."),
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


def _rows_of(doc_type: str) -> set[int]:
    """Các dòng một loại giấy chiếm (Đơn = nút Thêm giấy tờ, ghi 0)."""
    if doc_type == _DON:
        return {0}
    if doc_type == _GCN:
        return {_GCN_ROW, _SAI_SOT_ROW}
    return {_ROUTES[doc_type]["row"]}


def _place(doc_type: str) -> str:
    if doc_type == _DON:
        return f"{_ADD_DOCUMENT['documentName']} (nút Thêm giấy tờ)"
    route = _ROUTES[doc_type]
    return f"{route['documentName']} (dòng {route['row']})"


def _row_item(index: int, file_name: str, route: dict, doc_type: str) -> dict:
    return {
        "fileIndex": index,
        "fileName": file_name,
        "documentName": route["documentName"],
        "componentName": route["name"],
        "componentIndex": route["row"],
        "target": "attp-row",
        "needsAddComponent": False,
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

        if doc_type == _DON:
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
                "fallbackComponentName": _SAI_SOT_NAME,
                "detectedType": doc_type,
            })
            classified.append({"fileName": file_name, "docType": doc_type, "docTypes": doc_types, "source": "llm",
                               "addDocument": True})
        elif doc_type in _ROUTES:
            attachments.append(_row_item(index, file_name, _ROUTES[doc_type], doc_type))
            if doc_type == _GCN:
                attachments.append(_row_item(index, file_name, _GCN_COPY, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "docTypes": doc_types, "source": "llm",
                               "componentIndex": _ROUTES[doc_type]["row"]})
        else:
            # Không nhận diện được: không bỏ file mà đính chung dòng 2, giữ TÊN FILE GỐC để cán bộ soát.
            attachments.append(_row_item(index, file_name, {**_ROUTES[_BANG_CHUNG], "documentName": file_name}, _OTHER))
            warnings.append(
                f"Chưa nhận diện chắc loại giấy tờ cho '{file_name}' — tạm đính vào dòng {_SAI_SOT_ROW} (Giấy tờ chứng "
                "minh sai sót); cán bộ kiểm tra lại."
            )
            classified.append({"fileName": file_name, "docType": _OTHER, "docTypes": doc_types,
                               "source": "llm" if raw_types else "unknown", "routedTo": _SAI_SOT_ROW})
            continue

        # Giấy có chỗ RIÊNG nhưng nằm chung file với giấy chính: đính nguyên file một lần, báo cán bộ không đính lại.
        placed = _rows_of(doc_type)
        bundled = [_place(other) for other in doc_types
                   if other != doc_type and other in _PRIORITY and not _rows_of(other) <= placed]
        if bundled:
            warnings.append(f"'{file_name}' gộp nhiều giấy tờ — đính nguyên file một lần, không tách sang: "
                            f"{'; '.join(dict.fromkeys(bundled))}.")

    if files:
        warnings.extend(message for doc_type, message in _MISSING if doc_type not in present)
    # Dòng 3 cổng tick sẵn: tự nộp (không có văn bản ủy quyền) thì FE bỏ tick, không chặn chuyển bước.
    if attachments and _AUTHORIZATION not in present:
        attachments[0]["untickRows"] = [_UY_QUYEN_NAME]
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
