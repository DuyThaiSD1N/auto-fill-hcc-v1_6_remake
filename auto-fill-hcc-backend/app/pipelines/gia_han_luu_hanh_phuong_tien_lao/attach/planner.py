"""Đính kèm bước "Thành phần hồ sơ" cho "Gia hạn thời gian lưu hành tại Việt Nam cho phương tiện của Lào" (cổng
Bộ Xây dựng — Angular mat-table, engine FE `attp-row`).

Bảng 2 dòng (đều "1 Bản chính"): 1 Giấy đề nghị gia hạn theo mẫu (Mẫu 07) · 2 Giấy phép liên vận Việt Nam –
Lào. Một file hay gộp nhiều giấy (vd báo giá sửa xe + giấy phép liên vận) → ENGINE TÁCH TRANG (copy
dang_ky_cap_gcn_nhan_chuyen_nhuong_du_an_bds_da_nang): LLM gán khoảng trang + loại + tên cho từng đoạn, FE tách
PDF con theo `sourceSegments`. Phân loại THUẦN LLM.
⚑ KHÔNG BỎ TRANG: báo giá / giấy chứng minh lý do, CCCD, ủy quyền, giấy khác → đính chung dòng 1 (giữ tên thật):
nút "Thêm giấy tờ" của cổng Bộ Xây dựng chưa có engine đã kiểm chứng.
"""

import base64
import re
import time
from typing import Any

import fitz

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.gia_han_luu_hanh_phuong_tien_lao.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DE_NGHI = "giay_de_nghi"
_GPLV = "giay_phep_lien_van"
_CHUNG_MINH = "giay_to_chung_minh"
_UY_QUYEN = "uy_quyen"
_CCCD = "cccd"
_OTHER = "other"

# componentName = đoạn chữ đặc trưng; componentIndex = STT dòng (1-based).
_ROWS: dict[str, dict[str, Any]] = {
    _DE_NGHI: {"componentName": "Giấy đề nghị gia hạn theo mẫu", "componentIndex": 1,
               "documentName": "Giấy đề nghị gia hạn Mẫu 07"},
    _GPLV: {"componentName": "Giấy phép liên vận giữa Việt Nam và Lào", "componentIndex": 2,
            "documentName": "Giấy phép liên vận Việt Nam Lào"},
}
# Không có dòng riêng → dòng 1 (bảng không có dòng "giấy tờ khác"; bỏ đoạn là mất trang hồ sơ).
_FALLBACK = _DE_NGHI
_ALLOWED = set(_ROWS) | {_CHUNG_MINH, _UY_QUYEN, _CCCD, _OTHER}
_EXTRA_NAMES = {_CHUNG_MINH: "Giấy tờ chứng minh lý do gia hạn", _UY_QUYEN: "Văn bản ủy quyền",
                _CCCD: "Căn cước công dân"}

_PAGE_HEADER_RE = re.compile(
    r"(?im)^[\t ─-╿-]*(?:trang|page)\s+(\d+)\s*/\s*(\d+)[\t ─-╿-]*$"
)


# ---------------- Segment engine (copy dang_ky_cap_gcn_nhan_chuyen_nhuong_du_an_bds_da_nang) ----------------
def _truncate(text: str, limit: int = 1500) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    return value if len(value) <= limit else value[:limit] + "..."


def _decode_data_url(data_url: str) -> bytes:
    _, sep, payload = str(data_url or "").partition(",")
    if not sep:
        return b""
    payload += "=" * (-len(payload) % 4)
    return base64.b64decode(payload)


def _pdf_page_count(file: dict) -> int:
    is_pdf = "pdf" in str(file.get("type") or "").lower() or str(file.get("name") or "").lower().endswith(".pdf")
    if not is_pdf:
        return 1
    try:
        doc = fitz.open(stream=_decode_data_url(file.get("dataUrl") or ""), filetype="pdf")
        try:
            return max(1, doc.page_count)
        finally:
            doc.close()
    except Exception:  # noqa: BLE001
        return 1


