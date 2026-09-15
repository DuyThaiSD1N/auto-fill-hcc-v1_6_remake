"""Lập kế hoạch đính kèm cho thủ tục đính chính GCN đã cấp lần đầu có sai sót — cổng DVC Quảng Ngãi.

Bảng thành phần hồ sơ có ĐÚNG 4 dòng DOM, tất cả đều là GIẤY TỜ THẬT (đã đối chiếu VERBATIM với
'đính chính đính kèm.html' và ảnh 'ANH_XA_Thanh_phan_ho_so_eForm_Dinh_chinh_GCN.png'). componentIndex
là vị trí DOM 0-based của dòng (STT − 1); componentName là đoạn text đặc trưng trong cột "Tên giấy
tờ" (FE khớp substring hai chiều sau khi fold dấu, đã soát chéo để mỗi chuỗi chỉ trúng ĐÚNG dòng
mong muốn).

  index 0 (STT1): Đơn đăng ký biến động ... theo Mẫu số 18   -> don_bien_dong (ĐƠN CHÍNH) + other
  index 1 (STT2): - Bản gốc Giấy chứng nhận đã cấp;          -> land_certificate
  index 2 (STT3): - Giấy tờ chứng minh sai sót thông tin ...  -> giay_to_chung_minh_sai_sot + identity
  index 3 (STT4): - Trường hợp ... văn bản về việc ủy quyền   -> authorization
  (nút "+ Thêm giấy tờ" cuối bảng KHÔNG phải một dòng DOM -> không có index, engine attp-row không
   bấm được nút này.)

KHÁC bảng của thủ tục "xác định lại diện tích đất ở" cùng cổng: bảng đó có 5 dòng DOM trong đó 2
dòng là GHI CHÚ PHÁP LÝ ("(4) Khi nộp các giấy tờ quy định...", "Trường hợp nộp bản sao hoặc bản số
hóa..."). Bảng của thủ tục ĐÍNH CHÍNH này KHÔNG có dòng ghi chú nào (đã grep toàn bộ cột "Tên giấy
tờ": đúng 4 dòng, 4 ô "Chọn tệp tin") và cũng không có dòng trùng text. Test khóa cứng việc này để
bảng cổng đổi thì phát hiện ngay.

CCCD ĐI VÀO DÒNG "GIẤY TỜ CHỨNG MINH SAI SÓT" (index 2), KHÔNG vào dòng Đơn: đây là điểm khác các
thủ tục đất đai khác. Ảnh ánh xạ ghi rõ tại mục ③ "Giấy tờ chứng minh sai sót — ĐÂY LÀ CHỨNG CỨ
CHÍNH CỦA THỦ TỤC: CCCD ghi <tên đúng> ↔ GCN ghi <tên sai>" và cảnh báo "Không tải nguyên tệp Đơn
vào đây — cán bộ mở mục ③ cần thấy CCCD, không phải Đơn". Bản chất thủ tục đính chính là đối chiếu
giấy tờ tùy thân với Giấy chứng nhận, nên thẻ căn cước chính là thành phần hồ sơ bắt buộc của dòng
này; để nó ở dòng Đơn sẽ khiến mục ③ trống và hồ sơ bị trả lại. data[note] của process nói rõ chỗ
này để cán bộ soát.

GIẤY TỜ KHÔNG CÓ DÒNG RIÊNG (giấy xác nhận cư trú, tờ khai thuế, biên lai...): ảnh ánh xạ khuyên cán
bộ bấm "+ Thêm giấy tờ" để tách ra dòng mới, NHƯNG engine attp-row chỉ điền vào các dòng CÓ SẴN và
extension không được sửa trong phạm vi thủ tục này -> để KHÔNG RỚT FILE, ta đính chúng CHUNG vào
DÒNG ĐƠN (index 0), giữ TÊN FILE GỐC làm documentName + cảnh báo. Đây là điểm CỐ Ý khác khuyến nghị
thao tác tay trong ảnh ánh xạ.

Phân loại LLM-FIRST tuyệt đối: doc_type CHỈ lấy từ LLM, KHÔNG có nhánh rule keyword (giòn, dễ sai).
Không rõ/không hợp lệ -> đính CHUNG vào dòng Đơn, KHÔNG bỏ file, giữ TÊN FILE GỐC + cảnh báo.
KHÔNG set Bản chính/Bản sao (loaiBan): cán bộ tự chọn (ảnh ánh xạ nhắc mục ① còn cho phép "1 Bản
photo", và bản gốc GCN vẫn phải nộp trực tiếp — đó là quyết định của cán bộ, không phải của máy).
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON_BIEN_DONG = "don_bien_dong"
_LAND_CERTIFICATE = "land_certificate"
_ERROR_PROOF = "giay_to_chung_minh_sai_sot"
_IDENTITY = "identity"
_AUTHORIZATION = "authorization"
_OTHER = "other"

# componentName lấy VERBATIM từ cột "Tên giấy tờ" của 'đính chính đính kèm.html'; mỗi chuỗi đã soát
# chéo trên cả 4 dòng DOM để chỉ khớp đúng dòng mong muốn (FE so khớp hai chiều sau khi fold dấu).
_DON_NAME = "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18"
_DON_INDEX = 0
_LAND_CERTIFICATE_NAME = "Bản gốc Giấy chứng nhận đã cấp"
_LAND_CERTIFICATE_INDEX = 1
_ERROR_PROOF_NAME = "Giấy tờ chứng minh sai sót thông tin của người được cấp Giấy chứng nhận"
_ERROR_PROOF_INDEX = 2
_AUTHORIZATION_NAME = "văn bản về việc ủy quyền theo quy định của pháp luật về dân sự"
_AUTHORIZATION_INDEX = 3

# Bảng của thủ tục này KHÔNG có dòng ghi chú pháp lý nào (khác thủ tục xác định lại diện tích đất ở
# cùng cổng). Giữ hằng số rỗng để test khóa cứng: bảng cổng phát sinh dòng chú thích thì phải cập
# nhật ở đây trước khi route.
_NOTE_ROW_INDEXES: set[int] = set()
# Tổng số dòng DOM có ô "Chọn tệp tin" trên bảng — mọi route phải nằm trong khoảng này.
_ROW_COUNT = 4

_ROUTES: dict[str, dict[str, Any]] = {
    _DON_BIEN_DONG: {
        "index": _DON_INDEX,
        "name": _DON_NAME,
        "documentName": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18)",
    },
    _LAND_CERTIFICATE: {
        "index": _LAND_CERTIFICATE_INDEX,
        "name": _LAND_CERTIFICATE_NAME,
        "documentName": "Bản gốc Giấy chứng nhận quyền sử dụng đất đã cấp",
    },
    _ERROR_PROOF: {
        "index": _ERROR_PROOF_INDEX,
        "name": _ERROR_PROOF_NAME,
        "documentName": "Giấy tờ chứng minh sai sót thông tin",
    },
    # CCCD/giấy tờ tùy thân LÀ chứng cứ đối chiếu tên đúng ↔ tên sai trên Giấy chứng nhận -> dòng
    # "Giấy tờ chứng minh sai sót" (xem docstring), KHÔNG phải dòng Đơn.
    _IDENTITY: {
        "index": _ERROR_PROOF_INDEX,
        "name": _ERROR_PROOF_NAME,
        "documentName": "Căn cước công dân/giấy xác nhận số định danh cá nhân (chứng minh sai sót)",
    },
    _AUTHORIZATION: {
        "index": _AUTHORIZATION_INDEX,
        "name": _AUTHORIZATION_NAME,
        "documentName": "Văn bản về việc ủy quyền",
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
        # (index 0). Giữ TÊN FILE GỐC làm documentName để cán bộ nhận ra và soát lại.
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
            f"biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18; cán bộ kiểm tra lại."
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
