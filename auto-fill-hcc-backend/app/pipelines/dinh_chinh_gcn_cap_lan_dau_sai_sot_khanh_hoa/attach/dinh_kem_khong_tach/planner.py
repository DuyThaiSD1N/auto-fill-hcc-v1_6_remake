"""Đính kèm KHÔNG TÁCH cho 4 dòng thành phần hồ sơ trên cổng iGate Khánh Hòa (1.012796-01) — cài đặt tách tắt.

Bảng 4 dòng (mat-checkbox + radio Bản chính/Bản sao + "Chọn tệp tin", engine FE `attp-row`), tên dòng theo DOM cổng
Khánh Hòa (file mapping, Phần IV), cột "Tên giấy tờ" đúng thứ tự; chỗ đặt từng giấy theo ảnh ánh xạ đính kèm:

  dòng 1: Bản gốc Giấy chứng nhận đã cấp.                 -> KHÔNG đính, bỏ tích (bản gốc giấy nộp trực tiếp khi cơ quan
                                                             yêu cầu)
  dòng 2: Giấy tờ chứng minh sai sót thông tin …          -> gcn + bang_chung (giấy khai sinh, bản sao chứng thực…) +
                                                             cu_tru + giấy không rõ loại (1 Bản chính)
  dòng 3: Văn bản về việc ủy quyền …                       -> authorization; không có thì bỏ tích
  dòng 4: Đơn đăng ký biến động … theo Mẫu số 18           -> don_bien_dong + identity (CCCD, kể cả bản sao chứng thực)
                                                             (1 Bản chính) — Đơn mục 3 kê khai CCCD kèm Đơn

Cổng tick sẵn cả 4 dòng → mọi mục gửi `untickUnplannedRows`: FE bỏ tích hết rồi chỉ tích lại dòng có tệp (dòng 1 luôn
trống, dòng 3 trống khi tự nộp). componentIndex = STT (FE thử rows[componentIndex - 1] trước rồi mới so tên).

MỖI FILE ĐÍNH NGUYÊN KHỐI, MỘT LẦN, vào dòng của giấy chính trong file theo _PRIORITY (Đơn thắng). LLM liệt kê mọi loại
giấy trong file để chọn dòng và báo cán bộ những giấy nằm chung file. OCR phân loại dùng lại cách của đăng ký đất đai lần
đầu Khánh Hòa (chữ đủ trang từ cache bước điền); chữ gửi LLM là trích đoạn đầu TỪNG trang.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.documents import representative_excerpt
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.attach.planner import _LLM_TEXT_MAX_CHARS, _ocr_for_classify
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON = "don_bien_dong"
_GCN = "gcn"
_BANG_CHUNG = "bang_chung"
_CU_TRU = "cu_tru"
_IDENTITY = "identity"
_AUTHORIZATION = "authorization"
_OTHER = "other"

_SAI_SOT_ROW = 2
_UY_QUYEN_ROW = 3
_DON_ROW = 4

# STT -> dòng trên cổng. name là đoạn chữ của cột "Tên giấy tờ" (FE so khớp chuỗi con sau khi bỏ dấu); dòng 1 không
# nhận tệp nào nên không khai.
_ROWS: dict[int, dict[str, str]] = {
    _SAI_SOT_ROW: {"name": "Giấy tờ chứng minh sai sót thông tin của người được cấp Giấy chứng nhận",
                   "documentName": "Giấy tờ chứng minh sai sót thông tin", "loaiBan": "Bản chính"},
    _UY_QUYEN_ROW: {"name": "Văn bản về việc ủy quyền", "documentName": "Văn bản ủy quyền", "loaiBan": "Bản chính"},
    _DON_ROW: {"name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18",
               "documentName": "Đơn đăng ký biến động đất đai (Mẫu số 18)", "loaiBan": "Bản chính"},
}

# Loại giấy -> dòng nhận file + tên giấy khi đính nguyên file.
_TYPE_ROW: dict[str, int] = {
    _GCN: _SAI_SOT_ROW,
    _BANG_CHUNG: _SAI_SOT_ROW,
    _CU_TRU: _SAI_SOT_ROW,
    _AUTHORIZATION: _UY_QUYEN_ROW,
    _DON: _DON_ROW,
    _IDENTITY: _DON_ROW,
}
_TYPE_NAME: dict[str, str] = {
    _GCN: "Giấy chứng nhận đã cấp",
    _BANG_CHUNG: "Giấy tờ chứng minh sai sót thông tin",
    _CU_TRU: "Giấy xác nhận thông tin về cư trú",
    _AUTHORIZATION: "Văn bản ủy quyền",
    _DON: "Đơn đăng ký biến động đất đai (Mẫu số 18)",
    _IDENTITY: "Căn cước công dân",
}
# File gộp nhiều giấy: dòng của giấy ĐỨNG TRƯỚC nhận nguyên file. Đơn luôn thắng.
_PRIORITY: tuple[str, ...] = (_DON, _AUTHORIZATION, _GCN, _BANG_CHUNG, _CU_TRU, _IDENTITY)
_ALLOWED = set(_TYPE_ROW) | {_OTHER}

_MISSING: tuple[tuple[str, str], ...] = (
    (_GCN, "Hồ sơ chưa có Giấy chứng nhận đã cấp cần đính chính (đính ở dòng 2) — cán bộ bổ sung."),
    (_DON, "Hồ sơ chưa có Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18) ghi nội dung đính chính "
           "(dòng 4) — cán bộ bổ sung."),
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


def row_of(doc_type: str) -> int:
    """Giấy không rõ loại vào dòng 2 (giấy tờ chứng minh) để cán bộ soát."""
    return _TYPE_ROW.get(doc_type, _SAI_SOT_ROW)


def missing_warnings(present: set[str]) -> list[str]:
    return [message for doc_type, message in _MISSING if doc_type not in present]


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, list[str]]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=900, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    result: dict[int, list[str]] = {}
    for item in parsed.get("documents", []) or []:
        try:
            result[int(item.get("index"))] = _doc_types(item)
        except (TypeError, ValueError, AttributeError):
            continue
    return result


def attachment_item(file_index: int, file_name: str, row: int, document_name: str, doc_type: str) -> dict:
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": _ROWS[row]["name"],
        "componentIndex": row,
        "loaiBan": _ROWS[row]["loaiBan"],
        "target": "attp-row",
        # Cổng tick sẵn cả 4 dòng → FE bỏ tích hết trước khi đính, chỉ dòng có tệp được tích lại (dòng 1 bản gốc GCN
        # luôn bỏ tích, dòng 3 bỏ tích khi không có ủy quyền).
        "untickUnplannedRows": True,
        "needsAddComponent": False,
        "detectedType": doc_type,
    }


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
        present.update(doc_types)
        doc_type = next((item for item in _PRIORITY if item in doc_types), _OTHER)

        if doc_type == _OTHER:
            # Không nhận diện được: không bỏ file mà đính dòng 2, giữ TÊN FILE GỐC để cán bộ soát.
            attachments.append(attachment_item(index, file_name, _SAI_SOT_ROW, file_name, _OTHER))
            warnings.append(f"Chưa nhận diện chắc loại giấy tờ cho '{file_name}' — tạm đính vào dòng {_SAI_SOT_ROW} "
                            "(Giấy tờ chứng minh sai sót); cán bộ kiểm tra lại.")
            classified.append({"fileName": file_name, "docType": _OTHER, "docTypes": doc_types,
                               "source": "llm" if raw_types else "unknown", "rows": [_SAI_SOT_ROW]})
            continue

        row = row_of(doc_type)
        # Giấy có dòng RIÊNG nhưng nằm chung file với giấy chính: đính nguyên file một lần, báo cán bộ.
        others = sorted({row_of(item) for item in doc_types if item in _TYPE_ROW} - {row})
        # File gộp giữ tên gốc để cán bộ nhận ra đó là cả bộ hồ sơ, không chỉ một giấy.
        name = file_name if others else _TYPE_NAME[doc_type]
        attachments.append(attachment_item(index, file_name, row, name, doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "docTypes": doc_types, "source": "llm",
                           "rows": [row]})
        if others:
            warnings.append(f"'{file_name}' gộp nhiều giấy tờ — đính nguyên file một lần vào dòng {row} "
                            f"({_ROWS[row]['documentName']}), không tách sang dòng "
                            f"{', '.join(str(item) for item in others)}.")

    if files:
        warnings.extend(missing_warnings(present))
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
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
        {"index": index, "text": representative_excerpt(str(by_name[file.get("name")].get("text")),
                                                        _LLM_TEXT_MAX_CHARS)}
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
