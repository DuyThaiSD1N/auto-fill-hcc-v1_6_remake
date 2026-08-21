"""Attachment planner for "Thực hiện, điều chỉnh, thôi hưởng trợ cấp hưu trí xã hội".

The form has a fixed upload row for the request document. CCCD is used for
process/fill context only and must not be attached to this fixed slot.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.dieu_chinh_huu_tri_xa_hoi.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

SLOT = {
    "slotKey": "van_ban_de_nghi_huu_tri",
    "slotIndex": 0,
    "slotName": "Văn bản đề nghị thực hiện, điều chỉnh, thôi hưởng trợ cấp hưu trí xã hội",
    "detectedType": "Văn bản đề nghị trợ cấp hưu trí xã hội",
}

# CCCD/giấy tờ tùy thân KHÔNG có ô cố định → đính qua nút "Thêm giấy tờ" (modal app-add-form của cổng BYT).
# componentName phải KHỚP (fold-substring) nhãn option "Giấy tờ" trong autocomplete của modal.
CCCD_ADD = {
    "target": "add-document-dialog",
    "componentName": (
        "Một trong các giấy tờ có ảnh sau đây: Chứng minh nhân dân; Căn cước công dân; "
        "Hộ chiếu còn hiệu lực"
    ),
    "loaiBan": "Bản chính",
    "quantity": 1,
    "documentName": "Giấy tờ tùy thân có ảnh (CCCD/CMND/Hộ chiếu)",
    "detectedType": "Giấy tờ tùy thân có ảnh",
}


def is_excluded_document(text: str, file_name: str = "") -> bool:
    """Giấy tờ tùy thân không đính ở bước này."""
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
    """Rule fallback: nhận diện văn bản đề nghị từ OCR text."""
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
    raw = str(value or "").strip()
    if raw == SLOT["slotKey"]:
        return SLOT["slotKey"]
    text = _fold(raw)
    if "van ban de nghi" in text and "huu tri" in text:
        return SLOT["slotKey"]
    if "tro cap huu tri" in text and "de nghi" in text:
        return SLOT["slotKey"]
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


def _build_item(file: dict, file_index: int) -> dict:
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": SLOT["detectedType"],
        "componentName": SLOT["slotName"],
        "target": "fixed-slot",
        "needsAddComponent": False,
        "detectedType": SLOT["detectedType"],
        "slotKey": SLOT["slotKey"],
        "slotIndex": SLOT["slotIndex"],
        "slotName": SLOT["slotName"],
    }


def _build_add_document_item(file: dict, file_index: int) -> dict:
    """CCCD → tạo hàng qua modal 'Thêm giấy tờ' rồi upload (target add-document-dialog)."""
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": CCCD_ADD["documentName"],
        "componentName": CCCD_ADD["componentName"],
        "target": CCCD_ADD["target"],
        "loaiBan": CCCD_ADD["loaiBan"],
        "quantity": CCCD_ADD["quantity"],
        "needsAddComponent": True,
        "detectedType": CCCD_ADD["detectedType"],
    }


def _supports_add_document(options: dict | None) -> bool:
    """Extension bản mới báo năng lực qua options.attachSupports. Bản CŨ không gửi → False → giữ hành vi cũ
    (bỏ CCCD) để không phát target 'add-document-dialog' mà extension cũ chưa xử lý được (tránh lỗi 'target
    chưa hỗ trợ trong luồng hỗn hợp')."""
    caps = (options or {}).get("attachSupports") or []
    return isinstance(caps, (list, tuple)) and "add-document-dialog" in caps


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_slots: dict[int, str] | None = None,
    support_add_doc: bool = False,
) -> tuple[list[dict], list[str]]:
    llm_slots = llm_slots or {}
    by_name = {item.get("name"): item for item in ocr_results}
    items: list[dict] = []
    warnings: list[str] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = str(by_name.get(file_name, {}).get("text") or "")
        slot_key = llm_slots.get(idx, "") or detect_slot_key(text, file_name)
        if slot_key == SLOT["slotKey"]:
            items.append(_build_item(file, idx))
            continue
        if is_excluded_document(text, file_name):
            if support_add_doc:
                # Extension mới: CCCD đính qua nút "Thêm giấy tờ" (modal).
                items.append(_build_add_document_item(file, idx))
            else:
                # Extension cũ chưa hỗ trợ modal → giữ hành vi cũ, bỏ qua (không gây lỗi luồng hỗn hợp).
                warnings.append(
                    f"File '{file_name}' là giấy tờ tùy thân — không đính kèm ở bước này, đã bỏ qua."
                )
        else:
            warnings.append(f"Không xác định được file '{file_name}' là văn bản đề nghị hưu trí xã hội — bỏ qua.")

    return items, warnings


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    """Entry point đính kèm cho dieu-chinh-huu-tri-xa-hoi."""
    _ = session
    support_add_doc = _supports_add_document(options)
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

    attachments, warnings = build_plan_items(raw_files, ocr_results, llm_slots, support_add_doc)
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
