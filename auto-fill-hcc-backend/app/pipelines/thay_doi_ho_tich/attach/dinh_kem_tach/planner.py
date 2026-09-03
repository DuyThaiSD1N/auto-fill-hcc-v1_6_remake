"""Lập kế hoạch đính kèm cho thủ tục thay đổi/cải chính hộ tịch."""

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

from app.pipelines.thay_doi_ho_tich.attach.dinh_kem_tach.prompt import (
    SYSTEM_PROMPT,
    build_user_prompt,
)
_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_ALLOWED_TYPES = {
    "identity", "paper_declaration", "supporting_evidence", "authorization", "blank_page", "other",
}

_IDENTITY_LABEL = "Căn cước công dân"
_IDENTITY_MIXED_LABEL = "Giấy tờ tùy thân"
_DECLARATION_LABEL = "Tờ khai cải chính hộ tịch bản giấy"
_EVIDENCE_LABEL = "Giấy tờ làm căn cứ cải chính hộ tịch"
_AUTHORIZATION_LABEL = "Văn bản ủy quyền"
_OTHER_LABEL = "Tài liệu kèm theo"
_BLANK_PAGE_LABEL = "Trang trắng"

_FALLBACK_SLOTS = {
    "supporting_evidence": (
        2,
        "Giấy tờ liên quan đến việc thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc",
    ),
    "authorization": (3, "Văn bản ủy quyền"),
}

_PAGE_HEADER_RE = re.compile(
    r"(?im)^[\t \u2500-\u257f-]*(?:trang|page)\s+(\d+)\s*/\s*(\d+)[\t \u2500-\u257f-]*$"
)
_IDENTITY_NUMBER_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")
_FACE_FRONT_MARKERS = (
    "can cuoc cong dan", "citizen identity", "identity card", "ho va ten", "full name",
    "ngay sinh", "date of birth", "gia tri den", "date of expiry", "passport", "ho chieu",
)
_FACE_BACK_MARKERS = (
    "dac diem nhan dang", "personal identification", "cuc truong cuc canh sat",
    "director general", "idvnm",
)


def _truncate_text(text: str, limit: int = 1800) -> str:
    # Giữ xuống dòng để LLM nhìn đúng khối tiêu đề nhiều dòng; chỉ rút gọn khoảng trắng ngang.
    lines = [re.sub(r"[\t ]+", " ", line).strip() for line in str(text or "").splitlines()]
    value = "\n".join(line for line in lines if line).strip()
    return value if len(value) <= limit else value[:limit] + "..."


def _canonical_type(item: dict) -> str:
    raw = re.sub(r"[\s-]+", "_", str(item.get("type") or "").strip().lower())
    aliases = {
        "id": "identity",
        "cccd": "identity",
        "cmnd": "identity",
        "passport": "identity",
        "requester_identity": "identity",
        "ho_tich_doc": "supporting_evidence",
        "civil_status": "supporting_evidence",
        "birth": "supporting_evidence",
        "marriage": "supporting_evidence",
        "death": "supporting_evidence",
        "declaration": "paper_declaration",
        "paper_form": "paper_declaration",
        "uy_quyen": "authorization",
        "power_of_attorney": "authorization",
    }
    raw = aliases.get(raw, raw)
    return raw if raw in _ALLOWED_TYPES else "other"


def _clean_subject_name(value: Any) -> str:
    subject = re.sub(r"\s+", " ", str(value or "")).strip(" :-")
    if _fold(subject) in {"", "ho ten", "ho va ten", "full name", "khong ro"}:
        return ""
    return subject[:40].strip()


def _identity_name(document_type: Any, subject_name: Any) -> str:
    folded_type = _fold(str(document_type or ""))
    if "chung minh nhan dan" in folded_type or "cmnd" in folded_type:
        label, fallback = "CMND", "Chứng minh nhân dân"
    elif "ho chieu" in folded_type or "passport" in folded_type:
        label = fallback = "Hộ chiếu"
    elif "can cuoc" in folded_type or "cccd" in folded_type or "identity card" in folded_type:
        label, fallback = "CCCD", _IDENTITY_LABEL
    else:
        label = fallback = _IDENTITY_MIXED_LABEL
    subject = _clean_subject_name(subject_name)
    return normalize_document_name(f"{label} {subject}", fallback) if subject else fallback


