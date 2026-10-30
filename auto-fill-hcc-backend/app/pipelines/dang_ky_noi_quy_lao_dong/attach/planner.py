"""Đính kèm bước "Thành phần hồ sơ" cho "Đăng ký nội quy lao động của doanh nghiệp" (2.001955, cổng DVCQG — Angular
mat-table, engine FE `attp-row` + modal "Thêm giấy tờ").

ENGINE TÁCH/GỘP (như bao_cao_to_chuc_dai_hoi_hoi_cap_tinh): OCR per-file có header "Trang n/m" → LLM gán KHOẢNG TRANG
+ loại cho từng đoạn → hậu xử lý tất định → MỖI giấy một file riêng vào đúng dòng (dòng attp-row nhận nhiều file);
chỉ cắt trang (`sourceSegments`) khi một file chứa nhiều giấy, không ghép các file khác nhau lại.

Bảng 4 dòng cố định (đều "1 Bản chính"), theo ảnh ánh xạ thành phần hồ sơ:
  1. "Nội quy lao động"                 ← Quyết định ban hành + toàn văn Nội quy lao động (mỗi giấy một file).
  2. "Văn bản góp ý của tổ chức đại diện người lao động tại cơ sở" ← Biên bản hội nghị đối thoại / văn bản góp ý.
  3. "Các văn bản của người sử dụng lao động có quy định liên quan đến kỷ luật lao động và trách nhiệm vật chất (nếu
     có)" ← quy chế riêng; hồ sơ không có thì để trống (không phải lỗi thiếu file).
  4. "Văn bản đề nghị đăng ký nội quy lao động." (cổng tích sẵn) ← công văn đề nghị, khớp 1:1.
Giấy ủy quyền không có dòng → tạo dòng 5 bằng "+ Thêm giấy tờ" (`add-document-dialog`, 1 Bản chính); modal không tạo
được thì FE ĐÍNH CHUNG vào dòng 4 (`fallbackComponentName`). CCCD / Giấy chứng nhận ĐKDN / giấy chưa rõ loại không có
dòng → đính chung dòng 1, không bỏ file nào.
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
from app.pipelines.dang_ky_noi_quy_lao_dong.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DE_NGHI = "van_ban_de_nghi"
_QUYET_DINH = "quyet_dinh_ban_hanh"
_NOI_QUY = "noi_quy_lao_dong"
_GOP_Y = "gop_y_dai_dien"
_KY_LUAT = "quy_dinh_ky_luat"
_UY_QUYEN = "giay_uy_quyen"
_DKDN = "dang_ky_doanh_nghiep"
_CCCD = "cccd"
_OTHER = "other"
# Thứ tự các file trong cùng một dòng: Quyết định đứng trước toàn văn Nội quy.
_ORDER = [_DE_NGHI, _QUYET_DINH, _NOI_QUY, _GOP_Y, _KY_LUAT, _UY_QUYEN]
_ALLOWED = set(_ORDER) | {_DKDN, _CCCD, _OTHER}
_EXTRA_NAMES = {_DKDN: "Giấy chứng nhận đăng ký doanh nghiệp", _CCCD: "Căn cước công dân"}

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold); componentIndex = STT dòng (1-based). Dòng 1
# "Nội quy lao động" nằm trong chữ dòng 4 → FE định vị theo componentIndex trước.
_ROWS: dict[int, dict[str, str]] = {
    1: {"componentName": "Nội quy lao động",
        "documentName": "Quyết định ban hành và Nội quy lao động"},
    2: {"componentName": "Văn bản góp ý của tổ chức đại diện người lao động tại cơ sở",
        "documentName": "Văn bản góp ý của tổ chức đại diện NLĐ"},
    3: {"componentName": "quy định liên quan đến kỷ luật lao động và trách nhiệm vật chất",
        "documentName": "Văn bản về kỷ luật lao động, trách nhiệm vật chất"},
    4: {"componentName": "Văn bản đề nghị đăng ký nội quy lao động",
        "documentName": "Văn bản đề nghị đăng ký nội quy lao động"},
}
_ROUTE: dict[str, int] = {_QUYET_DINH: 1, _NOI_QUY: 1, _GOP_Y: 2, _KY_LUAT: 3, _DE_NGHI: 4}
# Dòng tạo bằng "+ Thêm giấy tờ": componentName là chữ gõ vào ô autocomplete "Giấy tờ" của modal.
_ROW_UY_QUYEN = {"componentName": "Giấy ủy quyền", "documentName": "Giấy ủy quyền", "loaiBan": "Bản chính"}
_ID_CARD_MARKERS = ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "citizen identity")


def _normalize_type(value: str) -> str:
    t = re.sub(r"[\s-]+", "_", _fold(value or ""))
    if t in _ALLOWED:
        return t
    if "uy_quyen" in t:
        return _UY_QUYEN
    if "quyet_dinh" in t:
        return _QUYET_DINH
    if "ky_luat" in t or "vat_chat" in t:
        return _KY_LUAT
    if "noi_quy" in t:
        return _DE_NGHI if "de_nghi" in t or "dang_ky" in t else _NOI_QUY
    if "de_nghi" in t or "cong_van" in t:
        return _DE_NGHI
    if "gop_y" in t or "doi_thoai" in t or "cong_doan" in t or "bien_ban" in t:
        return _GOP_Y
    if "doanh_nghiep" in t:
        return _DKDN
    if "cccd" in t or "can_cuoc" in t or "cmnd" in t:
        return _CCCD
    return _OTHER


def _rule_type(text: str) -> str:
    """Fallback khi LLM trả other. Nhận theo TIÊU ĐỀ đầu đoạn — công văn, quyết định, biên bản đều nhắc "Nội quy lao
    động" trong thân."""
    h = _fold(text)
    if not h:
        return _OTHER
    head = h[:600]
    if "giay uy quyen" in head or "ben duoc uy quyen" in h:
        return _UY_QUYEN
    if "noi quy lao dong" in head and "ve viec ban hanh" not in head and (
        "kem theo quyet dinh" in head or "chuong i" in head or "nhung quy dinh chung" in head
    ):
        return _NOI_QUY
    if "quyet dinh" in head and "ban hanh" in head and "noi quy" in head:
        return _QUYET_DINH
    if "dang ky noi quy" in head and "kinh gui" in h:
        return _DE_NGHI
    if ("bien ban" in head or "gop y" in head) and ("doi thoai" in h or "cong doan" in h or "noi quy" in h):
        return _GOP_Y
    if "giay chung nhan dang ky doanh nghiep" in head:
        return _DKDN
    if any(m in h for m in _ID_CARD_MARKERS):
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


