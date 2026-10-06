"""Đính kèm bước "Thành phần hồ sơ" cho "Xác định lại diện tích đất ở (GCN cấp trước 01/7/2004)" — cổng
DVC Đà Nẵng (Angular mat-table, engine FE `attp-row`).

Bảng 3 dòng (đều "1 Bản chính"):
  [1] Bản gốc Giấy chứng nhận đã cấp.
  [2] Văn bản về việc đại diện … thông qua người đại diện (chỉ khi nộp qua người đại diện).
  [3] Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18.

QUY TẮC ĐÍNH CHUNG (theo ảnh ánh xạ đính kèm của thủ tục): cổng không có dòng riêng cho Bản mô tả ranh
giới, công văn của cơ quan đăng ký đất đai, phiếu đo đạc, CCCD… nên MỌI trang không phải GCN / văn bản đại
diện đều đính CHUNG ở dòng [3] cùng Đơn. File không có trang GCN/đại diện nào → đính NGUYÊN file vào dòng
[3] (giữ cả trang trắng như bản giấy). File có lẫn trang GCN/đại diện → tách: trang GCN sang [1], trang đại
diện sang [2], phần còn lại ghép thành MỘT PDF ở [3] (`sourceSegments`, FE applyMergeGroups tự dựng).

Trang trắng đi theo giấy tờ đứng TRƯỚC nó trong cùng file (mặt sau của GCN vẫn nằm ở dòng GCN).

ENGINE TÁCH TRANG copy từ dinh_chinh_gcn_da_cap_da_nang: OCR per-file có header "Trang n/m" → LLM gán
KHOẢNG TRANG + loại → hậu xử lý tất định (chống chồng/thiếu trang) → gom theo dòng.
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
from app.pipelines.xac_dinh_lai_dien_tich_dat_o_gcn_truoc_2004.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_GCN = "gcn_da_cap"
_DAI_DIEN = "van_ban_dai_dien"
_DON = "don_bien_dong"
_MO_TA = "ban_mo_ta_ranh_gioi"
_CO_QUAN = "van_ban_co_quan"
_DO_DAC = "phieu_do_dac"
_CCCD = "cccd"
_BLANK = "trang_trang"
_OTHER = "other"
_ALLOWED = {_GCN, _DAI_DIEN, _DON, _MO_TA, _CO_QUAN, _DO_DAC, _CCCD, _BLANK, _OTHER}

_ROW_GCN = 1
_ROW_DAI_DIEN = 2
_ROW_DON = 3

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng; componentIndex = STT dòng (1-based) để FE khớp đúng dòng.
_ROWS: dict[int, dict[str, Any]] = {
    _ROW_GCN: {"componentName": "Bản gốc Giấy chứng nhận đã cấp", "componentIndex": 1,
               "documentName": "Bản gốc Giấy chứng nhận đã cấp"},
    _ROW_DAI_DIEN: {"componentName": "Văn bản về việc đại diện", "componentIndex": 2,
                    "documentName": "Văn bản về việc đại diện"},
    _ROW_DON: {"componentName": "Đơn đăng ký biến động đất đai", "componentIndex": 3,
               "documentName": "Đơn đăng ký biến động đất đai"},
}
_ROW_BY_TYPE = {_GCN: _ROW_GCN, _DAI_DIEN: _ROW_DAI_DIEN}  # mọi loại khác → _ROW_DON (đính chung).

# Tên mặc định của đoạn khi LLM không đặt tên — dùng ghép tên tệp đính chung ở dòng Đơn.
_TYPE_NAMES = {
    _DON: "Đơn đăng ký biến động đất đai",
    _MO_TA: "Bản mô tả ranh giới, mốc giới thửa đất",
    _CO_QUAN: "Văn bản của cơ quan đăng ký đất đai",
    _DO_DAC: "Phiếu đo đạc chỉnh lý thửa đất",
    _CCCD: "Căn cước công dân",
    _OTHER: "Giấy tờ khác",
}

_PAGE_HEADER_RE = re.compile(
    r"(?im)^[\t ─-╿-]*(?:trang|page)\s+(\d+)\s*/\s*(\d+)[\t ─-╿-]*$"
)


# ---------------- Segment engine (copy dinh_chinh_gcn_da_cap_da_nang) ----------------
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


def _normalize_type(value: Any) -> str:
    t = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    if t in _ALLOWED:
        return t
    if "uy_quyen" in t or "dai_dien" in t:
        return _DAI_DIEN
    if "do_dac" in t or "trich_do" in t:
        return _DO_DAC
    if "ranh_gioi" in t or "mo_ta" in t:
        return _MO_TA
    if "cong_van" in t or "co_quan" in t or "thong_bao" in t:
        return _CO_QUAN
    if "gcn" in t or "chung_nhan" in t or "so_do" in t:
        return _GCN
    if "don" in t or "bien_dong" in t or "mau_so" in t:
        return _DON
    if "cccd" in t or "can_cuoc" in t or "cmnd" in t:
        return _CCCD
    if "trang" in t or "blank" in t:
        return _BLANK
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


# --- Rule fallback theo OCR (khi LLM không phân loại được đoạn) ---
def _rule_type(text: str) -> str:
    h = _fold(text)
    if len(re.sub(r"[^a-z0-9]", "", h)) < 20:
        return _BLANK
    if "don dang ky bien dong" in h:
        return _DON
    # Công văn trước GCN/ủy quyền: công văn hay NHẮC "đã được cấp Giấy chứng nhận số …".
    if "noi nhan" in h and ("v/v" in h or re.search(r"\bso\s*:\s*\d+", h)):
        return _CO_QUAN
    if "ban mo ta ranh gioi" in h or "moc gioi thua dat" in h:
        return _MO_TA
    if any(m in h for m in ("hop dong uy quyen", "giay uy quyen", "van ban uy quyen", "cu nguoi dai dien")):
        return _DAI_DIEN
    if "so vao so cap giay chung nhan" in h or "nhung thay doi sau khi cap" in h:
        return _GCN
    if "phieu do dac" in h or "trich do" in h:
        return _DO_DAC
    if "can cuoc" in h or "chung minh nhan dan" in h:
        return _CCCD
    return _OTHER


def _resolved_type(segment: dict, text: str) -> str:
    """LLM là chính; rule OCR chỉ vá khi LLM trả other / không có kết quả (đoạn fallback)."""
    doc_type = segment.get("type") or _OTHER
    return _rule_type(text) if doc_type == _OTHER else doc_type


def _rows_for_file(segments: list[dict]) -> list[int]:
    """Dòng đích cho từng đoạn (cùng thứ tự). Trang trắng đi theo đoạn có nội dung đứng TRƯỚC nó
    (thiếu thì theo đoạn đứng SAU) — mặt sau trắng của GCN không bị đẩy sang dòng Đơn."""
    rows: list[int | None] = [
        None if seg["type"] == _BLANK else _ROW_BY_TYPE.get(seg["type"], _ROW_DON) for seg in segments
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
    return [row or _ROW_DON for row in rows]


def _don_group_name(segments: list[dict]) -> str:
    content = [s for s in segments if s["type"] != _BLANK]
    types = {s["type"] for s in content}
    if types == {_DON}:
        return _TYPE_NAMES[_DON]
    if _DON in types:
        return "Đơn đăng ký biến động và giấy tờ kèm theo"
    if len(content) == 1:
        return content[0].get("documentName") or _TYPE_NAMES.get(content[0]["type"], _TYPE_NAMES[_OTHER])
    return "Giấy tờ kèm theo Đơn đăng ký biến động"


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


def build_attachments(
    segments: list[dict],
    raw_files: list[dict],
    file_meta: dict[int, dict],
    page_text_by_file: dict[int, dict[int, str]],
    full_text_by_file: dict[int, str],
) -> tuple[list[dict], list[dict], list[str]]:
    """Gom đoạn đã kiểm tra thành kế hoạch attp-row. Trả (attachments, classified, errors)."""
    resolved: dict[int, list[dict]] = {}
    for segment in segments:
        text = _segment_text(segment, page_text_by_file, full_text_by_file)
        resolved.setdefault(segment["fileIndex"], []).append({**segment, "type": _resolved_type(segment, text)})

    attachments: list[dict] = []
    classified: list[dict] = []
    used_names: set[str] = set()
    for file_index in sorted(resolved):
        file = raw_files[file_index]
        page_count = file_meta[file_index]["pageCount"]
        file_segments = resolved[file_index]
        rows = _rows_for_file(file_segments)
        for seg, row in zip(file_segments, rows):
            classified.append({
                "fileIndex": file_index, "fileName": file.get("name"),
                "pageFrom": seg["pageFrom"], "pageTo": seg["pageTo"],
                "type": seg["type"], "documentName": seg.get("documentName") or _TYPE_NAMES.get(seg["type"], ""),
                "componentIndex": _ROWS[row]["componentIndex"],
            })

        for row in (_ROW_GCN, _ROW_DAI_DIEN, _ROW_DON):
            group = [seg for seg, r in zip(file_segments, rows) if r == row]
            if not group:
                continue
            spec = _ROWS[row]
            base_name = _don_group_name(group) if row == _ROW_DON else spec["documentName"]
            item = {
                "fileIndex": file_index,
                "fileName": str(file.get("name") or f"file-{file_index + 1}"),
                "documentName": _unique_name(base_name, used_names, spec["documentName"]),
                "componentName": spec["componentName"],
                "componentIndex": spec["componentIndex"],
                "loaiBan": "Bản chính",
                "target": "attp-row",
                "needsAddComponent": False,
                "detectedType": next((s["type"] for s in group if s["type"] != _BLANK), group[0]["type"]),
            }
            pages = sorted({p for seg in group for p in range(seg["pageFrom"], seg["pageTo"] + 1)})
            if pages != list(range(1, page_count + 1)):  # chỉ một phần file → FE tách theo trang.
                item["sourceSegments"] = [{"fileIndex": file_index, "pageIndexes": [p - 1 for p in pages]}]
            attachments.append(item)

    errors: list[str] = []
    all_types = {c["type"] for c in classified}
    if attachments and _GCN not in all_types:
        errors.append(
            "Hồ sơ chưa có bản scan Giấy chứng nhận đã cấp (dòng 1 'Bản gốc Giấy chứng nhận đã cấp'). Bổ "
            "sung bản scan hoặc dùng nút 'Lấy giấy tờ từ kho' trước khi nộp."
        )
    if attachments and _DON not in all_types:
        errors.append(
            "Không nhận ra Đơn đăng ký biến động đất đai trong hồ sơ — các giấy tờ vẫn được đính chung ở dòng "
            "3, cán bộ kiểm tra lại đã có Đơn chưa."
        )
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
