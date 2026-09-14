"""Đính kèm bước "Thành phần hồ sơ" cho thủ tục "Đăng ký hành nghề" (Sở Y tế — Angular mat-table, engine
FE `attp-row`).

Bảng thành phần hồ sơ có 4 dòng cố định, cột "Loại bản" đều là "1 Bản chính":
  1. Danh sách đăng ký hành nghề                                   ← danh sách ĐĂNG KÝ LẦN ĐẦU (bắt buộc).
  2. Danh sách đăng ký hành nghề đã thay đổi theo Mẫu 01 PL II …   ← chỉ khi danh sách có THAY ĐỔI.
  3. Báo cáo                                                       ← văn bản báo cáo.
  4. Danh sách đăng ký hành nghề đã bổ sung theo Mẫu 01 PL II …    ← chỉ khi BỔ SUNG người hành nghề.

⚠ BẪY KHỚP DÒNG: FE khớp componentName theo kiểu "chứa nhau" (rowText ⊂ want HOẶC want ⊂ rowText) và lấy
dòng ĐẦU TIÊN khớp. Tên đầy đủ của dòng 2/4 CHỨA NGUYÊN tên dòng 1 → gửi tên đầy đủ là rơi vào dòng 1.
Vì vậy mỗi dòng gửi kèm componentIndex (FE xét dòng theo chỉ số TRƯỚC) và componentName là đoạn text
CHỈ dòng đó có ("đã thay đổi theo Mẫu 01", "đã bổ sung theo Mẫu 01") — không đoạn nào chứa tên dòng 1.

Cả 3 loại danh sách dùng chung biểu mẫu Mẫu 01 nên rất khó phân biệt: mặc định là danh sách LẦN ĐẦU, chỉ
xếp vào dòng 2/4 khi LLM thấy RÕ là thay đổi/bổ sung (rule dự phòng không bao giờ tự đoán sang dòng 2/4).

Phân loại **LLM-primary**: LLM đọc OCR quyết định loại; rule keyword chỉ DỰ PHÒNG. CCCD KHÔNG có dòng riêng
(chỉ dùng ở bước thông tin) → bỏ qua. Giấy tờ không xác định → KHÔNG đính bừa, chỉ cảnh báo.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.compact_agent.runner import _extract_docx_text, _is_docx
from app.pipelines.dang_ky_hanh_nghe.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_LOAI_BAN = "Bản chính"

_DS_LAN_DAU = "ds_lan_dau"
_DS_THAY_DOI = "ds_thay_doi"
_DS_BO_SUNG = "ds_bo_sung"
_BAO_CAO = "bao_cao"
_CCCD = "cccd"
_OTHER = "other"

_ROWS: dict[str, dict[str, Any]] = {
    _DS_LAN_DAU: {
        "componentIndex": 1,
        "componentName": "Danh sách đăng ký hành nghề",
        "loaiBan": _LOAI_BAN,
        "documentName": "Danh sách đăng ký hành nghề (Mẫu 01 Phụ lục II NĐ 96/2023/NĐ-CP)",
    },
    _DS_THAY_DOI: {
        "componentIndex": 2,
        "componentName": "đã thay đổi theo Mẫu 01",
        "loaiBan": _LOAI_BAN,
        "documentName": "Danh sách đăng ký hành nghề đã thay đổi (Mẫu 01 Phụ lục II NĐ 96/2023/NĐ-CP)",
    },
    _BAO_CAO: {
        "componentIndex": 3,
        "componentName": "Báo cáo",
        "loaiBan": _LOAI_BAN,
        "documentName": "Báo cáo",
    },
    _DS_BO_SUNG: {
        "componentIndex": 4,
        "componentName": "đã bổ sung theo Mẫu 01",
        "loaiBan": _LOAI_BAN,
        "documentName": "Danh sách đăng ký hành nghề đã bổ sung (Mẫu 01 Phụ lục II NĐ 96/2023/NĐ-CP)",
    },
}
_DS_TYPES = {_DS_LAN_DAU, _DS_THAY_DOI, _DS_BO_SUNG}
_SKIP_DOCS = {_CCCD}
_ALLOWED_DOC_TYPES = set(_ROWS) | _SKIP_DOCS | {_OTHER}


def _is_identity_text(h: str) -> bool:
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport"))


def _is_danh_sach(h: str) -> bool:
    return (
        "danh sach dang ky nguoi hanh nghe" in h
        or "danh sach dang ky hanh nghe" in h
        or ("danh sach" in h and "nguoi hanh nghe" in h and ("giay phep hanh nghe" in h or "pham vi hanh nghe" in h))
    )


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM).

    Danh sách nhận TRƯỚC báo cáo (danh sách có thể nhắc "báo cáo") và TRƯỚC CCCD (bảng người hành nghề có
    cột số CCCD). Rule KHÔNG đoán dòng thay đổi/bổ sung — mẫu in sẵn các chữ đó dù chưa đánh dấu.
    """
    h = _fold(text)
    if not h:
        return ""
    if _is_danh_sach(h):
        return _DS_LAN_DAU
    # Tiêu đề "BÁO CÁO" nằm ở phần đầu văn bản (sau quốc hiệu/tên cơ quan).
    if " bao cao " in f" {h[:300]} ":
        return _BAO_CAO
    if _is_identity_text(h):
        return _CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "").replace(" ", "_")
    if text in _ALLOWED_DOC_TYPES:
        return text
    if "thay_doi" in text:
        return _DS_THAY_DOI
    if "bo_sung" in text:
        return _DS_BO_SUNG
    if "bao_cao" in text:
        return _BAO_CAO
    if "danh_sach" in text or text.startswith("ds"):
        return _DS_LAN_DAU
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


