"""Đính kèm bước "Thành phần hồ sơ" cho "Cấp GCN đủ điều kiện điểm trò chơi điện tử công cộng".

Cổng Bộ VHTTDL — bảng `<table class="style_table">` 3 dòng cố định, mỗi dòng có input file trực tiếp
(trong `<app-upload-flie-multi>`). FE bơm thẳng file vào input theo slotIndex (engine fixed-slot,
`isUploadSlotInput` đã nhận input trong app-upload-flie-multi). KHÔNG có menu/ví giấy tờ.

3 slot (slotIndex = thứ tự input file trên trang):
  slot 0  "Đơn đề nghị cấp GCN đủ điều kiện (Mẫu 51a)"  ← Đơn 51a (request)
  slot 1  "Giấy tờ tùy thân của chủ điểm"                ← CCCD (identity)
  slot 2  "GCN đăng ký hộ kinh doanh"                    ← Giấy phép kinh doanh (business_registration)

LLM phân loại chính; rule dự phòng khi LLM lỗi/không chắc. Nhiều file cùng loại → gộp vào 1 slot
(FE input multiple).
"""
import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# --- Loại giấy tờ ---
_T_REQUEST = "request"
_T_IDENTITY = "identity"
_T_BUSINESS = "business_registration"
_T_OTHER = "other"

_ALLOWED_LLM_TYPES = {_T_REQUEST, _T_IDENTITY, _T_BUSINESS}
_CONFIDENT_LLM_TYPES = set(_ALLOWED_LLM_TYPES)

# --- Slot (thành phần) trên bảng — slotIndex = thứ tự input file trên trang ---
_G_REQUEST = "tro_choi_don_de_nghi"
_G_IDENTITY = "tro_choi_giay_tuy_than"
_G_BUSINESS = "tro_choi_gpkd"

_COMP_REQUEST = "Đơn đề nghị cấp giấy chứng nhận đủ điều kiện hoạt động điểm cung cấp dịch vụ trò chơi điện tử công cộng"
_COMP_IDENTITY = "Thông tin chứng minh nhân dân/căn cước/căn cước công dân của chủ điểm"
_COMP_BUSINESS = "Thông tin về giấy chứng nhận đăng ký kinh doanh/giấy chứng nhận đăng ký doanh nghiệp"

_GROUPS: dict[str, dict[str, Any]] = {
    _G_REQUEST: {"slotIndex": 0, "componentName": _COMP_REQUEST, "label": "Đơn đề nghị cấp GCN (Mẫu 51a)"},
    _G_IDENTITY: {"slotIndex": 1, "componentName": _COMP_IDENTITY, "label": "Giấy tờ tùy thân chủ điểm (CCCD)"},
    _G_BUSINESS: {"slotIndex": 2, "componentName": _COMP_BUSINESS, "label": "GCN đăng ký hộ kinh doanh"},
}

_TYPE_TO_GROUP = {
    _T_REQUEST: _G_REQUEST,
    _T_IDENTITY: _G_IDENTITY,
    _T_BUSINESS: _G_BUSINESS,
}

_LABELS = {
    _T_REQUEST: "Đơn đề nghị cấp GCN (Mẫu 51a)",
    _T_IDENTITY: "Căn cước công dân",
    _T_BUSINESS: "Giấy chứng nhận đăng ký hộ kinh doanh",
    _T_OTHER: "Giấy tờ kèm theo hồ sơ",
}


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def _has_any(haystack: str, needles: tuple[str, ...]) -> bool:
    return any(n in haystack for n in needles)


def _canonical_type(value: str) -> str:
    raw = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    return raw if raw in _ALLOWED_LLM_TYPES else _T_OTHER


def _looks_like_identity(h: str) -> bool:
    if _has_any(h, ("can cuoc cong dan", "the can cuoc", "cccd", "chung minh nhan dan", "ho chieu", "citizen identity")):
        return True
    if "so dinh danh ca nhan" not in h:
        return False
    markers = ("co gia tri den", "date of expiry", "noi thuong tru", "place of residence", "que quan")
    return sum(1 for m in markers if m in h) >= 2


def _rule_doc_type(ocr_text: str, file_name: str = "") -> str | None:
    h = _fold((ocr_text or "") + "\n" + (file_name or ""))
    if not h.strip():
        return None
    if _has_any(h, ("de nghi cap giay chung nhan du dieu kien", "tro choi dien tu cong cong", "mau so 51a", "mau so 51b")):
        return _T_REQUEST
    if _has_any(h, ("giay chung nhan dang ky ho kinh doanh", "dang ky ho kinh doanh", "dang ky kinh doanh",
                    "dang ky doanh nghiep", "ma so ho kinh doanh")):
        return _T_BUSINESS
    if _looks_like_identity(h):
        return _T_IDENTITY
    return None


