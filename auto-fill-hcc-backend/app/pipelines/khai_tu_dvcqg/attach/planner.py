"""Đính kèm khai tử (Cổng DVC quốc gia mới).

Bảng thành phần có 4 dòng cố định (giấy báo tử / văn bản ủy quyền / chứng cứ người chết đã lâu / chứng minh nơi
chết), một dòng nhận nhiều tệp qua nút "Tải lên file", không có nút "Thêm thành phần". LLM đọc từng tệp để xếp
đúng dòng; tệp không thuộc dòng nào (tờ khai, CCCD...) đính chung dòng giấy báo tử để không sót tệp. LLM lỗi /
OCR hụt → dòng giấy báo tử.
"""

import asyncio
import os
import time

from app.config import settings
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

ROW_GIAY_BAO_TU = {"slotKey": "khai_tu_giay_bao_tu", "slotIndex": 0,
                   "slotName": "Giấy báo tử hoặc giấy tờ thay Giấy báo tử"}
ROWS = {
    "death_notice": ROW_GIAY_BAO_TU,
    "authorization": {"slotKey": "khai_tu_uy_quyen", "slotIndex": 1,
                      "slotName": "Văn bản ủy quyền (được chứng thực) theo quy định"},
    "death_event_proof": {"slotKey": "khai_tu_chet_da_lau", "slotIndex": 2,
                          "slotName": "Giấy tờ, tài liệu, chứng cứ do cơ quan, tổ chức có thẩm quyền"},
    "death_place_proof": {"slotKey": "khai_tu_noi_chet", "slotIndex": 3,
                          "slotName": "Trường hợp không xác định được nơi cư trú cuối cùng"},
}


def build_plan_items(file_names: list[str], doc_types: dict[int, str]) -> list[dict]:
    items = []
    for index, name in enumerate(file_names):
        doc_type = doc_types.get(index) if doc_types.get(index) in ROWS else "other"
        row = ROWS.get(doc_type, ROW_GIAY_BAO_TU)
        items.append({
            "fileIndex": index,
            "fileName": name,
            "documentName": os.path.splitext(name)[0] or name,
            "componentName": row["slotName"],
            "target": "fixed-slot",
            "needsAddComponent": False,
            "detectedType": doc_type,
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
    return index, str(first.get("docType") or "").strip()


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
