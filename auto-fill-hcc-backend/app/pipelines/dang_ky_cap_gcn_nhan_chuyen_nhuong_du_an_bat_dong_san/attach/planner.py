"""Đính kèm bước "Thành phần hồ sơ" cho "Đăng ký, cấp GCN cho người nhận chuyển nhượng QSDĐ, quyền sở hữu nhà ở,
công trình xây dựng trong dự án bất động sản" — cổng DVC Đà Nẵng (Angular mat-table, engine FE `attp-row`).

Bảng 11 dòng (theo ảnh ánh xạ đính kèm của thủ tục):
  [1] Văn bản nghiệm thu nhà ở/công trình          Bản chính — chỉ khi hồ sơ có.
  [2] Đơn đăng ký biến động Mẫu số 18               Bản chính — mọi bản Đơn (chủ đầu tư ký + bên nhận ký).
  [3] Hợp đồng chuyển nhượng                         Bản chính — Hợp đồng + MỌI văn bản sửa đổi bổ sung.
  [4] Biên bản bàn giao nhà, đất                     Bản chính — biên bản + biên bản điều chỉnh.
  [5] Giấy chứng nhận đã cấp cho chủ đầu tư          Bản sao (chứng thực).
  [6] Văn bản đủ điều kiện được chuyển nhượng        Bản chính — chỉ khi có (đất có hạ tầng cho cá nhân tự xây).
  [7] Chứng từ hoàn thành nghĩa vụ tài chính         Bản sao — hóa đơn, giấy nộp tiền, tờ khai… VÀ mọi giấy tờ
                                                     không có dòng riêng (CCCD, CT07, kết hôn, ĐKDN, ủy quyền…).
  [8] = tên dòng 4 → đính LẠI cùng tệp dòng 4.
  [9] = dòng 1 "(nếu có)" → để trống.   [10] không có tên trên cổng → để trống, không suy đoán.
  [11] = dòng 7 "(nếu có)" → đính LẠI cùng tệp dòng 7 (khi dòng 7 có chứng từ tài chính).

Ô upload mỗi dòng chỉ nhận MỘT tệp → mọi trang của một dòng (kể cả từ nhiều file) ghép thành MỘT PDF qua
`sourceSegments` (FE applyMergeGroups/composeSegmentsToPdf; pageIndexes=None = nguyên file). Dòng chỉ gồm
nguyên một file → đính file gốc, không tách.

FE gom item theo componentName (không theo index) → dòng trùng tên (4/8, 7/11) PHẢI có componentName khác
nhau. Dòng 10 không tên bị FE loại khỏi danh sách dòng nên index của dòng 11 lệch → componentName dòng 11 phải
khớp DUY NHẤT dòng 11 (đuôi "(nếu có)").

ENGINE TÁCH TRANG copy từ dinh_chinh_gcn_da_cap_da_nang: OCR per-file có header "Trang n/m" → LLM gán KHOẢNG
TRANG + loại → hậu xử lý tất định (chống chồng/thiếu trang) → rule OCR vá đoạn LLM không xếp được → gom theo
dòng. Trang trắng đi theo giấy tờ đứng TRƯỚC nó trong cùng file.
"""

import base64
import re
import time
from typing import Any

import fitz

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.dang_ky_cap_gcn_nhan_chuyen_nhuong_du_an_bat_dong_san.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_NGHIEM_THU = "nghiem_thu"
_DON18 = "don_mau_18"
_HOP_DONG = "hop_dong_chuyen_nhuong"
_BAN_GIAO = "bien_ban_ban_giao"
_GCN_CDT = "gcn_chu_dau_tu"
_DU_DIEU_KIEN = "van_ban_du_dieu_kien"
_TAI_CHINH = "chung_tu_tai_chinh"
_NHAN_THAN = "giay_to_nhan_than"
_DKDN = "giay_dkdn"
_UY_QUYEN = "uy_quyen"
_BLANK = "trang_trang"
_OTHER = "other"
_ALLOWED = {_NGHIEM_THU, _DON18, _HOP_DONG, _BAN_GIAO, _GCN_CDT, _DU_DIEU_KIEN, _TAI_CHINH, _NHAN_THAN, _DKDN,
            _UY_QUYEN, _BLANK, _OTHER}
