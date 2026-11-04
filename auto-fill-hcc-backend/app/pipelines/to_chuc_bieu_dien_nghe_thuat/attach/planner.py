"""Đính kèm [Bộ VHTTDL] Thủ tục tổ chức biểu diễn nghệ thuật (1.009397).

Cổng `dichvucong.bvhttdl.gov.vn` — form và bảng thành phần hồ sơ CHUNG trang `/nop-ho-so`. Bảng có 2 dòng, mỗi
dòng một `<app-upload-flie-multi>` (input file multiple) → engine FE `fixed-slot`, dò ô THEO CHỮ của dòng
(sectionHeader + slotKeywords) như thủ tục CCHN bảo quản di tích:

  0 : a) Văn bản đề nghị tổ chức biểu diễn nghệ thuật (Mẫu số 02 …)                      — Bản chính 1
  1 : b) Kịch bản, danh mục tác phẩm gắn với tác giả, người chịu trách nhiệm chính về nội
         dung chương trình (tác phẩm nước ngoài kèm bản dịch tiếng Việt có chứng thực)      — Bản chính 1

Mỗi tệp đính NGUYÊN VẸN, không tách. Giấy chứng nhận ĐKDN và giấy tiếp nhận địa điểm không có dòng riêng —
Văn bản đề nghị liệt kê chúng ở mục "Tài liệu kèm theo" nên đính CHUNG dòng a). CCCD chỉ dùng để điền, không
đính. Tệp chưa nhận ra loại → dòng a) kèm cảnh báo.
"""

import asyncio
import re
import time
import unicodedata
from typing import Any

from app.config import settings
from app.process.schemas import FileItem
from app.services.llm import client
from app.services.pdf_utils import trim_files_for_classify

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
# Phân loại chỉ cần vài trang đầu; kịch bản dài hàng chục trang OCR đủ là quá timeout 100s của extension.
_CLASSIFY_MAX_PAGES = 3

_T_VAN_BAN = "van_ban_de_nghi"
_T_KICH_BAN = "kich_ban"
_T_GCN = "gcn_dkdn"
_T_TIEP_NHAN = "giay_tiep_nhan_dia_diem"
_T_CCCD = "cccd"
_T_OTHER = "other"

_SLOT_VAN_BAN, _SLOT_KICH_BAN = 0, 1

_SLOT_NAMES = {
    _SLOT_VAN_BAN: "a) Văn bản đề nghị tổ chức biểu diễn nghệ thuật (Mẫu số 02)",
    _SLOT_KICH_BAN: (
        "b) Kịch bản, danh mục tác phẩm gắn với tác giả, người chịu trách nhiệm chính về nội dung chương trình"
    ),
}

# Engine khoanh các dòng dưới tiêu đề bảng rồi khớp cụm chữ riêng của từng dòng (đã fold dấu).
_BANG_HEADER = "Thành phần hồ sơ"
_SLOT_KEYWORDS = {
    _SLOT_VAN_BAN: ["van ban de nghi"],
    _SLOT_KICH_BAN: ["danh muc tac pham"],
}

_ROUTES: dict[str, int] = {
    _T_VAN_BAN: _SLOT_VAN_BAN,
    _T_KICH_BAN: _SLOT_KICH_BAN,
    _T_GCN: _SLOT_VAN_BAN,
    _T_TIEP_NHAN: _SLOT_VAN_BAN,
}
_DISPLAY = {
    _T_VAN_BAN: "Văn bản đề nghị tổ chức biểu diễn nghệ thuật (Mẫu số 02)",
    _T_KICH_BAN: "Kịch bản, danh mục tác phẩm",
    _T_GCN: "Giấy chứng nhận đăng ký doanh nghiệp",
    _T_TIEP_NHAN: "Giấy tiếp nhận / chấp thuận địa điểm biểu diễn",
}
# Không đính vào bảng: loại → lý do hiện cho cán bộ.
_KHONG_DINH = {
    _T_CCCD: "căn cước chỉ dùng để điền, không thuộc thành phần hồ sơ",
}
_ALLOWED = set(_ROUTES) | set(_KHONG_DINH) | {_T_OTHER}
_SLOT_GIAY_TO_LA = _SLOT_VAN_BAN

