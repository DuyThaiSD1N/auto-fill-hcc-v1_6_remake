"""Đính kèm bước 3 cho thủ tục "Đăng ký việc nuôi con nuôi trong nước" (mã 2.001263).

Thủ tục chỉ đính kèm, không điền bước Kê khai. Bảng thành phần hồ sơ trên cổng:
  STT1 - Bản sao Hộ chiếu, Thẻ căn cước... của người nhận con nuôi.
  STT2 - Giấy khám sức khỏe của người nhận con nuôi.
  STT3 - Văn bản xác nhận hoàn cảnh gia đình, tình trạng chỗ ở, điều kiện kinh tế.
  STT4 - Văn bản xác nhận tình trạng hôn nhân (giấy chứng nhận kết hôn...).
  STT5 - Đơn xin nhận con nuôi: tờ khai online ("Khai tờ khai"), không đính file.
  STT6 - Đơn đăng ký nhu cầu nhận trẻ em: tờ khai online, không đính file.

Giấy tờ phía trẻ (giấy khai sinh, giấy khám sức khỏe, ảnh) và của cha/mẹ đẻ (CCCD, văn bản
đồng ý), đơn bản giấy, giấy tờ khác -> thêm thành phần hồ sơ mới.

Hai vợ chồng cùng nhận con nuôi nên một dòng có sẵn thường nhận NHIỀU file (2 CCCD, 2 giấy khám
sức khỏe). Mỗi input có sẵn chỉ đính một lần được nên các file cùng nhóm gộp thành MỘT item mang
`sourceFileIndexes` để FE gộp PDF — không đẩy người thứ hai sang dòng mới như planner hộ tịch khác.
"""

import re
import time
from datetime import date
from typing import Any

from app.config import settings
from app.pipelines._shared import fold, normalize_document_name
from app.pipelines._shared.identity_merge import merge_identity_records
from app.pipelines.nuoi_con_nuoi_trong_nuoc.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_IMAGE_TYPES = {"image/jpeg", "image/png", "image/jpg", "image/webp"}

_DOC_ADOPTER_IDENTITY = "adopter_identity"
_DOC_ADOPTER_HEALTH = "adopter_health"
_DOC_FAMILY_CIRCUMSTANCE = "family_circumstance"
_DOC_MARITAL_STATUS = "marital_status"
_DOC_APPLICATION = "adoption_application"
_DOC_CHILD_BIRTH = "child_birth_certificate"
_DOC_CHILD_HEALTH = "child_health"
_DOC_CHILD_PHOTO = "child_photo"
_DOC_BIRTH_PARENT_IDENTITY = "birth_parent_identity"
_DOC_BIRTH_PARENT_DOCUMENT = "birth_parent_document"
_DOC_OTHER = "other"
_DOC_SKIP = "skip"

_ALLOWED_DOC_TYPES = {
    _DOC_ADOPTER_IDENTITY,
    _DOC_ADOPTER_HEALTH,
    _DOC_FAMILY_CIRCUMSTANCE,
    _DOC_MARITAL_STATUS,
    _DOC_APPLICATION,
    _DOC_CHILD_BIRTH,
    _DOC_CHILD_HEALTH,
    _DOC_CHILD_PHOTO,
    _DOC_BIRTH_PARENT_IDENTITY,
    _DOC_BIRTH_PARENT_DOCUMENT,
    _DOC_OTHER,
    _DOC_SKIP,
}

# Nhãn nhận dạng dòng có sẵn: FE khớp theo substring đã fold nên chỉ lấy đoạn đầu ổn định của câu.
_EXISTING_ROWS: dict[str, tuple[int, str]] = {
    _DOC_ADOPTER_IDENTITY: (1, "Bản sao Hộ chiếu, Thẻ căn cước hoặc giấy tờ có giá trị thay thế"),
    _DOC_ADOPTER_HEALTH: (2, "Giấy khám sức khỏe do bệnh viện đa khoa hoặc phòng khám đa khoa"),
    _DOC_FAMILY_CIRCUMSTANCE: (3, "Văn bản xác nhận hoàn cảnh gia đình, tình trạng chỗ ở, điều kiện kinh tế"),
    _DOC_MARITAL_STATUS: (4, "Văn bản xác nhận tình trạng hôn nhân"),
}

