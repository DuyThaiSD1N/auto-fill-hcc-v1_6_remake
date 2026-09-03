"""Tách tài liệu logic khi người dùng bật tách hồ sơ đăng ký lại khai sinh."""

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

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_ALLOWED_TYPES = {
    "birth_certificate_copy",
    "identity",
    "personal_supporting_document",
    "authorization",
    "paper_declaration",
    "commitment_statement",
    "death_document",
    "blank_page",
    "other",
}

_BIRTH_LABEL = "Giấy khai sinh bản sao"
_IDENTITY_LABEL = "Căn cước công dân"
_SUPPORTING_LABEL = "Giấy tờ cá nhân"
_AUTHORIZATION_LABEL = "Văn bản ủy quyền"
_DECLARATION_LABEL = "Tờ khai bản giấy"
_COMMITMENT_LABEL = "Bản cam đoan"
_DEATH_LABEL = "Trích lục khai tử"
_OTHER_LABEL = "Giấy tờ đăng ký lại khai sinh"

_ROW_2_COMPONENT = (
    "+ Bản sao Giấy khai sinh do cơ quan có thẩm quyền của Việt Nam cấp hợp lệ "
    "(bản sao được chứng thực từ bản chính, bản sao được cấp từ Sổ đăng ký khai sinh); "
    "bản chính hoặc bản sao giấy tờ có giá trị thay thế Giấy khai sinh"
)
_ROW_3_COMPONENT = (
    "+ Trường hợp người yêu cầu không có giấy tờ nêu trên thì phải nộp bản sao giấy tờ "
    "do cơ quan, tổ chức có thẩm quyền của Việt Nam cấp hợp lệ như: Giấy chứng minh nhân dân, "
    "Thẻ căn cước công dân hoặc Hộ chiếu; giấy tờ chứng minh về nơi cư trú; Bằng tốt nghiệp, "
    "Giấy chứng nhận, Chứng chỉ, Học bạ, hồ sơ học tập"
)
_ROW_5_COMPONENT = (
    "- Văn bản ủy quyền theo quy định của pháp luật trong trường hợp ủy quyền thực hiện "
    "việc đăng ký lại khai sinh."
)

_PAGE_HEADER_RE = re.compile(
    r"(?im)^[\t \u2500-\u257f-]*(?:trang|page)\s+(\d+)\s*/\s*(\d+)"
    r"[\t \u2500-\u257f-]*$"
)
_CCCD_HEADER_RE = re.compile(
    r"(?im)^\s*(?:CĂN CƯỚC CÔNG DÂN|THẺ CĂN CƯỚC|CĂN CƯỚC)\s*$"
)
_SUBJECT_NAME_RE = re.compile(
    r"(?im)(?:họ\s*(?:,|và)?\s*tên|full\s*name)\s*:?\s*(?:\n\s*)?"
    r"([A-ZÀ-ỸĐ][A-ZÀ-ỸĐ\s]{3,60})"
)
_DEATH_MARKERS = ("trich luc khai tu", "giay bao tu", "giay chung tu", "giay khai tu")
_CCCD_MARKERS = (
    "citizen identity",
    "identity card",
    "idvnm",
    "dac diem nhan dang",
    "personal identification",
)
_TITLE_SIGNAL_RE = re.compile(
    r"\b(?:to khai|ban cam doan|giay cam doan|giay|quyet dinh|trich luc|don|van ban|"
    r"hop dong|hoc ba|bang|can cuoc|ho chieu)\b"
)
_TITLE_HEADER_MARKERS = (
    "cong hoa xa hoi chu nghia viet nam",
    "doc lap tu do hanh phuc",
    "socialist republic",
    "independence freedom happiness",
)


def _truncate_text(text: str, limit: int = 1800) -> str:
    # Giữ ranh giới dòng để LLM còn phân biệt tiêu đề thật với tên giấy tờ chỉ được nhắc trong thân bài.
    lines = [re.sub(r"[\t ]+", " ", line).strip() for line in str(text or "").splitlines()]
    value = "\n".join(line for line in lines if line).strip()
    return value if len(value) <= limit else value[:limit] + "..."


