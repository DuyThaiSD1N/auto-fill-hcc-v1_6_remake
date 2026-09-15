"""Lập kế hoạch đính kèm hồ sơ XÓA đăng ký biện pháp bảo đảm bằng QSDĐ, tài sản gắn liền với đất (Quảng Ninh).

Cùng nền tảng (React/Radix, modal "Danh sách tài liệu điện tử" → engine wallet-modal, target "existing")
với các thủ tục đất đai Quảng Ninh khác. Form có 6 hàng thành phần hồ sơ SẴN (thứ tự DOM); mapping thực tế:
  hàng 1 = Giấy chứng nhận (bản gốc); hàng 2 = Phiếu yêu cầu Mẫu 02a; hàng 4 = Văn bản chuyển giao quyền
  đòi nợ; hàng 5 = Văn bản khác chứng minh căn cứ (= công văn ngân hàng đồng ý xóa); hàng 6 = Văn bản sửa
  đổi HĐ bảo đảm. Hàng 3 là điều kiện (không phải giấy tờ) → không route.

Phân loại LLM-FIRST (không rule keyword — theo feedback: giòn, dễ nhận nhầm). File gộp (phiếu + công văn
trong 1 PDF) → phân theo tài liệu CHÍNH (phiếu, trang đầu) → hàng 2; công văn ngân hàng RIÊNG → hàng 5.
componentName là khóa chính (FE khớp substring sau khi fold dấu); componentIndex (1-based) chỉ là gợi ý.
"""

import asyncio
import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import sanitize_wallet_document_label as _wallet_label
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_LOAI_BAN = "Bản chính"
_AUTHORIZATION = "van_ban_dai_dien"

# 6 hàng thành phần hồ sơ trong HTML (thứ tự DOM). componentName = đoạn tiêu đề đặc trưng để FE khớp.
_ROUTES: dict[str, dict[str, Any]] = {
    "gcn": {
        "index": 1,
        "name": "Giấy chứng nhận (bản gốc) trong trường hợp tài sản bảo đảm",
    },
    "phieu_yeu_cau_02a": {
        "index": 2,
        "name": "Phiếu yêu cầu theo Mẫu số 02a",
    },
    "van_ban_chuyen_giao": {
        "index": 4,
        "name": "Văn bản chuyển giao quyền đòi nợ, chuyển giao nghĩa vụ",
    },
    "cong_van_dong_y_xoa": {
        "index": 5,
        "name": "Văn bản khác chứng minh có căn cứ đăng ký thay đổi",
    },
    "van_ban_sua_doi_hd": {
        "index": 6,
        "name": "Văn bản sửa đổi, bổ sung hợp đồng bảo đảm",
    },
}
_ALLOWED = set(_ROUTES) | {_AUTHORIZATION, "other"}

_DISPLAY = {
    "gcn": "Giấy chứng nhận quyền sử dụng đất (bản gốc)",
    "phieu_yeu_cau_02a": "Phiếu yêu cầu xóa đăng ký biện pháp bảo đảm (Mẫu số 02a)",
    "van_ban_chuyen_giao": "Văn bản chuyển giao quyền đòi nợ, chuyển giao nghĩa vụ",
    "cong_van_dong_y_xoa": "Văn bản đồng ý xóa đăng ký thế chấp của bên nhận bảo đảm",
    "van_ban_sua_doi_hd": "Văn bản sửa đổi, bổ sung hợp đồng bảo đảm",
    _AUTHORIZATION: "Văn bản đại diện hoặc ủy quyền",
}


