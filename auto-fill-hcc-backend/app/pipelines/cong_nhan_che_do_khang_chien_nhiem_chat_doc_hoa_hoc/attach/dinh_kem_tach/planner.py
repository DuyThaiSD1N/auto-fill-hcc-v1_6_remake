"""Đính kèm bước "Thành phần hồ sơ" cho "Công nhận và giải quyết chế độ ưu đãi người hoạt động kháng chiến bị nhiễm chất
độc hóa học" (1.010816, cổng Bộ Nội vụ — Angular mat-table, engine FE `attp-row`) — chế độ TÁCH giấy tờ.

OCR per-file có header "Trang n/m" → MỘT lượt LLM gán KHOẢNG TRANG + loại cho từng đoạn → hậu xử lý tất định (chống chồng
/ sót trang, trang nối tiếp mang loại giấy trước) → MỖI giấy một file riêng vào đúng dòng; chỉ cắt trang
(`sourceSegments`) khi giấy chiếm một phần file. LLM lỗi → chế độ không tách (đính nguyên tệp).

Bảng 4 dòng theo ảnh ánh xạ thành phần hồ sơ (cổng tích sẵn cả 4):
  1. "Bản khai theo Mẫu số 09 Phụ lục I Nghị định số 131/2021/NĐ-CP" (1 Bản chính)  ← Bản khai.
  2. "b) … giấy tờ có ghi nhận thời gian tham gia kháng chiến …" (chọn 1 Bản sao)   ← giấy X Y Z / QĐ phục viên / lý lịch
     … + Giấy xác nhận giải mã phiên hiệu Mẫu 37 (đính chung dòng này).
  3. "d) … Giấy xác nhận người hoạt động kháng chiến có vợ hoặc có chồng nhưng không có con đẻ …" (1 Bản chính) ← chỉ
     trường hợp vô sinh; hồ sơ không có thì `untickRows` bỏ tick dòng này.
  4. "c) … giấy tờ ghi nhận mắc bệnh …" (1 Bản chính) ← bản tóm tắt hồ sơ bệnh án; trường hợp vô sinh (có dòng 3, không
     có giấy bệnh) thì bỏ tick dòng này.
CCCD / giấy chưa rõ loại không có dòng → đính chung dòng 1, không bỏ file nào.
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

_BAN_KHAI = "ban_khai_mau_09"
_KHANG_CHIEN = "giay_to_khang_chien"
_PHIEN_HIEU = "xac_nhan_phien_hieu"
_KHONG_CON = "xac_nhan_khong_con_de"
_BENH = "giay_to_mac_benh"
_CCCD = "cccd"
_OTHER = "other"
# Thứ tự file trong cùng một dòng: giấy tờ gốc đứng trước giấy giải mã phiên hiệu.
_ORDER = [_BAN_KHAI, _KHANG_CHIEN, _PHIEN_HIEU, _KHONG_CON, _BENH, _CCCD, _OTHER]
_ALLOWED = set(_ORDER)
_EXTRA_NAMES = {_CCCD: "Căn cước công dân"}

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold); componentIndex = STT dòng (1-based). Dòng 4 cũng
# nhắc "có vợ hoặc có chồng nhưng không có con đẻ" → chuỗi dòng 3 phải bắt đầu từ "Giấy xác nhận người hoạt động".
_ROWS: dict[int, dict[str, str]] = {
    1: {"componentName": "Bản khai theo Mẫu số 09",
        "documentName": "Bản khai Mẫu số 09", "loaiBan": "Bản chính"},
    2: {"componentName": "ghi nhận thời gian tham gia kháng chiến",
        "documentName": "Giấy tờ ghi nhận thời gian tham gia kháng chiến", "loaiBan": "Bản sao"},
    3: {"componentName": "Giấy xác nhận người hoạt động kháng chiến có vợ hoặc có chồng",
        "documentName": "Giấy xác nhận có vợ hoặc chồng nhưng không có con đẻ", "loaiBan": "Bản chính"},
    4: {"componentName": "giấy tờ ghi nhận mắc bệnh",
        "documentName": "Bản tóm tắt hồ sơ bệnh án", "loaiBan": "Bản chính"},
}
_ROUTE: dict[str, int] = {_BAN_KHAI: 1, _KHANG_CHIEN: 2, _PHIEN_HIEU: 2, _KHONG_CON: 3, _BENH: 4}
_ID_CARD_MARKERS = ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "citizen identity")


def _normalize_type(value: str) -> str:
    t = re.sub(r"[\s-]+", "_", _fold(value or ""))
    if t in _ALLOWED:
        return t
    if "ban_khai" in t or "mau_09" in t or "mau_so_09" in t:
        return _BAN_KHAI
    if "phien_hieu" in t or "mau_37" in t:
        return _PHIEN_HIEU
    if "con_de" in t or "vo_sinh" in t:
        return _KHONG_CON
    if "benh" in t or "ra_vien" in t or "y_te" in t:
        return _BENH
    if "khang_chien" in t or any(k in t for k in ("phuc_vien", "xuat_ngu", "ly_lich", "thuong_binh", "huan_chuong",
                                                   "huy_chuong", "khen_thuong", "bhxh", "bao_hiem")):
        return _KHANG_CHIEN
    if "cccd" in t or "can_cuoc" in t or "cmnd" in t:
        return _CCCD
    return _OTHER


def _rule_type(text: str) -> str:
    """Fallback khi LLM trả other — nhận theo TIÊU ĐỀ đầu đoạn. Bản khai xét trước: ghi chú của nó nhắc "không có con đẻ"
    và "Tình trạng bệnh tật"."""
    h = _fold(text)
    if not h:
        return _OTHER
    head = h[:700]
    if "ban khai" in head and ("chat doc hoa hoc" in head or "mau so 09" in head):
        return _BAN_KHAI
    if "phien hieu" in head and ("giai ma" in head or "xac nhan" in head):
        return _PHIEN_HIEU
    if "xac nhan" in head and "khong co con de" in h:
        return _KHONG_CON
    if any(k in head for k in ("tom tat ho so benh an", "giay ra vien", "benh an ngoai tru", "chan doan")):
        return _BENH
    if any(k in head for k in ("phuc vien", "xuat ngu", "ly lich", "thuong binh", "huan chuong", "huy chuong",
                               "giay chung nhan", "khen thuong", "giay x y z", "giay xyz")):
        return _KHANG_CHIEN
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


def untick_rows(found_rows: set[int]) -> list[str]:
    """Dòng cổng tích sẵn mà hồ sơ không dùng: dòng 3 (không có con đẻ) khi không có giấy xác nhận; dòng 4 (mắc bệnh)
    khi là trường hợp vô sinh (có dòng 3, không có giấy bệnh)."""
    rows = []
    if 3 not in found_rows:
        rows.append(_ROWS[3]["componentName"])
    elif 4 not in found_rows:
        rows.append(_ROWS[4]["componentName"])
    return rows


def missing_warnings(found_rows: set[int]) -> list[str]:
    warnings = []
    if 1 not in found_rows:
        warnings.append("Chưa có Bản khai Mẫu số 09 (dòng 1) — cần bổ sung.")
    if 2 not in found_rows:
        warnings.append("Chưa có giấy tờ ghi nhận thời gian tham gia kháng chiến tại vùng quân đội Mỹ sử dụng chất độc "
                        "hóa học (dòng 2: giấy X Y Z, quyết định phục viên / xuất ngũ, lý lịch…) — cần bổ sung.")
    if 3 not in found_rows and 4 not in found_rows:
        warnings.append("Chưa có giấy tờ ghi nhận mắc bệnh (dòng 4: bản tóm tắt hồ sơ bệnh án) — cần bổ sung; trường "
                        "hợp vô sinh thì đính Giấy xác nhận có vợ hoặc có chồng nhưng không có con đẻ (dòng 3).")
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
        typed.append((segment, doc_type))
    typed = _merge_adjacent(_inherit_continuations(typed, pages_by_file))

    classified: list[dict] = []
    extra_pages: list[str] = []
    by_row: dict[int, list[tuple[dict, str]]] = {}
    for segment, doc_type in typed:
        file = raw_files[segment["fileIndex"]]
        row_idx = _ROUTE.get(doc_type, 1)
        if doc_type not in _ROUTE:
            extra_pages.append(f"{file.get('name')} trang {segment['pageFrom']}-{segment['pageTo']}")
        by_row.setdefault(row_idx, []).append((segment, doc_type))
        classified.append({"fileIndex": segment["fileIndex"], "fileName": file.get("name"),
                           "pageFrom": segment["pageFrom"], "pageTo": segment["pageTo"], "type": doc_type,
                           "componentIndex": row_idx})

    order = {t: i for i, t in enumerate(_ORDER)}
    attachments: list[dict] = []
    used_names: set[str] = set()
    for row_idx in sorted(by_row):
        row = _ROWS[row_idx]
        parts = sorted(by_row[row_idx], key=lambda p: (order.get(p[1], 99), p[0]["fileIndex"], p[0]["pageFrom"]))
        for segment, doc_type in parts:
            file = raw_files[segment["fileIndex"]]
            default_name = row["documentName"] if doc_type in _ROUTE else _EXTRA_NAMES.get(doc_type, "Giấy tờ kèm theo")
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

    found = set(by_row)
    if attachments and (untick := untick_rows(found)):
        attachments[0]["untickRows"] = untick
    warnings = missing_warnings(found)
    if extra_pages:
        warnings.append("Giấy tờ không có dòng riêng (CCCD, giấy chưa rõ loại) đã đính chung dòng 1 Bản khai: "
                        + "; ".join(extra_pages))
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
            "rows": [{"componentIndex": k, **row} for k, row in _ROWS.items()],
        },
        "ocr_text": join_ocr_documents(indexed_ocr),
        "llm_output": {"documents": raw_segments},
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
