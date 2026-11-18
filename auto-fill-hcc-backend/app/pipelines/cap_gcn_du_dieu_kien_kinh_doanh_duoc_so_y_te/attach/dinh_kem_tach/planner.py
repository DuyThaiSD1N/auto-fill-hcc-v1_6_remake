"""Đính kèm "Cấp GCN đủ điều kiện kinh doanh dược (Sở Y tế)" (1.014076) — chế độ TÁCH giấy tờ theo cài đặt.

Hồ sơ hay dồn mọi giấy vào một PDF (Danh mục + Đơn Mẫu 10 + GCN đăng ký doanh nghiệp + Tài liệu kỹ thuật + Mẫu 11 +
CCHN). LLM đọc theo TRANG trong MỘT lượt, chia thành từng giấy (cơ chế chia trang dùng chung với khai sinh 1.001193:
tiêu đề từng trang, xác nhận ranh giới mâu thuẫn, không sót trang); mỗi giấy vào ĐÚNG dòng của bảng chế độ không tách.
Mỗi dòng = MỘT tệp: mọi đoạn cùng dòng (Danh mục hồ sơ + Tài liệu kỹ thuật ở dòng 2) gộp một mục — extension cắt đúng
trang theo ``sourceSegments`` rồi ghép một PDF; dòng chỉ gồm tệp nguyên vẹn thì đính nguyên tệp (``sourceFileIndexes``).
CCCD / giấy lạ → dòng Đơn, chỉ lấy đúng trang của nó + cảnh báo. OCR / LLM lỗi → quay về chế độ không tách.
"""

import time

from app.config import settings
from app.pipelines._shared.compact_agent.runner import _extract_docx_text, _is_docx
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
    EXTRA_ROW,
    OTHER,
    ROW_OF_TYPE,
    ROWS,
    canonical_type,
    extra_item,
    extra_warning,
    missing_warnings,
    page_type,
    row_item,
    row_label,
    rule_types,
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


def segment_type(segment: dict, pages_by_file: dict[int, list[str]]) -> str:
    """Loại giấy LLM gán; LLM để trống / other thì đọc tiêu đề trang đầu đoạn."""
    doc_type = canonical_type(segment["doc"].get("docType"))
    if doc_type != OTHER:
        return doc_type
    pages = pages_by_file.get(segment["fileIndex"]) or []
    first = (segment["pages"] or [0])[0]
    return (page_type(pages[first]) if first < len(pages) else None) or OTHER


def _label(name: str, pages: list[int] | None) -> str:
    if pages is None:
        return name
    return f"{name} (trang {', '.join(str(p + 1) for p in pages)})"


def build_split_items(
    names: list[str], segments: list[dict], pages_by_file: dict[int, list[str]] | None = None,
) -> tuple[list[dict], list[str]]:
    """Đoạn trang đã phân loại → (mục đính kèm, cảnh báo). Tách khỏi I/O để test.

    ``segments``: [{fileIndex, pages (0-based, None = cả tệp), doc: {docType, documentName}}] theo thứ tự tệp, trang.
    """
    pages_by_file = pages_by_file or {}
    parts_of_file: dict[int, int] = {}
    for s in segments:
        parts_of_file[s["fileIndex"]] = parts_of_file.get(s["fileIndex"], 0) + 1

    def whole(segment: dict) -> bool:
        return segment["pages"] is None or parts_of_file[segment["fileIndex"]] == 1

    typed = [(s, segment_type(s, pages_by_file)) for s in segments]
    used_names: set[str] = set()
    attachments: list[dict] = []
    for row in ROWS:
        parts = [s for s, doc_type in typed if doc_type in row[1]]
        if not parts:
            continue
        types = {doc_type for _, doc_type in typed if doc_type in row[1]}
        doc_type = next(t for t in row[1][::-1] if t in types)
        first = parts[0]["fileIndex"]
        item = row_item(row, row_label(row, types), doc_type, first, names[first], used_names)
        if all(whole(p) for p in parts):
            files = list(dict.fromkeys(p["fileIndex"] for p in parts))
            if len(files) > 1:
                item["sourceFileIndexes"] = files
        else:
            item["sourceSegments"] = [{"fileIndex": p["fileIndex"], "pageIndexes": None if whole(p) else p["pages"]}
                                      for p in parts]
        attachments.append(item)

    extras: list[str] = []
    for s, doc_type in typed:
        if doc_type in ROW_OF_TYPE:
            continue
        name = names[s["fileIndex"]]
        pages = None if whole(s) else s["pages"]
        base = str(s["doc"].get("documentName") or "").strip()
        item = extra_item(doc_type, s["fileIndex"], name, base, used_names)
        if pages is not None:
            item["sourceSegments"] = [{"fileIndex": s["fileIndex"], "pageIndexes": pages}]
        attachments.append(item)
        extras.append(_label(name, pages))

    found_rows = {item["componentIndex"] for item in attachments if item["detectedType"] in ROW_OF_TYPE}
    all_text = " ".join(" ".join(pages) for pages in pages_by_file.values())
    warnings = missing_warnings(found_rows, all_text) + extra_warning(extras)
    return attachments, warnings


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
    for i in range(len(names)):
        if i in covered:
            continue
        # Tệp không OCR (Word) → loại theo tiêu đề trong chữ trích từ tệp; còn lại để giấy chưa rõ loại.
        text = str(_extract_docx_text(raw_files[i]).get("text") or "") if _is_docx(raw_files[i]) else ""
        found = [t for t in rule_types(text) if t in ROW_OF_TYPE]
        segments.append({"fileIndex": i, "pages": None, "doc": {"docType": found[0] if found else OTHER}})
    segments.sort(key=lambda s: (s["fileIndex"], (s["pages"] or [0])[0]))

    attachments, warnings = build_split_items(names, segments, pages_by_file)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": names,
            "segments": [
                {"fileName": names[s["fileIndex"]], "docType": segment_type(s, pages_by_file),
                 "documentName": s["doc"].get("documentName") or "",
                 "pages": [p + 1 for p in s["pages"]] if s["pages"] is not None else "cả tệp"}
                for s in segments
            ],
            "extraRow": EXTRA_ROW[0],
            "attachmentMode": "split",
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
