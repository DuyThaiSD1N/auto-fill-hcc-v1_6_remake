"""Đính kèm bước "Thành phần hồ sơ" cho "Thông báo kết quả đại hội và phê duyệt đổi tên hội, phê duyệt điều lệ hội
(cấp tỉnh)" (1.012943, cổng DVCQG — Angular mat-table, engine FE `attp-row`).

ENGINE TÁCH/GỘP (như bao_cao_to_chuc_dai_hoi_hoi_cap_tinh): OCR per-file có header "Trang n/m" → LLM gán KHOẢNG TRANG
+ loại cho từng đoạn → hậu xử lý tất định → GOM các đoạn cùng dòng thành MỘT file gộp (`sourceSegments`, theo thứ
tự trang trong hồ sơ). Đều "Bản chính".

Bảng 7 dòng:
  1 văn bản báo cáo kết quả đại hội (Tờ trình) + Danh sách BCH "kèm theo tờ trình"
  2 đơn đề nghị đổi tên hội (chỉ khi đại hội đổi tên)
  3 biên bản đại hội, biên bản bầu cử, biên bản họp BCH bầu chức danh + các danh sách BCH / BTV / CT-PCT / BKT
  4 dự thảo Điều lệ (chỉ khi sửa đổi Điều lệ)
  5 Nghị quyết đại hội
  6 Chương trình hoạt động; hồ sơ không có văn bản riêng thì đính tạm Báo cáo tổng kết (phần phương hướng) kèm báo
    cáo kinh phí, phụ lục thi đua
  7 Sơ yếu lý lịch + Phiếu LLTP số 1 của Chủ tịch (chỉ khi Chủ tịch không phải nhân sự dự kiến đã báo cáo)
Dòng 2, 4, 7 là dòng điều kiện — hồ sơ không có giấy tờ thì gửi `untickRows` để FE bỏ tick (cổng tick sẵn dòng 7).
CCCD không có dòng → bỏ qua (chỉ dùng ở bước điền thông tin).
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
    _unique_name,
)
from app.pipelines.thong_bao_ket_qua_dai_hoi_phe_duyet_dieu_le_hoi_cap_tinh.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_BAO_CAO = "bao_cao_ket_qua"
_DOI_TEN = "don_doi_ten"
_BIEN_BAN = "bien_ban"
_DANH_SACH = "danh_sach"
_DIEU_LE = "du_thao_dieu_le"
_NQ = "nghi_quyet_dai_hoi"
_CT_HD = "chuong_trinh_hoat_dong"
_TONG_KET = "bao_cao_tong_ket"
_SYLL = "so_yeu_ly_lich"
_LLTP = "ly_lich_tu_phap"
_CCCD = "cccd"
_OTHER = "other"
_ALLOWED = {_BAO_CAO, _DOI_TEN, _BIEN_BAN, _DANH_SACH, _DIEU_LE, _NQ, _CT_HD, _TONG_KET, _SYLL, _LLTP, _CCCD, _OTHER}

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold); componentIndex = STT dòng (1-based).
_ROWS: dict[int, dict[str, str]] = {
    1: {"componentName": "Văn bản báo cáo kết quả đại hội",
        "documentName": "Văn bản báo cáo kết quả đại hội"},
    2: {"componentName": "kèm theo đơn đề nghị đổi tên hội",
        "documentName": "Đơn đề nghị đổi tên hội"},
    3: {"componentName": "Biên bản đại hội; biên bản bầu ban thường vụ",
        "documentName": "Biên bản đại hội, biên bản bầu cử và danh sách"},
    4: {"componentName": "Dự thảo điều lệ hoặc dự thảo Điều lệ sửa đổi",
        "documentName": "Dự thảo điều lệ"},
    5: {"componentName": "Nghị quyết đại hội",
        "documentName": "Nghị quyết đại hội"},
    6: {"componentName": "Chương trình hoạt động của hội",
        "documentName": "Chương trình hoạt động của hội"},
    7: {"componentName": "hội bổ sung sơ yếu lý lịch cá nhân",
        "documentName": "Sơ yếu lý lịch, phiếu lý lịch tư pháp số 1"},
}

_ROUTE: dict[str, int] = {
    _BAO_CAO: 1,
    _DOI_TEN: 2,
    _BIEN_BAN: 3,
    _DANH_SACH: 3,
    _DIEU_LE: 4,
    _NQ: 5,
    _CT_HD: 6,
    _TONG_KET: 6,
    _SYLL: 7,
    _LLTP: 7,
}

_REQUIRED: list[tuple[int, str]] = [
    (1, "Văn bản báo cáo kết quả đại hội"),
    (3, "Biên bản đại hội, biên bản bầu Ban thường vụ, Ban kiểm tra, Chủ tịch, Phó Chủ tịch (có danh sách kèm theo)"),
    (5, "Nghị quyết đại hội"),
    (6, "Chương trình hoạt động của hội"),
]
_CONDITIONAL_ROWS = (2, 4, 7)


def _normalize_type(value: str) -> str:
    t = re.sub(r"[\s-]+", "_", _fold(value or ""))
    if t in _ALLOWED:
        return t
    if "tu_phap" in t or "lltp" in t:
        return _LLTP
    if "so_yeu" in t:
        return _SYLL
    if "dieu_le" in t:
        return _DIEU_LE
    if "nghi_quyet" in t:
        return _NQ
    if "doi_ten" in t:
        return _DOI_TEN
    if "bien_ban" in t:
        return _BIEN_BAN
    if "danh_sach" in t:
        return _DANH_SACH
    if "chuong_trinh" in t:
        return _CT_HD
    if "tong_ket" in t or "chinh_tri" in t or "kinh_phi" in t or "tai_chinh" in t or "thi_dua" in t:
        return _TONG_KET
    if "bao_cao" in t or "to_trinh" in t or "ket_qua" in t:
        return _BAO_CAO
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


def _rule_type(text: str) -> str:
    """Fallback khi LLM trả other. Nhận theo TIÊU ĐỀ đầu đoạn — các văn bản nhắc tên nhau trong thân bài."""
    h = _fold(text)
    if not h:
        return _OTHER
    head = h[:500]
    if "ly lich tu phap" in head or "tinh trang an tich" in h:
        return _LLTP
    if "so yeu ly lich" in head:
        return _SYLL
    if "dieu le" in head and ("chuong i" in h or "dieu 1." in h):
        return _DIEU_LE
    if "don" in head and "doi ten" in head:
        return _DOI_TEN
    if "bao cao tong ket" in head or "bao cao chinh tri" in head or "bao cao kinh phi" in head \
            or "thong ke ket qua thi dua" in head:
        return _TONG_KET
    if "chuong trinh hoat dong" in head or "chuong trinh hanh dong" in head:
        return _CT_HD
    if "nghi quyet" in head and ("quyet nghi" in h or "dai hoi" in head):
        return _NQ
    if "bien ban" in head:
        return _BIEN_BAN
    if "danh sach" in head:
        return _DANH_SACH
    if "to trinh" in head or ("ket qua dai hoi" in head and "kinh gui" in h):
        return _BAO_CAO
    if any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc")):
        return _CCCD
    return _OTHER


def _inherit_continuations(typed: list[tuple[dict, str]],
                           pages_by_file: dict[int, dict[int, str]]) -> list[tuple[dict, str]]:
    """Đoạn `other` không có quốc hiệu là trang nối tiếp của giấy tờ ngay trước (vd trang bảng danh sách tràn)."""
    out: list[tuple[dict, str]] = []
    prev_type = None
    for segment, doc_type in typed:
        if doc_type == _OTHER and prev_type not in (None, _OTHER, _CCCD):
            head = _fold(_segment_text(segment, pages_by_file))[:500]
            if "cong hoa xa hoi chu nghia" not in head:
                doc_type = prev_type
        out.append((segment, doc_type))
        prev_type = doc_type
    return out


def _attached_to_report(text: str) -> bool:
    """Danh sách ghi "(Kèm theo tờ trình số ...)" → đính chung dòng văn bản báo cáo."""
    h = _fold(text)[:800]
    return "kem theo to trinh" in h or "kem theo van ban" in h or "kem theo bao cao" in h


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
    typed = _merge_adjacent(_inherit_continuations(typed, pages_by_file))
    found = {doc_type for _, doc_type in typed}
    has_report = _BAO_CAO in found

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
        row_idx = _ROUTE.get(doc_type)
        if doc_type == _DANH_SACH and has_report and _attached_to_report(_segment_text(segment, pages_by_file)):
            row_idx = 1
        if row_idx is None:
            skipped_pages.append(f"{file.get('name')} trang {segment['pageFrom']}-{segment['pageTo']}")
            classified.append({**base, "target": "skip"})
            continue
        by_row.setdefault(row_idx, []).append((segment, doc_type))
        classified.append({**base, "componentIndex": row_idx})

    attachments: list[dict] = []
    used_names: set[str] = set()
    for row_idx in sorted(by_row):
        row = _ROWS[row_idx]
        # Ghép theo đúng thứ tự trang trong hồ sơ (biên bản → danh sách kèm theo → biên bản họp BCH ...).
        parts = sorted(by_row[row_idx], key=lambda p: (p[0]["fileIndex"], p[0]["pageFrom"]))
        first_segment = parts[0][0]
        base_name = (first_segment.get("documentName") if len(parts) == 1 else "") or row["documentName"]
        document_name = _unique_name(base_name.replace("/", "-"), used_names, row["documentName"])
        first_file = raw_files[first_segment["fileIndex"]]
        attachments.append({
            "fileIndex": first_segment["fileIndex"],
            "fileName": str(first_file.get("name") or f"file-{first_segment['fileIndex'] + 1}"),
            "documentName": document_name,
            "componentName": row["componentName"],
            "componentIndex": row_idx,
            "loaiBan": "Bản chính",
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": parts[0][1],
            "includedTypes": [doc_type for _, doc_type in parts],
            # Mỗi dòng = MỘT file gộp: FE trích đúng trang từng đoạn rồi ghép theo thứ tự này.
            "sourceSegments": [
                _source_segment(segment, file_meta[segment["fileIndex"]]["pageCount"]) for segment, _ in parts
            ],
        })

    # Dòng điều kiện cổng có thể tick sẵn (dòng 7) mà hồ sơ không có → bỏ tick.
    untick = [_ROWS[idx]["componentName"] for idx in _CONDITIONAL_ROWS if idx not in by_row]
    if attachments and untick:
        attachments[0]["untickRows"] = untick

    # --- Cảnh báo ---
    for row_idx, label in _REQUIRED:
        if row_idx not in by_row:
            warnings.append(f"Chưa có {label} (dòng {row_idx}) — cần bổ sung.")
    if 6 in by_row and _CT_HD not in found:
        warnings.append("Hồ sơ không có Chương trình hoạt động riêng — dòng 6 đính tạm Báo cáo tổng kết (phần phương "
                        "hướng nhiệm vụ); nên bổ sung Chương trình hoạt động của hội.")
    bien_ban_text = " ".join(
        _fold(_segment_text(segment, pages_by_file))[:400] for segment, t in typed if t == _BIEN_BAN
    )
    if 3 in by_row and "bien ban dai hoi" not in bien_ban_text:
        warnings.append("Dòng 3 chưa có Biên bản đại hội (chỉ có biên bản bầu cử / họp Ban chấp hành, danh sách) — "
                        "cần bổ sung nếu cơ quan tiếp nhận yêu cầu.")
    if _DIEU_LE not in found:
        report_text = " ".join(
            _fold(_segment_text(segment, pages_by_file)) for segment, t in typed if t == _BAO_CAO
        )
        if "dieu le" not in report_text:
            warnings.append("Hồ sơ không có dự thảo Điều lệ và văn bản báo cáo chưa nêu việc phê duyệt / tiếp tục thực "
                            "hiện điều lệ hiện hành — đề nghị hội bổ sung nội dung này vào văn bản báo cáo.")
    if 7 not in by_row:
        warnings.append("Không có sơ yếu lý lịch, phiếu lý lịch tư pháp số 1 của Chủ tịch — đã bỏ tick dòng 7; chỉ "
                        "cần nộp khi Chủ tịch không phải nhân sự dự kiến đã báo cáo cơ quan nhà nước.")
    elif _SYLL in found and _LLTP not in found:
        warnings.append("Chưa có Phiếu lý lịch tư pháp số 1 của Chủ tịch hội (dòng 7) — cần bổ sung, trừ khi người đó "
                        "là cán bộ, công chức, viên chức (kể cả đã nghỉ hưu) được cơ quan có thẩm quyền đồng ý.")
    if skipped_pages:
        warnings.append("Không xác định được loại giấy tờ (bỏ qua, đính thủ công nếu cần): " + "; ".join(skipped_pages))
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
            "rows": [{"componentIndex": k, **row} for k, row in _ROWS.items()],
        },
        "ocr_text": join_ocr_documents(indexed_ocr),
        "llm_output": {"documents": raw_segments},
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
