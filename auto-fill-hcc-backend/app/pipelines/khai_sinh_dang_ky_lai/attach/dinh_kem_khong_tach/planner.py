"""Giữ nguyên từng file khi đính kèm thủ tục đăng ký lại khai sinh."""

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
_PERSONAL_SUPPORTING_LABEL = "Giấy tờ cá nhân"
_AUTHORIZATION_LABEL = "Văn bản ủy quyền"
_PAPER_DECLARATION_LABEL = "Tờ khai bản giấy"
_COMMITMENT_STATEMENT_LABEL = "Bản cam đoan"
_OTHER_LABEL = "Giấy tờ đăng ký lại khai sinh"
_FALLBACK_DOCUMENT_LABEL = "Tài liệu"
_DOSSIER_LABEL = "Hồ sơ đăng ký lại khai sinh"
_MIXED_FILE_LABELS = {
    _fold("Tờ khai và bản cam đoan"),
    _fold(_DOSSIER_LABEL),
    _fold(_OTHER_LABEL),
    _fold(_PERSONAL_SUPPORTING_LABEL),
}

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


def _canonical_type(raw_type: Any, item: dict | None = None) -> str:
    raw = re.sub(r"[\s-]+", "_", str(raw_type or "").strip().lower())
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
    if raw == "personal_supporting_document" and item:
        evidence = _fold(f"{item.get('title', '')} {item.get('documentName', '')}")
        identity_names = (*_CCCD_DOCUMENT_NAMES, "chung minh nhan dan", "ho chieu")
        if any(marker in evidence for marker in identity_names):
            raw = "identity"
    return raw if raw in _ALLOWED_LLM_TYPES else "other"


def _types_from_llm_item(item: dict) -> list[str]:
    raw_types = item.get("types")
    if isinstance(raw_types, str):
        raw_types = [raw_types]
    elif not isinstance(raw_types, list):
        raw_types = [item.get("type")]
    types: list[str] = []
    for raw_type in raw_types:
        doc_type = _canonical_type(raw_type, item)
        if doc_type not in types:
            types.append(doc_type)
    return types or ["other"]


def _label_for_type(doc_type: str) -> str:
    return {
        "birth_certificate_copy": _BIRTH_CERT_COPY_LABEL,
        "identity": _IDENTITY_LABEL,
        "personal_supporting_document": _PERSONAL_SUPPORTING_LABEL,
        "authorization": _AUTHORIZATION_LABEL,
        "paper_declaration": _PAPER_DECLARATION_LABEL,
        "commitment_statement": _COMMITMENT_STATEMENT_LABEL,
        "other": _OTHER_LABEL,
    }.get(doc_type, _OTHER_LABEL)


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


def _split_ocr_pages(text: str, expected_count: int) -> list[dict]:
    """Ranh giới trang chỉ giúp LLM đọc; planner không bao giờ dùng chúng để cắt file."""
    value = str(text or "")
    matches = list(_PAGE_HEADER_RE.finditer(value))
    if not matches:
        return [{"pageNumber": 1, "ocrText": _truncate_text(value)}]

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
    ]


async def _classify_with_llm(documents: list[dict[str, Any]]) -> list[dict]:
    """Phân loại mọi file bằng một request, mỗi file chỉ có một kết quả."""
    if not documents:
        return []
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    raw = await client.chat(
        messages,
        max_tokens=max(1000, min(3200, len(documents) * 180)),
        enable_thinking=settings.agent_reasoning,
    )
    parsed = client.extract_json_block(raw)
    return parsed.get("documents", []) or []


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _validated_file_classifications(
    raw_items: list[dict],
    raw_files: list[dict],
    errors: list[str],
) -> list[dict]:
    """Co mọi phản hồi LLM về đúng một bản phân loại cho mỗi file, không bao giờ sinh đoạn trang."""
    by_file: dict[int, list[dict]] = {index: [] for index in range(len(raw_files))}
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        file_index = _coerce_int(item.get("fileIndex", item.get("index")))
        if file_index in by_file:
            by_file[file_index].append(item)

    validated: list[dict] = []
    for file_index in range(len(raw_files)):
        items = by_file[file_index]
        if len(items) > 1:
            errors.append(
                f"attachment_agent trả nhiều kết quả cho fileIndex={file_index}; đã giữ nguyên file và gộp phân loại."
            )
        types: list[str] = []
        names: list[str] = []
        for item in items:
            for doc_type in _types_from_llm_item(item):
                if doc_type not in types:
                    types.append(doc_type)
            name = str(item.get("documentName") or item.get("title") or "").strip()
            if name and _fold(name) not in {_fold(existing) for existing in names}:
                names.append(name)
        validated.append({
            "fileIndex": file_index,
            "types": types or ["other"],
            "documentName": names[0] if len(names) == 1 else "",
        })
    return validated


