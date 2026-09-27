"""Phân loại theo nguyên file cho thủ tục cấp bản sao trích lục hộ tịch.

Nhánh này không sinh ``sourceSegments``. Hai file rời là hai mặt giấy tờ tùy thân
cùng người vẫn được gộp bằng ``sourceFileIndexes`` theo số định danh/MRZ.

⚑ LLM QUYẾT TRƯỚC, RULE CHỈ ĐỠ KHI LLM KHÔNG TRẢ KẾT QUẢ cho file đó. Không rule keyword nào được
đè lên kết quả LLM: chữ trong giấy tờ hộ tịch tham chiếu chéo nhau rất nhiều (trích lục cải chính
ghi "…Giấy khai sinh số…", Giấy khai sinh có trang ghi chú nhắc trích lục cải chính), rule dò chữ
đè lên LLM là đổi đúng thành sai.

⚑ Mỗi file một lượt gọi LLM: gọi chung cả hồ sơ thì các file giống nhau kéo nhau sai cùng chiều
(hai trích lục cải chính/bổ sung cùng bị gọi là giấy kết hôn), và phải tin fileIndex LLM trả về.
"""

import asyncio
import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines._shared.identity_merge import merge_identity_attachments
from app.pipelines.trich_luc.attach.civil_status_names import civil_status_name, is_civil_status
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_ALLOWED_TYPES = {
    "civil_status_birth", "civil_status_marriage", "civil_status_death", "identity",
    "authorization", "residence_proof", "paper_declaration", "other",
}

_BIRTH_LABEL = "Giấy khai sinh"
_MARRIAGE_LABEL = "Giấy đăng ký kết hôn"
_DEATH_LABEL = "Trích lục khai tử"
_IDENTITY_LABEL = "Căn cước công dân"
_AUTHORIZATION_LABEL = "Văn bản ủy quyền"
_RESIDENCE_LABEL = "Giấy tờ chứng minh cư trú"
_DECLARATION_LABEL = "Tờ khai bản giấy"
_OTHER_LABEL = "Tài liệu trích lục hộ tịch"
_BUNDLE_LABEL = "Hồ sơ trích lục hộ tịch"

_ROW_BY_TYPE = {
    "authorization": (2, "Văn bản ủy quyền theo quy định của pháp luật trong trường hợp ủy quyền"),
    "identity": (3, "Hộ chiếu/Chứng minh nhân dân/Thẻ căn cước công dân/Thẻ căn cước/Căn cước điện tử"),
    "residence_proof": (4, "Giấy tờ có giá trị chứng minh thông tin về cư trú"),
}

_CCCD_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")
_PAGE_HEADER_RE = re.compile(
    r"(?im)^[\t \u2500-\u257f-]*(?:trang|page)\s+\d+\s*/\s*\d+"
    r"[\t \u2500-\u257f-]*$"
)
_DECLARATION_MARKERS = (
    "to khai yeu cau cap ban sao", "to khai cap ban sao", "yeu cau cap ban sao trich luc ho tich",
)
_PAGE_KIND_MARKERS = {
    "birth": ("giay khai sinh", "trich luc khai sinh"),
    "marriage": ("giay chung nhan ket hon", "trich luc ket hon", "trich luc ghi chu ket hon"),
    "death": ("trich luc khai tu", "giay chung tu"),
    "authorization": ("van ban uy quyen", "giay uy quyen"),
    "residence": ("giay xac nhan thong tin ve cu tru", "giay to chung minh cu tru"),
}

_IDENTITY_DIRECT_MARKERS = (
    "can cuoc cong dan", "citizen identity", "identity card", "chung minh nhan dan",
    "giay chung minh nhan dan", "passport", "ho chieu", "idvnm",
)
_IDENTITY_BACK_SIGNAL_GROUPS = (
    ("dac diem nhan dang", "personal identification"),
    ("van tay", "ngon tro", "left index finger", "right index finger"),
    ("cuc truong cuc canh sat", "director general", "quan ly hanh chinh ve trat tu xa hoi"),
)


def _has_identity_evidence(text: str) -> bool:
    """Không để một cụm OCR chung như 'Đặc điểm nhận dạng' tự biến trang nhiễu thành CCCD."""
    folded = _fold(text)
    if any(marker in folded for marker in _IDENTITY_DIRECT_MARKERS):
        return True
    signal_count = sum(
        1 for group in _IDENTITY_BACK_SIGNAL_GROUPS if any(marker in folded for marker in group)
    )
    if _CCCD_RE.search(str(text or "")):
        signal_count += 1
    return signal_count >= 2


