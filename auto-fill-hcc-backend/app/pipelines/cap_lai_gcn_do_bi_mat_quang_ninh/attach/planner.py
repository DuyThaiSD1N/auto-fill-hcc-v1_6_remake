"""Lập kế hoạch đính kèm "[Đặc thù] Cấp lại Giấy chứng nhận do bị mất - Miền núi, hải đảo" tại Quảng Ninh
(1.115849).

Cùng nền tảng với các thủ tục đất đai Quảng Ninh khác (React/Radix, modal "Danh sách tài liệu điện tử"
→ engine wallet-modal). Bảng thành phần hồ sơ có 8 hàng cố định; componentName là khóa chính (FE khớp
substring sau khi fold dấu), componentIndex (1-based) chỉ là gợi ý thứ tự DOM.

GCN gốc đã MẤT nên hàng 1 thường để trống: bản photo GCN nằm sẵn trong bộ phiếu đo đạc (hàng 2) hoặc bộ
giấy tờ cấp lại/thừa kế (hàng 6). Mỗi file đính NGUYÊN vào một hàng (không tách trang); planner đề xuất
một câu trích yếu cho ô "Ghi chú", đọc từ đơn/phiếu đo đạc.
Hàng 7 (mất Trang bổ sung) chỉ dùng khi giấy tờ nói rõ việc mất Trang bổ sung.
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
from app.services.pdf_utils import trim_files_for_classify

from .prompt import SYSTEM_PROMPT, build_user_prompt


def _derive_component_name(file_name: str) -> str:
    """Tên thành phần hồ sơ MỚI cho giấy tờ ngoài danh mục — lấy theo tên file (bỏ đuôi, gạch dưới→cách)."""
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", str(file_name or "")).strip()
    stem = re.sub(r"[_]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem or "Tài liệu khác kèm theo"


_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
# Bộ hồ sơ hay có PDF gộp 10-25 trang: OCR đủ trang mất ~160s, quá timeout 100s của extension. Loại giấy tờ
# và số thửa/tờ/seri đều ở trang 1-2 → chỉ OCR 2 trang đầu (~35s); tệp đính lên cổng vẫn là bản gốc đủ trang.
_OCR_MAX_PAGES = 2
_LOAI_BAN = "Bản chính"
_AUTHORIZATION = "van_ban_dai_dien"
_EXTRA_TYPES = {_AUTHORIZATION}   # không có hàng sẵn → "Thêm thành phần hồ sơ"
_REQUIRED = ("giay_to_cap_lai_bi_mat", "don_mau_18")

# 8 hàng thành phần hồ sơ trên cổng (thứ tự DOM).
_ROUTES: dict[str, dict[str, Any]] = {
    "gcn_da_cap": {
        "index": 1,
        "name": "Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất đã cấp",
    },
    "manh_trich_do": {
        "index": 2,
        "name": "Mảnh trích đo bản đồ địa chính thửa đất",
    },
    "to_khai_01_lptb": {
        "index": 3,
        "name": "Tờ khai lệ phí trước bạ theo Mẫu số 01/LPTB",
    },
    "to_khai_sddpnn": {
        "index": 4,
        "name": "Tờ khai thuế sử dụng đất phi nông nghiệp theo Mẫu số 04/TK-SDDPNN",
    },
    "to_khai_03_bds_tncn": {
        "index": 5,
        "name": "Tờ khai thuế thu nhập cá nhân theo Mẫu số 03/BĐS-TNCN",
    },
    "giay_to_cap_lai_bi_mat": {
        "index": 6,
        "name": "Đối với trường hợp cấp lại Giấy chứng nhận bị mất",
    },
    "mat_trang_bo_sung": {
        "index": 7,
        "name": "Đối với trường hợp mất Trang bổ sung",
    },
    "don_mau_18": {
        "index": 8,
        "name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18",
    },
}
_ALLOWED = set(_ROUTES) | _EXTRA_TYPES | {"other"}

_DISPLAY = {
    "gcn_da_cap": "Giấy chứng nhận quyền sử dụng đất đã cấp",
    "manh_trich_do": "Mảnh trích đo bản đồ địa chính thửa đất",
    "to_khai_01_lptb": "Tờ khai lệ phí trước bạ Mẫu số 01/LPTB",
    "to_khai_sddpnn": "Tờ khai thuế sử dụng đất phi nông nghiệp",
    "to_khai_03_bds_tncn": "Tờ khai thuế thu nhập cá nhân Mẫu số 03/BĐS-TNCN",
    "giay_to_cap_lai_bi_mat": "Giấy tờ cấp lại Giấy chứng nhận bị mất",
    "mat_trang_bo_sung": "Giấy tờ trường hợp mất Trang bổ sung",
    "don_mau_18": "Đơn đăng ký biến động đất đai Mẫu số 18",
    _AUTHORIZATION: "Văn bản đại diện hoặc ủy quyền",
}

_MEASURE_MARKERS = (
    "phieu do dac chinh ly thua dat",
    "phieu xac nhan ket qua do dac hien trang thua dat",
    "ban mo ta ranh gioi, moc gioi thua dat",
    "manh trich do ban do dia chinh thua dat",
)
_DON_18_MARKER = "don dang ky bien dong dat dai, tai san gan lien voi dat"
_AUTHORIZATION_MARKERS = ("giay uy quyen", "hop dong uy quyen", "van ban uy quyen")
# Bộ giấy tờ cấp lại do mất GCN (thường gộp cả bộ thừa kế) — chỉ marker đủ đặc trưng.
_LOST_MARKERS = (
    "thong bao mat giay chung nhan",
    "xac nhan mat giay chung nhan",
    "bien ban ket thuc niem yet",
    "van ban phan chia di san",
    "van ban khai nhan di san",
    "van ban thoa thuan phan chia di san",
    "tu choi nhan di san",
)


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

    # Tờ khai liệt kê "Phiếu đo đạc", "Văn bản phân chia di sản" ở mục giấy tờ kèm → xét mã mẫu TRƯỚC.
    if "03/bds-tncn" in folded:
        return "to_khai_03_bds_tncn"
    if "tk-sddpnn" in folded:
        return "to_khai_sddpnn"
    if "01/lptb" in folded:
        return "to_khai_01_lptb"

    # Đơn Mẫu 18 cũng liệt kê phiếu đo đạc, văn bản phân chia di sản ở mục IV → xét đơn TRƯỚC.
    if _DON_18_MARKER in folded or ("mau so 18" in folded and "dang ky bien dong" in folded):
        return "don_mau_18"
    # Phiếu đo đạc ghi "GCN ... số seri" và hay kèm bản photo GCN + hợp đồng ủy quyền → xét TRƯỚC GCN.
    if any(marker in folded for marker in _MEASURE_MARKERS):
        return "manh_trich_do"
    if "mat trang bo sung" in folded:
        return "mat_trang_bo_sung"
    # Hợp đồng ủy quyền nhận thừa kế cũng nhắc "di sản" → chỉ coi là ủy quyền khi tiêu đề nằm ở đầu file.
    if any(marker in folded[:400] for marker in _AUTHORIZATION_MARKERS):
        return _AUTHORIZATION
    if any(marker in folded for marker in _LOST_MARKERS):
        return "giay_to_cap_lai_bi_mat"
    if "giay chung nhan" in folded and any(
        marker in folded for marker in ("quyen su dung dat", "quyen so huu tai san gan lien voi dat")
    ):
        return "gcn_da_cap"
    return ""


def _first(pattern: str, folded: str) -> str:
    match = re.search(pattern, folded)
    return match.group(1) if match else ""


def _suggest_note(texts: list[str]) -> str:
    """Câu trích yếu đề xuất cho ô Ghi chú, đọc từ đơn/phiếu đo đạc. Thiếu số thửa thì không đề xuất."""
    folded = " ".join(_fold(text) for text in texts if text)
    thua = _first(r"thua dat so\s*[:.]?\s*(\d+)", folded)
    if not thua:
        return ""
    to = _first(r"to ban do so\s*[:.]?\s*(\d+)", folded)
    seri = _first(r"seri\s*[:.]?\s*([a-z]{1,2}\s?\d{5,})", folded).upper()

    note = f"Cấp lại GCN do bị mất đối với thửa đất số {thua}"
    if to:
        note += f", tờ bản đồ số {to}"
    if seri:
        note += f" (GCN đã cấp số seri {seri})"
    if "nhan thua ke" in folded:
        note += "; đăng ký nhận thừa kế quyền sử dụng đất"
    elif "nhan tang cho" in folded:
        note += "; đăng ký nhận tặng cho quyền sử dụng đất"
    return note + "."


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
    if doc_type in _EXTRA_TYPES:
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
    note_sources: list[str] = []

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        text = str(ocr_by_name.get(file_name, {}).get("text") or "")
        llm_type = llm_types.get(index, "")
        rule_type = _rule_doc_type(text)

        if llm_type in _ROUTES or llm_type in _EXTRA_TYPES:
            doc_type, source = llm_type, "llm"
        elif rule_type in _ROUTES or rule_type in _EXTRA_TYPES:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = "other", "llm" if llm_type == "other" else "unknown"

        if doc_type in ("don_mau_18", "manh_trich_do"):
            note_sources.append(text)
        # Cổng ghi Mẫu 04/TK-SDDPNN nhưng hộ gia đình, cá nhân hay khai Mẫu 01 → nhắc kiểm tra, vẫn đính hàng 4.
        if doc_type == "to_khai_sddpnn" and "01/tk-sddpnn" in _fold(text):
            warnings.append(
                f'File "{file_name}" là Mẫu 01/TK-SDDPNN, cổng ghi Mẫu 04/TK-SDDPNN — kiểm tra lại mẫu trước khi nộp.'
            )

        if doc_type in _ROUTES or doc_type in _EXTRA_TYPES:
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

        # Giấy tờ NGOÀI danh mục → KHÔNG bỏ qua: thêm thành phần hồ sơ MỚI đặt tên theo file.
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

    found = {item["detectedType"] for item in attachments}
    for doc_type in _REQUIRED:
        if doc_type not in found:
            warnings.append(f'Chưa có "{_ROUTES[doc_type]["name"]}" (hàng {_ROUTES[doc_type]["index"]}) — mời bổ sung.')

    note = _suggest_note(note_sources)
    if note:
        warnings.append(f"Ghi chú (Trích yếu nội dung hồ sơ) đề xuất: {note}")

    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    ocr_files = trim_files_for_classify(
        [item for item in raw_files if item.get("type") in _OCR_TYPES], _OCR_MAX_PAGES
    )
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