def _looks_like_cccd(text: str, document_name: str = "") -> bool:
    folded = _fold(text)
    folded_name = _fold(document_name)
    has_front = (
        any(marker in folded for marker in _CCCD_FRONT_TITLES)
        or bool(_CCCD_VIETNAMESE_HEADER_RE.search(text or ""))
    )
    # Một cụm "đặc điểm nhận dạng" đơn lẻ có thể do OCR rác; mặt sau phải có MRZ hoặc số định danh.
    has_back = "idvnm" in folded or (
        any(marker in folded for marker in _CCCD_BACK_TITLES)
        and bool(_CCCD_RE.search(text or ""))
    )
    return (
        has_front
        or has_back
        or any(marker in folded_name for marker in _CCCD_DOCUMENT_NAMES)
    )


def _death_document_name(text: str, document_name: str = "") -> str:
    """Sự kiện chết không được đi vào dòng giấy tờ thay thế Giấy khai sinh."""
    evidence = f"{_fold(document_name)} {_fold(text)[:1200]}"
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


def _aggregate_document_name(
    types: list[str],
    llm_name: str,
) -> str:
    """Giữ tên toàn file từ LLM; chỉ chặn tên một tài liệu con cho file hỗn hợp."""
    type_set = set(types)
    if len(type_set) == 1:
        fallback = (
            _FALLBACK_DOCUMENT_LABEL
            if types[0] == "other"
            and (not llm_name or _fold(llm_name) == _fold(_FALLBACK_DOCUMENT_LABEL))
            else _label_for_type(types[0])
        )
    else:
        fallback = _DOSSIER_LABEL if "paper_declaration" in type_set else _OTHER_LABEL
    document_name = normalize_document_name(llm_name, fallback)
    if len(type_set) > 1 and _fold(document_name) not in _MIXED_FILE_LABELS:
        # types đã xác nhận đây là file hỗn hợp: tên riêng của một giấy tờ con không thể đại diện cả file.
        return fallback
    return document_name


def _route_for_types(types: list[str]) -> tuple[str, int | None, str]:
    categories: set[int | str] = set()
    if "birth_certificate_copy" in types:
        categories.add(2)
    if any(doc_type in {"identity", "personal_supporting_document"} for doc_type in types):
        categories.add(3)
    if "authorization" in types:
        categories.add(5)
    if any(doc_type in {"paper_declaration", "commitment_statement", "other"} for doc_type in types):
        categories.add("new")
    if categories == {2}:
        return "existing", 2, _ROW_2_COMPONENT
    if categories == {3}:
        return "existing", 3, _ROW_3_COMPONENT
    if categories == {5}:
        return "existing", 5, _ROW_5_COMPONENT
    return "new", None, ""


