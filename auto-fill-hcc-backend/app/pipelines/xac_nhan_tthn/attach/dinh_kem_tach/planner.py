"""Phân đoạn và phân loại tài liệu khi người dùng bật tách hồ sơ."""

import base64
import re
import time
from typing import Any

import fitz

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines._shared.identity_merge import merge_identity_records
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from app.pipelines.xac_nhan_tthn.attach.dinh_kem_tach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.pipelines.xac_nhan_tthn.attach.nghia_hung import OMITTED_DECLARATION_NOTE, omits_paper_declaration

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_ALLOWED_LLM_TYPES = {
    "identity",
    "divorce_or_death_proof",
    "foreign_divorce_note",
    "previous_marital_status_certificate",
    "authorization",
    "paper_declaration",
    "blank_page",
    "other",
}

_IDENTITY_LABEL = "Căn cước công dân"
_DIVORCE_OR_DEATH_LABEL = "Giấy tờ chứng minh đã ly hôn hoặc vợ chồng đã chết"
_FOREIGN_DIVORCE_NOTE_LABEL = "Trích lục ghi chú ly hôn"
_PREVIOUS_CERT_LABEL = "Giấy xác nhận tình trạng hôn nhân đã cấp"
_AUTHORIZATION_LABEL = "Văn bản ủy quyền"
_PAPER_DECLARATION_LABEL = "Tờ khai bản giấy"
_OTHER_LABEL = "Tài liệu xác nhận tình trạng hôn nhân"
_BLANK_PAGE_LABEL = "Trang trắng"

_ROW_2_COMPONENT = (
    "Trường hợp người yêu cầu cấp Giấy xác nhận tình trạng hôn nhân đã có vợ hoặc chồng "
    "nhưng đã ly hôn hoặc người vợ/chồng đã chết"
)
_ROW_3_COMPONENT = "Công dân Việt Nam đã ly hôn, hủy việc kết hôn ở nước ngoài"
_ROW_4_COMPONENT = "Trường hợp cá nhân yêu cầu cấp lại Giấy xác nhận tình trạng hôn nhân"
_ROW_5_COMPONENT = (
    "Văn bản ủy quyền theo quy định của pháp luật trong trường hợp ủy quyền thực hiện "
    "việc cấp Giấy xác nhận tình trạng hôn nhân"
)

_PAGE_HEADER_RE = re.compile(
    r"(?im)^[\t \u2500-\u257f-]*(?:trang|page)\s+(\d+)\s*/\s*(\d+)"
    r"[\t \u2500-\u257f-]*$"
)
_CCCD_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")
_FACE_FRONT_MARKERS = (
    "can cuoc cong dan", "citizen identity", "identity card", "ho va ten", "full name",
    "ngay sinh", "date of birth", "gia tri den", "date of expiry",
)
_FACE_BACK_MARKERS = (
    "dac diem nhan dang", "personal identification", "cuc truong cuc canh sat",
    "director general", "idvnm",
)


def _truncate_text(text: str, limit: int = 1800) -> str:
    value = re.sub(r"\s+", " ", text or "").strip()
    return value if len(value) <= limit else value[:limit] + "..."


def _canonical_type(item: dict) -> str:
    raw = re.sub(r"[\s-]+", "_", str(item.get("type") or "").strip().lower())
    aliases = {
        "id": "identity",
        "cccd": "identity",
        "cmnd": "identity",
        "passport": "identity",
        "divorce_proof": "divorce_or_death_proof",
        "death_proof": "divorce_or_death_proof",
        "civil_status_death": "divorce_or_death_proof",
        "divorce_note": "foreign_divorce_note",
        "previous_certificate": "previous_marital_status_certificate",
    }
    raw = aliases.get(raw, raw)
    # Cache/provider cũ từng gộp giấy xác nhận cũ và ủy quyền vào một type.
    if raw == "previous_marital_status_certificate_or_authorization":
        evidence = _fold(f"{item.get('title', '')} {item.get('documentName', '')}")
        return "authorization" if "uy quyen" in evidence else "previous_marital_status_certificate"
    return raw if raw in _ALLOWED_LLM_TYPES else "other"


def _clean_subject_name(value: Any) -> str:
    subject = re.sub(r"\s+", " ", str(value or "")).strip(" :-")
    if _fold(subject) in {"", "ho ten", "ho va ten", "full name", "khong ro"}:
        return ""
    return subject[:40].strip()


