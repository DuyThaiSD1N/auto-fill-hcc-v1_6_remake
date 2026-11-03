"""Đính kèm [Bộ VHTTDL] Thủ tục cấp Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích (1.001822, QT-09).

Cổng `dichvucong.bvhttdl.gov.vn` — form và bảng thành phần hồ sơ CHUNG trang `/nop-ho-so`. Bảng có 3 dòng, mỗi
dòng một `<app-upload-flie-multi>` (input file multiple) → engine FE `fixed-slot`, dò ô THEO CHỮ của dòng
(sectionHeader + slotKeywords) như thủ tục quảng cáo băng-rôn:

  0 : (1) Đơn đề nghị cấp CCHN … theo Mẫu số 51                                   — Bản chính 1
  1 : (2) Bản sao chứng thực CCHN thiết kế quy hoạch xây dựng / thiết kế xây dựng /
          giám sát thi công, bằng tốt nghiệp đại học trở lên chuyên ngành liên quan  — Bản sao 1
  2 : (3) Ít nhất 02 ảnh màu khổ 4 cm x 6 cm                                        — Bản chính 1

Dòng (2) nhận CHUNG CCHN xây dựng + CCHN kiến trúc + bằng đại học + chứng chỉ bồi dưỡng; dòng (3) nhận cả hai
ảnh — các tệp cùng dòng chung `slotKey` để engine gom vào một lần gán input `multiple`.

⚑ CHỨNG CHỈ BỒI DƯỠNG không có dòng riêng trong bảng. Ánh xạ của BA đặt nó ở mục "Hồ sơ gửi kèm" (vùng kéo thả
ngoài bảng, engine fixed-slot không với tới, chưa có DOM để làm) → xếp vào dòng (2) như bản mapping Excel ("tạm
xếp vào đây"), không để sót tệp (trace req_ddac8c0e0653). CCCD chỉ dùng để điền, không thuộc thành phần hồ sơ →
không đính. Tệp chưa nhận ra loại → dòng (2) kèm cảnh báo.

⚑ ẢNH 4x6 không có chữ nên OCR rỗng → nhận tất định (tệp ảnh/PDF gần như không có chữ), không chờ LLM.
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

_T_DON = "don_de_nghi"
_T_CCHN_XD = "cchn_xay_dung"
_T_CCHN_KT = "cchn_kien_truc"
_T_VAN_BANG = "van_bang"
_T_BOI_DUONG = "chung_chi_boi_duong"
_T_ANH = "anh_the"
_T_CCCD = "cccd"
_T_OTHER = "other"

_SLOT_DON, _SLOT_BAN_SAO, _SLOT_ANH = 0, 1, 2

_SLOT_NAMES = {
    _SLOT_DON: "Đơn đề nghị cấp Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích theo Mẫu số 51",
    _SLOT_BAN_SAO: (
        "Bản sao có chứng thực Chứng chỉ hành nghề thiết kế quy hoạch xây dựng, hành nghề thiết kế xây dựng, hành "
        "nghề giám sát thi công xây dựng, bằng tốt nghiệp đại học trở lên"
    ),
    _SLOT_ANH: "Ít nhất 02 ảnh màu khổ 4 cm x 6 cm",
}
_LOAI_BAN = {_SLOT_DON: "Bản chính", _SLOT_BAN_SAO: "Bản sao", _SLOT_ANH: "Bản chính"}

# Engine khoanh các dòng dưới tiêu đề bảng rồi khớp cụm chữ riêng của từng dòng (đã fold dấu). Cụm không lặp ở
# dòng khác: dòng (2) cũng có chữ "đề nghị cấp Chứng chỉ hành nghề bảo quản" nhưng không có "mẫu số 51".
_BANG_HEADER = "Thành phần hồ sơ"
_SLOT_KEYWORDS = {
    _SLOT_DON: ["mau so 51"],
    _SLOT_BAN_SAO: ["bang tot nghiep dai hoc"],
    _SLOT_ANH: ["anh mau kho 4"],
}

_ROUTES: dict[str, int] = {
    _T_DON: _SLOT_DON,
    _T_CCHN_XD: _SLOT_BAN_SAO,
    _T_CCHN_KT: _SLOT_BAN_SAO,
    _T_VAN_BANG: _SLOT_BAN_SAO,
    _T_BOI_DUONG: _SLOT_BAN_SAO,
    _T_ANH: _SLOT_ANH,
}
_DISPLAY = {
    _T_DON: "Đơn đề nghị cấp Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích (Mẫu số 51)",
    _T_CCHN_XD: "Bản sao Chứng chỉ hành nghề hoạt động xây dựng",
    _T_CCHN_KT: "Bản sao Chứng chỉ hành nghề kiến trúc",
    _T_VAN_BANG: "Bản sao bằng tốt nghiệp đại học",
    _T_BOI_DUONG: "Bản sao chứng chỉ bồi dưỡng kiến thức bảo quản, tu bổ, phục hồi di tích",
    _T_ANH: "Ảnh màu 4 cm x 6 cm",
}
# Không đính vào bảng: loại → lý do hiện cho cán bộ.
_KHONG_DINH = {
    _T_CCCD: "căn cước chỉ dùng để điền, không thuộc thành phần hồ sơ",
}
_ALLOWED = set(_ROUTES) | set(_KHONG_DINH) | {_T_OTHER}
_SLOT_GIAY_TO_LA = _SLOT_BAN_SAO

# Tệp ảnh/PDF có ít hơn ngần này ký tự chữ-số sau OCR coi như ảnh chân dung (ảnh 4x6 không có chữ).
_PHOTO_MAX_TEXT_CHARS = 30


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _canon(value: Any) -> str:
    return re.sub(r"[_\-\s]+", "_", _fold(value)).strip("_")


def _normalize_doc_type(value: Any) -> str:
    canon = _canon(value)
    return next((t for t in _ALLOWED if canon == _canon(t)), _T_OTHER)


def _looks_like_photo(file: dict, text: str) -> bool:
    kind = str(file.get("type") or "").lower()
    if not (kind.startswith("image/") or kind == "application/pdf"):
        return False
    return len(re.sub(r"[\W_]+", "", text or "")) < _PHOTO_MAX_TEXT_CHARS


async def _classify_one(document: dict[str, Any]) -> tuple[int, str]:
    index = int(document["index"])
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(
            [{"index": index, "text": str(document.get("text") or "")[:14000]}]
        )},
    ]
    raw = await client.chat(messages, max_tokens=180, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    first = next(iter(parsed.get("documents", []) or []), {})
    return index, _normalize_doc_type(first.get("docType") or first.get("type"))


async def _classify_with_llm(documents: list[dict[str, Any]], errors: list[str]) -> dict[int, str]:
    outcomes = await asyncio.gather(*(_classify_one(d) for d in documents), return_exceptions=True)
    result: dict[int, str] = {}
    for document, outcome in zip(documents, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            errors.append(f"attachment_agent file {document.get('index')}: {outcome}")
            continue
        result[outcome[0]] = outcome[1]
    return result


def build_plan_items(
    files: list[dict], llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    """`llm_types[index]` = docType. Tệp ảnh 4x6 đã được planner gán sẵn `anh_the`."""
    llm_types = llm_types or {}
    attachments: list[dict] = []
    classified: list[dict] = []
    la: list[str] = []
    khong_dinh: list[str] = []
    seen: set[str] = set()

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        doc_type = llm_types.get(index, _T_OTHER)
        if doc_type not in _ALLOWED:
            doc_type = _T_OTHER
        source = "llm" if index in llm_types else "default"
        seen.add(doc_type)

        if doc_type in _KHONG_DINH:
            khong_dinh.append(f"{file_name} ({_KHONG_DINH[doc_type]})")
            classified.append({
                "fileName": file_name, "docType": doc_type, "source": source,
                "target": "skip", "reason": _KHONG_DINH[doc_type],
            })
            continue

        slot = _ROUTES.get(doc_type, _SLOT_GIAY_TO_LA)
        if doc_type == _T_OTHER:
            la.append(file_name)
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": _DISPLAY.get(doc_type, file_name),
            "componentName": _SLOT_NAMES[slot],
            "loaiBan": _LOAI_BAN[slot],
            "target": "fixed-slot",
            "needsAddComponent": False,
            # slotKey theo DÒNG: các tệp cùng dòng phải chung key để engine gom vào một lần gán input.
            "slotKey": f"cchn_di_tich_row_{slot}",
            "slotIndex": slot,
            "slotName": _SLOT_NAMES[slot],
            "sectionHeader": _BANG_HEADER,
            "slotKeywords": _SLOT_KEYWORDS[slot],
            "detectedType": doc_type,
        })
        classified.append({"fileName": file_name, "docType": doc_type, "source": source, "slotIndex": slot})

    by_slot: dict[int, int] = {}
    for item in attachments:
        by_slot[item["slotIndex"]] = by_slot.get(item["slotIndex"], 0) + 1

    warnings: list[str] = []
    if khong_dinh:
        warnings.append("Không đính vào bảng thành phần hồ sơ: " + "; ".join(khong_dinh) + ".")
    if la:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã đưa vào dòng (2) bản sao chứng chỉ/văn bằng (trang không có ô giấy tờ "
            f"khác): {', '.join(la)} — cán bộ đối chiếu lại, bỏ tệp nếu nơi tiếp nhận không yêu cầu."
        )
    if _SLOT_DON not in by_slot:
        warnings.append("Chưa thấy ĐƠN ĐỀ NGHỊ (Mẫu số 51) — thành phần bắt buộc, cán bộ bổ sung trước khi nộp.")
    if not seen & {_T_CCHN_XD, _T_CCHN_KT, _T_VAN_BANG}:
        warnings.append(
            "Chưa thấy bản sao CHỨNG CHỈ HÀNH NGHỀ xây dựng/kiến trúc hoặc BẰNG TỐT NGHIỆP đại học — thành phần "
            "bắt buộc (2), cán bộ bổ sung."
        )
    so_anh = by_slot.get(_SLOT_ANH, 0)
    if so_anh < 2:
        warnings.append(
            f"Thành phần (3) cần ít nhất 02 ảnh màu 4 cm x 6 cm, hồ sơ mới có {so_anh} ảnh — tải thêm ảnh rồi đính lại."
        )
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_pairs = [(index, file) for index, file in enumerate(raw_files) if file.get("type") in _OCR_TYPES]
    errors: list[str] = []

    from app.services import ocr

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file([file for _, file in ocr_pairs]) if ocr_pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)

    # Kết quả OCR khớp THỨ TỰ đầu vào — hai ảnh 4x6 giống hệt nhau vẫn là hai tệp, không map theo tên.
    llm_types: dict[int, str] = {}
    llm_documents: list[dict[str, Any]] = []
    for (index, file), result in zip(ocr_pairs, ocr_results):
        text = str(result.get("text") or "")
        if result.get("error"):
            errors.append(f"OCR {result.get('name')}: {result['error']}")
        # Ảnh 4x6 không có chữ → nhận tất định. Tệp OCR lỗi thì KHÔNG coi là ảnh (có thể là đơn).
        elif _looks_like_photo(file, text):
            llm_types[index] = _T_ANH
            continue
        if text.strip():
            llm_documents.append({"index": index, "text": text})

    started = time.monotonic()
    if llm_documents:
        llm_types.update(await _classify_with_llm(llm_documents, errors))
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, llm_types)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "llmDocuments": [raw_files[d["index"]]["name"] for d in llm_documents],
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