def _fold(value: Any) -> str:
    import unicodedata

    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _derive_component_name(file_name: str) -> str:
    """Tên thành phần hồ sơ MỚI cho giấy tờ ngoài danh mục — lấy theo tên file (bỏ đuôi, gạch dưới→cách)."""
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", str(file_name or "")).strip()
    stem = re.sub(r"[_]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem or "Tài liệu khác kèm theo"


def _canon_type(value: Any) -> str:
    """Chuẩn hóa mọi separator (khoảng trắng/gạch dưới/gạch ngang) → '_' để khớp bất kể LLM trả kiểu nào."""
    return re.sub(r"[_\-\s]+", "_", _fold(value)).strip("_")


def _normalize_doc_type(value: Any) -> str:
    canon = _canon_type(value)
    for doc_type in _ALLOWED:
        if canon == _canon_type(doc_type):
            return doc_type
    return "other"


def _llm_document(document: dict[str, Any]) -> dict[str, Any]:
    text = str(document.get("text") or "")
    return {"index": document.get("index"), "text": text[:12000]}


async def _classify_one_with_llm(document: dict[str, Any]) -> tuple[int, str]:
    index = int(document.get("index"))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt([_llm_document(document)])},
    ]
    raw = await client.chat(messages, max_tokens=120, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    first = next(iter(parsed.get("documents", []) or []), {})
    return index, _normalize_doc_type(first.get("docType") or first.get("type"))


async def _classify_with_llm(
    documents: list[dict[str, Any]],
    errors: list[str] | None = None,
) -> dict[int, str]:
    if not documents:
        return {}

    # Một prompt/call cho mỗi file: PDF dài hoặc một lỗi provider chỉ làm file đó fallback other.
    outcomes = await asyncio.gather(
        *(_classify_one_with_llm(document) for document in documents),
        return_exceptions=True,
    )
    result: dict[int, str] = {}
    for document, outcome in zip(documents, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            if errors is not None:
                errors.append(f"attachment_agent file {document.get('index')}: {outcome}")
            continue
        index, doc_type = outcome
        result[index] = doc_type
    return result


def _build_item(file: dict, file_index: int, doc_type: str) -> dict:
    base = {
        "fileIndex": file_index,
        "fileName": str(file.get("name") or f"file-{file_index + 1}"),
        "documentName": _wallet_label(_DISPLAY[doc_type]),
        "loaiBan": _LOAI_BAN,
        "detectedType": doc_type,
    }
    # Văn bản ủy quyền không có hàng sẵn trong danh mục → tạo thành phần bổ sung ("Thêm thành phần hồ sơ").
    if doc_type == _AUTHORIZATION:
        return {
            **base,
            "componentName": _DISPLAY[doc_type],
            "target": "new",
            "needsAddComponent": True,
        }

    route = _ROUTES[doc_type]
    return {
        **base,
        "componentName": route["name"],
        "componentIndex": route["index"],
        # Quảng Ninh (React/Radix) đính qua modal "Danh sách tài liệu điện tử" → engine wallet-modal.
        "target": "existing",
        "needsAddComponent": False,
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        # LLM-FIRST: type do LLM quyết; không hợp lệ/không rõ → other → thêm thành phần mới (không rớt file).
        llm_type = llm_types.get(index, "")
        doc_type = llm_type if llm_type in _ALLOWED else "other"
        source = "llm" if llm_type else "default"

        if doc_type in _ROUTES or doc_type == _AUTHORIZATION:
            item = _build_item(file, index, doc_type)
            attachments.append(item)
            classified_item = {
                "fileName": file_name,
                "docType": doc_type,
                "source": source,
                "target": item["target"],
            }
            if "componentIndex" in item:
                classified_item["componentIndex"] = item["componentIndex"]
            classified.append(classified_item)
            continue

        # Giấy tờ NGOÀI danh mục → KHÔNG bỏ qua: thêm thành phần hồ sơ MỚI (nút "Thêm thành phần hồ sơ")
        # đặt tên theo file để cán bộ không phải đính tay.
        new_name = _derive_component_name(file_name)
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": _wallet_label(new_name),
            "loaiBan": _LOAI_BAN,
            "detectedType": "other",
            "componentName": new_name,
            "target": "new",
            "needsAddComponent": True,
        })
        classified.append({"fileName": file_name, "docType": "other", "source": source, "target": "new"})

    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    ocr_files = [item for item in raw_files if item.get("type") in _OCR_TYPES]
    errors: list[str] = []

    from app.services import ocr

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    llm_documents = [
        {"index": index, "text": str(by_name.get(file.get("name"), {}).get("text") or "")}
        for index, file in enumerate(raw_files)
        if str(by_name.get(file.get("name"), {}).get("text") or "").strip()
    ]
    started = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_documents:
        try:
            llm_types = await _classify_with_llm(llm_documents, errors)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [item["name"] for item in raw_files],
            "ocrDocuments": [item.get("name") for item in ocr_results if item.get("text")],
            "llmDocuments": [raw_files[item["index"]]["name"] for item in llm_documents],
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
