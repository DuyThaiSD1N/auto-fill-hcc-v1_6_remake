"""Đính kèm cho thủ tục chuyển đổi tên hợp đồng nước sạch."""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold
from app.pipelines.doi_ten_nuoc_sach.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_CONFIRMED_APPLICATION = "confirmed_name_change_application"
_TEMPLATE_APPLICATION = "template_name_change_application"
_BUSINESS_REGISTRATION = "business_registration_or_establishment"
_LEGAL_LAND_HOUSE = "legal_land_house_document"
_TRANSFER_CONTRACT = "transfer_contract"
_ORG_PROPERTY_LEASE = "organization_property_or_lease_authorization"
_OWNER_CONSENT = "owner_consent_for_company_rental"
_IDENTITY = "identity_document"
_OTHER = "other"

SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": "doi_ten_legal_land_house_document",
        "docType": _LEGAL_LAND_HOUSE,
        "slotIndex": 0,
        "slotName": "Giấy tờ chứng minh nhà, đất hợp pháp",
        "detectedType": "Giấy tờ chứng minh nhà, đất hợp pháp",
        "documentName": "Giấy chứng nhận quyền sử dụng đất",
    },
    {
        "slotKey": "doi_ten_confirmed_name_change_application",
        "docType": _CONFIRMED_APPLICATION,
        "slotIndex": 1,
        "slotName": "Đơn xin đổi tên trong Hợp đồng dịch vụ cấp nước có xác nhận và dấu của 02 đơn vị",
        "detectedType": "Đơn xin đổi tên trong hợp đồng dịch vụ cấp nước",
        "documentName": "Đơn xin đổi tên trong hợp đồng dịch vụ cấp nước",
    },
    {
        "slotKey": "doi_ten_org_property_or_lease_authorization",
        "docType": _ORG_PROPERTY_LEASE,
        "slotIndex": 2,
        "slotName": "Giấy chứng nhận nhà đất của tổ chức hoặc hợp đồng thuê/ủy quyền lắp đặt",
        "detectedType": "Giấy tờ nhà đất của tổ chức hoặc hợp đồng thuê/ủy quyền",
        "documentName": "Giấy tờ nhà đất của tổ chức",
    },
    {
        "slotKey": "doi_ten_business_registration_or_establishment",
        "docType": _BUSINESS_REGISTRATION,
        "slotIndex": 3,
        "slotName": "Quyết định thành lập/Giấy chứng nhận đăng ký kinh doanh",
        "detectedType": "Giấy chứng nhận đăng ký doanh nghiệp hoặc quyết định thành lập",
        "documentName": "Giấy chứng nhận đăng ký doanh nghiệp",
    },
    {
        "slotKey": "doi_ten_template_name_change_application",
        "docType": _TEMPLATE_APPLICATION,
        "slotIndex": 4,
        "slotName": "Đơn đề nghị đổi tên trong Hợp đồng dịch vụ cấp nước (theo mẫu.)",
        "detectedType": "Đơn đề nghị đổi tên trong hợp đồng dịch vụ cấp nước theo mẫu",
        "documentName": "Đơn đề nghị đổi tên trong hợp đồng dịch vụ cấp nước",
    },
    {
        "slotKey": "doi_ten_transfer_contract",
        "docType": _TRANSFER_CONTRACT,
        "slotIndex": 5,
        "slotName": "Hợp đồng chuyển nhượng quyền sử dụng đất/quyền sở hữu nhà ở",
        "detectedType": "Hợp đồng chuyển nhượng/mua bán nhà đất",
        "documentName": "Hợp đồng chuyển nhượng nhà đất",
    },
    {
        "slotKey": "doi_ten_owner_consent_company_rental",
        "docType": _OWNER_CONSENT,
        "slotIndex": 6,
        "slotName": "Giấy đồng thuận của chủ nhà cho công ty đứng tên đồng hồ nước",
        "detectedType": "Giấy đồng thuận của chủ nhà",
        "documentName": "Giấy đồng thuận của chủ nhà",
    },
]

