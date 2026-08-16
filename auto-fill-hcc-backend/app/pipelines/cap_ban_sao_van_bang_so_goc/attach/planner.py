"""Đính kèm "Thành phần hồ sơ" cho "Cấp bản sao văn bằng, chứng chỉ từ sổ gốc" (cổng DVC Bộ GD&ĐT —
Angular Reactive Form, engine FE `attp-row`).

Bảng thành phần hồ sơ 3 dòng dùng chung rdo_File: (1) Đơn đề nghị/Phiếu BM04 — Bản chính; (2) Giấy ủy
quyền / giấy tờ chứng minh quan hệ; (3) Bản sao chứng thực + phong bì (nộp bưu điện). FE khớp dòng bằng
componentName (substring fold); engine gom nhiều file cùng componentName vào 1 ô upload (multiple).

Theo yêu cầu: Phiếu BM04 + BẢN PHOTO VĂN BẰNG + CCCD của chủ văn bằng đều đính CHUNG dòng (1) "Đơn đề
nghị"; chỉ giấy ủy quyền/chứng minh quan hệ đính dòng (2).

Phân loại **LLM-primary**: LLM đọc OCR quyết định loại; rule keyword + heuristic ảnh chỉ DỰ PHÒNG.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.compact_agent.runner import _extract_docx_text, _is_docx
from app.pipelines.cap_ban_sao_van_bang_so_goc.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON = "don_bm04"
_VANBANG = "van_bang"
_CCCD = "cccd"
_UYQUYEN = "uy_quyen"
_OTHER = "other"

# componentName = đoạn text nguyên văn ĐẶC TRƯNG của dòng thành phần hồ sơ trên trang (FE fold + substring).
_DON_COMPONENT = "Đơn đề nghị cấp bản sao văn bằng, chứng chỉ, trong đó cung cấp"
_UYQUYEN_COMPONENT = "phải xuất trình giấy ủy quyền"

_ROWS: dict[str, dict[str, str]] = {
    # Dòng (1) — cả Phiếu BM04, bản photo văn bằng, CCCD đều gom vào đây (Bản chính).
    _DON: {
        "componentName": _DON_COMPONENT,
        "loaiBan": "Bản chính",
        "documentName": "Đơn đề nghị/Phiếu yêu cầu cấp bản sao văn bằng (Mẫu BM04)",
    },
    _VANBANG: {
        "componentName": _DON_COMPONENT,
        "loaiBan": "Bản chính",
        "documentName": "Bản photo văn bằng, chứng chỉ (kèm Đơn đề nghị)",
    },
    _CCCD: {
        "componentName": _DON_COMPONENT,
        "loaiBan": "Bản chính",
        "documentName": "Căn cước công dân (kèm Đơn đề nghị)",
    },
    # Dòng (2) — ủy quyền / chứng minh quan hệ.
    _UYQUYEN: {
        "componentName": _UYQUYEN_COMPONENT,
        "loaiBan": "Bản chính",
        "documentName": "Giấy ủy quyền / giấy tờ chứng minh quan hệ",
    },
}
_ALLOWED_DOC_TYPES = set(_ROWS) | {_OTHER}


def _is_identity_text(text: str) -> bool:
    h = _fold(text)
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport"))


def _is_photo_like(text: str) -> bool:
    """File ẢNH (bản photo văn bằng scan mờ): OCR rỗng/chỉ nhãn ảnh/rác. Đếm chữ cái < 20 → coi là ảnh."""
    letters = sum(1 for c in _fold(text) if c.isalpha())
    return letters < 20


def _rule_doc_type(text: str) -> str:
    h = _fold(text)
    if not h:
        return ""
    if "phieu yeu cau cap ban sao van bang" in h or "so luong ban sao xin cap" in h:
        return _DON
    if _is_identity_text(h):
        return _CCCD
    if "bang tot nghiep" in h or "so vao so cap bang" in h or "so hieu" in h:
        return _VANBANG
    if "giay uy quyen" in h or "giay uy quyen" in h:
        return _UYQUYEN
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if text in _ALLOWED_DOC_TYPES:
        return text
    if "uy quyen" in text or "quan he" in text:
        return _UYQUYEN
    if "van bang" in text or "chung chi" in text or "tot nghiep" in text:
        return _VANBANG
    if "cccd" in text or "can cuoc" in text or "cmnd" in text or "ho chieu" in text:
        return _CCCD
    if "don" in text or "bm04" in text or "phieu" in text:
        return _DON
    return _OTHER


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

        # DỰ PHÒNG: file ẢNH (OCR rỗng/rác) — thường là bản photo văn bằng scan → dòng "Đơn đề nghị".
        # KHÔNG áp dụng cho docx (đơn Word luôn có chữ).
        if not _is_docx(file) and _is_photo_like(text):
            items.append(_build_row_item(file, idx, _VANBANG))
            classified.append({"fileName": file_name, "docType": _VANBANG, "source": "photo-fallback"})
            continue

        # Mặc định an toàn: dòng "Đơn đề nghị" nhận nhiều file → gom cả file chưa rõ vào đây (trừ ủy quyền
        # đã tách ở trên). Vẫn cảnh báo để người dùng kiểm tra.
        items.append(_build_row_item(file, idx, _DON))
        classified.append({"fileName": file_name, "docType": _DON, "source": f"{source}-default"})
        warnings.append(f"Không phân loại chắc chắn '{file_name}' — tạm đính dòng 'Đơn đề nghị', vui lòng kiểm tra.")

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
    # docx (đơn Word): trích text trực tiếp để phân loại đúng theo nội dung.
    ocr_results.extend(_extract_docx_text(f) for f in raw_files if _is_docx(f))
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
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES and not _is_docx(f)]

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
