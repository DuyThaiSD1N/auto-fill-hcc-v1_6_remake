"""Phân đoạn và phân loại tài liệu khi bật tách hồ sơ đăng ký giám hộ."""

import base64
import re
import time
from typing import Any

import fitz

from app.config import settings
from app.pipelines._shared import fold, normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_ALLOWED_TYPES = {
    "guardian_appointment", "guardian_condition", "authorization", "paper_declaration",
    "identity", "marital_status_certificate", "skip", "blank_page", "other",
}

_APPOINTMENT_LABEL = "Văn bản thỏa thuận cử người giám hộ"
_CONDITION_LABEL = "Giấy tờ chứng minh điều kiện giám hộ"
_AUTHORIZATION_LABEL = "Văn bản ủy quyền"
_DECLARATION_LABEL = "Tờ khai đăng ký giám hộ bản giấy"
_IDENTITY_LABEL = "Căn cước công dân"
_MARITAL_STATUS_LABEL = "Giấy xác nhận tình trạng hôn nhân"
_OTHER_LABEL = "Tài liệu đăng ký giám hộ"
_BLANK_LABEL = "Trang trắng"

_ROW_BY_TYPE = {
    "guardian_appointment": (2, "- Văn bản cử người giám hộ theo quy định của Bộ luật Dân sự"),
    "guardian_condition": (
        3,
        "- Giấy tờ chứng minh điều kiện giám hộ đương nhiên theo quy định của Bộ luật Dân sự",
    ),
    "identity": (
        3,
        "- Giấy tờ chứng minh điều kiện giám hộ đương nhiên theo quy định của Bộ luật Dân sự",
    ),
    "authorization": (
        4,
        "- Văn bản ủy quyền theo quy định của pháp luật trong trường hợp ủy quyền",
    ),
}

_PAGE_HEADER_RE = re.compile(
    r"(?im)^[\t \u2500-\u257f-]*(?:trang|page)\s+(\d+)\s*/\s*(\d+)"
    r"[\t \u2500-\u257f-]*$"
)
_CCCD_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")
_IDENTITY_DIRECT_MARKERS = (
    "can cuoc cong dan", "the can cuoc", "citizen identity card", "identity card",
    "giay chung minh nhan dan", "chung minh nhan dan", "passport", "ho chieu", "idvnm",
)
_IDENTITY_BACK_GROUPS = (
    ("dac diem nhan dang", "personal identification"),
    ("van tay", "ngon tro", "left index finger", "right index finger"),
    ("cuc truong cuc canh sat", "director general", "quan ly hanh chinh ve trat tu xa hoi"),
)


def _truncate(text: str, limit: int = 1800) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    return value if len(value) <= limit else value[:limit] + "..."


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
    except Exception:  # noqa: BLE001 - test dùng data URL giả; OCR header vẫn cho biết số trang
        return 1


def _split_ocr_pages(text: str, expected_count: int) -> tuple[list[dict], bool]:
    value = str(text or "")
    matches = list(_PAGE_HEADER_RE.finditer(value))
    if not matches:
        return [{"pageNumber": 1, "pageTo": expected_count, "ocrText": _truncate(value)}], expected_count == 1

    declared_total = expected_count
    pages: dict[int, str] = {}
    for position, match in enumerate(matches):
        page_number = int(match.group(1))
        declared_total = max(declared_total, int(match.group(2)))
        end = matches[position + 1].start() if position + 1 < len(matches) else len(value)
        pages[page_number] = value[match.end():end].strip()
    return [
        {"pageNumber": number, "ocrText": _truncate(pages.get(number, ""))}
        for number in range(1, max(1, declared_total) + 1)
    ], True


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _canonical_type(value: Any) -> str:
    raw = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    aliases = {
        "cccd": "identity", "cmnd": "identity", "id": "identity",
        "condition": "guardian_condition", "commitment": "guardian_condition",
        "birth_certificate": "guardian_condition", "population_database": "guardian_condition",
        "marital_status": "marital_status_certificate",
        "declaration": "paper_declaration", "irrelevant": "skip",
    }
    raw = aliases.get(raw, raw)
    return raw if raw in _ALLOWED_TYPES else "other"


def _clean_subject(value: Any) -> str:
    subject = re.sub(r"\s+", " ", str(value or "")).strip(" :-")
    if fold(subject) in {"", "ho ten", "ho va ten", "full name", "khong ro"}:
        return ""
    return subject[:40].strip()


def _has_identity_evidence(text: str) -> bool:
    folded = fold(text)
    if any(marker in folded for marker in _IDENTITY_DIRECT_MARKERS):
        return True
    signals = sum(1 for group in _IDENTITY_BACK_GROUPS if any(marker in folded for marker in group))
    if _CCCD_RE.search(str(text or "")):
        signals += 1
    return signals >= 2


