"""Phân loại theo nguyên file cho thủ tục "Đăng ký giám hộ".

Bảng thành phần hồ sơ:
  STT1 - Mẫu hộ tịch điện tử tương tác đăng ký giám hộ: eForm tự có, không xử lý.
  STT2 - Văn bản cử người giám hộ đối với đăng ký giám hộ cử.
  STT3 - Giấy tờ chứng minh điều kiện giám hộ đương nhiên/điều kiện người giám hộ.
         Theo rule nghiệp vụ hiện tại, mọi CCCD/căn cước trong hồ sơ đưa vào STT3.
  STT4 - Văn bản ủy quyền nếu có.

Tờ khai đăng ký giám hộ bản giấy -> thêm thành phần hồ sơ mới.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold, normalize_document_name
from app.pipelines._shared.identity_merge import merge_identity_attachments
from app.pipelines.dang_ky_giam_ho.attach.dinh_kem_khong_tach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DOC_APPOINTMENT = "guardian_appointment"
_DOC_CONDITION = "guardian_condition"
_DOC_AUTHORIZATION = "authorization"
_DOC_PAPER_DECLARATION = "paper_declaration"
_DOC_MARITAL_STATUS = "marital_status_certificate"
_DOC_OTHER = "other"
_DOC_SKIP = "skip"

_ALLOWED_DOC_TYPES = {
    _DOC_APPOINTMENT,
    _DOC_CONDITION,
    _DOC_AUTHORIZATION,
    _DOC_PAPER_DECLARATION,
    _DOC_MARITAL_STATUS,
    _DOC_OTHER,
    _DOC_SKIP,
}

_APPOINTMENT_LABEL = "Văn bản thỏa thuận cử người giám hộ"
_CONDITION_LABEL = "Giấy tờ chứng minh điều kiện giám hộ"
_AUTHORIZATION_LABEL = "Văn bản ủy quyền"
_PAPER_DECLARATION_LABEL = "Tờ khai đăng ký giám hộ bản giấy"
_OTHER_LABEL = "Tài liệu đăng ký giám hộ"
_SKIP_LABEL = "Bỏ qua"

_ROW_2_COMPONENT = "- Văn bản cử người giám hộ theo quy định của Bộ luật Dân sự"
_ROW_3_COMPONENT = "- Giấy tờ chứng minh điều kiện giám hộ đương nhiên theo quy định của Bộ luật Dân sự"
_ROW_4_COMPONENT = "- Văn bản ủy quyền theo quy định của pháp luật trong trường hợp ủy quyền"

_PAGE_HEADER_RE = re.compile(
    r"(?im)^[\t \u2500-\u257f-]*(?:trang|page)\s+\d+\s*/\s*\d+"
    r"[\t \u2500-\u257f-]*$"
)
_CCCD_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")
_MARITAL_STATUS_LABEL = "Giấy xác nhận tình trạng hôn nhân"
_IDENTITY_MARKERS = (
    "can cuoc cong dan", "the can cuoc", "citizen identity card", "identity card",
    "chung minh nhan dan", "giay chung minh nhan dan", "ho chieu", "passport", "idvnm",
)


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _normalize_doc_type(value: str) -> str:
    raw = str(value or "").strip()
    if raw in _ALLOWED_DOC_TYPES:
        return raw
    text = fold(raw)
    if not text:
        return _DOC_OTHER
    if "guardian appointment" in text or "cu nguoi giam ho" in text or "thoa thuan" in text:
        return _DOC_APPOINTMENT
    if "guardian condition" in text or "dieu kien giam ho" in text or "identity" in text or "cccd" in text:
        return _DOC_CONDITION
    if "authorization" in text or "uy quyen" in text:
        return _DOC_AUTHORIZATION
    if "paper" in text or "declaration" in text or "to khai" in text:
        return _DOC_PAPER_DECLARATION
    if "marital status" in text or "xac nhan tinh trang hon nhan" in text:
        return _DOC_MARITAL_STATUS
    if "skip" in text or "irrelevant" in text or "khong lien quan" in text:
        return _DOC_SKIP
    return _DOC_OTHER


def _has_any(haystack: str, needles: tuple[str, ...]) -> bool:
    return any(needle in haystack for needle in needles)


def _first_meaningful_page(text: str) -> str:
    """Mode không tách lấy giấy tờ mở đầu làm loại chính của nguyên file vật lý."""
    value = str(text or "")
    matches = list(_PAGE_HEADER_RE.finditer(value))
    if not matches:
        return value
    for position, match in enumerate(matches):
        end = matches[position + 1].start() if position + 1 < len(matches) else len(value)
        page = value[match.end():end].strip()
        if page and fold(page) not in {"trang trang", "trang trong"}:
            return page
    return value


def _has_identity_evidence(text: str) -> bool:
    folded = fold(text)
    return any(marker in folded for marker in _IDENTITY_MARKERS)


def _rule_doc_type(text: str) -> str:
    first_page = fold(_first_meaningful_page(text))
    haystack = fold(text)
    if not haystack:
        return ""

    if "to khai dang ky giam ho" in first_page:
        return _DOC_PAPER_DECLARATION

    # Các trang sau có thể là ảnh màn hình thủ tục giám hộ chứa nhiều số CCCD. Chúng không được
    # làm mất tiêu đề rõ ràng "Giấy xác nhận tình trạng hôn nhân" ở trang mở đầu.
    if "giay xac nhan tinh trang hon nhan" in first_page:
        return _DOC_MARITAL_STATUS

    if _has_any(
        haystack,
        (
            "van ban thoa thuan cu nguoi giam ho",
            "van ban cu nguoi giam ho",
            "nguoi cu giam ho",
            "cu nguoi co ten duoi day",
            "lam nguoi giam ho cho nguoi co ten duoi day",
        ),
    ):
        return _DOC_APPOINTMENT

    if _has_any(
        haystack,
        (
            "van ban uy quyen",
            "giay uy quyen",
            "ben uy quyen",
            "ben duoc uy quyen",
        ),
    ):
        return _DOC_AUTHORIZATION

    if _has_any(
        haystack,
        (
            "ban cam doan",
            "nang luc hanh vi dan su",
            "khong bi truy cuu trach nhiem hinh su",
            "khong phai la nguoi bi toa an tuyen bo han che quyen",
            "du dieu kien giam ho",
            "co nha rieng",
        ),
    ):
        return _DOC_CONDITION

    if _has_any(
        haystack,
        (
            "giay chung nhan quyen su dung dat",
            "quyen so huu nha o",
            "quyen su dung dat",
            "so vao so cap gcn",
            "thua dat so",
        ),
    ):
        return _DOC_CONDITION

    if _has_identity_evidence(haystack):
        return _DOC_CONDITION

    if _has_any(
        haystack,
        (
            "giay khai sinh",
            "noi dang ky khai sinh",
            "nguoi duoc giam ho",
            "thong tin tra cuu co so du lieu dan cu",
            "thong tin gia dinh",
        ),
    ):
        return _DOC_CONDITION

    return ""


def _rule_document_name(doc_type: str, text: str) -> str:
    haystack = fold(text)
    if doc_type == _DOC_PAPER_DECLARATION:
        return _PAPER_DECLARATION_LABEL
    if doc_type == _DOC_APPOINTMENT:
        return _APPOINTMENT_LABEL
    if doc_type == _DOC_AUTHORIZATION:
        return _AUTHORIZATION_LABEL
    if doc_type == _DOC_MARITAL_STATUS:
        return _MARITAL_STATUS_LABEL
    if doc_type == _DOC_CONDITION:
        if "ban cam doan" in haystack:
            return "Bản cam đoan đủ điều kiện giám hộ"
        # OCR thường mất trang bìa/tiêu đề của sổ đỏ, nhưng các nhãn cấu trúc dưới đây chỉ có trên
        # giấy chứng nhận. Dùng chúng để giữ tên giấy tờ thật thay vì đổi thành tên nhóm STT 3.
        if _has_any(
            haystack,
            (
                "giay chung nhan quyen su dung dat",
                "quyen su dung dat",
                "so vao so cap gcn",
                "thua dat so",
            ),
        ):
            return "Giấy chứng nhận quyền sử dụng đất"
        if "giay khai sinh" in haystack:
            return "Giấy khai sinh người được giám hộ"
        if "co so du lieu dan cu" in haystack:
            return "Trích xuất cơ sở dữ liệu dân cư"
        if _has_identity_evidence(haystack):
            return "Căn cước công dân"
        return _CONDITION_LABEL
    return ""


def _route_for_type(doc_type: str) -> tuple[str, int | None, str]:
    if doc_type == _DOC_APPOINTMENT:
        return "existing", 2, _ROW_2_COMPONENT
    if doc_type == _DOC_CONDITION:
        return "existing", 3, _ROW_3_COMPONENT
    if doc_type == _DOC_AUTHORIZATION:
        return "existing", 4, _ROW_4_COMPONENT
    return "new", None, ""


def _label_for_type(doc_type: str) -> str:
    return {
        _DOC_APPOINTMENT: _APPOINTMENT_LABEL,
        _DOC_CONDITION: _CONDITION_LABEL,
        _DOC_AUTHORIZATION: _AUTHORIZATION_LABEL,
        _DOC_PAPER_DECLARATION: _PAPER_DECLARATION_LABEL,
        _DOC_MARITAL_STATUS: _MARITAL_STATUS_LABEL,
        _DOC_SKIP: _SKIP_LABEL,
    }.get(doc_type, _OTHER_LABEL)


def _unique_document_name(base: str, used: set[str], fallback: str) -> str:
    normalized = normalize_document_name(base, fallback)
    key = fold(normalized)
    if key and key not in used:
        used.add(key)
        return normalized
    stem = normalized[:45].strip() or fallback[:45].strip() or _OTHER_LABEL
    n = 2
    while True:
        candidate = f"{stem} {n}"[:50].strip()
        key = fold(candidate)
        if key not in used:
            used.add(key)
            return candidate
        n += 1


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    if not documents:
        return {}

    docs = [
        {
            "index": item["index"],
            "text": _truncate_text(item.get("text", "")),
        }
        for item in documents
    ]
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(docs)},
    ]
    raw = await client.chat(messages, max_tokens=900, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    parsed_docs = parsed.get("documents", []) or []

    def _coerce(item: dict) -> dict[str, str]:
        return {
            "type": _normalize_doc_type(str(item.get("docType") or item.get("type") or "")),
            "documentName": str(item.get("documentName") or item.get("title") or "").strip(),
            "subjectName": str(item.get("subjectName") or "").strip(),
        }

    out: dict[int, dict[str, str]] = {}
    valid = {doc["index"] for doc in documents}
    for item in parsed_docs:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        if idx in valid and idx not in out:
            out[idx] = _coerce(item)
    return out


def _resolve_document_name(file: dict, doc_type: str, detected: dict, used: set[str]) -> str:
    fallback = _label_for_type(doc_type)
    base = detected.get("documentName") or fallback or file.get("name") or ""
    return _unique_document_name(base, used, fallback)


def _build_item(file: dict, idx: int, doc_type: str, document_name: str) -> dict:
    target, component_index, existing_component = _route_for_type(doc_type)
    component_name = existing_component if target == "existing" else document_name
    return {
        "fileIndex": idx,
        "fileName": str(file.get("name") or f"file-{idx + 1}"),
        "documentName": document_name,
        "componentName": component_name,
        "target": target,
        "componentIndex": component_index,
        "needsAddComponent": target == "new",
        "detectedType": document_name,
    }


def _build_group_item(
    files: list[dict],
    entries: list[dict],
    document_name: str,
    component_name: str,
    component_index: int,
    used_names: set[str],
) -> dict:
    source_indexes = [entry["idx"] for entry in sorted(entries, key=lambda item: item["idx"])]
    primary = source_indexes[0]
    normalized_name = _unique_document_name(document_name, used_names, document_name)
    return {
        "fileIndex": primary,
        "sourceFileIndexes": source_indexes,
        "fileName": str(files[primary].get("name") or f"file-{primary + 1}"),
        "documentName": normalized_name,
        "componentName": component_name,
        "target": "existing",
        "componentIndex": component_index,
        "needsAddComponent": False,
        "detectedType": normalized_name,
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, dict[str, str]] | None = None,
) -> tuple[list[dict], list[dict]]:
    llm_types = llm_types or {}
    by_name = {item.get("name"): item for item in ocr_results}
    resolved: list[dict] = []
    classified: list[dict] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = str(by_name.get(file_name, {}).get("text") or "")
        rule_type = _rule_doc_type(text)
        detected = llm_types.get(idx) or {}
        llm_type = detected.get("type") or ""
        doc_type = rule_type or llm_type or _DOC_OTHER
        if doc_type not in _ALLOWED_DOC_TYPES:
            doc_type = _DOC_OTHER

        rule_name = _rule_document_name(doc_type, text) if rule_type else ""
        if (
            rule_name == "Căn cước công dân"
            and detected.get("subjectName")
            and len(set(_CCCD_RE.findall(text))) <= 1
        ):
            rule_name = f"CCCD {detected['subjectName']}"
        name_source = {"documentName": rule_name} if rule_name else detected
        resolved.append({
            "idx": idx,
            "fileName": file_name,
            "file": file,
            "docType": doc_type,
            "nameSource": name_source,
            "source": "rule" if rule_type else ("llm" if llm_type else "default"),
        })

    used_names: set[str] = set()
    attachments: list[dict] = []
    identity_indexes: set[int] = set()
    ocr_text_by_index: dict[int, str] = {}

    for entry in sorted(resolved, key=lambda item: item["idx"]):
        idx = entry["idx"]
        file = entry["file"]
        doc_type = entry["docType"]

        if doc_type == _DOC_SKIP:
            classified.append({
                "fileName": entry["fileName"],
                "docType": doc_type,
                "documentName": _MARITAL_STATUS_LABEL,
                "target": "skip",
                "componentIndex": None,
                "source": entry["source"],
            })
            continue

        document_name = _resolve_document_name(file, doc_type, entry["nameSource"], used_names)
        item = _build_item(file, idx, doc_type, document_name)
        attachments.append(item)
        text = str(by_name.get(entry["fileName"], {}).get("text") or "")
        ocr_text_by_index[idx] = text
        if doc_type == _DOC_CONDITION and _rule_document_name(doc_type, text) == "Căn cước công dân":
            identity_indexes.add(idx)
        classified.append({
            "fileName": entry["fileName"],
            "docType": doc_type,
            "documentName": document_name,
            "target": item["target"],
            "componentIndex": item["componentIndex"],
            "source": entry["source"],
        })

    attachments = merge_identity_attachments(attachments, ocr_text_by_index, identity_indexes)
    # Mỗi dòng portal chỉ có một input: nhóm/chứng cứ đầu tiên dùng dòng sẵn, các chủ thể hoặc giấy
    # điều kiện tiếp theo phải thành component mới.
    occupied_slots: set[int] = set()
    for item in attachments:
        component_index = item.get("componentIndex")
        if item.get("target") == "existing" and isinstance(component_index, int):
            if component_index in occupied_slots:
                item.update({
                    "target": "new",
                    "componentIndex": None,
                    "componentName": item["documentName"],
                    "needsAddComponent": True,
                })
            else:
                occupied_slots.add(component_index)

    return attachments, classified


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
        {
            "index": idx,
            "text": str(ocr_by_name.get(file.get("name"), {}).get("text") or ""),
        }
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

    attachments, classified = build_plan_items(raw_files, ocr_results, llm_types)
    skipped_ocr = [file["name"] for file in raw_files if file.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [file["name"] for file in raw_files],
            "ocrDocuments": [item.get("name") for item in ocr_results if item.get("text")],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "sessionId": (session or {}).get("request_id"),
            "attachmentMode": "preserve_files",
            "classified": classified,
            "skippedOcr": skipped_ocr,
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "errors": errors,
    }
