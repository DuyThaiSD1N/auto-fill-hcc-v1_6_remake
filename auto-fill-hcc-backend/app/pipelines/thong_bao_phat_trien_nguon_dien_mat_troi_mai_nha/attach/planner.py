"""Đính kèm bước "Thành phần hồ sơ" cho "Thông báo phát triển nguồn điện mặt trời mái nhà tự sản xuất, tự tiêu
thụ" (cổng Bộ Công Thương — bảng Angular, engine FE `attp-row` + modal "Thêm giấy tờ").

Bảng chỉ có MỘT dòng cố định: "Thông báo theo Mẫu số 01 tại Phụ lục III kèm theo Nghị định số 243/2026/NĐ-CP"
(1 Bản chính). Hai giấy "II. HỒ SƠ KÈM THEO" in trên Mẫu 01 không có dòng → tạo bằng nút "+ Thêm giấy tờ"
(`add-document-dialog`); modal không tạo được thì FE ĐÍNH CHUNG vào dòng Thông báo (`fallbackComponentName`):
  - Bản vẽ thiết kế lắp đặt nguồn điện (Bản chính);
  - Bản sao tài liệu liên quan đến công trình có mái nhà — GCN QSDĐ/QSHN, giấy phép xây dựng, nghiệm thu PCCC.
Mọi tệp còn lại đều đính chung dòng Thông báo, đặt tên theo loại giấy: hình ảnh dự án, chứng từ thiết bị (C/O,
CQ…), CCCD, giấy do cơ quan lập (biên nhận, phiếu kiểm soát, Thông báo UBND) và giấy không rõ loại (không đưa
qua modal: tên lạ không có trong danh mục modal sẽ kéo cả bản vẽ/GCN về dòng dự phòng).
Chỉ bỏ qua file bảng tính (.xlsx — cổng nhận PDF/ảnh).

Phân loại LLM-primary trên OCR; rule keyword chỉ dự phòng. Mọi tệp được đặt tên theo loại giấy.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.thong_bao_phat_trien_nguon_dien_mat_troi_mai_nha.attach import prompt
from app.pipelines.thong_bao_phat_trien_nguon_dien_mat_troi_mai_nha.process.schema import OCR_MAX_PAGES
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client
from app.services.pdf_utils import trim_files_for_classify

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_SHEET_EXTENSIONS = (".xlsx", ".xls", ".xlsm", ".csv")

_THONG_BAO = "thong_bao"
_BAN_VE = "ban_ve"
_CONG_TRINH = "tai_lieu_cong_trinh"
_HINH_ANH = "hinh_anh"
_THIET_BI = "thiet_bi"
_CCCD = "cccd"
_KET_QUA = "ket_qua"
_OTHER = "other"
_ALLOWED_DOC_TYPES = {_THONG_BAO, _BAN_VE, _CONG_TRINH, _HINH_ANH, _THIET_BI, _CCCD, _KET_QUA, _OTHER}

# componentName khớp substring (fold) với nhãn dòng trên cổng.
_MAIN_ROW = {
    "componentName": "Thông báo theo Mẫu số 01 tại Phụ lục III",
    "loaiBan": "Bản chính",
}
# Dòng tạo qua modal "Thêm giấy tờ" — tên theo mục "II. HỒ SƠ KÈM THEO" của Mẫu 01.
_DIALOG_ROWS: dict[str, dict[str, str]] = {
    _BAN_VE: {"componentName": "Bản vẽ thiết kế lắp đặt nguồn điện", "loaiBan": "Bản chính"},
    _CONG_TRINH: {
        "componentName": "Bản sao tài liệu liên quan đến công trình có mái nhà",
        "loaiBan": "Bản sao",
    },
}
# Tên tài liệu theo loại (≤50 ký tự, không ngoặc, không dấu chấm); other giữ tên tệp gốc.
_LABELS: dict[str, str] = {
    _THONG_BAO: "Thông báo phát triển điện mặt trời mái nhà",
    _BAN_VE: "Bản vẽ thiết kế lắp đặt nguồn điện",
    _CONG_TRINH: "Tài liệu liên quan đến công trình có mái nhà",
    _HINH_ANH: "Hình ảnh dự án",
    _THIET_BI: "Chứng từ xuất xứ, chất lượng thiết bị",
    _CCCD: "Căn cước công dân",
}
# Giấy cơ quan lập chung một loại ket_qua → tên theo dấu hiệu OCR; không nhận ra thì giữ tên tệp gốc.
_KET_QUA_LABELS = (
    (("giay tiep nhan ho so", "hen tra ket qua"), "Giấy tiếp nhận hồ sơ và hẹn trả kết quả"),
    (("phieu kiem soat",), "Phiếu kiểm soát quá trình giải quyết hồ sơ"),
    (("tb-ubnd", "uy ban nhan dan"), "Thông báo của Ủy ban nhân dân"),
)


def _document_label(doc_type: str, text: str) -> str:
    if doc_type != _KET_QUA:
        return _LABELS.get(doc_type, "")
    h = _fold(text)
    return next((label for markers, label in _KET_QUA_LABELS if any(m in h for m in markers)), "")


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM). Giấy cơ quan lập nhận TRƯỚC: Thông báo UBND và biên nhận
    cũng nhắc nguyên tên thủ tục."""
    h = _fold(text)
    if not h:
        return ""
    if "giay tiep nhan ho so" in h or "hen tra ket qua" in h or "phieu kiem soat qua trinh" in h \
            or "/tb-ubnd" in h or "tb-ubnd" in h:
        return _KET_QUA
    if "phat trien nguon dien mat troi mai nha" in h and (
            "thong tin chung" in h or "san luong dien du" in h or "thong bao" in h):
        return _THONG_BAO
    if "drawing name" in h or "mat bang bo tri" in h or "so do nguyen ly" in h \
            or ("ban ve" in h and ("tam pv" in h or "inverter" in h)):
        return _BAN_VE
    if "quyen su dung dat" in h or "giay phep xay dung" in h \
            or ("nghiem thu" in h and "phong chay" in h):
        return _CONG_TRINH
    if "hinh anh du an" in h:
        return _HINH_ANH
    if "certificate of origin" in h or "quality certificate" in h or "inspection report" in h \
            or "certificate of product" in h or "packing list" in h:
        return _THIET_BI
    if any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu")):
        return _CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "").replace(" ", "_")
    return text if text in _ALLOWED_DOC_TYPES else _OTHER


