"""Đính kèm Cấp hộ chiếu phổ thông ở trong nước (1.001456) — chế độ KHÔNG tách: mỗi tệp đính NGUYÊN một lần.

Bảng "Thành phần hồ sơ" của Cổng DVC Bộ Công an (eForm Nth, cùng khuôn mẫu con dấu) — ảnh ánh xạ bộ mẫu 18/11/2026:
  - dòng 1 "+ Bản chụp có chứng thực giấy tờ … chứng minh người đại diện hợp pháp …" (Bản sao): chỉ dùng khi hồ sơ có
    giấy tờ người đại diện (người chưa đủ 14 tuổi / mất năng lực hành vi). Người thành niên tự nộp → KHÔNG tick, không
    đính;
  - dòng 2 "+ Hộ chiếu phổ thông cấp lần gần nhất …" (Bản chính): hộ chiếu cũ; bị mất thì đơn trình báo mất / thông
    báo tiếp nhận đơn. Bảng không có dòng riêng cho tờ khai nên tờ khai (và giấy còn lại) ĐÍNH KÈM CHUNG vào dòng 2,
    hộ chiếu đứng trước (ảnh ánh xạ: "[F1] hộ chiếu, [F2] tờ khai").
Cấp lần đầu (không hộ chiếu cũ, không đơn trình báo mất) → dòng 2 không áp dụng, giấy còn lại không đính, cảnh báo.
Trang này không có khối "Giấy tờ khác" (ảnh ánh xạ) nên không có mục target "new".

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

HO_CHIEU = "ho_chieu"
TO_KHAI = "to_khai"
TRINH_BAO = "trinh_bao_mat"
DAI_DIEN = "dai_dien_hop_phap"
IDENTITY = "identity"
OTHER = "other"
BLANK = "blank_page"
# Ảnh chân dung 4x6: đã gắn ở ô tải ảnh đầu trang kê khai (process runner) → không đính vào bảng Thành phần hồ sơ.
PORTRAIT = "anh_chan_dung"
ALLOWED = {HO_CHIEU, TO_KHAI, TRINH_BAO, DAI_DIEN, IDENTITY, OTHER, BLANK}
# Thứ tự ghép trong dòng 2: hộ chiếu (giấy chính của dòng) → đơn trình báo mất → tờ khai → giấy còn lại.
ROW2_ORDER = (HO_CHIEU, TRINH_BAO, TO_KHAI, IDENTITY, OTHER)

# slotName = cột "Tên giấy tờ" trên cổng (rút gọn); slotKeywords dạng đã fold (khớp foldChoiceText của extension).
SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": "hcpt_row01",
        "slotIndex": 0,
        "slotName": "Bản chụp có chứng thực giấy tờ chứng minh người đại diện hợp pháp",
        "slotKeywords": ["chung minh nguoi dai dien hop phap"],
    },
    {
        "slotKey": "hcpt_row02",
        "slotIndex": 1,
        "slotName": "Hộ chiếu phổ thông cấp lần gần nhất",
        "slotKeywords": ["ho chieu pho thong cap lan gan nhat"],
    },
]
ROW_DOCUMENT_NAMES = {
    0: "Giấy tờ chứng minh người đại diện hợp pháp",
    1: "Hộ chiếu phổ thông cấp lần gần nhất",
}
# Tên từng giấy trong câu ghi chú "dòng 2 đính kèm chung".
TYPE_NAMES = {
    HO_CHIEU: "Hộ chiếu phổ thông cấp lần gần nhất",
    TRINH_BAO: "Đơn trình báo mất hộ chiếu",
    TO_KHAI: "Tờ khai đề nghị cấp hộ chiếu",
    IDENTITY: "Thẻ căn cước",
    DAI_DIEN: "Giấy tờ người đại diện hợp pháp",
}


def canonical_type(value: Any) -> str:
    folded = fold(str(value or "")).replace(" ", "_")
    return folded if folded in ALLOWED else OTHER


def rule_doc_type(text: str) -> str:
    """Luật theo TIÊU ĐỀ. Tờ khai nhắc "hộ chiếu" trong thân → xét trước hộ chiếu; hộ chiếu in "ID card" → trước CCCD."""
    haystack = fold(text)
    if not haystack.strip():
        return ""
    head = haystack[:_HEAD_CHARS]
    if "to khai" in head and "ho chieu" in head:
        return TO_KHAI
    if re.search(r"\b(don trinh bao mat|trinh bao mat ho chieu|tiep nhan don trinh bao)\b", head):
        return TRINH_BAO
    if "p<vnm" in haystack.replace(" ", "") or re.search(r"\b(passport|issuing authority|co quan cap ho chieu)\b",
                                                         haystack):
        return HO_CHIEU
    if re.search(r"\b(giay khai sinh|trich luc khai sinh|giam ho|nguoi dai dien hop phap)\b", head):
        return DAI_DIEN
    if any(marker in haystack for marker in ("can cuoc", "chung minh nhan dan", "identity card")):
        return IDENTITY
    return ""


def _clean_name(value: Any, limit: int = 250) -> str:
    text = " ".join(str(value or "").split()).strip(" .;,")
    return text[:limit].rstrip()


def _slot_item(slot: dict, file_index: int, file_name: str, doc_type: str) -> dict:
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": ROW_DOCUMENT_NAMES[slot["slotIndex"]],
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


def _part_label(entry: dict, names: list[str]) -> str:
    label = TYPE_NAMES.get(entry["docType"]) or _clean_name(entry.get("documentName")) or names[entry["fileIndex"]]
    if entry["pages"] is not None:
        pages = [p + 1 for p in entry["pages"]]
        label += f" (trang {pages[0]}–{pages[-1]})" if len(pages) > 1 else f" (trang {pages[0]})"
    return f"{label} — {names[entry['fileIndex']]}"


def build_items(names: list[str], entries: list[dict]) -> tuple[list[dict], list[str]]:
    """Đoạn đã phân loại → (mục đính kèm, cảnh báo). Tách khỏi I/O để test, dùng chung hai chế độ.

    ``entries``: [{fileIndex, pages (0-based, None = cả tệp), docType, documentName, text}] theo thứ tự tệp, trang.
    Đoạn cùng dòng bảng gộp thành MỘT tệp (cổng mỗi dòng một ô chọn tệp): toàn tệp → ``sourceFileIndexes``, có đoạn
    cắt trang → ``sourceSegments``.
    """
    portraits = [e for e in entries if e.get("docType") == PORTRAIT]
    entries = [e for e in entries if e.get("docType") not in (BLANK, PORTRAIT)]
    parts_of_file: dict[int, int] = {}
    for e in entries:
        parts_of_file[e["fileIndex"]] = parts_of_file.get(e["fileIndex"], 0) + 1

    def pages_of(entry: dict):
        return None if entry["pages"] is None or parts_of_file[entry["fileIndex"]] == 1 else entry["pages"]

    representative = [e for e in entries if e["docType"] == DAI_DIEN]
    rest = [e for e in entries if e["docType"] != DAI_DIEN]
    rest.sort(key=lambda e: ROW2_ORDER.index(e["docType"]) if e["docType"] in ROW2_ORDER else len(ROW2_ORDER))
    row2_applies = any(e["docType"] in (HO_CHIEU, TRINH_BAO) for e in rest)

    attachments: list[dict] = []
    warnings: list[str] = [
        f"Ảnh chân dung '{names[e['fileIndex']]}' không đính vào Thành phần hồ sơ — đã gắn vào ô Ảnh chân dung đầu "
        "trang kê khai (đổi sang .jpg), kiểm tra đúng ảnh 4x6 nền trắng của người đề nghị." for e in portraits
    ]
    for slot, parts in ((SLOTS[0], representative), (SLOTS[1], rest if row2_applies else [])):
        if not parts:
            continue
        first = parts[0]["fileIndex"]
        item = _slot_item(slot, first, names[first], parts[0]["docType"])
        if all(pages_of(p) is None for p in parts):
            files = list(dict.fromkeys(p["fileIndex"] for p in parts))
            if len(files) > 1:
                item["sourceFileIndexes"] = files
        else:
            item["sourceSegments"] = [{"fileIndex": p["fileIndex"], "pageIndexes": pages_of(p)} for p in parts]
        attachments.append(item)
        if len(parts) > 1:
            warnings.append(
                f"Dòng \"{slot['slotName']}\" đính kèm chung {len(parts)} giấy (gộp một tệp): "
                + "; ".join(f"({i}) {_part_label(p, names)}" for i, p in enumerate(parts, 1)) + "."
            )

    if not row2_applies:
        warnings.append(
            "Hồ sơ chưa có hộ chiếu phổ thông cấp lần gần nhất (hoặc đơn trình báo mất hộ chiếu) — dòng \"Hộ chiếu phổ "
            "thông cấp lần gần nhất\" để trống; cấp lần đầu thì bỏ qua, đã có hộ chiếu thì tải bổ sung."
        )
        if rest:
            warnings.append(
                "Chưa đính kèm " + ", ".join(f"'{names[e['fileIndex']]}'" for e in rest)
                + " vì bảng Thành phần hồ sơ không có dòng phù hợp."
            )
    unknown = [names[e["fileIndex"]] for e in rest if row2_applies and e["docType"] == OTHER]
    if unknown:
        warnings.append(
            "Không xác định được loại giấy tờ của " + ", ".join(f"'{n}'" for n in dict.fromkeys(unknown))
            + " — đã đính chung vào dòng \"Hộ chiếu phổ thông cấp lần gần nhất\", vui lòng kiểm tra."
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


def mark_portrait(entries: list[dict], raw_files: list[dict], texts: dict[int, str]) -> list[dict]:
    """Tệp ảnh chân dung (cùng luật với process runner, ``mapper.find_portrait``) → loại PORTRAIT để không đính."""
    from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process.mapper import find_portrait

    index = find_portrait(raw_files, texts)
    if index is None:
        return entries
    return [{**e, "docType": PORTRAIT} if e["fileIndex"] == index else e for e in entries]


def portrait_page_fields(raw_files: list[dict], texts: dict[int, str]) -> list[dict]:
    """Ô ``filename46`` (comp ``bca-photo``) cho bước đính kèm: Auto Fill bấm "Đính kèm" mà không điền lại vẫn gắn được ảnh
    chân dung vào ô tải ảnh đầu trang kê khai. Extension gửi ảnh dưới dạng PDF một trang — mapper tự lấy lại ảnh gốc.
    Không có ảnh chân dung → [] (câu nhắc tải ảnh đã nằm ở bước điền)."""
    from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process.mapper import portrait_field

    try:
        field, _ = portrait_field(raw_files, texts)
    except Exception:  # noqa: BLE001 — ảnh hỏng không được làm hỏng kế hoạch đính kèm
        return []
    return [field] if field else []


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

    index_texts = {i: texts.get(names[i], "") for i in range(len(names))}
    entries = mark_portrait([e for e in classify_files(raw_files, texts, llm) if e["fileIndex"] in keep], raw_files,
                            index_texts)
    attachments, warnings = build_items(names, entries)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "pageFields": portrait_page_fields(raw_files, index_texts),
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
