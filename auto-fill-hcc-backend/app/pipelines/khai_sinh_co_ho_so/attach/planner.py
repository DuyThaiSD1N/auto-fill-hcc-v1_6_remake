"""Đính kèm bước 3 cho thủ tục "Đăng ký khai sinh cho người đã có hồ sơ, giấy tờ cá nhân" (1.004772).

Bảng "Thành phần hồ sơ" của thủ tục này có 5 dòng CỐ ĐỊNH:
  STT 1 — Mẫu hộ tịch điện tử tương tác (Tờ khai.pdf): BẮT BUỘC nhưng hệ thống TỰ SINH từ bước Kê khai
          → planner KHÔNG BAO GIỜ đính file vào dòng này.
  STT 2 — Văn bản cam đoan về việc chưa được đăng ký khai sinh (một văn bản).
  STT 3 — Bản sao TOÀN BỘ hồ sơ, giấy tờ cá nhân: CCCD, thẻ BHYT, giấy tờ cư trú, bằng/chứng chỉ/học bạ,
          giấy chứng nhận kết hôn, trích lục khai tử của cha/mẹ, giấy đề nghị xác nhận…
          → Ô GOM: NHIỀU tài liệu cùng vào một dòng (khác đăng ký lại khai sinh — ở đó mỗi ô một file).
  STT 4 — Văn bản xác nhận của Thủ trưởng cơ quan (chỉ khi người yêu cầu là cán bộ/CCVC/lực lượng vũ trang).
  STT 5 — Văn bản ủy quyền (chỉ khi ủy quyền thực hiện).

Tờ khai bản GIẤY người dân nộp kèm chỉ dùng để OCR ở bước 2; đính vào thành phần MỚI để không đụng
STT 1 mà cũng không bỏ rơi file nào.
"""
import re
import time
import unicodedata
from typing import Any

from app.config import settings
from app.pipelines._shared.identity_merge import merge_identity_attachments
from app.pipelines.khai_sinh_co_ho_so.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_ALLOWED_TYPES = {
    "commitment",
    "personal_document",
    "civil_servant_doc",
    "authorization",
    "paper_declaration",
    "other",
}

# Ô CÓ SẴN trên form → (componentIndex, đoạn text khớp dòng). FE khớp componentName theo substring đã
# fold nên chỉ cần đoạn đặc trưng; componentIndex chỉ là gợi ý vị trí (FE tự dò lại theo tên nếu lệch).
_ROW_2 = "Văn bản cam đoan của người yêu cầu về việc chưa được đăng ký khai sinh"
_ROW_3 = (
    "Bản sao toàn bộ hồ sơ, giấy tờ của người yêu cầu hoặc hồ sơ, giấy tờ, tài liệu khác "
    "trong đó có thông tin liên quan đến nội dung khai sinh"
)
_ROW_4 = (
    "Trường hợp người yêu cầu đăng ký khai sinh là cán bộ, công chức, viên chức, người đang công tác "
    "trong lực lượng vũ trang"
)
_ROW_5 = (
    "Văn bản ủy quyền theo quy định của pháp luật trong trường hợp ủy quyền thực hiện việc "
    "đăng ký khai sinh"
)

_EXISTING_ROUTE = {
    "commitment": (2, _ROW_2),
    "personal_document": (3, _ROW_3),
    "civil_servant_doc": (4, _ROW_4),
    "authorization": (5, _ROW_5),
}

# STT 3 là ô GOM: nhiều tài liệu cùng vào một dòng. Các ô còn lại chỉ nhận một tài liệu; file thứ hai
# rơi xuống STT 3 vì bản chất nó vẫn là "hồ sơ, giấy tờ khác của người yêu cầu".
_MULTI_FILE_SLOTS = {3}
_OVERFLOW_ROUTE = (3, _ROW_3)

# Nhãn hiển thị (documentName = tên tài liệu khi upload) cho từng loại.
_DOC_LABEL = {
    "commitment": "Bản cam đoan",
    "personal_document": "Giấy tờ cá nhân",
    "civil_servant_doc": "Văn bản xác nhận của cơ quan",
    "authorization": "Văn bản ủy quyền",
    "paper_declaration": "Tờ khai đăng ký khai sinh (bản giấy)",
    "other": "Tài liệu khai sinh",
}

_CCCD_MARKERS = (
    "can cuoc cong dan", "the can cuoc", "cccd", "citizen identity",
    "identity card", "chung minh nhan dan", "so dinh danh ca nhan", "idvnm",
)
_PERSONAL_DOC_MARKERS = (
    "bao hiem y te", "bhyt", "ma so bhxh",
    "giay chung nhan ket hon", "trich luc khai tu", "giay chung tu", "giay bao tu",
    "hoc ba", "bang tot nghiep", "chung chi", "ho so hoc tap",
    "giay xac nhan thong tin ve cu tru", "giay de nghi xac nhan", "ho chieu",
)
_COMMITMENT_MARKERS = ("cam doan", "cam ket")


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _is_cccd_text(text: str) -> bool:
    folded = _fold(text)
    return any(marker in folded for marker in _CCCD_MARKERS)