def _sample_text(text: str, head: int = 4000, tail: int = 1500) -> str:
    """Đầu + cuối OCR: tệp gộp hàng chục trang thì giấy thứ hai trở đi thường chỉ thấy ở phần sau."""
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= head + tail:
        return text
    return f"{text[:head]} … {text[-tail:]}"


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    if not documents:
        return {}
    docs = [{"index": item["index"], "text": _sample_text(item.get("text", ""))} for item in documents]
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(docs)},
    ]
    raw = await client.chat(
        messages, max_tokens=max(400, 60 * len(docs)), enable_thinking=settings.agent_reasoning,
    )
    parsed = client.extract_json_block(raw)
    valid = {item["index"] for item in documents}
    out: dict[int, dict[str, Any]] = {}
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        if idx not in valid:
            continue
        out[idx] = {
            "docType": _normalize_doc_type(str(item.get("docType") or item.get("type") or "")),
            "bundle": item.get("bundle") is True,
        }
    return out


def _is_sheet(file: dict) -> bool:
    return str(file.get("name") or "").lower().endswith(_SHEET_EXTENSIONS)


def _item(file_name: str, file_index: int, doc_type: str, document_name: str) -> dict:
    row = _DIALOG_ROWS.get(doc_type)
    if row:
        return {
            "fileIndex": file_index,
            "fileName": file_name,
            "documentName": document_name,
            "componentName": row["componentName"],
            "loaiBan": row["loaiBan"],
            "quantity": 1,
            "target": "add-document-dialog",
            "needsAddComponent": True,
            "detectedType": doc_type,
            # Modal không tạo được dòng → đính chung vào dòng Thông báo.
            "fallbackComponentName": _MAIN_ROW["componentName"],
        }
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": _MAIN_ROW["componentName"],
        "loaiBan": _MAIN_ROW["loaiBan"],
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": doc_type,
    }


