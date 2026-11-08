"""Đính kèm KHÔNG TÁCH cho 8 dòng thành phần hồ sơ trên cổng iGate Tuyên Quang (1.012796) — cài đặt tách tắt.

Bảng 8 dòng (mat-checkbox + radio Bản chính/Bản sao + "Chọn tệp tin", engine FE `attp-row`), tên dòng lấy nguyên văn
từ file mapping (sheet "Đính chính GCN - Tuyên Quang", Phần III). Cổng lặp danh mục hai lần, chỉ khác dấu câu:

  dòng 1: - Bản gốc Giấy chứng nhận đã cấp;                 -> land_certificate
  dòng 2: - Giấy tờ chứng minh sai sót ... đã cấp           -> giay_to_chung_minh_sai_sot + identity (Bản sao)
  dòng 3: - Trường hợp ... thông qua người đại diện ...     -> authorization
  dòng 4: - Đơn ... theo Mẫu số 11/ĐK (bản chính) ...       -> don_mau_11
  dòng 5/6/7: lặp danh mục dòng 1/2/3                       -> KHÔNG đính (cả hai chế độ)
  dòng 8: Đơn ... theo Mẫu số 18                            -> don_mau_18 (+ file không nhận diện được)

componentIndex ở đây là STT (đếm từ 1) — FE tìm `rows[componentIndex - 1]` trước rồi mới so tên. Tên dòng 2 cũng khớp
dòng 6 (dòng 6 chỉ thêm dấu chấm cuối), nên chỉ số này là thứ giữ file ở đúng dòng 2.

MỖI FILE ĐÍNH NGUYÊN KHỐI, MỘT LẦN: cả bộ hồ sơ thường là MỘT file scan gộp (Đơn, hợp đồng, Giấy chứng nhận, giấy
khai sinh, CCCD, trích lục) — nguyên file vào dòng của giấy chính trong file theo _PRIORITY (có Đơn thì luôn là dòng
Đơn). LLM liệt kê mọi loại giấy trong file để chọn dòng và báo cán bộ những giấy nằm chung file. Dòng giấy tờ chứng
minh sai sót chọn "Bản sao", các dòng khác "Bản chính".

OCR phân loại dùng lại cách của đăng ký đất đai lần đầu Khánh Hòa: chữ đủ trang từ cache bước điền, chưa có cache thì
vài trang đầu. Chữ gửi LLM là trích đoạn đầu TỪNG trang để file gộp 10+ trang vẫn lộ đủ các giấy ở trang sau.
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

_DON_MAU_18 = "don_mau_18"
_DON_MAU_11 = "don_mau_11"
_LAND_CERTIFICATE = "land_certificate"
_ERROR_PROOF = "giay_to_chung_minh_sai_sot"
_IDENTITY = "identity"
_AUTHORIZATION = "authorization"
_OTHER = "other"

_ERROR_PROOF_TEXT = (
    "Giấy tờ chứng minh sai sót thông tin của người được cấp Giấy chứng nhận so với thông tin tại thời điểm đề nghị "
    "đính chính hoặc sai sót thông tin về thửa đất, tài sản gắn liền với đất so với thông tin trên Giấy chứng nhận đã cấp"
)

# STT -> dòng trên cổng. name là đoạn chữ của cột "Tên giấy tờ"; dòng 5/6/7 lặp dòng 1/2/3 nên không khai.
_ROWS: dict[int, dict[str, str]] = {
    1: {"name": "Bản gốc Giấy chứng nhận đã cấp;", "documentName": "Bản gốc Giấy chứng nhận đã cấp",
        "loaiBan": "Bản chính"},
    2: {"name": _ERROR_PROOF_TEXT, "documentName": "Giấy tờ chứng minh sai sót", "loaiBan": "Bản sao"},
    3: {"name": "Trường hợp người sử dụng đất, chủ sở hữu tài sản gắn liền với đất thực hiện thủ tục thông qua người "
                "đại diện",
        "documentName": "Văn bản ủy quyền", "loaiBan": "Bản chính"},
    4: {"name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 11/ĐK",
        "documentName": "Đơn đăng ký biến động đất đai (Mẫu số 11/ĐK)", "loaiBan": "Bản chính"},
    8: {"name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18",
        "documentName": "Đơn đăng ký biến động đất đai (Mẫu số 18)", "loaiBan": "Bản chính"},
}
_DON_ROW = 8

# Loại giấy -> dòng nhận file.
_TYPE_ROW: dict[str, int] = {
    _LAND_CERTIFICATE: 1,
    _ERROR_PROOF: 2,
    _IDENTITY: 2,  # CCCD là chứng cứ tên đúng đối chiếu với tên sai trên Giấy chứng nhận
    _AUTHORIZATION: 3,
    _DON_MAU_11: 4,
    _DON_MAU_18: _DON_ROW,
}
# File gộp nhiều giấy: dòng của giấy ĐỨNG TRƯỚC nhận nguyên file. Đơn luôn thắng.
_PRIORITY: tuple[str, ...] = (
    _DON_MAU_18, _DON_MAU_11, _LAND_CERTIFICATE, _ERROR_PROOF, _IDENTITY, _AUTHORIZATION,
)
_ALLOWED = set(_TYPE_ROW) | {_OTHER}


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


def _item(file_index: int, file_name: str, row: int, document_name: str, doc_type: str) -> dict:
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": _ROWS[row]["name"],
        "componentIndex": row,
        "loaiBan": _ROWS[row]["loaiBan"],
        "target": "attp-row",
        # Cổng iGate Tuyên Quang tick sẵn mọi dòng thành phần → FE bỏ tick hết trước khi đính, chỉ dòng có tệp được tick lại.
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

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        raw_types = llm_types.get(index)
        doc_types = _doc_types({"docTypes": raw_types}) if raw_types else []
        doc_type = next((item for item in _PRIORITY if item in doc_types), _OTHER)

        if doc_type == _OTHER:
            # Không nhận diện được: không bỏ file mà đính dòng Đơn, giữ TÊN FILE GỐC để cán bộ soát.
            attachments.append(_item(index, file_name, _DON_ROW, file_name, _OTHER))
            warnings.append(
                f"Chưa nhận diện chắc loại giấy tờ cho '{file_name}' — tạm đính vào dòng {_DON_ROW} (Đơn đăng ký "
                f"biến động Mẫu số 18); cán bộ kiểm tra lại."
            )
            classified.append({"fileName": file_name, "docType": _OTHER, "docTypes": doc_types,
                               "source": "llm" if raw_types else "unknown", "rows": [_DON_ROW]})
            continue

        row = _TYPE_ROW[doc_type]
        # Giấy có dòng RIÊNG nhưng nằm chung file với giấy chính: đính nguyên file một lần, báo cán bộ.
        others = sorted({_TYPE_ROW[item] for item in doc_types if item in _TYPE_ROW} - {row})
        # File gộp giữ tên gốc để cán bộ nhận ra đó là cả bộ hồ sơ, không chỉ một giấy.
        name = file_name if others else _ROWS[row]["documentName"]
        attachments.append(_item(index, file_name, row, name, doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "docTypes": doc_types, "source": "llm",
                           "rows": [row]})
        if others:
            warnings.append(
                f"'{file_name}' gộp nhiều giấy tờ — đính nguyên file một lần vào dòng {row} "
                f"({_ROWS[row]['documentName']}), không tách sang dòng {', '.join(str(item) for item in others)}."
            )

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
