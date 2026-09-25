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
from app.pipelines.ket_hon.attach.dinh_kem_tach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.pipelines.xac_nhan_tthn.attach.nghia_hung import OMITTED_DECLARATION_NOTE, omits_paper_declaration
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_ALLOWED_DOC_TYPES = {"identity", "marriage_declaration", "commitment", "blank_page", "other"}

_IDENTITY_LABEL = "Giấy tờ tùy thân"
_DECLARATION_LABEL = "Tờ khai đăng ký kết hôn"
_COMMITMENT_LABEL = "Bản cam đoan"
_OTHER_LABEL = "Tài liệu đính kèm"

# Fallback tương thích khi extension cũ không gửi attachmentContext. Luồng mới ưu tiên tuyệt đối
# index + tên thật thu trực tiếp từ bảng thành phần trên trang.
_ID_SLOT_INDEX = 2
_ID_SLOT_COMPONENT = (
    "Hộ chiếu/Chứng minh nhân dân/Thẻ căn cước công dân/Thẻ căn cước/Căn cước điện tử"
)

_PAGE_HEADER_RE = re.compile(
    r"(?im)^[\t \u2500-\u257f-]*(?:trang|page)\s+(\d+)\s*/\s*(\d+)"
    r"[\t \u2500-\u257f-]*$"
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
    value = re.sub(r"\s+", " ", text or "").strip()
    return value if len(value) <= limit else value[:limit] + "..."


def _canonical_type(item: dict) -> str:
    raw = re.sub(r"[\s-]+", "_", str(item.get("type") or "").strip().lower())
    aliases = {
        "id": "identity",
        "cccd": "identity",
        "cmnd": "identity",
        "passport": "identity",
        "paper_declaration": "marriage_declaration",
        "declaration": "marriage_declaration",
        "cam_doan": "commitment",
        "blank": "blank_page",
        "empty": "blank_page",
    }
    raw = aliases.get(raw, raw)
    return raw if raw in _ALLOWED_DOC_TYPES else "other"


def _clean_subject_name(value: Any) -> str:
    subject = re.sub(r"\s+", " ", str(value or "")).strip(" :-")
    if _fold(subject) in {"", "ho ten", "ho va ten", "full name", "khong ro"}:
        return ""
    return subject[:40].strip()


def _label_for_type(doc_type: str, title: str = "") -> str:
    labels = {
        "identity": _IDENTITY_LABEL,
        "marriage_declaration": _DECLARATION_LABEL,
        "commitment": _COMMITMENT_LABEL,
    }
    return str(title or "").strip() or labels.get(doc_type, _OTHER_LABEL)


def _rule_doc_type(text: str) -> str:
    """Fallback an toàn: chỉ nhận identity khi OCR có dấu hiệu rõ của giấy tờ tùy thân."""
    folded = _fold(text)
    if "to khai dang ky ket hon" in folded:
        return "marriage_declaration"
    if "ban cam doan" in folded:
        return "commitment"
    identity_markers = (
        "can cuoc cong dan", "citizen identity card", "chung minh nhan dan",
        "giay chung minh nhan dan", "passport", "ho chieu", "idvnm",
    )
    return "identity" if any(marker in folded for marker in identity_markers) else "other"


def _fallback_document_name(text: str) -> str:
    """Giữ tên giấy tờ rõ ràng khi LLM lỗi; không biến mọi tài liệu thành CCCD."""
    folded = _fold(text)
    known_titles = (
        ("giay xac nhan tinh trang hon nhan", "Giấy xác nhận tình trạng hôn nhân"),
        ("quyet dinh ly hon", "Quyết định ly hôn"),
        ("ban an ly hon", "Bản án ly hôn"),
        ("trich luc khai tu", "Trích lục khai tử"),
        ("giay bao tu", "Giấy báo tử"),
        ("giay uy quyen", "Giấy ủy quyền"),
        ("van ban uy quyen", "Văn bản ủy quyền"),
    )
    for marker, title in known_titles:
        if marker in folded:
            return title
    return ""


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
    except Exception:  # noqa: BLE001 - PDF giả trong test hoặc PDF hỏng vẫn cần fallback OCR
        return 1


def _split_ocr_pages(text: str, expected_count: int) -> tuple[list[dict], bool]:
    """Không có header Trang n/m thì không cho LLM tự đoán điểm cắt của PDF nhiều trang."""
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
    """Phân đoạn và phân loại toàn bộ hồ sơ bằng đúng một request LLM."""
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


def _fallback_segment(file_index: int, page_from: int, page_to: int) -> dict:
    return {
        "fileIndex": file_index,
        "pageFrom": page_from,
        "pageTo": page_to,
        "type": "other",
        "title": "",
        "documentName": "",
    }


def _validated_segments(
    raw_segments: list[dict], raw_files: list[dict], file_meta: dict[int, dict], errors: list[str],
) -> list[dict]:
    """Chốt biên trang tất định: không mất, chồng hoặc đảo trang dù LLM trả lỗi."""
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
    for file_index, _file in enumerate(raw_files):
        meta = file_meta[file_index]
        page_count = meta["pageCount"]
        items = sorted(by_file[file_index], key=lambda item: (item["pageFrom"], item["pageTo"]))
        if not meta["pageBoundariesAvailable"]:
            if len(items) == 1:
                valid.append({**items[0], "pageFrom": 1, "pageTo": page_count})
            else:
                if len(items) > 1:
                    errors.append(
                        f"Không có mốc trang cho fileIndex={file_index}; đã giữ nguyên file thay vì tách theo suy đoán."
                    )
                valid.append(_fallback_segment(file_index, 1, page_count))
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
                    accepted.append(_fallback_segment(file_index, start, previous))
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
    match = _IDENTITY_NUMBER_RE.search(str(text or ""))
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
    """Giữ từng người liền nhau và ưu tiên mặt trước trước mặt sau."""
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
    ordered.extend(sorted(unknown, key=lambda item: (_face_rank(item["ocrText"]), item["order"])))
    return ordered


def _source_segment(segment: dict, page_count: int) -> dict | None:
    if segment["pageFrom"] == 1 and segment["pageTo"] == page_count:
        return None
    return {
        "fileIndex": segment["fileIndex"],
        "pageIndexes": list(range(segment["pageFrom"] - 1, segment["pageTo"])),
    }


def _identity_slot(options: dict | None) -> tuple[int, str]:
    """Lấy đúng dòng giấy tờ tùy thân từ DOM; chỉ dùng STT 2 khi client cũ chưa gửi context."""
    components = (((options or {}).get("attachmentContext") or {}).get("components") or [])
    candidates: list[tuple[int, int, str]] = []
    for component in components:
        if not isinstance(component, dict):
            continue
        name = str(component.get("componentName") or "").strip()
        folded = _fold(name)
        score = 0
        if "ho chieu" in folded:
            score += 3
        if "can cuoc" in folded:
            score += 3
        if "chung minh nhan dan" in folded or "cmnd" in folded:
            score += 2
        if "giay to tuy than" in folded:
            score += 2
        index = _coerce_int(component.get("index"))
        if score and index and index > 0:
            candidates.append((score, index, name))
    if candidates:
        _, index, name = max(candidates, key=lambda item: (item[0], -item[1]))
        return index, name
    return _ID_SLOT_INDEX, _ID_SLOT_COMPONENT


def _identity_group_name(records: list[dict], subject_name: str = "") -> str:
    folded = _fold("\n".join(record["ocrText"] for record in records))
    has_passport = "passport" in folded or "ho chieu" in folded
    has_cccd = "can cuoc" in folded or "citizen identity" in folded or "idvnm" in folded
    has_cmnd = "chung minh nhan dan" in folded
    if has_cccd and not has_passport and not has_cmnd:
        subject = _clean_subject_name(subject_name)
        if subject:
            return normalize_document_name(f"CCCD {subject}", "Căn cước công dân")
        return "Căn cước công dân"
    if has_passport and not has_cccd and not has_cmnd:
        return "Hộ chiếu"
    if has_cmnd and not has_cccd and not has_passport:
        return "Chứng minh nhân dân"
    return _IDENTITY_LABEL


def _build_item(file: dict, segment: dict, document_name: str) -> dict:
    item = {
        "fileIndex": segment["fileIndex"],
        "fileName": str(file.get("name") or f"file-{segment['fileIndex'] + 1}"),
        "documentName": document_name,
        "componentName": document_name,
        "target": "new",
        "componentIndex": None,
        "needsAddComponent": True,
        "detectedType": document_name,
    }
    source = _source_segment(segment, segment["pageCount"])
    if source:
        item["sourceSegments"] = [source]
    return item


async def plan_ket_hon_attachments(
    files: list[FileItem], options: dict | None = None, session: dict | None = None,
) -> dict:
    omit_declaration = omits_paper_declaration(options)
    errors: list[str] = []
    raw_files = [{"name": file.name, "type": file.type, "dataUrl": file.dataUrl} for file in files]
    ocr_pairs = [(index, file) for index, file in enumerate(raw_files) if file.get("type") in _OCR_TYPES]

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file([file for _, file in ocr_pairs]) if ocr_pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    # Ghép theo vị trí đầu vào, không theo tên file; hai file trùng tên vẫn giữ hai OCR độc lập.
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
        except Exception as exc:  # noqa: BLE001 - fallback giữ đủ file, không gán bừa thành CCCD
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)
    segments = _validated_segments(raw_segments, raw_files, file_meta, errors)

    attachments: list[dict] = []
    classified: list[dict] = []
    identity_records: list[dict] = []
    identity_insert_at: int | None = None
    used_names: set[str] = set()
    slot = _identity_slot(options)

    for order, raw_segment in enumerate(segments):
        file_index = raw_segment["fileIndex"]
        file = raw_files[file_index]
        segment = {**raw_segment, "pageCount": file_meta[file_index]["pageCount"]}
        ocr_text = _segment_text(segment, page_text_by_file, full_text_by_file)
        doc_type = segment["type"]
        # Chỉ nâng fallback other thành loại chuyên biệt khi OCR có tiêu đề/dấu hiệu chắc chắn.
        if doc_type == "other" and not segment.get("title") and not segment.get("documentName"):
            doc_type = _rule_doc_type(ocr_text)

        # Chỉ nhánh người dùng CHỦ ĐỘNG chọn tách mới được loại trang trắng. Không suy diễn bằng
        # rule hậu xử lý: chỉ bỏ đoạn LLM đã phân loại rõ là blank_page; đoạn không chắc vẫn giữ.
        if doc_type == "blank_page":
            classified.append({
                "fileIndex": file_index,
                "fileName": file.get("name"),
                "pageFrom": segment["pageFrom"],
                "pageTo": segment["pageTo"],
                "type": doc_type,
                "documentName": "Trang trắng",
                "target": "ignored",
                "componentIndex": None,
            })
            continue
        if omit_declaration and doc_type == "marriage_declaration":
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
                "documentName": _DECLARATION_LABEL,
                "target": "ignored",
                "componentIndex": None,
            })
            continue

        if doc_type == "identity":
            document_name = _identity_group_name(
                [{"ocrText": ocr_text}], segment.get("subjectName") or "",
            )
        elif doc_type == "marriage_declaration":
            document_name = _unique_document_name(_DECLARATION_LABEL, used_names, _DECLARATION_LABEL)
        elif doc_type == "commitment":
            document_name = _unique_document_name(_COMMITMENT_LABEL, used_names, _COMMITMENT_LABEL)
        else:
            base_name = (
                segment.get("documentName") or segment.get("title") or _fallback_document_name(ocr_text)
                or file.get("name") or ""
            )
            document_name = _unique_document_name(base_name, used_names, _OTHER_LABEL)

        item = _build_item(file, segment, document_name)
        if doc_type == "identity":
            if identity_insert_at is None:
                identity_insert_at = len(attachments)
            identity_records.append({
                "item": item,
                "ocrText": ocr_text,
                "order": order,
                "subjectName": segment.get("subjectName") or "",
            })
            target, component_index = "existing", slot[0]
        else:
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
            existing_slot=slot,
            default_document_name=_IDENTITY_LABEL,
        )
        record_by_source: dict[tuple[int, tuple[int, ...] | None], dict] = {}
        for record in identity_records:
            record_sources = record["item"].get("sourceSegments") or [{
                "fileIndex": record["item"]["fileIndex"],
                "pageIndexes": None,
            }]
            for source in record_sources:
                indexes = source.get("pageIndexes")
                key = (source["fileIndex"], tuple(indexes) if isinstance(indexes, list) else None)
                record_by_source[key] = record

        used_identity_names: set[str] = set()
        final_name_by_source: dict[tuple[int, tuple[int, ...] | None], str] = {}
        for item in grouped_identities:
            sources = item.get("sourceSegments") or [{
                "fileIndex": item["fileIndex"],
                "pageIndexes": None,
            }]
            group_records: list[dict] = []
            source_keys: list[tuple[int, tuple[int, ...] | None]] = []
            for source in sources:
                indexes = source.get("pageIndexes")
                key = (source["fileIndex"], tuple(indexes) if isinstance(indexes, list) else None)
                source_keys.append(key)
                record = record_by_source.get(key)
                if record and record not in group_records:
                    group_records.append(record)

            subjects: list[str] = []
            for record in group_records:
                subject = _clean_subject_name(record.get("subjectName"))
                if subject and _fold(subject) not in {_fold(value) for value in subjects}:
                    subjects.append(subject)
            subject_name = subjects[0] if len(subjects) == 1 else ""
            base_name = _identity_group_name(group_records, subject_name)
            document_name = _unique_document_name(base_name, used_identity_names, _IDENTITY_LABEL)
            item["documentName"] = document_name
            item["detectedType"] = document_name
            if item.get("target") == "new":
                item["componentName"] = document_name
            for key in source_keys:
                final_name_by_source[key] = document_name

        for classified_item in classified:
            if classified_item.get("type") != "identity":
                continue
            file_index = classified_item["fileIndex"]
            if (
                classified_item["pageFrom"] == 1
                and classified_item["pageTo"] == file_meta[file_index]["pageCount"]
            ):
                page_indexes = None
            else:
                page_indexes = tuple(range(
                    classified_item["pageFrom"] - 1,
                    classified_item["pageTo"],
                ))
            final_name = final_name_by_source.get((file_index, page_indexes))
            if final_name:
                classified_item["documentName"] = final_name
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


plan = plan_ket_hon_attachments
