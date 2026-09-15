"""Lập kế hoạch đính kèm hồ sơ ATTP trên cổng MAE.

Hai dòng Phụ lục I/II có sẵn trong bảng Angular nên dùng engine ``attp-row``.
CCCD không có dòng cố định nên dùng modal "Thêm giấy tờ"; Giấy đăng ký kinh doanh chỉ là nguồn điền
eForm và không được gắn nhầm vào hai dòng Phụ lục I/II.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.cap_gcn_attp_nong_lam_thuy_san.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON = "don_de_nghi"
_THUYET_MINH = "thuyet_minh"
_CCCD = "cccd"
_GCN_DKKD = "gcn_dkkd"
_OTHER = "other"
_LOAI_BAN = "Bản chính"

_ROWS: dict[str, dict[str, str]] = {
    _DON: {
        "componentName": "Đơn đề nghị cấp Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm theo mẫu tại Phụ lục I",
        "loaiBan": "Bản chính",
        "documentName": "Đơn đề nghị cấp Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm (Phụ lục I)",
    },
    _THUYET_MINH: {
        "componentName": "Bản thuyết minh về cơ sở vật chất, trang thiết bị, dụng cụ bảo đảm điều kiện vệ sinh an toàn thực phẩm",
        "loaiBan": "Bản chính",
        "documentName": "Bản thuyết minh điều kiện bảo đảm an toàn thực phẩm (Phụ lục II)",
    },
}
_CCCD_COMPONENT = (
    "Trường hợp nộp trực tiếp thì xuất trình bản chính hoặc bản sao có chứng thực giấy chứng minh nhân dân "
    "hoặc hộ chiếu còn giá trị sử dụng."
)
_SKIP_DOCS = {_GCN_DKKD}
_ALLOWED_DOC_TYPES = set(_ROWS) | _SKIP_DOCS | {_CCCD, _OTHER}


def _rule_doc_type(text: str) -> str:
    folded = _fold(text)
    if not folded:
        return ""
    if (
        "don de nghi cap" in folded
        and "co so du dieu kien an toan thuc pham" in folded
        and ("ten co so" in folded or "mat hang san xuat" in folded)
    ):
        return _DON
    if (
        "ban thuyet minh" in folded
        and "dieu kien bao dam an toan thuc pham" in folded
        and ("thong tin chung" in folded or "mo ta ve san pham" in folded)
    ):
        return _THUYET_MINH
    if any(marker in folded for marker in ("can cuoc cong dan", "the can cuoc", "chung minh nhan dan", "passport")):
        return _CCCD
    if any(marker in folded for marker in (
        "giay chung nhan dang ky doanh nghiep",
        "giay chung nhan dang ky ho kinh doanh",
        "ma so doanh nghiep",
        "dang ky hoat dong chi nhanh",
    )):
        return _GCN_DKKD
    return ""


def _normalize_doc_type(value: str) -> str:
    folded = _fold(value)
    if "thuyet minh" in folded:
        return _THUYET_MINH
    if "don" in folded and "de nghi" in folded:
        return _DON
    if any(marker in folded for marker in ("cccd", "can cuoc", "cmnd", "ho chieu")):
        return _CCCD
    if "dang ky" in folded or "doanh nghiep" in folded or "ho kinh doanh" in folded:
        return _GCN_DKKD
    return value if value in _ALLOWED_DOC_TYPES else _OTHER


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=400, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    out: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            index = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        out[index] = _normalize_doc_type(str(item.get("docType") or item.get("type") or ""))
    return out


def _build_row_item(file: dict, file_index: int, doc_type: str, detected_type: str | None = None) -> dict:
    row = _ROWS[doc_type]
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        # GIỮ NGUYÊN tên file gốc — engine attp-row đặt tên file theo documentName (content.js dataUrlToFile).
        "documentName": file_name,
        "componentName": row["componentName"],
        "loaiBan": row["loaiBan"],
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": detected_type or doc_type,
    }


def _build_cccd_item(cccd_group: list[tuple[int, dict]]) -> dict:
    """1 item CCCD cho modal 'Thêm giấy tờ'. Nếu ≥2 file (2 MẶT CCCD) → gộp thành 1 PDF qua
    sourceFileIndexes (FE applyMergeGroups.mergeToPdf). Giữ NGUYÊN tên file gốc (file đầu)."""
    first_index, first_file = cccd_group[0]
    first_name = str(first_file.get("name") or f"file-{first_index + 1}")
    item = {
        "fileIndex": first_index,
        "fileName": first_name,
        "documentName": first_name,
        "componentName": _CCCD_COMPONENT,
        "loaiBan": _LOAI_BAN,
        "quantity": 1,
        "target": "add-document-dialog",
        "needsAddComponent": True,
        "detectedType": _CCCD,
    }
    if len(cccd_group) > 1:
        item["sourceFileIndexes"] = [idx for idx, _ in cccd_group]
    return item


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    ocr_by_name = {item.get("name"): item for item in ocr_results}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    cccd_group: list[tuple[int, dict]] = []   # gom mọi file CCCD để gộp 2 mặt thành 1 PDF

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        text = str(ocr_by_name.get(file_name, {}).get("text") or "")
        rule_type = _rule_doc_type(text)
        llm_type = llm_types.get(index, "")
        if rule_type in _ROWS or rule_type == _CCCD or rule_type in _SKIP_DOCS:
            doc_type, source = rule_type, "rule"
        elif llm_type in _ROWS or llm_type == _CCCD or llm_type in _SKIP_DOCS:
            doc_type, source = llm_type, "llm"
        else:
            doc_type, source = _OTHER, "unknown"

        if doc_type in _ROWS:
            attachments.append(_build_row_item(file, index, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "source": source})
        elif doc_type == _CCCD:
            cccd_group.append((index, file))
            classified.append({"fileName": file_name, "docType": doc_type, "source": source})
        elif doc_type in _SKIP_DOCS:
            # Giấy ĐKKD/ĐKDN chỉ là nguồn điền eForm — KHÔNG đính (tránh gắn nhầm vào hàng Phụ lục).
            classified.append({"fileName": file_name, "docType": doc_type, "source": source, "skipped": True})
        else:
            # Giấy tờ ngoài 2 loại đã định nghĩa (other) → ĐÍNH CHUNG vào HÀNG TỜ KHAI (Đơn Phụ lục I),
            # KHÔNG bỏ qua; giữ nguyên tên file gốc (attp-row nhận nhiều file/1 dòng).
            attachments.append(_build_row_item(file, index, _DON, detected_type=_OTHER))
            classified.append({"fileName": file_name, "docType": _OTHER, "source": source, "routedTo": _DON})

    # 2 mặt CCCD (hoặc nhiều ảnh CCCD lẻ) → gộp thành 1 PDF rồi vào modal "Thêm giấy tờ".
    if cccd_group:
        attachments.append(_build_cccd_item(cccd_group))

    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    _ = session
    errors: list[str] = []
    raw_files = [{"name": file.name, "type": file.type, "dataUrl": file.dataUrl} for file in files]
    ocr_files = [file for file in raw_files if file.get("type") in _OCR_TYPES]

    from app.services import ocr

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    ocr_by_name = {item.get("name"): item for item in ocr_results}
    unresolved: list[dict[str, Any]] = []
    for index, file in enumerate(raw_files):
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        if text.strip() and not _rule_doc_type(text):
            # Mọi tài liệu rule chưa xác định đều phải qua LLM trước khi trở thành other.
            unresolved.append({"index": index, "text": text})

    llm_started = time.monotonic()
    llm_types: dict[int, str] = {}
    if unresolved:
        try:
            llm_types = await _classify_with_llm(unresolved)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - llm_started) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [file["name"] for file in raw_files],
            "ocrDocuments": [item.get("name") for item in ocr_results if item.get("text")],
            "llmDocuments": [raw_files[item["index"]]["name"] for item in unresolved],
            "classified": classified,
            "rows": [{"docType": doc_type, **row} for doc_type, row in _ROWS.items()],
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "errors": errors,
    }
