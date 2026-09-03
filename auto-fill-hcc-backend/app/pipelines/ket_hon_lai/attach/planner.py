"""Đính kèm bước 3 cho thủ tục đăng ký lại kết hôn."""
import re
import time
import unicodedata
from typing import Any

from app.config import settings
from app.pipelines._shared import normalize_document_name
from app.pipelines._shared.identity_merge import merge_identity_attachments
from app.pipelines.ket_hon_lai.attach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_MALE_LABEL = "CCCD bên nam"
_FEMALE_LABEL = "CCCD bên nữ"
_BOTH_LABEL = "CCCD của cả bên nam và bên nữ"
_UNKNOWN_LABEL = "CCCD"

_DECLARATION_LABEL = "Tờ khai đăng ký lại kết hôn"
_COMMITMENT_LABEL = "Bản cam đoan"
_OTHER_LABEL = "Tài liệu đăng ký lại kết hôn"
_ALLOWED_DOC_TYPES = {"identity", "marriage_certificate", "marriage_declaration", "commitment", "other"}

# componentName = substring khớp dòng STT2 có sẵn (dòng trên form ghi tên rất dài).
# documentName = tên tài liệu đặt trong ví/khi tải lên — ngắn gọn.
_ROW_2_COMPONENT = "Bản sao Giấy chứng nhận kết hôn"
_ROW_2_DOCUMENT_NAME = "Bản sao Giấy chứng nhận kết hôn"

