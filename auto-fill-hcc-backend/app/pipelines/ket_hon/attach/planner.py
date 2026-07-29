import re
import time
import unicodedata
from typing import Any

from app.config import settings
from app.pipelines._shared import normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.ket_hon.attach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_MALE_LABEL = "CCCD bên nam"
_FEMALE_LABEL = "CCCD bên nữ"
_BOTH_LABEL = "CCCD của cả bên nam và bên nữ"
_UNKNOWN_LABEL = "CCCD"

# Loại giấy tờ KHÔNG phải CCCD (đặt tên riêng, không bị gán nhầm thành CCCD).
_DECLARATION_LABEL = "Tờ khai đăng ký kết hôn"
_COMMITMENT_LABEL = "Bản cam đoan"
_OTHER_LABEL = "Tài liệu kết hôn"


_ALLOWED_DOC_TYPES = {"identity", "marriage_declaration", "commitment", "other"}

# Ô hồ sơ CÓ SẴN STT 2 trên form (giấy tờ tùy thân của 2 bên). Một CCCD sẽ ghim vào ô này,
# các CCCD còn lại thêm thành phần mới. componentName để frontend khớp dòng (substring đã fold).
_ID_SLOT_INDEX = 2
_ID_SLOT_COMPONENT = (
    "Hộ chiếu/Chứng minh nhân dân/Thẻ căn cước công dân/Thẻ căn cước/Căn cước điện tử"
)


def _rule_doc_type(text: str) -> str:
    """Fallback rule khi LLM lỗi: phân loại theo tiêu đề OCR.

    Thủ tục kết hôn mặc định giấy tờ tải lên là CCCD; chỉ carve-out tờ khai đăng ký kết hôn và
    bản cam đoan (2 loại này cũng nhắc tới 'căn cước công dân số ...' nên phải kiểm tiêu đề TRƯỚC).
    Còn lại (CCCD, hoặc OCR chỉ còn số định danh) → identity."""
    folded = _fold(text)
    if "to khai dang ky ket hon" in folded:
        return "marriage_declaration"
    if "ban cam doan" in folded:
        return "commitment"
    return "identity"