def _label_for_type(doc_type: str) -> str:
    return {
        "identity": _IDENTITY_LABEL,
        "paper_declaration": _DECLARATION_LABEL,
        "supporting_evidence": _EVIDENCE_LABEL,
        "authorization": _AUTHORIZATION_LABEL,
    }.get(doc_type, _OTHER_LABEL)


def _unique_name(base: str, used: set[str], fallback: str) -> str:
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


def _page_count(file: dict) -> int:
    is_pdf = "pdf" in str(file.get("type") or "").lower() or str(file.get("name") or "").lower().endswith(".pdf")
    if not is_pdf:
        return 1
    try:
        document = fitz.open(stream=_decode_data_url(file.get("dataUrl") or ""), filetype="pdf")
        try:
            return max(1, document.page_count)
        finally:
            document.close()
    except Exception:  # noqa: BLE001 - file hỏng vẫn phải được giữ nguyên để fallback
        return 1


def _split_pages(text: str, expected_count: int) -> tuple[list[dict], bool]:
    value = str(text or "")
    matches = list(_PAGE_HEADER_RE.finditer(value))
    if not matches:
        return [{"pageNumber": 1, "pageTo": expected_count, "ocrText": _truncate_text(value)}], expected_count == 1
    pages: dict[int, str] = {}
    total = expected_count
    for position, match in enumerate(matches):
        page_number = int(match.group(1))
        total = max(total, int(match.group(2)))
        end = matches[position + 1].start() if position + 1 < len(matches) else len(value)
        pages[page_number] = value[match.end():end].strip()
    return [
        {"pageNumber": number, "ocrText": _truncate_text(pages.get(number, ""))}
        for number in range(1, max(1, total) + 1)
    ], True


async def _classify(documents: list[dict[str, Any]]) -> list[dict]:
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
    output = parsed.get("documents", []) if isinstance(parsed, dict) else []
    return output if isinstance(output, list) else []


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _fallback_segment(file_index: int, page_from: int, page_to: int) -> dict:
    return {
        "fileIndex": file_index,
        "pageFrom": page_from,
        "pageTo": page_to,
        "type": "other",
        "documentName": "",
        "subjectName": "",
        "identityType": "",
        "titleText": "",
    }


def _validate_segments(raw: list[dict], files: list[dict], meta: dict[int, dict], errors: list[str]) -> list[dict]:
    by_file: dict[int, list[dict]] = {index: [] for index in range(len(files))}
    for item in raw:
        if not isinstance(item, dict):
            continue
        file_index = _as_int(item.get("fileIndex", item.get("index")))
        if file_index not in by_file:
            continue
        count = meta[file_index]["pageCount"]
        page_from = _as_int(item.get("pageFrom")) or 1
        page_to = _as_int(item.get("pageTo")) or count
        if 1 <= page_from <= page_to <= count:
            by_file[file_index].append({
                "fileIndex": file_index,
                "pageFrom": page_from,
                "pageTo": page_to,
                "type": _canonical_type(item),
                "documentName": str(item.get("documentName") or item.get("title") or "").strip(),
                "subjectName": _clean_subject_name(item.get("subjectName")),
                "identityType": str(item.get("identityType") or "").strip(),
                "titleText": str(item.get("titleText") or "").strip(),
            })
        else:
            errors.append(f"Phân đoạn fileIndex={file_index} có khoảng trang không hợp lệ: {page_from}-{page_to}.")

    valid: list[dict] = []
    for file_index in range(len(files)):
        count = meta[file_index]["pageCount"]
        items = sorted(by_file[file_index], key=lambda item: (item["pageFrom"], item["pageTo"]))
        if not meta[file_index]["pageBoundariesAvailable"]:
            if len(items) == 1:
                valid.append({**items[0], "pageFrom": 1, "pageTo": count})
            else:
                if len(items) > 1:
                    errors.append(f"Không có mốc trang cho fileIndex={file_index}; đã giữ nguyên file.")
                valid.append(_fallback_segment(file_index, 1, count))
            continue
        occupied: set[int] = set()
        accepted: list[dict] = []
        for item in items:
            pages = set(range(item["pageFrom"], item["pageTo"] + 1))
            if occupied & pages:
                errors.append(f"Phân đoạn fileIndex={file_index} bị chồng trang; đã bỏ đoạn bị chồng.")
                continue
            occupied.update(pages)
            accepted.append(item)
        missing = [page for page in range(1, count + 1) if page not in occupied]
        start = previous = None
        for page in missing + [None]:
            if page is not None and start is None:
                start = previous = page
            elif page is not None and page == previous + 1:
                previous = page
            else:
                if start is not None:
                    accepted.append(_fallback_segment(file_index, start, previous))
                start = previous = page
        valid.extend(sorted(accepted, key=lambda item: item["pageFrom"]))
    return sorted(valid, key=lambda item: (item["fileIndex"], item["pageFrom"]))


