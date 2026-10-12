"""Đính kèm "Thành phần hồ sơ" cho "Gia hạn giấy phép xây dựng" (mã 1.013227, cổng Bộ Xây dựng dvc.moc.gov.vn —
Angular mat-table, engine FE `attp-row` + modal "Thêm giấy tờ").

Bảng của cổng chỉ có HAI dòng cố định (đều 1 Bản chính):
  1. "Đơn đề nghị gia hạn giấy phép xây dựng theo Mẫu số 2 Phụ lục số II Nghị định số 217/2026/NĐ-CP…" — dòng
     ĐÍNH KÈM CHUNG: Đơn + CCCD chủ hộ (2 mặt) + Giấy ủy quyền (nếu có), Đơn đứng trước.
  2. "Bản chính giấy phép xây dựng đã được cấp".
GCN QSDĐ không có dòng → tạo dòng 3 bằng nút "+ Thêm giấy tờ" (`add-document-dialog`, 1 Bản sao); modal không
tạo được thì FE ĐÍNH CHUNG vào dòng Đơn (`fallbackComponentName`).

Phân loại LLM-primary trên OCR vài trang đầu; rule keyword chỉ dự phòng. Tệp không rõ loại → bỏ qua + cảnh báo.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.gia_han_giay_phep_xay_dung.attach import prompt
from app.pipelines.gia_han_giay_phep_xay_dung.process.schema import OCR_MAX_PAGES
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client
from app.services.pdf_utils import trim_files_for_classify

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON = "don_gia_han"
_CCCD = "cccd"
_UY_QUYEN = "giay_uy_quyen"
_GPXD = "gpxd_da_cap"
_DAT_DAI = "giay_to_dat_dai"
_OTHER = "other"

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold).
_ROW_DON = {
    "componentName": "Đơn đề nghị gia hạn giấy phép xây dựng theo Mẫu số 2",
    "loaiBan": "Bản chính",
}
_ROW_GPXD = {
    "componentName": "Bản chính giấy phép xây dựng đã được cấp",
    "loaiBan": "Bản chính",
}
# Dòng tạo bằng "+ Thêm giấy tờ": componentName là chữ gõ vào ô autocomplete "Giấy tờ" của modal.
_ROW_DAT_DAI = {
    "componentName": "Giấy chứng nhận quyền sử dụng đất",
    "loaiBan": "Bản sao",
}

_ROW_BY_TYPE = {_DON: _ROW_DON, _CCCD: _ROW_DON, _UY_QUYEN: _ROW_DON, _GPXD: _ROW_GPXD, _DAT_DAI: _ROW_DAT_DAI}

# Tên tệp gửi lên cổng (cán bộ tiếp nhận đọc tên là biết giấy gì; <= 50 ký tự).
_DOCUMENT_NAMES = {
    _DON: "Đơn đề nghị gia hạn GPXD (Mẫu số 02)",
    _CCCD: "Căn cước công dân",
    _UY_QUYEN: "Giấy ủy quyền",
    _GPXD: "Giấy phép xây dựng đã được cấp",
    _DAT_DAI: "Giấy chứng nhận quyền sử dụng đất",
}
# Trong dòng gộp chung, Đơn phải đứng trước CCCD/ủy quyền.
_ORDER = {_DON: 0, _CCCD: 1, _UY_QUYEN: 2, _GPXD: 3, _DAT_DAI: 4}
_ALLOWED_DOC_TYPES = set(_ROW_BY_TYPE) | {_OTHER}


def _truncate(text: str, limit: int = 2500) -> str:
    """Loại giấy tờ nhận ra từ TRANG ĐẦU (tiêu đề); cắt ngắn để nhiều file không vượt context LLM."""
    value = re.sub(r"\s+", " ", text or "").strip()
    return value if len(value) <= limit else value[:limit] + "..."


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM). Đơn trước; GPXD trước GCN (GPXD có nhắc số GCN QSDĐ)."""
    h = _fold(text)
    if not h:
        return ""
    if "don de nghi" in h and "giay phep xay dung" in h and any(k in h for k in ("gia han", "dieu chinh", "cap lai")):
        return _DON
    if "giay phep xay dung" in h and "don de nghi" not in h \
            and any(k in h for k in ("gpxd", "cap cho", "duoc phep xay dung")):
        return _GPXD
    if "giay chung nhan" in h and "quyen su dung dat" in h:
        return _DAT_DAI
    if "uy quyen" in h and ("giay uy quyen" in h or "hop dong uy quyen" in h):
        return _UY_QUYEN
    if "can cuoc" in h or "chung minh nhan dan" in h:
        return _CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "").replace(" ", "_")
    if not text or text == _OTHER:
        return _OTHER
    if text in _ALLOWED_DOC_TYPES:
        return text
    if "don" in text:
        return _DON
    if "cccd" in text or "can_cuoc" in text or "cmnd" in text:
        return _CCCD
    if "uy_quyen" in text:
        return _UY_QUYEN
    if "gpxd" in text or "giay_phep" in text:
        return _GPXD
    if "dat" in text or "qsdd" in text or "chung_nhan" in text or "so_do" in text:
        return _DAT_DAI
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