def _canonical_type(value: Any) -> str:
    doc_type = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    aliases = {
        "cccd": "identity",
        "cmnd": "identity",
        "passport": "identity",
        "birth_certificate": "birth_certificate_copy",
        "civil_status_birth": "birth_certificate_copy",
        "residence_proof": "personal_supporting_document",
        "education_document": "personal_supporting_document",
        "civil_status_death": "death_document",
    }
    doc_type = aliases.get(doc_type, doc_type)
    return doc_type if doc_type in _ALLOWED_TYPES else "other"


def _label_for_type(doc_type: str) -> str:
    return {
        "birth_certificate_copy": _BIRTH_LABEL,
        "identity": _IDENTITY_LABEL,
        "personal_supporting_document": _SUPPORTING_LABEL,
        "authorization": _AUTHORIZATION_LABEL,
        "paper_declaration": _DECLARATION_LABEL,
        "commitment_statement": _COMMITMENT_LABEL,
        "death_document": _DEATH_LABEL,
    }.get(doc_type, _OTHER_LABEL)


def _clean_subject_name(value: Any) -> str:
    subject = re.sub(r"\s+", " ", str(value or "")).strip(" :-")
    if _fold(subject) in {"", "ho ten", "ho va ten", "full name", "khong ro"}:
        return ""
    return subject[:40].strip()


def _subject_from_text(text: str) -> str:
    match = _SUBJECT_NAME_RE.search(str(text or ""))
    return _clean_subject_name(match.group(1)) if match else ""


def _identity_name(subject_name: Any) -> str:
    subject = _clean_subject_name(subject_name)
    return normalize_document_name(f"CCCD {subject}", _IDENTITY_LABEL) if subject else _IDENTITY_LABEL


def _unique_name(base: str, used: set[str], fallback: str) -> str:
    normalized = normalize_document_name(base, fallback)
    if _fold(normalized) not in used:
        used.add(_fold(normalized))
        return normalized
    stem = normalized[:45].strip() or fallback
    suffix = 2
    while True:
        candidate = f"{stem} {suffix}"[:50].strip()
        if _fold(candidate) not in used:
            used.add(_fold(candidate))
            return candidate
        suffix += 1


def _decode_data_url(data_url: str) -> bytes:
    _, separator, payload = str(data_url or "").partition(",")
    if not separator:
        return b""
    payload += "=" * (-len(payload) % 4)
    return base64.b64decode(payload)


def _pdf_page_count(file: dict) -> int:
    is_pdf = (
        "pdf" in str(file.get("type") or "").lower()
        or str(file.get("name") or "").lower().endswith(".pdf")
    )
    if not is_pdf:
        return 1
    try:
        document = fitz.open(stream=_decode_data_url(file.get("dataUrl") or ""), filetype="pdf")
        try:
            return max(1, document.page_count)
        finally:
            document.close()
    except Exception:  # noqa: BLE001 - PDF test giả hoặc file lỗi vẫn phải được giữ
        return 1


def _split_ocr_pages(text: str, expected_count: int) -> tuple[list[dict], bool]:
    """Không có header trang thì không cho mô hình tự đoán vị trí cắt."""
    value = str(text or "")
    matches = list(_PAGE_HEADER_RE.finditer(value))
    if not matches:
        return [
            {"pageNumber": 1, "pageTo": expected_count, "ocrText": _truncate_text(value)}
        ], expected_count == 1

    pages_by_number: dict[int, str] = {}
    total = expected_count
    for position, match in enumerate(matches):
        page_number = int(match.group(1))
        total = max(total, int(match.group(2)))
        end = matches[position + 1].start() if position + 1 < len(matches) else len(value)
        pages_by_number[page_number] = value[match.end():end].strip()
    return [
        {"pageNumber": number, "ocrText": _truncate_text(pages_by_number.get(number, ""))}
        for number in range(1, max(1, total) + 1)
    ], True