def _rule_segment(text: str, proposed_subject: str = "") -> tuple[str, str] | None:
    """Tiêu đề rõ ràng thắng dự đoán LLM; tránh ảnh CSDL bị đổi thành CCCD."""
    folded = fold(text)
    if not folded or folded in {"trang trang", "trang trong", "markdown"}:
        return "blank_page", _BLANK_LABEL
    if "to khai dang ky giam ho" in folded:
        return "paper_declaration", _DECLARATION_LABEL
    if "giay xac nhan tinh trang hon nhan" in folded:
        return "marital_status_certificate", _MARITAL_STATUS_LABEL
    if any(marker in folded for marker in (
        "van ban thoa thuan cu nguoi giam ho", "van ban cu nguoi giam ho",
        "cu nguoi co ten duoi day", "lam nguoi giam ho cho nguoi co ten duoi day",
    )):
        return "guardian_appointment", _APPOINTMENT_LABEL
    if any(marker in folded for marker in (
        "van ban uy quyen", "giay uy quyen", "ben uy quyen", "ben duoc uy quyen",
    )):
        return "authorization", _AUTHORIZATION_LABEL
    if _has_identity_evidence(text):
        subject = _clean_subject(proposed_subject)
        return "identity", f"CCCD {subject}" if subject else _IDENTITY_LABEL
    if "ban cam doan" in folded and any(marker in folded for marker in (
        "nang luc hanh vi dan su", "du dieu kien giam ho", "khong bi truy cuu trach nhiem hinh su",
    )):
        return "guardian_condition", "Bản cam đoan đủ điều kiện giám hộ"
    if any(marker in folded for marker in (
        "giay chung nhan quyen su dung dat", "so vao so cap gcn", "thua dat so",
    )):
        return "guardian_condition", "Giấy chứng nhận quyền sử dụng đất"
    if "giay khai sinh" in folded:
        return "guardian_condition", "Giấy khai sinh người được giám hộ"
    if any(marker in folded for marker in (
        "thong tin tra cuu co so du lieu dan cu", "xac thuc voi csdlqg ve dan cu",
        "thong tin ca nhan", "thong tin gia dinh",
    )):
        return "guardian_condition", "Trích xuất cơ sở dữ liệu dân cư"
    return None


async def _classify_with_llm(documents: list[dict[str, Any]]) -> list[dict]:
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


def _fallback_segment(file_index: int, page_from: int, page_to: int) -> dict:
    return {
        "fileIndex": file_index,
        "pageFrom": page_from,
        "pageTo": page_to,
        "type": "other",
        "title": "",
        "documentName": "",
        "subjectName": "",
    }


