"""Đính kèm cấp bản sao trích lục — chế độ demo (che_do_demo.BAT): CHỈ đính giấy ủy quyền.

Dòng thành phần hồ sơ duy nhất của cổng là "Văn bản ủy quyền …". LLM đọc từng tệp và gắn nhãn laUyQuyen; tệp có nhãn
true mới vào kế hoạch (cùng đích fixed-slot như chế độ thường), tệp khác bỏ qua và ghi tên vào errors để cán bộ thấy.
OCR / LLM lỗi → không biết tệp nào là giấy ủy quyền → không đính tệp nào, báo để cán bộ tự đính.
"""

import asyncio
import time

from app.process.schemas import FileItem
from app.services.llm import client

from ..dinh_kem_khong_tach.planner import _OCR_TYPES, ROW_NAME, _document_name, _max_tokens, shrink_oversized
from .prompt import SYSTEM_PROMPT, build_user_prompt


async def _labels(texts: dict[int, str]) -> dict[int, dict]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt([{"index": i, "text": t[:12000]} for i, t in texts.items()])},
    ]
    raw = await client.chat(messages, max_tokens=_max_tokens(texts), enable_thinking=False)
    out: dict[int, dict] = {}
    for item in client.extract_json_block(raw).get("documents", []) or []:
        try:
            index = int(item.get("index"))
        except (AttributeError, TypeError, ValueError):
            continue
        if index in texts and index not in out:
            out[index] = item
    return out


def _item(index: int, file_name: str, document_name: str) -> dict:
    return {
        "fileIndex": index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": ROW_NAME,
        "target": "fixed-slot",
        "needsAddComponent": False,
        "slotKey": "uy_quyen",
        "slotIndex": 0,
        "slotName": ROW_NAME,
        "noChooserClick": True,
    }


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    from app.services import ocr

    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    errors: list[str] = []
    pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]
    started = time.monotonic()
    shrink_task = asyncio.create_task(shrink_oversized(raw_files, errors))
    ocr_results = await ocr.ocr_per_file([f for _, f in pairs]) if pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    texts: dict[int, str] = {}
    for (index, file), result in zip(pairs, ocr_results):
        if result.get("error"):
            errors.append(f"OCR {file.get('name')}: {result['error']}")
        if str(result.get("text") or "").strip():
            texts[index] = str(result["text"])

    started = time.monotonic()
    labels: dict[int, dict] = {}
    llm_failed = False
    if texts:
        try:
            labels = await _labels(texts)
        except Exception as exc:  # noqa: BLE001 — không biết tệp nào là giấy ủy quyền → không đính, báo cán bộ
            llm_failed = True
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    replace_files = await shrink_task
    names = [replace_files[str(i)]["name"] if str(i) in replace_files else f["name"] for i, f in enumerate(raw_files)]
    kept = [i for i in range(len(raw_files)) if (labels.get(i) or {}).get("laUyQuyen") is True]
    attachments, seen = [], {}
    for index in kept:
        name = _document_name(names[index], str(labels[index].get("documentName") or "").strip() or "Văn bản ủy quyền")
        seen[name.lower()] = seen.get(name.lower(), 0) + 1
        if seen[name.lower()] > 1:
            name = f"{name} {seen[name.lower()]}"
        attachments.append(_item(index, names[index], name))
    skipped = [raw_files[i]["name"] for i in range(len(raw_files)) if i not in kept]
    # Một câu ngắn cho cán bộ; tên từng tệp chỉ ghi trong extracted (trace).
    if llm_failed:
        errors.append("Chưa đọc được tệp để tìm giấy ủy quyền.")
    elif not attachments:
        errors.append(f"Không có giấy ủy quyền — đã bỏ qua {len(skipped)} tệp." if skipped
                      else "Không có giấy ủy quyền.")
    elif skipped:
        errors.append(f"Đã bỏ qua {len(skipped)} tệp không phải giấy ủy quyền.")
    return {
        "attachments": attachments,
        "replaceFiles": {k: v for k, v in replace_files.items() if int(k) in kept} or None,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "authorizationOnly": True,
            "kept": [raw_files[i]["name"] for i in kept],
            "skipped": skipped,
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