def _group_same_cccd_faces(records: list[dict]) -> list[list[dict]]:
    """Chỉ ghép hai file là mặt trước/mặt sau của đúng cùng một số CCCD."""
    candidates = [
        record
        for record in records
        if record["isCccd"] and set(record["types"]) == {"identity"} and _face_rank(record["ocrText"]) < 2
    ]
    front_people = []
    for record in candidates:
        if _face_rank(record["ocrText"]) != 0:
            continue
        number = _identity_number(record["ocrText"])
        if number and number not in front_people:
            front_people.append(number)

    by_person: dict[str, dict[int, list[dict]]] = {}
    for record in candidates:
        person = _identity_person(record["ocrText"], front_people)
        if not person:
            continue
        rank = _face_rank(record["ocrText"])
        by_person.setdefault(person, {0: [], 1: []})[rank].append(record)

    pair_by_order: dict[int, list[dict]] = {}
    consumed: set[int] = set()
    for faces in by_person.values():
        # Có bản trùng hoặc thiếu mặt thì không tự suy diễn ghép để tránh trộn sai chủ thể/thẻ.
        if len(faces[0]) != 1 or len(faces[1]) != 1:
            continue
        pair = [faces[0][0], faces[1][0]]
        pair.sort(key=lambda record: (_face_rank(record["ocrText"]), record["order"]))
        first_order = min(record["order"] for record in pair)
        pair_by_order[first_order] = pair
        consumed.update(record["order"] for record in pair)

    groups: list[list[dict]] = []
    for record in records:
        if record["order"] in pair_by_order:
            groups.append(pair_by_order[record["order"]])
        elif record["order"] not in consumed:
            groups.append([record])
    return groups


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

    full_text_by_file: dict[int, str] = {}
    page_count_by_file: dict[int, int] = {}
    llm_files: list[dict] = []
    for file_index, file in enumerate(raw_files):
        text = str((ocr_by_index.get(file_index) or {}).get("text") or "")
        full_text_by_file[file_index] = text
        page_count = _pdf_page_count(file)
        pages = _split_ocr_pages(text, page_count)
        page_count = max(page_count, max((int(page["pageNumber"]) for page in pages), default=1))
        page_count_by_file[file_index] = page_count
        llm_files.append({"fileIndex": file_index, "pageCount": page_count, "pages": pages})

    started = time.monotonic()
    raw_classifications: list[dict] = []
    if llm_files:
        try:
            raw_classifications = await _classify_with_llm(llm_files)
        except Exception as exc:  # noqa: BLE001 - fallback vẫn giữ đủ mọi file
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)
    classifications = _validated_file_classifications(raw_classifications, raw_files, errors)

    records: list[dict] = []
    for order, classification in enumerate(classifications):
        file_index = classification["fileIndex"]
        text = full_text_by_file[file_index]
        llm_name = classification["documentName"]
        types = list(classification["types"])
        page_count = page_count_by_file[file_index]
        ocr_death_name = _death_document_name(text)
        death_name = ocr_death_name or _death_document_name("", llm_name)
        if ocr_death_name and page_count == 1:
            # Tiêu đề khai tử rõ trên file một trang là bằng chứng tất định, không giữ type bị LLM gán lệch.
            types = ["other"]
            llm_name = ocr_death_name
        elif death_name:
            types = [doc_type for doc_type in types if doc_type != "birth_certificate_copy"]
            if "other" not in types:
                types.append("other")
        is_cccd = _looks_like_cccd(text, llm_name)
        if is_cccd and page_count == 1 and set(types) <= {"identity", "other"}:
            # File CCCD độc lập không trở thành hỗn hợp chỉ vì LLM trả thêm other.
            types = ["identity"]
            if not any(marker in _fold(llm_name) for marker in _CCCD_DOCUMENT_NAMES):
                llm_name = _IDENTITY_LABEL
        elif is_cccd and "identity" not in types:
            types.insert(0, "identity")
        if not types:
            types = ["other"]
        document_name = _aggregate_document_name(
            types,
            llm_name,
        )
        records.append({
            "order": order,
            "fileIndex": file_index,
            "fileName": raw_files[file_index].get("name"),
            "ocrText": text,
            "types": types,
            "isCccd": is_cccd,
            "documentName": document_name,
        })

    groups = _group_same_cccd_faces(records)
    group_infos: list[dict] = []
    for group_order, group in enumerate(groups):
        merged_faces = len(group) == 2
        types: list[str] = []
        for record in group:
            for doc_type in record["types"]:
                if doc_type not in types:
                    types.append(doc_type)
        target, component_index, component_name = _route_for_types(types)
        group_infos.append({
            "order": group_order,
            "records": group,
            "types": types,
            "isCccd": all(record["isCccd"] for record in group),
            "mergedFaces": merged_faces,
            # Hai mặt đã được ghép đúng số CCCD; giữ tên có chủ thể mà LLM đọc từ mặt trước.
            "baseName": group[0]["documentName"],
            "target": target,
            "componentIndex": component_index,
            "componentName": component_name,
        })

    # Mỗi ô có sẵn chỉ nhận một file. Riêng STT 3 ưu tiên CCCD trước giấy tờ hỗ trợ khác.
    winners: dict[int, int] = {}
    for slot in (2, 3, 5):
        candidates = [info for info in group_infos if info["componentIndex"] == slot]
        if not candidates:
            continue
        if slot == 3:
            candidates.sort(key=lambda info: (not info["isCccd"], info["order"]))
        winners[slot] = candidates[0]["order"]

    used_names: set[str] = set()
    attachments: list[dict] = []
    result_by_record_order: dict[int, tuple[str, int | None, str]] = {}
    for info in group_infos:
        fallback_name = (
            _FALLBACK_DOCUMENT_LABEL
            if _fold(info["baseName"]) == _fold(_FALLBACK_DOCUMENT_LABEL)
            else _OTHER_LABEL
        )
        document_name = _unique_document_name(info["baseName"], used_names, fallback_name)
        target = info["target"]
        component_index = info["componentIndex"]
        component_name = info["componentName"]
        if target == "existing" and winners.get(component_index) != info["order"]:
            target = "new"
            component_index = None
            component_name = document_name
        elif target == "new":
            component_name = document_name

        first = info["records"][0]
        item = {
            "fileIndex": first["fileIndex"],
            "fileName": str(first["fileName"] or f"file-{first['fileIndex'] + 1}"),
            "documentName": document_name,
            "componentName": component_name,
            "target": target,
            "componentIndex": component_index,
            "needsAddComponent": target == "new",
            "detectedType": document_name,
        }
        if info["mergedFaces"]:
            item["sourceFileIndexes"] = [record["fileIndex"] for record in info["records"]]
        attachments.append(item)
        for record in info["records"]:
            result_by_record_order[record["order"]] = (target, component_index, document_name)

    classified = []
    for record in records:
        target, component_index, document_name = result_by_record_order[record["order"]]
        classified.append({
            "fileIndex": record["fileIndex"],
            "fileName": record["fileName"],
            "pageFrom": 1,
            "pageTo": page_count_by_file[record["fileIndex"]],
            "types": record["types"],
            "type": record["types"][0],
            "documentName": document_name,
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


plan = plan_dang_ky_lai_khai_sinh_attachments
