"""Đính kèm bước "Thành phần hồ sơ" cho "Đăng ký lại phương tiện ... chuyển quyền sở hữu" (1.004002, Angular
mat-table, engine FE `attp-row`).

ENGINE TÁCH/GỘP (như cap_moi_chung_chi_hanh_nghe_moi_gioi_bat_dong_san): OCR per-file có header "Trang n/m" → LLM gán
KHOẢNG TRANG + loại cho từng đoạn → hậu xử lý tất định → GOM các đoạn cùng dòng thành MỘT file gộp (`sourceSegments`)
theo thứ tự cố định. Hồ sơ hay là MỘT PDF gộp cả bộ giấy tờ.

Bảng 4 dòng (theo ảnh ánh xạ của thủ tục):
  1. Biên lai nộp lệ phí trước bạ                ← Giấy nộp tiền NSNN (Bản chính)
  2. GCN an toàn kỹ thuật và BVMT còn hiệu lực    ← GCN ATKT&BVMT (Bản chính; bản sao chứng thực → Bản sao)
  3. Hợp đồng mua bán / quyết định điều chuyển... ← GỘP: Hợp đồng + lời chứng → Hóa đơn GTGT → GCN đăng ký PT cũ
                                                   (Bản sao — hợp đồng nộp là bản sao chứng thực)
  4. Đơn đề nghị đăng ký lại PT thủy nội địa      ← GỘP: Đơn Mẫu 07 → Đơn xóa đăng ký Mẫu 10 (chỉ có Bản chính)
GCN đăng ký cũ, hóa đơn, Đơn Mẫu 10 không có dòng riêng → đính chung dòng 3 / 4 thay vì "Thêm giấy tờ". Dòng 1, 2 chỉ
áp dụng phương tiện thuộc diện nộp lệ phí trước bạ / đăng kiểm — không có giấy thì gửi `untickRows` bỏ tick. CCCD
chỉ dùng ở bước điền thông tin.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.cap_moi_chung_chi_hanh_nghe_moi_gioi_bat_dong_san.attach.planner import _certified
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
from app.pipelines.dang_ky_lai_phuong_tien_chuyen_quyen_so_huu_khong_doi_co_quan.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON_07 = "don_dang_ky_lai"
_DON_10 = "don_xoa_dang_ky"
_GCN_DK = "gcn_dang_ky"
_GCN_ATKT = "gcn_an_toan_ky_thuat"
_HOP_DONG = "hop_dong"
_HOA_DON = "hoa_don"
_BIEN_LAI = "bien_lai_le_phi"
_CCCD = "cccd"
_OTHER = "other"
_ALLOWED = {_DON_07, _DON_10, _GCN_DK, _GCN_ATKT, _HOP_DONG, _HOA_DON, _BIEN_LAI, _CCCD, _OTHER}
# Loại không có dòng trên bảng → bỏ qua, không cảnh báo.
_NO_ROW = {_CCCD}

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold); componentIndex = STT dòng (1-based).
_ROWS: dict[int, dict[str, str]] = {
    1: {"componentName": "Biên lai nộp lệ phí trước bạ",
        "documentName": "Biên lai nộp lệ phí trước bạ", "loaiBan": "Bản chính"},
    2: {"componentName": "Giấy chứng nhận an toàn kỹ thuật và bảo vệ môi trường của phương tiện",
        "documentName": "Giấy chứng nhận an toàn kỹ thuật và BVMT", "loaiBan": "Bản chính"},
    3: {"componentName": "Hợp đồng mua bán phương tiện hoặc quyết định điều chuyển phương tiện",
        "documentName": "Hợp đồng mua bán, hóa đơn, GCN đăng ký cũ", "loaiBan": "Bản sao"},
    4: {"componentName": "Đơn đề nghị đăng ký lại phương tiện thủy nội địa",
        "documentName": "Đơn đề nghị đăng ký lại, đơn xóa đăng ký", "loaiBan": "Bản chính"},
}
_ROUTE = {_BIEN_LAI: 1, _GCN_ATKT: 2, _HOP_DONG: 3, _HOA_DON: 3, _GCN_DK: 3, _DON_07: 4, _DON_10: 4}
# Thứ tự ghép các loại trong CÙNG một file gộp (theo ảnh ánh xạ).
_ORDER = [_DON_07, _DON_10, _BIEN_LAI, _GCN_ATKT, _HOP_DONG, _HOA_DON, _GCN_DK]
# Dòng chỉ áp dụng cho một số phương tiện → không có giấy thì bỏ tick, chỉ nhắc.
_CONDITIONAL_ROWS = {
    1: "Biên lai nộp lệ phí trước bạ (phương tiện thuộc diện nộp lệ phí trước bạ)",
    2: "Giấy chứng nhận an toàn kỹ thuật và BVMT còn hiệu lực (phương tiện thuộc diện đăng kiểm)",
}
_REQUIRED = [
    (3, "Hợp đồng mua bán / quyết định điều chuyển / giấy tờ cho, tặng, thừa kế phương tiện"),
    (4, "Đơn đề nghị đăng ký lại phương tiện thủy nội địa (Mẫu số 07)"),
]


def _normalize_type(value: str) -> str:
    t = re.sub(r"[\s-]+", "_", _fold(value or ""))
    if t in _ALLOWED:
        return t
    if "xoa" in t:
        return _DON_10
    if "dang_ky_lai" in t or "mau_07" in t or t == "don":
        return _DON_07
    if "an_toan" in t or "dang_kiem" in t or "atkt" in t:
        return _GCN_ATKT
    if "gcn" in t or "chung_nhan_dang_ky" in t:
        return _GCN_DK
    if "hop_dong" in t or "dieu_chuyen" in t or "cong_chung" in t:
        return _HOP_DONG
    if "hoa_don" in t or "vat" in t:
        return _HOA_DON
    if "bien_lai" in t or "le_phi" in t or "ngan_sach" in t or "nop_tien" in t:
        return _BIEN_LAI
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
    """Fallback khi LLM trả other. Nhận theo TIÊU ĐỀ đầu đoạn — Đơn 07, hóa đơn, hợp đồng đều nhắc số đăng ký / GCN
    đăng ký trong thân văn bản."""
    h = _fold(text)
    if not h:
        return _OTHER
    head = h[:600]
    if "dang ky lai phuong tien" in head:
        return _DON_07
    if "xoa dang ky phuong tien" in head:
        return _DON_10
    if "an toan ky thuat va bao ve moi truong" in head:
        return _GCN_ATKT
    if "hop dong mua ban phuong tien" in head or "loi chung cua cong chung vien" in head:
        return _HOP_DONG
    if "hoa don gia tri gia tang" in head or "vat invoice" in head:
        return _HOA_DON
    if "nop tien vao ngan sach" in head or "le phi truoc ba" in h:
        return _BIEN_LAI
    if "chung nhan dang ky phuong tien" in head and "da duoc dang ky phuong tien" in h:
        return _GCN_DK
    if any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "identity card", "idvnm")):
        return _CCCD
    return _OTHER


def _inherit_continuations(typed: list[tuple[dict, str]],
                           pages_by_file: dict[int, dict[int, str]]) -> list[tuple[dict, str]]:
    """Đoạn `other` không có quốc hiệu, CÙNG file, ngay sau một giấy tờ → trang nối tiếp (trang 2-3 hợp đồng, lời
    chứng, trang chứng thực bản sao)."""
    out: list[tuple[dict, str]] = []
    prev: tuple[dict, str] | None = None
    for segment, doc_type in typed:
        if (doc_type == _OTHER and prev and prev[1] not in (_OTHER, _CCCD)
                and prev[0]["fileIndex"] == segment["fileIndex"]):
            head = _fold(_segment_text(segment, pages_by_file))[:500]
            if "cong hoa xa hoi chu nghia" not in head:
                doc_type = prev[1]
        out.append((segment, doc_type))
        prev = (segment, doc_type)
    return out


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

    classified: list[dict] = []
    warnings: list[str] = []
    skipped_pages: list[str] = []
    by_row: dict[int, list[tuple[dict, str]]] = {}

    for segment, doc_type in typed:
        file = raw_files[segment["fileIndex"]]
        base = {"fileIndex": segment["fileIndex"], "fileName": file.get("name"),
                "pageFrom": segment["pageFrom"], "pageTo": segment["pageTo"], "type": doc_type}
        row_idx = _ROUTE.get(doc_type)
        if row_idx is None:
            if doc_type not in _NO_ROW:
                skipped_pages.append(f"{file.get('name')} trang {segment['pageFrom']}-{segment['pageTo']}")
            classified.append({**base, "target": "skip"})
            continue
        by_row.setdefault(row_idx, []).append((segment, doc_type))
        classified.append({**base, "componentIndex": row_idx})

    order = {t: i for i, t in enumerate(_ORDER)}
    attachments: list[dict] = []
    used_names: set[str] = set()
    for row_idx in sorted(by_row):
        row = _ROWS[row_idx]
        parts = sorted(by_row[row_idx], key=lambda p: (order.get(p[1], 99), p[0]["fileIndex"], p[0]["pageFrom"]))
        first_segment = parts[0][0]
        base_name = (first_segment.get("documentName") if len(parts) == 1 else "") or row["documentName"]
        document_name = _unique_name(base_name.replace("/", "-"), used_names, row["documentName"])
        loai_ban = row["loaiBan"]
        if row_idx == 2 and _certified(" ".join(_segment_text(s, pages_by_file) for s, _ in parts)):
            loai_ban = "Bản sao"
        first_file = raw_files[first_segment["fileIndex"]]
        attachments.append({
            "fileIndex": first_segment["fileIndex"],
            "fileName": str(first_file.get("name") or f"file-{first_segment['fileIndex'] + 1}"),
            "documentName": document_name,
            "componentName": row["componentName"],
            "componentIndex": row_idx,
            "loaiBan": loai_ban,
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": parts[0][1],
            "includedTypes": [doc_type for _, doc_type in parts],
            # Mỗi dòng = MỘT file gộp: FE trích đúng trang từng đoạn rồi ghép theo thứ tự này.
            "sourceSegments": [
                _source_segment(segment, file_meta[segment["fileIndex"]]["pageCount"]) for segment, _ in parts
            ],
        })

    # Dòng 1, 2 chỉ áp dụng một số phương tiện — cổng tick sẵn thì bỏ tick khi hồ sơ không có giấy.
    untick = [_ROWS[idx]["componentName"] for idx in _CONDITIONAL_ROWS if idx not in by_row]
    if attachments and untick:
        attachments[0]["untickRows"] = untick

    # --- Cảnh báo ---
    for row_idx, label in _REQUIRED:
        if row_idx not in by_row:
            warnings.append(f"Chưa có {label} (dòng {row_idx}) — cần bổ sung.")
    for row_idx, label in _CONDITIONAL_ROWS.items():
        if row_idx not in by_row:
            warnings.append(f"Hồ sơ không có {label} — đã bỏ tick dòng {row_idx}; bổ sung nếu phương tiện thuộc diện.")
    if _HOP_DONG in found and _GCN_DK not in found:
        warnings.append("Chưa thấy Giấy chứng nhận đăng ký phương tiện cũ trong hồ sơ — cần nộp kèm để đăng ký lại.")
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
            "rows": [{"componentIndex": k, **row} for k, row in _ROWS.items()],
        },
        "ocr_text": join_ocr_documents(indexed_ocr),
        "llm_output": {"documents": raw_segments},
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
