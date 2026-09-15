"""Lập kế hoạch đính kèm "Tách thửa đất, hợp thửa đất - Tách thửa cùng tên - Miền núi, hải đảo" (Quảng Ninh).

Cùng nền tảng (React/Radix, modal "Danh sách tài liệu điện tử" → engine wallet-modal, target "existing")
với các thủ tục đất đai Quảng Ninh khác. 7 dòng thành phần hồ sơ.

⚠ PHÂN LOẠI LLM-FIRST (KHÔNG dùng rule keyword — xem feedback): LLM đọc OCR quyết định loại; thiếu/không
nhận ra → thêm THÀNH PHẦN HỒ SƠ MỚI (không bỏ qua). componentName = đoạn text đặc trưng của dòng.
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

# 7 dòng thành phần hồ sơ (thứ tự DOM, componentIndex 1-based). componentName = đoạn tiêu đề đặc trưng.
_ROWS: dict[str, dict[str, Any]] = {
    "to_khai_01_lptb": {
        "index": 1, "name": "Tờ khai lệ phí trước bạ theo Mẫu số 01/LPTB",
        "display": "Tờ khai lệ phí trước bạ Mẫu số 01/LPTB",
    },
    "to_khai_04_sddpnn": {
        "index": 2, "name": "Tờ khai thuế sử dụng đất phi nông nghiệp theo Mẫu số 04/TK-SDDPNN",
        "display": "Tờ khai thuế sử dụng đất phi nông nghiệp Mẫu số 04/TK-SDDPNN",
    },
    "to_khai_03_bds_tncn": {
        "index": 3, "name": "Tờ khai thuế thu nhập cá nhân theo Mẫu số 03/BĐS-TNCN",
        "display": "Tờ khai thuế thu nhập cá nhân Mẫu số 03/BĐS-TNCN",
    },
    "gcn_da_cap": {
        "index": 4, "name": "Giấy chứng nhận đã cấp",
        "display": "Bản gốc Giấy chứng nhận quyền sử dụng đất đã cấp",
    },
    "don_mau_26": {
        "index": 5, "name": "Đơn đề nghị tách thửa đất, hợp thửa đất theo Mẫu số 26",
        "display": "Đơn đề nghị tách thửa đất, hợp thửa đất Mẫu số 26",
    },
    "ban_ve_mau_27": {
        "index": 6, "name": "Bản vẽ tách thửa đất, hợp thửa đất lập theo Mẫu số 27",
        "display": "Bản vẽ tách thửa đất, hợp thửa đất Mẫu số 27",
    },
    "van_ban_co_quan": {
        "index": 7, "name": "Các văn bản của cơ quan có thẩm quyền có thể hiện nội dung tách thửa",
        "display": "Văn bản của cơ quan có thẩm quyền về tách/hợp thửa",
    },
}
_ALLOWED = set(_ROWS) | {_OTHER}


def _derive_component_name(file_name: str) -> str:
    """Tên thành phần hồ sơ MỚI cho giấy tờ ngoài danh mục — theo tên file (bỏ đuôi, gạch dưới→cách)."""
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", str(file_name or "")).strip()
    stem = re.sub(r"[_]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem or "Tài liệu khác kèm theo"


def _normalize(value: str) -> str:
    """Chuẩn hóa chuỗi docType do LLM trả về → mã canonical (KHÔNG phải rule trên document)."""
    f = _fold(value)
    if "01/lptb" in f or "01 lptb" in f or ("le phi truoc ba" in f):
        return "to_khai_01_lptb"
    if "04/tk-sddpnn" in f or "04 tk sddpnn" in f or "phi nong nghiep" in f:
        return "to_khai_04_sddpnn"
    if "03/bds-tncn" in f or "03 bds tncn" in f or "thu nhap ca nhan" in f:
        return "to_khai_03_bds_tncn"
    if "ban ve" in f and ("27" in f or "tach" in f or "hop thua" in f):
        return "ban_ve_mau_27"
    if "don" in f and ("26" in f or "tach thua" in f or "hop thua" in f):
        return "don_mau_26"
    if "van ban" in f and "co quan" in f:
        return "van_ban_co_quan"
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
        # Quảng Ninh (React/Radix) đính qua modal "Danh sách tài liệu điện tử" → engine wallet-modal.
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
        # LLM-PRIMARY: hoàn toàn theo LLM (không rule keyword). Không thuộc 7 dòng → thành phần MỚI.
        doc_type = llm_types.get(index, "")
        if doc_type in _ROWS:
            attachments.append(_build_item(file, index, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "source": "llm", "target": "existing"})
        else:
            # Ngoài danh mục → THÊM thành phần hồ sơ MỚI (không bỏ qua), tên theo file.
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
