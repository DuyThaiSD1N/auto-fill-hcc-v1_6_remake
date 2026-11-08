"""Đính kèm TÁCH giấy tờ cho thủ tục đính chính GCN có sai sót (iGate Tuyên Quang) — cài đặt "Có tách hồ sơ khi
đính kèm" bật.

Bộ hồ sơ hay là MỘT bản scan gộp (Đơn, hợp đồng, Giấy chứng nhận, giấy khai sinh, CCCD, trích lục). LLM đọc đầu từng
trang trong MỘT lượt, chỉ ra trang nào mở giấy mới và loại giấy đó; mỗi giấy thành một mục đính kèm có `sourceSegments`
(extension cắt đúng các trang) đặt vào dòng của loại giấy:

  land_certificate -> dòng 1 | giấy tờ chứng minh sai sót, CCCD -> dòng 2 (Bản sao) | authorization -> dòng 3
  don_mau_11 -> dòng 4 | don_mau_18 và giấy không rõ loại -> dòng 8

Dòng 5/6/7 lặp danh mục dòng 1/2/3 nên KHÔNG đính. Trang trắng bỏ; trang nối tiếp thuộc giấy liền trước. Tệp không
cắt được (ảnh, số trang OCR lệch PDF) và trường hợp LLM chia giấy lỗi → đính như chế độ không tách: nguyên tệp một
lần vào dòng của giấy chính.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.documents import representative_excerpt
from app.pipelines.di_chuyen_ho_so_nguoi_huong_tro_cap.attach.planner import splittable_pages
from app.process.schemas import FileItem
from app.services.llm import client

from ..dinh_kem_khong_tach.planner import _DON_ROW, _OTHER, _PRIORITY, _ROWS, _TYPE_ROW, _normalize_doc_type
from ..dinh_kem_khong_tach.planner import plan as plan_without_split
from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
# Trang trắng / mặt sau hoa văn: OCR chỉ ra vài chữ rác; trang đầu giấy thật luôn hàng trăm ký tự.
_MIN_PAGE_CHARS = 40
_PAGE_OCR_CHARS = 1200
_MAX_NAME = 60


def _row(doc_type: str) -> int:
    return _TYPE_ROW.get(doc_type, _DON_ROW)


def _is_blank(page: str) -> bool:
    return len(re.findall(r"\w", page or "")) < _MIN_PAGE_CHARS


def _clean_name(raw: Any) -> str:
    text = re.sub(r"[^\w\s,.()\-]", " ", str(raw or "").replace("/", "-"))
    return re.sub(r"\s+", " ", text).strip(" -,.")[:_MAX_NAME].strip(" -,.")


def _page_ocr(page: str) -> str:
    if _is_blank(page):
        return "(trang trắng / mặt sau, không có nội dung)"
    return re.sub(r"\s+", " ", page).strip()[:_PAGE_OCR_CHARS]


def parse_documents(data: dict, page_counts: dict[int, int]) -> dict[int, list[tuple[int, str, str]]]:
    """JSON LLM → {tệp: [(trang đầu 0-based, docType, tên)]} theo trang tăng dần; bỏ số trang ngoài tệp."""
    out: dict[int, list[tuple[int, str, str]]] = {}
    for item in data.get("tep") or []:
        if not isinstance(item, dict):
            continue
        try:
            file_index = int(item.get("fileIndex"))
        except (TypeError, ValueError):
            continue
        count = page_counts.get(file_index) or 0
        if not count or file_index in out:
            continue
        docs: list[tuple[int, str, str]] = []
        for doc in item.get("giayTo") or []:
            if not isinstance(doc, dict):
                continue
            try:
                page = int(doc.get("trangDau")) - 1
            except (TypeError, ValueError):
                continue
            if 0 <= page < count:
                docs.append((page, _normalize_doc_type(doc.get("docType")), _clean_name(doc.get("ten"))))
        out[file_index] = sorted(docs, key=lambda doc: doc[0])
    return out


async def _segment(units: dict[int, list[str]]) -> dict[int, list[tuple[int, str, str]]]:
    payload = [
        {"fileIndex": index, "soTrang": len(pages),
         "trang": [{"trang": n + 1, "ocr": _page_ocr(page)} for n, page in enumerate(pages)]}
        for index, pages in units.items()
    ]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": build_user_prompt(payload)}]
    total = sum(len(pages) for pages in units.values())
    for attempt in range(2):  # JSON hỏng → hỏi lại một lần
        # temperature 0: cùng tệp phải ra cùng cách chia giữa các lần chạy.
        raw = await client.chat(messages, temperature=0, max_tokens=max(400, min(4000, 120 + 60 * total)),
                                enable_thinking=settings.agent_reasoning)
        try:
            return parse_documents(client.extract_json_block(raw), {i: len(p) for i, p in units.items()})
        except Exception:  # noqa: BLE001
            if attempt:
                raise
    return {}


def _item(file_index: int, file_name: str, row: int, document_name: str, doc_type: str,
          pages: list[int] | None) -> dict:
    item = {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": _ROWS[row]["name"],
        "componentIndex": row,
        "loaiBan": _ROWS[row]["loaiBan"],
        "target": "attp-row",
        # Cổng iGate Tuyên Quang tick sẵn mọi dòng thành phần → FE bỏ tick hết trước khi đính, chỉ dòng có tệp được tick lại.
        "untickUnplannedRows": True,
        "needsAddComponent": False,
        "detectedType": doc_type,
    }
    if pages is not None:
        item["sourceSegments"] = [{"fileIndex": file_index, "pageIndexes": pages}]
    return item


def _label(pages: list[int]) -> str:
    return f"trang {pages[0] + 1}" if len(pages) == 1 else f"trang {pages[0] + 1}-{pages[-1] + 1}"


def build_plan_items(
    files: list[dict],
    pages_by_file: dict[int, list[str]],
    documents: dict[int, list[tuple[int, str, str]]],
) -> tuple[list[dict], list[str], list[dict]]:
    """``pages_by_file``: trang OCR của tệp cắt được (>1 trang khớp PDF); tệp có chữ mà không cắt được mang 1 "trang"."""
    attachments: list[dict] = []
    warnings: list[str] = []
    segments: list[dict] = []
    seen_names: dict[str, int] = {}

    def add(file_index: int, doc_type: str, name: str, pages: list[int] | None) -> None:
        file_name = str(files[file_index].get("name") or f"file-{file_index + 1}")
        row = _row(doc_type)
        document_name = name or (file_name if doc_type == _OTHER else _ROWS[row]["documentName"])
        # Hai giấy cùng tên (CCCD hai người...) → đánh số để cổng và cán bộ phân biệt được.
        key = _fold(document_name)
        seen_names[key] = seen_names.get(key, 0) + 1
        if seen_names[key] > 1:
            document_name = f"{document_name} {seen_names[key]}"
        attachments.append(_item(file_index, file_name, row, document_name, doc_type, pages))
        segments.append({"fileName": file_name, "documentName": document_name, "docType": doc_type, "row": row,
                         "pages": "cả tệp" if pages is None else [p + 1 for p in pages]})
        if doc_type == _OTHER:
            where = f"{file_name}, {_label(pages)}" if pages is not None else file_name
            warnings.append(f"Chưa nhận diện chắc loại giấy tờ '{document_name}' ({where}) — tạm đính vào dòng "
                            f"{_DON_ROW} (Đơn đăng ký biến động Mẫu số 18); cán bộ kiểm tra lại.")

    for index in range(len(files)):
        pages = pages_by_file.get(index) or []
        docs = documents.get(index) or []
        if len(pages) <= 1:
            # Ảnh / tệp không cắt được: nguyên tệp MỘT lần vào dòng của giấy chính, như chế độ không tách.
            types = [doc_type for _, doc_type, _ in docs]
            doc_type = next((item for item in _PRIORITY if item in types), _OTHER)
            others = sorted({_row(item) for item in types if item in _TYPE_ROW} - {_row(doc_type)})
            file_name = str(files[index].get("name") or f"file-{index + 1}")
            name = file_name if others else next((n for _, item, n in docs if item == doc_type), "")
            add(index, doc_type, name, None)
            if others:
                warnings.append(f"'{file_name}' gộp nhiều giấy tờ nhưng không tách được trang — đính nguyên tệp một "
                                f"lần vào dòng {_row(doc_type)}, không tách sang dòng "
                                f"{', '.join(str(row) for row in others)}.")
            continue
        starts: dict[int, tuple[str, str]] = {}
        for page, doc_type, name in docs:
            starts.setdefault(page, (doc_type, name))
        starts.setdefault(0, (_OTHER, ""))
        bounds = sorted(starts) + [len(pages)]
        for first, end in zip(bounds, bounds[1:]):
            kept = [p for p in range(first, end) if not _is_blank(pages[p])]
            if not kept:
                continue  # đoạn toàn trang trắng
            doc_type, name = starts[first]
            whole = kept == list(range(len(pages)))
            add(index, doc_type, name, None if whole else kept)

    return attachments, warnings, segments


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    from app.services import ocr

    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    pairs = [(index, file) for index, file in enumerate(raw_files) if file.get("type") in _OCR_TYPES]
    errors: list[str] = []

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file([file for _, file in pairs]) if pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    pages_by_file: dict[int, list[str]] = {}
    for (index, file), result in zip(pairs, ocr_results):
        if result.get("error"):
            errors.append(f"OCR {file.get('name')}: {result['error']}")
        text = str(result.get("text") or "")
        if not text.strip():
            continue
        # Không cắt được (số trang OCR lệch PDF) → cả tệp là một "trang" trích đoạn đại diện.
        pages_by_file[index] = splittable_pages(file, text) or [representative_excerpt(text, 6000)]

    started = time.monotonic()
    try:
        documents = await _segment(pages_by_file) if pages_by_file else {}
    except Exception as exc:  # noqa: BLE001 — chia giấy hỏng thì đính nguyên tệp như chế độ không tách
        result = await plan_without_split(files, options, session)
        result["errors"] = [f"Tách giấy tờ: {exc} — đính nguyên tệp.", *errors, *result.get("errors", [])]
        return result
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, segments = build_plan_items(raw_files, pages_by_file, documents)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [item["name"] for item in raw_files],
            "tachGiayTo": segments,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
