"""Đính kèm khai sinh có yếu tố nước ngoài — chế độ TÁCH giấy tờ theo cài đặt của extension.

Hồ sơ hay dồn cả bộ vào một PDF (tờ khai + giấy chứng sinh + thỏa thuận quốc tịch + giấy kết hôn + hộ chiếu + bản
dịch + kết quả ADN). LLM đọc theo TRANG trong MỘT lượt, chia thành từng giấy; mỗi giấy thành một mục có
`sourceSegments` (extension cắt đúng trang) đặt vào ĐÚNG dòng có sẵn theo bảng của chế độ không tách. Cơ chế chia
trang (tiêu đề từng trang, xác nhận ranh giới mâu thuẫn, không sót trang, ghép hai mặt CCCD) dùng chung với khai sinh
1.001193; chỉ prompt và bảng dòng là riêng. OCR / LLM lỗi → quay về chế độ không tách.
"""

import asyncio
import time

from app.config import settings
from app.pipelines._shared.identity_merge import ho_ten_co_dau, mat_the, so_dinh_danh_the
from app.pipelines.cai_chinh_dvc_moi.attach.dinh_kem_khong_tach.planner import shrink_merged, shrink_oversized
from app.pipelines.khai_sinh_dvc_moi.attach.dinh_kem_khong_tach.planner import (
    _document_name,
    _llm_document_name,
    both_sides,
    pair_card_sides,
)
from app.pipelines.khai_sinh_dvc_moi.attach.dinh_kem_tach.planner import (
    _BLANK,
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

from ..dinh_kem_khong_tach.planner import plan as plan_without_split
from ..dinh_kem_khong_tach.planner import plan_item
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
    titles = _page_titles(pages_by_file, data.get("tep"))
    disputed = _disputed_starts(documents, titles)
    confirmed = await _confirm_starts(pages_by_file, disputed) if disputed else set()
    return _by_page_titles(documents, titles, {(f, p) for f, p, _ in disputed} - confirmed)


def _item(file_index: int, file_name: str, document_name: str, doc_type: str, sources: list[dict] | None) -> dict:
    item = plan_item(file_index, file_name, document_name, doc_type if doc_type != _BLANK else "")
    if sources is not None:
        item["sourceSegments"] = sources
    return item


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
        documents = await _segment_all(pages_by_file) if pages_by_file else []
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
    parts_of_file = {i: sum(1 for s in segments if s["fileIndex"] == i) for i in range(len(names))}

    # Số định danh đọc từ OCR của từng đoạn: khoá ghép hai mặt thẻ (họ tên LLM đọc có thể lệch giữa hai mặt).
    for s in segments:
        pages = pages_by_file.get(s["fileIndex"], [])
        text = "\n".join(pages if s["pages"] is None else [pages[i] for i in s["pages"] if i < len(pages)])
        s["doc"] = {**s["doc"], "_soThe": so_dinh_danh_the(text), "_matTheOcr": mat_the(text),
                    "chuThe": ho_ten_co_dau(s["doc"].get("chuThe") or "", text)}

    attachments: list[dict] = []
    seen: dict[str, int] = {}
    # Hai mặt thẻ của CÙNG một người (dù khác trang, khác tệp) luôn gộp thành MỘT giấy.
    for group in pair_card_sides([s["doc"] for s in segments]):
        parts = [segments[i] for i in group]
        doc = both_sides(parts[0]["doc"]) if len(parts) > 1 else parts[0]["doc"]
        file_index = parts[0]["fileIndex"]
        name = names[file_index]
        document_name = _document_name(name, _llm_document_name(doc) if doc else "")
        # Hai giấy cùng tên (hai bản dịch, CCCD hai người...) → đánh số để cổng và cán bộ phân biệt được.
        seen[document_name.lower()] = seen.get(document_name.lower(), 0) + 1
        if seen[document_name.lower()] > 1:
            document_name = f"{document_name} {seen[document_name.lower()]}"
        # Nhóm phủ đúng mọi phần của MỘT tệp → đính nguyên tệp, không dựng lại PDF.
        whole = {p["fileIndex"] for p in parts} == {file_index} and parts_of_file[file_index] == len(parts)
        sources = None if whole else [{"fileIndex": p["fileIndex"], "pageIndexes": p["pages"]} for p in parts]
        attachments.append(_item(file_index, name, document_name, str(doc.get("docType") or "").strip(), sources))

    await shrink_merged(raw_files, attachments, replace_files, errors)
    return {
        "attachments": attachments,
        "replaceFiles": replace_files or None,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "segments": [
                {"fileName": item["fileName"], "documentName": item["documentName"], "slotIndex": item["slotIndex"],
                 "pages": [[s["fileIndex"], [p + 1 for p in s["pageIndexes"] or []] or "cả tệp"]
                           for s in item.get("sourceSegments") or []] or "cả tệp"}
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
