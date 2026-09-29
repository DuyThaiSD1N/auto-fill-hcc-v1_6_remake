"""Đính kèm [Đà Nẵng · Bộ VHTTDL] Thủ tục cấp thẻ hướng dẫn viên du lịch tại điểm (1.001440, QT-115).

Cổng `dichvucong.bvhttdl.gov.vn` — form và bảng thành phần hồ sơ NẰM CHUNG trang. Bảng chỉ có 2 dòng,
mỗi dòng một `<app-upload-flie-multi>` chứa input file (multiple) → engine FE `fixed-slot` (slotIndex =
thứ tự input file trên trang):

  0 : (1) Đơn đề nghị cấp thẻ hướng dẫn viên du lịch tại điểm (Mẫu số 06)        — Bản chính 1
  1 : (2) 02 ảnh chân dung màu size 3 cm x 4 cm hoặc bản điện tử ảnh màu        — Bản chính 1

⚑ KHÔNG CÓ DÒNG cho chứng chỉ nghiệp vụ, văn bằng hay "Giấy tờ khác": các tệp này ĐÍNH KÈM CHUNG vào
dòng (1) cùng Đơn (cùng `slotKey` → engine gom vào một lần gán input `multiple`), và cán bộ phải ghi rõ
ở ô "Mô tả" của dòng (1) — planner trả sẵn nội dung Mô tả trong cảnh báo vì engine chưa điền được modal.

⚑ ẢNH CHÂN DUNG không có chữ nên OCR rỗng → nhận tất định (tệp ảnh/PDF gần như không có chữ), không
chờ LLM. Ảnh in trên chứng chỉ KHÔNG thay được ảnh 3x4 riêng. Phân loại THUẦN LLM cho tệp có chữ (không
lưới keyword). Không bỏ sót tệp nào.
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

_T_DON = "don_de_nghi"
_T_CHUNG_CHI = "chung_chi_nghiep_vu"
_T_VAN_BANG = "van_bang"
_T_ANH = "anh_chan_dung"
_T_OTHER = "other"

_SLOT_DON, _SLOT_ANH = 0, 1

# Tên dòng theo nhãn chuẩn hoá của bản mapping (DOM gốc bị Google Dịch) — chỉ để hiển thị, FE đi theo slotIndex.
_SLOT_NAMES = {
    _SLOT_DON: "Đơn đề nghị cấp thẻ hướng dẫn viên du lịch tại điểm (Mẫu số 06)",
    _SLOT_ANH: "02 ảnh chân dung màu cỡ 3 cm x 4 cm hoặc bản điện tử ảnh màu",
}
_LOAI_BAN = {_SLOT_DON: _BAN_CHINH, _SLOT_ANH: _BAN_CHINH}
# slotKey theo DÒNG (không theo loại giấy tờ): tệp đính kèm chung phải chung key với Đơn để engine gom vào
# một lần gán input. Cố ý không trùng FIXED_SLOT_KEYWORDS của extension để FE đi thẳng theo slotIndex.
_SLOT_KEYS = {_SLOT_DON: "hdvtd_don_de_nghi", _SLOT_ANH: "hdvtd_anh_chan_dung"}

# Mọi loại giấy tờ không phải ảnh đều lên dòng Đơn — trang không có dòng nào khác.
_ROUTES: dict[str, int] = {
    _T_DON: _SLOT_DON,
    _T_CHUNG_CHI: _SLOT_DON,
    _T_VAN_BANG: _SLOT_DON,
    _T_ANH: _SLOT_ANH,
}
_DISPLAY = {
    _T_DON: "Đơn đề nghị cấp thẻ hướng dẫn viên du lịch",
    _T_CHUNG_CHI: "Chứng chỉ nghiệp vụ hướng dẫn du lịch",
    _T_VAN_BANG: "Bằng tốt nghiệp",
    _T_ANH: "Ảnh chân dung màu 3cm x 4cm",
}
_ALLOWED = set(_ROUTES) | {_T_OTHER}

# Thứ tự chọn loại cho tệp gộp: Đơn trước, rồi chứng chỉ/văn bằng, ảnh sau cùng.
_ROW_PRIORITY = (_T_DON, _T_CHUNG_CHI, _T_VAN_BANG, _T_ANH)


def _normalize_doc_type(value: Any) -> str:
    canon = _canon(value)
    for doc_type in _ALLOWED:
        if canon == _canon(doc_type):
            return doc_type
    return _T_OTHER


def _normalize_also(values: Any, primary: str) -> list[str]:
    """Loại giấy tờ KHÁC cùng nằm trong một tệp gộp — chỉ dùng để ghi Mô tả và chọn dòng."""
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


def _mo_ta(files_on_don: list[tuple[str, str, list[str]]]) -> str:
    """Nội dung gợi ý cho ô "Mô tả" của dòng Đơn khi dòng này nhận nhiều tệp."""
    parts = []
    for n, (file_name, doc_type, also) in enumerate(files_on_don, start=1):
        loai = " + ".join(_DISPLAY.get(t, "") for t in (doc_type, *also) if t in _DISPLAY) or "Giấy tờ khác"
        parts.append(f"({n}) {loai} — tệp {file_name}")
    return (
        f"Đính kèm chung {len(files_on_don)} tệp: " + "; ".join(parts) + ". Lý do: danh mục thành phần hồ "
        "sơ trực tuyến không có dòng riêng cho các giấy tờ này."
    )


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, tuple[str, list[str]] | str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    """`llm_types[index]` = (docType, alsoTypes). Tệp ảnh chân dung đã được planner gán sẵn `anh_chan_dung`."""
    llm_types = llm_types or {}

    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    tren_dong_don: list[tuple[str, str, list[str]]] = []  # (tên tệp, loại, alsoTypes) theo thứ tự
    so_tep_don = 0
    co_anh = False
    co_trong_ho_so: set[str] = set()

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        raw = llm_types.get(index)
        doc_type, also = raw if isinstance(raw, tuple) else (raw, [])
        if doc_type not in _ALLOWED:
            doc_type = _T_OTHER
        also = _normalize_also(also, doc_type) if doc_type != _T_OTHER else []
        source = "llm" if index in llm_types else "default"

        if doc_type == _T_OTHER:
            chon, slot, document_name = None, _SLOT_DON, file_name
        else:
            loai_trong_tep = (doc_type, *also)
            chua_co = [t for t in _ROW_PRIORITY if t in loai_trong_tep and t not in co_trong_ho_so]
            chon = chua_co[0] if chua_co else doc_type
            slot, document_name = _ROUTES[chon], _DISPLAY[chon]
            co_trong_ho_so.update(loai_trong_tep)

        attachments.append(_item(index, file_name, slot, document_name, chon or doc_type))
        if slot == _SLOT_ANH:
            co_anh = True
        else:
            tren_dong_don.append((file_name, doc_type, also))
            if chon == _T_DON:
                so_tep_don += 1
        classified.append({
            "fileName": file_name, "docType": doc_type, "alsoTypes": also,
            "assignedType": chon, "source": source, "slotIndex": slot,
        })

    if _T_DON not in co_trong_ho_so:
        warnings.append(
            "Chưa thấy ĐƠN ĐỀ NGHỊ cấp thẻ hướng dẫn viên du lịch tại điểm (Mẫu số 06) — thành phần bắt buộc "
            "(1), cán bộ bổ sung trước khi nộp."
        )
    elif so_tep_don > 1:
        warnings.append(
            f"Có {so_tep_don} tệp cùng nhận là Đơn đề nghị — kiểm tra lại, dòng (1) chỉ cần 01 bản chính."
        )
    if not co_anh:
        warnings.append(
            "Chưa thấy ẢNH CHÂN DUNG màu 3cm x 4cm — thành phần bắt buộc (2). Ảnh in trên chứng chỉ/CCCD không "
            "thay được; tải ảnh riêng (jpg/png hoặc PDF một trang chỉ có ảnh) rồi đính lại."
        )
    # Nhiều tệp, tệp không phải đơn, hoặc MỘT tệp scan gộp đơn + chứng chỉ/văn bằng đều cần ghi Mô tả.
    if len(tren_dong_don) > 1 or any(t != _T_DON or a for _n, t, a in tren_dong_don):
        warnings.append(
            "Dòng (1) Đơn đề nghị nhận CHUNG các giấy tờ không có dòng riêng trên trang. Cán bộ bấm nút Mô tả "
            f"của dòng (1) và ghi: \"{_mo_ta(tren_dong_don)}\""
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