def _label_for_type(doc_type: str, title: str = "") -> str:
    title = normalize_document_name(title, "") if title else ""
    if title and doc_type not in {_T_IDENTITY}:
        return title
    return _LABELS.get(doc_type, _LABELS[_T_OTHER])


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    if not documents:
        return {}
    docs = [{"index": item["index"], "text": _truncate_text(item.get("text", ""))} for item in documents]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(docs)},
    ]
    raw = await client.chat(messages, max_tokens=600, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    parsed_docs = parsed.get("documents", []) or []

    def _coerce(item: dict) -> dict[str, str]:
        return {
            "type": _canonical_type(str(item.get("type") or "")),
            "documentName": str(item.get("documentName") or "").strip(),
        }

    out: dict[int, dict[str, str]] = {}
    if len(parsed_docs) == len(documents):
        for pos, item in enumerate(parsed_docs):
            out[documents[pos]["index"]] = _coerce(item)
        return out
    raw_items: list[tuple[int, dict]] = []
    for item in parsed_docs:
        try:
            raw_items.append((int(item.get("index")), item))
        except Exception:  # noqa: BLE001
            continue
    offset = 0 if any(r == 0 for r, _ in raw_items) else 1
    valid = {d["index"] for d in documents}
    for r, item in raw_items:
        idx = r - offset
        if idx in valid:
            out[idx] = _coerce(item)
    return out


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, dict[str, str]] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    by_name = {r.get("name"): r for r in ocr_results}
    resolved: list[dict] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = str(by_name.get(file_name, {}).get("text") or "")
        detected = llm_types.get(idx) or {}
        llm_type = detected.get("type") or ""
        llm_ok = llm_type in _CONFIDENT_LLM_TYPES
        rule_type = "" if llm_ok else (_rule_doc_type(text, file_name) or "")
        doc_type = (llm_type if llm_ok else "") or rule_type or _T_OTHER
        resolved.append({
            "idx": idx, "fileName": file_name, "docType": doc_type,
            "title": detected.get("documentName", ""),
            "source": "llm" if llm_ok else ("rule" if rule_type else "default"),
        })

    groups: dict[str, list[dict]] = {g: [] for g in _GROUPS}
    unclassified: list[dict] = []
    for entry in resolved:
        gk = _TYPE_TO_GROUP.get(entry["docType"])
        if gk:
            groups[gk].append(entry)
        else:
            unclassified.append(entry)

    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for group_key, meta in _GROUPS.items():
        entries = sorted(groups[group_key], key=lambda e: e["idx"])
        if not entries:
            continue
        source_indexes = [e["idx"] for e in entries]
        head = entries[0]
        document_name = _label_for_type(head["docType"], head.get("title", "")) if len(entries) == 1 else meta["label"]
        attachments.append({
            "fileIndex": source_indexes[0],
            "sourceFileIndexes": source_indexes,   # nhiều file cùng loại → 1 slot (input multiple)
            "fileName": str(files[source_indexes[0]].get("name") or f"file-{source_indexes[0] + 1}"),
            "documentName": document_name,
            "componentName": meta["componentName"],
            "target": "fixed-slot",
            "needsAddComponent": False,
            "detectedType": document_name,
            "slotKey": group_key,
            "slotIndex": meta["slotIndex"],
            "slotName": meta["componentName"],
        })
        for e in entries:
            classified.append({
                "fileName": e["fileName"], "docType": e["docType"],
                "documentName": _label_for_type(e["docType"], e.get("title", "")),
                "group": group_key, "slotIndex": meta["slotIndex"], "source": e["source"],
            })

    for e in unclassified:
        warnings.append(f"Không phân loại được tài liệu '{e['fileName']}' vào 3 thành phần (Đơn 51a/CCCD/GPKD).")

    if not attachments:
        warnings.append("Không phân loại được tài liệu nào vào thành phần hồ sơ.")
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    from app.services import ocr

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for r in ocr_results:
        if r.get("error"):
            errors.append(f"OCR {r.get('name')}: {r['error']}")

    ocr_by_name = {r.get("name"): r for r in ocr_results}
    llm_docs = [
        {"index": idx, "text": str(ocr_by_name.get(file.get("name"), {}).get("text") or "")}
        for idx, file in enumerate(raw_files)
    ]

    t1 = time.monotonic()
    llm_types: dict[int, dict[str, str]] = {}
    if any(d["text"].strip() for d in llm_docs):
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as e:  # noqa: BLE001
            errors.append(f"attachment_agent: {e}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types)
    errors.extend(warnings)

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [f["name"] for f in raw_files],
            "sessionId": (session or {}).get("request_id"),
            "classified": classified,
            "groups": [{"slotKey": k, **v} for k, v in _GROUPS.items()],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
