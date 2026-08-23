import base64
import re
import time
from typing import Any

import fitz

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_ALLOWED_LLM_TYPES = {
    "birth_certificate_copy",
    "identity",
    "personal_supporting_document",
    "authorization",
    "paper_declaration",
    "commitment_statement",
    "other",
}

_BIRTH_CERT_COPY_LABEL = "Giấy khai sinh bản sao"
_IDENTITY_LABEL = "Căn cước công dân"
_PERSONAL_SUPPORTING_LABEL = "Giấy tờ cá nhân thay thế giấy khai sinh"
_AUTHORIZATION_LABEL = "Văn bản ủy quyền"
_PAPER_DECLARATION_LABEL = "Tờ khai bản giấy"
_COMMITMENT_STATEMENT_LABEL = "Bản cam đoan"
_OTHER_LABEL = "Tài liệu đăng ký lại khai sinh"

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
_CCCD_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")
_FACE_FRONT_MARKERS = (
    "can cuoc cong dan",
    "citizen identity",
    "identity card",
    "ho va ten",
    "full name",
    "ngay sinh",
    "date of birth",
    "gia tri den",
    "date of expiry",
)
_FACE_BACK_MARKERS = (
    "dac diem nhan dang",
    "personal identification",
    "cuc truong cuc canh sat",
    "director general",
    "idvnm",
)
_CCCD_FRONT_TITLES = ("citizen identity", "identity card")
_CCCD_BACK_TITLES = ("idvnm", "dac diem nhan dang", "personal identification")
_CCCD_DOCUMENT_NAMES = ("can cuoc cong dan", "the can cuoc", "cccd")
_DEATH_DOCUMENT_MARKERS = (
    "trich luc khai tu",
    "giay bao tu",
    "giay chung tu",
    "giay khai tu",
)
_CCCD_VIETNAMESE_HEADER_RE = re.compile(
    r"(?im)^\s*(?:CĂN CƯỚC CÔNG DÂN|THẺ CĂN CƯỚC|CĂN CƯỚC)\s*$"
)


def _truncate_text(text: str, limit: int = 1800) -> str:
    value = re.sub(r"\s+", " ", text or "").strip()
    return value if len(value) <= limit else value[:limit] + "..."


def _canonical_type(item: dict) -> str:
    raw = re.sub(r"[\s-]+", "_", str(item.get("type") or "").strip().lower())
    aliases = {
        "cccd": "identity",
        "cmnd": "identity",
        "passport": "identity",
        "birth_certificate": "birth_certificate_copy",
        "civil_status_birth": "birth_certificate_copy",
        "residence_proof": "personal_supporting_document",
        "education_document": "personal_supporting_document",
    }
    raw = aliases.get(raw, raw)
    if raw == "personal_supporting_document":
        evidence = _fold(f"{item.get('title', '')} {item.get('documentName', '')}")
        if any(marker in evidence for marker in (*_CCCD_DOCUMENT_NAMES, "chung minh nhan dan", "ho chieu")):
            raw = "identity"
    return raw if raw in _ALLOWED_LLM_TYPES else "other"


def _label_for_type(doc_type: str, title: str = "") -> str:
    labels = {
        "birth_certificate_copy": _BIRTH_CERT_COPY_LABEL,
        "identity": _IDENTITY_LABEL,
        "personal_supporting_document": _PERSONAL_SUPPORTING_LABEL,
        "authorization": _AUTHORIZATION_LABEL,
        "paper_declaration": _PAPER_DECLARATION_LABEL,
        "commitment_statement": _COMMITMENT_STATEMENT_LABEL,
    }
    # Tên component do người dùng nhìn thấy cần ổn định cho hai giấy tự lập này, không phụ thuộc
    # cách LLM diễn đạt tiêu đề dài/ngắn ở từng lần chạy.
    if doc_type in {"paper_declaration", "commitment_statement", "authorization"}:
        return labels[doc_type]
    return str(title or "").strip() or labels.get(doc_type, _OTHER_LABEL)


def _route_for_type(doc_type: str) -> tuple[str, int | None, str]:
    if doc_type == "birth_certificate_copy":
        return "existing", 2, _ROW_2_COMPONENT
    if doc_type == "authorization":
        return "existing", 5, _ROW_5_COMPONENT
    # CCCD và giấy tờ cá nhân được quyết định sau khi đã biết toàn bộ hồ sơ, để CCCD luôn ưu tiên STT 3.
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
    except Exception:  # noqa: BLE001 - file test giả hoặc PDF lỗi vẫn phải được giữ lại
        return 1


def _split_ocr_pages(text: str, expected_count: int) -> tuple[list[dict], bool]:
    """Chỉ cho phép tách khi OCR còn header Trang n/m; thiếu ranh giới thì giữ nguyên cả file."""
    value = str(text or "")
    matches = list(_PAGE_HEADER_RE.finditer(value))
    if not matches:
        return [
            {"pageNumber": 1, "pageTo": expected_count, "ocrText": _truncate_text(value)}
        ], expected_count == 1

    pages_by_number: dict[int, str] = {}
    declared_total = expected_count
    for position, match in enumerate(matches):
        page_number = int(match.group(1))
        declared_total = max(declared_total, int(match.group(2)))
        end = matches[position + 1].start() if position + 1 < len(matches) else len(value)
        pages_by_number[page_number] = value[match.end():end].strip()
    pages = [
        {"pageNumber": number, "ocrText": _truncate_text(pages_by_number.get(number, ""))}
        for number in range(1, max(1, declared_total) + 1)
    ]
    return pages, True


