"""Đính kèm "Thành phần hồ sơ" cho "Đăng ký biến động 1.013980" (cổng DVC Đà Nẵng — Angular, engine FE `attp-row`).

Bảng có 12 dòng, gộp nhiều trường hợp nên có dòng TRÙNG nội dung (1/9 Đơn, 3/8/11 Văn bản đại diện, 5/10 Giấy chứng
nhận). Mỗi loại giấy tờ chỉ đính vào DÒNG ĐẦU của nó; componentName là đoạn chữ ĐẶC TRƯNG của dòng (FE khớp
substring sau khi fold) + componentIndex để chốt đúng dòng khi tên trùng:
  [1]  (1) Đơn đăng ký biến động … Mẫu số 18          ← cả giấy tờ KHÔNG có dòng riêng
  [2]  Hợp đồng mua bán tài sản công …
  [3]  (6) Văn bản về việc đại diện …
  [4]  Bản vẽ tách thửa đất, hợp thửa đất (Mẫu số 22)
  [5]  (2) Bản gốc Giấy chứng nhận đã cấp
  [6]  Một trong các văn bản: hợp đồng chuyển nhượng / mua bán tài sản đấu giá / thế chấp …
  [7]  Mảnh trích đo bản đồ địa chính
  [12] Biên bản hòa giải thành / quyết định giải quyết tranh chấp / bản án, quyết định thi hành án / Trọng tài
Hồ sơ hay quét GỘP tất cả vào MỘT PDF vài chục trang: file đó được xếp theo giấy tờ ở trang đầu (Đơn) và chỉ đính
MỘT lần ở dòng 1 — các dòng khác đã nằm trong file chung, không đính lại.

Tờ khai thuế/lệ phí trước bạ, hóa đơn, giấy nộp tiền, đơn cam kết, công văn, giấy tiếp nhận hồ sơ, văn bản thỏa
thuận hộ gia đình/vợ chồng không có dòng riêng → đính CHUNG dòng 1 sau Đơn (giữ nguyên từng tệp) và cảnh báo.
CCCD chỉ đối chiếu → bỏ qua. Phân loại LLM-primary, rule keyword dự phòng.
"""

import base64
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.dang_ky_bien_dong_thoa_thuan_thanh_vien_ho_gia_dinh_da_nang.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client
from app.services.pdf_utils import trim_files_for_classify

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
# PDF gộp vài chục trang OCR đủ thì quá timeout 100s của extension; loại giấy tờ nằm ở trang 1-2 → chỉ OCR 2
# trang đầu để phân loại; tệp đính lên cổng vẫn là bản gốc đủ trang.
_OCR_MAX_PAGES = 2
# File PDF từ ngần này trang trở lên coi là file GỘP cả bộ hồ sơ.
_MERGED_MIN_PAGES = 6
_LOAI_BAN = "Bản chính"

_DON = "don_bien_dong"
_HD_TAI_SAN_CONG = "hop_dong_tai_san_cong"
_VB_DAI_DIEN = "van_ban_dai_dien"
_BAN_VE = "ban_ve_tach_hop_thua"
_GCN = "giay_chung_nhan"
_HD_CHUYEN_QUYEN = "hop_dong_chuyen_quyen"
_TRICH_DO = "manh_trich_do"
_GIAI_QUYET = "van_ban_giai_quyet_tranh_chap"
_THOA_THUAN = "van_ban_thoa_thuan"
_CCCD = "cccd"
_OTHER = "other"

_ROWS: dict[str, dict[str, Any]] = {
    _DON: {"componentIndex": 1, "componentName": "(1) Đơn đăng ký biến động đất đai",
           "documentName": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18)"},
    _HD_TAI_SAN_CONG: {"componentIndex": 2, "componentName": "Hợp đồng mua bán tài sản công",
           "documentName": "Hợp đồng mua bán tài sản công là quyền sử dụng đất"},
    _VB_DAI_DIEN: {"componentIndex": 3, "componentName": "(6) Văn bản về việc đại diện",
           "documentName": "Văn bản về việc đại diện (giấy ủy quyền)"},
    _BAN_VE: {"componentIndex": 4, "componentName": "Bản vẽ tách thửa đất, hợp thửa đất",
           "documentName": "Bản vẽ tách thửa đất, hợp thửa đất (Mẫu số 22)"},
    _GCN: {"componentIndex": 5, "componentName": "(2) Bản gốc Giấy chứng nhận đã cấp",
           "documentName": "Bản gốc Giấy chứng nhận đã cấp"},
    _HD_CHUYEN_QUYEN: {"componentIndex": 6,
           "componentName": "Hợp đồng mua bán tài sản đấu giá quyền sử dụng đất",
           "documentName": "Hợp đồng chuyển nhượng / mua bán tài sản đấu giá / thế chấp quyền sử dụng đất"},
    _TRICH_DO: {"componentIndex": 7, "componentName": "Mảnh trích đo bản đồ địa chính",
           "documentName": "Mảnh trích đo bản đồ địa chính thửa đất"},
    _GIAI_QUYET: {"componentIndex": 12, "componentName": "Biên bản hòa giải thành",
           "documentName": "Biên bản hòa giải thành / quyết định giải quyết tranh chấp / bản án / quyết định thi hành án"},
}
for _r in _ROWS.values():
    _r["loaiBan"] = _LOAI_BAN

