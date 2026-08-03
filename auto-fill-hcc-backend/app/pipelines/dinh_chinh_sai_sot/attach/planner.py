"""Đính kèm cho [Lai Châu] Đính chính GCN đã cấp lần đầu có sai sót.

Trang Lai Châu có 8 ô cố định nhưng thực chất là hai nhóm hồ sơ:
- Nhóm hiện hành Mẫu 11/ĐK: slot 0..3.
- Nhóm cũ Mẫu 18: slot 4..7.

Ba dòng hỗ trợ của hai nhóm có nhãn giống nhau. Vì vậy phải xác định mẫu đơn trước
rồi gán bằng slotIndex tuyệt đối; không được dựa vào text để chọn dòng đầu tiên.
"""

import re
import time
from pathlib import Path
from typing import Any

from app.config import settings
from app.pipelines._shared import fold, normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.dinh_chinh_sai_sot.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_MAX_FILE_BYTES = 6 * 1024 * 1024

_APP_11 = "application_11dk"
_APP_18 = "application_18"
_APP_GENERIC = "change_application"
_LAND = "land_certificate"
_PROOF = "error_proof"
_AUTH = "authorization"
_IDENTITY = "identity"
_OTHER = "other"
_ALLOWED_TYPES = {
    _APP_11, _APP_18, _APP_GENERIC, _LAND, _PROOF, _AUTH, _IDENTITY, _OTHER,
}

_BRANCH_11 = "11dk"
_BRANCH_18 = "18"

_ROW_LAND = "Bản gốc Giấy chứng nhận đã cấp. (Bản sao)"
_ROW_PROOF = (
    "Giấy tờ chứng minh sai sót thông tin của người được cấp Giấy chứng nhận so với thông tin "
    "tại thời điểm đề nghị đính chính hoặc sai sót thông tin về thửa đất, tài sản gắn liền với đất "
    "so với thông tin trên Giấy chứng nhận đã cấp. (Bản sao)"
)
_ROW_AUTH = (
    "Văn bản về việc ủy quyền theo quy định của pháp luật về dân sự đối với trường hợp thực hiện "
    "thủ tục thông qua người đại diện. (Bản sao)"
)
_ROW_APP_11 = (
    "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 11/ĐK ban hành kèm theo "
    "Nghị định số 101/2024/NĐ-CP. (Bản sao)"
)
_ROW_APP_18 = "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18. (Bản sao)"

SLOTS: list[dict[str, Any]] = [
    {"slotKey": "dinh_chinh_lc_11_land", "slotIndex": 0, "slotName": _ROW_LAND},
    {"slotKey": "dinh_chinh_lc_11_proof", "slotIndex": 1, "slotName": _ROW_PROOF},
    {"slotKey": "dinh_chinh_lc_11_auth", "slotIndex": 2, "slotName": _ROW_AUTH},
    {"slotKey": "dinh_chinh_lc_11_application", "slotIndex": 3, "slotName": _ROW_APP_11},
    {"slotKey": "dinh_chinh_lc_18_land", "slotIndex": 4, "slotName": _ROW_LAND},
    {"slotKey": "dinh_chinh_lc_18_proof", "slotIndex": 5, "slotName": _ROW_PROOF},
    {"slotKey": "dinh_chinh_lc_18_auth", "slotIndex": 6, "slotName": _ROW_AUTH},
    {"slotKey": "dinh_chinh_lc_18_application", "slotIndex": 7, "slotName": _ROW_APP_18},
]
_SLOT_BY_INDEX = {slot["slotIndex"]: slot for slot in SLOTS}

_LABELS = {
    _APP_11: "Đơn đăng ký biến động Mẫu số 11/ĐK",
    _APP_18: "Đơn đăng ký biến động Mẫu số 18",
    _APP_GENERIC: "Đơn đăng ký biến động đất đai",
    _LAND: "Giấy chứng nhận quyền sử dụng đất",
    _PROOF: "Giấy tờ chứng minh sai sót",
    _AUTH: "Văn bản ủy quyền",
    _IDENTITY: "Căn cước công dân",
    _OTHER: "Tài liệu chưa xác định",
}