def _build_item(file_index: int, file_name: str, doc_type: str, document_name: str) -> dict:
    row = _ROW_BY_TYPE[doc_type]
    item = {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": row["componentName"],
        "loaiBan": row["loaiBan"],
        "target": "attp-row",
        # Cổng tick sẵn mọi dòng → dòng không đính bị bắt buộc khi chuyển bước; FE bỏ tick trước khi đính.
        "untickUnplannedRows": True,
        "needsAddComponent": False,
        "detectedType": doc_type,
    }
    if doc_type == _DAT_DAI:
        item.update({
            "target": "add-document-dialog",
            "needsAddComponent": True,
            "quantity": 1,
            # Modal không tạo được dòng → đính chung vào dòng Đơn (dòng đính kèm chung của thủ tục).
            "fallbackComponentName": _ROW_DON["componentName"],
        })
    return item


def build_plan_items(
    files: list[dict],
    texts: dict[int, str] | None = None,
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    texts = texts or {}
    llm_types = llm_types or {}
    picked: list[tuple[int, str, str]] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        llm_type = llm_types.get(idx, "")
        rule_type = _rule_doc_type(texts.get(idx, ""))
        if llm_type in _ROW_BY_TYPE:
            doc_type, source = llm_type, "llm"
        elif rule_type:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = _OTHER, "unknown"
        if doc_type in _ROW_BY_TYPE:
            picked.append((idx, file_name, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "source": source})
            continue
        warnings.append(f"Không xác định được loại giấy tờ cho file '{file_name}' — vui lòng đính kèm thủ công.")
        classified.append({"fileName": file_name, "docType": _OTHER, "source": source, "skipped": True})

    items: list[dict] = []
    counts: dict[str, int] = {}
    for idx, file_name, doc_type in sorted(picked, key=lambda p: (_ORDER[p[2]], p[0])):
        counts[doc_type] = counts.get(doc_type, 0) + 1
        name = _DOCUMENT_NAMES[doc_type]
        if counts[doc_type] > 1:
            name = f"{name} {counts[doc_type]}"
        items.append(_build_item(idx, file_name, doc_type, name))

    found = {doc_type for _, _, doc_type in picked}
    if _DON not in found:
        warnings.append("Chưa có Đơn đề nghị gia hạn GPXD (Mẫu số 02) — thành phần hồ sơ bắt buộc.")
    if _GPXD not in found:
        warnings.append("Chưa có Bản chính Giấy phép xây dựng đã được cấp — thành phần hồ sơ bắt buộc.")
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
    llm_docs = [{"index": idx, "text": _truncate(text)} for idx, text in texts.items()]

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
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [raw_files[idx]["name"] for idx in texts],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "classified": classified,
            "skippedOcr": skipped_ocr,
            "rows": [
                {"docType": _DON, **_ROW_DON},
                {"docType": _GPXD, **_ROW_GPXD},
                {"docType": _DAT_DAI, **_ROW_DAT_DAI, "addDocument": True},
            ],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