async def _classify_with_llm(documents: list[dict[str, Any]]) -> list[dict]:
    """Phân đoạn mọi file bằng đúng một request LLM."""
    if not documents:
        return []
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    page_total = sum(len(item.get("pages") or []) for item in documents)
    raw = await client.chat(
        messages,
        max_tokens=max(1200, min(4000, page_total * 180)),
        enable_thinking=settings.agent_reasoning,
    )
    parsed = client.extract_json_block(raw)
    return parsed.get("documents", []) or []


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
    }


def _validated_segments(
    raw_segments: list[dict],
    raw_files: list[dict],
    file_meta: dict[int, dict],
    errors: list[str],
) -> list[dict]:
    """Không để LLM làm mất, chồng hoặc đảo trang trong kế hoạch tách tài liệu."""
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
            errors.append(
                f"Phân đoạn fileIndex={file_index} có khoảng trang không hợp lệ: {page_from}-{page_to}."
            )
            continue
        by_file[file_index].append({
            "fileIndex": file_index,
            "pageFrom": page_from,
            "pageTo": page_to,
            "type": _canonical_type(item),
            "title": str(item.get("title") or "").strip(),
            "documentName": str(item.get("documentName") or "").strip(),
        })

    valid: list[dict] = []
    for file_index, file in enumerate(raw_files):
        meta = file_meta[file_index]
        page_count = meta["pageCount"]
        items = sorted(by_file[file_index], key=lambda item: (item["pageFrom"], item["pageTo"]))
        if not meta["pageBoundariesAvailable"]:
            first = items[0] if items else _fallback_segment(
                file_index, 1, page_count, str(file.get("name") or "file")
            )
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
                        file_index,
                        start,
                        previous,
                        str(file.get("name") or f"file-{file_index + 1}"),
                    ))
                start = previous = page
        valid.extend(sorted(accepted, key=lambda item: item["pageFrom"]))
    return sorted(valid, key=lambda item: (item["fileIndex"], item["pageFrom"]))


def _segment_text(
    segment: dict,
    page_text_by_file: dict[int, dict[int, str]],
    full_text_by_file: dict[int, str],
) -> str:
    file_index = segment["fileIndex"]
    pages = page_text_by_file.get(file_index) or {}
    if not pages:
        return full_text_by_file.get(file_index, "")
    return "\n".join(
        pages.get(page, "") for page in range(segment["pageFrom"], segment["pageTo"] + 1)
    ).strip()


def _looks_like_cccd(text: str, document_name: str = "") -> bool:
    folded = _fold(text)
    folded_name = _fold(document_name)
    return (
        any(marker in folded for marker in _CCCD_FRONT_TITLES + _CCCD_BACK_TITLES)
        or bool(_CCCD_VIETNAMESE_HEADER_RE.search(text or ""))
        or any(marker in folded_name for marker in _CCCD_DOCUMENT_NAMES)
    )


def _death_document_name(text: str, document_name: str = "") -> str:
    """Nhận diện tiêu đề khai tử để chặn LLM đưa nhầm giấy tờ sự kiện chết vào STT 2."""
    folded_name = _fold(document_name)
    folded_heading = _fold(text)[:800]
    evidence = f"{folded_name} {folded_heading}"
    if not any(marker in evidence for marker in _DEATH_DOCUMENT_MARKERS):
        return ""
    if "trich luc khai tu" in evidence:
        return "Trích lục khai tử"
    if "giay bao tu" in evidence:
        return "Giấy báo tử"
    if "giay chung tu" in evidence or "giay khai tu" in evidence:
        return "Giấy chứng tử"
    return ""


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


def _ordered_cccd_records(records: list[dict]) -> list[dict]:
    """Giữ từng người thành một cụm, mặt trước đứng trước mặt sau; file không rõ giữ theo thứ tự gốc."""
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


def _merge_all_cccds(records: list[dict]) -> dict:
    """Gộp toàn bộ CCCD vào STT 3 nhưng không đảo mặt giữa hai người."""
    ordered = _ordered_cccd_records(records)
    primary = ordered[0]["item"]
    segments: list[dict] = []
    for record in ordered:
        item = record["item"]
        segments.extend(
            item.get("sourceSegments")
            or [{"fileIndex": item["fileIndex"], "pageIndexes": None}]
        )
    merged = {
        **primary,
        "fileIndex": segments[0]["fileIndex"],
        "fileName": _IDENTITY_LABEL + ".pdf",
        "documentName": _IDENTITY_LABEL,
        "componentName": _ROW_3_COMPONENT,
        "target": "existing",
        "componentIndex": 3,
        "needsAddComponent": False,
        "detectedType": _IDENTITY_LABEL,
    }
    if len(segments) > 1 or segments[0].get("pageIndexes") is not None:
        merged["sourceSegments"] = segments
    else:
        merged.pop("sourceSegments", None)
    return merged