def _label_for_type(doc_type: str, title: str = "") -> str:
    labels = {
        "identity": _IDENTITY_LABEL,
        "divorce_or_death_proof": _DIVORCE_OR_DEATH_LABEL,
        "foreign_divorce_note": _FOREIGN_DIVORCE_NOTE_LABEL,
        "previous_marital_status_certificate": _PREVIOUS_CERT_LABEL,
        "authorization": _AUTHORIZATION_LABEL,
        "paper_declaration": _PAPER_DECLARATION_LABEL,
    }
    return str(title or "").strip() or labels.get(doc_type, _OTHER_LABEL)


def _route_for_type(doc_type: str) -> tuple[str, int | None, str]:
    # STT 1 là eForm do cổng sinh sẵn, planner tuyệt đối không đính vào đó.
    if doc_type == "divorce_or_death_proof":
        return "existing", 2, _ROW_2_COMPONENT
    if doc_type == "foreign_divorce_note":
        return "existing", 3, _ROW_3_COMPONENT
    if doc_type == "previous_marital_status_certificate":
        return "existing", 4, _ROW_4_COMPONENT
    if doc_type == "authorization":
        return "existing", 5, _ROW_5_COMPONENT
    return "new", None, ""


def _unique_document_name(base: str, used: set[str], fallback: str) -> str:
    normalized = normalize_document_name(base, fallback)
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


def _decode_data_url(data_url: str) -> bytes:
    _, separator, payload = str(data_url or "").partition(",")
    if not separator:
        return b""
    payload += "=" * (-len(payload) % 4)
    return base64.b64decode(payload)


def _pdf_page_count(file: dict) -> int:
    is_pdf = "pdf" in str(file.get("type") or "").lower() or str(file.get("name") or "").lower().endswith(".pdf")
    if not is_pdf:
        return 1
    try:
        document = fitz.open(stream=_decode_data_url(file.get("dataUrl") or ""), filetype="pdf")
        try:
            return max(1, document.page_count)
        finally:
            document.close()
    except Exception:  # noqa: BLE001 - file giả trong test hoặc PDF hỏng vẫn cần fallback OCR
        return 1


def _split_ocr_pages(text: str, expected_count: int) -> tuple[list[dict], bool]:
    """Chỉ cho phép tách khi OCR giữ được header Trang n/m; không để LLM đoán ranh giới."""
    value = str(text or "")
    matches = list(_PAGE_HEADER_RE.finditer(value))
    if not matches:
        return [{"pageNumber": 1, "pageTo": expected_count, "ocrText": _truncate_text(value)}], expected_count == 1

    pages_by_number: dict[int, str] = {}
    declared_total = expected_count
    for position, match in enumerate(matches):
        page_number = int(match.group(1))
        declared_total = max(declared_total, int(match.group(2)))
        end = matches[position + 1].start() if position + 1 < len(matches) else len(value)
        pages_by_number[page_number] = value[match.end():end].strip()
    return [
        {"pageNumber": number, "ocrText": _truncate_text(pages_by_number.get(number, ""))}
        for number in range(1, max(1, declared_total) + 1)
    ], True


async def _classify_with_llm(documents: list[dict[str, Any]]) -> list[dict]:
    """Phân loại và phân đoạn mọi file bằng đúng một request LLM."""
    if not documents:
        return []
    raw = await client.chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(documents)},
        ],
        max_tokens=max(1200, min(4000, sum(len(item.get("pages") or []) for item in documents) * 180)),
        enable_thinking=settings.agent_reasoning,
    )
    parsed = client.extract_json_block(raw)
    return parsed.get("documents", []) if isinstance(parsed, dict) else []


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _fallback_segment(file_index: int, page_from: int, page_to: int, file_name: str) -> dict:
    suffix = f" trang {page_from}" if page_from == page_to else f" trang {page_from}-{page_to}"
    return {
        "fileIndex": file_index,
        "pageFrom": page_from,
        "pageTo": page_to,
        "type": "other",
        "title": "",
        "documentName": f"{file_name}{suffix}",
        "subjectName": "",
    }


