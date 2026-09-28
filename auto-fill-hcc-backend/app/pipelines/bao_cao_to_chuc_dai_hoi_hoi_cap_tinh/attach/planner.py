"""Đính kèm bước "Thành phần hồ sơ" cho "Thủ tục báo cáo tổ chức đại hội thành lập, đại hội nhiệm kỳ, đại hội bất
thường của hội (cấp tỉnh)" (1.012942, cổng DVCQG — Angular mat-table, engine FE `attp-row`).

ENGINE TÁCH/GỘP (như chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh): OCR per-file có header "Trang n/m" → LLM gán KHOẢNG
TRANG + loại cho từng đoạn → hậu xử lý tất định → GOM các đoạn cùng dòng thành MỘT file gộp (`sourceSegments`).

Bảng 18 dòng gộp chung 3 trường hợp; dòng nhận giấy tờ phụ thuộc LOẠI ĐẠI HỘI (đọc từ văn bản báo cáo / Nghị quyết
BCH, mặc định nhiệm kỳ). Đều "Bản chính". Nhiều dòng trùng chữ (2 ⊃ 14; 6 = 7) → FE định vị theo componentIndex.
  Đại hội NHIỆM KỲ:  văn bản báo cáo (+ đơn đổi tên)→15; dự kiến thời gian, địa điểm→6 (không có văn bản riêng thì
                     đính chung văn bản báo cáo); Đề án nhân sự + danh sách dự kiến BCH→3; Nghị quyết BCH→13; ý
                     kiến đồng ý / công văn cử cán bộ→14; Sơ yếu lý lịch + Phiếu LLTP→16.
  Đại hội BẤT THƯỜNG: văn bản báo cáo (+ đơn đổi tên)→5; dự kiến→7; Nghị quyết BCH→12; còn lại như nhiệm kỳ.
  Đại hội THÀNH LẬP: văn bản báo cáo của Ban vận động→10; Đề án nhân sự→8; dự kiến→9; ý kiến đồng ý + Sơ yếu lý
                     lịch + Phiếu LLTP→2.
  Mọi trường hợp: Dự thảo Điều lệ→1; báo cáo số lượng hội viên→4; dự thảo báo cáo tổng kết / chính trị + báo cáo
  kiểm điểm BCH + báo cáo Ban kiểm tra + báo cáo tài chính→11; dự thảo Nghị quyết đại hội→17.
Dòng 18 ("các nội dung khác") không tự đính. CCCD không có dòng → bỏ qua (chỉ dùng ở bước điền thông tin).
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.bao_cao_to_chuc_dai_hoi_hoi_cap_tinh.attach import prompt
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.attach.planner import (
    _page_subset,
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

_BAO_CAO = "bao_cao_to_chuc_dai_hoi"
_DOI_TEN = "don_doi_ten"
_NQ_BCH = "nghi_quyet_bch"
_NQ_DAI_HOI = "du_thao_nghi_quyet_dai_hoi"
_DU_KIEN = "du_kien_chuong_trinh"
_DE_AN = "de_an_nhan_su"
_DS_BCH = "danh_sach_bch"
_Y_KIEN = "y_kien_dong_y"
_TONG_KET = "bao_cao_tong_ket"
_KIEM_DIEM = "bao_cao_kiem_diem"
_BKT = "bao_cao_ban_kiem_tra"
_TAI_CHINH = "bao_cao_tai_chinh"
_HOI_VIEN = "bao_cao_hoi_vien"
_DIEU_LE = "du_thao_dieu_le"
_SYLL = "so_yeu_ly_lich"
_LLTP = "ly_lich_tu_phap"
_CCCD = "cccd"
_OTHER = "other"
# Thứ tự ghép các loại trong CÙNG một file gộp.
_ORDER = [_BAO_CAO, _DOI_TEN, _DU_KIEN, _DE_AN, _DS_BCH, _NQ_BCH, _Y_KIEN, _SYLL, _LLTP, _TONG_KET, _KIEM_DIEM,
          _BKT, _TAI_CHINH, _HOI_VIEN, _NQ_DAI_HOI, _DIEU_LE]
_ALLOWED = set(_ORDER) | {_CCCD, _OTHER}

_NHIEM_KY = "nhiem_ky"
_BAT_THUONG = "bat_thuong"
_THANH_LAP = "thanh_lap"
_CASE_LABEL = {_NHIEM_KY: "đại hội nhiệm kỳ", _BAT_THUONG: "đại hội bất thường", _THANH_LAP: "đại hội thành lập"}

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold); componentIndex = STT dòng (1-based).
_ROWS: dict[int, dict[str, str]] = {
    1: {"componentName": "Dự thảo điều lệ sửa đổi, bổ sung",
        "documentName": "Dự thảo điều lệ sửa đổi, bổ sung"},
    2: {"componentName": "Trường hợp dự kiến chủ tịch hội không phải là trưởng ban vận động thành lập hội",
        "documentName": "Ý kiến đồng ý, sơ yếu lý lịch, phiếu LLTP số 1"},
    3: {"componentName": "Đề án nhân sự, trong đó nêu rõ tiêu chuẩn",
        "documentName": "Đề án nhân sự"},
    4: {"componentName": "Báo cáo số lượng hội viên",
        "documentName": "Báo cáo số lượng hội viên"},
    5: {"componentName": "Văn bản báo cáo tổ chức đại hội bất thường của hội",
        "documentName": "Văn bản báo cáo tổ chức đại hội bất thường"},
    6: {"componentName": "Dự kiến thời gian, địa điểm tổ chức đại hội, số lượng đại biểu mời",
        "documentName": "Dự kiến thời gian, địa điểm, chương trình đại hội"},
    7: {"componentName": "Dự kiến thời gian, địa điểm tổ chức đại hội, số lượng đại biểu mời",
        "documentName": "Dự kiến thời gian, địa điểm, chương trình đại hội"},
    8: {"componentName": "Đề án nhân sự (bản gốc)",
        "documentName": "Đề án nhân sự (bản gốc)"},
    9: {"componentName": "dự kiến chương trình đại hội (bản gốc)",
        "documentName": "Dự kiến thời gian, địa điểm đại hội (bản gốc)"},
    10: {"componentName": "Văn bản báo cáo tổ chức đại hội thành lập của Ban Vận động",
         "documentName": "Văn bản báo cáo tổ chức đại hội thành lập"},
    11: {"componentName": "Dự thảo báo cáo tổng kết công tác nhiệm kỳ",
         "documentName": "Dự thảo báo cáo tổng kết, kiểm điểm, tài chính"},
    12: {"componentName": "Nghị quyết của Ban chấp hành hội về việc tổ chức đại hội bất thường",
         "documentName": "Nghị quyết BCH về tổ chức đại hội bất thường"},
    13: {"componentName": "Nghị quyết của ban chấp hành hội về việc tổ chức đại hội nhiệm kỳ",
         "documentName": "Nghị quyết BCH về tổ chức đại hội nhiệm kỳ"},
    14: {"componentName": "Ý kiến đồng ý của cơ quan có thẩm quyền theo quy định về phân cấp quản lý cán bộ",
         "documentName": "Ý kiến đồng ý của cơ quan có thẩm quyền"},
    15: {"componentName": "Văn bản báo cáo tổ chức đại hội nhiệm kỳ của hội",
         "documentName": "Văn bản báo cáo tổ chức đại hội nhiệm kỳ"},
    16: {"componentName": "Sơ yếu lý lịch cá nhân và phiếu lý lịch tư pháp số 1 không quá 06 tháng",
         "documentName": "Sơ yếu lý lịch, phiếu lý lịch tư pháp số 1"},
    17: {"componentName": "Dự thảo những nội dung thảo luận và quyết định tại đại hội",
         "documentName": "Dự thảo nội dung thảo luận, quyết định tại đại hội"},
    18: {"componentName": "thuộc thẩm quyền của đại hội theo quy định của điều lệ hội",
         "documentName": "Nội dung khác thuộc thẩm quyền đại hội"},
}


def _same(row: int) -> dict[str, int]:
    return {_NHIEM_KY: row, _BAT_THUONG: row, _THANH_LAP: row}


# Loại giấy tờ → dòng theo loại đại hội. Loại không có ở một trường hợp thì không đính.
_ROUTE: dict[str, dict[str, int]] = {
    _BAO_CAO: {_NHIEM_KY: 15, _BAT_THUONG: 5, _THANH_LAP: 10},
    _DOI_TEN: {_NHIEM_KY: 15, _BAT_THUONG: 5},
    _DU_KIEN: {_NHIEM_KY: 6, _BAT_THUONG: 7, _THANH_LAP: 9},
    _DE_AN: {_NHIEM_KY: 3, _BAT_THUONG: 3, _THANH_LAP: 8},
    _DS_BCH: {_NHIEM_KY: 3, _BAT_THUONG: 3, _THANH_LAP: 8},
    _NQ_BCH: {_NHIEM_KY: 13, _BAT_THUONG: 12},
    _Y_KIEN: {_NHIEM_KY: 14, _BAT_THUONG: 14, _THANH_LAP: 2},
    _SYLL: {_NHIEM_KY: 16, _BAT_THUONG: 16, _THANH_LAP: 2},
    _LLTP: {_NHIEM_KY: 16, _BAT_THUONG: 16, _THANH_LAP: 2},
    _DIEU_LE: _same(1),
    _HOI_VIEN: _same(4),
    _TONG_KET: _same(11),
    _KIEM_DIEM: _same(11),
    _BKT: _same(11),
    _TAI_CHINH: _same(11),
    _NQ_DAI_HOI: _same(17),
}

# Dòng BẮT BUỘC theo loại đại hội → nhãn trong cảnh báo khi thiếu.
_REQUIRED: dict[str, list[tuple[int, str]]] = {
    _NHIEM_KY: [
        (15, "Văn bản báo cáo tổ chức đại hội nhiệm kỳ"),
        (13, "Nghị quyết của Ban chấp hành về việc tổ chức đại hội nhiệm kỳ"),
        (3, "Đề án nhân sự"),
        (6, "Dự kiến thời gian, địa điểm, số đại biểu, chương trình đại hội"),
        (11, "Dự thảo báo cáo tổng kết nhiệm kỳ, báo cáo kiểm điểm BCH, Ban kiểm tra, báo cáo tài chính"),
        (4, "Báo cáo số lượng hội viên (nêu rõ số hội viên chính thức)"),
        (16, "Sơ yếu lý lịch, phiếu lý lịch tư pháp số 1 của nhân sự dự kiến Chủ tịch"),
        (17, "Dự thảo những nội dung thảo luận và quyết định tại đại hội"),
    ],
    _BAT_THUONG: [
        (5, "Văn bản báo cáo tổ chức đại hội bất thường"),
        (12, "Nghị quyết của Ban chấp hành về việc tổ chức đại hội bất thường"),
        (7, "Dự kiến thời gian, địa điểm, số đại biểu, chương trình đại hội"),
        (17, "Dự thảo những nội dung thảo luận và quyết định tại đại hội"),
    ],
    _THANH_LAP: [
        (10, "Văn bản báo cáo tổ chức đại hội thành lập của Ban vận động"),
        (8, "Đề án nhân sự (bản gốc)"),
        (9, "Dự kiến thời gian, địa điểm, chương trình đại hội (bản gốc)"),
        (2, "Ý kiến đồng ý / sơ yếu lý lịch, phiếu lý lịch tư pháp số 1 của nhân sự dự kiến Chủ tịch"),
    ],
}


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
        return _NQ_DAI_HOI if "dai_hoi" in t else _NQ_BCH
    if "kiem_tra" in t:
        return _BKT
    if "kiem_diem" in t:
        return _KIEM_DIEM
    if "tai_chinh" in t:
        return _TAI_CHINH
    if "tong_ket" in t or "chinh_tri" in t:
        return _TONG_KET
    if "hoi_vien" in t:
        return _HOI_VIEN
    if "doi_ten" in t:
        return _DOI_TEN
    if "chuong_trinh" in t or "du_kien" in t:
        return _DU_KIEN
    if "de_an" in t:
        return _DE_AN
    if "danh_sach" in t or "ban_chap_hanh" in t:
        return _DS_BCH
    if "y_kien" in t or "cu_can_bo" in t or "dong_y" in t:
        return _Y_KIEN
    if "bao_cao" in t or "to_chuc" in t:
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
    if "nghi quyet dai hoi" in head:
        return _NQ_DAI_HOI
    if "nghi quyet" in head and ("quyet nghi" in h or "dieu 1" in h):
        return _NQ_BCH
    if "bao cao" in head and "ban kiem tra" in head:
        return _BKT
    if "bao cao kiem diem" in head:
        return _KIEM_DIEM
    if "bao cao tai chinh" in head or "quyet toan" in head:
        return _TAI_CHINH
    if "bao cao tong ket" in head or "bao cao chinh tri" in head:
        return _TONG_KET
    if "don" in head and "doi ten" in head:
        return _DOI_TEN
    if "cu can bo" in head or "gioi thieu can bo" in head or "gioi thieu nhan su" in head:
        return _Y_KIEN
    if "to chuc dai hoi" in head and "kinh gui" in h:
        return _BAO_CAO
    if "hoi vien" in head and ("so luong" in head or "danh sach hoi vien" in head):
        return _HOI_VIEN
    if "de an" in head and "nhan su" in head:
        return _DE_AN
    if "danh sach" in head and ("ban chap hanh" in head or "bch" in head):
        return _DS_BCH
    if "chuong trinh dai hoi" in head:
        return _DU_KIEN
    if any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc")):
        return _CCCD
    return _OTHER


def _inherit_continuations(typed: list[tuple[dict, str]],
                           pages_by_file: dict[int, dict[int, str]]) -> list[tuple[dict, str]]:
    """Đoạn `other` không có quốc hiệu là trang nối tiếp của giấy tờ ngay trước — kể cả sang file sau (hồ sơ mẫu:
    Điều lệ nằm cuối file 1 và 6 trang đầu file 2, trang đầu file 2 không có tiêu đề)."""
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


def _case(typed: list[tuple[dict, str]], pages_by_file: dict[int, dict[int, str]]) -> tuple[str, bool]:
    """(loại đại hội, đọc được từ hồ sơ hay không) — theo văn bản báo cáo / đơn đổi tên / Nghị quyết BCH."""
    text = " ".join(
        _fold(_segment_text(segment, pages_by_file))[:2000]
        for segment, doc_type in typed if doc_type in (_BAO_CAO, _DOI_TEN, _NQ_BCH)
    )
    if "bat thuong" in text:
        return _BAT_THUONG, True
    if "dai hoi thanh lap" in text or "ban van dong thanh lap" in text:
        return _THANH_LAP, True
    return _NHIEM_KY, bool(text)


def _mentions_schedule(page: str) -> bool:
    h = _fold(page)
    return "dia diem" in h or "thoi gian" in h


def build_plan_items(
    raw_files: list[dict],
    segments: list[dict],
    file_meta: dict[int, dict],
    pages_by_file: dict[int, dict[int, str]],
) -> tuple[list[dict], list[dict], list[str], str]:
    """Đoạn đã hợp lệ → (attachments, classified, warnings, loại đại hội). Thuần tất định, không gọi OCR/LLM."""
    typed: list[tuple[dict, str]] = []
    for segment in segments:
        doc_type = segment["type"]
        # LLM là chính; rule OCR chỉ vá khi LLM trả other/không rõ.
        if doc_type == _OTHER:
            doc_type = _rule_type(_segment_text(segment, pages_by_file))
        typed.append((segment, doc_type))
    typed = _merge_adjacent(_inherit_continuations(typed, pages_by_file))
    found = {doc_type for _, doc_type in typed}
    case, case_known = _case(typed, pages_by_file)

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
        row_idx = _ROUTE.get(doc_type, {}).get(case)
        if row_idx is None:
            skipped_pages.append(f"{file.get('name')} trang {segment['pageFrom']}-{segment['pageTo']}")
            classified.append({**base, "target": "skip"})
            continue
        by_row.setdefault(row_idx, []).append((segment, doc_type))
        classified.append({**base, "componentIndex": row_idx})

    # --- Không có văn bản dự kiến riêng: đính chung văn bản báo cáo (nêu thời gian, địa điểm) ---
    du_kien_row = _ROUTE[_DU_KIEN][case]
    du_kien_from_bao_cao = False
    if du_kien_row not in by_row:
        bao_cao_segments = [segment for segment, doc_type in typed if doc_type == _BAO_CAO]
        if any(_mentions_schedule(_segment_text(s, pages_by_file)) for s in bao_cao_segments):
            du_kien_from_bao_cao = True
            for segment in bao_cao_segments:
                by_row[du_kien_row] = by_row.get(du_kien_row, []) + [(segment, _BAO_CAO)]
                classified.append({"fileIndex": segment["fileIndex"],
                                   "fileName": raw_files[segment["fileIndex"]].get("name"),
                                   "pageFrom": segment["pageFrom"], "pageTo": segment["pageTo"], "type": _BAO_CAO,
                                   "componentIndex": du_kien_row, "shared": True})

    order = {t: i for i, t in enumerate(_ORDER)}
    attachments: list[dict] = []
    used_names: set[str] = set()
    for row_idx in sorted(by_row):
        row = _ROWS[row_idx]
        parts = sorted(by_row[row_idx], key=lambda p: (order.get(p[1], 99), p[0]["fileIndex"], p[0]["pageFrom"]))
        first_segment = parts[0][0]
        single = len(parts) == 1 and not (du_kien_from_bao_cao and row_idx == du_kien_row)
        base_name = (first_segment.get("documentName") if single else "") or row["documentName"]
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

    # --- Cảnh báo ---
    if not case_known:
        warnings.append("Không tìm thấy văn bản báo cáo / Nghị quyết BCH để xác định loại đại hội — đã đính theo "
                        "trường hợp đại hội nhiệm kỳ, kiểm tra lại.")
    elif case != _NHIEM_KY:
        warnings.append(f"Hồ sơ báo cáo tổ chức {_CASE_LABEL[case]} — đã đính vào các dòng của trường hợp này.")
    if skipped_pages:
        warnings.append("Không xác định được loại giấy tờ hoặc giấy tờ không thuộc trường hợp "
                        f"{_CASE_LABEL[case]} (bỏ qua, đính thủ công nếu cần): " + "; ".join(skipped_pages))
    if du_kien_from_bao_cao:
        warnings.append(f"Hồ sơ không có văn bản dự kiến chương trình đại hội riêng — dòng {du_kien_row} đính chung "
                        "văn bản báo cáo (nêu thời gian, địa điểm, số đại biểu); cần bổ sung chương trình đại hội "
                        "chi tiết nếu văn bản báo cáo chưa có.")
    for row_idx, label in _REQUIRED[case]:
        if row_idx not in by_row:
            warnings.append(f"Chưa có {label} (dòng {row_idx}) — cần bổ sung.")
    if case == _NHIEM_KY and 11 in by_row and _TAI_CHINH not in found:
        warnings.append("Dòng 11 chưa có Báo cáo tài chính riêng của hội — cần bổ sung.")
    if case != _THANH_LAP and _Y_KIEN not in found:
        warnings.append("Không thấy văn bản ý kiến đồng ý / cử cán bộ (dòng 14) — bắt buộc khi nhân sự dự kiến Ban "
                        "chấp hành, Ban thường vụ là cán bộ, công chức, viên chức.")
    if _SYLL in found and _LLTP not in found:
        warnings.append("Chưa có Phiếu lý lịch tư pháp số 1 của nhân sự dự kiến Chủ tịch — cần bổ sung, trừ khi người "
                        "đó là cán bộ, công chức, viên chức (kể cả đã nghỉ hưu) được cơ quan có thẩm quyền đồng ý "
                        "bằng văn bản hoặc đang là Chủ tịch hội nhiệm kỳ hiện tại.")
    return attachments, classified, warnings, case


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
    attachments, classified, warnings, case = build_plan_items(raw_files, segments, file_meta, pages_by_file)
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
            "loaiDaiHoi": case,
            "classified": classified,
            "rows": [{"componentIndex": k, **row} for k, row in _ROWS.items()],
        },
        "ocr_text": join_ocr_documents(indexed_ocr),
        "llm_output": {"documents": raw_segments},
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