def _build_row_item(file_index: int, file_name: str, doc_type: str, document_name: str) -> dict:
    row = _ROWS[doc_type]
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": row["componentName"],
        "componentIndex": row["componentIndex"],
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
        if llm_type in _ALLOWED_DOC_TYPES and llm_type != _OTHER:
            doc_type, source = llm_type, "llm"
        elif rule_type:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = _OTHER, "unknown"

        if doc_type in _SKIP_DOCS:
            classified.append({"fileName": file_name, "docType": doc_type, "source": source, "skipped": True})
            continue
        if doc_type == _OTHER:
            classified.append({"fileName": file_name, "docType": doc_type, "source": source, "skipped": True})
            warnings.append(
                f"Không xác định được file '{file_name}' thuộc dòng nào của Thành phần hồ sơ — chưa đính kèm, "
                "vui lòng đính tay nếu cần."
            )
            continue

        items.append(_build_row_item(idx, file_name, doc_type, _ROWS[doc_type]["documentName"]))
        classified.append({"fileName": file_name, "docType": doc_type, "source": source})
        if doc_type in (_DS_THAY_DOI, _DS_BO_SUNG):
            row_label = "đã thay đổi" if doc_type == _DS_THAY_DOI else "đã bổ sung"
            warnings.append(
                f"File '{file_name}' được xếp vào dòng 'Danh sách đăng ký hành nghề {row_label}' — cả ba loại "
                "danh sách dùng chung Mẫu 01, vui lòng kiểm tra lại đúng dòng."
            )

    # Một dòng nhận NHIỀU file (vd 3 danh sách của 3 cơ sở): FE chống trùng theo documentName, cùng một tên
    # chuẩn là file thứ 2 trở đi bị coi như đã đính → giữ TÊN GỐC cho từng file khi dòng có hơn 1 file.
    per_row: dict[str, int] = {}
    for item in items:
        per_row[item["detectedType"]] = per_row.get(item["detectedType"], 0) + 1
    for item in items:
        if per_row[item["detectedType"]] > 1:
            item["documentName"] = item["fileName"]

    types = {item["detectedType"] for item in items}
    if not types & _DS_TYPES:
        warnings.append(
            "Không tìm thấy Danh sách đăng ký hành nghề (Mẫu 01 Phụ lục II NĐ 96/2023/NĐ-CP) — dòng 1 là bắt buộc."
        )
    if _BAO_CAO not in types:
        warnings.append("Hồ sơ chưa có Báo cáo (dòng 3) — Sở yêu cầu thì vui lòng đính tay.")

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
    # Danh sách Mẫu 01 hay được gửi nguyên file .docx: đọc text trực tiếp, không qua OCR.
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
            "rows": [{"docType": k, **v} for k, v in _ROWS.items()],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