def _canonical_type(value: Any) -> str:
    raw = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    aliases = {
        "id": "identity", "cccd": "identity", "cmnd": "identity", "passport": "identity",
        "birth": "civil_status_birth", "marriage": "civil_status_marriage",
        "death": "civil_status_death", "declaration": "paper_declaration",
    }
    raw = aliases.get(raw, raw)
    return raw if raw in _ALLOWED_TYPES else "other"


def _rule_doc_type(text: str) -> str:
    """Fallback thận trọng khi LLM lỗi; chỉ route khi toàn file có một nhóm rõ ràng."""
    folded = _fold(text)
    # Tên giấy tờ được kể trong tờ khai chỉ là nội dung tham chiếu. Nếu có header trang,
    # `_is_mixed_bundle` sẽ kiểm tra riêng để vẫn nhận ra bộ hồ sơ thực sự có nhiều tài liệu.
    if any(marker in folded for marker in _DECLARATION_MARKERS):
        return "paper_declaration"
    detected: set[str] = set()
    if "giay khai sinh" in folded or "trich luc khai sinh" in folded:
        detected.add("civil_status_birth")
    if any(marker in folded for marker in ("giay chung nhan ket hon", "trich luc ket hon")):
        detected.add("civil_status_marriage")
    if "trich luc khai tu" in folded or "giay chung tu" in folded:
        detected.add("civil_status_death")
    if "van ban uy quyen" in folded or "giay uy quyen" in folded:
        detected.add("authorization")
    if "giay xac nhan thong tin ve cu tru" in folded or "giay to chung minh cu tru" in folded:
        detected.add("residence_proof")
    if _has_identity_evidence(text):
        detected.add("identity")
    return next(iter(detected)) if len(detected) == 1 else "other"


def _page_starts(text: str) -> list[str]:
    value = str(text or "")
    matches = list(_PAGE_HEADER_RE.finditer(value))
    if not matches:
        return []
    starts = []
    for position, match in enumerate(matches):
        end = matches[position + 1].start() if position + 1 < len(matches) else len(value)
        starts.append(_fold(value[match.end():end][:700]))
    return starts


def _is_mixed_bundle(text: str, proposed_name: str = "") -> bool:
    """Nhìn đầu từng trang để không nhầm nội dung/chú thích của một giấy tờ là tài liệu khác."""
    if _fold(proposed_name) == _fold(_BUNDLE_LABEL):
        return True
    kinds: set[str] = set()
    for page in _page_starts(text):
        if not page or page.startswith("chu thich"):
            continue
        if any(marker in page for marker in _DECLARATION_MARKERS):
            kinds.add("declaration")
            continue
        if _has_identity_evidence(page):
            kinds.add("identity")
            continue
        for kind, markers in _PAGE_KIND_MARKERS.items():
            if any(marker in page for marker in markers):
                kinds.add(kind)
                break
    return len(kinds) >= 2


def _clean_subject_name(value: Any) -> str:
    subject = re.sub(r"\s+", " ", str(value or "")).strip(" :-")
    if _fold(subject) in {"", "ho ten", "ho va ten", "full name", "khong ro"}:
        return ""
    return subject[:40].strip()


def _identity_document_name(text: str, subject_name: str = "") -> str:
    folded = _fold(text)
    has_passport = "passport" in folded or "ho chieu" in folded
    has_cccd = "can cuoc" in folded or "citizen identity" in folded or "idvnm" in folded
    has_cmnd = "chung minh nhan dan" in folded or "cmnd" in folded
    if has_cccd and not has_passport and not has_cmnd:
        subject = _clean_subject_name(subject_name)
        if subject and len(set(_CCCD_RE.findall(str(text or "")))) <= 1:
            return normalize_document_name(f"CCCD {subject}", _IDENTITY_LABEL)
        return _IDENTITY_LABEL
    if has_passport and not has_cccd and not has_cmnd:
        return "Hộ chiếu"
    if has_cmnd and not has_cccd and not has_passport:
        return "Chứng minh nhân dân"
    return "Giấy tờ tùy thân"


def _label_for_type(doc_type: str) -> str:
    return {
        "civil_status_birth": _BIRTH_LABEL,
        "civil_status_marriage": _MARRIAGE_LABEL,
        "civil_status_death": _DEATH_LABEL,
        "authorization": _AUTHORIZATION_LABEL,
        "residence_proof": _RESIDENCE_LABEL,
        "paper_declaration": _DECLARATION_LABEL,
    }.get(doc_type, _OTHER_LABEL)