_LABELS = {
    _DOC_ADOPTER_IDENTITY: "Căn cước của người nhận con nuôi",
    _DOC_ADOPTER_HEALTH: "Giấy khám sức khỏe người nhận con nuôi",
    _DOC_FAMILY_CIRCUMSTANCE: "Văn bản xác nhận hoàn cảnh gia đình",
    _DOC_MARITAL_STATUS: "Giấy chứng nhận kết hôn",
    _DOC_APPLICATION: "Đơn xin nhận con nuôi bản giấy",
    _DOC_CHILD_BIRTH: "Giấy khai sinh của trẻ",
    _DOC_CHILD_HEALTH: "Giấy khám sức khỏe của trẻ",
    _DOC_CHILD_PHOTO: "Ảnh của trẻ",
    _DOC_BIRTH_PARENT_IDENTITY: "Căn cước của cha mẹ đẻ",
    _DOC_BIRTH_PARENT_DOCUMENT: "Giấy tờ của cha mẹ đẻ",
    _DOC_OTHER: "Tài liệu nhận con nuôi",
    _DOC_SKIP: "Bỏ qua",
}

# Các nhóm gộp mọi file thành một thành phần (kể cả dòng mới). "other" giữ từng file riêng vì mỗi
# file là một loại giấy tờ khác nhau, gộp lại sẽ mất tên tài liệu.
_GROUPED_TYPES = set(_EXISTING_ROWS) | {
    _DOC_APPLICATION,
    _DOC_CHILD_BIRTH,
    _DOC_CHILD_HEALTH,
    _DOC_CHILD_PHOTO,
    _DOC_BIRTH_PARENT_IDENTITY,
    _DOC_BIRTH_PARENT_DOCUMENT,
}
_IDENTITY_TYPES = {_DOC_ADOPTER_IDENTITY, _DOC_BIRTH_PARENT_IDENTITY}

_DOC_ORDER = [
    _DOC_ADOPTER_IDENTITY,
    _DOC_ADOPTER_HEALTH,
    _DOC_FAMILY_CIRCUMSTANCE,
    _DOC_MARITAL_STATUS,
    _DOC_APPLICATION,
    _DOC_CHILD_BIRTH,
    _DOC_CHILD_HEALTH,
    _DOC_CHILD_PHOTO,
    _DOC_BIRTH_PARENT_IDENTITY,
    _DOC_BIRTH_PARENT_DOCUMENT,
]

_ADULT_AGE = 18
_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})\s*[/.-]\s*(\d{1,2})\s*[/.-]\s*((?:19|20)\d{2})(?!\d)")


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _has_any(haystack: str, needles: tuple[str, ...]) -> bool:
    return any(needle in haystack for needle in needles)


def _normalize_doc_type(value: str) -> str:
    raw = str(value or "").strip()
    if raw in _ALLOWED_DOC_TYPES:
        return raw
    text = fold(raw)
    if not text or text == "other":
        return _DOC_OTHER
    if _has_any(text, ("skip", "irrelevant", "bo qua")):
        return _DOC_SKIP
    return _DOC_OTHER


# ---------------------------------------------------------------------------
# Đọc họ tên / ngày sinh từ OCR để phân vai (cha mẹ nuôi vs cha mẹ đẻ vs trẻ)
# ---------------------------------------------------------------------------

def _clean_name(value: str) -> str:
    text = fold(value)
    text = re.split(r"\s(?:ngay|sinh|gioi tinh|date|sex|nam sinh|dan toc|quoc tich)\b", text)[0]
    text = re.sub(r"[^a-z\s]", " ", text)
    words = [w for w in text.split() if w]
    if not 2 <= len(words) <= 6:
        return ""
    return " ".join(words)


def _value_after_label(lines: list[str], label_re: re.Pattern) -> str:
    """Giá trị nằm sau nhãn trên cùng dòng, hoặc ở dòng kế tiếp nếu nhãn đứng riêng."""
    for pos, line in enumerate(lines):
        folded = fold(line)
        match = label_re.search(folded)
        if not match:
            continue
        rest = folded[match.end():]
        rest = re.sub(r"^[\s:/.\-]*(?:full name)?[\s:/.\-]*", "", rest)
        name = _clean_name(rest)
        if not name and pos + 1 < len(lines):
            name = _clean_name(lines[pos + 1])
        if name:
            return name
    return ""


