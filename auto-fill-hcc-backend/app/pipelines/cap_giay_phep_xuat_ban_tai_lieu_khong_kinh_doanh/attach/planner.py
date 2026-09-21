"""Đính kèm [Bộ VHTTDL] Cấp giấy phép xuất bản tài liệu không kinh doanh (1.003868).

Cổng `dichvucong.bvhttdl.gov.vn` — form và bảng thành phần hồ sơ NẰM CHUNG trang `/nop-ho-so`. Bảng
`<table class="style_table">` có 4 dòng, mỗi dòng một `<app-upload-flie-multi>` chứa input file →
engine FE `fixed-slot` (slotIndex = thứ tự input file trên trang):

  0 : (1) Đơn đề nghị cấp giấy phép xuất bản tài liệu không kinh doanh (Mẫu số 04, NĐ 138/2025)
  1 : (2) Hai (02) bản thảo tài liệu có đóng dấu của cơ quan, tổ chức đề nghị
  2 : (3) Bản dịch tiếng Việt (tài liệu tiếng nước ngoài / tiếng dân tộc thiểu số)
  3 : (4) Ý kiến xác nhận bằng văn bản (đơn vị quân đội/công an, tài liệu lịch sử Đảng…)

⚑ TRANG KHÔNG CÓ Ô "GIẤY TỜ KHÁC" — chỉ đúng 4 ô upload. Giấy tờ ngoài danh mục (GCN đăng ký doanh
nghiệp, giấy phép hoạt động in của nhà in…) vẫn phải lên hồ sơ nên đưa vào dòng (4) kèm cảnh báo
nói rõ đó không phải văn bản ý kiến, để cán bộ tự đối chiếu.

⚑ MỖI TỆP CHỈ ĐÍNH VÀO MỘT DÒNG; tệp chứa nhiều giấy tờ thì ưu tiên dòng ĐƠN ĐỀ NGHỊ.

Phân loại THUẦN LLM (không lưới keyword). Không bỏ sót tệp nào.
"""

import asyncio
import re
import time
import unicodedata
from typing import Any

from app.config import settings
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_LOAI_BAN = "Bản chính"

_T_DON = "don_de_nghi"
_T_BAN_THAO = "ban_thao"
_T_BAN_DICH = "ban_dich"
_T_Y_KIEN = "y_kien_xac_nhan"
_T_OTHER = "other"

_SLOT_NAMES = {
    0: "Đơn đề nghị cấp giấy phép xuất bản tài liệu không kinh doanh theo Mẫu số 04",
    1: "Hai (02) bản thảo tài liệu in trên giấy có đóng dấu của cơ quan, tổ chức đề nghị",
    2: "Bản dịch tiếng Việt có đóng dấu của cơ quan, tổ chức đề nghị cấp giấy phép xuất bản",
    3: "Ý kiến xác nhận bằng văn bản",
}

_ROUTES: dict[str, int] = {
    _T_DON: 0,
    _T_BAN_THAO: 1,
    _T_BAN_DICH: 2,
    _T_Y_KIEN: 3,
}
_DISPLAY = {
    _T_DON: "Đơn đề nghị cấp giấy phép xuất bản tài liệu không kinh doanh (Mẫu số 04)",
    _T_BAN_THAO: "Bản thảo tài liệu",
    _T_BAN_DICH: "Bản dịch tiếng Việt của tài liệu",
    _T_Y_KIEN: "Ý kiến xác nhận bằng văn bản",
}
_ALLOWED = set(_ROUTES) | {_T_OTHER}

# Thứ tự phủ dòng: Đơn đề nghị là giấy tờ bắt buộc số một, nên tệp gộp luôn ưu tiên dòng này.
_ROW_PRIORITY = (_T_DON, _T_BAN_THAO, _T_BAN_DICH, _T_Y_KIEN)

# Trang chỉ có 4 ô upload, không có dòng "Giấy tờ khác" → giấy tờ lạ vẫn phải lên hồ sơ ở dòng (4).
_SLOT_GIAY_TO_LA = _ROUTES[_T_Y_KIEN]


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _canon(value: Any) -> str:
    return re.sub(r"[_\-\s]+", "_", _fold(value)).strip("_")


def _normalize_doc_type(value: Any) -> str:
    canon = _canon(value)
    for doc_type in _ALLOWED:
        if canon == _canon(doc_type):
            return doc_type
    return _T_OTHER


def _normalize_also(values: Any, primary: str) -> list[str]:
    """Loại giấy tờ KHÁC cùng nằm trong một tệp gộp — chỉ dùng để chọn dòng còn trống."""
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for value in values:
        doc_type = _normalize_doc_type(value)
        if doc_type not in (_T_OTHER, primary) and doc_type not in out:
            out.append(doc_type)
    return out