# Văn bản đề nghị nêu tài liệu kèm theo (đã fold) → loại giấy tờ phải có trong bộ tệp.
_NEU_KEM_THEO = {
    _T_GCN: (("dang ky kinh doanh", "dang ky doanh nghiep"), "Giấy chứng nhận đăng ký doanh nghiệp/kinh doanh"),
    _T_TIEP_NHAN: (("giay tiep nhan", "chap thuan dia diem"), "giấy tiếp nhận/chấp thuận địa điểm"),
}


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _canon(value: Any) -> str:
    return re.sub(r"[_\-\s]+", "_", _fold(value)).strip("_")


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
    files: list[dict], llm_types: dict[int, str] | None = None, texts: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    """`llm_types[index]` = docType; `texts[index]` = OCR (vài trang đầu) để soát nội dung văn bản / kịch bản."""
    llm_types = llm_types or {}
    texts = texts or {}
    attachments: list[dict] = []
    classified: list[dict] = []
    la: list[str] = []
    kem_theo: list[str] = []
    khong_dinh: list[str] = []
    by_type: dict[str, list[int]] = {}

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        doc_type = llm_types.get(index, _T_OTHER)
        if doc_type not in _ALLOWED:
            doc_type = _T_OTHER
        source = "llm" if index in llm_types else "default"
        by_type.setdefault(doc_type, []).append(index)

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
        elif doc_type in (_T_GCN, _T_TIEP_NHAN):
            kem_theo.append(file_name)
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": _DISPLAY.get(doc_type, file_name),
            "componentName": _SLOT_NAMES[slot],
            "loaiBan": "Bản chính",
            "target": "fixed-slot",
            "needsAddComponent": False,
            # slotKey theo DÒNG: các tệp cùng dòng phải chung key để engine gom vào một lần gán input.
            "slotKey": f"bieu_dien_nt_row_{slot}",
            "slotIndex": slot,
            "slotName": _SLOT_NAMES[slot],
            "sectionHeader": _BANG_HEADER,
            "slotKeywords": _SLOT_KEYWORDS[slot],
            "detectedType": doc_type,
        })
        classified.append({"fileName": file_name, "docType": doc_type, "source": source, "slotIndex": slot})

    warnings: list[str] = []
    if khong_dinh:
        warnings.append("Không đính vào bảng thành phần hồ sơ: " + "; ".join(khong_dinh) + ".")
    if kem_theo:
        warnings.append(
            "Bảng thành phần hồ sơ không có dòng riêng cho " + ", ".join(kem_theo) + " — đã đính chung dòng a) "
            "cùng Văn bản đề nghị (tài liệu kèm theo của văn bản)."
        )
    if la:
        warnings.append(
            f"Chưa nhận ra loại giấy tờ, đã đưa vào dòng a) Văn bản đề nghị: {', '.join(la)} — cán bộ đối chiếu lại, "
            "bỏ tệp nếu nơi tiếp nhận không yêu cầu."
        )
    if not by_type.get(_T_VAN_BAN):
        warnings.append("Chưa thấy VĂN BẢN ĐỀ NGHỊ (Mẫu số 02) — thành phần bắt buộc a), cán bộ bổ sung trước khi nộp.")
    kich_ban = by_type.get(_T_KICH_BAN) or []
    if not kich_ban:
        warnings.append("Chưa thấy KỊCH BẢN, danh mục tác phẩm — thành phần bắt buộc b), cán bộ bổ sung trước khi nộp.")
    elif all(i in texts for i in kich_ban) and not any(
        "tac gia" in _fold(texts[i]) or "chiu trach nhiem" in _fold(texts[i]) for i in kich_ban
    ):
        warnings.append(
            "Kịch bản chưa thấy ghi tác giả và người chịu trách nhiệm chính về nội dung như thành phần b) yêu cầu — "
            "cán bộ kiểm tra, Sở có thể yêu cầu bổ sung."
        )
    van_ban_text = " ".join(_fold(texts.get(i, "")) for i in by_type.get(_T_VAN_BAN) or [])
    for doc_type, (cum, ten) in _NEU_KEM_THEO.items():
        if any(c in van_ban_text for c in cum) and not by_type.get(doc_type):
            warnings.append(f"Văn bản đề nghị nêu tài liệu kèm theo {ten} nhưng bộ tệp chưa có — cán bộ bổ sung.")
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_pairs = [(index, file) for index, file in enumerate(raw_files) if file.get("type") in _OCR_TYPES]
    errors: list[str] = []

    from app.services import ocr

    started = time.monotonic()
    ocr_input = trim_files_for_classify([file for _, file in ocr_pairs], _CLASSIFY_MAX_PAGES)
    ocr_results = await ocr.ocr_per_file(ocr_input) if ocr_pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)

    # Kết quả OCR khớp THỨ TỰ đầu vào, không map theo tên (hai tệp có thể trùng tên).
    texts: dict[int, str] = {}
    llm_documents: list[dict[str, Any]] = []
    for (index, _file), result in zip(ocr_pairs, ocr_results):
        text = str(result.get("text") or "")
        if result.get("error"):
            errors.append(f"OCR {result.get('name')}: {result['error']}")
        if text.strip():
            texts[index] = text
            llm_documents.append({"index": index, "text": text})

    started = time.monotonic()
    llm_types = await _classify_with_llm(llm_documents, errors) if llm_documents else {}
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, llm_types, texts)
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