# Nhãn LLM hay trả lệch enum → quy về enum (khớp NGUYÊN nhãn, không dò chuỗi con).
_TYPE_ALIASES = {"cccd": _NHAN_THAN, "can_cuoc": _NHAN_THAN, "ct07": _NHAN_THAN, "ket_hon": _NHAN_THAN,
                 "don_dang_ky_bien_dong": _DON18, "hop_dong": _HOP_DONG, "van_ban_sua_doi_bo_sung": _HOP_DONG,
                 "bien_ban_dieu_chinh": _BAN_GIAO, "gcn": _GCN_CDT, "blank": _BLANK}

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng; componentIndex = STT dòng (1-based).
_ROWS: dict[int, dict[str, Any]] = {
    1: {"componentName": "đã được nghiệm thu đưa vào khai thác", "componentIndex": 1, "loaiBan": "Bản chính",
        "documentName": "Văn bản nghiệm thu nhà ở, công trình"},
    2: {"componentName": "Đơn đăng ký biến động đất đai", "componentIndex": 2, "loaiBan": "Bản chính",
        "documentName": "Đơn đăng ký biến động đất đai Mẫu số 18"},
    3: {"componentName": "Hợp đồng chuyển nhượng quyền sử dụng đất", "componentIndex": 3, "loaiBan": "Bản chính",
        "documentName": "Hợp đồng chuyển nhượng và văn bản sửa đổi bổ sung"},
    4: {"componentName": "Biên bản bàn giao nhà, đất", "componentIndex": 4, "loaiBan": "Bản chính",
        "documentName": "Biên bản bàn giao nhà, đất"},
    5: {"componentName": "Giấy chứng nhận đã cấp cho chủ đầu tư", "componentIndex": 5, "loaiBan": "Bản sao",
        "documentName": "Giấy chứng nhận đã cấp cho chủ đầu tư"},
    6: {"componentName": "đủ điều kiện được chuyển nhượng", "componentIndex": 6, "loaiBan": "Bản chính",
        "documentName": "Văn bản đủ điều kiện chuyển nhượng"},
    7: {"componentName": "hoàn thành nghĩa vụ tài chính", "componentIndex": 7, "loaiBan": "Bản sao",
        "documentName": "Chứng từ nghĩa vụ tài chính và giấy tờ kèm theo"},
    # Dòng trùng tên: componentName khác dòng gốc để FE không gom chung một nhóm.
    8: {"componentName": "Biên bản bàn giao nhà, đất, công trình xây dựng, hạng mục công trình xây dựng.",
        "componentIndex": 8, "loaiBan": "Bản chính"},
    11: {"componentName": "làm phát sinh nghĩa vụ tài chính theo quy định của pháp luật (nếu có)",
         "componentIndex": 11, "loaiBan": "Bản sao"},
}
_ROW_BY_TYPE = {_NGHIEM_THU: 1, _DON18: 2, _HOP_DONG: 3, _BAN_GIAO: 4, _GCN_CDT: 5, _DU_DIEU_KIEN: 6,
                _TAI_CHINH: 7}
_ROW_CHUNG = 7       # Giấy tờ không có dòng riêng → đính chung dòng 7 (theo ảnh ánh xạ).
_DUPLICATES = {4: 8, 7: 11}   # dòng gốc → dòng đính lại cùng tệp.

