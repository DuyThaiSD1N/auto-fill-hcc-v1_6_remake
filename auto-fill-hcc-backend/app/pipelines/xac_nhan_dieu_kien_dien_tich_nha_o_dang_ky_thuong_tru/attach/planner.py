"""Đính kèm bước "Thành phần hồ sơ" cho "Xác nhận về điều kiện diện tích bình quân nhà ở để đăng ký thường trú
..." (1.013314, cổng tỉnh iGate — Angular mat-table, engine FE `attp-row` + modal "Thêm giấy tờ").

ENGINE TÁCH/GỘP (như dang_ky_lai_phuong_tien_chuyen_quyen_so_huu_khong_doi_co_quan): OCR per-file có header
"Trang n/m" → LLM gán KHOẢNG TRANG + loại cho từng đoạn → hậu xử lý tất định → GOM các đoạn cùng dòng thành MỘT
file (`sourceSegments`). Hồ sơ hay là MỘT PDF gộp Tờ khai + Giấy chứng nhận.

Bảng thành phần hồ sơ CHỈ CÓ MỘT dòng (theo ảnh ánh xạ của thủ tục):
  1. Tờ khai xác nhận tình trạng chỗ ở hợp pháp, diện tích nhà ở tối thiểu ... (Mẫu số 02)  ← to_khai (Bản chính)
Giấy chứng nhận QSDĐ/QSH nhà ở là giấy tờ chứng minh chỗ ở hợp pháp nhưng KHÔNG có dòng → bấm "+ Thêm giấy tờ"
(`add-document-dialog`) tạo dòng "Giấy chứng nhận quyền sử dụng đất" (Bản sao). Trong file GCN, trang BÌA + "VI-
Những thay đổi sau khi cấp" đứng TRƯỚC trang I-V (đúng thứ tự ánh xạ). Hợp đồng thuê/mượn/ở nhờ và văn bản ủy quyền
cũng đi qua "Thêm giấy tờ". Modal không tạo được dòng thì FE ĐÍNH CHUNG vào dòng Tờ khai (`fallbackComponentName`).
CCCD không thuộc thành phần hồ sơ (thông tin nhân thân đã kê khai ở bước 1) → bỏ qua. Trang không rõ loại → đính
chung dòng Tờ khai, kèm cảnh báo.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.attach.planner import (
    _segment_text,
    _source_segment,
    _split_ocr_pages,
)
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.attach.planner import (
    _coerce_int,
    _fallback_segment,
    _merge_adjacent,
    _pdf_page_count,
    _truncate,
)
from app.pipelines.xac_nhan_dieu_kien_dien_tich_nha_o_dang_ky_thuong_tru.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_TO_KHAI = "to_khai"
_GCN = "giay_chung_nhan"
_GIAY_TO_CHO_O = "giay_to_cho_o"
_AUTHORIZATION = "authorization"
_CCCD = "cccd"
_OTHER = "other"
_ALLOWED = {_TO_KHAI, _GCN, _GIAY_TO_CHO_O, _AUTHORIZATION, _CCCD, _OTHER}

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold).
_TO_KHAI_ROW = {
    "componentName": "Tờ khai xác nhận tình trạng chỗ ở hợp pháp",
    "componentIndex": 0,
    "documentName": "Tờ khai xác nhận tình trạng chỗ ở hợp pháp",
    "loaiBan": "Bản chính",
}
# Dòng tạo qua modal "Thêm giấy tờ": componentName gõ vào ô autocomplete "Giấy tờ" của modal.
_ADDED_ROWS: dict[str, dict[str, str]] = {
    _GCN: {
        "componentName": "Giấy chứng nhận quyền sử dụng đất",
        "documentName": "Giấy chứng nhận quyền sử dụng đất",
        "loaiBan": "Bản sao",
    },
    _GIAY_TO_CHO_O: {
        "componentName": "Giấy tờ, tài liệu chứng minh chỗ ở hợp pháp",
        "documentName": "Giấy tờ chứng minh chỗ ở hợp pháp",
        "loaiBan": "Bản sao",
    },
    _AUTHORIZATION: {
        "componentName": "Văn bản ủy quyền",
        "documentName": "Văn bản ủy quyền",
        "loaiBan": "Bản chính",
    },
}
# Thứ tự dòng thêm (theo ánh xạ: GCN là dòng 2).
_ADDED_ORDER = [_GCN, _GIAY_TO_CHO_O, _AUTHORIZATION]


def _normalize_type(value: Any) -> str:
    t = re.sub(r"[\s-]+", "_", _fold(str(value or "")))
    if t in _ALLOWED:
        return t
    if "to_khai" in t or "mau_02" in t or t == "don":
        return _TO_KHAI
    if "chung_nhan" in t or "gcn" in t or "so_do" in t or "so_hong" in t:
        return _GCN
    if "uy_quyen" in t:
        return _AUTHORIZATION
    if "hop_dong" in t or "cho_o" in t or "thue" in t or "o_nho" in t:
        return _GIAY_TO_CHO_O
    if "cccd" in t or "can_cuoc" in t or "cmnd" in t or "chieu" in t:
        return _CCCD
    return _OTHER


def _validated_segments(raw_segments: list[dict], raw_files: list[dict], file_meta: dict[int, dict],
                        errors: list[str]) -> list[dict]:
    """Chống khoảng trang sai / chồng trang; trang sót thành đoạn `other`."""
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


def _rule_type(text: str) -> str:
    """Fallback khi LLM trả other. Nhận theo TIÊU ĐỀ đầu đoạn."""
    h = _fold(text)
    if not h:
        return _OTHER
    head = h[:700]
    if "tinh trang cho o hop phap" in head or "thong tin ve cho o hop phap" in h:
        return _TO_KHAI
    if "giay chung nhan" in head and ("quyen su dung dat" in h or "quyen so huu nha o" in h):
        return _GCN
    if "ten nguoi su dung dat" in h or "thua dat duoc quyen su dung" in h or "nhung thay doi sau khi cap" in h:
        return _GCN
    if "uy quyen" in head:
        return _AUTHORIZATION
    if "hop dong" in head and any(k in h for k in ("thue nha", "cho thue", "cho muon", "o nho")):
        return _GIAY_TO_CHO_O
    if any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "identity card", "idvnm")):
        return _CCCD
    return _OTHER


def _is_gcn_cover_page(text: str) -> bool:
    h = _fold(text)
    return "nhung thay doi sau khi cap" in h or "can chu y" in h


def _gcn_segment_with_cover_first(segment: dict, pages_by_file: dict[int, dict[int, str]]) -> dict:
    """Trong một đoạn GCN nhiều trang: trang bìa/'VI- Những thay đổi' lên trước, trang I-V theo sau."""
    pages = list(range(segment["pageFrom"], segment["pageTo"] + 1))
    if len(pages) < 2:
        return segment
    texts = pages_by_file.get(segment["fileIndex"]) or {}
    cover = [p for p in pages if _is_gcn_cover_page(texts.get(p, ""))]
    if not cover or len(cover) == len(pages):
        return segment
    return {**segment, "pages": cover + [p for p in pages if p not in cover]}


def build_plan_items(
    raw_files: list[dict],
    segments: list[dict],
    file_meta: dict[int, dict],
    pages_by_file: dict[int, dict[int, str]],
) -> tuple[list[dict], list[dict], list[str]]:
    """Đoạn đã hợp lệ → (attachments, classified, warnings). Thuần tất định, không gọi OCR/LLM."""
    typed: list[tuple[dict, str]] = []
    for segment in segments:
        doc_type = segment["type"]
        # LLM là chính; rule OCR chỉ vá khi LLM trả other/không rõ.
        if doc_type == _OTHER:
            doc_type = _rule_type(_segment_text(segment, pages_by_file))
        typed.append((segment, doc_type))
    typed = _merge_adjacent(typed)

    classified: list[dict] = []
    warnings: list[str] = []
    unknown_pages: list[str] = []
    to_khai_parts: list[tuple[dict, str]] = []
    added_parts: dict[str, list[dict]] = {}

    for segment, doc_type in typed:
        file = raw_files[segment["fileIndex"]]
        base = {"fileIndex": segment["fileIndex"], "fileName": file.get("name"),
                "pageFrom": segment["pageFrom"], "pageTo": segment["pageTo"], "type": doc_type}
        if doc_type == _CCCD:
            classified.append({**base, "target": "skip"})
            continue
        if doc_type in _ADDED_ROWS:
            if doc_type == _GCN:
                segment = _gcn_segment_with_cover_first(segment, pages_by_file)
            added_parts.setdefault(doc_type, []).append(segment)
            classified.append({**base, "target": "add-document-dialog"})
            continue
        if doc_type == _OTHER:
            unknown_pages.append(f"{file.get('name')} trang {segment['pageFrom']}-{segment['pageTo']}")
        to_khai_parts.append((segment, doc_type))
        classified.append({**base, "componentIndex": _TO_KHAI_ROW["componentIndex"]})

    def _file_name(segment: dict) -> str:
        file = raw_files[segment["fileIndex"]]
        return str(file.get("name") or f"file-{segment['fileIndex'] + 1}")

    def _segments(parts: list[dict]) -> list[dict]:
        return [_source_segment(s, file_meta[s["fileIndex"]]["pageCount"]) for s in parts]

    attachments: list[dict] = []
    if to_khai_parts:
        # Tờ khai trước, trang không rõ loại theo sau.
        parts = sorted(to_khai_parts, key=lambda p: (p[1] != _TO_KHAI, p[0]["fileIndex"], p[0]["pageFrom"]))
        first = parts[0][0]
        attachments.append({
            "fileIndex": first["fileIndex"],
            "fileName": _file_name(first),
            "documentName": _TO_KHAI_ROW["documentName"],
            "componentName": _TO_KHAI_ROW["componentName"],
            "componentIndex": _TO_KHAI_ROW["componentIndex"],
            "loaiBan": _TO_KHAI_ROW["loaiBan"],
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": parts[0][1],
            "includedTypes": [doc_type for _, doc_type in parts],
            "sourceSegments": _segments([segment for segment, _ in parts]),
        })

    for doc_type in _ADDED_ORDER:
        parts = sorted(added_parts.get(doc_type) or [], key=lambda s: (s["fileIndex"], s["pageFrom"]))
        if not parts:
            continue
        row = _ADDED_ROWS[doc_type]
        attachments.append({
            "fileIndex": parts[0]["fileIndex"],
            "fileName": _file_name(parts[0]),
            "documentName": row["documentName"],
            "componentName": row["componentName"],
            "loaiBan": row["loaiBan"],
            "quantity": 1,
            "target": "add-document-dialog",
            "needsAddComponent": True,
            "detectedType": doc_type,
            # Modal không tạo được dòng → đính chung vào dòng Tờ khai (phương án dự phòng của ánh xạ).
            "fallbackComponentName": _TO_KHAI_ROW["componentName"],
            "sourceSegments": _segments(parts),
        })

    # --- Cảnh báo ---
    found = {doc_type for _, doc_type in typed}
    if _TO_KHAI not in found:
        warnings.append("Chưa có Tờ khai xác nhận tình trạng chỗ ở hợp pháp (Mẫu số 02) — cần bổ sung.")
    if _GCN not in found and _GIAY_TO_CHO_O not in found:
        warnings.append(
            "Chưa thấy Giấy chứng nhận hoặc giấy tờ chứng minh chỗ ở hợp pháp — cần nộp kèm qua nút Thêm giấy tờ."
        )
    if unknown_pages:
        warnings.append(
            "Không xác định được loại giấy tờ, đã đính chung dòng Tờ khai (cán bộ kiểm tra lại): "
            + "; ".join(unknown_pages)
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
        max_tokens=max(800, min(4000, page_total * 180)),
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
    pages_by_file: dict[int, dict[int, str]] = {}
    llm_docs: list[dict] = []
    for file_index, file in enumerate(raw_files):
        text = str((ocr_by_index.get(file_index) or {}).get("text") or "")
        page_count = _pdf_page_count(file)
        pages, boundaries = _split_ocr_pages(text, page_count)
        page_count = max(page_count, max(pages, default=1))
        file_meta[file_index] = {"pageCount": page_count, "pageBoundariesAvailable": boundaries}
        pages_by_file[file_index] = pages
        if text.strip():
            llm_docs.append({
                "fileIndex": file_index, "pageCount": page_count, "pageBoundariesAvailable": boundaries,
                "pages": [{"pageNumber": p, "ocrText": _truncate(t)} for p, t in sorted(pages.items())],
            })

    t1 = time.monotonic()
    raw_segments: list[dict] = []
    if llm_docs:
        try:
            raw_segments = await _classify_with_llm(llm_docs)
        except Exception as e:  # noqa: BLE001
            errors.append(f"attachment_agent: {e}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    segments = _validated_segments(raw_segments, raw_files, file_meta, errors)
    attachments, classified, warnings = build_plan_items(raw_files, segments, file_meta, pages_by_file)
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
        },
        "ocr_text": join_ocr_documents(indexed_ocr),
        "llm_output": {"documents": raw_segments},
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
