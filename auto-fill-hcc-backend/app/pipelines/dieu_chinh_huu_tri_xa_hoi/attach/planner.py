"""Đính kèm cho thủ tục "Thực hiện, điều chỉnh, thôi hưởng trợ cấp hưu trí xã hội" (cổng BYT).

⚑ BẢNG THÀNH PHẦN HỒ SƠ CHỈ CÒN **ĐÚNG MỘT DÒNG** (chốt user 2026-09-15): "Văn bản đề nghị hưởng trợ
cấp hưu trí xã hội (theo Mẫu số 01 ban hành kèm theo Nghị định số 176/2025/NĐ-CP)". Cổng đã bỏ các
thành phần phụ và bỏ luôn nút "Thêm giấy tờ" → **MỌI FILE đều đính vào dòng 1** (fixed-slot,
slotIndex 0). Không còn nhánh `add-document-dialog` nào ở thủ tục này.

Phân loại LLM **chỉ còn để đặt TÊN HIỂN THỊ + cảnh báo**, không còn quyết định đích đến. (Với
target `fixed-slot`, FE upload bằng TÊN FILE GỐC — `documentName` chỉ hiện trong kế hoạch/trace.)

⚠ TUYỆT ĐỐI KHÔNG dùng lưới keyword để phân loại (chốt user 2026-09-15). Hai hàm
`is_excluded_document` / `detect_slot_key` bên dưới CHỈ còn để đối chứng, không nằm trong luồng.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.dieu_chinh_huu_tri_xa_hoi.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_TYPE_GIAY_TO_TUY_THAN = "giay_to_tuy_than"

SLOT = {
    "slotKey": "van_ban_de_nghi_huu_tri",
    "slotIndex": 0,
    # Text VERBATIM dòng duy nhất của cổng (đã đổi theo Nghị định 176/2025/NĐ-CP). FE dùng slotIndex
    # (slotKey không nằm trong FIXED_SLOT_KEYWORDS) nên đây chủ yếu để hiển thị/đối chiếu trace.
    "slotName": (
        "Văn bản đề nghị hưởng trợ cấp hưu trí xã hội "
        "(theo Mẫu số 01 ban hành kèm theo Nghị định số 176/2025/NĐ-CP)"
    ),
    "detectedType": "Văn bản đề nghị trợ cấp hưu trí xã hội",
}



def is_excluded_document(text: str, file_name: str = "") -> bool:
    """⚠ KHÔNG CÒN DÙNG TRONG LUỒNG QUYẾT ĐỊNH — giữ lại chỉ để tham chiếu/đối chứng.

    Lưới keyword này từng quét OCR tìm "can cuoc cong dan"/"the can cuoc"… để coi file là giấy tờ tùy
    thân. Nó SAI ở mọi giấy tờ hành chính có NHẮC số căn cước của người khác: hồ sơ thật
    (req_1d66e02a4271) nộp TRÍCH LỤC KHAI TỬ có dòng "Giấy tờ tùy thân: Thẻ căn cước công dân số …"
    → bị xếp thành CCCD và đính vào dòng "Một trong các giấy tờ có ảnh…". Việc phân loại giờ do LLM
    đảm nhiệm hoàn toàn (prompt.py có type giay_to_tuy_than + khối <traps>).
    """
    _ = file_name
    haystack = _fold(text or "")
    if not haystack:
        return False
    return any(
        marker in haystack
        for marker in (
            "can cuoc cong dan",
            "cccd",
            "chung minh nhan dan",
            "the can cuoc",
            "citizen identity card",
            "identity card",
            "ho chieu",
            "passport",
        )
    )


def detect_slot_key(text: str, file_name: str = "") -> str:
    """⚠ KHÔNG CÒN DÙNG TRONG LUỒNG QUYẾT ĐỊNH — giữ lại chỉ để tham chiếu/đối chứng.

    Lưới keyword nhận diện văn bản đề nghị từ OCR text. Đã gỡ khỏi `build_plan_items` (chốt user
    2026-09-15: "đừng dùng keyword, dùng LLM"). Phân loại giờ do LLM đảm nhiệm 100%; LLM im lặng thì
    file rơi về dòng Văn bản đề nghị kèm cảnh báo, KHÔNG đoán bằng keyword.
    """
    _ = file_name
    haystack = _fold(text or "")
    if not haystack:
        return ""
    # Mẫu số 01 là biểu mẫu duy nhất của thủ tục này. Chặn sớm để tiêu đề chung
    # không làm rule fallback nhận nhầm một mẫu khác ghi rõ Mẫu số 02.
    if "mau so 02" in haystack and "mau so 01" not in haystack:
        return ""
    if (
        "van ban de nghi huong tro cap huu tri xa hoi" in haystack
        or "de nghi huong tro cap huu tri xa hoi" in haystack
        or "de nghi nhan tro cap huu tri xa hoi tai noi cu tru moi" in haystack
        or "de nghi thay doi thong tin nguoi dang huong tro cap huu tri xa hoi" in haystack
        or (
            "mau so 01" in haystack
            and "tro cap huu tri xa hoi" in haystack
            and (
                "thong tin nguoi de nghi" in haystack
                or "thong tin nguoi dang huong" in haystack
            )
        )
    ):
        return SLOT["slotKey"]
    return ""


def _slot_from_llm_type(value: str) -> str:
    """Chuẩn hoá type LLM → "" (other) | slotKey văn bản đề nghị | giay_to_tuy_than."""
    raw = str(value or "").strip()
    if raw == SLOT["slotKey"]:
        return SLOT["slotKey"]
    if raw == _TYPE_GIAY_TO_TUY_THAN:
        return _TYPE_GIAY_TO_TUY_THAN
    text = _fold(raw)
    if "van ban de nghi" in text and "huu tri" in text:
        return SLOT["slotKey"]
    if "tro cap huu tri" in text and "de nghi" in text:
        return SLOT["slotKey"]
    if "giay to tuy than" in text or "can cuoc" in text or "ho chieu" in text:
        return _TYPE_GIAY_TO_TUY_THAN
    return ""


async def _classify_documents_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=300, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    out: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        out[idx] = _slot_from_llm_type(str(item.get("type") or ""))
    return out


def _build_item(file: dict, file_index: int, document_name: str = "") -> dict:
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    label = document_name or SLOT["detectedType"]
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": label,
        "componentName": SLOT["slotName"],
        "target": "fixed-slot",
        "needsAddComponent": False,
        "detectedType": label,
        "slotKey": SLOT["slotKey"],
        "slotIndex": SLOT["slotIndex"],
        "slotName": SLOT["slotName"],
    }




def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_slots: dict[int, str] | None = None,
) -> tuple[list[dict], list[str]]:
    """MỌI FILE đều đính vào dòng 1 — bảng của thủ tục này chỉ còn đúng một dòng.

    LLM chỉ dùng để đặt tên hiển thị và cảnh báo giấy tờ không phải Văn bản đề nghị; nó KHÔNG còn
    quyết định đích đến, và KHÔNG có lưới keyword nào tham gia.
    """
    llm_slots = llm_slots or {}
    del ocr_results  # OCR text không còn được dùng để suy loại (LLM-first tuyệt đối).
    items: list[dict] = []
    warnings: list[str] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        doc_type = llm_slots.get(idx, "")

        if doc_type == SLOT["slotKey"]:
            items.append(_build_item(file, idx))
            continue

        # Không phải Văn bản đề nghị nhưng VẪN đính (dòng 1 là chỗ duy nhất) — tuyệt đối không bỏ sót
        # file. Tên hiển thị giữ khác nhau để cán bộ soát được trong danh sách kế hoạch.
        if doc_type == _TYPE_GIAY_TO_TUY_THAN:
            label = "Giấy tờ tùy thân có ảnh (CCCD/CMND/Hộ chiếu)"
            reason = "là giấy tờ tùy thân"
        else:
            label = f"Tài liệu khác - {file_name}"
            reason = "chưa nhận diện chắc loại giấy tờ"
        items.append(_build_item(file, idx, label))
        warnings.append(
            f"File '{file_name}' {reason}, không phải Văn bản đề nghị (Mẫu số 01) — vẫn đính vào dòng "
            "duy nhất của thủ tục; cán bộ kiểm tra lại."
        )

    return items, warnings


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    """Entry point đính kèm cho dieu-chinh-huu-tri-xa-hoi."""
    _ = session
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    from app.services import ocr

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    ocr_by_name = {item.get("name"): item for item in ocr_results}
    llm_docs: list[dict[str, Any]] = []
    for idx, file in enumerate(raw_files):
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        if text.strip():
            llm_docs.append({"index": idx, "text": text})

    t1 = time.monotonic()
    llm_slots: dict[int, str] = {}
    if llm_docs:
        try:
            llm_slots = await _classify_documents_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings = build_plan_items(raw_files, ocr_results, llm_slots)
    errors.extend(warnings)
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]
    ocr_text = "\n\n---\n\n".join(
        f"===== {r.get('name') or '(không tên)'} =====\n{str(r.get('text') or '').strip()}"
        for r in ocr_results
        if r.get("text")
    )

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "skippedOcr": skipped_ocr,
            "slots": [SLOT["slotName"]],
        },
        "ocr_text": ocr_text,
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "errors": errors,
    }
