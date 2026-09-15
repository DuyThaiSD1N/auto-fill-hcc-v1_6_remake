"""Đính kèm cho thủ tục "Hỗ trợ chi phí mai táng đối với đối tượng hưởng trợ cấp hưu trí xã hội".

⚑ BẢNG THÀNH PHẦN HỒ SƠ CHỈ CÒN **ĐÚNG MỘT DÒNG** (chốt user 2026-09-15): "Thành phần hồ sơ gồm: Tờ
khai đề nghị hỗ trợ chi phí mai táng (theo Mẫu số 02 ban hành kèm theo Nghị định số 176/2025/NĐ-CP)."
Cổng đã bỏ 2 dòng cũ (giấy chứng tử, quyết định thôi hưởng) và không có nút thêm thành phần → **MỌI
FILE đều đính vào dòng 1** (fixed-slot, slotIndex 0), tuyệt đối không bỏ sót.

Phân loại LLM **chỉ còn để đặt TÊN HIỂN THỊ + cảnh báo**, không còn quyết định đích đến. (Với target
`fixed-slot`, FE upload bằng TÊN FILE GỐC — `documentName` chỉ hiện trong kế hoạch/trace.)

⚠ TUYỆT ĐỐI KHÔNG dùng lưới keyword để phân loại (chốt user 2026-09-15). Trước đây `detect_slot_key`
chạy TRƯỚC cả LLM và `is_excluded_document` quét "the can cuoc" để bỏ file — cả hai đã bị GỠ khỏi
luồng, chỉ giữ lại để đối chứng. Xem [[luoi-keyword-cccd-nuot-trich-luc-khai-tu]].
"""
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.ho_tro_mai_tang_huu_tri_xa_hoi.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# Dòng DUY NHẤT của cổng. slotName lấy VERBATIM (cổng đã đổi sang Mẫu số 02 / NĐ 176/2025, trước
# planner ghi "Mẫu số 04" là tên cũ). FE tìm ô bằng slotIndex nên đây chủ yếu để hiển thị/đối chiếu.
SLOT = {
    "slotKey": "to_khai_mai_tang",
    "slotIndex": 0,
    "slotName": (
        "Thành phần hồ sơ gồm: Tờ khai đề nghị hỗ trợ chi phí mai táng "
        "(theo Mẫu số 02 ban hành kèm theo Nghị định số 176/2025/NĐ-CP)."
    ),
    "detectedType": "Tờ khai đề nghị hỗ trợ chi phí mai táng",
}
SLOTS: list[dict] = [SLOT]  # giữ tên cũ cho chỗ đọc `extracted.slots`.

# Nhãn hiển thị theo loại LLM nhận ra (chỉ để cán bộ soát trong kế hoạch, không đổi đích đến).
_LABELS = {
    "to_khai_mai_tang": "Tờ khai đề nghị hỗ trợ chi phí mai táng",
    "giay_chung_tu": "Giấy chứng tử/Trích lục khai tử",
    "quyet_dinh_thoi_huong": "Quyết định thôi hưởng trợ cấp",
}


def is_excluded_document(text: str, file_name: str = "") -> bool:
    """⚠ KHÔNG CÒN DÙNG TRONG LUỒNG QUYẾT ĐỊNH — giữ lại chỉ để tham chiếu/đối chứng.

    Lưới keyword quét OCR tìm "can cuoc"/"the can cuoc"… để BỎ file. Nó sai ở mọi giấy tờ hành chính
    có NHẮC số căn cước của người khác (trích lục khai tử ghi "Giấy tờ tùy thân: Thẻ căn cước công
    dân số …") và vi phạm nguyên tắc không-bỏ-sót-file. Đã gỡ khỏi `build_plan_items`.

    Chỉ tính khi chính tài liệu LÀ giấy tùy thân (tiêu đề), không tính các giấy tờ chỉ
    *nhắc tới* số căn cước (vd trích lục khai tử có dòng "Thẻ căn cước công dân số...").
    """
    haystack = _fold((text or "") + "\n" + (file_name or ""))
    if not haystack:
        return False
    return (
        "can cuoc cong dan" in haystack
        or "cccd" in haystack
        or "chung minh nhan dan" in haystack
        or "the can cuoc" in haystack
        or "citizen identity card" in haystack
    )


