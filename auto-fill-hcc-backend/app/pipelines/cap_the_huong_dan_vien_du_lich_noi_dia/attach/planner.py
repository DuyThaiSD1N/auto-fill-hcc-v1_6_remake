"""Đính kèm [Bộ VHTTDL] Thủ tục cấp thẻ hướng dẫn viên du lịch nội địa (1.004623, QT-121).

Cổng `dichvucong.bvhttdl.gov.vn` — form và bảng thành phần hồ sơ NẰM CHUNG trang. Bảng có 3 dòng, mỗi
dòng một `<app-upload-flie-multi>` chứa input file (multiple) → engine FE `fixed-slot` (slotIndex = thứ
tự input file trên trang, KHÔNG phải số thứ tự (1)(2)(3) in trong tên thành phần):

  0 : (3) 01 ảnh chân dung màu 3cm x 4cm hoặc bản điện tử ảnh màu            — Bản chính 1
  1 : (1) Đơn đề nghị cấp thẻ hướng dẫn viên du lịch nội địa (Mẫu số 04)     — Bản chính 1
  2 : (2) Bản sao bằng tốt nghiệp trung cấp trở lên … và bản sao chứng chỉ
          nghiệp vụ hướng dẫn du lịch nội địa                                  — Bản sao 1

⚑ Dòng 2 nhận CHUNG hai tệp (văn bằng + chứng chỉ nghiệp vụ) khi văn bằng thuộc chuyên ngành khác:
hai item cùng `slotKey` → engine gom vào một lần gán input `multiple`.

⚑ ẢNH CHÂN DUNG không có chữ nên OCR rỗng → nhận tất định (tệp ảnh/PDF gần như không có chữ), không
chờ LLM. ⚑ TRANG KHÔNG CÓ Ô "GIẤY TỜ KHÁC": tệp ngoài danh mục đưa vào dòng Đơn đề nghị kèm cảnh báo.

Phân loại THUẦN LLM cho tệp có chữ (không lưới keyword). Không bỏ sót tệp nào.
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
_BAN_CHINH = "Bản chính"
_BAN_SAO = "Bản sao"

_T_DON = "don_de_nghi"
_T_VAN_BANG = "van_bang"
_T_CHUNG_CHI = "chung_chi_nghiep_vu"
_T_ANH = "anh_chan_dung"
_T_OTHER = "other"

_SLOT_ANH, _SLOT_DON, _SLOT_BANG = 0, 1, 2

_SLOT_NAMES = {
    _SLOT_ANH: "01 ảnh chân dung màu 3cm x 4cm hoặc bản điện tử ảnh màu",
    _SLOT_DON: "Đơn đề nghị cấp thẻ hướng dẫn viên du lịch nội địa (Mẫu số 04)",
    _SLOT_BANG: (
        "Bản sao bằng tốt nghiệp trung cấp trở lên chuyên ngành hướng dẫn du lịch; hoặc bản sao bằng "
        "tốt nghiệp chuyên ngành khác và bản sao chứng chỉ nghiệp vụ hướng dẫn du lịch nội địa"
    ),
}
_LOAI_BAN = {_SLOT_ANH: _BAN_CHINH, _SLOT_DON: _BAN_CHINH, _SLOT_BANG: _BAN_SAO}
# slotKey theo DÒNG (không theo loại giấy tờ): văn bằng và chứng chỉ phải chung key để engine gom vào
# một lần gán input. Cố ý không trùng FIXED_SLOT_KEYWORDS của extension để FE đi thẳng theo slotIndex.
_SLOT_KEYS = {_SLOT_ANH: "hdv_anh_chan_dung", _SLOT_DON: "hdv_don_de_nghi", _SLOT_BANG: "hdv_van_bang_chung_chi"}

_ROUTES: dict[str, int] = {
    _T_ANH: _SLOT_ANH,
    _T_DON: _SLOT_DON,
    _T_VAN_BANG: _SLOT_BANG,
    _T_CHUNG_CHI: _SLOT_BANG,
}
_DISPLAY = {
    _T_ANH: "Ảnh chân dung màu 3cm x 4cm",
    _T_DON: "Đơn đề nghị cấp thẻ hướng dẫn viên du lịch nội địa (Mẫu số 04)",
    _T_VAN_BANG: "Bản sao bằng tốt nghiệp",
    _T_CHUNG_CHI: "Bản sao chứng chỉ nghiệp vụ hướng dẫn du lịch nội địa",
}
_ALLOWED = set(_ROUTES) | {_T_OTHER}

# Thứ tự phủ dòng cho tệp gộp: Đơn đề nghị trước, rồi văn bằng/chứng chỉ, ảnh sau cùng.
_ROW_PRIORITY = (_T_DON, _T_VAN_BANG, _T_CHUNG_CHI, _T_ANH)

# Trang chỉ có 3 ô upload, không có dòng "Giấy tờ khác" → giấy tờ lạ vẫn phải lên hồ sơ ở dòng Đơn.
_SLOT_GIAY_TO_LA = _SLOT_DON

# Tệp ảnh/PDF có ít hơn ngần này ký tự chữ-số sau OCR coi như ảnh chân dung (ảnh 3x4 không có chữ).
_PHOTO_MAX_TEXT_CHARS = 30


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


def _looks_like_photo(file: dict, text: str) -> bool:
    kind = str(file.get("type") or "").lower()
    if not (kind.startswith("image/") or kind == "application/pdf"):
        return False
    return len(re.sub(r"[\W_]+", "", text or "")) < _PHOTO_MAX_TEXT_CHARS


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


def _item(index: int, file_name: str, slot_index: int, document_name: str, doc_type: str) -> dict:
    return {
        "fileIndex": index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": _SLOT_NAMES[slot_index],
        "loaiBan": _LOAI_BAN[slot_index],
        "target": "fixed-slot",
        "needsAddComponent": False,
        "slotKey": _SLOT_KEYS[slot_index],
        "slotIndex": slot_index,
        "slotName": _SLOT_NAMES[slot_index],
        "detectedType": doc_type,
    }


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, tuple[str, list[str]] | str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    """`llm_types[index]` = (docType, alsoTypes). Tệp ảnh chân dung đã được planner gán sẵn `anh_chan_dung`."""
    llm_types = llm_types or {}

    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    la: list[str] = []
    by_slot: dict[int, list[str]] = {}
    da_dung: set[str] = set()  # loại giấy tờ đã chiếm dòng
    co_trong_ho_so: set[str] = set()  # mọi loại đọc được, kể cả nằm trong tệp gộp

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        raw = llm_types.get(index)
        doc_type, also = raw if isinstance(raw, tuple) else (raw, [])
        if doc_type not in _ALLOWED:
            doc_type = _T_OTHER
        also = _normalize_also(also, doc_type) if doc_type != _T_OTHER else []
        source = "llm" if index in llm_types else "default"

        if doc_type == _T_OTHER:
            attachments.append(_item(index, file_name, _SLOT_GIAY_TO_LA, file_name, doc_type))
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
        slot = _ROUTES[chon]

        attachments.append(_item(index, file_name, slot, _DISPLAY[chon], chon))
        by_slot.setdefault(slot, []).append(file_name)
        da_dung.add(chon)
        co_trong_ho_so.update((doc_type, *also))
        classified.append({
            "fileName": file_name, "docType": doc_type, "alsoTypes": also,
            "assignedType": chon, "source": source, "slotIndex": slot,
        })

    if la:
        warnings.append(
            "Trang này chỉ có 3 ô đính kèm, KHÔNG có dòng \"Giấy tờ khác\", nên các tệp chưa nhận ra loại "
            f"đã được đưa vào dòng \"{_SLOT_NAMES[_SLOT_GIAY_TO_LA]}\": {', '.join(la)}. Cán bộ đối chiếu "
            "lại, bỏ tệp nếu nơi tiếp nhận không yêu cầu."
        )
    if _SLOT_ANH not in by_slot:
        warnings.append(
            "Chưa thấy ẢNH CHÂN DUNG màu 3cm x 4cm — thành phần bắt buộc. Tải ảnh (jpg/png hoặc PDF một "
            "trang chỉ có ảnh) rồi đính lại."
        )
    if _T_DON not in da_dung:
        warnings.append(
            "Chưa thấy ĐƠN ĐỀ NGHỊ cấp thẻ (Mẫu số 04) — thành phần bắt buộc, cán bộ bổ sung trước khi nộp."
        )
    if _T_VAN_BANG not in co_trong_ho_so:
        warnings.append(
            "Chưa thấy BẢN SAO BẰNG TỐT NGHIỆP trung cấp trở lên — thành phần bắt buộc (2), cán bộ bổ sung."
        )
    elif _SLOT_BANG not in by_slot:
        warnings.append(
            "Văn bằng đang nằm CHUNG TỆP với Đơn đề nghị nên dòng (2) còn trống — tách văn bằng/chứng chỉ "
            "ra tệp riêng rồi đính vào dòng (2)."
        )
    elif _T_CHUNG_CHI not in co_trong_ho_so:
        warnings.append(
            "Hồ sơ có văn bằng nhưng CHƯA có chứng chỉ nghiệp vụ hướng dẫn du lịch nội địa. Văn bằng không "
            "thuộc chuyên ngành hướng dẫn du lịch thì phải nộp kèm chứng chỉ này ở cùng dòng (2)."
        )
    for slot_index, names in by_slot.items():
        unique = list(dict.fromkeys(names))
        if len(unique) > 1 and slot_index != _SLOT_BANG:
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
    llm_types: dict[int, tuple[str, list[str]]] = {}
    llm_documents: list[dict[str, Any]] = []
    for index, file in enumerate(raw_files):
        entry = by_name.get(file.get("name"), {})
        text = str(entry.get("text") or "")
        # Ảnh chân dung không có chữ → nhận tất định. Tệp OCR lỗi thì KHÔNG coi là ảnh (có thể là đơn).
        if not entry.get("error") and file.get("type") in _OCR_TYPES and _looks_like_photo(file, text):
            llm_types[index] = (_T_ANH, [])
        elif text.strip():
            llm_documents.append({"index": index, "text": text})

    started = time.monotonic()
    if llm_documents:
        try:
            llm_types.update(await _classify_with_llm(llm_documents, errors))
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
