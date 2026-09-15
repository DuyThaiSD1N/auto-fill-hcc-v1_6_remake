"""Lập kế hoạch đính kèm "Đăng ký tài sản gắn liền với đất - nghĩa vụ tài chính - Miền núi, hải đảo" (QN).

⚠ Form KHÔNG có dòng thành phần hồ sơ sẵn → MỌI file đều target "new" (needsAddComponent) qua nút
"Thêm thành phần hồ sơ". Phân loại LLM-first (KHÔNG rule) chỉ để đặt TÊN thành phần cho đúng; loại không
nhận ra → đặt tên theo file. Engine FE wallet-modal (React/Radix).
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

# docType (LLM) → TÊN thành phần hồ sơ (dùng đặt tên khi thêm thành phần mới).
_DISPLAY: dict[str, str] = {
    "don_dang_ky": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất",
    "gcn_da_cap": "Bản gốc Giấy chứng nhận đã cấp",
    "giay_phep_xay_dung": "Giấy phép xây dựng",
    "ho_so_thiet_ke": "Hồ sơ thiết kế xây dựng nhà ở, công trình",
    "so_do_do_dac": "Sơ đồ, phiếu đo đạc tài sản gắn liền với đất",
    "giay_to_so_huu": "Giấy tờ chứng minh quyền sở hữu tài sản gắn liền với đất",
    "to_khai_01_lptb": "Tờ khai lệ phí trước bạ Mẫu số 01/LPTB",
    "to_khai_04_sddpnn": "Tờ khai thuế sử dụng đất phi nông nghiệp Mẫu số 04/TK-SDDPNN",
    "to_khai_03_bds_tncn": "Tờ khai thuế thu nhập cá nhân Mẫu số 03/BĐS-TNCN",
}
_ALLOWED = set(_DISPLAY) | {_OTHER}


def _derive_component_name(file_name: str) -> str:
    """Tên thành phần cho giấy tờ LLM không nhận ra — theo tên file (bỏ đuôi, gạch dưới→cách)."""
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", str(file_name or "")).strip()
    stem = re.sub(r"[_]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem or "Tài liệu kèm theo"


def _normalize(value: str) -> str:
    """Chuẩn hóa chuỗi docType LLM trả về → mã canonical (chuẩn hóa OUTPUT của LLM, không phải rule)."""
    f = _fold(value)
    if "01/lptb" in f or "le phi truoc ba" in f:
        return "to_khai_01_lptb"
    if "04/tk-sddpnn" in f or "phi nong nghiep" in f:
        return "to_khai_04_sddpnn"
    if "03/bds-tncn" in f or "thu nhap ca nhan" in f:
        return "to_khai_03_bds_tncn"
    if "giay phep xay dung" in f:
        return "giay_phep_xay_dung"
    if "thiet ke" in f:
        return "ho_so_thiet_ke"
    if "so do" in f or "do dac" in f or "ban ve hien trang" in f:
        return "so_do_do_dac"
    if "don" in f and ("dang ky" in f or "bien dong" in f):
        return "don_dang_ky"
    if "so huu" in f:
        return "giay_to_so_huu"
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
        # LLM-PRIMARY: LLM đặt tên loại; KHÔNG có dòng sẵn → LUÔN thêm thành phần MỚI.
        doc_type = llm_types.get(index, "")
        name = _DISPLAY.get(doc_type) or _derive_component_name(file_name)
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": _wallet_label(name),
            "loaiBan": _LOAI_BAN,
            "detectedType": doc_type if doc_type in _DISPLAY else _OTHER,
            "componentName": name,
            "target": "new",
            "needsAddComponent": True,
        })
        classified.append({
            "fileName": file_name,
            "docType": doc_type if doc_type in _DISPLAY else _OTHER,
            "source": "llm",
            "target": "new",
        })

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
