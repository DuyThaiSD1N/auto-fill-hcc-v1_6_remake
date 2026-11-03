"""Đính kèm cho [Lai Châu] Hỗ trợ chi phí mai táng đối với người dân tộc thiểu số giai đoạn 2025-2030 (2.002862).

Bước 3 cổng dichvucong.laichau.gov.vn là BẢNG 5 DÒNG cố định, mỗi dòng có checkbox ở cột "#" + ô "Số bản"
(cổng để sẵn 1) + một ``input[type=file]``; dưới bảng là "Về việc" (cổng điền sẵn tên thủ tục, giữ
nguyên), "Ghi chú" và khối "Giấy tờ khác" (``HoSoOnline_giayToKhac[]`` tên + tệp, có nút thêm dòng).

Định tuyến chốt theo ảnh ánh xạ của bộ hồ sơ mẫu:
  - dòng 1 Biên bản Mẫu 02, dòng 2 Trích lục khai tử, dòng 3 Giấy hộ nghèo/cận nghèo, dòng 4 Tờ khai Mẫu 01,
    dòng 5 Giấy xác nhận hỏa táng (chỉ khi có — hồ sơ chôn cất không tick dòng này);
  - một file gộp CẢ Mẫu 01 lẫn Mẫu 02 (file Word "HS MAI TÁNG") đính NGUYÊN file vào CẢ dòng 1 và dòng 4,
    không tách;
  - CCCD người nộp không có dòng riêng → "Giấy tờ khác", ô tên ghi "Căn cước người nộp - <Họ tên>".

Engine ``fixed-slot`` của extension: khớp dòng theo ``slotKeywords`` (dự phòng ``slotIndex`` 0-based), tích
checkbox dòng (``tickRow``) rồi bơm tệp vào input của dòng. Mục ``target="new"`` đi khối "Giấy tờ khác".

Phân loại: LLM trước, LLM trả other/lỗi thì rule theo TIÊU ĐỀ văn bản. Tệp không nhận ra vẫn không bị rớt:
đưa vào "Giấy tờ khác" giữ tên tệp, kèm cảnh báo. Cổng chặn 6 MB/tệp → tệp vượt bị loại kèm cảnh báo tách nhỏ.
"""

import re
import time
from pathlib import Path
from typing import Any

from app.config import settings
from app.pipelines._shared import fold, normalize_document_name
from app.pipelines._shared.compact_agent.runner import _extract_docx_text, _is_docx
from app.pipelines._shared.documents import join_ocr_documents
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_MAX_FILE_BYTES = 6 * 1024 * 1024

_BIEN_BAN = "bien_ban_mai_tang"
_TO_KHAI = "to_khai_de_nghi"
_TO_KHAI_VA_BIEN_BAN = "to_khai_va_bien_ban"
_TRICH_LUC = "trich_luc_khai_tu"
_HO_NGHEO = "xac_nhan_ho_ngheo"
_HOA_TANG = "xac_nhan_hoa_tang"
_IDENTITY = "identity"
_OTHER = "other"

# slotName VERBATIM cột "Tên giấy tờ" trên cổng; slotKeywords dạng đã fold (khớp foldChoiceText của extension).
SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": "mttds_lc_row01",
        "slotIndex": 0,
        "slotName": "Biên bản xác nhận việc mai táng của Trưởng thôn, bản, tổ dân phố và đại diện Hộ gia đình, "
        "cá nhân hoặc cơ quan, tổ chức trực tiếp thực hiện việc mai táng cho người chết theo mẫu số 02 (Bản sao)",
        "slotKeywords": ["bien ban xac nhan viec mai tang"],
    },
    {
        "slotKey": "mttds_lc_row02",
        "slotIndex": 1,
        "slotName": "Bản sao trích lục khai tử; (Bản sao)",
        "slotKeywords": ["trich luc khai tu"],
    },
    {
        "slotKey": "mttds_lc_row03",
        "slotIndex": 2,
        "slotName": "Văn bản xác nhận người chết thuộc hộ nghèo hoặc hộ cận nghèo do Uỷ ban nhân dân cấp xã cấp "
        "(Bản sao)",
        "slotKeywords": ["ho ngheo hoac ho can ngheo"],
    },
    {
        "slotKey": "mttds_lc_row04",
        "slotIndex": 3,
        "slotName": "Tờ khai đề nghị hỗ trợ chi phí mai táng của hộ gia đình, cá nhân hoặc cơ quan, tổ chức trực "
        "tiếp tổ chức thực hiện việc mai táng cho người chết theo mẫu số 01 (Bản sao)",
        "slotKeywords": ["to khai de nghi ho tro chi phi mai tang"],
    },
    {
        "slotKey": "mttds_lc_row05",
        "slotIndex": 4,
        "slotName": "Giấy xác nhận của cơ sở hỏa táng (đối với trường hợp thi thể người chết thực hiện hỏa táng); "
        "(Bản sao)",
        "slotKeywords": ["co so hoa tang"],
    },
]
_SLOT_BY_INDEX = {slot["slotIndex"]: slot for slot in SLOTS}