_TYPE_NAMES = {
    _NGHIEM_THU: "Văn bản nghiệm thu nhà ở, công trình",
    _DON18: "Đơn đăng ký biến động đất đai",
    _HOP_DONG: "Hợp đồng chuyển nhượng",
    _BAN_GIAO: "Biên bản bàn giao nhà, đất",
    _GCN_CDT: "Giấy chứng nhận đã cấp cho chủ đầu tư",
    _DU_DIEU_KIEN: "Văn bản đủ điều kiện chuyển nhượng",
    _TAI_CHINH: "Chứng từ nghĩa vụ tài chính",
    _NHAN_THAN: "Giấy tờ nhân thân",
    _DKDN: "Giấy chứng nhận đăng ký doanh nghiệp",
    _UY_QUYEN: "Văn bản ủy quyền",
    _OTHER: "Giấy tờ kèm theo",
}

_PAGE_HEADER_RE = re.compile(
    r"(?im)^[\t ─-╿-]*(?:trang|page)\s+(\d+)\s*/\s*(\d+)[\t ─-╿-]*$"
)


# ---------------- Segment engine (copy dinh_chinh_gcn_da_cap_da_nang) ----------------
def _truncate(text: str, limit: int = 1500) -> str:
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
    return {"fileIndex": file_index, "pageFrom": page_from, "pageTo": page_to, "type": _OTHER, "documentName": "",
            "fallback": True}


def _normalize_type(value: Any) -> str:
    """Khớp ĐÚNG nhãn enum (hoặc alias nguyên nhãn); nhãn lạ → other để rule OCR vá."""
    t = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    if t in _ALLOWED:
        return t
    return _TYPE_ALIASES.get(t, _OTHER)


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
    for file_index, _file in enumerate(raw_files):
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
        # Trang LLM bỏ sót → MỖI TRANG một đoạn fallback để rule OCR xếp riêng từng trang (một đoạn liền
        # nhiều trang sẽ bị gán trọn theo tiêu đề trang đầu, kéo giấy tờ khác sang sai dòng).
        accepted.extend(_fallback_segment(file_index, p, p) for p in range(1, page_count + 1) if p not in occupied)
        valid.extend(sorted(accepted, key=lambda x: x["pageFrom"]))
    return sorted(valid, key=lambda x: (x["fileIndex"], x["pageFrom"]))


def _segment_text(segment: dict, page_text_by_file: dict[int, dict[int, str]],
                  full_text_by_file: dict[int, str]) -> str:
    pages = page_text_by_file.get(segment["fileIndex"]) or {}
    if not pages:
        return full_text_by_file.get(segment["fileIndex"], "")
    return "\n".join(pages.get(p, "") for p in range(segment["pageFrom"], segment["pageTo"] + 1)).strip()


# --- Rule fallback theo OCR (khi LLM không phân loại được đoạn) ---
# Mỗi loại một bộ cụm TIÊU ĐỀ; cụm xuất hiện SỚM NHẤT trong đoạn thắng. Giấy tờ loại này hay trích dẫn loại
# kia ở phần căn cứ (biên bản bàn giao "căn cứ Hợp đồng mua bán…", văn bản sửa đổi nhắc biên bản bàn giao),
# còn tiêu đề luôn đứng đầu trang → so vị trí thay vì thứ tự ưu tiên cố định.
_RULE_MARKERS: list[tuple[str, tuple[str, ...]]] = [
    (_DON18, ("don dang ky bien dong",)),
    (_HOP_DONG, ("van ban sua doi, bo sung so", "van ban sua doi bo sung so", "phu luc hop dong",
                 "hop dong mua ban", "hop dong chuyen nhuong")),
    (_BAN_GIAO, ("bien ban ban giao", "bien ban dieu chinh bien ban ban giao")),
    (_DKDN, ("giay chung nhan dang ky doanh nghiep",)),
    (_UY_QUYEN, ("hop dong uy quyen", "giay uy quyen", "van ban uy quyen")),
    (_TAI_CHINH, ("hoa don gia tri gia tang", "giay nop tien vao ngan sach", "to khai le phi truoc ba",
                  "to khai thue su dung dat phi nong nghiep", "bang ke thue", "bang tong hop hoa don")),
    (_NHAN_THAN, ("xac nhan thong tin ve cu tru", "giay chung nhan ket hon", "can cuoc cong dan",
                  "chung minh nhan dan")),
    (_NGHIEM_THU, ("bien ban nghiem thu", "nghiem thu hoan thanh")),
    (_DU_DIEU_KIEN, ("du dieu kien duoc chuyen nhuong",)),
    (_GCN_CDT, ("giay chung nhan quyen su dung dat", "so vao so cap giay chung nhan")),
]