def detect_slot_key(text: str, file_name: str = "") -> str:
    """⚠ KHÔNG CÒN DÙNG TRONG LUỒNG QUYẾT ĐỊNH — giữ lại chỉ để tham chiếu/đối chứng.

    Trước đây hàm này chạy TRƯỚC cả LLM nên keyword đè hoàn toàn kết quả phân loại. Đã gỡ khỏi
    `build_plan_items` (chốt user 2026-09-15: "đừng dùng keyword, dùng LLM").

    Thứ tự ưu tiên QUAN TRỌNG: tờ khai Mẫu 04 thường liệt kê "giấy chứng tử" trong phần
    hồ sơ kèm theo, nên phải nhận diện tờ khai (theo tiêu đề riêng) TRƯỚC giấy chứng tử,
    nếu không tờ khai sẽ bị xếp nhầm vào ô chứng tử.
    """
    haystack = _fold((text or "") + "\n" + (file_name or ""))
    if not haystack:
        return ""
    # 1. Tờ khai/đơn đề nghị hỗ trợ chi phí mai táng (Mẫu 04) — tín hiệu tiêu đề riêng,
    #    trích lục khai tử độc lập KHÔNG bao giờ chứa cụm "đề nghị hỗ trợ chi phí mai táng".
    if (
        "de nghi ho tro chi phi mai tang" in haystack
        or "ho tro chi phi mai tang" in haystack
        or "to khai de nghi ho tro" in haystack
        or "mau so 04" in haystack
    ):
        return "to_khai_mai_tang"
    # 2. Quyết định/danh sách thôi hưởng trợ cấp.
    if "thoi huong" in haystack and ("tro cap" in haystack or "bao hiem xa hoi" in haystack):
        return "quyet_dinh_thoi_huong"
    # 3. Giấy chứng tử/báo tử/trích lục khai tử (tài liệu độc lập).
    if (
        "trich luc khai tu" in haystack
        or "giay chung tu" in haystack
        or "giay bao tu" in haystack
    ):
        return "giay_chung_tu"
    return ""


def _slot_from_llm_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return ""
    if "chung tu" in text or "bao tu" in text or "khai tu" in text:
        return "giay_chung_tu"
    if "thoi huong" in text:
        return "quyet_dinh_thoi_huong"
    if "mai tang" in text or "to khai" in text:
        return "to_khai_mai_tang"
    return ""


async def _classify_documents_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=400, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    out: dict[int, str] = {}
    for item in parsed.get("documents", []):
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        out[idx] = _slot_from_llm_type(str(item.get("type") or ""))
    return out


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_slots: dict[int, str] | None = None,
) -> tuple[list[dict], list[str]]:
    """MỌI FILE đều đính vào dòng 1 — bảng của thủ tục này chỉ còn đúng một dòng.

    LLM chỉ dùng để đặt tên hiển thị và cảnh báo giấy tờ không phải Tờ khai; nó KHÔNG còn quyết định
    đích đến, và KHÔNG có lưới keyword nào tham gia.
    """
    llm_slots = llm_slots or {}
    del ocr_results  # OCR text không còn được dùng để suy loại (LLM-first tuyệt đối).
    items: list[dict] = []
    warnings: list[str] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        doc_type = llm_slots.get(idx, "")
        label = _LABELS.get(doc_type) or f"Tài liệu khác - {file_name}"

        items.append({
            "fileIndex": idx,
            "fileName": file_name,
            "documentName": label,
            "componentName": SLOT["slotName"],
            "target": "fixed-slot",
            "needsAddComponent": False,
            "detectedType": label,
            "slotKey": SLOT["slotKey"],
            "slotIndex": SLOT["slotIndex"],
            "slotName": SLOT["slotName"],
        })

        # Không bỏ sót file nào; chỉ cảnh báo để cán bộ soát khi không phải Tờ khai Mẫu số 02.
        if doc_type != SLOT["slotKey"]:
            reason = (
                f"được nhận là '{_LABELS[doc_type]}'" if doc_type in _LABELS
                else "chưa nhận diện chắc loại giấy tờ"
            )
            warnings.append(
                f"File '{file_name}' {reason}, không phải Tờ khai đề nghị hỗ trợ chi phí mai táng "
                "(Mẫu số 02) — vẫn đính vào dòng duy nhất của thủ tục; cán bộ kiểm tra lại."
            )

    return items, warnings


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    """Entry point đính kèm cho ho-tro-mai-tang-huu-tri-xa-hoi."""
    _ = session
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    from app.services import ocr


    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for r in ocr_results:
        if r.get("error"):
            errors.append(f"OCR {r.get('name')}: {r['error']}")

    ocr_by_name = {r.get("name"): r for r in ocr_results}
    llm_docs: list[dict[str, Any]] = []
    for idx, f in enumerate(raw_files):
        text = str(ocr_by_name.get(f.get("name"), {}).get("text") or "")
        if text.strip():
            llm_docs.append({"index": idx, "fileName": f.get("name"), "text": text})

    t1 = time.monotonic()
    llm_slots: dict[int, str] = {}
    if llm_docs:
        try:
            llm_slots = await _classify_documents_with_llm(llm_docs)
        except Exception as e:  # noqa: BLE001
            errors.append(f"attachment_agent: {e}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings = build_plan_items(raw_files, ocr_results, llm_slots)
    errors.extend(warnings)
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [doc["fileName"] for doc in llm_docs],
            "skippedOcr": skipped_ocr,
            "slots": [s["slotName"] for s in SLOTS],
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "errors": errors,
    }
