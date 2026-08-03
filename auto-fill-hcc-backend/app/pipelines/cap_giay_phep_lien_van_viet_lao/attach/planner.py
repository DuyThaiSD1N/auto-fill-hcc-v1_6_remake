"""Đính kèm bước "Thành phần hồ sơ" cho thủ tục "Cấp, cấp lại Giấy phép liên vận giữa Việt Nam và Lào"
(cổng Bộ Xây dựng — Angular table).

Bảng 6 dòng (2)-(7); mỗi dòng có mat-checkbox + rdo_File (Bản chính / Bản sao) + ô upload → engine FE
`attp-row` (target "attp-row"). Dòng chia theo nhóm phương tiện THƯƠNG MẠI (3,4) vs PHI THƯƠNG MẠI (5,6,7)
+ dòng (2) Quyết định cử đi công tác. componentName dùng tiền tố "thương mại]"/"phi thương mại]" để phân
biệt 2 dòng cùng tên (đăng ký xe / giấy đề nghị).

Phân loại **LLM-primary**: LLM đọc OCR mọi file quyết định loại + cờ thuongMai; rule keyword chỉ DỰ PHÒNG.
CCCD/other không có dòng riêng → bỏ qua.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.cap_giay_phep_lien_van_viet_lao.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DE_NGHI = "giay_de_nghi"
_DANG_KY_XE = "dang_ky_xe"
_HOP_DONG = "hop_dong_du_an"
_QUYET_DINH = "quyet_dinh_cong_tac"
_CCCD = "cccd"
_OTHER = "other"

# Định nghĩa từng DÒNG trên bảng. componentName = ĐOẠN TEXT ĐẶC TRƯNG DUY NHẤT của dòng (FE khớp substring
# đã fold dấu vào tên dòng). Tiền tố "Phương tiện thương mại]" ≠ "phi thương mại]" → không nhầm 2 dòng.
_ROW_DEFS: dict[str, dict[str, str]] = {
    "quyet_dinh": {
        "componentName": "Quyết định cử đi công tác",
        "loaiBan": "Bản sao",
        "documentName": "Quyết định cử đi công tác của cơ quan có thẩm quyền",
    },
    "dangkyxe_tm": {
        "componentName": "Phương tiện thương mại]Giấy chứng nhận đăng ký xe",
        "loaiBan": "Bản sao",
        "documentName": "[Thương mại] Giấy chứng nhận đăng ký xe ô tô",
    },
    "denghi_tm": {
        "componentName": "Phương tiện thương mại]Giấy đề nghị",
        "loaiBan": "Bản chính",
        "documentName": "[Thương mại] Giấy đề nghị cấp, cấp lại giấy phép theo mẫu",
    },
    "hopdong": {
        "componentName": "tài liệu chứng minh đơn vị đang thực hiện công trình",
        "loaiBan": "Bản sao",
        "documentName": "[Phi thương mại] Hợp đồng/tài liệu chứng minh công trình, dự án tại Lào",
    },
    "dangkyxe_ptm": {
        "componentName": "phi thương mại]Giấy chứng nhận đăng ký xe",
        "loaiBan": "Bản sao",
        "documentName": "[Phi thương mại] Giấy chứng nhận đăng ký xe ô tô",
    },
    "denghi_ptm": {
        "componentName": "phi thương mại]Giấy đề nghị",
        "loaiBan": "Bản chính",
        "documentName": "[Phi thương mại] Giấy đề nghị cấp, cấp lại Giấy phép theo mẫu",
    },
}
_ALLOWED_DOC_TYPES = {_DE_NGHI, _DANG_KY_XE, _HOP_DONG, _QUYET_DINH, _CCCD, _OTHER}
_SKIP_DOCS = {_CCCD}


def _row_id(doc_type: str, thuong_mai: bool) -> str:
    """docType + cờ thương mại → id dòng trên bảng (None nếu không có dòng riêng)."""
    if doc_type == _QUYET_DINH:
        return "quyet_dinh"
    if doc_type == _DANG_KY_XE:
        return "dangkyxe_tm" if thuong_mai else "dangkyxe_ptm"
    if doc_type == _DE_NGHI:
        return "denghi_tm" if thuong_mai else "denghi_ptm"
    if doc_type == _HOP_DONG:
        return "hopdong"
    return ""


def _is_identity_text(text: str) -> bool:
    h = _fold(text)
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport"))


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM)."""
    h = _fold(text)
    if not h:
        return ""
    if "quyet dinh" in h and ("cu di cong tac" in h or "di cong tac" in h):
        return _QUYET_DINH
    if "de nghi cap" in h and "giay phep lien van" in h:
        return _DE_NGHI
    if ("dang ky xe" in h or "chung nhan dang ky xe" in h) and ("bien so" in h or "so khung" in h or "so may" in h):
        return _DANG_KY_XE
    if "hop dong" in h or ("cong trinh" in h and ("du an" in h or "lao" in h)) or "tai lieu chung minh" in h:
        return _HOP_DONG
    if _is_identity_text(h):
        return _CCCD
    return ""


def _rule_thuong_mai(texts: list[str]) -> bool:
    """Suy cờ thương mại dự phòng từ OCR Giấy đề nghị."""
    joined = _fold(" ".join(texts))
    if "phi thuong mai" in joined:
        return False
    return "thuong mai" in joined and "phi thuong mai" not in joined


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if "quyet dinh" in text or "cong tac" in text:
        return _QUYET_DINH
    if "de nghi" in text:
        return _DE_NGHI
    if "dang ky xe" in text or "dangkyxe" in text:
        return _DANG_KY_XE
    if "hop dong" in text or "du an" in text or "cong trinh" in text:
        return _HOP_DONG
    if any(k in text for k in ("cccd", "can cuoc", "cmnd", "ho chieu")):
        return _CCCD
    return value if value in _ALLOWED_DOC_TYPES else _OTHER


async def _classify_with_llm(documents: list[dict[str, Any]]) -> tuple[bool, dict[int, str]]:
    if not documents:
        return False, {}
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=500, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    thuong_mai = bool(parsed.get("thuongMai"))
    out: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        out[idx] = _normalize_doc_type(str(item.get("docType") or item.get("type") or ""))
    return thuong_mai, out


def _build_row_item(file: dict, file_index: int, row_id: str, doc_type: str) -> dict:
    row = _ROW_DEFS[row_id]
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
    thuong_mai: bool = False,
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
        # LLM-primary: ưu tiên phán đoán LLM; rule dự phòng khi LLM trả other/không hợp lệ.
        if llm_type and llm_type != _OTHER:
            doc_type, source = llm_type, "llm"
        elif rule_type:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = _OTHER, "unknown"

        if doc_type in _SKIP_DOCS:
            classified.append({"fileName": file_name, "docType": doc_type, "source": source, "skipped": True})
            continue

        row_id = _row_id(doc_type, thuong_mai)
        if row_id:
            items.append(_build_row_item(file, idx, row_id, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "rowId": row_id, "source": source})
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
    thuong_mai = False
    llm_types: dict[int, str] = {}
    if llm_docs:
        try:
            thuong_mai, llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
            thuong_mai = _rule_thuong_mai([d["text"] for d in llm_docs])
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types, thuong_mai)
    errors.extend(warnings)
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "thuongMai": thuong_mai,
            "classified": classified,
            "skippedOcr": skipped_ocr,
            "rows": [{"rowId": k, **v} for k, v in _ROW_DEFS.items()],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