async def _classify_doc_types_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    """LLM phân loại LOẠI giấy tờ + đặt tên cụ thể (đồng bộ các planner khác).

    Trả {fileIndex: {"type": <loại>, "documentName": <tên cụ thể cho loại 'other'>}}."""
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
    # Map theo THỨ TỰ mảng khi đủ số lượng (tránh lệch 0/1-based index).
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


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _digits(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


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
    """Khớp số định danh: mặt trước có đủ 12 số; mặt sau (MRZ) OCR thường chỉ còn phần đuôi,
    nên chấp nhận khớp 9 số cuối liên tiếp."""
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
    # Fallback nhẹ cho trường hợp session không có số định danh hoặc OCR mất vài số.
    if "gioi tinh nam" in folded or "sex nam" in folded:
        return "male"
    if "gioi tinh nu" in folded or "sex nu" in folded:
        return "female"
    return "unknown"


def _detect_face_from_text(text: str) -> str:
    """Phân biệt mặt trước / mặt sau CCCD để đặt tên riêng khi mỗi file CHỈ có 1 mặt.

    Nếu file chứa CẢ 2 mặt (CCCD scan đầy đủ) → trả "" (không gắn hậu tố mặt)."""
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
        return ""  # file có cả 2 mặt → không cần phân biệt mặt trước/sau
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
    """Bảo đảm tên thành phần hồ sơ DUY NHẤT (form coi trùng tên là 'đã có'). Trùng → thêm ' 2', ' 3'..."""
    candidate = label
    n = 2
    while _fold(candidate) in used:
        candidate = f"{label} {n}"
        n += 1
    used.add(_fold(candidate))
    return candidate


# Map giá trị LLM trả về → giá trị nội bộ.
_SIDE_MAP = {"nam": "male", "nu": "female", "ca_hai": "both", "both": "both", "male": "male", "female": "female"}
_FACE_MAP = {"truoc": "front", "sau": "back", "ca_hai": "", "both": "", "front": "front", "back": "back"}


def _compose_label(side: str, face: str, used: set[str]) -> str:
    """Tên thành phần hồ sơ CCCD = người + mặt (trước/sau) để mỗi ảnh là 1 thành phần riêng,
    tránh trùng tên khiến chỉ đính kèm được 1 ảnh/người."""
    # Form chỉ cho phép chữ, số, khoảng trắng, gạch dưới, gạch ngang — KHÔNG dùng ngoặc đơn.
    base = _label_for_side(side)
    suffix = {"front": " - mặt trước", "back": " - mặt sau"}.get(face, "")
    return _dedup_label(f"{base}{suffix}", used)


def _build_item(file: dict, source_indexes: list[int], label: str, detected_type: str) -> dict:
    """Một đơn vị đính kèm. `source_indexes` (đã sắp thứ tự) là các file gốc FE sẽ GỘP thành 1 PDF;
    độ dài 1 = file lẻ như thường, >1 = FE gộp (mặt trước/sau, người 1→người 2)."""
    primary = source_indexes[0]
    return {
        "fileIndex": primary,
        "sourceFileIndexes": list(source_indexes),
        "fileName": str(file.get("name") or f"file-{primary + 1}"),
        "documentName": label,
        "componentName": label,
        "target": "new",
        "componentIndex": None,
        "needsAddComponent": True,
        "detectedType": detected_type,
    }


async def plan_ket_hon_attachments(
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

    # LLM phân loại LOẠI giấy tờ (đồng bộ các planner khác); rule là fallback khi LLM lỗi/thiếu.
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

    # CHỈ CCCD mới đi logic nam/nữ + mặt trước/sau. side/face do LLM quyết (đặc biệt "file đủ 2 mặt"
    # → face ca_hai → KHÔNG gắn hậu tố mặt); rule chỉ là fallback khi LLM không trả.
    doc_types: list[str] = []
    sides: list[str] = []
    faces: list[str] = []
    for idx, file in enumerate(raw_files):
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        info = llm_types.get(idx) or {}
        doc_type = info.get("type") or _rule_doc_type(text)
        doc_types.append(doc_type)
        if doc_type == "identity":
            side = _SIDE_MAP.get(info.get("side", "")) or _detect_side_from_text(text, male_id, female_id)
            llm_face = info.get("face", "")
            face = _FACE_MAP[llm_face] if llm_face in _FACE_MAP else _detect_face_from_text(text)
            sides.append(side)
            faces.append(face)
        else:
            sides.append("")
            faces.append("")

    # Suy luận nam/nữ cho CCCD chưa rõ: chỉ áp dụng khi có ĐÚNG 2 file CCCD.
    id_indexes = [i for i, t in enumerate(doc_types) if t == "identity"]
    if len(id_indexes) == 2:
        resolved = _resolve_unknown_sides([sides[i] for i in id_indexes])
        for i, s in zip(id_indexes, resolved):
            sides[i] = s
    elif len(id_indexes) == 1 and sides[id_indexes[0]] == "unknown":
        sides[id_indexes[0]] = "both"  # 1 file CCCD không rõ → coi như chứa cả 2 mặt/2 người

    used_labels: set[str] = set()

    # --- Gom CCCD thành ĐƠN VỊ đính kèm ---
    # Gom theo NGƯỜI (side) — KHÔNG theo face vì face OCR không đáng tin. Người có ≥2 file CCCD
    # = tải nhiều mặt rời → GỘP; người 1 file (PDF đủ 2 mặt) → để lẻ. Face chỉ dùng sắp thứ tự.
    side_counts: dict[str, int] = {}
    for i in id_indexes:
        side_counts[sides[i]] = side_counts.get(sides[i], 0) + 1
    split_idxs = [i for i in id_indexes if side_counts.get(sides[i], 0) >= 2]
    single_idxs = [i for i in id_indexes if side_counts.get(sides[i], 0) == 1]

    person_order: dict[str, int] = {}
    for i in split_idxs:
        person_order.setdefault(sides[i], len(person_order))
    _face_rank = {"front": 0, "back": 1}
    merge_sorted = sorted(
        split_idxs,
        key=lambda i: (person_order.get(sides[i], 99), _face_rank.get(faces[i], 2), i),
    )

    # Mỗi đơn vị: (primary_index, [source_indexes theo thứ tự gộp], label).
    id_units: list[tuple[int, list[int], str]] = []
    if len(merge_sorted) >= 2:
        # Gộp TẤT CẢ file của các NGƯỜI tải nhiều mặt → 1 PDF (mặt trước→sau, người 1→người 2).
        group_sides = {sides[i] for i in merge_sorted if sides[i] in ("male", "female")}
        if {"male", "female"} <= group_sides:
            merged_label = _BOTH_LABEL
        elif group_sides:
            merged_label = _label_for_side(next(iter(group_sides)))
        else:
            merged_label = _UNKNOWN_LABEL
        id_units.append((merge_sorted[0], merge_sorted, _dedup_label(merged_label, used_labels)))
    else:  # 0 hoặc 1 file cần gộp → không gộp
        for i in merge_sorted:
            id_units.append((i, [i], _compose_label(sides[i], faces[i], used_labels)))
    for i in single_idxs:
        id_units.append((i, [i], _compose_label(sides[i], faces[i], used_labels)))
    id_units.sort(key=lambda u: u[0])  # đơn vị CCCD đầu tiên = primary index nhỏ nhất

    # Đơn vị CCCD ĐẦU TIÊN → ghim ô STT 2 có sẵn; còn lại giữ target "new".
    id_items: dict[int, dict] = {}
    for k, (primary, sources, label) in enumerate(id_units):
        item = _build_item(raw_files[primary], sources, label, label)
        if k == 0:
            item["componentName"] = _ID_SLOT_COMPONENT
            item["target"] = "existing"
            item["componentIndex"] = _ID_SLOT_INDEX
            item["needsAddComponent"] = False
        id_items[primary] = item

    # Giấy tờ KHÔNG phải CCCD → mỗi file 1 thành phần mới (như cũ).
    non_id_items: dict[int, dict] = {}
    for idx, file in enumerate(raw_files):
        if doc_types[idx] == "identity":
            continue
        if doc_types[idx] == "other":
            base = (llm_types.get(idx) or {}).get("documentName") or file.get("name") or ""
            label = _dedup_label(normalize_document_name(base, _OTHER_LABEL), used_labels)
        else:  # marriage_declaration / commitment — tên chuẩn cố định
            label = _dedup_label(_label_for_doc_type(doc_types[idx]), used_labels)
        non_id_items[idx] = _build_item(file, [idx], label, label)

    # Ghép theo thứ tự index tự nhiên (đơn vị gộp lấy theo primary index).
    attachments: list[dict] = [
        id_items.get(idx) or non_id_items[idx]
        for idx in sorted(list(id_items.keys()) + list(non_id_items.keys()))
    ]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "sessionId": (session or {}).get("request_id"),
            "matched": [
                {
                    "fileName": raw_files[idx].get("name"),
                    "docType": doc_types[idx],
                    "side": sides[idx],
                }
                for idx in range(len(raw_files))
            ],
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        # Cho trace xem lại OCR (AttachmentPlanResp tự lược khỏi HTTP response).
        "ocr_text": join_ocr_documents(ocr_results),
        "errors": errors,
    }


plan = plan_ket_hon_attachments