def _segment_text(segment: dict, page_texts: dict[int, dict[int, str]], full_texts: dict[int, str]) -> str:
    pages = page_texts.get(segment["fileIndex"]) or {}
    if not pages:
        return full_texts.get(segment["fileIndex"], "")
    return "\n".join(
        pages.get(page, "") for page in range(segment["pageFrom"], segment["pageTo"] + 1)
    ).strip()


def _ensure_unique_component_targets(attachments: list[dict], errors: list[str]) -> None:
    """Chốt cuối: một component hiện có chỉ được nhận đúng một tài liệu."""
    claimed_indexes: set[int] = set()
    used_new_names: set[str] = set()
    for item in attachments:
        index = _as_int(item.get("componentIndex"))
        if item.get("target") == "existing" and index and index not in claimed_indexes:
            claimed_indexes.add(index)
            continue
        if item.get("target") == "existing":
            errors.append(
                f"Component {index or 'không xác định'} bị trùng; tài liệu sau đã chuyển sang component mới."
            )
            item.update(target="new", componentIndex=None, needsAddComponent=True)
            item["componentName"] = item.get("documentName") or _OTHER_LABEL
        component_name = _unique_name(
            str(item.get("componentName") or item.get("documentName") or ""),
            used_new_names,
            _OTHER_LABEL,
        )
        item["componentName"] = component_name


def _slot_score(doc_type: str, component_name: str) -> int:
    folded = _fold(component_name)
    if doc_type == "supporting_evidence":
        markers = ("giay to lien quan", "thay doi", "cai chinh")
        return 12 if all(marker in folded for marker in markers) else 0
    if doc_type == "authorization":
        return 12 if "van ban uy quyen" in folded else (8 if "giay uy quyen" in folded else 0)
    return 0


def _slot(
    options: dict | None,
    doc_type: str,
    claimed_component_indexes: set[int],
) -> tuple[int, str] | None:
    fallback = _FALLBACK_SLOTS.get(doc_type)
    if not fallback:
        return None
    components = (((options or {}).get("attachmentContext") or {}).get("components") or [])
    candidates: list[tuple[int, int]] = []
    for component in components:
        if not isinstance(component, dict):
            continue
        index = _as_int(component.get("index"))
        name = str(component.get("componentName") or "").strip()
        score = _slot_score(doc_type, name)
        if index and index > 0 and score:
            candidates.append((score, index))
    if candidates:
        for _, index in sorted(candidates, key=lambda item: (-item[0], item[1])):
            if index in claimed_component_indexes:
                continue
            # `hasFile` từ DOM không đủ tin cậy để quyết định định tuyến: ô upload luôn chứa
            # nhãn nút chọn tệp và có thể bị báo là đã có file dù hàng còn trống. Chống trùng
            # được thực hiện bằng claimed_component_indexes ngay trong chính kế hoạch này.
            claimed_component_indexes.add(index)
            # componentIndex là khóa định tuyến. Dùng nhãn ổn định thay vì giữ nguyên chuỗi DOM
            # có thể bị lặp phần "Tên Hồ Sơ" trong trace và thông báo cho người dùng.
            return index, fallback[1]
        return None
    if components:
        return None
    index, name = fallback
    if index in claimed_component_indexes:
        return None
    claimed_component_indexes.add(index)
    return index, name


