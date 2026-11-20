"""Đính kèm bước "Thành phần hồ sơ" cho "Cấp, cấp lại Giấy phép liên vận giữa Việt Nam, Lào và Campuchia" (1.002877,
Angular mat-table, engine FE `attp-row`) — chế độ TÁCH giấy tờ.

OCR per-file có header "Trang n/m" → MỘT lượt LLM gán KHOẢNG TRANG + loại cho từng đoạn → hậu xử lý tất định (chống chồng
/ sót trang, trang nối tiếp mang loại giấy trước) → MỖI giấy một file riêng vào đúng dòng; chỉ cắt trang
(`sourceSegments`) khi giấy chiếm một phần file. LLM lỗi → chế độ không tách (đính nguyên tệp).

Bảng 7 dòng theo thứ tự STT trên cổng (Sở Xây dựng Đà Nẵng), chia nhóm phương tiện:
  1. "[Phương tiện phi thương mại] Giấy đề nghị … theo mẫu"      (1 Bản chính)  ← Giấy đề nghị (phi thương mại)
  2. "- Thành phần hồ sơ đối với phương tiện thương mại:"        (tiêu đề nhóm, không tệp)
  3. "[Phi thương mại] Giấy chứng nhận đăng ký xe ô tô cho phương tiện phi thương mại" (1 Bản sao) ← đăng ký xe
  4. "- Thành phần hồ sơ đối với phương tiện phi thương mại:"  (tiêu đề nhóm, không tệp; phi thương mại giữ tick)
  5. "[Thương mại] Giấy chứng nhận đăng ký xe ô tô hoặc giấy hẹn …"            (1 Bản sao) ← đăng ký xe (thương mại)
  6. "[Phương tiện thương mại] Giấy đề nghị … theo mẫu"          (1 Bản chính)  ← Giấy đề nghị (thương mại)
  7. "[Phi thương mại] Đối với doanh nghiệp thực hiện công trình, dự án …"     (1 Bản sao) ← hợp đồng / tài liệu dự án
Nhóm theo loại Giấy đề nghị LLM gán (giay_de_nghi_thuong_mai / giay_de_nghi_phi_thuong_mai), không có → phi thương mại;
tiêu đề trang chỉ dự phòng cho trang LLM bỏ sót. Tài liệu quyền sử
dụng xe (hợp đồng thuê…) đi chung dòng đăng ký xe của nhóm; CCCD / giấy chưa rõ đính chung dòng Giấy đề nghị của nhóm.
Dòng của nhóm kia + dòng 7 khi không có hợp đồng → `untickRows`. componentName là cụm chỉ có ở đúng dòng (hai dòng Giấy
đề nghị / hai dòng đăng ký xe chỉ khác chữ "phi"), componentIndex = STT dòng.
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
from app.pipelines.dang_ky_noi_quy_lao_dong.attach.dinh_kem_tach.planner import _inherit_continuations
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from . import prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DE_NGHI = "giay_de_nghi"
# Giấy đề nghị của phương tiện thương mại: chỉ dùng để chọn nhóm, rồi quy về _DE_NGHI.
_DE_NGHI_TM = "giay_de_nghi_thuong_mai"
_DANG_KY_XE = "dang_ky_xe"
_QUYEN_SU_DUNG = "quyen_su_dung_xe"
_HOP_DONG = "hop_dong_du_an"
_CCCD = "cccd"
_OTHER = "other"
# Thứ tự file trong cùng một dòng: giấy chính trước, giấy kèm (hợp đồng thuê xe, CCCD, chưa rõ) sau.
_ORDER = [_DE_NGHI, _DANG_KY_XE, _QUYEN_SU_DUNG, _HOP_DONG, _CCCD, _OTHER]
_ALLOWED = set(_ORDER) | {_DE_NGHI_TM}
_EXTRA_NAMES = {_CCCD: "Căn cước công dân", _QUYEN_SU_DUNG: "Tài liệu chứng minh quyền sử dụng phương tiện"}

# STT = số dòng hiện trên cổng (cán bộ đối chiếu theo số này); extension thử dòng theo STT rồi khớp componentName.
ROWS: dict[int, dict[str, str]] = {
    1: {"componentName": "Campuchia cho phương tiện phi thương mại theo mẫu",
        "documentName": "Giấy đề nghị cấp giấy phép liên vận (phi thương mại)", "loaiBan": "Bản chính"},
    2: {"componentName": "Thành phần hồ sơ đối với phương tiện thương mại",
        "documentName": "Thành phần hồ sơ đối với phương tiện thương mại", "loaiBan": ""},
    3: {"componentName": "Giấy chứng nhận đăng ký xe ô tô cho phương tiện phi thương mại",
        "documentName": "Giấy chứng nhận đăng ký xe ô tô", "loaiBan": "Bản sao"},
    4: {"componentName": "Thành phần hồ sơ đối với phương tiện phi thương mại",
        "documentName": "Thành phần hồ sơ đối với phương tiện phi thương mại", "loaiBan": ""},
    5: {"componentName": "giấy hẹn nhận giấy chứng nhận đăng ký xe ô tô",
        "documentName": "Giấy chứng nhận đăng ký xe ô tô", "loaiBan": "Bản sao"},
    6: {"componentName": "Campuchia cho phương tiện thương mại theo mẫu",
        "documentName": "Giấy đề nghị cấp giấy phép liên vận (thương mại)", "loaiBan": "Bản chính"},
    7: {"componentName": "Đối với doanh nghiệp thực hiện công trình, dự án",
        "documentName": "Hợp đồng, tài liệu công trình dự án tại Lào, Campuchia", "loaiBan": "Bản sao"},
}
# Nhóm → (dòng Giấy đề nghị, dòng đăng ký xe, dòng hợp đồng dự án | None, các dòng của nhóm kia / tiêu đề cần bỏ tick).
_GROUP = {
    False: {"de_nghi": 1, "dang_ky_xe": 3, "hop_dong": 7, "untick": (2, 5, 6)},
    True: {"de_nghi": 6, "dang_ky_xe": 5, "hop_dong": None, "untick": (1, 3, 4, 7)},
}
THUONG_MAI_ROWS = (5, 6)
_ID_CARD_MARKERS = ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "citizen identity", "ho chieu",
                    "passport")


def is_thuong_mai(texts) -> bool:
    """Dự phòng (trang LLM bỏ sót): nhóm theo tiêu đề Giấy đề nghị; không thấy chữ nào → phi thương mại."""
    joined = _fold(" ".join(str(t or "") for t in texts))
    if "phi thuong mai" in joined:
        return False
    return "phuong tien thuong mai" in joined


def route(doc_type: str, thuong_mai: bool) -> int:
    """Loại giấy → STT dòng. Loại không có dòng riêng (CCCD, chưa rõ, hợp đồng dự án ở nhóm thương mại) → dòng Giấy đề nghị."""
    group = _GROUP[thuong_mai]
    if doc_type in (_DANG_KY_XE, _QUYEN_SU_DUNG):
        return group["dang_ky_xe"]
    if doc_type == _HOP_DONG and group["hop_dong"]:
        return group["hop_dong"]
    return group["de_nghi"]


def split_group(types) -> tuple[bool, list[str]]:
    """Nhóm thương mại theo loại Giấy đề nghị LLM gán; trả kèm danh sách loại đã quy _DE_NGHI_TM về _DE_NGHI."""
    types = list(types)
    thuong_mai = _DE_NGHI_TM in types and _DE_NGHI not in types
    return thuong_mai, [_DE_NGHI if t == _DE_NGHI_TM else t for t in types]


def has_own_row(doc_type: str, thuong_mai: bool) -> bool:
    return doc_type in (_DE_NGHI, _DANG_KY_XE, _QUYEN_SU_DUNG) or (doc_type == _HOP_DONG and not thuong_mai)


def _normalize_type(value: str) -> str:
    t = re.sub(r"[\s-]+", "_", _fold(value or ""))
    if t in _ALLOWED:
        return t
    if "de_nghi" in t:
        return _DE_NGHI_TM if "thuong_mai" in t and "phi_thuong_mai" not in t else _DE_NGHI
    if "thue" in t or "quyen_su_dung" in t or "cho_muon" in t:
        return _QUYEN_SU_DUNG
    if "dang_ky_xe" in t or "ca_vet" in t or "giay_hen" in t:
        return _DANG_KY_XE
    if "hop_dong" in t or "du_an" in t or "cong_trinh" in t:
        return _HOP_DONG
    if "cccd" in t or "can_cuoc" in t or "cmnd" in t or "ho_chieu" in t:
        return _CCCD
    return _OTHER


def _rule_type(text: str) -> str:
    """Dự phòng cho trang LLM bỏ sót (không cho đoạn LLM đã gán other) — nhận theo TIÊU ĐỀ đầu đoạn."""
    h = _fold(text)
    if not h:
        return _OTHER
    head = h[:700]
    if "giay de nghi" in head and "lien van" in head:
        return _DE_NGHI_TM if is_thuong_mai([text]) else _DE_NGHI
    if ("dang ky xe" in head or "vehicle registration" in head) and any(k in h for k in ("bien so", "so khung", "so may")):
        return _DANG_KY_XE
    if "hop dong" in head and ("thue" in head or "cho thue tai chinh" in head) and ("xe" in head or "phuong tien" in head):
        return _QUYEN_SU_DUNG
    if "hop dong" in head or (("cong trinh" in h or "du an" in h) and ("lao" in h or "campuchia" in h)):
        return _HOP_DONG
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
            first = items[0] if items else {**_fallback_segment(file_index, 1, page_count), "missed": True}
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
                    accepted.append({**_fallback_segment(file_index, start, prev), "missed": True})
                start = prev = page
        valid.extend(sorted(accepted, key=lambda x: x["pageFrom"]))
    return sorted(valid, key=lambda x: (x["fileIndex"], x["pageFrom"]))


def untick_rows(planned_rows: set[int], thuong_mai: bool) -> list[str]:
    """Dòng của nhóm kia + tiêu đề nhóm kia; phi thương mại không có hợp đồng dự án thì bỏ tick cả dòng hợp đồng."""
    group = _GROUP[thuong_mai]
    rows = [r for r in group["untick"] if r not in planned_rows]
    if group["hop_dong"] and group["hop_dong"] not in planned_rows:
        rows.append(group["hop_dong"])
    return [ROWS[r]["componentName"] for r in sorted(rows)]


def missing_warnings(found_types: set[str], thuong_mai: bool) -> list[str]:
    group = _GROUP[thuong_mai]
    warnings = []
    if _DE_NGHI not in found_types:
        warnings.append(f"Chưa có Giấy đề nghị cấp, cấp lại Giấy phép liên vận (dòng {group['de_nghi']}) — cần bổ sung.")
    if _DANG_KY_XE not in found_types:
        warnings.append(f"Chưa có Giấy chứng nhận đăng ký xe ô tô (dòng {group['dang_ky_xe']}, bắt buộc) — cần bổ sung bản "
                        "sao giấy đăng ký xe; xe không thuộc sở hữu người đề nghị thì kèm tài liệu chứng minh quyền sử "
                        "dụng hợp pháp.")
    if not thuong_mai and _HOP_DONG not in found_types:
        warnings.append("Không có hợp đồng/tài liệu công trình, dự án tại Lào, Campuchia — đã bỏ tick dòng "
                        f"{group['hop_dong']} (chỉ bắt buộc "
                        "với doanh nghiệp thực hiện công trình, dự án, hoạt động kinh doanh tại Lào/Campuchia).")
    return warnings


def build_plan_items(
    raw_files: list[dict],
    segments: list[dict],
    file_meta: dict[int, dict],
    pages_by_file: dict[int, dict[int, str]],
) -> tuple[list[dict], list[dict], list[str]]:
    """Đoạn đã hợp lệ → (attachments, classified, warnings). Thuần tất định, không gọi OCR/LLM."""
    # LLM quyết loại (kể cả other); tiêu đề trang / trang nối tiếp chỉ đoán cho trang LLM bỏ sót.
    typed: list[tuple[dict, str]] = []
    for segment in segments:
        doc_type = segment["type"]
        if segment.get("missed"):
            doc_type = _rule_type(_segment_text(segment, pages_by_file))
        typed.append((segment, doc_type))
    inherited = _inherit_continuations(typed, pages_by_file)
    typed = [(s, new if s.get("missed") else old) for (s, new), (_, old) in zip(inherited, typed)]
    thuong_mai, types = split_group(t for _, t in typed)
    typed = _merge_adjacent([(s, t) for (s, _), t in zip(typed, types)])

    classified: list[dict] = []
    extra_pages: list[str] = []
    by_row: dict[int, list[tuple[dict, str]]] = {}
    for segment, doc_type in typed:
        file = raw_files[segment["fileIndex"]]
        row_idx = route(doc_type, thuong_mai)
        if not has_own_row(doc_type, thuong_mai):
            extra_pages.append(f"{file.get('name')} trang {segment['pageFrom']}-{segment['pageTo']}")
        by_row.setdefault(row_idx, []).append((segment, doc_type))
        classified.append({"fileIndex": segment["fileIndex"], "fileName": file.get("name"),
                           "pageFrom": segment["pageFrom"], "pageTo": segment["pageTo"], "type": doc_type,
                           "componentIndex": row_idx})

    order = {t: i for i, t in enumerate(_ORDER)}
    attachments: list[dict] = []
    used_names: set[str] = set()
    for row_idx in sorted(by_row):
        row = ROWS[row_idx]
        parts = sorted(by_row[row_idx], key=lambda p: (order.get(p[1], 99), p[0]["fileIndex"], p[0]["pageFrom"]))
        for segment, doc_type in parts:
            file = raw_files[segment["fileIndex"]]
            own = doc_type in (_DE_NGHI, _DANG_KY_XE, _HOP_DONG) and has_own_row(doc_type, thuong_mai)
            default_name = row["documentName"] if own else _EXTRA_NAMES.get(doc_type, "Giấy tờ kèm theo")
            source = _source_segment(segment, file_meta[segment["fileIndex"]]["pageCount"])
            item = {
                "fileIndex": segment["fileIndex"],
                "fileName": str(file.get("name") or f"file-{segment['fileIndex'] + 1}"),
                "documentName": _unique_name(
                    (segment.get("documentName") or default_name).replace("/", "-"), used_names, default_name),
                "loaiBan": row["loaiBan"],
                "detectedType": doc_type,
                "componentName": row["componentName"],
                "componentIndex": row_idx,
                "target": "attp-row",
                "needsAddComponent": False,
            }
            if source["pageIndexes"] is not None:
                item["sourceSegments"] = [source]
            attachments.append(item)

    if attachments and (untick := untick_rows(set(by_row), thuong_mai)):
        attachments[0]["untickRows"] = untick
    warnings = missing_warnings({t for _, t in typed}, thuong_mai)
    if extra_pages:
        warnings.append("Giấy tờ không có dòng riêng (CCCD, giấy chưa rõ loại) đã đính chung dòng "
                        f"{_GROUP[thuong_mai]['de_nghi']} Giấy đề nghị: " + "; ".join(extra_pages))
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
    return client.extract_json_block(raw).get("documents", []) or []


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
            from ..dinh_kem_khong_tach.planner import plan as plan_without_split

            result = await plan_without_split(files, options, session)
            result["errors"] = [f"attachment_agent (tách): {e}", *result.get("errors", [])]
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
            "thuongMai": any(a["componentIndex"] in THUONG_MAI_ROWS for a in attachments),
            "rows": [{"componentIndex": k, **row} for k, row in ROWS.items()],
        },
        "ocr_text": join_ocr_documents(indexed_ocr),
        "llm_output": {"documents": raw_segments},
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
