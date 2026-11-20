"""Đính kèm Điều chỉnh thông tin về cư trú — chế độ TÁCH giấy tờ theo cài đặt của extension.

Hồ sơ hay dồn cả bộ vào một PDF (bìa + tờ khai CT01 + văn bản thống nhất + trích lục khai tử + CCCD). LLM đọc theo
TRANG trong MỘT lượt, chia thành từng giấy; mỗi giấy thành một mục có `sourceSegments` (extension cắt đúng trang)
đặt vào đúng dòng của bảng 3 dòng (bảng ở chế độ không tách). Cơ chế chia trang (tiêu đề từng trang, xác nhận ranh
giới mâu thuẫn, không sót trang, ghép hai mặt CCCD) dùng chung với khai sinh Cổng DVC quốc gia mới; chỉ prompt và
bảng dòng là riêng. Giấy không có dòng riêng (CCCD, bìa / danh mục hồ sơ) → dòng giấy tờ chứng minh + cảnh báo.
OCR / LLM lỗi → quay về chế độ không tách.
"""

import re
import time

from app.config import settings
from app.pipelines._shared.identity_merge import ho_ten_co_dau, mat_the, so_dinh_danh_the
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
    _file_index,
    _max_tokens,
    _page_titles,
    _segments,
)
from app.process.schemas import FileItem
from app.services.llm import client

from ..dinh_kem_khong_tach.planner import LEFTOVER_ROW, ROWS, finalize_rows, ocr_pages, plan_item
from ..dinh_kem_khong_tach.planner import plan as plan_without_split
from .prompt import SYSTEM_PROMPT, build_user_prompt


# Model hay quên dấu "}" đóng mục "tep" ('…"Thẻ căn cước"]],"documents"…' thay vì ']}],'): chạy thật 16/11/2026, 2/4
# lượt hỏng y hệt, hỏi lại không đỡ → JSON hỏng thì vá đúng chỗ này rồi đọc lại.
_TEP_MISSING_BRACE = re.compile(r'("tieuDeTrang"\s*:\s*\[[^\[\]]*\])\s*\]')


def _parse(raw: str) -> dict:
    try:
        return client.extract_json_block(raw)
    except Exception:  # noqa: BLE001
        fixed = _TEP_MISSING_BRACE.sub(r"\1}]", raw)
        if fixed == raw:
            raise
        return client.extract_json_block(fixed)


def _mark_document_starts(titles: dict[int, list[str]], documents: list[dict]) -> None:
    """Trang đầu mỗi giấy trong "documents" cũng là trang mở giấy, kể cả khi "tep" để tiêu đề rỗng.

    `_by_page_titles` chỉ tách theo tiêu đề; chạy thật 16/11/2026 model để tiêu đề trang văn bản thống nhất rỗng
    (cùng lúc "documents" tách đúng) → văn bản thống nhất bị dồn vào tờ khai, mất dòng "ý kiến đồng ý"."""
    for doc in documents:
        page_titles = titles.get(_file_index(doc))
        pages = [int(p) for p in doc.get("pages") or [] if str(p).isdigit()]
        if not page_titles or not pages or str(doc.get("docType") or "").strip() == _BLANK:
            continue
        first = min(pages)
        if 1 <= first <= len(page_titles) and not page_titles[first - 1]:
            page_titles[first - 1] = str(doc.get("documentName") or doc.get("docType") or "giấy").strip()


async def _segment_all(pages_by_file: dict[int, list[str]], system_prompt: str = SYSTEM_PROMPT,
                       user_prompt=build_user_prompt) -> list[dict]:
    """Chia trang một lượt. Tách hộ (cùng trang cổng) dùng lại hàm này với prompt riêng của mình."""
    payload = [{"fileIndex": i, "pages": [{"page": n + 1, "text": t[:2500]} for n, t in enumerate(pages)]}
               for i, pages in pages_by_file.items()]
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt(payload)},
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
    parts_of_file = {i: sum(1 for s in segments if s["fileIndex"] == i) for i in range(len(names))}

    # Số định danh đọc từ OCR của từng đoạn: khoá ghép hai mặt thẻ (họ tên LLM đọc có thể lệch giữa hai mặt).
    for s in segments:
        pages = pages_by_file.get(s["fileIndex"], [])
        text = "\n".join(pages if s["pages"] is None else [pages[i] for i in s["pages"] if i < len(pages)])
        s["doc"] = {**s["doc"], "_soThe": so_dinh_danh_the(text), "_matTheOcr": mat_the(text),
                    "chuThe": ho_ten_co_dau(s["doc"].get("chuThe") or "", text)}

    attachments: list[dict] = []
    leftovers: list[str] = []
    seen: dict[str, int] = {}
    # Hai mặt thẻ của CÙNG một người (dù khác trang, khác tệp) luôn gộp thành MỘT giấy.
    for group in pair_card_sides([s["doc"] for s in segments]):
        parts = [segments[i] for i in group]
        doc = both_sides(parts[0]["doc"]) if len(parts) > 1 else parts[0]["doc"]
        file_index = parts[0]["fileIndex"]
        name = names[file_index]
        doc_type = str(doc.get("docType") or "").strip()
        if doc_type == _BLANK:
            doc_type = ""
        document_name = _document_name(name, _llm_document_name(doc) if doc else "")
        # Hai giấy cùng tên → đánh số để cổng và cán bộ phân biệt được.
        seen[document_name.lower()] = seen.get(document_name.lower(), 0) + 1
        if seen[document_name.lower()] > 1:
            document_name = f"{document_name} {seen[document_name.lower()]}"
        row_type = doc_type if doc_type in ROWS else LEFTOVER_ROW
        if doc_type not in ROWS:
            leftovers.append(document_name)
        item = plan_item(file_index, name, document_name, row_type, doc_type or "other")
        # Nhóm phủ đúng mọi phần của MỘT tệp → đính nguyên tệp, không dựng lại PDF.
        whole = {p["fileIndex"] for p in parts} == {file_index} and parts_of_file[file_index] == len(parts)
        if not whole:
            item["sourceSegments"] = [{"fileIndex": p["fileIndex"], "pageIndexes": p["pages"]} for p in parts]
        attachments.append(item)

    finalize_rows(attachments)
    if leftovers:
        errors.append(f"Giấy tờ không có dòng riêng hoặc chưa rõ loại đã đính vào dòng "
                      f"\"{ROWS[LEFTOVER_ROW]['componentName']}\": " + ", ".join(leftovers))
    return {
        "attachments": attachments,
        "extracted": {
            "documents": names,
            "segments": [
                {"fileName": item["fileName"], "documentName": item["documentName"], "row": item["detectedType"],
                 "pages": [[s["fileIndex"], [p + 1 for p in s["pageIndexes"] or []] or "cả tệp"]
                           for s in item.get("sourceSegments") or []] or "cả tệp"}
                for item in attachments
            ],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
