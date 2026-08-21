"""Lập kế hoạch đính kèm hồ sơ chuyển mục đích/hình thức/thời hạn đất tại Quảng Ninh.

Ba hàng 2, 6 và 14 trong HTML là tiêu đề nhóm, không nhận file. GCN và trích lục xuất hiện ở nhiều
nhánh nên chỉ được định tuyến sau khi xác định nhánh từ chính loại đơn trong cùng hồ sơ.
"""

import asyncio
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
_AUTHORIZATION = "van_ban_uy_quyen"

_BRANCH_BY_APPLICATION = {
    "don_chuyen_muc_dich": "chuyen_muc_dich",
    "don_chuyen_hinh_thuc": "chuyen_hinh_thuc",
    "don_gia_han": "gia_han",
    "don_dieu_chinh_thoi_han_du_an": "dieu_chinh_thoi_han_du_an",
}

# Extension dùng componentIndex 1-based. Các hàng 2, 6, 14 là tiêu đề nhóm nhưng vẫn có nút chọn
# file trong DOM, vì vậy chúng vẫn phải được tính khi xác định chỉ số hàng.
_ROUTES: dict[str, dict[str, Any]] = {
    "giay_to_mien_giam_nghia_vu_tai_chinh": {
        "index": 1,
        "name": "Giấy tờ chứng minh thuộc đối tượng miễn, giảm nghĩa vụ tài chính",
    },
    "don_chuyen_muc_dich": {
        "index": 3,
        "name": "Đơn theo Mẫu số 02 ban hành kèm theo Quy định của UBND tỉnh",
    },
    "don_chuyen_hinh_thuc": {
        "index": 7,
        "name": "Đơn theo Mẫu số 03 ban hành kèm theo Quy định của UBND tỉnh",
    },
    "quyet_dinh_dat_dai_chuyen_hinh_thuc": {
        "index": 9,
        "name": "Quyết định giao đất, quyết định cho thuê đất, quyết định cho phép chuyển mục đích sử dụng đất",
    },
    "don_gia_han": {
        "index": 11,
        "name": "Đơn theo Mẫu số 23 ban hành kèm theo Quy định này",
    },
    "quyet_dinh_dat_dai_gia_han": {
        "index": 12,
        "name": "Quyết định giao đất, cho thuê đất, cho phép chuyển mục đích sử dụng đất",
    },
    "van_ban_gia_han_du_an": {
        "index": 13,
        "name": "Văn bản của cơ quan có thẩm quyền cho phép gia hạn thời hạn hoạt động của dự án đầu tư",
    },
    "don_dieu_chinh_thoi_han_du_an": {
        "index": 15,
        "name": "Đơn theo Mẫu số 10 tại Phụ lục ban hành kèm theo Nghị định số 102/2024/NĐ-CP",
    },
    "van_ban_thay_doi_thoi_han_du_an": {
        "index": 16,
        "name": "Văn bản của cơ quan có thẩm quyền cho phép thay đổi thời hạn hoạt động của dự án đầu tư",
    },
    "to_khai_01_lptb": {
        "index": 18,
        "name": "Tờ khai lệ phí trước bạ theo Mẫu số 01/LPTB",
    },
    "to_khai_04_sddpnn": {
        "index": 19,
        "name": "Tờ khai thuế sử dụng đất phi nông nghiệp theo Mẫu số 04/TK-SDDPNN",
    },
    "to_khai_03_bds_tncn": {
        "index": 20,
        "name": "Tờ khai thuế thu nhập cá nhân theo Mẫu số 03/BĐS-TNCN",
    },
}

_BRANCH_ROUTES: dict[str, dict[str, dict[str, Any]]] = {
    "chuyen_muc_dich": {
        "gcn": {
            "index": 4,
            "name": "Một trong các giấy chứng nhận quy định tại khoản 21 Điều 3, khoản 3 Điều 256 Luật Đất đai",
        },
        "trich_luc_ban_do_dia_chinh": {"index": 5, "name": "Bản trích lục bản đồ địa chính"},
    },
    "chuyen_hinh_thuc": {
        "gcn": {
            "index": 8,
            # Dùng đoạn riêng của hàng 8 để fallback theo text không nhận nhầm hàng 4 là tiền tố.
            "name": "Một trong các loại giấy tờ quy định tại Điều 137 Luật Đất đai",
        },
        "trich_luc_ban_do_dia_chinh": {"index": 10, "name": "Bản trích lục bản đồ địa chính"},
    },
    "dieu_chinh_thoi_han_du_an": {
        "gcn": {
            "index": 17,
            # Đoạn riêng chỉ xuất hiện ở hàng GCN của nhánh điều chỉnh thời hạn dự án.
            "name": "Giấy chứng nhận quyền sở hữu công trình xây dựng",
        },
    },
}

