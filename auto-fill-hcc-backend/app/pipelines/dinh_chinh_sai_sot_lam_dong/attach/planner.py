"""Đính kèm bước "Thành phần hồ sơ" cho [Lâm Đồng] đính chính GCN có sai sót.

Cổng Lâm Đồng (Form.io/Angular apply-online) — CÙNG nền tảng đính kèm với GPXD lamdong:
bảng thành phần hồ sơ có các dòng cố định, FE bơm file theo VỊ TRÍ (slotIndex) qua fallback
(FIXED_SLOT_KEYWORDS không có entry cho thủ tục này nên không cần sửa extension).

4 dòng trên form (thứ tự cố định):
  [0] "Giấy tờ chứng minh sai sót…"          ← Giấy chứng nhận (ảnh phần sai) + Giấy khai sinh.
  [1] "Văn bản về việc ủy quyền…"            ← Giấy ủy quyền (chỉ khi nộp qua người đại diện).
  [2] "Đơn đăng ký biến động… Mẫu số 18"     ← Đơn Mẫu 18 + CCCD.
  [3] "- Bản gốc Giấy chứng nhận đã cấp."    ← nộp trực tiếp một cửa, KHÔNG scan đính kèm.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold, normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.dinh_chinh_sai_sot_lam_dong.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DOC_LAND = "land_certificate"
_DOC_BIRTH = "birth_certificate"
_DOC_APPLICATION = "change_application"
_DOC_IDENTITY = "identity_document"
_DOC_AUTHORIZATION = "authorization"
_DOC_OTHER = "other"
_DOC_SKIP = "skip"

_ALLOWED_DOC_TYPES = {
    _DOC_LAND, _DOC_BIRTH, _DOC_APPLICATION, _DOC_IDENTITY,
    _DOC_AUTHORIZATION, _DOC_OTHER, _DOC_SKIP,
}

_PROOF_TYPES = {_DOC_LAND, _DOC_BIRTH}
_AUTH_TYPES = {_DOC_AUTHORIZATION}
_APPLICATION_TYPES = {_DOC_APPLICATION, _DOC_IDENTITY}

_ROW_PROOF = (
    "Giấy tờ chứng minh sai sót thông tin của người được cấp Giấy chứng nhận so với thông tin tại thời "
    "điểm đề nghị đính chính hoặc sai sót thông tin về thửa đất, tài sản gắn liền với đất so với thông "
    "tin trên Giấy chứng nhận đã cấp."
)
_ROW_AUTH = (
    "Văn bản về việc ủy quyền theo quy định của pháp luật về dân sự đối với trường hợp thực hiện thủ tục "
    "thông qua người đại diện."
)
_ROW_APPLICATION = "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18"

_SLOT_PROOF = "dinhchinh_ld_proof"
_SLOT_AUTH = "dinhchinh_ld_authorization"
_SLOT_APPLICATION = "dinhchinh_ld_application"

SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": _SLOT_PROOF,
        "slotIndex": 0,
        "componentIndex": 1,
        "slotName": _ROW_PROOF,
        "documentName": "Giấy tờ chứng minh sai sót",
        "detectedType": "Giấy tờ chứng minh sai sót",
    },
    {
        "slotKey": _SLOT_AUTH,
        "slotIndex": 1,
        "componentIndex": 2,
        "slotName": _ROW_AUTH,
        "documentName": "Văn bản ủy quyền",
        "detectedType": "Văn bản ủy quyền",
    },
    {
        "slotKey": _SLOT_APPLICATION,
        "slotIndex": 2,
        "componentIndex": 3,
        "slotName": _ROW_APPLICATION,
        "documentName": "Đơn đăng ký biến động Mẫu số 18",
        "detectedType": "Đơn đăng ký biến động Mẫu số 18",
    },
]
_SLOT_BY_KEY = {item["slotKey"]: item for item in SLOTS}

_LABELS = {
    _DOC_LAND: "Giấy chứng nhận quyền sử dụng đất",
    _DOC_BIRTH: "Giấy khai sinh",
    _DOC_APPLICATION: "Đơn đăng ký biến động đất đai (Mẫu số 18)",
    _DOC_IDENTITY: "Căn cước công dân",
    _DOC_AUTHORIZATION: "Văn bản ủy quyền",
    _DOC_OTHER: "Tài liệu đính chính Giấy chứng nhận",
    _DOC_SKIP: "Bỏ qua",
}

# Trong 1 dòng: GCN trước khai sinh; Đơn trước CCCD.
_GROUP_PRIORITY = {
    _DOC_LAND: 10,
    _DOC_BIRTH: 20,
    _DOC_APPLICATION: 10,
    _DOC_IDENTITY: 20,
    _DOC_AUTHORIZATION: 10,
}


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def _has_any(haystack: str, needles: tuple[str, ...]) -> bool:
    return any(needle in haystack for needle in needles)


def _normalize_doc_type(value: str) -> str:
    raw = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    if raw in _ALLOWED_DOC_TYPES:
        return raw
    text = fold(raw)
    if not text or text == "other":
        return _DOC_OTHER
    if _has_any(text, ("change_application", "don dang ky bien dong", "mau so 18", "bien dong")):
        return _DOC_APPLICATION
    if _has_any(text, ("land", "giay chung nhan", "so do", "qsd", "quyen su dung dat")):
        return _DOC_LAND
    if _has_any(text, ("birth", "khai sinh")):
        return _DOC_BIRTH
    if _has_any(text, ("identity", "cccd", "can cuoc", "cmnd", "ho chieu")):
        return _DOC_IDENTITY
    if _has_any(text, ("authorization", "uy quyen")):
        return _DOC_AUTHORIZATION
    if _has_any(text, ("skip", "khong ap dung")):
        return _DOC_SKIP
    return _DOC_OTHER


def _rule_doc_type(text: str, file_name: str = "") -> str:
    haystack = fold((text or "") + "\n" + (file_name or ""))
    if not haystack:
        return ""
    # Ủy quyền kiểm tra sớm (tránh dính CCCD của bên được ủy quyền in kèm).
    if _has_any(haystack, ("giay uy quyen", "van ban uy quyen", "hop dong uy quyen", "ben duoc uy quyen", "ben uy quyen")):
        return _DOC_AUTHORIZATION
    # Đơn Mẫu 18 trước GCN (đơn cũng nhắc "biến động đất đai").
    if _has_any(haystack, ("don dang ky bien dong dat dai", "dang ky bien dong dat dai", "mau so 18", "theo mau so 18")):
        return _DOC_APPLICATION
    # Giấy khai sinh trước CCCD.
    if _has_any(haystack, ("giay khai sinh", "ban sao giay khai sinh", "trich luc khai sinh", "birth certificate")):
        return _DOC_BIRTH
    if _has_any(
        haystack,
        (
            "giay chung nhan quyen su dung dat", "quyen so huu nha o", "quyen so huu tai san",
            "so vao so cap gcn", "thua dat so", "to ban do so", "nguoi su dung dat",
        ),
    ):
        return _DOC_LAND
    if _has_any(
        haystack,
        (
            "can cuoc cong dan", "the can cuoc", "citizen identity card", "identity card",
            "so dinh danh ca nhan", "idvnm", "chung minh nhan dan", "cmnd", "ho chieu",
        ),
    ):
        return _DOC_IDENTITY
    return ""


def _label_for_type(doc_type: str, title: str = "") -> str:
    title = normalize_document_name(title, "") if title else ""
    if title and doc_type not in {_DOC_IDENTITY, _DOC_LAND, _DOC_BIRTH}:
        return title
    return _LABELS.get(doc_type, _LABELS[_DOC_OTHER])


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    if not documents:
        return {}
    docs = [{"index": item["index"], "text": _truncate_text(item.get("text", ""))} for item in documents]
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(docs)},
    ]
    raw = await client.chat(messages, max_tokens=700, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    parsed_docs = parsed.get("documents", []) or []

    def _coerce(item: dict) -> dict[str, str]:
        return {
            "type": _normalize_doc_type(str(item.get("type") or item.get("docType") or "")),
            "title": str(item.get("title") or item.get("documentName") or "").strip(),
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
    offset = 0 if any(idx == 0 for idx, _ in raw_items) else 1
    valid = {doc["index"] for doc in documents}
    for raw_idx, item in raw_items:
        idx = raw_idx - offset
        if idx in valid:
            out[idx] = _coerce(item)
    return out


def _ordered_entries(entries: list[dict]) -> list[dict]:
    return sorted(entries, key=lambda item: (_GROUP_PRIORITY.get(item["docType"], 99), item["idx"]))


def _slot_key_for_type(doc_type: str) -> str:
    if doc_type in _PROOF_TYPES:
        return _SLOT_PROOF
    if doc_type in _AUTH_TYPES:
        return _SLOT_AUTH
    if doc_type in _APPLICATION_TYPES:
        return _SLOT_APPLICATION
    return ""


def _build_fixed_item(files: list[dict], entry: dict) -> dict:
    slot = _SLOT_BY_KEY[_slot_key_for_type(entry["docType"])]
    idx = entry["idx"]
    document_name = _label_for_type(entry["docType"], entry.get("title", ""))
    return {
        "fileIndex": idx,
        "fileName": str(files[idx].get("name") or f"file-{idx + 1}"),
        "documentName": document_name,
        "componentName": slot["slotName"],
        "target": "fixed-slot",
        "componentIndex": slot["componentIndex"],
        "needsAddComponent": False,
        "detectedType": document_name,
        "slotKey": slot["slotKey"],
        "slotIndex": slot["slotIndex"],
        "slotName": slot["slotName"],
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, dict[str, str]] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    by_name = {item.get("name"): item for item in ocr_results}
    resolved: list[dict] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = str(by_name.get(file_name, {}).get("text") or "")
        rule_type = _rule_doc_type(text, file_name)
        detected = llm_types.get(idx) or {}
        llm_type = detected.get("type") or ""
        doc_type = rule_type or llm_type or _DOC_OTHER
        if doc_type not in _ALLOWED_DOC_TYPES:
            doc_type = _DOC_OTHER
        title = "" if rule_type and llm_type and rule_type != llm_type else detected.get("title", "")
        resolved.append({
            "idx": idx,
            "fileName": file_name,
            "docType": doc_type,
            "title": title,
            "source": "rule" if rule_type else ("llm" if llm_type else "default"),
        })

    proof_entries = [e for e in resolved if e["docType"] in _PROOF_TYPES]
    auth_entries = [e for e in resolved if e["docType"] in _AUTH_TYPES]
    application_entries = [e for e in resolved if e["docType"] in _APPLICATION_TYPES]
    skipped_entries = [
        e for e in resolved
        if e["docType"] not in _PROOF_TYPES | _AUTH_TYPES | _APPLICATION_TYPES
    ]

    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for entries, slot_key in (
        (proof_entries, _SLOT_PROOF),
        (auth_entries, _SLOT_AUTH),
        (application_entries, _SLOT_APPLICATION),
    ):
        slot = _SLOT_BY_KEY[slot_key]
        for entry in _ordered_entries(entries):
            item = _build_fixed_item(files, entry)
            attachments.append(item)
            classified.append({
                "fileName": entry["fileName"],
                "docType": entry["docType"],
                "documentName": item["documentName"],
                "target": "fixed-slot",
                "componentIndex": slot["componentIndex"],
                "slotKey": slot["slotKey"],
                "slotIndex": slot["slotIndex"],
                "source": entry["source"],
            })

    for entry in skipped_entries:
        warnings.append(
            f"Không xác định được dòng thành phần hồ sơ cho file '{entry['fileName']}' — đã bỏ qua."
        )
        classified.append({
            "fileName": entry["fileName"],
            "docType": entry["docType"],
            "documentName": _label_for_type(entry["docType"], entry.get("title", "")),
            "target": "skip",
            "componentIndex": None,
            "source": entry["source"],
        })

    return attachments, warnings, classified


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [file for file in raw_files if file.get("type") in _OCR_TYPES]

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    ocr_by_name = {item.get("name"): item for item in ocr_results}
    llm_docs = [
        {"index": idx, "text": str(ocr_by_name.get(file.get("name"), {}).get("text") or "")}
        for idx, file in enumerate(raw_files)
    ]

    t1 = time.monotonic()
    llm_types: dict[int, dict[str, str]] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types)
    errors.extend(warnings)
    skipped_ocr = [file["name"] for file in raw_files if file.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [file["name"] for file in raw_files],
            "ocrDocuments": [item.get("name") for item in ocr_results if item.get("text")],
            "llmDocuments": [file["name"] for file in raw_files],
            "sessionId": (session or {}).get("request_id"),
            "classified": classified,
            "skippedOcr": skipped_ocr,
            "slots": SLOTS,
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "ocr_text": join_ocr_documents(ocr_results),
        "llm_output": {str(idx): val for idx, val in llm_types.items()},
        "errors": errors,
    }
