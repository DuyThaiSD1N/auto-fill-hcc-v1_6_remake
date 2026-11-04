"""Lập kế hoạch đính kèm cho 15 dòng thành phần hồ sơ trên cổng iGate Khánh Hòa (1.013949) + nút "Thêm giấy tờ".

Bảng 15 dòng (mat-checkbox + radio Bản chính/Bản sao + "Chọn tệp tin", engine FE `attp-row`) cùng danh mục với cổng
Quảng Ngãi cùng mã; componentName lấy theo tên dòng đã đối chiếu nguyên văn ở pipeline Quảng Ngãi:

  index 0  (STT1)  : Dự án đầu tư đối với khu rừng đề nghị giao              -> du_an_giao_rung
  index 1  (STT2)  : Kết quả đấu giá thuê rừng                               -> dau_gia_thue_rung
  index 2  (STT3)  : Văn bản phê duyệt kết quả lựa chọn nhà đầu tư           -> ket_qua_lua_chon_nha_dau_tu
  index 3  (STT4)  : Phương án sử dụng tầng đất mặt Mẫu số 26                -> phuong_an_tang_dat_mat
  index 4  (STT5)  : Văn bản phê duyệt dự án đầu tư, chấp thuận chủ trương    -> van_ban_phe_duyet_dau_tu
  index 5  (STT6)  : "Một trong các loại giấy tờ sau" (nhóm đầu tư)          -> giay_to_dau_tu_tong_hop
  index 6-8 (STT7-9): Phương án sử dụng đất (tổ chức kinh tế / đất thu hồi / công ty nông, lâm nghiệp)
  index 9  (STT10) : TRÙNG dòng STT6                                         -> BỎ
  index 10 (STT11) : GCN cho trường hợp gia hạn                              -> BỎ (GCN chỉ đính dòng 13, theo ánh xạ)
  index 11 (STT12) : Đơn đề nghị gia hạn sử dụng đất                         -> don_gia_han
  index 12 (STT13) : Giấy chứng nhận/giấy tờ Điều 137/quyết định giao đất    -> gcn
  index 13 (STT14) : Đơn đề nghị giao đất/thuê đất/chuyển mục đích ...       -> don_de_nghi (+ CCCD, tờ khai, đơn khác)
  index 14 (STT15) : TRÙNG dòng STT4                                         -> BỎ
  "+ Thêm giấy tờ"  : Giấy ủy quyền, giấy giới thiệu                          -> authorization (modal, dự phòng dòng 14)

MỖI FILE ĐÍNH NGUYÊN KHỐI, KHÔNG TÁCH TRANG (ánh xạ hồ sơ: file UQ gộp 2 giấy ủy quyền + giấy giới thiệu đính chung
qua "Thêm giấy tờ"). LLM liệt kê mọi loại giấy trong file, planner chọn dòng theo _PRIORITY rồi cảnh báo những giấy có
chỗ riêng mà nằm chung file. OCR phân loại dùng lại cách của đăng ký đất đai lần đầu Khánh Hòa: chữ đủ trang từ cache
bước điền, chưa có cache thì vài trang đầu. KHÔNG set Bản chính/Bản sao ở các dòng có sẵn: cán bộ tự chọn.
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

_DON_DE_NGHI = "don_de_nghi"
_DON_GIA_HAN = "don_gia_han"
_GCN = "gcn"
_AUTHORIZATION = "authorization"
_DU_AN_GIAO_RUNG = "du_an_giao_rung"
_DAU_GIA_THUE_RUNG = "dau_gia_thue_rung"
_KET_QUA_LUA_CHON_NHA_DAU_TU = "ket_qua_lua_chon_nha_dau_tu"
_PHUONG_AN_TANG_DAT_MAT = "phuong_an_tang_dat_mat"
_VAN_BAN_PHE_DUYET_DAU_TU = "van_ban_phe_duyet_dau_tu"
_GIAY_TO_DAU_TU_TONG_HOP = "giay_to_dau_tu_tong_hop"
_PHUONG_AN_TO_CHUC_KINH_TE = "phuong_an_to_chuc_kinh_te"
_PHUONG_AN_DAT_THU_HOI = "phuong_an_dat_thu_hoi"
_PHUONG_AN_CONG_TY_NONG_LAM = "phuong_an_cong_ty_nong_lam"
_DON_BIEN_DONG = "don_bien_dong"
_DON_THAM_DINH_NHU_CAU = "don_tham_dinh_nhu_cau"
_TO_KHAI_THUE = "to_khai_thue"
_IDENTITY = "identity"
_OTHER = "other"

_DON_DE_NGHI_NAME = (
    "Đơn đề nghị giao đất/thuê đất/chuyển mục đích sử dụng đất/giao đất và giao rừng/cho thuê đất và cho thuê rừng"
)
_DON_DE_NGHI_INDEX = 13

_ROUTES: dict[str, dict[str, Any]] = {
    _DU_AN_GIAO_RUNG: {
        "index": 0,
        "name": "Dự án đầu tư đối với khu rừng đề nghị giao",
        "documentName": "Dự án đầu tư khu rừng đề nghị giao",
    },
    _DAU_GIA_THUE_RUNG: {
        "index": 1,
        "name": "Kết quả đấu giá thuê rừng; biên bản đấu giá cho thuê rừng",
        "documentName": "Kết quả đấu giá thuê rừng",
    },
    _KET_QUA_LUA_CHON_NHA_DAU_TU: {
        "index": 2,
        "name": "Bản sao văn bản phê duyệt kết quả lựa chọn nhà đầu tư của cơ quan nhà nước có thẩm quyền",
        "documentName": "Văn bản phê duyệt kết quả lựa chọn nhà đầu tư",
    },
    _PHUONG_AN_TANG_DAT_MAT: {
        # STT4 và STT15 trùng text -> chỉ dòng chính STT4.
        "index": 3,
        "name": "Phương án sử dụng tầng đất mặt theo Mẫu số 26",
        "documentName": "Phương án sử dụng tầng đất mặt (Mẫu số 26)",
    },
    _VAN_BAN_PHE_DUYET_DAU_TU: {
        "index": 4,
        "name": "Bản sao văn bản phê duyệt dự án đầu tư, quyết định chấp thuận chủ trương đầu tư",
        "documentName": "Văn bản phê duyệt dự án đầu tư/chấp thuận chủ trương đầu tư",
    },
    _GIAY_TO_DAU_TU_TONG_HOP: {
        # STT6 và STT10 trùng text -> chỉ dòng chính STT6.
        "index": 5,
        "name": "Một trong các loại giấy tờ sau",
        "documentName": "Giấy tờ nhóm đầu tư/đấu giá/nhận chuyển nhượng dự án",
    },
    _PHUONG_AN_TO_CHUC_KINH_TE: {
        "index": 6,
        "name": (
            "Bản sao Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối với tổ chức kinh tế"
        ),
        "documentName": "Phương án sử dụng đất của tổ chức kinh tế/đơn vị sự nghiệp công lập",
    },
    _PHUONG_AN_DAT_THU_HOI: {
        "index": 7,
        "name": (
            "Bản sao Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối với diện tích đất "
            "thu hồi"
        ),
        "documentName": "Phương án sử dụng diện tích đất thu hồi của công ty nông, lâm nghiệp",
    },
    _PHUONG_AN_CONG_TY_NONG_LAM: {
        "index": 8,
        "name": "Bản sao Phương án sử dụng đất của công ty nông, lâm nghiệp tại địa phương",
        "documentName": "Phương án sử dụng đất của công ty nông, lâm nghiệp tại địa phương",
    },
    _DON_GIA_HAN: {
        "index": 11,
        "name": "Đơn đề nghị gia hạn sử dụng đất",
        "documentName": "Đơn đề nghị gia hạn sử dụng đất",
    },
    _GCN: {
        # Ánh xạ hồ sơ: GCN chỉ đính dòng 13, KHÔNG đính trùng dòng 11 (dòng 11 dành cho hồ sơ gia hạn).
        "index": 12,
        "name": "Một trong các giấy chứng nhận quy định tại khoản 21 Điều 3, khoản 3 Điều 256 Luật Đất đai",
        "documentName": "Giấy chứng nhận quyền sử dụng đất",
    },
    _DON_DE_NGHI: {
        "index": _DON_DE_NGHI_INDEX,
        "name": _DON_DE_NGHI_NAME,
        "documentName": "Đơn đề nghị giao đất/thuê đất/chuyển mục đích sử dụng đất",
    },
    # Không có dòng riêng -> đính chung dòng Đơn đề nghị, documentName để cán bộ phân biệt.
    _DON_BIEN_DONG: {
        "index": _DON_DE_NGHI_INDEX,
        "name": _DON_DE_NGHI_NAME,
        "documentName": "Đơn đăng ký biến động đất đai",
    },
    _DON_THAM_DINH_NHU_CAU: {
        "index": _DON_DE_NGHI_INDEX,
        "name": _DON_DE_NGHI_NAME,
        "documentName": "Đơn đề nghị thẩm định nhu cầu sử dụng đất",
    },
    _TO_KHAI_THUE: {
        "index": _DON_DE_NGHI_INDEX,
        "name": _DON_DE_NGHI_NAME,
        "documentName": "Tờ khai thuế/lệ phí trước bạ",
    },
    _IDENTITY: {
        "index": _DON_DE_NGHI_INDEX,
        "name": _DON_DE_NGHI_NAME,
        "documentName": "Giấy tờ nhân thân (CCCD/căn cước)",
    },
}

# Giấy ủy quyền/giấy giới thiệu không có dòng trong bảng -> tạo dòng qua modal "Thêm giấy tờ" (ánh xạ hồ sơ). Modal
# bắt chọn một mục trong danh mục giấy tờ của cổng: FE thử lần lượt formOptionHints rồi componentName; không tạo được
# dòng thì đính chung dòng Đơn đề nghị (fallbackComponentName) và nhắc cán bộ ghi chú.
_ADD_DOCUMENT = {
    "componentName": "Giấy ủy quyền",
    "formOptionHints": ["Giấy ủy quyền", "Văn bản ủy quyền", "Hợp đồng ủy quyền", "ủy quyền", "Giấy tờ khác"],
    "documentName": "Giấy ủy quyền/giấy giới thiệu người nộp",
}

# File gộp nhiều giấy: chỗ của giấy ĐỨNG TRƯỚC nhận nguyên file. Đơn luôn thắng, rồi GCN, giấy tờ dự án/phương án,
# giấy ủy quyền, cuối cùng các giấy không có dòng riêng.
_PRIORITY: tuple[str, ...] = (
    _DON_DE_NGHI,
    _DON_GIA_HAN,
    _GCN,
    _VAN_BAN_PHE_DUYET_DAU_TU,
    _GIAY_TO_DAU_TU_TONG_HOP,
    _KET_QUA_LUA_CHON_NHA_DAU_TU,
    _DU_AN_GIAO_RUNG,
    _DAU_GIA_THUE_RUNG,
    _PHUONG_AN_TANG_DAT_MAT,
    _PHUONG_AN_TO_CHUC_KINH_TE,
    _PHUONG_AN_DAT_THU_HOI,
    _PHUONG_AN_CONG_TY_NONG_LAM,
    _AUTHORIZATION,
    _DON_BIEN_DONG,
    _DON_THAM_DINH_NHU_CAU,
    _TO_KHAI_THUE,
    _IDENTITY,
)
_ALLOWED = set(_ROUTES) | {_AUTHORIZATION, _OTHER}


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
    return f"{route['documentName']} (dòng {route['index'] + 1})"


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

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        raw_types = llm_types.get(index)
        doc_types = _doc_types({"docTypes": raw_types}) if raw_types else []
        doc_type = _primary(doc_types)

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
                "fallbackComponentName": _DON_DE_NGHI_NAME,
                "detectedType": doc_type,
            })
            classified.append({"fileName": file_name, "docType": doc_type, "docTypes": doc_types, "source": "llm",
                               "addDocument": True})
            place_index = None
        elif doc_type in _ROUTES:
            route = _ROUTES[doc_type]
            attachments.append({
                "fileIndex": index,
                "fileName": file_name,
                "documentName": route["documentName"],
                "componentName": route["name"],
                "componentIndex": route["index"],
                "target": "attp-row",
                "needsAddComponent": False,
                "detectedType": doc_type,
            })
            classified.append({"fileName": file_name, "docType": doc_type, "docTypes": doc_types, "source": "llm",
                               "componentIndex": route["index"]})
            place_index = route["index"]
        else:
            # Không nhận diện được: không bỏ file mà đính chung dòng Đơn đề nghị, giữ TÊN FILE GỐC để cán bộ soát.
            attachments.append({
                "fileIndex": index,
                "fileName": file_name,
                "documentName": file_name,
                "componentName": _DON_DE_NGHI_NAME,
                "componentIndex": _DON_DE_NGHI_INDEX,
                "target": "attp-row",
                "needsAddComponent": False,
                "detectedType": _OTHER,
            })
            warnings.append(
                f"Chưa nhận diện chắc loại giấy tờ cho '{file_name}' — tạm đính vào dòng {_DON_DE_NGHI_INDEX + 1} "
                f"(Đơn đề nghị); cán bộ kiểm tra lại."
            )
            classified.append({"fileName": file_name, "docType": _OTHER, "docTypes": doc_types,
                               "source": "llm" if raw_types else "unknown", "routedTo": _DON_DE_NGHI_INDEX})
            continue

        # Giấy có chỗ RIÊNG nhưng nằm chung file với giấy chính: đính nguyên file một lần, báo cán bộ không đính lại.
        bundled = []
        for other in doc_types:
            if other == doc_type or other not in _PRIORITY:
                continue
            other_index = None if other == _AUTHORIZATION else _ROUTES[other]["index"]
            if other_index == _DON_DE_NGHI_INDEX and other != _DON_DE_NGHI:
                continue  # giấy không có dòng riêng, vốn đã đính chung dòng Đơn
            if other_index != place_index and _place(other) not in bundled:
                bundled.append(_place(other))
        if bundled:
            warnings.append(f"'{file_name}' gộp nhiều giấy tờ — đính nguyên file một lần, không tách sang: "
                            f"{'; '.join(bundled)}.")

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