_ALLOWED = set(_ROUTES) | set(_BRANCH_BY_APPLICATION) | {"gcn", "trich_luc_ban_do_dia_chinh", _AUTHORIZATION, "other"}
_DISPLAY = {
    "giay_to_mien_giam_nghia_vu_tai_chinh": "Giấy tờ chứng minh miễn, giảm nghĩa vụ tài chính",
    "don_chuyen_muc_dich": "Đơn đề nghị chuyển mục đích sử dụng đất",
    "gcn": "Giấy chứng nhận quyền sử dụng đất đã cấp",
    "trich_luc_ban_do_dia_chinh": "Bản trích lục bản đồ địa chính",
    "don_chuyen_hinh_thuc": "Đơn đề nghị chuyển hình thức sử dụng đất Mẫu số 03",
    "quyet_dinh_dat_dai_chuyen_hinh_thuc": "Quyết định về đất đai cho nhánh chuyển hình thức sử dụng đất",
    "don_gia_han": "Đơn đề nghị gia hạn sử dụng đất Mẫu số 23",
    "quyet_dinh_dat_dai_gia_han": "Quyết định về đất đai cho nhánh gia hạn sử dụng đất",
    "van_ban_gia_han_du_an": "Văn bản về thời hạn hoạt động của dự án đầu tư",
    "don_dieu_chinh_thoi_han_du_an": "Đơn điều chỉnh thời hạn sử dụng đất của dự án Mẫu số 10",
    "van_ban_thay_doi_thoi_han_du_an": "Văn bản cho phép thay đổi thời hạn hoạt động của dự án",
    "to_khai_01_lptb": "Tờ khai lệ phí trước bạ Mẫu số 01/LPTB",
    "to_khai_04_sddpnn": "Tờ khai thuế sử dụng đất phi nông nghiệp Mẫu số 04/TK-SDDPNN",
    "to_khai_03_bds_tncn": "Tờ khai thuế thu nhập cá nhân Mẫu số 03/BĐS-TNCN",
    _AUTHORIZATION: "Văn bản ủy quyền",
}


def _normalize_doc_type(value: Any) -> str:
    folded = _fold(str(value or ""))
    for doc_type in _ALLOWED:
        if folded == _fold(doc_type):
            return doc_type
    return "other"


def _rule_doc_type(text: str) -> str:
    """Fallback dùng marker đặc trưng; không dựa vào tên file hoặc thứ tự tải lên."""
    folded = _fold(text or "")
    if not folded:
        return ""

    if "03/bds-tncn" in folded:
        return "to_khai_03_bds_tncn"
    if "04/tk-sddpnn" in folded:
        return "to_khai_04_sddpnn"
    if "01/lptb" in folded:
        return "to_khai_01_lptb"
    if "don de nghi chuyen muc dich su dung dat" in folded or (
        "mau so 02" in folded and "chuyen muc dich su dung dat" in folded
    ):
        return "don_chuyen_muc_dich"
    if ("don" in folded and "chuyen hinh thuc su dung dat" in folded) or (
        "mau so 03" in folded and "chuyen hinh thuc su dung dat" in folded
    ):
        return "don_chuyen_hinh_thuc"
    if ("don" in folded and "gia han su dung dat" in folded) or (
        "mau so 23" in folded and "gia han" in folded
    ):
        return "don_gia_han"
    if ("don" in folded and "dieu chinh thoi han su dung dat" in folded) or (
        "mau so 10" in folded and "thoi han su dung dat" in folded
    ):
        return "don_dieu_chinh_thoi_han_du_an"
    if any(marker in folded for marker in ("trich luc ban do dia chinh", "trich luc manh trich do ban do dia chinh")):
        return "trich_luc_ban_do_dia_chinh"
    if "giay chung nhan" in folded and any(
        marker in folded for marker in ("quyen su dung dat", "quyen so huu tai san gan lien voi dat")
    ):
        return "gcn"
    if "cho phep thay doi thoi han hoat dong cua du an dau tu" in folded:
        return "van_ban_thay_doi_thoi_han_du_an"
    if "gia han thoi han hoat dong cua du an dau tu" in folded or (
        "thoi han hoat dong cua du an dau tu" in folded and "gia han" in folded
    ):
        return "van_ban_gia_han_du_an"
    if "quyet dinh" in folded and any(
        marker in folded for marker in ("giao dat", "cho thue dat", "cho phep chuyen muc dich su dung dat")
    ):
        # Quyết định có cùng nội dung ở hai nhánh; nếu không có nhãn nhánh rõ ràng thì để LLM/đơn
        # quyết định, không ép vào một hàng bằng fallback.
        return ""
    if "mien" in folded and "giam" in folded and "nghia vu tai chinh" in folded:
        return "giay_to_mien_giam_nghia_vu_tai_chinh"
    if any(marker in folded for marker in ("giay uy quyen", "hop dong uy quyen", "van ban uy quyen")):
        return _AUTHORIZATION
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


