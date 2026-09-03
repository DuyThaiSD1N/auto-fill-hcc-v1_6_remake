"""Đính kèm "Thành phần hồ sơ" cho "Giao đất, cho thuê đất, chuyển mục đích SDĐ; giao/cho thuê rừng; gia
hạn SDĐ" (cổng DVC Đà Nẵng — engine `attp-row`).

Bảng thành phần hồ sơ của form này có ~12 dòng theo NHIỀU NHÁNH (giao đất/cho thuê đất/chuyển mục đích/giao
rừng/cho thuê rừng/gia hạn). Mỗi hồ sơ chỉ dùng vài dòng. Ta chỉ route những loại giấy tờ NHẬN DIỆN được:
  (1)  Đơn theo Mẫu số 01                                   → Bản chính
  (8)  Một trong các Giấy chứng nhận (khoản 21 Điều 3.../Điều 137)/quyết định giao-thuê-chuyển MĐ → Bản sao
  (2)  Phương án sử dụng tầng đất mặt theo Mẫu số 26        → Bản chính  (đất chuyên trồng lúa)
  (3)  Dự án đầu tư + báo cáo/bản đồ hiện trạng rừng        → Bản chính  (giao đất và giao rừng)
  (4)  Kết quả/biên bản đấu giá cho thuê rừng               → Bản sao    (cho thuê đất và cho thuê rừng)
FE khớp dòng bằng componentName (substring fold vào nhãn dòng), tick + chọn loaiBan (Bản chính/Bản sao) +
set file. Phân loại **LLM-primary**; rule keyword chỉ DỰ PHÒNG. CCCD/ủy quyền/tờ khai thuế/cam kết KHÔNG có
dòng riêng → bỏ qua (chỉ đối chiếu).
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.giao_thue_chuyen_muc_dich_dat_da_nang.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON_M01 = "don_m01"
_GCN = "gcn"
_PHUONG_AN_DAT_MAT = "phuong_an_dat_mat"
_DU_AN_GIAO_RUNG = "du_an_giao_rung"
_DAU_GIA_THUE_RUNG = "dau_gia_thue_rung"
_CCCD = "cccd"
_OTHER = "other"

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold vào nhãn dòng lấy từ DOM).
# loaiBan theo yêu cầu từng dòng (đọc từ HTML đính kèm thật — mỗi dòng đều có radio Bản chính/Bản sao).
_ROWS: dict[str, dict[str, str]] = {
    _DON_M01: {"componentName": "Đơn theo Mẫu số 01", "loaiBan": "Bản chính",
               "documentName": "Đơn đề nghị theo Mẫu số 01"},
    # Dòng (8): "Một trong các giấy chứng nhận quy định tại khoản 21 Điều 3, khoản 3 Điều 256... hoặc quyết
    # định giao đất, quyết định cho thuê đất, quyết định cho phép chuyển mục đích...". "khoản 21 Điều 3" là
    # cụm ĐẶC TRƯNG chỉ có ở dòng này (phân biệt dòng 12 "Một trong các giấy tờ sau: + Bản sao...").
    _GCN: {"componentName": "khoản 21 Điều 3", "loaiBan": "Bản sao",
           "documentName": "Giấy chứng nhận quyền sử dụng đất / quyết định giao, cho thuê, cho phép chuyển "
                           "mục đích sử dụng đất"},
    _PHUONG_AN_DAT_MAT: {"componentName": "Phương án sử dụng tầng đất mặt", "loaiBan": "Bản chính",
           "documentName": "Phương án sử dụng tầng đất mặt theo Mẫu số 26 (đất chuyên trồng lúa)"},
    _DU_AN_GIAO_RUNG: {"componentName": "Dự án đầu tư đối với khu rừng", "loaiBan": "Bản chính",
           "documentName": "Dự án đầu tư + báo cáo, bản đồ hiện trạng rừng (giao đất và giao rừng)"},
    _DAU_GIA_THUE_RUNG: {"componentName": "Kết quả đấu giá thuê rừng", "loaiBan": "Bản sao",
           "documentName": "Kết quả/biên bản đấu giá cho thuê rừng + thông báo hoàn thành nghĩa vụ tài chính"},
}

# CCCD chỉ đối chiếu → bỏ qua.
_SKIP_DOCS = {_CCCD}
_ALLOWED_DOC_TYPES = set(_ROWS) | _SKIP_DOCS | {_OTHER}


def _is_identity_text(text: str) -> bool:
    h = _fold(text)
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport"))


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM). Dấu hiệu đặc trưng trước, GCN sau."""
    h = _fold(text)
    if not h:
        return ""
    if "mau so 01" in h and ("don" in h or "de nghi" in h):
        return _DON_M01
    if "phuong an su dung tang dat mat" in h or "mau so 26" in h:
        return _PHUONG_AN_DAT_MAT
    if "hien trang rung" in h or ("du an dau tu" in h and "rung" in h):
        return _DU_AN_GIAO_RUNG
    if "dau gia" in h and "thue rung" in h:
        return _DAU_GIA_THUE_RUNG
    if "giay chung nhan quyen su dung dat" in h or ("giay chung nhan" in h and "quyen su dung dat" in h):
        return _GCN
    if "quyet dinh giao dat" in h or "quyet dinh cho thue dat" in h or "quyet dinh cho phep chuyen muc dich" in h:
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
    if "01" in text or ("don" in text and "de nghi" in text):
        return _DON_M01
    if "dat mat" in text or "26" in text:
        return _PHUONG_AN_DAT_MAT
    if "giao rung" in text or ("du an" in text and "rung" in text):
        return _DU_AN_GIAO_RUNG
    if "dau gia" in text and "rung" in text:
        return _DAU_GIA_THUE_RUNG
    if "gcn" in text or "chung nhan" in text or "so do" in text or "quyet dinh" in text:
        return _GCN
    if "cccd" in text or "can cuoc" in text or "cmnd" in text or "ho chieu" in text:
        return _CCCD
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
        # LLM-PRIMARY: ưu tiên LLM; rule chỉ dùng khi LLM rỗng/không hợp lệ (lỗi 502...).
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
