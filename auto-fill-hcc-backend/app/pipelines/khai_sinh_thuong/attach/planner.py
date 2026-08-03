"""Đính kèm cho thủ tục đăng ký khai sinh THƯỜNG (moj eForm, bảng "Chọn tệp đính kèm").

KHÁC liên thông khai sinh (cổng React, menu-slot). Ở đây dùng cơ chế:
  - Ô CÓ SẴN (target "existing", khớp theo text dòng): chứng sinh→STT2, bỏ rơi→STT3,
    mang thai hộ→STT4, ủy quyền→STT5.
  - CCCD & giấy tờ khác → THÊM thành phần mới (target "new"), tên thành phần = "loại + tên người",
    tên file ngắn gọn (cccd_<tên>). KHÔNG bỏ qua file nào.
"""
import re
import time
import unicodedata
from typing import Any

from app.config import settings
from app.pipelines.khai_sinh_thuong.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_ALLOWED_TYPES = {
    "birth_proof",
    "abandoned_record",
    "surrogacy_doc",
    "authorization",
    "identity",
    "commitment",
    "other",
}

# Ô CÓ SẴN trên form → (componentIndex, text khớp dòng). componentName là đoạn đặc trưng của dòng
# (FE khớp substring đã fold), componentIndex chỉ là gợi ý vị trí.
_ROW_2 = "Giấy chứng sinh; trường hợp không có Giấy chứng sinh thì nộp văn bản của người làm chứng xác nhận về việc sinh"
_ROW_3 = "Trường hợp trẻ em bị bỏ rơi thì phải có biên bản về việc trẻ bị bỏ rơi do cơ quan có thẩm quyền lập"
_ROW_4 = "Trường hợp khai sinh cho trẻ em sinh ra do mang thai hộ phải có văn bản xác nhận của cơ sở y tế"
_ROW_5 = "Văn bản ủy quyền (được chứng thực) theo quy định của pháp luật trong trường hợp ủy quyền thực hiện việc đăng ký khai sinh"

_EXISTING_ROUTE = {
    "birth_proof": (2, _ROW_2),
    "abandoned_record": (3, _ROW_3),
    "surrogacy_doc": (4, _ROW_4),
    "authorization": (5, _ROW_5),
}

# Nhãn hiển thị (documentName = tên tài liệu khi upload) cho từng loại.
_DOC_LABEL = {
    "birth_proof": "Giấy chứng sinh",
    "abandoned_record": "Biên bản trẻ bị bỏ rơi",
    "surrogacy_doc": "Văn bản xác nhận mang thai hộ",
    "authorization": "Văn bản ủy quyền",
    "identity": "Căn cước công dân",
    "commitment": "Bản cam đoan",
    "other": "Tài liệu khai sinh",
}

_CCCD_MARKERS = (
    "can cuoc cong dan", "the can cuoc", "cccd", "citizen identity",
    "identity card", "chung minh nhan dan", "so dinh danh ca nhan", "idvnm",
)


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _is_cccd_text(text: str) -> bool:
    folded = _fold(text)
    return any(m in folded for m in _CCCD_MARKERS)


def _is_birth_proof_text(text: str) -> bool:
    folded = _fold(text)
    if "chung sinh" in folded:
        return True
    if "lam chung" in folded and "sinh" in folded:
        return True
    if "cam doan" in folded and "viec sinh" in folded:
        return True
    return False


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
    name = re.sub(r"\b[Ii]\b$", "", name).strip()
    return name.title() if name else ""


def _short_file_name(prefix: str, person: str, idx: int) -> str:
    """Tên file ngắn gọn: cccd_<ten> (bỏ dấu, gạch dưới). Không có tên → cccd_<n>."""
    slug = re.sub(r"[^a-z0-9]+", "_", _fold(person)).strip("_")
    return f"{prefix}_{slug}" if slug else f"{prefix}_{idx + 1}"


def _canonical_type(value: str) -> str:
    t = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    return t if t in _ALLOWED_TYPES else "other"


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=700, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    parsed_docs = parsed.get("documents", []) or []

    def _coerce(item: dict) -> dict[str, str]:
        return {
            "type": _canonical_type(item.get("type") or item.get("docType")),
            "title": str(item.get("title") or "").strip(),
        }

    out: dict[int, dict[str, str]] = {}
    # Bền vững: LLM trả đúng số lượng → map theo THỨ TỰ (tránh lệch 0/1-based index).
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
    offset = 0 if any(r == 0 for r, _ in raw_items) else 1
    valid = {d["index"] for d in documents}
    for r, item in raw_items:
        idx = r - offset
        if idx in valid:
            out[idx] = _coerce(item)
    return out


def _unique_label(base: str, used: set[str]) -> str:
    """Tên thành phần DUY NHẤT (form coi trùng tên là 'đã có' → bỏ qua). Trùng → thêm ' 2', ' 3'..."""
    candidate = base
    n = 2
    while _fold(candidate) in used:
        candidate = f"{base} {n}"
        n += 1
    used.add(_fold(candidate))
    return candidate


async def plan_khai_sinh_thuong_attachments(
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
        {"index": idx, "fileName": file.get("name"),
         "text": str(ocr_by_name.get(file.get("name"), {}).get("text") or "")}
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

    used_labels: set[str] = set()
    used_existing: set[int] = set()
    attachments: list[dict] = []
    classified: list[dict] = []
    for idx, file in enumerate(raw_files):
        detected = llm_types.get(idx) or {"type": "other", "title": ""}
        doc_type = detected["type"]
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")

        # Fallback rule khi LLM lỡ để "other": CCCD → identity; chứng sinh/người làm chứng → birth_proof.
        if doc_type == "other":
            if _is_cccd_text(text):
                doc_type = "identity"
            elif _is_birth_proof_text(text):
                doc_type = "birth_proof"

        route = _EXISTING_ROUTE.get(doc_type)
        if route and route[0] not in used_existing:
            comp_index, existing_component = route
            used_existing.add(comp_index)
            document_name = _DOC_LABEL.get(doc_type, "Tài liệu")
            item = {
                "fileIndex": idx,
                "fileName": file["name"],
                "documentName": document_name,
                "componentName": existing_component,
                "target": "existing",
                "componentIndex": comp_index,
                "needsAddComponent": False,
                "detectedType": document_name,
            }
        else:
            # Thành phần MỚI. Tên thành phần = "loại + tên người"; tên file ngắn gọn.
            # _is_cccd_text chỉ dùng ở fallback other → identity phía trên. Khi LLM đã
            # phân loại rõ (ví dụ Bản cam đoan có nhắc số CCCD), không được đổi cách
            # đặt tên tài liệu sang cccd_*.
            if doc_type == "identity":
                person = _extract_person_name(text)
                label = detected.get("title") or _DOC_LABEL["identity"]
                component_base = f"{label} {person}".strip() if person else label
                document_name = _short_file_name("cccd", person, idx)
            else:
                label = detected.get("title") or _DOC_LABEL.get(doc_type, "Tài liệu khai sinh")
                component_base = label
                document_name = label
            component_name = _unique_label(component_base, used_labels)
            item = {
                "fileIndex": idx,
                "fileName": file["name"],
                "documentName": document_name,
                "componentName": component_name,
                "target": "new",
                "componentIndex": None,
                "needsAddComponent": True,
                "detectedType": component_name,
            }

        attachments.append(item)
        classified.append({
            "fileName": file["name"], "type": doc_type,
            "target": item["target"], "componentIndex": item["componentIndex"],
            "documentName": item["documentName"], "componentName": item["componentName"],
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


plan = plan_khai_sinh_thuong_attachments
