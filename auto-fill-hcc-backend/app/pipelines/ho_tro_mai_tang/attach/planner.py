"""Đính kèm cho thủ tục Hỗ trợ chi phí mai táng.

Khác với chứng thực (ví giấy tờ + thêm thành phần mới), thủ tục này có 3 THÀNH PHẦN
HỒ SƠ CỐ ĐỊNH sẵn trên form, mỗi thành phần 1 ô upload riêng. Nhiệm vụ ở đây là OCR +
phân loại mỗi file vào ĐÚNG 1 trong 3 ô (hoặc bỏ qua nếu không khớp) rồi trả "fixed-slot"
plan để extension bơm file vào input của đúng hàng.
"""
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.ho_tro_mai_tang.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# 3 thành phần hồ sơ cố định (đúng thứ tự hiển thị trên form bước 3).
SLOTS: list[dict] = [
    {
        "slotKey": "to_khai_mai_tang",
        "slotIndex": 0,
        "slotName": "Tờ khai đề nghị hỗ trợ chi phí mai táng (Mẫu số 04)",
        "detectedType": "Tờ khai đề nghị hỗ trợ chi phí mai táng",
    },
    {
        "slotKey": "giay_chung_tu",
        "slotIndex": 1,
        "slotName": "Bản sao giấy chứng tử hoặc giấy báo tử của đối tượng",
        "detectedType": "Giấy chứng tử/Trích lục khai tử",
    },
    {
        "slotKey": "quyet_dinh_thoi_huong",
        "slotIndex": 2,
        "slotName": "Bản sao quyết định/danh sách thôi hưởng trợ cấp BHXH",
        "detectedType": "Quyết định thôi hưởng trợ cấp",
    },
]
_SLOT_BY_KEY = {s["slotKey"]: s for s in SLOTS}


def is_excluded_document(text: str, file_name: str = "") -> bool:
    """CCCD/CMND/hộ chiếu — KHÔNG nằm trong 3 thành phần hồ sơ, không đính kèm ở bước này.

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
    """Phân loại nhanh bằng rule trên OCR text; trả slotKey hoặc "" nếu không chắc.

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
    return _SLOT_BY_KEY.get(value, {}).get("slotKey", "") if value in _SLOT_BY_KEY else ""


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
    llm_slots = llm_slots or {}
    by_name = {item.get("name"): item for item in ocr_results}
    items: list[dict] = []
    warnings: list[str] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        ocr_item = by_name.get(file_name, {})
        text = str(ocr_item.get("text") or "")
        rule_slot = detect_slot_key(text, file_name)
        if rule_slot:
            slot_key = rule_slot
        elif is_excluded_document(text, file_name):
            # CCCD/giấy tùy thân không thuộc 3 thành phần hồ sơ — bỏ qua, KHÔNG hỏi LLM.
            warnings.append(f"File '{file_name}' là giấy tùy thân (CCCD) — không cần đính kèm ở bước này, đã bỏ qua.")
            continue
        else:
            slot_key = llm_slots.get(idx, "")
        slot = _SLOT_BY_KEY.get(slot_key)
        if not slot:
            warnings.append(
                f"Không xác định được loại giấy tờ cho file '{file_name}' — bỏ qua, vui lòng đính kèm thủ công."
            )
            continue
        items.append(
            {
                "fileIndex": idx,
                "fileName": file_name,
                "documentName": slot["detectedType"],
                "componentName": slot["slotName"],
                "target": "fixed-slot",
                "needsAddComponent": False,
                "detectedType": slot["detectedType"],
                "slotKey": slot["slotKey"],
                "slotIndex": slot["slotIndex"],
                "slotName": slot["slotName"],
            }
        )

    return items, warnings


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    """Entry point đính kèm cho ho-tro-mai-tang (gọi qua registry.get_attach_pipeline)."""
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
