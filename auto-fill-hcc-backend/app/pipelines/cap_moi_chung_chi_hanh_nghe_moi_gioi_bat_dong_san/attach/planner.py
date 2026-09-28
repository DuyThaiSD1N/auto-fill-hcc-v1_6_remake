"""Đính kèm bước "Thành phần hồ sơ" cho "Cấp mới chứng chỉ hành nghề môi giới bất động sản" (1.012906, Angular
mat-table, engine FE `attp-row`).

ENGINE TÁCH/GỘP (như bao_cao_to_chuc_dai_hoi_hoi_cap_tinh): OCR per-file có header "Trang n/m" → LLM gán KHOẢNG TRANG
+ loại cho từng đoạn → hậu xử lý tất định → GOM các đoạn cùng dòng thành MỘT file gộp (`sourceSegments`). Hồ sơ hay
là một PDF gộp Đơn (trang 1) + CCCD 2 mặt (trang 2) → mỗi trang về đúng dòng của nó.

Bảng 6 dòng:
  1. Bằng tốt nghiệp THPT trở lên (Bản sao)          4. Chứng chỉ do nước ngoài cấp + bản dịch (Bản sao)
  2. CCCD / thẻ căn cước / hộ chiếu (Bản sao)        5. GCN hoàn thành khóa học môi giới BĐS (Bản sao)
  3. Đơn đăng ký dự thi có dán ảnh 4x6 (Bản chính)  6. 02 ảnh 4x6 + 02 phong bì dán tem (Bản chính)
Không có ảnh rời → dòng 6 đính CHUNG trang đơn (ảnh dán trên đơn). Không có chứng chỉ nước ngoài → gửi `untickRows`
để FE bỏ tick dòng 4 (chỉ áp dụng người nước ngoài / người có chứng chỉ nước ngoài). Chứng chỉ cũ trong nước, giấy tờ
của tổ chức không có dòng → bỏ qua (chỉ dùng ở bước điền thông tin).
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.cap_moi_chung_chi_hanh_nghe_moi_gioi_bat_dong_san.attach import prompt
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
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_IMAGE_TYPES = {"image/jpeg", "image/png", "image/jpg", "image/webp"}

_DON = "don_dang_ky"
_CCCD = "cccd"
_BANG = "bang_tot_nghiep"
_GCN = "gcn_khoa_hoc"
_NUOC_NGOAI = "chung_chi_nuoc_ngoai"
_ANH = "anh_the"
_CC_CU = "chung_chi_cu"
_TO_CHUC = "giay_to_to_chuc"
_OTHER = "other"
_ALLOWED = {_DON, _CCCD, _BANG, _GCN, _NUOC_NGOAI, _ANH, _CC_CU, _TO_CHUC, _OTHER}
# Loại không có dòng trên bảng → bỏ qua.
_NO_ROW = {_CC_CU, _TO_CHUC}

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold); componentIndex = STT dòng (1-based).
# ⚠ Dòng 3 cũng chứa "ảnh mầu cỡ 4x6cm chụp trong thời gian 06 tháng" → dòng 6 khớp theo cụm "phong bì".
_ROWS: dict[int, dict[str, str]] = {
    1: {"componentName": "Bản sao chứng thực bằng tốt nghiệp từ trung học phổ thông hoặc tương đương trở lên",
        "documentName": "Bằng tốt nghiệp", "loaiBan": "Bản sao"},
    2: {"componentName": "Bản sao chứng thực Giấy chứng minh nhân dân hoặc Căn cước công dân hoặc Thẻ căn cước",
        "documentName": "Căn cước công dân", "loaiBan": "Bản sao"},
    3: {"componentName": "Đơn đăng ký dự thi có dán ảnh",
        "documentName": "Đơn đăng ký dự thi sát hạch", "loaiBan": "Bản chính"},
    4: {"componentName": "Bản sao và bản dịch có chứng thực chứng chỉ do nước ngoài cấp",
        "documentName": "Chứng chỉ do nước ngoài cấp và bản dịch", "loaiBan": "Bản sao"},
    5: {"componentName": "Giấy chứng nhận đã hoàn thành khóa học về đào tạo bồi dưỡng kiến thức hành nghề môi giới",
        "documentName": "Giấy chứng nhận hoàn thành khóa học", "loaiBan": "Bản sao"},
    6: {"componentName": "phong bì có dán tem ghi rõ họ tên, số điện thoại, địa chỉ người nhận",
        "documentName": "Ảnh 4x6", "loaiBan": "Bản chính"},
}
_ROUTE = {_BANG: 1, _CCCD: 2, _DON: 3, _NUOC_NGOAI: 4, _GCN: 5, _ANH: 6}
# Thứ tự ghép các loại trong CÙNG một file gộp.
_ORDER = [_DON, _ANH, _CCCD, _BANG, _GCN, _NUOC_NGOAI]

_REQUIRED = [
    (1, "Bản sao chứng thực bằng tốt nghiệp THPT hoặc tương đương trở lên"),
    (2, "Bản sao chứng thực CCCD / thẻ căn cước / hộ chiếu"),
    (3, "Đơn đăng ký dự thi có dán ảnh 4x6 (Phụ lục XXI NĐ 96/2024/NĐ-CP)"),
    (5, "Bản sao chứng thực Giấy chứng nhận hoàn thành khóa học đào tạo, bồi dưỡng kiến thức hành nghề môi giới BĐS"),
]

# Ảnh chân dung chụp rời: OCR gần như không ra chữ.
_PHOTO_MAX_TEXT = 40


def _normalize_type(value: str) -> str:
    t = re.sub(r"[\s-]+", "_", _fold(value or ""))
    if t in _ALLOWED:
        return t
    if "nuoc_ngoai" in t:
        return _NUOC_NGOAI
    if "khoa_hoc" in t or "hoan_thanh" in t:
        return _GCN
    if "tot_nghiep" in t or "van_bang" in t or "bang_" in t:
        return _BANG
    if "don" in t:
        return _DON
    if "cccd" in t or "can_cuoc" in t or "cmnd" in t or "chieu" in t:
        return _CCCD
    if "anh" in t or "phong_bi" in t:
        return _ANH
    if "chung_chi" in t:
        return _CC_CU
    if "doanh_nghiep" in t or "to_chuc" in t or "gioi_thieu" in t:
        return _TO_CHUC
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
    """Fallback khi LLM trả other. Nhận theo TIÊU ĐỀ đầu đoạn — trang đơn cũng ghi số CCCD, "Thẻ căn cước"."""
    h = _fold(text)
    if not h:
        return _OTHER
    head = h[:500]
    if "don" in head and ("du thi" in head or "chung chi hanh nghe" in head or "moi gioi" in head):
        return _DON
    if "hoan thanh khoa" in h and "moi gioi" in h:
        return _GCN
    if "chung chi hanh nghe moi gioi" in head:
        return _CC_CU
    if "bang tot nghiep" in head or "tot nghiep trung hoc pho thong" in head or "bang cu nhan" in head:
        return _BANG
    if "dang ky doanh nghiep" in head or "giay gioi thieu" in head:
        return _TO_CHUC
    if any(m in h for m in ("can cuoc", "chung minh nhan dan", "identity card", "idvnm")):
        return _CCCD
    return _OTHER


def _inherit_continuations(typed: list[tuple[dict, str]],
                           pages_by_file: dict[int, dict[int, str]]) -> list[tuple[dict, str]]:
    """Đoạn `other` không có quốc hiệu, CÙNG file, ngay sau một giấy tờ → trang nối tiếp (mặt sau văn bằng, trang 2
    của đơn)."""
    out: list[tuple[dict, str]] = []
    prev: tuple[dict, str] | None = None
    for segment, doc_type in typed:
        if (doc_type == _OTHER and prev and prev[1] not in (_OTHER, _ANH)
                and prev[0]["fileIndex"] == segment["fileIndex"]):
            head = _fold(_segment_text(segment, pages_by_file))[:500]
            if "cong hoa xa hoi chu nghia" not in head:
                doc_type = prev[1]
        out.append((segment, doc_type))
        prev = (segment, doc_type)
    return out


def _is_photo(file: dict, text: str) -> bool:
    return str(file.get("type") or "").lower() in _IMAGE_TYPES and len(re.sub(r"\s+", "", text)) <= _PHOTO_MAX_TEXT


def _certified(text: str) -> bool:
    h = _fold(text)
    return any(m in h for m in ("chung thuc", "sao y", "ban sao dung voi ban chinh"))


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
        text = _segment_text(segment, pages_by_file)
        # LLM là chính; rule OCR chỉ vá khi LLM trả other/không rõ.
        if doc_type == _OTHER:
            doc_type = _rule_type(text)
        if doc_type == _OTHER and _is_photo(raw_files[segment["fileIndex"]], text):
            doc_type = _ANH
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

    # --- Không có ảnh rời: dòng 6 đính chung trang đơn (ảnh 4x6 dán trên đơn) ---
    anh_from_don = False
    if 6 not in by_row and 3 in by_row:
        anh_from_don = True
        by_row[6] = [(segment, _DON) for segment, _ in by_row[3]]
        for segment, _ in by_row[3]:
            classified.append({"fileIndex": segment["fileIndex"],
                               "fileName": raw_files[segment["fileIndex"]].get("name"),
                               "pageFrom": segment["pageFrom"], "pageTo": segment["pageTo"], "type": _DON,
                               "componentIndex": 6, "shared": True})

    order = {t: i for i, t in enumerate(_ORDER)}
    attachments: list[dict] = []
    used_names: set[str] = set()
    for row_idx in sorted(by_row):
        row = _ROWS[row_idx]
        parts = sorted(by_row[row_idx], key=lambda p: (order.get(p[1], 99), p[0]["fileIndex"], p[0]["pageFrom"]))
        first_segment = parts[0][0]
        single = len(parts) == 1 and not (anh_from_don and row_idx == 6)
        base_name = (first_segment.get("documentName") if single else "") or row["documentName"]
        if anh_from_don and row_idx == 6:
            base_name = "Ảnh 4x6 dán trên đơn"
        document_name = _unique_name(base_name.replace("/", "-"), used_names, row["documentName"])
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

    # Dòng 4 chỉ dành cho người có chứng chỉ do nước ngoài cấp — cổng tick sẵn thì bỏ tick.
    if attachments and 4 not in by_row:
        attachments[0]["untickRows"] = [_ROWS[4]["componentName"]]

    # --- Cảnh báo ---
    for row_idx, label in _REQUIRED:
        if row_idx not in by_row:
            warnings.append(f"Chưa có {label} (dòng {row_idx}) — cần bổ sung.")
    don_text = " ".join(_fold(_segment_text(s, pages_by_file))[:600] for s, t in typed if t == _DON)
    if "cap lai" in don_text:
        warnings.append("Đơn trong hồ sơ là ĐƠN XIN CẤP LẠI chứng chỉ — dòng 3 yêu cầu Đơn đăng ký dự thi sát hạch "
                        "(Phụ lục XXI NĐ 96/2024/NĐ-CP); đã đính tạm vào dòng 3, kiểm tra lại thủ tục.")
    if anh_from_don:
        warnings.append("Hồ sơ không có ảnh 4x6 chụp rời — dòng 6 đính chung trang đơn (ảnh dán trên đơn); còn thiếu "
                        "02 ảnh 4x6 và 02 phong bì có dán tem ghi rõ họ tên, số điện thoại, địa chỉ người nhận.")
    elif 6 not in by_row:
        warnings.append("Chưa có 02 ảnh 4x6 và 02 phong bì có dán tem (dòng 6) — cần bổ sung.")
    cccd_segments = [s for s, t in typed if t == _CCCD]
    if cccd_segments and not any(_certified(_segment_text(s, pages_by_file)) for s in cccd_segments):
        warnings.append("Bản CCCD trong hồ sơ chưa thấy dấu chứng thực — dòng 2 yêu cầu bản sao chứng thực (hoặc bản "
                        "sao kèm bản chính để đối chiếu).")
    if _CC_CU in found:
        warnings.append("Hồ sơ có chứng chỉ hành nghề môi giới BĐS đã cấp — bảng thành phần không có dòng riêng, dùng "
                        "'Thêm giấy tờ' nếu cần nộp kèm.")
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
