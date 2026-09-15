"""Lập kế hoạch đính kèm vào đúng dòng hồ sơ trên cổng DVC Ninh Bình.

Thủ tục "Đăng ký biến động QSDĐ, tài sản gắn liền với đất" (chuyển đổi/chuyển nhượng/thừa kế/tặng cho/
góp vốn/cho thuê): bảng đính kèm có sẵn 13 dòng. componentIndex là vị trí DOM 0-based của dòng (STT − 1);
componentName là đoạn text đặc trưng trong cột "Tên giấy tờ" của dòng đó (khớp substring sau khi fold
dấu ở FE). 13 dòng lấy VERBATIM từ HTML thật (biến động đính kèm.html):

  index 0 (STT1)  : Văn bản về việc đại diện theo quy định của pháp luật về dân sự -> authorization
  index 1 (STT2)  : Bản gốc Giấy chứng nhận đã cấp -> land_certificate
  index 2 (STT3)  : Bản vẽ tách thửa đất, hợp thửa đất theo Mẫu số 22 -> ban_ve_tach_thua
  index 3 (STT4)  : Hợp đồng/văn bản bán/tặng cho/thừa kế/góp vốn bằng TÀI SẢN gắn liền với đất (đất
                    thuê Nhà nước trả tiền hằng năm) -> hop_dong_tai_san
  index 4 (STT5)  : Hợp đồng/văn bản CHUYỂN QUYỀN SDĐ (chuyển đổi/chuyển nhượng/thừa kế/tặng cho/góp
                    vốn bằng QUYỀN SỬ DỤNG ĐẤT) -> hop_dong_chuyen_quyen (DÒNG HỢP ĐỒNG CHÍNH)
  index 5 (STT6)  : Mảnh trích đo bản đồ địa chính thửa đất -> trich_do
  index 6 (STT7)  : Văn bản của bên nhận thế chấp đồng ý cho chuyển nhượng/tặng cho -> van_ban_the_chap
  index 7 (STT8)  : Văn bản của người SDĐ đồng ý cho chủ tài sản chuyển nhượng/tặng cho/góp vốn ->
                    van_ban_dong_y_su_dung_dat
  index 8 (STT9)  : Văn bản thỏa thuận cấp chung một Giấy chứng nhận -> thoa_thuan_cap_chung
  index 9 (STT10) : Văn bản cho thuê, cho thuê lại quyền sử dụng đất -> van_ban_cho_thue
  index 10 (STT11): Đơn đăng ký biến động đất đai theo Mẫu số 18 -> don_bien_dong (ĐƠN CHÍNH)
  index 11 (STT12): Biên bản họp giữa UBND cấp xã với người SDĐ về việc tặng cho QSDĐ -> bien_ban_hop_ubnd
  index 12 (STT13): Văn bản tặng cho QSDĐ hoặc biên bản họp giữa đại diện thôn về tặng cho -> van_ban_tang_cho

Form KHÔNG có dòng riêng cho CCCD/tờ khai thuế/giấy tờ hộ tịch → gom CHUNG vào dòng Đơn Mẫu 18
(index 10), giữ documentName mô tả để cán bộ soát (data[note] đã nêu rõ chỗ này). Lưu ý nghiệp vụ:
HỢP ĐỒNG TẶNG CHO QSDĐ có công chứng đi vào dòng HỢP ĐỒNG CHUYỂN QUYỀN (index 4), KHÔNG vào index 12
(index 12 chỉ dành cho văn bản tặng cho không qua hợp đồng / biên bản họp cộng đồng thôn về tặng cho).

Phân loại LLM-FIRST tuyệt đối: doc_type CHỈ lấy từ LLM. Không có nhánh rule keyword nào (giòn, dễ sai).
Không rõ/không hợp lệ -> đính CHUNG vào dòng Đơn Mẫu 18 (index 10), KHÔNG bỏ file, kèm cảnh báo.
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

_AUTHORIZATION = "authorization"
_LAND_CERTIFICATE = "land_certificate"
_BAN_VE_TACH_THUA = "ban_ve_tach_thua"
_HOP_DONG_TAI_SAN = "hop_dong_tai_san"
_HOP_DONG_CHUYEN_QUYEN = "hop_dong_chuyen_quyen"
_TRICH_DO = "trich_do"
_VAN_BAN_THE_CHAP = "van_ban_the_chap"
_VAN_BAN_DONG_Y_SU_DUNG_DAT = "van_ban_dong_y_su_dung_dat"
_THOA_THUAN_CAP_CHUNG = "thoa_thuan_cap_chung"
_VAN_BAN_CHO_THUE = "van_ban_cho_thue"
_DON_BIEN_DONG = "don_bien_dong"
_BIEN_BAN_HOP_UBND = "bien_ban_hop_ubnd"
_VAN_BAN_TANG_CHO = "van_ban_tang_cho"
_IDENTITY = "identity"
_TO_KHAI_THUE = "to_khai_thue"
_HO_TICH = "ho_tich"
_OTHER = "other"

# componentName lấy VERBATIM từ cột "Tên giấy tờ" của biến động đính kèm.html (đã đối chiếu 13 dòng).
_DON_BIEN_DONG_NAME = "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18"
_ROUTES: dict[str, dict[str, Any]] = {
    _AUTHORIZATION: {
        "index": 0,
        "name": "Văn bản về việc đại diện theo quy định của pháp luật về dân sự",
        "documentName": "Văn bản ủy quyền/đại diện",
    },
    _LAND_CERTIFICATE: {
        "index": 1,
        "name": "Bản gốc Giấy chứng nhận đã cấp",
        "documentName": "Bản gốc Giấy chứng nhận đã cấp",
    },
    _BAN_VE_TACH_THUA: {
        "index": 2,
        "name": "Bản vẽ tách thửa đất, hợp thửa đất theo Mẫu số 22",
        "documentName": "Bản vẽ tách thửa/hợp thửa (Mẫu số 22)",
    },
    _HOP_DONG_TAI_SAN: {
        "index": 3,
        "name": "Hợp đồng hoặc văn bản về việc bán hoặc tặng cho hoặc để thừa kế hoặc góp vốn bằng tài sản gắn liền với đất",
        "documentName": "Hợp đồng/văn bản về tài sản gắn liền với đất thuê Nhà nước",
    },
    _HOP_DONG_CHUYEN_QUYEN: {
        "index": 4,
        "name": "Hợp đồng hoặc văn bản về việc chuyển quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất",
        "documentName": "Hợp đồng/văn bản chuyển quyền sử dụng đất",
    },
    _TRICH_DO: {
        "index": 5,
        "name": "Mảnh trích đo bản đồ địa chính thửa đất",
        "documentName": "Mảnh trích đo bản đồ địa chính",
    },
    _VAN_BAN_THE_CHAP: {
        "index": 6,
        "name": "Văn bản của bên nhận thế chấp về việc đồng ý cho bên thế chấp được chuyển nhượng, tặng cho",
        "documentName": "Văn bản bên nhận thế chấp đồng ý",
    },
    _VAN_BAN_DONG_Y_SU_DUNG_DAT: {
        "index": 7,
        "name": "Văn bản của người sử dụng đất đồng ý cho chủ sở hữu tài sản gắn liền với đất được chuyển nhượng, tặng cho, góp vốn",
        "documentName": "Văn bản người sử dụng đất đồng ý cho chủ tài sản",
    },
    _THOA_THUAN_CAP_CHUNG: {
        "index": 8,
        "name": "Văn bản thỏa thuận về việc cấp chung một Giấy chứng nhận",
        "documentName": "Văn bản thỏa thuận cấp chung một GCN",
    },
    _VAN_BAN_CHO_THUE: {
        "index": 9,
        "name": "Văn bản về việc cho thuê, cho thuê lại quyền sử dụng đất",
        "documentName": "Văn bản cho thuê/cho thuê lại quyền sử dụng đất",
    },
    _DON_BIEN_DONG: {
        "index": 10,
        "name": _DON_BIEN_DONG_NAME,
        "documentName": "Đơn đăng ký biến động (Mẫu số 18)",
    },
    _BIEN_BAN_HOP_UBND: {
        "index": 11,
        "name": "biên bản họp giữa Ủy ban nhân dân cấp xã với người sử dụng đất về việc tặng cho quyền sử dụng đất",
        "documentName": "Biên bản họp UBND cấp xã về tặng cho QSDĐ",
    },
    _VAN_BAN_TANG_CHO: {
        "index": 12,
        "name": "Văn bản tặng cho quyền sử dụng đất hoặc biên bản họp giữa đại diện thôn",
        "documentName": "Văn bản tặng cho QSDĐ / biên bản họp thôn",
    },
    # Form KHÔNG có dòng riêng cho các giấy tờ dưới đây -> gom CHUNG vào dòng Đơn Mẫu 18 (index 10),
    # giữ documentName mô tả để cán bộ phân biệt trong cùng ô upload. data[note] đã nêu rõ chỗ này.
    _IDENTITY: {
        "index": 10,
        "name": _DON_BIEN_DONG_NAME,
        "documentName": "Căn cước công dân",
    },
    _TO_KHAI_THUE: {
        "index": 10,
        "name": _DON_BIEN_DONG_NAME,
        "documentName": "Tờ khai thuế/lệ phí",
    },
    _HO_TICH: {
        "index": 10,
        "name": _DON_BIEN_DONG_NAME,
        "documentName": "Giấy tờ hộ tịch",
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


def _build_item(file: dict, file_index: int, doc_type: str) -> dict:
    route = _ROUTES[doc_type]
    return {
        "fileIndex": file_index,
        "fileName": str(file.get("name") or f"file-{file_index + 1}"),
        "documentName": route["documentName"],
        "componentName": route["name"],
        "componentIndex": route["index"],
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": doc_type,
    }


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
        # doc_type CHỈ lấy từ LLM; không có rule fallback.
        doc_type = llm_type if llm_type in _ROUTES else _OTHER

        if doc_type in _ROUTES:
            item = _build_item(file, index, doc_type)
            attachments.append(item)
            classified.append(
                {
                    "fileName": file_name,
                    "docType": doc_type,
                    "source": "llm",
                    "componentIndex": item["componentIndex"],
                }
            )
            continue

        # Form KHÔNG có dòng "Giấy tờ khác" → KHÔNG bỏ file (sẽ rớt), mà đính CHUNG vào dòng ĐƠN đăng ký
        # biến động (Mẫu 18, index 10). Giữ TÊN FILE GỐC làm documentName để cán bộ nhận ra và soát lại.
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": file_name,
            "componentName": _DON_BIEN_DONG_NAME,
            "componentIndex": 10,
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": _OTHER,
        })
        warnings.append(
            f"Chưa nhận diện chắc loại giấy tờ cho '{file_name}' — tạm đính vào dòng Đơn đăng ký "
            f"biến động (Mẫu số 18); cán bộ kiểm tra lại."
        )
        source = "llm" if llm_type == _OTHER else "unknown"
        classified.append({"fileName": file_name, "docType": _OTHER, "source": source, "routedTo": 10})

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
