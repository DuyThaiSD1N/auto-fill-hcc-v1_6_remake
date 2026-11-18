"""Đính kèm Đăng ký mẫu con dấu mới (2.001428) — chế độ KHÔNG tách: mỗi tệp đính NGUYÊN một lần.

Trang "Thông tin hồ sơ" của Cổng DVC Bộ Công an (eForm Nth, cùng khuôn cổng Lai Châu) — ảnh ánh xạ bộ mẫu 18/11/2026:
  - bảng "Thành phần hồ sơ" 2 dòng cố định, mỗi dòng checkbox + "Số bản" (cổng để sẵn 1) + nút "Chọn tệp tin":
      dòng 1 "Quyết định công nhận tổ chức của cơ quan có thẩm quyền."  ← quyết định thành lập (kèm danh sách);
      dòng 2 "Giấy giới thiệu hoặc giấy ủy quyền."                       ← văn bản đề nghị (mục 6 giới thiệu người nộp);
        có giấy giới thiệu / ủy quyền RIÊNG thì giấy đó vào dòng 2, văn bản đề nghị sang "Giấy tờ khác";
  - "Về việc" cổng điền sẵn tên thủ tục (giữ nguyên);
  - "Giấy tờ khác" (``HoSoOnline_giayToKhac[]`` tên + tệp): văn bản đồng ý khắc dấu (tên = số, ngày, cơ quan, trích
    yếu), CCCD người nộp, giấy không rõ loại.
Ghi chú tổng hợp tệp trong ảnh ánh xạ là tuỳ chọn — extension chưa có engine điền ô Ghi chú, bỏ qua.

Phân loại: LLM trước, LLM trả other / lỗi thì luật theo TIÊU ĐỀ. Cổng chặn 6 MB/tệp → tệp vượt bị loại kèm cảnh báo.
``build_items`` dùng chung với chế độ tách (đoạn trang thay cho cả tệp).
"""

import re
import time
from pathlib import Path
from typing import Any

from app.config import settings
from app.pipelines._shared import fold
from app.pipelines._shared.compact_agent.runner import _extract_docx_text, _is_docx
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.chuyen_muc_dich_su_dung_dat_mien_nui_lai_chau.attach.planner import (
    _data_url_size,
    _identity_holder_name,
)
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
MAX_FILE_BYTES = 6 * 1024 * 1024
_HEAD_CHARS = 600

QUYET_DINH = "quyet_dinh_thanh_lap"
DE_NGHI = "van_ban_de_nghi"
GIOI_THIEU = "giay_gioi_thieu"
DONG_Y = "van_ban_dong_y"
IDENTITY = "identity"
OTHER = "other"
BLANK = "blank_page"
ALLOWED = {QUYET_DINH, DE_NGHI, GIOI_THIEU, DONG_Y, IDENTITY, OTHER, BLANK}

# slotName = cột "Tên giấy tờ" trên cổng; slotKeywords dạng đã fold (khớp foldChoiceText của extension).
SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": "dkmcd_row01",
        "slotIndex": 0,
        "slotName": "Quyết định công nhận tổ chức của cơ quan có thẩm quyền.",
        "slotKeywords": ["quyet dinh cong nhan to chuc"],
    },
    {
        "slotKey": "dkmcd_row02",
        "slotIndex": 1,
        "slotName": "Giấy giới thiệu hoặc giấy ủy quyền.",
        "slotKeywords": ["giay gioi thieu hoac giay uy quyen"],
    },
]
ROW_DOCUMENT_NAMES = {
    QUYET_DINH: "Quyết định thành lập cơ quan, tổ chức",
    DE_NGHI: "Văn bản đề nghị đăng ký mẫu con dấu",
    GIOI_THIEU: "Giấy giới thiệu",
}
# Tên ở "Giấy tờ khác" khi LLM không đặt được tên riêng.
OTHER_NAMES = {
    DE_NGHI: "Văn bản đề nghị đăng ký mẫu con dấu",
    DONG_Y: "Văn bản đồng ý khắc dấu",
    QUYET_DINH: "Quyết định thành lập cơ quan, tổ chức",
    GIOI_THIEU: "Giấy giới thiệu",
}


