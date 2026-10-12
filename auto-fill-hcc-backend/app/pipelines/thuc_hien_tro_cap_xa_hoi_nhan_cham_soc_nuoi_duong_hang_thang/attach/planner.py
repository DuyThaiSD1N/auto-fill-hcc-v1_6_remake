"""Đính kèm bước 2 "Thành phần hồ sơ" cho thủ tục "Thực hiện trợ cấp xã hội và nhận chăm sóc, nuôi dưỡng,
hỗ trợ kinh phí nhận chăm sóc, nuôi dưỡng hằng tháng" (cổng Bộ Y tế — Angular table, engine FE `attp-row`).

Bảng chỉ có HAI dòng (cùng ô "Chọn/Bỏ chọn tất cả" — không tick):
  1. Tờ khai đề nghị trợ cấp xã hội, trợ cấp hưu trí xã hội (Mẫu số 01 — NĐ 335/2026/NĐ-CP)
  2. Tờ khai nhận chăm sóc, nuôi dưỡng, đề nghị hỗ trợ kinh phí nhận chăm sóc, nuôi dưỡng (Mẫu số 02)
Mỗi dòng: mat-checkbox + rdo_File + ô upload multiple. Thủ tục không có ô riêng cho CCCD, Giấy xác nhận khuyết
tật... → các giấy tờ này đính CHUNG vào dòng tờ khai chính (Mẫu 01; hồ sơ chỉ có Mẫu 02 thì dòng Mẫu 02), xếp
sau tờ khai: Tờ khai → căn cước → cư trú → khai sinh → khuyết tật → giấy tờ khác. Dòng Mẫu 02 chỉ tick khi hồ
sơ có Tờ khai Mẫu 02.

Phân loại **LLM-primary**: LLM đọc OCR mọi file; rule keyword chỉ DỰ PHÒNG khi LLM trả other/không hợp lệ.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.thuc_hien_tro_cap_xa_hoi_nhan_cham_soc_nuoi_duong_hang_thang.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_LOAI_BAN = "Scan tệp tin"

_TK_01 = "to_khai_mau_01"
_TK_02 = "to_khai_mau_02"
_CAN_CUOC = "can_cuoc"
_CU_TRU = "cu_tru"
_KHAI_SINH = "khai_sinh"
_KHUYET_TAT = "khuyet_tat"
_OTHER = "other"

# componentName = đoạn text đặc trưng của dòng (FE khớp substring đã fold dấu vào tên dòng lấy từ DOM).
_ROW_MAU_01 = "Tờ khai đề nghị trợ cấp xã hội"
_ROW_MAU_02 = "Tờ khai nhận chăm sóc, nuôi dưỡng"

# Tên tệp tải lên (engine attp-row đổi tên theo documentName) + thứ tự trong dòng.
_DOC_NAMES: dict[str, str] = {
    _TK_01: "Tờ khai đề nghị trợ cấp xã hội (Mẫu số 01)",
    _TK_02: "Tờ khai nhận chăm sóc, nuôi dưỡng (Mẫu số 02)",
    _CAN_CUOC: "Căn cước",
    _CU_TRU: "Giấy xác nhận thông tin về cư trú",
    _KHAI_SINH: "Giấy khai sinh",
    _KHUYET_TAT: "Giấy xác nhận khuyết tật",
}
_ORDER = [_TK_01, _TK_02, _CAN_CUOC, _CU_TRU, _KHAI_SINH, _KHUYET_TAT, _OTHER]
_ALLOWED_DOC_TYPES = set(_ORDER)


def _is_identity_text(h: str) -> bool:
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport",
                                "citizen identity", "identity card"))


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM). Tờ khai nhận trước: Mẫu 01 có nhắc "giấy xác nhận
    khuyết tật số..." nên không được để rule khuyết tật bắt trước."""
    h = _fold(text)
    if not h:
        return ""
    if "to khai" in h:
        if "nhan cham soc, nuoi duong" in h or "nhan cham soc nuoi duong" in h:
            return _TK_02
        if "de nghi tro cap xa hoi" in h or "tro cap huu tri xa hoi" in h:
            return _TK_01
    if "xac nhan khuyet tat" in h or "giam dinh y khoa" in h or "muc do khuyet tat" in h:
        return _KHUYET_TAT
    if "giay khai sinh" in h or "trich luc khai sinh" in h:
        return _KHAI_SINH
    if "thong tin ve cu tru" in h or "thong bao so dinh danh" in h:
        return _CU_TRU
    if _is_identity_text(h):
        return _CAN_CUOC
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "").replace("_", " ")
    if not text or text == "other":
        return _OTHER
    if "02" in text or "nhan cham soc" in text:
        return _TK_02
    if "01" in text or "to khai" in text:
        return _TK_01
    if "khuyet tat" in text or "giam dinh" in text:
        return _KHUYET_TAT
    if "khai sinh" in text:
        return _KHAI_SINH
    if "cu tru" in text or "dinh danh" in text:
        return _CU_TRU
    if "can cuoc" in text or "cccd" in text or "cmnd" in text:
        return _CAN_CUOC
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


