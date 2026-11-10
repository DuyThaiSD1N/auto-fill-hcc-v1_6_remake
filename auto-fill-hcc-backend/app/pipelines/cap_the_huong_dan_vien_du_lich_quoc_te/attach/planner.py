"""Đính kèm [Bộ VHTTDL] Thủ tục cấp thẻ hướng dẫn viên du lịch quốc tế (1.004628, QT-120).

Cổng `dichvucong.bvhttdl.gov.vn` — form và bảng thành phần hồ sơ NẰM CHUNG trang. Bảng có 4 dòng, mỗi dòng một
`<app-upload-flie-multi>` chứa input file (multiple) → engine FE `fixed-slot` (slotIndex = thứ tự input file trên trang,
KHÔNG phải số (1)(3)(4) in trong tên thành phần — cổng đánh số lệch, hai dòng cùng số (4)):

  0 : (4) 01 ảnh chân dung màu 3 cm x 4 cm hoặc bản điện tử ảnh màu          — Bản chính 1
  1 : (1) Đơn đề nghị cấp thẻ hướng dẫn viên du lịch quốc tế (Mẫu số 04)      — Bản chính 1
  2 : (3) Giấy tờ chứng minh điều kiện về trình độ ngoại ngữ                   — Bản sao 1
  3 : (4) Giấy tờ chứng minh điều kiện về trình độ nghiệp vụ                   — Bản sao 1

⚑ Dòng 3 nhận CHUNG văn bằng + chứng chỉ nghiệp vụ HDV quốc tế (văn bằng ngành khác): hai item cùng `slotKey` → engine
gom vào một lần gán input `multiple`; tệp scan gộp cả hai thì đính nguyên tệp, không tách.

⚑ ẢNH CHÂN DUNG không có chữ nên OCR rỗng → nhận tất định, không chờ LLM. ⚑ TRANG KHÔNG CÓ Ô "GIẤY TỜ KHÁC": tệp ngoài
danh mục (CCCD…) đưa vào dòng Đơn đề nghị kèm cảnh báo.

Phân loại THUẦN LLM cho tệp có chữ (không lưới keyword). Không bỏ sót tệp nào.
"""

import asyncio
import time
from typing import Any

from app.config import settings
from app.pipelines.cap_the_huong_dan_vien_du_lich_noi_dia.attach.planner import _canon, _looks_like_photo
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_BAN_CHINH = "Bản chính"
_BAN_SAO = "Bản sao"

_T_DON = "don_de_nghi"
_T_CC_NGOAI_NGU = "chung_chi_ngoai_ngu"
_T_VB_NGOAI_NGU = "van_bang_ngoai_ngu"
_T_VAN_BANG = "van_bang"
_T_CHUNG_CHI = "chung_chi_nghiep_vu"
_T_ANH = "anh_chan_dung"
_T_OTHER = "other"

_SLOT_ANH, _SLOT_DON, _SLOT_NGOAI_NGU, _SLOT_NGHIEP_VU = 0, 1, 2, 3

_SLOT_NAMES = {
    _SLOT_ANH: "01 ảnh chân dung màu 3 cm x 4 cm hoặc bản điện tử ảnh màu",
    _SLOT_DON: "Đơn đề nghị cấp thẻ hướng dẫn viên du lịch quốc tế (Mẫu số 04)",
    _SLOT_NGOAI_NGU: "Giấy tờ chứng minh điều kiện về trình độ ngoại ngữ",
    _SLOT_NGHIEP_VU: "Giấy tờ chứng minh điều kiện về trình độ nghiệp vụ",
}
_LOAI_BAN = {_SLOT_ANH: _BAN_CHINH, _SLOT_DON: _BAN_CHINH, _SLOT_NGOAI_NGU: _BAN_SAO, _SLOT_NGHIEP_VU: _BAN_SAO}
# slotKey theo DÒNG (không theo loại giấy tờ): văn bằng và chứng chỉ nghiệp vụ chung key để engine gom vào một lần gán
# input. Cố ý không trùng FIXED_SLOT_KEYWORDS của extension để FE đi thẳng theo slotIndex.
_SLOT_KEYS = {
    _SLOT_ANH: "hdvqt_anh_chan_dung",
    _SLOT_DON: "hdvqt_don_de_nghi",
    _SLOT_NGOAI_NGU: "hdvqt_ngoai_ngu",
    _SLOT_NGHIEP_VU: "hdvqt_nghiep_vu",
}

_ROUTES: dict[str, int] = {
    _T_ANH: _SLOT_ANH,
    _T_DON: _SLOT_DON,
    _T_CC_NGOAI_NGU: _SLOT_NGOAI_NGU,
    _T_VB_NGOAI_NGU: _SLOT_NGOAI_NGU,
    _T_VAN_BANG: _SLOT_NGHIEP_VU,
    _T_CHUNG_CHI: _SLOT_NGHIEP_VU,
}
_DISPLAY = {
    _T_ANH: "Ảnh chân dung màu 3 cm x 4 cm",
    _T_DON: "Đơn đề nghị cấp thẻ hướng dẫn viên du lịch quốc tế (Mẫu số 04)",
    _T_CC_NGOAI_NGU: "Bản sao chứng chỉ ngoại ngữ",
    _T_VB_NGOAI_NGU: "Bản sao bằng tốt nghiệp chuyên ngành ngoại ngữ",
    _T_VAN_BANG: "Bản sao có chứng thực bằng tốt nghiệp",
    _T_CHUNG_CHI: "Bản sao có chứng thực chứng chỉ nghiệp vụ hướng dẫn du lịch quốc tế",
}
_ALLOWED = set(_ROUTES) | {_T_OTHER}
_NGOAI_NGU = {_T_CC_NGOAI_NGU, _T_VB_NGOAI_NGU}