def _rule_type(text: str) -> str:
    h = _fold(text)
    best, best_pos = _OTHER, len(h) + 1
    for doc_type, markers in _RULE_MARKERS:
        for marker in markers:
            pos = h.find(marker)
            if 0 <= pos < best_pos:
                best, best_pos = doc_type, pos
    # Xét tiêu đề TRƯỚC: trang chỉ có một dòng tiêu đề ngắn vẫn là giấy tờ, không phải trang trắng.
    if best == _OTHER and len(re.sub(r"[^a-z0-9]", "", h)) < 20:
        return _BLANK
    return best


def _resolved_type(segment: dict, text: str) -> str:
    """LLM là chính; rule OCR chỉ vá khi LLM trả other / không có kết quả (đoạn fallback)."""
    doc_type = segment.get("type") or _OTHER
    return _rule_type(text) if doc_type == _OTHER else doc_type


def _rows_for_file(segments: list[dict]) -> list[int]:
    """Dòng đích cho từng đoạn (cùng thứ tự). Trang trắng đi theo đoạn có nội dung đứng TRƯỚC nó (thiếu thì
    theo đoạn SAU); file toàn trang trắng → dòng đính chung."""
    rows: list[int | None] = [
        None if seg["type"] == _BLANK else _ROW_BY_TYPE.get(seg["type"], _ROW_CHUNG) for seg in segments
    ]
    last = None
    for i, row in enumerate(rows):
        if row is None:
            rows[i] = last
        else:
            last = row
    nxt = None
    for i in range(len(rows) - 1, -1, -1):
        if rows[i] is None:
            rows[i] = nxt
        else:
            nxt = rows[i]
    return [row or _ROW_CHUNG for row in rows]


def _clean_name(value: str) -> str:
    """Tên tài liệu: bỏ ngoặc, "/" (engine đặt tên tệp theo tên này), gọn khoảng trắng, ≤ 50 ký tự."""
    text = re.sub(r"[()\[\]{}]", " ", str(value or "")).replace("/", "-")
    text = re.sub(r"\s+", " ", text).strip(" .-")
    return text[:50].rstrip(" .-")


def _unique_name(base: str, used: set[str], fallback: str) -> str:
    normalized = _clean_name(base) or _clean_name(fallback) or "Tài liệu kèm theo"
    key = _fold(normalized)
    if key not in used:
        used.add(key)
        return normalized
    stem = normalized[:45].strip()
    n = 2
    while True:
        cand = f"{stem} {n}"
        if _fold(cand) not in used:
            used.add(_fold(cand))
            return cand
        n += 1


def _group_name(row: int, group: list[dict]) -> str:
    content = [s for s in group if s["type"] != _BLANK]
    if len(content) == 1:
        seg = content[0]
        return seg.get("documentName") or _TYPE_NAMES.get(seg["type"], _ROWS[row]["documentName"])
    return _ROWS[row]["documentName"]