def _unique_document_name(base: str, used: set[str], fallback: str) -> str:
    normalized = normalize_document_name(base, fallback)
    key = _fold(normalized)
    if key and key not in used:
        used.add(key)
        return normalized
    stem = normalized[:45].strip() or fallback[:45].strip() or _OTHER_LABEL
    suffix = 2
    while True:
        candidate = f"{stem} {suffix}"[:50].strip()
        key = _fold(candidate)
        if key not in used:
            used.add(key)
            return candidate
        suffix += 1


async def _classify_one(document: dict[str, Any]) -> dict | None:
    raw = await client.chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt([document])},
        ],
        max_tokens=300,
        enable_thinking=settings.agent_reasoning,
    )
    parsed = client.extract_json_block(raw)
    items = parsed.get("documents", []) if isinstance(parsed, dict) else []
    # Chỉ gửi đúng một file nên lấy phần tử đầu, KHÔNG tra theo fileIndex LLM tự ghi.
    first = next((item for item in items if isinstance(item, dict)), None)
    if first is None:
        return None
    return {
        "type": _canonical_type(first.get("type")),
        "documentName": str(first.get("documentName") or first.get("title") or "").strip(),
        "subjectName": _clean_subject_name(first.get("subjectName")),
    }


async def _classify_with_llm(
    documents: list[dict[str, Any]], errors: list[str] | None = None,
) -> dict[int, dict]:
    """Một lượt gọi cho MỖI file; file lỗi thì vắng khỏi kết quả để rule đỡ riêng file đó."""
    if not documents:
        return {}
    outcomes = await asyncio.gather(*(_classify_one(d) for d in documents), return_exceptions=True)
    result: dict[int, dict] = {}
    for document, outcome in zip(documents, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            if errors is not None:
                errors.append(f"attachment_agent fileIndex={document['fileIndex']}: {outcome}")
            continue
        if outcome is not None:
            result[document["fileIndex"]] = outcome
    return result


def _route_for_type(doc_type: str, document_name: str, used_slots: set[int]) -> tuple[str, int | None, str, bool]:
    row = _ROW_BY_TYPE.get(doc_type)
    if row is None:
        return "new", None, document_name, True
    component_index, component_name = row
    if component_index in used_slots:
        return "new", None, document_name, True
    used_slots.add(component_index)
    return "existing", component_index, component_name, False


async def plan_trich_luc_attachments_without_split(
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
    for file_index, result in ocr_by_index.items():
        if result.get("error"):
            errors.append(f"OCR fileIndex={file_index} {raw_files[file_index].get('name')}: {result['error']}")

    documents = [
        {"fileIndex": file_index, "ocrText": str((ocr_by_index.get(file_index) or {}).get("text") or "")}
        for file_index in range(len(raw_files))
    ]
    started = time.monotonic()
    classified_by_index: dict[int, dict] = {}
    if documents:
        try:
            classified_by_index = await _classify_with_llm(documents, errors)
        except Exception as exc:  # noqa: BLE001 - fallback vẫn phải giữ đủ file
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments: list[dict] = []
    classified: list[dict] = []
    identity_indexes: set[int] = set()
    identity_subject_by_index: dict[int, str] = {}
    used_names: set[str] = set()
    used_slots: set[int] = set()

    for file_index, file in enumerate(raw_files):
        text = documents[file_index]["ocrText"]
        llm_item = classified_by_index.get(file_index) or {}
        if file_index in classified_by_index:
            # LLM đã trả lời → tin LLM. Chỉ coi là bộ hồ sơ khi CHÍNH LLM đặt tên bộ hồ sơ; quét đầu
            # trang bằng chữ KHÔNG được đè lên kết quả LLM.
            source = "llm"
            doc_type = llm_item.get("type") or "other"
            mixed_bundle = _fold(llm_item.get("documentName")) == _fold(_BUNDLE_LABEL)
        else:
            # LLM không trả kết quả cho file này (lỗi gọi, JSON hỏng) → rule đỡ để vẫn giữ đủ file.
            source = "rule"
            doc_type = _rule_doc_type(text)
            mixed_bundle = _is_mixed_bundle(text)
        if mixed_bundle:
            doc_type = "other"

        if doc_type == "identity":
            document_name = _unique_document_name(
                _identity_document_name(text, llm_item.get("subjectName") or ""),
                used_names,
                _IDENTITY_LABEL,
            )
            identity_indexes.add(file_index)
            identity_subject_by_index[file_index] = llm_item.get("subjectName") or ""
        elif mixed_bundle:
            document_name = _unique_document_name(_BUNDLE_LABEL, used_names, _BUNDLE_LABEL)
        elif is_civil_status(doc_type):
            label = civil_status_name(doc_type, llm_item.get("documentName") or "")
            document_name = _unique_document_name(label, used_names, label)
        elif doc_type in {"authorization", "residence_proof", "paper_declaration"}:
            label = _label_for_type(doc_type)
            document_name = _unique_document_name(label, used_names, label)
        else:
            # Giấy tờ đơn lẻ "lạ" (trích lục cải chính, bổ sung…) giữ ĐÚNG tiêu đề LLM đọc được. Không
            # có tiêu đề thì dùng tên chung — KHÔNG đoán tên bằng chữ trong giấy: trích lục cải chính
            # luôn có câu "…Giấy khai sinh số…" nên đoán theo chữ là gọi nó thành Giấy khai sinh.
            proposed = llm_item.get("documentName") or _OTHER_LABEL
            document_name = _unique_document_name(proposed, used_names, _OTHER_LABEL)

        target, component_index, component_name, needs_add = _route_for_type(
            doc_type, document_name, used_slots,
        )
        attachments.append({
            "fileIndex": file_index,
            "fileName": str(file.get("name") or f"file-{file_index + 1}"),
            "documentName": document_name,
            "componentName": component_name,
            "target": target,
            "componentIndex": component_index,
            "needsAddComponent": needs_add,
            "detectedType": document_name,
        })
        classified.append({
            "fileIndex": file_index, "fileName": file.get("name"), "type": doc_type,
            "documentName": document_name, "target": target, "componentIndex": component_index,
            # Ghi nguồn quyết định vào trace: không có trường này thì phải suy ngược mới biết loại sai
            # là do LLM hay do rule.
            "source": source, "llmTitle": llm_item.get("documentName") or "",
        })

    ocr_text_by_index = {item["fileIndex"]: item["ocrText"] for item in documents}
    attachments = merge_identity_attachments(attachments, ocr_text_by_index, identity_indexes)

    # Sau khi gộp hai mặt, lấy tên chủ thể từ mặt đọc được rõ nhất và đồng bộ trace theo file nguồn.
    used_identity_names: set[str] = set()
    final_by_source: dict[int, dict] = {}
    for item in attachments:
        source_indexes = item.get("sourceFileIndexes") or [item.get("fileIndex")]
        if not any(index in identity_indexes for index in source_indexes):
            continue
        combined_text = "\n".join(ocr_text_by_index.get(index, "") for index in source_indexes)
        subjects = []
        for index in source_indexes:
            subject = _clean_subject_name(identity_subject_by_index.get(index, ""))
            if subject and _fold(subject) not in {_fold(value) for value in subjects}:
                subjects.append(subject)
        base_name = _identity_document_name(combined_text, subjects[0] if len(subjects) == 1 else "")
        document_name = _unique_document_name(base_name, used_identity_names, _IDENTITY_LABEL)
        item["documentName"] = document_name
        item["detectedType"] = document_name
        if item.get("target") == "new":
            item["componentName"] = document_name
        for index in source_indexes:
            if isinstance(index, int):
                final_by_source[index] = item
    for item in classified:
        final = final_by_source.get(item["fileIndex"])
        if final:
            item.update({
                "documentName": final["documentName"], "target": final["target"],
                "componentIndex": final.get("componentIndex"),
            })

    indexed_ocr_results = []
    for file_index, file in enumerate(raw_files):
        result = ocr_by_index.get(file_index)
        if result:
            indexed_ocr_results.append({
                **result,
                "name": f"fileIndex={file_index} · {file.get('name') or f'file-{file_index + 1}'}",
            })

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [file["name"] for file in raw_files],
            "ocrDocuments": [
                raw_files[index].get("name") for index, result in ocr_by_index.items() if result.get("text")
            ],
            "llmDocuments": [file.get("name") for file in raw_files],
            "sessionId": (session or {}).get("request_id"),
            "attachmentMode": "preserve_files",
            "classified": classified,
        },
        "ocr_text": join_ocr_documents(indexed_ocr_results),
        "stats": {
            "ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "errors": errors,
    }


plan = plan_trich_luc_attachments_without_split

__all__ = ["plan", "plan_trich_luc_attachments_without_split"]
