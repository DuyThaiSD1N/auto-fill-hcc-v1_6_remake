import re
import time
import unicodedata
from typing import Any

from app.config import settings
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


_CCCD_MARKERS = (
    "can cuoc cong dan",
    "the can cuoc",
    "cccd",
    "citizen identity",
    "identity card",
    "chung minh nhan dan",
    "so dinh danh ca nhan",
    "idvnm",
)


def _is_cccd_text(text: str) -> bool:
    folded = _fold(text)
    return any(marker in folded for marker in _CCCD_MARKERS)


def _extract_person_name(text: str) -> str:
    """Trích họ tên chủ CCCD từ OCR (sau 'Full name'/'Họ và tên'...) để đặt tên thành phần riêng."""
    if not text:
        return ""
    m = re.search(
        r"(?:Full name|tên khai sinh|H[oọ] và tên|H[oọ], chữ đệm)\s*[:.\-/]*\s*"
        r"([A-ZÀ-ỸĐ][A-ZÀ-ỸĐ\s]{2,45}?)\s+"
        r"(?:Ngày|Ngay|Date|Quốc|Quoc|Giới|Gioi|Sex|Nationality|Số|So)\b",
        text,
    )
    if not m:
        return ""
    name = re.sub(r"\s+", " ", m.group(1)).strip()
    # Bỏ phần nhãn còn sót (vd "I", "/") và viết hoa đầu chữ.
    name = re.sub(r"\b[IiI]\b$", "", name).strip()
    return name.title() if name else ""

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_ALLOWED_LLM_TYPES = {
    "birth_certificate_copy",
    "personal_supporting_document",
    "authorization",
    "paper_declaration",
    "commitment_statement",
    "other",
}

_BIRTH_CERT_COPY_LABEL = "Giấy khai sinh bản sao"
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
_ROW_5_COMPONENT = "- Văn bản ủy quyền theo quy định của pháp luật trong trường hợp ủy quyền thực hiện việc đăng ký lại khai sinh."


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _canonical_type(value: str) -> str:
    doc_type = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    return doc_type if doc_type in _ALLOWED_LLM_TYPES else "other"


def _label_for_type(doc_type: str, title: str = "") -> str:
    title = str(title or "").strip()
    if doc_type == "birth_certificate_copy":
        return title or _BIRTH_CERT_COPY_LABEL
    if doc_type == "personal_supporting_document":
        return title or _PERSONAL_SUPPORTING_LABEL
    if doc_type == "authorization":
        return title or _AUTHORIZATION_LABEL
    if doc_type == "paper_declaration":
        return _PAPER_DECLARATION_LABEL
    if doc_type == "commitment_statement":
        return _COMMITMENT_STATEMENT_LABEL
    return title or _OTHER_LABEL


def _route_for_type(doc_type: str, personal_supporting_seen: int) -> tuple[str, int | None, str]:
    if doc_type == "birth_certificate_copy":
        return "existing", 2, _ROW_2_COMPONENT
    if doc_type == "personal_supporting_document" and personal_supporting_seen == 0:
        return "existing", 3, _ROW_3_COMPONENT
    if doc_type == "authorization":
        return "existing", 5, _ROW_5_COMPONENT
    if doc_type == "commitment_statement":
        return "new", None, ""
    return "new", None, ""


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    if not documents:
        return {}

    docs = [
        {
            "index": item["index"],
            "fileName": item["fileName"],
            "text": _truncate_text(item.get("text", "")),
        }
        for item in documents
    ]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(docs)},
    ]
    raw = await client.chat(messages, max_tokens=800, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    out: dict[int, dict[str, str]] = {}
    for item in parsed.get("documents", []):
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        out[idx] = {
            "type": _canonical_type(str(item.get("type") or "")),
            "title": str(item.get("title") or "").strip(),
        }
    return out


def _unique_label(base: str, used: set[str]) -> str:
    """Đảm bảo tên thành phần là duy nhất để extension không coi là trùng và bỏ qua."""
    candidate = base
    n = 2
    while _fold(candidate) in used:
        candidate = f"{base} {n}"
        n += 1
    used.add(_fold(candidate))
    return candidate


def _build_item(file: dict, idx: int, doc_type: str, label: str, personal_supporting_seen: int) -> dict:
    target, component_index, existing_component = _route_for_type(doc_type, personal_supporting_seen)
    component_name = existing_component if target == "existing" else label
    return {
        "fileIndex": idx,
        "fileName": str(file.get("name") or f"file-{idx + 1}"),
        "documentName": label,
        "componentName": component_name,
        "target": target,
        "componentIndex": component_index,
        "needsAddComponent": target == "new",
        "detectedType": label,
    }


async def plan_dang_ky_lai_khai_sinh_attachments(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    from app.services import ocr


    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for r in ocr_results:
        if r.get("error"):
            errors.append(f"OCR {r.get('name')}: {r['error']}")

    ocr_by_name = {r.get("name"): r for r in ocr_results}
    llm_docs = [
        {
            "index": idx,
            "fileName": file.get("name"),
            "text": str(ocr_by_name.get(file.get("name"), {}).get("text") or ""),
        }
        for idx, file in enumerate(raw_files)
    ]

    t1 = time.monotonic()
    llm_types: dict[int, dict[str, str]] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as e:  # noqa: BLE001
            errors.append(f"attachment_agent: {e}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    personal_supporting_seen = 0
    used_labels: set[str] = set()
    attachments: list[dict] = []
    classified: list[dict] = []
    for idx, file in enumerate(raw_files):
        detected = llm_types.get(idx) or {"type": "other", "title": ""}
        doc_type = detected["type"]
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")

        # CCCD/CMND → đặt tên "cccd_<tên chủ thẻ>" để mỗi thẻ là 1 thành phần riêng (cho phép up nhiều).
        if doc_type == "personal_supporting_document" and _is_cccd_text(text):
            name = _extract_person_name(text)
            base_label = f"cccd_{name}" if name else f"cccd_{idx + 1}"
        else:
            base_label = _label_for_type(doc_type, detected.get("title", ""))
        label = _unique_label(base_label, used_labels)

        item = _build_item(file, idx, doc_type, label, personal_supporting_seen)
        attachments.append(item)
        if doc_type == "personal_supporting_document":
            personal_supporting_seen += 1
        classified.append({
            "fileName": file.get("name"),
            "type": doc_type,
            "title": detected.get("title", ""),
            "label": label,
            "target": item["target"],
            "componentIndex": item["componentIndex"],
        })

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [doc["fileName"] for doc in llm_docs],
            "sessionId": (session or {}).get("request_id"),
            "classified": classified,
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "errors": errors,
    }


plan = plan_dang_ky_lai_khai_sinh_attachments
