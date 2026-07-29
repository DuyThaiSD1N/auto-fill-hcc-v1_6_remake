"""Đính kèm cho thủ tục đăng ký lắp đặt sử dụng nước sạch."""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold
from app.pipelines.cap_nuoc_sach.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_HOUSEHOLD_APPLICATION = "household_application"
_ORGANIZATION_APPLICATION = "organization_application"
_BUSINESS_REGISTRATION = "business_registration_or_establishment"
_LEGAL_LAND_HOUSE = "legal_land_house_document"
_TRANSFER_CONTRACT = "land_house_transfer_contract"
_ORG_PROPERTY_LEASE = "organization_property_or_lease_authorization"
_IDENTITY = "identity_document"
_OTHER = "other"

SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": _HOUSEHOLD_APPLICATION,
        "slotIndex": 0,
        "slotName": "Đơn đề nghị đấu nối nước sạch và hợp đồng dịch vụ cấp nước (theo mẫu.)",
        "detectedType": "Đơn đề nghị cấp nước sạch hộ gia đình",
        "documentName": "Đơn đề nghị cấp nước sạch hộ gia đình",
    },
    {
        "slotKey": _ORGANIZATION_APPLICATION,
        "slotIndex": 1,
        "slotName": "Đơn đề nghị đấu nối nước sạch và hợp đồng dịch vụ cấp nước (tổ chức.)",
        "detectedType": "Đơn đề nghị cấp nước sạch tổ chức",
        "documentName": "Đơn đề nghị cấp nước sạch tổ chức",
    },
    {
        "slotKey": _BUSINESS_REGISTRATION,
        "slotIndex": 2,
        "slotName": "Quyết định thành lập/Giấy chứng nhận đăng ký kinh doanh",
        "detectedType": "Giấy chứng nhận đăng ký doanh nghiệp hoặc quyết định thành lập",
        "documentName": "Giấy chứng nhận đăng ký doanh nghiệp",
    },
    {
        "slotKey": _LEGAL_LAND_HOUSE,
        "slotIndex": 3,
        "slotName": "Giấy tờ chứng minh nhà, đất hợp pháp",
        "detectedType": "Giấy tờ chứng minh nhà, đất hợp pháp",
        "documentName": "Giấy chứng nhận quyền sử dụng đất",
    },
    {
        "slotKey": _TRANSFER_CONTRACT,
        "slotIndex": 4,
        "slotName": "Hợp đồng chuyển nhượng quyền sử dụng đất/quyền sở hữu nhà ở",
        "detectedType": "Hợp đồng chuyển nhượng/mua bán nhà đất",
        "documentName": "Hợp đồng chuyển nhượng nhà đất",
    },
    {
        "slotKey": _ORG_PROPERTY_LEASE,
        "slotIndex": 5,
        "slotName": "Giấy chứng nhận nhà đất của tổ chức hoặc hợp đồng thuê/ủy quyền lắp đặt",
        "detectedType": "Giấy tờ nhà đất của tổ chức hoặc hợp đồng thuê/ủy quyền",
        "documentName": "Giấy tờ nhà đất của tổ chức",
    },
]

_SLOT_BY_KEY = {item["slotKey"]: item for item in SLOTS}
_ALLOWED_DOC_TYPES = set(_SLOT_BY_KEY) | {_IDENTITY, _OTHER}


async def _ocr_per_file(files: list[dict]) -> list[dict]:
    from app.services import ocr

    return await ocr.ocr_per_file(files)


def _is_identity_text(text: str) -> bool:
    haystack = fold(text)
    return any(
        marker in haystack
        for marker in (
            "can cuoc cong dan",
            "chung minh nhan dan",
            "the can cuoc",
            "citizen identity card",
            "identity card",
            "ho chieu",
            "passport",
        )
    )


def _rule_doc_type(text: str) -> str:
    haystack = fold(text)
    if not haystack:
        return ""

    if _is_identity_text(haystack):
        return _IDENTITY

    if (
        "giay chung nhan dang ky doanh nghiep" in haystack
        or "giay chung nhan dang ky kinh doanh" in haystack
        or "ma so doanh nghiep" in haystack
        or "dang ky kinh doanh" in haystack
        or "quyet dinh thanh lap" in haystack
    ):
        return _BUSINESS_REGISTRATION

    if (
        "hop dong chuyen nhuong" in haystack
        or "hop dong mua ban nha dat" in haystack
        or ("chuyen nhuong quyen su dung dat" in haystack and "hop dong" in haystack)
    ):
        return _TRANSFER_CONTRACT

    if (
        "hop dong thue nha dat" in haystack
        or "thue tru so" in haystack
        or ("van ban uy quyen" in haystack and "lap dat dong ho" in haystack)
        or ("co quan" in haystack and "to chuc" in haystack and "doanh nghiep" in haystack and "quyen so huu nha" in haystack)
    ):
        return _ORG_PROPERTY_LEASE

    if (
        "don de nghi cap nuoc sach" in haystack
        or "don de nghi dau noi nuoc sach" in haystack
        or "hop dong dich vu cap nuoc" in haystack
    ):
        if (
            "mau co quan" in haystack
            or "ten co quan" in haystack
            or "nguoi dai dien" in haystack
            or "mst cq/dn" in haystack
            or "mst cq dn" in haystack
        ):
            return _ORGANIZATION_APPLICATION
        return _HOUSEHOLD_APPLICATION

    if (
        "giay chung nhan" in haystack
        and (
            "quyen su dung dat" in haystack
            or "quyen so huu tai san gan lien voi dat" in haystack
            or "quyen so huu nha" in haystack
        )
    ) or ("thua dat" in haystack and "to ban do" in haystack):
        return _LEGAL_LAND_HOUSE

    return ""


