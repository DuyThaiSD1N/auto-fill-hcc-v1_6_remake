"""Đính kèm bước "Thành phần hồ sơ" cho thủ tục "Thực hiện, điều chỉnh, thôi hưởng trợ cấp xã hội hàng
tháng, hỗ trợ kinh phí chăm sóc, nuôi dưỡng hàng tháng" (cổng Bộ Y tế — Angular table).

Trang thành phần hồ sơ là BẢNG 9 dòng (MỤC 1-9); mỗi dòng có: mat-checkbox (chọn) + rdo_File (Bản chính /
Scan tệp tin) + ô upload (input[type=file]). Giống ATTP (Bộ Công Thương) — FE phải TICK checkbox + chọn
loại bản + set file vào đúng dòng, khớp dòng bằng TÊN giấy tờ (componentName, substring fold). Xem engine
FE `attachFilesByAttpRow` (target "attp-row"). Ta upload BẢN SCAN → loaiBan = "Scan tệp tin".

Phân loại **LLM-primary**: LLM đọc OCR mọi file quyết định loại; rule keyword chỉ DỰ PHÒNG khi LLM trả
other/không hợp lệ. Mỗi loại → 1 dòng; FE gom item theo componentName rồi set nhiều file 1 lần. Giấy tờ
nguồn không có dòng riêng (ủy quyền) → bỏ qua.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.tro_cap_xa_hoi_hang_thang.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_LOAI_BAN = "Scan tệp tin"

_TK_DOITUONG = "to_khai_doi_tuong"
_TK_HOGD = "to_khai_ho_gd_khuyet_tat"
_TK_CHAMSOC = "to_khai_cham_soc"
_TK_DUOC_CHAMSOC = "to_khai_duoc_cham_soc"
_CU_TRU_CCCD = "cu_tru_cccd"
_KHAI_SINH = "khai_sinh"
_HIV = "hiv"
_MANG_THAI = "mang_thai"
_KHUYET_TAT = "khuyet_tat"
_GIAM_DINH = "bien_ban_giam_dinh"
_UY_QUYEN = "uy_quyen"
_OTHER = "other"

# Mỗi loại giấy tờ → 1 dòng trong bảng. componentName = ĐOẠN TEXT ĐẶC TRƯNG DUY NHẤT của dòng (FE khớp
# substring đã fold dấu vào tên dòng lấy từ DOM). loaiBan = "Scan tệp tin" (đều là file scan/PDF/ảnh chụp).
# Biên bản giám định y khoa (căn cứ khuyết tật) đính CHUNG dòng "Giấy xác nhận khuyết tật" (MỤC 9).
_ROWS: dict[str, dict[str, str]] = {
    _TK_DOITUONG: {
        "componentName": "Mẫu số 1a, 1b, 1c, 1d",
        "loaiBan": _LOAI_BAN,
        "documentName": "Tờ khai đề nghị trợ giúp xã hội (Mẫu số 1a/1b/1c/1d/1đ)",
    },
    _TK_HOGD: {
        "componentName": "Tờ khai hộ gia đình có người khuyết tật",
        "loaiBan": _LOAI_BAN,
        "documentName": "Tờ khai hộ gia đình có người khuyết tật (Mẫu số 2a)",
    },
    _TK_CHAMSOC: {
        "componentName": "nhận chăm sóc, nuôi dưỡng đối tượng bảo trợ xã hội",
        "loaiBan": _LOAI_BAN,
        "documentName": "Tờ khai nhận chăm sóc, nuôi dưỡng đối tượng bảo trợ xã hội (Mẫu số 2b)",
    },
    _TK_DUOC_CHAMSOC: {
        "componentName": "được nhận chăm sóc, nuôi dưỡng trong trường hợp",
        "loaiBan": _LOAI_BAN,
        "documentName": "Tờ khai của đối tượng được nhận chăm sóc, nuôi dưỡng (Mẫu số 03)",
    },
    _CU_TRU_CCCD: {
        "componentName": "Giấy xác nhận thông tin về cư trú",
        "loaiBan": _LOAI_BAN,
        "documentName": "Giấy xác nhận thông tin về cư trú / định danh cá nhân / CCCD",
    },
    _KHAI_SINH: {
        "componentName": "Giấy khai sinh của trẻ em",
        "loaiBan": _LOAI_BAN,
        "documentName": "Giấy khai sinh của trẻ em",
    },
    _HIV: {
        "componentName": "nhiễm HIV",
        "loaiBan": _LOAI_BAN,
        "documentName": "Giấy tờ xác nhận bị nhiễm HIV",
    },
    _MANG_THAI: {
        "componentName": "đang mang thai",
        "loaiBan": _LOAI_BAN,
        "documentName": "Giấy tờ xác nhận đang mang thai",
    },
    _KHUYET_TAT: {
        "componentName": "Giấy xác nhận khuyết tật",
        "loaiBan": _LOAI_BAN,
        "documentName": "Giấy xác nhận khuyết tật",
    },
    _GIAM_DINH: {
        "componentName": "Giấy xác nhận khuyết tật",
        "loaiBan": _LOAI_BAN,
        "documentName": "Biên bản giám định y khoa (kèm Giấy xác nhận khuyết tật)",
    },
}
# Giấy tờ nguồn KHÔNG có dòng riêng trên bảng thành phần hồ sơ → bỏ qua.
_SKIP_DOCS = {_UY_QUYEN}
_ALLOWED_DOC_TYPES = set(_ROWS) | _SKIP_DOCS | {_OTHER}


def _is_identity_text(text: str) -> bool:
    h = _fold(text)
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport"))


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM). Nhận giấy tờ đặc trưng TRƯỚC."""
    h = _fold(text)
    if not h:
        return ""
    # Giấy ủy quyền.
    if "giay uy quyen" in h or ("uy quyen" in h and "ben uy quyen" in h):
        return _UY_QUYEN
    # Biên bản giám định y khoa.
    if "giam dinh y khoa" in h or "hoi dong giam dinh" in h:
        return _GIAM_DINH
    # Giấy xác nhận khuyết tật.
    if "xac nhan khuyet tat" in h or "giay xac nhan khuyet tat" in h:
        return _KHUYET_TAT
    # Xác nhận nhiễm HIV.
    if "nhiem hiv" in h or "xet nghiem hiv" in h:
        return _HIV
    # Xác nhận đang mang thai.
    if "mang thai" in h or "thai nhi" in h:
        return _MANG_THAI
    # Tờ khai — phân biệt theo mẫu số.
    if "to khai" in h:
        if "mau so 2a" in h or ("ho gia dinh" in h and "khuyet tat" in h):
            return _TK_HOGD
        if "mau so 2b" in h or "nhan cham soc, nuoi duong doi tuong bao tro" in h:
            return _TK_CHAMSOC
        if "mau so 03" in h or "duoc nhan cham soc, nuoi duong" in h:
            return _TK_DUOC_CHAMSOC
        if any(k in h for k in ("mau so 1a", "mau so 1b", "mau so 1c", "mau so 1d", "mau so 1d ")) \
                or "de nghi tro giup xa hoi" in h:
            return _TK_DOITUONG
    # Giấy khai sinh.
    if "giay khai sinh" in h or ("khai sinh" in h and "ho tich" in h):
        return _KHAI_SINH
    # Xác nhận cư trú / định danh.
    if "thong tin ve cu tru" in h or "so dinh danh ca nhan" in h or "thong bao so dinh danh" in h:
        return _CU_TRU_CCCD
    # CCCD/CMND (sau cùng, cũng thuộc dòng cư trú/CCCD).
    if _is_identity_text(h):
        return _CU_TRU_CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if "uy quyen" in text:
        return _UY_QUYEN
    if "giam dinh" in text:
        return _GIAM_DINH
    if "khuyet tat" in text and "ho gia dinh" not in text:
        return _KHUYET_TAT
    if "hiv" in text:
        return _HIV
    if "mang thai" in text:
        return _MANG_THAI
    if "ho gd" in text or "ho gia dinh" in text or "2a" in text:
        return _TK_HOGD
    if "duoc cham soc" in text or "duoc_cham_soc" in text or "03" in text:
        return _TK_DUOC_CHAMSOC
    if "cham soc" in text or "2b" in text:
        return _TK_CHAMSOC
    if "doi tuong" in text or "1a" in text or "1b" in text or "1c" in text or "1d" in text:
        return _TK_DOITUONG
    if "khai sinh" in text:
        return _KHAI_SINH
    if "cu tru" in text or "cccd" in text or "can cuoc" in text or "dinh danh" in text:
        return _CU_TRU_CCCD
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
        # LLM-primary: ưu tiên phán đoán của LLM; rule keyword chỉ dự phòng khi LLM trả other/không hợp lệ.
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
    # LLM-primary: gửi MỌI file có OCR text cho LLM phân loại.
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