def _truncate_text(text: str, limit: int = 3500) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _rule_doc_type(text: str) -> str:
    haystack = fold(text or "")
    if not haystack:
        return ""

    # Ủy quyền xét trước vì văn bản thường chứa CCCD của cả hai bên.
    if _has_any(
        haystack,
        ("giay uy quyen", "van ban uy quyen", "hop dong uy quyen", "ben duoc uy quyen"),
    ):
        return _AUTH

    # Mẫu 11/ĐK xét trước Mẫu 18 và các từ "đăng ký biến động" dùng chung.
    if _has_any(haystack, ("mau so 11/dk", "mau 11/dk", "mau so 11 dk", "mau 11 dk")) or (
        "nghi dinh so 101/2024/nd-cp" in haystack and "dang ky bien dong" in haystack
    ):
        return _APP_11
    if _has_any(haystack, ("mau so 18", "mau 18")) and "dang ky bien dong" in haystack:
        return _APP_18
    # Tiêu đề đơn là bằng chứng mạnh hơn các cụm "người sử dụng đất", "Giấy chứng nhận đã cấp"
    # xuất hiện bên trong đơn. Mẫu bị OCR sai số (ví dụ 16) vẫn phải vào dòng Đơn, không phải GCN.
    if _has_any(
        haystack,
        (
            "don dang ky bien dong dat dai",
            "don dang ky bien dong dat dai, tai san gan lien voi dat",
        ),
    ):
        return _APP_GENERIC

    if _has_any(
        haystack,
        (
            "giay chung nhan quyen su dung dat",
            "quyen so huu nha o",
            "quyen so huu tai san gan lien voi dat",
            "so vao so cap gcn",
        ),
    ) or ("thua dat" in haystack and "to ban do" in haystack and "giay chung nhan" in haystack):
        return _LAND

    if _has_any(
        haystack,
        (
            "can cuoc cong dan",
            "citizen identity card",
            "the can cuoc",
            "chung minh nhan dan",
            "identity card",
            "idvnm",
            "ho chieu",
            "passport",
        ),
    ):
        return _IDENTITY

    if _has_any(
        haystack,
        (
            "giay khai sinh",
            "trich luc khai sinh",
            "quyet dinh cai chinh",
            "quyet dinh dinh chinh",
            "van ban xac nhan",
            "giay to chung minh sai sot",
            "noi dung sai sot",
            "thong tin de nghi dinh chinh",
        ),
    ):
        return _PROOF
    return ""


