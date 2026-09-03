"""Đính kèm bước "Thành phần hồ sơ" cho "Cấp Giấy chứng nhận đủ điều kiện ATTP" (cổng Bộ Công Thương —
Angular CDK table, engine FE `attp-row`, CÙNG cổng #42 cap_lai_an_toan_thuc_pham).

Bảng nhiều dòng; mỗi dòng: mat-checkbox + rdo_File (Bản chính/Bản sao) + input[type=file]. FE khớp dòng
bằng TÊN giấy tờ (componentName, substring fold vào cột tên). Có 7 dòng nhưng thủ tục CẤP dùng 5 dòng —
BỎ QUA "Báo cáo kết quả khắc phục Mẫu số 04" (chỉ khi thẩm định lại) và dòng "Cơ quan giải quyết TTHC khai
thác CSDL…" (cơ quan tự khai thác, không nộp).

Phân loại **LLM-primary**: LLM đọc OCR quyết định loại; rule keyword chỉ DỰ PHÒNG. CCCD/ủy quyền → bỏ qua.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.cap_gcn_attp_cong_thuong.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON = "don_01a"
_THUYET_MINH = "thuyet_minh"
_TAP_HUAN = "tap_huan"
_SUC_KHOE = "suc_khoe"
_GCN_DKKD = "gcn_dkkd"
_CCCD = "cccd"
_UY_QUYEN = "uy_quyen"
_OTHER = "other"

# Mỗi loại → 1 dòng. componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold). loaiBan theo
# cột "Loại bản" của form.
_ROWS: dict[str, dict[str, str]] = {
    _DON: {
        "componentName": "Đơn đề nghị theo Mẫu số 01a",
        "loaiBan": "Bản chính",
        "documentName": "Đơn đề nghị cấp Giấy chứng nhận cơ sở đủ điều kiện ATTP (Mẫu số 01a)",
    },
    _THUYET_MINH: {
        "componentName": "Bản thuyết minh về cơ sở vật chất",
        "loaiBan": "Bản chính",
        "documentName": "Bản thuyết minh về cơ sở vật chất, trang thiết bị, dụng cụ (Mẫu 02a/02b)",
    },
    _GCN_DKKD: {
        # Dòng 1: "Bản sao Giấy chứng nhận đăng ký kinh doanh hoặc Giấy chứng nhận đăng ký doanh nghiệp
        # hoặc Giấy chứng nhận đầu tư". Cụm "đăng ký kinh doanh hoặc" đặc trưng, KHÔNG có ở dòng 7 (chỉ ghi
        # "đăng ký doanh nghiệp").
        "componentName": "đăng ký kinh doanh hoặc Giấy chứng nhận đăng ký doanh nghiệp",
        "loaiBan": "Bản sao",
        "documentName": "Bản sao Giấy chứng nhận đăng ký kinh doanh/doanh nghiệp/đầu tư",
    },
    _TAP_HUAN: {
        "componentName": "tập huấn kiến thức về an toàn thực phẩm",
        "loaiBan": "Bản chính",
        "documentName": "Giấy xác nhận đã được tập huấn kiến thức về an toàn thực phẩm",
    },
    _SUC_KHOE: {
        "componentName": "Danh sách tổng hợp đủ sức khỏe",
        "loaiBan": "Bản chính",
        "documentName": "Danh sách tổng hợp đủ sức khỏe / giấy xác nhận đủ sức khỏe",
    },
}
# Giấy tờ nguồn KHÔNG có dòng riêng → bỏ qua (chỉ dùng điền form).
_SKIP_DOCS = {_CCCD, _UY_QUYEN}
_ALLOWED_DOC_TYPES = set(_ROWS) | _SKIP_DOCS | {_OTHER}


def _is_identity_text(text: str) -> bool:
    h = _fold(text)
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport"))


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM)."""
    h = _fold(text)
    if not h:
        return ""
    if "giay uy quyen" in h or ("uy quyen" in h and "ben uy quyen" in h):
        return _UY_QUYEN
    # Đơn đề nghị CẤP (Mẫu 01a) — không có "cap lai".
    if ("don de nghi" in h and "an toan thuc pham" in h and "cap lai" not in h) or "mau so 01a" in h:
        return _DON
    if "ban thuyet minh" in h or ("thuyet minh" in h and ("co so vat chat" in h or "trang thiet bi" in h)):
        return _THUYET_MINH
    if "tap huan kien thuc" in h or ("tap huan" in h and "an toan thuc pham" in h):
        return _TAP_HUAN
    if "du suc khoe" in h or "kham suc khoe" in h or "giay kham benh" in h:
        return _SUC_KHOE
    if any(k in h for k in ("dang ky ho kinh doanh", "dang ky doanh nghiep", "dang ky kinh doanh",
                            "ma so ho kinh doanh", "ma so doanh nghiep", "dia diem kinh doanh")):
        return _GCN_DKKD
    if _is_identity_text(h):
        return _CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if "uy quyen" in text:
        return _UY_QUYEN
    if "don" in text and ("01a" in text or "de nghi" in text):
        return _DON
    if "thuyet minh" in text:
        return _THUYET_MINH
    if "tap huan" in text:
        return _TAP_HUAN
    if "suc khoe" in text:
        return _SUC_KHOE
    if "dang ky" in text or "doanh nghiep" in text or "kinh doanh" in text or "dkkd" in text:
        return _GCN_DKKD
    if any(k in text for k in ("can cuoc", "cccd", "cmnd", "ho chieu")):
        return _CCCD
    return value if value in _ALLOWED_DOC_TYPES else _OTHER


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


def _build_row_item(file: dict, file_index: int, doc_type: str) -> dict:
    row = _ROWS[doc_type]
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": row["documentName"],
        "componentName": row["componentName"],
        "loaiBan": row["loaiBan"],
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": doc_type,
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    by_name = {item.get("name"): item for item in ocr_results}
    items: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = str(by_name.get(file_name, {}).get("text") or "")
        llm_type = llm_types.get(idx, "")
        rule_type = _rule_doc_type(text)
        # LLM-primary: ưu tiên phán đoán LLM; rule keyword chỉ dự phòng khi LLM trả other/không hợp lệ.
        if llm_type in _ROWS or llm_type in _SKIP_DOCS:
            doc_type, source = llm_type, "llm"
        elif rule_type:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = _OTHER, "unknown"

        if doc_type in _ROWS:
            items.append(_build_row_item(file, idx, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "source": source})
            continue
        if doc_type in _SKIP_DOCS:
            classified.append({"fileName": file_name, "docType": doc_type, "source": source, "skipped": True})
            continue

        warnings.append(f"Không xác định được loại giấy tờ cho file '{file_name}' — vui lòng đính kèm thủ công.")
        classified.append({"fileName": file_name, "docType": _OTHER, "source": source})

    return items, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    _ = session
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

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

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types)
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
