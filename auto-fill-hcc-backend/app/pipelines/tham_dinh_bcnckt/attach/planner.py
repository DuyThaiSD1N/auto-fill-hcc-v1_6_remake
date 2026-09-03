"""Đính kèm bước "Thành phần hồ sơ" cho "Thẩm định BCNCKT đầu tư xây dựng" (cổng DVC Bộ Xây dựng
dvc.moc.gov.vn — Angular mat-table, engine FE `attp-row`, CÙNG cổng #113/#76/#91).

Bảng có 19 dòng, PHẦN LỚN "(nếu có)"/điều kiện (sửa chữa, vốn công, điều chỉnh, vi phạm, BIM). Chỉ classify
vào 8 dòng CÓ THẬT phổ biến; các dòng còn lại (kể cả QĐ điều chỉnh quy hoạch dòng 18 — dễ nhầm dòng 9) →
other, cán bộ tự đính. FE khớp dòng bằng componentName substring fold (không dùng componentIndex vì thứ tự
DOM ≠ thứ tự hiển thị).

Phân loại **LLM-primary**: LLM đọc OCR quyết định; rule keyword chỉ DỰ PHÒNG.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.tham_dinh_bcnckt.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_TO_TRINH = "to_trinh"
_MOI_TRUONG = "moi_truong"
_CHU_TRUONG = "chu_truong"
_DAU_NOI = "dau_noi"
_NHA_THAU = "nha_thau"
_QUY_HOACH = "quy_hoach"
_KHAO_SAT = "khao_sat_thiet_ke"
_GP_DAU_TU = "gp_dau_tu"
_OTHER = "other"

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold). loaiBan theo cột "Loại bản".
_ROWS: dict[str, dict[str, str]] = {
    _TO_TRINH: {
        "componentName": "Tờ trình thẩm định Báo cáo nghiên cứu khả thi đầu tư xây dựng",
        "loaiBan": "Bản chính",
        "documentName": "Tờ trình thẩm định BCNCKT đầu tư xây dựng (Mẫu số 01)",
    },
    _MOI_TRUONG: {
        "componentName": "phê duyệt kết quả thẩm định báo cáo đánh giá tác động môi trường",
        "loaiBan": "Bản sao",
        "documentName": "QĐ phê duyệt ĐTM / Giấy phép môi trường",
    },
    _CHU_TRUONG: {
        "componentName": "Văn bản về chủ trương đầu tư xây dựng công trình",
        "loaiBan": "Bản sao",
        "documentName": "Văn bản chủ trương đầu tư xây dựng công trình",
    },
    _DAU_NOI: {
        "componentName": "thỏa thuận, xác nhận về đấu nối hạ tầng kỹ thuật",
        "loaiBan": "Bản sao",
        "documentName": "Văn bản thỏa thuận đấu nối hạ tầng kỹ thuật / độ cao công trình",
    },
    _NHA_THAU: {
        "componentName": "Danh sách các nhà thầu kèm theo mã số chứng chỉ năng lực",
        "loaiBan": "Bản sao",
        "documentName": "Danh sách nhà thầu kèm mã số chứng chỉ năng lực/hành nghề",
    },
    _QUY_HOACH: {
        "componentName": "bản đồ, bản vẽ kèm theo (nếu có) của quy hoạch sử dụng làm căn cứ lập dự án",
        "loaiBan": "Bản sao",
        "documentName": "QĐ phê duyệt quy hoạch + bản đồ/bản vẽ (căn cứ lập dự án)",
    },
    _KHAO_SAT: {
        "componentName": "Hồ sơ khảo sát xây dựng được phê duyệt",
        "loaiBan": "Bản sao",
        "documentName": "Hồ sơ khảo sát XD + thuyết minh BCNCKT + thiết kế cơ sở",
    },
    _GP_DAU_TU: {
        "componentName": "Giấy phép đầu tư, Giấy chứng nhận ưu đãi đầu tư",
        "loaiBan": "Bản sao",
        "documentName": "Giấy phép/Giấy chứng nhận đầu tư",
    },
}
_ALLOWED_DOC_TYPES = set(_ROWS) | {_OTHER}


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM)."""
    h = _fold(text)
    if not h:
        return ""
    if "to trinh" in h and "bao cao nghien cuu kha thi" in h:
        return _TO_TRINH
    if "danh gia tac dong moi truong" in h or "giay phep moi truong" in h:
        return _MOI_TRUONG
    if "chu truong dau tu" in h:
        return _CHU_TRUONG
    if "dau noi ha tang" in h or ("thoa thuan" in h and "ha tang" in h):
        return _DAU_NOI
    if "danh sach" in h and "nha thau" in h and "chung chi" in h:
        return _NHA_THAU
    if "khao sat xay dung" in h and ("thiet ke co so" in h or "thuyet minh" in h):
        return _KHAO_SAT
    if "quy hoach" in h and ("1/500" in h or "chi tiet xay dung" in h or "phe duyet" in h):
        return _QUY_HOACH
    if "giay chung nhan dau tu" in h or "giay phep dau tu" in h or "dang ky dau tu" in h:
        return _GP_DAU_TU
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if "to trinh" in text:
        return _TO_TRINH
    if "moi truong" in text:
        return _MOI_TRUONG
    if "chu truong" in text:
        return _CHU_TRUONG
    if "dau noi" in text:
        return _DAU_NOI
    if "nha thau" in text:
        return _NHA_THAU
    if "quy hoach" in text:
        return _QUY_HOACH
    if "khao sat" in text or "thiet ke" in text:
        return _KHAO_SAT
    if "dau tu" in text:
        return _GP_DAU_TU
    return value if value in _ALLOWED_DOC_TYPES else _OTHER


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
        if llm_type in _ROWS:
            doc_type, source = llm_type, "llm"
        elif rule_type:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = _OTHER, "unknown"

        if doc_type in _ROWS:
            items.append(_build_row_item(file, idx, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "source": source})
            continue
        # other = giấy tờ không map dòng cố định (CCCD/ủy quyền/nội bộ, hoặc dòng điều kiện hiếm) → bỏ qua.
        classified.append({"fileName": file_name, "docType": _OTHER, "source": source, "skipped": True})

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
