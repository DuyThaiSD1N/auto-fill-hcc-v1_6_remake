"""Đính kèm Trình báo mất hộ chiếu phổ thông cấp tỉnh (1.001445) — chế độ KHÔNG tách: mỗi tệp đính NGUYÊN một lần.

Bảng "Thành phần hồ sơ" của Cổng DVC Bộ Công an (eForm Nth, cùng trang form kê khai) — ảnh ánh xạ 20/11/2026, 2 dòng:
  - dòng 1 (giấy tờ 17526) "Giấy tờ chứng minh là cha, mẹ hoặc người đại diện hợp pháp đối với trường hợp trình báo mất
    hộ chiếu cho trẻ em dưới 14 tuổi, người mất năng lực hành vi dân sự …" (Bản chính): chỉ khi hồ sơ có giấy khai sinh /
    giấy tờ giám hộ. Người thành niên tự trình báo → KHÔNG tick, không đính;
  - dòng 2 (giấy tờ 17535) "01 đơn trình báo mất hộ chiếu (mẫu TK05) …" (Bản chính, bắt buộc): đơn TK05 là tệp chính;
    tờ khai TK01 ĐÍNH KÈM CHUNG vào dòng này (bảng không có dòng riêng cho TK01, cùng sự việc mất hộ chiếu, có xác nhận
    đối chiếu của cơ quan XNC) — đơn đứng trước.
Thẻ căn cước: thủ tục không yêu cầu nộp (thông tin nhân thân cổng lấy từ CSDL dân cư) → không đính, cảnh báo. Tệp không rõ
loại: có đơn thì đính chung dòng 2 kèm cảnh báo; không nhận ra đơn thì vẫn đính vào dòng 2 (dòng bắt buộc, thà đính để
người dùng soát còn hơn để trống). Chỉ có tờ khai mà không có đơn → dòng 2 để trống, cảnh báo. Trang không có khối "Giấy
tờ khác" nên không có mục target "new".

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
DAI_DIEN = "dai_dien_hop_phap"
IDENTITY = "identity"
OTHER = "other"
BLANK = "blank_page"
ALLOWED = {TRINH_BAO, TO_KHAI, DAI_DIEN, IDENTITY, OTHER, BLANK}
# Thứ tự ghép trong dòng 2: đơn TK05 (tệp chính) → tờ khai TK01 → giấy không rõ loại.
ROW2_ORDER = (TRINH_BAO, TO_KHAI, OTHER)

# slotName = cột "Tên giấy tờ" trên cổng (rút gọn); slotKeywords dạng đã fold (khớp foldChoiceText của extension).
SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": "tbmhct_row01",
        "slotIndex": 0,
        "slotName": "Giấy tờ chứng minh là cha, mẹ hoặc người đại diện hợp pháp",
        "slotKeywords": ["giay to chung minh la cha"],
    },
    {
        "slotKey": "tbmhct_row02",
        "slotIndex": 1,
        "slotName": "01 đơn trình báo mất hộ chiếu (mẫu TK05)",
        "slotKeywords": ["don trinh bao mat ho chieu"],
    },
]
ROW_DOCUMENT_NAMES = {
    0: "Giấy tờ chứng minh người đại diện hợp pháp",
    1: "Đơn trình báo mất hộ chiếu phổ thông",
}
# Tên từng giấy trong câu ghi chú "đính kèm chung" / "chưa đính kèm".
TYPE_NAMES = {
    TRINH_BAO: "Đơn trình báo mất hộ chiếu phổ thông",
    TO_KHAI: "Tờ khai đề nghị cấp hộ chiếu",
    DAI_DIEN: "Giấy tờ người đại diện hợp pháp",
    IDENTITY: "Thẻ căn cước",
}


def canonical_type(value: Any) -> str:
    folded = fold(str(value or "")).replace(" ", "_")
    return folded if folded in ALLOWED else OTHER


def rule_doc_type(text: str) -> str:
    """Luật theo TIÊU ĐỀ. Đơn trình báo nhắc "hộ chiếu" ở mọi mục và "người đại diện hợp pháp" ở ghi chú → xét trước;
    tờ khai mục 14 có thể ghi "cấp lại hộ chiếu do bị mất" nhưng không có cụm "đơn trình báo mất"."""
    haystack = fold(text)
    if not haystack.strip():
        return ""
    head = haystack[:_HEAD_CHARS]
    if re.search(r"\b(don trinh bao mat ho chieu|trinh bao mat ho chieu pho thong)\b", head):
        return TRINH_BAO
    if "to khai" in head and "ho chieu" in head:
        return TO_KHAI
    if re.search(r"\b(giay khai sinh|trich luc khai sinh|giam ho|nguoi dai dien hop phap)\b", head):
        return DAI_DIEN
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


def build_items(names: list[str], entries: list[dict]) -> tuple[list[dict], list[str]]:
    """Đoạn đã phân loại → (mục đính kèm, cảnh báo). Tách khỏi I/O để test, dùng chung hai chế độ.

    ``entries``: [{fileIndex, pages (0-based, None = cả tệp), docType, documentName, text}] theo thứ tự tệp, trang.
    Đoạn cùng dòng bảng gộp thành MỘT tệp (cổng mỗi dòng một ô chọn tệp): toàn tệp → ``sourceFileIndexes``, có đoạn cắt
    trang → ``sourceSegments``.
    """
    entries = [e for e in entries if e.get("docType") != BLANK]
    parts_of_file: dict[int, int] = {}
    for e in entries:
        parts_of_file[e["fileIndex"]] = parts_of_file.get(e["fileIndex"], 0) + 1

    def pages_of(entry: dict):
        return None if entry["pages"] is None or parts_of_file[entry["fileIndex"]] == 1 else entry["pages"]

    warnings: list[str] = []
    representative = [e for e in entries if e["docType"] == DAI_DIEN]
    row2 = [e for e in entries if e["docType"] in ROW2_ORDER]
    has_report = any(e["docType"] == TRINH_BAO for e in row2)
    # Không nhận ra đơn → tệp không rõ loại (nhiều khả năng là đơn đọc mờ) làm tệp chính, đứng trước tờ khai.
    order = ROW2_ORDER if has_report else (OTHER, TO_KHAI)
    row2.sort(key=lambda e: order.index(e["docType"]))
    unknown = [e for e in row2 if e["docType"] == OTHER]
    if not has_report and not unknown:
        row2 = []  # chỉ có tờ khai → không đính tờ khai thay cho đơn
    in_rows = {id(e) for e in [*representative, *row2]}
    rest = [e for e in entries if id(e) not in in_rows]

    attachments: list[dict] = []
    for slot, parts in ((SLOTS[0], representative), (SLOTS[1], row2)):
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

    if not has_report:
        if unknown:
            warnings.append(
                "Không nhận ra đơn trình báo mất hộ chiếu (Mẫu TK05) — đã đính "
                + ", ".join(f"'{n}'" for n in dict.fromkeys(names[e["fileIndex"]] for e in unknown))
                + " vào dòng \"01 đơn trình báo mất hộ chiếu (mẫu TK05)\", vui lòng kiểm tra."
            )
        else:
            warnings.append(
                "Hồ sơ chưa có đơn trình báo mất hộ chiếu phổ thông (Mẫu TK05) — dòng bắt buộc \"01 đơn trình báo mất hộ "
                "chiếu (mẫu TK05)\" để trống; tải bổ sung bản chụp đơn đã ký."
            )
    elif unknown:
        warnings.append(
            "Không xác định được loại giấy tờ của "
            + ", ".join(f"'{n}'" for n in dict.fromkeys(names[e["fileIndex"]] for e in unknown))
            + " — đã đính chung vào dòng \"01 đơn trình báo mất hộ chiếu (mẫu TK05)\", vui lòng kiểm tra."
        )
    if rest:
        warnings.append(
            "Chưa đính kèm " + "; ".join(_part_label(e, names) for e in rest)
            + " vì bảng Thành phần hồ sơ không có dòng cho giấy này (thủ tục không yêu cầu nộp; giấy đã dùng để điền "
            "biểu mẫu)."
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