def _resolved_types(files: list[dict], ocr_results: list[dict], llm_types: dict[int, str]) -> list[tuple[str, str]]:
    ocr_by_name = {item.get("name"): item for item in ocr_results}
    resolved: list[tuple[str, str]] = []
    for index, file in enumerate(files):
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        llm_type = llm_types.get(index, "")
        rule_type = _rule_doc_type(text)
        if llm_type in _ALLOWED - {"other"}:
            resolved.append((llm_type, "llm"))
        elif rule_type in _ALLOWED - {"other"}:
            resolved.append((rule_type, "rule"))
        else:
            resolved.append(("other", "llm" if llm_type == "other" else "unknown"))
    return resolved


def _dossier_branch(resolved: list[tuple[str, str]]) -> str:
    branches = {
        _BRANCH_BY_APPLICATION[doc_type]
        for doc_type, _source in resolved
        if doc_type in _BRANCH_BY_APPLICATION
    }
    return next(iter(branches)) if len(branches) == 1 else ""


def _build_item(file: dict, file_index: int, doc_type: str, route: dict[str, Any]) -> dict:
    return {
        "fileIndex": file_index,
        "fileName": str(file.get("name") or f"file-{file_index + 1}"),
        "documentName": _wallet_label(_DISPLAY[doc_type]),
        "loaiBan": _LOAI_BAN,
        "detectedType": doc_type,
        "componentName": route["name"],
        "componentIndex": route["index"],
        # Quảng Ninh (React/Radix) đính qua modal "Danh sách tài liệu điện tử" như Bộ Tư pháp → engine
        # wallet-modal (target "existing"), không phải bảng mat-radio attp-row.
        "target": "existing",
        "needsAddComponent": False,
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict], str]:
    llm_types = llm_types or {}
    resolved = _resolved_types(files, ocr_results, llm_types)
    branch = _dossier_branch(resolved)
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for index, (file, (doc_type, source)) in enumerate(zip(files, resolved, strict=True)):
        file_name = str(file.get("name") or f"file-{index + 1}")
        route = _ROUTES.get(doc_type)
        if doc_type in {"gcn", "trich_luc_ban_do_dia_chinh"}:
            route = _BRANCH_ROUTES.get(branch, {}).get(doc_type)

        if doc_type == _AUTHORIZATION:
            item = {
                "fileIndex": index,
                "fileName": file_name,
                "documentName": _wallet_label(_DISPLAY[doc_type]),
                "loaiBan": _LOAI_BAN,
                "detectedType": doc_type,
                "componentName": _DISPLAY[doc_type],
                "target": "new",
                "needsAddComponent": True,
            }
        elif route:
            item = _build_item(file, index, doc_type, route)
        else:
            if doc_type in {"gcn", "trich_luc_ban_do_dia_chinh"} and not branch:
                reason = "không xác định được nhánh hồ sơ từ loại đơn"
            elif doc_type in {"gcn", "trich_luc_ban_do_dia_chinh"}:
                reason = f"loại giấy tờ không có hàng phù hợp trong nhánh {branch}"
            else:
                reason = "không xác định được loại giấy tờ"
            warnings.append(f"File '{file_name}': {reason} — vui lòng đính kèm thủ công.")
            classified.append({
                "fileName": file_name,
                "docType": doc_type,
                "source": source,
                "branch": branch or None,
                "skipped": True,
            })
            continue

        attachments.append(item)
        classified_item = {
            "fileName": file_name,
            "docType": doc_type,
            "source": source,
            "branch": branch or None,
            "target": item["target"],
        }
        if "componentIndex" in item:
            classified_item["componentIndex"] = item["componentIndex"]
        classified.append(classified_item)

    return attachments, warnings, classified, branch


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

    attachments, warnings, classified, branch = build_plan_items(raw_files, ocr_results, llm_types)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [item["name"] for item in raw_files],
            "ocrDocuments": [item.get("name") for item in ocr_results if item.get("text")],
            "llmDocuments": [raw_files[item["index"]]["name"] for item in llm_documents],
            "classified": classified,
            "branch": branch or None,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