def _normalize_doc_type(value: str) -> str:
    raw = str(value or "").strip()
    if raw in _ALLOWED_DOC_TYPES:
        return raw
    text = fold(raw)
    if not text or text == "other":
        return _OTHER
    if "identity" in text or "can cuoc" in text or "cccd" in text:
        return _IDENTITY
    if "household" in text or "ho gia dinh" in text or "chu ho" in text:
        return _HOUSEHOLD_APPLICATION
    if "organization_application" in text or "co quan" in text or "to chuc" in text:
        return _ORGANIZATION_APPLICATION
    if "business" in text or "dang ky doanh nghiep" in text or "quyet dinh thanh lap" in text:
        return _BUSINESS_REGISTRATION
    if "transfer" in text or "chuyen nhuong" in text or "mua ban nha dat" in text:
        return _TRANSFER_CONTRACT
    if "lease" in text or "thue" in text or "uy quyen" in text:
        return _ORG_PROPERTY_LEASE
    if "land" in text or "house" in text or "quyen su dung dat" in text:
        return _LEGAL_LAND_HOUSE
    return _OTHER


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}

    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=700, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    out: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        out[idx] = _normalize_doc_type(str(item.get("docType") or item.get("type") or ""))
    return out


def _build_fixed_item(file: dict, file_index: int, slot_key: str) -> dict:
    slot = _SLOT_BY_KEY[slot_key]
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": slot["documentName"],
        "componentName": slot["slotName"],
        "target": "fixed-slot",
        "needsAddComponent": False,
        "detectedType": slot["detectedType"],
        "slotKey": slot["slotKey"],
        "slotIndex": slot["slotIndex"],
        "slotName": slot["slotName"],
    }


def _build_identity_item(file: dict, file_index: int) -> dict:
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": "Căn cước công dân người nộp",
        "componentName": "Căn cước công dân người nộp",
        "target": "new",
        "componentIndex": None,
        "needsAddComponent": True,
        "detectedType": "Căn cước công dân",
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    by_name = {item.get("name"): item for item in ocr_results}
    items: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = str(by_name.get(file_name, {}).get("text") or "")
        rule_type = _rule_doc_type(text)
        llm_type = llm_types.get(idx, "")
        doc_type = llm_type if llm_type in _ALLOWED_DOC_TYPES and llm_type != _OTHER else rule_type
        if not doc_type:
            doc_type = llm_type if llm_type in _ALLOWED_DOC_TYPES else _OTHER

        if doc_type == _IDENTITY:
            items.append(_build_identity_item(file, idx))
            classified.append({"fileName": file_name, "docType": _IDENTITY, "source": "llm" if llm_type == _IDENTITY else "rule"})
            continue

        if doc_type in _SLOT_BY_KEY:
            items.append(_build_fixed_item(file, idx, doc_type))
            classified.append({
                "fileName": file_name,
                "docType": doc_type,
                "source": "llm" if llm_type in _SLOT_BY_KEY else "rule",
                "slotIndex": _SLOT_BY_KEY[doc_type]["slotIndex"],
            })
            continue

        warnings.append(f"Không xác định được loại giấy tờ cho file '{file_name}' — bỏ qua, vui lòng đính kèm thủ công.")
        classified.append({"fileName": file_name, "docType": _OTHER, "source": "unknown"})

    return items, warnings, classified


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    _ = options or {}
    _ = session
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    t0 = time.monotonic()
    ocr_results = await _ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    ocr_by_name = {item.get("name"): item for item in ocr_results}
    llm_docs: list[dict[str, Any]] = []
    for idx, file in enumerate(raw_files):
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        if text.strip():
            llm_docs.append({"index": idx, "text": text})

    t1 = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types)
    errors.extend(warnings)
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "classified": classified,
            "skippedOcr": skipped_ocr,
            "slots": SLOTS,
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "errors": errors,
    }
