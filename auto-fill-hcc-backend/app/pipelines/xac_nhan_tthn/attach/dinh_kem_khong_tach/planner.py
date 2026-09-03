"""Phân loại theo nguyên file cho thủ tục xác nhận tình trạng hôn nhân.

Nhánh này không sinh ``sourceSegments``. Ngoại lệ duy nhất là các file rời chứa hai mặt giấy tờ
tùy thân cùng người được gộp bằng ``sourceFileIndexes`` dựa trên số định danh/MRZ.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines._shared.identity_merge import merge_identity_attachments
from app.pipelines.xac_nhan_tthn.attach.dinh_kem_khong_tach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_ALLOWED_TYPES = {
    "identity",
    "divorce_or_death_proof",
    "foreign_divorce_note",
    "previous_marital_status_certificate",
    "authorization",
    "paper_declaration",
    "other",
}

_IDENTITY_LABEL = "Giấy tờ tùy thân"
_PAPER_DECLARATION_LABEL = "Tờ khai bản giấy"
_OTHER_LABEL = "Tài liệu xác nhận tình trạng hôn nhân"
_DECLARATION_BUNDLE_LABEL = "Hồ sơ xác nhận tình trạng hôn nhân"
_CCCD_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")
_TRAILING_CONNECTOR_RE = re.compile(r"\s+(?:và|hoặc|của|với)$", re.IGNORECASE)
_PAGE_HEADER_RE = re.compile(
    r"(?im)^[\t \u2500-\u257f-]*(?:trang|page)\s+\d+\s*/\s*\d+"
    r"[\t \u2500-\u257f-]*$"
)
_DECLARATION_MARKER = "to khai cap giay xac nhan tinh trang hon nhan"
_RELATED_DOCUMENT_MARKERS = (
    "can cuoc cong dan",
    "citizen identity",
    "identity card",
    "idvnm",
    "giay chung nhan ket hon",
    "ket qua kiem tra thong tin cong dan",
    "quyet dinh ly hon",
    "ban an ly hon",
    "trich luc khai tu",
    "giay bao tu",
    "trich luc ghi chu ly hon",
    "van ban uy quyen",
    "giay uy quyen",
)

_IDENTITY_DIRECT_MARKERS = (
    "can cuoc cong dan", "citizen identity", "identity card", "chung minh nhan dan",
    "giay chung minh nhan dan", "passport", "ho chieu", "idvnm",
)
_IDENTITY_BACK_SIGNAL_GROUPS = (
    ("dac diem nhan dang", "personal identification"),
    ("van tay", "ngon tro", "left index finger", "right index finger"),
    ("cuc truong cuc canh sat", "director general", "quan ly hanh chinh ve trat tu xa hoi"),
)


def _has_identity_evidence(text: str) -> bool:
    """Một cụm OCR chung không đủ biến trang nhiễu thành giấy tờ tùy thân."""
    folded = _fold(text)
    if any(marker in folded for marker in _IDENTITY_DIRECT_MARKERS):
        return True
    signal_count = sum(
        1 for group in _IDENTITY_BACK_SIGNAL_GROUPS if any(marker in folded for marker in group)
    )
    if _CCCD_RE.search(str(text or "")):
        signal_count += 1
    return signal_count >= 2

_ROW_BY_TYPE = {
    "divorce_or_death_proof": (
        2,
        "Trường hợp người yêu cầu cấp Giấy xác nhận tình trạng hôn nhân đã có vợ hoặc chồng "
        "nhưng đã ly hôn hoặc người vợ/chồng đã chết",
    ),
    "foreign_divorce_note": (3, "Công dân Việt Nam đã ly hôn, hủy việc kết hôn ở nước ngoài"),
    "previous_marital_status_certificate": (
        4,
        "Trường hợp cá nhân yêu cầu cấp lại Giấy xác nhận tình trạng hôn nhân",
    ),
    "authorization": (
        5,
        "Văn bản ủy quyền theo quy định của pháp luật trong trường hợp ủy quyền thực hiện "
        "việc cấp Giấy xác nhận tình trạng hôn nhân",
    ),
}


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _canonical_type(value: Any) -> str:
    raw = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    aliases = {
        "id": "identity",
        "cccd": "identity",
        "cmnd": "identity",
        "passport": "identity",
        "divorce_proof": "divorce_or_death_proof",
        "death_proof": "divorce_or_death_proof",
        "divorce_note": "foreign_divorce_note",
        "previous_certificate": "previous_marital_status_certificate",
        "declaration": "paper_declaration",
    }
    raw = aliases.get(raw, raw)
    return raw if raw in _ALLOWED_TYPES else "other"


def _rule_doc_type(text: str) -> str:
    """Fallback thận trọng khi LLM lỗi; chỉ route hàng có dấu hiệu nghiệp vụ đủ mạnh."""
    folded = _fold(text)
    # Giấy tờ được kể trong Tờ khai chỉ là tham chiếu. Bộ hồ sơ thực sự có tài liệu độc lập
    # được `_is_declaration_bundle` xử lý riêng theo đầu trang/đầu dòng.
    if _DECLARATION_MARKER in folded:
        return "paper_declaration"
    special: set[str] = set()
    if any(marker in folded for marker in (
        "trich luc ghi chu ly hon", "ghi chu huy viec ket hon o nuoc ngoai",
    )):
        special.add("foreign_divorce_note")
    if any(marker in folded for marker in (
        "quyet dinh ly hon", "ban an ly hon", "quyet dinh cong nhan thuan tinh ly hon",
        "trich luc khai tu", "giay bao tu", "giay chung tu",
    )):
        special.add("divorce_or_death_proof")
    if "van ban uy quyen" in folded or "giay uy quyen" in folded:
        special.add("authorization")
    if "giay xac nhan tinh trang hon nhan" in folded and "to khai" not in folded:
        special.add("previous_marital_status_certificate")
    if len(special) == 1:
        return next(iter(special))
    if len(special) > 1:
        return "other"
    return "identity" if _has_identity_evidence(text) else "other"


def _fallback_document_name(text: str) -> str:
    folded = _fold(text)
    titles = []
    for marker, title in (
        ("trich luc ghi chu ly hon", "Trích lục ghi chú ly hôn"),
        ("quyet dinh ly hon", "Quyết định ly hôn"),
        ("ban an ly hon", "Bản án ly hôn"),
        ("trich luc khai tu", "Trích lục khai tử"),
        ("giay bao tu", "Giấy báo tử"),
        ("giay xac nhan tinh trang hon nhan", "Giấy xác nhận tình trạng hôn nhân"),
        ("van ban uy quyen", "Văn bản ủy quyền"),
        ("giay uy quyen", "Giấy ủy quyền"),
        ("to khai cap giay xac nhan tinh trang hon nhan", "Tờ khai bản giấy"),
    ):
        if marker in folded and title not in titles:
            titles.append(title)
    return " và ".join(titles[:3])


def _is_declaration_bundle(text: str) -> bool:
    """Nhận bộ hồ sơ theo đầu mỗi trang, tránh nhầm phần chú thích của chính Tờ khai là file khác."""
    value = str(text or "")
    matches = list(_PAGE_HEADER_RE.finditer(value))
    if matches:
        page_starts = []
        for position, match in enumerate(matches):
            end = matches[position + 1].start() if position + 1 < len(matches) else len(value)
            page_starts.append(_fold(value[match.end():end][:600]))
    else:
        # OCR đôi khi mất header Trang n/m. Chỉ coi là tài liệu độc lập nếu tiêu đề mạnh nằm
        # ở đầu một dòng riêng; câu trong nội dung như "kèm Quyết định ly hôn" không được tính.
        lines = [_fold(line) for line in value.splitlines() if str(line).strip()]
        has_declaration_title = any(line.startswith(_DECLARATION_MARKER) for line in lines)
        has_related_title = any(
            any(line.startswith(marker) for marker in _RELATED_DOCUMENT_MARKERS)
            for line in lines
            if not line.startswith(_DECLARATION_MARKER)
        )
        return has_declaration_title and has_related_title

    if not any(_DECLARATION_MARKER in page for page in page_starts):
        return False
    return any(
        _DECLARATION_MARKER not in page
        and not page.startswith("chu thich")
        and any(marker in page for marker in _RELATED_DOCUMENT_MARKERS)
        for page in page_starts
    )


def _clean_subject_name(value: Any) -> str:
    subject = re.sub(r"\s+", " ", str(value or "")).strip(" :-")
    if _fold(subject) in {"", "ho ten", "ho va ten", "full name", "khong ro"}:
        return ""
    return subject[:40].strip()


def _identity_document_name(text: str, subject_name: str = "") -> str:
    folded = _fold(text)
    has_passport = "passport" in folded or "ho chieu" in folded
    has_cccd = "can cuoc" in folded or "citizen identity" in folded or "idvnm" in folded
    has_cmnd = "chung minh nhan dan" in folded or "cmnd" in folded
    if has_cccd and not has_passport and not has_cmnd:
        subject = _clean_subject_name(subject_name)
        if subject and len(set(_CCCD_RE.findall(str(text or "")))) <= 1:
            return normalize_document_name(f"CCCD {subject}", "Căn cước công dân")
        return "Căn cước công dân"
    if has_passport and not has_cccd and not has_cmnd:
        return "Hộ chiếu"
    if has_cmnd and not has_cccd and not has_passport:
        return "Chứng minh nhân dân"
    return _IDENTITY_LABEL


def _unique_document_name(base: str, used: set[str], fallback: str) -> str:
    normalized = normalize_document_name(base, fallback)
    # Helper dùng chung giới hạn 50 ký tự bằng phép cắt cứng. Riêng tên do LLM sinh, lùi về ranh
    # giới từ và bỏ liên từ treo để tên component luôn là một cụm hoàn chỉnh.
    if len(str(base or "").strip()) > 50 and len(normalized) == 50 and " " in normalized:
        normalized = normalized.rsplit(" ", 1)[0].strip()
        normalized = _TRAILING_CONNECTOR_RE.sub("", normalized).strip() or fallback
    key = _fold(normalized)
    if key and key not in used:
        used.add(key)
        return normalized
    stem = normalized[:45].strip() or fallback[:45].strip() or _OTHER_LABEL
    suffix = 2
    while True:
        candidate = f"{stem} {suffix}"[:50].strip()
        key = _fold(candidate)
        if key not in used:
            used.add(key)
            return candidate
        suffix += 1


async def _classify_with_llm(documents: list[dict[str, Any]]) -> list[dict]:
    if not documents:
        return []
    raw = await client.chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(documents)},
        ],
        max_tokens=max(900, min(2800, len(documents) * 180)),
        enable_thinking=settings.agent_reasoning,
    )
    parsed = client.extract_json_block(raw)
    return parsed.get("documents", []) if isinstance(parsed, dict) else []


def _validated_classifications(raw_items: list[dict], file_count: int) -> dict[int, dict]:
    result: dict[int, dict] = {}
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        file_index = _coerce_int(raw.get("fileIndex", raw.get("index")))
        if file_index is None or not 0 <= file_index < file_count or file_index in result:
            continue
        result[file_index] = {
            "type": _canonical_type(raw.get("type")),
            "documentName": str(raw.get("documentName") or raw.get("title") or "").strip(),
            "subjectName": _clean_subject_name(raw.get("subjectName")),
        }
    return result


def _route_for_type(doc_type: str, document_name: str, used_slots: set[int]) -> tuple[str, int | None, str, bool]:
    row = _ROW_BY_TYPE.get(doc_type)
    if row is None:
        return "new", None, document_name, True
    component_index, component_name = row
    if component_index in used_slots:
        return "new", None, document_name, True
    used_slots.add(component_index)
    return "existing", component_index, component_name, False


async def plan_xac_nhan_tthn_attachments_without_split(
    files: list[FileItem], options: dict | None = None, session: dict | None = None,
) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": file.name, "type": file.type, "dataUrl": file.dataUrl} for file in files]
    ocr_pairs = [(index, file) for index, file in enumerate(raw_files) if file.get("type") in _OCR_TYPES]

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file([file for _, file in ocr_pairs]) if ocr_pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    ocr_by_index = {raw_index: result for (raw_index, _), result in zip(ocr_pairs, ocr_results)}
    for file_index, result in ocr_by_index.items():
        if result.get("error"):
            errors.append(f"OCR fileIndex={file_index} {raw_files[file_index].get('name')}: {result['error']}")

    documents = [
        {
            "fileIndex": file_index,
            "ocrText": str((ocr_by_index.get(file_index) or {}).get("text") or ""),
        }
        for file_index in range(len(raw_files))
    ]
    started = time.monotonic()
    raw_classifications: list[dict] = []
    if documents:
        try:
            raw_classifications = await _classify_with_llm(documents)
        except Exception as exc:  # noqa: BLE001 - fallback vẫn giữ đủ file
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)
    classified_by_index = _validated_classifications(raw_classifications, len(raw_files))

    attachments: list[dict] = []
    classified: list[dict] = []
    identity_indexes: set[int] = set()
    identity_subject_by_index: dict[int, str] = {}
    used_names: set[str] = set()
    used_slots: set[int] = set()

    for file_index, file in enumerate(raw_files):
        ocr_text = documents[file_index]["ocrText"]
        llm_item = classified_by_index.get(file_index) or {}
        doc_type = llm_item.get("type") if file_index in classified_by_index else _rule_doc_type(ocr_text)
        declaration_bundle = _is_declaration_bundle(ocr_text)
        # LLM có thể chỉ nhìn trang đầu và trả paper_declaration. Khi OCR chứng minh có thêm tài liệu
        # độc lập, ép về other; riêng type STT 2-5 vẫn được giữ để không làm sai hàng đính kèm.
        if declaration_bundle and doc_type in {"identity", "paper_declaration", "other"}:
            doc_type = "other"
        if doc_type == "identity":
            document_name = _unique_document_name(
                _identity_document_name(ocr_text, llm_item.get("subjectName") or ""),
                used_names,
                _IDENTITY_LABEL,
            )
            identity_indexes.add(file_index)
            identity_subject_by_index[file_index] = llm_item.get("subjectName") or ""
        elif doc_type == "paper_declaration":
            document_name = _unique_document_name(_PAPER_DECLARATION_LABEL, used_names, _PAPER_DECLARATION_LABEL)
        else:
            proposed = llm_item.get("documentName") or _fallback_document_name(ocr_text)
            if declaration_bundle:
                proposed = _DECLARATION_BUNDLE_LABEL
            fallback = _OTHER_LABEL if doc_type == "other" else proposed or _OTHER_LABEL
            document_name = _unique_document_name(proposed, used_names, fallback)

        target, component_index, component_name, needs_add = _route_for_type(
            doc_type, document_name, used_slots,
        )
        attachments.append({
            "fileIndex": file_index,
            "fileName": str(file.get("name") or f"file-{file_index + 1}"),
            "documentName": document_name,
            "componentName": component_name,
            "target": target,
            "componentIndex": component_index,
            "needsAddComponent": needs_add,
            "detectedType": document_name,
        })
        classified.append({
            "fileIndex": file_index,
            "fileName": file.get("name"),
            "type": doc_type,
            "documentName": document_name,
            "target": target,
            "componentIndex": component_index,
        })

    ocr_text_by_index = {item["fileIndex"]: item["ocrText"] for item in documents}
    attachments = merge_identity_attachments(attachments, ocr_text_by_index, identity_indexes)

    # Đặt lại tên sau khi gộp để mặt sau có thể dùng họ tên đọc được từ mặt trước cùng chủ thể.
    used_identity_names: set[str] = set()
    final_identity_name_by_file: dict[int, str] = {}
    for item in attachments:
        source_indexes = item.get("sourceFileIndexes") or [item.get("fileIndex")]
        if not any(index in identity_indexes for index in source_indexes):
            continue
        combined_text = "\n".join(ocr_text_by_index.get(index, "") for index in source_indexes)
        subjects = []
        for index in source_indexes:
            subject = _clean_subject_name(identity_subject_by_index.get(index, ""))
            if subject and _fold(subject) not in {_fold(value) for value in subjects}:
                subjects.append(subject)
        base_name = _identity_document_name(combined_text, subjects[0] if len(subjects) == 1 else "")
        document_name = _unique_document_name(base_name, used_identity_names, _IDENTITY_LABEL)
        item["documentName"] = document_name
        item["detectedType"] = document_name
        if item.get("target") == "new":
            item["componentName"] = document_name
        for index in source_indexes:
            if isinstance(index, int):
                final_identity_name_by_file[index] = document_name
    for item in classified:
        if item["fileIndex"] in final_identity_name_by_file:
            item["documentName"] = final_identity_name_by_file[item["fileIndex"]]

    indexed_ocr_results = []
    for file_index, file in enumerate(raw_files):
        result = ocr_by_index.get(file_index)
        if result:
            indexed_ocr_results.append({
                **result,
                "name": f"fileIndex={file_index} · {file.get('name') or f'file-{file_index + 1}'}",
            })

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [file["name"] for file in raw_files],
            "ocrDocuments": [
                raw_files[index].get("name") for index, result in ocr_by_index.items() if result.get("text")
            ],
            "llmDocuments": [file.get("name") for file in raw_files],
            "sessionId": (session or {}).get("request_id"),
            "attachmentMode": "preserve_files",
            "classified": classified,
        },
        "ocr_text": join_ocr_documents(indexed_ocr_results),
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "errors": errors,
    }


plan = plan_xac_nhan_tthn_attachments_without_split

__all__ = ["plan", "plan_xac_nhan_tthn_attachments_without_split"]
