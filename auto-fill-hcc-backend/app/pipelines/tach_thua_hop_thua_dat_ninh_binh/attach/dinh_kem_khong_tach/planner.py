"""Đính kèm KHÔNG TÁCH cho thủ tục tách thửa hoặc hợp thửa đất (iGate Ninh Bình, 1.012784) — cài đặt tách tắt.

Bảng "Thành phần hồ sơ" 4 dòng (mat-checkbox + radio "1 Bản chính"/"1 Bản sao" + "Chọn tệp tin", engine FE `attp-row`), tên
dòng và thứ tự theo file mapping Phần IV; chỗ đặt từng giấy theo ảnh ánh xạ đính kèm:

  dòng 1: (2) Bản vẽ tách thửa đất, hợp thửa đất lập theo Mẫu số 02/ĐK …   -> ban_ve + giay_phep_do_dac (giấy phép của đơn
                                                                           vị đo đạc lập bản vẽ đính CHUNG dòng bản vẽ)
  dòng 2: (3) Giấy chứng nhận đã cấp hoặc bản sao Giấy chứng nhận đã cấp …  -> gcn
  dòng 3: (4) Các văn bản của cơ quan có thẩm quyền … (nếu có)               -> van_ban_cqctq; không có thì để trống
  dòng 4: (1) Đơn đề nghị tách thửa đất, hợp thửa đất theo Mẫu số 01/ĐK      -> don_tach_thua + giấy không rõ loại
  "+ Thêm giấy tờ": văn bản ủy quyền, CCCD                                   -> add-document-dialog; modal không tạo được
                                                                               dòng thì FE đính chung dòng 4 (Đơn)

Loại bản: "1 Bản chính" (cổng chọn sẵn). Dòng chưa tích sẵn nên không gửi cờ bỏ tích. componentIndex = STT (FE thử
rows[componentIndex - 1] trước rồi mới so tên); mục "Thêm giấy tờ" không mang componentIndex (dòng tạo mới).

MỖI FILE ĐÍNH NGUYÊN KHỐI, MỘT LẦN, vào chỗ của giấy chính trong file theo _PRIORITY (Đơn thắng). LLM liệt kê mọi loại giấy
trong file để chọn chỗ và báo cán bộ những giấy nằm chung file. OCR phân loại dùng lại cách của đăng ký đất đai lần đầu
Khánh Hòa (chữ đủ trang từ cache bước điền); chữ gửi LLM là trích đoạn đầu TỪNG trang.
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

_DON = "don_tach_thua"
_BAN_VE = "ban_ve"
_GIAY_PHEP = "giay_phep_do_dac"
_GCN = "gcn"
_VAN_BAN = "van_ban_cqctq"
_AUTHORIZATION = "authorization"
_IDENTITY = "identity"
_OTHER = "other"

_BAN_VE_ROW = 1
_GCN_ROW = 2
_VAN_BAN_ROW = 3
_DON_ROW = 4

# STT -> dòng trên cổng. name là đoạn chữ ĐẶC TRƯNG của cột "Tên giấy tờ" (FE so khớp chuỗi con sau khi bỏ dấu).
_ROWS: dict[int, dict[str, str]] = {
    _BAN_VE_ROW: {"name": "Bản vẽ tách thửa đất, hợp thửa đất lập theo Mẫu số 02/ĐK",
                  "documentName": "Bản vẽ tách thửa đất, hợp thửa đất", "loaiBan": "Bản chính"},
    _GCN_ROW: {"name": "Giấy chứng nhận đã cấp hoặc bản sao Giấy chứng nhận đã cấp",
               "documentName": "Giấy chứng nhận đã cấp", "loaiBan": "Bản chính"},
    _VAN_BAN_ROW: {"name": "Các văn bản của cơ quan có thẩm quyền có thể hiện nội dung tách thửa đất, hợp thửa đất",
                   "documentName": "Văn bản của cơ quan có thẩm quyền về tách thửa, hợp thửa", "loaiBan": "Bản chính"},
    _DON_ROW: {"name": "Đơn đề nghị tách thửa đất, hợp thửa đất theo Mẫu số 01/ĐK",
               "documentName": "Đơn đề nghị tách thửa đất, hợp thửa đất (Mẫu số 01/ĐK)", "loaiBan": "Bản chính"},
}

# Loại giấy có dòng sẵn trong bảng -> STT.
_TYPE_ROW: dict[str, int] = {
    _BAN_VE: _BAN_VE_ROW,
    _GIAY_PHEP: _BAN_VE_ROW,
    _GCN: _GCN_ROW,
    _VAN_BAN: _VAN_BAN_ROW,
    _DON: _DON_ROW,
}
# Loại giấy không có dòng -> tạo dòng qua modal "+ Thêm giấy tờ" (FE thử lần lượt formOptionHints rồi componentName).
_ADD_DOCUMENT: dict[str, dict[str, Any]] = {
    _AUTHORIZATION: {"componentName": "Văn bản ủy quyền",
                     "formOptionHints": ["Văn bản ủy quyền", "Giấy ủy quyền", "Hợp đồng ủy quyền", "Giấy tờ khác"]},
    _IDENTITY: {"componentName": "Căn cước công dân",
                "formOptionHints": ["Căn cước công dân", "Căn cước", "Giấy tờ tùy thân", "Giấy tờ khác"]},
}
_TYPE_NAME: dict[str, str] = {
    _BAN_VE: "Bản vẽ tách thửa đất, hợp thửa đất",
    _GIAY_PHEP: "Giấy phép hoạt động đo đạc và bản đồ",
    _GCN: "Giấy chứng nhận đã cấp",
    _VAN_BAN: "Văn bản của cơ quan có thẩm quyền về tách thửa, hợp thửa",
    _DON: "Đơn đề nghị tách thửa đất, hợp thửa đất (Mẫu số 01/ĐK)",
    _AUTHORIZATION: "Văn bản ủy quyền",
    _IDENTITY: "Căn cước công dân",
}
# File gộp nhiều giấy: chỗ của giấy ĐỨNG TRƯỚC nhận nguyên file. Đơn luôn thắng.
_PRIORITY: tuple[str, ...] = (_DON, _BAN_VE, _GCN, _VAN_BAN, _GIAY_PHEP, _AUTHORIZATION, _IDENTITY)
_ALLOWED = set(_PRIORITY) | {_OTHER}

_MISSING: tuple[tuple[str, str], ...] = (
    (_DON, "Hồ sơ chưa có Đơn đề nghị tách thửa đất, hợp thửa đất (Mẫu số 01/ĐK, dòng 4) — cán bộ bổ sung."),
    (_BAN_VE, "Hồ sơ chưa có Bản vẽ tách thửa đất, hợp thửa đất (dòng 1) — cán bộ bổ sung."),
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


def row_of(doc_type: str) -> int:
    """STT dòng nhận giấy; 0 = dòng tạo qua "+ Thêm giấy tờ". Giấy không rõ loại vào dòng Đơn để cán bộ soát."""
    if doc_type in _ADD_DOCUMENT:
        return 0
    return _TYPE_ROW.get(doc_type, _DON_ROW)


def place_label(doc_type: str) -> str:
    row = row_of(doc_type)
    return f"dòng {row}" if row else f"nút Thêm giấy tờ ({_ADD_DOCUMENT[doc_type]['componentName']})"


def missing_warnings(present: set[str]) -> list[str]:
    warnings = [message for doc_type, message in _MISSING if doc_type not in present]
    if _BAN_VE in present and _GIAY_PHEP not in present:
        warnings.append("Chưa thấy Giấy phép hoạt động đo đạc và bản đồ của đơn vị lập bản vẽ — bản vẽ do đơn vị đo đạc "
                        "lập thì phải đính kèm chung dòng 1; cán bộ kiểm tra lại.")
    return warnings


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


def attachment_item(file_index: int, file_name: str, doc_type: str, document_name: str) -> dict:
    """Mục đính kèm vào dòng có sẵn (attp-row) hoặc dòng tạo qua "+ Thêm giấy tờ" (add-document-dialog)."""
    if doc_type in _ADD_DOCUMENT:
        add = _ADD_DOCUMENT[doc_type]
        return {
            "fileIndex": file_index,
            "fileName": file_name,
            "documentName": document_name,
            "componentName": add["componentName"],
            "formOptionHints": list(add["formOptionHints"]),
            "loaiBan": "Bản chính",
            "quantity": 1,
            "target": "add-document-dialog",
            "needsAddComponent": True,
            "fallbackComponentName": _ROWS[_DON_ROW]["name"],
            "detectedType": doc_type,
        }
    row = row_of(doc_type)
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": _ROWS[row]["name"],
        "componentIndex": row,
        "loaiBan": _ROWS[row]["loaiBan"],
        "target": "attp-row",
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
            # Không nhận diện được: không bỏ file mà đính dòng Đơn, giữ TÊN FILE GỐC để cán bộ soát.
            attachments.append(attachment_item(index, file_name, _OTHER, file_name))
            warnings.append(f"Chưa nhận diện chắc loại giấy tờ cho '{file_name}' — tạm đính vào dòng {_DON_ROW} (Đơn đề "
                            "nghị tách thửa, hợp thửa); cán bộ kiểm tra lại.")
            classified.append({"fileName": file_name, "docType": _OTHER, "docTypes": doc_types,
                               "source": "llm" if raw_types else "unknown", "place": f"dòng {_DON_ROW}"})
            continue

        place = place_label(doc_type)
        # Giấy có chỗ RIÊNG nhưng nằm chung file với giấy chính: đính nguyên file một lần, báo cán bộ.
        others = sorted({place_label(item) for item in doc_types if item in _ALLOWED and item != _OTHER} - {place})
        # File gộp giữ tên gốc để cán bộ nhận ra đó là cả bộ hồ sơ, không chỉ một giấy.
        name = file_name if others else _TYPE_NAME[doc_type]
        attachments.append(attachment_item(index, file_name, doc_type, name))
        classified.append({"fileName": file_name, "docType": doc_type, "docTypes": doc_types, "source": "llm",
                           "place": place})
        if others:
            warnings.append(f"'{file_name}' gộp nhiều giấy tờ — đính nguyên file một lần vào {place}, không tách sang "
                            f"{', '.join(others)}.")

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