# Thứ tự phủ dòng cho tệp gộp: Đơn đề nghị trước, rồi ngoại ngữ, nghiệp vụ, ảnh sau cùng.
_ROW_PRIORITY = (_T_DON, _T_CC_NGOAI_NGU, _T_VB_NGOAI_NGU, _T_VAN_BANG, _T_CHUNG_CHI, _T_ANH)

# Trang chỉ có 4 ô upload, không có dòng "Giấy tờ khác" → giấy tờ lạ vẫn phải lên hồ sơ ở dòng Đơn.
_SLOT_GIAY_TO_LA = _SLOT_DON


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
        chua_co = [t for t in _ROW_PRIORITY if t in (doc_type, *also) and _ROUTES[t] not in by_slot]
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
            "Trang này chỉ có 4 ô đính kèm, KHÔNG có dòng \"Giấy tờ khác\", nên các tệp chưa nhận ra loại đã được đưa "
            f"vào dòng \"{_SLOT_NAMES[_SLOT_GIAY_TO_LA]}\": {', '.join(la)}. Cán bộ đối chiếu lại, bỏ tệp nếu nơi tiếp "
            "nhận không yêu cầu."
        )
    if _SLOT_ANH not in by_slot:
        warnings.append(
            "Chưa thấy ẢNH CHÂN DUNG màu 3 cm x 4 cm — thành phần bắt buộc. Tải ảnh (jpg/png hoặc PDF một trang chỉ có "
            "ảnh) rồi đính lại."
        )
    if _T_DON not in da_dung:
        warnings.append(
            "Chưa thấy ĐƠN ĐỀ NGHỊ cấp thẻ hướng dẫn viên du lịch quốc tế (Mẫu số 04) — thành phần bắt buộc, cán bộ bổ "
            "sung trước khi nộp."
        )
    if not (co_trong_ho_so & _NGOAI_NGU):
        warnings.append(
            "Chưa thấy GIẤY TỜ CHỨNG MINH TRÌNH ĐỘ NGOẠI NGỮ (chứng chỉ ngoại ngữ còn hạn từ bậc 4/B2, hoặc bằng tốt "
            "nghiệp chuyên ngành ngoại ngữ) — thành phần bắt buộc (3), cán bộ bổ sung."
        )
    elif _SLOT_NGOAI_NGU not in by_slot:
        warnings.append(
            "Giấy tờ ngoại ngữ đang nằm CHUNG TỆP với giấy tờ khác nên dòng (3) còn trống — tách ra tệp riêng rồi đính "
            "vào dòng (3)."
        )
    co_van_bang = bool(co_trong_ho_so & {_T_VAN_BANG, _T_VB_NGOAI_NGU})
    if not co_van_bang:
        warnings.append(
            "Chưa thấy BẢN SAO CÓ CHỨNG THỰC BẰNG TỐT NGHIỆP cao đẳng trở lên — thành phần bắt buộc (4) giấy tờ nghiệp "
            "vụ, cán bộ bổ sung."
        )
    elif _SLOT_NGHIEP_VU not in by_slot:
        warnings.append(
            "Dòng (4) giấy tờ nghiệp vụ còn trống: văn bằng đang nằm chung tệp với giấy tờ khác hoặc chỉ có bằng ngành "
            "ngoại ngữ (đã đính dòng ngoại ngữ). Đính thêm bản sao văn bằng + chứng chỉ nghiệp vụ vào dòng (4)."
        )
    elif _T_VAN_BANG not in co_trong_ho_so:
        warnings.append(
            "Dòng (4) giấy tờ nghiệp vụ chỉ có chứng chỉ, chưa có văn bằng: bằng tốt nghiệp duy nhất (ngành ngoại ngữ) "
            "đã đính dòng (3). Đính THÊM bản sao bằng đó vào dòng (4) cùng chứng chỉ nghiệp vụ."
        )
    elif _T_CHUNG_CHI not in co_trong_ho_so:
        warnings.append(
            "Hồ sơ có văn bằng nhưng CHƯA có chứng chỉ nghiệp vụ hướng dẫn du lịch quốc tế. Văn bằng không thuộc chuyên "
            "ngành hướng dẫn du lịch thì phải nộp kèm chứng chỉ này ở cùng dòng (4)."
        )
    for slot_index, names in by_slot.items():
        unique = list(dict.fromkeys(names))
        if len(unique) > 1 and slot_index not in (_SLOT_NGHIEP_VU, _SLOT_NGOAI_NGU):
            warnings.append(
                f"Dòng \"{_SLOT_NAMES[slot_index]}\" nhận {len(unique)} tệp ({', '.join(unique)}) — kiểm tra lại số "
                "bản khai trên bảng thành phần hồ sơ."
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
