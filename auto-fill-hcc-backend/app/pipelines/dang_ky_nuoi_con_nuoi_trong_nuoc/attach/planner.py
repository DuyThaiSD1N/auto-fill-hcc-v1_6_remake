"""Đính kèm bước 3 cho thủ tục "Đăng ký việc nuôi con nuôi trong nước" (mã TTHC 2.001263).

Bảng thành phần hồ sơ trên cổng:
  STT1 - Bản sao hộ chiếu/thẻ căn cước: CCCD của cha mẹ nuôi.
  STT2 - Giấy khám sức khỏe: của cha mẹ nuôi.
  STT3 - Văn bản xác nhận hoàn cảnh gia đình, chỗ ở, kinh tế: sổ đỏ, bảng lương, xác nhận thu nhập...
  STT4 - Văn bản xác nhận tình trạng hôn nhân: giấy chứng nhận kết hôn (vợ chồng) hoặc giấy xác nhận
         tình trạng hôn nhân của người nhận con nuôi đơn thân.
  STT5 - Đơn xin nhận con nuôi, STT6 - Đơn đăng ký nhu cầu nhận trẻ em: nút "Khai tờ khai" (eForm),
         không đính file.

Giấy khai sinh, giấy khám sức khỏe, ảnh của trẻ và giấy tờ của cha/mẹ đẻ (CCCD, giấy xác nhận tình
trạng hôn nhân...) -> thêm thành phần hồ sơ mới. Mỗi dòng có sẵn nhận MỘT file gộp (sourceFileIndexes).

Giấy tùy thân, giấy khám sức khỏe, giấy xác nhận tình trạng hôn nhân có thể là của cha mẹ nuôi hoặc của
trẻ/mẹ đẻ: phân xử bằng số định danh trên đơn (phần người nhận con nuôi / phần người được nhận làm con
nuôi), không tin LLM.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold, normalize_document_name
from app.pipelines.dang_ky_nuoi_con_nuoi_trong_nuoc.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# Loại thô (luật OCR + LLM).
_IDENTITY = "identity"
_HEALTH = "health"
_FAMILY_CONDITION = "family_condition"
_MARRIAGE = "marriage_certificate"
_MARITAL_STATUS = "marital_status"
_APPLICATION = "adoption_application"
_BIRTH_CERT = "birth_certificate"
_CHILD_PHOTO = "child_photo"
_BIRTH_PARENT = "birth_parent_document"
_CRIMINAL_RECORD = "criminal_record"
_AUTHORIZATION = "authorization"
_OTHER = "other"
_SKIP = "skip"

_ALLOWED_DOC_TYPES = {
    _IDENTITY, _HEALTH, _FAMILY_CONDITION, _MARRIAGE, _MARITAL_STATUS, _APPLICATION, _BIRTH_CERT,
    _CHILD_PHOTO, _BIRTH_PARENT, _CRIMINAL_RECORD, _AUTHORIZATION, _OTHER, _SKIP,
}

# Loại sau khi phân xử chủ thể.
_ADOPTER_IDENTITY = "adopter_identity"
_ADOPTER_HEALTH = "adopter_health"
_CHILD_HEALTH = "child_health"

# Dòng có sẵn: (STT, đầu tên thành phần trên cổng, tên tài liệu).
_EXISTING_ROWS = {
    _ADOPTER_IDENTITY: (1, "Bản sao Hộ chiếu, Thẻ căn cước hoặc giấy tờ có giá trị thay thế", "Căn cước công dân của cha mẹ nuôi"),
    _ADOPTER_HEALTH: (2, "Giấy khám sức khỏe do bệnh viện đa khoa hoặc phòng khám đa khoa", "Giấy khám sức khỏe của cha mẹ nuôi"),
    _FAMILY_CONDITION: (3, "Văn bản xác nhận hoàn cảnh gia đình, tình trạng chỗ ở, điều kiện kinh tế", "Giấy tờ chứng minh hoàn cảnh, kinh tế"),
    _MARRIAGE: (4, "Văn bản xác nhận tình trạng hôn nhân", "Giấy chứng nhận kết hôn"),
}

# Thêm thành phần hồ sơ mới: mỗi loại gộp thành một thành phần.
_NEW_GROUP_LABELS = {
    _BIRTH_CERT: "Giấy khai sinh của trẻ",
    _CHILD_HEALTH: "Giấy khám sức khỏe của trẻ",
    _CHILD_PHOTO: "Ảnh toàn thân của trẻ",
    _BIRTH_PARENT: "Giấy tờ của cha mẹ đẻ",
    _CRIMINAL_RECORD: "Phiếu lý lịch tư pháp",
    _AUTHORIZATION: "Văn bản ủy quyền",
}
_OTHER_LABEL = "Tài liệu đăng ký nuôi con nuôi"
_APPLICATION_LABEL = "Đơn xin nhận con nuôi"
_SKIP_LABEL = "Bỏ qua"

# Header trang dịch vụ OCR chèn vào text: "───── Trang 2/4 ─────".
_PAGE_HEADER_RE = re.compile(
    r"(?im)^[\t \u2500-\u257f-]*(?:trang|page)\s+(\d+)\s*/\s*(\d+)[\t \u2500-\u257f-]*$"
)
# Số định danh 12 chữ số đứng riêng.
_ID_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")
# Ảnh trẻ gần như không có chữ; dưới ngưỡng này (ký tự chữ/số) coi là ảnh.
_PHOTO_MAX_CHARS = 30


def _has_any(haystack: str, needles: tuple[str, ...]) -> bool:
    return any(needle in haystack for needle in needles)


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def _normalize_doc_type(value: str) -> str:
    raw = str(value or "").strip()
    if raw in _ALLOWED_DOC_TYPES:
        return raw
    text = fold(raw)
    if _has_any(text, ("identity", "cccd", "can cuoc", "cmnd", "ho chieu")):
        return _IDENTITY
    if _has_any(text, ("health", "suc khoe")):
        return _HEALTH
    if _has_any(text, ("marriage", "ket hon")):
        return _MARRIAGE
    if _has_any(text, ("marital", "tinh trang hon nhan")):
        return _MARITAL_STATUS
    if _has_any(text, ("application", "don xin", "to khai")):
        return _APPLICATION
    if _has_any(text, ("birth", "khai sinh")):
        return _BIRTH_CERT
    if _has_any(text, ("photo", "anh")):
        return _CHILD_PHOTO
    if _has_any(text, ("criminal", "ly lich tu phap")):
        return _CRIMINAL_RECORD
    if _has_any(text, ("authorization", "uy quyen")):
        return _AUTHORIZATION
    if _has_any(text, ("skip", "bo qua")):
        return _SKIP
    return _OTHER


def _rule_doc_type(text: str) -> str:
    haystack = fold(text)
    if len(re.sub(r"[^a-z0-9]", "", haystack)) <= _PHOTO_MAX_CHARS:
        return ""
    if _has_any(haystack, ("van ban uy quyen", "giay uy quyen", "ben duoc uy quyen")):
        return _AUTHORIZATION
    if "phieu ly lich tu phap" in haystack:
        return _CRIMINAL_RECORD
    if _has_any(haystack, (
        "don xin nhan con nuoi",
        "phan khai ve nguoi nhan con nuoi",
        "don dang ky nhu cau nhan tre em",
    )):
        return _APPLICATION
    if _has_any(haystack, ("giay chung nhan ket hon", "trich luc ket hon", "giay dang ky ket hon")):
        return _MARRIAGE
    if "xac nhan tinh trang hon nhan" in haystack:
        return _MARITAL_STATUS
    if _has_any(haystack, ("giay kham suc khoe", "phan loai suc khoe")):
        return _HEALTH
    if _has_any(haystack, (
        "giay chung nhan quyen su dung dat",
        "quyen so huu nha o",
        "bang thanh toan tien luong",
        "bang luong",
        "xac nhan thu nhap",
        "thu nhap hang thang",
        "hoan canh gia dinh",
        "dieu kien kinh te",
        "hop dong thue nha",
    )):
        return _FAMILY_CONDITION
    if _has_any(haystack, ("giay khai sinh", "trich luc khai sinh", "noi dang ky khai sinh")):
        return _BIRTH_CERT
    # Chỉ dấu riêng của THẺ (đơn và giấy khám sức khỏe cũng ghi chữ "căn cước công dân số").
    if _has_any(haystack, (
        "citizen identity",
        "identity card",
        "idvnm",
        "dac diem nhan dang",
        "chung minh nhan dan",
        "ho chieu",
        "passport",
    )):
        return _IDENTITY
    return ""


def _application_ids(text: str) -> tuple[set[str], set[str]]:
    """Số định danh trên đơn: (cha mẹ nuôi — trước phần người được nhận làm con nuôi, trẻ — sau đó)."""
    lines = (text or "").splitlines()
    split = next((i for i, line in enumerate(lines) if "nguoi duoc nhan lam con nuoi" in fold(line)), len(lines))
    before, after = "\n".join(lines[:split]), "\n".join(lines[split:])
    return set(_ID_RE.findall(before)), set(_ID_RE.findall(after))


def _mentions_any(text: str, ids: set[str]) -> bool:
    digits = re.sub(r"\D", "", text or "")
    return any(number in digits for number in ids)


def _resolve_subject(raw_type: str, text: str, adopter_ids: set[str], child_ids: set[str], has_marriage: bool) -> str:
    """Giấy tùy thân / khám sức khỏe / xác nhận tình trạng hôn nhân là của cha mẹ nuôi hay của trẻ, mẹ đẻ."""
    if raw_type == _IDENTITY:
        if not adopter_ids or _mentions_any(text, adopter_ids):
            return _ADOPTER_IDENTITY
        # Thẻ của người không có tên trong phần người nhận con nuôi (thường là mẹ đẻ). Mặt sau không
        # đọc được số thì không kết luận được → giữ ở dòng của cha mẹ nuôi.
        return _BIRTH_PARENT if _ID_RE.search(text or "") else _ADOPTER_IDENTITY
    if raw_type == _HEALTH:
        if adopter_ids and _mentions_any(text, adopter_ids):
            return _ADOPTER_HEALTH
        haystack = fold(text)
        if (child_ids and _mentions_any(text, child_ids)) or _has_any(
            haystack, ("chua du 18 tuoi", "duoi 18 tuoi", "nguoi chua thanh nien")
        ):
            return _CHILD_HEALTH
        return _ADOPTER_HEALTH
    if raw_type == _MARITAL_STATUS:
        if adopter_ids and _mentions_any(text, adopter_ids):
            return _MARRIAGE
        # Vợ chồng nhận nuôi đã có giấy chứng nhận kết hôn → giấy xác nhận này là của mẹ/cha đẻ.
        return _BIRTH_PARENT if (adopter_ids or has_marriage) else _MARRIAGE
    return raw_type


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


def _alnum_chars(text: str) -> int:
    return len(re.sub(r"[^a-z0-9]", "", fold(text)))


def _is_photo(text: str, ocr_error: Any = None) -> bool:
    """Ảnh trẻ gần như không có chữ (OCR chỉ đọc được chữ ký nháy vài ký tự)."""
    return _alnum_chars(text) <= _PHOTO_MAX_CHARS and not ocr_error


def _split_pages(text: str) -> list[str]:
    """Text OCR theo trang (dịch vụ OCR chèn header "───── Trang i/n ─────"). Không có header → 1 trang."""
    matches = list(_PAGE_HEADER_RE.finditer(text or ""))
    if not matches:
        return [text or ""]
    total = max(int(m.group(2)) for m in matches)
    pages = [""] * max(total, len(matches))
    for pos, match in enumerate(matches):
        end = matches[pos + 1].start() if pos + 1 < len(matches) else len(text)
        number = int(match.group(1))
        if 1 <= number <= len(pages):
            pages[number - 1] = text[match.end():end]
    return pages


def _page_start_type(text: str, adopter_ids: set[str], child_ids: set[str], has_marriage: bool) -> str:
    """Loại giấy tờ nếu trang này là trang ĐẦU của một giấy; "" nếu là trang tiếp theo của giấy trước.

    Giấy khám sức khỏe: chỉ trang có tiêu đề "Giấy khám sức khỏe" mới mở giấy mới (các trang kết quả
    khám phía sau có chữ "phân loại sức khỏe" nhưng thuộc giấy trước). CCCD: mặt trước có số định danh
    mở thẻ mới, mặt sau (không có số đứng riêng) đi theo mặt trước.
    """
    raw = _rule_doc_type(text)
    if not raw:
        return ""
    if raw == _HEALTH and "giay kham suc khoe" not in fold(text):
        return ""
    if raw == _IDENTITY and not _ID_RE.search(text or ""):
        return ""
    return _resolve_subject(raw, text, adopter_ids, child_ids, has_marriage)


def _segments_of_file(entry: dict, adopter_ids: set[str], child_ids: set[str], has_marriage: bool) -> list[dict]:
    """Chia một file thành các đoạn trang liền nhau cùng loại: [{"type", "pages": [0-based]}]."""
    pages = entry["pages"]
    file_type = entry["type"]
    if len(pages) <= 1 or file_type in (_APPLICATION, _SKIP, _CHILD_PHOTO):
        return [{"type": file_type, "pages": list(range(len(pages)))}]
    segments: list[dict] = []
    for number, page in enumerate(pages):
        page_type = _page_start_type(page, adopter_ids, child_ids, has_marriage)
        if not page_type:
            page_type = segments[-1]["type"] if segments else file_type
        if segments and segments[-1]["type"] == page_type:
            segments[-1]["pages"].append(number)
        else:
            segments.append({"type": page_type, "pages": [number]})
    return segments


def _plan_item(files: list[dict], sources: list[dict], document_name: str, *,
               component_name: str, component_index: int | None) -> dict:
    """sources: [{"fileIndex", "pageIndexes" (None = cả file)}] theo thứ tự ghép."""
    primary = sources[0]["fileIndex"]
    item = {
        "fileIndex": primary,
        "fileName": str(files[primary].get("name") or f"file-{primary + 1}"),
        "documentName": document_name,
        "componentName": component_name,
        "target": "existing" if component_index else "new",
        "componentIndex": component_index,
        "needsAddComponent": not component_index,
        "detectedType": document_name,
    }
    if any(source["pageIndexes"] is not None for source in sources):
        item["sourceSegments"] = sources
    elif len(sources) > 1:
        item["sourceFileIndexes"] = [source["fileIndex"] for source in sources]
    return item


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, dict[str, str]] | None = None,
) -> tuple[list[dict], list[dict]]:
    llm_types = llm_types or {}
    by_name = {item.get("name"): item for item in ocr_results}

    entries: list[dict] = []
    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        ocr_item = by_name.get(file_name, {})
        text = str(ocr_item.get("text") or "")
        detected = llm_types.get(idx) or {}
        if _is_photo(text, ocr_item.get("error")):
            # Đi trước LLM: vài ký tự chữ ký nháy trên ảnh từng bị LLM đặt làm tên tài liệu.
            doc_type, source, detected = _CHILD_PHOTO, "rule", {}
        else:
            rule_type = _rule_doc_type(text)
            doc_type = rule_type or detected.get("type") or _OTHER
            source = "rule" if rule_type else ("llm" if detected.get("type") else "default")
        if doc_type not in _ALLOWED_DOC_TYPES:
            doc_type = _OTHER
        entries.append({
            "idx": idx,
            "fileName": file_name,
            "text": text,
            "pages": _split_pages(text),
            "type": doc_type,
            "llmName": detected.get("documentName") or "",
            "source": source,
        })

    adopter_ids: set[str] = set()
    child_ids: set[str] = set()
    for entry in entries:
        if entry["type"] == _APPLICATION:
            adopters, children = _application_ids(entry["text"])
            adopter_ids |= adopters
            child_ids |= children
    has_marriage = any(_rule_doc_type(page) == _MARRIAGE for entry in entries for page in entry["pages"])

    # Gom các đoạn trang theo loại; mỗi dòng có sẵn / mỗi loại thêm mới nhận MỘT file ghép.
    grouped: dict[str, list[dict]] = {}
    has_marriage_cert = False
    attachments: list[dict] = []
    classified: list[dict] = []
    used_names: set[str] = set()
    for entry in entries:
        entry["type"] = _resolve_subject(entry["type"], entry["text"], adopter_ids, child_ids, has_marriage)
        segments = _segments_of_file(entry, adopter_ids, child_ids, has_marriage)
        whole = len(segments) == 1
        for segment in segments:
            doc_type = segment["type"]
            pages = segment["pages"]
            source = {"fileIndex": entry["idx"], "pageIndexes": None if whole else pages}
            record = {
                "fileName": entry["fileName"],
                "pageFrom": pages[0] + 1,
                "pageTo": pages[-1] + 1,
                "docType": doc_type,
                "source": entry["source"],
            }
            if doc_type in (_APPLICATION, _SKIP):
                # Đơn xin nhận con nuôi khai bằng eForm ở STT 5 → không đính file.
                label = _APPLICATION_LABEL if doc_type == _APPLICATION else _SKIP_LABEL
                classified.append({**record, "documentName": label, "target": "skip", "componentIndex": None})
                continue
            if doc_type in _EXISTING_ROWS or doc_type in _NEW_GROUP_LABELS:
                grouped.setdefault(doc_type, []).append(source)
                if doc_type == _MARRIAGE and any(_rule_doc_type(entry["pages"][n]) == _MARRIAGE for n in pages):
                    has_marriage_cert = True
                classified.append({**record, "group": doc_type})
                continue
            document_name = _unique_document_name(entry["llmName"] or _OTHER_LABEL, used_names, _OTHER_LABEL)
            attachments.append(_plan_item(files, [source], document_name,
                                          component_name=document_name, component_index=None))
            classified.append({**record, "documentName": document_name, "target": "new", "componentIndex": None})

    group_items: dict[str, dict] = {}

    def add_group(doc_type: str, label: str, component_name: str | None, component_index: int | None) -> None:
        sources = grouped.get(doc_type)
        if not sources:
            return
        document_name = _unique_document_name(label, used_names, label)
        item = _plan_item(files, sources, document_name,
                          component_name=component_name or document_name, component_index=component_index)
        attachments.append(item)
        group_items[doc_type] = item

    for doc_type, (component_index, component_name, label) in _EXISTING_ROWS.items():
        # Dòng 4 chỉ có giấy xác nhận tình trạng hôn nhân (người nhận con nuôi đơn thân).
        if doc_type == _MARRIAGE and not has_marriage_cert:
            label = "Giấy xác nhận tình trạng hôn nhân"
        add_group(doc_type, label, component_name, component_index)
    for doc_type, label in _NEW_GROUP_LABELS.items():
        add_group(doc_type, label, None, None)

    for record in classified:
        item = group_items.get(record.pop("group", None))
        if item:
            record.update(documentName=item["documentName"], target=item["target"],
                          componentIndex=item["componentIndex"])
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
    # Chỉ hỏi LLM những file luật OCR chưa nhận ra và có chữ.
    llm_docs = []
    for idx, file in enumerate(raw_files):
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        if not _is_photo(text) and not _rule_doc_type(text):
            llm_docs.append({"index": idx, "text": text})

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