def _inherit_continuations(typed: list[tuple[dict, str]],
                           pages_by_file: dict[int, dict[int, str]]) -> list[tuple[dict, str]]:
    """Đoạn `other` không có quốc hiệu là trang nối tiếp của giấy tờ ngay trước (kể cả sang file sau)."""
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
    extra_pages: list[str] = []
    by_row: dict[int, list[tuple[dict, str]]] = {}
    uy_quyen: list[tuple[dict, str]] = []

    for segment, doc_type in typed:
        file = raw_files[segment["fileIndex"]]
        base = {"fileIndex": segment["fileIndex"], "fileName": file.get("name"),
                "pageFrom": segment["pageFrom"], "pageTo": segment["pageTo"], "type": doc_type}
        if doc_type == _UY_QUYEN:
            uy_quyen.append((segment, doc_type))
            classified.append({**base, "target": "add-document-dialog"})
            continue
        # GCN ĐKDN, CCCD, giấy chưa rõ loại không có dòng riêng → đính chung dòng 1, không bỏ file nào.
        row_idx = _ROUTE.get(doc_type, 1)
        if doc_type not in _ROUTE:
            extra_pages.append(f"{file.get('name')} trang {segment['pageFrom']}-{segment['pageTo']}")
        by_row.setdefault(row_idx, []).append((segment, doc_type))
        classified.append({**base, "componentIndex": row_idx})

    order = {t: i for i, t in enumerate(_ORDER)}
    attachments: list[dict] = []
    used_names: set[str] = set()

    def merged_item(parts: list[tuple[dict, str]], default_name: str) -> dict:
        parts = sorted(parts, key=lambda p: (order.get(p[1], 99), p[0]["fileIndex"], p[0]["pageFrom"]))
        first_segment = parts[0][0]
        base_name = (first_segment.get("documentName") if len(parts) == 1 else "") or default_name
        first_file = raw_files[first_segment["fileIndex"]]
        return {
            "fileIndex": first_segment["fileIndex"],
            "fileName": str(first_file.get("name") or f"file-{first_segment['fileIndex'] + 1}"),
            "documentName": _unique_name(base_name.replace("/", "-"), used_names, default_name),
            "loaiBan": "Bản chính",
            "detectedType": parts[0][1],
            "includedTypes": [doc_type for _, doc_type in parts],
            "sourceSegments": [
                _source_segment(segment, file_meta[segment["fileIndex"]]["pageCount"]) for segment, _ in parts
            ],
        }

    def segment_item(segment: dict, doc_type: str, default_name: str) -> dict:
        """Một giấy = một file riêng (dòng attp-row nhận nhiều file); chỉ cắt trang khi giấy chiếm một phần file."""
        file = raw_files[segment["fileIndex"]]
        source = _source_segment(segment, file_meta[segment["fileIndex"]]["pageCount"])
        item = {
            "fileIndex": segment["fileIndex"],
            "fileName": str(file.get("name") or f"file-{segment['fileIndex'] + 1}"),
            "documentName": _unique_name(
                (segment.get("documentName") or default_name).replace("/", "-"), used_names, default_name
            ),
            "loaiBan": "Bản chính",
            "detectedType": doc_type,
        }
        if source["pageIndexes"] is not None:
            item["sourceSegments"] = [source]
        return item

    for row_idx in sorted(by_row):
        row = _ROWS[row_idx]
        parts = sorted(by_row[row_idx], key=lambda p: (order.get(p[1], 99), p[0]["fileIndex"], p[0]["pageFrom"]))
        for segment, doc_type in parts:
            attachments.append({
                **segment_item(segment, doc_type, row["documentName"] if doc_type in _ROUTE else
                               _EXTRA_NAMES.get(doc_type, "Giấy tờ kèm theo")),
                "componentName": row["componentName"],
                "componentIndex": row_idx,
                "target": "attp-row",
                "needsAddComponent": False,
            })
    if uy_quyen:
        attachments.append({
            **merged_item(uy_quyen, _ROW_UY_QUYEN["documentName"]),
            "componentName": _ROW_UY_QUYEN["componentName"],
            "loaiBan": _ROW_UY_QUYEN["loaiBan"],
            "quantity": 1,
            "target": "add-document-dialog",
            "needsAddComponent": True,
            # Modal không tạo được dòng → đính chung vào dòng Văn bản đề nghị.
            "fallbackComponentName": _ROWS[4]["componentName"],
        })

    # --- Cảnh báo ---
    if 4 not in by_row:
        warnings.append("Chưa có Văn bản đề nghị đăng ký nội quy lao động (dòng 4) — cần bổ sung.")
    if _NOI_QUY not in found:
        warnings.append("Chưa có toàn văn Nội quy lao động (dòng 1) — cần bổ sung.")
    if _QUYET_DINH not in found:
        warnings.append("Không thấy Quyết định ban hành Nội quy lao động — dòng 1 chỉ có toàn văn Nội quy, kiểm tra lại.")
    if 2 not in by_row:
        warnings.append("Chưa có văn bản góp ý / biên bản đối thoại của tổ chức đại diện người lao động (dòng 2) — bắt "
                        "buộc với nơi có tổ chức đại diện người lao động tại cơ sở.")
    if extra_pages:
        warnings.append("Giấy tờ không có dòng riêng (GCN đăng ký doanh nghiệp, CCCD, giấy chưa rõ loại) đã đính chung "
                        "dòng 1 Nội quy lao động: " + "; ".join(extra_pages))
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
        max_tokens=max(1200, min(6000, page_total * 120)),
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