def _source_segment(segment: dict) -> dict | None:
    if segment["pageFrom"] == 1 and segment["pageTo"] == segment["pageCount"]:
        return None
    return {
        "fileIndex": segment["fileIndex"],
        "pageIndexes": list(range(segment["pageFrom"] - 1, segment["pageTo"])),
    }


def _build_item(
    file: dict,
    segment: dict,
    doc_type: str,
    document_name: str,
    options: dict | None,
    claimed_component_indexes: set[int],
) -> dict:
    slot = _slot(options, doc_type, claimed_component_indexes)
    item = {
        "fileIndex": segment["fileIndex"],
        "fileName": str(file.get("name") or f"file-{segment['fileIndex'] + 1}"),
        "documentName": document_name,
        "componentName": slot[1] if slot else document_name,
        "target": "existing" if slot else "new",
        "componentIndex": slot[0] if slot else None,
        "needsAddComponent": slot is None,
        "detectedType": document_name,
    }
    source = _source_segment(segment)
    if source:
        item["sourceSegments"] = [source]
    return item


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
    match = _IDENTITY_NUMBER_RE.search(str(text or ""))
    return match.group(0) if match else ""


def _ordered_identities(records: list[dict]) -> list[dict]:
    people: list[str] = []
    for record in records:
        number = _identity_number(record["ocrText"])
        if number and number not in people:
            people.append(number)
    groups: dict[str, list[dict]] = {person: [] for person in people}
    unknown: list[dict] = []
    for record in records:
        direct = _identity_number(record["ocrText"])
        digits = re.sub(r"\D+", "", record["ocrText"])
        person = direct or next(
            (candidate for candidate in people if candidate in digits or candidate[-9:] in digits),
            None,
        )
        (groups[person] if person else unknown).append(record)
    ordered: list[dict] = []
    for person in people:
        ordered.extend(sorted(groups[person], key=lambda item: (_face_rank(item["ocrText"]), item["order"])))
    ordered.extend(sorted(unknown, key=lambda item: (_face_rank(item["ocrText"]), item["order"])))
    return ordered


def _identity_group_name(records: list[dict]) -> str:
    folded = _fold("\n".join(record["ocrText"] for record in records))
    has_passport = "passport" in folded or "ho chieu" in folded
    has_cccd = "can cuoc" in folded or "citizen identity" in folded or "idvnm" in folded
    has_cmnd = "chung minh nhan dan" in folded
    if has_cccd and not has_passport and not has_cmnd:
        return _IDENTITY_LABEL
    if has_passport and not has_cccd and not has_cmnd:
        return "Hộ chiếu"
    if has_cmnd and not has_cccd and not has_passport:
        return "Chứng minh nhân dân"
    return _IDENTITY_MIXED_LABEL


