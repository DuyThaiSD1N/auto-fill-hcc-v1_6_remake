"""Đính kèm bước "Thành phần hồ sơ" cho thủ tục "Cấp lại Chứng chỉ hành nghề thú y" (Sở Nông nghiệp và
Môi trường — Angular mat-table, engine FE `attp-row`).

Bảng thành phần hồ sơ có 1 dòng cố định: "Đơn đăng ký cấp lại." (mẫu 03.HNTY), cột "Loại bản" là radio
rdo_File "1 Bản chính / 1 Bản sao" và cột đính kèm có "Scan tệp tin" / "Chọn tệp tin". FE khớp dòng bằng
componentName (substring fold), tick checkbox + chọn loaiBan "Bản chính" + set file.

Vì form CHỈ có 1 ô đính kèm, mọi giấy tờ trừ CCCD đều vào dòng này (ô upload nhận nhiều file): Đơn
03.HNTY giữ tên chuẩn, Chứng chỉ hành nghề cũ / ảnh 4x6 / giấy tờ khác giữ TÊN GỐC để khỏi trùng tên.

Phân loại **LLM-primary**: LLM đọc OCR quyết định loại; rule keyword chỉ DỰ PHÒNG. CCCD KHÔNG có dòng
riêng (chỉ dùng ở bước thông tin) → bỏ qua.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.cap_lai_CCHN_thu_y.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# Cột "Loại bản" của dòng duy nhất: mẫu hướng dẫn chốt "1 Bản chính".
_LOAI_BAN = "Bản chính"

_DON = "don_cap_lai"
_CCHN_CU = "cchn_cu"
_ANH_THE = "anh_the"
_CCCD = "cccd"
_OTHER = "other"

_ROWS: dict[str, dict[str, str]] = {
    _DON: {
        "componentName": "Đơn đăng ký cấp lại",
        "loaiBan": _LOAI_BAN,
        "documentName": "Đơn đăng ký cấp lại Chứng chỉ hành nghề thú y (Mẫu 03.HNTY)",
    },
}
# CCCD chỉ dùng đối chiếu ở bước thông tin, KHÔNG có dòng riêng trên bảng → bỏ qua.
_SKIP_DOCS = {_CCCD}
_ALLOWED_DOC_TYPES = set(_ROWS) | _SKIP_DOCS | {_CCHN_CU, _ANH_THE, _OTHER}


def _is_identity_text(text: str) -> bool:
    h = _fold(text)
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport"))


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM)."""
    h = _fold(text)
    if not h:
        return ""
    # Đơn đăng ký cấp lại Mẫu 03.HNTY — nhận TRƯỚC chứng chỉ cũ vì đơn cũng nhắc "chứng chỉ hành nghề".
    if "don dang ky cap lai" in h or "03.hnty" in h or "03 hnty" in h \
            or ("don dang ky" in h and "hanh nghe thu y" in h) \
            or ("cap lai" in h and "hanh nghe thu y" in h and "nguoi lam don" in h):
        return _DON
    # Chứng chỉ hành nghề thú y đã cấp.
    if "chung chi hanh nghe thu y" in h and ("so dang ky" in h or "co gia tri den" in h):
        return _CCHN_CU
    # CCCD/CMND (bỏ qua).
    if _is_identity_text(h):
        return _CCCD
    return ""


def _is_photo_only(file: dict, text: str) -> bool:
    """Ảnh chân dung 4x6: file ẢNH mà OCR ra (gần như) không có chữ."""
    return str(file.get("type") or "") in {"image/jpeg", "image/png", "image/jpg"} and len(_fold(text)) < 20


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if "don" in text or "03" in text:
        return _DON
    if "cchn" in text or "chung chi" in text:
        return _CCHN_CU
    if "anh" in text or "4x6" in text:
        return _ANH_THE
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
    raw = await client.chat(messages, max_tokens=400, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    out: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        out[idx] = _normalize_doc_type(str(item.get("docType") or item.get("type") or ""))
    return out


def _build_row_item(file: dict, file_index: int, doc_type: str, document_name: str) -> dict:
    row = _ROWS[_DON]
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
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
        if llm_type in _ALLOWED_DOC_TYPES and llm_type != _OTHER:
            doc_type, source = llm_type, "llm"
        elif rule_type:
            doc_type, source = rule_type, "rule"
        elif _is_photo_only(file, text):
            # Ảnh 4x6 gần như không có chữ nên LLM/rule đều bó tay; ảnh không OCR ra chữ trong hồ sơ này
            # chỉ có thể là ảnh chân dung → khỏi cảnh báo oan.
            doc_type, source = _ANH_THE, "rule"
        else:
            doc_type, source = _OTHER, "unknown"

        if doc_type in _SKIP_DOCS:
            classified.append({"fileName": file_name, "docType": doc_type, "source": source, "skipped": True})
            continue

        # Form chỉ có 1 dòng "Đơn đăng ký cấp lại" (ô upload nhận NHIỀU file) → mọi giấy tờ còn lại vào
        # dòng này. Đơn → tên chuẩn Mẫu 03.HNTY; chứng chỉ cũ/ảnh 4x6/giấy tờ khác → giữ TÊN GỐC.
        document_name = _ROWS[_DON]["documentName"] if doc_type == _DON else file_name
        items.append(_build_row_item(file, idx, doc_type, document_name))
        classified.append({"fileName": file_name, "docType": doc_type, "source": source})
        if doc_type == _OTHER:
            warnings.append(
                f"Không xác định được loại giấy tờ cho file '{file_name}' — đã đính vào dòng "
                "'Đơn đăng ký cấp lại', vui lòng kiểm tra lại."
            )

    if not any(item["detectedType"] == _DON for item in items):
        warnings.append(
            "Không tìm thấy Đơn đăng ký cấp lại Chứng chỉ hành nghề thú y (Mẫu 03.HNTY) trong hồ sơ."
        )

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