def _file_label(document_name: str) -> str:
    # Tên tệp tải lên không được chứa "/" (trình duyệt/cổng coi là đường dẫn, cắt mất phần trước).
    return document_name.replace(" / ", ", ").replace("/", ", ")


def _build_row_item(file: dict, file_index: int, doc_type: str, component_name: str, document_name: str) -> dict:
    return {
        "fileIndex": file_index,
        "fileName": str(file.get("name") or f"file-{file_index + 1}"),
        "documentName": document_name,
        "componentName": component_name,
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
    warnings: list[str] = []
    classified: list[dict] = []
    typed: list[tuple[int, dict, str]] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = str(by_name.get(file_name, {}).get("text") or "")
        llm_type = llm_types.get(idx, "")
        rule_type = _rule_doc_type(text)
        # LLM-primary: ưu tiên phán đoán của LLM; rule keyword chỉ dự phòng khi LLM trả other/không hợp lệ.
        if llm_type in _ALLOWED_DOC_TYPES and llm_type != _OTHER:
            doc_type, source = llm_type, "llm"
        elif rule_type:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = _OTHER, "unknown" if not llm_type else "llm"
        typed.append((idx, file, doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "source": source})

    has_01 = any(t == _TK_01 for _, _, t in typed)
    has_02 = any(t == _TK_02 for _, _, t in typed)
    # Dòng nhận giấy tờ dùng chung: Mẫu 01; hồ sơ chỉ có Mẫu 02 (hộ nhận chăm sóc) thì dòng Mẫu 02.
    main_row = _ROW_MAU_02 if has_02 and not has_01 else _ROW_MAU_01
    if not has_01 and not has_02 and files:
        warnings.append(
            "Không thấy Tờ khai Mẫu số 01/02 trong các tệp — giấy tờ được đính vào dòng Tờ khai Mẫu số 01; "
            "cán bộ bổ sung tờ khai."
        )

    items: list[dict] = []
    name_counts: dict[str, int] = {}
    for idx, file, doc_type in sorted(typed, key=lambda t: (_ORDER.index(t[2]), t[0])):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        component = _ROW_MAU_02 if doc_type == _TK_02 else main_row
        if doc_type == _OTHER:
            # Chưa biết loại → giữ TÊN GỐC để cán bộ không nhầm với tờ khai cùng dòng.
            document_name = file_name
            warnings.append(
                f"Chưa nhận diện chắc loại giấy tờ cho '{file_name}' — đính chung vào dòng "
                f"{'Tờ khai Mẫu số 02' if component == _ROW_MAU_02 else 'Tờ khai Mẫu số 01'}; cán bộ kiểm tra lại."
            )
        else:
            document_name = _file_label(_DOC_NAMES[doc_type])
            name_counts[document_name] = name_counts.get(document_name, 0) + 1
            if name_counts[document_name] > 1:
                document_name = f"{document_name} {name_counts[document_name]}"
        items.append(_build_row_item(file, idx, doc_type, component, document_name))

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
            "rows": [_ROW_MAU_01, _ROW_MAU_02],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