def _validated_segments(
    raw_segments: list[dict], raw_files: list[dict], file_meta: dict[int, dict], errors: list[str],
) -> list[dict]:
    """Không làm mất, chồng hoặc đảo trang khi LLM trả phân đoạn lỗi."""
    by_file: dict[int, list[dict]] = {index: [] for index in range(len(raw_files))}
    for item in raw_segments:
        if not isinstance(item, dict):
            continue
        file_index = _coerce_int(item.get("fileIndex", item.get("index")))
        if file_index not in by_file:
            continue
        page_count = file_meta[file_index]["pageCount"]
        page_from = _coerce_int(item.get("pageFrom")) or 1
        page_to = _coerce_int(item.get("pageTo")) or page_count
        if not 1 <= page_from <= page_to <= page_count:
            errors.append(f"Phân đoạn fileIndex={file_index} có khoảng trang không hợp lệ: {page_from}-{page_to}.")
            continue
        by_file[file_index].append({
            "fileIndex": file_index,
            "pageFrom": page_from,
            "pageTo": page_to,
            "type": _canonical_type(item),
            "title": str(item.get("title") or "").strip(),
            "documentName": str(item.get("documentName") or "").strip(),
            "subjectName": _clean_subject_name(item.get("subjectName")),
        })

    valid: list[dict] = []
    for file_index, file in enumerate(raw_files):
        meta = file_meta[file_index]
        page_count = meta["pageCount"]
        items = sorted(by_file[file_index], key=lambda item: (item["pageFrom"], item["pageTo"]))
        if not meta["pageBoundariesAvailable"]:
            first = items[0] if items else _fallback_segment(file_index, 1, page_count, file.get("name") or "file")
            valid.append({**first, "pageFrom": 1, "pageTo": page_count})
            continue

        occupied: set[int] = set()
        accepted: list[dict] = []
        for item in items:
            pages = set(range(item["pageFrom"], item["pageTo"] + 1))
            if occupied & pages:
                errors.append(
                    f"Phân đoạn fileIndex={file_index} bị chồng trang; "
                    f"đã bỏ đoạn {item['pageFrom']}-{item['pageTo']}."
                )
                continue
            occupied.update(pages)
            accepted.append(item)

        missing = [page for page in range(1, page_count + 1) if page not in occupied]
        start = previous = None
        for page in missing + [None]:
            if page is not None and start is None:
                start = previous = page
            elif page is not None and page == previous + 1:
                previous = page
            else:
                if start is not None:
                    accepted.append(_fallback_segment(
                        file_index, start, previous, str(file.get("name") or f"file-{file_index + 1}"),
                    ))
                start = previous = page
        valid.extend(sorted(accepted, key=lambda item: item["pageFrom"]))
    return sorted(valid, key=lambda item: (item["fileIndex"], item["pageFrom"]))


def _segment_text(segment: dict, page_text_by_file: dict[int, dict[int, str]], full_text_by_file: dict[int, str]) -> str:
    file_index = segment["fileIndex"]
    pages = page_text_by_file.get(file_index) or {}
    if not pages:
        return full_text_by_file.get(file_index, "")
    return "\n".join(
        pages.get(page, "") for page in range(segment["pageFrom"], segment["pageTo"] + 1)
    ).strip()


def _face_rank(text: str) -> int:
    folded = _fold(text)
    front = any(marker in folded for marker in _FACE_FRONT_MARKERS)
    back = any(marker in folded for marker in _FACE_BACK_MARKERS)
    if front and not back:
        return 0
    if back and not front:
        return 1
    return 2


def _identity_number(text: str) -> str:
    match = _CCCD_RE.search(str(text or ""))
    return match.group(0) if match else ""


def _identity_person(text: str, people: list[str]) -> str | None:
    direct = _identity_number(text)
    if direct:
        return direct
    digits = re.sub(r"\D+", "", str(text or ""))
    for person in people:
        if person in digits or person[-9:] in digits:
            return person
    return None


def _ordered_identity_records(records: list[dict]) -> list[dict]:
    people: list[str] = []
    for record in records:
        number = _identity_number(record["ocrText"])
        if number and number not in people:
            people.append(number)
    groups: dict[str, list[dict]] = {person: [] for person in people}
    unknown: list[dict] = []
    for record in records:
        person = _identity_person(record["ocrText"], people)
        (groups[person] if person else unknown).append(record)
    ordered: list[dict] = []
    for person in people:
        ordered.extend(sorted(groups[person], key=lambda item: (_face_rank(item["ocrText"]), item["order"])))
    ordered.extend(sorted(unknown, key=lambda item: item["order"]))
    return ordered


