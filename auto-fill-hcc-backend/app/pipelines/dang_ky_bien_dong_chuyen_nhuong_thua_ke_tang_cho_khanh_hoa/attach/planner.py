"""Lập kế hoạch đính kèm cho 13 dòng thành phần hồ sơ trên cổng iGate Khánh Hòa (1.013831) + nút "Thêm giấy tờ".

Bảng 13 dòng (mat-checkbox + radio Bản chính/Bản sao + "Chọn tệp tin", engine FE `attp-row`), thứ tự DOM theo file
mapping; chỉ dòng 3 (Bản gốc GCN) cổng tick sẵn:

  STT1 : Mảnh trích đo bản đồ địa chính thửa đất …                 -> manh_trich_do (kể cả phiếu đo đạc chỉnh lý)
  STT2 : Văn bản của bên nhận thế chấp đồng ý chuyển nhượng …       -> van_ban_the_chap
  STT3 : Bản gốc Giấy chứng nhận đã cấp.                            -> gcn
  STT4 : Hợp đồng hoặc văn bản về việc chuyển quyền …               -> hop_dong_chuyen_quyen (HĐ, văn bản thừa kế)
  STT5 : Văn bản thỏa thuận cấp chung một Giấy chứng nhận           -> thoa_thuan_cap_chung
  STT6 : … tài sản gắn liền với đất thuê trả tiền hằng năm          -> dat_thue_hang_nam
  STT7 : Đơn đăng ký biến động … theo Mẫu số 18                     -> don_bien_dong (+ CCCD, giấy tờ nhân thân)
  STT8 : Văn bản cho thuê, cho thuê lại QSDĐ trong dự án hạ tầng    -> cho_thue_ha_tang
  STT9 : Văn bản người sử dụng đất đồng ý cho chủ sở hữu tài sản    -> dong_y_chu_tai_san
  STT10: Văn bản về việc đại diện theo pháp luật dân sự             -> authorization
  STT11: Bản vẽ tách thửa, hợp thửa theo Mẫu số 22                  -> ban_ve_tach_hop_thua
  STT12: Văn bản tặng cho/biên bản họp với đại diện thôn, tổ dân phố -> tang_cho_cong_dong (tặng cho Nhà nước/cộng đồng)
  STT13: Ghi chú "biên bản họp với UBND cấp xã … chỉ nộp bản gốc GCN" -> KHÔNG route (câu hướng dẫn, không phải giấy)
  "+ Thêm giấy tờ": tờ khai lệ phí trước bạ/thuế TNCN (một dòng); giấy nộp tiền, quyết định xử phạt (một dòng khác)
                    -> add-document-dialog, không tạo được dòng thì đính chung dòng Đơn.

componentIndex = STT (FE thử rows[componentIndex - 1] trước rồi mới dò tên — tên dòng 3 cũng nằm trong chữ dòng 12, 13).
MỖI FILE ĐÍNH NGUYÊN KHỐI, KHÔNG TÁCH TRANG (ánh xạ hồ sơ: file 26 trang gộp văn bản thỏa thuận phân chia di sản + hợp
đồng tặng cho + văn bản phân chia di sản đính chung dòng 4). KHÔNG set Bản chính/Bản sao ở dòng có sẵn: giữ loại bản
mặc định của cổng.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.attach.planner import _LLM_TEXT_MAX_CHARS, _ocr_for_classify
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_MANH_TRICH_DO = "manh_trich_do"
_VB_THE_CHAP = "van_ban_the_chap"
_GCN = "gcn"
_HOP_DONG = "hop_dong_chuyen_quyen"
_CAP_CHUNG = "thoa_thuan_cap_chung"
_DAT_THUE = "dat_thue_hang_nam"
_DON = "don_bien_dong"
_CHO_THUE = "cho_thue_ha_tang"
_DONG_Y_TAI_SAN = "dong_y_chu_tai_san"
_AUTHORIZATION = "authorization"
_BAN_VE = "ban_ve_tach_hop_thua"
_TANG_CHO_CONG_DONG = "tang_cho_cong_dong"
_IDENTITY = "identity"
_TO_KHAI_THUE = "to_khai_thue"
_CHUNG_TU_NOP_TIEN = "chung_tu_nop_tien"
_QUYET_DINH_XU_PHAT = "quyet_dinh_xu_phat"
_OTHER = "other"

_DON_ROW = 7
_DON_NAME = "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18"

_ROUTES: dict[str, dict[str, Any]] = {
    _MANH_TRICH_DO: {
        "row": 1,
        "name": "Mảnh trích đo bản đồ địa chính thửa đất",
        "documentName": "Mảnh trích đo/phiếu đo đạc chỉnh lý thửa đất",
    },
    _VB_THE_CHAP: {
        "row": 2,
        "name": "Văn bản của bên nhận thế chấp",
        "documentName": "Văn bản bên nhận thế chấp đồng ý chuyển quyền",
    },
    _GCN: {"row": 3, "name": "Bản gốc Giấy chứng nhận đã cấp", "documentName": "Bản gốc Giấy chứng nhận đã cấp"},
    _HOP_DONG: {
        "row": 4,
        "name": "Hợp đồng hoặc văn bản về việc chuyển quyền sử dụng đất",
        "documentName": "Hợp đồng/văn bản chuyển quyền sử dụng đất",
    },
    _CAP_CHUNG: {
        "row": 5,
        "name": "Văn bản thỏa thuận về việc cấp chung một Giấy chứng nhận",
        "documentName": "Văn bản thỏa thuận cấp chung một Giấy chứng nhận",
    },
    _DAT_THUE: {
        "row": 6,
        "name": "về việc bán hoặc tặng cho hoặc để thừa kế hoặc góp vốn bằng tài sản gắn liền với đất",
        "documentName": "Hợp đồng/văn bản về tài sản gắn liền với đất thuê trả tiền hằng năm",
    },
    _DON: {
        "row": _DON_ROW,
        "name": _DON_NAME,
        "documentName": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất",
    },
    _CHO_THUE: {
        "row": 8,
        "name": "Văn bản về việc cho thuê, cho thuê lại quyền sử dụng đất",
        "documentName": "Văn bản cho thuê, cho thuê lại quyền sử dụng đất",
    },
    _DONG_Y_TAI_SAN: {
        "row": 9,
        "name": "Văn bản của người sử dụng đất đồng ý cho chủ sở hữu tài sản",
        "documentName": "Văn bản người sử dụng đất đồng ý cho chủ sở hữu tài sản",
    },
    _AUTHORIZATION: {
        "row": 10,
        "name": "Văn bản về việc đại diện theo quy định của pháp luật về dân sự",
        "documentName": "Văn bản ủy quyền/đại diện",
    },
    _BAN_VE: {
        "row": 11,
        "name": "Bản vẽ tách thửa đất, hợp thửa đất",
        "documentName": "Bản vẽ tách thửa đất, hợp thửa đất",
    },
    _TANG_CHO_CONG_DONG: {
        "row": 12,
        "name": "biên bản họp giữa đại diện thôn",
        "documentName": "Văn bản tặng cho/biên bản họp về tặng cho quyền sử dụng đất",
    },
    # Không có dòng riêng -> đính chung dòng Đơn, documentName để cán bộ phân biệt.
    _IDENTITY: {"row": _DON_ROW, "name": _DON_NAME, "documentName": "Giấy tờ nhân thân, hộ tịch"},
}

# Giấy không có dòng trong bảng -> tạo dòng qua modal "Thêm giấy tờ" (ánh xạ hồ sơ). FE thử lần lượt formOptionHints
# (cụ thể -> chung) rồi componentName; không tạo được dòng thì đính chung dòng Đơn (fallbackComponentName).
_ADD_DOCUMENTS: dict[str, dict[str, Any]] = {
    _TO_KHAI_THUE: {
        "componentName": "Tờ khai lệ phí trước bạ, tờ khai thuế thu nhập cá nhân",
        "formOptionHints": ["Tờ khai lệ phí trước bạ", "Tờ khai thuế thu nhập cá nhân", "Tờ khai thuế", "Giấy tờ khác"],
        "documentName": "Tờ khai lệ phí trước bạ, thuế thu nhập cá nhân",
    },
    _CHUNG_TU_NOP_TIEN: {
        "componentName": "Chứng từ nộp tiền, quyết định xử phạt vi phạm hành chính",
        "formOptionHints": ["Chứng từ thực hiện nghĩa vụ tài chính", "Giấy nộp tiền", "Biên lai", "Giấy tờ khác"],
        "documentName": "Giấy nộp tiền, quyết định xử phạt vi phạm hành chính",
    },
}
_ADD_GROUP = {_TO_KHAI_THUE: _TO_KHAI_THUE, _CHUNG_TU_NOP_TIEN: _CHUNG_TU_NOP_TIEN,
              _QUYET_DINH_XU_PHAT: _CHUNG_TU_NOP_TIEN}

# File gộp nhiều giấy: chỗ của giấy ĐỨNG TRƯỚC nhận nguyên file.
_PRIORITY: tuple[str, ...] = (
    _DON, _GCN, _HOP_DONG, _MANH_TRICH_DO, _BAN_VE, _VB_THE_CHAP, _CAP_CHUNG, _DAT_THUE, _CHO_THUE, _DONG_Y_TAI_SAN,
    _TANG_CHO_CONG_DONG, _AUTHORIZATION, _TO_KHAI_THUE, _CHUNG_TU_NOP_TIEN, _QUYET_DINH_XU_PHAT, _IDENTITY,
)
_ALLOWED = set(_ROUTES) | set(_ADD_GROUP) | {_OTHER}

# Giấy cốt lõi của thủ tục -> lời nhắc khi hồ sơ không có (dòng 3 cổng tick sẵn).
_REQUIRED_DOCS: tuple[tuple[str, str], ...] = (
    (_GCN, "Hồ sơ chưa có Bản gốc Giấy chứng nhận đã cấp (dòng 3, cổng tick sẵn) — cán bộ bổ sung."),
    (_HOP_DONG, "Hồ sơ chưa có hợp đồng/văn bản chuyển quyền (chuyển nhượng, tặng cho, thừa kế) cho dòng 4 — cán bộ "
                "kiểm tra."),
    (_DON, "Hồ sơ chưa có Đơn đăng ký biến động đất đai (dòng 7) — cán bộ bổ sung."),
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
    if doc_type in _ADD_GROUP:
        return ("add", _ADD_GROUP[doc_type])
    return ("row", _ROUTES[doc_type]["row"])


def _place(doc_type: str) -> str:
    """Chỗ đính của một loại giấy, để báo cán bộ khi giấy đó nằm chung file với giấy chính."""
    if doc_type in _ADD_GROUP:
        return f"{_ADD_DOCUMENTS[_ADD_GROUP[doc_type]]['documentName']} (nút Thêm giấy tờ)"
    route = _ROUTES[doc_type]
    return f"{route['documentName']} (dòng {route['row']})"


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

        if doc_type in _ADD_GROUP:
            group = _ADD_DOCUMENTS[_ADD_GROUP[doc_type]]
            attachments.append({
                "fileIndex": index,
                "fileName": file_name,
                "documentName": group["documentName"],
                "componentName": group["componentName"],
                "formOptionHints": list(group["formOptionHints"]),
                "loaiBan": "Bản chính",
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

        # Giấy có chỗ RIÊNG nhưng nằm chung file với giấy chính: đính nguyên file một lần, báo cán bộ không đính lại.
        place = _place_key(doc_type)
        bundled = []
        for other in doc_types:
            if other == doc_type or other not in _PRIORITY or other == _IDENTITY:
                continue  # giấy nhân thân không có dòng riêng, đi kèm file nào cũng được
            if _place_key(other) != place and _place(other) not in bundled:
                bundled.append(_place(other))
        if bundled:
            warnings.append(f"'{file_name}' gộp nhiều giấy tờ — đính nguyên file một lần, không tách sang: "
                            f"{'; '.join(bundled)}.")

    if files:
        warnings.extend(message for doc_type, message in _REQUIRED_DOCS if doc_type not in present)
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
