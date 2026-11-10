"""Lập kế hoạch đính kèm cho 8 dòng thành phần hồ sơ trên cổng iGate Khánh Hòa (1.013995) + nút "Thêm giấy tờ".

Bảng 8 dòng (mat-checkbox + radio Bản chính/Bản sao + "Chọn tệp tin", engine FE `attp-row`), thứ tự DOM theo file
mapping 1.013995-1.1 (số trong ngoặc là thứ tự của danh mục quốc gia, KHÔNG phải STT trên cổng); cổng không tick sẵn
dòng nào:

  STT1 : (1) Đơn đăng ký biến động … theo Mẫu số 18                     -> don_bien_dong
  STT2 : (7) Mảnh trích đo bản đồ địa chính thửa đất …                  -> manh_trich_do
  STT3 : (8) Văn bản về việc đại diện theo pháp luật dân sự …           -> authorization
  STT4 : (6) Văn bản chấp thuận gia hạn thời hạn sở hữu nhà ở …          -> van_ban_gia_han
  STT5 : (4) Sơ đồ nhà ở, công trình xây dựng …                         -> so_do_nha (sơ đồ đứng riêng)
  STT6 : (2) Giấy chứng nhận đã cấp.                                    -> gcn
  STT7 : (3) Một trong các loại giấy tờ theo quy định tại các Điều 148, Điều 149 … -> giay_to_148_149 (giấy phép XD)
  STT8 : (5) Hồ sơ thiết kế xây dựng … đã được … thẩm định …            -> ho_so_thiet_ke (thẩm định / nghiệm thu)
  "+ Thêm giấy tờ": tờ khai lệ phí trước bạ; giấy nộp tiền/biên lai thuế; CCCD — mỗi loại một dòng (add-document-dialog,
                    không tạo được dòng thì đính chung dòng Đơn).

componentIndex = STT (FE thử rows[componentIndex - 1] trước rồi mới dò tên — dòng 5 cũng nhắc "một trong các loại giấy tờ
quy định tại các Điều 148" nên tên dòng 7 giữ chữ "theo"). MỖI FILE ĐÍNH NGUYÊN KHỐI, KHÔNG TÁCH TRANG (ánh xạ hồ sơ: file
giấy phép xây dựng + bìa hồ sơ thiết kế + bản vẽ 36 trang đính nguyên ở dòng 7; sơ đồ nhà nằm trong đó nên dòng 5 KHÔNG
tải lại). KHÔNG set Bản chính/Bản sao ở dòng có sẵn: giữ loại bản mặc định của cổng.
"""

import re
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
_MANH_TRICH_DO = "manh_trich_do"
_AUTHORIZATION = "authorization"
_GIA_HAN = "van_ban_gia_han"
_SO_DO = "so_do_nha"
_GCN = "gcn"
_GIAY_TO_148 = "giay_to_148_149"
_THIET_KE = "ho_so_thiet_ke"
_TO_KHAI_THUE = "to_khai_thue"
_CHUNG_TU_NOP_TIEN = "chung_tu_nop_tien"
_IDENTITY = "identity"
_OTHER = "other"

_DON_ROW = 1
_DON_NAME = "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18"

_ROUTES: dict[str, dict[str, Any]] = {
    _DON: {
        "row": _DON_ROW,
        "name": _DON_NAME,
        "documentName": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất",
    },
    _MANH_TRICH_DO: {
        "row": 2,
        "name": "Mảnh trích đo bản đồ địa chính thửa đất",
        "documentName": "Mảnh trích đo bản đồ địa chính thửa đất",
    },
    _AUTHORIZATION: {
        "row": 3,
        "name": "Văn bản về việc đại diện theo quy định của pháp luật về dân sự",
        "documentName": "Văn bản ủy quyền/đại diện",
    },
    _GIA_HAN: {
        "row": 4,
        "name": "Văn bản chấp thuận gia hạn thời hạn sở hữu nhà ở",
        "documentName": "Văn bản chấp thuận gia hạn thời hạn sở hữu nhà ở",
    },
    _SO_DO: {
        "row": 5,
        "name": "Sơ đồ nhà ở, công trình xây dựng",
        "documentName": "Sơ đồ nhà ở, công trình xây dựng",
    },
    _GCN: {"row": 6, "name": "Giấy chứng nhận đã cấp", "documentName": "Giấy chứng nhận đã cấp"},
    _GIAY_TO_148: {
        "row": 7,
        "name": "Một trong các loại giấy tờ theo quy định tại các Điều 148",
        "documentName": "Giấy phép xây dựng/giấy tờ về quyền sở hữu tài sản (Điều 148, 149 Luật Đất đai)",
    },
    _THIET_KE: {
        "row": 8,
        "name": "Hồ sơ thiết kế xây dựng",
        "documentName": "Hồ sơ thiết kế xây dựng đã thẩm định/văn bản chấp thuận nghiệm thu",
    },
}

