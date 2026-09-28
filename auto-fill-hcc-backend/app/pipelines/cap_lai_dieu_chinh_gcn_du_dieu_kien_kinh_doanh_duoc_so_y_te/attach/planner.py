"""Đính kèm bước "Thành phần hồ sơ" cho "Cấp lại, điều chỉnh GCN đủ điều kiện kinh doanh dược (Sở Y tế)"
(cổng Bộ Y tế — Angular mat-table, engine FE `attp-row`).

ENGINE TÁCH/GỘP (như dinh_chinh_gcn_da_cap_da_nang): OCR per-file có header "Trang n/m" → LLM gán KHOẢNG
TRANG + loại cho từng đoạn → hậu xử lý tất định (chống chồng/thiếu trang) → mỗi đoạn thành 1 attachment kèm
`sourceSegments` (pageIndexes). FE tự tách PDF gộp thành từng PDF con rồi attp-row gom theo dòng (1 dòng
nhận được NHIỀU file). Xử lý được cả 1 PDF gộp cả hồ sơ lẫn nhiều file riêng.

Bảng 6 dòng (đều "1 Bản chính"):
  [1] Đơn đề nghị CẤP LẠI (Mẫu 11 PL I)          ← don_cap_lai
  [2] GCN đủ ĐKKD dược bị ghi sai do lỗi cơ quan  ← gcn_du_dkkd_duoc, CHỈ khi hồ sơ là CẤP LẠI (có Đơn cấp
                                                    lại); hồ sơ điều chỉnh thì không đính, báo để cán bộ tự quyết
  [3] Đơn đề nghị ĐIỀU CHỈNH (Mẫu 12 PL I)        ← don_dieu_chinh
  [4] Chứng chỉ hành nghề dược                    ← cchn_duoc
  [5] GCN đăng ký DN / tài liệu pháp lý thay đổi  ← giay_to_phap_ly (GCN ĐKHKD, GCN ĐKDN, GPP... cùng dòng)
  [6] Tài liệu thuyết minh an ninh (Mẫu 11 PL II)  ← thuyet_minh_an_ninh
CCCD không có dòng → bỏ qua (chỉ dùng ở bước điền thông tin).
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
from app.pipelines.cap_lai_dieu_chinh_gcn_du_dieu_kien_kinh_doanh_duoc_so_y_te.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON_CAP_LAI = "don_cap_lai"
_GCN_DKKD = "gcn_du_dkkd_duoc"
_DON_DIEU_CHINH = "don_dieu_chinh"
_CCHN = "cchn_duoc"
_PHAP_LY = "giay_to_phap_ly"
_THUYET_MINH = "thuyet_minh_an_ninh"
_CCCD = "cccd"
_OTHER = "other"
_ALLOWED = {_DON_CAP_LAI, _GCN_DKKD, _DON_DIEU_CHINH, _CCHN, _PHAP_LY, _THUYET_MINH, _CCCD, _OTHER}

# componentName = ĐOẠN TEXT ĐẶC TRƯNG DUY NHẤT của dòng (FE khớp substring fold); componentIndex = STT dòng
# (1-based) làm gợi ý, lệch thì FE tự rơi về khớp theo chữ. Dòng 1/2/3 đều chứa "Giấy chứng nhận đủ điều
# kiện kinh doanh dược" nên cụm chọn phải chứa phần phân biệt ("cấp lại" / "bị ghi sai" / "điều chỉnh").
_ROWS: dict[str, dict[str, Any]] = {
    _DON_CAP_LAI: {
        "componentName": "Đơn đề nghị cấp lại Giấy chứng nhận đủ điều kiện kinh doanh dược",
        "componentIndex": 1,
        "documentName": "Đơn đề nghị cấp lại GCN đủ ĐKKD dược (Mẫu 11)",
    },
    _GCN_DKKD: {
        "componentName": "bị ghi sai do lỗi của cơ quan cấp",
        "componentIndex": 2,
        "documentName": "Giấy chứng nhận đủ điều kiện kinh doanh dược",
    },
    _DON_DIEU_CHINH: {
        "componentName": "Đơn đề nghị điều chỉnh Giấy chứng nhận đủ điều kiện kinh doanh dược",
        "componentIndex": 3,
        "documentName": "Đơn đề nghị điều chỉnh GCN đủ ĐKKD dược (Mẫu 12)",
    },
    _CCHN: {
        "componentName": "Chứng chỉ hành nghề dược đối với các trường hợp thay đổi vị trí công việc",
        "componentIndex": 4,
        "documentName": "Chứng chỉ hành nghề dược",
    },
    _PHAP_LY: {
        "componentName": "tài liệu pháp lý chứng minh việc thay đổi",
        "componentIndex": 5,
        "documentName": "Tài liệu pháp lý chứng minh thay đổi tên, địa chỉ cơ sở",
    },
    _THUYET_MINH: {
        "componentName": "Tài liệu thuyết minh cơ sở đáp ứng các biện pháp bảo đảm an ninh",
        "componentIndex": 6,
        "documentName": "Tài liệu thuyết minh bảo đảm an ninh (Mẫu 11 PL II)",
    },
}
_LOAI_BAN = "Bản chính"

_PAGE_HEADER_RE = re.compile(
    r"(?im)^[\t ─-╿-]*(?:trang|page)\s+(\d+)\s*/\s*(\d+)[\t ─-╿-]*$"
)


# ---------------- Segment engine (copy pattern dinh_chinh_gcn_da_cap_da_nang) ----------------
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
    t = re.sub(r"[\s-]+", "_", _fold(value or ""))
    if t in _ALLOWED:
        return t
    if "thuyet_minh" in t or "an_ninh" in t:
        return _THUYET_MINH
    if "dieu_chinh" in t:
        return _DON_DIEU_CHINH
    if "cap_lai" in t:
        return _DON_CAP_LAI
    if "cchn" in t or "chung_chi" in t:
        return _CCHN
    if "phap_ly" in t or "ho_kinh_doanh" in t or "doanh_nghiep" in t or "gpp" in t:
        return _PHAP_LY
    if "dkkd" in t or "du_dieu_kien" in t:
        return _GCN_DKKD
    if "cccd" in t or "can_cuoc" in t or "cmnd" in t:
        return _CCCD
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
    for file_index in range(len(raw_files)):
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
def _rule_type(text: str) -> str:
    """THỨ TỰ QUAN TRỌNG: Đơn kê lại "Đã được cấp Giấy chứng nhận đủ điều kiện kinh doanh dược" và "Số CCHN
    Dược" → phải nhận Đơn TRƯỚC GCN đủ ĐKKD dược / CCHN. Mẫu 11 PL II (thuyết minh) nhận trước Đơn cấp lại
    vì cùng số mẫu."""
    h = _fold(text)
    if not h:
        return _OTHER
    if "thuyet minh" in h and ("an ninh" in h or "that thoat" in h or "kiem soat dac biet" in h):
        return _THUYET_MINH
    if "don de nghi" in h and "dieu chinh" in h and "kinh doanh duoc" in h:
        return _DON_DIEU_CHINH
    if "don de nghi" in h and "cap lai" in h and "kinh doanh duoc" in h:
        return _DON_CAP_LAI
    if (
        "dang ky ho kinh doanh" in h
        or "dang ky doanh nghiep" in h
        or "thuc hanh tot" in h
        or re.search(r"\bg[pd]p\b", h)
    ):
        return _PHAP_LY
    if "giay chung nhan" in h and "du dieu kien kinh doanh duoc" in h:
        return _GCN_DKKD
    if "chung chi hanh nghe duoc" in h:
        return _CCHN
    if any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu")):
        return _CCCD
    return _OTHER


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


def build_plan_items(
    raw_files: list[dict],
    segments: list[dict],
    file_meta: dict[int, dict],
    page_text_by_file: dict[int, dict[int, str]],
    full_text_by_file: dict[int, str],
) -> tuple[list[dict], list[dict], list[str]]:
    """Đoạn đã hợp lệ → (attachments, classified, warnings). Thuần tất định, không gọi OCR/LLM."""
    typed: list[tuple[dict, str, str]] = []
    for segment in segments:
        seg_text = _segment_text(segment, page_text_by_file, full_text_by_file)
        doc_type = segment["type"]
        # LLM là chính; rule OCR chỉ vá khi LLM trả other/không rõ.
        if doc_type not in _ROWS and doc_type != _CCCD:
            doc_type = _rule_type(seg_text)
        typed.append((segment, doc_type, seg_text))

    is_cap_lai = any(doc_type == _DON_CAP_LAI for _, doc_type, _ in typed)
    attachments: list[dict] = []
    classified: list[dict] = []
    warnings: list[str] = []
    used_names: set[str] = set()
    skipped_pages: list[str] = []

    for segment, doc_type, _ in typed:
        file_index = segment["fileIndex"]
        file = raw_files[file_index]
        page_count = file_meta[file_index]["pageCount"]
        where = f"{file.get('name')} trang {segment['pageFrom']}-{segment['pageTo']}"
        base = {"fileIndex": file_index, "fileName": file.get("name"),
                "pageFrom": segment["pageFrom"], "pageTo": segment["pageTo"], "type": doc_type}

        if doc_type == _CCCD:
            classified.append({**base, "target": "skip", "reason": "CCCD không nằm trong thành phần hồ sơ"})
            continue
        if doc_type == _GCN_DKKD and not is_cap_lai:
            warnings.append(
                f"{where}: Giấy chứng nhận đủ điều kiện kinh doanh dược — dòng 2 chỉ dùng khi CẤP LẠI do cơ quan "
                "cấp ghi sai, hồ sơ này là điều chỉnh nên không đính kèm; nếu Sở yêu cầu thì đính tay."
            )
            classified.append({**base, "target": "skip", "reason": "chỉ đính khi cấp lại"})
            continue
        if doc_type not in _ROWS:
            skipped_pages.append(where)
            classified.append({**base, "type": _OTHER, "target": "skip"})
            continue

        row = _ROWS[doc_type]
        document_name = _unique_name(segment.get("documentName") or row["documentName"], used_names,
                                     row["documentName"])
        item = {
            "fileIndex": file_index,
            "fileName": str(file.get("name") or f"file-{file_index + 1}"),
            "documentName": document_name,
            "componentName": row["componentName"],
            "componentIndex": row["componentIndex"],
            "loaiBan": _LOAI_BAN,
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": doc_type,
        }
        source = _source_segment(segment, page_count)
        if source["pageIndexes"] is not None:  # đoạn con của PDF gộp → FE tách theo trang.
            item["sourceSegments"] = [source]
        attachments.append(item)
        classified.append({**base, "documentName": document_name, "componentIndex": row["componentIndex"]})

    if skipped_pages:
        warnings.append("Không xác định được loại giấy tờ (bỏ qua, đính thủ công nếu cần): " + "; ".join(skipped_pages))

    found = {item["detectedType"] for item in attachments}
    if not found & {_DON_CAP_LAI, _DON_DIEU_CHINH}:
        warnings.append("Không tìm thấy Đơn đề nghị cấp lại (Mẫu 11) / điều chỉnh (Mẫu 12) — vui lòng đính tay.")
    all_text = _fold(" ".join(full_text_by_file.values()))
    controlled = any(k in all_text for k in ("gay nghien", "huong than", "tien chat"))
    if controlled and _THUYET_MINH not in found:
        warnings.append(
            "Phạm vi kinh doanh có thuốc chứa dược chất gây nghiện/hướng thần/tiền chất nhưng hồ sơ chưa có Tài "
            "liệu thuyết minh bảo đảm an ninh (Mẫu 11 PL II) — xác nhận với Sở Y tế có cần bổ sung dòng 6 không."
        )
    return attachments, classified, warnings


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
    attachments, classified, warnings = build_plan_items(
        raw_files, segments, file_meta, page_text_by_file, full_text_by_file
    )
    errors.extend(warnings)

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
            "rows": [{"docType": k, **v} for k, v in _ROWS.items()],
        },
        "ocr_text": join_ocr_documents(indexed_ocr),
        "llm_output": {"documents": raw_segments},
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