async def _classify_with_llm(documents: list[dict[str, Any]]) -> list[dict]:
    if not documents:
        return []
    raw = await client.chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(documents)},
        ],
        max_tokens=max(
            1200,
            min(4000, sum(len(item.get("pages") or []) for item in documents) * 180),
        ),
        enable_thinking=settings.agent_reasoning,
    )
    return client.extract_json_block(raw).get("documents", []) or []


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _fallback_segment(file_index: int, page_from: int, page_to: int, file_name: str) -> dict:
    return {
        "fileIndex": file_index,
        "pageFrom": page_from,
        "pageTo": page_to,
        "type": "other",
        "documentName": file_name,
        "subjectName": "",
    }


def _validated_segments(
    raw_segments: list[dict],
    raw_files: list[dict],
    file_meta: dict[int, dict],
    errors: list[str],
) -> list[dict]:
    """Giữ đủ trang và loại mọi khoảng trang không hợp lệ hoặc bị chồng."""
    by_file: dict[int, list[dict]] = {index: [] for index in range(len(raw_files))}
    for raw in raw_segments:
        if not isinstance(raw, dict):
            continue
        file_index = _coerce_int(raw.get("fileIndex", raw.get("index")))
        if file_index not in by_file:
            continue
        page_count = file_meta[file_index]["pageCount"]
        page_from = _coerce_int(raw.get("pageFrom")) or 1
        page_to = _coerce_int(raw.get("pageTo")) or page_count
        if not 1 <= page_from <= page_to <= page_count:
            errors.append(
                f"Phân đoạn fileIndex={file_index} không hợp lệ: {page_from}-{page_to}."
            )
            continue
        by_file[file_index].append({
            "fileIndex": file_index,
            "pageFrom": page_from,
            "pageTo": page_to,
            "type": _canonical_type(raw.get("type")),
            "documentName": str(raw.get("documentName") or raw.get("title") or "").strip(),
            "subjectName": str(raw.get("subjectName") or "").strip(),
        })

    validated: list[dict] = []
    for file_index, file in enumerate(raw_files):
        meta = file_meta[file_index]
        page_count = meta["pageCount"]
        items = sorted(by_file[file_index], key=lambda item: (item["pageFrom"], item["pageTo"]))
        if not meta["pageBoundariesAvailable"]:
            first = items[0] if items else _fallback_segment(
                file_index, 1, page_count, str(file.get("name") or "file")
            )
            validated.append({**first, "pageFrom": 1, "pageTo": page_count})
            continue

        occupied: set[int] = set()
        accepted: list[dict] = []
        for item in items:
            pages = set(range(item["pageFrom"], item["pageTo"] + 1))
            if pages & occupied:
                errors.append(
                    f"Phân đoạn fileIndex={file_index} bị chồng trang; bỏ đoạn "
                    f"{item['pageFrom']}-{item['pageTo']}."
                )
                continue
            occupied.update(pages)
            accepted.append(item)

        missing = [page for page in range(1, page_count + 1) if page not in occupied]
        range_start = range_end = None
        for page in missing + [None]:
            if page is not None and range_start is None:
                range_start = range_end = page
            elif page is not None and page == range_end + 1:
                range_end = page
            else:
                if range_start is not None:
                    accepted.append(_fallback_segment(
                        file_index,
                        range_start,
                        range_end,
                        str(file.get("name") or f"file-{file_index + 1}"),
                    ))
                range_start = range_end = page
        validated.extend(sorted(accepted, key=lambda item: item["pageFrom"]))
    return sorted(validated, key=lambda item: (item["fileIndex"], item["pageFrom"]))


