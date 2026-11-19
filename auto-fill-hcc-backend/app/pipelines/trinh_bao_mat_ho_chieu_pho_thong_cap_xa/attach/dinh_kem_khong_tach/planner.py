"""Đính kèm Trình báo mất hộ chiếu phổ thông cấp xã (1.010386) — chế độ KHÔNG tách: mỗi tệp đính NGUYÊN một lần.

Bảng "Thành phần hồ sơ" của Cổng DVC Bộ Công an (eForm Nth, cùng khuôn hộ chiếu 1.001456) — ảnh ánh xạ chỉ có MỘT dòng:
  - dòng 1 "01 đơn trình báo mất hộ chiếu phổ thông (mẫu TK05) … (Bản chính)" (bắt buộc): đơn TK05 đã ký.
Tờ khai đề nghị cấp hộ chiếu (TK01) và thẻ căn cước dùng để điền form, KHÔNG có dòng nhận → không đính, cảnh báo. Không
nhận ra đơn trình báo mà có tệp không rõ loại → đính tệp đó vào dòng 1 kèm cảnh báo (dòng bắt buộc, thà đính để người
dùng soát còn hơn để trống). Trang không có khối "Giấy tờ khác" nên không có mục target "new".

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
from app.pipelines.chuyen_muc_dich_su_dung_dat_mien_nui_lai_chau.attach.planner import _data_url_size
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
MAX_FILE_BYTES = 6 * 1024 * 1024
_HEAD_CHARS = 600

TRINH_BAO = "trinh_bao_mat"
TO_KHAI = "to_khai"
IDENTITY = "identity"
OTHER = "other"
BLANK = "blank_page"
ALLOWED = {TRINH_BAO, TO_KHAI, IDENTITY, OTHER, BLANK}

# slotName = cột "Tên giấy tờ" trên cổng (rút gọn); slotKeywords dạng đã fold (khớp foldChoiceText của extension).
SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": "tbmhc_row01",
        "slotIndex": 0,
        "slotName": "Đơn trình báo mất hộ chiếu phổ thông (mẫu TK05)",
        "slotKeywords": ["don trinh bao mat ho chieu pho thong"],
    },
]
ROW_DOCUMENT_NAME = "Đơn trình báo mất hộ chiếu phổ thông"
TYPE_NAMES = {
    TRINH_BAO: ROW_DOCUMENT_NAME,
    TO_KHAI: "Tờ khai đề nghị cấp hộ chiếu",
    IDENTITY: "Thẻ căn cước",
}


def canonical_type(value: Any) -> str:
    folded = fold(str(value or "")).replace(" ", "_")
    return folded if folded in ALLOWED else OTHER


def rule_doc_type(text: str) -> str:
    """Luật theo TIÊU ĐỀ. Đơn trình báo nhắc "hộ chiếu" ở mọi mục → xét trước tờ khai; tờ khai mục 14 có thể ghi "cấp
    lại hộ chiếu do bị mất" nhưng không có cụm "đơn trình báo mất"."""
    haystack = fold(text)
    if not haystack.strip():
        return ""
    head = haystack[:_HEAD_CHARS]
    if re.search(r"\b(don trinh bao mat ho chieu|trinh bao mat ho chieu pho thong)\b", head):
        return TRINH_BAO
    if "to khai" in head and "ho chieu" in head:
        return TO_KHAI
    if any(marker in haystack for marker in ("can cuoc", "chung minh nhan dan", "identity card")):
        return IDENTITY
    return ""


def _clean_name(value: Any, limit: int = 250) -> str:
    text = " ".join(str(value or "").split()).strip(" .;,")
    return text[:limit].rstrip()


def _part_label(entry: dict, names: list[str]) -> str:
    label = TYPE_NAMES.get(entry["docType"]) or _clean_name(entry.get("documentName")) or names[entry["fileIndex"]]
    if entry["pages"] is not None:
        pages = [p + 1 for p in entry["pages"]]
        label += f" (trang {pages[0]}–{pages[-1]})" if len(pages) > 1 else f" (trang {pages[0]})"
    return f"{label} — {names[entry['fileIndex']]}"


