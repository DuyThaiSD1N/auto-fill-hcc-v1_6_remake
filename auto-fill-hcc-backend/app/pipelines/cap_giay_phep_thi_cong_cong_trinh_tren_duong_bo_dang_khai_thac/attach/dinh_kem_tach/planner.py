"""Đính kèm bước "Thành phần hồ sơ" cho "Cấp giấy phép thi công công trình trên đường bộ đang khai thác" (1.013061,
Angular mat-table, engine FE `attp-row`).

ENGINE TÁCH ĐOẠN (cùng khuôn 1.012906): OCR per-file có header "Trang n/m" → MỘT lượt LLM gán KHOẢNG TRANG + loại cho
từng đoạn → hậu xử lý tất định → MỖI ĐOẠN (một thành phần hồ sơ liền trang trong một tệp) là một item riêng của dòng;
đoạn chỉ là một phần tệp thì gửi `sourceSegments` để FE cắt trang. Hồ sơ hay là MỘT PDF gộp cả bộ (đơn → hồ sơ khoảng
cách DPC → báo cáo thẩm tra → BPTC-BĐGT + hoàn trả → bản vẽ thiết kế thi công) → mỗi bộ về đúng dòng của nó, KHÔNG
đính nguyên tệp gộp vào một dòng (ảnh ánh xạ của người dùng).

Bảng 5 dòng (đúng thứ tự trên cổng, loại bản đều "Bản chính"):
  1. Đơn đề nghị cấp phép thi công (mẫu Đơn_TT1.013061)
  2. Thông tin khoảng cách tới dải phân cách giữa — chỉ công trình trong phạm vi DPC giữa
  3. Báo cáo thẩm tra thiết kế + tính toán khả năng chịu lực — chỉ công trình lắp vào cầu, hầm, kết cấu phức tạp
  4. Bản vẽ hoàn trả + thuyết minh, bản vẽ biện pháp tổ chức thi công, bảo đảm giao thông
  5. Bản vẽ thiết kế thi công (đính MỘT lần ở đây, dòng 2 / 3 chỉ nhận phần "ngoài bản vẽ thiết kế thi công")
Dòng 2 / 3 không có giấy → `untickRows` để FE bỏ tick. CCCD, giấy tờ khác (văn bản chấp thuận, quyết định phê duyệt,
ủy quyền), đoạn chưa rõ loại không có dòng riêng → mỗi đoạn một tệp đính chung dòng 1 (Đơn), kèm cảnh báo. Tệp Word
(bản .docx của đơn) không OCR được → dòng 1.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.attach.dinh_kem_tach.planner import (
    _segment_text,
    _source_segment,
    _split_ocr_pages,
)
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.attach.dinh_kem_tach.planner import (
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

from . import prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON = "don_de_nghi"
_KC_DPC = "khoang_cach_dpc"
_THAM_TRA = "tham_tra_chiu_luc"
_BPTC = "bptc_bdgt_hoan_tra"
_TKTC = "thiet_ke_thi_cong"
_CCCD = "cccd"            # trùng hằng _CCCD của _merge_adjacent → hai đoạn CCCD liền nhau không bị gộp.
_KHAC = "giay_to_khac"
_OTHER = "other"
_ALLOWED = {_DON, _KC_DPC, _THAM_TRA, _BPTC, _TKTC, _CCCD, _KHAC, _OTHER}
# Loại không có dòng riêng (CCCD, giấy tờ khác, chưa rõ) → đính chung dòng Đơn.
_FALLBACK_ROW = 1

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold); componentIndex = STT dòng (1-based).
# ⚠ Dòng 2 và 3 đều chứa "ngoài Bản vẽ thiết kế thi công" → dòng 5 khớp theo cụm "... có các thông tin về".
_ROWS: dict[int, dict[str, str]] = {
    1: {"componentName": "Đơn đề nghị cấp phép thi công công trình trên đường bộ đang khai thác",
        "documentName": "Đơn đề nghị cấp phép thi công", "loaiBan": "Bản chính"},
    2: {"componentName": "Đối với công trình đề nghị cấp giấy phép thi công trong phạm vi dải phân cách giữa",
        "documentName": "Khoảng cách dải phân cách giữa", "loaiBan": "Bản chính"},
    3: {"componentName": "Đối với công trình đề nghị cấp giấy phép thi công lắp đặt vào cầu, hầm",
        "documentName": "Báo cáo thẩm tra, tính toán chịu lực", "loaiBan": "Bản chính"},
    4: {"componentName": "Bản vẽ thiết kế hoàn trả công trình đường bộ bị ảnh hưởng",
        "documentName": "Biện pháp thi công, BĐGT, hoàn trả", "loaiBan": "Bản chính"},
    5: {"componentName": "Bản vẽ thiết kế thi công có các thông tin về",
        "documentName": "Bản vẽ thiết kế thi công", "loaiBan": "Bản chính"},
}
_ROUTE = {_DON: 1, _KC_DPC: 2, _THAM_TRA: 3, _BPTC: 4, _TKTC: 5}
# Dòng chỉ áp dụng cho một số loại công trình: không có giấy thì bỏ tick.
_OPTIONAL_ROWS = (2, 3)
# Thứ tự các item trong CÙNG một dòng (dòng Đơn: đơn trước, giấy đi kèm sau).
_ORDER = [_DON, _KC_DPC, _THAM_TRA, _BPTC, _TKTC, _CCCD, _KHAC, _OTHER]

_REQUIRED = [
    (1, "Đơn đề nghị cấp phép thi công công trình trên đường bộ đang khai thác"),
    (4, "Bản vẽ thiết kế hoàn trả + thuyết minh, bản vẽ biện pháp tổ chức thi công, bảo đảm giao thông"),
    (5, "Bản vẽ thiết kế thi công (vị trí, lý trình, khoảng cách, bộ phận đường bộ phải đào, khoan)"),
]
_OPTIONAL_LABELS = {
    2: "thông tin khoảng cách tới dải phân cách giữa (chỉ công trình trong phạm vi dải phân cách giữa)",
    3: "báo cáo thẩm tra thiết kế và tính toán khả năng chịu lực (chỉ công trình lắp vào cầu, hầm, kết cấu phức tạp)",
}

# Khung tên bản vẽ: "Số hiệu BV DPC-01" / "HT-01" / "TCGT-01" / "TC-01".
_DRAWING_RE = re.compile(r"so hieu bv\W{0,5}(dpc|tcgt|ht|tc)\s*-?\s*\d")
_DRAWING_TYPES = {"dpc": _KC_DPC, "tcgt": _BPTC, "ht": _BPTC, "tc": _TKTC}
_WORD_EXT_RE = re.compile(r"\.(docx?|odt|rtf)$", re.I)


def _normalize_type(value: str) -> str:
    t = re.sub(r"[\s-]+", "_", _fold(value or ""))
    if t in _ALLOWED:
        return t
    if "don" in t.split("_"):
        return _DON
    if "dai_phan_cach" in t or "khoang_cach" in t or "dpc" in t:
        return _KC_DPC
    if "tham_tra" in t or "chiu_luc" in t:
        return _THAM_TRA
    if "bptc" in t or "bdgt" in t or "hoan_tra" in t or "bien_phap" in t or "giao_thong" in t:
        return _BPTC
    if "thiet_ke" in t or "ban_ve" in t or "tktc" in t:
        return _TKTC
    if "cccd" in t or "can_cuoc" in t or "cmnd" in t or "chieu" in t:
        return _CCCD
    if "khac" in t or "chap_thuan" in t or "quyet_dinh" in t or "uy_quyen" in t or "doanh_nghiep" in t:
        return _KHAC
    return _OTHER


def _rule_type(text: str) -> str:
    """Fallback khi LLM trả other / lỗi. Nhận theo TIÊU ĐỀ đầu đoạn và khung tên bản vẽ — thân Đơn, báo cáo thẩm tra
    nhắc tên các thành phần khác nên không dò cả trang."""
    h = _fold(text)
    if not h:
        return _OTHER
    head = h[:700]
    if "don de nghi cap phep thi cong" in head:
        return _DON
    drawing = _DRAWING_RE.search(h)
    if drawing:
        return _DRAWING_TYPES[drawing.group(1)]
    # Đơn trang 2 nhắc "Báo cáo kết quả thẩm tra thiết kế số …" → phải có cả "chịu lực" của tiêu đề báo cáo.
    if "tham tra" in head and "chiu luc" in head:
        return _THAM_TRA
    if any(m in head for m in ("ho so thiet ke ban ve thi cong", "danh muc ho so ban ve thiet ke thi cong",
                               "thuyet minh thiet ke ban ve thi cong")):
        return _TKTC
    if "thong tin khoang cach" in head or "thong tin ve khoang cach" in head:
        return _KC_DPC
    # Báo cáo thẩm tra có mục "Biện pháp tổ chức thi công, bảo đảm giao thông" → chỉ nhận cụm của TIÊU ĐỀ bộ BPTC.
    if any(m in head for m in ("thuyet minh va ban ve bien phap", "bien phap to chuc thi cong, bien phap bao dam",
                               "so do to chuc thi cong va bao dam giao thong", "thiet ke hoan tra")):
        return _BPTC
    if any(m in h for m in ("can cuoc cong dan", "citizen identity", "idvnm", "chung minh nhan dan")):
        return _CCCD
    # Đơn nhắc "Quyết định phê duyệt", "văn bản chấp thuận vị trí" trong phần căn cứ → chỉ nhận tiêu đề rõ ràng.
    if any(m in head[:300] for m in ("giay uy quyen", "giay chung nhan dang ky doanh nghiep")):
        return _KHAC
    return _OTHER


def _is_word(file: dict) -> bool:
    kind = str(file.get("type") or "").lower()
    return "word" in kind or "opendocument.text" in kind or bool(_WORD_EXT_RE.search(str(file.get("name") or "")))


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
        page_count = file_meta[file_index]["pageCount"]
        items = sorted(by_file[file_index], key=lambda x: (x["pageFrom"], x["pageTo"]))
        if not file_meta[file_index]["pageBoundariesAvailable"]:
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
        start = prev = None
        for page in [p for p in range(1, page_count + 1) if p not in occupied] + [None]:
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
    """Đoạn `other` không có quốc hiệu, CÙNG file, ngay sau một thành phần → trang nối tiếp (trang ký, tờ bản vẽ)."""
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


def untick_optional(attachments: list[dict], rows_with_files: set[int]) -> None:
    """Dòng 2 / 3 chỉ áp dụng cho một số loại công trình — không có tệp thì FE bỏ tick."""
    untick = [_ROWS[r]["componentName"] for r in _OPTIONAL_ROWS if r not in rows_with_files]
    if attachments and untick:
        attachments[0]["untickRows"] = untick


def common_warnings(found_rows: set[int], found_types: set[str], extra_names: list[str]) -> list[str]:
    warnings = [f"Chưa có {label} (dòng {row}) — cần bổ sung." for row, label in _REQUIRED if row not in found_rows]
    warnings += [f"Hồ sơ không có {label} — đã bỏ tick dòng {row}; công trình thuộc diện này thì cần bổ sung."
                 for row, label in _OPTIONAL_LABELS.items() if row not in found_rows]
    if _CCCD in found_types:
        warnings.append("CCCD không có dòng riêng trong thành phần hồ sơ — đã đính chung dòng 1 (Đơn); chỉ dùng để "
                        "điền thông tin người nộp, có thể bỏ nếu không cần.")
    if extra_names:
        warnings.append(f"Giấy tờ không có dòng riêng hoặc chưa rõ loại đã đính chung dòng 1 "
                        f"\"{_ROWS[_FALLBACK_ROW]['componentName']}\": " + "; ".join(extra_names))
    return warnings


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
        if doc_type == _OTHER and _is_word(raw_files[segment["fileIndex"]]):
            doc_type = _DON
        typed.append((segment, doc_type))
    typed = _merge_adjacent(_inherit_continuations(typed, pages_by_file))

    classified: list[dict] = []
    by_row: dict[int, list[tuple[dict, str]]] = {}
    extra_names: list[str] = []
    for segment, doc_type in typed:
        file = raw_files[segment["fileIndex"]]
        row_idx = _ROUTE.get(doc_type, _FALLBACK_ROW)
        entry = {"fileIndex": segment["fileIndex"], "fileName": file.get("name"), "pageFrom": segment["pageFrom"],
                 "pageTo": segment["pageTo"], "type": doc_type, "componentIndex": row_idx}
        if doc_type not in _ROUTE:
            entry["routedTo"] = _FALLBACK_ROW
            if doc_type != _CCCD:
                extra_names.append(f"{file.get('name')} trang {segment['pageFrom']}-{segment['pageTo']}")
        classified.append(entry)
        by_row.setdefault(row_idx, []).append((segment, doc_type))

    order = {t: i for i, t in enumerate(_ORDER)}
    attachments: list[dict] = []
    used_names: set[str] = set()
    for row_idx in sorted(by_row):
        row = _ROWS[row_idx]
        parts = sorted(by_row[row_idx], key=lambda p: (order.get(p[1], 99), p[0]["fileIndex"], p[0]["pageFrom"]))
        for segment, doc_type in parts:
            file = raw_files[segment["fileIndex"]]
            file_name = str(file.get("name") or f"file-{segment['fileIndex'] + 1}")
            if doc_type in _ROUTE:
                base_name = segment.get("documentName") or row["documentName"]
            elif doc_type == _CCCD:
                base_name = segment.get("documentName") or "Căn cước công dân"
            else:
                base_name = segment.get("documentName") or file_name
            page_count = file_meta[segment["fileIndex"]]["pageCount"]
            source = _source_segment(segment, page_count)
            item = {
                "fileIndex": segment["fileIndex"],
                "fileName": file_name,
                "documentName": _unique_name(base_name.replace("/", "-"), used_names, row["documentName"]),
                "componentName": row["componentName"],
                "componentIndex": row_idx,
                "loaiBan": row["loaiBan"],
                "target": "attp-row",
                "needsAddComponent": False,
                "detectedType": doc_type,
                "includedTypes": [doc_type],
            }
            if source["pageIndexes"] is not None and source["pageIndexes"] != list(range(page_count)):
                item["sourceSegments"] = [source]
            attachments.append(item)

    found_rows = {_ROUTE[t] for _, t in typed if t in _ROUTE}
    untick_optional(attachments, set(by_row))
    warnings = common_warnings(found_rows, {t for _, t in typed}, extra_names)
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
        max_tokens=max(800, min(4000, page_total * 120)),
        enable_thinking=settings.agent_reasoning,
    )
    parsed = client.extract_json_block(raw)
    return parsed.get("documents", []) or []


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
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
        except Exception as e:  # noqa: BLE001 — chia giấy hỏng thì đính nguyên tệp như chế độ không tách
            # Import trễ: chế độ không tách import bảng dòng của module này.
            from ..dinh_kem_khong_tach.planner import plan as plan_without_split

            result = await plan_without_split(files, options, session)
            result["errors"] = [f"attachment_agent (tách): {e} — đã đính nguyên tệp như chế độ không tách.",
                                *result.get("errors", [])]
            return result
    llm_ms = int((time.monotonic() - t1) * 1000)

    segments = _validated_segments(raw_segments, raw_files, file_meta, errors)
    attachments, classified, warnings = build_plan_items(raw_files, segments, file_meta, pages_by_file)
    errors.extend(warnings)

    indexed_ocr = [{**res, "name": f"fileIndex={i} · {raw_files[i].get('name')}"} for i, res in ocr_by_index.items()]
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
