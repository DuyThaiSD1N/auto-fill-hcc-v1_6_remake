"""Đính kèm bước "Thành phần hồ sơ" cho "Đăng ký tài sản gắn liền với thửa đất đã được cấp GCN..." (1.013995,
cổng DVC Đà Nẵng — Angular mat-table, engine FE `attp-row`).

ENGINE TÁCH/GỘP (như dinh_chinh_gcn_da_cap_da_nang): OCR per-file có header "Trang n/m" → LLM gán KHOẢNG
TRANG + loại cho từng đoạn → hậu xử lý tất định (chống chồng/thiếu trang, gộp đoạn LIỀN KỀ cùng loại) → mỗi
đoạn thành 1 attachment kèm `sourceSegments` (pageIndexes). FE tự tách PDF gộp thành từng PDF con rồi attp-row
gom theo dòng. Ca điển hình: 1 PDF scan "Đơn (trang 1) + GCN (trang 2-3)" → trang 1 vào dòng 1, trang 2-3 vào
dòng 2; văn bản thẩm định riêng → dòng 5.

Bảng 8 dòng (loại bản theo cổng: dòng 1 "Bản chính", còn lại "Bản sao"):
  [1] Đơn đăng ký biến động Mẫu số 18                  ← don_mau_18
  [2] Giấy chứng nhận đã cấp                           ← gcn_da_cap
  [3] Giấy tờ theo Điều 148, 149 Luật Đất đai (nếu có)  ← giay_to_148_149 (giấy phép xây dựng, HĐ mua bán nhà...)
  [4] Sơ đồ nhà ở, công trình xây dựng                 ← so_do_cong_trinh
  [5] Hồ sơ thiết kế đã thẩm định / chấp thuận nghiệm thu ← ho_so_thiet_ke
  [6] Văn bản chấp thuận gia hạn sở hữu nhà ở (nước ngoài) ← van_ban_gia_han
  [7] Mảnh trích đo bản đồ địa chính                    ← manh_trich_do
  [8] Văn bản về việc đại diện                          ← van_ban_dai_dien
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
from app.pipelines.dang_ky_tai_san_gan_lien_thua_dat_da_cap_gcn.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON18 = "don_mau_18"
_GCN = "gcn_da_cap"
_GIAY_TO_148 = "giay_to_148_149"
_SO_DO = "so_do_cong_trinh"
_THIET_KE = "ho_so_thiet_ke"
_GIA_HAN = "van_ban_gia_han"
_TRICH_DO = "manh_trich_do"
_DAI_DIEN = "van_ban_dai_dien"
_CCCD = "cccd"
_OTHER = "other"
_ALLOWED = {_DON18, _GCN, _GIAY_TO_148, _SO_DO, _THIET_KE, _GIA_HAN, _TRICH_DO, _DAI_DIEN, _CCCD, _OTHER}

# componentName = ĐOẠN TEXT ĐẶC TRƯNG DUY NHẤT của dòng (FE khớp substring fold); componentIndex = STT dòng
# (1-based) làm gợi ý, lệch thì FE tự rơi về khớp theo chữ. Dòng 3 và 4 đều nhắc "Điều 148, Điều 149" → cụm
# của dòng 3 phải có "theo quy định" (dòng 4 viết "giấy tờ quy định", không có "theo").
_ROWS: dict[str, dict[str, Any]] = {
    _DON18: {
        "componentName": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18",
        "componentIndex": 1,
        "documentName": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18)",
        "loaiBan": "Bản chính",
    },
    _GCN: {
        "componentName": "Giấy chứng nhận đã cấp",
        "componentIndex": 2,
        "documentName": "Giấy chứng nhận đã cấp",
        "loaiBan": "Bản sao",
    },
    _GIAY_TO_148: {
        "componentName": "Một trong các loại giấy tờ theo quy định tại các Điều 148",
        "componentIndex": 3,
        "documentName": "Giấy tờ về quyền sở hữu tài sản (Điều 148, 149 Luật Đất đai)",
        "loaiBan": "Bản sao",
    },
    _SO_DO: {
        "componentName": "Sơ đồ nhà ở, công trình xây dựng",
        "componentIndex": 4,
        "documentName": "Sơ đồ nhà ở, công trình xây dựng",
        "loaiBan": "Bản sao",
    },
    _THIET_KE: {
        "componentName": "Hồ sơ thiết kế xây dựng công trình đã được cơ quan chuyên môn về xây dựng thẩm định",
        "componentIndex": 5,
        "documentName": "Hồ sơ thiết kế xây dựng đã thẩm định / chấp thuận nghiệm thu",
        "loaiBan": "Bản sao",
    },
    _GIA_HAN: {
        "componentName": "Văn bản chấp thuận gia hạn thời hạn sở hữu nhà ở",
        "componentIndex": 6,
        "documentName": "Văn bản chấp thuận gia hạn thời hạn sở hữu nhà ở",
        "loaiBan": "Bản sao",
    },
    _TRICH_DO: {
        "componentName": "Mảnh trích đo bản đồ địa chính thửa đất",
        "componentIndex": 7,
        "documentName": "Mảnh trích đo bản đồ địa chính thửa đất",
        "loaiBan": "Bản sao",
    },
    _DAI_DIEN: {
        "componentName": "Văn bản về việc đại diện",
        "componentIndex": 8,
        "documentName": "Văn bản về việc đại diện",
        "loaiBan": "Bản sao",
    },
}

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
    if "dai_dien" in t or "uy_quyen" in t:
        return _DAI_DIEN
    if "mau_18" in t or "bien_dong" in t or t == "don":
        return _DON18
    if "gia_han" in t:
        return _GIA_HAN
    if "trich_do" in t:
        return _TRICH_DO
    if "thiet_ke" in t or "tham_dinh" in t or "nghiem_thu" in t:
        return _THIET_KE
    if "so_do" in t or "ban_ve" in t or "hoan_cong" in t:
        return _SO_DO
    if "148" in t or "149" in t or "giay_phep_xay_dung" in t or "gpxd" in t:
        return _GIAY_TO_148
    if "gcn" in t or "chung_nhan" in t:
        return _GCN
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
    """THỨ TỰ QUAN TRỌNG: Đơn Mẫu 18 kê "(1) Giấy chứng nhận đã cấp" → nhận Đơn TRƯỚC GCN. Văn bản thẩm định
    nhắc "giấy phép xây dựng" / "Giấy chứng nhận đăng ký đầu tư" → nhận thẩm định TRƯỚC giấy phép / GCN. GCN
    in "Sơ đồ thửa đất" → nhận GCN TRƯỚC sơ đồ công trình."""
    h = _fold(text)
    if not h:
        return _OTHER
    if "ben duoc uy quyen" in h or "hop dong uy quyen" in h or "giay uy quyen" in h:
        return _DAI_DIEN
    if "don dang ky bien dong" in h or "mau so 18" in h:
        return _DON18
    if "gia han thoi han so huu nha o" in h:
        return _GIA_HAN
    if "manh trich do" in h or "trich do ban do dia chinh" in h:
        return _TRICH_DO
    if (
        "ket qua tham dinh" in h
        or "nghiem thu hoan thanh" in h
        or "ket qua nghiem thu" in h
        or ("tham dinh" in h and ("thiet ke" in h or "bao cao nghien cuu kha thi" in h))
    ):
        return _THIET_KE
    if "giay phep xay dung" in h or "hop dong mua ban nha" in h or "hop dong mua ban cong trinh" in h:
        return _GIAY_TO_148
    if "giay chung nhan" in h and (
        "quyen su dung dat" in h or "quyen so huu nha" in h or "so vao so cap" in h or "thua dat so" in h
    ):
        return _GCN
    # Trang trong của GCN (mục II-IV) thường không in lại chữ "Giấy chứng nhận".
    if "so vao so cap" in h or ("thua dat so" in h and "to ban do so" in h):
        return _GCN
    if "so do nha" in h or "so do cong trinh" in h or "ban ve hoan cong" in h or "ban ve hien trang" in h:
        return _SO_DO
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


def _merge_adjacent(typed: list[tuple[dict, str]]) -> list[tuple[dict, str]]:
    """Gộp các đoạn LIỀN KỀ cùng file + cùng loại có dòng (vd GCN bìa trang 2 + trang trong trang 3) thành
    1 đoạn → 1 file đính kèm, đúng như bản giấy."""
    merged: list[tuple[dict, str]] = []
    for segment, doc_type in typed:
        if merged:
            prev_segment, prev_type = merged[-1]
            if (
                doc_type in _ROWS
                and doc_type == prev_type
                and prev_segment["fileIndex"] == segment["fileIndex"]
                and prev_segment["pageTo"] + 1 == segment["pageFrom"]
            ):
                merged[-1] = ({**prev_segment, "pageTo": segment["pageTo"]}, prev_type)
                continue
        merged.append((segment, doc_type))
    return merged


def build_plan_items(
    raw_files: list[dict],
    segments: list[dict],
    file_meta: dict[int, dict],
    page_text_by_file: dict[int, dict[int, str]],
    full_text_by_file: dict[int, str],
) -> tuple[list[dict], list[dict], list[str]]:
    """Đoạn đã hợp lệ → (attachments, classified, warnings). Thuần tất định, không gọi OCR/LLM."""
    typed: list[tuple[dict, str]] = []
    for segment in segments:
        doc_type = segment["type"]
        # LLM là chính; rule OCR chỉ vá khi LLM trả other/không rõ.
        if doc_type not in _ROWS and doc_type != _CCCD:
            doc_type = _rule_type(_segment_text(segment, page_text_by_file, full_text_by_file))
        typed.append((segment, doc_type))

    attachments: list[dict] = []
    classified: list[dict] = []
    warnings: list[str] = []
    used_names: set[str] = set()
    skipped_pages: list[str] = []

    for segment, doc_type in _merge_adjacent(typed):
        file_index = segment["fileIndex"]
        file = raw_files[file_index]
        page_count = file_meta[file_index]["pageCount"]
        where = f"{file.get('name')} trang {segment['pageFrom']}-{segment['pageTo']}"
        base = {"fileIndex": file_index, "fileName": file.get("name"),
                "pageFrom": segment["pageFrom"], "pageTo": segment["pageTo"], "type": doc_type}

        if doc_type == _CCCD:
            classified.append({**base, "target": "skip", "reason": "CCCD không nằm trong thành phần hồ sơ"})
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
            "loaiBan": row["loaiBan"],
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
    if _DON18 not in found:
        warnings.append("Không tìm thấy Đơn đăng ký biến động Mẫu số 18 (dòng 1, bắt buộc) — vui lòng đính tay.")
    if _GCN not in found:
        warnings.append("Không tìm thấy Giấy chứng nhận đã cấp (dòng 2, bắt buộc) — vui lòng đính tay.")
    if not found & {_GIAY_TO_148, _SO_DO}:
        warnings.append(
            "Hồ sơ chưa có Sơ đồ nhà ở, công trình xây dựng (dòng 4) hay giấy tờ theo Điều 148, 149 Luật Đất đai "
            "(dòng 3) — kiểm tra, bổ sung sơ đồ công trình nếu tài sản đăng ký chưa có trong GCN."
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