_SIDE_MAP = {"nam": "male", "nu": "female", "ca_hai": "both", "both": "both", "male": "male", "female": "female"}
_FACE_MAP = {"truoc": "front", "sau": "back", "ca_hai": "", "both": "", "front": "front", "back": "back"}


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _digits(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _rule_doc_type(text: str) -> str:
    folded = _fold(text)
    if "to khai dang ky lai ket hon" in folded or "to khai dang ky ket hon" in folded:
        return "marriage_declaration"
    if "ban cam doan" in folded or "cam ket" in folded:
        return "commitment"
    if "giay chung nhan ket hon" in folded or "chung nhan ket hon" in folded or "trich luc ket hon" in folded:
        return "marriage_certificate"
    return "identity"


async def _classify_doc_types_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=600, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    parsed_docs = parsed.get("documents", []) or []

    def _coerce(item: dict) -> dict[str, str]:
        t = re.sub(r"[\s-]+", "_", str(item.get("type") or "").strip().lower())
        return {
            "type": t if t in _ALLOWED_DOC_TYPES else "other",
            "side": re.sub(r"[\s-]+", "_", str(item.get("side") or "").strip().lower()),
            "face": re.sub(r"[\s-]+", "_", str(item.get("face") or "").strip().lower()),
            "documentName": str(item.get("documentName") or "").strip(),
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
    offset = 0 if any(r == 0 for r, _ in raw_items) else 1
    valid = {d["index"] for d in documents}
    for r, item in raw_items:
        idx = r - offset
        if idx in valid:
            out[idx] = _coerce(item)
    return out


def _label_for_doc_type(doc_type: str) -> str:
    if doc_type == "marriage_declaration":
        return _DECLARATION_LABEL
    if doc_type == "commitment":
        return _COMMITMENT_LABEL
    return _OTHER_LABEL


def _fields_by_name(session: dict | None) -> dict[str, Any]:
    fields = (session or {}).get("fields") or []
    return {
        str(item.get("name")): item.get("value")
        for item in fields
        if isinstance(item, dict) and item.get("value") not in (None, "", {}, [])
    }


def _identity_numbers_from_session(session: dict | None) -> tuple[str, str]:
    values = _fields_by_name(session)
    male = _digits(values.get("SoDinhDanh_BenNam") or values.get("SoGiayToDinhDanh_BenNam"))
    female = _digits(values.get("SoDinhDanh_BenNu") or values.get("SoGiayToDinhDanh_BenNu"))
    return male, female


def _id_in_text(id_num: str, digits: str) -> bool:
    if not id_num or not digits:
        return False
    if id_num in digits:
        return True
    tail = id_num[-9:]
    return len(tail) >= 9 and tail in digits


def _detect_side_from_text(text: str, male_id: str, female_id: str) -> str:
    digits = _digits(text)
    has_male = _id_in_text(male_id, digits)
    has_female = _id_in_text(female_id, digits)
    if has_male and has_female:
        return "both"
    if has_male:
        return "male"
    if has_female:
        return "female"

    folded = _fold(text)
    if "gioi tinh nam" in folded or "sex nam" in folded:
        return "male"
    if "gioi tinh nu" in folded or "sex nu" in folded:
        return "female"
    return "unknown"


def _detect_face_from_text(text: str) -> str:
    folded = _fold(text)
    back_markers = (
        "dac diem nhan dang",
        "personal identification",
        "cuc truong cuc canh sat",
        "director general",
        "idvnm",
    )
    front_markers = (
        "can cuoc cong dan",
        "citizen identity",
        "ho va ten",
        "full name",
        "ngay sinh",
        "date of birth",
        "gia tri den",
        "date of expiry",
    )
    has_back = any(m in folded for m in back_markers)
    has_front = any(m in folded for m in front_markers)
    if has_back and has_front:
        return ""
    if has_back:
        return "back"
    if has_front:
        return "front"
    return ""


def _resolve_unknown_sides(sides: list[str]) -> list[str]:
    resolved = sides[:]
    if len(resolved) != 2:
        return resolved
    known = set(side for side in resolved if side in {"male", "female"})
    unknown_indexes = [idx for idx, side in enumerate(resolved) if side == "unknown"]
    if len(unknown_indexes) == 1 and len(known) == 1:
        resolved[unknown_indexes[0]] = "female" if "male" in known else "male"
    return resolved


def _label_for_side(side: str) -> str:
    if side == "male":
        return _MALE_LABEL
    if side == "female":
        return _FEMALE_LABEL
    if side == "both":
        return _BOTH_LABEL
    return _UNKNOWN_LABEL


def _dedup_label(label: str, used: set[str]) -> str:
    candidate = label
    n = 2
    while _fold(candidate) in used:
        candidate = f"{label} {n}"
        n += 1
    used.add(_fold(candidate))
    return candidate


def _compose_label(side: str, face: str, used: set[str]) -> str:
    base = _label_for_side(side)
    suffix = {"front": " - mặt trước", "back": " - mặt sau"}.get(face, "")
    return _dedup_label(f"{base}{suffix}", used)


def _build_item(file: dict, idx: int, label: str, detected_type: str) -> dict:
    return {
        "fileIndex": idx,
        "fileName": str(file.get("name") or f"file-{idx + 1}"),
        "documentName": label,
        "componentName": label,
        "target": "new",
        "componentIndex": None,
        "needsAddComponent": True,
        "detectedType": detected_type,
    }


def _is_marriage_cert(doc_type: str, document_name: str, text: str) -> bool:
    """Giấy chứng nhận/trích lục kết hôn cũ, khác tờ khai đăng ký lại kết hôn."""
    folded = _fold(f"{document_name} {text}")
    if "to khai" in folded:
        return False
    if doc_type == "marriage_certificate":
        return True
    return "giay chung nhan ket hon" in folded or "chung nhan ket hon" in folded or "trich luc ket hon" in folded


async def plan_ket_hon_lai_attachments(
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

    male_id, female_id = _identity_numbers_from_session(session)
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
            llm_types = await _classify_doc_types_with_llm(llm_docs)
        except Exception as e:  # noqa: BLE001
            errors.append(f"attachment_agent: {e}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    doc_types: list[str] = []
    sides: list[str] = []
    faces: list[str] = []
    is_cert: list[bool] = []
    for idx, file in enumerate(raw_files):
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        info = llm_types.get(idx) or {}
        doc_type = info.get("type") or _rule_doc_type(text)
        cert = _is_marriage_cert(doc_type, info.get("documentName", ""), text)
        is_cert.append(cert)
        doc_types.append(doc_type)
        if doc_type == "identity" and not cert:
            side = _SIDE_MAP.get(info.get("side", "")) or _detect_side_from_text(text, male_id, female_id)
            llm_face = info.get("face", "")
            face = _FACE_MAP[llm_face] if llm_face in _FACE_MAP else _detect_face_from_text(text)
            sides.append(side)
            faces.append(face)
        else:
            sides.append("")
            faces.append("")

    id_indexes = [i for i, t in enumerate(doc_types) if t == "identity" and not is_cert[i]]
    if len(id_indexes) == 2:
        resolved = _resolve_unknown_sides([sides[i] for i in id_indexes])
        for i, s in zip(id_indexes, resolved):
            sides[i] = s
    elif len(id_indexes) == 1 and sides[id_indexes[0]] == "unknown":
        sides[id_indexes[0]] = "both"

    attachments: list[dict] = []
    used_labels: set[str] = set()
    cert_used = False
    for idx, file in enumerate(raw_files):
        if is_cert[idx] and not cert_used:
            cert_used = True
            attachments.append({
                "fileIndex": idx,
                "fileName": str(file.get("name") or f"file-{idx + 1}"),
                "documentName": _ROW_2_DOCUMENT_NAME,
                "componentName": _ROW_2_COMPONENT,
                "target": "existing",
                "componentIndex": 2,
                "needsAddComponent": False,
                "detectedType": "marriage_certificate",
            })
            continue
        if doc_types[idx] == "identity" and not is_cert[idx]:
            label = _compose_label(sides[idx], faces[idx], used_labels)
        elif doc_types[idx] in {"marriage_declaration", "commitment"}:
            label = _dedup_label(_label_for_doc_type(doc_types[idx]), used_labels)
        else:
            base = (llm_types.get(idx) or {}).get("documentName") or file.get("name") or ""
            label = _dedup_label(normalize_document_name(base, _OTHER_LABEL), used_labels)
        attachments.append(_build_item(file, idx, label, label))

    # Chỉ ghép mặt trước/mặt sau của cùng một số định danh. CCCD của hai bên
    # (hoặc chủ thể khác) luôn giữ thành các dòng riêng.
    attachments = merge_identity_attachments(
        attachments,
        {
            idx: str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
            for idx, file in enumerate(raw_files)
        },
        id_indexes,
    )

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "sessionId": (session or {}).get("request_id"),
            "matched": [
                {
                    "fileName": raw_files[i].get("name"),
                    "docType": "marriage_certificate" if is_cert[i] else doc_types[i],
                    "side": sides[i],
                }
                for i in range(len(raw_files))
            ],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }


plan = plan_ket_hon_lai_attachments