def _is_personal_document_text(text: str) -> bool:
    folded = _fold(text)
    return any(marker in folded for marker in _PERSONAL_DOC_MARKERS)


def _is_commitment_text(text: str) -> bool:
    """Bản cam đoan CỦA THỦ TỤC NÀY: cam đoan về việc chưa được đăng ký khai sinh."""
    folded = _fold(text)
    if not any(marker in folded for marker in _COMMITMENT_MARKERS):
        return False
    return "chua duoc dang ky khai sinh" in folded or "chua dang ky khai sinh" in folded


def _extract_person_name(text: str) -> str:
    """Trích họ tên chủ CCCD từ OCR (sau 'Full name'/'Họ và tên'...) để đặt tên tài liệu riêng."""
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


def _canonical_type(value: str) -> str:
    t = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    aliases = {
        "identity": "personal_document",
        "cccd": "personal_document",
        "cmnd": "personal_document",
        "passport": "personal_document",
        "residence_proof": "personal_document",
        "education_document": "personal_document",
        "commitment_statement": "commitment",
    }
    t = aliases.get(t, t)
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
    """Tên DUY NHẤT (form coi trùng tên là 'đã có' → bỏ qua). Trùng → thêm ' 2', ' 3'..."""
    candidate = base
    n = 2
    while _fold(candidate) in used:
        candidate = f"{base} {n}"
        n += 1
    used.add(_fold(candidate))
    return candidate


def _fallback_type(doc_type: str, text: str) -> str:
    """LLM để 'other' nhưng OCR đủ bằng chứng → kéo về đúng loại.

    Mọi giấy tờ mang thông tin nhân thân của người được khai sinh đều thuộc STT 3, nên fallback ở đây
    thiên về personal_document: bỏ sót một giấy tờ cá nhân vào ô gom tệ hơn là gắn dư một thành phần.
    """
    if doc_type != "other":
        return doc_type
    if _is_commitment_text(text):
        return "commitment"
    if _is_cccd_text(text) or _is_personal_document_text(text):
        return "personal_document"
    return "other"


async def plan_khai_sinh_co_ho_so_attachments(
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
    used_single_slots: set[int] = set()
    attachments: list[dict] = []
    classified: list[dict] = []
    identity_indexes: set[int] = set()
    for idx, file in enumerate(raw_files):
        detected = llm_types.get(idx) or {"type": "other", "title": ""}
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        doc_type = _fallback_type(detected["type"], text)

        route = _EXISTING_ROUTE.get(doc_type)
        if route and route[0] in used_single_slots:
            # Ô một-file đã có chủ → dồn xuống ô gom STT 3 thay vì đẻ thành phần mới.
            route = _OVERFLOW_ROUTE
        if route:
            comp_index, existing_component = route
            if comp_index not in _MULTI_FILE_SLOTS:
                used_single_slots.add(comp_index)
            if comp_index == _OVERFLOW_ROUTE[0]:
                # Ô gom chứa nhiều giấy tờ khác nhau → tên tài liệu phải nói rõ đó là giấy gì,
                # kèm tên người với CCCD để cán bộ phân biệt được các file trong cùng một dòng.
                label = detected.get("title") or _DOC_LABEL[doc_type]
                person = _extract_person_name(text) if _is_cccd_text(text) else ""
                document_name = _unique_label(f"{label} {person}".strip() if person else label, used_labels)
            else:
                document_name = _unique_label(
                    detected.get("title") or _DOC_LABEL.get(doc_type, "Tài liệu"), used_labels
                )
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
            # paper_declaration / other: không thuộc ô nào có sẵn. KHÔNG đính vào STT 1 (mẫu điện tử
            # do hệ thống tự sinh) — thêm thành phần mới để không bỏ rơi file người dân đã tải lên.
            label = detected.get("title") or _DOC_LABEL.get(doc_type, "Tài liệu khai sinh")
            component_name = _unique_label(label, used_labels)
            item = {
                "fileIndex": idx,
                "fileName": file["name"],
                "documentName": component_name,
                "componentName": component_name,
                "target": "new",
                "componentIndex": None,
                "needsAddComponent": True,
                "detectedType": component_name,
            }

        if _is_cccd_text(text):
            identity_indexes.add(idx)

        attachments.append(item)
        classified.append({
            "fileIndex": idx,
            "fileName": file["name"],
            "type": doc_type,
            "target": item["target"],
            "componentIndex": item["componentIndex"],
            "documentName": item["documentName"],
            "componentName": item["componentName"],
        })

    # Hai mặt chỉ được ghép khi OCR chứng minh cùng số định danh. Mỗi chủ thể khác nhau vẫn là một
    # item riêng; mặt sau không xác định được chủ thể được giữ lẻ.
    attachments = merge_identity_attachments(
        attachments,
        {
            idx: str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
            for idx, file in enumerate(raw_files)
        },
        identity_indexes,
    )

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


plan = plan_khai_sinh_co_ho_so_attachments

__all__ = ["plan", "plan_khai_sinh_co_ho_so_attachments"]