_IDENTITY_NAME_RE = re.compile(r"(?:ho, chu dem va ten(?: khai sinh)?|ho va ten|full name)")
_MOTHER_NAME_RE = re.compile(r"(?:ho, chu dem(?:,| va) ten (?:nguoi )?me|ho va ten (?:nguoi )?me|^me\b)")
_FATHER_NAME_RE = re.compile(r"(?:ho, chu dem(?:,| va) ten (?:nguoi )?cha|ho va ten (?:nguoi )?cha|^cha\b)")
_CHILD_NAME_RE = re.compile(r"^(?:ho, chu dem(?:,| va) ten|ho va ten)\s*:")


def _lines(text: str) -> list[str]:
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


def _identity_holder_name(text: str) -> str:
    return _value_after_label(_lines(text), _IDENTITY_NAME_RE)


def _birth_certificate_names(text: str) -> dict[str, str]:
    lines = _lines(text)
    return {
        "mother": _value_after_label(lines, _MOTHER_NAME_RE),
        "father": _value_after_label(lines, _FATHER_NAME_RE),
        "child": _value_after_label(lines, _CHILD_NAME_RE),
    }


def _birth_year(text: str) -> int | None:
    folded = fold(text)
    anchor = re.search(r"(?:ngay, thang, nam sinh|ngay sinh|sinh ngay|date of birth|nam sinh)", folded)
    scope = folded[anchor.end():anchor.end() + 60] if anchor else ""
    match = _DATE_RE.search(scope)
    if match:
        return int(match.group(3))
    year = re.search(r"(?<!\d)((?:19|20)\d{2})(?!\d)", scope)
    return int(year.group(1)) if year else None


# ---------------------------------------------------------------------------
# Rule phân loại theo OCR
# ---------------------------------------------------------------------------

def _looks_like_identity(haystack: str) -> bool:
    if _has_any(
        haystack,
        (
            "can cuoc cong dan",
            "the can cuoc",
            "citizen identity",
            "identity card",
            "idvnm",
            "dac diem nhan dang",
            "chung minh nhan dan",
            "ho chieu",
            "passport",
        ),
    ):
        return True
    return "so dinh danh ca nhan" in haystack and _has_any(
        haystack, ("co gia tri den", "date of expiry", "noi thuong tru", "place of residence", "que quan")
    )


def _rule_doc_type(text: str, file_type: str = "") -> str:
    """Nhóm giấy tờ TẤT ĐỊNH theo OCR. Identity/khám sức khỏe trả nhóm phía người nhận con nuôi;
    phân vai trẻ / cha mẹ đẻ làm ở bước sau khi đã đọc đủ bộ hồ sơ."""
    haystack = fold(text)
    if len(re.sub(r"[^a-z0-9]", "", haystack)) < 20:
        return _DOC_CHILD_PHOTO if file_type in _IMAGE_TYPES else ""

    # Đơn nhắc tới đủ thứ (kết hôn, sức khỏe, hoàn cảnh) nên phải xét trước.
    if _has_any(haystack, ("don xin nhan con nuoi", "don dang ky nhu cau nhan tre em")):
        return _DOC_APPLICATION
    if _has_any(haystack, ("dong y cho con lam con nuoi", "y kien cua cha me de", "y kien cua cha, me de")):
        return _DOC_BIRTH_PARENT_DOCUMENT
    if "giay kham suc khoe" in haystack or "kham suc khoe dinh ky" in haystack:
        return _DOC_ADOPTER_HEALTH
    if _has_any(haystack, ("hoan canh gia dinh", "tinh trang cho o", "dieu kien kinh te")):
        return _DOC_FAMILY_CIRCUMSTANCE
    if _has_any(
        haystack,
        (
            "giay chung nhan ket hon",
            "trich luc ket hon",
            "dang ky ket hon",
            "xac nhan tinh trang hon nhan",
        ),
    ):
        return _DOC_MARITAL_STATUS
    # Giấy khai sinh đời mới cũng in "số định danh cá nhân" -> xét trước identity.
    if _has_any(haystack, ("giay khai sinh", "trich luc khai sinh", "giay chung sinh", "noi dang ky khai sinh")):
        return _DOC_CHILD_BIRTH
    if _looks_like_identity(haystack):
        return _DOC_ADOPTER_IDENTITY
    return ""