def _split_ocr_pages(text: str, expected_count: int) -> tuple[list[dict], bool]:
    value = str(text or "")
    matches = list(_PAGE_HEADER_RE.finditer(value))
    if not matches:
        return [{"pageNumber": 1, "ocrText": _truncate(value)}], expected_count == 1
    pages_by_number: dict[int, str] = {}
    declared_total = expected_count
    for pos, m in enumerate(matches):
        page_number = int(m.group(1))
        declared_total = max(declared_total, int(m.group(2)))
        end = matches[pos + 1].start() if pos + 1 < len(matches) else len(value)
        pages_by_number[page_number] = value[m.end():end].strip()
    return [
        {"pageNumber": p, "ocrText": _truncate(pages_by_number.get(p, ""))}
        for p in range(1, max(1, declared_total) + 1)
    ], True


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _fallback_segment(file_index: int, page_from: int, page_to: int) -> dict:
    return {"fileIndex": file_index, "pageFrom": page_from, "pageTo": page_to, "type": _OTHER, "documentName": ""}


def _normalize_type(value: str) -> str:
    """Khớp ĐÚNG nhãn enum; nhãn lạ → other (không dò chuỗi con — nhãn này chứa chữ của nhãn kia)."""
    t = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    return t if t in _ALLOWED else _OTHER


def _validated_segments(raw_segments: list[dict], raw_files: list[dict], file_meta: dict[int, dict],
                        errors: list[str]) -> list[dict]:
    by_file: dict[int, list[dict]] = {i: [] for i in range(len(raw_files))}
    for raw in raw_segments:
        if not isinstance(raw, dict):
            continue
        file_index = _coerce_int(raw.get("fileIndex", raw.get("index")))
        if file_index not in by_file:
            continue
        page_count = file_meta[file_index]["pageCount"]
        page_from = _coerce_int(raw.get("pageFrom")) or 1
        page_to = _coerce_int(raw.get("pageTo")) or page_count
        if not 1 <= page_from <= page_to <= page_count:
            errors.append(f"Phân đoạn fileIndex={file_index} có khoảng trang không hợp lệ: {page_from}-{page_to}.")
            continue
        by_file[file_index].append({
            "fileIndex": file_index, "pageFrom": page_from, "pageTo": page_to,
            "type": _normalize_type(raw.get("type") or raw.get("detectedType")),
            "documentName": str(raw.get("documentName") or raw.get("title") or "").strip(),
        })

    valid: list[dict] = []
    for file_index, file in enumerate(raw_files):
        meta = file_meta[file_index]
        page_count = meta["pageCount"]
        items = sorted(by_file[file_index], key=lambda x: (x["pageFrom"], x["pageTo"]))
        if not meta["pageBoundariesAvailable"]:
            first = items[0] if items else _fallback_segment(file_index, 1, page_count)
            valid.append({**first, "pageFrom": 1, "pageTo": page_count})
            continue
        occupied: set[int] = set()
        accepted: list[dict] = []
        for item in items:
            pages = set(range(item["pageFrom"], item["pageTo"] + 1))
            if occupied & pages:
                errors.append(f"Phân đoạn fileIndex={file_index} bị chồng trang; bỏ đoạn {item['pageFrom']}-{item['pageTo']}.")
                continue
            occupied.update(pages)
            accepted.append(item)
        missing = [p for p in range(1, page_count + 1) if p not in occupied]
        start = prev = None
        for page in missing + [None]:
            if page is not None and start is None:
                start = prev = page
            elif page is not None and page == prev + 1:
                prev = page
            else:
                if start is not None:
                    accepted.append(_fallback_segment(file_index, start, prev))
                start = prev = page
        valid.extend(sorted(accepted, key=lambda x: x["pageFrom"]))
    return sorted(valid, key=lambda x: (x["fileIndex"], x["pageFrom"]))


def _source_segment(segment: dict, page_count: int) -> dict:
    indexes = None
    if segment["pageFrom"] != 1 or segment["pageTo"] != page_count:
        indexes = list(range(segment["pageFrom"] - 1, segment["pageTo"]))
    return {"fileIndex": segment["fileIndex"], "pageIndexes": indexes}


async def _classify_with_llm(documents: list[dict[str, Any]]) -> list[dict]:
    if not documents:
        return []
    page_total = sum(len(d.get("pages") or []) for d in documents)
    raw = await client.chat(
        [
            {"role": "system", "content": prompt.SYSTEM_PROMPT},
            {"role": "user", "content": prompt.build_user_prompt(documents)},
        ],
        max_tokens=max(1200, min(4000, page_total * 180)),
        enable_thinking=settings.agent_reasoning,
    )
    parsed = client.extract_json_block(raw)
    return parsed.get("documents", []) or []


def _clean_name(value: str) -> str:
    """Tên tài liệu: bỏ ngoặc, "/" (engine đặt tên tệp theo tên này), gọn khoảng trắng, ≤ 50 ký tự."""
    text = re.sub(r"[()\[\]{}]", " ", str(value or "")).replace("/", "-")
    text = re.sub(r"\s+", " ", text).strip(" .-")
    return text[:50].rstrip(" .-")


