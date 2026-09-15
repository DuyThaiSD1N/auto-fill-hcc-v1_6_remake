"""Lập kế hoạch đính kèm cho thủ tục xác định lại diện tích đất ở trên cổng DVC Quảng Ngãi.

Bảng thành phần hồ sơ có ĐÚNG 5 dòng DOM (đã đối chiếu VERBATIM với 'đinmhs kèm.html' và ảnh
'anh-xa-thanh-phan-ho-so (3).png'), nhưng CHỈ 3 dòng là GIẤY TỜ THẬT. componentIndex là vị trí DOM
0-based của dòng (STT − 1); componentName là đoạn text đặc trưng trong cột "Tên giấy tờ" (FE khớp
substring sau khi fold dấu, đã soát chéo để mỗi chuỗi chỉ trúng ĐÚNG dòng mong muốn).

  index 0 (STT1): Giấy chứng nhận đã cấp                                  -> land_certificate
  index 1 (STT2): "(4) Khi nộp các giấy tờ quy định, người yêu cầu..."    -> KHÔNG route (ghi chú)
  index 2 (STT3): "Trường hợp nộp bản sao hoặc bản số hóa các loại..."    -> KHÔNG route (ghi chú)
  index 3 (STT4): Đơn đăng ký biến động ... theo Mẫu số 11/ĐK             -> don_bien_dong (ĐƠN CHÍNH)
  index 4 (STT5): (3) Văn bản về việc đại diện theo pháp luật dân sự      -> authorization

HAI DÒNG GHI CHÚ (index 1 và 2): cổng vẫn render ô "Chọn tệp tin" cho chúng, nhưng ảnh ánh xạ đánh
dấu cả hai bằng nhãn "KHÔNG ĐÍNH KÈM — dòng chú thích pháp lý trong bảng thành phần hồ sơ, không
phải giấy tờ phải nộp. Hệ thống vẫn render ô đính kèm nhưng bỏ trống." -> KHÔNG docType nào được trỏ
vào hai index này (có test khóa cứng).

DÒNG ĐƠN LÀ MẪU 11/ĐK, KHÔNG PHẢI MẪU 15: cổng treo file mẫu 'Mẫu số 11.docx'. Ảnh ánh xạ ghi chú
hồ sơ thực tế hay nộp đơn biến động theo mẫu cũ (Mẫu số 18) — prompt vì thế nhận MỌI mẫu đơn đăng ký
biến động, không đòi đúng số hiệu mẫu; cán bộ tự soát việc lệch mẫu.

CCCD VÀ GIẤY TỜ KHÔNG CÓ DÒNG RIÊNG: bảng không có dòng cho căn cước công dân, giấy xác nhận cư trú
hay công văn phúc đáp của cơ quan đăng ký đất đai. Ảnh ánh xạ khuyên cán bộ bấm "+ Thêm giấy tờ" để
tách từng trang ra dòng mới, NHƯNG engine attp-row chỉ điền vào các dòng CÓ SẴN và extension không
được sửa trong phạm vi thủ tục này -> để KHÔNG RỚT FILE, ta đính chúng CHUNG vào DÒNG ĐƠN (index 3),
giữ documentName mô tả rõ; data[note] của process nói thẳng chỗ này để cán bộ soát và tự tách sang
dòng thêm mới nếu cổng bắt buộc. Đây là điểm CỐ Ý khác khuyến nghị thao tác tay trong ảnh ánh xạ.

Phân loại LLM-FIRST tuyệt đối: doc_type CHỈ lấy từ LLM, KHÔNG có nhánh rule keyword (giòn, dễ sai).
Không rõ/không hợp lệ -> đính CHUNG vào dòng Đơn, KHÔNG bỏ file, giữ TÊN FILE GỐC + cảnh báo.
KHÔNG set Bản chính/Bản sao (loaiBan): cán bộ tự chọn (ảnh ánh xạ cũng nhắc phải đổi sang Bản sao
khi nộp bản số hóa — đó là quyết định của cán bộ, không phải của máy).
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_LAND_CERTIFICATE = "land_certificate"
_DON_BIEN_DONG = "don_bien_dong"
_AUTHORIZATION = "authorization"
_IDENTITY = "identity"
_OTHER = "other"

# componentName lấy VERBATIM từ cột "Tên giấy tờ" của 'đinmhs kèm.html'; mỗi chuỗi đã soát chéo trên
# cả 5 dòng DOM để chỉ khớp đúng dòng mong muốn (FE so khớp hai chiều sau khi fold dấu).
_DON_NAME = "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 11/ĐK"
_DON_INDEX = 3
_LAND_CERTIFICATE_NAME = "Giấy chứng nhận đã cấp"
_LAND_CERTIFICATE_INDEX = 0
_AUTHORIZATION_NAME = "Văn bản về việc đại diện theo quy định của pháp luật về dân sự"
_AUTHORIZATION_INDEX = 4

# Hai dòng GHI CHÚ pháp lý của cổng — khóa lại để test chặn mọi route trỏ nhầm vào đây.
_NOTE_ROW_INDEXES = {1, 2}

_ROUTES: dict[str, dict[str, Any]] = {
    _LAND_CERTIFICATE: {
        "index": _LAND_CERTIFICATE_INDEX,
        "name": _LAND_CERTIFICATE_NAME,
        "documentName": "Giấy chứng nhận quyền sử dụng đất đã cấp",
    },
    _DON_BIEN_DONG: {
        "index": _DON_INDEX,
        "name": _DON_NAME,
        "documentName": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 11/ĐK)",
    },
    _AUTHORIZATION: {
        "index": _AUTHORIZATION_INDEX,
        "name": _AUTHORIZATION_NAME,
        "documentName": "Văn bản về việc đại diện/ủy quyền",
    },
    # KHÔNG có dòng riêng trong bảng -> gom CHUNG vào dòng ĐƠN, giữ documentName mô tả để cán bộ
    # phân biệt trong cùng ô upload (xem docstring).
    _IDENTITY: {
        "index": _DON_INDEX,
        "name": _DON_NAME,
        "documentName": "Căn cước công dân/giấy xác nhận số định danh cá nhân",
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
        # doc_type CHỈ lấy từ LLM; không có rule keyword fallback.
        doc_type = llm_type if llm_type in _ROUTES else _OTHER

        if doc_type in _ROUTES:
            item = _build_item(file, index, doc_type)
            attachments.append(item)
            classified.append({
                "fileName": file_name,
                "docType": doc_type,
                "source": "llm",
                "componentIndex": item["componentIndex"],
            })
            continue

        # Bảng KHÔNG có dòng "Giấy tờ khác" -> KHÔNG bỏ file (sẽ rớt), mà đính CHUNG vào dòng ĐƠN
        # (index 3). Giữ TÊN FILE GỐC làm documentName để cán bộ nhận ra và soát lại.
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": file_name,
            "componentName": _DON_NAME,
            "componentIndex": _DON_INDEX,
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": _OTHER,
        })
        warnings.append(
            f"Chưa nhận diện chắc loại giấy tờ cho '{file_name}' — tạm đính vào dòng Đơn đăng ký "
            f"biến động đất đai, tài sản gắn liền với đất theo Mẫu số 11/ĐK; cán bộ kiểm tra lại."
        )
        source = "llm" if llm_type == _OTHER else "unknown"
        classified.append({
            "fileName": file_name,
            "docType": _OTHER,
            "source": source,
            "routedTo": _DON_INDEX,
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
