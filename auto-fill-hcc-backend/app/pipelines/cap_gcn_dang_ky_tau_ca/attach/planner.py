"""Đính kèm bước "Thành phần hồ sơ" cho thủ tục "Cấp giấy chứng nhận đăng ký tàu cá, tàu phục vụ nuôi
trồng thủy sản" (cổng Nông nghiệp & Môi trường — Angular mat-table 16 dòng, engine FE `attp-row`).

Bảng có 16 dòng cố định; mỗi dòng 3 nút loại bản (Bản chính / Bản sao / Scan tệp tin). Ta upload bản
SCAN → loaiBan = "Scan tệp tin". FE khớp dòng bằng componentName (substring fold); các dòng có nhãn LỒNG
nhau (Giấy chứng nhận xóa đăng ký ở dòng 3/8/13) được disambiguate bằng componentIndex (vị trí dòng).

Phân loại **LLM-primary**: LLM đọc OCR quyết định loại; rule keyword chỉ DỰ PHÒNG. CCCD chỉ đối chiếu,
KHÔNG có dòng riêng → bỏ qua. Ảnh tàu (file ảnh, OCR nghèo) thường không phân loại được → để thủ công.

⚠ Route mặc định theo doc-type PHỔ BIẾN: Giấy chứng nhận xóa đăng ký → dòng 8 (mua bán trong tỉnh/thành
phố). Trường hợp nhập khẩu (dòng 3) / mua bán ngoài tỉnh (dòng 13) hiếm → cần hồ sơ thật để tinh chỉnh.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.cap_gcn_dang_ky_tau_ca.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_LOAI_BAN = "Scan tệp tin"

# doc-type → dòng thành phần hồ sơ. componentIndex = STT dòng trên bảng (1..16) để chọn đúng dòng lồng nhau.
_ROWS: dict[str, dict[str, Any]] = {
    "gcn_an_toan_ky_thuat": {
        "componentName": "Giấy chứng nhận an toàn kỹ thuật", "componentIndex": 1,
        "documentName": "Giấy chứng nhận an toàn kỹ thuật của tàu cá (Mẫu số 05.BĐ)",
    },
    "to_khai_hai_quan": {
        "componentName": "Tờ khai hải quan", "componentIndex": 2,
        "documentName": "Tờ khai hải quan",
    },
    "tb_thue_truoc_ba": {
        "componentName": "Biên lai nộp thuế trước bạ", "componentIndex": 4,
        "documentName": "Thông báo nộp lệ phí trước bạ",
    },
    "to_khai_02a": {
        "componentName": "Tờ khai đăng ký theo Mẫu số 02a", "componentIndex": 5,
        "documentName": "Tờ khai đăng ký tàu cá (Mẫu số 02a.ĐKT)",
    },
    "gcn_dang_ky_tau_ca_cu": {
        "componentName": "Giấy chứng nhận đăng ký tàu cá cũ", "componentIndex": 7,
        "documentName": "Giấy chứng nhận đăng ký tàu cá cũ kèm hồ sơ đăng ký gốc",
    },
    "gcn_xoa_dang_ky": {
        "componentName": "Giấy chứng nhận xóa đăng ký", "componentIndex": 8,
        "documentName": "Giấy chứng nhận xóa đăng ký",
    },
    "to_khai_02c": {
        "componentName": "Tờ khai đăng ký theo Mẫu số 02c", "componentIndex": 9,
        "documentName": "Tờ khai đăng ký tàu cá (Mẫu số 02c.ĐK)",
    },
    "hop_dong_thue_tau_tran": {
        "componentName": "hợp đồng thuê tàu trần", "componentIndex": 10,
        "documentName": "Hợp đồng thuê tàu trần",
    },
    "gcn_xuat_xuong": {
        "componentName": "Giấy chứng nhận xuất xưởng", "componentIndex": 11,
        "documentName": "Giấy chứng nhận xuất xưởng (Mẫu số 03.ĐKT)",
    },
    "giay_to_chuyen_nhuong": {
        "componentName": "Giấy tờ chuyển nhượng quyền sở hữu tàu", "componentIndex": 14,
        "documentName": "Giấy tờ chuyển nhượng quyền sở hữu tàu (Hợp đồng mua bán)",
    },
    "gcn_cai_hoan": {
        "componentName": "Giấy chứng nhận cải hoán", "componentIndex": 15,
        "documentName": "Giấy chứng nhận cải hoán (Mẫu số 04.ĐKT)",
    },
}

_CCCD = "cccd"
_OTHER = "other"
_SKIP_DOCS = {_CCCD}
_ALLOWED_DOC_TYPES = set(_ROWS) | _SKIP_DOCS | {_OTHER}


def _is_identity_text(text: str) -> bool:
    h = _fold(text)
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport"))


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM)."""
    h = _fold(text)
    if not h:
        return ""
    if _is_identity_text(h):
        return _CCCD
    if "to khai hai quan" in h:
        return "to_khai_hai_quan"
    if "truoc ba" in h and any(k in h for k in ("thong bao", "bien lai", "co quan thue", "le phi")):
        return "tb_thue_truoc_ba"
    if "thue tau tran" in h:
        return "hop_dong_thue_tau_tran"
    if "02c" in h:
        return "to_khai_02c"
    if "to khai" in h and ("02a" in h or ("dang ky" in h and "tau ca" in h and "giay chung nhan" not in h)):
        return "to_khai_02a"
    if "xuat xuong" in h:
        return "gcn_xuat_xuong"
    if "cai hoan" in h and any(k in h for k in ("giay chung nhan", "quyet dinh", "chap thuan", "04.dkt", "mau so 04")):
        return "gcn_cai_hoan"
    if "xoa dang ky" in h:
        return "gcn_xoa_dang_ky"
    if "an toan ky thuat" in h:
        return "gcn_an_toan_ky_thuat"
    if ("hop dong" in h and ("mua ban" in h or "chuyen nhuong" in h)) or ("ben ban" in h and "ben mua" in h):
        return "giay_to_chuyen_nhuong"
    if "giay chung nhan dang ky tau ca" in h and "xoa" not in h:
        return "gcn_dang_ky_tau_ca_cu"
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if text in {_fold(k) for k in _ALLOWED_DOC_TYPES}:
        # LLM trả đúng slug.
        for k in _ALLOWED_DOC_TYPES:
            if _fold(k) == text:
                return k
    if "hai quan" in text:
        return "to_khai_hai_quan"
    if "truoc ba" in text or "thue" in text:
        return "tb_thue_truoc_ba"
    if "02c" in text:
        return "to_khai_02c"
    if "thue tau tran" in text:
        return "hop_dong_thue_tau_tran"
    if "02a" in text or "to khai dang ky" in text:
        return "to_khai_02a"
    if "xuat xuong" in text:
        return "gcn_xuat_xuong"
    if "cai hoan" in text:
        return "gcn_cai_hoan"
    if "xoa dang ky" in text or "xoa" in text:
        return "gcn_xoa_dang_ky"
    if "an toan ky thuat" in text:
        return "gcn_an_toan_ky_thuat"
    if "chuyen nhuong" in text or "mua ban" in text:
        return "giay_to_chuyen_nhuong"
    if "dang ky tau ca" in text:
        return "gcn_dang_ky_tau_ca_cu"
    if any(k in text for k in ("cccd", "can cuoc", "cmnd", "ho chieu")):
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
        "componentIndex": row["componentIndex"],
        "loaiBan": _LOAI_BAN,
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
        if doc_type == _CCCD:
            # CCCD chỉ đối chiếu ở bước thông tin, không có dòng đính kèm → bỏ qua.
            classified.append({"fileName": file_name, "docType": _CCCD, "source": source})
            continue

        warnings.append(f"Không xác định được loại giấy tờ cho file '{file_name}' — vui lòng đính kèm thủ công.")
        classified.append({"fileName": file_name, "docType": _OTHER, "source": source, "manualAttachment": True})

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
    manual = [item for item in classified if item.get("manualAttachment")]
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "classified": classified,
            "manualAttachments": manual,
            "skippedOcr": skipped_ocr,
            "rows": [{"docType": k, **v} for k, v in _ROWS.items()],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
