"""Đính kèm "Thành phần hồ sơ" cho "Đăng ký biến động QSDĐ..." (cổng DVC Đà Nẵng — Angular Reactive Form,
engine FE `attp-row`).

Bảng thành phần hồ sơ có 13 loại giấy tờ (áp dụng cho nhiều tình huống biến động: chuyển đổi/chuyển
nhượng/thừa kế/tặng cho/góp vốn/cho thuê/tách-hợp thửa...). Mỗi hồ sơ chỉ dùng vài loại. FE khớp dòng bằng
componentName (substring fold), tick + chọn loaiBan + set file. Ta upload bản scan → loaiBan = "Bản chính".

Phân loại **LLM-primary**: LLM đọc OCR quyết định loại; rule keyword chỉ DỰ PHÒNG. CCCD / Hợp đồng ủy
quyền không có dòng riêng phù hợp → bỏ qua (trừ khi rơi vào "Văn bản đại diện").
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.chuyen_muc_dich_su_dung_dat_da_nang.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_LOAI_BAN = "Bản chính"

_DON = "don_bien_dong"
_HD_CHUYEN_QUYEN = "hop_dong_chuyen_quyen"
_HD_TAI_SAN_THUE = "hop_dong_tai_san_thue"
_VB_CHO_THUE = "van_ban_cho_thue"
_MAU_22 = "mau_22_tach_hop"
_VB_CAP_CHUNG = "van_ban_cap_chung_gcn"
_VB_DAI_DIEN = "van_ban_dai_dien"
_VB_DONG_Y = "van_ban_dong_y_nsdd"
_VB_THE_CHAP = "van_ban_nhan_the_chap"
_BAN_GOC_GCN = "ban_goc_gcn"
_VB_TANG_CHO = "van_ban_tang_cho"
_GCN_UBND = "ban_goc_gcn_ubnd"
_CCCD = "cccd"
_OTHER = "other"

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold vào tên dòng lấy từ DOM).
_ROWS: dict[str, dict[str, str]] = {
    _DON: {"componentName": "Đơn đăng ký biến động đất đai",
           "documentName": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18)"},
    _HD_CHUYEN_QUYEN: {"componentName": "Hợp đồng hoặc văn bản về việc chuyển quyền sử dụng đất",
           "documentName": "Hợp đồng/văn bản chuyển quyền sử dụng đất, tài sản gắn liền với đất"},
    _HD_TAI_SAN_THUE: {"componentName": "bán hoặc tặng cho hoặc để thừa kế hoặc góp vốn bằng tài sản gắn liền với đất",
           "documentName": "Hợp đồng/văn bản về tài sản gắn liền với đất thuê trả tiền hằng năm"},
    _VB_CHO_THUE: {"componentName": "cho thuê, cho thuê lại quyền sử dụng đất",
           "documentName": "Văn bản cho thuê, cho thuê lại quyền sử dụng đất (dự án hạ tầng)"},
    _MAU_22: {"componentName": "Mẫu số 22",
           "documentName": "Mẫu số 22 (trường hợp tách thửa, hợp thửa)"},
    _VB_CAP_CHUNG: {"componentName": "cấp chung một Giấy chứng nhận",
           "documentName": "Văn bản thỏa thuận cấp chung một Giấy chứng nhận"},
    _VB_DAI_DIEN: {"componentName": "Văn bản về việc đại diện",
           "documentName": "Văn bản về việc đại diện (ủy quyền thực hiện thủ tục)"},
    _VB_DONG_Y: {"componentName": "người sử dụng đất đồng ý cho chủ sở hữu tài sản",
           "documentName": "Văn bản người sử dụng đất đồng ý cho chủ sở hữu tài sản chuyển nhượng/tặng cho/góp vốn"},
    _VB_THE_CHAP: {"componentName": "bên nhận thế chấp về việc đồng ý",
           "documentName": "Văn bản bên nhận thế chấp đồng ý cho chuyển nhượng/tặng cho"},
    _BAN_GOC_GCN: {"componentName": "Bản gốc Giấy chứng nhận đã cấp",
           "documentName": "Bản gốc Giấy chứng nhận đã cấp"},
    _VB_TANG_CHO: {"componentName": "Văn bản tặng cho quyền sử dụng đất hoặc biên bản họp",
           "documentName": "Văn bản tặng cho QSDĐ hoặc biên bản họp + bản gốc Giấy chứng nhận"},
    _GCN_UBND: {"componentName": "bản gốc Giấy chứng nhận đã cấp cho Ủy ban nhân dân cấp xã",
           "documentName": "Bản gốc Giấy chứng nhận đã cấp cho UBND cấp xã"},
}
for _r in _ROWS.values():
    _r["loaiBan"] = _LOAI_BAN

# CCCD chỉ đối chiếu → bỏ qua.
_SKIP_DOCS = {_CCCD}
_ALLOWED_DOC_TYPES = set(_ROWS) | _SKIP_DOCS | {_OTHER}


def _is_identity_text(text: str) -> bool:
    h = _fold(text)
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport"))


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM). Thứ tự: dấu hiệu đặc trưng trước, GCN gốc sau."""
    h = _fold(text)
    if not h:
        return ""
    if "don dang ky bien dong" in h or "mau so 18" in h:
        return _DON
    if "mau so 22" in h:
        return _MAU_22
    if "hop dong uy quyen" in h or ("uy quyen" in h and "ben duoc uy quyen" in h):
        return _VB_DAI_DIEN
    if ("hop dong" in h or "van ban" in h) and "chuyen nhuong" in h and "quyen su dung dat" in h:
        return _HD_CHUYEN_QUYEN
    if ("hop dong" in h or "van ban" in h) and ("tang cho" in h or "thua ke" in h or "gop von" in h) \
            and "quyen su dung dat" in h:
        return _HD_CHUYEN_QUYEN
    if "cho thue" in h and "quyen su dung dat" in h:
        return _VB_CHO_THUE
    # Giấy chứng nhận QSDĐ (sổ đỏ) — bản gốc.
    if "giay chung nhan quyen su dung dat" in h or ("giay chung nhan" in h and "quyen su dung dat" in h):
        return _BAN_GOC_GCN
    if _is_identity_text(h):
        return _CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if text in _ALLOWED_DOC_TYPES:
        return text
    if "18" in text or ("don" in text and "bien dong" in text):
        return _DON
    if "22" in text or "tach" in text or "hop thua" in text:
        return _MAU_22
    if "dai dien" in text or "uy quyen" in text:
        return _VB_DAI_DIEN
    if "cho thue" in text:
        return _VB_CHO_THUE
    if "the chap" in text:
        return _VB_THE_CHAP
    if "dong y" in text:
        return _VB_DONG_Y
    if "cap chung" in text:
        return _VB_CAP_CHUNG
    if "ubnd" in text or "uy ban" in text:
        return _GCN_UBND
    if "tang cho" in text and "bien ban" in text:
        return _VB_TANG_CHO
    if "tai san" in text and "thue" in text:
        return _HD_TAI_SAN_THUE
    if "hop dong" in text or "chuyen quyen" in text or "chuyen nhuong" in text:
        return _HD_CHUYEN_QUYEN
    if "gcn" in text or "chung nhan" in text or "so do" in text:
        return _BAN_GOC_GCN
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