# Giấy không có dòng trong bảng -> tạo dòng qua modal "Thêm giấy tờ" (ánh xạ hồ sơ: tờ khai và giấy nộp tiền mỗi thứ một
# dòng, CCCD cũng thêm ở đây). FE thử lần lượt formOptionHints (cụ thể -> chung) rồi componentName; không tạo được dòng
# thì đính chung dòng Đơn (fallbackComponentName).
_ADD_DOCUMENTS: dict[str, dict[str, Any]] = {
    _TO_KHAI_THUE: {
        "componentName": "Tờ khai lệ phí trước bạ",
        "formOptionHints": ["Tờ khai lệ phí trước bạ", "Tờ khai thuế", "Giấy tờ khác"],
        "documentName": "Tờ khai lệ phí trước bạ",
    },
    _CHUNG_TU_NOP_TIEN: {
        "componentName": "Giấy nộp tiền vào ngân sách nhà nước, biên lai thu thuế",
        "formOptionHints": ["Chứng từ thực hiện nghĩa vụ tài chính", "Giấy nộp tiền", "Biên lai", "Giấy tờ khác"],
        "documentName": "Giấy nộp tiền vào ngân sách nhà nước/biên lai thu thuế",
    },
    _IDENTITY: {
        "componentName": "Căn cước công dân",
        "formOptionHints": ["Căn cước công dân", "Căn cước", "Giấy tờ tùy thân", "Giấy tờ khác"],
        "documentName": "Căn cước công dân (bản sao)",
    },
}

# File gộp nhiều giấy: chỗ của giấy ĐỨNG TRƯỚC nhận nguyên file (giấy phép XD đứng trước sơ đồ/bản vẽ đi kèm).
_PRIORITY: tuple[str, ...] = (
    _DON, _GCN, _GIAY_TO_148, _GIA_HAN, _THIET_KE, _SO_DO, _MANH_TRICH_DO, _AUTHORIZATION, _TO_KHAI_THUE,
    _CHUNG_TU_NOP_TIEN, _IDENTITY,
)
_ALLOWED = set(_ROUTES) | set(_ADD_DOCUMENTS) | {_OTHER}

# Giấy cốt lõi của thủ tục -> lời nhắc khi hồ sơ không có (cổng không tick sẵn dòng nào).
_REQUIRED_DOCS: tuple[tuple[tuple[str, ...], str], ...] = (
    ((_DON,), "Hồ sơ chưa có Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (dòng 1) — cán bộ bổ sung."),
    ((_GCN,), "Hồ sơ chưa có Giấy chứng nhận đã cấp (dòng 6) — cán bộ bổ sung."),
    ((_GIAY_TO_148, _SO_DO, _THIET_KE, _GIA_HAN),
     "Hồ sơ chưa có giấy tờ về tài sản gắn liền với đất (giấy phép xây dựng — dòng 7, sơ đồ nhà ở — dòng 5, hồ sơ thiết "
     "kế đã thẩm định — dòng 8) — cán bộ kiểm tra."),
)
_IDENTITY_MISSING = ("Đơn có liệt kê Căn cước công dân (bản sao) nhưng hồ sơ chưa có file CCCD — cán bộ bổ sung qua nút "
                     "'Thêm giấy tờ'.")
# Mục giấy tờ kèm theo của Đơn ghi "Căn cước công dân (bản sao)" / "CCCD (bản sao)" (chữ đã fold dấu).
_DON_LISTS_IDENTITY = re.compile(r"(?:can cuoc(?: cong dan)?|cccd)\s*\(?\s*ban sao")


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


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, list[str]]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=700, enable_thinking=settings.agent_reasoning)
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
    """Loại giấy do LLM quyết; chữ OCR chỉ dùng để xem Đơn có liệt kê CCCD mà hồ sơ thiếu file hay không."""
    llm_types = llm_types or {}
    text_by_name = {item.get("name"): str(item.get("text") or "") for item in ocr_results or []}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    present: set[str] = set()
    don_lists_identity = False

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        raw_types = llm_types.get(index)
        doc_types = _doc_types({"docTypes": raw_types}) if raw_types else []
        doc_type = _primary(doc_types)
        present.update(doc_types)
        if _DON in doc_types and _DON_LISTS_IDENTITY.search(_fold(text_by_name.get(file.get("name"), ""))):
            don_lists_identity = True

        if doc_type in _ADD_DOCUMENTS:
            group = _ADD_DOCUMENTS[doc_type]
            attachments.append({
                "fileIndex": index,
                "fileName": file_name,
                "documentName": group["documentName"],
                "componentName": group["componentName"],
                "formOptionHints": list(group["formOptionHints"]),
                "loaiBan": "Bản sao" if doc_type == _IDENTITY else "Bản chính",
                "quantity": 1,
                "target": "add-document-dialog",
                "needsAddComponent": True,
                "fallbackComponentName": _DON_NAME,
                "detectedType": doc_type,
            })
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

        # Giấy có chỗ RIÊNG nằm chung file với giấy chính (vd sơ đồ nhà trong bộ bản vẽ kèm giấy phép xây dựng): đính
        # nguyên file một lần, báo cán bộ không tải lại ở dòng kia.
        place = _place_key(doc_type)
        bundled = []
        for other in doc_types:
            if other == doc_type or other not in _PRIORITY or other == _IDENTITY:
                continue  # giấy nhân thân đi kèm file nào cũng được
            if _place_key(other) != place and _place(other) not in bundled:
                bundled.append(_place(other))
        if bundled:
            where = f"dòng {_ROUTES[doc_type]['row']}" if doc_type in _ROUTES else "nút Thêm giấy tờ"
            warnings.append(f"'{file_name}' gộp nhiều giấy tờ — đính nguyên file một lần ở {where}, không tải lại sang: "
                            f"{'; '.join(bundled)}.")

    if files:
        warnings.extend(message for doc_types, message in _REQUIRED_DOCS if not present.intersection(doc_types))
        if don_lists_identity and _IDENTITY not in present:
            warnings.append(_IDENTITY_MISSING)
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
