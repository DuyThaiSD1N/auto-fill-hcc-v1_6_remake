"""Đính kèm bước "Thành phần hồ sơ" cho "Đăng ký biến động ... do chia, tách, hợp nhất, sáp nhập tổ chức..." (1.013977,
cổng DVC Đà Nẵng — Angular mat-table, engine FE `attp-row`).

ENGINE TÁCH/GỘP (như dang_ky_tai_san_gan_lien_thua_dat_da_cap_gcn): OCR per-file có header "Trang n/m" → LLM gán
KHOẢNG TRANG + loại cho từng đoạn → hậu xử lý tất định (chống chồng/thiếu trang) → GOM các đoạn cùng dòng thành
MỘT file gộp (`sourceSegments` nhiều đoạn, giấy tờ chính trước, giấy tờ "đính kèm chung" sau). FE tự trích/gộp
trang thành một PDF cho mỗi dòng.

Bảng 9 dòng (thứ tự trên cổng; dòng 1 "Bản chính", còn lại "Bản sao"):
  [1] (1) Đơn Mẫu số 18                        ← don_mau_18 + đính kèm chung to_khai_thue (LPTB, SDĐPNN)
  [2] (2) Giấy chứng nhận đã cấp               ← gcn_da_cap + đính kèm chung giay_to_tai_san (GPXD, thẩm định)
  [3] (3) Văn bản về việc đại diện             ← van_ban_dai_dien + đính kèm chung van_ban_the_chap (CV ngân hàng)
  [4] (4) QĐ phê duyệt quy hoạch XD chi tiết   ← qd_quy_hoach_chi_tiet
  [5] (7) Mảnh trích đo bản đồ địa chính       ← manh_trich_do
  [6] (5) Bản vẽ tách thửa, hợp thửa Mẫu 22    ← ban_ve_tach_hop_thua
  [7] (6) GCN đăng ký doanh nghiệp / VB thành lập ← gcn_dang_ky_doanh_nghiep + đính kèm chung bang_thay_doi_dkdn
  [8] (4) QĐ/VB chia, tách, hợp nhất, sáp nhập, chuyển đổi ← qd_to_chuc_lai (QĐ + biên bản họp HĐTV)
  [9] (4) QĐ phê duyệt điều chỉnh QHXD chi tiết ← qd_dieu_chinh_quy_hoach + nghia_vu_tai_chinh
Chứng từ nghĩa vụ tài chính chỉ vào dòng 9 khi có QĐ điều chỉnh quy hoạch; không thì đính chung dòng 1.
CCCD không có dòng → bỏ qua (chỉ dùng ở bước điền thông tin).
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
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON18 = "don_mau_18"
_TO_KHAI_THUE = "to_khai_thue"
_GCN = "gcn_da_cap"
_TAI_SAN = "giay_to_tai_san"
_DAI_DIEN = "van_ban_dai_dien"
_THE_CHAP = "van_ban_the_chap"
_QH_CHI_TIET = "qd_quy_hoach_chi_tiet"
_TRICH_DO = "manh_trich_do"
_TACH_HOP = "ban_ve_tach_hop_thua"
_DKDN = "gcn_dang_ky_doanh_nghiep"
_BANG_DKDN = "bang_thay_doi_dkdn"
_TO_CHUC_LAI = "qd_to_chuc_lai"
_DIEU_CHINH_QH = "qd_dieu_chinh_quy_hoach"
_NGHIA_VU_TC = "nghia_vu_tai_chinh"
_CCCD = "cccd"
_OTHER = "other"
_ALLOWED = {
    _DON18, _TO_KHAI_THUE, _GCN, _TAI_SAN, _DAI_DIEN, _THE_CHAP, _QH_CHI_TIET, _TRICH_DO, _TACH_HOP, _DKDN,
    _BANG_DKDN, _TO_CHUC_LAI, _DIEU_CHINH_QH, _NGHIA_VU_TC, _CCCD, _OTHER,
}

# componentName = ĐOẠN TEXT ĐẶC TRƯNG DUY NHẤT của dòng (FE khớp substring fold); componentIndex = STT dòng
# (1-based) làm gợi ý. Dòng 4 và 9 cùng mở đầu "Quyết định phê duyệt" → dòng 4 dùng "phê duyệt quy hoạch", dòng 9
# dùng "phê duyệt điều chỉnh quy hoạch". `types` = loại giấy tờ vào dòng, theo THỨ TỰ trong file gộp.
_ROWS: dict[int, dict[str, Any]] = {
    1: {
        "componentName": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18",
        "documentName": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18)",
        "loaiBan": "Bản chính",
        "types": [_DON18, _TO_KHAI_THUE, _NGHIA_VU_TC],
    },
    2: {
        "componentName": "Giấy chứng nhận đã cấp",
        "documentName": "Giấy chứng nhận đã cấp",
        "loaiBan": "Bản sao",
        "types": [_GCN, _TAI_SAN],
    },
    3: {
        "componentName": "Văn bản về việc đại diện theo quy định của pháp luật về dân sự",
        "documentName": "Văn bản về việc đại diện",
        "loaiBan": "Bản sao",
        "types": [_DAI_DIEN, _THE_CHAP],
    },
    4: {
        "componentName": "Quyết định phê duyệt quy hoạch xây dựng chi tiết",
        "documentName": "Quyết định phê duyệt quy hoạch xây dựng chi tiết",
        "loaiBan": "Bản sao",
        "types": [_QH_CHI_TIET],
    },
    5: {
        "componentName": "Mảnh trích đo bản đồ địa chính thửa đất",
        "documentName": "Mảnh trích đo bản đồ địa chính thửa đất",
        "loaiBan": "Bản sao",
        "types": [_TRICH_DO],
    },
    6: {
        "componentName": "Bản vẽ tách thửa đất, hợp thửa đất theo Mẫu số 22",
        "documentName": "Bản vẽ tách thửa đất, hợp thửa đất (Mẫu số 22)",
        "loaiBan": "Bản sao",
        "types": [_TACH_HOP],
    },
    7: {
        "componentName": "Giấy chứng nhận đăng ký doanh nghiệp hoặc văn bản về việc thành lập tổ chức",
        "documentName": "Giấy chứng nhận đăng ký doanh nghiệp",
        "loaiBan": "Bản sao",
        "types": [_DKDN, _BANG_DKDN],
    },
    8: {
        "componentName": "văn bản về việc chia, tách, hợp nhất, sáp nhập, chuyển đổi mô hình tổ chức",
        "documentName": "Quyết định về việc chia, tách, hợp nhất, sáp nhập, chuyển đổi tổ chức",
        "loaiBan": "Bản sao",
        "types": [_TO_CHUC_LAI],
    },
    9: {
        "componentName": "Quyết định phê duyệt điều chỉnh quy hoạch xây dựng chi tiết",
        "documentName": "Quyết định phê duyệt điều chỉnh quy hoạch xây dựng chi tiết",
        "loaiBan": "Bản sao",
        "types": [_DIEU_CHINH_QH, _NGHIA_VU_TC],
    },
}
# Loại CHÍNH của từng dòng (loại đầu tiên); còn lại là "đính kèm chung".
_MAIN_TYPES = {row["types"][0]: idx for idx, row in _ROWS.items()}

_PAGE_HEADER_RE = re.compile(
    r"(?im)^[\t ─-╿-]*(?:trang|page)\s+(\d+)\s*/\s*(\d+)[\t ─-╿-]*$"
)


# ---------------- Segment engine (copy pattern dang_ky_tai_san_gan_lien_thua_dat_da_cap_gcn) ----------------
# Hồ sơ thủ tục này hay là PDF gộp 50-60 trang: 2000 ký tự/trang làm prompt vượt ngữ cảnh model chính. Phân đoạn
# chỉ cần tiêu đề + số trang đầu trang nên 800 ký tự là đủ.
def _truncate(text: str, limit: int = 800) -> str:
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


def _normalize_type(value: str) -> str:
    t = re.sub(r"[\s-]+", "_", _fold(value or ""))
    if t in _ALLOWED:
        return t
    if "the_chap" in t or "ngan_hang" in t or "bao_dam" in t:
        return _THE_CHAP
    if "dai_dien" in t or "uy_quyen" in t:
        return _DAI_DIEN
    if "mau_18" in t or "bien_dong" in t or t == "don":
        return _DON18
    if "to_khai" in t or "lptb" in t or "le_phi" in t or "thue" in t:
        return _TO_KHAI_THUE
    if "dieu_chinh" in t and "quy_hoach" in t:
        return _DIEU_CHINH_QH
    if "quy_hoach" in t:
        return _QH_CHI_TIET
    if "trich_do" in t:
        return _TRICH_DO
    if "tach_thua" in t or "hop_thua" in t or "mau_22" in t:
        return _TACH_HOP
    if "tinh_hinh_thay_doi" in t or "bang_thay_doi" in t:
        return _BANG_DKDN
    if "doanh_nghiep" in t or "dkdn" in t or "thanh_lap" in t:
        return _DKDN
    if "hdtv" in t or "hoi_dong" in t or "chia_tach" in t or "sap_nhap" in t or "hop_nhat" in t or "bien_ban" in t:
        return _TO_CHUC_LAI
    if "nghia_vu" in t or "nop_tien" in t or "bien_lai" in t:
        return _NGHIA_VU_TC
    if "giay_phep" in t or "gpxd" in t or "tham_dinh" in t or "nghiem_thu" in t or "tai_san" in t:
        return _TAI_SAN
    if "gcn" in t or "chung_nhan" in t:
        return _GCN
    if "cccd" in t or "can_cuoc" in t or "cmnd" in t:
        return _CCCD
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


def _segment_text(segment: dict, page_text_by_file: dict[int, dict[int, str]],
                  full_text_by_file: dict[int, str]) -> str:
    pages = page_text_by_file.get(segment["fileIndex"]) or {}
    if not pages:
        return full_text_by_file.get(segment["fileIndex"], "")
    return "\n".join(pages.get(p, "") for p in range(segment["pageFrom"], segment["pageTo"] + 1)).strip()


def _source_segment(segment: dict, page_count: int) -> dict:
    indexes = None
    if segment["pageFrom"] != 1 or segment["pageTo"] != page_count:
        indexes = list(range(segment["pageFrom"] - 1, segment["pageTo"]))
    return {"fileIndex": segment["fileIndex"], "pageIndexes": indexes}


# --- Rule fallback theo OCR (khi LLM không phân loại được đoạn) ---
def _rule_type(text: str) -> str:
    """THỨ TỰ QUAN TRỌNG: Đơn Mẫu 18 kê "(1) Giấy chứng nhận đã cấp; (3) Giấy ủy quyền" → nhận Đơn TRƯỚC. Tờ khai
    thuế, công văn ngân hàng, giấy phép xây dựng, quyết định HĐTV đều nhắc GCN / mã số doanh nghiệp → nhận TRƯỚC
    GCN và GCN đăng ký doanh nghiệp. Quyết định điều chỉnh quy hoạch nhận TRƯỚC quyết định quy hoạch."""
    h = _fold(text)
    if not h:
        return _OTHER
    if "don dang ky bien dong" in h or "mau so 18" in h:
        return _DON18
    if (
        "le phi truoc ba" in h
        or "01/lptb" in h
        or "thue su dung dat phi nong nghiep" in h
        or "tk-sddpnn" in h
    ) and "to khai" in h:
        return _TO_KHAI_THUE
    if "ben duoc uy quyen" in h or "hop dong uy quyen" in h:
        return _DAI_DIEN
    if "chap thuan" in h and ("the chap" in h or "tai san bao dam" in h):
        return _THE_CHAP
    if "tinh hinh thay doi dang ky doanh nghiep" in h:
        return _BANG_DKDN
    if "dieu chinh quy hoach" in h and "chi tiet" in h and "phe duyet" in h:
        return _DIEU_CHINH_QH
    if (
        ("quyet dinh" in h or "bien ban hop" in h or "nghi quyet" in h)
        and ("hoi dong thanh vien" in h or "dai hoi dong co dong" in h or "hoi dong quan tri" in h)
    ):
        return _TO_CHUC_LAI
    if "giay phep xay dung" in h or "ket qua tham dinh" in h or "nghiem thu hoan thanh" in h:
        return _TAI_SAN
    if "giay chung nhan dang ky doanh nghiep" in h and "ma so doanh nghiep" in h:
        return _DKDN
    if "quyet dinh" in h and any(
        m in h for m in ("chia, tach", "hop nhat", "sap nhap", "chuyen doi loai hinh doanh nghiep", "to chuc lai")
    ):
        return _TO_CHUC_LAI
    if "phe duyet" in h and "quy hoach" in h and "chi tiet" in h:
        return _QH_CHI_TIET
    if "manh trich do" in h or "trich do ban do dia chinh" in h:
        return _TRICH_DO
    if "ban ve tach thua" in h or "tach thua dat, hop thua dat" in h or "mau so 22" in h:
        return _TACH_HOP
    if "giay nop tien vao ngan sach" in h or "bien lai thu" in h:
        return _NGHIA_VU_TC
    if "giay chung nhan" in h and (
        "quyen su dung dat" in h or "quyen so huu nha" in h or "so vao so cap" in h or "thua dat so" in h
    ):
        return _GCN
    # Trang trong / trang bổ sung của GCN thường không in lại chữ "Giấy chứng nhận".
    if "so vao so cap" in h or ("thua dat so" in h and "to ban do so" in h) or "trang bo sung" in h:
        return _GCN
    if any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu")):
        return _CCCD
    return _OTHER


def _merge_adjacent(typed: list[tuple[dict, str]]) -> list[tuple[dict, str]]:
    """Gộp các đoạn LIỀN KỀ cùng file + cùng loại (vd GCN bìa trang 1 + trang bổ sung trang 2-3) thành 1 đoạn."""
    merged: list[tuple[dict, str]] = []
    for segment, doc_type in typed:
        if merged:
            prev_segment, prev_type = merged[-1]
            if (
                doc_type == prev_type
                and prev_segment["fileIndex"] == segment["fileIndex"]
                and prev_segment["pageTo"] + 1 == segment["pageFrom"]
            ):
                merged[-1] = ({**prev_segment, "pageTo": segment["pageTo"]}, prev_type)
                continue
        merged.append((segment, doc_type))
    return merged


def _row_of(doc_type: str, found: set[str]) -> int | None:
    """Dòng cho một loại giấy tờ. Chứng từ nghĩa vụ tài chính chỉ vào dòng 9 khi có QĐ điều chỉnh quy hoạch."""
    if doc_type == _NGHIA_VU_TC:
        return 9 if _DIEU_CHINH_QH in found else 1
    for idx, row in _ROWS.items():
        if doc_type in row["types"]:
            return idx
    return None


def build_plan_items(
    raw_files: list[dict],
    segments: list[dict],
    file_meta: dict[int, dict],
    page_text_by_file: dict[int, dict[int, str]],
    full_text_by_file: dict[int, str],
) -> tuple[list[dict], list[dict], list[str]]:
    """Đoạn đã hợp lệ → (attachments, classified, warnings). Thuần tất định, không gọi OCR/LLM."""
    typed: list[tuple[dict, str]] = []
    for segment in segments:
        doc_type = segment["type"]
        # LLM là chính; rule OCR chỉ vá khi LLM trả other/không rõ.
        if doc_type == _OTHER:
            doc_type = _rule_type(_segment_text(segment, page_text_by_file, full_text_by_file))
        typed.append((segment, doc_type))
    typed = _merge_adjacent(typed)
    found = {doc_type for _, doc_type in typed}

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
        row_idx = _row_of(doc_type, found)
        if row_idx is None:
            skipped_pages.append(f"{file.get('name')} trang {segment['pageFrom']}-{segment['pageTo']}")
            classified.append({**base, "type": _OTHER, "target": "skip"})
            continue
        by_row.setdefault(row_idx, []).append((segment, doc_type))
        classified.append({**base, "componentIndex": row_idx,
                           "shared": doc_type not in _MAIN_TYPES or _MAIN_TYPES[doc_type] != row_idx})

    attachments: list[dict] = []
    used_names: set[str] = set()
    for row_idx in sorted(by_row):
        row = _ROWS[row_idx]
        order = {t: i for i, t in enumerate(row["types"])}
        parts = sorted(by_row[row_idx], key=lambda p: (order.get(p[1], 99), p[0]["fileIndex"], p[0]["pageFrom"]))
        first_segment = parts[0][0]
        base_name = (first_segment.get("documentName") if len(parts) == 1 else "") or row["documentName"]
        document_name = _unique_name(base_name, used_names, row["documentName"])
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

    if skipped_pages:
        warnings.append("Không xác định được loại giấy tờ (bỏ qua, đính thủ công nếu cần): " + "; ".join(skipped_pages))

    if _DON18 not in found:
        warnings.append("Không tìm thấy Đơn đăng ký biến động Mẫu số 18 (dòng 1, bắt buộc) — vui lòng đính tay.")
    if _GCN not in found:
        warnings.append("Không tìm thấy Giấy chứng nhận đã cấp (dòng 2, bắt buộc) — vui lòng đính tay.")
    if not found & {_DKDN, _TO_CHUC_LAI, _QH_CHI_TIET, _DIEU_CHINH_QH}:
        warnings.append(
            "Hồ sơ chưa có Giấy chứng nhận đăng ký doanh nghiệp / quyết định chia, tách, sáp nhập, đổi tên (dòng 7, "
            "8) hay quyết định phê duyệt (điều chỉnh) quy hoạch chi tiết (dòng 4, 9) — kiểm tra, bổ sung."
        )
    elif _DKDN in found and _TO_CHUC_LAI not in found:
        warnings.append(
            "Chưa thấy quyết định / văn bản về việc chia, tách, hợp nhất, sáp nhập, chuyển đổi, đổi tên tổ chức "
            "(dòng 8) — kiểm tra, bổ sung nếu có."
        )
    if _THE_CHAP in found and _DAI_DIEN not in found:
        warnings.append("Có công văn chấp thuận của bên nhận thế chấp nhưng chưa có giấy ủy quyền — đã đính công "
                        "văn vào dòng 3, kiểm tra lại.")
    return attachments, classified, warnings


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
