"""Lập kế hoạch đính kèm "Đăng ký biến động - đổi tên/thay đổi thông tin người SDĐ - Miền núi, hải đảo" (QN).

Cùng nền tảng (React/Radix, modal "Danh sách tài liệu điện tử" → engine wallet-modal, target "existing")
với các thủ tục đất đai Quảng Ninh khác. 7 dòng thành phần hồ sơ có sẵn.

⚠ PHÂN LOẠI LLM-FIRST (KHÔNG rule keyword). Giấy tờ ngoài danh mục → thêm THÀNH PHẦN HỒ SƠ MỚI.
⚠ Hàng 4 và 5 TRÙNG "Đơn đăng ký biến động … Mẫu số 18" → don_mau_18 route hàng 4 (componentIndex).
"""

import asyncio
import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import sanitize_wallet_document_label as _wallet_label
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_LOAI_BAN = "Bản chính"
_OTHER = "other"

# 7 dòng (componentIndex 1-based). componentName = đoạn tiêu đề đặc trưng của dòng.
_ROWS: dict[str, dict[str, Any]] = {
    "gcn_da_cap": {
        "index": 1, "name": "Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất đã cấp",
        "display": "Giấy chứng nhận quyền sử dụng đất đã cấp",
    },
    "manh_trich_do": {
        "index": 2, "name": "Mảnh trích đo bản đồ địa chính thửa đất",
        "display": "Mảnh trích đo bản đồ địa chính thửa đất",
    },
    "van_ban_dai_dien": {
        "index": 3, "name": "Văn bản về việc đại diện theo quy định của pháp luật về dân sự",
        "display": "Văn bản đại diện theo pháp luật về dân sự",
    },
    "don_mau_18": {
        # Hàng 4 & 5 cùng nội dung; route hàng 4.
        "index": 4, "name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18",
        "display": "Đơn đăng ký biến động đất đai Mẫu số 18",
    },
    "giay_to_doi_ten": {
        "index": 6, "name": "giấy tờ chứng minh về việc đổi tên, thay đổi thông tin của người sử dụng đất",
        "display": "Giấy tờ chứng minh việc đổi tên, thay đổi thông tin",
    },
    "van_ban_cho_phep_doi_ten": {
        "index": 7, "name": "Văn bản của cơ quan có thẩm quyền cho phép hoặc công nhận việc đổi tên",
        "display": "Văn bản cơ quan có thẩm quyền cho phép/công nhận đổi tên",
    },
}
_ALLOWED = set(_ROWS) | {_OTHER}


def _derive_component_name(file_name: str) -> str:
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", str(file_name or "")).strip()
    stem = re.sub(r"[_]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem or "Tài liệu khác kèm theo"


def _normalize(value: str) -> str:
    """Chuẩn hóa chuỗi docType LLM trả về → mã canonical (không phải rule trên document)."""
    f = _fold(value)
    if "manh trich do" in f or ("trich do" in f and "dia chinh" in f):
        return "manh_trich_do"
    if "dai dien" in f or "uy quyen" in f:
        return "van_ban_dai_dien"
    if "don" in f and ("18" in f or "bien dong" in f):
        return "don_mau_18"
    if ("doi ten" in f or "thay doi thong tin" in f) and ("cho phep" in f or "cong nhan" in f or "co quan" in f):
        return "van_ban_cho_phep_doi_ten"
    if "doi ten" in f or "thay doi thong tin" in f:
        return "giay_to_doi_ten"
    if "giay chung nhan" in f or "gcn" in f:
        return "gcn_da_cap"
    return value if value in _ALLOWED else _OTHER


async def _classify_one(document: dict[str, Any]) -> tuple[int, str]:
    index = int(document.get("index"))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt([{"index": index, "text": str(document.get("text") or "")[:12000]}])},
    ]
    raw = await client.chat(messages, max_tokens=120, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    first = next(iter(parsed.get("documents", []) or []), {})
    return index, _normalize(str(first.get("docType") or first.get("type") or ""))


async def _classify_with_llm(documents: list[dict[str, Any]], errors: list[str] | None = None) -> dict[int, str]:
    if not documents:
        return {}
    outcomes = await asyncio.gather(*(_classify_one(d) for d in documents), return_exceptions=True)
    result: dict[int, str] = {}
    for document, outcome in zip(documents, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            if errors is not None:
                errors.append(f"attachment_agent file {document.get('index')}: {outcome}")
            continue
        result[outcome[0]] = outcome[1]
    return result


def _build_item(file: dict, file_index: int, doc_type: str) -> dict:
    row = _ROWS[doc_type]
    return {
        "fileIndex": file_index,
        "fileName": str(file.get("name") or f"file-{file_index + 1}"),
        "documentName": _wallet_label(row["display"]),
        "loaiBan": _LOAI_BAN,
        "detectedType": doc_type,
        "componentName": row["name"],
        "componentIndex": row["index"],
        "target": "existing",
        "needsAddComponent": False,
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    _ = ocr_results
    llm_types = llm_types or {}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        doc_type = llm_types.get(index, "")
        if doc_type in _ROWS:
            attachments.append(_build_item(file, index, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "source": "llm", "target": "existing"})
        else:
            # Ngoài 7 dòng → THÊM thành phần hồ sơ MỚI, tên theo file.
            new_name = _derive_component_name(file_name)
            attachments.append({
                "fileIndex": index,
                "fileName": file_name,
                "documentName": _wallet_label(new_name),
                "loaiBan": _LOAI_BAN,
                "detectedType": _OTHER,
                "componentName": new_name,
                "target": "new",
                "needsAddComponent": True,
            })
            classified.append({"fileName": file_name, "docType": _OTHER, "source": "llm", "target": "new"})

    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options
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
    llm_docs = [
        {"index": index, "text": str(by_name.get(f.get("name"), {}).get("text") or "")}
        for index, f in enumerate(raw_files)
        if str(by_name.get(f.get("name"), {}).get("text") or "").strip()
    ]
    started = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs, errors)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [item.get("name") for item in ocr_results if item.get("text")],
            "llmDocuments": [raw_files[d["index"]]["name"] for d in llm_docs],
            "classified": classified,
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
