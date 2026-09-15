"""Lập kế hoạch đính kèm CẤP ĐỔI GCN QSDĐ - do đo đạc lại thửa đất (ranh giới không đổi), KHÔNG phải
thực hiện nghĩa vụ tài chính - miền núi, hải đảo tại Quảng Ninh (maThuTuc 1.115848).

Cùng nền tảng (React/Radix, modal "Danh sách tài liệu điện tử" → engine wallet-modal, target "existing")
và cùng danh mục thành phần hồ sơ với biến thể "Các trường hợp khác"; tách package riêng để sửa độc lập.
componentName là khóa chính vì FE khớp substring sau khi fold dấu; componentIndex (1-based) chỉ là gợi ý.
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


def _derive_component_name(file_name: str) -> str:
    """Tên thành phần hồ sơ MỚI cho giấy tờ ngoài danh mục — lấy theo tên file (bỏ đuôi, gạch dưới→cách)."""
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", str(file_name or "")).strip()
    stem = re.sub(r"[_]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem or "Tài liệu khác kèm theo"

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_LOAI_BAN = "Bản chính"
_AUTHORIZATION = "van_ban_dai_dien"

# 6 hàng thành phần hồ sơ trong HTML (thứ tự DOM). componentName = đoạn tiêu đề đặc trưng để FE khớp.
_ROUTES: dict[str, dict[str, Any]] = {
    "to_khai_01_lptb": {
        "index": 1,
        "name": "Tờ khai lệ phí trước bạ theo Mẫu số 01/LPTB",
    },
    "to_khai_04_sddpnn": {
        "index": 2,
        "name": "Tờ khai thuế sử dụng đất phi nông nghiệp theo Mẫu số 04/TK-SDDPNN",
    },
    "to_khai_03_bds_tncn": {
        "index": 3,
        "name": "Tờ khai thuế thu nhập cá nhân theo Mẫu số 03/BĐS-TNCN",
    },
    "gcn_da_cap": {
        "index": 4,
        "name": "Giấy chứng nhận đã cấp",
    },
    "manh_trich_do": {
        "index": 5,
        "name": "Mảnh trích đo bản đồ địa chính thửa đất",
    },
    "don_mau_18": {
        "index": 6,
        "name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18",
    },
}
_ALLOWED = set(_ROUTES) | {_AUTHORIZATION, "other"}

_DISPLAY = {
    "to_khai_01_lptb": "Tờ khai lệ phí trước bạ Mẫu số 01/LPTB",
    "to_khai_04_sddpnn": "Tờ khai thuế sử dụng đất phi nông nghiệp Mẫu số 04/TK-SDDPNN",
    "to_khai_03_bds_tncn": "Tờ khai thuế thu nhập cá nhân Mẫu số 03/BĐS-TNCN",
    "gcn_da_cap": "Giấy chứng nhận quyền sử dụng đất đã cấp",
    "manh_trich_do": "Mảnh trích đo bản đồ địa chính",
    "don_mau_18": "Đơn đăng ký biến động đất đai Mẫu số 18",
    _AUTHORIZATION: "Văn bản đại diện hoặc ủy quyền",
}


def _normalize_doc_type(value: Any) -> str:
    folded = _fold(str(value or ""))
    for doc_type in _ALLOWED:
        if folded == _fold(doc_type):
            return doc_type
    return "other"


def _rule_doc_type(text: str) -> str:
    """Fallback chỉ dùng marker đủ đặc trưng để không đính nhầm hàng."""
    folded = _fold(text or "")
    if not folded:
        return ""

    # Mã biểu mẫu phải đứng trước các cụm mô tả chung trong đơn/tờ khai.
    if "03/bds-tncn" in folded:
        return "to_khai_03_bds_tncn"
    if "04/tk-sddpnn" in folded:
        return "to_khai_04_sddpnn"
    if "01/lptb" in folded:
        return "to_khai_01_lptb"

    # Tài liệu chính nhận diện trước GCN/tài liệu kèm ở trang sau.
    if "don dang ky bien dong dat dai, tai san gan lien voi dat" in folded or (
        "mau so 18" in folded and "dang ky bien dong" in folded
    ):
        return "don_mau_18"
    if any(
        marker in folded
        for marker in (
            "manh trich do ban do dia chinh thua dat",
            "phieu do dac chinh ly thua dat",
            "phieu xac nhan ket qua do dac hien trang thua dat",
            "ban mo ta ranh gioi, moc gioi thua dat",
        )
    ):
        return "manh_trich_do"
    if any(marker in folded for marker in ("giay uy quyen", "hop dong uy quyen", "van ban uy quyen")) or (
        "van ban ve viec dai dien" in folded and "phap luat ve dan su" in folded
    ):
        return _AUTHORIZATION
    if "giay chung nhan" in folded and any(
        marker in folded for marker in ("quyen su dung dat", "quyen so huu tai san gan lien voi dat")
    ):
        return "gcn_da_cap"
    return ""


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

    # Một prompt/call cho mỗi file: PDF dài hoặc một lỗi provider chỉ làm file đó fallback rule.
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
    ocr_by_name = {item.get("name"): item for item in ocr_results}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        text = str(ocr_by_name.get(file_name, {}).get("text") or "")
        llm_type = llm_types.get(index, "")
        rule_type = _rule_doc_type(text)

        if llm_type in _ROUTES or llm_type == _AUTHORIZATION:
            doc_type, source = llm_type, "llm"
        elif rule_type in _ROUTES or rule_type == _AUTHORIZATION:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = "other", "llm" if llm_type == "other" else "unknown"

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

        # Giấy tờ NGOÀI danh mục (vd Công văn xác nhận thông tin nhà ở) → KHÔNG bỏ qua: thêm thành phần
        # hồ sơ MỚI (nút "Thêm thành phần hồ sơ") đặt tên theo file để cán bộ không phải đính tay.
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
