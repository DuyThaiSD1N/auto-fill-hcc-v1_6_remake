"""Đính kèm bước "Thành phần hồ sơ" cho "Hỗ trợ cơ sở sản xuất bị thiệt hại do dịch bệnh động vật" (1.013997,
cổng ngành Nông nghiệp và Môi trường — Angular mat-table, engine FE `attp-row`).

ENGINE TÁCH/GỘP (như xac_nhan_dieu_kien_dien_tich_nha_o_dang_ky_thuong_tru): OCR per-file có header "Trang n/m"
→ LLM gán KHOẢNG TRANG + loại cho từng đoạn → hậu xử lý tất định → GOM các đoạn thành MỘT file (`sourceSegments`).
Hồ sơ hay là MỘT PDF gộp Đơn đề nghị + nhiều Biên bản tiêu hủy.

Bảng thành phần hồ sơ CHỈ CÓ MỘT dòng (theo ảnh ánh xạ của thủ tục):
  1. Đơn đề nghị hỗ trợ theo từng loại hình cơ sở sản xuất theo Mẫu số 2a, Mẫu số 2b ... NĐ 116/2025/NĐ-CP
Đơn + mọi Biên bản tiêu hủy đính chung vào dòng 1 (Bản chính), Đơn đứng trước, Biên bản giữ thứ tự trang. CCCD chỉ
dùng ở bước điền, không đính kèm. Trang không rõ loại vẫn đính cuối file kèm cảnh báo để cán bộ kiểm tra.
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
from app.pipelines.ho_tro_co_so_san_xuat_thiet_hai_dich_benh_dong_vat.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON = "don_de_nghi"
_BIEN_BAN = "bien_ban_tieu_huy"
_CCCD = "cccd"
_OTHER = "other"
_ALLOWED = {_DON, _BIEN_BAN, _CCCD, _OTHER}

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold).
_DON_ROW = {
    "componentName": "Đơn đề nghị hỗ trợ theo từng loại hình cơ sở sản xuất",
    "componentIndex": 0,
    "documentName": "Đơn đề nghị hỗ trợ thiệt hại do dịch bệnh động vật",
    "loaiBan": "Bản chính",
}
# Thứ tự gộp vào dòng Đơn; CCCD không đính.
_ORDER = [_DON, _BIEN_BAN, _OTHER]


def _normalize_type(value: Any) -> str:
    t = re.sub(r"[\s-]+", "_", _fold(str(value or "")))
    if t in _ALLOWED:
        return t
    if "bien_ban" in t or "tieu_huy" in t:
        return _BIEN_BAN
    if "don" in t or "de_nghi" in t or "mau_2" in t:
        return _DON
    if "cccd" in t or "can_cuoc" in t or "cmnd" in t:
        return _CCCD
    return _OTHER


def _rule_type(text: str) -> str:
    """Fallback khi LLM trả other. Nhận theo TIÊU ĐỀ đầu đoạn."""
    h = _fold(text)
    if not h:
        return _OTHER
    head = h[:700]
    if "don de nghi" in head and ("thiet hai" in head or "dich benh" in head):
        return _DON
    if "bien ban" in head and "tieu huy" in head:
        return _BIEN_BAN
    if "doi tuong tieu huy" in h or "khoi luong tieu huy" in h or "chu ho chan nuoi" in h:
        return _BIEN_BAN
    if any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "identity card", "idvnm")):
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
    unknown_pages: list[str] = []
    parts: list[tuple[dict, str]] = []
    for segment, doc_type in typed:
        file = raw_files[segment["fileIndex"]]
        entry = {"fileIndex": segment["fileIndex"], "fileName": file.get("name"),
                 "pageFrom": segment["pageFrom"], "pageTo": segment["pageTo"], "type": doc_type}
        if doc_type == _CCCD:
            classified.append({**entry, "attached": False})
            continue
        if doc_type == _OTHER:
            unknown_pages.append(f"{file.get('name')} trang {segment['pageFrom']}-{segment['pageTo']}")
        parts.append((segment, doc_type))
        classified.append({**entry, "componentIndex": _DON_ROW["componentIndex"]})

    attachments: list[dict] = []
    if parts:
        parts.sort(key=lambda p: (_ORDER.index(p[1]), p[0]["fileIndex"], p[0]["pageFrom"]))
        first = parts[0][0]
        file = raw_files[first["fileIndex"]]
        attachments.append({
            "fileIndex": first["fileIndex"],
            "fileName": str(file.get("name") or f"file-{first['fileIndex'] + 1}"),
            "documentName": _DON_ROW["documentName"],
            "componentName": _DON_ROW["componentName"],
            "componentIndex": _DON_ROW["componentIndex"],
            "loaiBan": _DON_ROW["loaiBan"],
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": parts[0][1],
            "includedTypes": [doc_type for _, doc_type in parts],
            "sourceSegments": [
                _source_segment(s, file_meta[s["fileIndex"]]["pageCount"]) for s, _ in parts
            ],
        })

    warnings: list[str] = []
    found = {doc_type for _, doc_type in typed}
    if _DON not in found:
        warnings.append(
            "Chưa có Đơn đề nghị hỗ trợ thiệt hại (Mẫu số 2a/2b) — cần bổ sung; đã đính Biên bản vào dòng Đơn."
        )
    if _BIEN_BAN not in found:
        warnings.append("Chưa thấy Biên bản tiêu hủy động vật — cần bổ sung.")
    if unknown_pages:
        warnings.append(
            "Không xác định được loại giấy tờ, đã đính chung dòng Đơn đề nghị (cán bộ kiểm tra lại): "
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
