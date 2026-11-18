"""Đính kèm Cấp thị thực cho người nước ngoài tại Việt Nam (1.001194) — chế độ KHÔNG tách: mỗi tệp đính NGUYÊN.

Bảng "Thành phần hồ sơ" của Cổng DVC Bộ Công an (eForm Nth, cùng khuôn hộ chiếu 1.001456) — ảnh ánh xạ bộ mẫu:
  - dòng 1 "Tờ khai đề nghị cấp thị thực, gia hạn tạm trú (Mẫu NA5)" (Bản chính);
  - dòng 2 "Giấy tờ chứng minh lý do được gia hạn tạm trú để tiếp tục ở lại Việt Nam - nếu có": thuộc gia hạn tạm
    trú → thủ tục cấp thị thực KHÔNG tick, không đính;
  - dòng 3 "Giấy tờ chứng minh lý do được cấp thị thực, thẻ tạm trú…như: giấy phép lao động, giấy chứng nhận đầu tư,
    giấy đăng ký kết hôn…" (Bản chính).
Hộ chiếu và thẻ căn cước người bảo lãnh không có dòng riêng: hộ chiếu đính chung dòng 1 sau tờ khai (ghi chú (1) tờ
khai: "Mỗi người khai 1 bản, kèm hộ chiếu"), căn cước đính chung dòng 3 sau giấy chứng minh. Hồ sơ dồn cả bộ trong MỘT
tệp (ảnh ánh xạ: "hồ sơ nằm trong 1 tệp PDF duy nhất") → đính NGUYÊN tệp vào cả dòng 1 lẫn dòng 3.
Ảnh trang nhân thân hộ chiếu + ảnh chân dung 4x6 ở đầu form là ô tải ảnh riêng → mapper cảnh báo tải tay.

Phân loại: LLM trước, LLM trả other / lỗi thì luật theo TIÊU ĐỀ; tệp có cả tờ khai NA5 lẫn giấy chứng minh luôn là
``ho_so_gop`` (LLM chỉ thấy 4000 ký tự đầu). Cổng chặn 6 MB/tệp → tệp vượt bị loại kèm cảnh báo. ``build_items`` dùng
chung với chế độ tách (đoạn trang thay cho cả tệp).
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

TO_KHAI = "to_khai"
HO_CHIEU = "ho_chieu"
CHUNG_MINH = "chung_minh"
IDENTITY = "identity"
BIA = "bia_ho_so"
GOP = "ho_so_gop"
OTHER = "other"
BLANK = "blank_page"
ALLOWED = {TO_KHAI, HO_CHIEU, CHUNG_MINH, IDENTITY, BIA, GOP, OTHER, BLANK}
FORM_TYPES = (TO_KHAI, GOP)
PROOF_TYPES = (CHUNG_MINH, GOP)
# Thứ tự ghép trong từng dòng (bìa + tờ khai + hộ chiếu / giấy chứng minh + căn cước + giấy khác).
ROW1_ORDER = (BIA, TO_KHAI, GOP, HO_CHIEU)
ROW3_ORDER = (CHUNG_MINH, GOP, IDENTITY, OTHER)

# slotName = cột "Tên giấy tờ" trên cổng (rút gọn); slotKeywords dạng đã fold (khớp foldChoiceText của extension).
SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": "ttnnn_row01",
        "slotIndex": 0,
        "slotName": "Tờ khai đề nghị cấp thị thực, gia hạn tạm trú (Mẫu NA5)",
        "slotKeywords": ["to khai de nghi cap thi thuc"],
    },
    {
        "slotKey": "ttnnn_row03",
        "slotIndex": 2,
        "slotName": "Giấy tờ chứng minh lý do được cấp thị thực, thẻ tạm trú",
        "slotKeywords": ["chung minh ly do duoc cap thi thuc"],
    },
]
ROW_DOCUMENT_NAMES = {
    0: "Tờ khai đề nghị cấp thị thực, gia hạn tạm trú (Mẫu NA5)",
    2: "Giấy tờ chứng minh lý do được cấp thị thực",
}
# Tiêu đề tờ khai NA5. OCR Tiếng Nói hay làm rơi dòng tiêu đề in hoa (bộ mẫu 18/11: chỉ còn "Mẫu (Form NA5" và
# "APPLICATION FORM FOR VISISA ISSUANCE") → nhận thêm hai dấu hiệu đó; bìa / danh mục chỉ ghi "(Mẫu NA5)", không có "Form".
_FORM_TITLE_RE = re.compile(r"T[ỜO]\s+KHAI\s+Đ[ỀE]\s+NGH[ỊI]\s+C[ẤA]P\s+TH[ỊI]\s+TH[ỰU]C|APPLICATION\s+FORM\s+FOR\s+VI"
                            r"|(?i:\(?\s*form\s*\)?\s*na\s*5\b)")
_PROOF_TITLE_RE = re.compile(r"GI[ẤA]Y\s+(CH[ỨU]NG\s+NH[ẬA]N\s+K[ẾE]T\s+H[ÔO]N|PH[ÉE]P\s+LAO\s+Đ[ỘO]NG|KHAI\s+SINH"
                             r"|CH[ỨU]NG\s+NH[ẬA]N\s+Đ[ĂA]NG\s+K[ÝY]\s+Đ[ẦA]U\s+T[ƯU])")


def canonical_type(value: Any) -> str:
    folded = fold(str(value or "")).replace(" ", "_")
    return folded if folded in ALLOWED else OTHER


def rule_doc_type(text: str) -> str:
    """Luật theo TIÊU ĐỀ. Tờ khai nhắc hộ chiếu / quan hệ trong thân → xét trước; hộ chiếu in "Passport" → trước CCCD."""
    haystack = fold(text)
    if not haystack.strip():
        return ""
    head = haystack[:_HEAD_CHARS]
    if re.search(r"\b(ho so thu tuc hanh chinh|danh muc thanh phan ho so)\b", head):
        return BIA
    if ("to khai" in head and "thi thuc" in head) or "application form for vi" in head or re.search(r"form\s*\)?\s*na\s*5",
                                                                                                head):
        return TO_KHAI
    if re.search(r"\b(giay chung nhan ket hon|giay phep lao dong|giay khai sinh|trich luc|giay chung nhan dang ky dau tu"
                 r"|cong van moi)\b", head):
        return CHUNG_MINH
    if "p<" in haystack.replace(" ", "") or re.search(r"\b(passport|nhap canh / arrival|arrival)\b", haystack):
        return HO_CHIEU
    if any(marker in haystack for marker in ("can cuoc", "chung minh nhan dan", "identity card", "the tam tru",
                                              "the thuong tru")):
        return IDENTITY
    return ""


def is_combined(text: str) -> bool:
    """Tệp có cả tiêu đề tờ khai NA5 lẫn tiêu đề giấy chứng minh (IN HOA — danh mục ở bìa ghi chữ thường)."""
    return bool(_FORM_TITLE_RE.search(text or "")) and bool(_PROOF_TITLE_RE.search(text or ""))


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


def _ordered(entries: list[dict], order: tuple[str, ...]) -> list[dict]:
    picked = [e for e in entries if e["docType"] in order]
    return sorted(picked, key=lambda e: order.index(e["docType"]))  # sort ổn định: giữ thứ tự tệp, trang


def build_items(names: list[str], entries: list[dict]) -> tuple[list[dict], list[str]]:
    """Đoạn đã phân loại → (mục đính kèm, cảnh báo). Tách khỏi I/O để test, dùng chung hai chế độ.

    ``entries``: [{fileIndex, pages (0-based, None = cả tệp), docType, documentName, text}] theo thứ tự tệp, trang.
    Đoạn cùng dòng bảng gộp thành MỘT tệp (cổng mỗi dòng một ô chọn tệp): toàn tệp → ``sourceFileIndexes``, có đoạn
    cắt trang → ``sourceSegments``. Tệp ``ho_so_gop`` đính vào CẢ dòng 1 và dòng 3.
    """
    entries = [e for e in entries if e.get("docType") != BLANK]
    parts_of_file: dict[int, int] = {}
    for e in entries:
        parts_of_file[e["fileIndex"]] = parts_of_file.get(e["fileIndex"], 0) + 1

    def pages_of(entry: dict):
        return None if entry["pages"] is None or parts_of_file[entry["fileIndex"]] == 1 else entry["pages"]

    has_form = any(e["docType"] in FORM_TYPES for e in entries)
    if has_form:
        row1, row3 = _ordered(entries, ROW1_ORDER), _ordered(entries, ROW3_ORDER)
    else:
        # Không có tờ khai: dòng 1 để trống; bìa + hộ chiếu đính chung dòng 3 cho khỏi sót trang.
        row1, row3 = [], _ordered(entries, (BIA,) + ROW3_ORDER + (HO_CHIEU,))

    attachments: list[dict] = []
    warnings: list[str] = []
    for slot, parts in ((SLOTS[0], row1), (SLOTS[1], row3)):
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

    # Gộp nhiều giấy vào một dòng, tệp gộp đính cả dòng 1 lẫn dòng 3, dòng 2 (gia hạn tạm trú) không tick đều là ĐÚNG ảnh
    # ánh xạ — không cảnh báo (user 18/11: "xóa mấy cái cảnh báo, không cho hiện"). Chỉ cảnh báo khi hồ sơ thiếu / lạ.
    if not has_form:
        warnings.append("Hồ sơ chưa có Tờ khai đề nghị cấp thị thực (Mẫu NA5) — dòng Tờ khai để trống, cần tải bổ sung.")
    if not any(e["docType"] in PROOF_TYPES for e in entries):
        warnings.append(
            "Hồ sơ chưa có giấy tờ chứng minh lý do được cấp thị thực (giấy chứng nhận kết hôn, giấy phép lao động, giấy "
            "chứng nhận đầu tư …) — dòng này bắt buộc, cần tải bổ sung."
        )
    unknown = [names[e["fileIndex"]] for e in entries if e["docType"] == OTHER]
    if unknown:
        warnings.append(
            "Không xác định được loại giấy tờ của " + ", ".join(f"'{n}'" for n in dict.fromkeys(unknown))
            + " — đã đính chung vào dòng \"Giấy tờ chứng minh lý do được cấp thị thực\", vui lòng kiểm tra."
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
    """Mỗi tệp một đoạn (cả tệp): tệp gộp nhận theo tiêu đề; còn lại loại theo LLM, LLM other / thiếu → luật tiêu đề."""
    entries = []
    for index, file in enumerate(files):
        text = texts.get(file.get("name"), "")
        got = llm.get(index) or {}
        doc_type = got.get("docType") or OTHER
        if is_combined(text):
            doc_type = GOP
        elif doc_type in (OTHER, BLANK):
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
