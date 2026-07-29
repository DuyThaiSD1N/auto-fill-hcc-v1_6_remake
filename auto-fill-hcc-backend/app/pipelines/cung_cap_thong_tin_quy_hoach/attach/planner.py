"""Đính kèm bước "Thành phần hồ sơ" cho "Cung cấp thông tin quy hoạch đô thị và nông thôn".

Cổng Bộ Xây dựng (Form.io/Angular apply-online) — CÙNG nền tảng đính kèm với các thủ tục Lâm Đồng:
gộp NHIỀU file → 1 PDF (FE `applyMergeGroups` theo `sourceFileIndexes`), bơm file gộp vào TRIGGER
'Chọn tệp tin' theo slotIndex (FE fallback vị trí, không cần sửa extension).

Thủ tục này chỉ có 1 thành phần hồ sơ:
  slot 0  "Văn bản đề nghị cung cấp thông tin về quy hoạch đô thị và nông thôn"
          ← Đơn đề nghị + Giấy chứng nhận QSDĐ + CCCD (+ Giấy ủy quyền nếu nộp thay).
Tất cả file gộp thành 1 PDF, sắp thứ tự: Đơn đề nghị → GCN → ủy quyền → CCCD.

LLM phân loại chính (đặt documentName + xếp thứ tự); rule chỉ dự phòng khi LLM lỗi/không chắc.
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
_T_REQUEST = "request"                # Đơn/Văn bản đề nghị cung cấp thông tin quy hoạch
_T_LAND_CERT = "land_certificate"     # Giấy chứng nhận QSDĐ (sổ đỏ)
_T_IDENTITY = "identity"              # CCCD
_T_AUTHORIZATION = "authorization"    # Giấy ủy quyền
_T_OTHER = "other"

_ALLOWED_LLM_TYPES = {_T_REQUEST, _T_LAND_CERT, _T_IDENTITY, _T_AUTHORIZATION}
_CONFIDENT_LLM_TYPES = set(_ALLOWED_LLM_TYPES)

# --- Thành phần (component) trên form — DUY NHẤT 1 ô ---
_COMP_MAIN = "Văn bản đề nghị cung cấp thông tin về quy hoạch đô thị và nông thôn"
_SLOT_INDEX = 0
_SLOT_KEY = "g_request"

# thứ tự ưu tiên khi gộp (số nhỏ lên trước): Đơn đề nghị → GCN → ủy quyền → CCCD → khác.
_TYPE_PRIORITY = {
    _T_REQUEST: 10, _T_LAND_CERT: 20, _T_AUTHORIZATION: 25, _T_IDENTITY: 30, _T_OTHER: 90,
}

_LABELS = {
    _T_REQUEST: "Đơn đề nghị cung cấp thông tin quy hoạch",
    _T_LAND_CERT: "Giấy chứng nhận quyền sử dụng đất",
    _T_IDENTITY: "Căn cước công dân",
    _T_AUTHORIZATION: "Giấy ủy quyền",
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
    markers = ("co gia tri den", "date of expiry", "noi thuong tru", "place of residence", "que quan", "dac diem nhan dang")
    return sum(1 for m in markers if m in h) >= 2


def _rule_doc_type(ocr_text: str, file_name: str = "") -> str | None:
    """Route TẤT ĐỊNH theo nội dung OCR (+ tên file). None = không rõ."""
    h = _fold((ocr_text or "") + "\n" + (file_name or ""))
    if not h.strip():
        return None
    if _has_any(h, ("giay uy quyen", "van ban uy quyen", "hop dong uy quyen", "ben duoc uy quyen", "nguoi duoc uy quyen")):
        return _T_AUTHORIZATION
    if _has_any(h, ("de nghi cung cap thong tin", "cung cap thong tin quy hoach", "thong tin ve quy hoach",
                    "don de nghi cung cap", "chung chi quy hoach")):
        return _T_REQUEST
    # Giấy chứng nhận QSDĐ — tiêu đề "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT".
    if _has_any(h, ("giay chung nhan quyen su dung dat", "quyen so huu tai san gan lien voi dat",
                    "giay chung nhan quyen su dung")):
        return _T_LAND_CERT
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
        # LLM PHÂN LOẠI CHÍNH; rule chỉ dự phòng khi LLM "other"/không chắc hoặc lỗi.
        rule_type = "" if llm_ok else (_rule_doc_type(text, file_name) or "")
        doc_type = (llm_type if llm_ok else "") or rule_type or _T_OTHER
        resolved.append({
            "idx": idx, "fileName": file_name, "docType": doc_type,
            "title": detected.get("documentName", ""),
            "source": "llm" if llm_ok else ("rule" if rule_type else "default"),
        })

    # 1 nhóm duy nhất — gộp mọi file theo thứ tự ưu tiên loại.
    entries = sorted(resolved, key=lambda e: (_TYPE_PRIORITY.get(e["docType"], 99), e["idx"]))
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    if entries:
        source_indexes = [e["idx"] for e in entries]
        head = entries[0]
        document_name = (
            _label_for_type(head["docType"], head.get("title", "")) if len(entries) == 1
            else "Văn bản đề nghị cung cấp thông tin quy hoạch (kèm giấy tờ liên quan)"
        )
        attachments.append({
            "fileIndex": source_indexes[0],
            "sourceFileIndexes": source_indexes,   # FE gộp các file này thành 1 PDF theo thứ tự
            "fileName": str(files[source_indexes[0]].get("name") or f"file-{source_indexes[0] + 1}"),
            "documentName": document_name,
            "componentName": _COMP_MAIN,
            "target": "fixed-slot",
            "needsAddComponent": False,
            "detectedType": document_name,
            "slotKey": _SLOT_KEY,
            "slotIndex": _SLOT_INDEX,
            "slotName": _COMP_MAIN,
        })
        for e in entries:
            classified.append({
                "fileName": e["fileName"], "docType": e["docType"],
                "documentName": _label_for_type(e["docType"], e.get("title", "")),
                "group": _SLOT_KEY, "slotIndex": _SLOT_INDEX, "source": e["source"],
            })
    else:
        warnings.append("Không có tài liệu nào để đính kèm vào thành phần hồ sơ.")

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
            "groups": [{"slotKey": _SLOT_KEY, "slotIndex": _SLOT_INDEX, "componentName": _COMP_MAIN}],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
