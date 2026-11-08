"""Đính kèm KHÔNG TÁCH cho 14 dòng thành phần hồ sơ trên cổng iGate Tuyên Quang (1.013949) — cài đặt tách tắt.

Bảng 14 dòng (mat-checkbox + radio Bản chính/Bản sao + "Chọn tệp tin", engine FE `attp-row`), tên dòng lấy nguyên văn
từ file mapping (cùng bảng ở cả hai form). componentIndex là STT (đếm từ 1) — FE tìm `rows[componentIndex - 1]` trước
rồi mới so tên, nên dòng 3 (phê duyệt dự án) không bị nhầm sang dòng 8 vốn chứa cùng câu đó:

  dòng 1 : văn bản phê duyệt kết quả lựa chọn nhà đầu tư       -> ket_qua_lua_chon_nha_dau_tu
  dòng 2 : Đơn theo Mẫu số 01                                    -> don_de_nghi (+ giấy ủy quyền, CCCD, giấy không rõ loại)
  dòng 3 : văn bản phê duyệt dự án đầu tư, chấp thuận chủ trương -> van_ban_phe_duyet_du_an
  dòng 4 : Giấy chứng nhận / giấy tờ Điều 137 / quyết định giao  -> gcn
  dòng 5 : phương án sử dụng tầng đất mặt (Mẫu số 26)            -> phuong_an_tang_dat_mat
  dòng 6 : dự án đầu tư khu rừng đề nghị giao                   -> du_an_giao_rung
  dòng 7 : kết quả đấu giá thuê rừng                             -> dau_gia_thue_rung
  dòng 8 : "Một trong các loại giấy tờ sau" (nhóm đầu tư)        -> giay_to_dau_tu_tong_hop
  dòng 9 : phương án sử dụng đất của công ty nông, lâm nghiệp    -> phuong_an_cong_ty_nong_lam
  dòng 10: phương án sử dụng diện tích đất thu hồi               -> phuong_an_dat_thu_hoi
  dòng 11: TRÙNG dòng 8                                          -> KHÔNG đính
  dòng 12: phương án sử dụng đất của tổ chức kinh tế             -> phuong_an_to_chuc_kinh_te
  dòng 13: nhóm giấy tờ của hồ sơ gia hạn                        -> gcn khi hồ sơ là gia hạn (chỉ có Đơn Mẫu số 04)
  dòng 14: Đơn theo Mẫu số 04                                    -> don_gia_han (+ ủy quyền, CCCD… của hồ sơ gia hạn)

Ánh xạ hồ sơ (file mapping): giấy ủy quyền không có dòng riêng → đính chung dòng Đơn; Giấy chứng nhận đính dòng 4, không
đính lại dòng 13 (dòng 13 đi cùng hồ sơ gia hạn). Mọi dòng chọn "Bản chính".

MỖI FILE ĐÍNH NGUYÊN KHỐI, MỘT LẦN, vào dòng của giấy chính trong file theo _PRIORITY (có Đơn thì luôn là dòng Đơn); LLM
liệt kê mọi loại giấy trong file để chọn dòng và báo cán bộ những giấy có dòng riêng mà nằm chung file. OCR phân loại
dùng lại cách của đăng ký đất đai lần đầu Khánh Hòa (chữ đủ trang từ cache bước điền), gửi LLM trích đoạn đầu từng trang.
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

_DON_DE_NGHI = "don_de_nghi"
_DON_GIA_HAN = "don_gia_han"
_GCN = "gcn"
_AUTHORIZATION = "authorization"
_IDENTITY = "identity"
_KET_QUA_LUA_CHON_NHA_DAU_TU = "ket_qua_lua_chon_nha_dau_tu"
_VAN_BAN_PHE_DUYET_DU_AN = "van_ban_phe_duyet_du_an"
_GIAY_TO_DAU_TU_TONG_HOP = "giay_to_dau_tu_tong_hop"
_PHUONG_AN_TANG_DAT_MAT = "phuong_an_tang_dat_mat"
_DU_AN_GIAO_RUNG = "du_an_giao_rung"
_DAU_GIA_THUE_RUNG = "dau_gia_thue_rung"
_PHUONG_AN_CONG_TY_NONG_LAM = "phuong_an_cong_ty_nong_lam"
_PHUONG_AN_DAT_THU_HOI = "phuong_an_dat_thu_hoi"
_PHUONG_AN_TO_CHUC_KINH_TE = "phuong_an_to_chuc_kinh_te"
_OTHER = "other"

_DON_ROW = 2
_GIA_HAN_DON_ROW = 14
_GIA_HAN_GCN_ROW = 13

# STT -> dòng trên cổng: name là đoạn chữ đầu cột "Tên giấy tờ"; dòng 11 trùng dòng 8 nên không khai.
_ROWS: dict[int, str] = {
    1: "Bản sao văn bản phê duyệt kết quả lựa chọn nhà đầu tư của cơ quan nhà nước có thẩm quyền",
    2: "Đơn theo Mẫu số 01",
    3: "Bản sao văn bản phê duyệt dự án đầu tư, quyết định chấp thuận chủ trương đầu tư",
    4: "Một trong các giấy chứng nhận quy định tại khoản 21 Điều 3, khoản 3 Điều 256 Luật Đất đai",
    5: "Phương án sử dụng tầng đất mặt theo Mẫu số 26",
    6: "Dự án đầu tư đối với khu rừng đề nghị giao",
    7: "Kết quả đấu giá thuê rừng; biên bản đấu giá cho thuê rừng",
    8: "Một trong các loại giấy tờ sau",
    9: "Bản sao Phương án sử dụng đất của công ty nông, lâm nghiệp tại địa phương",
    10: "Bản sao Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối với diện tích đất thu hồi",
    12: "Bản sao Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối với tổ chức kinh tế",
    13: "Một trong các giấy tờ sau: + Bản sao một trong các giấy chứng nhận",
    14: "Đơn theo Mẫu số 04",
}

# Loại giấy -> (dòng, tên tài liệu khi đính). None = đi theo dòng Đơn của hồ sơ (Mẫu số 01, hoặc 04 nếu gia hạn).
_ROUTES: dict[str, tuple[int | None, str]] = {
    _DON_DE_NGHI: (_DON_ROW, "Đơn đề nghị giao đất, cho thuê đất, chuyển mục đích sử dụng đất (Mẫu số 01)"),
    _DON_GIA_HAN: (_GIA_HAN_DON_ROW, "Đơn đề nghị gia hạn sử dụng đất (Mẫu số 04)"),
    _GCN: (4, "Giấy chứng nhận quyền sử dụng đất"),
    _AUTHORIZATION: (None, "Giấy ủy quyền"),
    _IDENTITY: (None, "Căn cước công dân"),
    _KET_QUA_LUA_CHON_NHA_DAU_TU: (1, "Văn bản phê duyệt kết quả lựa chọn nhà đầu tư"),
    _VAN_BAN_PHE_DUYET_DU_AN: (3, "Văn bản phê duyệt dự án đầu tư, chấp thuận chủ trương đầu tư"),
    _PHUONG_AN_TANG_DAT_MAT: (5, "Phương án sử dụng tầng đất mặt (Mẫu số 26)"),
    _DU_AN_GIAO_RUNG: (6, "Dự án đầu tư khu rừng đề nghị giao"),
    _DAU_GIA_THUE_RUNG: (7, "Kết quả đấu giá thuê rừng"),
    _GIAY_TO_DAU_TU_TONG_HOP: (8, "Giấy tờ chấp thuận nhà đầu tư, đấu giá, nhận chuyển nhượng dự án"),
    _PHUONG_AN_CONG_TY_NONG_LAM: (9, "Phương án sử dụng đất của công ty nông, lâm nghiệp"),
    _PHUONG_AN_DAT_THU_HOI: (10, "Phương án sử dụng diện tích đất thu hồi của công ty nông, lâm nghiệp"),
    _PHUONG_AN_TO_CHUC_KINH_TE: (12, "Phương án sử dụng đất của tổ chức kinh tế, đơn vị sự nghiệp công lập"),
}
# File gộp nhiều giấy: dòng của giấy ĐỨNG TRƯỚC nhận nguyên file. Đơn luôn thắng, rồi Giấy chứng nhận, giấy tờ dự án.
_PRIORITY: tuple[str, ...] = (
    _DON_DE_NGHI, _DON_GIA_HAN, _GCN, _VAN_BAN_PHE_DUYET_DU_AN, _GIAY_TO_DAU_TU_TONG_HOP, _KET_QUA_LUA_CHON_NHA_DAU_TU,
    _DU_AN_GIAO_RUNG, _DAU_GIA_THUE_RUNG, _PHUONG_AN_TANG_DAT_MAT, _PHUONG_AN_TO_CHUC_KINH_TE, _PHUONG_AN_DAT_THU_HOI,
    _PHUONG_AN_CONG_TY_NONG_LAM, _AUTHORIZATION, _IDENTITY,
)
_ALLOWED = set(_ROUTES) | {_OTHER}


def is_gia_han(doc_types: set[str]) -> bool:
    """Hồ sơ gia hạn: có Đơn Mẫu số 04 mà không có Đơn Mẫu số 01."""
    return _DON_GIA_HAN in doc_types and _DON_DE_NGHI not in doc_types


def route_row(doc_type: str, gia_han: bool) -> int:
    """Dòng nhận giấy; giấy không có dòng riêng (ủy quyền, CCCD, giấy lạ) đi theo dòng Đơn của hồ sơ."""
    if doc_type == _GCN and gia_han:
        return _GIA_HAN_GCN_ROW
    row = _ROUTES[doc_type][0] if doc_type in _ROUTES else None
    return row if row is not None else (_GIA_HAN_DON_ROW if gia_han else _DON_ROW)


def document_name(doc_type: str) -> str:
    return _ROUTES[doc_type][1] if doc_type in _ROUTES else ""


def primary(doc_types: list[str] | set[str]) -> str:
    return next((doc_type for doc_type in _PRIORITY if doc_type in doc_types), _OTHER)


def normalize_doc_type(value: Any) -> str:
    folded = _fold(str(value or ""))
    for doc_type in _ALLOWED:
        if folded == _fold(doc_type):
            return doc_type
    return _OTHER


def _doc_types(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        raw = [raw]
    out: list[str] = []
    for value in raw:
        doc_type = normalize_doc_type(value)
        if doc_type not in out:
            out.append(doc_type)
    return out


def attachment(file_index: int, file_name: str, row: int, name: str, doc_type: str) -> dict:
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": name,
        "componentName": _ROWS[row],
        "componentIndex": row,
        "loaiBan": "Bản chính",
        "target": "attp-row",
        # Cổng iGate Tuyên Quang tick sẵn mọi dòng thành phần → FE bỏ tick hết trước khi đính, chỉ dòng có tệp được tick lại.
        "untickUnplannedRows": True,
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
    raw = await client.chat(messages, max_tokens=900, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    result: dict[int, list[str]] = {}
    for item in parsed.get("documents", []) or []:
        try:
            result[int(item.get("index"))] = _doc_types(item.get("docTypes", item.get("docType")))
        except (TypeError, ValueError, AttributeError):
            continue
    return result


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict] | None = None,
    llm_types: dict[int, list[str] | str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    del ocr_results  # LLM-first: không suy luận rule từ OCR text ở đây.
    types_by_file = {index: _doc_types(raw) for index, raw in (llm_types or {}).items() if raw}
    gia_han = is_gia_han({doc_type for types in types_by_file.values() for doc_type in types})
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        doc_types = types_by_file.get(index, [])
        doc_type = primary(doc_types)
        row = route_row(doc_type, gia_han)
        others = sorted({route_row(item, gia_han) for item in doc_types if item in _ROUTES} - {row})
        # File gộp hoặc không rõ loại giữ TÊN GỐC để cán bộ nhận ra; file một giấy mang tên giấy.
        name = file_name if others or doc_type == _OTHER else document_name(doc_type)
        attachments.append(attachment(index, file_name, row, name, doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "docTypes": doc_types,
                           "source": "llm" if index in types_by_file else "unknown", "rows": [row]})
        if doc_type == _OTHER:
            warnings.append(f"Chưa nhận diện chắc loại giấy tờ cho '{file_name}' — tạm đính vào dòng {row} (Đơn); "
                            f"cán bộ kiểm tra lại.")
        elif others:
            warnings.append(f"'{file_name}' gộp nhiều giấy tờ — đính nguyên file một lần vào dòng {row} "
                            f"({document_name(doc_type)}), không tách sang dòng {', '.join(map(str, others))}.")

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
