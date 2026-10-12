"""Đính kèm "Thành phần hồ sơ" cho "Đề nghị miễn, giảm học phí trong cơ sở GDNN, GDĐH tư thục…" (mã 1.014335, cổng
DVC Bộ GD&ĐT dvc.moet.gov.vn — Angular mat-table, engine FE `attp-row`).

Bảng của cổng có HAI dòng cố định (đều 1 Bản chính). Theo mapping đính kèm, MỖI dòng nhận MỘT file PDF gộp
(`sourceFileIndexes` theo đúng thứ tự trang, FE gộp bằng pdf-lib):
  1. "Bản sao chứng thực … giấy tờ chứng minh thuộc đối tượng miễn, giảm học phí …" — Giấy xác nhận của trường (mẫu
     riêng) → Giấy xác nhận Phụ lục V → giấy tờ đối tượng khác → CCCD → Giấy khai sinh → Bằng tốt nghiệp.
  2. "Đơn đề nghị chi trả tiền miễn giảm học phí theo mẫu tại Phụ lục IV …" — Đơn PL IV → Dự toán PL VI.
Giấy tiếp nhận hồ sơ và hẹn trả kết quả là phiếu cơ quan cấp SAU khi nộp → không đính.

Phân loại LLM-primary trên OCR vài trang đầu; rule keyword chỉ dự phòng. Tệp chưa rõ loại → gộp cuối dòng 1 (dòng
giấy tờ chứng minh nhận mọi giấy tờ bổ trợ) + cảnh báo.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.compact_agent.runner import _extract_docx_text, _is_docx
from app.pipelines.mien_giam_hoc_phi_gdnn_dai_hoc_tu_thuc.attach import prompt
from app.pipelines.mien_giam_hoc_phi_gdnn_dai_hoc_tu_thuc.process.schema import OCR_MAX_PAGES
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client
from app.services.pdf_utils import trim_files_for_classify

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON = "don_pl4"
_DU_TOAN = "du_toan_pl6"
_GXN_TRUONG = "gxn_truong"
_GXN_PL5 = "gxn_pl5"
_DOI_TUONG = "giay_to_doi_tuong"
_CCCD = "cccd"
_KHAI_SINH = "giay_khai_sinh"
_BANG = "bang_tot_nghiep"
_PHIEU_TN = "phieu_tiep_nhan"
_OTHER = "other"

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold). documentName = tên file PDF gộp (<= 50 ký tự).
_ROW_CHUNG_MINH = {
    "componentName": "giấy tờ chứng minh thuộc đối tượng miễn, giảm học phí",
    "loaiBan": "Bản chính",
    "documentName": "Giấy tờ chứng minh đối tượng miễn, giảm học phí",
}
_ROW_DON = {
    "componentName": "Đơn đề nghị chi trả tiền miễn giảm học phí theo mẫu tại Phụ lục IV",
    "loaiBan": "Bản chính",
    "documentName": "Đơn đề nghị chi trả miễn, giảm học phí (PL IV)",
}

# Thứ tự trang trong file gộp của từng dòng (theo mapping đính kèm).
_ROW_ORDER: list[tuple[dict, tuple[str, ...]]] = [
    (_ROW_CHUNG_MINH, (_GXN_TRUONG, _GXN_PL5, _DOI_TUONG, _CCCD, _KHAI_SINH, _BANG, _OTHER)),
    (_ROW_DON, (_DON, _DU_TOAN)),
]
_ROW_TYPES = {t for _, types in _ROW_ORDER for t in types}
_ALLOWED_DOC_TYPES = _ROW_TYPES | {_PHIEU_TN}

_PHU_LUC_V = re.compile(r"\bphu luc v\b")
_DOI_TUONG_MARKERS = (
    "nguoi co cong", "khuyet tat", "ho ngheo", "can ngheo", "mo coi", "tro cap xa hoi", "tai nan lao dong",
    "benh nghe nghiep",
)


def _truncate(text: str, limit: int = 2500) -> str:
    """Loại giấy tờ nhận ra từ TRANG ĐẦU (tiêu đề); cắt ngắn để nhiều file không vượt context LLM."""
    value = re.sub(r"\s+", " ", text or "").strip()
    return value if len(value) <= limit else value[:limit] + "..."


def _is_photo_like(text: str) -> bool:
    """Ảnh chụp mờ / trang bìa (vd bìa Bằng tốt nghiệp): OCR gần như không có chữ."""
    return sum(1 for c in _fold(text) if c.isalpha()) < 20


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM). Giấy tiếp nhận đứng ĐẦU (nó chép lại tên cả 2 thành phần hồ sơ);
    Dự toán trước Đơn (cùng nhắc 'cấp bù tiền miễn, giảm học phí')."""
    h = _fold(text)
    if not h:
        return ""
    if "tiep nhan ho so" in h and "hen tra ket qua" in h:
        return _PHIEU_TN
    if "du toan kinh phi" in h:
        return _DU_TOAN
    if "don de nghi chi tra tien mien" in h or "nguoi lam don" in h:
        return _DON
    if "giay xac nhan" in h and _PHU_LUC_V.search(h):
        return _GXN_PL5
    if "giay xac nhan" in h and ("xac nhan sinh vien" in h or "thuoc doi tuong" in h):
        return _GXN_TRUONG
    if "giay khai sinh" in h or "trich luc khai sinh" in h:
        return _KHAI_SINH
    if any(k in h for k in ("can cuoc cong dan", "citizen identity", "chung minh nhan dan", "idvnm", "the can cuoc")):
        return _CCCD
    if "bang tot nghiep" in h or "so vao so cap bang" in h or "hoc ba" in h:
        return _BANG
    if any(k in h for k in _DOI_TUONG_MARKERS):
        return _DOI_TUONG
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "").replace(" ", "_")
    if not text or text == _OTHER:
        return _OTHER
    if text in _ALLOWED_DOC_TYPES:
        return text
    if "tiep_nhan" in text or "phieu" in text:
        return _PHIEU_TN
    if "du_toan" in text or "pl6" in text:
        return _DU_TOAN
    if "don" in text or "pl4" in text:
        return _DON
    if "pl5" in text:
        return _GXN_PL5
    if "xac_nhan" in text or "gxn" in text:
        return _GXN_TRUONG
    if "khai_sinh" in text:
        return _KHAI_SINH
    if "cccd" in text or "can_cuoc" in text or "cmnd" in text:
        return _CCCD
    if "bang" in text or "tot_nghiep" in text:
        return _BANG
    if "doi_tuong" in text:
        return _DOI_TUONG
    return _OTHER


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=500, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    out: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        out[idx] = _normalize_doc_type(str(item.get("docType") or item.get("type") or ""))
    return out