async def plan_thay_doi_ho_tich_attachments(
    files: list[FileItem], options: dict | None = None, session: dict | None = None,
) -> dict:
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

    meta: dict[int, dict] = {}
    page_texts: dict[int, dict[int, str]] = {}
    full_texts: dict[int, str] = {}
    llm_documents: list[dict] = []
    for file_index, file in enumerate(raw_files):
        text = str((ocr_by_index.get(file_index) or {}).get("text") or "")
        full_texts[file_index] = text
        count = _page_count(file)
        pages, boundaries = _split_pages(text, count)
        count = max(count, max((int(page.get("pageNumber") or 1) for page in pages), default=1))
        meta[file_index] = {"pageCount": count, "pageBoundariesAvailable": boundaries}
        page_texts[file_index] = {
            int(page.get("pageNumber") or 1): str(page.get("ocrText") or "") for page in pages
        }
        llm_documents.append({
            "fileIndex": file_index,
            "pageCount": count,
            "pageBoundariesAvailable": boundaries,
            "pages": pages,
        })

    started = time.monotonic()
    raw_segments: list[dict] = []
    try:
        raw_segments = await _classify(llm_documents) if llm_documents else []
    except Exception as exc:  # noqa: BLE001 - fallback vẫn giữ đủ mọi file
        errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)
    segments = _validate_segments(raw_segments, raw_files, meta, errors)

    attachments: list[dict] = []
    classified: list[dict] = []
    identities: list[dict] = []
    identity_position: int | None = None
    used_names: set[str] = set()
    claimed_component_indexes: set[int] = set()
    for order, raw_segment in enumerate(segments):
        file_index = raw_segment["fileIndex"]
        file = raw_files[file_index]
        segment = {**raw_segment, "pageCount": meta[file_index]["pageCount"]}
        text = _segment_text(segment, page_texts, full_texts)
        doc_type = segment["type"]
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
        if doc_type == "identity":
            document_name = _identity_name(
                segment.get("identityType") or segment.get("documentName"),
                segment.get("subjectName"),
            )
        elif doc_type == "paper_declaration":
            document_name = _unique_name(_DECLARATION_LABEL, used_names, _DECLARATION_LABEL)
        else:
            base = (
                segment.get("documentName")
                or _label_for_type(doc_type)
            )
            document_name = _unique_name(base, used_names, _label_for_type(doc_type))
        item = _build_item(
            file,
            segment,
            doc_type,
            document_name,
            options,
            claimed_component_indexes,
        )
        if doc_type == "identity":
            item["_subjectName"] = _clean_subject_name(segment.get("subjectName"))
            if identity_position is None:
                identity_position = len(attachments)
            identities.append({"item": item, "ocrText": text, "order": order})
            target, component_index = "new", None
        else:
            attachments.append(item)
            target, component_index = item["target"], item.get("componentIndex")
        classified.append({
            "fileIndex": file_index,
            "fileName": file.get("name"),
            "pageFrom": segment["pageFrom"],
            "pageTo": segment["pageTo"],
            "titleText": segment.get("titleText") or "",
            "type": doc_type,
            "identityType": segment.get("identityType") or "",
            "documentName": document_name,
            "target": target,
            "componentIndex": component_index,
        })
    if identities:
        grouped_identities = merge_identity_records(
            identities,
            default_document_name=_IDENTITY_LABEL,
        )
        for item in grouped_identities:
            base_name = _identity_name(item.get("documentName"), item.pop("_subjectName", ""))
            document_name = _unique_name(base_name, used_names, _IDENTITY_LABEL)
            item["documentName"] = document_name
            item["componentName"] = document_name
            item["detectedType"] = document_name
        insert_at = identity_position or 0
        attachments[insert_at:insert_at] = grouped_identities
    _ensure_unique_component_targets(attachments, errors)

    indexed_ocr = [
        {
            **result,
            "name": f"fileIndex={file_index} · {raw_files[file_index].get('name') or f'file-{file_index + 1}'}",
        }
        for file_index, result in ocr_by_index.items()
    ]
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [file["name"] for file in raw_files],
            "ocrDocuments": [raw_files[index].get("name") for index, result in ocr_by_index.items() if result.get("text")],
            "llmDocuments": [file.get("name") for file in raw_files],
            "sessionId": (session or {}).get("request_id"),
            "attachmentMode": "split_documents",
            "classified": classified,
        },
        "ocr_text": join_ocr_documents(indexed_ocr),
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "errors": errors,
    }


plan = plan_thay_doi_ho_tich_attachments