def _validated_segments(
    raw_segments: list[dict], raw_files: list[dict], file_meta: dict[int, dict], errors: list[str],
) -> list[dict]:
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
            errors.append(f"Phân đoạn fileIndex={file_index} không hợp lệ: {page_from}-{page_to}.")
            continue
        by_file[file_index].append({
            "fileIndex": file_index,
            "pageFrom": page_from,
            "pageTo": page_to,
            "type": _canonical_type(raw.get("type", raw.get("docType"))),
            "title": str(raw.get("title") or "").strip(),
            "documentName": str(raw.get("documentName") or "").strip(),
            "subjectName": _clean_subject(raw.get("subjectName")),
        })

    valid: list[dict] = []
    for file_index, _file in enumerate(raw_files):
        meta = file_meta[file_index]
        page_count = meta["pageCount"]
        items = sorted(by_file[file_index], key=lambda item: (item["pageFrom"], item["pageTo"]))
        if not meta["pageBoundariesAvailable"]:
            first = items[0] if items else _fallback_segment(file_index, 1, page_count)
            valid.append({**first, "pageFrom": 1, "pageTo": page_count})
            continue

        occupied: set[int] = set()
        accepted: list[dict] = []
        for item in items:
            pages = set(range(item["pageFrom"], item["pageTo"] + 1))
            if occupied & pages:
                errors.append(
                    f"Phân đoạn fileIndex={file_index} chồng trang; bỏ {item['pageFrom']}-{item['pageTo']}."
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


def _segment_text(segment: dict, page_text: dict[int, dict[int, str]], full_text: dict[int, str]) -> str:
    pages = page_text.get(segment["fileIndex"]) or {}
    if not pages:
        return full_text.get(segment["fileIndex"], "")
    return "\n".join(
        pages.get(page, "") for page in range(segment["pageFrom"], segment["pageTo"] + 1)
    ).strip()


def _label_for_type(doc_type: str) -> str:
    return {
        "guardian_appointment": _APPOINTMENT_LABEL,
        "guardian_condition": _CONDITION_LABEL,
        "authorization": _AUTHORIZATION_LABEL,
        "paper_declaration": _DECLARATION_LABEL,
        "identity": _IDENTITY_LABEL,
        "marital_status_certificate": _MARITAL_STATUS_LABEL,
        "skip": _OTHER_LABEL,
        "blank_page": _BLANK_LABEL,
    }.get(doc_type, _OTHER_LABEL)


def _unique_name(base: str, used: set[str], fallback: str) -> str:
    normalized = normalize_document_name(base, fallback)
    key = fold(normalized)
    if key and key not in used:
        used.add(key)
        return normalized
    stem = normalized[:45].strip() or fallback[:45].strip() or _OTHER_LABEL
    suffix = 2
    while True:
        candidate = f"{stem} {suffix}"[:50].strip()
        key = fold(candidate)
        if key not in used:
            used.add(key)
            return candidate
        suffix += 1


def _source_segment(segment: dict, page_count: int) -> dict | None:
    if segment["pageFrom"] == 1 and segment["pageTo"] == page_count:
        return None
    return {
        "fileIndex": segment["fileIndex"],
        "pageIndexes": list(range(segment["pageFrom"] - 1, segment["pageTo"])),
    }


def _route(
    doc_type: str, document_name: str, used_slots: set[int],
) -> tuple[str, int | None, str, bool]:
    row = _ROW_BY_TYPE.get(doc_type)
    if row is None:
        return "new", None, document_name, True
    component_index, component_name = row
    if component_index in used_slots:
        return "new", None, document_name, True
    used_slots.add(component_index)
    return "existing", component_index, component_name, False


async def plan(
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
    for raw_index, result in ocr_by_index.items():
        if result.get("error"):
            errors.append(f"OCR fileIndex={raw_index} {raw_files[raw_index].get('name')}: {result['error']}")

    file_meta: dict[int, dict] = {}
    page_text: dict[int, dict[int, str]] = {}
    full_text: dict[int, str] = {}
    llm_files: list[dict] = []
    for file_index, file in enumerate(raw_files):
        text = str((ocr_by_index.get(file_index) or {}).get("text") or "")
        full_text[file_index] = text
        page_count = _pdf_page_count(file)
        pages, boundaries = _split_ocr_pages(text, page_count)
        page_count = max(page_count, max((int(page.get("pageNumber") or 1) for page in pages), default=1))
        file_meta[file_index] = {"pageCount": page_count, "pageBoundariesAvailable": boundaries}
        page_text[file_index] = {
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
        except Exception as exc:  # noqa: BLE001 - fallback vẫn giữ đủ trang/file
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)
    segments = _validated_segments(raw_segments, raw_files, file_meta, errors)

    attachments: list[dict] = []
    classified: list[dict] = []
    used_names: set[str] = set()
    used_slots: set[int] = set()

    for segment in segments:
        file_index = segment["fileIndex"]
        file = raw_files[file_index]
        text = _segment_text(segment, page_text, full_text)
        rule = _rule_segment(text, segment.get("subjectName") or "")
        doc_type, rule_name = rule if rule else (segment["type"], "")
        fallback = _label_for_type(doc_type)
        proposed_name = segment.get("documentName") or segment.get("title") or ""
        if rule_name == "Trích xuất cơ sở dữ liệu dân cư" and fold(proposed_name).startswith("trich xuat"):
            base_name = proposed_name
        else:
            base_name = rule_name or proposed_name or fallback

        if doc_type in {"skip", "blank_page"}:
            document_name = _MARITAL_STATUS_LABEL if doc_type == "skip" else _BLANK_LABEL
            classified.append({
                "fileIndex": file_index,
                "fileName": file.get("name"),
                "pageFrom": segment["pageFrom"],
                "pageTo": segment["pageTo"],
                "type": doc_type,
                "documentName": document_name,
                "target": "ignored",
                "componentIndex": None,
            })
            continue

        document_name = _unique_name(base_name, used_names, fallback)
        target, component_index, component_name, needs_add = _route(doc_type, document_name, used_slots)
        item = {
            "fileIndex": file_index,
            "fileName": str(file.get("name") or f"file-{file_index + 1}"),
            "documentName": document_name,
            "componentName": component_name,
            "target": target,
            "componentIndex": component_index,
            "needsAddComponent": needs_add,
            "detectedType": document_name,
        }
        source = _source_segment(segment, file_meta[file_index]["pageCount"])
        if source:
            item["sourceSegments"] = [source]
        attachments.append(item)
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
            "ocrDocuments": [raw_files[index]["name"] for index, result in ocr_by_index.items() if result.get("text")],
            "llmDocuments": [file["name"] for file in raw_files],
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
