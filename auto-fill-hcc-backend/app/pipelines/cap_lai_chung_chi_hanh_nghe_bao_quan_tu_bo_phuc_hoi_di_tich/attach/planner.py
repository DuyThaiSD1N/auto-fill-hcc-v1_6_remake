"""Đính kèm [Bộ VHTTDL] Thủ tục cấp lại Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích (1.002003, QT-10).

Cùng cổng, cùng kiểu bảng với bản cấp mới 1.001822: 3 dòng, mỗi dòng một `<app-upload-flie-multi>` → engine FE
`fixed-slot` dò ô THEO CHỮ của dòng (sectionHeader + slotKeywords):

  0 : (1) Đơn đề nghị cấp lại CCHN … theo Mẫu số 51                                — Bản chính 1
  1 : (2) Trường hợp bổ sung nội dung hành nghề … bản sao có chứng thực chứng chỉ,
          chứng nhận … đối với nội dung hành nghề bổ sung                          — Bản chính 1
  2 : (3) Ít nhất 02 ảnh màu khổ 4 cm x 6 cm                                        — Bản chính 1

⚑ Trang KHÔNG có dòng riêng cho chứng chỉ đã cấp (hết hạn) hay văn bằng/chứng chỉ bồi dưỡng/CCHN xây dựng → theo
ánh xạ của BA tạm đính CHUNG dòng (2) (dòng duy nhất nhận bản sao), kèm cảnh báo "cần xác nhận". Tệp chưa nhận ra
loại cũng vào dòng (2). CCCD chỉ dùng để điền → không đính.

⚑ ẢNH 4x6 không có chữ nhưng tệp ký số của Sở in dấu "Ký bởi … Cơ quan … Ngày ký …" → bỏ khối dấu đó rồi mới đếm
chữ, nhận tất định không chờ LLM. Hai ảnh giống hệt nhau từng byte vẫn đính đủ hai, cảnh báo cán bộ xác nhận.
"""

import asyncio
import re
import time
from typing import Any

from app.config import settings
from app.pipelines.cap_chung_chi_hanh_nghe_bao_quan_tu_bo_phuc_hoi_di_tich.attach.planner import (
    _OCR_TYPES,
    _canon,
    _fold,
    _looks_like_photo,
)
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_T_DON = "don_de_nghi"
_T_CC_DA_CAP = "chung_chi_da_cap"
_T_CCHN_XD = "cchn_xay_dung"
_T_CCHN_KT = "cchn_kien_truc"
_T_VAN_BANG = "van_bang"
_T_BOI_DUONG = "chung_chi_boi_duong"
_T_ANH = "anh_the"
_T_CCCD = "cccd"
_T_OTHER = "other"

_SLOT_DON, _SLOT_BAN_SAO, _SLOT_ANH = 0, 1, 2

_SLOT_NAMES = {
    _SLOT_DON: "Đơn đề nghị cấp lại Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích theo Mẫu số 51",
    _SLOT_BAN_SAO: (
        "Trường hợp bổ sung nội dung hành nghề: bản sao có chứng thực chứng chỉ, chứng nhận đối với nội dung hành "
        "nghề bổ sung"
    ),
    _SLOT_ANH: "Ít nhất 02 ảnh màu khổ 4 cm x 6 cm",
}
_LOAI_BAN = {_SLOT_DON: "Bản chính", _SLOT_BAN_SAO: "Bản sao", _SLOT_ANH: "Bản chính"}

# Cụm chữ riêng của từng dòng (đã fold dấu): dòng (2) mở đầu "Trường hợp bổ sung nội dung hành nghề…", dòng (1)
# không có cụm này.
_BANG_HEADER = "Thành phần hồ sơ"
_SLOT_KEYWORDS = {
    _SLOT_DON: ["mau so 51"],
    _SLOT_BAN_SAO: ["truong hop bo sung noi dung"],
    _SLOT_ANH: ["anh mau kho 4"],
}

