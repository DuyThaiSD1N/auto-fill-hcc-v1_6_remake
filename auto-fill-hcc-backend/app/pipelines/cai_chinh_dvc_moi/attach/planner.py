"""Đính kèm thay đổi, cải chính hộ tịch (Cổng DVC quốc gia mới).

Bảng thành phần có hai dòng: "Văn bản ủy quyền..." và "Giấy tờ làm căn cứ
thay đổi, cải chính, bổ sung thông tin hộ tịch". Một dòng nhận nhiều tệp (nút "Tải lên file" + input dùng
chung). LLM đọc từng tệp để nhận ra VĂN BẢN ỦY QUYỀN → dòng 1; mọi tệp còn lại (CCCD, trích lục, tờ khai, giấy
tờ làm căn cứ) → dòng 2. LLM lỗi / OCR hụt → dòng 2, không tệp nào bị bỏ.
"""

import asyncio
import os
import time

from app.config import settings
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_UY_QUYEN = "uy_quyen"

ROW_UY_QUYEN = {"slotKey": "cai_chinh_uy_quyen", "slotIndex": 0, "slotName": "Văn bản ủy quyền"}
ROW_CAN_CU = {
    "slotKey": "cai_chinh_can_cu",
    "slotIndex": 1,
    "slotName": "Giấy tờ làm căn cứ thay đổi, cải chính, bổ sung thông tin hộ tịch",
}


def build_plan_items(file_names: list[str], doc_types: dict[int, str]) -> list[dict]:
    items = []
    for index, name in enumerate(file_names):
        is_uy_quyen = doc_types.get(index) == _UY_QUYEN
        row = ROW_UY_QUYEN if is_uy_quyen else ROW_CAN_CU
        items.append({
            "fileIndex": index,
            "fileName": name,
            "documentName": os.path.splitext(name)[0] or name,
            "componentName": row["slotName"],
            "target": "fixed-slot",
            "needsAddComponent": False,
            "detectedType": _UY_QUYEN if is_uy_quyen else "other",
            "noChooserClick": True,
            **row,
        })
    return items


async def _classify_one(index: int, text: str) -> tuple[int, str]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt([{"index": index, "text": text[:12000]}])},
    ]
    raw = await client.chat(messages, max_tokens=120, enable_thinking=settings.agent_reasoning)
    first = next(iter(client.extract_json_block(raw).get("documents", []) or []), {})
    return index, _UY_QUYEN if str(first.get("docType") or "").strip() == _UY_QUYEN else "other"


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    from app.services import ocr

    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    errors: list[str] = []
    pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]
    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file([f for _, f in pairs]) if pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    texts = {}
    for (index, file), result in zip(pairs, ocr_results):
        if result.get("error"):
            errors.append(f"OCR {file.get('name')}: {result['error']}")
        if str(result.get("text") or "").strip():
            texts[index] = str(result["text"])

    started = time.monotonic()
    outcomes = await asyncio.gather(*(_classify_one(i, t) for i, t in texts.items()), return_exceptions=True)
    llm_ms = int((time.monotonic() - started) * 1000)
    doc_types: dict[int, str] = {}
    for index, outcome in zip(texts, outcomes):
        if isinstance(outcome, BaseException):
            errors.append(f"attachment_agent file {index}: {outcome}")
            continue
        doc_types[index] = outcome[1]

    attachments = build_plan_items([f["name"] for f in raw_files], doc_types)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "classified": [
                {"fileName": item["fileName"], "docType": item["detectedType"], "slotIndex": item["slotIndex"]}
                for item in attachments
            ],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