async def _classify_one(document: dict[str, Any]) -> tuple[int, str, list[str]]:
    index = int(document.get("index"))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(
            [{"index": index, "text": str(document.get("text") or "")[:14000]}]
        )},
    ]
    raw = await client.chat(messages, max_tokens=180, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    first = next(iter(parsed.get("documents", []) or []), {})
    doc_type = _normalize_doc_type(first.get("docType") or first.get("type"))
    return index, doc_type, _normalize_also(first.get("alsoTypes"), doc_type)


async def _classify_with_llm(
    documents: list[dict[str, Any]],
    errors: list[str] | None = None,
) -> dict[int, tuple[str, list[str]]]:
    if not documents:
        return {}
    outcomes = await asyncio.gather(*(_classify_one(d) for d in documents), return_exceptions=True)
    result: dict[int, tuple[str, list[str]]] = {}
    for document, outcome in zip(documents, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            if errors is not None:
                errors.append(f"attachment_agent file {document.get('index')}: {outcome}")
            continue
        index, doc_type, also = outcome
        result[index] = (doc_type, also)
    return result


def _item(index: int, file_name: str, slot_index: int, document_name: str, slot_key: str,
          doc_type: str) -> dict:
    return {
        "fileIndex": index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": _SLOT_NAMES[slot_index],
        "loaiBan": _LOAI_BAN,
        "target": "fixed-slot",
        "needsAddComponent": False,
        # Cố ý không trùng FIXED_SLOT_KEYWORDS của extension để FE đi thẳng theo slotIndex.
        "slotKey": slot_key,
        "slotIndex": slot_index,
        "slotName": _SLOT_NAMES[slot_index],
        "detectedType": doc_type,
    }


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, tuple[str, list[str]] | str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}

    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    la: list[str] = []
    by_slot: dict[int, list[str]] = {}
    da_dung: set[str] = set()

    resolved: list[tuple[int, str, str, list[str], str]] = []
    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        raw = llm_types.get(index)
        doc_type, also = raw if isinstance(raw, tuple) else (raw, [])
        if doc_type not in _ALLOWED:
            doc_type = _T_OTHER
        also = _normalize_also(also, doc_type) if doc_type != _T_OTHER else []
        resolved.append((index, file_name, doc_type, also, "llm" if index in llm_types else "default"))

    for index, file_name, doc_type, also, source in resolved:
        if doc_type == _T_OTHER:
            attachments.append(_item(
                index, file_name, _SLOT_GIAY_TO_LA,
                document_name=file_name, slot_key="gpxb_giay_to_khac", doc_type=doc_type,
            ))
            by_slot.setdefault(_SLOT_GIAY_TO_LA, []).append(file_name)
            la.append(file_name)
            classified.append({
                "fileName": file_name, "docType": doc_type, "alsoTypes": also,
                "assignedType": None, "source": source, "slotIndex": _SLOT_GIAY_TO_LA,
            })
            continue

        # Mỗi tệp CHỈ một dòng; tệp gộp dùng để phủ dòng còn trống, ưu tiên Đơn đề nghị.
        chua_co = [t for t in _ROW_PRIORITY if t in (doc_type, *also) and t not in da_dung]
        chon = chua_co[0] if chua_co else doc_type

        attachments.append(_item(
            index, file_name, _ROUTES[chon], _DISPLAY[chon], f"gpxb_{chon}", chon,
        ))
        by_slot.setdefault(_ROUTES[chon], []).append(file_name)
        da_dung.add(chon)
        classified.append({
            "fileName": file_name, "docType": doc_type, "alsoTypes": also,
            "assignedType": chon, "source": source, "slotIndex": _ROUTES[chon],
        })

    if la:
        warnings.append(
            "Trang này chỉ có 4 ô đính kèm, KHÔNG có dòng \"Giấy tờ khác\", nên các tệp chưa nhận ra "
            f"loại đã được đưa vào dòng \"{_SLOT_NAMES[_SLOT_GIAY_TO_LA]}\": {', '.join(la)}. Đây "
            "KHÔNG phải văn bản ý kiến của cơ quan có thẩm quyền — cán bộ đối chiếu lại, thành phần "
            "này có thể vẫn đang thiếu giấy tờ đúng yêu cầu."
        )
    for slot_index, names in by_slot.items():
        unique = list(dict.fromkeys(names))
        if len(unique) > 1:
            warnings.append(
                f"Dòng \"{_SLOT_NAMES[slot_index]}\" nhận {len(unique)} tệp ({', '.join(unique)}) — "
                "kiểm tra lại số bản khai trên bảng thành phần hồ sơ."
            )
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]
    errors: list[str] = []

    from app.services import ocr

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    llm_documents = [
        {"index": index, "text": str(by_name.get(file.get("name"), {}).get("text") or "")}
        for index, file in enumerate(raw_files)
        if str(by_name.get(file.get("name"), {}).get("text") or "").strip()
    ]
    started = time.monotonic()
    llm_types: dict[int, tuple[str, list[str]]] = {}
    if llm_documents:
        try:
            llm_types = await _classify_with_llm(llm_documents, errors)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, llm_types)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[d["index"]]["name"] for d in llm_documents],
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
