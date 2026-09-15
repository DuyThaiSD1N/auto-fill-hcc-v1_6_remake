"""Lập kế hoạch đính kèm vào 4 dòng thành phần hồ sơ hỏa táng trên cổng DVC Quảng Ngãi.

Bảng thành phần hồ sơ có sẵn ĐÚNG 4 dòng (đã đối chiếu VERBATIM với 'quảng ngãi khuyến khích hoả
táng đính kèm.html' + ảnh ANH_XA_Thanh_phan_ho_so_hoa_tang.png + sheet "2. Thành phần hồ sơ" của
MAPPING_eForm). componentIndex là vị trí DOM 0-based của dòng (STT − 1); componentName là text
VERBATIM trong cột "Tên giấy tờ" (FE khớp substring sau khi fold dấu — hai dòng Tờ khai chỉ khác
nhau ở đuôi "(dành cho cá nhân)" / "(dành cho cơ quan, tổ chức)" nên phải giữ NGUYÊN cả câu, kể cả
dấu chấm cuối, để không khớp chéo).

  index 0 (STT1): Tờ khai ... theo Mẫu số 01 (dành cho cá nhân).      -> to_khai_ca_nhan
  index 1 (STT2): Tờ khai ... theo Mẫu số 02 (dành cho cơ quan, tổ chức). -> to_khai_to_chuc
  index 2 (STT3): Bản chính Hợp đồng và Hóa đơn tài chính của cơ sở hỏa táng. -> hop_dong + hoa_don
  index 3 (STT4): Văn bản ủy quyền ... hoặc giấy giới thiệu ... (nếu có). -> authorization

HỢP ĐỒNG VÀ HÓA ĐƠN DÙNG CHUNG MỘT DÒNG: ảnh ánh xạ ghi rõ "ĐÍNH KÈM CHUNG — 02 tệp trong 01 mục",
thiếu một trong hai chứng từ là hồ sơ không hợp lệ. Hai docType route về cùng index 2 với
documentName KHÁC nhau để cán bộ vẫn phân biệt được trong cùng ô upload; FE gom nhóm theo
componentName nên hai file được set một lượt vào cùng input (ô upload nhận nhiều file).

HAI DÒNG TỜ KHAI LOẠI TRỪ NHAU: hồ sơ cá nhân chỉ dùng Mẫu số 01, hồ sơ cơ quan/tổ chức chỉ dùng Mẫu
số 02. Ảnh ánh xạ cảnh báo "tuyệt đối không đính nhầm tệp Mẫu số 01 vào dòng Mẫu số 02" -> route
CHẶT theo docType do LLM đọc từ chính nội dung tờ khai, không rải file sang cả hai dòng.

TRÍCH LỤC KHAI TỬ VÀ CCCD KHÔNG CÓ DÒNG RIÊNG: ảnh ánh xạ xếp Trích lục khai tử vào ô đỏ "PHẢI BỔ
SUNG — eForm không có dòng sẵn", cách xử lý của cán bộ là bấm "+ Thêm giấy tờ". Extension KHÔNG được
sửa trong phạm vi thủ tục này và engine attp-row chỉ điền vào các dòng có sẵn, nên để KHÔNG RỚT FILE
ta đính chúng CHUNG vào DÒNG TỜ KHAI (dòng chính của hồ sơ), giữ documentName mô tả rõ; data[note]
của process nói thẳng chỗ này để cán bộ soát và tự tách sang dòng thêm mới nếu cổng bắt buộc.

DÒNG TỜ KHAI CHÍNH được chọn tất định theo chính kế hoạch: hồ sơ nào có Tờ khai Mẫu số 02 (và không
có Mẫu số 01) thì dòng chính là index 1, còn lại là index 0 — tránh dồn giấy tờ vào một dòng bỏ
trống khi người đề nghị là cơ quan, tổ chức.

Phân loại LLM-FIRST tuyệt đối: doc_type CHỈ lấy từ LLM, KHÔNG có nhánh rule keyword (giòn, dễ sai).
Không rõ/không hợp lệ -> đính CHUNG vào dòng Tờ khai chính, KHÔNG bỏ file, giữ TÊN FILE GỐC + cảnh
báo. KHÔNG set Bản chính/Bản sao (loaiBan): cán bộ tự chọn.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_TO_KHAI_CA_NHAN = "to_khai_ca_nhan"
_TO_KHAI_TO_CHUC = "to_khai_to_chuc"
_HOP_DONG_HOA_TANG = "hop_dong_hoa_tang"
_HOA_DON_HOA_TANG = "hoa_don_hoa_tang"
_TRICH_LUC_KHAI_TU = "trich_luc_khai_tu"
_AUTHORIZATION = "authorization"
_IDENTITY = "identity"
_OTHER = "other"

# componentName lấy VERBATIM từ cột "Tên giấy tờ" của 'quảng ngãi khuyến khích hoả táng đính kèm.html'.
_ROW_TO_KHAI_CA_NHAN = (
    "Tờ khai đề nghị hỗ trợ chi phí khuyến khích sử dụng hình thức hỏa táng theo Mẫu số 01 "
    "(dành cho cá nhân)."
)
_ROW_TO_KHAI_TO_CHUC = (
    "Tờ khai đề nghị hỗ trợ chi phí khuyến khích sử dụng hình thức hỏa táng theo Mẫu số 02 "
    "(dành cho cơ quan, tổ chức)."
)
_ROW_HOP_DONG_HOA_DON = "Bản chính Hợp đồng và Hóa đơn tài chính của cơ sở hỏa táng."
_ROW_UY_QUYEN = (
    "Văn bản ủy quyền của cá nhân được chứng thực hoặc giấy giới thiệu của cơ quan, tổ chức (nếu có)."
)

_ROW_NAMES = {
    0: _ROW_TO_KHAI_CA_NHAN,
    1: _ROW_TO_KHAI_TO_CHUC,
    2: _ROW_HOP_DONG_HOA_DON,
    3: _ROW_UY_QUYEN,
}

# index=None => "dòng Tờ khai chính", chốt lúc dựng plan (xem _main_row_index).
_ROUTES: dict[str, dict[str, Any]] = {
    _TO_KHAI_CA_NHAN: {
        "index": 0,
        "documentName": "Tờ khai đề nghị hỗ trợ chi phí hỏa táng (Mẫu số 01 - cá nhân)",
    },
    _TO_KHAI_TO_CHUC: {
        "index": 1,
        "documentName": "Tờ khai đề nghị hỗ trợ chi phí hỏa táng (Mẫu số 02 - cơ quan, tổ chức)",
    },
    _HOP_DONG_HOA_TANG: {"index": 2, "documentName": "Hợp đồng dịch vụ hỏa táng"},
    _HOA_DON_HOA_TANG: {"index": 2, "documentName": "Hóa đơn tài chính của cơ sở hỏa táng"},
    _AUTHORIZATION: {"index": 3, "documentName": "Văn bản ủy quyền/giấy giới thiệu"},
    # Không có dòng riêng -> dòng Tờ khai chính (xem docstring).
    _TRICH_LUC_KHAI_TU: {"index": None, "documentName": "Trích lục khai tử/Giấy báo tử"},
    _IDENTITY: {"index": None, "documentName": "Căn cước công dân"},
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


def _main_row_index(doc_types: list[str]) -> int:
    """Dòng Tờ khai chính của hồ sơ: Mẫu số 02 chỉ khi hồ sơ thực sự là của cơ quan, tổ chức."""
    if _TO_KHAI_TO_CHUC in doc_types and _TO_KHAI_CA_NHAN not in doc_types:
        return 1
    return 0


def _build_item(file: dict, file_index: int, doc_type: str, row_index: int, document_name: str) -> dict:
    return {
        "fileIndex": file_index,
        "fileName": str(file.get("name") or f"file-{file_index + 1}"),
        "documentName": document_name,
        "componentName": _ROW_NAMES[row_index],
        "componentIndex": row_index,
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

    # doc_type CHỈ lấy từ LLM; không có rule keyword fallback.
    resolved = [
        llm_types.get(index, "") if llm_types.get(index, "") in _ROUTES else _OTHER
        for index in range(len(files))
    ]
    main_row = _main_row_index(resolved)

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        doc_type = resolved[index]

        if doc_type in _ROUTES:
            route = _ROUTES[doc_type]
            row_index = main_row if route["index"] is None else route["index"]
            attachments.append(
                _build_item(file, index, doc_type, row_index, route["documentName"])
            )
            classified.append({
                "fileName": file_name,
                "docType": doc_type,
                "source": "llm",
                "componentIndexes": [row_index],
            })
            continue

        # Bảng KHÔNG có dòng "Giấy tờ khác" -> KHÔNG bỏ file (sẽ rớt), mà đính CHUNG vào dòng Tờ khai
        # chính. Giữ TÊN FILE GỐC làm documentName để cán bộ nhận ra và soát lại.
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": file_name,
            "componentName": _ROW_NAMES[main_row],
            "componentIndex": main_row,
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": _OTHER,
        })
        warnings.append(
            f"Chưa nhận diện chắc loại giấy tờ cho '{file_name}' — tạm đính vào dòng Tờ khai đề nghị "
            f"hỗ trợ chi phí khuyến khích sử dụng hình thức hỏa táng; cán bộ kiểm tra lại."
        )
        source = "llm" if llm_types.get(index, "") == _OTHER else "unknown"
        classified.append({
            "fileName": file_name,
            "docType": _OTHER,
            "source": source,
            "routedTo": main_row,
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
