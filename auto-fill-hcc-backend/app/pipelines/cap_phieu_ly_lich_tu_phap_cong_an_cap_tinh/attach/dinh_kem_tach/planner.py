"""Đính kèm cấp Phiếu lý lịch tư pháp (3.000333) — chế độ TÁCH giấy tờ theo cài đặt của extension.

Hồ sơ hay dồn tờ khai + căn cước + biên lai (+ giấy miễn giảm phí) vào một PDF. LLM đọc cả hồ sơ theo TRANG trong MỘT
lượt và chia thành từng giấy (khung chia trang dùng chung với khai sinh Cổng DVC quốc gia mới: tiêu đề từng trang, xác
nhận ranh giới mâu thuẫn, không sót trang). Mỗi giấy một mục trên dòng duy nhất của bảng, đúng các trang của nó
(``sourceSegments``); giấy phủ trọn một tệp thì đính nguyên tệp; hai mặt thẻ căn cước của cùng một người (dù khác trang,
khác tệp) gộp một giấy; giấy chứng minh miễn/giảm phí đứng đầu. OCR / LLM lỗi → quay về chế độ không tách.
"""

import asyncio
import time

from app.config import settings
from app.pipelines.cai_chinh_dvc_moi.attach.dinh_kem_khong_tach.planner import shrink_merged, shrink_oversized
from app.pipelines.khai_sinh_dvc_moi.attach.dinh_kem_khong_tach.planner import (
    _document_name,
    _llm_document_name,
    both_sides,
    pair_card_sides,
)
from app.pipelines.khai_sinh_dvc_moi.attach.dinh_kem_tach.planner import (
    _OCR_TYPES,
    _by_page_titles,
    _confirm_starts,
    _disputed_starts,
    _max_tokens,
    _page_titles,
    _pages,
    _segments,
)
from app.process.schemas import FileItem
from app.services.llm import client

from ..dinh_kem_khong_tach.planner import card_meta, exemption_first, item, unique_name
from ..dinh_kem_khong_tach.planner import plan as plan_without_split
from .prompt import SYSTEM_PROMPT, build_user_prompt


async def _segment_all(pages_by_file: dict[int, list[str]]) -> list[dict]:
    payload = [{"fileIndex": i, "pages": [{"page": n + 1, "text": t[:2500]} for n, t in enumerate(pages)]}
               for i, pages in pages_by_file.items()]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(payload)},
    ]
    data: dict = {}
    for attempt in range(2):  # JSON hỏng / rỗng → hỏi lại một lần
        raw = await client.chat(messages, max_tokens=_max_tokens(pages_by_file),
                                enable_thinking=settings.agent_reasoning)
        try:
            data = client.extract_json_block(raw)
        except Exception:  # noqa: BLE001
            if attempt:
                raise
            continue
        if any(isinstance(d, dict) and d.get("pages") for d in data.get("documents") or []):
            break
    documents = [d for d in data.get("documents") or [] if isinstance(d, dict)]
    if not documents:
        raise RuntimeError("LLM không chia được giấy tờ")
    titles = _page_titles(pages_by_file, data.get("tep"))
    disputed = _disputed_starts(documents, titles)
    confirmed = await _confirm_starts(pages_by_file, disputed) if disputed else set()
    return _by_page_titles(documents, titles, {(f, p) for f, p, _ in disputed} - confirmed)


def build_split_items(names: list[str], segments: list[dict]) -> list[dict]:
    """Đoạn giấy → mục trên dòng duy nhất. Nhóm phủ trọn MỘT tệp → đính nguyên tệp, không dựng lại PDF."""
    parts_of_file: dict[int, int] = {}
    for s in segments:
        parts_of_file[s["fileIndex"]] = parts_of_file.get(s["fileIndex"], 0) + 1
    items: list[dict] = []
    seen: dict[str, int] = {}
    for group in pair_card_sides([s["doc"] for s in segments]):
        parts = [segments[i] for i in group]
        doc = both_sides(parts[0]["doc"]) if len(parts) > 1 else parts[0]["doc"]
        file_index = parts[0]["fileIndex"]
        name = names[file_index]
        document_name = unique_name(_document_name(name, _llm_document_name(doc) if doc else ""), seen)
        whole = {p["fileIndex"] for p in parts} == {file_index} and parts_of_file[file_index] == len(parts)
        sources = None if whole else [{"fileIndex": p["fileIndex"], "pageIndexes": p["pages"]} for p in parts]
        items.append(item(file_index, name, document_name, str(doc.get("docType") or "").strip(), sources))
    return exemption_first(items)


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    from app.services import ocr

    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    errors: list[str] = []
    pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]
    started = time.monotonic()
    shrink_task = asyncio.create_task(shrink_oversized(raw_files, errors))
    ocr_results = await ocr.ocr_per_file([f for _, f in pairs]) if pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    pages_by_file: dict[int, list[str]] = {}
    for (index, file), result in zip(pairs, ocr_results):
        if result.get("error"):
            errors.append(f"OCR {file.get('name')}: {result['error']}")
        if str(result.get("text") or "").strip():
            pages_by_file[index] = _pages(str(result["text"]))

    started = time.monotonic()
    try:
        if not pages_by_file:
            raise RuntimeError("OCR không đọc được tệp nào")
        documents = await _segment_all(pages_by_file)
    except Exception as exc:  # noqa: BLE001 — chia giấy hỏng thì đính nguyên tệp như chế độ không tách
        shrink_task.cancel()
        result = await plan_without_split(files, options, session)
        result["errors"] = [f"attachment_agent (tách): {exc}", *result.get("errors", [])]
        return result
    llm_ms = int((time.monotonic() - started) * 1000)

    replace_files = await shrink_task
    names = [replace_files[str(i)]["name"] if str(i) in replace_files else f["name"] for i, f in enumerate(raw_files)]
    segments = _segments(pages_by_file, documents)
    covered = {s["fileIndex"] for s in segments}
    segments += [{"fileIndex": i, "pages": None, "doc": {}} for i in range(len(names)) if i not in covered]
    segments.sort(key=lambda s: (s["fileIndex"], (s["pages"] or [0])[0]))

    # Mặt thẻ / số định danh đọc từ OCR của từng đoạn: khoá ghép hai mặt thẻ (kể cả đoạn LLM bỏ sót).
    for s in segments:
        pages = pages_by_file.get(s["fileIndex"], [])
        text = "\n".join(pages if s["pages"] is None else [pages[i] for i in s["pages"] if i < len(pages)])
        s["doc"] = card_meta(s["doc"], text)
    attachments = build_split_items(names, segments)
    await shrink_merged(raw_files, attachments, replace_files, errors)
    return {
        "attachments": attachments,
        "replaceFiles": replace_files or None,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "segments": [
                {"fileName": names[s["fileIndex"]], "docType": str(s["doc"].get("docType") or ""),
                 "documentName": str(s["doc"].get("documentName") or ""),
                 "pages": [p + 1 for p in s["pages"]] if s["pages"] is not None else "cả tệp"}
                for s in segments
            ],
            "attachmentMode": "split",
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
