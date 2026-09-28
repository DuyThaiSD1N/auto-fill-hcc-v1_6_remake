"""Đính kèm bước "Thành phần hồ sơ" cho "Thủ tục chia, tách; sáp nhập; hợp nhất hội (cấp tỉnh)" (1.012945, cổng
DVCQG — Angular mat-table, engine FE `attp-row`).

ENGINE TÁCH/GỘP (như dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua): OCR per-file có header
"Trang n/m" → LLM gán KHOẢNG TRANG + loại cho từng đoạn → hậu xử lý tất định → GOM các đoạn cùng dòng thành MỘT
file gộp (`sourceSegments`). FE tự trích/gộp trang thành một PDF cho mỗi dòng.

Bảng 7 dòng (thứ tự trên cổng; đều "Bản chính", dòng 6 chọn radio "1 Bản chính"):
  [1] Văn bản xác nhận nơi dự kiến đặt trụ sở    ← van_ban_tru_so; THIẾU thì tạm đính các TRANG Đề án nói về trụ sở
  [2] Đơn đề nghị (Mẫu số 10)                     ← don_de_nghi
  [3] Đề án                                        ← de_an (toàn văn)
  [4] Nghị quyết của ban chấp hành                ← nghi_quyet + đính kèm chung bien_ban_hop
  [5] Danh sách ban chấp hành và ban kiểm tra     ← danh_sach_bch + (danh sách riêng không có BKT) TRANG Đề án có
                                                     bảng Ban kiểm tra; không có danh sách riêng → trang Đề án có
                                                     bảng BCH/BKT
  [6] Sơ yếu lý lịch, phiếu LLTP số 1             ← so_yeu_ly_lich + ly_lich_tu_phap
  [7] Dự thảo điều lệ                              ← du_thao_dieu_le
CCCD không có dòng → bỏ qua (chỉ dùng ở bước điền thông tin).
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.attach import prompt
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.attach.planner import (
    _PAGE_HEADER_RE,
    _coerce_int,
    _fallback_segment,
    _merge_adjacent,
    _pdf_page_count,
    _truncate,
    _unique_name,
)
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_TRU_SO = "van_ban_tru_so"
_DON = "don_de_nghi"
_DE_AN = "de_an"
_NGHI_QUYET = "nghi_quyet"
_BIEN_BAN = "bien_ban_hop"
_DS_BCH = "danh_sach_bch"
_SYLL = "so_yeu_ly_lich"
_LLTP = "ly_lich_tu_phap"
_DIEU_LE = "du_thao_dieu_le"
_CCCD = "cccd"
_OTHER = "other"
_ALLOWED = {_TRU_SO, _DON, _DE_AN, _NGHI_QUYET, _BIEN_BAN, _DS_BCH, _SYLL, _LLTP, _DIEU_LE, _CCCD, _OTHER}

# componentName = ĐOẠN TEXT ĐẶC TRƯNG DUY NHẤT của dòng (FE khớp substring fold); componentIndex = STT dòng
# (1-based) làm gợi ý. `types` = loại giấy tờ vào dòng, theo THỨ TỰ trong file gộp.
_ROWS: dict[int, dict[str, Any]] = {
    1: {
        "componentName": "Văn bản xác nhận nơi dự kiến đặt trụ sở của hội",
        "documentName": "Văn bản xác nhận nơi dự kiến đặt trụ sở",
        "loaiBan": "Bản chính",
        "types": [_TRU_SO],
    },
    2: {
        "componentName": "Đơn đề nghị chia, tách; sáp nhập; hợp nhất hội",
        "documentName": "Đơn đề nghị chia, tách, sáp nhập, hợp nhất hội",
        "loaiBan": "Bản chính",
        "types": [_DON],
    },
    3: {
        "componentName": "Đề án chia, tách; sáp nhập; hợp nhất hội",
        "documentName": "Đề án chia, tách, sáp nhập, hợp nhất hội",
        "loaiBan": "Bản chính",
        "types": [_DE_AN],
    },
    4: {
        "componentName": "Nghị quyết của ban chấp hành hội về việc chia, tách",
        "documentName": "Nghị quyết của ban chấp hành hội",
        "loaiBan": "Bản chính",
        "types": [_NGHI_QUYET, _BIEN_BAN],
    },
    5: {
        "componentName": "Danh sách ban chấp hành và ban kiểm tra của hội",
        "documentName": "Danh sách ban chấp hành và ban kiểm tra",
        "loaiBan": "Bản chính",
        "types": [_DS_BCH],
    },
    6: {
        "componentName": "Sơ yếu lý lịch cá nhân, phiếu lý lịch tư pháp số 1",
        "documentName": "Sơ yếu lý lịch, phiếu lý lịch tư pháp số 1",
        "loaiBan": "Bản chính",
        "types": [_SYLL, _LLTP],
    },
    7: {
        "componentName": "Dự thảo điều lệ hội mới",
        "documentName": "Dự thảo điều lệ hội",
        "loaiBan": "Bản chính",
        "types": [_DIEU_LE],
    },
}
# Loại CHÍNH của từng dòng; loại khác cùng dòng / trang Đề án đính thêm là "đính kèm chung".
_MAIN_TYPES = {row["types"][0]: idx for idx, row in _ROWS.items()}


def _split_ocr_pages(text: str, expected_count: int) -> tuple[dict[int, str], bool]:
    """{số trang: văn bản ĐỦ} + có header trang hay không. Bản cắt ngắn chỉ dùng cho prompt LLM; dò trang Đề án
    nói về trụ sở / Ban kiểm tra cần văn bản đủ (mục trụ sở hay nằm cuối trang)."""
    value = str(text or "")
    matches = list(_PAGE_HEADER_RE.finditer(value))
    if not matches:
        return {1: value.strip()}, expected_count == 1
    pages_by_number: dict[int, str] = {}
    declared_total = expected_count
    for pos, m in enumerate(matches):
        declared_total = max(declared_total, int(m.group(2)))
        end = matches[pos + 1].start() if pos + 1 < len(matches) else len(value)
        pages_by_number[int(m.group(1))] = value[m.end():end].strip()
    return {p: pages_by_number.get(p, "") for p in range(1, max(1, declared_total) + 1)}, True


def _normalize_type(value: str) -> str:
    t = re.sub(r"[\s-]+", "_", _fold(value or ""))
    if t in _ALLOWED:
        return t
    if "tu_phap" in t or "lltp" in t:
        return _LLTP
    if "so_yeu" in t or "mau_17" in t:
        return _SYLL
    if "dieu_le" in t:
        return _DIEU_LE
    if "tru_so" in t:
        return _TRU_SO
    if "bien_ban" in t:
        return _BIEN_BAN
    if "nghi_quyet" in t:
        return _NGHI_QUYET
    if "danh_sach" in t or "ban_chap_hanh" in t or "ban_kiem_tra" in t:
        return _DS_BCH
    if "de_an" in t:
        return _DE_AN
    if "don" in t or "mau_10" in t:
        return _DON
    if "cccd" in t or "can_cuoc" in t or "cmnd" in t:
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


def _segment_text(segment: dict, pages_by_file: dict[int, dict[int, str]]) -> str:
    pages = pages_by_file.get(segment["fileIndex"]) or {}
    return "\n".join(pages.get(p, "") for p in range(segment["pageFrom"], segment["pageTo"] + 1)).strip()


def _rule_type(text: str) -> str:
    """Fallback khi LLM trả other. Nhận theo TIÊU ĐỀ đầu đoạn: Đơn / Đề án / Nghị quyết có chung phần "Căn cứ" và
    nhắc tên nhau trong thân văn bản."""
    h = _fold(text)
    if not h:
        return _OTHER
    head = h[:700]
    if "ly lich tu phap" in head or "tinh trang an tich" in h:
        return _LLTP
    if "so yeu ly lich" in head:
        return _SYLL
    if "dieu le" in head and ("chuong i" in h or "dieu 1." in h):
        return _DIEU_LE
    if "bien ban hop" in head or ("bien ban" in head and "thanh phan" in h):
        return _BIEN_BAN
    if "nghi quyet" in head and ("quyet nghi" in h or "dieu 1" in h):
        return _NGHI_QUYET
    if "de an" in head:
        return _DE_AN
    if "don xin" in head or "don de nghi" in head:
        return _DON
    if "danh sach ban chap hanh" in head or "danh sach ban kiem tra" in head:
        return _DS_BCH
    if "tru so" in h and any(m in h for m in ("xac nhan", "cho muon", "cho thue", "dong y")):
        return _TRU_SO
    if any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc")):
        return _CCCD
    return _OTHER


def _mentions_tru_so(page: str) -> bool:
    return "tru so" in _fold(page)


def _has_bkt_table(page: str) -> bool:
    h = _fold(page)
    return "ban kiem tra" in h and ("ho va ten" in h or "truong ban" in h)


def _has_bch_table(page: str) -> bool:
    h = _fold(page)
    return ("ban chap hanh" in h and ("ho va ten" in h or "chuc danh" in h)) or _has_bkt_table(page)


def _page_subset(segments: list[dict], pages_by_file: dict[int, dict[int, str]], predicate) -> list[dict]:
    """Các trang (trong những đoạn cho trước) thoả điều kiện → đoạn con mang danh sách trang `pages`."""
    subsets: list[dict] = []
    for segment in segments:
        pages = pages_by_file.get(segment["fileIndex"]) or {}
        hit = [p for p in range(segment["pageFrom"], segment["pageTo"] + 1) if predicate(pages.get(p, ""))]
        if hit:
            subsets.append({**segment, "pages": hit})
    return subsets


def _source_segment(segment: dict, page_count: int) -> dict:
    if segment.get("pages"):
        return {"fileIndex": segment["fileIndex"], "pageIndexes": [p - 1 for p in segment["pages"]]}
    indexes = None
    if segment["pageFrom"] != 1 or segment["pageTo"] != page_count:
        indexes = list(range(segment["pageFrom"] - 1, segment["pageTo"]))
    return {"fileIndex": segment["fileIndex"], "pageIndexes": indexes}


def _row_of(doc_type: str) -> int | None:
    for idx, row in _ROWS.items():
        if doc_type in row["types"]:
            return idx
    return None


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
    found = {doc_type for _, doc_type in typed}

    classified: list[dict] = []
    warnings: list[str] = []
    skipped_pages: list[str] = []
    by_row: dict[int, list[tuple[dict, str]]] = {}

    for segment, doc_type in typed:
        file = raw_files[segment["fileIndex"]]
        base = {"fileIndex": segment["fileIndex"], "fileName": file.get("name"),
                "pageFrom": segment["pageFrom"], "pageTo": segment["pageTo"], "type": doc_type}
        if doc_type == _CCCD:
            classified.append({**base, "target": "skip", "reason": "CCCD không nằm trong thành phần hồ sơ"})
            continue
        row_idx = _row_of(doc_type)
        if row_idx is None:
            skipped_pages.append(f"{file.get('name')} trang {segment['pageFrom']}-{segment['pageTo']}")
            classified.append({**base, "type": _OTHER, "target": "skip"})
            continue
        by_row.setdefault(row_idx, []).append((segment, doc_type))
        classified.append({**base, "componentIndex": row_idx, "shared": _MAIN_TYPES.get(doc_type) != row_idx})

    # --- Trang Đề án đính chung sang dòng 1 (trụ sở) và dòng 5 (BCH/BKT) ---
    de_an_segments = [segment for segment, doc_type in typed if doc_type == _DE_AN]
    temp_tru_so = False
    if _TRU_SO not in found and de_an_segments:
        subsets = _page_subset(de_an_segments, pages_by_file, _mentions_tru_so)
        if subsets:
            temp_tru_so = True
            for subset in subsets:
                by_row.setdefault(1, []).append((subset, _DE_AN))
                classified.append({"fileIndex": subset["fileIndex"],
                                   "fileName": raw_files[subset["fileIndex"]].get("name"),
                                   "pageFrom": subset["pages"][0], "pageTo": subset["pages"][-1],
                                   "pages": subset["pages"], "type": _DE_AN, "componentIndex": 1, "shared": True})

    ds_segments = [segment for segment, doc_type in typed if doc_type == _DS_BCH]
    ds_has_bkt = any(_has_bkt_table(_segment_text(s, pages_by_file)) for s in ds_segments)
    bkt_from_de_an = False
    if de_an_segments and not ds_has_bkt:
        subsets = _page_subset(de_an_segments, pages_by_file, _has_bkt_table if ds_segments else _has_bch_table)
        for subset in subsets:
            bkt_from_de_an = True
            by_row.setdefault(5, []).append((subset, _DE_AN))
            classified.append({"fileIndex": subset["fileIndex"],
                               "fileName": raw_files[subset["fileIndex"]].get("name"),
                               "pageFrom": subset["pages"][0], "pageTo": subset["pages"][-1],
                               "pages": subset["pages"], "type": _DE_AN, "componentIndex": 5, "shared": True})

    attachments: list[dict] = []
    used_names: set[str] = set()
    for row_idx in sorted(by_row):
        row = _ROWS[row_idx]
        order = {t: i for i, t in enumerate(row["types"])}
        parts = sorted(by_row[row_idx], key=lambda p: (order.get(p[1], 99), p[0]["fileIndex"], p[0]["pageFrom"]))
        first_segment = parts[0][0]
        single_main = len(parts) == 1 and parts[0][1] in row["types"]
        base_name = (first_segment.get("documentName") if single_main else "") or row["documentName"]
        document_name = _unique_name(base_name, used_names, row["documentName"])
        first_file = raw_files[first_segment["fileIndex"]]
        attachments.append({
            "fileIndex": first_segment["fileIndex"],
            "fileName": str(first_file.get("name") or f"file-{first_segment['fileIndex'] + 1}"),
            "documentName": document_name,
            "componentName": row["componentName"],
            "componentIndex": row_idx,
            "loaiBan": row["loaiBan"],
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": parts[0][1],
            "includedTypes": [doc_type for _, doc_type in parts],
            # Mỗi dòng = MỘT file gộp: FE trích đúng trang từng đoạn rồi ghép theo thứ tự này.
            "sourceSegments": [
                _source_segment(segment, file_meta[segment["fileIndex"]]["pageCount"]) for segment, _ in parts
            ],
        })

    if skipped_pages:
        warnings.append("Không xác định được loại giấy tờ (bỏ qua, đính thủ công nếu cần): " + "; ".join(skipped_pages))
    if temp_tru_so:
        warnings.append("Hồ sơ chưa có văn bản xác nhận nơi dự kiến đặt trụ sở (dòng 1) — đã TẠM đính các trang Đề "
                        "án nói về trụ sở; cần bổ sung văn bản xác nhận của đơn vị quản lý địa điểm.")
    elif _TRU_SO not in found:
        warnings.append("Không tìm thấy văn bản xác nhận nơi dự kiến đặt trụ sở (dòng 1) — vui lòng đính tay.")
    if _DON not in found:
        warnings.append("Không tìm thấy Đơn đề nghị chia, tách, sáp nhập, hợp nhất hội (dòng 2) — vui lòng đính tay.")
    if _DE_AN not in found:
        warnings.append("Không tìm thấy Đề án (dòng 3) — vui lòng đính tay.")
    if _NGHI_QUYET not in found:
        warnings.append(
            "Không tìm thấy Nghị quyết của ban chấp hành (dòng 4)"
            + (" — đã đính Biên bản họp, kiểm tra lại." if _BIEN_BAN in found else " — vui lòng đính tay.")
        )
    if 5 not in by_row:
        warnings.append("Không tìm thấy Danh sách ban chấp hành và ban kiểm tra (dòng 5) — vui lòng đính tay.")
    elif ds_segments and not ds_has_bkt and not bkt_from_de_an:
        warnings.append("Danh sách ban chấp hành chưa có Ban kiểm tra (dòng 5) — cần bổ sung danh sách Ban kiểm tra.")
    elif bkt_from_de_an and ds_segments:
        warnings.append("Danh sách ban chấp hành không có Ban kiểm tra — đã đính kèm trang Đề án có danh sách Ban "
                        "kiểm tra vào dòng 5.")
    if _SYLL not in found:
        warnings.append("Chưa có Sơ yếu lý lịch (Mẫu số 17) của người dự kiến làm chủ tịch (dòng 6) — cần bổ sung.")
    if _LLTP not in found:
        warnings.append("Chưa có Phiếu lý lịch tư pháp số 1 (dòng 6, bản chính, không quá 06 tháng) — cần bổ sung.")
    if _DIEU_LE not in found:
        warnings.append("Không tìm thấy Dự thảo điều lệ (dòng 7) — vui lòng đính tay.")
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
        max_tokens=max(1200, min(6000, page_total * 180)),
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
            "rows": [{"componentIndex": k, **{n: v for n, v in row.items() if n != "types"}}
                     for k, row in _ROWS.items()],
        },
        "ocr_text": join_ocr_documents(indexed_ocr),
        "llm_output": {"documents": raw_segments},
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