def build_plan_items(
    files: list[dict],
    texts: dict[int, str] | None = None,
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    texts = texts or {}
    llm_types = llm_types or {}
    picked: dict[str, list[int]] = {}
    warnings: list[str] = []
    classified: list[dict] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = texts.get(idx, "")
        llm_type = llm_types.get(idx, "")
        rule_type = _rule_doc_type(text)
        if llm_type in _ALLOWED_DOC_TYPES:
            doc_type, source = llm_type, "llm"
        elif rule_type:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = _OTHER, "unknown"

        if doc_type == _PHIEU_TN:
            classified.append({"fileName": file_name, "docType": doc_type, "source": source, "skipped": True})
            warnings.append(f"'{file_name}' là Giấy tiếp nhận hồ sơ (phiếu cơ quan cấp sau khi nộp) — không đính kèm.")
            continue
        if doc_type == _OTHER:
            # Ảnh chụp gần như không chữ thường là trang bìa Bằng tốt nghiệp; còn lại gộp cuối dòng giấy tờ chứng minh.
            if not _is_docx(file) and _is_photo_like(text):
                doc_type, source = _BANG, "photo-fallback"
            else:
                warnings.append(f"Không phân loại chắc chắn '{file_name}' — tạm gộp vào dòng giấy tờ chứng minh đối "
                                "tượng, vui lòng kiểm tra.")
        picked.setdefault(doc_type, []).append(idx)
        classified.append({"fileName": file_name, "docType": doc_type, "source": source})

    items: list[dict] = []
    for row, order in _ROW_ORDER:
        indexes = [idx for doc_type in order for idx in picked.get(doc_type, [])]
        if not indexes:
            continue
        first = indexes[0]
        types = [doc_type for doc_type in order if picked.get(doc_type)]
        items.append({
            "fileIndex": first,
            # Gộp MỌI tệp của dòng thành MỘT PDF theo đúng thứ tự trang (FE: applyMergeGroups).
            "sourceFileIndexes": indexes,
            "fileName": str(files[first].get("name") or f"file-{first + 1}"),
            "documentName": row["documentName"],
            "componentName": row["componentName"],
            "loaiBan": row["loaiBan"],
            "target": "attp-row",
            # Cổng tick sẵn mọi dòng → dòng không đính bị bắt buộc khi chuyển bước; FE bỏ tick trước khi đính.
            "untickUnplannedRows": True,
            "needsAddComponent": False,
            "detectedType": types[0],
            "detectedTypes": types,
        })

    if not picked.get(_DON):
        warnings.append("Chưa có Đơn đề nghị chi trả tiền miễn, giảm học phí (Phụ lục IV) — thành phần hồ sơ bắt buộc.")
    if not any(picked.get(t) for t in (_GXN_TRUONG, _GXN_PL5, _DOI_TUONG)):
        warnings.append("Chưa có giấy tờ chứng minh thuộc đối tượng miễn, giảm học phí (Giấy xác nhận của trường, giấy "
                        "xác nhận người có công/khuyết tật/hộ nghèo…) — thành phần hồ sơ bắt buộc.")
    return items, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options
    _ = session
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_indexes = [idx for idx, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]
    # Cùng số trang với bước điền → trúng cache OCR; tệp gửi lên cổng vẫn là bản gốc đủ trang.
    ocr_files = trim_files_for_classify([raw_files[idx] for idx in ocr_indexes], OCR_MAX_PAGES)

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    # ocr_per_file trả đúng thứ tự tệp đưa vào → ghép theo vị trí, không theo tên (hai ảnh có thể trùng tên).
    texts: dict[int, str] = {}
    for idx, result in zip(ocr_indexes, ocr_results):
        text = str(result.get("text") or "")
        if text.strip():
            texts[idx] = text
    # Đơn Word (mẫu tải về từ cổng): trích text trực tiếp để phân loại theo nội dung.
    for idx, f in enumerate(raw_files):
        if _is_docx(f):
            text = str(_extract_docx_text(f).get("text") or "")
            if text.strip():
                texts[idx] = text
    llm_docs = [{"index": idx, "text": _truncate(text)} for idx, text in sorted(texts.items())]

    t1 = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, texts, llm_types)
    errors.extend(warnings)
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES and not _is_docx(f)]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [raw_files[idx]["name"] for idx in texts],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "classified": classified,
            "skippedOcr": skipped_ocr,
            "rows": [{"docTypes": list(order), **row} for row, order in _ROW_ORDER],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