# docType -> [(slotIndex, tên tài liệu hiển thị)]; file gộp Mẫu 01 + Mẫu 02 lên CẢ hai dòng.
_ROUTES: dict[str, list[tuple[int, str]]] = {
    _BIEN_BAN: [(0, "Biên bản xác nhận việc mai táng")],
    _TRICH_LUC: [(1, "Trích lục khai tử")],
    _HO_NGHEO: [(2, "Giấy chứng nhận hộ nghèo, hộ cận nghèo")],
    _TO_KHAI: [(3, "Tờ khai đề nghị hỗ trợ chi phí mai táng")],
    _TO_KHAI_VA_BIEN_BAN: [
        (0, "Hồ sơ mai táng (Tờ khai Mẫu 01 và Biên bản Mẫu 02)"),
        (3, "Hồ sơ mai táng (Tờ khai Mẫu 01 và Biên bản Mẫu 02)"),
    ],
    _HOA_TANG: [(4, "Giấy xác nhận của cơ sở hỏa táng")],
}
_ALLOWED = set(_ROUTES) | {_IDENTITY, _OTHER}

_IDENTITY_NAME_RE = re.compile(
    r"(?:full\s*name|h[ọo],?\s*ch[ữu]\s*đ[ệe]m\s*v[àa]\s*t[êe]n(?:\s*khai\s*sinh)?|h[ọo]\s*v[àa]\s*t[êe]n)"
    r"[^\n:]*:?[ \t]*([^\n]*)(?:\n[ \t]*([^\n]*))?",
    re.IGNORECASE,
)


def _normalize_doc_type(value: Any) -> str:
    folded = fold(str(value or ""))
    for doc_type in _ALLOWED:
        if folded == fold(doc_type):
            return doc_type
    return _OTHER


def _rule_doc_type(text: str) -> str:
    """Rule theo TIÊU ĐỀ — Tờ khai/Biên bản nhắc cả trích lục, hộ nghèo, hỏa táng nên xét chúng trước."""
    haystack = fold(text)
    if not haystack:
        return ""
    has_to_khai = "to khai de nghi ho tro chi phi mai tang" in haystack
    has_bien_ban = "bien ban xac nhan viec mai tang" in haystack
    if has_to_khai and has_bien_ban:
        return _TO_KHAI_VA_BIEN_BAN
    if has_to_khai:
        return _TO_KHAI
    if has_bien_ban:
        return _BIEN_BAN
    if "giay chung nhan ho ngheo" in haystack or "ho ngheo, ho can ngheo" in haystack:
        return _HO_NGHEO
    if "trich luc khai tu" in haystack or "giay chung tu" in haystack:
        return _TRICH_LUC
    if "co so hoa tang" in haystack and "xac nhan" in haystack:
        return _HOA_TANG
    if any(marker in haystack for marker in ("can cuoc", "chung minh nhan dan", "identity card", "passport")):
        return _IDENTITY
    return ""


def _identity_holder_name(text: str) -> str | None:
    """Họ tên chủ thẻ đọc từ OCR CCCD ("Họ, chữ đệm và tên khai sinh / Full name: ...") → "Nguyễn Văn A"."""
    for match in _IDENTITY_NAME_RE.finditer(text or ""):
        for candidate in match.groups():
            name = " ".join(re.sub(r"[^\w\s]", " ", candidate or "").split())
            if name and not re.search(r"\d", name) and 2 <= len(name.split()) <= 6 and "name" not in name.lower():
                return name.title()
    return None


