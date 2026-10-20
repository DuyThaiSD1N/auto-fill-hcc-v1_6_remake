"""Đính kèm đăng ký lại kết hôn — chế độ TÁCH giấy tờ theo cài đặt của extension.

Một tệp hay gộp nhiều giấy (bản cam đoan + giấy khai sinh + CCCD hai bên...). LLM đọc cả hồ sơ theo TRANG trong MỘT
lượt, chia thành từng giấy và phân loại; mỗi giấy coi như một tệp riêng rồi xếp dòng bằng ĐÚNG luật của chế độ không
tách (`build_plan_items`: STT2 nhận một giấy — GCN kết hôn cũ, không có thì giấy tờ liên quan, rồi mới tới bản cam
đoan; CCCD đặt tên theo bên nam / bên nữ, gộp hai mặt cùng người; còn lại thêm dòng mới). Kết quả trỏ về tệp gốc kèm
`sourceSegments` để extension cắt đúng trang; giấy chiếm trọn một tệp thì đính nguyên tệp. Không sót trang: trang LLM
không nhắc tới gộp vào giấy liền trước của cùng tệp; chỉ trang LLM nói là trang trắng mới bỏ. OCR / LLM lỗi → quay
về chế độ không tách.
"""

import re
import time
from pathlib import Path

from app.config import settings
from app.pipelines.ket_hon_lai.attach.planner import _ALLOWED_DOC_TYPES, build_plan_items, plan_without_split
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_PAGE_RE = re.compile(r"(?m)^\W*Trang\s+(\d+)\s*/\s*(\d+)\W*$")
_BLANK = "blank_page"


def _pages(text: str) -> list[str]:
    """Text OCR → text từng trang theo mốc "Trang i/N"; không có mốc (ảnh) → một trang."""
    marks = list(_PAGE_RE.finditer(text))
    if not marks:
        return [text.strip()]
    return [text[m.end():(marks[k + 1].start() if k + 1 < len(marks) else len(text))].strip()
            for k, m in enumerate(marks)]


async def _segment_all(pages_by_file: dict[int, list[str]]) -> list[dict]:
    payload = [{"fileIndex": i, "pages": [{"page": n + 1, "text": t[:2500]} for n, t in enumerate(pages)]}
               for i, pages in pages_by_file.items()]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(payload)},
    ]
    max_tokens = max(1200, min(4000, sum(len(p) for p in pages_by_file.values()) * 180))
    raw = await client.chat(messages, max_tokens=max_tokens, enable_thinking=settings.agent_reasoning)
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


def _parts(raw_files: list[dict], pages_by_file: dict[int, list[str]], documents: list[dict]) -> list[dict]:
    """Mỗi giấy → một "tệp ảo" (text + trang cần cắt). Tệp không có OCR giữ nguyên làm một phần."""
    parts = _segments(pages_by_file, documents)
    covered = {p["fileIndex"] for p in parts}
    parts += [{"fileIndex": i, "pages": None, "doc": {}} for i in range(len(raw_files)) if i not in covered]
    parts.sort(key=lambda p: (p["fileIndex"], (p["pages"] or [0])[0]))
    for part in parts:
        pages = pages_by_file.get(part["fileIndex"]) or []
        name = str(raw_files[part["fileIndex"]].get("name") or f"file-{part['fileIndex'] + 1}")
        if part["pages"] is None or len(part["pages"]) == len(pages):
            part.update(text="\n".join(pages), pageIndexes=None, name=name)
            continue
        first, last = part["pages"][0] + 1, part["pages"][-1] + 1
        path = Path(name)
        # Tên tệp ảo phải khác nhau (build_plan_items tra OCR theo tên) và vẫn đọc được khi phải làm tên giấy.
        part.update(text="\n".join(pages[i] for i in part["pages"]), pageIndexes=part["pages"],
                    name=f"{path.stem} trang {first}-{last}{path.suffix}")
    return parts


def _to_sources(attachments: list[dict], parts: list[dict], raw_files: list[dict]) -> list[dict]:
    """Mục đính kèm của tệp ảo → tệp gốc: giấy cắt trang mang `sourceSegments`; nhiều tệp nguyên (hai mặt CCCD ở
    hai tệp) giữ `sourceFileIndexes` như chế độ không tách."""
    out: list[dict] = []
    for item in attachments:
        sources = [{"fileIndex": parts[v]["fileIndex"], "pageIndexes": parts[v]["pageIndexes"]}
                   for v in item.get("sourceFileIndexes") or [item["fileIndex"]]]
        first = sources[0]["fileIndex"]
        mapped = {k: v for k, v in item.items() if k != "sourceFileIndexes"}
        mapped.update(fileIndex=first, fileName=str(raw_files[first].get("name") or f"file-{first + 1}"))
        if any(s["pageIndexes"] is not None for s in sources):
            mapped["sourceSegments"] = sources
        elif len(sources) > 1:
            mapped["sourceFileIndexes"] = [s["fileIndex"] for s in sources]
        out.append(mapped)
    return out


def _llm_info(doc: dict) -> dict[str, str]:
    """Kết quả chia giấy → cùng dạng phân loại của chế độ không tách (type / side / face / documentName)."""
    doc_type = re.sub(r"[\s-]+", "_", str(doc.get("docType") or "").strip().lower())
    return {
        "type": doc_type if doc_type in _ALLOWED_DOC_TYPES else "other",
        "side": re.sub(r"[\s-]+", "_", str(doc.get("side") or "").strip().lower()),
        "face": re.sub(r"[\s-]+", "_", str(doc.get("face") or "").strip().lower()),
        "documentName": str(doc.get("documentName") or "").strip(),
    }


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
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
    if not pages_by_file:
        return await plan_without_split(files, options, session)

    started = time.monotonic()
    try:
        documents = await _segment_all(pages_by_file)
    except Exception as exc:  # noqa: BLE001 — chia giấy hỏng thì đính nguyên tệp như chế độ không tách
        result = await plan_without_split(files, options, session)
        result["errors"] = [f"attachment_agent (tách): {exc}", *result.get("errors", [])]
        return result
    llm_ms = int((time.monotonic() - started) * 1000)

    parts = _parts(raw_files, pages_by_file, documents)
    virtual_files = [{"name": p["name"], "type": raw_files[p["fileIndex"]]["type"]} for p in parts]
    virtual_ocr = [{"name": p["name"], "text": p["text"]} for p in parts]
    # Giấy LLM không phân loại (trang lạc, tệp không OCR) để trống → build_plan_items tự dùng lưới rule.
    llm_types = {v: _llm_info(p["doc"]) for v, p in enumerate(parts) if p["doc"]}
    attachments, classified = build_plan_items(virtual_files, virtual_ocr, llm_types, session)

    return {
        "attachments": _to_sources(attachments, parts, raw_files),
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "attachmentMode": "split_documents",
            "classified": [
                {**c, "pages": [i + 1 for i in p["pageIndexes"]] if p["pageIndexes"] is not None else "cả tệp"}
                for c, p in zip(classified, parts)
            ],
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
