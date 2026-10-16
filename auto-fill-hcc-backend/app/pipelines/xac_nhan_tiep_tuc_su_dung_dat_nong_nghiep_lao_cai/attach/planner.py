"""Đính kèm [Lào Cai] 1.013947 — bảng "Thành phần hồ sơ" của cổng `dichvucong.laocai.gov.vn`.

Bảng PHẲNG, 3 dòng theo thứ tự DOM (theo ảnh ánh xạ đính kèm); mỗi dòng có checkbox + "Số bản" + nút
"Chọn tệp tin" (+ cột "Loại" mặc định "Bản" sau khi tích):

  0. Tập tin chứa thành phần hồ sơ theo mục b.2.1 phải được số hóa từ bản chính hoặc bản sao …
     → yêu cầu CHUNG về số hoá, áp cho cả Đơn và Giấy chứng nhận đã đính ở dòng 1, 2. KHÔNG tích, KHÔNG
       đính (tải lại ở đây là trùng tệp).
  1. Văn bản đề nghị xác nhận lại thời hạn sử dụng đất theo Mẫu số 09 tại Phụ lục ban hành kèm theo
     Nghị định số 102/2024/NĐ-CP …
  2. Giấy chứng nhận đã cấp.

Bên dưới: "Lấy giấy tờ từ KDL" / "Biểu mẫu giấy tờ" (không dùng), "Về việc" (*) + "Ghi chú" do cổng điền
sẵn — KHÔNG ghi đè, và danh sách "Giấy tờ khác" (Loại "Mới", tự gõ tên rồi chọn tệp).

Khớp ô theo `slotIndex` + `tickRow`, slotKey CỐ Ý không nằm trong `FIXED_SLOT_KEYWORDS` của content.js
(giống 1.115677) để FE dùng thẳng thứ tự DOM. Đơn in tiêu đề "Mẫu số 39" trong khi dòng 1 ghi "Mẫu số 09
… NĐ 102/2024" — cùng loại văn bản đề nghị, planner nhắc để cán bộ biết.

MỘT TỆP chỉ đi ĐÚNG MỘT DÒNG, không cắt trang. Giấy chứng nhận chụp thành nhiều ảnh (bìa, trang chứng
nhận) → tất cả vào dòng 2. Giấy tờ không có dòng riêng (Đơn đăng ký biến động Mẫu 24, CCCD, giấy ủy
quyền, mảnh trích đo) xuống "Giấy tờ khác" kèm cảnh báo, không âm thầm bỏ tệp.
"""

import asyncio
import time

from app.config import settings
from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep.attach.planner import (
    _canon,
    _data_url_size,
    _other_display,
    _unique_document_name,
)
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
# Cổng ghi rõ trên trang: "Dung lượng tối đa là 6 Mb".
_MAX_FILE_BYTES = 6 * 1024 * 1024

_OTHER = "khac"

# 3 dòng của bảng; `slotIndex` là thứ tự DOM 0-based của các ô upload. Dòng 0 không bao giờ đính.
_ROWS: dict[int, str] = {
    0: "Tập tin chứa thành phần hồ sơ theo mục b.2.1 phải được số hóa từ bản chính hoặc bản sao giấy tờ "
       "đã được công chứng, chứng thực theo quy định của pháp luật",
    1: "Văn bản đề nghị xác nhận lại thời hạn sử dụng đất theo Mẫu số 09 tại Phụ lục ban hành kèm theo "
       "Nghị định số 102/2024/NĐ-CP",
    2: "Giấy chứng nhận đã cấp",
}

# docType (LLM) → (slotIndex, tên hiển thị của tài liệu).
_ROUTES: dict[str, tuple[int, str]] = {
    "don_de_nghi": (1, "Đơn xin xác nhận lại thời hạn sử dụng đất nông nghiệp"),
    "gcn": (2, "Giấy chứng nhận quyền sử dụng đất đã cấp"),
}

# docType KHÔNG có dòng riêng → "Giấy tờ khác" (tên dòng = documentName).
_OTHER_ROUTES: dict[str, str] = {
    "don_bien_dong": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 24)",
    "manh_trich_do": "Mảnh trích đo bản đồ địa chính thửa đất",
    "van_ban_dai_dien": "Văn bản về việc đại diện (Giấy ủy quyền)",
    "giay_to_nhan_than": "CCCD và giấy tờ hộ tịch của người sử dụng đất",
    _OTHER: "Tài liệu kèm theo",
}

_ALLOWED = set(_ROUTES) | set(_OTHER_ROUTES)

# Dòng 1, 2 là thành phần hồ sơ BẮT BUỘC — trống thì phải nhắc.
_ROWS_CAN_NHAC = {
    1: "Văn bản đề nghị xác nhận lại thời hạn sử dụng đất (Đơn Mẫu số 09/39)",
    2: "Giấy chứng nhận đã cấp",
}

# Giấy tờ đưa xuống "Giấy tờ khác" dù KHÔNG thuộc thành phần hồ sơ → nhắc cán bộ xoá nếu không cần.
_NGOAI_THANH_PHAN: dict[str, str] = {
    "don_bien_dong": "Đơn đăng ký biến động đất đai (Mẫu số 24)",
    "giay_to_nhan_than": "CCCD/giấy tờ hộ tịch",
}


def _normalize_doc_type(value) -> str:
    canon = _canon(value)
    for doc_type in _ALLOWED:
        if canon == _canon(doc_type):
            return doc_type
    return _OTHER