def _source_segment(segment: dict, page_count: int) -> dict | None:
    if segment["pageFrom"] == 1 and segment["pageTo"] == page_count:
        return None
    return {
        "fileIndex": segment["fileIndex"],
        "pageIndexes": list(range(segment["pageFrom"] - 1, segment["pageTo"])),
    }


def _build_item(file: dict, segment: dict, doc_type: str, document_name: str) -> dict:
    target, component_index, existing_component = _route_for_type(doc_type)
    item = {
        "fileIndex": segment["fileIndex"],
        "fileName": str(file.get("name") or f"file-{segment['fileIndex'] + 1}"),
        "documentName": document_name,
        "componentName": existing_component if target == "existing" else document_name,
        "target": target,
        "componentIndex": component_index,
        "needsAddComponent": target == "new",
        "detectedType": document_name,
    }
    source = _source_segment(segment, segment["pageCount"])
    if source:
        item["sourceSegments"] = [source]
    return item


async def plan_xac_nhan_tthn_attachments(
    files: list[FileItem], options: dict | None = None, session: dict | None = None,
) -> dict:
    omit_declaration = omits_paper_declaration(options)
    errors: list[str] = []
    raw_files = [{"name": file.name, "type": file.type, "dataUrl": file.dataUrl} for file in files]
    ocr_pairs = [(index, file) for index, file in enumerate(raw_files) if file.get("type") in _OCR_TYPES]

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file([file for _, file in ocr_pairs]) if ocr_pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    ocr_by_index = {raw_index: result for (raw_index, _), result in zip(ocr_pairs, ocr_results)}
    for raw_index, result in ocr_by_index.items():
        if result.get("error"):
            errors.append(f"OCR fileIndex={raw_index} {raw_files[raw_index].get('name')}: {result['error']}")

    file_meta: dict[int, dict] = {}
    page_text_by_file: dict[int, dict[int, str]] = {}
    full_text_by_file: dict[int, str] = {}
    llm_files: list[dict] = []
    for file_index, file in enumerate(raw_files):
        text = str((ocr_by_index.get(file_index) or {}).get("text") or "")
        full_text_by_file[file_index] = text
        page_count = _pdf_page_count(file)
        pages, boundaries = _split_ocr_pages(text, page_count)
        page_count = max(page_count, max((int(page.get("pageNumber") or 1) for page in pages), default=1))
        file_meta[file_index] = {"pageCount": page_count, "pageBoundariesAvailable": boundaries}
        page_text_by_file[file_index] = {
            int(page.get("pageNumber") or 1): str(page.get("ocrText") or "") for page in pages
        }
        llm_files.append({
            "fileIndex": file_index,
            "pageCount": page_count,
            "pageBoundariesAvailable": boundaries,
            "pages": pages,
        })

    started = time.monotonic()
    raw_segments: list[dict] = []
    if llm_files:
        try:
            raw_segments = await _classify_with_llm(llm_files)
        except Exception as exc:  # noqa: BLE001 - fallback giữ đủ file, không làm rơi hồ sơ
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)
    segments = _validated_segments(raw_segments, raw_files, file_meta, errors)

    attachments: list[dict] = []
    classified: list[dict] = []
    identity_records: list[dict] = []
    identity_insert_at: int | None = None
    used_names: set[str] = set()
    used_slots: set[int] = set()

    for order, raw_segment in enumerate(segments):
        file_index = raw_segment["fileIndex"]
        file = raw_files[file_index]
        doc_type = raw_segment["type"]
        segment = {**raw_segment, "pageCount": file_meta[file_index]["pageCount"]}
        if doc_type == "blank_page":
            classified.append({
                "fileIndex": file_index,
                "fileName": file.get("name"),
                "pageFrom": segment["pageFrom"],
                "pageTo": segment["pageTo"],
                "type": doc_type,
                "documentName": _BLANK_PAGE_LABEL,
                "target": "ignored",
                "componentIndex": None,
            })
            continue
        if omit_declaration and doc_type == "paper_declaration":
            # Xã Nghĩa Hưng: đoạn Tờ khai (giấy hay scan) không đính, các đoạn khác giữ nguyên.
            pages = (
                str(segment["pageFrom"]) if segment["pageFrom"] == segment["pageTo"]
                else f"{segment['pageFrom']}-{segment['pageTo']}"
            )
            errors.append(f"{OMITTED_DECLARATION_NOTE}: trang {pages} của {file.get('name') or 'file'}")
            classified.append({
                "fileIndex": file_index,
                "fileName": file.get("name"),
                "pageFrom": segment["pageFrom"],
                "pageTo": segment["pageTo"],
                "type": doc_type,
                "documentName": _PAPER_DECLARATION_LABEL,
                "target": "ignored",
                "componentIndex": None,
            })
            continue
        if doc_type == "other":
            fallback = _OTHER_LABEL
            base_name = segment.get("documentName") or file.get("name") or ""
        else:
            fallback = _label_for_type(doc_type)
            base_name = segment.get("documentName") or _label_for_type(doc_type, segment.get("title", ""))
        document_name = (
            _IDENTITY_LABEL if doc_type == "identity"
            else _unique_document_name(base_name, used_names, fallback)
        )
        item = _build_item(file, segment, doc_type, document_name)

        if doc_type == "identity":
            if identity_insert_at is None:
                identity_insert_at = len(attachments)
            identity_records.append({
                "item": item,
                "ocrText": _segment_text(segment, page_text_by_file, full_text_by_file),
                "order": order,
                "subjectName": segment.get("subjectName") or "",
            })
            target, component_index = "new", None
        else:
            component_index = item.get("componentIndex")
            # Mỗi dòng có một input. Giữ file đầu đúng dòng và thêm các file cùng loại còn lại thành
            # phần mới để không ghi đè hoặc làm mất giấy tờ.
            if item["target"] == "existing":
                if component_index in used_slots:
                    item.update({
                        "target": "new",
                        "componentIndex": None,
                        "componentName": document_name,
                        "needsAddComponent": True,
                    })
                else:
                    used_slots.add(component_index)
            attachments.append(item)
            target, component_index = item["target"], item.get("componentIndex")

        classified.append({
            "fileIndex": file_index,
            "fileName": file.get("name"),
            "pageFrom": segment["pageFrom"],
            "pageTo": segment["pageTo"],
            "type": doc_type,
            "documentName": document_name,
            "target": target,
            "componentIndex": component_index,
        })

    if identity_records:
        grouped_identities = merge_identity_records(
            identity_records,
            default_document_name=_IDENTITY_LABEL,
        )
        subject_by_source: dict[tuple[int, tuple[int, ...] | None], str] = {}
        for record in identity_records:
            sources = record["item"].get("sourceSegments") or [{
                "fileIndex": record["item"]["fileIndex"],
                "pageIndexes": None,
            }]
            for source in sources:
                pages = source.get("pageIndexes")
                key = (source["fileIndex"], tuple(pages) if isinstance(pages, list) else None)
                subject_by_source[key] = _clean_subject_name(record.get("subjectName"))

        used_identity_names: set[str] = set()
        final_name_by_source: dict[tuple[int, tuple[int, ...] | None], str] = {}
        for item in grouped_identities:
            sources = item.get("sourceSegments") or [{"fileIndex": item["fileIndex"], "pageIndexes": None}]
            subjects: list[str] = []
            source_keys = []
            for source in sources:
                pages = source.get("pageIndexes")
                key = (source["fileIndex"], tuple(pages) if isinstance(pages, list) else None)
                source_keys.append(key)
                subject = subject_by_source.get(key, "")
                if subject and _fold(subject) not in {_fold(value) for value in subjects}:
                    subjects.append(subject)
            base_name = str(item.get("documentName") or _IDENTITY_LABEL)
            if len(subjects) == 1 and "can cuoc" in _fold(base_name):
                base_name = f"CCCD {subjects[0]}"
            document_name = _unique_document_name(base_name, used_identity_names, _IDENTITY_LABEL)
            item["documentName"] = document_name
            item["detectedType"] = document_name
            if item.get("target") == "new":
                item["componentName"] = document_name
            for key in source_keys:
                final_name_by_source[key] = document_name

        for row in classified:
            if row.get("type") != "identity":
                continue
            pages = list(range(row["pageFrom"] - 1, row["pageTo"]))
            page_key = (row["fileIndex"], tuple(pages))
            whole_key = (row["fileIndex"], None)
            row["documentName"] = final_name_by_source.get(
                page_key, final_name_by_source.get(whole_key, row["documentName"]),
            )
        insert_at = identity_insert_at or 0
        attachments[insert_at:insert_at] = grouped_identities

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
            "attachmentMode": "split_documents",
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


plan = plan_xac_nhan_tthn_attachments