def _segment_text(
    segment: dict,
    page_text_by_file: dict[int, dict[int, str]],
    full_text_by_file: dict[int, str],
) -> str:
    pages = page_text_by_file.get(segment["fileIndex"]) or {}
    if not pages:
        return full_text_by_file.get(segment["fileIndex"], "")
    return "\n".join(
        pages.get(page, "") for page in range(segment["pageFrom"], segment["pageTo"] + 1)
    ).strip()


def _looks_like_cccd(text: str) -> bool:
    folded = _fold(text)
    return bool(_CCCD_HEADER_RE.search(text or "")) or any(marker in folded for marker in _CCCD_MARKERS)


def _document_title(text: str) -> str:
    """Lấy tiêu đề có cấu trúc từ OCR, không lấy tên giấy tờ nằm trong câu kê khai."""
    for raw_line in str(text or "").splitlines()[:24]:
        line = re.sub(r"\s+", " ", raw_line).strip(" :-–—|\t")
        folded = _fold(line)
        if not 3 <= len(line) <= 120:
            continue
        if any(marker in folded for marker in _TITLE_HEADER_MARKERS):
            continue
        if _TITLE_SIGNAL_RE.search(folded):
            return line
    return ""


def _title_type(title: str) -> str | None:
    folded = _fold(title)
    if not folded:
        return None
    if "cam doan" in folded:
        return "commitment_statement"
    if "to khai" in folded and "dang ky lai" in folded and "khai sinh" in folded:
        return "paper_declaration"
    if "uy quyen" in folded:
        return "authorization"
    if any(marker in folded for marker in _DEATH_MARKERS):
        return "death_document"
    if "khai sinh" in folded and ("giay" in folded or "trich luc" in folded):
        return "birth_certificate_copy"
    if any(marker in folded for marker in (
        "can cuoc", "chung minh nhan dan", "ho chieu", "identity card",
    )):
        return "identity"
    return None


def _display_title(title: str, fallback: str) -> str:
    value = normalize_document_name(title, fallback)
    letters = [char for char in value if char.isalpha()]
    if letters and all(char.isupper() for char in letters):
        value = value.lower()
        value = value[:1].upper() + value[1:]
    return value


def _looks_like_death_document(text: str, title: str) -> bool:
    if _title_type(title) == "death_document":
        return True
    folded = _fold(text)
    structural_markers = (
        "da chet vao luc",
        "noi chet",
        "da duoc dang ky khai tu",
        "so dang ky khai tu",
        "thuc hien trich luc tu so dang ky khai tu",
    )
    return sum(marker in folded for marker in structural_markers) >= 2


def _death_name(text: str, title: str) -> str:
    if not _looks_like_death_document(text, title):
        return ""
    evidence = f"{_fold(title)} {_fold(text)[:1200]}"
    if "trich luc khai tu" in evidence:
        return "Trích lục khai tử"
    if "giay bao tu" in evidence:
        return "Giấy báo tử"
    return "Giấy chứng tử"


def _source_segment(segment: dict, page_count: int) -> dict | None:
    if segment["pageFrom"] == 1 and segment["pageTo"] == page_count:
        return None
    return {
        "fileIndex": segment["fileIndex"],
        "pageIndexes": list(range(segment["pageFrom"] - 1, segment["pageTo"])),
    }


def _desired_route(doc_type: str) -> tuple[int | None, str]:
    if doc_type == "birth_certificate_copy":
        return 2, _ROW_2_COMPONENT
    if doc_type in {"identity", "personal_supporting_document"}:
        return 3, _ROW_3_COMPONENT
    if doc_type == "authorization":
        return 5, _ROW_5_COMPONENT
    return None, ""