async def _classify_one(document: dict) -> tuple[int, str]:
    index = int(document.get("index"))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",
         "content": build_user_prompt([{"index": index, "text": str(document.get("text") or "")[:12000]}])},
    ]
    raw = await client.chat(messages, max_tokens=120, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    first = next(iter(parsed.get("documents", []) or []), {})
    return index, _normalize_doc_type(first.get("docType") or first.get("type"))


async def _classify_with_llm(documents: list[dict], errors: list[str] | None = None) -> dict[int, str]:
    if not documents:
        return {}
    outcomes = await asyncio.gather(*(_classify_one(d) for d in documents), return_exceptions=True)
    result: dict[int, str] = {}
    for document, outcome in zip(documents, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            if errors is not None:
                errors.append(f"attachment_agent file {document.get('index')}: {outcome}")
            continue
        index, doc_type = outcome
        result[index] = doc_type
    return result


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    unknown: list[str] = []
    used_other_names: set[str] = set()

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        llm_type = llm_types.get(index, "")
        doc_type = llm_type if llm_type in _ALLOWED else _OTHER
        source = "llm" if llm_type else "default"

        if doc_type in _ROUTES:
            slot_index, document_name = _ROUTES[doc_type]
            attachments.append({
                "fileIndex": index,
                "fileName": file_name,
                "documentName": document_name,
                "componentName": _ROWS[slot_index],
                "target": "fixed-slot",
                "needsAddComponent": False,
                # slotKey theo DÒNG để nhiều ảnh Giấy chứng nhận cùng dòng được GOM vào một lần bơm tệp.
                "slotKey": f"lc_013947_row_{slot_index}",
                "slotIndex": slot_index,
                "slotName": _ROWS[slot_index],
                "tickRow": True,
                "detectedType": doc_type,
            })
            classified.append({
                "fileName": file_name, "docType": doc_type, "source": source, "slotIndex": slot_index,
            })
            continue

        base_name = _other_display(file_name) if doc_type == _OTHER else _OTHER_ROUTES[doc_type]
        document_name = _unique_document_name(base_name, used_other_names)
        if doc_type == _OTHER:
            unknown.append(file_name)
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": document_name,
            "componentName": document_name,
            "target": "new",
            "needsAddComponent": True,
            "detectedType": doc_type,
            # iGate VNPT: bấm "Chọn tệp tin" mở hộp thoại file của hệ điều hành → FE chỉ gán thẳng.
            "noChooserClick": True,
        })
        classified.append({"fileName": file_name, "docType": doc_type, "source": source, "slotIndex": None})

    if unknown:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã tạm đưa xuống \"Giấy tờ khác\" để không bỏ sót — cán bộ kiểm "
            f"tra lại: {', '.join(unknown)}."
        )

    filled_rows = {item["slotIndex"] for item in attachments if item.get("target") == "fixed-slot"}
    thieu = [name for slot, name in sorted(_ROWS_CAN_NHAC.items()) if slot not in filled_rows]
    if thieu:
        warnings.append(
            "Chưa có tệp nào cho dòng: " + "; ".join(thieu) + ". Đây là thành phần hồ sơ bắt buộc của "
            "thủ tục — cán bộ đề nghị người dân bổ sung rồi tích dòng."
        )
    if 1 in filled_rows:
        warnings.append(
            "Đơn giấy thường in tiêu đề \"Mẫu số 39\" trong khi dòng thành phần hồ sơ ghi \"Mẫu số 09 … Nghị "
            "định số 102/2024/NĐ-CP\" — cùng loại văn bản đề nghị, trợ lý vẫn đính vào dòng này; nơi tiếp "
            "nhận yêu cầu đúng mẫu thì cán bộ đề nghị người dân viết lại."
        )

    have_types = {item.get("detectedType") for item in attachments}
    ngoai = [mo_ta for doc_type, mo_ta in _NGOAI_THANH_PHAN.items() if doc_type in have_types]
    if ngoai:
        warnings.append(
            ", ".join(ngoai) + " KHÔNG thuộc thành phần hồ sơ của thủ tục này; trợ lý đưa xuống \"Giấy tờ "
            "khác\" để không bỏ sót tệp. Nơi tiếp nhận không yêu cầu thì cán bộ xoá dòng đó đi."
        )

    if not attachments:
        warnings.append("Không có tài liệu nào để đính kèm.")
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]

    valid_files: list[dict] = []
    for file in raw_files:
        size = _data_url_size(file.get("dataUrl", ""))
        if size > _MAX_FILE_BYTES:
            errors.append(
                f"File '{file['name']}' vượt quá 6 MB ({size / 1024 / 1024:.2f} MB) — cổng không nhận, "
                "đã bỏ qua."
            )
        else:
            valid_files.append(file)

    from app.services import ocr

    ocr_files = [f for f in valid_files if f.get("type") in _OCR_TYPES]
    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    llm_documents = [
        {"index": index, "text": str(by_name.get(file.get("name"), {}).get("text") or "")}
        for index, file in enumerate(valid_files)
        if str(by_name.get(file.get("name"), {}).get("text") or "").strip()
    ]
    started = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_documents:
        try:
            llm_types = await _classify_with_llm(llm_documents, errors)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(valid_files, llm_types)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [valid_files[d["index"]]["name"] for d in llm_documents],
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
