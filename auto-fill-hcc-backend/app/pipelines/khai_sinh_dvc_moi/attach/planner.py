"""Đính kèm đăng ký khai sinh (Cổng DVC quốc gia mới).

Bảng thành phần có 4 dòng (giấy chứng sinh / mang thai hộ / trẻ bị bỏ rơi / văn bản ủy quyền), một dòng nhận nhiều
tệp qua nút "Tải lên file". LLM đọc từng tệp để nhận ra văn bản mang thai hộ, biên bản trẻ bị bỏ rơi, văn bản ủy
quyền → đúng dòng; mọi tệp còn lại (giấy chứng sinh, tờ khai, giấy kết hôn, CCCD, trích lục khai tử...) đính
chung vào dòng giấy chứng sinh vì cổng không có dòng riêng. LLM lỗi / OCR hụt → dòng giấy chứng sinh.

Cổng chỉ nhận tệp dưới 2 MB: tệp trên 2 MB được nén bằng đúng thang của cải chính (cùng Cổng DVC quốc gia mới), trả
về ở `replaceFiles` để extension đính bản nén thay bản gốc. Tệp nhỏ hơn để nguyên. OCR vẫn đọc bản gốc.
"""

import asyncio
import os
import time

from app.config import settings
from app.pipelines.cai_chinh_dvc_moi.attach.planner import shrink_oversized
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

ROW_CHUNG_SINH = {"slotKey": "khai_sinh_chung_sinh", "slotIndex": 0,
                  "slotName": "Giấy chứng sinh; trường hợp không có Giấy chứng sinh"}
ROWS = {
    "surrogacy_doc": {"slotKey": "khai_sinh_mang_thai_ho", "slotIndex": 1,
                      "slotName": "Trường hợp khai sinh cho trẻ em sinh ra do mang thai hộ"},
    "abandoned_record": {"slotKey": "khai_sinh_bo_roi", "slotIndex": 2,
                         "slotName": "Trường hợp trẻ em bị bỏ rơi thì phải có biên bản"},
    "authorization": {"slotKey": "khai_sinh_uy_quyen", "slotIndex": 3,
                      "slotName": "Văn bản ủy quyền (được chứng thực)"},
}


def build_plan_items(file_names: list[str], doc_types: dict[int, str]) -> list[dict]:
    items = []
    for index, name in enumerate(file_names):
        doc_type = doc_types.get(index) if doc_types.get(index) in ROWS else "other"
        row = ROWS.get(doc_type, ROW_CHUNG_SINH)
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
    shrink_task = asyncio.create_task(shrink_oversized(raw_files, errors))
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

    replace_files = await shrink_task
    names = [replace_files[str(i)]["name"] if str(i) in replace_files else f["name"] for i, f in enumerate(raw_files)]
    attachments = build_plan_items(names, doc_types)
    return {
        "attachments": attachments,
        "replaceFiles": replace_files or None,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "classified": [
                {"fileName": item["fileName"], "docType": item["detectedType"], "slotIndex": item["slotIndex"]}
                for item in attachments
            ],
            "shrunk": [
                {"fileName": r["name"], "originalBytes": r["originalBytes"], "bytes": r["bytes"], "level": r["level"]}
                for r in replace_files.values()
            ],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