def canonical_type(value: Any) -> str:
    folded = fold(str(value or "")).replace(" ", "_")
    return folded if folded in ALLOWED else OTHER


def rule_doc_type(text: str) -> str:
    """Luật theo TIÊU ĐỀ (phần đầu văn bản). Văn bản đề nghị nhắc quyết định + công văn trong thân → xét trước."""
    haystack = fold(text)
    if not haystack.strip():
        return ""
    head = haystack[:_HEAD_CHARS]
    if "de nghi dang ky mau con dau" in head or "co quan, to chuc de nghi dang ky mau con dau" in haystack:
        return DE_NGHI
    if re.search(r"\bgiay (gioi thieu|uy quyen)\b", head[:200]):
        return GIOI_THIEU
    if re.search(r"\bkhac (moi )?(con )?dau\b", head):
        return DONG_Y
    if "quyet dinh" in head and re.search(r"\b(thanh lap|cong nhan|cho phep)\b", head):
        return QUYET_DINH
    if any(marker in haystack for marker in ("can cuoc", "chung minh nhan dan", "identity card", "passport")):
        return IDENTITY
    return ""


def _clean_name(value: Any, limit: int = 250) -> str:
    text = " ".join(str(value or "").split()).strip(" .;,")
    return text[:limit].rstrip()


def _slot_item(slot: dict, file_index: int, file_name: str, doc_type: str, document_name: str) -> dict:
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": slot["slotName"],
        "target": "fixed-slot",
        "needsAddComponent": False,
        "detectedType": doc_type,
        "slotKey": slot["slotKey"],
        "slotIndex": slot["slotIndex"],
        "slotName": slot["slotName"],
        "slotKeywords": slot["slotKeywords"],
        "tickRow": True,
    }


def _other_item(file_index: int, file_name: str, doc_type: str, name: str) -> dict:
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": name,
        "componentName": name,
        "target": "new",
        "componentIndex": None,
        "needsAddComponent": True,
        "detectedType": doc_type,
    }


def build_items(names: list[str], entries: list[dict]) -> tuple[list[dict], list[str]]:
    """Đoạn đã phân loại → (mục đính kèm, cảnh báo). Tách khỏi I/O để test, dùng chung hai chế độ.

    ``entries``: [{fileIndex, pages (0-based, None = cả tệp), docType, documentName, text}] theo thứ tự tệp, trang.
    Đoạn cùng dòng bảng gộp thành MỘT tệp (cổng mỗi dòng một ô chọn tệp): toàn tệp → ``sourceFileIndexes``, có đoạn
    cắt trang → ``sourceSegments``.
    """
    entries = [e for e in entries if e.get("docType") != BLANK]
    parts_of_file: dict[int, int] = {}
    for e in entries:
        parts_of_file[e["fileIndex"]] = parts_of_file.get(e["fileIndex"], 0) + 1

    def pages_of(entry: dict):
        return None if entry["pages"] is None or parts_of_file[entry["fileIndex"]] == 1 else entry["pages"]

    by_type: dict[str, list[dict]] = {}
    for e in entries:
        by_type.setdefault(e["docType"], []).append(e)
    row_types = {0: QUYET_DINH, 1: GIOI_THIEU if by_type.get(GIOI_THIEU) else DE_NGHI}

    attachments: list[dict] = []
    warnings: list[str] = []
    used: set[int] = set()
    for slot in SLOTS:
        doc_type = row_types[slot["slotIndex"]]
        parts = by_type.get(doc_type) or []
        if not parts:
            label = "Quyết định thành lập / công nhận tổ chức" if doc_type == QUYET_DINH else \
                "Giấy giới thiệu hoặc văn bản đề nghị (mục 6 giới thiệu người nộp)"
            warnings.append(f"Hồ sơ đã gửi chưa có {label} cho dòng \"{slot['slotName']}\" — cần bổ sung.")
            continue
        first = parts[0]["fileIndex"]
        item = _slot_item(slot, first, names[first], doc_type, ROW_DOCUMENT_NAMES[doc_type])
        if all(pages_of(p) is None for p in parts):
            files = list(dict.fromkeys(p["fileIndex"] for p in parts))
            if len(files) > 1:
                item["sourceFileIndexes"] = files
        else:
            item["sourceSegments"] = [{"fileIndex": p["fileIndex"], "pageIndexes": pages_of(p)} for p in parts]
        attachments.append(item)
        used.update(id(p) for p in parts)

    seen_names: dict[str, int] = {}
    unknown: list[str] = []
    for e in entries:
        if id(e) in used:
            continue
        file_name = names[e["fileIndex"]]
        doc_type = e["docType"]
        if doc_type == IDENTITY:
            holder = _identity_holder_name(e.get("text") or "")
            name = f"Căn cước người nộp - {holder}" if holder else "Căn cước người nộp"
        else:
            name = _clean_name(e.get("documentName")) or OTHER_NAMES.get(doc_type) or ""
            if not name:
                name = _clean_name(Path(file_name).stem) or "Giấy tờ khác"
                unknown.append(file_name)
        count = seen_names[name.lower()] = seen_names.get(name.lower(), 0) + 1
        if count > 1:
            name = f"{name} ({count})"
        item = _other_item(e["fileIndex"], file_name, doc_type, name)
        pages = pages_of(e)
        if pages is not None:
            item["sourceSegments"] = [{"fileIndex": e["fileIndex"], "pageIndexes": pages}]
        attachments.append(item)
    if unknown:
        warnings.append(
            "Không xác định được loại giấy tờ của " + ", ".join(f"'{n}'" for n in dict.fromkeys(unknown))
            + " — đã đính vào \"Giấy tờ khác\", vui lòng kiểm tra."
        )
    return attachments, warnings