def _is_child_health(text: str, child_names: set[str], today: date) -> bool:
    haystack = fold(text)
    if _has_any(haystack, ("chua du 18 tuoi", "duoi 18 tuoi", "nguoi chua thanh nien", "kham suc khoe tre em")):
        return True
    holder = _identity_holder_name(text)
    if holder and holder in child_names:
        return True
    year = _birth_year(text)
    return year is not None and today.year - year < _ADULT_AGE


def _assign_roles(resolved: list[dict], today: date) -> None:
    """Phân vai sau khi có đủ bộ hồ sơ: đối chiếu họ tên trên giấy khai sinh của trẻ."""
    parent_names: set[str] = set()
    child_names: set[str] = set()
    for entry in resolved:
        if entry["docType"] != _DOC_CHILD_BIRTH:
            continue
        names = _birth_certificate_names(entry["text"])
        parent_names.update(n for n in (names["mother"], names["father"]) if n)
        if names["child"]:
            child_names.add(names["child"])

    for entry in resolved:
        doc_type = entry["docType"]
        llm_type = entry["llmType"]
        if doc_type in _IDENTITY_TYPES:
            holder = _identity_holder_name(entry["text"])
            if holder and holder in parent_names:
                entry["docType"] = _DOC_BIRTH_PARENT_IDENTITY
            elif holder and parent_names:
                # Đọc được tên cha mẹ đẻ trên giấy khai sinh mà không trùng -> người nhận con nuôi.
                entry["docType"] = _DOC_ADOPTER_IDENTITY
            elif llm_type in _IDENTITY_TYPES:
                # Không đối chiếu được bằng tên (mặt sau thẻ, thiếu giấy khai sinh) -> tin LLM.
                entry["docType"] = llm_type
        elif doc_type in {_DOC_ADOPTER_HEALTH, _DOC_CHILD_HEALTH}:
            if _is_child_health(entry["text"], child_names, today):
                entry["docType"] = _DOC_CHILD_HEALTH
            elif llm_type == _DOC_CHILD_HEALTH and not _birth_year(entry["text"]):
                entry["docType"] = _DOC_CHILD_HEALTH

    # Mặt sau thẻ không in họ tên: đi theo vai của mặt trước có cùng số định danh (MRZ nhúng số).
    role_by_number: dict[str, str] = {}
    for entry in resolved:
        if entry["docType"] in _IDENTITY_TYPES and _holder_has_name(entry):
            number = _identity_number(entry["text"])
            if number:
                role_by_number[number] = entry["docType"]
    for entry in resolved:
        if entry["docType"] not in _IDENTITY_TYPES or _holder_has_name(entry):
            continue
        digits = re.sub(r"\D+", "", entry["text"])
        for number, role in role_by_number.items():
            if number in digits or number[-9:] in digits:
                entry["docType"] = role
                break


_ID_NUMBER_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")


def _identity_number(text: str) -> str:
    match = _ID_NUMBER_RE.search(text or "")
    return match.group(0) if match else ""


def _holder_has_name(entry: dict) -> bool:
    return bool(_identity_holder_name(entry["text"]))


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    if not documents:
        return {}

    docs = [{"index": item["index"], "text": _truncate_text(item.get("text", ""))} for item in documents]
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


def _unique_document_name(base: str, used: set[str], fallback: str) -> str:
    normalized = normalize_document_name(base, fallback)
    key = fold(normalized)
    if key and key not in used:
        used.add(key)
        return normalized
    stem = normalized[:45].strip() or fallback[:45].strip() or _LABELS[_DOC_OTHER]
    n = 2
    while True:
        candidate = f"{stem} {n}"[:50].strip()
        key = fold(candidate)
        if key not in used:
            used.add(key)
            return candidate
        n += 1


