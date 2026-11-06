"""Đính kèm bước "Thành phần hồ sơ" cho "Hòa giải tranh chấp đất đai" (1.012812) — bảng attp-row 2 dòng.

Bảng theo ảnh ánh xạ đính kèm (mat-checkbox + radio "1 Bản chính/1 Bản sao" + "Chọn tệp tin"):
  STT1: Các giấy tờ có liên quan đến việc sử dụng đất (bản phô tô hoặc có công chức hoặc có chứng thực).
        -> mọi giấy tờ đất đai (hợp đồng ủy quyền, giấy chuyển nhượng, thông báo thuế, sổ hộ khẩu, bản mô tả ranh
           giới, phiếu đo đạc, mảnh trích đo, bản vẽ...), 1 Bản sao.
  STT2: Đơn yêu cầu yêu cầu hòa giải tranh chấp đất đai (bản chính).   (cổng lặp chữ "yêu cầu")
        -> Đơn yêu cầu hòa giải, 1 Bản chính.
MỖI FILE ĐÍNH NGUYÊN KHỐI, KHÔNG TÁCH TRANG (ánh xạ: PDF gộp 26 trang giấy tờ vào nguyên dòng 1). File gộp cả Đơn lẫn
giấy tờ khác → dòng Đơn nhận nguyên file, cảnh báo cán bộ. componentIndex đếm từ 1 (FE thử rows[componentIndex - 1]
rồi mới dò tên); componentName là đoạn chữ đặc trưng của dòng, chịu được cả khi cổng sửa lỗi lặp chữ.
Phân loại LLM-first theo chữ OCR (cache bước điền, chưa có thì vài trang đầu); LLM lỗi/không trả thì luật dự phòng
theo tiêu đề đầu file.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.attach.planner import _LLM_TEXT_MAX_CHARS, _ocr_for_classify
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON = "don_yeu_cau_hoa_giai"
_GIAY_TO = "giay_to_su_dung_dat"
_OTHER = "other"
_ALLOWED = (_DON, _GIAY_TO, _OTHER)

_ROWS: dict[str, dict[str, Any]] = {
    _GIAY_TO: {
        "componentIndex": 1,
        "componentName": "Các giấy tờ có liên quan đến việc sử dụng đất",
        "loaiBan": "Bản sao",
        "documentName": "Giấy tờ liên quan đến việc sử dụng đất",
    },
    _DON: {
        "componentIndex": 2,
        "componentName": "hòa giải tranh chấp đất đai",
        "loaiBan": "Bản chính",
        "documentName": "Đơn yêu cầu hòa giải tranh chấp đất đai",
    },
}

# FE coi tệp là "đã đính" khi 24 ký tự chữ-số đầu của tên trùng tệp đang có trên dòng → mỗi tệp một tên khác.
_FINGERPRINT_CHARS = 24


def _fingerprint(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", re.sub(r"\.[a-z0-9]{2,5}$", "", _fold(name)))[:_FINGERPRINT_CHARS]


def _stem(file_name: str) -> str:
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", str(file_name or "")).replace("_", " ")
    return " ".join(stem.split()) or "Giấy tờ"


def _normalize_type(value: Any) -> str:
    folded = re.sub(r"[\s-]+", "_", _fold(str(value or "")))
    if folded in _ALLOWED:
        return folded
    if "hoa_giai" in folded or folded.startswith("don"):
        return _DON
    if "giay_to" in folded or "dat" in folded.split("_"):
        return _GIAY_TO
    return _OTHER


def _doc_types(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        raw = [raw]
    out: list[str] = []
    for value in raw:
        doc_type = _normalize_type(value)
        if doc_type not in out:
            out.append(doc_type)
    return out


def _rule_types(text: str) -> list[str]:
    """Dự phòng khi LLM không trả: lá đơn có tiêu đề "ĐƠN …" + "tranh chấp" + "Kính gửi" ngay đầu file."""
    folded = _fold(text)
    if not folded.strip():
        return []
    head = folded[:1500]
    if re.search(r"\bdon\b", head) and "tranh chap" in head and "kinh gui" in head:
        return [_DON]
    return [_GIAY_TO]


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, Any] | None = None,
    ocr_texts: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    """Thuần tất định: loại giấy từng file → (attachments, warnings, classified)."""
    llm_types = llm_types or {}
    ocr_texts = ocr_texts or {}
    warnings: list[str] = []
    classified: list[dict] = []
    routed: list[tuple[int, str, str]] = []  # (fileIndex, fileName, dòng)

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        raw = llm_types.get(index)
        doc_types = [t for t in _doc_types(raw) if t != _OTHER] if raw else []
        source = "llm"
        if not doc_types:
            doc_types = _rule_types(ocr_texts.get(index) or "")
            source = "rule" if doc_types else "unknown"
        if _DON in doc_types:
            row = _DON
            if _GIAY_TO in doc_types:
                warnings.append(
                    f"'{file_name}' gộp Đơn yêu cầu hòa giải với giấy tờ sử dụng đất — đã đính nguyên file một lần vào "
                    "dòng 2 (Đơn); dòng 1 (giấy tờ liên quan đến việc sử dụng đất) cần tệp giấy tờ riêng."
                )
        else:
            row = _GIAY_TO
            if not doc_types:
                warnings.append(
                    f"Chưa nhận diện chắc loại giấy tờ của '{file_name}' — tạm đính vào dòng 1 (giấy tờ liên quan đến "
                    "việc sử dụng đất); cán bộ kiểm tra lại."
                )
        routed.append((index, file_name, row))
        classified.append({"fileName": file_name, "docTypes": doc_types, "source": source,
                           "componentIndex": _ROWS[row]["componentIndex"]})

    if not any(row == _DON for _, _, row in routed):
        warnings.append("Chưa có Đơn yêu cầu hòa giải tranh chấp đất đai (dòng 2, bản chính) — cần bổ sung.")

    per_row = {row: sum(1 for _, _, r in routed if r == row) for row in _ROWS}
    used: set[str] = set()
    attachments: list[dict] = []
    for index, file_name, row in routed:
        spec = _ROWS[row]
        # Một tệp trên dòng: tên chuẩn của dòng. Nhiều tệp: giữ tên file gốc để cán bộ phân biệt.
        document_name = spec["documentName"] if per_row[row] == 1 else _stem(file_name)
        base, n = document_name, 2
        while _fingerprint(document_name) in used:
            document_name, n = f"{n}. {base}", n + 1
        used.add(_fingerprint(document_name))
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": document_name,
            "componentName": spec["componentName"],
            "componentIndex": spec["componentIndex"],
            "loaiBan": spec["loaiBan"],
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": row,
        })
    return attachments, warnings, classified


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, list[str]]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=600, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    result: dict[int, list[str]] = {}
    for item in parsed.get("documents", []) or []:
        try:
            types = item.get("docTypes")
            result[int(item.get("index"))] = types if types is not None else item.get("docType") or item.get("type")
        except (TypeError, ValueError, AttributeError):
            continue
    return result


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    ocr_pairs = [(index, item) for index, item in enumerate(raw_files) if item.get("type") in _OCR_TYPES]
    errors: list[str] = []

    started = time.monotonic()
    ocr_results = await _ocr_for_classify([item for _, item in ocr_pairs]) if ocr_pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    ocr_texts: dict[int, str] = {}
    for (index, _item), result in zip(ocr_pairs, ocr_results):
        if result.get("error"):
            errors.append(f"OCR {result.get('name')}: {result['error']}")
        ocr_texts[index] = str(result.get("text") or "")

    llm_documents = [
        {"index": index, "text": text[:_LLM_TEXT_MAX_CHARS]} for index, text in ocr_texts.items() if text.strip()
    ]
    started = time.monotonic()
    llm_types: dict[int, list[str]] = {}
    if llm_documents:
        try:
            llm_types = await _classify_with_llm(llm_documents)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, llm_types, ocr_texts)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [item["name"] for item in raw_files],
            "ocrDocuments": [raw_files[index]["name"] for index, text in ocr_texts.items() if text.strip()],
            "llmDocuments": [raw_files[item["index"]]["name"] for item in llm_documents],
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
