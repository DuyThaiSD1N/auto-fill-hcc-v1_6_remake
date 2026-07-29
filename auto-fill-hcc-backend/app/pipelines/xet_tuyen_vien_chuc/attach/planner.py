"""Đính kèm cho thủ tục xét tuyển Viên chức.

Form bước "Thành phần hồ sơ" chỉ có một ô cố định: Phiếu đăng ký dự tuyển.
Planner này chỉ đính file được nhận diện là Phiếu đăng ký dự tuyển vào slot 0;
CCCD/tài liệu khác được bỏ qua để tránh đính nhầm.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.xet_tuyen_vien_chuc.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

SLOT = {
    "slotKey": "phieu_dang_ky_du_tuyen",
    "slotIndex": 0,
    "slotName": (
        "Phiếu đăng ký dự tuyển theo mẫu số 01 ban hành kèm theo Nghị định số 85/2023/NĐ-CP "
        "và hợp đồng lao động ban hành kèm theo Nghị định số 115/2020/NĐ-CP"
    ),
    "detectedType": "Phiếu đăng ký dự tuyển",
}


def is_excluded_document(text: str, file_name: str = "") -> bool:
    """Giấy tờ không phải phiếu đăng ký dự tuyển."""
    _ = file_name
    haystack = _fold(text or "")
    if not haystack:
        return False
    excluded_markers = (
        "can cuoc cong dan",
        "cccd",
        "chung minh nhan dan",
        "the can cuoc",
        "citizen identity card",
        "hochieu",
        "ho chieu",
        "passport",
    )
    return any(marker in haystack for marker in excluded_markers)


def detect_slot_key(text: str, file_name: str = "") -> str:
    """Rule fallback: nhận diện phiếu dự tuyển từ OCR text."""
    _ = file_name
    haystack = _fold(text or "")
    if not haystack:
        return ""
    if "phieu dang ky du tuyen" in haystack:
        return "phieu_dang_ky_du_tuyen"
    if "mau so 01" in haystack and ("du tuyen vien chuc" in haystack or "nghi dinh so 85/2023" in haystack):
        return "phieu_dang_ky_du_tuyen"
    if "nghi dinh so 85/2023" in haystack and "vien chuc" in haystack:
        return "phieu_dang_ky_du_tuyen"
    if "nghi dinh so 115/2020" in haystack and "du tuyen" in haystack and "vien chuc" in haystack:
        return "phieu_dang_ky_du_tuyen"
    return ""


def _slot_from_llm_type(value: str) -> str:
    text = _fold(value or "")
    if text == "phieu_dang_ky_du_tuyen" or "phieu dang ky du tuyen" in text:
        return "phieu_dang_ky_du_tuyen"
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
        slot_key = rule_slot or llm_slots.get(idx, "")
        if slot_key != SLOT["slotKey"]:
            if is_excluded_document(text, file_name):
                warnings.append(f"File '{file_name}' là giấy tờ tùy thân/tài liệu khác — không đính ở ô Phiếu đăng ký dự tuyển.")
            else:
                warnings.append(f"Không xác định được file '{file_name}' là Phiếu đăng ký dự tuyển — bỏ qua.")
            continue
        items.append(
            {
                "fileIndex": idx,
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
        )

    return items, warnings


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    """Entry point đính kèm cho xet-tuyen-vien-chuc."""
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
        if text.strip() and not detect_slot_key(text, str(f.get("name") or "")) and not is_excluded_document(text, str(f.get("name") or "")):
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
            "llmDocuments": [doc["fileName"] for doc in llm_docs],
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