async def classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=900, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    result: dict[int, dict] = {}
    for item in parsed.get("documents", []) or []:
        try:
            result[int(item.get("index"))] = {
                "docType": canonical_type(item.get("docType") or item.get("type")),
                "documentName": _clean_name(item.get("documentName")),
            }
        except (TypeError, ValueError):
            continue
    return result


def classify_files(files: list[dict], texts: dict[str, str], llm: dict[int, dict]) -> list[dict]:
    """Mỗi tệp một đoạn (cả tệp): loại theo LLM, LLM other / thiếu → luật tiêu đề."""
    entries = []
    for index, file in enumerate(files):
        text = texts.get(file.get("name"), "")
        got = llm.get(index) or {}
        doc_type = got.get("docType") or OTHER
        if doc_type in (OTHER, BLANK):
            doc_type = rule_doc_type(text) or OTHER
        entries.append({"fileIndex": index, "pages": None, "docType": doc_type,
                        "documentName": got.get("documentName") or "", "text": text})
    return entries


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    names = [str(f.get("name") or f"file-{i + 1}") for i, f in enumerate(raw_files)]
    errors: list[str] = []

    keep = [i for i, f in enumerate(raw_files) if _data_url_size(f.get("dataUrl", "")) <= MAX_FILE_BYTES]
    for i in range(len(raw_files)):
        if i not in keep:
            size = _data_url_size(raw_files[i].get("dataUrl", ""))
            errors.append(
                f"File '{names[i]}' nặng {size / 1024 / 1024:.1f} MB, vượt giới hạn 6 MB của cổng — hãy tách nhỏ hoặc "
                "giảm độ phân giải (mỗi tệp dưới 6 MB) rồi đính kèm lại."
            )
    small = [raw_files[i] for i in keep]
    ocr_files = [f for f in small if f.get("type") in _OCR_TYPES]

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_results.extend(_extract_docx_text(f) for f in small if _is_docx(f))
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")
    texts = {item.get("name"): str(item.get("text") or "") for item in ocr_results}

    documents = [{"index": i, "name": names[i], "text": texts.get(names[i], "")}
                 for i in keep if texts.get(names[i], "").strip()]
    started = time.monotonic()
    llm: dict[int, dict] = {}
    if documents:
        try:
            llm = await classify_with_llm(documents)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    entries = [e for e in classify_files(raw_files, texts, llm) if e["fileIndex"] in keep]
    attachments, warnings = build_items(names, entries)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": names,
            "classified": [{"fileName": names[e["fileIndex"]], "docType": e["docType"]} for e in entries],
            "slots": SLOTS,
            "attachmentMode": "whole",
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "ocr_text": join_ocr_documents(ocr_results),
        "llm_output": {str(k): v for k, v in llm.items()},
        "errors": errors,
    }