async def plan_dang_ky_lai_khai_sinh_attachments(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": file.name, "type": file.type, "dataUrl": file.dataUrl} for file in files]
    ocr_pairs = [
        (index, file) for index, file in enumerate(raw_files) if file.get("type") in _OCR_TYPES
    ]

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file([file for _, file in ocr_pairs]) if ocr_pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    ocr_by_index = {raw_index: result for (raw_index, _), result in zip(ocr_pairs, ocr_results)}
    for raw_index, result in ocr_by_index.items():
        if result.get("error"):
            errors.append(
                f"OCR fileIndex={raw_index} {raw_files[raw_index].get('name')}: {result['error']}"
            )

    file_meta: dict[int, dict] = {}
    page_text_by_file: dict[int, dict[int, str]] = {}
    full_text_by_file: dict[int, str] = {}
    llm_files: list[dict] = []
    for file_index, file in enumerate(raw_files):
        text = str((ocr_by_index.get(file_index) or {}).get("text") or "")
        full_text_by_file[file_index] = text
        actual_page_count = _pdf_page_count(file)
        pages, boundaries = _split_ocr_pages(text, actual_page_count)
        page_count = max((int(page.get("pageNumber") or 1) for page in pages), default=1)
        page_count = max(page_count, actual_page_count)
        file_meta[file_index] = {
            "pageCount": page_count,
            "pageBoundariesAvailable": boundaries,
        }
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
        except Exception as exc:  # noqa: BLE001 - fallback phải giữ đủ file/trang
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)
    segments = _validated_segments(raw_segments, raw_files, file_meta, errors)

    records: list[dict] = []
    classified: list[dict] = []
    identity_records: list[dict] = []
    for order, raw_segment in enumerate(segments):
        file_index = raw_segment["fileIndex"]
        file = raw_files[file_index]
        page_count = file_meta[file_index]["pageCount"]
        segment = {**raw_segment, "pageCount": page_count}
        text = _segment_text(segment, page_text_by_file, full_text_by_file)
        doc_type = segment["type"]

        if doc_type == "blank_page":
            classified.append({
                "fileIndex": file_index,
                "fileName": file.get("name"),
                "pageFrom": segment["pageFrom"],
                "pageTo": segment["pageTo"],
                "type": "blank_page",
                "documentName": "Trang trắng",
                "target": "ignored",
                "componentIndex": None,
            })
            continue

        title = _document_title(text)
        title_type = _title_type(title)
        original_doc_type = doc_type
        if title_type:
            doc_type = title_type
        elif _looks_like_cccd(text):
            doc_type = "identity"
        elif doc_type == "identity":
            # LLM không được biến giấy tờ chuyên ngành có họ tên/ảnh thành CCCD khi OCR thiếu bằng chứng định danh.
            doc_type = "personal_supporting_document" if title else "other"

        death_name = _death_name(text, title)
        if doc_type == "death_document" and not death_name:
            # Tên LLM tự đặt không phải bằng chứng về sự kiện chết.
            doc_type = "personal_supporting_document" if title else "other"
        elif death_name:
            doc_type = "death_document"

        subject = _clean_subject_name(segment.get("subjectName"))
        if doc_type == "identity" and not subject:
            subject = _subject_from_text(text)
        if doc_type == "identity":
            base_name = _identity_name(subject)
        elif death_name:
            base_name = death_name
        elif title_type == "commitment_statement":
            base_name = _COMMITMENT_LABEL
        elif title_type == "paper_declaration":
            base_name = "Tờ khai đăng ký lại khai sinh"
        elif title_type == "authorization":
            base_name = _display_title(title, _AUTHORIZATION_LABEL)
        elif title_type == "birth_certificate_copy":
            base_name = _display_title(title, _BIRTH_LABEL)
        elif original_doc_type == "identity" and doc_type != "identity" and title:
            base_name = _display_title(title, _SUPPORTING_LABEL)
        else:
            base_name = segment.get("documentName") or _label_for_type(doc_type)

        item = {
            "fileIndex": file_index,
            "fileName": str(file.get("name") or f"file-{file_index + 1}"),
            "documentName": base_name,
            "componentName": base_name,
            "target": "new",
            "componentIndex": None,
            "needsAddComponent": True,
            "detectedType": base_name,
            "_docType": doc_type,
            "_order": order,
        }
        source = _source_segment(segment, page_count)
        if source:
            item["sourceSegments"] = [source]

        classified_item = {
            "fileIndex": file_index,
            "fileName": file.get("name"),
            "pageFrom": segment["pageFrom"],
            "pageTo": segment["pageTo"],
            "type": doc_type,
            "documentName": base_name,
            "target": "new",
            "componentIndex": None,
            "_order": order,
        }
        classified.append(classified_item)

        if doc_type == "identity":
            item["_subjectName"] = subject
            identity_records.append({"item": item, "ocrText": text, "order": order})
        else:
            records.append(item)

    if identity_records:
        grouped = merge_identity_records(
            identity_records,
            existing_slot=None,
            default_document_name=_IDENTITY_LABEL,
        )
        for item in grouped:
            item["_docType"] = "identity"
            item["documentName"] = _identity_name(item.get("_subjectName"))
            item["componentName"] = item["documentName"]
            item["detectedType"] = item["documentName"]
            records.append(item)

            sources = item.get("sourceSegments") or [
                {"fileIndex": item["fileIndex"], "pageIndexes": None}
            ]
            for source in sources:
                page_indexes = source.get("pageIndexes")
                for classified_item in classified:
                    if classified_item["type"] != "identity":
                        continue
                    if classified_item["fileIndex"] != source["fileIndex"]:
                        continue
                    if page_indexes is not None and not any(
                        classified_item["pageFrom"] <= int(page_index) + 1 <= classified_item["pageTo"]
                        for page_index in page_indexes
                    ):
                        continue
                    classified_item["documentName"] = item["documentName"]
                    classified_item["_routeOrder"] = int(item.get("_order", 0))

    records.sort(key=lambda item: int(item.get("_order", 0)))

    # Chọn đúng một người thắng cho mỗi dòng có sẵn. STT 3 luôn ưu tiên CCCD hơn giấy tờ hỗ trợ.
    winners: dict[int, int] = {}
    for slot in (2, 3, 5):
        candidates = [
            item for item in records if _desired_route(item["_docType"])[0] == slot
        ]
        if not candidates:
            continue
        if slot == 3:
            candidates.sort(key=lambda item: (item["_docType"] != "identity", item["_order"]))
        winners[slot] = int(candidates[0]["_order"])

    used_names: set[str] = set()
    attachments: list[dict] = []
    route_by_order: dict[int, tuple[str, int | None, str]] = {}
    for item in records:
        doc_type = item.pop("_docType")
        order = int(item.pop("_order"))
        item.pop("_subjectName", None)
        document_name = _unique_name(item["documentName"], used_names, _label_for_type(doc_type))
        item["documentName"] = document_name
        item["detectedType"] = document_name
        slot, existing_component = _desired_route(doc_type)
        if slot is not None and winners.get(slot) == order:
            item.update({
                "componentName": existing_component,
                "target": "existing",
                "componentIndex": slot,
                "needsAddComponent": False,
            })
        else:
            item.update({
                "componentName": document_name,
                "target": "new",
                "componentIndex": None,
                "needsAddComponent": True,
            })
        attachments.append(item)
        route_by_order[order] = (item["target"], item.get("componentIndex"), document_name)

    for item in classified:
        order = item.pop("_order", None)
        if order is None:
            continue
        route_order = int(item.pop("_routeOrder", order))
        target, component_index, document_name = route_by_order.get(
            route_order, (item["target"], item["componentIndex"], item["documentName"])
        )
        item.update({
            "target": target,
            "componentIndex": component_index,
            "documentName": document_name,
        })

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
                raw_files[index].get("name")
                for index, result in ocr_by_index.items()
                if result.get("text")
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


plan = plan_dang_ky_lai_khai_sinh_attachments

__all__ = ["plan", "plan_dang_ky_lai_khai_sinh_attachments"]
