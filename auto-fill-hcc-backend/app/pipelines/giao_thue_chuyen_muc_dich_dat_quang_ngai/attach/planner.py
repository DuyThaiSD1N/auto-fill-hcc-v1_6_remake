"""Lập kế hoạch đính kèm vào đúng 15 dòng hồ sơ trên cổng DVC Quảng Ngãi.

Thủ tục "Giao đất, cho thuê đất, chuyển mục đích sử dụng đất... gia hạn sử dụng đất": bảng thành
phần hồ sơ có sẵn 15 dòng (đã đối chiếu VERBATIM với 'giao đất đính kèm.html' + 3 ảnh ánh xạ
01/02/03). componentIndex là vị trí DOM 0-based của dòng (STT − 1); componentName là đoạn text đặc
trưng trong cột "Tên giấy tờ" của dòng đó (FE khớp substring sau khi fold dấu).

  index 0  (STT1)  : Dự án đầu tư đối với khu rừng đề nghị giao...           -> du_an_giao_rung
  index 1  (STT2)  : Kết quả đấu giá thuê rừng; biên bản đấu giá...          -> dau_gia_thue_rung
  index 2  (STT3)  : Bản sao văn bản phê duyệt kết quả lựa chọn nhà đầu tư   -> ket_qua_lua_chon_nha_dau_tu
  index 3  (STT4)  : Phương án sử dụng tầng đất mặt theo Mẫu số 26           -> phuong_an_tang_dat_mat
  index 4  (STT5)  : Bản sao văn bản phê duyệt dự án đầu tư, QĐ chấp thuận   -> van_ban_phe_duyet_dau_tu
  index 5  (STT6)  : "Một trong các loại giấy tờ sau: ..." (nhóm đầu tư)     -> giay_to_dau_tu_tong_hop
  index 6  (STT7)  : Phương án SDĐ của tổ chức kinh tế, đơn vị SN công lập   -> phuong_an_to_chuc_kinh_te
  index 7  (STT8)  : Phương án SDĐ đối với diện tích đất THU HỒI của cty NLN -> phuong_an_dat_thu_hoi
  index 8  (STT9)  : Phương án SDĐ của công ty nông, lâm nghiệp tại địa phương -> phuong_an_cong_ty_nong_lam
  index 9  (STT10) : TRÙNG HOÀN TOÀN dòng STT6 (lỗi cấu hình danh mục Cổng)
  index 10 (STT11) : "Một trong các giấy tờ sau: + Bản sao một trong các GCN..." -> gcn (dòng A)
  index 11 (STT12) : Đơn đề nghị gia hạn sử dụng đất                         -> don_gia_han
  index 12 (STT13) : "Một trong các giấy chứng nhận quy định tại khoản 21 Điều 3..." -> gcn (dòng B)
  index 13 (STT14) : Đơn đề nghị giao đất/thuê đất/chuyển mục đích...        -> don_de_nghi (ĐƠN CHÍNH)
  index 14 (STT15) : TRÙNG dòng STT4 (Phương án tầng đất mặt Mẫu số 26)

GIẤY CHỨNG NHẬN ĐI 2 DÒNG: ảnh ánh xạ 03 ghi rõ dòng 11 và dòng 13 cùng yêu cầu Giấy chứng nhận đã
cấp và "phải tải lên file ở CẢ HAI dòng" (hệ thống lưu file riêng theo từng dòng). Hai dòng có TEXT
KHÁC NHAU nên FE gom nhóm theo componentName sẽ tạo 2 nhóm -> cả hai dòng đều nhận file.

DÒNG TRÙNG TEXT (STT4≡STT15, STT6≡STT10) chỉ route về DÒNG CHÍNH (index 3 và index 5): FE gom nhóm
theo componentName, hai item cùng tên sẽ nhập một nhóm và chỉ một dòng được đính -> nhân đôi là vô
nghĩa và gây hiểu nhầm. Cán bộ tự đính thêm dòng trùng nếu cổng bắt buộc.

Bảng KHÔNG có dòng riêng cho CCCD, văn bản ủy quyền, Đơn đăng ký biến động (Mẫu số 18), Đơn đề nghị
thẩm định nhu cầu chuyển mục đích, tờ khai thuế/lệ phí -> gom CHUNG vào dòng ĐƠN ĐỀ NGHỊ (index 13),
giữ documentName mô tả để cán bộ soát (data[note] đã nêu rõ chỗ này).

Phân loại LLM-FIRST tuyệt đối: doc_type CHỈ lấy từ LLM, KHÔNG có nhánh rule keyword (giòn, dễ sai).
Không rõ/không hợp lệ -> đính CHUNG vào dòng Đơn đề nghị, KHÔNG bỏ file, giữ TÊN FILE GỐC + cảnh báo.
KHÔNG set Bản chính/Bản sao (loaiBan): cán bộ tự chọn.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DU_AN_GIAO_RUNG = "du_an_giao_rung"
_DAU_GIA_THUE_RUNG = "dau_gia_thue_rung"
_KET_QUA_LUA_CHON_NHA_DAU_TU = "ket_qua_lua_chon_nha_dau_tu"
_PHUONG_AN_TANG_DAT_MAT = "phuong_an_tang_dat_mat"
_VAN_BAN_PHE_DUYET_DAU_TU = "van_ban_phe_duyet_dau_tu"
_GIAY_TO_DAU_TU_TONG_HOP = "giay_to_dau_tu_tong_hop"
_PHUONG_AN_TO_CHUC_KINH_TE = "phuong_an_to_chuc_kinh_te"
_PHUONG_AN_DAT_THU_HOI = "phuong_an_dat_thu_hoi"
_PHUONG_AN_CONG_TY_NONG_LAM = "phuong_an_cong_ty_nong_lam"
_GCN = "gcn"
_DON_GIA_HAN = "don_gia_han"
_DON_DE_NGHI = "don_de_nghi"
_DON_BIEN_DONG = "don_bien_dong"
_DON_THAM_DINH_NHU_CAU = "don_tham_dinh_nhu_cau"
_TO_KHAI_THUE = "to_khai_thue"
_IDENTITY = "identity"
_AUTHORIZATION = "authorization"
_OTHER = "other"

# componentName lấy VERBATIM từ cột "Tên giấy tờ" của 'giao đất đính kèm.html'; mỗi chuỗi được chọn
# sao cho CHỈ khớp đúng dòng mong muốn (đã soát chéo 15 dòng, kể cả 3 cặp dòng trùng text).
_DON_DE_NGHI_NAME = (
    "Đơn đề nghị giao đất/thuê đất/chuyển mục đích sử dụng đất/giao đất và giao rừng/"
    "cho thuê đất và cho thuê rừng"
)
_DON_DE_NGHI_INDEX = 13

# Giấy chứng nhận phải lên CẢ HAI dòng 11 và 13 (ảnh ánh xạ 03) -> khai 2 route với tên KHÁC nhau.
_GCN_ROUTE_A = {
    "index": 10,
    "name": (
        "Bản sao một trong các giấy chứng nhận: Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài "
        "sản gắn liền với đất"
    ),
}
_GCN_ROUTE_B = {
    "index": 12,
    "name": "Một trong các giấy chứng nhận quy định tại khoản 21 Điều 3, khoản 3 Điều 256 Luật Đất đai",
}

_ROUTES: dict[str, dict[str, Any]] = {
    _DU_AN_GIAO_RUNG: {
        "routes": [{"index": 0, "name": "Dự án đầu tư đối với khu rừng đề nghị giao"}],
        "documentName": "Dự án đầu tư khu rừng đề nghị giao",
    },
    _DAU_GIA_THUE_RUNG: {
        "routes": [{"index": 1, "name": "Kết quả đấu giá thuê rừng; biên bản đấu giá cho thuê rừng"}],
        "documentName": "Kết quả đấu giá thuê rừng",
    },
    _KET_QUA_LUA_CHON_NHA_DAU_TU: {
        "routes": [{
            "index": 2,
            "name": "Bản sao văn bản phê duyệt kết quả lựa chọn nhà đầu tư của cơ quan nhà nước có thẩm quyền",
        }],
        "documentName": "Văn bản phê duyệt kết quả lựa chọn nhà đầu tư",
    },
    _PHUONG_AN_TANG_DAT_MAT: {
        # STT4 và STT15 trùng text -> chỉ dòng chính STT4 (index 3).
        "routes": [{"index": 3, "name": "Phương án sử dụng tầng đất mặt theo Mẫu số 26"}],
        "documentName": "Phương án sử dụng tầng đất mặt (Mẫu số 26)",
    },
    _VAN_BAN_PHE_DUYET_DAU_TU: {
        "routes": [{
            "index": 4,
            "name": "Bản sao văn bản phê duyệt dự án đầu tư, quyết định chấp thuận chủ trương đầu tư",
        }],
        "documentName": "Văn bản phê duyệt dự án đầu tư/chấp thuận chủ trương đầu tư",
    },
    _GIAY_TO_DAU_TU_TONG_HOP: {
        # STT6 và STT10 trùng text -> chỉ dòng chính STT6 (index 5).
        "routes": [{"index": 5, "name": "Một trong các loại giấy tờ sau"}],
        "documentName": "Giấy tờ nhóm đầu tư/đấu giá/nhận chuyển nhượng dự án",
    },
    _PHUONG_AN_TO_CHUC_KINH_TE: {
        "routes": [{
            "index": 6,
            "name": (
                "Bản sao Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối "
                "với tổ chức kinh tế"
            ),
        }],
        "documentName": "Phương án sử dụng đất của tổ chức kinh tế/đơn vị sự nghiệp công lập",
    },
    _PHUONG_AN_DAT_THU_HOI: {
        "routes": [{
            "index": 7,
            "name": (
                "Bản sao Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối "
                "với diện tích đất thu hồi"
            ),
        }],
        "documentName": "Phương án sử dụng diện tích đất thu hồi của công ty nông, lâm nghiệp",
    },
    _PHUONG_AN_CONG_TY_NONG_LAM: {
        "routes": [{
            "index": 8,
            "name": "Bản sao Phương án sử dụng đất của công ty nông, lâm nghiệp tại địa phương",
        }],
        "documentName": "Phương án sử dụng đất của công ty nông, lâm nghiệp tại địa phương",
    },
    _GCN: {
        "routes": [_GCN_ROUTE_A, _GCN_ROUTE_B],
        "documentName": "Giấy chứng nhận quyền sử dụng đất",
    },
    _DON_GIA_HAN: {
        "routes": [{"index": 11, "name": "Đơn đề nghị gia hạn sử dụng đất"}],
        "documentName": "Đơn đề nghị gia hạn sử dụng đất",
    },
    _DON_DE_NGHI: {
        "routes": [{"index": _DON_DE_NGHI_INDEX, "name": _DON_DE_NGHI_NAME}],
        "documentName": "Đơn đề nghị giao đất/thuê đất/chuyển mục đích sử dụng đất",
    },
    # Các loại dưới đây KHÔNG có dòng riêng trong bảng 15 dòng -> gom CHUNG vào dòng Đơn đề nghị,
    # giữ documentName mô tả để cán bộ phân biệt trong cùng ô upload.
    _DON_BIEN_DONG: {
        "routes": [{"index": _DON_DE_NGHI_INDEX, "name": _DON_DE_NGHI_NAME}],
        "documentName": "Đơn đăng ký biến động đất đai (Mẫu số 18)",
    },
    _DON_THAM_DINH_NHU_CAU: {
        "routes": [{"index": _DON_DE_NGHI_INDEX, "name": _DON_DE_NGHI_NAME}],
        "documentName": "Đơn đề nghị thẩm định nhu cầu sử dụng đất/chuyển mục đích",
    },
    _TO_KHAI_THUE: {
        "routes": [{"index": _DON_DE_NGHI_INDEX, "name": _DON_DE_NGHI_NAME}],
        "documentName": "Tờ khai thuế/lệ phí trước bạ",
    },
    _IDENTITY: {
        "routes": [{"index": _DON_DE_NGHI_INDEX, "name": _DON_DE_NGHI_NAME}],
        "documentName": "Căn cước công dân",
    },
    _AUTHORIZATION: {
        "routes": [{"index": _DON_DE_NGHI_INDEX, "name": _DON_DE_NGHI_NAME}],
        "documentName": "Văn bản ủy quyền",
    },
}
_ALLOWED = set(_ROUTES) | {_OTHER}


def _normalize_doc_type(value: Any) -> str:
    folded = _fold(str(value or ""))
    for doc_type in _ALLOWED:
        if folded == _fold(doc_type):
            return doc_type
    return _OTHER


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=700, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    result: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            result[int(item.get("index"))] = _normalize_doc_type(item.get("docType") or item.get("type"))
        except (TypeError, ValueError):
            continue
    return result


def _build_items(file: dict, file_index: int, doc_type: str) -> list[dict]:
    route_set = _ROUTES[doc_type]
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    return [
        {
            "fileIndex": file_index,
            "fileName": file_name,
            "documentName": route_set["documentName"],
            "componentName": route["name"],
            "componentIndex": route["index"],
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": doc_type,
        }
        for route in route_set["routes"]
    ]


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict] | None = None,
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    del ocr_results  # LLM-first: không dùng OCR text để suy luận rule ở đây.
    llm_types = llm_types or {}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        llm_type = llm_types.get(index, "")
        # doc_type CHỈ lấy từ LLM; không có rule keyword fallback.
        doc_type = llm_type if llm_type in _ROUTES else _OTHER

        if doc_type in _ROUTES:
            items = _build_items(file, index, doc_type)
            attachments.extend(items)
            classified.append({
                "fileName": file_name,
                "docType": doc_type,
                "source": "llm",
                "componentIndexes": [item["componentIndex"] for item in items],
            })
            continue

        # Bảng KHÔNG có dòng "Giấy tờ khác" -> KHÔNG bỏ file (sẽ rớt), mà đính CHUNG vào dòng ĐƠN ĐỀ
        # NGHỊ (index 13). Giữ TÊN FILE GỐC làm documentName để cán bộ nhận ra và soát lại.
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
            f"Chưa nhận diện chắc loại giấy tờ cho '{file_name}' — tạm đính vào dòng Đơn đề nghị "
            f"giao đất/thuê đất/chuyển mục đích sử dụng đất; cán bộ kiểm tra lại."
        )
        source = "llm" if llm_type == _OTHER else "unknown"
        classified.append({
            "fileName": file_name,
            "docType": _OTHER,
            "source": source,
            "routedTo": _DON_DE_NGHI_INDEX,
        })

    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    ocr_files = [item for item in raw_files if item.get("type") in _OCR_TYPES]
    errors: list[str] = []

    from app.services import ocr

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    llm_documents = [
        {"index": index, "text": str(by_name.get(file.get("name"), {}).get("text") or "")}
        for index, file in enumerate(raw_files)
        if str(by_name.get(file.get("name"), {}).get("text") or "").strip()
    ]
    started = time.monotonic()
    llm_types: dict[int, str] = {}
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