def build_items(names: list[str], entries: list[dict]) -> tuple[list[dict], list[str]]:
    """Đoạn đã phân loại → (mục đính kèm, cảnh báo). Tách khỏi I/O để test, dùng chung hai chế độ.

    ``entries``: [{fileIndex, pages (0-based, None = cả tệp), docType, documentName, text}] theo thứ tự tệp, trang.
    Mọi đoạn vào dòng 1 gộp thành MỘT tệp (cổng mỗi dòng một ô chọn tệp): toàn tệp → ``sourceFileIndexes``, có đoạn cắt
    trang → ``sourceSegments``.
    """
    entries = [e for e in entries if e.get("docType") != BLANK]
    parts_of_file: dict[int, int] = {}
    for e in entries:
        parts_of_file[e["fileIndex"]] = parts_of_file.get(e["fileIndex"], 0) + 1

    def pages_of(entry: dict):
        return None if entry["pages"] is None or parts_of_file[entry["fileIndex"]] == 1 else entry["pages"]

    warnings: list[str] = []
    parts = [e for e in entries if e["docType"] == TRINH_BAO]
    if not parts:
        parts = [e for e in entries if e["docType"] == OTHER]
        if parts:
            warnings.append(
                "Không nhận ra đơn trình báo mất hộ chiếu (Mẫu TK05) — đã đính "
                + ", ".join(f"'{n}'" for n in dict.fromkeys(names[e["fileIndex"]] for e in parts))
                + " vào dòng \"Đơn trình báo mất hộ chiếu phổ thông\", vui lòng kiểm tra."
            )
    in_row = {id(e) for e in parts}
    rest = [e for e in entries if id(e) not in in_row]

    attachments: list[dict] = []
    if parts:
        slot = SLOTS[0]
        first = parts[0]["fileIndex"]
        item = {
            "fileIndex": first,
            "fileName": names[first],
            "documentName": ROW_DOCUMENT_NAME,
            "componentName": slot["slotName"],
            "target": "fixed-slot",
            "needsAddComponent": False,
            "detectedType": parts[0]["docType"],
            "slotKey": slot["slotKey"],
            "slotIndex": slot["slotIndex"],
            "slotName": slot["slotName"],
            "slotKeywords": slot["slotKeywords"],
            "tickRow": True,
        }
        if all(pages_of(p) is None for p in parts):
            files = list(dict.fromkeys(p["fileIndex"] for p in parts))
            if len(files) > 1:
                item["sourceFileIndexes"] = files
        else:
            item["sourceSegments"] = [{"fileIndex": p["fileIndex"], "pageIndexes": pages_of(p)} for p in parts]
        attachments.append(item)
        if len(parts) > 1:
            warnings.append(
                f"Dòng \"{slot['slotName']}\" đính kèm chung {len(parts)} phần (gộp một tệp): "
                + "; ".join(f"({i}) {_part_label(p, names)}" for i, p in enumerate(parts, 1)) + "."
            )
    else:
        warnings.append(
            "Hồ sơ chưa có đơn trình báo mất hộ chiếu phổ thông (Mẫu TK05) — dòng bắt buộc \"Đơn trình báo mất hộ chiếu "
            "phổ thông\" để trống; tải bổ sung bản chụp đơn đã ký."
        )
    if rest:
        warnings.append(
            "Chưa đính kèm " + "; ".join(_part_label(e, names) for e in rest)
            + " vì bảng Thành phần hồ sơ chỉ có dòng đơn trình báo mất hộ chiếu (giấy này đã dùng để điền biểu mẫu)."
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
                        "documentName": got.get("documentName") or _clean_name(Path(file.get("name") or "").stem),
                        "text": text})
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
