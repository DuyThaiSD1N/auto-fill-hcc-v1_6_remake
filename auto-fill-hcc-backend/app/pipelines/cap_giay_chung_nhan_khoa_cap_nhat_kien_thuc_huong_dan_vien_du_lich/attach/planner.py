"""Đính kèm [Bộ VHTTDL] Thủ tục cấp GCN khóa cập nhật kiến thức cho hướng dẫn viên du lịch (1.004605, QT-123).

Cổng `dichvucong.bvhttdl.gov.vn` — form và bảng thành phần hồ sơ CHUNG trang `/nop-ho-so`. Bảng chỉ có MỘT dòng, một
`<app-upload-flie-multi>` (input file multiple) → engine FE `fixed-slot`, dò ô THEO CHỮ của dòng (sectionHeader +
slotKeywords) như các thủ tục liz khác:

  0 : (1) Đăng ký tham dự khóa cập nhật kiến thức cho hướng dẫn viên du lịch (Mẫu số 06 Phụ lục II ban hành kèm
          theo Thông tư 04/2024/TT-BVHTTDL)                                       — Bản chính 1, Bản sao 0

Đơn đính NGUYÊN FILE, không tách trang. CCCD và thẻ HDV chỉ dùng để điền, không thuộc thành phần hồ sơ → không đính.
Tệp chưa nhận ra loại → vẫn vào dòng (1) (trang không có ô giấy tờ khác) kèm cảnh báo.
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
# Phân loại chỉ cần trang đầu; bản scan nhiều trang OCR đủ là dễ quá timeout 100s của extension.
_CLASSIFY_MAX_PAGES = 2

_T_DON = "don_dang_ky"
_T_CCCD = "cccd"
_T_THE = "the_hdv"
_T_OTHER = "other"

_SLOT_DON = 0
_SLOT_NAME = (
    "(1) Đăng ký tham dự khóa cập nhật kiến thức cho hướng dẫn viên du lịch (Mẫu số 06 Phụ lục II Thông tư "
    "04/2024/TT-BVHTTDL)"
)
_DISPLAY_DON = "Đăng ký tham dự khóa cập nhật kiến thức cho hướng dẫn viên du lịch (Mẫu số 06)"

# Engine khoanh các dòng dưới tiêu đề bảng rồi khớp cụm chữ riêng của dòng (đã fold dấu).
_BANG_HEADER = "Thành phần hồ sơ"
_SLOT_KEYWORDS = ["khoa cap nhat kien thuc", "mau so 06"]
_SLOT_KEY = "khoa_cap_nhat_hdv_row_0"

# Không đính vào bảng: loại → lý do hiện cho cán bộ.
_KHONG_DINH = {
    _T_CCCD: "căn cước chỉ dùng để điền, không thuộc thành phần hồ sơ",
    _T_THE: "thẻ hướng dẫn viên chỉ dùng để điền, không thuộc thành phần hồ sơ",
}
_ALLOWED = {_T_DON, _T_OTHER, *_KHONG_DINH}

# Đơn còn dòng chú thích của bản mẫu → chưa phải bản đã sửa, đã ký.
_BAN_MAU_RE = re.compile(r"ban mau tham khao|thong tin dien mau")


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
    """`llm_types[index]` = docType; `texts[index]` = OCR (chỉ để nhận dòng chú thích bản mẫu trên đơn)."""
    llm_types = llm_types or {}
    texts = texts or {}
    attachments: list[dict] = []
    classified: list[dict] = []
    la: list[str] = []
    khong_dinh: list[str] = []
    ban_mau: list[str] = []
    so_don = 0

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        doc_type = llm_types.get(index, _T_OTHER)
        if doc_type not in _ALLOWED:
            doc_type = _T_OTHER
        source = "llm" if index in llm_types else "default"

        if doc_type in _KHONG_DINH:
            khong_dinh.append(f"{file_name} ({_KHONG_DINH[doc_type]})")
            classified.append({
                "fileName": file_name, "docType": doc_type, "source": source,
                "target": "skip", "reason": _KHONG_DINH[doc_type],
            })
            continue

        if doc_type == _T_DON:
            so_don += 1
            if _BAN_MAU_RE.search(_fold(texts.get(index))):
                ban_mau.append(file_name)
        else:
            la.append(file_name)
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": _DISPLAY_DON if doc_type == _T_DON else file_name,
            "componentName": _SLOT_NAME,
            "loaiBan": "Bản chính",
            "target": "fixed-slot",
            "needsAddComponent": False,
            # Mọi tệp chung một dòng → chung slotKey để engine gom vào một lần gán input `multiple`.
            "slotKey": _SLOT_KEY,
            "slotIndex": _SLOT_DON,
            "slotName": _SLOT_NAME,
            "sectionHeader": _BANG_HEADER,
            "slotKeywords": _SLOT_KEYWORDS,
            "detectedType": doc_type,
        })
        classified.append({"fileName": file_name, "docType": doc_type, "source": source, "slotIndex": _SLOT_DON})

    warnings: list[str] = []
    if khong_dinh:
        warnings.append("Không đính vào bảng thành phần hồ sơ: " + "; ".join(khong_dinh) + ".")
    if la:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã đưa vào dòng (1) Đăng ký tham dự khóa (trang chỉ có một dòng thành phần): "
            f"{', '.join(la)} — cán bộ đối chiếu lại, bỏ tệp nếu nơi tiếp nhận không yêu cầu."
        )
    if not so_don:
        warnings.append(
            "Chưa thấy ĐƠN ĐĂNG KÝ tham dự khóa cập nhật kiến thức (Mẫu số 06) — thành phần bắt buộc, cán bộ bổ sung "
            "trước khi nộp."
        )
    elif so_don > 1:
        warnings.append(
            f"Có {so_don} tệp Đơn đăng ký (Mẫu số 06) cùng vào dòng (1) — thành phần chỉ cần 01 bản chính, cán bộ bỏ "
            "bản thừa."
        )
    if ban_mau:
        warnings.append(
            f"Đơn {', '.join(ban_mau)} còn dòng \"BẢN MẪU THAM KHẢO – THÔNG TIN ĐIỀN MẪU\" — đây là bản mẫu, cán bộ "
            "thay bằng đơn đã sửa thông tin thật và đã ký trước khi nộp."
        )
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
