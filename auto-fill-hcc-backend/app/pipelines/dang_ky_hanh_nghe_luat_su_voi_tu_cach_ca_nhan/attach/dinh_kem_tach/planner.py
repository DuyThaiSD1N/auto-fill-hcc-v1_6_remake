"""Đính kèm "Đăng ký hành nghề luật sư với tư cách cá nhân" (1.002153) — chế độ TÁCH giấy tờ theo cài đặt.

Hồ sơ hay dồn nhiều giấy vào một PDF (Đơn + HĐLĐ + lời chứng + CCCD + Thẻ luật sư...). LLM đọc theo TRANG trong MỘT
lượt, chia thành từng giấy (cơ chế chia trang dùng chung với khai sinh 1.001193: tiêu đề từng trang, xác nhận ranh giới
mâu thuẫn, không sót trang); mỗi giấy xếp vào ĐÚNG dòng của bảng chế độ không tách — Thẻ luật sư vào cả dòng 2 và 4,
Chứng chỉ vào cả dòng 1 và 2. Mỗi thành phần = MỘT tệp: mọi đoạn cùng dòng gộp thành một mục — extension cắt đúng trang
theo ``sourceSegments`` rồi ghép một PDF; dòng chỉ gồm tệp nguyên vẹn thì đính nguyên tệp (``sourceFileIndexes``).
Đơn / Danh mục hồ sơ / CCCD không đính (lý do ở cảnh báo, trang nằm trong ``extracted.skipped``). Giấy lạ → thêm thành
phần hồ sơ mới. OCR / LLM lỗi → quay về chế độ không tách.
"""

import time

from app.config import settings
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

from ..dinh_kem_khong_tach.planner import (
    MISSING,
    ROW_TYPES,
    ROWS,
    SKIPPED,
    canonical_type,
    missing_warnings,
    new_item,
    row_item,
    skipped_warnings,
)
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
    titles = _page_titles(pages_by_file, data.get("tep"))
    disputed = _disputed_starts(documents, titles)
    confirmed = await _confirm_starts(pages_by_file, disputed) if disputed else set()
    return _by_page_titles(documents, titles, {(f, p) for f, p, _ in disputed} - confirmed)


def _label(name: str, pages: list[int] | None) -> str:
    if pages is None:
        return name
    return f"{name} (trang {', '.join(str(p + 1) for p in pages)})"


def build_split_items(names: list[str], segments: list[dict]) -> tuple[list[dict], list[str], list[dict]]:
    """Đoạn trang đã phân loại → (mục đính kèm, cảnh báo, đoạn không đính). Tách khỏi I/O để test.

    ``segments``: [{fileIndex, pages (0-based, None = cả tệp), doc: {docType, documentName}}] theo thứ tự tệp, trang.
    """
    parts_of_file: dict[int, int] = {}
    for s in segments:
        parts_of_file[s["fileIndex"]] = parts_of_file.get(s["fileIndex"], 0) + 1

    def whole(segment: dict) -> bool:
        return segment["pages"] is None or parts_of_file[segment["fileIndex"]] == 1

    used_names: set[str] = set()
    attachments: list[dict] = []
    missing_rows: dict[str, list[int]] = {doc_type: [] for doc_type in MISSING}
    for row, types, component, label in ROWS:
        parts: list[dict] = []
        for doc_type in types:
            found = [s for s in segments if canonical_type(s["doc"].get("docType")) == doc_type]
            if not found:
                missing_rows[doc_type].append(row)
            parts.extend(found)
        if not parts:
            continue
        first = parts[0]["fileIndex"]
        item = row_item(row, canonical_type(parts[0]["doc"].get("docType")), component, label, first, names[first],
                        used_names)
        if all(whole(p) for p in parts):
            files = list(dict.fromkeys(p["fileIndex"] for p in parts))
            if len(files) > 1:
                item["sourceFileIndexes"] = files
        else:
            item["sourceSegments"] = [{"fileIndex": p["fileIndex"], "pageIndexes": None if whole(p) else p["pages"]}
                                      for p in parts]
        attachments.append(item)

    skipped: dict[str, list[str]] = {doc_type: [] for doc_type in SKIPPED}
    skipped_parts: list[dict] = []
    extra: list[str] = []
    for s in segments:
        doc_type = canonical_type(s["doc"].get("docType"))
        if doc_type in ROW_TYPES:
            continue
        name = names[s["fileIndex"]]
        pages = None if whole(s) else s["pages"]
        if doc_type in SKIPPED:
            skipped[doc_type].append(_label(name, pages))
            skipped_parts.append({"fileIndex": s["fileIndex"], "pages": pages, "docType": doc_type})
            continue
        item = new_item(s["fileIndex"], name, str(s["doc"].get("documentName") or "").strip(), used_names)
        if pages is not None:
            item["sourceSegments"] = [{"fileIndex": s["fileIndex"], "pageIndexes": pages}]
        attachments.append(item)
        extra.append(_label(name, pages))

    warnings = missing_warnings(missing_rows)
    warnings.extend(skipped_warnings(skipped))
    if extra:
        warnings.append("Giấy tờ ngoài 4 thành phần hồ sơ đã thêm thành phần hồ sơ mới: " + ", ".join(extra) + ".")
    return attachments, warnings, skipped_parts


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
            pages_by_file[index] = _pages(str(result["text"]))

    started = time.monotonic()
    try:
        if not pages_by_file:
            raise RuntimeError("không đọc được chữ của tệp nào")
        documents = await _segment_all(pages_by_file)
    except Exception as exc:  # noqa: BLE001 — chia giấy hỏng thì đính nguyên tệp như chế độ không tách
        result = await plan_without_split(files, options, session)
        result["errors"] = [f"attachment_agent (tách): {exc}", *result.get("errors", [])]
        return result
    llm_ms = int((time.monotonic() - started) * 1000)

    names = [f["name"] for f in raw_files]
    segments = _segments(pages_by_file, documents)
    covered = {s["fileIndex"] for s in segments}
    segments += [{"fileIndex": i, "pages": None, "doc": {}} for i in range(len(names)) if i not in covered]
    segments.sort(key=lambda s: (s["fileIndex"], (s["pages"] or [0])[0]))

    attachments, warnings, skipped = build_split_items(names, segments)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": names,
            "segments": [
                {"fileName": names[s["fileIndex"]], "docType": canonical_type(s["doc"].get("docType")),
                 "documentName": s["doc"].get("documentName") or "",
                 "pages": [p + 1 for p in s["pages"]] if s["pages"] is not None else "cả tệp"}
                for s in segments
            ],
            "skipped": skipped,
            "attachmentMode": "split",
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