def _ordered_sources(doc_type: str, entries: list[dict]) -> list[int]:
    """Thứ tự file trong PDF gộp. Giấy tùy thân: theo từng người, mặt trước rồi mặt sau."""
    if doc_type not in _IDENTITY_TYPES or len(entries) < 2:
        return [entry["idx"] for entry in entries]
    records = [
        {"item": {"fileIndex": entry["idx"]}, "ocrText": entry["text"], "order": entry["idx"]}
        for entry in entries
    ]
    indexes: list[int] = []
    for item in merge_identity_records(records):
        segments = item.get("sourceSegments") or [{"fileIndex": item["fileIndex"]}]
        indexes.extend(int(segment["fileIndex"]) for segment in segments)
    return indexes


def _build_item(doc_type: str, entries: list[dict], document_name: str) -> dict:
    sources = _ordered_sources(doc_type, entries)
    first = next(entry for entry in entries if entry["idx"] == sources[0])
    row = _EXISTING_ROWS.get(doc_type)
    item = {
        "fileIndex": sources[0],
        "fileName": first["fileName"],
        "documentName": document_name,
        "componentName": row[1] if row else document_name,
        "target": "existing" if row else "new",
        "componentIndex": row[0] if row else None,
        "needsAddComponent": row is None,
        "detectedType": document_name,
    }
    if len(sources) > 1:
        item["sourceFileIndexes"] = sources
    return item


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, dict[str, str]] | None = None,
    today: date | None = None,
) -> tuple[list[dict], list[dict]]:
    llm_types = llm_types or {}
    today = today or date.today()
    by_name = {item.get("name"): item for item in ocr_results}
    resolved: list[dict] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = str(by_name.get(file_name, {}).get("text") or "")
        rule_type = _rule_doc_type(text, str(file.get("type") or ""))
        detected = llm_types.get(idx) or {}
        llm_type = detected.get("type") or ""
        doc_type = rule_type or llm_type or _DOC_OTHER
        if doc_type not in _ALLOWED_DOC_TYPES:
            doc_type = _DOC_OTHER
        resolved.append({
            "idx": idx,
            "fileName": file_name,
            "text": text,
            "docType": doc_type,
            "llmType": llm_type,
            "llmName": detected.get("documentName") or "",
            "source": "rule" if rule_type else ("llm" if llm_type else "default"),
        })

    _assign_roles(resolved, today)

    used_names: set[str] = set()
    attachments: list[dict] = []
    classified: list[dict] = []
    groups: dict[str, list[dict]] = {}
    others: list[dict] = []

    for entry in resolved:
        doc_type = entry["docType"]
        if doc_type == _DOC_SKIP:
            classified.append({
                "fileName": entry["fileName"],
                "docType": doc_type,
                "documentName": _LABELS[_DOC_SKIP],
                "target": "skip",
                "componentIndex": None,
                "source": entry["source"],
            })
            continue
        if doc_type in _GROUPED_TYPES:
            groups.setdefault(doc_type, []).append(entry)
        else:
            others.append(entry)

    for doc_type in _DOC_ORDER:
        entries = groups.get(doc_type)
        if not entries:
            continue
        document_name = _unique_document_name(_LABELS[doc_type], used_names, _LABELS[doc_type])
        item = _build_item(doc_type, entries, document_name)
        attachments.append(item)
        for entry in entries:
            classified.append({
                "fileName": entry["fileName"],
                "docType": doc_type,
                "documentName": document_name,
                "target": item["target"],
                "componentIndex": item["componentIndex"],
                "source": entry["source"],
            })

    for entry in others:
        fallback = _LABELS[_DOC_OTHER]
        document_name = _unique_document_name(entry["llmName"] or fallback, used_names, fallback)
        item = _build_item(_DOC_OTHER, [entry], document_name)
        attachments.append(item)
        classified.append({
            "fileName": entry["fileName"],
            "docType": _DOC_OTHER,
            "documentName": document_name,
            "target": item["target"],
            "componentIndex": None,
            "source": entry["source"],
        })

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

    attachments, classified = build_plan_items(raw_files, ocr_results, llm_types)
    skipped_ocr = [file["name"] for file in raw_files if file.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [file["name"] for file in raw_files],
            "ocrDocuments": [item.get("name") for item in ocr_results if item.get("text")],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "sessionId": (session or {}).get("request_id"),
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