async def plan_dang_ky_lai_khai_sinh_attachments(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": file.name, "type": file.type, "dataUrl": file.dataUrl} for file in files]
    ocr_pairs = [(index, file) for index, file in enumerate(raw_files) if file.get("type") in _OCR_TYPES]

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file([file for _, file in ocr_pairs]) if ocr_pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    # Ghép theo vị trí request, không theo tên file: hai file cùng tên vẫn giữ đúng OCR riêng.
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
        page_count = _pdf_page_count(file)
        pages, boundaries = _split_ocr_pages(text, page_count)
        page_count = max(
            page_count,
            max((int(page.get("pageNumber") or 1) for page in pages), default=1),
        )
        file_meta[file_index] = {
            "pageCount": page_count,
            "pageBoundariesAvailable": boundaries,
        }
        page_text_by_file[file_index] = {
            int(page.get("pageNumber") or 1): str(page.get("ocrText") or "")
            for page in pages
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
        except Exception as exc:  # noqa: BLE001 - fallback vẫn giữ đủ mọi file/trang
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)
    segments = _validated_segments(raw_segments, raw_files, file_meta, errors)

    records: list[dict] = []
    used_names: set[str] = set()
    cccd_records: list[dict] = []
    for order, raw_segment in enumerate(segments):
        file_index = raw_segment["fileIndex"]
        file = raw_files[file_index]
        segment = {**raw_segment, "pageCount": file_meta[file_index]["pageCount"]}
        segment_text = _segment_text(segment, page_text_by_file, full_text_by_file)
        doc_type = segment["type"]
        llm_document_name = segment.get("documentName") or segment.get("title") or ""
        death_document_name = _death_document_name(segment_text, llm_document_name)
        # Dòng 2 chỉ dành cho chứng cứ về sự kiện khai sinh. Tiêu đề khai tử là bằng chứng
        # tất định mạnh hơn enum LLM, nên phải giữ thành thành phần riêng dù model chọn nhầm type.
        if doc_type == "birth_certificate_copy" and death_document_name:
            doc_type = "other"
        is_cccd = doc_type == "identity" and _looks_like_cccd(segment_text, llm_document_name)
        # Mặt sau CCCD hay bị LLM trả other vì không có tiêu đề; marker thẻ là bằng chứng tất định an toàn.
        if is_cccd:
            doc_type = "identity"

        fallback = _label_for_type(doc_type)
        if doc_type in {"paper_declaration", "commitment_statement", "authorization"}:
            base_name = _label_for_type(doc_type)
        elif doc_type == "other":
            base_name = (
                death_document_name
                or segment.get("documentName")
                or file.get("name")
                or ""
            )
        else:
            base_name = segment.get("documentName") or _label_for_type(
                doc_type, segment.get("title", "")
            )
        document_name = (
            _IDENTITY_LABEL
            if is_cccd
            else _unique_document_name(base_name, used_names, fallback)
        )
        item = _build_item(file, segment, doc_type, document_name)
        record = {
            "order": order,
            "fileIndex": file_index,
            "fileName": file.get("name"),
            "segment": segment,
            "ocrText": segment_text,
            "type": doc_type,
            "isCccd": is_cccd,
            "documentName": document_name,
            "item": item,
        }
        records.append(record)
        if is_cccd:
            cccd_records.append(record)

    attachments: list[dict] = []
    classified: list[dict] = []
    emitted_cccd = False
    row3_used = bool(cccd_records)
    used_slots: set[int] = set()
    for record in records:
        item = record["item"]
        doc_type = record["type"]

        if record["isCccd"]:
            if not emitted_cccd:
                attachments.append(_merge_all_cccds(cccd_records))
                emitted_cccd = True
            target, component_index = "existing", 3
        else:
            # Không có CCCD thì giấy tờ thuộc nhóm STT 3 đầu tiên chiếm ô có sẵn; các giấy còn lại
            # thành component mới để portal không ghi đè một input bằng nhiều file.
            is_row3_support = doc_type in {"identity", "personal_supporting_document"}
            if is_row3_support and not row3_used:
                item.update({
                    "target": "existing",
                    "componentIndex": 3,
                    "componentName": _ROW_3_COMPONENT,
                    "needsAddComponent": False,
                })
                row3_used = True

            component_index = item.get("componentIndex")
            if item["target"] == "existing":
                if component_index in used_slots:
                    item.update({
                        "target": "new",
                        "componentIndex": None,
                        "componentName": record["documentName"],
                        "needsAddComponent": True,
                    })
                else:
                    used_slots.add(component_index)
            attachments.append(item)
            target, component_index = item["target"], item.get("componentIndex")

        segment = record["segment"]
        classified.append({
            "fileIndex": record["fileIndex"],
            "fileName": record["fileName"],
            "pageFrom": segment["pageFrom"],
            "pageTo": segment["pageTo"],
            "type": doc_type,
            "documentName": record["documentName"],
            "target": target,
            "componentIndex": component_index,
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
