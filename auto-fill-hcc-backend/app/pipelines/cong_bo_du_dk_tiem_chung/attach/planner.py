"""Đính kèm bước "Thành phần hồ sơ" cho "Công bố cơ sở đủ điều kiện tiêm chủng" (Sở Y tế — Angular
mat-table, engine FE `attp-row`).

Bảng thành phần hồ sơ có đúng 1 dòng, "1 Bản chính":
  1. Văn bản thông báo đủ điều kiện tiêm chủng theo mẫu quy định tại Phụ lục ban hành kèm theo Nghị định số
     104/2016/NĐ-CP ngày 01/7/2016.

Tờ Thông báo là giấy tờ chính. Tờ trình và Danh sách cơ sở đi kèm (hay scan chung một PDF với Thông báo)
cũng thuộc bộ văn bản thông báo → đính vào CÙNG dòng. CCCD chỉ dùng ở bước thông tin → bỏ qua. Giấy tờ
không xác định → KHÔNG đính bừa, chỉ cảnh báo.

Phân loại **LLM-primary**: LLM đọc OCR quyết định loại; rule keyword chỉ DỰ PHÒNG.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.compact_agent.runner import _extract_docx_text, _is_docx
from app.pipelines.cong_bo_du_dk_tiem_chung.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_THONG_BAO = "thong_bao"
_TO_TRINH = "to_trinh"
_DANH_SACH = "danh_sach"
_CCCD = "cccd"
_OTHER = "other"

_ROW: dict[str, Any] = {
    "componentIndex": 1,
    "componentName": "Văn bản thông báo đủ điều kiện tiêm chủng",
    "loaiBan": "Bản chính",
}
_DOCUMENT_NAMES = {
    _THONG_BAO: "Thông báo cơ sở đủ điều kiện tiêm chủng",
    _TO_TRINH: "Tờ trình về việc công bố cơ sở đủ điều kiện tiêm chủng",
    _DANH_SACH: "Danh sách cơ sở đủ điều kiện tiêm chủng",
}
_ATTACH_TYPES = set(_DOCUMENT_NAMES)
_SKIP_DOCS = {_CCCD}
_ALLOWED_DOC_TYPES = _ATTACH_TYPES | _SKIP_DOCS | {_OTHER}


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM).

    Thông báo nhận TRƯỚC: PDF gộp tờ trình + danh sách + thông báo vẫn phải ra thong_bao.
    """
    h = _fold(text)
    if not h:
        return ""
    if "ten co so thong bao" in h or ("thong bao" in h and "nguoi dung dau co so" in h):
        return _THONG_BAO
    if "to trinh" in h and "tiem chung" in h:
        return _TO_TRINH
    if "danh sach co so du dieu kien tiem chung" in h:
        return _DANH_SACH
    if any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport")):
        return _CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "").replace(" ", "_")
    if text in _ALLOWED_DOC_TYPES:
        return text
    if "thong_bao" in text:
        return _THONG_BAO
    if "to_trinh" in text:
        return _TO_TRINH
    if "danh_sach" in text:
        return _DANH_SACH
    if any(k in text for k in ("cccd", "can_cuoc", "cmnd", "ho_chieu")):
        return _CCCD
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
        if llm_type in _ALLOWED_DOC_TYPES and llm_type != _OTHER:
            doc_type, source = llm_type, "llm"
        elif rule_type:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = _OTHER, "unknown"

        if doc_type not in _ATTACH_TYPES:
            classified.append({"fileName": file_name, "docType": doc_type, "source": source, "skipped": True})
            if doc_type == _OTHER:
                warnings.append(
                    f"Không xác định được file '{file_name}' thuộc Thành phần hồ sơ — chưa đính kèm, vui lòng "
                    "đính tay nếu cần."
                )
            continue

        items.append({
            "fileIndex": idx,
            "fileName": file_name,
            "documentName": _DOCUMENT_NAMES[doc_type],
            "componentName": _ROW["componentName"],
            "componentIndex": _ROW["componentIndex"],
            "loaiBan": _ROW["loaiBan"],
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": doc_type,
        })
        classified.append({"fileName": file_name, "docType": doc_type, "source": source})

    # Dòng duy nhất nhận NHIỀU file: FE chống trùng theo documentName, trùng tên chuẩn là file sau bị coi như
    # đã đính → khi có hơn 1 file thì giữ TÊN GỐC cho từng file.
    if len(items) > 1:
        for item in items:
            item["documentName"] = item["fileName"]

    if not any(item["detectedType"] == _THONG_BAO for item in items):
        warnings.append(
            "Không tìm thấy tờ Thông báo cơ sở đủ điều kiện tiêm chủng (theo mẫu NĐ 104/2016/NĐ-CP) — thành phần "
            "hồ sơ bắt buộc, vui lòng đính tay."
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
            llm_docs.append({"index": idx, "text": text[:6000]})

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
            "rows": [{"docType": _THONG_BAO, **_ROW}],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
