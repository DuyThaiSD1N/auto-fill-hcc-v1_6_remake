"""Đính kèm bước "Thành phần hồ sơ" cho "Đăng ký đất đai lần đầu đối với trường hợp được Nhà nước giao đất để quản
lý" (1.012756, cổng DVC Đà Nẵng — Angular mat-table, engine FE `attp-row`).

ENGINE TÁCH (segment như dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua): OCR per-file có
header "Trang n/m" → LLM gán KHOẢNG TRANG + loại cho từng giấy tờ → hậu xử lý tất định (chống chồng/thiếu trang, bỏ
trang trắng) → MỖI GIẤY TỜ MỘT FILE RIÊNG (`sourceSegments` một đoạn). Cổng chỉ có 2 dòng mà Đơn Mẫu 15 mục 5 kê
cả chục giấy tờ kèm theo → các file cùng dòng được FE đặt một lần vào ô "Chọn tệp tin" (input multiple). Tên file
đánh số D1-01, D1-02 … / D2-01 … theo đúng thứ tự cần chọn.

Bảng 2 dòng (thứ tự trên cổng, cả hai "Bản chính"):
  [1] Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu 15)
        ← don_mau_15, rồi giấy tờ kèm theo mục 5 của Đơn: quyet_dinh (giao/cho thuê đất, chủ trương đầu tư, điều
          chỉnh), hop_dong_thue_dat (+ phụ lục), bien_ban_giao_dat, gcn_dang_ky_doanh_nghiep, phieu_do_dac,
          nghia_vu_tai_chinh (xác nhận / thông báo thuế), to_khai_thue (LPTB), van_ban_dai_dien, giay_to_khac
  [2] Báo cáo kết quả rà soát hiện trạng sử dụng đất (Mẫu 15đ)
        ← bao_cao_ra_soat + trich_luc_ban_do (mục "Kèm theo Báo cáo này": trích lục / mảnh trích đo thửa đất)
Cùng loại thì theo thứ tự trang trong hồ sơ. CCCD không có dòng → bỏ qua (chỉ dùng ở bước điền thông tin).
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.attach.planner import (
    _coerce_int,
    _pdf_page_count,
    _split_ocr_pages,
)
from app.pipelines.dang_ky_dat_dai_lan_dau_nha_nuoc_giao_quan_ly.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON15 = "don_mau_15"
_BAO_CAO = "bao_cao_ra_soat"
_TRICH_LUC = "trich_luc_ban_do"
_PHIEU_DO_DAC = "phieu_do_dac"
_QD = "quyet_dinh"
_HD_THUE = "hop_dong_thue_dat"
_BB_GIAO = "bien_ban_giao_dat"
_DKDN = "gcn_dang_ky_doanh_nghiep"
_NGHIA_VU_TC = "nghia_vu_tai_chinh"
_TO_KHAI_THUE = "to_khai_thue"
_DAI_DIEN = "van_ban_dai_dien"
_KHAC = "giay_to_khac"
_CCCD = "cccd"
_OTHER = "other"
_ALLOWED = {
    _DON15, _BAO_CAO, _TRICH_LUC, _PHIEU_DO_DAC, _QD, _HD_THUE, _BB_GIAO, _DKDN, _NGHIA_VU_TC, _TO_KHAI_THUE,
    _DAI_DIEN, _KHAC, _CCCD, _OTHER,
}

# componentName = ĐOẠN TEXT ĐẶC TRƯNG DUY NHẤT của dòng (FE khớp substring fold); componentIndex = STT dòng
# (1-based) làm gợi ý. `types` = loại giấy tờ vào dòng, theo THỨ TỰ file cần chọn.
_ROWS: dict[int, dict[str, Any]] = {
    1: {
        "componentName": "Đơn đăng ký đất đai, tài sản gắn liền với đất",
        "documentName": "Đơn đăng ký đất đai, tài sản gắn liền với đất",
        "loaiBan": "Bản chính",
        "types": [_DON15, _QD, _HD_THUE, _BB_GIAO, _DKDN, _PHIEU_DO_DAC, _NGHIA_VU_TC, _TO_KHAI_THUE, _DAI_DIEN,
                  _KHAC],
    },
    2: {
        "componentName": "Báo cáo kết quả rà soát hiện trạng sử dụng đất",
        "documentName": "Báo cáo kết quả rà soát hiện trạng sử dụng đất (Mẫu số 15đ)",
        "loaiBan": "Bản chính",
        "types": [_BAO_CAO, _TRICH_LUC],
    },
}
_ROW_OF_TYPE = {t: idx for idx, row in _ROWS.items() for t in row["types"]}

# Tên file mặc định khi LLM không đặt tên (≤ 44 ký tự để còn chỗ cho tiền tố "D1-01 ").
_TYPE_NAMES = {
    _DON15: "Đơn đăng ký đất đai Mẫu 15",
    _BAO_CAO: "Báo cáo rà soát hiện trạng sử dụng đất",
    _TRICH_LUC: "Trích lục bản đồ thửa đất",
    _PHIEU_DO_DAC: "Phiếu đo đạc chỉnh lý thửa đất",
    _QD: "Quyết định giao đất cho thuê đất",
    _HD_THUE: "Hợp đồng thuê đất",
    _BB_GIAO: "Biên bản giao đất trên thực địa",
    _DKDN: "Giấy chứng nhận đăng ký doanh nghiệp",
    _NGHIA_VU_TC: "Giấy tờ nghĩa vụ tài chính",
    _TO_KHAI_THUE: "Tờ khai lệ phí trước bạ",
    _DAI_DIEN: "Giấy ủy quyền",
    _KHAC: "Giấy tờ kèm theo",
}


def _fallback_segment(file_index: int, page_from: int, page_to: int) -> dict:
    return {"fileIndex": file_index, "pageFrom": page_from, "pageTo": page_to, "type": _OTHER, "documentName": ""}


def _normalize_type(value: str) -> str:
    t = re.sub(r"[\s-]+", "_", _fold(value or ""))
    if t in _ALLOWED:
        return t
    if "ra_soat" in t or "mau_15d" in t or "bao_cao" in t:
        return _BAO_CAO
    if "mau_15" in t or t == "don" or "don_dang_ky" in t:
        return _DON15
    if "phieu_do" in t or "chinh_ly" in t:
        return _PHIEU_DO_DAC
    if "trich_luc" in t or "trich_do" in t or "ban_do" in t or "so_do" in t:
        return _TRICH_LUC
    if "hop_dong_thue" in t or "phu_luc" in t:
        return _HD_THUE
    if "bien_ban" in t or "giao_dat_thuc_dia" in t:
        return _BB_GIAO
    if "uy_quyen" in t or "dai_dien" in t or "gioi_thieu" in t:
        return _DAI_DIEN
    if "to_khai" in t or "lptb" in t or "le_phi" in t:
        return _TO_KHAI_THUE
    if "nghia_vu" in t or "thue" in t or "nop_tien" in t or "bien_lai" in t or "don_gia" in t:
        return _NGHIA_VU_TC
    if "doanh_nghiep" in t or "dkdn" in t or "thanh_lap" in t:
        return _DKDN
    if "quyet_dinh" in t or t.startswith("qd") or "chu_truong" in t:
        return _QD
    if "cccd" in t or "can_cuoc" in t or "cmnd" in t:
        return _CCCD
    if "cong_van" in t or "khac" in t or "chap_thuan" in t:
        return _KHAC
    return _OTHER


def _validated_segments(raw_segments: list[dict], raw_files: list[dict], file_meta: dict[int, dict],
                        errors: list[str]) -> list[dict]:
    """Chuẩn hóa đoạn LLM trả: bỏ đoạn sai khoảng / chồng trang, vá trang thiếu thành đoạn "other"."""
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


def _is_blank(text: str) -> bool:
    """Trang trắng (mặt sau không in): OCR gần như không ra chữ."""
    return sum(ch.isalnum() for ch in str(text or "")) < 5


def _is_document_start(text: str) -> bool:
    """Trang mở đầu một văn bản: quốc hiệu / "Mẫu số" / thẻ căn cước ở đầu trang; trang nối tiếp thì không có."""
    head = _fold(re.sub(r"\s+", " ", str(text or ""))[:600])
    return "cong hoa xa hoi chu nghia" in head or "mau so" in head or "can cuoc" in head


def _content_pages(segment: dict, file_meta: dict[int, dict],
                   page_text_by_file: dict[int, dict[int, str]]) -> list[int]:
    """Trang có nội dung của đoạn. Không có ranh giới trang thì không biết trang nào trắng → giữ nguyên."""
    pages = list(range(segment["pageFrom"], segment["pageTo"] + 1))
    if not file_meta[segment["fileIndex"]]["pageBoundariesAvailable"]:
        return pages
    texts = page_text_by_file.get(segment["fileIndex"]) or {}
    return [p for p in pages if not _is_blank(texts.get(p, ""))]


# --- Rule fallback theo OCR (khi LLM không phân loại được đoạn) ---
def _rule_type(text: str) -> str:
    """THỨ TỰ QUAN TRỌNG: Đơn Mẫu 15 và Báo cáo rà soát kê tên quyết định / hợp đồng / GCN ĐKDN → nhận TRƯỚC. Hợp
    đồng thuê đất, biên bản giao đất, thông báo thuế đều nhắc "quyết định" → nhận TRƯỚC quyết định."""
    h = _fold(text)
    if not h:
        return _OTHER
    if "don dang ky dat dai" in h:
        return _DON15
    if "ra soat hien trang su dung dat" in h:
        return _BAO_CAO
    if "to khai" in h and ("le phi truoc ba" in h or "01/lptb" in h or "thue su dung dat" in h):
        return _TO_KHAI_THUE
    if "ben duoc uy quyen" in h or "hop dong uy quyen" in h or "giay uy quyen" in h:
        return _DAI_DIEN
    if "phieu do dac" in h:
        return _PHIEU_DO_DAC
    if "trich luc" in h or "manh trich do" in h or "trich do ban do dia chinh" in h:
        return _TRICH_LUC
    if "hop dong thue dat" in h:
        return _HD_THUE
    if "bien ban" in h and "giao dat" in h:
        return _BB_GIAO
    if "giay chung nhan dang ky doanh nghiep" in h and "ma so doanh nghiep" in h:
        return _DKDN
    if (
        "don gia thue dat" in h
        or ("xac nhan" in h and "nghia vu" in h)
        or "giay nop tien vao ngan sach" in h
        or "bien lai thu" in h
    ):
        return _NGHIA_VU_TC
    if "quyet dinh" in h and any(
        m in h for m in ("giao dat", "cho thue dat", "thu hoi dat", "chu truong dau tu", "hinh thuc thue dat")
    ):
        return _QD
    if any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu")):
        return _CCCD
    return _OTHER


def _source_segment(file_index: int, pages: list[int], page_count: int) -> dict:
    indexes = None if pages == list(range(1, page_count + 1)) else [p - 1 for p in pages]
    return {"fileIndex": file_index, "pageIndexes": indexes}


def _file_name(row_idx: int, position: int, base: str, fallback: str) -> str:
    """"D1-03 Quyết định 500 QĐ-UBND cho thuê đất" — tiền tố giữ thứ tự và làm tên các file cùng dòng khác nhau
    (FE chống đính trùng theo 24 ký tự đầu của tên)."""
    prefix = f"D{row_idx}-{position:02d} "
    name = normalize_document_name(base or fallback, fallback)
    return normalize_document_name(prefix + name, prefix + fallback)


def build_plan_items(
    raw_files: list[dict],
    segments: list[dict],
    file_meta: dict[int, dict],
    page_text_by_file: dict[int, dict[int, str]],
    full_text_by_file: dict[int, str],
) -> tuple[list[dict], list[dict], list[str]]:
    """Đoạn đã hợp lệ → (attachments, classified, warnings). Thuần tất định, không gọi OCR/LLM."""
    classified: list[dict] = []
    warnings: list[str] = []
    skipped_pages: list[str] = []
    blank_pages: list[str] = []

    # 1) Loại + trang có nội dung. LLM là chính; rule OCR chỉ vá khi LLM trả other. Đoạn liền sau KHÔNG mở đầu văn
    #    bản mới (không quốc hiệu / "Mẫu số") mà cùng loại — hoặc rule không nhận ra — là trang nối tiếp → gộp vào
    #    đoạn trước. Ba quyết định liền nhau vẫn là ba file vì trang đầu mỗi quyết định có quốc hiệu.
    docs: list[dict] = []
    for segment in segments:
        file = raw_files[segment["fileIndex"]]
        texts = page_text_by_file.get(segment["fileIndex"]) or {}
        pages = _content_pages(segment, file_meta, page_text_by_file)
        dropped = [p for p in range(segment["pageFrom"], segment["pageTo"] + 1) if p not in pages]
        if dropped:
            blank_pages.append(f"{file.get('name')} trang {', '.join(map(str, dropped))}")
        base = {"fileIndex": segment["fileIndex"], "fileName": file.get("name"),
                "pageFrom": segment["pageFrom"], "pageTo": segment["pageTo"]}
        prev = docs[-1] if docs else None
        adjacent = (
            bool(prev) and prev["fileIndex"] == segment["fileIndex"] and prev["pageTo"] + 1 == segment["pageFrom"]
        )
        if not pages:
            classified.append({**base, "type": _OTHER, "target": "skip", "reason": "trang trắng"})
            if adjacent:
                # Mặt sau trắng giữa một văn bản không được làm đứt trang nối tiếp của nó.
                prev["pageTo"] = segment["pageTo"]
            continue
        doc_type = segment["type"]
        ruled = doc_type == _OTHER
        if ruled:
            text = "\n".join(texts.get(p, "") for p in pages)
            doc_type = _rule_type(text or full_text_by_file.get(segment["fileIndex"], ""))
        if (
            adjacent
            and (doc_type == prev["type"] or (ruled and doc_type == _OTHER))
            and file_meta[segment["fileIndex"]]["pageBoundariesAvailable"]
            and not _is_document_start(texts.get(pages[0], ""))
        ):
            prev["pageTo"] = segment["pageTo"]
            prev["pages"] += pages
            continue
        docs.append({**base, "type": doc_type, "pages": pages, "documentName": segment.get("documentName") or ""})

    # 2) Gán dòng.
    by_row: dict[int, list[dict]] = {}
    for doc in docs:
        base = {k: doc[k] for k in ("fileIndex", "fileName", "pageFrom", "pageTo", "type")}
        if doc["type"] == _CCCD:
            classified.append({**base, "target": "skip", "reason": "CCCD không nằm trong thành phần hồ sơ"})
            continue
        row_idx = _ROW_OF_TYPE.get(doc["type"])
        if row_idx is None:
            skipped_pages.append(f"{doc['fileName']} trang {doc['pageFrom']}-{doc['pageTo']}")
            classified.append({**base, "type": _OTHER, "target": "skip"})
            continue
        by_row.setdefault(row_idx, []).append(doc)
        classified.append({**base, "componentIndex": row_idx, "shared": doc["type"] != _ROWS[row_idx]["types"][0]})

    # 3) Mỗi giấy tờ một file, thứ tự theo `types` của dòng rồi theo trang.
    attachments: list[dict] = []
    for row_idx in sorted(by_row):
        row = _ROWS[row_idx]
        order = {t: i for i, t in enumerate(row["types"])}
        parts = sorted(by_row[row_idx], key=lambda d: (order.get(d["type"], 99), d["fileIndex"], d["pageFrom"]))
        for position, doc in enumerate(parts, start=1):
            file_index = doc["fileIndex"]
            attachments.append({
                "fileIndex": file_index,
                "fileName": str(doc["fileName"] or f"file-{file_index + 1}"),
                "documentName": _file_name(row_idx, position, doc["documentName"], _TYPE_NAMES[doc["type"]]),
                "componentName": row["componentName"],
                "componentIndex": row_idx,
                "loaiBan": row["loaiBan"],
                "target": "attp-row",
                "needsAddComponent": False,
                "detectedType": doc["type"],
                "includedTypes": [doc["type"]],
                "sourceSegments": [_source_segment(file_index, doc["pages"], file_meta[file_index]["pageCount"])],
            })

    if skipped_pages:
        warnings.append("Không xác định được loại giấy tờ (bỏ qua, đính thủ công nếu cần): " + "; ".join(skipped_pages))
    if blank_pages:
        warnings.append("Đã bỏ trang trắng không đính kèm: " + "; ".join(blank_pages) + ".")

    found = {doc["type"] for doc in docs}
    if _DON15 not in found:
        warnings.append("Không tìm thấy Đơn đăng ký đất đai, tài sản gắn liền với đất Mẫu số 15 (dòng 1, bắt buộc) "
                        "— vui lòng đính tay.")
    if _BAO_CAO not in found:
        warnings.append("Không tìm thấy Báo cáo kết quả rà soát hiện trạng sử dụng đất Mẫu số 15đ (dòng 2, bắt "
                        "buộc) — vui lòng đính tay.")
    elif _TRICH_LUC not in found:
        warnings.append("Chưa thấy trích lục bản đồ địa chính / mảnh trích đo thửa đất kèm Báo cáo rà soát (dòng 2) "
                        "— kiểm tra, bổ sung nếu có.")
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
    attachments, classified, warnings = build_plan_items(
        raw_files, segments, file_meta, page_text_by_file, full_text_by_file
    )
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
