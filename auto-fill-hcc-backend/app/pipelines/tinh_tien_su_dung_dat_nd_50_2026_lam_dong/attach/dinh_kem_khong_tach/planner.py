"""Đính kèm KHÔNG TÁCH cho bảng thành phần hồ sơ của 1.115148 trên cổng Lâm Đồng — cài đặt tách tắt.

Bảng (ảnh bước "Thành phần hồ sơ" + file mapping Phần V, 19/11/2026) chỉ có MỘT dòng: mat-checkbox + input[type=file]
multiple "Văn bản đề nghị tính hoặc tính lại tiền sử dụng đất", loại bản ghi cứng "1 Bản chính" (không có radio) → engine
FE `attp-row`, KHÔNG gửi loaiBan, componentIndex là STT đếm từ 1. Cổng có nút "Thêm giấy tờ" nhưng danh mục trong hộp
thoại của cổng Lâm Đồng chưa crawl → không tạo dòng mới: MỌI tệp (Đơn, CCCD, Giấy chứng nhận, thông báo / chứng từ nộp
tiền, giấy ủy quyền, giấy lạ) đính vào dòng duy nhất này, mỗi tệp một lần, tên tài liệu theo loại giấy chính của tệp.

Có attachmentContext thì dò dòng THẬT trên trang theo từ khóa, gửi đúng index + tên nguyên văn; trang không có dòng đó →
dòng đầu tiên của trang + cảnh báo. Hồ sơ không có Văn bản đề nghị (vd chỉ có Đơn đề nghị cấp giấy phép xây dựng như bộ
mẫu của file mapping) → vẫn đính, cảnh báo cán bộ bổ sung. OCR phân loại dùng lại cách của đăng ký đất đai lần đầu Khánh
Hòa (chữ đủ trang từ cache bước điền), gửi LLM trích đoạn đầu từng trang.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.documents import representative_excerpt
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.attach.planner import _LLM_TEXT_MAX_CHARS, _ocr_for_classify
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_VAN_BAN = "van_ban_de_nghi"
_OTHER = "other"

_ROW = 1
ROW_NAME = "Văn bản đề nghị tính hoặc tính lại tiền sử dụng đất"
# Từ khóa (đã fold) dò dòng thật khi extension gửi attachmentContext — tên đầy đủ trước rồi cụm đặc trưng.
_KEYS: tuple[str, ...] = (_fold(ROW_NAME), "van ban de nghi tinh", "tinh lai tien su dung dat", "tien su dung dat")

# Loại giấy -> tên tài liệu khi đính. Thứ tự = ưu tiên chọn giấy chính của file gộp (Văn bản đề nghị luôn thắng).
_NAMES: dict[str, str] = {
    _VAN_BAN: "Văn bản đề nghị tính hoặc tính lại tiền sử dụng đất",
    "don_gpxd": "Đơn đề nghị cấp giấy phép xây dựng",
    "thong_bao_nop_tien": "Thông báo nộp tiền sử dụng đất",
    "chung_tu_nop_tien": "Chứng từ nộp tiền vào ngân sách nhà nước",
    "quyet_dinh": "Quyết định của cơ quan nhà nước về đất đai",
    "gcn": "Giấy chứng nhận quyền sử dụng đất",
    "authorization": "Giấy ủy quyền",
    "identity": "Căn cước công dân",
}
_PRIORITY: tuple[str, ...] = tuple(_NAMES)
_ALLOWED = set(_NAMES) | {_OTHER}


def portal_rows(options: dict | None) -> list[tuple[int, str, str]]:
    """(STT, tên nguyên văn, tên fold) các dòng extension đọc trên trang (attachmentContext); [] nếu không gửi."""
    components = ((options or {}).get("attachmentContext") or {}).get("components")
    rows: list[tuple[int, str, str]] = []
    for component in components or []:
        if not isinstance(component, dict):
            continue
        try:
            index = int(component.get("index"))
        except (TypeError, ValueError):
            continue
        name = str(component.get("componentName") or "").strip()
        if index > 0 and name:
            rows.append((index, name, _fold(name)))
    return rows


def resolve_row(rows: list[tuple[int, str, str]]) -> tuple[int, str, str | None]:
    """(STT, tên dòng gửi FE, cảnh báo). Không có attachmentContext → dòng 1 của bảng đã crawl."""
    if not rows:
        return _ROW, ROW_NAME, None
    for key in _KEYS:
        hits = [item for item in rows if key in item[2]]
        if hits:
            index, name, _ = min(hits, key=lambda item: (len(item[2]), item[0]))
            return index, name, None
    index, name, _ = rows[0]
    return index, name, f"Trang không có dòng '{ROW_NAME}' — đính vào dòng '{name[:80]}'; cán bộ kiểm tra lại."


def document_name(doc_type: str) -> str:
    return _NAMES.get(doc_type, "")


def primary(doc_types: list[str] | set[str]) -> str:
    return next((doc_type for doc_type in _PRIORITY if doc_type in doc_types), _OTHER)


def normalize_doc_type(value: Any) -> str:
    folded = _fold(str(value or ""))
    for doc_type in _ALLOWED:
        if folded == _fold(doc_type):
            return doc_type
    return _OTHER


def _doc_types(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        raw = [raw]
    out: list[str] = []
    for value in raw:
        doc_type = normalize_doc_type(value)
        if doc_type not in out:
            out.append(doc_type)
    return out


def attachment(file_index: int, file_name: str, row: int, row_name: str, name: str, doc_type: str) -> dict:
    # KHÔNG gửi loaiBan: dòng của cổng ghi cứng "1 Bản chính". Nhiều item cùng dòng → FE bơm cả loạt vào một ô multiple.
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": name,
        "componentName": row_name,
        "componentIndex": row,
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": doc_type,
    }


def missing_request_warning(found: set[str]) -> str | None:
    """Thành phần hồ sơ bắt buộc của cổng là Văn bản đề nghị — thiếu thì nhắc, kể cả khi có Đơn GPXD thay vào."""
    if _VAN_BAN in found:
        return None
    if "don_gpxd" in found:
        return (f"Hồ sơ chỉ có Đơn đề nghị cấp giấy phép xây dựng, chưa có '{ROW_NAME}' — đã đính Đơn vào dòng này; "
                "cán bộ kiểm tra lại, cần thì bổ sung văn bản đề nghị.")
    return f"Chưa nhận diện được '{ROW_NAME}' trong hồ sơ — cán bộ kiểm tra lại, cần thì bổ sung."


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, list[str]]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=600, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    result: dict[int, list[str]] = {}
    for item in parsed.get("documents", []) or []:
        try:
            result[int(item.get("index"))] = _doc_types(item.get("docTypes", item.get("docType")))
        except (TypeError, ValueError, AttributeError):
            continue
    return result


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict] | None = None,
    llm_types: dict[int, list[str] | str] | None = None,
    rows: list[tuple[int, str, str]] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    del ocr_results  # LLM-first: không suy luận rule từ OCR text ở đây.
    types_by_file = {index: _doc_types(raw) for index, raw in (llm_types or {}).items() if raw}
    row, row_name, note = resolve_row(rows or [])
    attachments: list[dict] = []
    warnings: list[str] = [note] if note else []
    classified: list[dict] = []
    found: set[str] = set()

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        doc_types = types_by_file.get(index, [])
        found.update(doc_types)
        doc_type = primary(doc_types)
        bundled = [item for item in doc_types if item in _NAMES]
        # File gộp nhiều giấy hoặc không rõ loại giữ TÊN GỐC để cán bộ nhận ra; file một giấy mang tên giấy.
        name = file_name if len(bundled) > 1 or doc_type == _OTHER else document_name(doc_type)
        attachments.append(attachment(index, file_name, row, row_name, name, doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "docTypes": doc_types,
                           "source": "llm" if index in types_by_file else "unknown", "rows": [row]})
        if doc_type == _OTHER:
            warnings.append(f"Chưa nhận diện chắc loại giấy tờ cho '{file_name}' — vẫn đính vào dòng {row}; cán bộ "
                            "kiểm tra lại.")
        elif len(bundled) > 1:
            warnings.append(f"'{file_name}' gộp nhiều giấy tờ ({', '.join(document_name(t) for t in bundled)}) — đính "
                            f"nguyên file một lần vào dòng {row}.")

    if files:
        message = missing_request_warning(found)
        if message:
            warnings.append(message)
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    rows = portal_rows(options)
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    ocr_files = [item for item in raw_files if item.get("type") in _OCR_TYPES]
    errors: list[str] = []

    started = time.monotonic()
    ocr_results = await _ocr_for_classify(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    llm_documents = [
        {"index": index, "text": representative_excerpt(str(by_name[file.get("name")].get("text")),
                                                        _LLM_TEXT_MAX_CHARS)}
        for index, file in enumerate(raw_files)
        if str(by_name.get(file.get("name"), {}).get("text") or "").strip()
    ]
    started = time.monotonic()
    llm_types: dict[int, list[str]] = {}
    if llm_documents:
        try:
            llm_types = await _classify_with_llm(llm_documents)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types, rows)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [item["name"] for item in raw_files],
            "ocrDocuments": [item.get("name") for item in ocr_results if item.get("text")],
            "llmDocuments": [raw_files[item["index"]]["name"] for item in llm_documents],
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