_ROUTES: dict[str, int] = {
    _T_DON: _SLOT_DON,
    _T_CC_DA_CAP: _SLOT_BAN_SAO,
    _T_CCHN_XD: _SLOT_BAN_SAO,
    _T_CCHN_KT: _SLOT_BAN_SAO,
    _T_VAN_BANG: _SLOT_BAN_SAO,
    _T_BOI_DUONG: _SLOT_BAN_SAO,
    _T_ANH: _SLOT_ANH,
}
_DISPLAY = {
    _T_DON: "Đơn đề nghị cấp lại Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích (Mẫu số 51)",
    _T_CC_DA_CAP: "Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích đã được cấp",
    _T_CCHN_XD: "Bản sao Chứng chỉ hành nghề hoạt động xây dựng",
    _T_CCHN_KT: "Bản sao Chứng chỉ hành nghề kiến trúc",
    _T_VAN_BANG: "Bản sao bằng tốt nghiệp đại học",
    _T_BOI_DUONG: "Bản sao chứng chỉ bồi dưỡng kiến thức bảo quản, tu bổ, phục hồi di tích",
    _T_ANH: "Ảnh màu 4 cm x 6 cm",
}
_KHONG_DINH = {
    _T_CCCD: "căn cước chỉ dùng để điền, không thuộc thành phần hồ sơ",
}
_ALLOWED = set(_ROUTES) | set(_KHONG_DINH) | {_T_OTHER}
_SLOT_GIAY_TO_LA = _SLOT_BAN_SAO

# Dấu ký số in trên tệp: "Ký bởi: … Cơ quan: … Ngày ký: 30-10-2026 14:53:01 +07:00" (đã fold).
_DAU_KY_SO_RE = re.compile(r"ky boi\s*:.*?ngay ky\s*:?\s*[\d\-/.]+\s*[\d:]*\s*(\+\d{2}:?\d{2})?", re.DOTALL)


def _bo_dau_ky_so(text: str) -> str:
    return _DAU_KY_SO_RE.sub(" ", _fold(text))


def _normalize_doc_type(value: Any) -> str:
    canon = _canon(value)
    return next((t for t in _ALLOWED if canon == _canon(t)), _T_OTHER)


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
            "slotKey": f"cchn_di_tich_cap_lai_row_{slot}",
            "slotIndex": slot,
            "slotName": _SLOT_NAMES[slot],
            "sectionHeader": _BANG_HEADER,
            "slotKeywords": _SLOT_KEYWORDS[slot],
            "detectedType": doc_type,
        })
        classified.append({"fileName": file_name, "docType": doc_type, "source": source, "slotIndex": slot})

    by_slot: dict[int, list[dict]] = {}
    for item in attachments:
        by_slot.setdefault(item["slotIndex"], []).append(item)

    warnings: list[str] = []
    if khong_dinh:
        warnings.append("Không đính vào bảng thành phần hồ sơ: " + "; ".join(khong_dinh) + ".")
    if _SLOT_DON not in by_slot:
        warnings.append(
            "Chưa thấy ĐƠN ĐỀ NGHỊ CẤP LẠI (Mẫu số 51) — thành phần bắt buộc, cán bộ bổ sung trước khi nộp."
        )
    tam_xep = [i["fileName"] for i in by_slot.get(_SLOT_BAN_SAO, []) if i["detectedType"] != _T_OTHER]
    if tam_xep:
        warnings.append(
            "Dòng (2) dành cho trường hợp BỔ SUNG nội dung hành nghề; trang không có dòng riêng cho chứng chỉ đã cấp "
            f"/ văn bằng nên tạm đính ở đây: {', '.join(tam_xep)} — cán bộ xác nhận với Sở, bỏ tệp nếu không cần."
        )
    if la:
        warnings.append(
            f"Chưa nhận ra loại giấy tờ, đã đưa vào dòng (2): {', '.join(la)} — cán bộ đối chiếu lại, bỏ tệp nếu nơi "
            "tiếp nhận không yêu cầu."
        )
    if _T_CC_DA_CAP not in seen:
        warnings.append(
            "Chưa thấy CHỨNG CHỈ HÀNH NGHỀ đã được cấp — cán bộ kiểm tra số, ngày cấp chứng chỉ cũ trên Đơn."
        )
    anh = by_slot.get(_SLOT_ANH, [])
    if len(anh) < 2:
        warnings.append(
            f"Thành phần (3) cần ít nhất 02 ảnh màu 4 cm x 6 cm, hồ sơ mới có {len(anh)} ảnh — tải thêm ảnh rồi đính lại."
        )
    trung: dict[str, list[str]] = {}
    for item in anh:
        data = files[item["fileIndex"]].get("dataUrl")
        if data:
            trung.setdefault(data, []).append(item["fileName"])
    for names in trung.values():
        if len(names) > 1:
            warnings.append(
                f"Các ảnh {', '.join(names)} giống hệt nhau từng byte (cùng một bản scan) — cán bộ xác nhận nơi tiếp "
                "nhận có chấp nhận, và ảnh chụp trong 06 tháng gần nhất."
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
        # Ảnh 4x6 chỉ còn dấu ký số → nhận tất định. Tệp OCR lỗi thì KHÔNG coi là ảnh (có thể là đơn).
        elif _looks_like_photo(file, _bo_dau_ky_so(text)):
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