_SLOT_BY_DOC_TYPE = {item["docType"]: item for item in SLOTS}
_ALLOWED_DOC_TYPES = set(_SLOT_BY_DOC_TYPE) | {_IDENTITY, _OTHER}


async def _ocr_per_file(files: list[dict]) -> list[dict]:
    from app.services import ocr

    return await ocr.ocr_per_file(files)


def _is_identity_text(text: str) -> bool:
    haystack = fold(text)
    return any(
        marker in haystack
        for marker in (
            "can cuoc cong dan",
            "can cuoc",
            "chung minh nhan dan",
            "the can cuoc",
            "citizen identity card",
            "identity card",
            "personal identification number",
            "ho chieu",
            "passport",
        )
    )


def _is_name_change_application(haystack: str) -> bool:
    return (
        "don xin doi ten trong hop dong dich vu cap nuoc" in haystack
        or "don de nghi doi ten trong hop dong dich vu cap nuoc" in haystack
        or ("doi ten" in haystack and "hop dong dich vu cap nuoc" in haystack)
    )


def _is_confirmed_application(haystack: str) -> bool:
    return any(
        marker in haystack
        for marker in (
            "ben giao",
            "ben nhan",
            "ben chuyen nhuong",
            "ben nhan chuyen nhuong",
            "xac nhan va dau cua 02 don vi",
            "dau cua 02 don vi",
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
        "giay dong thuan" in haystack
        or ("chu nha dong y" in haystack and "dong ho nuoc" in haystack)
        or ("cong ty thue nha" in haystack and "chu nha" in haystack)
    ):
        return _OWNER_CONSENT

    if (
        "hop dong chuyen nhuong" in haystack
        or "hop dong mua ban nha dat" in haystack
        or ("hop dong" in haystack and "chuyen nhuong quyen su dung dat" in haystack)
    ):
        return _TRANSFER_CONTRACT

    if (
        "hop dong thue nha dat" in haystack
        or "thue tru so" in haystack
        or ("van ban uy quyen" in haystack and ("lap dat dong ho" in haystack or "dong ho nuoc" in haystack))
        or ("co quan" in haystack and "to chuc" in haystack and "doanh nghiep" in haystack and "quyen so huu nha" in haystack)
    ):
        return _ORG_PROPERTY_LEASE

    if _is_name_change_application(haystack):
        return _CONFIRMED_APPLICATION if _is_confirmed_application(haystack) else _TEMPLATE_APPLICATION

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
    if "confirmed" in text or "don xin doi ten" in text or "xac nhan" in text:
        return _CONFIRMED_APPLICATION
    if "template" in text or "theo mau" in text:
        return _TEMPLATE_APPLICATION
    if "business" in text or "dang ky doanh nghiep" in text or "quyet dinh thanh lap" in text:
        return _BUSINESS_REGISTRATION
    if "transfer" in text or "chuyen nhuong" in text or "mua ban nha dat" in text:
        return _TRANSFER_CONTRACT
    if "owner_consent" in text or "dong thuan" in text or "chu nha dong y" in text:
        return _OWNER_CONSENT
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
    raw = await client.chat(messages, max_tokens=800, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    out: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        out[idx] = _normalize_doc_type(str(item.get("docType") or item.get("type") or ""))
    return out


def _build_fixed_item(file: dict, file_index: int, doc_type: str) -> dict:
    slot = _SLOT_BY_DOC_TYPE[doc_type]
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

        if doc_type in _SLOT_BY_DOC_TYPE:
            slot = _SLOT_BY_DOC_TYPE[doc_type]
            items.append(_build_fixed_item(file, idx, doc_type))
            classified.append({
                "fileName": file_name,
                "docType": doc_type,
                "source": "llm" if llm_type in _SLOT_BY_DOC_TYPE else "rule",
                "slotIndex": slot["slotIndex"],
                "slotKey": slot["slotKey"],
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
