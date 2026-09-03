"""Đính kèm bước "Thành phần hồ sơ" cho "Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót" (cổng DVC
Đà Nẵng — Angular mat-table, engine FE `attp-row`).

ENGINE TÁCH/GỘP (như hộ tịch): OCR per-file có header "Trang n/m" → LLM gán KHOẢNG TRANG + loại cho từng
đoạn tài liệu → hậu xử lý tất định (chống chồng/thiếu trang) → mỗi đoạn thành 1 attachment kèm
`sourceSegments` (pageIndexes). FE (applyMergeGroups, generic) tự tách 1 PDF hỗn hợp thành từng PDF con
rồi engine attp-row gom theo dòng. Xử lý được cả 2 kiểu: 1 PDF gộp cả hồ sơ HOẶC nhiều file riêng.

Bảng 4 dòng (đều "Bản chính"): [1] Bản gốc GCN đã cấp · [2] Giấy tờ chứng minh sai sót (CCCD/trích lục/
khai sinh/HĐ — mỗi giấy 1 file, cùng đổ vào dòng 2) · [3] Văn bản ủy quyền · [4] Đơn Mẫu 18.
"""

import base64
import re
import time
from typing import Any

import fitz

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.dinh_chinh_gcn_da_cap_da_nang.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_GCN = "gcn_da_cap"
_CHUNG_MINH = "giay_to_chung_minh"
_UY_QUYEN = "van_ban_uy_quyen"
_DON18 = "don_mau_18"
_OTHER = "other"
_ALLOWED = {_GCN, _CHUNG_MINH, _UY_QUYEN, _DON18, _OTHER}

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng; componentIndex = STT dòng (1-based) để FE khớp đúng dòng
# (dòng 1 & 2 đều chứa "Giấy chứng nhận đã cấp" → cần index).
_ROWS: dict[str, dict[str, Any]] = {
    _GCN: {"componentName": "Bản gốc Giấy chứng nhận đã cấp", "componentIndex": 1,
           "documentName": "Bản gốc Giấy chứng nhận đã cấp"},
    _CHUNG_MINH: {"componentName": "Giấy tờ chứng minh sai sót thông tin", "componentIndex": 2,
                  "documentName": "Giấy tờ chứng minh sai sót thông tin"},
    _UY_QUYEN: {"componentName": "Văn bản về việc ủy quyền", "componentIndex": 3,
                "documentName": "Văn bản về việc ủy quyền"},
    _DON18: {"componentName": "Đơn đăng ký biến động đất đai", "componentIndex": 4,
             "documentName": "Đơn đăng ký biến động đất đai (Mẫu số 18)"},
}

_PAGE_HEADER_RE = re.compile(
    r"(?im)^[\t ─-╿-]*(?:trang|page)\s+(\d+)\s*/\s*(\d+)[\t ─-╿-]*$"
)


# ---------------- Segment engine (copy pattern hộ tịch/chung_thuc) ----------------
def _truncate(text: str, limit: int = 2000) -> str:
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
    t = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    if t in _ALLOWED:
        return t
    if "uy_quyen" in t:
        return _UY_QUYEN
    if "mau_18" in t or "bien_dong" in t or t == "don":
        return _DON18
    if "gcn" in t or "chung_nhan" in t:
        return _GCN
    if "cccd" in t or "can_cuoc" in t or "chung_minh" in t or "trich_luc" in t or "khai_sinh" in t:
        return _CHUNG_MINH
    return _OTHER


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


def _segment_text(segment: dict, page_text_by_file: dict[int, dict[int, str]],
                  full_text_by_file: dict[int, str]) -> str:
    pages = page_text_by_file.get(segment["fileIndex"]) or {}
    if not pages:
        return full_text_by_file.get(segment["fileIndex"], "")
    return "\n".join(pages.get(p, "") for p in range(segment["pageFrom"], segment["pageTo"] + 1)).strip()


def _source_segment(segment: dict, page_count: int) -> dict:
    indexes = None
    if segment["pageFrom"] != 1 or segment["pageTo"] != page_count:
        indexes = list(range(segment["pageFrom"] - 1, segment["pageTo"]))
    return {"fileIndex": segment["fileIndex"], "pageIndexes": indexes}


# --- Rule fallback theo OCR (khi LLM không phân loại được đoạn) ---
def _is_identity_text(h: str) -> bool:
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu"))


def _rule_type(text: str) -> str:
    h = _fold(text)
    if not h:
        return _OTHER
    if "uy quyen" in h:
        return _UY_QUYEN
    if "don dang ky bien dong" in h or "mau so 18" in h:
        return _DON18
    if "giay chung nhan" in h and ("so vao so" in h or "quyen so huu nha" in h or "quyen su dung dat" in h):
        return _GCN
    if _is_identity_text(h) or "trich luc ket hon" in h or "giay khai sinh" in h or "hop dong chuyen dich" in h:
        return _CHUNG_MINH
    return _OTHER


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


def _unique_name(base: str, used: set[str], fallback: str) -> str:
    normalized = normalize_document_name(base or fallback, fallback)
    key = _fold(normalized)
    if key and key not in used:
        used.add(key)
        return normalized
    stem = normalized[:45].strip() or fallback[:45].strip() or "Tài liệu"
    n = 2
    while True:
        cand = f"{stem} {n}"[:50].strip()
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
    page_text_by_file: dict[int, dict[int, str]] = {}
    full_text_by_file: dict[int, str] = {}
    llm_docs: list[dict] = []
    for file_index, file in enumerate(raw_files):
        text = str((ocr_by_index.get(file_index) or {}).get("text") or "")
        full_text_by_file[file_index] = text
        page_count = _pdf_page_count(file)
        pages, boundaries = _split_ocr_pages(text, page_count)
        page_count = max(page_count, max((int(p.get("pageNumber") or 1) for p in pages), default=1))
        file_meta[file_index] = {"pageCount": page_count, "pageBoundariesAvailable": boundaries}
        page_text_by_file[file_index] = {int(p.get("pageNumber") or 1): str(p.get("ocrText") or "") for p in pages}
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
    skipped_pages: list[str] = []
    for segment in segments:
        file_index = segment["fileIndex"]
        file = raw_files[file_index]
        page_count = file_meta[file_index]["pageCount"]
        seg_text = _segment_text(segment, page_text_by_file, full_text_by_file)
        doc_type = segment["type"]
        # LLM là chính; rule OCR chỉ vá khi LLM trả other/không rõ.
        if doc_type not in _ROWS:
            doc_type = _rule_type(seg_text)

        if doc_type not in _ROWS:
            skipped_pages.append(f"{file.get('name')} trang {segment['pageFrom']}-{segment['pageTo']}")
            classified.append({"fileIndex": file_index, "pageFrom": segment["pageFrom"],
                               "pageTo": segment["pageTo"], "type": _OTHER, "target": "skip"})
            continue

        row = _ROWS[doc_type]
        document_name = _unique_name(segment.get("documentName") or row["documentName"], used_names, row["documentName"])
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

    if skipped_pages:
        errors.append("Không xác định được loại giấy tờ (bỏ qua, đính thủ công nếu cần): " + "; ".join(skipped_pages))

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
