"""Đính kèm cho thủ tục đăng ký khai sinh (liên thông).

Form bước đính kèm có thể có tới 2 ô (2 dòng):
  STT1 (luôn có): Giấy chứng sinh — hoặc văn bản người làm chứng xác nhận việc sinh, hoặc
                  giấy cam đoan về việc sinh.
  STT2 (tùy trường hợp): Tờ khai thay đổi thông tin cư trú (mẫu CT01) — khi trẻ không ở cùng
                  bố/mẹ/người giám hộ.
OCR + phân loại để tìm ĐÚNG từng file trong số file người dùng tải lên (có thể kèm CCCD
cha/mẹ), rồi gắn vào đúng ô theo vị trí (slotIndex 0 = chứng sinh, slotIndex 1 = tờ khai cư trú).
"""
import re
import time
import unicodedata
from typing import Any

from app.config import settings
from app.pipelines.khai_sinh_lien_thong.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_BIRTH_PROOF_LABEL = "Giấy chứng sinh"
_RESIDENCE_FORM_LABEL = "Tờ khai thay đổi thông tin cư trú"


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _is_birth_proof_text(text: str) -> bool:
    """Rule fallback khi LLM lỗi/không chắc: nhận diện giấy chứng sinh / người làm chứng / cam đoan."""
    folded = _fold(text)
    if "chung sinh" in folded:  # "giấy chứng sinh"
        return True
    if "lam chung" in folded and "sinh" in folded:  # văn bản người làm chứng xác nhận việc sinh
        return True
    if "cam doan" in folded and "sinh" in folded:  # giấy cam đoan về việc sinh
        return True
    return False


def _is_residence_form_text(text: str) -> bool:
    """Rule fallback: nhận diện Tờ khai thay đổi thông tin cư trú (mẫu CT01)."""
    folded = _fold(text)
    if "thay doi thong tin cu tru" in folded:
        return True
    if "thay doi noi cu tru" in folded:
        return True
    if "to khai thay doi" in folded and "cu tru" in folded:
        return True
    if "ct01" in folded.replace(" ", ""):  # mã mẫu CT01
        return True
    return False


# Loại tài liệu LLM gán cho mỗi file ở bước đính kèm khai sinh.
_DOC_BIRTH = "birth_proof"
_DOC_RESIDENCE = "residence_form"
_DOC_OTHER = "other"


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    """Trả về {fileIndex: docType} với docType ∈ {birth_proof, residence_form, other}."""
    if not documents:
        return {}

    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=400, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    parsed_docs = parsed.get("documents", []) or []
    out: dict[int, str] = {}

    def _norm(item: dict) -> str:
        dt = _fold(str(item.get("docType", "")))
        if dt in (_DOC_BIRTH, _DOC_RESIDENCE):
            return dt
        return _DOC_OTHER

    # Bền vững: LLM trả đúng số lượng → map theo THỨ TỰ (tránh lệch 0/1-based index).
    if len(parsed_docs) == len(documents):
        for pos, item in enumerate(parsed_docs):
            out[documents[pos]["index"]] = _norm(item)
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
            out[idx] = _norm(item)
    return out


async def plan_khai_sinh_attachments(
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
    llm_types: dict[int, str] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as e:  # noqa: BLE001
            errors.append(f"attachment_agent: {e}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    # Tìm 1 file cho mỗi ô (ưu tiên LLM, fallback rule theo OCR). 1 file không gán cho cả 2 ô.
    birth_index: int | None = None
    residence_index: int | None = None
    for idx, file in enumerate(raw_files):
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        dtype = llm_types.get(idx)
        # Rule là tín hiệu positive độc lập (cứu khi LLM trượt/gán other), giống bản cũ dùng OR.
        if birth_index is None and (dtype == _DOC_BIRTH or _is_birth_proof_text(text)):
            birth_index = idx
            continue
        if residence_index is None and (dtype == _DOC_RESIDENCE or _is_residence_form_text(text)):
            residence_index = idx
            continue

    attachments: list[dict] = []
    matched = {i for i in (birth_index, residence_index) if i is not None}

    if birth_index is not None:
        f = raw_files[birth_index]
        attachments.append({
            "fileIndex": birth_index,
            "fileName": f["name"],
            "documentName": _BIRTH_PROOF_LABEL,
            "componentName": _BIRTH_PROOF_LABEL,
            "target": "fixed-slot",
            "slotIndex": 0,            # STT1: giấy chứng sinh
            "slotKey": "birth_proof",  # FE khớp đúng dòng theo text tên giấy tờ
            "slotName": _BIRTH_PROOF_LABEL,
            "needsAddComponent": False,
            "detectedType": _BIRTH_PROOF_LABEL,
        })
    else:
        errors.append(
            "Không tìm thấy giấy chứng sinh (hoặc văn bản người làm chứng/giấy cam đoan về việc sinh) "
            "trong các file đã tải lên."
        )

    if residence_index is not None:
        f = raw_files[residence_index]
        attachments.append({
            "fileIndex": residence_index,
            "fileName": f["name"],
            "documentName": _RESIDENCE_FORM_LABEL,
            "componentName": _RESIDENCE_FORM_LABEL,
            "target": "fixed-slot",
            "slotIndex": 1,            # STT2: tờ khai thay đổi thông tin cư trú (tùy trường hợp)
            "slotKey": "residence_form",  # FE khớp đúng dòng theo text tên giấy tờ
            "slotName": _RESIDENCE_FORM_LABEL,
            "needsAddComponent": False,
            "detectedType": _RESIDENCE_FORM_LABEL,
        })

    skipped_names = [rf["name"] for i, rf in enumerate(raw_files) if i not in matched]
    if skipped_names:
        errors.append(
            "Bỏ qua file không thuộc giấy tờ cần nộp (chứng sinh / tờ khai cư trú): "
            + ", ".join(skipped_names)
        )

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [doc["fileName"] for doc in llm_docs],
            "birthProof": raw_files[birth_index]["name"] if birth_index is not None else None,
            "residenceForm": raw_files[residence_index]["name"] if residence_index is not None else None,
            "skipped": skipped_names,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "errors": errors,
    }


# Entrypoint thống nhất cho registry app.pipelines.<procedure>.attach.
plan = plan_khai_sinh_attachments