def _normalize_doc_type(value: str) -> str:
    raw = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    if raw in _ALLOWED_TYPES:
        return raw
    text = fold(value or "")
    if "11/dk" in text or "11 dk" in text:
        return _APP_11
    if "mau so 18" in text or "mau 18" in text:
        return _APP_18
    if _has_any(text, ("change_application", "don dang ky bien dong", "dang ky bien dong dat dai")):
        return _APP_GENERIC
    if "uy quyen" in text:
        return _AUTH
    if _has_any(text, ("land_certificate", "quyen su dung dat", "so do", "so hong")):
        return _LAND
    if _has_any(text, ("identity", "can cuoc", "cccd", "cmnd", "ho chieu")):
        return _IDENTITY
    if _has_any(text, ("error_proof", "chung minh sai sot", "khai sinh", "xac nhan")):
        return _PROOF
    return _OTHER


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    if not documents:
        return {}
    docs = [{
        "index": item["index"],
        "name": str(item.get("name") or ""),
        "text": _truncate_text(item.get("text", "")),
    } for item in documents]
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(docs)},
    ]
    raw = await client.chat(messages, max_tokens=700, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    parsed_docs = parsed.get("documents", []) or []

    def _coerce(item: dict) -> dict[str, str]:
        return {
            "type": _normalize_doc_type(str(item.get("type") or item.get("docType") or "")),
            "title": str(item.get("title") or item.get("documentName") or "").strip(),
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
    valid_indexes = {doc["index"] for doc in documents}
    for raw_idx, item in raw_items:
        idx = raw_idx - offset
        if idx in valid_indexes:
            out[idx] = _coerce(item)
    return out


def _data_url_size(data_url: str) -> int:
    """Ước lượng chính xác kích thước payload base64 mà không giải mã file lớn."""
    payload = str(data_url or "").partition(",")[2]
    if not payload:
        return 0
    payload = re.sub(r"\s+", "", payload)
    padding = len(payload) - len(payload.rstrip("="))
    return max(0, (len(payload) * 3) // 4 - padding)


def _numbers(text: str) -> set[str]:
    out: set[str] = set()
    for match in re.finditer(r"(?<!\d)(?:\d[\s.]*){9,12}(?!\d)", text or ""):
        value = re.sub(r"\D", "", match.group())
        if len(value) in {9, 12}:
            out.add(value)
    return out


def _authorized_identity_numbers(ocr_results: list[dict]) -> set[str]:
    """Lấy số giấy tờ trong phần người được ủy quyền để không đính nhầm vào ô chứng minh sai sót."""
    numbers: set[str] = set()
    for result in ocr_results:
        text = str(result.get("text") or "")
        folded = fold(text)
        marker_pos = max(folded.find("ben duoc uy quyen"), folded.find("nguoi duoc uy quyen"))
        if marker_pos < 0:
            continue
        # Chỉ đọc vùng gần tiêu đề bên được ủy quyền, tránh lấy số của bên ủy quyền ở phần khác.
        numbers.update(_numbers(folded[marker_pos:marker_pos + 1200]))
    return numbers


def _branch_from_entries(entries: list[dict]) -> tuple[str, str]:
    has_11 = any(entry["docType"] == _APP_11 for entry in entries)
    has_18 = any(entry["docType"] == _APP_18 for entry in entries)
    has_generic = any(entry["docType"] == _APP_GENERIC for entry in entries)
    if has_11 and has_18:
        return "", "conflict"
    if has_18:
        return _BRANCH_18, "application"
    if has_11:
        return _BRANCH_11, "application"
    if has_generic:
        # Không suy diễn Mẫu 16/OCR sai thành Mẫu 18; nhóm hiện hành 11/ĐK là mặc định an toàn.
        return _BRANCH_11, "generic_application"
    # Trang hiển thị nhóm 11/ĐK trước và đây là mẫu hiện hành; dùng khi người dân không tải đơn.
    return _BRANCH_11, "default"


def _slot_index(branch: str, doc_type: str) -> int | None:
    offset = 0 if branch == _BRANCH_11 else 4
    if doc_type == _LAND:
        return offset
    if doc_type in {_PROOF, _IDENTITY}:
        return offset + 1
    if doc_type == _AUTH:
        return offset + 2
    if doc_type in {_APP_11, _APP_18, _APP_GENERIC}:
        return offset + 3
    return None


def _unique_document_name(base: str, used: set[str], fallback: str) -> str:
    generic_names = {
        "tai lieu bo sung",
        "tai lieu khac",
        "ho so bo sung",
        "giay to bo sung",
        "tai lieu dinh kem",
        "khong xac dinh",
    }
    if fold(base) in generic_names:
        base = fallback
    value = normalize_document_name(base, fallback)
    key = fold(value)
    if key and key not in used:
        used.add(key)
        return value
    stem = value[:52].strip() or fallback[:52].strip()
    suffix = 2
    while True:
        candidate = f"{stem} {suffix}"[:60].strip()
        key = fold(candidate)
        if key not in used:
            used.add(key)
            return candidate
        suffix += 1


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, dict[str, str]] | None = None,
) -> tuple[list[dict], list[str], list[dict], str, str]:
    llm_types = llm_types or {}
    ocr_by_name = {item.get("name"): item for item in ocr_results}
    entries: list[dict] = []

    for position, file in enumerate(files):
        idx = int(file.get("_index", position))
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = str(ocr_by_name.get(file_name, {}).get("text") or "")
        rule_type = _rule_doc_type(text)
        llm = llm_types.get(idx) or {}
        llm_type = llm.get("type") or ""
        doc_type = rule_type or llm_type or _OTHER
        if doc_type not in _ALLOWED_TYPES:
            doc_type = _OTHER
        entries.append({
            "idx": idx,
            "file": file,
            "fileName": file_name,
            "text": text,
            "docType": doc_type,
            "title": llm.get("title", ""),
            "source": "rule" if rule_type else ("llm" if llm_type else "unknown"),
        })

    branch, branch_source = _branch_from_entries(entries)
    if not branch:
        message = "Phát hiện đồng thời Đơn Mẫu 11/ĐK và Mẫu 18; không tự đính kèm để tránh chọn sai nhóm hồ sơ."
        classified = [
            {
                "fileName": entry["fileName"],
                "docType": entry["docType"],
                "target": "skip",
                "source": entry["source"],
                "reason": "branch_conflict",
            }
            for entry in entries
        ]
        return [], [message], classified, "", branch_source

    authorized_numbers = _authorized_identity_numbers(ocr_results)
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    used_names: set[str] = set()

    for entry in entries:
        doc_type = entry["docType"]
        identity_numbers = _numbers(entry["text"]) if doc_type == _IDENTITY else set()
        if doc_type == _IDENTITY and identity_numbers & authorized_numbers:
            warnings.append(
                f"File '{entry['fileName']}' là giấy tờ của người được ủy quyền; trang không có dòng "
                "CCCD riêng nên đã bỏ qua."
            )
            classified.append({
                "fileName": entry["fileName"],
                "docType": doc_type,
                "target": "skip",
                "source": entry["source"],
                "reason": "authorized_representative_identity",
            })
            continue

        slot_index = _slot_index(branch, doc_type)
        if slot_index is None:
            stem = normalize_document_name(Path(entry["fileName"]).stem, "Tài liệu chưa xác định")
            warnings.append(
                f"Không xác định được dòng thành phần hồ sơ cho file '{entry['fileName']}' "
                f"(nhận diện: {stem}) — đã bỏ qua."
            )
            classified.append({
                "fileName": entry["fileName"],
                "docType": doc_type,
                "documentName": stem,
                "target": "skip",
                "source": entry["source"],
                "reason": "unknown_document_type",
            })
            continue

        slot = _SLOT_BY_INDEX[slot_index]
        fallback = _LABELS[doc_type]
        title = entry["title"] if entry["source"] == "llm" else ""
        document_name = _unique_document_name(title or fallback, used_names, fallback)
        item = {
            "fileIndex": entry["idx"],
            "fileName": entry["fileName"],
            "documentName": document_name,
            "componentName": slot["slotName"],
            "target": "fixed-slot",
            "needsAddComponent": False,
            "detectedType": document_name,
            "slotKey": slot["slotKey"],
            "slotIndex": slot["slotIndex"],
            "slotName": slot["slotName"],
        }
        attachments.append(item)
        classified.append({
            "fileName": entry["fileName"],
            "docType": doc_type,
            "documentName": document_name,
            "target": "fixed-slot",
            "slotKey": slot["slotKey"],
            "slotIndex": slot["slotIndex"],
            "source": entry["source"],
        })

    return attachments, warnings, classified, branch, branch_source


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [
        {"name": file.name, "type": file.type, "dataUrl": file.dataUrl, "_index": idx}
        for idx, file in enumerate(files)
    ]

    valid_files: list[dict] = []
    oversized: list[dict] = []
    for file in raw_files:
        size = _data_url_size(file.get("dataUrl", ""))
        if size > _MAX_FILE_BYTES:
            oversized.append(file)
            errors.append(
                f"File '{file['name']}' vượt quá 6 MB ({size / 1024 / 1024:.2f} MB) — đã bỏ qua."
            )
        else:
            valid_files.append(file)

    ocr_files = [file for file in valid_files if file.get("type") in _OCR_TYPES]
    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for result in ocr_results:
        if result.get("error"):
            errors.append(f"OCR {result.get('name')}: {result['error']}")

    ocr_by_name = {result.get("name"): result for result in ocr_results}
    llm_docs: list[dict[str, Any]] = []
    for file in valid_files:
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        # Rule chắc chắn được giữ nguyên; chỉ gửi file chưa nhận diện sang LLM.
        if not _rule_doc_type(text):
            llm_docs.append({
                "index": file["_index"],
                "name": file["name"],
                "text": text,
            })

    t1 = time.monotonic()
    llm_types: dict[int, dict[str, str]] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified, branch, branch_source = build_plan_items(
        valid_files,
        ocr_results,
        llm_types,
    )
    errors.extend(warnings)
    for file in oversized:
        classified.append({
            "fileName": file["name"],
            "docType": _OTHER,
            "target": "skip",
            "source": "validation",
            "reason": "file_too_large",
        })

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [file["name"] for file in raw_files],
            "ocrDocuments": [result.get("name") for result in ocr_results if result.get("text")],
            "llmDocuments": [
                raw_files[doc["index"]]["name"]
                for doc in llm_docs
                if 0 <= doc["index"] < len(raw_files)
            ],
            "sessionId": (session or {}).get("request_id"),
            "branch": branch,
            "branchSource": branch_source,
            "classified": classified,
            "slots": SLOTS,
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "ocr_text": join_ocr_documents(ocr_results),
        "llm_output": {str(idx): value for idx, value in llm_types.items()},
        "errors": errors,
    }