def _unique_name(base: str, used: set[str], fallback: str) -> str:
    normalized = _clean_name(base) or _clean_name(fallback) or "Tài liệu kèm theo"
    key = _fold(normalized)
    if key not in used:
        used.add(key)
        return normalized
    stem = normalized[:45].strip()
    n = 2
    while True:
        cand = f"{stem} {n}"
        if _fold(cand) not in used:
            used.add(_fold(cand))
            return cand
        n += 1


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file([f for _, f in ocr_pairs]) if ocr_pairs else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    ocr_by_index = {ri: res for (ri, _), res in zip(ocr_pairs, ocr_results)}
    for ri, res in ocr_by_index.items():
        if res.get("error"):
            errors.append(f"OCR fileIndex={ri} {raw_files[ri].get('name')}: {res['error']}")

    file_meta: dict[int, dict] = {}
    llm_docs: list[dict] = []
    for file_index, file in enumerate(raw_files):
        text = str((ocr_by_index.get(file_index) or {}).get("text") or "")
        page_count = _pdf_page_count(file)
        pages, boundaries = _split_ocr_pages(text, page_count)
        page_count = max(page_count, max((int(p.get("pageNumber") or 1) for p in pages), default=1))
        file_meta[file_index] = {"pageCount": page_count, "pageBoundariesAvailable": boundaries}
        if text.strip():
            llm_docs.append({"fileIndex": file_index, "pageCount": page_count,
                             "pageBoundariesAvailable": boundaries, "pages": pages})

    t1 = time.monotonic()
    raw_segments: list[dict] = []
    if llm_docs:
        try:
            raw_segments = await _classify_with_llm(llm_docs)
        except Exception as e:  # noqa: BLE001
            errors.append(f"attachment_agent: {e}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    segments = _validated_segments(raw_segments, raw_files, file_meta, errors)

    attachments: list[dict] = []
    classified: list[dict] = []
    used_names: set[str] = set()
    unknown_pages: list[str] = []
    for segment in segments:
        file_index = segment["fileIndex"]
        file = raw_files[file_index]
        page_count = file_meta[file_index]["pageCount"]
        doc_type = segment["type"]
        row_type = doc_type if doc_type in _ROWS else _FALLBACK
        row = _ROWS[row_type]
        if doc_type == _OTHER:
            unknown_pages.append(f"{file.get('name')} trang {segment['pageFrom']}-{segment['pageTo']}")
        fallback_name = row["documentName"] if doc_type in _ROWS else _EXTRA_NAMES.get(doc_type, "Giấy tờ kèm theo")
        document_name = _unique_name(segment.get("documentName") or "", used_names, fallback_name)
        item = {
            "fileIndex": file_index,
            "fileName": str(file.get("name") or f"file-{file_index + 1}"),
            "documentName": document_name,
            "componentName": row["componentName"],
            "componentIndex": row["componentIndex"],
            "loaiBan": "Bản chính",
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": doc_type,
        }
        source = _source_segment(segment, page_count)
        if source["pageIndexes"] is not None:  # đoạn con của PDF gộp → FE tách theo trang.
            item["sourceSegments"] = [source]
        attachments.append(item)
        classified.append({
            "fileIndex": file_index, "fileName": file.get("name"),
            "pageFrom": segment["pageFrom"], "pageTo": segment["pageTo"],
            "type": doc_type, "documentName": document_name,
            "componentIndex": row["componentIndex"],
        })

    if unknown_pages:
        errors.append("Chưa nhận ra loại giấy tờ, đã đính chung vào dòng Giấy đề nghị gia hạn để không bỏ sót — "
                      "cán bộ kiểm tra lại: " + "; ".join(unknown_pages))

    indexed_ocr = []
    for file_index, file in enumerate(raw_files):
        res = ocr_by_index.get(file_index)
        if res:
            indexed_ocr.append({**res, "name": f"fileIndex={file_index} · {file.get('name')}"})

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [raw_files[i]["name"] for i, r in ocr_by_index.items() if r.get("text")],
            "llmDocuments": [raw_files[d["fileIndex"]]["name"] for d in llm_docs],
            "sessionId": (session or {}).get("request_id"),
            "classified": classified,
        },
        "ocr_text": join_ocr_documents(indexed_ocr),
        "llm_output": {"documents": raw_segments},
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