def build_attachments(
    segments: list[dict],
    raw_files: list[dict],
    file_meta: dict[int, dict],
    page_text_by_file: dict[int, dict[int, str]],
    full_text_by_file: dict[int, str],
) -> tuple[list[dict], list[dict], list[str]]:
    """Gom đoạn đã kiểm tra thành kế hoạch attp-row (mỗi dòng MỘT tệp). Trả (attachments, classified, errors)."""
    resolved: dict[int, list[dict]] = {}
    prev_type: dict[int, str] = {}
    for segment in segments:
        file_index = segment["fileIndex"]
        doc_type = _resolved_type(segment, _segment_text(segment, page_text_by_file, full_text_by_file))
        # Trang fallback không có tiêu đề (trang tiếp theo của hợp đồng…) → thuộc giấy tờ đứng trước nó.
        if segment.get("fallback") and doc_type == _OTHER and file_index in prev_type:
            doc_type = prev_type[file_index]
        if doc_type != _BLANK:
            prev_type[file_index] = doc_type
        resolved.setdefault(file_index, []).append({**segment, "type": doc_type})

    by_row: dict[int, list[dict]] = {}
    classified: list[dict] = []
    for file_index in sorted(resolved):
        file_segments = resolved[file_index]
        for seg, row in zip(file_segments, _rows_for_file(file_segments)):
            by_row.setdefault(row, []).append(seg)
            classified.append({
                "fileIndex": file_index, "fileName": raw_files[file_index].get("name"),
                "pageFrom": seg["pageFrom"], "pageTo": seg["pageTo"], "type": seg["type"],
                "documentName": seg.get("documentName") or _TYPE_NAMES.get(seg["type"], ""),
                "componentIndex": row,
            })

    attachments: list[dict] = []
    used_names: set[str] = set()
    for row in sorted(by_row):
        group = by_row[row]
        spec = _ROWS[row]
        pages_by_file: dict[int, set[int]] = {}
        for seg in group:
            pages_by_file.setdefault(seg["fileIndex"], set()).update(range(seg["pageFrom"], seg["pageTo"] + 1))
        sources = []
        for file_index in sorted(pages_by_file):
            pages = sorted(pages_by_file[file_index])
            full = pages == list(range(1, file_meta[file_index]["pageCount"] + 1))
            sources.append({"fileIndex": file_index, "pageIndexes": None if full else [p - 1 for p in pages]})
        first = sources[0]["fileIndex"]
        item = {
            "fileIndex": first,
            "fileName": str(raw_files[first].get("name") or f"file-{first + 1}"),
            "documentName": _unique_name(_group_name(row, group), used_names, spec["documentName"]),
            "componentName": spec["componentName"],
            "componentIndex": spec["componentIndex"],
            "loaiBan": spec["loaiBan"],
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": next((s["type"] for s in group if s["type"] != _BLANK), group[0]["type"]),
        }
        # Nhiều file hoặc một phần file → FE ghép thành MỘT PDF (ô chỉ nhận một tệp).
        if len(sources) > 1 or sources[0]["pageIndexes"] is not None:
            item["sourceSegments"] = sources
        attachments.append(item)

        dup_row = _DUPLICATES.get(row)
        if dup_row and (row != _ROW_CHUNG or any(s["type"] == _TAI_CHINH for s in group)):
            dup_spec = _ROWS[dup_row]
            attachments.append({
                **item,
                "componentName": dup_spec["componentName"],
                "componentIndex": dup_spec["componentIndex"],
                "loaiBan": dup_spec["loaiBan"],
            })

    errors: list[str] = []
    all_types = {c["type"] for c in classified}
    if attachments:
        missing = [label for t, label in (
            (_DON18, "Đơn đăng ký biến động Mẫu số 18 (dòng 2)"),
            (_HOP_DONG, "Hợp đồng chuyển nhượng (dòng 3)"),
            (_BAN_GIAO, "Biên bản bàn giao (dòng 4, 8)"),
            (_GCN_CDT, "Giấy chứng nhận đã cấp cho chủ đầu tư (dòng 5)"),
        ) if t not in all_types]
        if missing:
            errors.append("Chưa nhận ra trong hồ sơ: " + "; ".join(missing) + ". Kiểm tra lại trước khi nộp.")
        if _TAI_CHINH not in all_types and _ROW_CHUNG in by_row:
            errors.append("Không thấy chứng từ nghĩa vụ tài chính — các giấy tờ không có dòng riêng vẫn được đính "
                          "chung ở dòng 7, cán bộ kiểm tra lại.")
    return attachments, classified, errors


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
    attachments, classified, plan_errors = build_attachments(
        segments, raw_files, file_meta, page_text_by_file, full_text_by_file
    )
    errors.extend(plan_errors)

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