def build_plan_items(
    files: list[dict],
    texts: dict[int, str] | None = None,
    llm_types: dict[int, dict[str, Any]] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    texts = texts or {}
    llm_types = llm_types or {}
    items: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    # Hai tệp cùng loại phải khác tên để cán bộ phân biệt trên cổng.
    name_counts: dict[str, int] = {}

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        if _is_sheet(file):
            classified.append({"fileName": file_name, "docType": "bang_tinh", "source": "rule", "skipped": True})
            warnings.append(f"Bỏ qua tệp bảng tính '{file_name}' — cổng nhận bản PDF, vui lòng xuất PDF nếu cần nộp.")
            continue
        detected = llm_types.get(idx) or {}
        llm_type = detected.get("docType", "")
        rule_type = _rule_doc_type(texts.get(idx, ""))
        if llm_type and llm_type != _OTHER:
            doc_type, source = llm_type, "llm"
        elif rule_type:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = _OTHER, "unknown"

        document_name = _document_label(doc_type, texts.get(idx, ""))
        if document_name:
            name_counts[document_name] = name_counts.get(document_name, 0) + 1
            if name_counts[document_name] > 1:
                document_name = f"{document_name} {name_counts[document_name]}"
        else:
            document_name = file_name

        item = _item(file_name, idx, doc_type, document_name)
        items.append(item)
        classified.append({
            "fileName": file_name, "docType": doc_type, "source": source, "routedTo": item["componentName"],
        })
        if doc_type == _OTHER:
            warnings.append(f"Không xác định được loại giấy tờ cho file '{file_name}' — đã đính chung vào dòng "
                            "Thông báo, vui lòng kiểm tra lại.")
        if detected.get("bundle"):
            warnings.append(f"Tệp '{file_name}' gộp nhiều loại giấy tờ — ghi rõ các giấy có trong tệp ở phần Ghi chú, "
                            "hoặc tách tệp theo từng loại trước khi nộp.")

    detected_types = [item["detectedType"] for item in items]
    if _THONG_BAO not in detected_types:
        warnings.append("Không tìm thấy Thông báo Mẫu 01 trong hồ sơ — dòng Thông báo là bắt buộc.")
    elif detected_types.count(_THONG_BAO) > 1:
        warnings.append("Hồ sơ có nhiều bản Thông báo Mẫu 01 — chỉ giữ bản đúng tư cách người nộp (cá nhân hoặc "
                        "tổ chức), bỏ bản còn lại.")
    if _BAN_VE not in detected_types:
        warnings.append("Không tìm thấy Bản vẽ thiết kế lắp đặt nguồn điện — giấy bắt buộc kèm Thông báo Mẫu 01.")

    return items, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options
    _ = session
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_indexes = [idx for idx, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES and not _is_sheet(f)]
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
    llm_docs = [{"index": idx, "text": text} for idx, text in texts.items()]

    t1 = time.monotonic()
    llm_types: dict[int, dict[str, Any]] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, texts, llm_types)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "classified": classified,
            "skippedOcr": [f["name"] for idx, f in enumerate(raw_files) if idx not in ocr_indexes],
            "rows": [{"docType": _THONG_BAO, **_MAIN_ROW}] + [{"docType": k, **v} for k, v in _DIALOG_ROWS.items()],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "ocr_text": join_ocr_documents(ocr_results),
        "llm_output": {str(idx): val for idx, val in llm_types.items()},
        "errors": errors,
    }
