"""Đính kèm đăng ký khai sinh (Cổng DVC quốc gia mới) — chế độ TÁCH giấy tờ theo cài đặt của extension.

Một tệp hay gộp nhiều giấy (tờ khai + CCCD + giấy khai sinh...). LLM đọc cả hồ sơ theo TRANG trong MỘT lượt và
chia thành từng giấy; mỗi giấy thành một mục đính kèm có `sourceSegments` (extension cắt đúng các trang) đặt vào
ĐÚNG dòng có sẵn của bảng thành phần — form mới không có nút thêm dòng, nên giấy không thuộc dòng riêng nào vào
dòng giấy chứng sinh. Không sót trang: trang LLM không nhắc tới gộp vào giấy liền trước của cùng tệp (không có thì
thành mục riêng ở dòng giấy chứng sinh); chỉ trang LLM nói là trang trắng mới bỏ. Tệp gọn một giấy → đính nguyên
tệp (giữ định dạng gốc). OCR/LLM lỗi → quay về chế độ không tách. Tệp trên 2 MB vẫn nén như chế độ không tách;
extension cắt trang từ bản nén (giữ nguyên số trang).
"""

import asyncio
import re
import time

from app.config import settings
from app.pipelines.cai_chinh_dvc_moi.attach.dinh_kem_khong_tach.planner import shrink_oversized
from app.process.schemas import FileItem
from app.services.llm import client

from ..dinh_kem_khong_tach.planner import ROW_CHUNG_SINH, ROWS, _document_name, _llm_document_name
from ..dinh_kem_khong_tach.planner import both_sides, pair_card_sides
from ..dinh_kem_khong_tach.planner import plan as plan_without_split
from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_PAGE_RE = re.compile(r"(?m)^\W*Trang\s+(\d+)\s*/\s*(\d+)\W*$")
_BLANK = "blank_page"
DEFAULT_ROW = ROW_CHUNG_SINH
ROW_BY_TYPE = ROWS


def _pages(text: str) -> list[str]:
    """Text OCR → danh sách text từng trang theo mốc "Trang i/N"; không có mốc (ảnh) → một trang."""
    marks = list(_PAGE_RE.finditer(text))
    if not marks:
        return [text.strip()]
    return [text[m.end():(marks[k + 1].start() if k + 1 < len(marks) else len(text))].strip()
            for k, m in enumerate(marks)]


def _max_tokens(pages_by_file: dict[int, list[str]]) -> int:
    """Trần token theo tổng số trang của hồ sơ, đúng công thức planner form cũ."""
    return max(1200, min(4000, sum(len(p) for p in pages_by_file.values()) * 180))


async def _segment_all(pages_by_file: dict[int, list[str]]) -> list[dict]:
    payload = [{"fileIndex": i, "pages": [{"page": n + 1, "text": t[:2500]} for n, t in enumerate(pages)]}
               for i, pages in pages_by_file.items()]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(payload)},
    ]
    raw = await client.chat(messages, max_tokens=_max_tokens(pages_by_file), enable_thinking=settings.agent_reasoning)
    documents = client.extract_json_block(raw).get("documents", []) or []
    return [d for d in documents if isinstance(d, dict)]


def _segments(pages_by_file: dict[int, list[str]], documents: list[dict]) -> list[dict]:
    """Giấy LLM chia → đoạn trang (0-based) theo tệp; trang không ai nhận gộp vào giấy liền trước, không sót trang."""
    taken: dict[int, set[int]] = {i: set() for i in pages_by_file}
    segments: list[dict] = []
    for doc in documents:
        try:
            file_index = int(doc.get("fileIndex"))
        except (TypeError, ValueError):
            continue
        if file_index not in pages_by_file:
            continue
        count = len(pages_by_file[file_index])
        pages = []
        for page in doc.get("pages") or []:
            try:
                index = int(page) - 1
            except (TypeError, ValueError):
                continue
            if 0 <= index < count and index not in taken[file_index] and index not in pages:
                pages.append(index)
        if not pages:
            continue
        taken[file_index].update(pages)
        if str(doc.get("docType") or "").strip() == _BLANK:
            continue
        segments.append({"fileIndex": file_index, "pages": sorted(pages), "doc": doc})
    for file_index, pages in pages_by_file.items():
        for index in range(len(pages)):
            if index in taken[file_index]:
                continue
            before = [s for s in segments if s["fileIndex"] == file_index and min(s["pages"]) < index]
            if before:
                max(before, key=lambda s: max(s["pages"]))["pages"].append(index)
            else:
                segments.append({"fileIndex": file_index, "pages": [index], "doc": {}})
    for segment in segments:
        segment["pages"].sort()
    return sorted(segments, key=lambda s: (s["fileIndex"], s["pages"][0]))


def _item(file_index: int, file_name: str, document_name: str, doc_type: str, sources: list[dict] | None) -> dict:
    row = ROW_BY_TYPE.get(doc_type, DEFAULT_ROW)
    item = {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": row["slotName"],
        "target": "fixed-slot",
        "needsAddComponent": False,
        "detectedType": doc_type if doc_type in ROW_BY_TYPE else "other",
        "noChooserClick": True,
        **row,
    }
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

    attachments: list[dict] = []
    seen: dict[str, int] = {}
    # Hai mặt thẻ của CÙNG một người (dù khác trang, khác tệp) luôn gộp thành MỘT giấy.
    for group in pair_card_sides([s["doc"] for s in segments]):
        parts = [segments[i] for i in group]
        doc = both_sides(parts[0]["doc"]) if len(parts) > 1 else parts[0]["doc"]
        file_index = parts[0]["fileIndex"]
        name = names[file_index]
        document_name = _document_name(name, _llm_document_name(doc) if doc else "")
        # Hai giấy cùng tên (CCCD hai người...) → đánh số để cổng và cán bộ phân biệt được.
        seen[document_name.lower()] = seen.get(document_name.lower(), 0) + 1
        if seen[document_name.lower()] > 1:
            document_name = f"{document_name} {seen[document_name.lower()]}"
        # Nhóm phủ đúng mọi phần của MỘT tệp (vd tệp CCCD 2 trang = 2 mặt) → đính nguyên tệp, không dựng lại PDF.
        whole = {p["fileIndex"] for p in parts} == {file_index} and parts_of_file[file_index] == len(parts)
        sources = None if whole else [{"fileIndex": p["fileIndex"], "pageIndexes": p["pages"]} for p in parts]
        attachments.append(_item(file_index, name, document_name, str(doc.get("docType") or "").strip(), sources))

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
