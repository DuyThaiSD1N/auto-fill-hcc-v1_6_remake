"""Đính kèm "Đăng ký hoạt động của Trung tâm tư vấn pháp luật" (1.000627) — chế độ KHÔNG tách giấy tờ.

Bảng "Thành phần hồ sơ" trên cổng (wizard tư pháp DVCQG) theo ảnh ánh xạ 18/11/2026:
  1. Danh sách kèm theo hồ sơ của người được đề nghị cấp Thẻ tư vấn viên pháp luật, của luật sư làm việc theo hợp
     đồng lao động cho Trung tâm                                                                    → staff_list
  2. Dự thảo quy chế tổ chức, hoạt động của Trung tâm tư vấn do tổ chức chủ quản ban hành         → charter
  3. Quyết định của tổ chức chủ quản về việc thành lập Trung tâm; về việc cử Giám đốc Trung tâm   → decision
  4. Đơn đăng ký hoạt động (Bắt buộc) — "Tờ khai.pdf" cổng tự sinh từ bước Kê khai → KHÔNG đính Đơn bản giấy lên
     (trùng nội dung). Danh mục hồ sơ chỉ dùng khi nộp giấy, CCCD của Giám đốc chỉ để đối chiếu tờ khai → không đính,
     báo trong cảnh báo. Không dùng "Thêm thành phần hồ sơ" cho các giấy trên.

Mỗi thành phần = đúng MỘT tệp: nhiều tệp cùng dòng gộp một PDF (``sourceFileIndexes``, theo thứ tự tải lên), mỗi tệp
đính nguyên khối. Tệp gộp nhiều giấy thuộc dòng của giấy CHÍNH (tiêu đề xuất hiện sớm nhất); dòng không có tệp riêng
mà nằm trong tệp gộp đó thì đính nguyên tệp đó vào dòng ấy (trừ Danh mục hồ sơ — bảng kê nhắc tên mọi giấy). Giấy lạ
(other) → "Thêm thành phần hồ sơ" mang tên giấy để không bỏ tệp. Dòng thiếu giấy → để trống + cảnh báo cần bổ sung.

Phân loại: tiêu đề giấy (rule) trước; tệp rule không nhận ra mới hỏi LLM (MỘT lượt), LLM lỗi thì rule căn cước / other.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold
from app.pipelines._shared.compact_agent.runner import _extract_docx_text, _is_docx
from app.pipelines._shared.identity_merge import _looks_like_cccd
from app.pipelines.xac_nhan_thong_tin_ho_tich.attach.planner import _coerce_int, _unique_document_name
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

STAFF_LIST = "staff_list"
CHARTER = "charter"
DECISION = "decision"
APPLICATION = "application"
DOSSIER_INDEX = "dossier_index"
IDENTITY = "identity"
OTHER = "other"
ALLOWED_TYPES = {STAFF_LIST, CHARTER, DECISION, APPLICATION, DOSSIER_INDEX, IDENTITY, OTHER}

# (STT dòng trên cổng, loại giấy, đoạn chữ RIÊNG của dòng để extension khớp, tên tài liệu đính vào dòng).
ROWS: tuple[tuple[int, str, str, str], ...] = (
    (1, STAFF_LIST, "Danh sách kèm theo hồ sơ của người được đề nghị cấp Thẻ tư vấn viên pháp luật",
     "Danh sách tư vấn viên pháp luật, luật sư kèm hồ sơ"),
    (2, CHARTER, "Dự thảo quy chế tổ chức, hoạt động của Trung tâm tư vấn",
     "Dự thảo Quy chế tổ chức, hoạt động"),
    (3, DECISION, "Quyết định của tổ chức chủ quản về việc thành lập Trung tâm tư vấn pháp luật",
     "Quyết định thành lập và cử Giám đốc Trung tâm"),
)
ROW_TYPES = {doc_type for _, doc_type, _, _ in ROWS}

# Câu báo thiếu theo đúng chữ trên bảng thành phần hồ sơ.
MISSING = {
    STAFF_LIST: "Danh sách kèm theo hồ sơ của người được đề nghị cấp Thẻ tư vấn viên pháp luật, của luật sư làm việc "
                "theo hợp đồng lao động cho Trung tâm",
    CHARTER: "Dự thảo quy chế tổ chức, hoạt động của Trung tâm tư vấn do tổ chức chủ quản ban hành",
    DECISION: "Quyết định của tổ chức chủ quản về việc thành lập Trung tâm tư vấn pháp luật; về việc cử Giám đốc",
}

# Giấy không đính (cổng đã có / không thuộc thành phần hồ sơ) → lý do báo trong cảnh báo.
SKIPPED = {
    APPLICATION: "Đơn đăng ký hoạt động đã có ở dòng 4 (Tờ khai cổng tự sinh từ bước Kê khai) nên không đính lại",
    DOSSIER_INDEX: "Danh mục hồ sơ chỉ dùng khi nộp hồ sơ giấy nên không đính",
    IDENTITY: "Căn cước của Giám đốc chỉ dùng để đối chiếu tờ khai, không thuộc thành phần hồ sơ nên không đính",
}

OTHER_LABEL = "Tài liệu khác"

# Tiêu đề giấy (đã fold, bỏ dấu câu). Chọn cụm riêng của TIÊU ĐỀ: Quyết định cử Giám đốc có câu "… Quy chế tổ chức,
# hoạt động của Trung tâm" (không có chữ "và … tư vấn pháp luật"), Đơn có dòng "Danh sách tư vấn viên pháp luật, luật
# sư và nhân viên khác" — không trùng cụm của Quy chế / danh sách hồ sơ nhân sự.
_TITLE_MARKERS: dict[str, tuple[str, ...]] = {
    APPLICATION: (
        "don dang ky hoat dong cua trung tam tu van phap luat",
        "tp tvpl 01",
    ),
    DOSSIER_INDEX: ("danh muc ho so",),
    CHARTER: (
        "quy che to chuc va hoat dong cua trung tam tu van phap luat",
        "du thao quy che to chuc",
    ),
    DECISION: (
        "ve viec thanh lap trung tam tu van phap luat",
        "ve viec cu giam doc trung tam tu van phap luat",
    ),
    STAFF_LIST: (
        "danh sach kem theo ho so",
        "giay de nghi cap the tu van vien phap luat",
        "tp tvpl 05",
    ),
}


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", fold(text or "")).strip()


def rule_types(text: str) -> list[str]:
    """Các loại giấy có tiêu đề trong tệp, xếp theo vị trí xuất hiện (giấy chính đứng đầu)."""
    haystack = _norm(text)
    if not haystack:
        return []
    first_hit: dict[str, int] = {}
    for doc_type, markers in _TITLE_MARKERS.items():
        positions = [haystack.find(marker) for marker in markers if marker in haystack]
        if positions:
            first_hit[doc_type] = min(positions)
    return sorted(first_hit, key=first_hit.get)


def canonical_type(value: Any) -> str:
    raw = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    aliases = {
        "danh_sach": STAFF_LIST, "staff": STAFF_LIST, "personnel": STAFF_LIST,
        "quy_che": CHARTER, "regulation": CHARTER,
        "quyet_dinh": DECISION, "decision_document": DECISION,
        "don": APPLICATION, "application_form": APPLICATION, "to_khai": APPLICATION,
        "danh_muc": DOSSIER_INDEX, "index": DOSSIER_INDEX,
        "cccd": IDENTITY, "cmnd": IDENTITY, "id": IDENTITY, "passport": IDENTITY,
    }
    raw = aliases.get(raw, raw)
    return raw if raw in ALLOWED_TYPES else OTHER


def validated_classifications(raw_items: list[dict], file_count: int) -> dict[int, dict]:
    result: dict[int, dict] = {}
    for raw in raw_items or []:
        if not isinstance(raw, dict):
            continue
        file_index = _coerce_int(raw.get("fileIndex", raw.get("index")))
        if file_index is None or not 0 <= file_index < file_count or file_index in result:
            continue
        result[file_index] = {
            "type": canonical_type(raw.get("type") or raw.get("docType")),
            "documentName": str(raw.get("documentName") or raw.get("title") or "").strip(),
        }
    return result


async def _classify_with_llm(documents: list[dict[str, Any]]) -> list[dict]:
    if not documents:
        return []
    raw = await client.chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(documents)},
        ],
        max_tokens=max(600, min(2000, len(documents) * 160)),
        enable_thinking=settings.agent_reasoning,
    )
    parsed = client.extract_json_block(raw)
    return parsed.get("documents", []) if isinstance(parsed, dict) else []


def row_item(row: int, doc_type: str, component: str, label: str, file_index: int, file_name: str,
             used_names: set[str]) -> dict:
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": _unique_document_name(label, used_names, label),
        "componentName": component,
        "target": "existing",
        "componentIndex": row,
        "needsAddComponent": False,
        "detectedType": doc_type,
    }


def new_item(file_index: int, file_name: str, base_name: str, used_names: set[str]) -> dict:
    document_name = _unique_document_name(base_name or OTHER_LABEL, used_names, OTHER_LABEL)
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": document_name,
        "target": "new",
        "componentIndex": None,
        "needsAddComponent": True,
        "detectedType": OTHER,
    }


def skipped_warnings(skipped: dict[str, list[str]]) -> list[str]:
    """{loại giấy: [tên tệp / đoạn trang]} → câu cảnh báo theo lý do không đính."""
    return [f"{SKIPPED[doc_type]}: {', '.join(names)}." for doc_type, names in skipped.items() if names]


def build_plan_items(
    raw_files: list[dict],
    ocr_text_by_index: dict[int, str],
    llm_by_index: dict[int, dict] | None = None,
) -> tuple[list[dict], list[dict], list[str]]:
    """Dựng kế hoạch đính kèm từ loại giấy đã phân (tách khỏi I/O để test)."""
    llm_by_index = llm_by_index or {}

    def file_name(index: int) -> str:
        return str(raw_files[index].get("name") or f"file-{index + 1}")

    main_type: dict[int, str] = {}
    covers: dict[int, list[str]] = {}
    source: dict[int, str] = {}
    for index in range(len(raw_files)):
        text = ocr_text_by_index.get(index, "")
        found = rule_types(text)
        if found:
            main_type[index], covers[index], source[index] = found[0], found, "rule"
            continue
        llm_item = llm_by_index.get(index)
        if llm_item:
            doc_type, source[index] = llm_item["type"], "llm"
        else:
            doc_type, source[index] = (IDENTITY if _looks_like_cccd(text) else OTHER), "default"
        main_type[index], covers[index] = doc_type, [doc_type]

    used_names: set[str] = set()
    attachments: list[dict] = []
    rows_by_file: dict[int, list[int]] = {index: [] for index in range(len(raw_files))}
    warnings: list[str] = []
    shared_notes: list[str] = []

    for row, doc_type, component, label in ROWS:
        primary = [i for i in range(len(raw_files)) if main_type[i] == doc_type]
        # Không có tệp riêng → dùng tệp gộp có chứa giấy này (đính nguyên tệp); bảng kê Danh mục hồ sơ không tính.
        sources = primary or [
            i for i in range(len(raw_files)) if doc_type in covers[i] and main_type[i] != DOSSIER_INDEX
        ]
        if not sources:
            warnings.append(f"Hồ sơ đã gửi không có {MISSING[doc_type]} (dòng {row}). Cần bổ sung.")
            continue
        if not primary:
            shared_notes.append(f"dòng {row}: " + ", ".join(file_name(i) for i in sources))
        item = row_item(row, doc_type, component, label, sources[0], file_name(sources[0]), used_names)
        if len(sources) > 1:
            item["sourceFileIndexes"] = sources
        attachments.append(item)
        for index in sources:
            rows_by_file[index].append(row)

    skipped: dict[str, list[str]] = {doc_type: [] for doc_type in SKIPPED}
    extra_files: list[str] = []
    for index in range(len(raw_files)):
        doc_type = main_type[index]
        if doc_type in ROW_TYPES:
            continue
        if doc_type in SKIPPED:
            # Tệp gộp đã đính vào một dòng (vd Đơn kèm Quy chế) thì không báo bỏ.
            if not rows_by_file[index]:
                skipped[doc_type].append(file_name(index))
            continue
        base = (llm_by_index.get(index) or {}).get("documentName") or ""
        attachments.append(new_item(index, file_name(index), base, used_names))
        extra_files.append(file_name(index))

    classified = []
    for index in range(len(raw_files)):
        rows = rows_by_file[index]
        classified.append({
            "fileIndex": index,
            "fileName": file_name(index),
            "type": main_type[index],
            "covers": covers[index],
            "source": source[index],
            "target": "existing" if rows else ("skip" if main_type[index] in SKIPPED else "new"),
            "componentIndex": rows[0] if rows else None,
            "componentIndexes": rows,
        })

    if shared_notes:
        warnings.append(
            "Tệp chứa nhiều giấy được đính nguyên tệp vào cả dòng không có tệp riêng — " + "; ".join(shared_notes) + "."
        )
    warnings.extend(skipped_warnings(skipped))
    if extra_files:
        warnings.append("Giấy tờ ngoài 3 thành phần hồ sơ đã thêm thành phần hồ sơ mới: " + ", ".join(extra_files) + ".")
    return attachments, classified, warnings


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file([f for _, f in ocr_pairs]) if ocr_pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    ocr_by_index = {i: result for (i, _), result in zip(ocr_pairs, ocr_results)}
    for i, result in ocr_by_index.items():
        if result.get("error"):
            errors.append(f"OCR fileIndex={i} {raw_files[i].get('name')}: {result['error']}")
    ocr_text_by_index = {i: str((ocr_by_index.get(i) or {}).get("text") or "") for i in range(len(raw_files))}
    for i, f in enumerate(raw_files):
        if _is_docx(f) and not ocr_text_by_index[i]:
            ocr_text_by_index[i] = str(_extract_docx_text(f).get("text") or "")

    # Chỉ hỏi LLM những tệp tiêu đề không nhận ra — hồ sơ đúng mẫu thì không tốn lượt gọi.
    llm_docs = [
        {"fileIndex": i, "ocrText": ocr_text_by_index[i][:12000]}
        for i in range(len(raw_files))
        if not rule_types(ocr_text_by_index[i])
    ]
    started = time.monotonic()
    raw_classifications: list[dict] = []
    if llm_docs:
        try:
            raw_classifications = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001 - rule dự phòng vẫn giữ đủ tệp
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    llm_indexes = {doc["fileIndex"] for doc in llm_docs}
    llm_by_index = {
        i: item for i, item in validated_classifications(raw_classifications, len(raw_files)).items()
        if i in llm_indexes
    }
    attachments, classified, warnings = build_plan_items(raw_files, ocr_text_by_index, llm_by_index)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [raw_files[i].get("name") for i, r in ocr_by_index.items() if r.get("text")],
            "llmDocuments": [raw_files[doc["fileIndex"]]["name"] for doc in llm_docs],
            "sessionId": (session or {}).get("request_id"),
            "attachmentMode": "preserve_files",
            "classified": classified,
            "skippedOcr": [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES and not _is_docx(f)],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