# Không có dòng riêng → đính CHUNG dòng Đơn.
_TO_DON_ROW = {_THOA_THUAN, _OTHER}
_SKIP_DOCS = {_CCCD}
_ALLOWED_DOC_TYPES = set(_ROWS) | _TO_DON_ROW | _SKIP_DOCS

_DISPLAY = {
    _THOA_THUAN: "văn bản thỏa thuận hộ gia đình/vợ chồng",
    _OTHER: "giấy tờ không có dòng riêng",
}


def _is_identity_text(text: str) -> bool:
    h = _fold(text)
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport"))


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR 1-2 trang đầu (dự phòng cho LLM). Dấu hiệu đặc trưng trước, GCN sau cùng vì mọi
    hợp đồng/quyết định đều nhắc tới "Giấy chứng nhận quyền sử dụng đất số …"."""
    h = _fold(text)
    if not h:
        return ""
    # Giấy tiếp nhận hồ sơ liệt kê tên đủ loại giấy tờ (kể cả "Đơn đăng ký biến động") → chặn trước.
    if "giay tiep nhan ho so" in h or "hen tra ket qua" in h:
        return _OTHER
    if "don dang ky bien dong" in h:
        return _DON
    if "giay uy quyen" in h or "hop dong uy quyen" in h or "ben duoc uy quyen" in h:
        return _VB_DAI_DIEN
    if "ban ve tach thua" in h or "mau so 22" in h:
        return _BAN_VE
    if "manh trich do" in h:
        return _TRICH_DO
    if "tai san cong" in h and "hop dong" in h:
        return _HD_TAI_SAN_CONG
    if "hop dong" in h and ("dau gia" in h or "chuyen nhuong" in h or "the chap" in h) \
            and "quyen su dung dat" in h:
        return _HD_CHUYEN_QUYEN
    if "bien ban cuoc dau gia" in h or "ket qua dau gia" in h:
        return _HD_CHUYEN_QUYEN
    if "hoa giai thanh" in h or "ban an" in h or "toa an nhan dan" in h or "trong tai thuong mai" in h:
        return _GIAI_QUYET
    if "thi hanh an" in h and ("quyet dinh" in h or "bien ban giao" in h or "thong bao" in h):
        return _GIAI_QUYET
    if "thoa thuan" in h and ("ho gia dinh" in h or "vo va chong" in h or "vo chong" in h):
        return _THOA_THUAN
    if "giay chung nhan" in h and "quyen su dung dat" in h:
        return _GCN
    if _is_identity_text(h):
        return _CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if text in _ALLOWED_DOC_TYPES:
        return text
    if "don" in text and "bien dong" in text:
        return _DON
    if "dai dien" in text or "uy quyen" in text:
        return _VB_DAI_DIEN
    if "tach" in text or "hop thua" in text or "22" in text:
        return _BAN_VE
    if "trich do" in text:
        return _TRICH_DO
    if "tai san cong" in text:
        return _HD_TAI_SAN_CONG
    if "tranh chap" in text or "ban an" in text or "hoa giai" in text or "thi hanh an" in text:
        return _GIAI_QUYET
    if "thoa thuan" in text:
        return _THOA_THUAN
    if "hop dong" in text or "chuyen nhuong" in text or "dau gia" in text or "the chap" in text:
        return _HD_CHUYEN_QUYEN
    if "gcn" in text or "chung nhan" in text or "so do" in text:
        return _GCN
    if "cccd" in text or "can cuoc" in text or "cmnd" in text or "ho chieu" in text:
        return _CCCD
    return _OTHER


def _pdf_page_count(file: dict) -> int:
    data_url = str(file.get("dataUrl") or "")
    header, sep, b64 = data_url.partition(",")
    if not sep or "pdf" not in header.lower():
        return 1
    try:
        import fitz  # pymupdf

        doc = fitz.open(stream=base64.b64decode(b64), filetype="pdf")
        try:
            return int(doc.page_count)
        finally:
            doc.close()
    except Exception:  # noqa: BLE001 — đếm trang chỉ để cảnh báo, lỗi thì coi như 1 trang
        return 1


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=600, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    out: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        out[idx] = _normalize_doc_type(str(item.get("docType") or item.get("type") or ""))
    return out


def _build_row_item(file: dict, file_index: int, row_type: str, detected_type: str) -> dict:
    row = _ROWS[row_type]
    return {
        "fileIndex": file_index,
        "fileName": str(file.get("name") or f"file-{file_index + 1}"),
        "documentName": row["documentName"],
        "componentName": row["componentName"],
        "componentIndex": row["componentIndex"],
        "loaiBan": row["loaiBan"],
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": detected_type,
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, str] | None = None,
    page_counts: dict[int, int] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    page_counts = page_counts or {}
    by_name = {item.get("name"): item for item in ocr_results}
    items: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    shared: list[str] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = str(by_name.get(file_name, {}).get("text") or "")
        llm_type = llm_types.get(idx, "")
        rule_type = _rule_doc_type(text)
        if rule_type == _DON:
            # File gộp có Đơn ở trang đầu: LLM hay đoán theo giấy tờ khác cùng trang (tờ khai, GCN) → Đơn thắng.
            doc_type = _DON
            source = "rule" if not llm_type else ("llm" if llm_type == _DON else "priority-don")
        elif llm_type and llm_type != _OTHER:
            doc_type, source = llm_type, "llm"
        elif rule_type:
            doc_type, source = rule_type, "rule"
        elif text.strip():
            # Đọc được chữ nhưng không thuộc dòng nào (tờ khai, hóa đơn…) → đính chung dòng Đơn.
            doc_type, source = _OTHER, "llm" if llm_type == _OTHER else "unknown"
        else:
            doc_type, source = "", "unknown"

        if doc_type in _SKIP_DOCS:
            classified.append({"fileName": file_name, "docType": doc_type, "source": source, "skipped": True})
            continue
        if doc_type in _ROWS:
            items.append(_build_row_item(file, idx, doc_type, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "source": source})
            pages = page_counts.get(idx, 1)
            if pages >= _MERGED_MIN_PAGES:
                warnings.append(
                    f"File '{file_name}' gộp {pages} trang → đính MỘT lần ở dòng {_ROWS[doc_type]['componentIndex']} "
                    "(theo giấy tờ ở trang đầu); các giấy tờ khác trong file (giấy ủy quyền, Giấy chứng nhận, hợp "
                    "đồng, văn bản thi hành án…) đã nằm trong file chung, không đính lại ở dòng riêng."
                )
            continue
        if doc_type in _TO_DON_ROW:
            items.append(_build_row_item(file, idx, _DON, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "source": source, "row": _DON})
            shared.append(f"{file_name} ({_DISPLAY[doc_type]})")
            continue

        warnings.append(f"Không đọc được nội dung file '{file_name}' — vui lòng đính kèm thủ công.")
        classified.append({"fileName": file_name, "docType": _OTHER, "source": source})

    if shared:
        warnings.append(
            f"Dòng 1 đính kèm chung {len(shared)} tệp cùng Đơn đăng ký biến động: {'; '.join(shared)}. Lý do: bảng "
            "thành phần hồ sơ không có dòng riêng cho các giấy tờ này."
        )
    return items, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    _ = session
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = trim_files_for_classify([f for f in raw_files if f.get("type") in _OCR_TYPES], _OCR_MAX_PAGES)
    page_counts = {idx: _pdf_page_count(f) for idx, f in enumerate(raw_files) if f.get("type") == "application/pdf"}

    from app.services import ocr

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    ocr_by_name = {item.get("name"): item for item in ocr_results}
    llm_docs: list[dict[str, Any]] = []
    for idx, file in enumerate(raw_files):
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        if text.strip():
            llm_docs.append({"index": idx, "text": text})

    t1 = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types, page_counts)
    errors.extend(warnings)
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "classified": classified,
            "skippedOcr": skipped_ocr,
            "rows": [{"docType": k, **v} for k, v in _ROWS.items()],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