def _data_url_size(data_url: str) -> int:
    payload = str(data_url or "").partition(",")[2]
    if not payload:
        return 0
    payload = re.sub(r"\s+", "", payload)
    padding = len(payload) - len(payload.rstrip("="))
    return max(0, (len(payload) * 3) // 4 - padding)


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=700, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    result: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            result[int(item.get("index"))] = _normalize_doc_type(item.get("docType") or item.get("type"))
        except (TypeError, ValueError):
            continue
    return result


def _slot_item(file_index: int, file_name: str, doc_type: str, slot_index: int, document_name: str) -> dict:
    slot = _SLOT_BY_INDEX[slot_index]
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


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict] | None = None,
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    text_by_name = {item.get("name"): str(item.get("text") or "") for item in ocr_results or []}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        size = _data_url_size(file.get("dataUrl", ""))
        if size > _MAX_FILE_BYTES:
            warnings.append(
                f"File '{file_name}' nặng {size / 1024 / 1024:.1f} MB, vượt giới hạn 6 MB của cổng — "
                "hãy tách nhỏ hoặc giảm độ phân giải (mỗi tệp dưới 6 MB) rồi đính kèm lại."
            )
            classified.append(
                {"fileName": file_name, "docType": _OTHER, "source": "validation", "skipped": True,
                 "reason": "file_too_large"}
            )
            continue

        text = text_by_name.get(file_name, "")
        rule_type = _rule_doc_type(text)
        llm_type = llm_types.get(index, "")
        # File Word gộp hai mẫu: rule thấy CẢ hai tiêu đề là chắc chắn, thắng nhãn đơn lẻ của LLM.
        if rule_type == _TO_KHAI_VA_BIEN_BAN or llm_type not in _ALLOWED or llm_type == _OTHER:
            doc_type, source = (rule_type, "rule") if rule_type else (_OTHER, "unknown")
        else:
            doc_type, source = llm_type, "llm"

        if doc_type in _ROUTES:
            for slot_index, document_name in _ROUTES[doc_type]:
                attachments.append(_slot_item(index, file_name, doc_type, slot_index, document_name))
            classified.append({
                "fileName": file_name, "docType": doc_type, "source": source,
                "slotIndex": [slot_index for slot_index, _ in _ROUTES[doc_type]],
            })
            continue

        if doc_type == _IDENTITY:
            holder = _identity_holder_name(text)
            name = f"Căn cước người nộp - {holder}" if holder else "Căn cước người nộp"
            attachments.append(_other_item(index, file_name, _IDENTITY, name))
            classified.append({"fileName": file_name, "docType": _IDENTITY, "source": source})
            continue

        # Không rõ loại: vẫn đính vào "Giấy tờ khác" với tên tệp gốc, cảnh báo để cán bộ kiểm tra.
        name = normalize_document_name(Path(file_name).stem, "Giấy tờ khác")
        attachments.append(_other_item(index, file_name, _OTHER, name))
        warnings.append(
            f"Không xác định được loại giấy tờ của file '{file_name}' — đã đính vào \"Giấy tờ khác\"; "
            "vui lòng kiểm tra và chuyển sang đúng dòng nếu cần."
        )
        classified.append({"fileName": file_name, "docType": _OTHER, "source": source})

    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    errors: list[str] = []

    small = [item for item in raw_files if _data_url_size(item.get("dataUrl", "")) <= _MAX_FILE_BYTES]
    ocr_files = [item for item in small if item.get("type") in _OCR_TYPES]

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    # OCR không đọc DOCX → lấy chữ thẳng từ XML (file Word gộp Tờ khai + Biên bản).
    ocr_results.extend(_extract_docx_text(item) for item in small if _is_docx(item))
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    llm_documents = [
        {"index": index, "name": file["name"], "text": str(by_name.get(file.get("name"), {}).get("text") or "")}
        for index, file in enumerate(raw_files)
        if str(by_name.get(file.get("name"), {}).get("text") or "").strip()
    ]

    started = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_documents:
        try:
            llm_types = await _classify_with_llm(llm_documents)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types)
    errors.extend(warnings)

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [item["name"] for item in raw_files],
            "ocrDocuments": [item.get("name") for item in ocr_results if item.get("text")],
            "llmDocuments": [item["name"] for item in llm_documents],
            "classified": classified,
            "slots": SLOTS,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "ocr_text": join_ocr_documents(ocr_results),
        "llm_output": {str(index): value for index, value in llm_types.items()},
        "errors": errors,
    }
