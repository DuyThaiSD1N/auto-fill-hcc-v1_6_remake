"""Đính kèm Cấp thẻ tạm trú cho người nước ngoài (1.003460) — chế độ TÁCH giấy tờ theo cài đặt của extension.

Hồ sơ hay dồn bìa + văn bản NA6 + tờ khai NA8 + hộ chiếu + giấy phép lao động vào một PDF. LLM đọc theo TRANG trong MỘT
lượt, chia thành từng giấy; mỗi giấy xếp vào ĐÚNG dòng của bảng chế độ không tách (``build_items`` dùng chung): giấy
chứng minh → dòng 1, bìa + tờ khai → dòng 2, văn bản đề nghị → dòng 3, hộ chiếu (+ căn cước, giấy khác) → "Giấy tờ
khác". Cơ chế chia trang dùng chung với khai sinh Cổng DVC quốc gia mới; mốc trang OCR + vá JSON theo Điều chỉnh thông tin
cư trú — như thị thực 1.001194. OCR / LLM lỗi → quay về chế độ không tách.
"""

import time

from app.config import settings
from app.pipelines.dieu_chinh_thong_tin_ve_cu_tru.attach.dinh_kem_khong_tach.planner import ocr_pages
from app.pipelines.dieu_chinh_thong_tin_ve_cu_tru.attach.dinh_kem_tach.planner import _mark_document_starts, _parse
from app.pipelines.khai_sinh_dvc_moi.attach.dinh_kem_tach.planner import (
    _OCR_TYPES,
    _by_page_titles,
    _confirm_starts,
    _disputed_starts,
    _max_tokens,
    _page_titles,
    _segments,
)
from app.process.schemas import FileItem
from app.services.llm import client

from ..dinh_kem_khong_tach.planner import OTHER, build_items, canonical_type, rule_doc_type
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
            data = _parse(raw)
        except Exception:  # noqa: BLE001
            if attempt:
                raise
            continue
        if any(isinstance(d, dict) and d.get("pages") for d in data.get("documents") or []):
            break
    documents = [d for d in data.get("documents") or [] if isinstance(d, dict)]
    titles = _page_titles(pages_by_file, data.get("tep"))
    _mark_document_starts(titles, documents)
    disputed = _disputed_starts(documents, titles)
    confirmed = await _confirm_starts(pages_by_file, disputed) if disputed else set()
    return _by_page_titles(documents, titles, {(f, p) for f, p, _ in disputed} - confirmed)


def segment_entries(pages_by_file: dict[int, list[str]], segments: list[dict]) -> list[dict]:
    """Đoạn trang → đầu vào ``build_items``. LLM trả other cho đoạn thì xét luật tiêu đề trên chữ của đoạn đó."""
    entries = []
    for s in segments:
        pages = pages_by_file.get(s["fileIndex"], [])
        text = "\n".join(pages if s["pages"] is None else [pages[i] for i in s["pages"] if i < len(pages)])
        doc_type = canonical_type(s["doc"].get("docType"))
        if doc_type == OTHER:
            doc_type = rule_doc_type(text) or OTHER
        entries.append({"fileIndex": s["fileIndex"], "pages": s["pages"], "docType": doc_type,
                        "documentName": str(s["doc"].get("documentName") or "").strip(), "text": text})
    return entries


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    from app.services import ocr

    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    errors: list[str] = []
    pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]
    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file([f for _, f in pairs]) if pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    pages_by_file: dict[int, list[str]] = {}
    for (index, file), result in zip(pairs, ocr_results):
        if result.get("error"):
            errors.append(f"OCR {file.get('name')}: {result['error']}")
        if str(result.get("text") or "").strip():
            pages_by_file[index] = ocr_pages(str(result["text"]))

    started = time.monotonic()
    try:
        if not pages_by_file:
            raise RuntimeError("OCR không đọc được tệp nào")
        documents = await _segment_all(pages_by_file)
    except Exception as exc:  # noqa: BLE001 — chia giấy hỏng thì đính nguyên tệp như chế độ không tách
        result = await plan_without_split(files, options, session)
        result["errors"] = [f"attachment_agent (tách): {exc}", *result.get("errors", [])]
        return result
    llm_ms = int((time.monotonic() - started) * 1000)

    names = [str(f.get("name") or f"file-{i + 1}") for i, f in enumerate(raw_files)]
    segments = _segments(pages_by_file, documents)
    covered = {s["fileIndex"] for s in segments}
    segments += [{"fileIndex": i, "pages": None, "doc": {}} for i in range(len(names)) if i not in covered]
    segments.sort(key=lambda s: (s["fileIndex"], (s["pages"] or [0])[0]))

    entries = segment_entries(pages_by_file, segments)
    attachments, warnings = build_items(names, entries)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": names,
            "segments": [
                {"fileName": names[e["fileIndex"]], "docType": e["docType"], "documentName": e["documentName"],
                 "pages": [p + 1 for p in e["pages"]] if e["pages"] is not None else "cả tệp"}
                for e in entries
            ],
            "attachmentMode": "split",
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
